# -*- coding: utf-8 -*-
"""
QMT 活跃股筛选器测试
验证 QMT 数据获取和功能
"""
import sys
import os

# 确保能找到项目路径
sys.path.append(os.getcwd())

from logic.active_stock_filter import get_active_stocks
from logic.logger import get_logger

logger = get_logger(__name__)


def test_qmt_active_filter():
    """测试 QMT 活跃股筛选器"""
    print(">>> 🚀 启动 QMT 活跃股筛选器测试...")

    try:
        # 获取活跃股（使用 QMT）
        print(">>> 📡 正在使用 QMT 获取活跃股票...")
        active_stocks = get_active_stocks(
            limit=10,  # 只取10只进行测试
            sort_by='amount',
            min_change_pct=None,
            max_change_pct=None,
            exclude_st=True,
            exclude_delisting=True,
            min_volume=0,
            skip_top=0,
            min_amplitude=0,
            only_20cm=False
        )

        if not active_stocks:
            print(">>> ❌ 未获取到活跃股票")
            return

        print(f">>> ✅ 成功获取 {len(active_stocks)} 只活跃股票")
        print("-" * 80)
        print(f"{'代码':<10} {'名称':<10} {'最新价':<10} {'涨跌幅%':<10} {'成交量(手)':<15} {'成交额(万)':<15}")
        print("-" * 80)

        for stock in active_stocks:
            code = stock.get('代码', stock.get('code', ''))
            name = stock.get('名称', stock.get('name', ''))
            price = stock.get('最新价', stock.get('price', 0))
            change_pct = stock.get('涨跌幅', stock.get('change_pct', 0)) * 100
            volume = stock.get('成交量', stock.get('volume', 0))
            amount = stock.get('成交额', stock.get('amount', 0))

            print(f"{code:<10} {name:<10} {price:<10.2f} {change_pct:<10.2f} {volume:<15.0f} {amount:<15.0f}")

        print("-" * 80)
        print(">>> ✅ 测试完成！")

        # 检查字段兼容性
        print("\n>>> 🔍 检查字段兼容性...")
        if active_stocks:
            sample = active_stocks[0]
            required_cn_fields = ['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额']
            required_en_fields = ['code', 'name', 'price', 'change_pct', 'volume', 'amount']

            missing_cn = [f for f in required_cn_fields if f not in sample]
            missing_en = [f for f in required_en_fields if f not in sample]

            if missing_cn:
                print(f"⚠️ 缺少中文字段: {', '.join(missing_cn)}")
            else:
                print(f"✅ 所有中文字段都存在")

            if missing_en:
                print(f"⚠️ 缺少英文字段: {', '.join(missing_en)}")
            else:
                print(f"✅ 所有英文字段都存在")

        print("\n>>> 💡 总结：")
        print(">>>    如果获取到数据，说明 QMT 活跃股筛选器工作正常")
        print(">>>    如果字段兼容性检查通过，说明数据格式与系统兼容")
        print(">>>    这样就彻底消灭了数据异构问题！")

    except Exception as e:
        print(f">>> ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 80)
    print("QMT 活跃股筛选器测试 - V19.17")
    print("=" * 80)

    test_qmt_active_filter()

    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)