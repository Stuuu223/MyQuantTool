"""
跨日风险特征计算器
负责计算基于多日数据的风控特征

核心功能：
1. 计算多日主力净流入（5d/10d/20d/30d）
2. 检测拉高出货模式（pump+dump）
3. 检测补涨尾声模式（长期流出后突然流入）
4. 计算板块阶段（启动/主升/尾声）
"""
from typing import Dict, List, Optional

def compute_multi_day_risk_features(
    code: str,
    trade_date: str,
    flow_records: List[Dict],
    price_3d_change: Optional[float] = None,
) -> Dict:
    """
    计算跨日风险特征（原有函数，保持兼容性）

    Args:
        code: 股票代码
        trade_date: 交易日期
        flow_records: 资金流入记录列表，按日期倒序
        price_3d_change: 3日涨幅（可选）

    Returns:
        dict: 特征字典
            - is_price_up_3d_capital_not_follow: bool
            - price_3d_change: float | None
            - capital_3d_net_sum: float
    """
    
    # 1. 计算最近3日资金净和
    capital_3d_net_sum = 0.0
    n_days = min(3, len(flow_records))
    
    for i in range(n_days):
        record = flow_records[i]
        main_net_inflow = record.get("main_net_inflow", 0)
        capital_3d_net_sum += main_net_inflow
    
    # 2. 判断"3日连涨但资金不跟"
    is_price_up_3d_capital_not_follow = False
    
    if price_3d_change is not None and n_days >= 3:
        # 近似版本：3日涨幅 > 0 && 3日资金净和 <= 0
        if price_3d_change > 0 and capital_3d_net_sum <= 0:
            is_price_up_3d_capital_not_follow = True
    
    return {
        "is_price_up_3d_capital_not_follow": is_price_up_3d_capital_not_follow,
        "price_3d_change": price_3d_change,
        "capital_3d_net_sum": capital_3d_net_sum,
    }


def compute_multi_day_capital_flow(
    flow_records: List[Dict],
    days: List[int] = [5, 10, 20, 30]
) -> Dict[str, float]:
    """
    计算多日主力净流入累积

    Args:
        flow_records: 资金流入记录列表，按日期倒序
        days: 需要计算的天数列表

    Returns:
        dict: 多日主力净流入累积
            - net_main_5d: 5日主力净流入
            - net_main_10d: 10日主力净流入
            - net_main_20d: 20日主力净流入
            - net_main_30d: 30日主力净流入
    """
    results = {}
    
    for day in days:
        net_sum = 0.0
        n = min(day, len(flow_records))
        
        for i in range(n):
            record = flow_records[i]
            main_net_inflow = record.get("main_net_inflow", 0)
            net_sum += main_net_inflow
        
        results[f"net_main_{day}d"] = net_sum
    
    return results


def detect_pump_dump_pattern(
    flow_records: List[Dict],
    price_records: Optional[List[Dict]] = None
) -> Dict:
    """
    检测拉高出货模式（one-day pump + next-day dump）

    Args:
        flow_records: 资金流入记录列表，按日期倒序
        price_records: 价格记录列表（可选），按日期倒序

    Returns:
        dict: 检测结果
            - one_day_pump_next_day_dump: bool
            - confidence: float (0-1)
            - reasons: list[str]
    """
    if len(flow_records) < 3:
        return {
            "one_day_pump_next_day_dump": False,
            "confidence": 0.0,
            "reasons": ["数据不足"]
        }
    
    reasons = []
    confidence = 0.0
    
    # T日（最新一天）
    day_t = flow_records[0]
    day_t1 = flow_records[1]
    day_t2 = flow_records[2] if len(flow_records) > 2 else None
    
    # T日主力净流入
    main_in_t = day_t.get("main_net_inflow", 0)
    super_in_t = day_t.get("super_large_net_in", 0)
    large_in_t = day_t.get("large_net_in", 0)
    
    # T+1日主力净流入
    main_in_t1 = day_t1.get("main_net_inflow", 0)
    super_out_t1 = day_t1.get("super_large_net_in", 0)
    large_out_t1 = day_t1.get("large_net_in", 0)
    
    # 判断条件1：T日主力大幅净流入
    pump_threshold = 5000000  # 500万
    if main_in_t > pump_threshold:
        confidence += 0.3
        reasons.append(f"T日主力大幅净流入 ({main_in_t/10000:.0f}万)")
    
    # 判断条件2：超大单主导
    if super_in_t > 0 and abs(super_in_t) > abs(large_in_t):
        confidence += 0.2
        reasons.append("T日超大单主导")
    
    # 判断条件3：T+1日主力大幅净流出
    dump_threshold = -3000000  # -300万
    if main_in_t1 < dump_threshold:
        confidence += 0.3
        reasons.append(f"T+1日主力大幅净流出 ({main_in_t1/10000:.0f}万)")
    
    # 判断条件4：T+1日超大单/大单大幅流出
    if super_out_t1 < -2000000 or large_out_t1 < -2000000:
        confidence += 0.2
        reasons.append("T+1日超大单/大单大幅流出")
    
    # 阈值判断
    is_pump_dump = confidence >= 0.6
    
    return {
        "one_day_pump_next_day_dump": is_pump_dump,
        "confidence": confidence,
        "reasons": reasons
    }


def detect_tail_rally_pattern(
    flow_records: List[Dict],
    capital_type: Optional[str] = None
) -> Dict:
    """
    检测补涨尾声模式（长期流出后突然流入）

    Args:
        flow_records: 资金流入记录列表，按日期倒序
        capital_type: 资金类型（HOTMONEY/INSTITUTIONAL）

    Returns:
        dict: 检测结果
            - first_pump_after_30d_outflow: bool
            - confidence: float (0-1)
            - reasons: list[str]
    """
    if len(flow_records) < 30:
        return {
            "first_pump_after_30d_outflow": False,
            "confidence": 0.0,
            "reasons": ["数据不足30天"]
        }
    
    reasons = []
    confidence = 0.0
    
    # 计算30日累计净流入
    net_30d = 0.0
    for record in flow_records[:30]:
        main_net_inflow = record.get("main_net_inflow", 0)
        net_30d += main_net_inflow
    
    # 当前日（最新一天）
    today = flow_records[0]
    main_in_today = today.get("main_net_inflow", 0)
    
    # 判断条件1：30日累计明显净流出
    outflow_threshold = -10000000  # -1000万
    if net_30d < outflow_threshold:
        confidence += 0.4
        reasons.append(f"30日累计净流出 ({net_30d/10000:.0f}万)")
    
    # 判断条件2：当前日巨额净流入
    pump_threshold = 5000000  # 500万
    if main_in_today > pump_threshold:
        confidence += 0.3
        reasons.append(f"当前日巨额净流入 ({main_in_today/10000:.0f}万)")
    
    # 判断条件3：游资主导
    if capital_type == "HOTMONEY":
        confidence += 0.3
        reasons.append("游资主导")
    
    # 阈值判断
    is_tail_rally = confidence >= 0.6
    
    return {
        "first_pump_after_30d_outflow": is_tail_rally,
        "confidence": confidence,
        "reasons": reasons
    }


def compute_sector_stage(
    sector_20d_pct_change: float,
    sector_5d_trend: float
) -> Dict:
    """
    计算板块阶段（粗版）

    Args:
        sector_20d_pct_change: 板块20日涨幅
        sector_5d_trend: 板块5日趋势

    Returns:
        dict: 板块阶段
            - sector_stage: int (1=启动, 2=主升, 3=尾声)
            - stage_name: str
    """
    stage = 1
    stage_name = "启动"
    
    # 简化规则：基于涨幅判断
    if sector_20d_pct_change < 5:
        stage = 1
        stage_name = "启动"
    elif sector_20d_pct_change < 20:
        stage = 2
        stage_name = "主升"
    else:
        stage = 3
        stage_name = "尾声"
    
    return {
        "sector_stage": stage,
        "stage_name": stage_name
    }


def compute_all_scenario_features(
    code: str,
    trade_date: str,
    flow_records: List[Dict],
    capital_type: Optional[str] = None,
    price_records: Optional[List[Dict]] = None,
    sector_20d_pct_change: Optional[float] = None,
    sector_5d_trend: Optional[float] = None,
) -> Dict:
    """
    计算所有场景特征（统一入口）

    Args:
        code: 股票代码
        trade_date: 交易日期
        flow_records: 资金流入记录列表，按日期倒序
        capital_type: 资金类型
        price_records: 价格记录列表
        sector_20d_pct_change: 板块20日涨幅
        sector_5d_trend: 板块5日趋势

    Returns:
        dict: 所有场景特征
    """
    features = {}
    
    # 1. 多日资金流
    capital_flow = compute_multi_day_capital_flow(flow_records)
    features.update(capital_flow)
    
    # 2. 拉高出货模式
    pump_dump = detect_pump_dump_pattern(flow_records, price_records)
    features.update(pump_dump)
    
    # 3. 补涨尾声模式
    tail_rally = detect_tail_rally_pattern(flow_records, capital_type)
    features.update(tail_rally)
    
    # 4. 板块阶段
    if sector_20d_pct_change is not None and sector_5d_trend is not None:
        sector_stage = compute_sector_stage(sector_20d_pct_change, sector_5d_trend)
        features.update(sector_stage)
    else:
        features["sector_stage"] = 2  # 默认主升
        features["stage_name"] = "主升"
    
    return features