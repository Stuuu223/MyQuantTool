"""
测试Redis修复验证脚本
验证save_limit_up_pool_to_redis和get_limit_up_pool_from_redis是否正常工作
"""

from logic.market_cycle import MarketCycleManager
from logic.logger import get_logger

logger = get_logger(__name__)

def test_redis_save_and_load():
    """测试Redis保存和加载功能"""
    print("=" * 60)
    print("🧪 测试Redis保存和加载功能")
    print("=" * 60)

    # 创建市场周期管理器
    cycle_manager = MarketCycleManager()

    # 测试数据
    test_stocks = [
        {'code': '000001', 'name': '平安银行', 'price': 12.34, 'change_pct': 10.00},
        {'code': '000002', 'name': '万科A', 'price': 23.45, 'change_pct': 10.01},
        {'code': '300606', 'name': '金太阳', 'price': 34.56, 'change_pct': 9.99},
    ]

    print(f"\n📝 测试数据：{len(test_stocks)}只股票")
    for stock in test_stocks:
        print(f"  - {stock['code']} {stock['name']} {stock['price']}元 {stock['change_pct']}%")

    # 测试保存
    print("\n💾 测试保存到Redis...")
    save_result = cycle_manager.save_limit_up_pool_to_redis(test_stocks)
    if save_result:
        print("✅ 保存成功")
    else:
        print("❌ 保存失败")
        return False

    # 测试加载
    print("\n📖 测试从Redis加载...")
    # 加载今天的数据，而不是昨天的数据
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    loaded_codes = cycle_manager.get_limit_up_pool_from_redis(today)
    if loaded_codes:
        print(f"✅ 加载成功，共{len(loaded_codes)}只股票")
        print(f"  股票代码：{loaded_codes}")
    else:
        print("❌ 加载失败")
        return False

    # 验证数据一致性
    print("\n🔍 验证数据一致性...")
    expected_codes = [stock['code'] for stock in test_stocks]
    if set(loaded_codes) == set(expected_codes):
        print("✅ 数据一致")
    else:
        print("❌ 数据不一致")
        print(f"  期望：{expected_codes}")
        print(f"  实际：{loaded_codes}")
        return False

    # 测试Redis连接状态
    print("\n🔌 检查Redis连接状态...")
    if cycle_manager.db._redis_client:
        print("✅ Redis客户端已初始化")
        # 测试ping
        try:
            cycle_manager.db._redis_client.ping()
            print("✅ Redis连接正常")
        except Exception as e:
            print(f"❌ Redis连接异常：{e}")
            return False
    else:
        print("❌ Redis客户端未初始化")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_redis_save_and_load()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
        exit(1)