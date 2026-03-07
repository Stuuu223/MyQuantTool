"""
断点测试：LiveTradingEngine初始化流程
"""
import sys
import time
sys.path.insert(0, 'E:/MyQuantTool')

print('='*60)
print('LiveTradingEngine初始化 断点测试')
print('='*60)

# ========== 断点1: QMT连接 ==========
print('\n[断点1] QMT连接...')
t1 = time.time()
from xtquant import xtdata
xtdata.enable_hello = False
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
print(f'  -> 完成: {len(all_stocks)}只, 耗时{time.time()-t1:.2f}s')

# ========== 断点2: 初始化QmtDataManager ==========
print('\n[断点2] 初始化QmtDataManager...')
t1 = time.time()
from logic.data_providers.qmt_manager import QmtDataManager
qmt_manager = QmtDataManager()
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点3: 导入LiveTradingEngine类 ==========
print('\n[断点3] 导入LiveTradingEngine类...')
t1 = time.time()
from tasks.run_live_trading_engine import LiveTradingEngine
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点4: 初始化LiveTradingEngine ==========
print('\n[断点4] 初始化LiveTradingEngine...')
t1 = time.time()
engine = LiveTradingEngine(qmt_manager=qmt_manager)
print(f'  -> 完成: 耗时{time.time()-t1:.2f}s')

# ========== 断点5: 检查adapter ==========
print('\n[断点5] 检查adapter...')
print(f'  -> adapter存在: {hasattr(engine, "qmt_adapter")}')
if hasattr(engine, 'qmt_adapter'):
    print(f'  -> adapter类型: {type(engine.qmt_adapter)}')

print('\n'+'='*60)
print('断点测试完成')
print('='*60)
