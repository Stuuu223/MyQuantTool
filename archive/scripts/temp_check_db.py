import sqlite3

conn = sqlite3.connect('E:/MyQuantTool/data/auction_snapshots.db')
cursor = conn.cursor()

cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('数据表:', [t[0] for t in tables])

if tables:
    cursor.execute(f'SELECT * FROM {tables[0][0]} LIMIT 3')
    print('示例数据:')
    for row in cursor.fetchall():
        print(row)

    cursor.execute(f'SELECT date, COUNT(*) FROM {tables[0][0]} GROUP BY date')
    print('\n已采集数据:')
    for r in cursor.fetchall():
        print(f'{r[0]}: {r[1]}只')

conn.close()