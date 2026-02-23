# -*- coding: utf-8 -*-
"""
交易守门人（Trade Gatekeeper）

功能：
统一封装策略拦截逻辑，确保手动扫描和自动监控使用相同的过滤标准
包括：防守斧、时机斧、资金流预警、决策标签等

Author: MyQuantTool Team
Date: 2026-02-13
Version: V11.0.1 - 架构重构版
"""

from typing import Dict, List, Tuple
from datetime import datetime
from logic.utils.logger import get_logger

logger = get_logger(__name__)

# Phase 9.2 TODO: 需要创建这些模块
try:
    from logic.sectors.sector_resonance import SectorResonanceCalculator
except ImportError:
    SectorResonanceCalculator = None

try:
    from logic.equity_data_accessor import get_circ_mv
except ImportError:
    get_circ_mv = None


class TradeGatekeeper:
    """
    交易守门人
    
    职责：
    - 防守斧：禁止场景检查
    - 时机斧：板块共振检查
    - 资金流预警：主力资金大量流出检测
    - 决策标签：资金推动力决策树
    - 信号压缩：诱多信号压缩
    """
    
    def __init__(self, config: dict = None):
        """
        初始化守门人
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 板块共振缓存（5分钟TTL）
        self.sector_resonance_cache = {}
        self.sector_resonance_cache_ttl = self.config.get('monitor', {}).get('cache', {}).get('sector_resonance_ttl', 300)
        
        # 资金流历史缓存（用于检测变化）
        self.capital_flow_history = {}
        self.capital_flow_history_ttl = 300  # 5分钟
        
        # 数据容忍度
        self.data_tolerance_minutes = self.config.get('monitor', {}).get('data_freshness', {}).get('tolerance_minutes', 30)
        
        logger.info("✅ 交易守门人初始化成功")
    
    def check_defensive_scenario(self, item: dict) -> Tuple[bool, str]:
        """
        🛡️ 防守斧：场景检查
        
        严格禁止 TAIL_RALLY/TRAP 场景开仓
        
        Args:
            item: 股票数据字典
        
        Returns:
            (is_forbidden, reason)
        """
        from logic.risk.risk_control import FORBIDDEN_SCENARIOS
        
        code = item.get('code', '')
        name = item.get('name', 'N/A')
        scenario_type = item.get('scenario_type', '')
        is_tail_rally = item.get('is_tail_rally', False)
        is_potential_trap = item.get('is_potential_trap', False)
        
        # 硬编码禁止规则
        if scenario_type in FORBIDDEN_SCENARIOS:
            reason = f"🛡️ [防守斧] 禁止场景: {scenario_type}"
            logger.warning(f"🛡️ [防守斧拦截] {code} ({name}) - {scenario_type}")
            return True, reason
        
        # 兼容旧版：通过布尔值检查
        if is_tail_rally:
            reason = "🛡️ [防守斧] 补涨尾声场景，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截] {code} ({name}) - 补涨尾声")
            return True, reason
        
        if is_potential_trap:
            reason = "🛡️ [防守斧] 拉高出货陷阱，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截] {code} ({name}) - 拉高出货")
            return True, reason
        
        # 通过检查
        return False, ""
    
    def check_sector_resonance(self, item: dict, all_results: dict) -> Tuple[bool, str]:
        """
        🎯 时机斧：板块共振检查
        
        只在板块满足共振条件时才允许入场：
        - Leaders ≥ 3：板块内涨停股数量 ≥ 3
        - Breadth ≥ 35%：板块内上涨比例 ≥ 35%
        
        Args:
            item: 股票数据字典
            all_results: 完整的扫描结果
        
        Returns:
            (is_blocked, reason)
        """
        code = item.get('code', '')
        name = item.get('name', 'N/A')
        sector_name = item.get('sector_name', '')
        sector_code = item.get('sector_code', '')
        
        # 如果没有板块信息，跳过检查（不拦截）
        if not sector_name or not sector_code or sector_name == '未知板块':
            return False, "⏸️ 无板块信息，跳过共振检查"
        
        # 检查板块共振缓存
        if sector_name in self.sector_resonance_cache:
            result, timestamp = self.sector_resonance_cache[sector_name]
            if (datetime.now() - timestamp).total_seconds() < self.sector_resonance_cache_ttl:
                # 缓存有效，使用缓存结果
                if not result.is_resonant:
                    reason = f"⏸️ [时机斧] 板块未共振（缓存）：{result.reason}"
                    return True, reason
                else:
                    return False, f"✅ [时机斧] 板块共振满足（缓存）：{result.reason}"
        
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
        
        # 更新缓存
        self.sector_resonance_cache[sector_name] = (resonance_result, datetime.now())
        
        # 检查是否满足共振条件
        if not resonance_result.is_resonant:
            reason = f"⏸️ [时机斧] 板块未共振：{resonance_result.reason}"
            logger.info(f"⏸️ [时机斧拦截] {code} ({name}) - Leaders:{resonance_result.leaders} Breadth:{resonance_result.breadth:.1f}%")
            return True, reason
        
        # 通过检查
        reason = f"✅ [时机斧] 板块共振满足：{resonance_result.reason}"
        logger.info(f"✅ [时机斧通过] {code} ({name}) - Leaders:{resonance_result.leaders} Breadth:{resonance_result.breadth:.1f}%")
        return False, reason
    
    def check_capital_flow_change(self, code: str, main_net_inflow: float) -> dict:
        """
        🔥 P0-4: 检查资金流变化（主力资金大量流出检测）
        
        检测逻辑：
        - 对比当前资金流与历史资金流
        - 检测是否出现大量流出
        - 检测资金推动力急剧下降
        
        Args:
            code: 股票代码
            main_net_inflow: 当前主力净流入（元）
        
        Returns:
            dict: {
                'has_alert': bool,
                'alert_type': str,
                'change_amount': float,
                'change_pct': float,
                'message': str
            }
        """
        result = {
            'has_alert': False,
            'alert_type': '',
            'change_amount': 0,
            'change_pct': 0,
            'message': ''
        }
        
        try:
            now = datetime.now()
            
            # 获取历史资金流数据
            if code in self.capital_flow_history:
                history = self.capital_flow_history[code]
                historical_flow = history['main_net_inflow']
                timestamp = history['timestamp']
                
                # 检查数据时效性（5分钟内有效）
                age = (now - timestamp).total_seconds()
                if age > self.capital_flow_history_ttl:
                    # 数据过期，清除历史数据
                    del self.capital_flow_history[code]
                    logger.debug(f"🔍 {code} 资金流历史数据已过期，重新建立基线")
                else:
                    # 计算资金流变化
                    change = main_net_inflow - historical_flow
                    change_pct = 0
                    
                    if historical_flow != 0:
                        change_pct = change / abs(historical_flow) * 100
                    
                    result['change_amount'] = change
                    result['change_pct'] = change_pct
                    
                    # 检测预警条件
                    
                    # 条件1: 主力资金大量流出（流入转为流出）
                    if historical_flow > 0 and main_net_inflow < 0:
                        outflow_amount = abs(change)
                        if outflow_amount > 50_000_000:  # 超过5000万
                            result['has_alert'] = True
                            result['alert_type'] = 'MASSIVE_OUTFLOW'
                            result['message'] = f'🚨 [资金流预警] {code} 主力资金大量流出 {outflow_amount/1e8:.2f}亿（由入转出）'
                            logger.warning(result['message'])
                    
                    # 条件2: 资金推动力急剧下降（>50%下降）
                    elif historical_flow > 0 and change_pct < -50:
                        result['has_alert'] = True
                        result['alert_type'] = 'MOMENTUM_DROP'
                        result['message'] = f'⚠️ [资金流预警] {code} 资金推动力急剧下降 {change_pct:.1f}%'
                        logger.warning(result['message'])
                    
                    # 条件3: 持续大量流出（连续3次检测到流出）
                    elif historical_flow < 0 and main_net_inflow < 0:
                        if abs(change) > 50_000_000:  # 超过5000万
                            result['has_alert'] = True
                            result['alert_type'] = 'CONTINUOUS_OUTFLOW'
                            result['message'] = f'⚠️ [资金流预警] {code} 持续大量流出 {abs(main_net_inflow)/1e8:.2f}亿'
                            logger.warning(result['message'])
            
            # 更新历史资金流数据
            self.capital_flow_history[code] = {
                'main_net_inflow': main_net_inflow,
                'timestamp': now
            }
        
        except Exception as e:
            logger.error(f"❌ 检测资金流变化失败 {code}: {e}")
        
        return result
    
    def compress_trap_signals(self, trap_signals: list) -> str:
        """
        压缩诱多信号为短字符串
        
        Args:
            trap_signals: 诱多信号列表
        
        Returns:
            压缩后的字符串
        """
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
    
    def calculate_decision_tag(self, ratio: float, risk_score: float, trap_signals: list) -> str:
        """
        资金推动力决策树:
        
        第1关: ratio < 0.5% → PASS❌（止损优先，资金推动力太弱）
        第2关: ratio > 5% → TRAP❌（暴拉出货风险）
        第3关: 诱多 + 高风险 → BLOCK❌
        第4关: 1-3% + 低风险 + 无诱多 → FOCUS✅
        
        Args:
            ratio: 主力净流入占比（%）
            risk_score: 风险评分
            trap_signals: 诱多信号列表
        
        Returns:
            决策标签字符串
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
    
    def validate_flow_data_freshness(self, flow_data: dict, tolerance_minutes: int = None) -> bool:
        """
        🔥 [P0修复] 验证资金流数据时效性（小时级精度）
        
        Args:
            flow_data: 资金流数据字典
            tolerance_minutes: 允许的数据延迟（分钟），默认使用配置值
        
        Returns:
            bool: 数据是否新鲜
        """
        if tolerance_minutes is None:
            tolerance_minutes = self.data_tolerance_minutes
        
        if not flow_data or 'latest' not in flow_data:
            logger.warning("❌ 资金流数据缺少时间戳")
            return False
        
        latest = flow_data.get('latest', {})
        fetch_time_str = latest.get('date', '')
        
        if not fetch_time_str:
            logger.warning("❌ 资金流数据缺少日期时间戳")
            return False
        
        try:
            # 解析日期时间（格式：YYYY-MM-DD）
            fetch_time = datetime.strptime(fetch_time_str, '%Y-%m-%d').replace(hour=15, minute=0)
        except Exception as e:
            logger.error(f"❌ 时间戳解析失败: {e}")
            return False
        
        # 计算数据年龄（分钟）
        age_minutes = (datetime.now() - fetch_time).total_seconds() / 60
        
        if age_minutes > tolerance_minutes:
            logger.warning(f"⚠️ 资金流数据已过期: {age_minutes:.1f} 分钟前（容忍 {tolerance_minutes} 分钟）")
            return False
        
        return True
    
    def filter_opportunities(self, opportunities: List[dict], all_results: dict = None) -> Tuple[List[dict], List[dict], List[dict]]:
        """
        统一过滤机会池
        
        Args:
            opportunities: 机会池列表
            all_results: 完整的扫描结果（用于板块共振计算）
        
        Returns:
            (opportunities_final, opportunities_blocked, timing_downgraded)
            - opportunities_final: 最终通过的机会
            - opportunities_blocked: 被防守斧拦截的机会
            - timing_downgraded: 被时机斧降级的机会
        """
        if all_results is None:
            all_results = {'opportunities': opportunities, 'watchlist': []}
        
        # 🛡️ 防守斧：过滤机会池中的禁止场景
        opportunities_safe = []
        opportunities_blocked = []
        
        for item in opportunities:
            is_forbidden, reason = self.check_defensive_scenario(item)
            if is_forbidden:
                opportunities_blocked.append((item, reason))
            else:
                opportunities_safe.append(item)
        
        # 🎯 时机斧：板块共振检查（降级到观察池）
        opportunities_final = []
        timing_downgraded = []
        
        for item in opportunities_safe:
            is_blocked, reason = self.check_sector_resonance(item, all_results)
            if is_blocked:
                # 降级到观察池，而非直接拒绝
                timing_downgraded.append((item, reason))
            else:
                opportunities_final.append(item)
        
        return opportunities_final, opportunities_blocked, timing_downgraded


# =============================================================================
# 订单级别检查（与trade_interface.py集成）
# =============================================================================

def check_buy_order(order, total_capital: float = 20000.0) -> Tuple[bool, str]:
    """
    检查买入订单（与TradeInterface集成）
    
    检查项：
    - 价格合理性（>0）
    - 数量合理性（100的整数倍）
    - 单次买入金额限制（默认不超过总资金50%）
    
    Args:
        order: TradeOrder对象或类似结构（有stock_code, price, quantity属性）
        total_capital: 总资金，用于计算单笔限额
    
    Returns:
        (is_valid, message)
    """
    # 检查1: 价格合理性
    if order.price <= 0:
        return False, f'买入价格异常: {order.price}'
    
    # 检查2: 数量合理性（A股必须是100的整数倍）
    if order.quantity <= 0:
        return False, f'买入数量必须大于0: {order.quantity}'
    if order.quantity % 100 != 0:
        return False, f'买入数量必须是100的整数倍: {order.quantity}'
    
    # 检查3: 单次买入金额限制
    MAX_SINGLE_ORDER_RATIO = 0.5  # 单笔最大占总资金比例
    order_amount = order.price * order.quantity
    max_single_order = total_capital * MAX_SINGLE_ORDER_RATIO
    if order_amount > max_single_order:
        return False, (f'单笔买入金额过大: {order_amount:.2f}, '
                      f'超过限制{max_single_order:.2f} ({MAX_SINGLE_ORDER_RATIO*100:.0f}%)')
    
    return True, '通过'


def check_sell_order(order, current_position: int) -> Tuple[bool, str]:
    """
    检查卖出订单（与TradeInterface集成）
    
    检查项：
    - 价格合理性（>0）
    - 数量合理性（100的整数倍）
    - 持仓检查
    
    Args:
        order: TradeOrder对象或类似结构
        current_position: 当前持仓数量
    
    Returns:
        (is_valid, message)
    """
    # 检查1: 价格合理性
    if order.price <= 0:
        return False, f'卖出价格异常: {order.price}'
    
    # 检查2: 数量合理性
    if order.quantity <= 0:
        return False, f'卖出数量必须大于0: {order.quantity}'
    if order.quantity % 100 != 0:
        return False, f'卖出数量必须是100的整数倍: {order.quantity}'
    
    # 检查3: 持仓检查
    if current_position <= 0:
        return False, f'未持有该股票: {order.stock_code}'
    if order.quantity > current_position:
        return False, f'卖出数量超过持仓: 卖出{order.quantity}, 持仓{current_position}'
    
    return True, '通过'