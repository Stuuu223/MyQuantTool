#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞价快照存档器 - 保存集合竞价数据

用途：竞价数据非常宝贵（9:15-9:25），错过了就再也拿不到了。我们要把它存成每天一个文件，而不是每秒一个文件。

Author: iFlow CLI
Version: V19.11.6
"""

import os
import pandas as pd
import time
from datetime import datetime
from logic.data_providers.data_source_manager import get_data_source_manager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class AuctionSnapshotSaver:
    def __init__(self):
        self.ds = get_data_source_manager()
        self.save_dir = "data/auction/auction_snapshots"
        os.makedirs(self.save_dir, exist_ok=True)
    
    def snapshot(self, stock_list):
        """
        执行快照保存
        建议只在 9:15 - 9:30 之间运行
        
        Args:
            stock_list: 股票代码列表
        """
        now_str = time.strftime("%H:%M:%S")
        date_str = time.strftime("%Y%m%d")
        
        # 1. 获取极速行情
        data = self.ds.get_realtime_price_fast(stock_list)
        if not data:
            logger.warning("⚠️ [竞价快照] 未获取到数据")
            return
        
        # 2. 转换为 DataFrame 方便追加
        records = []
        for code, info in data.items():
            records.append({
                "time": now_str,
                "code": code,
                "name": info.get('name'),
                "price": info.get('now'),
                "bid1": info.get('bid1'),
                "bid1_vol": info.get('bid1_volume'),
                "ask1": info.get('ask1'),
                "ask1_vol": info.get('ask1_volume')
            })
        
        df = pd.DataFrame(records)
        
        if df.empty:
            logger.warning("⚠️ [竞价快照] 数据为空")
            return
        
        # 3. 追加写入 (Mode='a')，每天一个文件，避免文件数爆炸
        file_path = os.path.join(self.save_dir, f"auction_{date_str}.csv")
        
        # 如果文件不存在，写入表头；存在则不写表头
        header = not os.path.exists(file_path)
        df.to_csv(file_path, mode='a', header=header, index=False, encoding='utf-8-sig')
        
        logger.info(f"📸 竞价快照已追加: {len(df)} 条 -> {file_path}")
    
    def get_today_snapshots(self):
        """
        获取今天的竞价快照数据
        
        Returns:
            DataFrame: 今天的竞价快照数据
        """
        date_str = time.strftime("%Y%m%d")
        file_path = os.path.join(self.save_dir, f"auction_{date_str}.csv")
        
        if os.path.exists(file_path):
            return pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            return pd.DataFrame()


# 使用示例 (可以放在 run_pre_market_warmup.py 里调用):
# saver = AuctionSnapshotSaver()
# saver.snapshot(['600000', '300750'])