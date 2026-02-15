"""
游资席位分析模块
分析龙虎榜游资、游资操作模式、识别知名游资"""

import pandas as pd
import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Optional
from logic.data.data_manager import DataManager
from logic.utils.logger import get_logger, log_execution_time, performance_context

# 获取日志记录器
logger = get_logger(__name__)

try:
    # diskcache is SQLite-backed persistent cache
    from diskcache import FanoutCache
except ImportError as e:
    raise ImportError("Please install diskcache: pip install diskcache") from e


@dataclass
class CacheResult:
    """缓存结果"""
    value: Any
    hit: bool


class DiskCacheManager:
    """
    本地持久化缓存（SQLite-backed）。
    - 适合缓存 pandas.DataFrame / dict / list 等可 pickle 对象
    - 支持 TTL expire
    - FanoutCache 适合多线程/多进程并发访问
    """

    _instance = None
    _cache = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        cache_dir: str = ".myquant_cache",
        shards: int = 8,
        size_limit_bytes: int = 5 * 1024**3,  # 5GB
        enabled: bool = True,
    ):
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.enabled = enabled
        self.cache_dir = cache_dir

        if not self.enabled:
            self._cache = None
            self._initialized = True
            return

        os.makedirs(cache_dir, exist_ok=True)
        self._cache = FanoutCache(
            directory=cache_dir,
            shards=shards,
            size_limit=size_limit_bytes,
            statistics=True,
        )
        self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存数据"""
        if not self.enabled or self._cache is None:
            return default
        return self._cache.get(key, default=default)

    def set(self, key: str, value: Any, expire: Optional[int] = None, tag: Optional[str] = None) -> bool:
        """设置缓存数据"""
        if not self.enabled or self._cache is None:
            return False
        # expire: seconds
        self._cache.set(key, value, expire=expire, tag=tag)
        return True

    def get_or_set(
        self,
        key: str,
        loader: Callable[[], Any],
        expire: Optional[int] = None,
        tag: Optional[str] = None,
        cache_none: bool = False,
    ) -> CacheResult:
        """
        获取或设置缓存
        - cache_none=False：loader 返回 None 时不写入缓存（避免把临时失败缓存住）
        """
        cached = self.get(key, default=None)
        if cached is not None:
            return CacheResult(cached, True)

        value = loader()
        if value is None and not cache_none:
            return CacheResult(None, False)

        self.set(key, value, expire=expire, tag=tag)
        return CacheResult(value, False)

    def invalidate_prefix(self, prefix: str) -> int:
        """
        删除所有以 prefix 开头的 key（用于按日期/模块批量失效）。
        """
        if not self.enabled or self._cache is None:
            return 0
        keys = list(self._cache.iterkeys())
        removed = 0
        for k in keys:
            if isinstance(k, str) and k.startswith(prefix):
                if self._cache.delete(k):
                    removed += 1
        return removed

    def invalidate_tag(self, tag: str) -> int:
        """
        删除所有指定 tag 的缓存条目
        """
        if not self.enabled or self._cache is None:
            return 0
        return self._cache.evict(tag)

    def clear(self) -> None:
        """清空所有缓存"""
        if self._cache is not None:
            self._cache.clear()

    def close(self) -> None:
        """关闭缓存"""
        if self._cache is not None:
            self._cache.close()

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.enabled or self._cache is None:
            return {'enabled': False}

        stats = self._cache.stats()
        return {
            'enabled': True,
            'cache_dir': self.cache_dir,
            'size_limit_bytes': self._cache.size_limit,
            'hits': stats.get('hits', 0),
            'misses': stats.get('misses', 0),
            'total_keys': len(list(self._cache.iterkeys())),
            'hit_rate': f"{stats.get('hits', 0) / max(stats.get('hits', 0) + stats.get('misses', 0), 1) * 100:.2f}%"
        }


class CacheManager:
    """缓存管理器 - 使用SQLite缓存API数据"""

    def __init__(self, db_path='data/cache.db'):
        """初始化缓存管理器"""
        self.db_path = db_path
        self._init_db()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get(self, key):
        """从缓存获取数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT data, expires_at, access_count FROM api_cache
            WHERE key = ? AND expires_at > CURRENT_TIMESTAMP
        ''', (key,))
        result = cursor.fetchone()
        
        if result:
            # 更新访问统计
            cursor.execute('''
                UPDATE api_cache 
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE key = ?
            ''', (key,))
            conn.commit()
            
            self.stats['hits'] += 1
            conn.close()
            return json.loads(result[0])
        
        self.stats['misses'] += 1
        conn.close()
        return None

    def set(self, key, data, ttl=3600):
        """设置缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(seconds=ttl)
        cursor.execute('''
            INSERT OR REPLACE INTO api_cache (key, data, expires_at, access_count, last_accessed)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''', (key, json.dumps(data), expires_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        self.stats['sets'] += 1

    def delete(self, key):
        """删除缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM api_cache WHERE key = ?', (key,))
        conn.commit()
        conn.close()
        
        self.stats['deletes'] += 1

    def clear_expired(self):
        """清理过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM api_cache WHERE expires_at <= CURRENT_TIMESTAMP')
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count

    def get_stats(self):
        """获取缓存统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取缓存总数
        cursor.execute('SELECT COUNT(*) FROM api_cache')
        total_count = cursor.fetchone()[0]
        
        # 获取过期缓存数
        cursor.execute('SELECT COUNT(*) FROM api_cache WHERE expires_at <= CURRENT_TIMESTAMP')
        expired_count = cursor.fetchone()[0]
        
        conn.close()
        
        hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
        
        return {
            'total_keys': total_count,
            'expired_keys': expired_count,
            'active_keys': total_count - expired_count,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes']
        }

    def clear_all(self):
        """清空所有缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM api_cache')
        conn.commit()
        conn.close()
        
        # 重置统计
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }


def retry_with_backoff(max_retries=3, backoff_factor=2):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        raise

                    wait_time = backoff_factor ** retries
                    print(f"函数 {func.__name__} 执行失败，{wait_time} 秒后进行第 {retries + 1} 次重试...")
                    time.sleep(wait_time)

            return None
        return wrapper
    return decorator


class CapitalAnalyzer:
    """游资席位分析模块"""

    # 知名游资席位列表（包含常见变体）
    FAMOUS_CAPITALISTS = {
        "章盟主": [
            "中信证券股份有限公司杭州延安路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "国泰君安证券股份有限公司上海江苏路证券营业部",
            "国泰君安证券股份有限公司上海江苏",
            "中信证券杭州延安路",
            "国泰君安上海江苏路",
            "国泰君安上海分公司"
        ],
        "方新侠": [
            "兴业证券股份有限公司西安分公司",
            "中信证券股份有限公司西安朱雀大街证券营业部",
            "兴业证券西安分公司",
            "中信证券西安朱雀大街",
            "兴业证券股份有限公司"
        ],
        "徐翔": [
            "国泰君安证券股份有限公司上海福山路证券营业部",
            "光大证券股份有限公司宁波解放南路证券营业部",
            "国泰君安上海福山路",
            "光大证券宁波解放南路",
            "国泰君安上海福建路"
        ],
        "赵老哥": [
            "中国银河证券股份有限公司绍兴证券营业部",
            "华泰证券股份有限公司浙江分公司",
            "银河证券绍兴",
            "华泰证券浙江分公司",
            "中国银河证券绍兴"
        ],
        "炒股养家": [
            "中信证券股份有限公司上海淮海中路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "中信证券上海淮海中路",
            "国泰君安上海分公司"
        ],
        "成都": [
            "华泰证券股份有限公司成都蜀金路证券营业部",
            "国泰君安证券股份有限公司成都分公司",
            "中信证券成都蜀金路",
            "国泰君安成都分公司"
        ],
        "深圳": [
            "光大证券股份有限公司深圳金田路证券营业部",
            "长江证券股份有限公司深圳科苑路证券营业部",
            "光大证券深圳金田路",
            "长江证券深圳科苑路",
            "光大证券深圳"
        ],
        "乔帮主": [
            "中国中金财富证券有限公司深圳分公司",
            "华泰证券股份有限公司深圳彩田路超算中心证券营业部",
            "中金财富深圳",
            "华泰证券深圳彩田路",
            "中国中金财富深圳"
        ],
        "作手新一": [
            "国泰君安证券股份有限公司南京太平南路证券营业部",
            "华泰证券股份有限公司南京江东中路证券营业部",
            "国泰君安南京太平南路",
            "华泰证券南京江东中路",
            "国泰君安南京"
        ],
        "小鳄鱼": [
            "中国银河证券股份有限公司北京中关村大街证券营业部",
            "中信证券股份有限公司北京总部证券营业部",
            "银河证券北京中关村大街",
            "中信证券北京总部",
            "银河证券北京"
        ],
        "拉萨帮": [
            "东方财富证券股份有限公司拉萨东环路第二证券营业部",
            "东方财富证券股份有限公司拉萨团结路第一证券营业部",
            "东方财富证券股份有限公司拉萨东环路第一证券营业部",
            "东方财富证券股份有限公司拉萨团结路第二证券营业部",
            "东方财富拉萨东环路第二",
            "东方财富拉萨团结路第一",
            "东方财富拉萨"
        ],
        "机构": [
            "深股通专用",
            "沪股通专用",
            "机构专用",
            "机构专用席位"
        ],
        "华泰": [
            "华泰证券股份有限公司南京庐山路证券营业部",
            "华泰证券股份有限公司浙江分公司",
            "华泰证券股份有限公司成都蜀金路证券营业部",
            "华泰证券股份有限公司深圳彩田路超算中心证券营业部",
            "华泰证券南京庐山路",
            "华泰证券浙江分公司",
            "华泰证券成都蜀金路",
            "华泰证券深圳彩田路"
        ],
        "国盛": [
            "国盛证券有限责任公司宁波桑田路证券营业部",
            "国盛证券宁波桑田路"
        ],
        "开源": [
            "开源证券股份有限公司西安西大街证券营业部",
            "开源证券西安西大街"
        ],
        "国信": [
            "国信证券股份有限公司浙江互联网分公司",
            "国信证券浙江互联网分公司"
        ],
        "爱建": [
            "爱建证券有限责任公司上海浦东新区前滩大道证券营业部",
            "爱建证券上海浦东新区前滩大道"
        ]
    }

    # 初始化缓存管理器
    cache = CacheManager()

    @staticmethod
    @log_execution_time
    def analyze_longhubu_capital(date=None):
        """
        分析龙虎榜游资
        返回当日龙虎榜中的游资席位分析

        数据源策略（三层）：
        1. 第一层：东方财富接口 - 使用 stock_lhb_detail_em 获取龙虎榜股票，然后使用 stock_lhb_yyb_detail_em 按营业部代码查询详细数据
        2. 第二层：新浪接口 - 使用 stock_lhb_yytj_sina 获取累积统计数据
        3. 第三层：本地缓存 - 如果前两层都失败，返回历史数据
        """
        logger.info(f"开始分析龙虎榜游资，日期: {date or '最新'}")

        try:
            import akshare as ak
            from datetime import datetime
            import time

            # 检查旧缓存（兼容性）
            cache_key = f"lhb_capital_{date or 'latest'}"
            cached_data = CapitalAnalyzer.cache.get(cache_key)
            if cached_data:
                logger.info(f"从旧缓存获取数据: {cache_key}")
                return cached_data

            # ===== 第一层：东方财富接口 =====
            logger.info("=" * 60)
            logger.info("第一层数据源：东方财富接口")
            logger.info("=" * 60)

            # 使用 diskcache 缓存龙虎榜列表
            disk_cache = DiskCacheManager()

            # 获取龙虎榜数据
            try:
                if date:
                    if isinstance(date, str):
                        # 支持多种日期格式
                        if '-' in date:
                            # %Y-%m-%d 格式
                            date_obj = pd.to_datetime(date)
                            date_str = date_obj.strftime("%Y%m%d")
                        else:
                            date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")

                    # 使用 diskcache 缓存龙虎榜列表
                    lhb_cache_key = f"lhb:list:{date_str}"
                    cache_result = disk_cache.get_or_set(
                        lhb_cache_key,
                        loader=lambda: ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str),
                        expire=86400,  # 24小时
                        tag=f"date:{date_str}"
                    )

                    if cache_result.hit:
                        logger.info(f"[缓存命中] 从 diskcache 获取 {date_str} 的龙虎榜数据")
                    else:
                        logger.info(f"[缓存未命中] 从 API 获取 {date_str} 的龙虎榜数据")

                    lhb_df = cache_result.value
                    logger.info(f"获取 {date_str} 的龙虎榜数据，共 {len(lhb_df)} 条记录")
                else:
                    # 获取最近几天的数据
                    today = datetime.now()
                    date_str = today.strftime("%Y%m%d")

                    # 使用 diskcache 缓存龙虎榜列表
                    lhb_cache_key = f"lhb:list:{date_str}"
                    cache_result = disk_cache.get_or_set(
                        lhb_cache_key,
                        loader=lambda: ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str),
                        expire=86400,  # 24小时
                        tag=f"date:{date_str}"
                    )

                    if cache_result.hit:
                        logger.info(f"[缓存命中] 从 diskcache 获取今日龙虎榜数据")
                    else:
                        logger.info(f"[缓存未命中] 从 API 获取今日龙虎榜数据")

                    lhb_df = cache_result.value
                    logger.info(f"获取今日龙虎榜数据，共 {len(lhb_df)} 条记录")

                    # 如果今日无数据，尝试获取昨天
                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        yesterday_str = yesterday.strftime("%Y%m%d")

                        # 使用 diskcache 缓存昨日龙虎榜列表
                        lhb_cache_key = f"lhb:list:{yesterday_str}"
                        cache_result = disk_cache.get_or_set(
                            lhb_cache_key,
                            loader=lambda: ak.stock_lhb_detail_em(start_date=yesterday_str, end_date=yesterday_str),
                            expire=86400,  # 24小时
                            tag=f"date:{yesterday_str}"
                        )

                        if cache_result.hit:
                            logger.info(f"[缓存命中] 从 diskcache 获取昨日龙虎榜数据")
                        else:
                            logger.info(f"[缓存未命中] 从 API 获取昨日龙虎榜数据")

                        lhb_df = cache_result.value
                        logger.info(f"今日无数据，获取昨日龙虎榜数据，共 {len(lhb_df)} 条记录")

                        date_str = yesterday_str
            except Exception as e:
                logger.error(f"获取龙虎榜数据失败: {e}", exc_info=True)
                lhb_df = None

            # 如果龙虎榜数据为空，尝试第二层数据源
            if lhb_df is None or lhb_df.empty:
                logger.warning("龙虎榜数据为空，切换到第二层数据源")
                return CapitalAnalyzer._get_sina_data()

            logger.info(f"[OK] 获取 {len(lhb_df)} 只龙虎榜股票")

            # ===== 方案1：按股票逐个查询营业部明细（并发优化） =====
            logger.info("=" * 60)
            logger.info("方案1：按股票逐个查询营业部明细（并发查询）")
            logger.info("=" * 60)

            # 使用并发查询获取营业部明细
            seat_detail_result = CapitalAnalyzer._get_seat_detail_by_stock_concurrent(lhb_df, date_str)
            if seat_detail_result is not None:
                return seat_detail_result

            # 如果并发查询失败，切换到第二层数据源
            logger.warning("并发查询营业部明细失败，切换到第二层数据源")
            return CapitalAnalyzer._get_sina_data()

        except Exception as e:
            logger.error(f"分析龙虎榜游资失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '分析过程中发生错误，请稍后重试'
            }

    @staticmethod
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def _get_seat_detail_by_stock_concurrent(lhb_df, date_str, max_workers=20):
        """
        ✅ 优化版本：按股票逐个查询营业部明细（并发优化）
        
        核心优化：
        1. max_workers 从 10 提升到 20 (+100% 吞吐量)
        2. 添加超时保护 (总 30s，单 5s)
        3. 优化异常处理 (分类处理，不中断流程)
        4. 添加性能日志

        Args:
            lhb_df: 龙虎榜股票列表
            date_str: 日期字符串（格式：YYYYMMDD）
            max_workers: 最大并发线程数 (优化值：20)

        Returns:
            游资分析结果
        """
        try:
            import akshare as ak
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from datetime import datetime as dt

            all_seats = []
            success_count = 0
            fail_count = 0
            timeout_count = 0
            
            start_time = dt.now()
            logger.info(f"📍 开始查询 {len(lhb_df)} 只股票的营业部明细 (max_workers={max_workers})")

            def fetch_seat_detail(stock_info):
                """获取单个股票的营业部明细"""
                code = stock_info['代码']
                name = stock_info['名称']

                try:
                    # 使用 diskcache 缓存单股营业部明细
                    disk_cache = DiskCacheManager()
                    seat_cache_key = f"lhb:seat_detail:{date_str}:{code}"

                    # 尝试从缓存获取
                    cached_seats = disk_cache.get(seat_cache_key)
                    if cached_seats is not None:
                        logger.debug(f"  [缓存命中] {name}({code}) 营业部明细")
                        return cached_seats, True

                    # 缓存未命中，调用 API
                    seats = ak.stock_lhb_stock_detail_em(
                        symbol=code,
                        date=date_str
                    )

                    if not seats.empty:
                        # 添加股票信息
                        seats['股票代码'] = code
                        seats['股票名称'] = name
                        seats['上榜日'] = date_str

                        # 缓存结果
                        disk_cache.set(seat_cache_key, seats, expire=86400, tag=f"date:{date_str}")
                        logger.debug(f"  [缓存未命中] {name}({code}) 营业部明细，已缓存")

                        return seats, True
                    else:
                        return None, False
                except Exception as e:
                    logger.debug(f"  [WARN] {name}({code}) 查询失败: {e}")
                    return None, False

            # 并发查询（提升到 20 workers）
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(fetch_seat_detail, row): idx
                    for idx, row in lhb_df.iterrows()
                }

                # 设置总超时为 30 秒
                try:
                    for future in as_completed(futures, timeout=30):
                        try:
                            result, success = future.result(timeout=5)  # 单个5秒
                            if success and result is not None:
                                all_seats.append(result)
                                success_count += 1
                                
                                # 每 5 个成功打印一次进度
                                if success_count % 5 == 0:
                                    logger.info(f"  ✅ 进度: {success_count} 成功，{fail_count} 失败，{timeout_count} 超时")
                            else:
                                fail_count += 1
                                
                        except TimeoutError:
                            timeout_count += 1
                        except Exception as e:
                            fail_count += 1
                            logger.debug(f"  处理结果时出错: {e}")
                            
                except TimeoutError:
                    logger.warning(f"  ⚠️  总查询超时 (30秒)，停止等待更多结果")
                    
            # 计算统计信息
            elapsed = (dt.now() - start_time).total_seconds()
            total_records = sum(len(df) for df in all_seats if df is not None)
            
            logger.info(f"""
✅ 并发查询完成
   - 查询结果: {success_count} 成功，{fail_count} 失败，{timeout_count} 超时
   - 获取记录: {total_records} 条营业部数据
   - 耗时: {elapsed:.1f}秒
   - 速度: {len(lhb_df)/elapsed:.2f} 股票/秒
           - 目标: < 15秒 {'[SUCCESS]' if elapsed < 15 else '[WARNING]' if elapsed < 20 else '[ERROR]'}""")
            
            if not all_seats:
                logger.error("[ERROR] 所有股票的营业部明细查询均失败")
                return None

            # 合并所有营业部数据
            df_all = pd.concat(all_seats, ignore_index=True)
            logger.info(f"[OK] 总计获取 {len(df_all)} 条营业部明细数据")
            logger.info(f"[OK] 营业部明细列名: {df_all.columns.tolist()}")

            # 分析营业部数据
            return CapitalAnalyzer._analyze_seat_data_from_stock_detail(df_all, date_str)

        except Exception as e:
            logger.error(f"[ERROR] 并发查询营业部明细失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def _analyze_seat_data_from_stock_detail(df_all, date_str=None):
        """
        分析从股票明细获取的营业部数据

        Args:
            df_all: 营业部明细数据
            date_str: 日期字符串（用于缓存）

        Returns:
            游资分析结果
        """
        try:
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            # ✅ 关键修复：检查正确的列名
            seat_col = None
            if '交易营业部名称' in df_all.columns:
                seat_col = '交易营业部名称'
            elif '营业部名称' in df_all.columns:
                seat_col = '营业部名称'
            else:
                logger.error(f"营业部明细数据中没有'营业部名称'列，可用列: {df_all.columns.tolist()}")
                return None

            logger.info(f"[OK] 使用列名: {seat_col}")
            logger.info(f"[OK] 营业部明细列名: {df_all.columns.tolist()}")

            # 分析每条营业部记录
            for _, row in df_all.iterrows():
                seat_name = str(row.get(seat_col, ''))

                if not seat_name or seat_name == 'nan':
                    continue

                # 使用智能匹配算法
                capital_name, match_score = CapitalAnalyzer._match_capital_seat(seat_name)

                # 只保留匹配度较高的结果（> 0.3）
                if capital_name and match_score > 0.3:
                    matched_count += 1

                    # 统计游资操作
                    if capital_name not in capital_stats:
                        capital_stats[capital_name] = {
                            '买入次数': 0,
                            '卖出次数': 0,
                            '买入金额': 0,
                            '卖出金额': 0,
                            '操作股票': []
                        }

                    # 获取买入和卖出金额
                    try:
                        buy_amount = float(row.get('买入金额', 0) or row.get('买入', 0) or 0)
                    except:
                        buy_amount = 0
                    
                    try:
                        sell_amount = float(row.get('卖出金额', 0) or row.get('卖出', 0) or 0)
                    except:
                        sell_amount = 0

                    # 获取买入和卖出次数
                    buy_count = 1 if buy_amount > 0 else 0
                    sell_count = 1 if sell_amount > 0 else 0

                    if buy_amount > 0:
                        capital_stats[capital_name]['买入次数'] += buy_count
                        capital_stats[capital_name]['买入金额'] += buy_amount
                    if sell_amount > 0:
                        capital_stats[capital_name]['卖出次数'] += sell_count
                        capital_stats[capital_name]['卖出金额'] += sell_amount

                    # 记录操作股票
                    stock_info = {
                        '代码': row.get('股票代码', ''),
                        '名称': row.get('股票名称', ''),
                        '日期': row.get('上榜日', ''),
                        '买入金额': buy_amount,
                        '卖出金额': sell_amount,
                        '净买入': buy_amount - sell_amount
                    }
                    capital_stats[capital_name]['操作股票'].append(stock_info)

                    capital_analysis.append({
                        '游资名称': capital_name,
                        '营业部名称': seat_name,
                        '股票代码': row.get('股票代码', ''),
                        '股票名称': row.get('股票名称', ''),
                        '上榜日': row.get('上榜日', ''),
                        '买入金额': buy_amount,
                        '卖出金额': sell_amount,
                        '净买入': buy_amount - sell_amount
                    })

            # 计算游资统计
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['买入金额'] - stats['卖出金额']
                total_trades = stats['买入次数'] + stats['卖出次数']

                # 判断操作风格
                if stats['买入金额'] > stats['卖出金额'] * 2:
                    style = "激进买入"
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖出"
                elif net_flow > 0:
                    style = "偏多"
                else:
                    style = "偏空"

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次数': total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票数': len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            logger.info(f"[OK] 分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游资")

            result = {
                '数据状态': '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录数': matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(df_all),
                '说明': f'通过并发查询获取营业部明细，在 {len(df_all)} 条记录中找到 {matched_count} 条游资操作记录'
            }

            # 保存到缓存
            if date_str:
                cache_key = f"lhb_capital_concurrent_{date_str}"
                CapitalAnalyzer.cache.set(cache_key, result, ttl=3600)  # 缓存1小时

            return result

        except Exception as e:
            logger.error(f"[ERROR] 分析营业部明细数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def _get_sina_data():
        """
        第二层数据源：新浪接口（带重试机制）
        获取营业部统计数据
        """
        try:
            import akshare as ak

            logger.info("=" * 60)
            logger.info("第二层数据源：新浪接口")
            logger.info("=" * 60)

            # 检查缓存
            cache_key = "sina_yyb_stats_latest"
            cached_data = CapitalAnalyzer.cache.get(cache_key)
            if cached_data:
                logger.info(f"从缓存获取新浪营业部数据")
                yyb_stats = pd.DataFrame(cached_data)
            else:
                # 使用新浪接口获取营业部统计数据
                yyb_stats = ak.stock_lhb_yytj_sina(symbol='5')  # 获取最近5天的数据
                if not yyb_stats.empty:
                    # 缓存数据，TTL为1小时
                    CapitalAnalyzer.cache.set(cache_key, yyb_stats.to_dict('records'), ttl=3600)

            if yyb_stats.empty:
                logger.warning("新浪接口返回空数据，切换到第三层数据源")
                return CapitalAnalyzer._get_historical_data()

            logger.info(f"获取到 {len(yyb_stats)} 条营业部统计数据")
            logger.info(f"新浪数据列名: {yyb_stats.columns.tolist()}")

            return CapitalAnalyzer._analyze_sina_seat_data(yyb_stats)

        except Exception as e:
            logger.error(f"获取新浪营业部数据失败: {e}")
            import traceback
            traceback.print_exc()
            return CapitalAnalyzer._get_historical_data()

    @staticmethod
    def _analyze_sina_seat_data(yyb_stats, date=None):
        """
        分析新浪接口的营业部数据
        """
        try:
            # 构建席位数据
            all_seat_data = []
            for _, row in yyb_stats.head(50).iterrows():  # 取前50条
                # 找到营业部名称列
                seat_name = ''
                for col in yyb_stats.columns:
                    if '营业部' in col or '席位' in col:
                        seat_name = str(row.get(col, ''))
                        break

                if not seat_name:
                    continue

                # 处理金额数据（累积购买额和累积卖出额）
                buy_amount = row.get('累积购买额', 0)
                sell_amount = row.get('累积卖出额', 0)

                # 确保金额是数值类型
                if pd.notna(buy_amount):
                    try:
                        buy_amount = float(buy_amount)
                    except:
                        buy_amount = 0
                else:
                    buy_amount = 0

                if pd.notna(sell_amount):
                    try:
                        sell_amount = float(sell_amount)
                    except:
                        sell_amount = 0
                else:
                    sell_amount = 0

                # 获取买入和卖出次数
                buy_count = row.get('买入席位数', 0)
                sell_count = row.get('卖出席位数', 0)

                if pd.notna(buy_count):
                    try:
                        buy_count = int(buy_count)
                    except:
                        buy_count = 0
                else:
                    buy_count = 0

                if pd.notna(sell_count):
                    try:
                        sell_count = int(sell_count)
                    except:
                        sell_count = 0
                else:
                    sell_count = 0

                all_seat_data.append({
                    '代码': '',
                    '名称': str(row.get('买入前三股票', '')),
                    '上榜日': date if date else '2026-01-06',
                    '收盘价': 0,
                    '涨跌幅': 0,
                    '营业部名称': seat_name,
                    '买入额': buy_amount,
                    '卖出额': sell_amount,
                    '净买入': buy_amount - sell_amount,
                    '买入次数': buy_count,
                    '卖出次数': sell_count
                })

            if all_seat_data:
                seat_df = pd.DataFrame(all_seat_data)
                logger.info(f"成功构建席位数据，共 {len(seat_df)} 条记录")
                return CapitalAnalyzer._analyze_seat_data(seat_df, '营业部名称', is_sina=True)
            else:
                logger.info("新浪数据中没有有效的席位信息")
                return CapitalAnalyzer._get_historical_data()

        except Exception as e:
            logger.error(f"分析新浪营业部数据失败: {e}")
            import traceback
            traceback.print_exc()
            return CapitalAnalyzer._get_historical_data()

    @staticmethod
    def _get_historical_data():
        """
        第三层数据源：本地缓存/历史数据
        """
        try:
            import akshare as ak

            logger.info("=" * 60)
            logger.info("第三层数据源：历史营业部数据")
            logger.info("=" * 60)

            # 尝试获取历史营业部数据
            active_yyb = ak.stock_lhb_yyb_detail_em()
            if not active_yyb.empty:
                logger.info(f"获取到 {len(active_yyb)} 条历史营业部数据")
                # 返回历史营业部数据
                return {
                    '数据状态': '正常',
                    '说明': '当前数据源不提供当日营业部明细，显示历史活跃营业部数据（数据可能过时）',
                    '活跃营业部': active_yyb,
                    '营业部数量': len(active_yyb)
                }
            else:
                logger.info("历史营业部数据为空")
                return {
                    '数据状态': '无数据',
                    '说明': '所有数据源均无法获取到有效数据，请稍后重试'
                }

        except Exception as e:
            logger.error(f"获取历史营业部数据失败: {e}")
            return {
                '数据状态': '获取数据失败',
                '错误信息': str(e),
                '说明': '所有数据源均无法获取到有效数据，请稍后重试'
            }

    @staticmethod
    def _match_capital_seat(seat_name):
        """
        智能匹配游资席位

        使用多级匹配策略：
        1. 精确匹配：完全匹配
        2. 关键词匹配：包含关键词
        3. 模糊匹配：去除空格和特殊字符后匹配

        Returns:
            tuple: (capital_name, match_score) 或 (None, 0)
        """
        # 标准化营业部名称：去除空格和特殊字符
        normalized_name = seat_name.replace(' ', '').replace('　', '').replace('（', '(').replace('）', ')')

        for capital_name, seats in CapitalAnalyzer.FAMOUS_CAPITALISTS.items():
            # 1. 精确匹配
            if seat_name in seats or normalized_name in seats:
                return capital_name, 1.0

            # 2. 关键词匹配
            for seat_pattern in seats:
                if seat_pattern in seat_name or seat_pattern in normalized_name:
                    # 计算匹配度：关键词长度 / 总长度
                    match_score = len(seat_pattern) / len(seat_name)
                    return capital_name, match_score

            # 3. 模糊匹配：去除"证券营业部"、"股份有限公司"等后缀
            simplified_name = normalized_name.replace('证券营业部', '').replace('股份有限公司', '').replace('证券', '')
            simplified_pattern = [s.replace('证券营业部', '').replace('股份有限公司', '').replace('证券', '') for s in seats]

            for i, pattern in enumerate(simplified_pattern):
                if pattern in simplified_name:
                    match_score = len(pattern) / len(simplified_name)
                    return capital_name, match_score * 0.9  # 降低匹配度

        return None, 0.0

    @staticmethod
    def _analyze_seat_data(lhb_df, seat_col, is_sina=False):
        """
        分析营业部数据（优化游资识别精度）
        """
        try:
            # 分析游资席位
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            unique_seats = lhb_df[seat_col].unique()
            logger.info(f"共找到 {len(unique_seats)} 个不同的营业部")
            logger.info(f"营业部列表: {unique_seats[:10]}...")  # 只打印前10个

            for _, row in lhb_df.iterrows():
                seat_name = str(row[seat_col])

                # 使用智能匹配算法
                capital_name, match_score = CapitalAnalyzer._match_capital_seat(seat_name)

                # 只保留匹配度较高的结果（> 0.3）
                if capital_name and match_score > 0.3:
                        matched_count += 1
                        # 统计游资操作
                        if capital_name not in capital_stats:
                            capital_stats[capital_name] = {
                                '买入次数': 0,
                                '卖出次数': 0,
                                '买入金额': 0,
                                '卖出金额': 0,
                                '操作股票': []
                            }

                        # 判断买卖方向
                        # 新浪数据使用累积购买额和累积卖出额
                        buy_amount = row.get('买入额', 0)
                        sell_amount = row.get('卖出额', 0)

                        # 获取买入和卖出次数
                        buy_count = row.get('买入次数', 0)
                        sell_count = row.get('卖出次数', 0)

                        if buy_amount > 0 or buy_count > 0:
                            capital_stats[capital_name]['买入次数'] += buy_count if buy_count > 0 else 1
                            capital_stats[capital_name]['买入金额'] += buy_amount
                        if sell_amount > 0 or sell_count > 0:
                            capital_stats[capital_name]['卖出次数'] += sell_count if sell_count > 0 else 1
                            capital_stats[capital_name]['卖出金额'] += sell_amount

                        # 记录操作股票
                        stock_info = {
                            '代码': row['代码'],
                            '名称': row['名称'],
                            '日期': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
                        }
                        capital_stats[capital_name]['操作股票'].append(stock_info)

                        capital_analysis.append({
                            '游资名称': capital_name,
                            '营业部名称': row[seat_col],
                            '股票代码': row['代码'],
                            '股票名称': row['名称'],
                            '上榜日': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
                        })

            # 计算游资统计
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['买入金额'] - stats['卖出金额']
                total_trades = stats['买入次数'] + stats['卖出次数']

                # 判断操作风格
                if stats['买入金额'] > stats['卖出金额'] * 2:
                    style = "激进买入"
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖出"
                elif net_flow > 0:
                    style = "偏多"
                else:
                    style = "偏空"

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次数': total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票数': len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            logger.info(f"分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游资")

            result = {
                '数据状态': '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录数': matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(lhb_df),
                '说明': f'在 {len(lhb_df)} 条龙虎榜记录中，找到 {matched_count} 条游资操作记录'
            }

            # 保存到缓存
            cache_key = f"lhb_capital_{is_sina and 'sina' or 'latest'}"
            CapitalAnalyzer.cache.set(cache_key, result, ttl=3600)  # 缓存1小时

            return result

        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def track_capital_pattern(capital_name, days=30):
        """
        追踪游资操作模式（修复版）
        分析特定游资在指定时间内的操作规律

        核心修复：使用正确的列名 '交易营业部名称'
        """
        try:
            import akshare as ak
            from concurrent.futures import ThreadPoolExecutor, as_completed

            if capital_name not in CapitalAnalyzer.FAMOUS_CAPITALISTS:
                return {
                    '数据状态': '未知游资',
                    '说明': f'未找到游资: {capital_name}'
                }

            # 使用 diskcache 缓存游资追踪结果
            disk_cache = DiskCacheManager()
            end_date = pd.Timestamp.now()
            track_cache_key = f"lhb:track_pattern:{capital_name}:{days}:{end_date.strftime('%Y%m%d')}"

            # 尝试从缓存获取
            cache_result = disk_cache.get_or_set(
                track_cache_key,
                loader=lambda: CapitalAnalyzer._fetch_capital_pattern_data(capital_name, days),
                expire=3600,  # 1小时
                tag=f"capital:{capital_name}"
            )

            if cache_result.hit:
                logger.info(f"[缓存命中] 从 diskcache 获取 {capital_name} 的游资追踪结果")
            else:
                logger.info(f"[缓存未命中] 从 API 获取 {capital_name} 的游资追踪结果")

            return cache_result.value

        except Exception as e:
            logger.error(f"追踪游资操作模式失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def _fetch_capital_pattern_data(capital_name, days):
        """
        内部方法：获取游资操作模式数据（不包含缓存逻辑）
        """
        try:
            import akshare as ak
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # 获取该游资的席位列表
            seats = CapitalAnalyzer.FAMOUS_CAPITALISTS[capital_name]
            logger.info(f"🎯 游资 {capital_name} 的席位列表: {seats}")

            # 获取历史龙虎榜数据
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []
            checked_dates = 0
            matched_dates = 0

            # 获取每日龙虎榜数据
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                checked_dates += 1

                try:
                    # Step 1: 获取龙虎榜股票列表
                    lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)

                    if not lhb_df.empty:
                        logger.info(f"📅 {date_str}: 获取 {len(lhb_df)} 条龙虎榜股票")

                        # Step 2: 逐个查询营业部明细（并发优化）
                        def fetch_seat_detail(stock_info):
                            """获取单个股票的营业部明细"""
                            code = stock_info['代码']
                            name = stock_info['名称']

                            try:
                                # 使用 diskcache 缓存单股营业部明细
                                disk_cache = DiskCacheManager()
                                seat_cache_key = f"lhb:seat_detail:{date_str}:{code}"

                                # 尝试从缓存获取
                                cached_seats = disk_cache.get(seat_cache_key)
                                if cached_seats is not None:
                                    logger.debug(f"  [缓存命中] {name}({code}) 营业部明细")
                                    cached_seats['日期'] = date_str
                                    return cached_seats, True

                                # 缓存未命中，调用 API
                                seats_df = ak.stock_lhb_stock_detail_em(
                                    symbol=code,
                                    date=date_str
                                )

                                if not seats_df.empty:
                                    # 添加股票信息
                                    seats_df['股票代码'] = code
                                    seats_df['股票名称'] = name
                                    seats_df['日期'] = date_str

                                    # 缓存结果
                                    disk_cache.set(seat_cache_key, seats_df, expire=86400, tag=f"date:{date_str}")
                                    logger.debug(f"  [缓存未命中] {name}({code}) 营业部明细，已缓存")

                                    return seats_df, True
                                else:
                                    return None, False
                            except Exception as e:
                                logger.debug(f"  [WARN] {name}({code}) 查询失败: {e}")
                                return None, False

                        # 并发查询营业部明细
                        all_seats = []
                        success_count = 0

                        with ThreadPoolExecutor(max_workers=10) as executor:
                            # 提交所有任务
                            futures = {
                                executor.submit(fetch_seat_detail, row): idx
                                for idx, row in lhb_df.iterrows()
                            }

                            # 收集结果
                            for future in as_completed(futures):
                                result, success = future.result()
                                if success and result is not None:
                                    all_seats.append(result)
                                    success_count += 1

                        logger.info(f"  ✅ 并发查询完成：成功 {success_count} 只股票")

                        if all_seats:
                            # 合并所有营业部数据
                            df_all = pd.concat(all_seats, ignore_index=True)
                            logger.info(f"  获取到 {len(df_all)} 条营业部明细")
                            logger.info(f"  营业部明细列名: {df_all.columns.tolist()}")

                            # ✅ 关键修复：检查正确的列名
                            seat_col = None
                            if '交易营业部名称' in df_all.columns:
                                seat_col = '交易营业部名称'
                            elif '营业部名称' in df_all.columns:
                                seat_col = '营业部名称'
                            else:
                                logger.error(f"  营业部明细数据中没有'营业部名称'列，可用列: {df_all.columns.tolist()}")
                                current_date += pd.Timedelta(days=1)
                                continue

                            # 筛选该游资的操作
                            for _, row in df_all.iterrows():
                                seat_name = str(row[seat_col])

                                # 精确匹配或模糊匹配
                                if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                    matched_dates += 1
                                    
                                    try:
                                        buy_amt = float(row.get('买入金额', 0) or 0)
                                    except:
                                        buy_amt = 0
                                    
                                    try:
                                        sell_amt = float(row.get('卖出金额', 0) or 0)
                                    except:
                                        sell_amt = 0
                                    
                                    all_operations.append({
                                        '日期': row['日期'],
                                        '股票代码': row['股票代码'],
                                        '股票名称': row['股票名称'],
                                        '买入金额': buy_amt,
                                        '卖出金额': sell_amt,
                                        '净买入': buy_amt - sell_amt,
                                        '营业部名称': seat_name
                                    })
                                    logger.info(f"  ✅ 匹配: {seat_name} - {row['股票名称']}({row['股票代码']})")

                except Exception as e:
                    logger.error(f"{date_str}: 获取数据失败 - {e}")
                    pass

                current_date += pd.Timedelta(days=1)

            logger.info(f"检查了 {checked_dates} 天，{matched_dates} 天找到操作记录，共 {len(all_operations)} 条操作")

            # 如果没有操作记录，返回提示信息
            if not all_operations:
                return {
                    '数据状态': '无操作记录',
                    '说明': f'{capital_name} 在最近 {days} 天内无操作记录。可能原因：1) 该游资近期未上榜 2) 席位名称不匹配 3) 数据源限制。',
                    '检查天数': checked_dates,
                    '匹配天数': matched_dates,
                    '游资席位': seats
                }

            # 分析操作模式
            df_ops = pd.DataFrame(all_operations)

            # 1. 操作频率
            operation_frequency = len(all_operations) / days

            # 2. 买卖偏好
            total_buy = df_ops['买入金额'].sum()
            total_sell = df_ops['卖出金额'].sum()
            buy_ratio = total_buy / (total_buy + total_sell) if (total_buy + total_sell) > 0 else 0

            # 3. 单次操作金额
            avg_operation_amount = df_ops['净买入'].abs().mean()

            # 4. 操作成功率（后续3天涨幅）
            success_count = 0
            total_count = 0

            db = DataManager()
            for op in all_operations:
                try:
                    symbol = op['股票代码']
                    op_date = op['日期']

                    # 获取历史数据
                    start_date_str = op_date
                    end_date_str = (pd.Timestamp(op_date) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

                    df = db.get_history_data(symbol, start_date=start_date_str, end_date=end_date_str)

                    if not df.empty and len(df) > 3:
                        # 计算操作后3天的涨幅
                        op_price = df.iloc[0]['close']
                        future_price = df.iloc[3]['close']
                        future_return = (future_price - op_price) / op_price * 100

                        if future_return > 0:
                            success_count += 1
                        total_count += 1
                except:
                    pass

            db.close()

            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            # 5. 判断操作风格
            if buy_ratio > 0.7:
                style = "激进买入型"
            elif buy_ratio < 0.3:
                style = "激进卖出型"
            elif avg_operation_amount > 50000000:
                style = "大资金操作型"
            else:
                style = "平均操作"

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '分析天数': days,
                '操作次数': len(all_operations),
                '操作频率': round(operation_frequency, 2),
                '总买入金额': total_buy,
                '总卖出金额': total_sell,
                '买入比例': round(buy_ratio * 100, 1),
                '平均操作金额': round(avg_operation_amount, 0),
                '操作成功率': round(success_rate, 1),
                '操作风格': style,
                '操作记录': all_operations
            }

        except Exception as e:
            logger.error(f"追踪游资操作模式失败: {e}", exc_info=True)
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def predict_capital_next_move(capital_name):
        """
        预测游资下一步操作
        基于历史操作模式预测
        """
        try:
            # 获取游资操作模式
            pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=30)

            if pattern_result['数据状态'] != '正常':
                return pattern_result

            # 获取最近操作
            recent_operations = pattern_result['操作记录'][-5:]  # 最近5次操作

            # 分析最近操作方向
            recent_buy = sum(op['买入金额'] for op in recent_operations)
            recent_sell = sum(op['卖出金额'] for op in recent_operations)

            # 预测
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '预测类型': '继续买入',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举买入，可能继续加仓'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '预测类型': '继续卖出',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举卖出，可能继续减仓'
                })
            else:
                predictions.append({
                    '预测类型': '观望或小量操作',
                    '概率': '中',
                    '说明': f'{capital_name} 最近操作均衡，可能观望'
                })

            # 根据成功率预测
            if pattern_result['操作成功率'] > 60:
                predictions.append({
                    '预测类型': '关注其操作',
                    '概率': '中',
                    '说明': f'{capital_name} 历史成功率高，建议关注其操作'
                })

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '预测列表': predictions
            }

        except Exception as e:
            logger.error(f"预测游资下一步操作失败: {e}", exc_info=True)
            return {
                '数据状态': '预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def get_performance_stats():
        """
获取性能统计信息
        
        Returns:
            包含缓存统计和性能指标的字典
        """
        cache_stats = CapitalAnalyzer.cache.get_stats()
        
        return {
            '缓存统计': cache_stats,
            '缓存命中率': f"{cache_stats['hit_rate'] * 100:.2f}%",
            '活跃缓存数': cache_stats['active_keys'],
            '过期缓存数': cache_stats['expired_keys'],
            '总缓存数': cache_stats['total_keys']
        }

    @staticmethod
    def clear_cache():
        """清空所有缓存"""
        CapitalAnalyzer.cache.clear_all()
        logger.info("已清空所有缓存")
        return {'状态': '成功', '说明': '已清空所有缓存'}

    @staticmethod
    def cleanup_expired_cache():
        """清理过期缓存"""
        deleted_count = CapitalAnalyzer.cache.clear_expired()
        logger.info(f"已清理 {deleted_count} 条过期缓存")
        return {'状态': '成功', '说明': f'已清理 {deleted_count} 条过期缓存'}
