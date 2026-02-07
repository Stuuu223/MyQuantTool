"""
数据迁移脚本:给历史快照补充 trade_date 字段
运行方式: python tasks/migrate_add_trade_date.py
"""

import json
from pathlib import Path
from datetime import datetime

def migrate_snapshots():
    """给历史快照补充 trade_date 字段"""
    scan_dir = Path("data/scan_results")
    
    if not scan_dir.exists():
        print(f"❌ 目录不存在: {scan_dir}")
        return
    
    snapshot_files = list(scan_dir.glob("*_intraday.json"))
    
    if not snapshot_files:
        print(f"⚠️  未找到快照文件 (格式: *_intraday.json)")
        return
    
    print(f"📂 找到 {len(snapshot_files)} 个快照文件")
    
    updated_count = 0
    
    for snapshot_file in snapshot_files:
        print(f"\n处理: {snapshot_file.name}")
        
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ 读取失败: {e}")
            continue
        
        # 从文件名提取日期: 2026-02-06_094521_intraday.json
        try:
            file_date = snapshot_file.stem.split('_')[0]  # "2026-02-06"
            trade_date = file_date.replace("-", "")  # "20260206"
            print(f"  提取日期: {file_date} → {trade_date}")
        except Exception as e:
            print(f"❌ 日期提取失败: {e}")
            continue
        
        # 给每个机会添加 trade_date
        modified = False
        
        # 修改为 results.opportunities
        results = data.get("results", {})
        opportunities = results.get("opportunities", [])
        
        for item in opportunities:
            if "trade_date" not in item:
                item["trade_date"] = trade_date
                modified = True
        
        # 保存
        if modified:
            try:
                with open(snapshot_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  ✅ 已更新")
                updated_count += 1
            except Exception as e:
                print(f"  ❌ 保存失败: {e}")
        else:
            print(f"  ⏭️  已包含 trade_date,跳过")
    
    print(f"\n{'='*60}")
    print(f"✅ 迁移完成: 更新了 {updated_count}/{len(snapshot_files)} 个文件")

if __name__ == "__main__":
    print("=" * 60)
    print("数据迁移工具: 给历史快照补充 trade_date 字段")
    print("=" * 60)
    migrate_snapshots()
