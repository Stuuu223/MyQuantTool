import sqlite3

conn = sqlite3.connect('E:\\MyQuantTool\\data\\stock_data.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("所有表:", tables)

# 查看 daily_kline 表结构
if any('daily_kline' in str(t) for t in tables):
    cursor.execute("PRAGMA table_info(daily_kline)")
    columns = cursor.fetchall()
    print("\ndaily_kline 表结构:")
    for col in columns:
        print(col)

# 查看数据示例
if any('daily_kline' in str(t) for t in tables):
    cursor.execute("SELECT * FROM daily_kline LIMIT 1")
    sample = cursor.fetchone()
    print("\n数据示例:", sample)

conn.close()