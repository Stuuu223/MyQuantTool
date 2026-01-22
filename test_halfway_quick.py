# -*- coding: utf-8 -*-
from logic.algo import QuantAlgo
import time

start = time.time()
result = QuantAlgo.scan_halfway_stocks(limit=1, min_score=30)
elapsed = time.time() - start

print('耗时:', elapsed, '秒')
print('数据状态:', result.get('数据状态'))
print('符合条件数量:', result.get('符合条件数量'))

stocks = result.get('半路板列表', [])
print('股票数量:', len(stocks))

for s in stocks[:1]:
    print(f"{s['代码']} {s['名称']}")
    print(f"  换手率: {s['换手率']:.2f}%")
    print(f"  量比: {s['量比']:.2f}")
    print(f"  乖离率: {s.get('乖离率', 0):.2f}%")
    print(f"  验证: {'通过' if s['换手率'] > 0 and s['量比'] > 1 else '失败'}")