# -*- coding: utf-8 -*-
"""
QMT 接口初始化和连接测试脚本

功能：
1. 初始化 QMT 数据接口
2. 测试 QMT 连接状态
3. 测试基础数据获取功能
4. 验证配置是否正确

使用方法：
    python scripts/init_qmt.py

Author: iFlow CLI
Date: 2026-01-28
"""

import os
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_qmt_config():
    """加载 QMT 配置"""
    config_path = project_root / "config" / "qmt_config.json"

    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请先创建配置文件 config/qmt_config.json")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config


def test_qmt_data_connection():
    """测试 QMT 数据接口连接"""
    print("=" * 80)
    print("🧪 测试 QMT 数据接口连接")
    print("=" * 80)

    try:
        from xtquant import xtdata

        print("\n✅ xtdata 模块导入成功")

        # 获取市场数据
        print("\n📊 测试获取市场数据...")

        # 获取股票列表
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
        print(f"✅ 获取到沪深A股股票数量: {len(stock_list) if stock_list else 0}")

        if stock_list and len(stock_list) > 0:
            # 获取第一只股票的实时数据
            test_stock = stock_list[0]
            print(f"\n📈 测试获取 {test_stock} 的实时数据...")

            # 下载历史数据
            print(f"\n📅 测试下载 {test_stock} 的历史数据...")
            xtdata.download_history_data(test_stock, period='1d', start_time='20240101', end_time='20240131')
            print(f"✅ 历史数据下载成功")

            # 获取本地数据
            data = xtdata.get_local_data(field_list=['time', 'open', 'high', 'low', 'close'],
                                         stock_list=[test_stock],
                                         period='1d',
                                         start_time='20240101',
                                         end_time='20240131')

            if data and test_stock in data:
                print(f"✅ 成功获取 {test_stock} 的本地数据，共 {len(data[test_stock])} 条记录")
                print(f"   最新数据: {data[test_stock][-1]}")
            else:
                print("⚠️  未能获取本地数据（可能需要先下载）")

            # 获取全市场tick数据
            print(f"\n⚡ 测试获取全市场tick数据...")
            tick_data = xtdata.get_full_tick([test_stock])
            if tick_data and test_stock in tick_data:
                print(f"✅ 成功获取 {test_stock} 的tick数据")
                print(f"   最新价格: {tick_data[test_stock].get('lastPrice', 'N/A')}")
            else:
                print("⚠️  未能获取tick数据（可能需要订阅）")

        print("\n" + "=" * 80)
        print("✅ QMT 数据接口连接测试完成")
        print("=" * 80)

        return True

    except ImportError as e:
        print(f"❌ 无法导入 xtdata 模块: {e}")
        print("\n请确保：")
        print("1. xtquant 模块已正确安装")
        print("2. xtquant 目录位于项目根目录下")
        return False
    except Exception as e:
        print(f"❌ QMT 数据接口连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qmt_trader_connection():
    """测试 QMT 交易接口连接"""
    print("\n" + "=" * 80)
    print("🧪 测试 QMT 交易接口连接")
    print("=" * 80)

    config = load_qmt_config()
    if not config or not config.get('qmt_trader', {}).get('enabled', False):
        print("⚠️  QMT 交易接口未启用，跳过测试")
        return None

    try:
        from xtquant import xttrader

        print("\n✅ xttrader 模块导入成功")

        # 创建交易回调类
        class MyXtQuantTraderCallback(xttrader.XtQuantTraderCallback):
            def on_connected(self):
                print("✅ 交易接口连接成功")

            def on_disconnected(self):
                print("❌ 交易接口连接断开")

            def on_account_status(self, status):
                print(f"📊 账户状态: {status}")

            def on_stock_asset(self, asset):
                print(f"💰 账户资产: {asset}")

        # 创建交易客户端
        trader_config = config['qmt_trader']
        trader = xttrader.XtQuantTrader(MyXtQuantTraderCallback(), trader_config['session_id'])

        # 连接交易接口
        print(f"\n🔌 连接交易接口 {trader_config['ip']}:{trader_config['port']}...")
        connect_result = trader.connect()

        if connect_result == 0:
            print("✅ 交易接口连接成功")
            print("\n" + "=" * 80)
            print("✅ QMT 交易接口连接测试完成")
            print("=" * 80)
            return True
        else:
            print(f"❌ 交易接口连接失败，错误码: {connect_result}")
            return False

    except ImportError as e:
        print(f"❌ 无法导入 xttrader 模块: {e}")
        return False
    except Exception as e:
        print(f"❌ QMT 交易接口连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_qmt_config():
    """检查 QMT 配置"""
    print("=" * 80)
    print("🔍 检查 QMT 配置")
    print("=" * 80)

    config = load_qmt_config()
    if not config:
        return False

    print("\n✅ 配置文件加载成功")
    print(f"\n📋 配置内容:")

    # 数据接口配置
    data_config = config.get('qmt_data', {})
    print(f"\n【数据接口】")
    print(f"  启用状态: {'✅ 已启用' if data_config.get('enabled', False) else '❌ 未启用'}")
    print(f"  服务地址: {data_config.get('ip', 'N/A')}:{data_config.get('port', 'N/A')}")
    print(f"  超时时间: {data_config.get('timeout', 'N/A')}秒")
    print(f"  重试次数: {data_config.get('retry_times', 'N/A')}")
    print(f"  自动连接: {'✅' if data_config.get('auto_connect', False) else '❌'}")

    # 交易接口配置
    trader_config = config.get('qmt_trader', {})
    print(f"\n【交易接口】")
    print(f"  启用状态: {'✅ 已启用' if trader_config.get('enabled', False) else '❌ 未启用'}")
    print(f"  服务地址: {trader_config.get('ip', 'N/A')}:{trader_config.get('port', 'N/A')}")
    print(f"  会话ID: {trader_config.get('session_id', 'N/A')}")

    # 订阅配置
    subscribe_config = config.get('data_subscribe', {})
    print(f"\n【数据订阅】")
    print(f"  启用状态: {'✅ 已启用' if subscribe_config.get('enabled', False) else '❌ 未启用'}")
    print(f"  订阅字段: {', '.join(subscribe_config.get('fields', []))}")

    # 日志配置
    log_config = config.get('log_config', {})
    print(f"\n【日志配置】")
    print(f"  启用状态: {'✅ 已启用' if log_config.get('enabled', False) else '❌ 未启用'}")
    print(f"  日志路径: {log_config.get('log_path', 'N/A')}")
    print(f"  日志级别: {log_config.get('log_level', 'N/A')}")

    print("\n" + "=" * 80)
    print("✅ 配置检查完成")
    print("=" * 80)

    return True


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 QMT 接口初始化和测试")
    print("=" * 80)
    print(f"📅 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 工作目录: {project_root}")

    # 1. 检查配置
    print("\n")
    config_ok = check_qmt_config()

    if not config_ok:
        print("\n❌ 配置检查失败，请检查配置文件")
        return

    # 2. 测试数据接口连接
    print("\n")
    data_ok = test_qmt_data_connection()

    # 3. 测试交易接口连接（如果启用）
    print("\n")
    trader_ok = test_qmt_trader_connection()

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"配置检查: {'✅ 通过' if config_ok else '❌ 失败'}")
    print(f"数据接口: {'✅ 通过' if data_ok else '❌ 失败'}")
    print(f"交易接口: {'✅ 通过' if trader_ok else '❌ 失败' if trader_ok is False else '⚠️  跳过'}")

    if config_ok and data_ok:
        print("\n🎉 QMT 接口配置成功！可以开始使用 QMT 数据接口。")
        if trader_ok:
            print("🎉 QMT 交易接口也已就绪，可以进行实盘交易。")
    else:
        print("\n❌ QMT 接口配置存在问题，请检查配置和 QMT 客户端状态。")

    print("=" * 80)


if __name__ == "__main__":
    main()
