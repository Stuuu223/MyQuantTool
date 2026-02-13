import sqlite3

conn = sqlite3.connect(r'E:\MyQuantTool\data\auction_snapshots.db')
cursor = conn.cursor()

# 查询最新日期的竞价数据
cursor.execute('''
    SELECT auction_time, code, auction_price, auction_volume, auction_change, volume_ratio
    FROM auction_snapshots
    WHERE date = "2026-02-12"
    LIMIT 5
''')

print("=== 2026-02-12 竞价快照数据样例 ===\n")
print("时间 | 股票代码 | 价格 | 成交量 | 涨跌幅 | 量比")
print("-" * 70)

for row in cursor.fetchall():
    auction_time, code, price, volume, change, vr = row
    change_pct = change * 100 if change is not None else 0
    print(f"{auction_time} | {code} | {price:.2f} | {volume} | {change_pct:+.2f}% | {vr:.2f}")

# 查询统计信息
cursor.execute('''
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN auction_change > 0.03 THEN 1 END) as high_open,
        COUNT(CASE WHEN auction_change < -0.03 THEN 1 END) as low_open,
        AVG(auction_change) as avg_change,
        AVG(volume_ratio) as avg_vr
    FROM auction_snapshots
    WHERE date = "2026-02-12"
''')

print("\n=== 2026-02-12 统计信息 ===\n")
row = cursor.fetchone()
total, high_open, low_open, avg_change, avg_vr = row
print(f"总记录数: {total}")
print(f"高开股票 (涨幅>3%): {high_open}")
print(f"低开股票 (跌幅<3%): {low_open}")
print(f"平均涨幅: {avg_change*100:.2f}%")
print(f"平均量比: {avg_vr:.2f}")

conn.close()