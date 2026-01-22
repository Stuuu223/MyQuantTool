# -*- coding: utf-8 -*-
import sqlite3

print("=" * 80)
print("🔍 检查数据库中的数据")
print("=" * 80)

# 检查 myquant.db
print("\n📊 myquant.db:")
conn = sqlite3.connect('data/myquant.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"  表数量: {len(tables)}")
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
    count = cursor.fetchone()[0]
    print(f"  - {table_name}: {count} 条记录")
conn.close()

# 检查 stock_data.db
print("\n📊 stock_data.db:")
conn = sqlite3.connect('data/stock_data.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"  表数量: {len(tables)}")
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
    count = cursor.fetchone()[0]
    print(f"  - {table_name}: {count} 条记录")
conn.close()

# 检查 Redis
print("\n📊 Redis:")
import redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
try:
    info = r.info()
    print(f"  状态: 运行中")
    print(f"  数据库大小: {info['used_memory_human']}")
    print(f"  键数量: {r.dbsize()}")
    print(f"  连接数: {info['connected_clients']}")
    
    # 列出所有键
    keys = r.keys('*')
    if keys:
        print(f"  键列表:")
        for key in keys:
            key_type = r.type(key)
            print(f"    - {key} ({key_type})")
    else:
        print(f"  键列表: 无")
except Exception as e:
    print(f"  状态: 连接失败 - {e}")