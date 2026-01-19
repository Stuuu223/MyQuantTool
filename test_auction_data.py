"""
测试竞价期间数据获取
"""

import time
from datetime import datetime
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_auction_data():
    """测试竞价期间数据获取"""
    print("=" * 80)
    print("🧪 测试竞价期间数据获取")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    db = DataManager()

    # 测试股票列表
    test_stocks = ['000001', '000002', '600000', '600519', '300750']

    print(f"\n🔍 测试获取 {len(test_stocks)} 只股票的实时数据...")

    t_start = time.time()
    realtime_data = db.get_fast_price(test_stocks)
    t_cost = time.time() - t_start

    print(f"\n📊 获取结果:")
    print(f"  - 耗时: {t_cost:.3f}秒")
    print(f"  - 返回数据: {len(realtime_data)} 只股票")

    if realtime_data:
        print(f"\n📋 详细数据:")
        for stock_code, data in realtime_data.items():
            print(f"\n  {stock_code}:")
            print(f"    - now: {data.get('now', 0)}")
            print(f"    - close: {data.get('close', 0)}")
            print(f"    - volume: {data.get('volume', 0)}")
            print(f"    - amount: {data.get('amount', 0)}")
            print(f"    - change_percent: {data.get('change_percent', 0)}")
            print(f"    - bid1: {data.get('bid1', 0)}")
            print(f"    - ask1: {data.get('ask1', 0)}")
            print(f"    - bid1_volume: {data.get('bid1_volume', 0)}")
            print(f"    - ask1_volume: {data.get('ask1_volume', 0)}")

    # 测试单只股票
    print(f"\n🔍 测试单只股票详细数据...")
    test_code = test_stocks[0]

    t_start = time.time()
    single_data = db.get_realtime_data(test_code)
    t_cost = time.time() - t_start

    print(f"\n📊 单只股票数据 ({test_code}):")
    print(f"  - 耗时: {t_cost:.3f}秒")
    print(f"  - 数据: {single_data}")

    # 测试 Easyquotation 直接获取
    print(f"\n🔍 测试 Easyquotation 直接获取...")
    if db.quotation:
        t_start = time.time()
        eq_data = db.quotation.stocks(test_stocks)
        t_cost = time.time() - t_start

        print(f"\n📊 Easyquotation 数据:")
        print(f"  - 耗时: {t_cost:.3f}秒")
        print(f"  - 返回数据: {len(eq_data)} 只股票")

        if eq_data:
            for code, data in list(eq_data.items())[:2]:
                print(f"\n  {code}:")
                print(f"    - 数据: {data}")
    else:
        print(f"  ⚠️  Easyquotation 未初始化")


if __name__ == '__main__':
    try:
        test_auction_data()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()