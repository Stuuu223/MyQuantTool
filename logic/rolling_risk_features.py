"""
跨日风险特征计算器
负责计算基于多日数据的风控特征
"""
from typing import Dict, List, Optional

def compute_multi_day_risk_features(
    code: str,
    trade_date: str,
    flow_records: List[Dict],
    price_3d_change: Optional[float] = None,
) -> Dict:
    """
    计算跨日风险特征

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