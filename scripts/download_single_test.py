#!/usr/bin/env python3
"""
单只股票Tick数据下载测试 - 网宿科技
"""
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from xtquant import xtdatacenter as xtdc
from xtquant import xtdata

VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"

# 设置数据目录
data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
data_dir.mkdir(parents=True, exist_ok=True)
xtdc.set_data_home_dir(str(data_dir))

# 设置Token
xtdc.set_token(VIP_TOKEN)
print(f"🔑 Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")

# 初始化
print("🚀 启动服务...")
xtdc.init()
listen_port = xtdc.listen(port=(58700, 58710))
print(f"✅ 服务已启动，端口: {listen_port}")

# 连接
_, port = listen_port
xtdata.connect(ip='127.0.0.1', port=port)
print("✅ 已连接到行情服务")

# 下载网宿科技 2025-11-17 的数据（已有数据的日期）
code = '300017.SZ'
start_time = '20251117000000'

print(f"\n📥 下载 {code} Tick数据...")
print(f"   开始时间: {start_time} (历史数据)")

start = time.time()
xtdata.download_history_data(code, period='tick', start_time=start_time)
elapsed = time.time() - start

print(f"✅ 下载完成，耗时: {elapsed:.1f}秒")

# 检查下载的数据
data = xtdata.get_local_data([code], period='tick', 
                              start_time='20260204 09:30:00',
                              end_time='20260213 15:00:00')
if code in data:
    print(f"📊 数据条数: {len(data[code])}")
else:
    print("⚠️ 无数据")

print("\n👋 完成")
