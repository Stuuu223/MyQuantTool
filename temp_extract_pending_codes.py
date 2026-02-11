#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从2026-02-06快照中提取待同步股票列表
"""
import json
import os
from pathlib import Path

def extract_pending_codes():
    """从快照中提取股票代码"""
    scan_results_dir = Path("data/scan_results")
    
    # 获取所有2026-02-06的快照文件
    snapshot_files = list(scan_results_dir.glob("2026-02-06_*_intraday.json"))
    
    if not snapshot_files:
        print("❌ 未找到2026-02-06的快照文件")
        return
    
    print(f"✅ 找到 {len(snapshot_files)} 个快照文件")
    
    # 收集所有股票代码
    all_codes = set()
    
    for snapshot_file in snapshot_files:
        print(f"  处理: {snapshot_file.name}")
        
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取机会池代码
            opportunities = data.get('results', {}).get('opportunities', [])
            for item in opportunities:
                code = item.get('code')
                if code:
                    all_codes.add(code)
            
            # 提取观察池代码
            watchlist = data.get('results', {}).get('watchlist', [])
            for item in watchlist:
                code = item.get('code')
                if code:
                    all_codes.add(code)
        
        except Exception as e:
            print(f"  ⚠️  处理失败: {e}")
    
    print(f"\n✅ 提取完成，共 {len(all_codes)} 只股票")
    
    # 写入文件
    output_file = "pending_equity_codes_20260206.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for code in sorted(all_codes):
            f.write(f"{code}\n")
    
    print(f"✅ 已写入: {output_file}")
    
    # 显示部分代码
    print(f"\n前10个股票代码:")
    for i, code in enumerate(sorted(all_codes)[:10]):
        print(f"  {i+1}. {code}")
    
    if len(all_codes) > 10:
        print(f"  ... 还有 {len(all_codes) - 10} 只")
    
    return list(all_codes)

if __name__ == "__main__":
    extract_pending_codes()
