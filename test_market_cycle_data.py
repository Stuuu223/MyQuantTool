"""
测试市场周期数据获取

用于调试市场天气显示数据为0的问题
"""

import sys
from datetime import datetime

def test_market_cycle_data():
    """测试市场周期数据获取"""
    print("=" * 60)
    print("市场周期数据获取测试")
    print("=" * 60)
    print()
    
    # 1. 测试 DataManager
    print("[1/4] 测试 DataManager...")
    try:
        from logic.data_manager import DataManager
        db = DataManager()
        print("✅ DataManager 初始化成功")
    except Exception as e:
        print(f"❌ DataManager 初始化失败: {e}")
        return False
    print()
    
    # 2. 测试获取股票列表
    print("[2/4] 测试获取股票列表...")
    try:
        import akshare as ak
        stock_list_df = ak.stock_info_a_code_name()
        stock_list = stock_list_df['code'].tolist()
        print(f"✅ 获取股票列表成功，共 {len(stock_list)} 只股票")
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return False
    print()
    
    # 3. 测试获取实时数据
    print("[3/4] 测试获取实时数据...")
    try:
        # 只测试前100只股票
        test_stock_list = stock_list[:100]
        realtime_data = db.get_fast_price(test_stock_list)
        print(f"✅ 获取实时数据成功，共 {len(realtime_data)} 只股票")
        
        if len(realtime_data) > 0:
            # 显示第一只股票的数据
            first_code = list(realtime_data.keys())[0]
            first_data = realtime_data[first_code]
            print(f"   示例数据 ({first_code}):")
            print(f"   - 名称: {first_data.get('name', 'N/A')}")
            print(f"   - 最新价: {first_data.get('now', 0)}")
            print(f"   - 涨跌幅: {first_data.get('change_pct', 0):.2f}%")
            print(f"   - 涨跌停状态: {first_data.get('limit_status', {})}")
    except Exception as e:
        print(f"❌ 获取实时数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # 4. 测试 MarketCycleManager
    print("[4/4] 测试 MarketCycleManager...")
    try:
        from logic.market_cycle import MarketCycleManager
        cycle_manager = MarketCycleManager()
        
        # 获取市场情绪指标
        indicators = cycle_manager.get_market_emotion()
        print(f"✅ 获取市场情绪指标成功")
        print()
        print("市场情绪指标:")
        print(f"   涨停家数: {indicators.get('limit_up_count', 0)}")
        print(f"   跌停家数: {indicators.get('limit_down_count', 0)}")
        print(f"   最高板: {indicators.get('highest_board', 0)}")
        print(f"   平均溢价: {indicators.get('avg_profit', 0):.2f}%")
        print(f"   炸板率: {indicators.get('burst_rate', 0):.2f}%")
        print(f"   晋级率: {indicators.get('promotion_rate', 0):.2f}%")
        
        # 显示涨停股票列表（前5只）
        limit_up_stocks = indicators.get('limit_up_stocks', [])
        if limit_up_stocks:
            print()
            print(f"涨停股票（前5只）:")
            for i, stock in enumerate(limit_up_stocks[:5]):
                print(f"   {i+1}. {stock.get('name', 'N/A')} ({stock.get('code', 'N/A')}) - {stock.get('change_pct', 0):.2f}%")
        
        # 获取当前周期
        cycle_info = cycle_manager.get_current_phase()
        print()
        print("当前市场周期:")
        print(f"   周期类型: {cycle_info.get('cycle', 'N/A')}")
        print(f"   周期描述: {cycle_info.get('description', 'N/A')}")
        print(f"   策略建议: {cycle_info.get('strategy', 'N/A')}")
        print(f"   风险等级: {cycle_info.get('risk_level', 0)}")
        
    except Exception as e:
        print(f"❌ MarketCycleManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # 5. 诊断问题
    print("=" * 60)
    print("问题诊断")
    print("=" * 60)
    
    limit_up_count = indicators.get('limit_up_count', 0)
    limit_down_count = indicators.get('limit_down_count', 0)
    
    if limit_up_count == 0 and limit_down_count == 0:
        print("❌ 问题：涨停和跌停家数都是 0")
        print()
        print("可能原因：")
        print("1. DataManager.get_fast_price() 返回空数据")
        print("2. DataCleaner.clean_realtime_data() 没有正确处理数据")
        print("3. DataCleaner.check_limit_status() 判断逻辑错误")
        print("4. 当前时间不是交易时间，数据源返回空数据")
        print()
        print("建议：")
        print("1. 检查 Redis 是否运行（如果依赖 Redis）")
        print("2. 检查网络连接")
        print("3. 检查当前时间是否在交易时间内")
        print("4. 查看日志文件获取详细错误信息")
    else:
        print(f"✅ 数据获取正常：涨停 {limit_up_count} 家，跌停 {limit_down_count} 家")
    
    print()
    
    # 6. 显示当前时间
    print("=" * 60)
    print("当前时间")
    print("=" * 60)
    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"星期: {now.strftime('%A')}")
    
    # 判断是否在交易时间内
    current_time = now.time()
    is_trading_time = (
        (current_time >= datetime.strptime("09:30", "%H:%M").time() and
         current_time <= datetime.strptime("11:30", "%H:%M").time()) or
        (current_time >= datetime.strptime("13:00", "%H:%M").time() and
         current_time <= datetime.strptime("15:00", "%H:%M").time())
    )
    
    is_weekday = now.weekday() < 5
    
    print(f"是否交易时间: {'是' if is_trading_time else '否'}")
    print(f"是否工作日: {'是' if is_weekday else '否'}")
    
    if not (is_trading_time and is_weekday):
        print()
        print("⚠️  当前不在交易时间内，数据可能为空或不准确")
    
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_market_cycle_data()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)