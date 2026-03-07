"""
断点测试：完整流程验证
"""
import sys
import time
sys.path.insert(0, 'E:/MyQuantTool')

print('='*60)
print('完整流程验证')
print('='*60)

# ========== 初始化 ==========
print('\n[初始化] QMT连接...')
from xtquant import xtdata
xtdata.enable_hello = False
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
print(f'  -> {len(all_stocks)}只')

print('\n[初始化] QmtDataManager...')
from logic.data_providers.qmt_manager import QmtDataManager
qmt_manager = QmtDataManager()

print('\n[初始化] LiveTradingEngine...')
from tasks.run_live_trading_engine import LiveTradingEngine
engine = LiveTradingEngine(qmt_manager=qmt_manager)

# ========== 断点1: _auction_snapshot_filter ==========
print('\n[断点1] _auction_snapshot_filter...')
t1 = time.time()
engine._auction_snapshot_filter()
print(f'  -> watchlist={len(engine.watchlist)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点2: _snapshot_filter ==========
print('\n[断点2] _snapshot_filter...')
t1 = time.time()
engine._snapshot_filter()
print(f'  -> watchlist={len(engine.watchlist)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点3: _setup_qmt_callbacks ==========
print('\n[断点3] _setup_qmt_callbacks...')
t1 = time.time()
engine._setup_qmt_callbacks()
print(f'  -> 完成, 耗时{time.time()-t1:.2f}s')

# ========== 断点4: _run_radar_main_loop (1次) ==========
print('\n[断点4] _run_radar_main_loop...')
t1 = time.time()
engine._run_radar_main_loop()
print(f'  -> 完成, 耗时{time.time()-t1:.2f}s')

print('\n'+'='*60)
print('完整流程验证成功!')
print('='*60)