#!/usr/bin/env python3
"""
顽主杯Top 50股票Tick数据下载
下载2025-01-25至2026-02-13的Tick数据

使用xtdatacenter本地服务+Token方式
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

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


def download_tick_batch(stock_list_path: Path, start_date: str, end_date: str):
    """批量下载Tick数据"""
    from xtquant import xtdata
    
    # 加载股票列表
    with open(stock_list_path, 'r', encoding='utf-8') as f:
        stocks = json.load(f)
    
    print(f"=" * 70)
    print(f"📥 下载顽主杯股票Tick数据")
    print(f"=" * 70)
    print(f"\n股票数: {len(stocks)}")
    print(f"日期范围: {start_date} 至 {end_date}")
    
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
    
    # 3. 转换日期格式
    start = start_date.replace('-', '')
    end = end_date.replace('-', '')
    start_time = f'{start}000000'
    
    # 4. 下载每只股票的数据
    print(f"\n开始下载...")
    success_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stocks[:50], 1):  # 先下载Top 50
        qmt_code = f"{stock['qmt_code']}.{stock['market']}"
        print(f"\n[{i}/50] {stock['name']} ({qmt_code})")
        
        try:
            # 下载Tick数据
            xtdata.download_history_data(
                stock_code=qmt_code,
                period='tick',
                start_time=start_time
            )
            print(f"  ✅ 下载成功")
            success_count += 1
            time.sleep(0.2)  # 避免请求过快
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
            fail_count += 1
    
    print(f"\n{'=' * 70}")
    print(f"下载完成: 成功 {success_count} 只, 失败 {fail_count} 只")
    print(f"{'=' * 70}")
    
    # 5. 保持运行
    print("\n🎉 任务完成！数据已保存到本地。按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 退出")


def main():
    stock_list_path = Path('config/wanzhu_top50_tick_download.json')
    
    if not stock_list_path.exists():
        print(f"❌ 股票列表不存在: {stock_list_path}")
        return
    
    # 下载2025-01-25至2026-02-13的数据
    download_tick_batch(
        stock_list_path,
        start_date='2025-01-25',
        end_date='2026-02-13'
    )


if __name__ == '__main__':
    main()
