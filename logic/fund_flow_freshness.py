#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流新鲜度检查器 (Fund Flow Freshness Checker)

核心功能：
1. 检查资金流数据是否是当日数据
2. 分级：FRESH/STALE/DEGRADED
3. 为 evidence_matrix 提供新鲜度指标

Author: MyQuantTool Team
Date: 2026-02-10
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class FundFlowFreshness:
    """资金流新鲜度等级"""
    FRESH = "FRESH"          # 当日数据
    STALE = "STALE"          # T-1 数据（昨天）
    DEGRADED = "DEGRADED"    # 更早的数据


def get_previous_trading_day(today: str) -> str:
    """
    获取上一个交易日（简化版，不考虑节假日）
    
    Args:
        today: 今天的日期字符串 (YYYY-MM-DD 格式)
    
    Returns:
        上一个交易日 (YYYY-MM-DD 格式)
    """
    try:
        today_date = datetime.strptime(today, '%Y-%m-%d')
        
        # 向前推一天
        prev_date = today_date - timedelta(days=1)
        
        # 如果是周末，继续向前推
        while prev_date.weekday() >= 5:  # 5=周六, 6=周日
            prev_date = prev_date - timedelta(days=1)
        
        return prev_date.strftime('%Y-%m-%d')
    
    except Exception as e:
        logger.warning(f"⚠️  计算上一个交易日失败: {e}")
        # 失败时返回今天的日期
        return today


def check_fund_flow_freshness(
    flow_data: Dict,
    current_time: Optional[datetime] = None
) -> Tuple[str, Dict]:
    """
    检查资金流数据新鲜度
    
    Args:
        flow_data: 资金流数据字典，包含:
            - latest: {
                'date': 'YYYY-MM-DD',  # 最新数据日期
                'main_net_inflow': float
              }
        current_time: 当前时间（默认为系统时间）
    
    Returns:
        (freshness_level, freshness_details)
        - freshness_level: FRESH/STALE/DEGRADED
        - freshness_details: {
            'flow_asof_date': str,         # 资金流数据截止日期
            'scan_date': str,              # 扫描日期
            'days_lag': int,               # 数据滚后天数
            'is_realtime': bool,           # 是否实时数据
            'warning': str                 # 警告信息（如果有）
          }
    """
    # 获取当前时间
    if current_time is None:
        current_time = datetime.now()
    
    today = current_time.strftime('%Y-%m-%d')
    
    # 提取资金流最新日期
    flow_latest_date = ''
    if 'latest' in flow_data and isinstance(flow_data['latest'], dict):
        flow_latest_date = flow_data['latest'].get('date', '')
    
    # 处理 date 字段的多种格式
    if flow_latest_date:
        # 如果是 datetime.date 对象，转换为字符串
        if hasattr(flow_latest_date, 'strftime'):
            flow_latest_date = flow_latest_date.strftime('%Y-%m-%d')
        # 如果是其他格式的字符串，尝试标准化
        elif isinstance(flow_latest_date, str):
            # 尝试处理 'YYYY-MM-DD' 或 'YYYYMMDD' 格式
            if len(flow_latest_date) == 10 and '-' in flow_latest_date:
                pass  # 已经是 'YYYY-MM-DD' 格式
            elif len(flow_latest_date) == 8:
                # 'YYYYMMDD' -> 'YYYY-MM-DD'
                flow_latest_date = f"{flow_latest_date[:4]}-{flow_latest_date[4:6]}-{flow_latest_date[6:8]}"
    
    # 数据缺失
    if not flow_latest_date:
        logger.warning("⚠️  资金流数据缺失 latest.date 字段")
        return FundFlowFreshness.DEGRADED, {
            'flow_asof_date': 'N/A',
            'scan_date': today,
            'days_lag': 9999,
            'is_realtime': False,
            'warning': '资金流数据缺失日期字段'
        }
    
    # 计算数据滚后天数
    try:
        flow_date = datetime.strptime(flow_latest_date, '%Y-%m-%d')
        current_date = datetime.strptime(today, '%Y-%m-%d')
        days_lag = (current_date - flow_date).days
    except Exception as e:
        logger.warning(f"⚠️  日期解析失败: {e}")
        return FundFlowFreshness.DEGRADED, {
            'flow_asof_date': flow_latest_date,
            'scan_date': today,
            'days_lag': 9999,
            'is_realtime': False,
            'warning': '日期格式解析失败'
        }
    
    # 分级判断
    if flow_latest_date == today:
        # 当日数据：实时数据
        freshness = FundFlowFreshness.FRESH
        is_realtime = True
        warning = ''
    elif flow_latest_date == get_previous_trading_day(today):
        # T-1 数据：昨天的数据，不是实时数据
        freshness = FundFlowFreshness.STALE
        is_realtime = False
        warning = f'资金流为T-1数据（{flow_latest_date}），禁止用于盘中决策'
    else:
        # 更早的数据：严重过期
        freshness = FundFlowFreshness.DEGRADED
        is_realtime = False
        warning = f'资金流数据严重过期（{flow_latest_date}，滚后{days_lag}天）'
    
    # 返回详细信息
    freshness_details = {
        'flow_asof_date': flow_latest_date,
        'scan_date': today,
        'days_lag': days_lag,
        'is_realtime': is_realtime,
        'warning': warning
    }
    
    return freshness, freshness_details


def validate_fund_flow_for_trading(
    freshness: str,
    trading_mode: str = 'intraday'
) -> Tuple[bool, str]:
    """
    验证资金流数据是否可用于交易决策
    
    Args:
        freshness: 新鲜度等级 (FRESH/STALE/DEGRADED)
        trading_mode: 交易模式
            - 'intraday': 盘中交易（强制要求 FRESH）
            - 'premarket': 盘前分析（允许 STALE）
            - 'postmarket': 盘后回测（允许 STALE）
    
    Returns:
        (is_valid, reason)
    """
    if trading_mode == 'intraday':
        # 盘中模式：必须是 FRESH 数据
        if freshness == FundFlowFreshness.FRESH:
            return True, '资金流数据新鲜，可用于盘中决策'
        elif freshness == FundFlowFreshness.STALE:
            return False, '资金流为T-1数据，禁止用于盘中决策'
        else:
            return False, '资金流数据严重过期，禁止交易'
    else:
        # 盘前/盘后模式：允许 STALE 数据
        if freshness in [FundFlowFreshness.FRESH, FundFlowFreshness.STALE]:
            return True, f'资金流数据可用于{trading_mode}分析'
        else:
            return False, '资金流数据严重过期，不建议使用'


# 单元测试
if __name__ == "__main__":
    from datetime import datetime
    
    print("🧪 开始单元测试: 资金流新鲜度检查器")
    print("=" * 80)
    
    # 测试用例1：当日数据 (FRESH)
    print("\n测试 1: 当日数据 (FRESH)")
    flow_data_fresh = {
        'latest': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'main_net_inflow': 10000000
        }
    }
    freshness, details = check_fund_flow_freshness(flow_data_fresh)
    print(f"  新鲜度: {freshness}")
    print(f"  详情: {details}")
    is_valid, reason = validate_fund_flow_for_trading(freshness, 'intraday')
    print(f"  盘中决策可用: {is_valid} - {reason}")
    
    # 测试用例2：T-1 数据 (STALE)
    print("\n测试 2: T-1 数据 (STALE)")
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    flow_data_stale = {
        'latest': {
            'date': yesterday,
            'main_net_inflow': 20000000
        }
    }
    freshness, details = check_fund_flow_freshness(flow_data_stale)
    print(f"  新鲜度: {freshness}")
    print(f"  详情: {details}")
    is_valid, reason = validate_fund_flow_for_trading(freshness, 'intraday')
    print(f"  盘中决策可用: {is_valid} - {reason}")
    is_valid_pre, reason_pre = validate_fund_flow_for_trading(freshness, 'premarket')
    print(f"  盘前分析可用: {is_valid_pre} - {reason_pre}")
    
    # 测试用例3：过期数据 (DEGRADED)
    print("\n测试 3: 过期数据 (DEGRADED)")
    old_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    flow_data_degraded = {
        'latest': {
            'date': old_date,
            'main_net_inflow': 30000000
        }
    }
    freshness, details = check_fund_flow_freshness(flow_data_degraded)
    print(f"  新鲜度: {freshness}")
    print(f"  详情: {details}")
    is_valid, reason = validate_fund_flow_for_trading(freshness, 'intraday')
    print(f"  盘中决策可用: {is_valid} - {reason}")
    
    # 测试用例4：数据缺失
    print("\n测试 4: 数据缺失")
    flow_data_missing = {
        'latest': {}
    }
    freshness, details = check_fund_flow_freshness(flow_data_missing)
    print(f"  新鲜度: {freshness}")
    print(f"  详情: {details}")
    
    print("\n" + "=" * 80)
    print("✅ 单元测试完成")
