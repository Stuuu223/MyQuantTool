#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出事件记录脚本

功能：
1. 导出事件记录为Excel表格
2. 显示事件统计信息
3. 按事件类型、股票代码、日期筛选

Author: iFlow CLI
Version: V2.0
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.event_recorder import get_event_recorder
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("📊 导出事件记录")
    print("=" * 80)
    
    # 获取事件记录器
    recorder = get_event_recorder()
    
    # 显示统计信息
    recorder.print_statistics()
    
    # 导出为Excel
    print("\n📋 导出Excel表格...")
    try:
        recorder.export_to_excel("data/event_records.xlsx")
        print("✅ Excel表格已导出到: data/event_records.xlsx")
    except Exception as e:
        print(f"❌ 导出Excel失败: {e}")
        print("   提示: 需要安装 pandas 和 openpyxl")
        print("   安装命令: pip install pandas openpyxl")
    
    # 导出为CSV（备用）
    print("\n📋 导出CSV表格...")
    try:
        recorder.export_to_csv("data/event_records.csv")
        print("✅ CSV表格已导出到: data/event_records.csv")
    except Exception as e:
        print(f"❌ 导出CSV失败: {e}")
    
    # 显示最近的记录
    print("\n📋 最近的10条记录:")
    print("-" * 80)
    records = recorder.get_records(limit=10)
    
    if records:
        print(f"{'时间':<20} {'股票代码':<12} {'事件类型':<20} {'描述':<30}")
        print("-" * 80)
        for record in records:
            event_time = record.event_time[:19]  # 只显示到秒
            print(f"{event_time:<20} {record.stock_code:<12} {record.event_type:<20} {record.description[:30]}")
    else:
        print("   暂无记录")
    
    print("-" * 80)
    print("\n" + "=" * 80)
    print("✅ 导出完成！")
    print("=" * 80)
    print("\n下一步：")
    print("1. 打开 data/event_records.xlsx 查看详细数据")
    print("2. 使用Excel的筛选功能分析事件")
    print("3. 统计每种事件的胜率和收益")
    print("=" * 80 + "\n")
    
    # 关闭数据库连接
    recorder.close()


if __name__ == "__main__":
    main()