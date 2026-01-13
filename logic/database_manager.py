"""
统一数据库管理器 - 支持Redis、MongoDB、SQLite
自动路由、性能监控、透明切换
"""

import sqlite3
import json
import time
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    统一数据库管理器
    
    自动路由：
    - Redis: 实时数据、缓存、会话
    - MongoDB: 历史数据、训练数据
    - SQLite: 配置、元数据
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据库管理器
        
        Args:
            config: 数据库配置
                {
                    'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
                    'mongodb': {'host': 'localhost', 'port': 27017, 'db': 'myquant'},
                    'sqlite': {'path': 'data/myquant.db'}
                }
        """
        self.config = config or {}
        self.performance_stats = {
            'redis': {'reads': 0, 'writes': 0, 'errors': 0, 'total_time': 0},
            'mongodb': {'reads': 0, 'writes': 0, 'errors': 0, 'total_time': 0},
            'sqlite': {'reads': 0, 'writes': 0, 'errors': 0, 'total_time': 0}
        }
        
        # 初始化连接
        self._redis_client = None
        self._mongodb_client = None
        self._sqlite_connection = None
        
        self._init_redis()
        self._init_mongodb()
        self._init_sqlite()
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            import redis
            redis_config = self.config.get('redis', {})
            self._redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                decode_responses=True
            )
            # 测试连接
            self._redis_client.ping()
            logger.info("✅ Redis连接成功")
        except ImportError:
            logger.warning("⚠️ Redis未安装，pip install redis")
        except Exception as e:
            logger.warning(f"⚠️ Redis连接失败: {e}")
    
    def _init_mongodb(self):
        """初始化MongoDB连接"""
        try:
            import pymongo
            mongo_config = self.config.get('mongodb', {})
            self._mongodb_client = pymongo.MongoClient(
                host=mongo_config.get('host', 'localhost'),
                port=mongo_config.get('port', 27017)
            )
            # 测试连接
            self._mongodb_client.admin.command('ping')
            logger.info("✅ MongoDB连接成功")
        except ImportError:
            logger.warning("⚠️ MongoDB未安装，pip install pymongo")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB连接失败: {e}")
    
    def _init_sqlite(self):
        """初始化SQLite连接"""
        try:
            sqlite_config = self.config.get('sqlite', {})
            db_path = sqlite_config.get('path', 'data/myquant.db')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._sqlite_connection = sqlite3.connect(db_path, check_same_thread=False)
            logger.info("✅ SQLite连接成功")
        except Exception as e:
            logger.error(f"❌ SQLite连接失败: {e}")
    
    # ==================== Redis 操作 ====================
    
    def redis_set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        Redis: 设置键值
        
        Args:
            key: 键
            value: 值
            expire: 过期时间（秒）
        
        Returns:
            是否成功
        """
        if not self._redis_client:
            return False
        
        start_time = time.time()
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self._redis_client.set(key, value, ex=expire)
            self._update_performance('redis', 'write', time.time() - start_time)
            return True
        except Exception as e:
            logger.error(f"Redis写入失败: {e}")
            self._update_performance('redis', 'error', 0)
            return False
    
    def redis_get(self, key: str) -> Any:
        """
        Redis: 获取键值
        
        Args:
            key: 键
        
        Returns:
            值
        """
        if not self._redis_client:
            return None
        
        start_time = time.time()
        try:
            value = self._redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            self._update_performance('redis', 'read', time.time() - start_time)
            return value
        except Exception as e:
            logger.error(f"Redis读取失败: {e}")
            self._update_performance('redis', 'error', 0)
            return None
    
    def redis_delete(self, key: str) -> bool:
        """Redis: 删除键"""
        if not self._redis_client:
            return False
        
        try:
            self._redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")
            return False
    
    # ==================== MongoDB 操作 ====================
    
    def mongodb_insert(self, collection: str, data: Dict[str, Any]) -> bool:
        """
        MongoDB: 插入文档
        
        Args:
            collection: 集合名
            data: 文档数据
        
        Returns:
            是否成功
        """
        if not self._mongodb_client:
            return False
        
        start_time = time.time()
        try:
            mongo_config = self.config.get('mongodb', {})
            db = self._mongodb_client[mongo_config.get('db', 'myquant')]
            collection = db[collection]
            
            # 添加时间戳
            data['created_at'] = datetime.now()
            data['updated_at'] = datetime.now()
            
            collection.insert_one(data)
            self._update_performance('mongodb', 'write', time.time() - start_time)
            return True
        except Exception as e:
            logger.error(f"MongoDB插入失败: {e}")
            self._update_performance('mongodb', 'error', 0)
            return False
    
    def mongodb_find(self, collection: str, query: Dict[str, Any] = None,
                    limit: int = 100, sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """
        MongoDB: 查找文档
        
        Args:
            collection: 集合名
            query: 查询条件
            limit: 限制数量
            sort: 排序 [('field', direction)]
        
        Returns:
            文档列表
        """
        if not self._mongodb_client:
            return []
        
        start_time = time.time()
        try:
            mongo_config = self.config.get('mongodb', {})
            db = self._mongodb_client[mongo_config.get('db', 'myquant')]
            coll = db[collection]
            
            cursor = coll.find(query or {})
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            # 转换ObjectId为字符串
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            self._update_performance('mongodb', 'read', time.time() - start_time)
            return results
        except Exception as e:
            logger.error(f"MongoDB查询失败: {e}")
            self._update_performance('mongodb', 'error', 0)
            return []
    
    def mongodb_update(self, collection: str, query: Dict[str, Any],
                     update: Dict[str, Any]) -> bool:
        """
        MongoDB: 更新文档
        
        Args:
            collection: 集合名
            query: 查询条件
            update: 更新内容
        
        Returns:
            是否成功
        """
        if not self._mongodb_client:
            return False
        
        start_time = time.time()
        try:
            mongo_config = self.config.get('mongodb', {})
            db = self._mongodb_client[mongo_config.get('db', 'myquant')]
            coll = db[collection]
            
            update['updated_at'] = datetime.now()
            coll.update_one(query, {'$set': update})
            
            self._update_performance('mongodb', 'write', time.time() - start_time)
            return True
        except Exception as e:
            logger.error(f"MongoDB更新失败: {e}")
            self._update_performance('mongodb', 'error', 0)
            return False
    
    # ==================== SQLite 操作 ====================
    
    def sqlite_execute(self, sql: str, params: tuple = None) -> bool:
        """
        SQLite: 执行SQL
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            是否成功
        """
        if not self._sqlite_connection:
            return False
        
        start_time = time.time()
        try:
            cursor = self._sqlite_connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            self._sqlite_connection.commit()
            self._update_performance('sqlite', 'write', time.time() - start_time)
            return True
        except Exception as e:
            logger.error(f"SQLite执行失败: {e}")
            self._update_performance('sqlite', 'error', 0)
            return False
    
    def sqlite_query(self, sql: str, params: tuple = None) -> List[tuple]:
        """
        SQLite: 查询
        
        Args:
            sql: SQL语句
            params: 参数
        
        Returns:
            查询结果
        """
        if not self._sqlite_connection:
            return []
        
        start_time = time.time()
        try:
            cursor = self._sqlite_connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            self._update_performance('sqlite', 'read', time.time() - start_time)
            return results
        except Exception as e:
            logger.error(f"SQLite查询失败: {e}")
            self._update_performance('sqlite', 'error', 0)
            return []
    
    # ==================== 高级API - 自动路由 ====================
    
    def save_realtime_data(self, symbol: str, data: Dict[str, Any], 
                         expire: int = 60) -> bool:
        """
        保存实时数据（自动路由到Redis）
        
        Args:
            symbol: 股票代码
            data: 实时数据
            expire: 过期时间（秒）
        
        Returns:
            是否成功
        """
        key = f"realtime:{symbol}"
        return self.redis_set(key, data, expire)
    
    def get_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时数据（从Redis）
        
        Args:
            symbol: 股票代码
        
        Returns:
            实时数据
        """
        key = f"realtime:{symbol}"
        return self.redis_get(key)
    
    def save_historical_data(self, collection: str, data: List[Dict[str, Any]]) -> int:
        """
        保存历史数据（自动路由到MongoDB）
        
        Args:
            collection: 集合名
            data: 历史数据列表
        
        Returns:
            成功插入的数量
        """
        success_count = 0
        for item in data:
            if self.mongodb_insert(collection, item):
                success_count += 1
        return success_count
    
    def get_historical_data(self, collection: str, symbol: str, 
                          limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取历史数据（从MongoDB）
        
        Args:
            collection: 集合名
            symbol: 股票代码
            limit: 限制数量
        
        Returns:
            历史数据
        """
        return self.mongodb_find(
            collection,
            query={'symbol': symbol},
            limit=limit,
            sort=[('date', -1)]
        )
    
    def save_config(self, key: str, value: Any) -> bool:
        """
        保存配置（自动路由到SQLite）
        
        Args:
            key: 配置键
            value: 配置值
        
        Returns:
            是否成功
        """
        return self.sqlite_execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat())
        )
    
    def get_config(self, key: str) -> Optional[Any]:
        """
        获取配置（从SQLite）
        
        Args:
            key: 配置键
        
        Returns:
            配置值
        """
        results = self.sqlite_query(
            "SELECT value FROM config WHERE key = ?",
            (key,)
        )
        if results:
            return json.loads(results[0][0])
        return None
    
    def cache_prediction(self, model_id: str, input_data: Dict[str, Any],
                      prediction: Any, expire: int = 3600) -> bool:
        """
        缓存模型预测（Redis）
        
        Args:
            model_id: 模型ID
            input_data: 输入数据
            prediction: 预测结果
            expire: 过期时间（秒）
        
        Returns:
            是否成功
        """
        # 生成缓存键
        import hashlib
        key_str = f"{model_id}:{json.dumps(input_data, sort_keys=True)}"
        cache_key = f"prediction:{hashlib.md5(key_str.encode()).hexdigest()}"
        
        cache_data = {
            'model_id': model_id,
            'input': input_data,
            'prediction': prediction,
            'cached_at': datetime.now().isoformat()
        }
        
        return self.redis_set(cache_key, cache_data, expire)
    
    def get_cached_prediction(self, model_id: str, 
                            input_data: Dict[str, Any]) -> Optional[Any]:
        """
        获取缓存的预测（Redis）
        
        Args:
            model_id: 模型ID
            input_data: 输入数据
        
        Returns:
            缓存的预测
        """
        import hashlib
        key_str = f"{model_id}:{json.dumps(input_data, sort_keys=True)}"
        cache_key = f"prediction:{hashlib.md5(key_str.encode()).hexdigest()}"
        
        cached = self.redis_get(cache_key)
        if cached:
            return cached.get('prediction')
        return None
    
    # ==================== 性能监控 ====================
    
    def _update_performance(self, db_type: str, operation: str, duration: float):
        """更新性能统计"""
        if operation == 'read':
            self.performance_stats[db_type]['reads'] += 1
        elif operation == 'write':
            self.performance_stats[db_type]['writes'] += 1
        elif operation == 'error':
            self.performance_stats[db_type]['errors'] += 1
        
        self.performance_stats[db_type]['total_time'] += duration
    
    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取性能统计
        
        Returns:
            性能统计数据
        """
        stats = {}
        for db_type, data in self.performance_stats.items():
            total_ops = data['reads'] + data['writes']
            avg_time = data['total_time'] / total_ops if total_ops > 0 else 0
            
            stats[db_type] = {
                'reads': data['reads'],
                'writes': data['writes'],
                'errors': data['errors'],
                'total_time': data['total_time'],
                'avg_time': avg_time,
                'ops_per_second': total_ops / data['total_time'] if data['total_time'] > 0 else 0
            }
        
        return stats
    
    def get_performance_report(self) -> str:
        """
        获取性能报告
        
        Returns:
            格式化的性能报告
        """
        stats = self.get_performance_stats()
        
        report = "📊 数据库性能报告\n"
        report += "=" * 50 + "\n\n"
        
        for db_type, data in stats.items():
            report += f"🔹 {db_type.upper()}\n"
            report += f"  读取次数: {data['reads']}\n"
            report += f"  写入次数: {data['writes']}\n"
            report += f"  错误次数: {data['errors']}\n"
            report += f"  总耗时: {data['total_time']:.4f}秒\n"
            report += f"  平均耗时: {data['avg_time']:.6f}秒\n"
            report += f"  吞吐量: {data['ops_per_second']:.2f} ops/秒\n\n"
        
        return report
    
    # ==================== 初始化 ====================
    
    def initialize_schema(self):
        """初始化数据库schema"""
        # SQLite schema
        self.sqlite_execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        self.sqlite_execute('''
            CREATE TABLE IF NOT EXISTS performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                db_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        logger.info("✅ 数据库schema初始化完成")
    
    # ==================== 清理 ====================
    
    def close(self):
        """关闭所有连接"""
        if self._redis_client:
            self._redis_client.close()
        
        if self._mongodb_client:
            self._mongodb_client.close()
        
        if self._sqlite_connection:
            self._sqlite_connection.close()
        
        logger.info("✅ 所有数据库连接已关闭")


# 全局实例
_db_manager = None


def get_db_manager(config: Dict[str, Any] = None) -> DatabaseManager:
    """
    获取数据库管理器实例（单例）
    
    Args:
        config: 数据库配置
    
    Returns:
        DatabaseManager实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
        _db_manager.initialize_schema()
    return _db_manager