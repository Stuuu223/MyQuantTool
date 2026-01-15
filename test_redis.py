"""
Redis 连接测试脚本

用于测试 Redis 是否正常工作，以及竞价快照功能是否可用
"""

import sys
import json
from datetime import datetime

def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("Redis 连接测试")
    print("=" * 60)
    print()
    
    # 1. 测试 Redis 模块是否安装
    print("[1/4] 检查 Redis 模块...")
    try:
        import redis
        print("✅ Redis 模块已安装")
    except ImportError:
        print("❌ Redis 模块未安装")
        print("请运行: pip install redis")
        return False
    print()
    
    # 2. 测试 Redis 连接
    print("[2/4] 测试 Redis 连接...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Redis 连接成功")
        print(f"   地址: localhost:6379")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        print()
        print("请确保 Redis 正在运行：")
        print("  1. 运行 start_with_redis.bat")
        print("  2. 或手动运行: redis-server")
        return False
    print()
    
    # 3. 测试竞价快照功能
    print("[3/4] 测试竞价快照功能...")
    try:
        from logic.auction_snapshot_manager import AuctionSnapshotManager
        from logic.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db = DatabaseManager()
        
        # 创建竞价快照管理器
        snapshot_manager = AuctionSnapshotManager(db)
        
        if snapshot_manager.is_available:
            print("✅ 竞价快照管理器初始化成功")
            
            # 测试保存竞价快照
            test_code = "600058"
            test_data = {
                'auction_volume': 10000,
                'auction_amount': 1000000,
                'timestamp': datetime.now().timestamp()
            }
            
            success = snapshot_manager.save_auction_snapshot(test_code, test_data)
            if success:
                print(f"✅ 成功保存竞价快照: {test_code}")
            
            # 测试加载竞价快照
            loaded_data = snapshot_manager.load_auction_snapshot(test_code)
            if loaded_data:
                print(f"✅ 成功加载竞价快照: {test_code}")
                print(f"   竞价量: {loaded_data.get('auction_volume', 0)} 手")
                print(f"   竞价金额: {loaded_data.get('auction_amount', 0)} 元")
            
            # 测试删除竞价快照
            snapshot_manager.delete_auction_snapshot(test_code)
            print(f"✅ 成功删除测试快照: {test_code}")
            
        else:
            print("❌ 竞价快照管理器不可用")
            print("   Redis 未连接或未初始化")
            return False
    except Exception as e:
        print(f"❌ 竞价快照功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # 4. 显示 Redis 状态
    print("[4/4] Redis 状态信息...")
    try:
        info = r.info()
        print(f"✅ Redis 版本: {info.get('redis_version', 'unknown')}")
        print(f"✅ 运行时间: {info.get('uptime_in_days', 0)} 天")
        print(f"✅ 连接数: {info.get('connected_clients', 0)}")
        print(f"✅ 内存使用: {info.get('used_memory_human', 'unknown')}")
        
        # 查看竞价快照数量
        keys = r.keys("auction:")
        print(f"✅ 竞价快照数量: {len(keys)}")
    except Exception as e:
        print(f"❌ 获取 Redis 状态失败: {e}")
    print()
    
    # 5. 显示配置信息
    print("=" * 60)
    print("配置信息")
    print("=" * 60)
    
    try:
        with open('config_database.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        redis_config = config.get('redis', {})
        print(f"Redis 主机: {redis_config.get('host', 'localhost')}")
        print(f"Redis 端口: {redis_config.get('port', 6379)}")
        print(f"Redis 数据库: {redis_config.get('db', 0)}")
        print(f"密码: {'已设置' if redis_config.get('password') else '未设置'}")
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
    print()
    
    # 6. 显示快照管理器状态
    print("=" * 60)
    print("快照管理器状态")
    print("=" * 60)
    
    if snapshot_manager.is_available:
        status = snapshot_manager.get_snapshot_status()
        print(f"✅ Redis 可用: {status.get('redis_connected', False)}")
        print(f"✅ 当前日期: {status.get('today', 'unknown')}")
        print(f"✅ 是否竞价时间: {status.get('is_auction_time', False)}")
        print(f"✅ 是否开盘后: {status.get('is_after_market_open', False)}")
    print()
    
    print("=" * 60)
    print("✅ 所有测试通过！Redis 正常工作")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_redis_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)