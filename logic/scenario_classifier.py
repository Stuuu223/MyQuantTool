"""
场景分类器 - 识别主线起爆/拉高出货/补涨尾声

核心功能：
1. 识别"主线起爆"候选
2. 识别"拉高出货"陷阱
3. 识别"补涨尾声"风险

使用方式：
    from logic.scenario_classifier import ScenarioClassifier
    classifier = ScenarioClassifier()
    result = classifier.classify(stock_data)
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ScenarioType(Enum):
    """场景类型"""
    MAINLINE_RALLY = "MAINLINE_RALLY"  # 主线起爆
    TRAP_PUMP_DUMP = "TRAP_PUMP_DUMP"  # 拉高出货
    TAIL_RALLY = "TAIL_RALLY"          # 补涨尾声
    UNCERTAIN = "UNCERTAIN"            # 不确定


@dataclass
class ScenarioResult:
    """场景分类结果"""
    code: str
    scenario: ScenarioType
    is_potential_mainline: bool  # 是否主线起爆候选
    is_tail_rally: bool         # 是否补涨尾声
    is_potential_trap: bool     # 是否拉高出货陷阱
    confidence: float            # 置信度 0-1
    reasons: List[str]           # 判断原因
    metrics: Dict                # 相关指标


class ScenarioClassifier:
    """
    场景分类器 - 识别右侧起爆/拉高出货/补涨尾声
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            # 多日资金流阈值
            "min_net_main_5d": -5000000,       # 5日累计净流入阈值
            "min_net_main_20d": -10000000,      # 20日累计净流入阈值

            # 补涨尾声判断阈值
            "tail_rally_outflow_threshold": 0.6,  # 过去30日60%以上时间流出
            "tail_rally_surge_percentile": 0.90,  # 当日流入超过90%分位
            "tail_rally_stage_3": True,           # 行业是否在stage_3

            # 拉高出货判断阈值
            "pump_dump_threshold": 0.7,           # 超大单占比>70%
            "dump_threshold": -0.5,               # 次日净流出>-50%
        }

    def classify(self, stock_data: Dict) -> ScenarioResult:
        """
        执行场景分类

        Args:
            stock_data: 股票数据字典，包含：
                - code: 股票代码
                - capitaltype: 资金类型
                - flow_data: 资金流向数据（含多日历史）
                - price_data: 价格数据
                - momentum_band: 动量段位
                - risk_score: 风险评分
                - trap_signals: 陷阱信号

        Returns:
            ScenarioResult: 分类结果
        """
        code = stock_data.get('code', '')
        capital_type = stock_data.get('capitaltype', '')
        flow_data = stock_data.get('flow_data', {})
        price_data = stock_data.get('price_data', {})
        risk_score = stock_data.get('risk_score', 0.5)
        trap_signals = stock_data.get('trap_signals', [])

        # 提取资金流历史数据
        main_net_history = self._extract_main_net_history(flow_data)

        # 计算多日资金流指标
        net_main_5d = self._calc_cumulative_flow(main_net_history, 5)
        net_main_20d = self._calc_cumulative_flow(main_net_history, 20)

        # 判断三种场景
        is_potential_mainline = self._check_mainline_scenario(
            net_main_5d, net_main_20d, capital_type, risk_score, trap_signals
        )

        is_tail_rally = self._check_tail_rally_scenario(
            net_main_20d, main_net_history, capital_type, flow_data
        )

        is_potential_trap = self._check_trap_scenario(
            flow_data, main_net_history, risk_score, trap_signals
        )

        # 综合判断场景类型
        scenario = self._determine_scenario(
            is_potential_mainline, is_tail_rally, is_potential_trap
        )

        # 生成判断原因
        reasons = self._generate_reasons(
            scenario, is_potential_mainline, is_tail_rally, is_potential_trap,
            net_main_5d, net_main_20d, risk_score, capital_type
        )

        # 计算置信度
        confidence = self._calc_confidence(
            scenario, net_main_5d, net_main_20d, risk_score, len(trap_signals)
        )

        # 相关指标
        metrics = {
            'net_main_5d': net_main_5d,
            'net_main_20d': net_main_20d,
            'capital_type': capital_type,
            'risk_score': risk_score,
            'flow_history_length': len(main_net_history),
        }

        return ScenarioResult(
            code=code,
            scenario=scenario,
            is_potential_mainline=is_potential_mainline,
            is_tail_rally=is_tail_rally,
            is_potential_trap=is_potential_trap,
            confidence=confidence,
            reasons=reasons,
            metrics=metrics
        )

    def _extract_main_net_history(self, flow_data: Dict) -> List[float]:
        """提取主力净流入历史数据"""
        history = []

        # 尝试从不同字段获取历史数据
        if 'main_net_inflow_history' in flow_data:
            history = flow_data['main_net_inflow_history']
        elif 'records' in flow_data:
            # 从records中提取
            records = flow_data['records']
            history = [r.get('main_net_inflow', 0) for r in records if 'main_net_inflow' in r]

        return history

    def _calc_cumulative_flow(self, history: List[float], days: int) -> float:
        """计算N日累计净流入"""
        if not history:
            return 0.0

        # 取最近N天数据
        recent = history[-days:] if len(history) >= days else history
        return sum(recent)

    def _check_mainline_scenario(
        self,
        net_main_5d: float,
        net_main_20d: float,
        capital_type: str,
        risk_score: float,
        trap_signals: List
    ) -> bool:
        """
        判断是否主线起爆候选

        条件：
        1. 多日资金流不差（不是持续大幅流出）
        2. 风险评分较低
        3. 没有明显陷阱信号
        4. 资金类型倾向机构或混合
        """
        # 条件1：多日资金流不差
        if net_main_5d < self.config['min_net_main_5d']:
            return False

        if net_main_20d < self.config['min_net_main_20d']:
            return False

        # 条件2：风险评分较低
        if risk_score > 0.5:
            return False

        # 条件3：没有明显陷阱信号
        if len(trap_signals) > 0:
            return False

        # 条件4：资金类型（纯HOTMONEY谨慎）
        if capital_type == 'HOTMONEY':
            return False

        return True

    def _check_tail_rally_scenario(
        self,
        net_main_20d: float,
        main_net_history: List[float],
        capital_type: str,
        flow_data: Dict
    ) -> bool:
        """
        判断是否补涨尾声

        条件：
        1. 过去30日累计净流出显著
        2. 当日突然巨额流入
        3. 资金类型为HOTMONEY
        """
        # 条件1：过去30日累计净流出显著
        if net_main_20d > -10000000:  # 流出不够
            return False

        # 条件2：当日突然巨额流入
        if not main_net_history:
            return False

        current_flow = main_net_history[-1]
        if current_flow <= 0:
            return False

        # 当日流入超过过去30日分位数
        percentile = np.percentile(main_net_history, 90)
        if current_flow < percentile:
            return False

        # 条件3：资金类型为HOTMONEY
        if capital_type != 'HOTMONEY':
            return False

        return True

    def _check_trap_scenario(
        self,
        flow_data: Dict,
        main_net_history: List[float],
        risk_score: float,
        trap_signals: List
    ) -> bool:
        """
        判断是否拉高出货陷阱

        条件：
        1. 超大单占比过高
        2. 次日大幅流出
        3. 风险评分较高
        4. 有陷阱信号
        """
        # 条件4：已有陷阱信号
        if len(trap_signals) > 0:
            return True

        # 条件3：风险评分较高
        if risk_score > 0.6:
            return True

        # 条件1：超大单占比过高
        super_large_ratio = flow_data.get('super_large_ratio', 0)
        if super_large_ratio > self.config['pump_dump_threshold']:
            return True

        # 条件2：次日大幅流出
        if len(main_net_history) >= 2:
            today_flow = main_net_history[-1]
            tomorrow_flow = main_net_history[-2]  # 注意顺序，数据可能需要调整
            if today_flow > 0 and tomorrow_flow < self.config['dump_threshold']:
                return True

        return False

    def _determine_scenario(
        self,
        is_potential_mainline: bool,
        is_tail_rally: bool,
        is_potential_trap: bool
    ) -> ScenarioType:
        """综合判断场景类型"""
        # 优先级：陷阱 > 补涨 > 主线
        if is_potential_trap:
            return ScenarioType.TRAP_PUMP_DUMP
        elif is_tail_rally:
            return ScenarioType.TAIL_RALLY
        elif is_potential_mainline:
            return ScenarioType.MAINLINE_RALLY
        else:
            return ScenarioType.UNCERTAIN

    def _generate_reasons(
        self,
        scenario: ScenarioType,
        is_potential_mainline: bool,
        is_tail_rally: bool,
        is_potential_trap: bool,
        net_main_5d: float,
        net_main_20d: float,
        risk_score: float,
        capital_type: str
    ) -> List[str]:
        """生成判断原因"""
        reasons = []

        if scenario == ScenarioType.MAINLINE_RALLY:
            reasons.append(f"多日资金流健康 (5日: {net_main_5d/10000:.1f}万, 20日: {net_main_20d/10000:.1f}万)")
            reasons.append(f"风险评分较低 ({risk_score:.2f})")
            reasons.append("无明显陷阱信号")
            if capital_type == 'INSTITUTIONAL':
                reasons.append("机构资金主导")

        elif scenario == ScenarioType.TRAP_PUMP_DUMP:
            reasons.append("检测到拉高出货模式")
            reasons.append(f"风险评分较高 ({risk_score:.2f})")
            reasons.append("超大单占比过高或次日大幅流出")

        elif scenario == ScenarioType.TAIL_RALLY:
            reasons.append("补涨尾声模式")
            reasons.append(f"长期流出后突然流入 (20日: {net_main_20d/10000:.1f}万)")
            reasons.append("HOTMONEY资金主导")

        else:
            reasons.append("无法明确判断场景类型")

        return reasons

    def _calc_confidence(
        self,
        scenario: ScenarioType,
        net_main_5d: float,
        net_main_20d: float,
        risk_score: float,
        trap_count: int
    ) -> float:
        """计算置信度"""
        confidence = 0.5  # 默认中等置信度

        if scenario == ScenarioType.MAINLINE_RALLY:
            # 主线起爆：资金流越好、风险越低，置信度越高
            confidence = 0.6
            if net_main_5d > 0 and risk_score < 0.3:
                confidence += 0.2
            if net_main_20d > 0:
                confidence += 0.1

        elif scenario == ScenarioType.TRAP_PUMP_DUMP:
            # 拉高出货：风险越高、陷阱越多，置信度越高
            confidence = 0.6
            if risk_score > 0.7:
                confidence += 0.2
            if trap_count > 0:
                confidence += 0.1

        elif scenario == ScenarioType.TAIL_RALLY:
            # 补涨尾声：流出越严重、突然流入越大，置信度越高
            confidence = 0.6
            if net_main_20d < -20000000:
                confidence += 0.2

        return min(confidence, 0.95)


# 测试代码
if __name__ == "__main__":
    classifier = ScenarioClassifier()

    # 测试用例1：主线起爆
    test_data_mainline = {
        'code': '000001',
        'capitaltype': 'INSTITUTIONAL',
        'flow_data': {
            'main_net_inflow_history': [100, 200, 150, 300, 250],  # 5日累计1000万
            'records': []
        },
        'price_data': {},
        'risk_score': 0.3,
        'trap_signals': []
    }

    result = classifier.classify(test_data_mainline)
    print(f"主线起爆测试: {result.scenario.value}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"原因: {result.reasons}")

    # 测试用例2：补涨尾声
    test_data_tail = {
        'code': '000002',
        'capitaltype': 'HOTMONEY',
        'flow_data': {
            'main_net_inflow_history': [-500, -600, -700, -800, 1000],  # 长期流出后突然流入
            'records': []
        },
        'price_data': {},
        'risk_score': 0.5,
        'trap_signals': []
    }

    result = classifier.classify(test_data_tail)
    print(f"\n补涨尾声测试: {result.scenario.value}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"原因: {result.reasons}")

    print("\n✅ 场景分类器测试完成")