#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存回放提供器（仅支持已有扫描记录）

功能：
- 扫描指定日期的所有快照文件
- 读取指定时间点的快照数据
- 验证复盘是否可行

Author: iFlow CLI
Version: V1.0
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class CacheReplayProvider:
    """缓存回放提供器（仅支持已有扫描记录）"""

    def __init__(self, target_date: str):
        """
        初始化缓存回放提供器

        Args:
            target_date: 目标日期 '2026-02-06'
        """
        self.target_date = target_date
        self.available_snapshots = self._scan_available_snapshots()

    def _scan_available_snapshots(self) -> Dict[str, str]:
        """
        扫描可用的时间点快照

        Returns:
            {'092157': '完整路径', '093027': '完整路径', ...}
        """
        pattern = f"data/scan_results/{self.target_date}_*_intraday.json"
        snapshots = {}

        files = glob.glob(pattern)
        if not files:
            logger.warning(f"⚠️ 未找到 {self.target_date} 的扫描结果")
            return snapshots

        for file in files:
            # 提取时间点：2026-02-06_092157_intraday.json -> 092157
            filename = os.path.basename(file)
            time_part = filename.split('_')[1][:6]  # 取前6位数字
            snapshots[time_part] = file

        logger.info(f"✅ 扫描到 {len(snapshots)} 个快照: {list(snapshots.keys())}")
        return snapshots

    def get_snapshot(self, time_point: str) -> Optional[Dict]:
        """
        获取指定时间点的快照

        Args:
            time_point: '092157' / '093027'

        Returns:
            快照数据字典，如果不存在返回 None
        """
        if time_point not in self.available_snapshots:
            logger.error(f"❌ 时间点 {time_point} 不存在")
            return None

        file_path = self.available_snapshots[time_point]
        logger.info(f"📖 读取快照: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            logger.info(f"✅ 快照加载成功: {snapshot['scan_time']}")
            return snapshot
        except Exception as e:
            logger.error(f"❌ 读取快照失败: {e}")
            return None

    def list_available_timepoints(self) -> List[str]:
        """列出所有可用的时间点（排序）"""
        return sorted(self.available_snapshots.keys())

    def validate_replay_possible(self) -> Tuple[bool, str]:
        """
        验证复盘是否可行

        Returns:
            (是否可行, 提示信息)
        """
        if not self.available_snapshots:
            return False, f"❌ {self.target_date} 没有扫描记录，无法复盘"

        return True, f"✅ {self.target_date} 有 {len(self.available_snapshots)} 个时间点快照: {self.list_available_timepoints()}"