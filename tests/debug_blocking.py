"""
断点测试 - 定位阻塞位置
"""
import sys
import time
from datetime import datetime

sys.path.insert(0, 'E:/MyQuantTool')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")

log("=" * 60)
log("断点测试开始")
log("=" * 60)

# ========== Step 1: QMT连接 ==========
log("Step 1: QMT连接...")
t1 = time.time()
from xtquant import xtdata
xtdata.enable_hello = False
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
log(f"  -> 完成: {len(all_stocks)} 只, 耗时 {time.time()-t1:.2f}s")

# ========== Step 2: TrueDictionary初始化 ==========
log("Step 2: TrueDictionary初始化...")
t1 = time.time()
from logic.data_providers.true_dictionary import get_true_dictionary, warmup_true_dictionary
from logic.utils.calendar_utils import get_nth_previous_trading_day
true_dict = get_true_dictionary()
log(f"  -> 完成: 耗时 {time.time()-t1:.2f}s")

# ========== Step 3: 全市场快照 ==========
log("Step 3: 全市场快照...")
t1 = time.time()
snapshot = xtdata.get_full_tick(all_stocks)
log(f"  -> 完成: {len(snapshot)} 只, 耗时 {time.time()-t1:.2f}s")

# ========== Step 4: 第一斩 ==========
log("Step 4: 第一斩（开盘价>=昨收）...")
t1 = time.time()
import pandas as pd
df = pd.DataFrame([{
    'stock_code': code,
    'open': t.get('open', 0) if t else 0,
    'volume': t.get('volume', 0) if t else 0,
    'prev_close': t.get('lastClose', 0) if t else 0,
} for code, t in snapshot.items() if t])

mask = ((df['open'] >= df['prev_close']) & (df['volume'] >= 1000) & (df['open'] > 0))
watchlist = df[mask]['stock_code'].tolist()
log(f"  -> 完成: {len(watchlist)} 只, 耗时 {time.time()-t1:.2f}s")

# ========== Step 5: 预热TrueDictionary ==========
log("Step 5: 预热TrueDictionary...")
t1 = time.time()
target_date = get_nth_previous_trading_day(datetime.now().strftime('%Y%m%d'), 1)
log(f"  -> target_date: {target_date}")

# 分批预热
batch_size = 200
for i in range(0, len(watchlist), batch_size):
    batch = watchlist[i:i+batch_size]
    log(f"  -> 预热批次 {i//batch_size+1}: {len(batch)} 只")
    warmup_true_dictionary(batch, target_date=target_date)
    log(f"     耗时: {time.time()-t1:.2f}s")
    
log(f"  -> 预热完成: 总耗时 {time.time()-t1:.2f}s")

# ========== Step 6: 第二斩（获取watchlist快照） ==========
log("Step 6: 第二斩（获取watchlist快照）...")
t1 = time.time()
snapshot2 = xtdata.get_full_tick(watchlist)
log(f"  -> 完成: {len(snapshot2)} 只, 耗时 {time.time()-t1:.2f}s")

# ========== Step 7: 计算量比 ==========
log("Step 7: 计算量比...")
t1 = time.time()
df2 = pd.DataFrame([{
    'stock_code': code,
    'volume': snapshot2[code].get('volume', 0) if snapshot2.get(code) else 0,
    'prev_close': snapshot2[code].get('lastClose', 0) if snapshot2.get(code) else 0,
} for code in watchlist if code in snapshot2])

df2['avg_volume_5d'] = df2['stock_code'].map(true_dict.get_avg_volume_5d)
df2['avg_volume_5d_gu'] = df2['avg_volume_5d'] * 100
df2['volume_gu'] = df2['volume'] * 100
df2['volume_ratio'] = df2['volume_gu'] / df2['avg_volume_5d_gu'].replace(0, 1)
df2['volume_ratio'] = df2['volume_ratio'].fillna(1.0)

watchlist2 = df2[df2['volume_ratio'] >= 1.5]['stock_code'].tolist()
log(f"  -> 完成: {len(watchlist2)} 只, 耗时 {time.time()-t1:.2f}s")

# ========== Step 8: 分批唤醒 ==========
log("Step 8: 分批唤醒（订阅Tick）...")
t1 = time.time()
batch_size = 100
for i in range(0, len(watchlist2), batch_size):
    batch = watchlist2[i:i+batch_size]
    log(f"  -> 唤醒批次 {i//batch_size+1}: {len(batch)} 只")
    xtdata.subscribe_whole_quote(batch)
    xtdata.get_full_tick(batch)
    time.sleep(0.1)
log(f"  -> 完成: 总耗时 {time.time()-t1:.2f}s")

# ========== Step 9: 雷达循环测试 ==========
log("Step 9: 雷达循环测试（5次）...")
for loop in range(5):
    t1 = time.time()
    ticks = xtdata.get_full_tick(watchlist2)
    active = sum(1 for c in watchlist2 if ticks.get(c, {}).get('lastPrice', 0) > 0)
    log(f"  -> 循环{loop+1}: active={active}, 耗时 {time.time()-t1:.2f}s")
    time.sleep(1)

log("=" * 60)
log("断点测试完成")
log("=" * 60)
