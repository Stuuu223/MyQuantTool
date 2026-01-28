# -*- coding: utf-8 -*-
"""
QMT 连接快速测试脚本

使用方法：
    python test_qmt_connection.py

Author: iFlow CLI
Date: 2026-01-28
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_basic_connection():
    """基础连接测试"""
    print("=" * 60)
    print("🧪 QMT 基础连接测试")
    print("=" * 60)

    try:
        # 导入模块
        print("\n1️⃣  导入 xtdata 模块...")
        from xtquant import xtdata
        print("   ✅ 导入成功")

        # 测试获取股票列表
        print("\n2️⃣  获取沪深A股股票列表...")
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
        if stock_list:
            print(f"   ✅ 成功获取 {len(stock_list)} 只股票")
            print(f"   示例股票: {stock_list[:5]}")
        else:
            print("   ⚠️  未获取到股票列表")

        # 测试获取tick数据
        print("\n3️⃣  测试获取tick数据...")
        if stock_list and len(stock_list) > 0:
            test_stock = stock_list[0]
            tick_data = xtdata.get_full_tick([test_stock])
            if tick_data and test_stock in tick_data:
                print(f"   ✅ 成功获取 {test_stock} 的tick数据")
                print(f"   最新价: {tick_data[test_stock].get('lastPrice', 'N/A')}")
            else:
                print(f"   ⚠️  {test_stock} 的tick数据为空（可能需要先下载数据或等待开盘）")

        print("\n" + "=" * 60)
        print("✅ QMT 基础连接测试完成")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_basic_connection()