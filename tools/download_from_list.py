#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从股票列表文件下载 QMT 分钟数据（迁移到TickProvider）

配合 get_hot_stocks.py 使用：
1. 首先运行 get_hot_stocks.py 生成股票列表
2. 然后运行本脚本下载这些股票的分钟数据

使用TickProvider统一封装类，不再直接导入xtdata

Author: MyQuantTool Team
Date: 2026-02-19 (T4迁移)
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import pandas as pd

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 🔥 T4迁移：不再直接导入xtdata，改用TickProvider
# from xtquant import xtdata
from logic.data_providers.tick_provider import TickProvider, DownloadStatus


def load_stock_list(file_path: str) -> List[str]:
    """从文件加载股票列表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        codes = [line.strip() for line in f if line.strip()]
    return codes


def download_stocks(
    codes: List[str],
    days: int = 30,
    output_dir: str = 'data/minute_data/1m'
):
    """下载股票分钟数据（使用TickProvider）"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 开始下载 {len(codes)} 只股票的分钟数据")
    print(f"   时间范围: 最近 {days} 天")
    print(f"   输出目录: {output_path}")
    print(f"   使用TickProvider统一封装类")
    
    # 计算时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_time_str = start_date.strftime('%Y%m%d') + "000000"
    end_time_str = end_date.strftime('%Y%m%d') + "235959"
    
    # 🔥 T4迁移：使用TickProvider
    with TickProvider() as provider:
        if not provider.is_connected():
            print("❌ QMT 连接失败")
            return
        
        print("✅ QMT 连接成功")
        
        success_count = 0
        failed_codes = []
        
        start_time = time.time()
        
        for idx, code in enumerate(codes):
            # 进度显示
            sys.stdout.write(f"\r   🚀 [{idx+1}/{len(codes)}] 下载 {code}...")
            sys.stdout.flush()
            
            try:
                # 1. 使用TickProvider下载数据
                result = provider.download_minute_data(
                    stock_codes=code,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    period='1m'
                )
                
                if result.success > 0:
                    # 2. 读取数据（使用provider内部的xtdata）
                    # 注意：这里需要直接访问xtdata来读取数据，因为我们已经封装了它
                    data = provider._xtdata.get_market_data_ex(
                        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                        stock_list=[code],
                        period='1m',
                        count=days * 240,
                        fill_data=False
                    )
                    
                    if code in data and len(data[code]) > 0:
                        df = data[code]
                        
                        # 转换时间
                        if 'time' in df.columns:
                            df['time_str'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                        else:
                            df['time_str'] = df.index
                            df['time_str'] = pd.to_datetime(df['time_str'], unit='ms') + pd.Timedelta(hours=8)

                        # 保存
                        file_path = output_path / f"{code}_1m.csv"
                        df.to_csv(file_path, index=False, encoding='utf-8-sig')
                        success_count += 1
                    else:
                        failed_codes.append(code)
                else:
                    failed_codes.append(code)
                    
            except Exception as e:
                failed_codes.append(code)
                print(f"\n   ⚠️  {code} 出错: {e}")
        
        elapsed = time.time() - start_time
        
        print(f"\n\n🏁 下载完成: {success_count}/{len(codes)} 成功")
        print(f"   耗时: {elapsed:.1f}s")
        
        if failed_codes:
            print(f"\n⚠️  失败的股票 ({len(failed_codes)}):")        
            for code in failed_codes[:10]:
                print(f"   - {code}")
            if len(failed_codes) > 10:
                print(f"   ... 还有 {len(failed_codes) - 10} 只")


def main():
    parser = argparse.ArgumentParser(description='从股票列表文件下载 QMT 分钟数据（TickProvider版）')
    parser.add_argument('--list', type=str, required=True,
                        help='股票列表文件路径（每行一个代码）')
    parser.add_argument('--days', type=int, default=30,
                        help='下载天数（默认30）')
    parser.add_argument('--output', type=str, default='data/minute_data/1m',
                        help='输出目录')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 QMT 分钟数据下载器 - TickProvider版")
    print("=" * 60)
    print("🔧 使用TickProvider统一封装类")
    
    # 加载股票列表
    print(f"\n📝 加载股票列表: {args.list}")
    codes = load_stock_list(args.list)
    print(f"   共 {len(codes)} 只股票")
    
    # 下载数据
    download_stocks(codes, days=args.days, output_dir=args.output)
    
    print("\n" + "=" * 60)
    print("✅ 完成！现在可以运行回测：")
    print(f"   python tools/run_backtest_1m.py --data-dir {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
