"""
Debug data units
"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.moneyflow_data_source import TushareMoneyflowSource, EastmoneyMoneyflowSource

# Test tushare
tushare_source = TushareMoneyflowSource()
tushare_snapshots = tushare_source.get_moneyflow(
    ts_code='603607.SH',
    start_date='20250812',
    end_date='20250812'
)

print("Tushare data:")
if tushare_snapshots:
    snapshot = tushare_snapshots[0]
    print(f"  main_net_inflow: {snapshot.main_net_inflow:.6f} 万元")
    print(f"  raw_data: {snapshot.raw_data}")

# Test eastmoney
eastmoney_source = EastmoneyMoneyflowSource()
eastmoney_snapshots = eastmoney_source.get_moneyflow(
    ts_code='603607.SH',
    start_date='20250812',
    end_date='20250812'
)

print("\nEastmoney data:")
if eastmoney_snapshots:
    snapshot = eastmoney_snapshots[0]
    print(f"  main_net_inflow: {snapshot.main_net_inflow:.6f} 万元")
    print(f"  raw_data: {snapshot.raw_data}")