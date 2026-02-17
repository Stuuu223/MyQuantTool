#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BacktestEngine数据适配器
解决DataManager返回的数据格式与BacktestEngine期望不匹配的问题
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_providers.data_manager import DataManager


class BacktestDataAdapter:
    """
    为BacktestEngine提供正确格式化的历史数据
    
    主要修复：
    1. 将'date'列（Unix时间戳毫秒）转换为DateTimeIndex
    2. 确保数据按日期排序
    3. 处理缺失值
    """
    
    def __init__(self):
        self.db = DataManager()
    
    def get_history_data(self, stock_code: str) -> pd.DataFrame:
        """
        获取正确格式的历史数据
        
        Returns:
            DataFrame with DateTimeIndex
        """
        df = self.db.get_history_data(stock_code)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 检查是否有'date'列（Unix时间戳毫秒）
        if 'date' in df.columns:
            # 确保date列是数值类型，然后转换为datetime
            df['date'] = pd.to_numeric(df['date'], errors='coerce')
            df['datetime'] = pd.to_datetime(df['date'], unit='ms')
            df.set_index('datetime', inplace=True)
        else:
            # 如果没有date列，尝试其他方式
            return pd.DataFrame()
        
        # 确保按日期排序
        df.sort_index(inplace=True)
        
        # 删除不必要的列
        cols_to_drop = ['index', 'date']
        for col in cols_to_drop:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)
        
        return df
    
    def close(self):
        """关闭数据连接"""
        self.db.close()
