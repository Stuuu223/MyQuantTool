#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证main_net_inflow字段是否存在
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.fund_flow_analyzer import FundFlowAnalyzer
import json

analyzer = FundFlowAnalyzer(enable_cache=True)
data = analyzer.get_fund_flow('002517.SZ', days=5)

print('=' * 80)
print('🔍 验证main_net_inflow字段（清空缓存后）')
print('=' * 80)

if 'error' in data:
    print(f'❌ 错误: {data["error"]}')
else:
    print('records:')
    for record in data.get('records', []):
        print(f'  日期: {record["date"]}')
        print(f'    main_net_inflow: {record.get("main_net_inflow", "N/A")}')
        print(f'    super_large_net: {record.get("super_large_net", "N/A")}')
        print(f'    large_net: {record.get("large_net", "N/A")}')
        print(f'    institution_net: {record.get("institution_net", "N/A")}')
        print()
    
    print('latest:')
    latest = data.get('latest', {})
    print(f'  main_net_inflow: {latest.get("main_net_inflow", "N/A")}')
    print(f'  super_large_net: {latest.get("super_large_net", "N/A")}')
    print(f'  large_net: {latest.get("large_net", "N/A")}')
    print(f'  from_cache: {data.get("from_cache", "N/A")}')
    print()

    # 验证main_net_inflow是否等于super_large_net + large_net
    if 'records' in data and data['records']:
        first_record = data['records'][0]
        main_net = first_record.get('main_net_inflow')
        super_large = first_record.get('super_large_net', 0)
        large = first_record.get('large_net', 0)
        
        if main_net is not None:
            expected = super_large + large
            if abs(main_net - expected) < 0.01:
                print(f'✅ 验证通过: main_net_inflow ({main_net:.0f}) = super_large_net ({super_large:.0f}) + large_net ({large:.0f})')
            else:
                print(f'❌ 验证失败: main_net_inflow ({main_net:.0f}) != super_large_net ({super_large:.0f}) + large_net ({large:.0f}) = {expected:.0f}')
        else:
            print('❌ main_net_inflow字段缺失！')

print('=' * 80)