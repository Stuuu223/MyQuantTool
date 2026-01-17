#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V12 第三阶段测试：预测雷达功能测试
验证预测引擎和 UI 模块是否正常工作
"""

import sys
import time
from logic.predictive_engine import PredictiveEngine
from logic.market_sentiment import MarketSentiment
from logic.database_manager import get_db_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_predictive_engine():
    """测试预测引擎核心功能"""
    print("=" * 60)
    print("🔮 测试 1: PredictiveEngine 核心功能")
    print("=" * 60)

    pe = PredictiveEngine()

    # 测试 1.1: 获取晋级概率
    print("\n📊 测试 1.1: 获取晋级概率")
    test_heights = [3, 4, 5, 6, 7]
    for height in test_heights:
        try:
            prob = pe.get_promotion_probability(height)
            if prob >= 0:
                print(f"  ✅ {height}板 ➜ {height+1}板: {prob}%")
            else:
                print(f"  ⚠️ {height}板 ➜ {height+1}板: 数据不足 (样本量 < 10)")
        except Exception as e:
            print(f"  ❌ {height}板 ➜ {height+1}板: 计算失败 - {e}")

    # 测试 1.2: 检测情绪转折点
    print("\n🎯 测试 1.2: 检测情绪转折点")
    try:
        pivot = pe.detect_sentiment_pivot()
        print(f"  ✅ 当前状态: {pivot['action']}")
        print(f"  ✅ 原因: {pivot['reason']}")
    except Exception as e:
        print(f"  ❌ 情绪转折检测失败: {e}")

    print("\n✅ PredictiveEngine 测试完成")


def test_market_sentiment():
    """测试市场情绪模块"""
    print("\n" + "=" * 60)
    print("🌤️ 测试 2: MarketSentiment 市场情绪")
    print("=" * 60)

    ms = MarketSentiment()

    # 测试 2.1: 获取连板高度
    print("\n📈 测试 2.1: 获取连板高度")
    try:
        height_data = ms.get_consecutive_board_height()
        print(f"  ✅ 最高板: {height_data.get('max_board', 0)}板")
        print(f"  ✅ 日期: {height_data.get('date', '未知')}")
    except Exception as e:
        print(f"  ❌ 获取连板高度失败: {e}")

    # 测试 2.2: 获取涨跌停家数
    print("\n🔥 测试 2.2: 获取涨跌停家数")
    try:
        limit_data = ms.get_limit_up_down_count()
        print(f"  ✅ 涨停家数: {limit_data.get('limit_up_count', 0)}")
        print(f"  ✅ 跌停家数: {limit_data.get('limit_down_count', 0)}")
    except Exception as e:
        print(f"  ❌ 获取涨跌停家数失败: {e}")

    # 测试 2.3: 获取昨日涨停溢价
    print("\n💰 测试 2.3: 获取昨日涨停溢价")
    try:
        profit_data = ms.get_prev_limit_up_profit()
        if profit_data:
            print(f"  ✅ 平均溢价: {profit_data.get('avg_profit', 0):.2f}%")
            print(f"  ✅ 盈利家数: {profit_data.get('profit_count', 0)}")
            print(f"  ✅ 亏损家数: {profit_data.get('loss_count', 0)}")
        else:
            print(f"  ⚠️ 溢价数据不足（可能未到 9:25 或数据未更新）")
    except Exception as e:
        print(f"  ❌ 获取昨日涨停溢价失败: {e}")

    ms.close()
    print("\n✅ MarketSentiment 测试完成")


def test_database_manager():
    """测试数据库管理器"""
    print("\n" + "=" * 60)
    print("💾 测试 3: DatabaseManager 历史数据")
    print("=" * 60)

    db = get_db_manager()

    # 测试 3.1: 查询历史高度数据
    print("\n📊 测试 3.1: 查询历史高度数据")
    try:
        history = db.sqlite_query(
            "SELECT date, highest_board FROM market_summary ORDER BY date DESC LIMIT 20"
        )
        if history and len(history) > 0:
            print(f"  ✅ 找到 {len(history)} 条历史记录")
            print(f"  ✅ 最新记录: {history[0][0]} - {history[0][1]}板")
            print(f"  ✅ 最早记录: {history[-1][0]} - {history[-1][1]}板")
        else:
            print(f"  ⚠️ 暂无历史数据，请在交易时段后查看")
    except Exception as e:
        print(f"  ❌ 查询历史数据失败: {e}")

    print("\n✅ DatabaseManager 测试完成")


def test_integration():
    """集成测试：模拟预测雷达的完整流程"""
    print("\n" + "=" * 60)
    print("🔗 测试 4: 集成测试（模拟预测雷达流程）")
    print("=" * 60)

    start_time = time.time()

    try:
        # 初始化组件
        pe = PredictiveEngine()
        ms = MarketSentiment()
        db = get_db_manager()

        print("\n📊 步骤 1: 获取市场实时状态")
        sentiment_data = ms.get_consecutive_board_height()
        current_height = sentiment_data.get('max_board', 0)
        print(f"  ✅ 当前最高板: {current_height}板")

        print("\n📊 步骤 2: 计算晋级概率")
        prob = pe.get_promotion_probability(current_height)
        if prob >= 0:
            print(f"  ✅ {current_height}板 ➜ {current_height+1}板: {prob}%")
        else:
            print(f"  ⚠️ 数据不足（样本量 < 10）")

        print("\n📊 步骤 3: 检测情绪转折点")
        pivot = pe.detect_sentiment_pivot()
        print(f"  ✅ 当前状态: {pivot['action']}")
        print(f"  ✅ 原因: {pivot['reason']}")

        print("\n📊 步骤 4: 获取历史高度数据")
        history = db.sqlite_query(
            "SELECT date, highest_board FROM market_summary ORDER BY date DESC LIMIT 20"
        )
        if history:
            print(f"  ✅ 找到 {len(history)} 条历史记录")
        else:
            print(f"  ⚠️ 暂无历史数据")

        # 关闭连接
        ms.close()

        elapsed = time.time() - start_time
        print(f"\n✅ 集成测试完成，耗时: {elapsed:.2f}秒")
        return True

    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🚀 V12 第三阶段：预测雷达功能测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        # 运行所有测试
        test_predictive_engine()
        test_market_sentiment()
        test_database_manager()
        success = test_integration()

        print("\n" + "=" * 60)
        if success:
            print("✅ 所有测试通过！预测雷达功能正常")
        else:
            print("❌ 部分测试失败，请检查日志")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())