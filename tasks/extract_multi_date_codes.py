"""
Extract stock codes from multiple date snapshots, deduplicate and aggregate
"""
import json
import os
from pathlib import Path
from typing import Set
from datetime import datetime

def extract_codes_from_snapshot(file_path: str) -> Set[str]:
    """从单个快照文件中提取股票代码"""
    codes = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 快照文件结构: { "results": { "opportunities": [...], "watchlist": [...], "blacklist": [...] } }
        if isinstance(data, dict):
            results = data.get('results', {})
            if isinstance(results, dict):
                # 提取 opportunities, watchlist, blacklist 中的股票代码
                for pool in ['opportunities', 'watchlist', 'blacklist']:
                    stocks = results.get(pool, [])
                    if isinstance(stocks, list):
                        for stock in stocks:
                            if isinstance(stock, dict):
                                code = stock.get('code') or stock.get('ts_code')
                                if code:
                                    codes.add(code)
    except Exception as e:
        print(f"  ⚠️ 读取失败 {file_path}: {e}")

    return codes

def extract_codes_from_date(scan_results_dir: str, date_str: str) -> Set[str]:
    """提取指定日期所有快照的股票代码"""
    date_codes = set()
    date_path = Path(scan_results_dir)

    # 查找该日期的所有快照文件
    pattern = f"{date_str}*.json"
    snapshot_files = list(date_path.glob(pattern))

    print(f"\n📅 {date_str}:")
    print(f"  找到 {len(snapshot_files)} 个快照文件")

    for file_path in snapshot_files:
        file_codes = extract_codes_from_snapshot(str(file_path))
        date_codes.update(file_codes)
        print(f"  - {file_path.name}: {len(file_codes)} 只股票")

    return date_codes

def main():
    scan_results_dir = "data/scan_results"

    # 要处理的日期列表
    dates = ["2026-02-05", "2026-02-06"]

    all_codes = set()
    date_codes_map = {}

    print("=" * 70)
    print("提取多日快照股票代码")
    print("=" * 70)

    for date_str in dates:
        date_codes = extract_codes_from_date(scan_results_dir, date_str)
        date_codes_map[date_str] = date_codes
        all_codes.update(date_codes)
        print(f"  ✅ {date_str} 合计: {len(date_codes)} 只股票")

    print("\n" + "=" * 70)
    print("汇总结果")
    print("=" * 70)
    print(f"所有去重股票数: {len(all_codes)}")

    # 保存汇总代码
    output_file = "pending_equity_codes_multi_date.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for code in sorted(all_codes):
            f.write(code + '\n')

    print(f"✅ 保存到: {output_file}")

    # 保存每个日期的代码数
    summary_file = "pending_equity_codes_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"日期范围: {dates[0]} ~ {dates[-1]}\n")
        f.write(f"总股票数: {len(all_codes)}\n\n")
        for date_str, codes in date_codes_map.items():
            f.write(f"{date_str}: {len(codes)} 只股票\n")

    print(f"✅ 保存统计到: {summary_file}")

if __name__ == "__main__":
    main()