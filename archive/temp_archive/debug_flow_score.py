"""调试主力流入评分"""
import json

# 从trade_details.json读取
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("主力流入评分调试:")
print("="*80)

for trade in trades:
    snapshot = trade['buy_snapshot']
    main_inflow = snapshot['flow']['main_net_inflow']  # 单位：元
    
    # 当前公式
    flow_score = min(main_inflow / 100 * 20, 100)
    
    # 正确公式（应该是/100万）
    flow_score_correct = min(main_inflow / 1000000 * 20, 100)
    
    print(f"\n{trade['code']}:")
    print(f"  主力流入: {main_inflow:,}元 = {main_inflow/1e4:.1f}万")
    print(f"  当前公式 ({main_inflow}/100*20): {flow_score:.1f}")
    print(f"  正确公式 ({main_inflow}/1000000*20): {flow_score_correct:.1f}")