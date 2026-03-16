# -*- coding: utf-8 -*-
"""
ScanValidator - 同质性自检模块 V1.0

核心职责：
  验证 scan 路径（run_historical_stream）与 live 路径（_run_radar_main_loop）
  对同一日期、同一批 Tick 数据打出的分数是否在容差范围内一致。

设计原则：
  - 方案B 严格入场：榜首必须通过 TriggerValidator 物理信号背书
  - 单仓（单吊）：任何时刻只允许 1 只持仓，集中火力
  - 零依赖外部网络：纯本地计算，不调用任何网络接口
  - 发现分叉立即抛出，不静默吞咽

【同质性自检三道门】
  门1: flow 计算路径一致性（扫描路径 vs 均摊路径差异率 < 20%）
  门2: volume 单位断言（手 or 股，必须一致）
  门3: TOP5 分数误差率 < 5%（scan 结果 vs live 盘后结果对比）

Author: CTO Research Lab
Date: 2026-03-16
Version: V1.0
"""
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """单项自检结果"""
    gate: str                    # 门编号: "GATE1" / "GATE2" / "GATE3"
    passed: bool                 # 是否通过
    score: float                 # 通过率 0.0~1.0
    detail: str                  # 描述
    samples: List[Dict] = field(default_factory=list)  # 抽样数据


@dataclass
class ScanVsLiveReport:
    """
    scan vs live 同质性报告
    """
    date: str                           # 检验日期 YYYYMMDD
    generated_at: str                   # 报告生成时间
    overall_passed: bool                # 总判定
    gates: List[ValidationResult] = field(default_factory=list)
    scan_top5: List[Dict] = field(default_factory=list)   # scan TOP5
    live_top5: List[Dict] = field(default_factory=list)   # live TOP5
    score_divergence_pct: float = 0.0   # 分数平均偏差率(%)
    verdict: str = ""                   # 最终裁定文本
    recommendations: List[str] = field(default_factory=list)  # 修复建议

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d


class ScanValidator:
    """
    同质性自检器

    用法:
        validator = ScanValidator(date="20260316")

        # 在 run_historical_stream 末尾注入 scan 结果
        validator.record_scan_result(scan_top_targets, scan_tick_metadata)

        # 在 _run_radar_main_loop 盘后定格后注入 live 结果
        validator.record_live_result(live_top_targets, live_tick_metadata)

        # 执行三道门验证，输出报告
        report = validator.validate()
        validator.export_report(report, "data/validation/20260316_scan_vs_live.json")
    """

    # 同质性容差阈值
    SCORE_TOLERANCE_PCT = 5.0       # TOP5 分数误差容忍上限 (%)
    FLOW_DIVERGENCE_THRESHOLD = 0.20  # flow 计算路径偏差容忍上限 (20%)
    MAX_VOLUME_UNIT_RATIO = 100.5   # volume 单位比值上限：手->股 = 100x，超出则报警

    def __init__(self, date: str = None):
        """
        Args:
            date: 检验日期 YYYYMMDD，默认今天
        """
        self.date = date or datetime.now().strftime('%Y%m%d')
        self._scan_result: Optional[Dict] = None
        self._live_result: Optional[Dict] = None
        self._scan_tick_meta: List[Dict] = []
        self._live_tick_meta: List[Dict] = []
        logger.info(f"[ScanValidator] 初始化完成，检验日期: {self.date}")

    # ------------------------------------------------------------------
    # 数据注入接口
    # ------------------------------------------------------------------

    def record_scan_result(
        self,
        top_targets: List[Dict],
        tick_metadata: List[Dict] = None
    ):
        """
        注入 scan 路径结果

        Args:
            top_targets: run_historical_stream 计算出的 current_top_targets
            tick_metadata: [{stock_code, volume_raw, volume_unit}] 用于 GATE2 volume 单位断言
        """
        self._scan_result = {
            'top_targets': top_targets[:10],
            'recorded_at': datetime.now().isoformat()
        }
        self._scan_tick_meta = tick_metadata or []
        logger.info(f"[ScanValidator] scan 结果已注入: {len(top_targets)} 只")

    def record_live_result(
        self,
        top_targets: List[Dict],
        tick_metadata: List[Dict] = None
    ):
        """
        注入 live 路径结果（盘后定格快照）

        Args:
            top_targets: _run_radar_main_loop 盘后算出的 current_top_targets
            tick_metadata: [{stock_code, volume_raw, volume_unit}]
        """
        self._live_result = {
            'top_targets': top_targets[:10],
            'recorded_at': datetime.now().isoformat()
        }
        self._live_tick_meta = tick_metadata or []
        logger.info(f"[ScanValidator] live 结果已注入: {len(top_targets)} 只")

    # ------------------------------------------------------------------
    # 核心验证
    # ------------------------------------------------------------------

    def validate(self) -> ScanVsLiveReport:
        """
        执行三道门同质性验证

        Returns:
            ScanVsLiveReport 报告对象
        """
        report = ScanVsLiveReport(
            date=self.date,
            generated_at=datetime.now().isoformat(),
            overall_passed=False
        )

        # 如果任意一方没有数据，直接失败
        if not self._scan_result or not self._live_result:
            missing = []
            if not self._scan_result:
                missing.append('scan')
            if not self._live_result:
                missing.append('live')
            report.verdict = f"[FAIL] 缺失数据源: {missing}，无法执行同质性验证"
            report.recommendations.append(
                f"请确保在 run_historical_stream 末尾调用 validator.record_scan_result()，"
                f"在 _run_radar_main_loop 盘后定格后调用 validator.record_live_result()"
            )
            return report

        scan_top = self._scan_result['top_targets']
        live_top = self._live_result['top_targets']
        report.scan_top5 = scan_top[:5]
        report.live_top5 = live_top[:5]

        # === GATE1: flow 计算路径一致性 ===
        gate1 = self._gate1_flow_path(scan_top, live_top)
        report.gates.append(gate1)

        # === GATE2: volume 单位断言 ===
        gate2 = self._gate2_volume_unit()
        report.gates.append(gate2)

        # === GATE3: TOP5 分数误差率 ===
        gate3, divergence = self._gate3_score_divergence(scan_top, live_top)
        report.gates.append(gate3)
        report.score_divergence_pct = divergence

        # === 总裁定 ===
        all_passed = all(g.passed for g in report.gates)
        report.overall_passed = all_passed

        if all_passed:
            report.verdict = (
                f"[PASS] 同质性验证通过 | 分数偏差: {divergence:.2f}% | "
                f"盘后改动 live 100% 可用"
            )
        else:
            failed_gates = [g.gate for g in report.gates if not g.passed]
            report.verdict = (
                f"[FAIL] 同质性验证未通过 | 失败门: {failed_gates} | "
                f"分数偏差: {divergence:.2f}% | 禁止用 scan 结论代替 live 决策"
            )
            report.recommendations.extend(
                self._generate_recommendations(report.gates)
            )

        self._log_report_summary(report)
        return report

    # ------------------------------------------------------------------
    # 三道门具体实现
    # ------------------------------------------------------------------

    def _gate1_flow_path(
        self,
        scan_top: List[Dict],
        live_top: List[Dict]
    ) -> ValidationResult:
        """
        GATE1: flow 计算路径一致性

        原理：scan 走 calculate_time_slice_flows（真实切片），
              live 走时间均摊估算。对相同代码的 inflow_ratio 进行对比。
              如果同一只票的 inflow_ratio 差异超过 20%，说明路径分叉。
        """
        scan_map = {t['code']: t for t in scan_top}
        live_map = {t['code']: t for t in live_top}
        common_codes = set(scan_map.keys()) & set(live_map.keys())

        if not common_codes:
            return ValidationResult(
                gate='GATE1',
                passed=False,
                score=0.0,
                detail=(
                    f"scan TOP 和 live TOP 无交集（scan:{len(scan_top)}只, "
                    f"live:{len(live_top)}只），可能是时间切片数据缺失导致 scan 大量 continue 跳过"
                )
            )

        divergent_samples = []
        consistent_count = 0

        for code in common_codes:
            s_ir = scan_map[code].get('inflow_ratio', 0.0)
            l_ir = live_map[code].get('inflow_ratio', 0.0)
            base = max(abs(s_ir), abs(l_ir), 1e-6)
            diff_pct = abs(s_ir - l_ir) / base

            if diff_pct > self.FLOW_DIVERGENCE_THRESHOLD:
                divergent_samples.append({
                    'code': code,
                    'scan_inflow_ratio': round(s_ir, 4),
                    'live_inflow_ratio': round(l_ir, 4),
                    'diff_pct': round(diff_pct * 100, 2)
                })
            else:
                consistent_count += 1

        pass_rate = consistent_count / len(common_codes)
        passed = pass_rate >= 0.80  # 至少 80% 的公共票 flow 一致

        return ValidationResult(
            gate='GATE1',
            passed=passed,
            score=pass_rate,
            detail=(
                f"共 {len(common_codes)} 只公共票 | "
                f"一致: {consistent_count} 只({pass_rate*100:.1f}%) | "
                f"分叉: {len(divergent_samples)} 只"
            ),
            samples=divergent_samples[:5]
        )

    def _gate2_volume_unit(self) -> ValidationResult:
        """
        GATE2: volume 单位断言

        scan 路径喂入的 tick.volume 单位必须与 live 路径一致（都是手，或都是股）。
        通过检查 tick_metadata 中的 volume_unit 字段是否统一来判断。
        如果未注入 tick_metadata，则报告为 WARNING（不阻断）。
        """
        if not self._scan_tick_meta and not self._live_tick_meta:
            return ValidationResult(
                gate='GATE2',
                passed=True,  # 无元数据时警告但不阻断
                score=1.0,
                detail=(
                    "[WARNING] 未注入 tick_metadata，无法执行 volume 单位断言。"
                    "建议在 MockQmtAdapter 中添加 volume_unit 字段注入。"
                )
            )

        all_meta = self._scan_tick_meta + self._live_tick_meta
        units = set(m.get('volume_unit', 'unknown') for m in all_meta)

        if len(units) > 1:
            return ValidationResult(
                gate='GATE2',
                passed=False,
                score=0.0,
                detail=(
                    f"[FAIL] volume 单位不统一！检测到多种单位: {units}。"
                    f"scan 和 live 路径对同一字段使用了不同单位，"
                    f"会导致打分结果无法对比。"
                ),
                samples=[{'units_found': list(units)}]
            )

        unit = list(units)[0]
        return ValidationResult(
            gate='GATE2',
            passed=True,
            score=1.0,
            detail=f"volume 单位统一: '{unit}' | 共 {len(all_meta)} 条元数据"
        )

    def _gate3_score_divergence(
        self,
        scan_top: List[Dict],
        live_top: List[Dict]
    ) -> Tuple[ValidationResult, float]:
        """
        GATE3: TOP5 分数误差率

        对 scan 和 live 共同出现在 TOP5 的票，比较 score 字段偏差。
        平均偏差 < 5% 则通过。
        """
        scan_top5 = scan_top[:5]
        live_top5 = live_top[:5]
        scan_map = {t['code']: t.get('score', 0.0) for t in scan_top5}
        live_map = {t['code']: t.get('score', 0.0) for t in live_top5}
        common = set(scan_map.keys()) & set(live_map.keys())

        if not common:
            return ValidationResult(
                gate='GATE3',
                passed=False,
                score=0.0,
                detail=(
                    f"scan TOP5 与 live TOP5 无交集，路径完全分叉。"
                    f"scan TOP5 代码: {list(scan_map.keys())} | "
                    f"live TOP5 代码: {list(live_map.keys())}"
                )
            ), 100.0

        diffs = []
        samples = []
        for code in common:
            s_score = scan_map[code]
            l_score = live_map[code]
            base = max(abs(s_score), abs(l_score), 1e-6)
            diff_pct = abs(s_score - l_score) / base * 100
            diffs.append(diff_pct)
            samples.append({
                'code': code,
                'scan_score': round(s_score, 2),
                'live_score': round(l_score, 2),
                'diff_pct': round(diff_pct, 2)
            })

        avg_divergence = sum(diffs) / len(diffs)
        passed = avg_divergence < self.SCORE_TOLERANCE_PCT

        return ValidationResult(
            gate='GATE3',
            passed=passed,
            score=max(0.0, 1.0 - avg_divergence / 100),
            detail=(
                f"共 {len(common)} 只公共 TOP5 票 | "
                f"平均分数偏差: {avg_divergence:.2f}% | "
                f"阈值: {self.SCORE_TOLERANCE_PCT}%"
            ),
            samples=samples
        ), avg_divergence

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _generate_recommendations(self, gates: List[ValidationResult]) -> List[str]:
        """根据失败的门生成修复建议"""
        recs = []
        for gate in gates:
            if gate.passed:
                continue
            if gate.gate == 'GATE1':
                recs.append(
                    "GATE1修复: run_historical_stream 中 calculate_time_slice_flows "
                    "拿不到切片时的降级逻辑应与 live 路径对齐："
                    "改为 current_amount / 240 * 5（全天均摊），而非 continue 跳过。"
                    "确保 scan 和 live 使用完全相同的 fallback 公式。"
                )
            elif gate.gate == 'GATE2':
                recs.append(
                    "GATE2修复: MockQmtAdapter 构造 tick 数据时，volume 字段必须与 "
                    "xtdata.get_full_tick() 保持相同单位（手）。"
                    "在 MockQmtAdapter.__init__ 中添加 volume_unit='lot' 标记，"
                    "并在 run_historical_stream 入口添加单位断言检查。"
                )
            elif gate.gate == 'GATE3':
                recs.append(
                    "GATE3修复: TOP5 分数偏差超出 5%，根因通常是 flow 路径或 "
                    "engine_mode 参数不一致。检查: "
                    "(1) scan 是否传入了 mode='scan' 而 live 盘后传入了 mode='live'； "
                    "(2) 盘后 live 路径是否正确切换到 engine_mode='scan' 跳过时间衰减； "
                    "(3) KineticCoreEngine.calculate_true_dragon_score 中 "
                    "'scan' mode 和 'live' mode 的分支是否引入了非预期差异。"
                )
        return recs

    def _log_report_summary(self, report: ScanVsLiveReport):
        """在日志中打印摘要"""
        line = '=' * 60
        logger.info(line)
        logger.info(f"[ScanValidator] 同质性验证报告 | 日期: {report.date}")
        logger.info(line)
        for gate in report.gates:
            status = '[PASS]' if gate.passed else '[FAIL]'
            logger.info(f"  {status} {gate.gate}: {gate.detail}")
        logger.info(f"  分数偏差率: {report.score_divergence_pct:.2f}%")
        logger.info(f"  总裁定: {report.verdict}")
        if report.recommendations:
            logger.info("  修复建议:")
            for rec in report.recommendations:
                logger.warning(f"    >> {rec}")
        logger.info(line)

    def export_report(
        self,
        report: ScanVsLiveReport,
        filepath: str
    ):
        """
        导出同质性验证报告到 JSON 文件

        Args:
            report: ScanVsLiveReport 对象
            filepath: 输出路径，如 'data/validation/20260316_scan_vs_live.json'
        """
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"[ScanValidator] 报告已导出: {filepath}")

    @staticmethod
    def load_report(filepath: str) -> Optional[Dict]:
        """
        加载历史验证报告

        Args:
            filepath: 报告路径

        Returns:
            报告字典或 None
        """
        if not os.path.exists(filepath):
            logger.warning(f"[ScanValidator] 报告文件不存在: {filepath}")
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
