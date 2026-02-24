#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全息时间机器数据下载器 - 支持参数
"""

import os
import sys
from datetime import datetime, timedelta
import argparse
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='全息时间机器数据下载器')
    parser.add_argument('--start-date', type=str, required=True, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, required=True, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--output', type=str, default='data/holographic_data', help='输出目录')
    parser.add_argument('--workers', type=int, default=4, help='并发数')
    parser.add_argument('--type', type=str, choices=['tick', 'kline', 'all'], default='tick', help='数据类型')
    
    args = parser.parse_args()
    
    print(f'📅 下载日期范围: {args.start_date} 到 {args.end_date}')
    print(f'💾 输出目录: {args.output}')
    print(f'⚡ 并发数: {args.workers}')
    
    # 实现下载逻辑
    from tools.download_holographic_data import get_universe_for_dates, download_tick_batch
    import json
    
    # 解析日期范围
    start_dt = datetime.strptime(args.start_date, '%Y%m%d')
    end_dt = datetime.strptime(args.end_date, '%Y%m%d')
    
    dates = []
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:  # 工作日
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    print(f'📊 交易日数量: {len(dates)} 天')
    
    # 获取股票池
    print('🔍 获取粗筛股票池...')
    stock_list = get_universe_for_dates(dates[:5])  # 只取前5天获取股票池
    
    if not stock_list:
        print('⚠️ 股票池为空，使用备选方案')
        # 使用当前日期的股票池
        test_date = datetime.now().strftime('%Y%m%d')
        stock_list = get_universe_for_dates([test_date])
    
    if stock_list:
        print(f'✅ 获取到 {len(stock_list)} 只股票')
        
        # 创建输出目录
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        config_path = output_path / 'download_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({
                'start_date': args.start_date,
                'end_date': args.end_date,
                'dates': dates,
                'stocks': stock_list,
                'count': len(stock_list),
                'created_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        print(f'💾 配置已保存: {config_path}')
        
        print(f'🔄 开始下载 {len(stock_list)} 只股票 × {len(dates)} 天的数据...')
        
        results = download_tick_batch(stock_list, dates)
        
        # 保存结果
        result_path = output_path / 'download_results.json'
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump({
                'config': {
                    'start_date': args.start_date,
                    'end_date': args.end_date,
                    'dates_count': len(dates),
                    'stocks_count': len(stock_list)
                },
                'results': results,
                'completed_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print('\n🎉 下载完成!')
        print(f'📈 统计:')
        print(f'   总任务: {results["total"]}')
        print(f'   成功: {results["success"]}')
        print(f'   失败: {results["failed"]}')
        print(f'   跳过: {results["skipped"]}')

if __name__ == '__main__':
    main()