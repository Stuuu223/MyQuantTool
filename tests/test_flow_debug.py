"""
断点测试：定位阻塞位置
"""
import sys
import time
sys.path.insert(0, 'E:/MyQuantTool')

print('='*60)
print('断点测试开始')
print('='*60)

# ========== 断点1: QMT连接 ==========
print('\n[断点1] QMT连接...')
t1 = time.time()
from xtquant import xtdata
xtdata.enable_hello = False
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
print(f'  -> 完成: {len(all_stocks)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点2: 全市场快照 ==========
print('\n[断点2] 全市场快照...')
t1 = time.time()
snapshot = xtdata.get_full_tick(all_stocks)
print(f'  -> 完成: {len(snapshot)}条, 耗时{time.time()-t1:.2f}s')

# ========== 断点3: 第一斩筛选 ==========
print('\n[断点3] 第一斩筛选...')
t1 = time.time()
import pandas as pd
df = pd.DataFrame([{
    'stock_code': code,
    'open': t.get('open', 0),
    'volume': t.get('volume', 0),
    'prev_close': t.get('lastClose', 0),
} for code, t in snapshot.items() if t])
mask = ((df['open'] >= df['prev_close']) & (df['volume'] >= 1000) & (df['open'] > 0))
watchlist = df[mask]['stock_code'].tolist()
print(f'  -> 完成: {len(watchlist)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点4: 导入TrueDictionary ==========
print('\n[断点4] 导入TrueDictionary...')
t1 = time.time()
from logic.data_providers.true_dictionary import get_true_dictionary, warmup_true_dictionary
from logic.utils.calendar_utils import get_nth_previous_trading_day
from datetime import datetime
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点5: 获取交易日 ==========
print('\n[断点5] 获取交易日...')
t1 = time.time()
today = datetime.now().strftime('%Y%m%d')
target_date = get_nth_previous_trading_day(today, 1)
print(f'  -> 完成: target_date={target_date}, 耗时{time.time()-t1:.2f}s')

# ========== 断点6: TrueDictionary预热 ==========
print('\n[断点6] TrueDictionary预热...')
t1 = time.time()
true_dict = get_true_dictionary()
print(f'  -> get_true_dictionary: 耗时{time.time()-t1:.2f}s')

t1 = time.time()
warmup_true_dictionary(watchlist, target_date=target_date)
print(f'  -> warmup完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点7: 获取watchlist快照 ==========
print('\n[断点7] 获取watchlist快照...')
t1 = time.time()
snapshot2 = xtdata.get_full_tick(watchlist)
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点8: 计算量比 ==========
print('\n[断点8] 计算量比...')
t1 = time.time()
df2 = pd.DataFrame([{
    'stock_code': code,
    'volume': snapshot2[code].get('volume', 0),
    'prev_close': snapshot2[code].get('lastClose', 0),
} for code in watchlist if code in snapshot2])
df2['avg_volume_5d'] = df2['stock_code'].map(true_dict.get_avg_volume_5d)
df2['avg_volume_5d_gu'] = df2['avg_volume_5d'] * 100
df2['volume_gu'] = df2['volume'] * 100
df2['volume_ratio'] = df2['volume_gu'] / df2['avg_volume_5d_gu'].replace(0, 1)
watchlist2 = df2[df2['volume_ratio'] >= 1.5]['stock_code'].tolist()
print(f'  -> 完成: {len(watchlist2)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点9: 分批订阅 ==========
print('\n[断点9] 分批订阅...')
t1 = time.time()
batch_size = 100
for i in range(0, len(watchlist2), batch_size):
    batch = watchlist2[i:i+batch_size]
    xtdata.subscribe_whole_quote(batch)
    xtdata.get_full_tick(batch)
    print(f'  -> 批次{i//batch_size+1}: {len(batch)}只')
    time.sleep(0.1)
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点10: 导入LiveTradingEngine ==========
print('\n[断点10] 导入LiveTradingEngine...')
t1 = time.time()
from tasks.run_live_trading_engine import LiveTradingEngine
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点11: 实例化Engine ==========
print('\n[断点11] 实例化Engine...')
t1 = time.time()
engine = LiveTradingEngine()
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点12: 设置adapter ==========
print('\n[断点12] 设置adapter...')
t1 = time.time()
engine._setup_qmt_adapter()
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点13: 获取全A股 ==========
print('\n[断点13] 获取全A股...')
t1 = time.time()
stocks = engine.qmt_adapter.get_all_a_shares()
print(f'  -> 完成: {len(stocks)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点14: _auction_snapshot_filter ==========
print('\n[断点14] _auction_snapshot_filter...')
t1 = time.time()
engine._auction_snapshot_filter()
print(f'  -> 完成: watchlist={len(engine.watchlist)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点15: _snapshot_filter ==========
print('\n[断点15] _snapshot_filter...')
t1 = time.time()
engine._snapshot_filter()
print(f'  -> 完成: watchlist={len(engine.watchlist)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点16: _setup_qmt_callbacks ==========
print('\n[断点16] _setup_qmt_callbacks...')
t1 = time.time()
engine._setup_qmt_callbacks()
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点17: 雷达循环(3次) ==========
print('\n[断点17] 雷达循环测试(3次)...')
for loop in range(3):
    t1 = time.time()
    engine._run_radar_main_loop()
    print(f'  -> 循环{loop+1}: 耗时{time.time()-t1:.2f}s')
    time.sleep(1)

print('\n'+'='*60)
print('断点测试完成')
print('='*60)
