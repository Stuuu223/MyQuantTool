# -*- coding: utf-8 -*-
# 【CTO修复】禁用阻塞下载，只使用本地缓存
# 系统只读取本地已缓存数据，无数据返回默认值

"""
CTO V46 时空折叠器 + 竞价MFE考核

核心功能：
1. extract_snapshot_at_time: 统一时间切片提取（Live/Scan两端对齐）
2. check_auction_validity: 竞价MFE物理探针（剔除布朗运动，不看涨跌幅）
"""

import pandas as pd
from typing import Optional, Union


def extract_snapshot_at_time(
    tick_data: Union[dict, pd.DataFrame],
    target_time_str: str = "092505"
) -> Optional[dict]:
    """
    【CTO V46 时空折叠器】
    无论Live内存快照还是Scan硬盘Tick，统一提取目标时间切片！
    
    用途：
    - Live模式：get_full_tick返回的dict直接透传
    - Scan模式：从全天Tick DataFrame中切片提取09:25或15:00快照
    
    Args:
        tick_data: dict (Live) 或 pd.DataFrame (Scan)
        target_time_str: 目标时间，默认09:25:05 (HHMMSS格式)
            - "092505" = 09:25:05 竞价快照
            - "150005" = 15:00:05 收盘快照
    
    Returns:
        统一的dict快照，找不到返回None
    
    示例:
        # Live模式
        snapshot = extract_snapshot_at_time(live_tick_dict, "092505")
        
        # Scan模式
        df = pd.DataFrame(local_data[stock])
        snapshot = extract_snapshot_at_time(df, "092505")
    """
    if tick_data is None:
        return None
    
    # Live模式：传进来的是已经是当下的快照dict
    if isinstance(tick_data, dict):
        return tick_data
        
    # Scan模式：按时间戳切片
    elif isinstance(tick_data, pd.DataFrame):
        if tick_data.empty:
            return None
        try:
            df = tick_data.copy()
            # QMT tick的time字段格式：HHMMSS 或 HHMMSSmmm（毫秒）
            # 统一提取前6位作为HHMMSS
            if 'time' in df.columns:
                df['time_str'] = df['time'].astype(str).str.zfill(9).str[:6]
                slice_df = df[df['time_str'] <= target_time_str]
                if slice_df.empty:
                    return None
                return slice_df.iloc[-1].to_dict()
            else:
                # 没有time字段，取最后一行
                return df.iloc[-1].to_dict()
        except Exception:
            return None
    
    return None


def check_auction_validity(
    snapshot_dict: Optional[dict],
    float_volume_shares: float,
    min_auction_amount: float = 1_000_000.0
) -> bool:
    """
    【CTO V46 极敏雷达】第一斩：剔除布朗运动，考核竞价MFE
    
    物理意义：
    - 不歧视低开/高开，只看资金做功效率
    - MFE = 振幅% / 资金占比 = (开盘价-昨收)/昨收 / (竞价金额/流通市值)
    - 低开+极负MFE = 放量暴跌无承接，剔除
    - 高开+极低MFE = 滞涨诱多（巨量只顶出1%），剔除
    
    Args:
        snapshot_dict: 竞价快照dict（来自extract_snapshot_at_time）
        float_volume_shares: 流通股本（股）
        min_auction_amount: 最低竞价金额阈值，默认100万
    
    Returns:
        True = 通过，False = 剔除
    
    示例:
        snapshot = extract_snapshot_at_time(tick_data, "092505")
        if check_auction_validity(snapshot, float_volume):
            # 通过竞价考核，进入观察池
            pass
    """
    if not snapshot_dict:
        return False
    
    # 提取关键字段
    auction_price = float(snapshot_dict.get('lastPrice', 0) or snapshot_dict.get('open', 0))
    auction_amount = float(snapshot_dict.get('amount', 0))
    pre_close = float(snapshot_dict.get('lastClose', 0) or snapshot_dict.get('prev_close', 0))
    
    if pre_close <= 0:
        pre_close = auction_price
    
    if auction_price <= 0 or pre_close <= 0:
        return False
    
    # 1. 剔除绝对死水（连100万竞价额都没有 = 纯布朗运动）
    if auction_amount < min_auction_amount:
        return False
    
    # 2. 剔除一字死板（买不到）
    auction_high = float(snapshot_dict.get('high', auction_price) or auction_price)
    auction_low = float(snapshot_dict.get('low', auction_price) or auction_price)
    
    # 一字板判断：最高=最低 且 接近涨停/跌停
    if auction_high == auction_low:
        change_from_pre = abs(auction_price - pre_close) / pre_close
        if change_from_pre >= 0.09:  # 接近涨跌停
            return False
    
    # 3. 计算竞价MFE（单位做功效率）
    amplitude_pct = (auction_price - pre_close) / pre_close
    
    # 流通市值
    fv = float_volume_shares
    if fv <= 0:
        return False
    if fv < 10_000_000:  # 万股BUG修复
        fv *= 10000
    
    float_cap = fv * pre_close
    if float_cap <= 0:
        return False
    
    inflow_ratio = auction_amount / float_cap
    
    if inflow_ratio <= 0:
        return False
    
    auction_mfe = amplitude_pct / inflow_ratio
    
    # 4. 物理过滤（不歧视低开，但看做功效率）
    # 低开 + 极度负效率 = 放量暴跌无承接
    if amplitude_pct < 0 and auction_mfe < -50.0:
        return False
    
    # 高开 + 极低效率 = 滞涨诱多（巨量只顶出1%）
    if amplitude_pct > 0 and auction_mfe < 5.0:
        return False
    
    return True


def calculate_auction_mfe(
    snapshot_dict: Optional[dict],
    float_volume_shares: float
) -> float:
    """
    计算竞价MFE值（用于排序和深度分析）
    
    Returns:
        MFE值，无效返回0.0
    """
    if not snapshot_dict:
        return 0.0
    
    auction_price = float(snapshot_dict.get('lastPrice', 0) or snapshot_dict.get('open', 0))
    auction_amount = float(snapshot_dict.get('amount', 0))
    pre_close = float(snapshot_dict.get('lastClose', 0) or snapshot_dict.get('prev_close', 0))
    
    if pre_close <= 0 or auction_price <= 0:
        return 0.0
    
    amplitude_pct = (auction_price - pre_close) / pre_close
    
    fv = float_volume_shares
    if fv <= 0:
        return 0.0
    if fv < 10_000_000:
        fv *= 10000
    
    float_cap = fv * pre_close
    if float_cap <= 0:
        return 0.0
    
    inflow_ratio = auction_amount / float_cap
    if inflow_ratio <= 0:
        return 0.0
    
    return amplitude_pct / inflow_ratio
