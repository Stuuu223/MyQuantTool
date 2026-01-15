 """测试数据库管理器
测试Redis、MongoDB、SQLite的集成
"""

import json
from datetime import datetime, timedelta
from logic.database_manager import DatabaseManager, get_db_manager


def test_database_manager():
    """测试数据库管理器"""
    
    print("=" * 60)
    print("测试数据库管理器")
    print("=" * 60)
    
    # 加载配置
    with open('config_database.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 创建数据库管理器
    db = DatabaseManager(config)
    
    # 测试1: SQLite操作
    print("\n📊 测试1: SQLite操作")
    print("-" * 40)
    
    # 保存配置
    db.save_config('test_key', {'value': 123, 'name': 'test'})
    print("✅ 保存配置成功")
    
    # 读取配置
    config_value = db.get_config('test_key')
    print(f"✅ 读取配置: {config_value}")
    
    # 测试2: Redis操作
    print("\n📊 测试2: Redis操作")
    print("-" * 40)
    
    # 保存实时数据
    realtime_data = {
        'symbol': '000001',
        'price': 10.50,
        'volume': 1000000,
        'timestamp': datetime.now().isoformat()
    }
    
    if db.redis_set('test_realtime', realtime_data, expire=60):
        print("✅ 保存实时数据到Redis成功")
    
    # 读取实时数据
    cached_data = db.redis_get('test_realtime')
    print(f"✅ 从Redis读取实时数据: {cached_data}")
    
    # 测试3: MongoDB操作
    print("\n📊 测试3: MongoDB操作")
    print("-" * 40)
    
    # 保存历史数据
    historical_data = [
        {
            'symbol': '000001',
            'date': '2024-01-01',
            'open': 10.0,
            'close': 10.5,
            'high': 10.8,
            'low': 9.9,
            'volume': 1000000
        },
        {
            'symbol': '000001',
            'date': '2024-01-02',
            'open': 10.5,
            'close': 10.3,
            'high': 10.7,
            'low': 10.2,
            'volume': 1200000
        }
    ]
    
    count = db.save_historical_data('stock_daily', historical_data)
    print(f"✅ 保存{count}条历史数据到MongoDB成功")
    
    # 读取历史数据
    retrieved_data = db.get_historical_data('stock_daily', '000001', limit=10)
    print(f"✅ 从MongoDB读取{len(retrieved_data)}条历史数据")
    
    # 测试4: 高级API
    print("\n📊 测试4: 高级API")
    print("-" * 40)
    
    # 保存实时数据（高级API）
    db.save_realtime_data('000001', realtime_data, expire=60)
    print("✅ 使用高级API保存实时数据")
    
    # 获取实时数据（高级API）
    realtime = db.get_realtime_data('000001')
    print(f"✅ 使用高级API获取实时数据: {realtime}")
    
    # 测试5: 缓存预测
    print("\n📊 测试5: 缓存预测")
    print("-" * 40)
    
    prediction_data = {
        'symbol': '000001',
        'features': [1.0, 2.0, 3.0],
        'prediction': 10.6,
        'confidence': 0.85
    }
    
    # 缓存预测
    db.cache_prediction('model_1', {'symbol': '000001'}, prediction_data, expire=3600)
    print("✅ 缓存预测成功")
    
    # 获取缓存的预测
    cached_prediction = db.get_cached_prediction('model_1', {'symbol': '000001'})
    print(f"✅ 获取缓存的预测: {cached_prediction}")
    
    # 测试6: 性能监控
    print("\n📊 测试6: 性能监控")
    print("-" * 40)
    
    # 执行一些操作以生成性能数据
    for i in range(10):
        db.redis_set(f'test_{i}', {'value': i}, expire=60)
        db.redis_get(f'test_{i}')
    
    for i in range(5):
        db.save_config(f'config_{i}', {'value': i})
        db.get_config(f'config_{i}')
    
    # 获取性能统计
    stats = db.get_performance_stats()
    print("\n性能统计:")
    for db_type, data in stats.items():
        print(f"  {db_type}:")
        print(f"    读取: {data['reads']}")
        print(f"    写入: {data['writes']}")
        print(f"    错误: {data['errors']}")
        print(f"    平均耗时: {data['avg_time']:.6f}秒")
        print(f"    吞吐量: {data['ops_per_second']:.2f} ops/秒")
    
    # 打印性能报告
    print("\n" + db.get_performance_report())
    
    # 测试7: 单例模式
    print("\n📊 测试7: 单例模式")
    print("-" * 40)
    
    db1 = get_db_manager(config)
    db2 = get_db_manager(config)
    
    print(f"✅ 单例模式: {db1 is db2}")
    
    # 清理
    print("\n📊 清理测试数据")
    print("-" * 40)
    
    db.redis_delete('test_realtime')
    db.redis_delete('test_0')
    db.redis_delete('test_1')
    # ... 清理其他测试数据
    
    db.close()
    print("✅ 清理完成")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


def test_performance_comparison():
    """性能对比测试"""
    
    print("\n" + "=" * 60)
    print("性能对比测试")
    print("=" * 60)
    
    import time
    
    # 加载配置
    with open('config_database.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db = DatabaseManager(config)
    
    # 测试数据
    test_data = {
        'symbol': '000001',
        'price': 10.50,
        'volume': 1000000,
        'timestamp': datetime.now().isoformat()
    }
    
    # 测试Redis性能
    print("\n📊 Redis性能测试")
    print("-" * 40)
    
    start = time.time()
    for i in range(1000):
        db.redis_set(f'perf_test_{i}', test_data, expire=60)
    redis_write_time = time.time() - start
    
    start = time.time()
    for i in range(1000):
        db.redis_get(f'perf_test_{i}')
    redis_read_time = time.time() - start
    
    print(f"写入1000次: {redis_write_time:.4f}秒 ({1000/redis_write_time:.2f} ops/秒)")
    print(f"读取1000次: {redis_read_time:.4f}秒 ({1000/redis_read_time:.2f} ops/秒)")
    
    # 测试MongoDB性能
    print("\n📊 MongoDB性能测试")
    print("-" * 40)
    
    start = time.time()
    for i in range(100):
        db.mongodb_insert('performance_test', {
            'index': i,
            'data': test_data
        })
    mongodb_write_time = time.time() - start
    
    start = time.time()
    for i in range(10):
        db.mongodb_find('performance_test', {'index': i}, limit=1)
    mongodb_read_time = time.time() - start
    
    print(f"写入100次: {mongodb_write_time:.4f}秒 ({100/mongodb_write_time:.2f} ops/秒)")
    print(f"读取10次: {mongodb_read_time:.4f}秒 ({10/mongodb_read_time:.2f} ops/秒)")
    
    # 测试SQLite性能
    print("\n📊 SQLite性能测试")
    print("-" * 40)
    
    start = time.time()
    for i in range(100):
        db.sqlite_execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
            (f'perf_test_{i}', json.dumps(test_data), datetime.now().isoformat())
        )
    sqlite_write_time = time.time() - start
    
    start = time.time()
    for i in range(100):
        db.sqlite_query("SELECT value FROM config WHERE key = ?", (f'perf_test_{i}',))
    sqlite_read_time = time.time() - start
    
    print(f"写入100次: {sqlite_write_time:.4f}秒 ({100/sqlite_write_time:.2f} ops/秒)")
    print(f"读取100次: {sqlite_read_time:.4f}秒 ({100/sqlite_read_time:.2f} ops/秒)")
    
    # 性能对比总结
    print("\n📊 性能对比总结")
    print("-" * 40)
    print(f"{'数据库':<15} {'写入性能':<20} {'读取性能':<20}")
    print(f"{'-'*55}")
    print(f"{'Redis':<15} {1000/redis_write_time:>10.2f} ops/s {1000/redis_read_time:>10.2f} ops/s")
    print(f"{'MongoDB':<15} {100/mongodb_write_time:>10.2f} ops/s {10/mongodb_read_time:>10.2f} ops/s")
    print(f"{'SQLite':<15} {100/sqlite_write_time:>10.2f} ops/s {100/sqlite_read_time:>10.2f} ops/s")
    
    db.close()
    
    print("\n✅ 性能测试完成！")


if __name__ == "__main__":
    test_database_manager()
    test_performance_comparison()
