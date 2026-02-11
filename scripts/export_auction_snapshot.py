#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出竞价快照数据到文件

功能：
1. 从Redis读取今日竞价快照数据
2. 导出为JSON格式
3. 按竞价量排序，显示热门股票

使用方法：
    python scripts/export_auction_snapshot.py

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from logic.database_manager import DatabaseManager
from logic.logger import get_logger

logger = get_logger(__name__)


def export_auction_snapshot():
    """导出竞价快照数据"""
    print('=' * 80)
    print('📤 导出竞价快照数据')
    print('=' * 80)

    db_manager = DatabaseManager()
    db_manager._init_redis()

    today = datetime.now().strftime('%Y%m%d')
    pattern = f'auction:{today}:*'

    print(f'\n📅 今日日期: {today}')
    print(f'🔑 查询模式: {pattern}')

    keys = db_manager._redis_client.keys(pattern)

    if not keys:
        print('\n❌ Redis中没有找到竞价快照数据')
        return

    print(f'📊 找到 {len(keys)} 条竞价快照记录')

    # 读取所有数据
    import json

    all_data = []

    print(f'\n📥 正在读取数据...')
    for i, key in enumerate(keys, 1):
        # Redis返回的key可能是bytes或str，需要处理
        if isinstance(key, bytes):
            stock_code = key.decode('utf-8').split(':')[-1]
        else:
            stock_code = str(key).split(':')[-1]

        raw_data = db_manager._redis_client.get(key)

        if raw_data:
            try:
                data = json.loads(raw_data)
                data['stock_code'] = stock_code
                all_data.append(data)
            except Exception as e:
                print(f'   ⚠️ 解析失败 {stock_code}: {e}')

    # 计算总竞价量
    total_volume = sum(item.get('auction_volume', 0) for item in all_data)
    total_amount = sum(item.get('auction_amount', 0) for item in all_data)

    # 按竞价量排序
    sorted_data = sorted(all_data, key=lambda x: x.get('auction_volume', 0), reverse=True)

    print(f'   ✅ 读取完成: {len(all_data)} 条')
    print(f'   📊 总竞价量: {total_volume:,}')
    print(f'   💰 总竞价额: {total_amount:,.2f}')

    # 导出JSON文件
    output_dir = Path('data/scan_results')
    output_dir.mkdir(parents=True, exist_ok=True)

    json_file = output_dir / f'auction_snapshot_{today}.json'

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': today,
            'total_stocks': len(all_data),
            'total_volume': total_volume,
            'total_amount': total_amount,
            'data': sorted_data
        }, f, ensure_ascii=False, indent=2)

    print(f'\n💾 JSON文件已保存: {json_file}')

    # 显示前20名
    print(f'\n📊 竞价量TOP20:')
    print('-' * 80)

    for i, item in enumerate(sorted_data[:20], 1):
        stock_code = item['stock_code']
        last_price = item.get('last_price', 0)
        last_close = item.get('last_close', 0)
        volume = item.get('auction_volume', 0)
        amount = item.get('auction_amount', 0)
        bid_vol = item.get('bid_vol', [])
        ask_vol = item.get('ask_vol', [])

        # 计算涨跌幅
        change_pct = 0
        if last_close > 0:
            change_pct = (last_price - last_close) / last_close * 100

        change_emoji = '🔴' if change_pct > 0 else '🟢' if change_pct < 0 else '⚪'

        print(f'{i:2d}. {stock_code:10s} | 价格: {last_price:7.2f} | 竞价量: {volume:6,} | 涨跌: {change_emoji} {change_pct:+6.2f}%')

    print('-' * 80)

    # 导出CSV文件
    import csv

    csv_file = output_dir / f'auction_snapshot_{today}.csv'

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)

        # 写入表头
        writer.writerow([
            '排名', '股票代码', '最新价', '昨收价', '涨跌幅(%)',
            '竞价量', '竞价额', '买盘', '卖盘', '时间'
        ])

        # 写入数据
        for i, item in enumerate(sorted_data, 1):
            stock_code = item['stock_code']
            last_price = item.get('last_price', 0)
            last_close = item.get('last_close', 0)
            volume = item.get('auction_volume', 0)
            amount = item.get('auction_amount', 0)
            bid_vol = sum(item.get('bid_vol', []))
            ask_vol = sum(item.get('ask_vol', []))
            timestamp = item.get('timestamp', 0)

            change_pct = 0
            if last_close > 0:
                change_pct = (last_price - last_close) / last_close * 100

            time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S') if timestamp else 'N/A'

            writer.writerow([
                i, stock_code, last_price, last_close, f'{change_pct:.2f}',
                volume, f'{amount:.2f}', bid_vol, ask_vol, time_str
            ])

    print(f'💾 CSV文件已保存: {csv_file}')

    print('\n' + '=' * 80)
    print('✅ 导出完成')
    print('=' * 80)


if __name__ == "__main__":
    export_auction_snapshot()