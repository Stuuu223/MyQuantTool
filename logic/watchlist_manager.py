#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观察池管理器（带容量控制）

功能：
1. 最大容量MAX 100只股票
2. 超过容量时自动删除最旧/最低分记录
3. 优先级排序（根据Level3得分）
4. 自动清理过期股票（7天未通过Level3）

Author: MyQuantTool Team
Date: 2026-02-11
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WatchlistItem:
    """观察池项目"""
    code: str
    name: str
    reason: str
    added_at: str
    level1_result: Optional[dict] = None
    level2_result: Optional[dict] = None
    level3_result: Optional[dict] = None
    priority_score: float = 0.0  # 优先级得分


class WatchlistManager:
    """
    观察池管理器
    
    使用场景：
    - 三漏斗扫描系统
    - 重点股票监控
    
    容量控制策略：
    - MAX 100只股票
    - 超过时删除最低优先级股票
    - 7天未通过Level3 → 自动清理
    
    优先级计算：
    - Level3得分 × 0.6
    - Level2得分 × 0.3
    - 添加时间 × 0.1
    
    示例：
    ```python
    manager = WatchlistManager(max_size=100)
    manager.add('600000.SH', '浦发银行', '主力吸筹')
    
    if manager.is_full():
        logger.warning("观察池已满")
    ```
    """
    
    def __init__(self, storage_path: str = "data/watchlist.json", max_size: int = 100):
        """
        初始化管理器
        
        Args:
            storage_path: 存储路径
            max_size: 最大容量
        """
        self.storage_path = Path(storage_path)
        self.max_size = max_size
        self.watchlist: Dict[str, WatchlistItem] = {}
        
        self._load()
        logger.info(f"WatchlistManager 初始化: max_size={max_size}, current_size={len(self.watchlist)}")
    
    def add(
        self,
        code: str,
        name: str,
        reason: str,
        force: bool = False
    ) -> bool:
        """
        添加股票到观察池
        
        Args:
            code: 股票代码
            name: 股票名称
            reason: 添加原因
            force: 强制添加（即使满了也添加）
        
        Returns:
            True: 添加成功
            False: 添加失败（容量满且非强制）
        """
        # 检查是否已存在
        if code in self.watchlist:
            logger.debug(f"{code} 已在观察池中")
            return True
        
        # 检查容量
        if len(self.watchlist) >= self.max_size:
            if not force:
                logger.warning(f"观察池已满 ({self.max_size}), 无法添加 {code}")
                return False
            else:
                # 强制添加，删除最低优先级
                self._remove_lowest_priority()
        
        # 添加新股票
        item = WatchlistItem(
            code=code,
            name=name,
            reason=reason,
            added_at=datetime.now().isoformat()
        )
        
        self.watchlist[code] = item
        self._save()
        
        logger.info(f"添加股票: {code} {name} ({len(self.watchlist)}/{self.max_size})")
        return True
    
    def remove(self, code: str) -> bool:
        """
        从观察池移除股票
        
        Args:
            code: 股票代码
        
        Returns:
            True: 移除成功
            False: 股票不存在
        """
        if code not in self.watchlist:
            logger.warning(f"{code} 不在观察池中")
            return False
        
        del self.watchlist[code]
        self._save()
        
        logger.info(f"移除股票: {code} ({len(self.watchlist)}/{self.max_size})")
        return True
    
    def update_result(self, code: str, level: int, result: dict):
        """
        更新股票的Level结果
        
        Args:
            code: 股票代码
            level: Level级别 (1, 2, 3)
            result: 结果字典
        """
        if code not in self.watchlist:
            logger.warning(f"{code} 不在观察池中")
            return
        
        item = self.watchlist[code]
        
        if level == 1:
            item.level1_result = result
        elif level == 2:
            item.level2_result = result
        elif level == 3:
            item.level3_result = result
        
        # 更新优先级得分
        item.priority_score = self._calculate_priority(item)
        
        self._save()
        logger.debug(f"{code} Level{level} 结果已更新 (priority={item.priority_score:.2f})")
    
    def get(self, code: str) -> Optional[WatchlistItem]:
        """获取股票信息"""
        return self.watchlist.get(code)
    
    def get_all(self) -> List[WatchlistItem]:
        """获取所有股票（按优先级排序）"""
        items = list(self.watchlist.values())
        items.sort(key=lambda x: x.priority_score, reverse=True)
        return items
    
    def is_full(self) -> bool:
        """检查观察池是否已满"""
        return len(self.watchlist) >= self.max_size
    
    def cleanup_expired(self, days: int = 7):
        """
        清理过期股票
        
        Args:
            days: 过期天数（默认7天）
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        expired_codes = []
        
        for code, item in self.watchlist.items():
            added_time = datetime.fromisoformat(item.added_at)
            
            # 7天内未通过Level3 → 清理
            if added_time < cutoff_time:
                if item.level3_result is None or not item.level3_result.get('passed', False):
                    expired_codes.append(code)
        
        # 执行清理
        for code in expired_codes:
            self.remove(code)
        
        if expired_codes:
            logger.info(f"清理过期股票: {len(expired_codes)} 只")
    
    def _remove_lowest_priority(self):
        """删除最低优先级股票"""
        if not self.watchlist:
            return
        
        # 找到最低优先级
        lowest_code = min(
            self.watchlist.keys(),
            key=lambda code: self.watchlist[code].priority_score
        )
        
        logger.info(f"容量满，删除最低优先级: {lowest_code} (score={self.watchlist[lowest_code].priority_score:.2f})")
        self.remove(lowest_code)
    
    def _calculate_priority(self, item: WatchlistItem) -> float:
        """
        计算优先级得分
        
        公式：
        - Level3得分 × 0.6
        - Level2得分 × 0.3
        - 添加时间 × 0.1 (新加股票优先级高)
        """
        score = 0.0
        
        # Level3得分
        if item.level3_result and item.level3_result.get('passed', False):
            score += item.level3_result.get('comprehensive_score', 0) * 0.6
        
        # Level2得分
        if item.level2_result and item.level2_result.get('passed', False):
            score += item.level2_result.get('fund_flow_score', 0) * 0.3
        
        # 添加时间得分（越新越高）
        try:
            added_time = datetime.fromisoformat(item.added_at)
            days_ago = (datetime.now() - added_time).days
            time_score = max(0, 100 - days_ago * 10)  # 每天-10分
            score += time_score * 0.1
        except:
            pass
        
        return score
    
    def _load(self):
        """从文件加载观察池"""
        if not self.storage_path.exists():
            logger.debug(f"观察池文件不存在: {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for code, item_data in data.items():
                self.watchlist[code] = WatchlistItem(**item_data)
            
            logger.info(f"加载观察池: {len(self.watchlist)} 只股票")
        
        except Exception as e:
            logger.error(f"加载观察池失败: {e}")
    
    def _save(self):
        """保存观察池到文件"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                code: asdict(item)
                for code, item in self.watchlist.items()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"保存观察池失败: {e}")
