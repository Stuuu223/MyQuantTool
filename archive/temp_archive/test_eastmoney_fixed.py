"""
Test eastmoney data source with correct file
"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.moneyflow_data_source import EastmoneyMoneyflowSource

# Test with 603607.SH
eastmoney_source = EastmoneyMoneyflowSource()

snapshots = eastmoney_source.get_moneyflow(
    ts_code='603607.SH',
    start_date='20250812',
    end_date='20250922'
)

print(f"Got {len(snapshots)} snapshots from eastmoney:")
for snapshot in snapshots:
    print(f"  {snapshot.trade_date}: main_net_inflow={snapshot.main_net_inflow:.2f}")