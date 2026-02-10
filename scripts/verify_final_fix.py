#!/usr/bin/env python3
"""
终极修复验证：时机斧 + current_price=0 问题
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.full_market_scanner import FullMarketScanner

print("🎯 终极修复验证结果:")

scanner = FullMarketScanner()
result = scanner.scan_with_risk_management(mode='intraday')

print(f"机会池: {len(result['opportunities'])} 只")
print(f"观察池: {len(result['watchlist'])} 只")
print(f"黑名单: {len(result['blacklist'])} 只")
print(f"置信度: {result['confidence']:.1%}")

# 检查 605088.SH
found = False
for pool, name in [('opportunities', '机会池'), ('watchlist', '观察池'), ('blacklist', '黑名单')]:
    codes = [s['code'] for s in result[pool]]
    if '605088.SH' in codes:
        print(f"✅ 605088.SH 在 {name}!")
        found = True
        break

if not found:
    print("❌ 605088.SH 仍未正确分类")

# 显示机会池详情
if result['opportunities']:
    print("\n📋 机会池详情:")
    for stock in result['opportunities'][:5]:
        print(f"  {stock['code']}: risk={stock.get('risk_score', 0):.2f}, scenario={stock.get('scenario_type', 'N/A')}")