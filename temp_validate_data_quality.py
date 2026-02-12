import sqlite3

conn = sqlite3.connect('E:/MyQuantTool/data/auction_snapshots.db')
cursor = conn.cursor()

# 量比分布
cursor.execute('SELECT volume_ratio FROM auction_snapshots WHERE volume_ratio > 0')
ratios = [r[0] for r in cursor.fetchall()]

print('量比分布:')
bins = [0, 0.5, 1.0, 2.0, 5.0, 10.0, float('inf')]
labels = ['0-0.5', '0.5-1.0', '1.0-2.0', '2.0-5.0', '5.0-10.0', '>10.0']
for i in range(len(bins)-1):
    count = sum(1 for r in ratios if bins[i] < r <= bins[i+1])
    print(f'  {labels[i]}: {count} ({count/len(ratios)*100:.1f}%)')
print(f'中位数: {sorted(ratios)[len(ratios)//2]:.2f}')

# 涨跌幅分布
cursor.execute('SELECT auction_change FROM auction_snapshots WHERE auction_change IS NOT NULL')
changes = [r[0] for r in cursor.fetchall()]

print('\n竞价涨跌幅分布:')
bins = [-float('inf'), -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, float('inf')]
labels = ['<-10%', '-10%~-5%', '-5%~-2%', '-2%~+2%', '+2%~+5%', '+5%~+10%', '>+10%']
for i in range(len(bins)-1):
    count = sum(1 for c in changes if bins[i] < c <= bins[i+1])
    print(f'  {labels[i]}: {count} ({count/len(changes)*100:.1f}%)')
print(f'中位数: {sorted(changes)[len(changes)//2]*100:.2f}%')

conn.close()