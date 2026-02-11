#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照回放器 (Phase3 第1周)

功能：
1. 回放任意历史日期的竞价快照
2. 结合开盘后5分钟K线数据
3. 自动调用诱多检测器
4. 输出美观的表格报告

使用示例：
    # 回放并检测诱多
    python tasks/replay_auction_snapshot.py --date 2026-02-10 --detect
    
    # 筛选高开股票并检测
    python tasks/replay_auction_snapshot.py --date 2026-02-10 --filter high_open --detect
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.auction_trap_detector import AuctionTrapDetector

logger = get_logger(__name__)


class AuctionSnapshotReplayer:
    """竞价快照回放器"""
    
    def __init__(self, db_path: str = None):
        """初始化回放器"""
        if db_path is None:
            db_path = project_root / "data" / "auction_snapshots.db"
        else:
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
        self.detector = AuctionTrapDetector()
        
        logger.info(f"✅ 竞价快照回放器初始化成功")
        logger.info(f"📁 数据库路径: {self.db_path}")
    
    def load_snapshots(self, date: str) -> List[Dict[str, Any]]:
        """加载指定日期的竞价快照"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT code, name, auction_price, auction_volume, auction_amount,
                       auction_change, volume_ratio, buy_orders, sell_orders,
                       bid_vol_1, ask_vol_1, market_type
                FROM auction_snapshots
                WHERE date = ?
                ORDER BY auction_change DESC
            """, (date,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            snapshots = []
            for row in rows:
                snapshot = dict(zip(columns, row))
                snapshots.append(snapshot)
            
            conn.close()
            
            logger.info(f"✅ 加载了 {len(snapshots)} 条竞价快照 ({date})")
            return snapshots
        
        except Exception as e:
            logger.error(f"❌ 加载竞价快照失败: {e}")
            return []
    
    def filter_snapshots(self, snapshots: List[Dict[str, Any]], filter_type: str = None) -> List[Dict[str, Any]]:
        """筛选竞价快照"""
        if filter_type is None:
            return snapshots
        
        filtered = []
        
        for snapshot in snapshots:
            if filter_type == "high_open":
                # 高开：涨幅>3%
                if snapshot.get('auction_change', 0) > 0.03:
                    filtered.append(snapshot)
            elif filter_type == "low_open":
                # 低开：跌幅< -3%
                if snapshot.get('auction_change', 0) < -0.03:
                    filtered.append(snapshot)
            elif filter_type == "high_volume":
                # 放量：量比>2
                if snapshot.get('volume_ratio', 0) > 2.0:
                    filtered.append(snapshot)
        
        logger.info(f"✅ 筛选后剩余 {len(filtered)} 条 (filter: {filter_type})")
        return filtered
    
    def detect_traps(self, snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测诱多陷阱"""
        results = []
        
        for snapshot in snapshots:
            try:
                # 获取开盘后5分钟K线数据（模拟）
                open_data = self._get_open_data(snapshot['code'], snapshot.get('date'))
                
                # 调用诱多检测器
                result = self.detector.detect(snapshot, open_data)
                
                # 合并结果
                merged_result = {**snapshot, **result}
                results.append(merged_result)
            
            except Exception as e:
                logger.warning(f"⚠️ 检测 {snapshot['code']} 失败: {e}")
        
        # 统计检测结果
        trap_count = sum(1 for r in results if r.get('trap_type') != 'NORMAL')
        logger.info(f"✅ 检测完成 - 总数: {len(results)}, 诱多: {trap_count}")
        
        return results
    
    def _get_open_data(self, code: str, date: str) -> Dict[str, Any]:
        """获取开盘后5分钟K线数据（模拟）"""
        # TODO: 从QMT或AkShare获取真实的开盘K线数据
        # 这里返回模拟数据
        return {
            'code': code,
            'date': date,
            'open_5min_change': 0.01,  # 开盘5分钟涨幅
            'volume_5min': 1000000,
        }
    
    def print_report(self, results: List[Dict[str, Any]], show_traps_only: bool = False):
        """打印报告"""
        if show_traps_only:
            results = [r for r in results if r.get('trap_type') != 'NORMAL']
        
        if not results:
            print("📊 没有数据可显示")
            return
        
        print(f"\n{'='*100}")
        print(f"{'代码':<10} {'名称':<12} {'竞价涨幅':<10} {'量比':<8} {'诱多类型':<20} {'风险级别':<10} {'置信度':<10}")
        print(f"{'='*100}")
        
        for r in results[:20]:  # 只显示前20条
            code = r.get('code', '').split('.')[0]
            name = r.get('name', '')
            change = f"{r.get('auction_change', 0)*100:.2f}%"
            volume_ratio = f"{r.get('volume_ratio', 0):.2f}"
            trap_type = r.get('trap_type', 'NORMAL')
            risk_level = r.get('risk_level', 'UNKNOWN')
            confidence = f"{r.get('confidence', 0)*100:.0f}%"
            
            print(f"{code:<10} {name:<12} {change:<10} {volume_ratio:<8} {trap_type:<20} {risk_level:<10} {confidence:<10}")
        
        print(f"{'='*100}")
        print(f"总计: {len(results)} 条")
        print(f"{'='*100}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='竞价快照回放器')
    parser.add_argument('--date', type=str, help='回放日期（格式：YYYY-MM-DD）')
    parser.add_argument('--filter', type=str, choices=['high_open', 'low_open', 'high_volume'], help='筛选条件')
    parser.add_argument('--detect', action='store_true', help='检测诱多陷阱')
    parser.add_argument('--traps-only', action='store_true', help='只显示诱多结果')
    
    args = parser.parse_args()
    
    # 初始化回放器
    replayer = AuctionSnapshotReplayer()
    
    # 获取日期
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"回放日期: {date}")
    print(f"{'='*60}\n")
    
    # 加载快照
    snapshots = replayer.load_snapshots(date)
    
    if not snapshots:
        logger.error(f"❌ 未找到 {date} 的竞价快照数据")
        return
    
    # 筛选
    if args.filter:
        snapshots = replayer.filter_snapshots(snapshots, args.filter)
    
    # 检测诱多
    if args.detect:
        snapshots = replayer.detect_traps(snapshots)
    
    # 打印报告
    replayer.print_report(snapshots, args.traps_only)


if __name__ == "__main__":
    main()