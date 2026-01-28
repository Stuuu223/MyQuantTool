# -*- coding: utf-8 -*-
"""
真正的"时光倒流"复盘测试
验证复盘模式是否真的能获取历史时间点的数据
"""
import sys
import os

# 确保能找到项目路径
sys.path.append(os.getcwd())

from logic.realtime_data_provider import RealtimeDataProvider
from logic.midway_strategy_v19_final import MidwayStrategy
from logic.logger import get_logger

logger = get_logger(__name__)


def test_real_replay_mode():
    """测试真正的复盘模式"""
    print(">>> 🚀 启动真正的'时光倒流'复盘测试...")
    print(">>> 🕒 复盘时间：2026-01-27 09:40:00（昨天上午 9:40）")

    try:
        # 1. 初始化复盘模式的数据提供者
        print(">>> 📡 正在初始化复盘模式数据提供者...")
        data_provider = RealtimeDataProvider(
            replay_mode=True,
            replay_date='20260127',  # 昨天
            replay_time='094000',  # 上午 9:40
            replay_period='1m'
        )

        # 2. 初始化半路战法（传入数据提供者作为 data_manager）
        print(">>> 🎯 正在初始化半路战法...")
        midway = MidwayStrategy(data_manager=data_provider)

        # 3. 准备测试股票池（活跃股）
        test_stocks = ['600000', '000001', '300059', '601127', '300750', '601899', '000426']

        print(f">>> 📊 测试股票池: {', '.join(test_stocks)}")

        # 4. 获取复盘数据（历史时间点）
        print(">>> 🕒 正在进行时光倒流，获取 2026-01-27 09:40:00 的数据...")
        realtime_data = data_provider.get_realtime_data(test_stocks)

        if not realtime_data:
            print(">>> ❌ 未获取到复盘数据")
            return

        print(f">>> ✅ 成功获取 {len(realtime_data)} 条历史数据")
        print("-" * 80)
        print(f"{'代码':<10} {'现价':<10} {'涨幅%':<10} {'成交量(手)':<15} {'成交额(万)':<15} {'时间点':<15}")
        print("-" * 80)

        for stock in realtime_data:
            code = stock['code']
            price = stock['price']
            change_pct = stock['change_pct'] * 100
            volume = stock['volume']
            amount = stock['amount']
            replay_time = stock.get('replay_time', 'N/A')
            source = stock.get('source', 'N/A')

            print(f"{code:<10} {price:<10.2f} {change_pct:<10.2f} {volume:<15.0f} {amount:<15.0f} {replay_time:<15}")

        print("-" * 80)
        print(f">>> 数据源: {source}")

        # 5. 测试半路战法复盘
        print(">>> 🎯 正在测试半路战法复盘...")
        print(">>>    半路战法逻辑：3% < 涨幅 < 8.5%")

        hit_count = 0
        print("-" * 80)
        print(f"{'代码':<10} {'现价':<10} {'涨幅%':<10} {'战法信号':<20}")
        print("-" * 80)

        for stock in realtime_data:
            code = stock['code']
            try:
                is_hit, reason = midway.check_breakout(code, stock)
                status = "✅ 命中" if is_hit else "⚫ 忽略"
                print(f"{code:<10} {stock['price']:<10.2f} {stock['change_pct']*100:<10.2f} {status:<20}")

                if is_hit:
                    hit_count += 1
                    print(f"        原因: {reason}")
            except Exception as e:
                print(f"{code:<10} {'ERROR':<10} {'ERROR':<10} {'分析失败':<20}")
                logger.error(f"半路战法分析 {code} 失败: {e}")

        print("-" * 80)
        print(f">>> 🎉 测试完成！")
        print(f">>>    命中数量: {hit_count}/{len(realtime_data)}")
        print(f">>>    如果命中数量 > 0，说明复盘模式真正工作了！")
        print(f">>>    如果命中数量 = 0，可能是：")
        print(f">>>       1. 昨天上午 9:40 确实没有符合半路战法的股票")
        print(f">>>       2. 复盘时间点选得不好（9:40 可能太早）")
        print(f">>>       3. 股票池太小")

        # 6. 建议更好的复盘时间点
        print("\n>>> 💡 建议的复盘时间点：")
        print(">>>    09:35 - 开盘初期，容易有半路机会")
        print(">>>    10:30 - 早盘中段，主力开始发力")
        print(">>>    14:30 - 尾盘冲刺，主力拉抬")
        print(">>>    14:56 - 尾盘偷袭，主力最后一搏")

    except Exception as e:
        print(f">>> ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 80)
    print("真正的'时光倒流'复盘测试 - V19.17")
    print("=" * 80)

    test_real_replay_mode()

    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)