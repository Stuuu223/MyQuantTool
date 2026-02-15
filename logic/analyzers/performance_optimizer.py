"""
性能优化模块

优化数据库查询和并发处理
"""

import sqlite3
import threading
from functools import lru_cache
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class PerformanceOptimizer:
    """
    性能优化器
    
    功能：
    1. 数据库连接池管理
    2. 批量查询优化
    3. 缓存管理
    4. 并发处理优化
    """
    
    def __init__(self, db_path: str, pool_size: int = 5):
        """
        初始化性能优化器
        
        Args:
            db_path: 数据库路径
            pool_size: 连接池大小
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.cache = {}
        self.cache_lock = threading.Lock()
        
        # 初始化连接池
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connection_pool.append(conn)
        
        logger.info(f"初始化连接池，大小: {self.pool_size}")
    
    def get_connection(self) -> sqlite3.Connection:
        """
        从连接池获取连接
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        with self.pool_lock:
            if self.connection_pool:
                return self.connection_pool.pop()
            else:
                # 连接池为空，创建新连接
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """
        归还连接到连接池
        
        Args:
            conn: 数据库连接
        """
        with self.pool_lock:
            if len(self.connection_pool) < self.pool_size:
                self.connection_pool.append(conn)
            else:
                conn.close()
    
    def batch_query(self, queries: List[str]) -> List[Dict]:
        """
        批量查询
        
        Args:
            queries: 查询语句列表
        
        Returns:
            list: 查询结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=min(len(queries), self.pool_size)) as executor:
            future_to_query = {
                executor.submit(self._execute_query, query): query
                for query in queries
            }
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"批量查询失败: {query}, 错误: {e}")
                    results.append(None)
        
        return results
    
    def _execute_query(self, query: str) -> Optional[Dict]:
        """
        执行单个查询
        
        Args:
            query: 查询语句
        
        Returns:
            dict: 查询结果
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            result = [dict(row) for row in rows]
            
            return result
        
        except Exception as e:
            logger.error(f"执行查询失败: {query}, 错误: {e}")
            return None
        
        finally:
            if conn:
                self.return_connection(conn)
    
    def cached_query(self, query: str, cache_key: str = None, ttl: int = 300) -> Optional[Dict]:
        """
        缓存查询
        
        Args:
            query: 查询语句
            cache_key: 缓存键
            ttl: 缓存时间（秒）
        
        Returns:
            dict: 查询结果
        """
        import time
        
        # 生成缓存键
        if cache_key is None:
            cache_key = query
        
        # 检查缓存
        with self.cache_lock:
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_data
        
        # 执行查询
        result = self._execute_query(query)
        
        # 更新缓存
        with self.cache_lock:
            self.cache[cache_key] = (result, time.time())
        
        return result
    
    def clear_cache(self):
        """清空缓存"""
        with self.cache_lock:
            self.cache.clear()
        
        logger.info("清空缓存")
    
    def batch_insert(self, table: str, data: List[Dict]) -> bool:
        """
        批量插入
        
        Args:
            table: 表名
            data: 数据列表
        
        Returns:
            bool: 是否成功
        """
        if not data:
            return True
        
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取字段名
            columns = list(data[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            columns_str = ','.join(columns)
            
            # 准备数据
            values = [tuple(row[col] for col in columns) for row in data]
            
            # 批量插入
            cursor.executemany(
                f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                values
            )
            
            conn.commit()
            
            logger.info(f"批量插入 {len(data)} 条数据到 {table}")
            return True
        
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            return False
        
        finally:
            if conn:
                self.return_connection(conn)
    
    def optimize_database(self):
        """优化数据库"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 分析数据库
            cursor.execute("ANALYZE")
            
            # 重建索引
            cursor.execute("REINDEX")
            
            # 压缩数据库
            cursor.execute("VACUUM")
            
            conn.commit()
            
            logger.info("数据库优化完成")
        
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
        
        finally:
            if conn:
                self.return_connection(conn)
    
    def close(self):
        """关闭连接池"""
        with self.pool_lock:
            for conn in self.connection_pool:
                conn.close()
            
            self.connection_pool = []
        
        logger.info("关闭连接池")


class ConcurrentProcessor:
    """
    并发处理器
    
    功能：
    1. 并发执行任务
    2. 任务队列管理
    3. 结果收集
    """
    
    def __init__(self, max_workers: int = 8):
        """
        初始化并发处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.task_lock = threading.Lock()
    
    def submit_task(self, task_id: str, func, *args, **kwargs):
        """
        提交任务
        
        Args:
            task_id: 任务ID
            func: 任务函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Future: 任务Future对象
        """
        future = self.executor.submit(func, *args, **kwargs)
        
        with self.task_lock:
            self.active_tasks[task_id] = {
                'future': future,
                'status': 'RUNNING',
                'submitted_at': time.time()
            }
        
        # 添加回调
        future.add_done_callback(lambda f: self._task_done(task_id))
        
        return future
    
    def _task_done(self, task_id: str):
        """
        任务完成回调
        
        Args:
            task_id: 任务ID
        """
        with self.task_lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['status'] = 'DONE'
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            dict: 任务状态信息
        """
        with self.task_lock:
            return self.active_tasks.get(task_id)
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
        
        Returns:
            Any: 任务结果
        """
        with self.task_lock:
            task_info = self.active_tasks.get(task_id)
        
        if task_info:
            return task_info['future'].result(timeout=timeout)
        else:
            raise ValueError(f"任务不存在: {task_id}")
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
        """
        with self.task_lock:
            task_info = self.active_tasks.get(task_id)
        
        if task_info:
            return task_info['future'].cancel()
        else:
            return False
    
    def shutdown(self, wait: bool = True):
        """
        关闭执行器
        
        Args:
            wait: 是否等待任务完成
        """
        self.executor.shutdown(wait=wait)
        logger.info("关闭并发处理器")