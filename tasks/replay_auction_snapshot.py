#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照回放器 (Phase3 第1周)

功能：
1. 回放历史竞价快照数据
2. 检测竞价诱多模式
3. 统计检测结果

使用方法：
    # 回放指定日期的竞价快照
    python tasks/replay_auction_snapshot.py --date 2026-02-10

    # 回放并检测诱多
    python tasks/replay_auction_snapshot.py --date 2026-02-10 --detect

    # 筛选高开股票
    python tasks/replay_auction_snapshot.py --date 2026-02-10 --filter high_open
"""

import sys
import os
import json
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from tabulate import tabulate

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.auction_trap_detector import AuctionTrapDetector, TrapType, RiskLevel

logger = get_logger(__name__)


class AuctionSnapshotReplayer:
    """
    竞价快照回放器

    回放历史竞价快照，验证竞价异动有效性
    """

    def __init__(self, db_path: str = None):
        """
        初始化回放器

        Args:
            db_path: SQLite数据库路径
        """
        # 数据库路径
        if db_path is None:
            db_path = project_root / "data" / "auction_snapshots.db"
        else:
            db_path = Path(db_path)

        if not db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")

        self.db_path = str(db_path)
        self.detector = AuctionTrapDetector()

        logger.info(f"竞价快照回放器初始化成功")
        logger.info(f"数据库路径: {self.db_path}")

    def load_auction_snapshots(self, date: str, filter_condition: str = 'all') -> List[Dict[str, Any]]:
        """
        加载竞价快照数据

        Args:
            date: 日期（格式：YYYY-MM-DD）
            filter_condition: 筛选条件（all, high_open, low_open, high_volume）

        Returns:
            竞价快照列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 构建查询条件
            if filter_condition == 'high_open':
                where_clause = "AND auction_change > 0.03"
            elif filter_condition == 'low_open':
                where_clause = "AND auction_change < -0.03"
            elif filter_condition == 'high_volume':
                where_clause = "AND volume_ratio > 2.0"
            else:
                where_clause = ""

            # 查询竞价快照
            query = f"""
                SELECT * FROM auction_snapshots
                WHERE date = ?
                {where_clause}
                ORDER BY auction_change DESC
            """

            cursor.execute(query, (date,))
            rows = cursor.fetchall()
            conn.close()

            # 转换为字典列表
            snapshots = []
            for row in rows:
                snapshots.append({
                    'code': row['code'],
                    'name': row['name'],
                    'auction_price': row['auction_price'],
                    'prev_close': row['auction_price'] / (1 + row['auction_change']),
                    'auction_change': row['auction_change'],
                    'auction_volume': row['auction_volume'],
                    'auction_amount': row['auction_amount'],
                    'volume_ratio': row['volume_ratio'],
                    'buy_orders': row['buy_orders'],
                    'sell_orders': row['sell_orders'],
                    'timestamp': row['auction_time']
                })

            logger.info(f"加载了 {len(snapshots)} 个竞价快照（筛选条件: {filter_condition}）")
            return snapshots

        except Exception as e:
            logger.error(f"加载竞价快照失败: {e}")
            return []

    def get_open_5min_data(self, code: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取开盘5分钟数据（优先使用CSV文件）

        Args:
            code: 股票代码
            date: 日期

        Returns:
            开盘5分钟数据
        """
        try:
            import pandas as pd

            # 优先方案1：从CSV文件读取（已下载的历史数据）
            csv_path = project_root / "data" / "minute_data" / f"{code}_1m.csv"

            if csv_path.exists():
                df = pd.read_csv(csv_path)

                # 筛选指定日期的数据
                df['date_str'] = df['time_str'].str.split(' ').str[0]
                df_date = df[df['date_str'] == date]

                if not df_date.empty:
                    # 获取开盘前5分钟的数据（09:30-09:35）
                    df_5min = df_date[df_date['time_str'].str.contains('09:3[0-4]')].head(5)

                    if len(df_5min) >= 1:
                        open_price = df_5min['open'].iloc[0]
                        high_5min = df_5min['high'].max()
                        low_5min = df_5min['low'].min()
                        close_5min = df_5min['close'].iloc[-1]
                        volume_5min = df_5min['volume'].sum()

                        # 计算尾盘回落
                        tail_drop = (high_5min - close_5min) / high_5min if high_5min > 0 else 0

                        return {
                            'code': code,
                            'open_price': open_price,
                            'high_5min': high_5min,
                            'low_5min': low_5min,
                            'close_5min': close_5min,
                            'volume_5min': volume_5min,
                            'tail_drop': tail_drop,
                            'timestamp': f"{date} 09:35:00"
                        }

            # 备用方案2：从QMT获取
            try:
                import xtquant.xtdata as xtdata

                date_num = date.replace('-', '')
                kline = xtdata.get_local_data(
                    field_list=['open', 'high', 'low', 'close', 'volume'],
                    stock_list=[code],
                    period='1m',
                    start_time=date_num,
                    end_time=date_num,
                    count=-1
                )

                if kline and code in kline:
                    data = kline[code]
                    if len(data) >= 1:
                        data_5min = data.head(5)

                        open_price = data_5min['open'].iloc[0]
                        high_5min = data_5min['high'].max()
                        low_5min = data_5min['low'].min()
                        close_5min = data_5min['close'].iloc[-1]
                        volume_5min = data_5min['volume'].sum()

                        tail_drop = (high_5min - close_5min) / high_5min if high_5min > 0 else 0

                        return {
                            'code': code,
                            'open_price': open_price,
                            'high_5min': high_5min,
                            'low_5min': low_5min,
                            'close_5min': close_5min,
                            'volume_5min': volume_5min,
                            'tail_drop': tail_drop,
                            'timestamp': f"{date_num} 09:35:00"
                        }
            except Exception as e:
                logger.debug(f"QMT获取失败: {e}")

        except Exception as e:
            logger.error(f"获取开盘数据失败 {code}: {e}")

        return None

    def replay_with_detection(self, date: str, filter_condition: str = 'all',
                            top_n: int = None) -> List[Dict[str, Any]]:
        """
        回放竞价快照并检测诱多

        Args:
            date: 日期
            filter_condition: 筛选条件
            top_n: 只处理前n个（默认全部）

        Returns:
            检测结果列表
        """
        # 加载竞价快照
        auction_snapshots = self.load_auction_snapshots(date, filter_condition)

        if not auction_snapshots:
            logger.warning(f"未找到 {date} 的竞价快照")
            return []

        # 限制数量
        if top_n:
            auction_snapshots = auction_snapshots[:top_n]

        logger.info(f"开始回放 {len(auction_snapshots)} 个竞价快照...")

        # 检测结果
        results = []

        for i, auction_data in enumerate(auction_snapshots, 1):
            code = auction_data['code']

            # 获取开盘5分钟数据
            open_data = self.get_open_5min_data(code, date)

            if open_data:
                # 检测诱多
                result = self.detector.detect(auction_data, open_data)

                if result:
                    results.append(result)

            # 进度提示
            if i % 100 == 0 or i == len(auction_snapshots):
                logger.info(f"进度: {i}/{len(auction_snapshots)} ({i/len(auction_snapshots)*100:.1f}%)")

        logger.info(f"回放完成 - 检测到 {len(results)} 个诱多")
        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """
        生成检测报告

        Args:
            results: 检测结果列表

        Returns:
            报告字符串
        """
        if not results:
            return "没有检测到诱多模式"

        # 统计
        trap_counts = {}
        for r in results:
            trap_type = r.trap_type.value
            trap_counts[trap_type] = trap_counts.get(trap_type, 0) + 1

        # 表格数据
        table_data = []
        for r in results[:50]:  # 只显示前50个
            table_data.append([
                r.code,
                r.name,
                f"{r.auction_change*100:.2f}%",
                f"{r.open_change*100:.2f}%",
                f"{r.volume_ratio:.1f}x",
                f"{r.tail_drop*100:.2f}%",
                r.trap_type.value,
                r.risk_level.value,
                f"{r.confidence*100:.0f}%",
                ", ".join(r.signals) if r.signals else "正常"
            ])

        # 报告
        report = []
        report.append("=" * 100)
        report.append("竞价诱多检测结果")
        report.append("=" * 100)
        report.append(f"诱多数: {len(results)}")
        report.append(f"诱多率: {len(results)/len(results)*100:.1f}%")
        report.append("")
        report.append("诱多类型分布：")
        for trap_type, count in trap_counts.items():
            report.append(f"  {trap_type}: {count} ({count/len(results)*100:.1f}%)")
        report.append("")
        report.append("=" * 100)

        if table_data:
            report.append(tabulate(
                table_data,
                headers=['代码', '名称', '竞价涨幅', '开盘涨幅', '量比', '尾盘回落', '诱多类型', '风险级别', '置信度', '信号'],
                tablefmt='grid',
                stralign='left'
            ))

        return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='竞价快照回放脚本')
    parser.add_argument('--date', type=str, required=True, help='回放日期（格式：YYYY-MM-DD）')
    parser.add_argument('--filter', type=str, default='all',
                       help='筛选条件（all, high_open, low_open, high_volume）')
    parser.add_argument('--detect', action='store_true', help='检测诱多')
    parser.add_argument('--top', type=int, help='只处理前n个')

    args = parser.parse_args()

    # 初始化回放器
    replayer = AuctionSnapshotReplayer()

    # 回放
    if args.detect:
        results = replayer.replay_with_detection(args.date, args.filter, args.top)

        # 显示报告
        report = replayer.generate_report(results)
        logger.info(f"\n{report}")
    else:
        # 只回放不检测
        snapshots = replayer.load_auction_snapshots(args.date, args.filter)

        if snapshots:
            logger.info(f"\n回放了 {len(snapshots)} 个竞价快照")

            # 显示前10个
            table_data = []
            for s in snapshots[:10]:
                table_data.append([
                    s['code'],
                    s['name'],
                    f"{s['auction_change']*100:.2f}%",
                    f"{s['volume_ratio']:.1f}x"
                ])

            print(tabulate(
                table_data,
                headers=['代码', '名称', '竞价涨幅', '量比'],
                tablefmt='grid'
            ))
        else:
            logger.warning("没有找到竞价快照")


if __name__ == "__main__":
    main()