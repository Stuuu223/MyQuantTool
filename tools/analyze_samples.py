"""分析现有数据提取黄金样本"""
import pandas as pd

print('=== 数据汇总 ===')

# 1. scan_returns_v45
df_scan = pd.read_csv('data/validation/scan_returns_v45.csv')
print(f'\n1. scan_returns_v45.csv: {len(df_scan)}样本')
print(f'   真龙(final_return>0): {(df_scan["final_return"]>0).sum()}')
print(f'   骗炮(final_return<=0): {(df_scan["final_return"]<=0).sum()}')

# 2. positions
df_pos = pd.read_csv('data/backtest_out/202602/positions.csv')
print(f'\n2. positions.csv: {len(df_pos)}样本')
print(f'   真龙(pnl_pct>0): {(df_pos["pnl_pct"]>0).sum()}')
print(f'   骗炮(pnl_pct<=0): {(df_pos["pnl_pct"]<=0).sum()}')

# 3. violent_surge
df_vs = pd.read_csv('data/validation/violent_surge_samples_detailed.csv')
samples = df_vs[df_vs['lag']==0][['stock_code','ignition_date','sample_return']].drop_duplicates()
print(f'\n3. violent_surge_samples: {len(samples)}样本 (全是成功案例)')

# 提取scan_returns中的样本
print(f'\n=== 建议的24个黄金样本 ===')
# 按分数排序
df_sorted = df_scan.sort_values('entry_score', ascending=False)
print('Top 13 真龙候选 (final_return>0):')
true_dragons = df_sorted[df_sorted['final_return']>0].head(13)
print(true_dragons[['code','first_seen','entry_score','final_return','max_return']].to_string())

print('\nTop 11 骗炮候选 (final_return<=0):')
traps = df_sorted[df_sorted['final_return']<=0].head(11)
print(traps[['code','first_seen','entry_score','final_return','max_return']].to_string())

# 输出黄金样本CSV
golden_samples = pd.concat([
    true_dragons[['code','first_seen']].assign(label=1),
    traps[['code','first_seen']].assign(label=0)
]).rename(columns={'code':'stock_code','first_seen':'date'})
golden_samples.to_csv('data/validation/golden_samples.csv', index=False)
print(f'\n已生成 golden_samples.csv: {len(golden_samples)}个样本')