#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from logic.qmt_historical_provider import QMTHistoricalProvider

# 测试000017.SZ（深圳）
provider = QMTHistoricalProvider('000017.SZ', '20251114', '20251120', period='tick')
df = provider.get_raw_ticks()
print(f'000017.SZ: {len(df)} 条Tick记录')
if len(df) > 0:
    print(f'  时间范围: {df["time"].min()} ~ {df["time"].max()}')
    print(f'  列名: {list(df.columns)}')
    print(f'  前5条:')
    print(df.head())
