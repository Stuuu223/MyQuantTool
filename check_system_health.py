"""
系统健康检查脚本
检查 Redis、数据快照、市场状态等
"""

import time
from datetime import datetime
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def check_redis_status():
    """检查 Redis 状态"""
    print("=" * 80)
    print("🔍 检查 Redis 状态")
    print("=" * 80)

    try:
        import subprocess
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        redis_running = 'redis-server.exe' in result.stdout

        if redis_running:
            print("✅ Redis 服务正在运行")
            print(f"   进程信息: {result.stdout.split('redis-server.exe')[1].split('\\n')[0].strip()}")
            return True
        else:
            print("❌ Redis 服务未运行")
            return False
    except Exception as e:
        print(f"❌ 检查 Redis 状态失败: {e}")
        return False


def check_data_snapshot(db):
    """检查数据快照状态"""
    print("\n" + "=" * 80)
    print("📊 检查数据快照状态")
    print("=" * 80)

    try:
        # 测试获取实时数据
        test_stocks = ['000001', '000002', '600000', '600519', '300750']

        print(f"🔍 测试获取 {len(test_stocks)} 只股票的实时数据...")

        t_start = time.time()
        realtime_data = db.get_fast_price(test_stocks)
        t_cost = time.time() - t_start

        # 判断是否在竞价时间（集合竞价：09:15-09:30）
        now = datetime.now()
        current_time = now.time()
        auction_start = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
        auction_end = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        is_auction_time = auction_start <= current_time < auction_end

        success_count = 0
        for stock_code in test_stocks:
            if stock_code in realtime_data:
                data = realtime_data[stock_code]
                if data:
                    # 竞价期间（09:15-09:30）：检查 bid1 或 ask1 是否有数据
                    # 盘中（09:30 以后）：检查 now 是否有数据
                    if is_auction_time:
                        has_data = data.get('bid1', 0) > 0 or data.get('ask1', 0) > 0
                        price = data.get('bid1', 0)
                        status = "竞价" if has_data else "无效"
                    else:
                        has_data = data.get('now', 0) > 0
                        price = data.get('now', 0)
                        status = "盘中" if has_data else "无效"

                    if has_data:
                        success_count += 1
                        print(f"  ✅ {stock_code}: {status} 价格={price:.2f}, 涨幅={data.get('change_percent', 0):.2f}%")
                    else:
                        print(f"  ⚠️  {stock_code}: 数据无效")
                else:
                    print(f"  ⚠️  {stock_code}: 数据为空")
            else:
                print(f"  ❌ {stock_code}: 未获取到数据")

        print(f"\n📈 快照统计:")
        print(f"  - 市场状态: {'竞价期间' if is_auction_time else '盘中'}")
        print(f"  - 成功率: {success_count}/{len(test_stocks)} ({success_count/len(test_stocks)*100:.1f}%)")
        print(f"  - 耗时: {t_cost:.3f}秒")

        if success_count >= len(test_stocks) * 0.8:
            print(f"  ✅ 数据快照正常")
            return True
        else:
            print(f"  ⚠️  数据快照异常，成功率低于 80%")
            return False

    except Exception as e:
        print(f"❌ 检查数据快照失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_market_status(db):
    """检查市场状态"""
    print("\n" + "=" * 80)
    print("🕐 检查市场状态")
    print("=" * 80)

    try:
        now = datetime.now()
        current_time = now.strftime('%H:%M:%S')
        current_date = now.strftime('%Y-%m-%d')

        print(f"📅 当前时间: {current_date} {current_time}")

        # 检查是否为交易日
        is_weekday = now.weekday() < 5  # 0-4 为周一到周五
        print(f"📅 工作日: {'是' if is_weekday else '否'}")

        # 检查市场开盘时间
        morning_open = "09:30:00"
        morning_close = "11:30:00"
        afternoon_open = "13:00:00"
        afternoon_close = "15:00:00"

        if morning_open <= current_time <= morning_close:
            market_status = "上午交易中"
        elif afternoon_open <= current_time <= afternoon_close:
            market_status = "下午交易中"
        elif "09:15:00" <= current_time < morning_open:
            market_status = "集合竞价"
        elif current_time < morning_open:
            market_status = "开盘前"
        elif morning_close < current_time < afternoon_open:
            market_status = "午休"
        elif current_time > afternoon_close:
            market_status = "收盘后"
        else:
            market_status = "未知"

        print(f"📊 市场状态: {market_status}")

        # 检查数据新鲜度
        try:
            import os
            data_dir = 'data'
            if os.path.exists(data_dir):
                files = os.listdir(data_dir)
                print(f"\n📂 数据目录文件数: {len(files)}")

                # 检查最近修改的文件
                recent_files = sorted([
                    (f, os.path.getmtime(os.path.join(data_dir, f)))
                    for f in files if os.path.isfile(os.path.join(data_dir, f))
                ], key=lambda x: x[1], reverse=True)[:5]

                if recent_files:
                    print(f"📄 最近修改的文件:")
                    for filename, mtime in recent_files:
                        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"   - {filename}: {mtime_str}")

        except Exception as e:
            print(f"⚠️  检查数据文件失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 检查市场状态失败: {e}")
        return False


def check_industry_cache(db):
    """检查行业缓存状态"""
    print("\n" + "=" * 80)
    print("🏭 检查行业缓存状态")
    print("=" * 80)

    try:
        code_to_industry = db.get_industry_cache()

        if code_to_industry:
            print(f"✅ 行业缓存已加载")
            print(f"   - 股票数量: {len(code_to_industry)}")

            # 统计行业分布
            industry_count = {}
            for industry in code_to_industry.values():
                industry_count[industry] = industry_count.get(industry, 0) + 1

            print(f"   - 行业数量: {len(industry_count)}")

            # 显示前 5 个行业
            top_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   - Top 5 行业:")
            for industry, count in top_industries:
                print(f"     - {industry}: {count} 只股票")

            return True
        else:
            print(f"❌ 行业缓存未加载")
            return False

    except Exception as e:
        print(f"❌ 检查行业缓存失败: {e}")
        return False


def write_health_log(redis_ok, snapshot_ok, market_ok, cache_ok):
    """写入健康检查日志"""
    print("\n" + "=" * 80)
    print("📝 写入健康检查日志")
    print("=" * 80)

    try:
        log_file = 'logs/system_health.log'
        import os

        # 确保 logs 目录存在
        os.makedirs('logs', exist_ok=True)

        # 写入日志
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"📅 系统健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
            f.write(f"✅ Redis 状态: {'正常' if redis_ok else '异常'}\n")
            f.write(f"✅ 数据快照: {'正常' if snapshot_ok else '异常'}\n")
            f.write(f"✅ 市场状态: {'正常' if market_ok else '异常'}\n")
            f.write(f"✅ 行业缓存: {'正常' if cache_ok else '异常'}\n")

            all_ok = redis_ok and snapshot_ok and market_ok and cache_ok
            f.write(f"\n🎯 总体状态: {'✅ 系统正常，可以开盘' if all_ok else '⚠️  系统异常，请检查'}\n")

        print(f"✅ 健康检查日志已写入: {log_file}")

        return all_ok

    except Exception as e:
        print(f"❌ 写入健康检查日志失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 系统健康检查")
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 初始化数据管理器
    print("\n🔄 初始化数据管理器...")
    db = DataManager()

    # 检查各项状态
    redis_ok = check_redis_status()
    snapshot_ok = check_data_snapshot(db)
    market_ok = check_market_status(db)
    cache_ok = check_industry_cache(db)

    # 写入日志
    all_ok = write_health_log(redis_ok, snapshot_ok, market_ok, cache_ok)

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 健康检查汇总")
    print("=" * 80)
    print(f"  Redis 状态: {'✅ 正常' if redis_ok else '❌ 异常'}")
    print(f"  数据快照: {'✅ 正常' if snapshot_ok else '❌ 异常'}")
    print(f"  市场状态: {'✅ 正常' if market_ok else '❌ 异常'}")
    print(f"  行业缓存: {'✅ 正常' if cache_ok else '❌ 异常'}")
    print(f"\n🎯 总体状态: {'✅ 系统正常，可以开盘' if all_ok else '⚠️  系统异常，请检查'}")
    print("=" * 80)

    return all_ok


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)