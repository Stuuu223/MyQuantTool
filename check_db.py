import sqlite3

conn = sqlite3.connect('E:\\MyQuantTool\\my_quant_cache.sqlite')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("所有表:", tables)

# 查看 daily_kline 表结构
if any('daily_kline' in t for t in tables):
    cursor.execute("PRAGMA table_info(daily_kline)")
    columns = cursor.fetchall()
    print("\ndaily_kline 表结构:")
    for col in columns:
        print(col)

conn.close()