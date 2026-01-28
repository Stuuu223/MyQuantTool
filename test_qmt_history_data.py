#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 QMT 历史数据获取功能
验证 get_history_data 是否已成功替换为 QMT 接口
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from logic.realtime_data_provider import RealtimeDataProvider
from logic.logger import get_logger

logger = get_logger(__name__)


def test_qmt_history_data():
    """测试 QMT 历史数据获取"""

    print("=" * 70)
    print("🧪 测试 QMT 历史数据获取功能")
    print("=" * 70)
    print()

    # 创建数据提供者
    try:
        provider = RealtimeDataProvider()
        print("✅ RealtimeDataProvider 初始化成功")
    except Exception as e:
        print(f"❌ RealtimeDataProvider 初始化失败: {e}")
        return

    # 检查 QMT 是否可用
    if not hasattr(provider, 'xtdata') or provider.xtdata is None:
        print("❌ QMT 接口不可用")
        return

    print("✅ QMT 接口已加载")
    print()

    # 测试股票代码
    test_stocks = ['000001', '600519', '000858']

    print("-" * 70)
    print("📊 开始测试历史数据获取...")
    print("-" * 70)
    print()

    for stock_code in test_stocks:
        print(f"📍 测试股票: {stock_code}")

        try:
            # 获取历史数据
            df = provider.get_history_data(symbol=stock_code, period='daily', adjust='qfq')

            if df is not None and not df.empty:
                print(f"  ✅ 成功获取 {len(df)} 条历史数据")
                print(f"  - 时间范围: {df['date'].iloc[0]} 到 {df['date'].iloc[-1]}")
                print(f"  - 最新收盘价: {df['close'].iloc[-1]:.2f}")
                print(f"  - 数据列: {list(df.columns)}")
            else:
                print(f"  ❌ 获取失败：数据为空")

        except Exception as e:
            print(f"  ❌ 获取失败: {e}")

        print()

    print("-" * 70)
    print("✅ 测试完成")
    print("-" * 70)
    print()
    print("📝 说明：")
    print("  - 如果所有股票都成功获取数据，说明 QMT 接口替换成功")
    print("  - 速度应该很快（0.1秒以内），不会出现 RemoteDisconnected 错误")
    print()


if __name__ == '__main__':
    test_qmt_history_data()