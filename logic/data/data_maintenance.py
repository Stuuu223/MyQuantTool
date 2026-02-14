#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据维护工具 - 自动清理过期文件

用途：防止CSV文件无限增殖，自动删除N天前的旧扫描结果

Author: iFlow CLI
Version: V19.11.6
"""

import os
import time
import glob
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DataMaintenance:
    @staticmethod
    def clean_old_files(folder_path, days_to_keep=3):
        """
        自动清理过期文件，防止硬盘爆炸
        
        Args:
            folder_path: 目标文件夹
            days_to_keep: 保留最近几天的文件
        """
        if not os.path.exists(folder_path):
            return
        
        now = time.time()
        cutoff = now - (days_to_keep * 86400)  # N天前的秒数
        
        # 查找所有 csv 文件
        files = glob.glob(os.path.join(folder_path, "*.csv"))
        deleted_count = 0
        
        for f in files:
            if os.path.getmtime(f) < cutoff:
                try:
                    os.remove(f)
                    deleted_count += 1
                    logger.info(f"🗑️ [自动清理] 已删除过期文件: {os.path.basename(f)}")
                except Exception as e:
                    logger.error(f"清理文件失败 {f}: {e}")
        
        if deleted_count > 0:
            logger.info(f"🧹 [自动清理] 已删除 {deleted_count} 个 {days_to_keep} 天前的过期文件")
        else:
            logger.info(f"✅ [自动清理] 没有找到需要清理的过期文件")
    
    @staticmethod
    def get_folder_size(folder_path):
        """
        获取文件夹大小
        
        Args:
            folder_path: 目标文件夹
        
        Returns:
            str: 文件夹大小（MB）
        """
        if not os.path.exists(folder_path):
            return "0 MB"
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        
        return f"{total_size / (1024 * 1024):.2f} MB"