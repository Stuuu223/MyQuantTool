#!/usr/bin/env python3
"""
下载网宿科技(300017.SZ)的Tick数据
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)

# VIP Token
VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"


def start_token_service():
    """启动 xtdatacenter 行情服务 (Token 模式)"""
    from xtquant import xtdatacenter as xtdc
    from xtquant import xtdata

    # 1. 设置数据目录
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    print(f"📂 数据目录: {data_dir}")

    # 2. 设置Token
    xtdc.set_token(VIP_TOKEN)
    print(f"🔑 Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")

    # 3. 初始化并监听端口（使用动态端口避免冲突）
    xtdc.init()
    listen_port = xtdc.listen(port=(58700, 58720))
    print(f"🚀 行情服务已启动，监听端口: {listen_port}")

    return listen_port


def download_wangsu_tick():
    """下载网宿科技的Tick数据"""
    from xtquant import xtdata

    # 网宿科技信息
    stock = {
        'name': '网宿科技',
        'code': '300017.SZ',
        'qmt_code': '300017',
        'market': 'SZ'
    }

    print(f"=" * 70)
    print(f"📥 下载 {stock['name']} ({stock['code']}) Tick数据")
    print(f"=" * 70)

    # 1. 启动Token服务
    print(f"\n🌐 启动Token服务...")
    listen_port = start_token_service()

    # 2. 连接到行情服务
    _, port = listen_port
    xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)

    # 等待连接成功
    for i in range(10):
        if xtdata.get_market_data(['close'], ['600519.SH'], count=1):
            print("✅ 成功连接到行情服务！")
            break
        time.sleep(1)
        print(f"⏳ 等待连接... {i+1}/10")
    else:
        print("❌ 连接失败")
        return

    # 3. 下载最近3个月的Tick数据
    qmt_code = f"{stock['qmt_code']}.{stock['market']}"
    print(f"\n📥 开始下载 {stock['name']} ({qmt_code})...")

    try:
        # 下载Tick数据（从2025-01-01开始）
        start_time = '20250101000000'
        xtdata.download_history_data(
            stock_code=qmt_code,
            period='tick',
            start_time=start_time
        )
        print(f"  ✅ 下载成功")
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return

    print(f"\n{'=' * 70}")
    print(f"🎉 下载完成！")
    print(f"{'=' * 70}")

    # 4. 验证数据
    print(f"\n📊 验证数据...")
    try:
        tick_data = xtdata.get_market_data(
            ['lastPrice'],
            [qmt_code],
            period='tick',
            count=10
        )
        if tick_data is not None:
            if hasattr(tick_data, 'empty'):
                if not tick_data.empty:
                    print(f"  ✅ 数据验证成功，获取到 {len(tick_data)} 条tick数据")
                    print(f"  📈 最新tick数据: {tick_data.iloc[-1].to_dict()}")
                else:
                    print(f"  ⚠️  数据验证失败，返回空数据")
            elif isinstance(tick_data, dict):
                print(f"  ✅ 数据验证成功，返回dict格式数据")
                print(f"  📈 数据结构: {list(tick_data.keys())}")
            else:
                print(f"  ✅ 数据验证成功，数据类型: {type(tick_data)}")
        else:
            print(f"  ⚠️  数据验证失败，返回None")
    except Exception as e:
        print(f"  ⚠️  数据验证异常: {e}")

    # 5. 完成
    print("\n✅ 任务完成！")


if __name__ == '__main__':
    download_wangsu_tick()