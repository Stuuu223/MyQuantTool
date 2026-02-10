#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动持续监控脚本 - 第二阶段框架

功能：
1. 支持两种模式：固定间隔扫描、事件驱动扫描
2. 在交易时间内持续运行（9:25-15:00）
3. 固定间隔模式：每N分钟执行一次全市场扫描
4. 事件驱动模式：检测到事件时触发扫描
5. 生成状态指纹，检测信号变化
6. 只有在状态变化时才保存快照
7. 输出实时日志到命令行

Author: iFlow CLI
Version: V2.0
"""

import time
import os
import sys
import json
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, List, Any, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.output_formatter import format_scan_result
from logic.market_status import MarketStatusChecker
from logic.equity_data_accessor import get_circ_mv
from logic.event_detector import EventManager, EventType
from logic.auction_event_detector import AuctionEventDetector
from logic.halfway_event_detector import HalfwayEventDetector
from logic.dip_buy_event_detector import DipBuyEventDetector
from logic.leader_event_detector import LeaderEventDetector
from logic.qmt_tick_monitor import get_tick_monitor
from logic.event_recorder import get_event_recorder
from logic.logger import get_logger
from logic.market_phase_checker import MarketPhaseChecker
from logic.sector_resonance import SectorResonanceCalculator

logger = get_logger(__name__)


class EventDrivenMonitor:
    """
    事件驱动持续监控器 - 第二阶段框架
    
    核心功能：
    - 事件驱动扫描（推荐）
    - 固定间隔扫描（备用）
    - 状态指纹对比
    - 智能快照保存
    """
    
    def __init__(
        self,
        scan_interval: int = 300,
        mode: str = "event_driven",
        monitor_stocks: List[str] = None
    ):
        """
        初始化事件驱动监控器
        
        Args:
            scan_interval: 扫描间隔（秒），默认300秒（5分钟）
            mode: 运行模式
                  - "event_driven": 事件驱动模式（推荐）
                  - "fixed_interval": 固定间隔模式
            monitor_stocks: 监控的股票列表（事件驱动模式下使用）
        """
        self.scan_interval = scan_interval
        self.mode = mode
        self.monitor_stocks = monitor_stocks or []
        
        # 初始化核心组件
        self.scanner = FullMarketScanner()
        self.market_checker = MarketStatusChecker()
        self.event_manager = EventManager()
        self.event_recorder = get_event_recorder()  # 初始化事件记录器

        # 初始化市场阶段检查器
        self.phase_checker = MarketPhaseChecker(self.market_checker)

        # 🔥 [修复] 加载紧急模式配置（使用绝对路径，避免依赖启动目录）
        import json
        from pathlib import Path
        # 定位项目根目录：从当前文件路径向上两级（tasks -> 项目根）
        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / 'config' / 'market_scan_config.json'

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.emergency_config = config.get('system', {}).get('emergency_mode', {
                    'enabled': False,
                    'allow_bypass_qmt_check': False,
                    'bypass_reason': ''
                })
            logger.info(f"✅ 加载紧急模式配置: {config_path}")
        except Exception as e:
            logger.warning(f"⚠️  加载紧急模式配置失败: {e}，使用默认配置（紧急模式关闭）")
            logger.warning(f"   配置路径: {config_path}")
            self.emergency_config = {
                'enabled': False,
                'allow_bypass_qmt_check': False,
                'bypass_reason': ''
            }

        # 状态管理
        self.last_signature = None
        self.scan_count = 0
        self.event_count = 0
        self.save_count = 0
        self.start_time = None
        
        # 🎯 CLI监控状态（供cli_monitor.py读取）
        self.monitor_state = {
            "sectors": {},   # 板块共振状态
            "signals": []    # 最终买入信号
        }
        self.last_state_export_time = None  # 上次状态导出时间
        self.state_export_interval = 5  # 每5秒导出一次状态
        
        # 真实候选池（带时间戳）
        self.hot_candidates = {}  # {code: {'timestamp': datetime, 'trigger_reason': str}}
        self.candidate_ttl_minutes = 10  # 候选池TTL：10分钟
        self.last_deep_scan_time = None  # 上次深扫时间
        
        # 初始化事件检测器
        self._init_event_detectors()
        
        # 初始化QMT Tick监控器（事件驱动模式）
        self.tick_monitor = None
        if self.mode == "event_driven":
            self._init_tick_monitor()
    
    def _init_event_detectors(self):
        """初始化所有事件检测器"""
        # 集合竞价战法事件检测器
        auction_detector = AuctionEventDetector()
        self.auction_detector = auction_detector  # 🔥 [Fix] 补全 AuctionDetector 初始化
        self.event_manager.register_detector(auction_detector)

        # 半路战法事件检测器
        halfway_detector = HalfwayEventDetector()
        self.halfway_detector = halfway_detector
        self.event_manager.register_detector(halfway_detector)

        # 低吸战法事件检测器
        dip_detector = DipBuyEventDetector()
        self.dip_detector = dip_detector
        self.event_manager.register_detector(dip_detector)

        # 龙头战法事件检测器
        leader_detector = LeaderEventDetector()
        self.leader_detector = leader_detector
        self.event_manager.register_detector(leader_detector)

        logger.info(f"✅ 事件检测器初始化完成: {len(self.event_manager.detectors)} 个")
    
    def _init_tick_monitor(self):
        """初始化QMT Tick监控器"""
        try:
            self.tick_monitor = get_tick_monitor()
            
            # 添加事件回调
            self.tick_monitor.add_event_callback(self._on_tick_update)
            
            logger.info("✅ QMT Tick监控器初始化成功")
        except Exception as e:
            logger.error(f"❌ QMT Tick监控器初始化失败: {e}")
            self.tick_monitor = None
    
    def _on_tick_update(self, stock_code: str, tick_data: Dict[str, Any]):
        """
        Tick数据更新回调
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        """
        try:
            # 构建上下文信息
            context = self._build_context(stock_code, tick_data)
            
            # 检测事件
            events = self.event_manager.detect_events(tick_data, context)
            
            if events:
                self.event_count += len(events)
                for event in events:
                    logger.info(f"🔔 检测到事件: {event.stock_code} - {event.description}")
                    
                    # 自动记录事件到数据库
                    try:
                        record_id = self.event_recorder.record_event(event, tick_data)
                        logger.info(f"💾 事件已记录到数据库 (ID: {record_id})")
                    except Exception as e:
                        logger.error(f"❌ 记录事件失败: {e}")
        
        except Exception as e:
            logger.error(f"❌ 处理Tick更新失败: {e}")
    
    def _build_context(self, stock_code: str, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建上下文信息
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        
        Returns:
            上下文字典
        """
        context = {
            'yesterday_close': tick_data.get('close', 0),
            'yesterday_volume': 0,  # 需要从其他地方获取
            'ma5': 0,  # 需要从K线数据获取
            'ma10': 0,
            'ma20': 0,
            'sector_data': {},  # 需要从板块数据获取
            'yesterday_data': {}  # 需要从历史数据获取
        }
        
        return context
    
    def is_trading_time(self) -> bool:
        """判断当前是否在交易时间内"""
        # 🚨 紧急补丁：强制基于本地系统时间判断交易阶段
        # 因为QMT时间戳异常（停留在午夜），绕过QMT的时间判断
        from datetime import time as dt_time
        
        current_time = datetime.now().time()
        
        # 竞价阶段：9:15-9:25
        if dt_time(9, 15) <= current_time <= dt_time(9, 25):
            logger.warning("🚨 紧急模式：强制进入竞价阶段（基于本地时间）")
            return True
        
        # 上午交易：9:30-11:30
        elif dt_time(9, 30) <= current_time <= dt_time(11, 30):
            logger.warning("🚨 紧急模式：强制进入上午交易（基于本地时间）")
            return True
        
        # 下午交易：13:00-15:00
        elif dt_time(13, 0) <= current_time <= dt_time(15, 0):
            logger.warning("🚨 紧急模式：强制进入下午交易（基于本地时间）")
            return True
        
        # 否则使用原逻辑
        return self.market_checker.is_trading_time()
    
    def save_snapshot(self, results: dict, mode: str):
        """
        保存快照（带状态指纹对比）
        
        Args:
            results: 扫描结果
            mode: 扫描模式
        """
        # 生成状态指纹
        current_signature = self.scanner.generate_state_signature(results)
        
        # 对比状态指纹
        if current_signature != self.last_signature:
            # 状态发生变化，保存快照
            os.makedirs('data/scan_results', exist_ok=True)
            
            # 使用时间戳命名，避免覆盖
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f"data/scan_results/{timestamp}_{mode}.json"
            
            output = {
                'scan_time': datetime.now().isoformat(),
                'mode': mode,
                'state_signature': current_signature,
                'state_changed': True,
                'summary': {
                    'opportunities': len(results['opportunities']),
                    'watchlist': len(results['watchlist']),
                    'blacklist': len(results['blacklist'])
                },
                'results': results
            }
            
            # 自定义 JSON 编码器处理 datetime.date 对象
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if hasattr(obj, 'strftime'):
                        return obj.strftime('%Y-%m-%d')
                    elif hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    return super().default(obj)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
            
            self.last_signature = current_signature
            self.save_count += 1
            
            logger.info(f"💾 [状态变化] 快照已保存: {filename}")
            logger.info(f"   状态指纹: {current_signature[:8]}...")
        else:
            logger.info(f"⏭️  [状态未变] 跳过保存，状态指纹: {current_signature[:8]}...")
    
    def _compress_trap_signals(self, trap_signals: list) -> str:
        """压缩诱多信号为短字符串"""
        if not trap_signals:
            return "-"

        # 信号映射表
        signal_map = {
            "单日暴量+隔日反手": "暴量",
            "长期流出+单日巨量": "长+巨",
            "游资突袭": "突袭",
            "连续涨停+巨量": "连涨",
            "尾盘拉升+巨量": "尾拉",
            "开盘暴跌+巨量": "开跌",
        }

        # 统计信号出现次数
        signal_count = {}
        for signal in trap_signals:
            short = signal_map.get(signal, signal[:4])  # 最多取前4个字符
            signal_count[short] = signal_count.get(short, 0) + 1

        # 生成压缩字符串
        compressed_parts = []
        for short, count in signal_count.items():
            if count > 1:
                compressed_parts.append(f"{short}*{count}")
            else:
                compressed_parts.append(short)

        return ",".join(compressed_parts)[:8]  # 限制最多8个字符

    def _calculate_decision_tag(self, ratio: float, risk_score: float, trap_signals: list) -> str:
        """
        资金推动力决策树:
        第1关: ratio < 0.5% → PASS❌（止损优先，资金推动力太弱）
        第2关: ratio > 5% → TRAP❌（暴拉出货风险）
        第3关: 诱多 + 高风险 → BLOCK❌
        第4关: 1-3% + 低风险 + 无诱多 → FOCUS✅
        """
        # 第1关: 资金推动力太弱，直接 PASS（止损优先）
        if ratio is not None and ratio < 0.5:
            return "PASS❌"

        # 第2关: 暴拉出货风险
        if ratio is not None and ratio > 5:
            return "TRAP❌"

        # 第3关: 诱多 + 高风险
        if trap_signals and risk_score >= 0.4:
            return "BLOCK❌"

        # 第4关: 标准 FOCUS
        if (ratio is not None and
            1 <= ratio <= 3 and
            risk_score <= 0.2 and
            not trap_signals):
            return "FOCUS✅"

        # 兜底
        return "BLOCK❌"

    def _print_low_risk_opportunities(self, opportunities: list):
        """打印低风险机会池表格（风险≤0.2）"""
        # 过滤低风险股票
        low_risk = [item for item in opportunities if item.get('risk_score', 0) <= 0.2]

        if not low_risk:
            return

        print(f"\n【低风险机会池】（风险≤0.2，{len(low_risk)} 只）")
        print("=" * 125)
        print(f"{'代码':<8} {'名称':<10} {'价格':>6} {'涨跌幅':>7} {'成交额(亿)':>9} {'流通市值(亿)':>11} {'主力净入(亿)':>12} {'占比(%)':>6} {'资金':>6} {'风险':>5} {'诱多信号':<8} {'决策':<8}")
        print("-" * 125)

        for item in low_risk:
            # 获取基础字段
            code = item.get('code', '')
            name = item.get('name', '')
            last_price = item.get('last_price', 0)
            pct_chg = item.get('pct_chg', 0)

            # 计算流通市值（优先使用 circulating_market_cap，否则用 circulating_shares * last_price）
            circulating_market_cap = item.get('circulating_market_cap', 0)
            if circulating_market_cap == 0:
                circulating_shares = item.get('circulating_shares', 0)
                circulating_market_cap = circulating_shares * last_price

            # 获取成交额
            amount_yuan = item.get('amount', 0)

            # 获取主力净流入
            flow_data = item.get('flow_data', {})
            latest = flow_data.get('latest', {})
            main_net_yuan = latest.get('main_net_inflow', 0)

            # 单位转换：元→亿
            amount_yi = amount_yuan / 1e8
            float_mv_yi = circulating_market_cap / 1e8
            main_net_yi = main_net_yuan / 1e8

            # 计算占比（主力净入占流通市值比）
            # 优先使用 Tushare 数据，回退到现有逻辑
            trade_date = item.get("trade_date")
            circ_mv_tushare = get_circ_mv(code, trade_date)

            if circ_mv_tushare > 0:
                ratio = main_net_yuan / circ_mv_tushare * 100
                # 更新流通市值显示为 Tushare 数据
                float_mv_yi = circ_mv_tushare / 1e8
            elif circulating_market_cap > 0:
                ratio = main_net_yuan / circulating_market_cap * 100
            else:
                ratio = None

            # 风险标签
            risk_score = item.get('risk_score', 0)
            risk_str = f"L{risk_score:.1f}"

            # 资金类型
            capital_type = item.get('capital_type', 'UNKNOWN')
            capital_abbr = {
                'HOT_MONEY': 'HOT',
                'INSTITUTIONAL': 'INST',
                'SPECULATION': 'SPEC',
                'UNKNOWN': 'UNKN'
            }.get(capital_type, capital_type[:4])

            # 诱多信号压缩
            trap_signals = item.get('trap_signals', [])
            trap_short = self._compress_trap_signals(trap_signals)

            # 计算决策标签
            decision_tag = self._calculate_decision_tag(ratio, risk_score, trap_signals)

            # DEBUG: 针对 601869.SH 的关键数据输出
            if code == "601869.SH":
                print(f"\n[DEBUG 601869.SH]")
                print(f"  trade_date={trade_date}")
                print(f"  main_net_inflow={main_net_yuan} 元 ({main_net_yi:.4f} 亿)")
                print(f"  circ_mv_tushare={circ_mv_tushare} 元 ({float_mv_yi:.2f} 亿)")
                print(f"  ratio={ratio} %")
                print(f"  decision_tag={decision_tag}")
                print(f"  risk_score={risk_score}")
                print(f"  trap_signals={trap_signals}")
                print()

            # 打印行
            print(f"{code:<8} {name:<10} {last_price:>6.2f} {pct_chg:>7.2f} {amount_yi:>9.2f} {float_mv_yi:>11.2f} {main_net_yi:>12.2f} {f'{ratio:>6.2f}' if ratio is not None else '  --  ':>6} {capital_abbr:>6} {risk_str:>5} {trap_short:<8} {decision_tag:<8}")

        print("=" * 125)

    def _check_defensive_scenario(self, item: dict) -> Tuple[bool, str]:
        """
        🛡️ 防守斧：场景检查 - 监控层拦截

        严格禁止 TAIL_RALLY/TRAP 场景开仓

        Args:
            item: 股票数据字典（来自全市场扫描结果）

        Returns:
            (is_forbidden, reason)
            is_forbidden: 是否禁止开仓
            reason: 禁止原因
        """
        # 导入硬编码禁止场景列表
        from logic.risk_control import FORBIDDEN_SCENARIOS

        code = item.get('code', '')
        name = item.get('name', 'N/A')
        scenario_type = item.get('scenario_type', '')
        is_tail_rally = item.get('is_tail_rally', False)
        is_potential_trap = item.get('is_potential_trap', False)

        # 硬编码禁止规则
        if scenario_type in FORBIDDEN_SCENARIOS:
            reason = f"🛡️ [防守斧] 禁止场景: {scenario_type}"
            logger.warning(f"🛡️ [防守斧拦截-监控层] {code} ({name})")
            logger.warning(f"   场景类型: {scenario_type}")
            logger.warning(f"   原因: {', '.join(item.get('scenario_reasons', [])[:2])}")
            logger.warning(f"   拦截位置: 监控层 (run_event_driven_monitor.py)")
            return True, reason

        # 兼容旧版：通过布尔值检查
        if is_tail_rally:
            reason = "🛡️ [防守斧] 补涨尾声场景，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截-监控层] {code} ({name})")
            logger.warning(f"   is_tail_rally: {is_tail_rally}")
            logger.warning(f"   拦截位置: 监控层 (run_event_driven_monitor.py)")
            return True, reason

        if is_potential_trap:
            reason = "🛡️ [防守斧] 拉高出货陷阱，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截-监控层] {code} ({name})")
            logger.warning(f"   is_potential_trap: {is_potential_trap}")
            logger.warning(f"   拦截位置: 监控层 (run_event_driven_monitor.py)")
            return True, reason

        # 通过检查
        return False, ""

    def _check_sector_resonance(self, item: dict, all_results: dict) -> Tuple[bool, str]:
        """
        🎯 时机斧：板块共振检查 - 监控层触发

        只在板块满足共振条件时才允许入场：
        - Leaders ≥ 3：板块内涨停股数量 ≥ 3
        - Breadth ≥ 35%：板块内上涨比例 ≥ 35%

        Args:
            item: 股票数据字典（来自全市场扫描结果）
            all_results: 完整的扫描结果（用于计算板块共振）

        Returns:
            (is_blocked, reason)
            is_blocked: 是否阻止入场
            reason: 阻止原因或允许原因
        """
        code = item.get('code', '')
        name = item.get('name', 'N/A')
        sector_name = item.get('sector_name', '')
        sector_code = item.get('sector_code', '')

        # 如果没有板块信息或板块信息未知，跳过检查（不拦截）
        if not sector_name or not sector_code or sector_name == '未知板块':
            return False, "⏸️ 无板块信息，跳过共振检查"

        # 提取板块内所有股票数据
        sector_stocks = []
        for stock in all_results.get('opportunities', []) + all_results.get('watchlist', []):
            if stock.get('sector_name') == sector_name:
                sector_stocks.append({
                    'pct_chg': stock.get('pct_chg', 0),
                    'is_limit_up': stock.get('is_limit_up', False),
                })

        # 如果板块内股票太少，跳过检查
        if len(sector_stocks) < 3:
            return False, f"⏸️ 板块内股票不足（{len(sector_stocks)}只），跳过共振检查"

        # 计算板块共振
        calculator = SectorResonanceCalculator()
        resonance_result = calculator.calculate(sector_stocks, sector_name, sector_code)
        
        # 🎯 更新CLI监控状态：板块共振状态
        self.monitor_state["sectors"][sector_name] = {
            "leaders": resonance_result.leaders,
            "breadth": resonance_result.breadth,
            "is_resonant": resonance_result.is_resonant,
            "reason": resonance_result.reason
        }

        # 检查是否满足共振条件
        if not resonance_result.is_resonant:
            reason = f"⏸️ [时机斧] 板块未共振：{resonance_result.reason}"
            logger.info(f"⏸️ [时机斧拦截-监控层] {code} ({name})")
            logger.info(f"   板块: {sector_name}")
            logger.info(f"   Leaders: {resonance_result.leaders}（需≥3）")
            logger.info(f"   Breadth: {resonance_result.breadth:.1f}%（需≥35%）")
            logger.info(f"   拦截位置: 监控层 (run_event_driven_monitor.py)")
            return True, reason

        # 通过检查
        reason = f"✅ [时机斧] 板块共振满足：{resonance_result.reason}"
        logger.info(f"✅ [时机斧通过-监控层] {code} ({name})")
        logger.info(f"   板块: {sector_name}")
        logger.info(f"   Leaders: {resonance_result.leaders}✅")
        logger.info(f"   Breadth: {resonance_result.breadth:.1f}%✅")
        return False, reason

    def _export_monitor_state(self):
        """
        🎯 导出监控状态到文件（供CLI监控终端读取）
        
        将当前的三把斧状态导出到data/monitor_state.json
        """
        try:
            state_file = Path("data/monitor_state.json")
            
            # 确保data目录存在
            state_file.parent.mkdir(exist_ok=True)
            
            # 导出状态
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitor_state, f, ensure_ascii=False, indent=2)
            
            self.last_state_export_time = datetime.now()
            
        except Exception as e:
            logger.warning(f"⚠️ 导出监控状态失败: {e}")

    def print_summary(self, results: dict):
        """打印扫描结果摘要（带防守斧拦截）"""
        print("\n" + "=" * 80)
        print(f"📊 扫描完成 #{self.scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)

        # 🛡️ 防守斧：过滤机会池中的禁止场景
        opportunities_safe = []
        opportunities_blocked = []
        for item in results['opportunities']:
            is_forbidden, reason = self._check_defensive_scenario(item)
            if is_forbidden:
                opportunities_blocked.append((item, reason))
            else:
                opportunities_safe.append(item)

        # 打印拦截统计
        if opportunities_blocked:
            print(f"🛡️ [防守斧] 本次拦截 {len(opportunities_blocked)} 只禁止场景股票:")
            for item, reason in opportunities_blocked:
                print(f"   ❌ {item['code']} ({item.get('name', 'N/A')}) - {reason}")
            print()

        # 🎯 时机斧：板块共振检查
        opportunities_final = []
        opportunities_timing_blocked = []
        for item in opportunities_safe:
            is_blocked, reason = self._check_sector_resonance(item, results)
            if is_blocked:
                opportunities_timing_blocked.append((item, reason))
            else:
                opportunities_final.append(item)

        # 打印时机斧拦截统计
        if opportunities_timing_blocked:
            print(f"⏸️ [时机斧] 本次拦截 {len(opportunities_timing_blocked)} 只未共振股票:")
            for item, reason in opportunities_timing_blocked:
                print(f"   ⏸️ {item['code']} ({item.get('name', 'N/A')}) - {reason}")
            print()

        # 显示过滤后的机会池数量
        print(f"✅ 机会池（最终）: {len(opportunities_final)} 只")
        print(f"🛡️ 机会池（防守斧拦截）: {len(opportunities_blocked)} 只")
        print(f"⏸️ 机会池（时机斧拦截）: {len(opportunities_timing_blocked)} 只")
        print(f"⚠️  观察池: {len(results['watchlist'])} 只")
        print(f"❌ 黑名单: {len(results['blacklist'])} 只")
        print(f"📈 系统置信度: {results['confidence']*100:.1f}%")
        print(f"💰 今日建议最大总仓位: {results['position_limit']*100:.1f}%")
        print(f"🎯 累计保存快照: {self.save_count} 次")
        print(f"🔔 累计检测事件: {self.event_count} 次")

        # 显示低风险机会池表格（只显示最终安全股票）
        if opportunities_final:
            self._print_low_risk_opportunities(opportunities_final)

        # 显示机会池全部股票（简化版，只显示最终安全股票）
        if opportunities_final:
            print(f"\n🔥 机会池（最终） ({len(opportunities_final)} 只):")
            for item in opportunities_final:
                risk_score = item.get('risk_score', 0)
                capital_type = item.get('capital_type', 'UNKNOWN')
                trap_signals = item.get('trap_signals', [])
                signal_str = f" 诱多信号: {', '.join(trap_signals)}" if trap_signals else ""
                print(f"   {item['code']} - 风险: {risk_score:.2f} - 类型: {capital_type}{signal_str}")

        # 🎯 更新CLI监控状态：最终买入信号
        self.monitor_state["signals"] = []
        for item in opportunities_final:
            flow_records = item.get('flow_data', {}).get('records', [])
            main_net_inflow = flow_records[0].get('main_net_inflow', 0) if flow_records else 0
            
            self.monitor_state["signals"].append({
                "time": datetime.now().strftime('%H:%M:%S'),
                "code": item.get('code', ''),
                "name": item.get('name', ''),
                "price": item.get('last_price', 0),
                "flow": main_net_inflow / 10000  # 转换为万元
            })

        # 显示观察池全部股票
        if results['watchlist']:
            print(f"\n⚠️  观察池 ({len(results['watchlist'])} 只):")
            for item in results['watchlist']:
                risk_score = item.get('risk_score', 0)
                capital_type = item.get('capital_type', 'UNKNOWN')
                trap_signals = item.get('trap_signals', [])
                signal_str = f" 诱多信号: {', '.join(trap_signals)}" if trap_signals else ""
                print(f"   {item['code']} - 风险: {risk_score:.2f} - 类型: {capital_type}{signal_str}")

        print("=" * 80 + "\n")
    
    def run_fixed_interval(self):
        """运行固定间隔模式"""
        logger.info("🔄 切换到固定间隔模式")
        
        while True:
            # 检查是否在交易时间
            if not self.is_trading_time():
                logger.info(f"⏰ 当前不在交易时间，等待中...")
                time.sleep(60)
                continue
            
            # 执行扫描
            logger.info(f"\n🔍 开始扫描 #{self.scan_count + 1}")
            logger.info("-" * 80)
            
            try:
                results = self.scanner.scan_with_risk_management(mode='intraday')
                self.scan_count += 1
                
                # 打印摘要
                self.print_summary(results)
                
                # 保存快照（带状态指纹对比）
                self.save_snapshot(results, mode='intraday')
                
            except Exception as e:
                logger.error(f"❌ 扫描失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 等待下一次扫描
            logger.info(f"⏱️  等待 {self.scan_interval} 秒后进行下一次扫描...")
            time.sleep(self.scan_interval)
    
    def run_event_driven(self):
        """运行事件驱动模式"""
        logger.info("🎯 切换到事件驱动模式")
        
        # 订阅监控股票
        if self.tick_monitor and self.monitor_stocks:
            try:
                self.tick_monitor.subscribe(self.monitor_stocks)
                self.tick_monitor.start()
            except Exception as e:
                logger.error(f"❌ 启动Tick监控失败: {e}")
                # 回退到固定间隔模式
                logger.info("🔄 回退到固定间隔模式")
                self.run_fixed_interval()
                return
        
        while True:
            # 检查是否在交易时间
            if not self.is_trading_time():
                logger.info(f"⏰ 当前不在交易时间，等待中...")
                time.sleep(60)
                continue
            
            # 检查是否有事件触发
            if self.event_manager.should_trigger_scan():
                logger.info(f"\n🔥 事件触发扫描！")
                logger.info("-" * 80)
                
                try:
                    results = self.scanner.scan_with_risk_management(mode='intraday')
                    self.scan_count += 1
                    
                    # 打印摘要
                    self.print_summary(results)
                    
                    # 🎯 导出监控状态（供CLI监控终端读取）
                    self._export_monitor_state()
                    
                    # 保存快照（带状态指纹对比）
                    self.save_snapshot(results, mode='intraday')
                    
                    # 标记扫描完成
                    self.event_manager.mark_scan_complete()
                    
                except Exception as e:
                    logger.error(f"❌ 扫描失败: {e}")
                    import traceback
                    traceback.print_exc()
                    self.event_manager.mark_scan_complete()
            else:
                # 显示心跳日志
                logger.info(f"💓 监控中... (累计事件: {self.event_count})")
            
            # 等待下一次检查
            time.sleep(10)  # 每10秒检查一次
    
    def run(self):
        """运行持续监控 - 统一入口，内部自动切换策略"""
        self.start_time = datetime.now()

        # ===== QMT 状态检查（启动时检查一次）=====
        from logic.qmt_health_check import check_qmt_health
        qmt_status = check_qmt_health()

        logger.info("=" * 80)
        logger.info("🚀 事件驱动持续监控启动 - 第二阶段框架（重构版）")
        logger.info("=" * 80)
        logger.info(f"📅 启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🎯 运行模式: 自动策略切换")
        logger.info(f"🎯 支持策略: auction（竞价） / event_driven（盘中） / idle（空闲）")
        logger.info(f"🔌 QMT 状态: {qmt_status['status']}")

        if qmt_status['status'] == 'ERROR':
            logger.warning("⚠️  QMT 状态异常，可能影响监控效果")
        elif qmt_status['status'] == 'WARNING':
            logger.warning("⚠️  QMT 状态警告，请注意")
        logger.info("=" * 80)
        
        print("\n🎯 事件驱动监控已启动，按 Ctrl+C 停止")
        print("=" * 80 + "\n")
        
        try:
            # 调度循环
            while True:
                # 🔥 [修复] 仅在配置开启时进入紧急模式
                if self.emergency_config.get('enabled', False):
                    # 🚨 [配置启用] 紧急模式：强制基于本地系统时间确定当前策略
                    # 因为QMT时间戳异常（停留在午夜），绕过QMT的策略判断
                    from datetime import time as dt_time

                    current_time = datetime.now().time()

                    # 竞价阶段：9:15-9:25
                    if dt_time(9, 15) <= current_time <= dt_time(9, 25):
                        strategy = 'auction'
                        logger.warning(f"🚨 [配置启用] 紧急模式：强制进入竞价策略（基于本地时间 {current_time.strftime('%H:%M:%S')}）")

                    # 上午交易：9:30-11:30
                    elif dt_time(9, 30) <= current_time <= dt_time(11, 30):
                        strategy = 'event_driven'
                        logger.warning(f"🚨 [配置启用] 紧急模式：强制进入事件驱动策略（基于本地时间 {current_time.strftime('%H:%M:%S')}）")

                    # 下午交易：13:00-15:00
                    elif dt_time(13, 0) <= current_time <= dt_time(15, 0):
                        strategy = 'event_driven'
                        logger.warning(f"🚨 [配置启用] 紧急模式：强制进入事件驱动策略（基于本地时间 {current_time.strftime('%H:%M:%S')}）")

                    # 否则使用原逻辑
                    else:
                        strategy = self.phase_checker.determine_strategy()
                else:
                    # 🔥 [修复] 正常模式：使用QMT时间判断
                    strategy = self.phase_checker.determine_strategy()
                
                # 2. 打印策略
                logger.info(f"🎯 当前策略: {strategy}")
                
                # 3. 按策略分发
                if strategy == 'auction':
                    self._run_auction_strategy()
                elif strategy == 'event_driven':
                    self._run_event_driven_strategy()
                elif strategy == 'idle':
                    self._run_idle_strategy()
                else:
                    logger.warning(f"⚠️ 未知策略: {strategy}")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 80)
            logger.info("🛑 持续监控已停止")
            logger.info("=" * 80)
            logger.info(f"📊 运行统计:")
            logger.info(f"   总扫描次数: {self.scan_count}")
            logger.info(f"   总检测事件: {self.event_count}")
            logger.info(f"   快照保存次数: {self.save_count}")
            logger.info(f"   运行时长: {datetime.now() - self.start_time}")
            logger.info("=" * 80)
    
    def _run_auction_strategy(self):
        """竞价策略 - 第一版（最小功能）"""
        logger.info("📢 [AUCTION] 进入竞价模式")
        
        # 🚨 Hotfix: 屏蔽竞价检测（auction_detector未实现）
        logger.info("   🚨 Hotfix: 竞价检测器未实现，跳过")
        
        # 1. 模拟深扫（跳过，第一版只验证阶段切换）
        logger.info("   模拟深扫: 跳过（第一版只验证阶段切换）")
        
        # 2. 等待下次循环（验证循环能跑通）
        logger.info("   等待 30 秒后重新检测...")
        time.sleep(30)
    
    def _run_event_driven_strategy(self):
        """事件驱动策略 - 第二版（真实候选池 + 深扫）"""
        logger.info("📡 [EVENT_DRIVEN] 进入事件驱动模式")

        # ===== QMT 状态检查（盘中模式强制要求实时）=====
        # 🔥 [修复] 仅在配置开启时允许绕过QMT检查
        if self.emergency_config.get('allow_bypass_qmt_check', False):
            bypass_reason = self.emergency_config.get('bypass_reason', 'No reason')
            logger.warning(f"🔥 [配置启用] 紧急绕过 QMT 检查: {bypass_reason}")
        else:
            # 🔥 [修复] 恢复正常的检查逻辑
            from logic.qmt_health_check import require_realtime_mode
            try:
                require_realtime_mode()
            except RuntimeError as e:
                logger.error(f"❌ QMT 状态不满足要求且紧急绕过未开启: {e}")
                logger.error("❌ 无法进行盘中监控，等待下一次循环...")
                time.sleep(60)
                return
        # ===== QMT 状态检查结束 =====
        
        # 1. 清理过期候选
        self._cleanup_expired_candidates()
        
        # 2. 从全市场扫描更新候选池
        self._update_candidates_from_market_scan()
        
        # 3. 打印候选池状态
        logger.info(f"   候选池: {len(self.hot_candidates)} 只")
        if self.hot_candidates:
            logger.info(f"   候选池: {list(self.hot_candidates.keys())[:3]}...")
        
        # 4. 如果有候选，执行深扫
        if self.hot_candidates:
            self._deep_scan_candidates()
        else:
            logger.info("   候选池为空，跳过深扫")
        
        # 5. 等待下次循环
        logger.info("   等待 30 秒后重新检测...")
        time.sleep(30)
    
    def _update_candidates_from_market_scan(self):
        """从全市场扫描更新候选池"""
        try:
            # 只运行Level1初筛（轻量级）
            level1_passed = self.scanner.run_level1_screening()
            
            if level1_passed:
                new_candidates_count = 0
                for stock_code in level1_passed:
                    # 添加到候选池
                    if self._add_candidate(stock_code, 'level1_screening'):
                        new_candidates_count += 1
                
                if new_candidates_count > 0:
                    logger.info(f"   全市场初筛: 新增 {new_candidates_count} 只候选")
        except Exception as e:
            logger.warning(f"   全市场初筛失败: {e}")
    
    def _add_candidate(self, code: str, trigger_reason: str = 'unknown') -> bool:
        """
        添加股票到候选池
        
        Args:
            code: 股票代码
            trigger_reason: 触发原因
        
        Returns:
            bool: 是否成功添加（如果已存在且未过期，返回False）
        """
        if code in self.hot_candidates:
            # 已存在，更新时间戳
            self.hot_candidates[code]['timestamp'] = datetime.now()
            self.hot_candidates[code]['trigger_reason'] = trigger_reason
            return False
        
        # 检查候选池大小限制
        if len(self.hot_candidates) >= 100:
            # 静默处理，不重复输出警告
            return False
        
        # 添加新候选
        self.hot_candidates[code] = {
            'timestamp': datetime.now(),
            'trigger_reason': trigger_reason
        }
        return True
    
    def _cleanup_expired_candidates(self):
        """清理过期的候选（TTL）"""
        if not self.hot_candidates:
            return
        
        expired_codes = []
        now = datetime.now()
        
        for code, data in self.hot_candidates.items():
            age_minutes = (now - data['timestamp']).total_seconds() / 60
            if age_minutes > self.candidate_ttl_minutes:
                expired_codes.append(code)
        
        for code in expired_codes:
            del self.hot_candidates[code]
        
        if expired_codes:
            logger.info(f"   清理过期候选: {len(expired_codes)} 只")
    
    def _deep_scan_candidates(self):
        """对候选池执行深度扫描"""
        try:
            # 提取候选股票代码列表
            candidate_codes = list(self.hot_candidates.keys())
            
            logger.info(f"   开始深度扫描: {len(candidate_codes)} 只候选")
            
            # 执行深度扫描（只扫描候选集）
            results = self.scanner.scan_with_risk_management(
                stock_list=candidate_codes,
                mode='intraday'
            )
            
            # 打印结果摘要
            self.print_summary(results)
            
            # 更新扫描时间
            self.last_deep_scan_time = datetime.now()
            
        except Exception as e:
            logger.error(f"   深度扫描失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _run_idle_strategy(self):
        """空闲策略 - 非交易时间"""
        logger.info("⏸️  [IDLE] 当前不在交易时间")
        
        # 检查是否刚刚收盘（15:00-15:10之间）
        now = datetime.now()
        if now.hour == 15 and now.minute < 10:
            logger.info("=" * 80)
            logger.info("📊 收盘后复盘提示")
            logger.info("=" * 80)
            logger.info("")
            logger.info("💡 建议操作：")
            logger.info("   1. 记录今日成交：python tasks/record_trade.py")
            logger.info("   2. 运行复盘脚本：python tasks/review_daily.py --date today")
            logger.info("   3. 重点分析B类样本（系统FOCUS + 没上）")
            logger.info("")
            logger.info("=" * 80)
        
        logger.info("   等待 60 秒后重新检测...")
        time.sleep(60)


if __name__ == "__main__":
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='事件驱动持续监控')
    parser.add_argument(
        '--mode',
        type=str,
        default='event_driven',
        choices=['event_driven', 'fixed_interval'],
        help='运行模式'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='扫描间隔（秒），仅在固定间隔模式下生效'
    )
    parser.add_argument(
        '--stocks',
        type=str,
        nargs='+',
        default=[],
        help='监控的股票列表，仅在事件驱动模式下生效'
    )
    # 新增：复盘模式参数
    parser.add_argument(
        '--replay',
        action='store_true',
        help='启用缓存回放模式'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='复盘日期（格式：YYYY-MM-DD），例如：2026-02-06'
    )
    parser.add_argument(
        '--timepoint',
        type=str,
        help='复盘时间点（格式：HHMMSS），例如：093027'
    )
    parser.add_argument(
        '--list-snapshots',
        action='store_true',
        help='列出指定日期的所有可用快照'
    )

    args = parser.parse_args()

    # ===== 复盘模式逻辑 =====
    if args.replay:
        if not args.date:
            print("❌ 错误：--replay 模式需要指定 --date 参数")
            print("示例：python tasks/run_event_driven_monitor.py --replay --date 2026-02-06")
            sys.exit(1)

        from logic.cache_replay_provider import CacheReplayProvider

        # 创建缓存回放提供器
        provider = CacheReplayProvider(args.date)

        # 验证复盘是否可行
        possible, message = provider.validate_replay_possible()
        print(message)
        if not possible:
            sys.exit(1)

        # 列出快照
        if args.list_snapshots:
            print("\n📋 可用时间点：")
            for tp in provider.list_available_timepoints():
                snapshot = provider.get_snapshot(tp)
                if snapshot:
                    summary = snapshot.get('summary', {})
                    print(f"   {tp}: 机会{summary.get('opportunities', 0)} | 观察{summary.get('watchlist', 0)} | 黑名单{summary.get('blacklist', 0)}")
            sys.exit(0)

        # 回放指定时间点
        if not args.timepoint:
            print("❌ 错误：需要指定 --timepoint 参数")
            print(f"可用时间点：{provider.list_available_timepoints()}")
            print("示例：python tasks/run_event_driven_monitor.py --replay --date 2026-02-06 --timepoint 093027")
            sys.exit(1)

        # 读取快照
        snapshot = provider.get_snapshot(args.timepoint)
        if not snapshot:
            print(f"❌ 无法读取时间点 {args.timepoint} 的快照")
            sys.exit(1)

        # 打印回放报告
        print("\n" + "=" * 80)
        print(f"📜 复盘报告：{snapshot['scan_time']} ({snapshot['mode']})")
        print("=" * 80)

        # 打印风控结论
        results = snapshot['results']
        print(f"\n📊 风控结论:")
        print(f"   系统置信度: {results['confidence']*100:.1f}%")
        print(f"   建议最大仓位: {results['position_limit']*100:.1f}%")
        if results.get('risk_warnings'):
            print(f"   风险提示:")
            for warning in results['risk_warnings']:
                print(f"     {warning}")

        # 打印机会池表格（复用现有的打印逻辑）
        opportunities = results.get('opportunities', [])
        watchlist = results.get('watchlist', [])
        blacklist = results.get('blacklist', [])

        # 🔥 修复：使用统一格式化输出，避免硬编码
        scan_time = results.get('scan_time', 0.0)
        print(format_scan_result(results, scan_time))

        # 打印机会池表格（全部）
        if opportunities:
            print(f"\n【机会池】（{len(opportunities)} 只）")
            print("=" * 125)
            print(f"{'代码':<8} {'名称':<10} {'价格':>6} {'涨跌幅':>7} {'成交额(亿)':>9} {'流通市值(亿)':>11} {'主力净入(亿)':>12} {'占比(%)':>6} {'资金':>6} {'风险':>5} {'诱多信号':<8} {'决策':<8}")
            print("-" * 125)

            for item in opportunities:
                code = item.get('code', '')
                name = item.get('name', '')
                last_price = item.get('last_price', 0)
                pct_chg = item.get('pct_chg', 0)

                # 计算流通市值
                circulating_market_cap = item.get('circulating_market_cap', 0)
                if circulating_market_cap == 0:
                    circulating_shares = item.get('circulating_shares', 0)
                    circulating_market_cap = circulating_shares * last_price

                # 获取成交额
                amount_yuan = item.get('amount', 0)

                # 获取主力净流入
                flow_data = item.get('flow_data', {})
                latest = flow_data.get('latest', {})
                main_net_yuan = latest.get('main_net_inflow', 0)

                # 单位转换
                amount_yi = amount_yuan / 1e8
                float_mv_yi = circulating_market_cap / 1e8
                main_net_yi = main_net_yuan / 1e8

                # 计算占比（使用新的 get_circ_mv）
                trade_date = item.get("trade_date")
                circ_mv_tushare = get_circ_mv(code, trade_date)

                if circ_mv_tushare > 0:
                    ratio = main_net_yuan / circ_mv_tushare * 100
                    float_mv_yi = circ_mv_tushare / 1e8
                elif circulating_market_cap > 0:
                    ratio = main_net_yuan / circulating_market_cap * 100
                else:
                    ratio = None

                # 风险标签
                risk_score = item.get('risk_score', 0)
                risk_str = f"L{risk_score:.1f}"

                # 资金类型
                capital_type = item.get('capital_type', 'UNKNOWN')
                capital_abbr = {
                    'HOT_MONEY': 'HOT',
                    'INSTITUTIONAL': 'INST',
                    'SPECULATION': 'SPEC',
                    'UNKNOWN': 'UNKN'
                }.get(capital_type, capital_type[:4])

                # 诱多信号压缩
                trap_signals = item.get('trap_signals', [])
                signal_map = {
                    "单日暴量+隔日反手": "暴量",
                    "长期流出+单日巨量": "长+巨",
                    "游资突袭": "突袭",
                    "连续涨停+巨量": "连涨",
                    "尾盘拉升+巨量": "尾拉",
                    "开盘暴跌+巨量": "开跌",
                }
                signal_count = {}
                for signal in trap_signals:
                    short = signal_map.get(signal, signal[:4])
                    signal_count[short] = signal_count.get(short, 0) + 1
                compressed_parts = []
                for short, count in signal_count.items():
                    if count > 1:
                        compressed_parts.append(f"{short}*{count}")
                    else:
                        compressed_parts.append(short)
                trap_short = ",".join(compressed_parts)[:8] if trap_signals else "-"

                # 决策标签（使用新的决策树逻辑）
                if ratio is not None and ratio < 0.5:
                    decision_tag = "PASS❌"
                elif ratio is not None and ratio > 5:
                    decision_tag = "TRAP❌"
                elif trap_signals and risk_score >= 0.4:
                    decision_tag = "BLOCK❌"
                elif (ratio is not None and 1 <= ratio <= 3 and risk_score <= 0.2 and not trap_signals):
                    decision_tag = "FOCUS✅"
                else:
                    decision_tag = "BLOCK❌"

                # DEBUG: 针对 601869.SH 的关键数据输出
                if code == "601869.SH":
                    print(f"\n[DEBUG 601869.SH]")
                    print(f"  trade_date={trade_date}")
                    print(f"  main_net_inflow={main_net_yuan} 元 ({main_net_yi:.4f} 亿)")
                    print(f"  circ_mv_tushare={circ_mv_tushare} 元 ({float_mv_yi:.2f} 亿)")
                    print(f"  ratio={ratio} %")
                    print(f"  decision_tag={decision_tag}")
                    print(f"  risk_score={risk_score}")
                    print(f"  trap_signals={trap_signals}")
                    print()

                # 打印行
                print(f"{code:<8} {name:<10} {last_price:>6.2f} {pct_chg:>7.2f} {amount_yi:>9.2f} {float_mv_yi:>11.2f} {main_net_yi:>12.2f} {f'{ratio:>6.2f}' if ratio is not None else '  --  ':>6} {capital_abbr:>6} {risk_str:>5} {trap_short:<8} {decision_tag:<8}")

            print("=" * 125)

        print("=" * 80 + "\n")
        sys.exit(0)

    # ===== 实时监控模式逻辑 =====
    # 创建监控器
    monitor = EventDrivenMonitor(
        scan_interval=args.interval,
        mode=args.mode,
        monitor_stocks=args.stocks
    )

    # 运行监控
    monitor.run()