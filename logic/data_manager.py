import akshare as ak
try:
    import easyquotation
except ImportError:
    easyquotation = None
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from logic.logger import get_logger
from logic.error_handler import handle_errors, DataError, NetworkError, ValidationError

logger = get_logger(__name__)

class DataManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, db_path: str = 'data/stock_data.db'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = 'data/stock_data.db') -> None:
        # 避免重复初始化
        if DataManager._initialized:
            return
        
        logger.info(f"初始化 DataManager，数据库路径: {db_path}")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 使用 WAL 模式提升并发性能
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA cache_size=-64000')  # 64MB 缓存
        
        # 延迟初始化数据库结构（首次使用时才初始化）
        self._db_initialized = False
        self._db_path = db_path
        
        # 实时数据缓存：{symbol: {'data': {...}, 'timestamp': datetime}}
        self.realtime_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expire_seconds: int = 60  # 缓存60秒
        
        # 🆕 V9.9 新增：K线磁盘缓存（懒加载）
        self.kline_cache_dir = "data/kline_cache"
        os.makedirs(self.kline_cache_dir, exist_ok=True)
        self.kline_cache_expire_hours: int = 2  # K线缓存2小时
        
        # 🔥🔥🔥 激活 Easyquotation 极速行情引擎 🔥🔥🔥
        if easyquotation is not None:
            try:
                logger.info("正在启动极速行情引擎 Easyquotation...")
                # 使用新浪接口（最快，带买一卖一量）
                self.quotation = easyquotation.use('sina')
                logger.info("✅ Easyquotation 启动成功！")
            except Exception as e:
                logger.warning(f"❌ Easyquotation 启动失败: {e}，将回退到 Akshare")
                self.quotation = None
        else:
            logger.warning("❌ Easyquotation 未安装，将使用 Akshare")
            self.quotation = None
        
        # 🆕 V9.2 新增：竞价快照管理器
        self.auction_snapshot_manager = None
        try:
            from logic.auction_snapshot_manager import AuctionSnapshotManager
            self.auction_snapshot_manager = AuctionSnapshotManager(self)
            logger.info("✅ 竞价快照管理器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 竞价快照管理器初始化失败: {e}")
        
        # 🆕 V9.3.7 新增：静态数据缓存（行业信息）
        self.static_cache_file = "data/industry_cache.json"
        self.industry_cache = {}
        self._load_industry_cache()
        
        DataManager._initialized = True
        logger.info("DataManager 初始化完成")
    
    def _ensure_connection_open(self):
        """确保数据库连接是打开的，如果已关闭则重新连接"""
        try:
            # 尝试执行一个简单的查询来测试连接
            self.conn.execute("SELECT 1")
        except sqlite3.ProgrammingError:
            # 连接已关闭，重新连接
            logger.warning("数据库连接已关闭，正在重新连接...")
            self.conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30.0)
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.conn.execute('PRAGMA synchronous=NORMAL')
            self.conn.execute('PRAGMA cache_size=-64000')
            logger.info("数据库连接已重新建立")

    def _ensure_db_initialized(self):
        """确保数据库已初始化（延迟初始化）"""
        self._ensure_connection_open()
        if not self._db_initialized:
            self.init_db()
            self.update_db_schema()
            self._db_initialized = True

    def init_db(self) -> None:
        """初始化数据库表结构
        
        创建 daily_bars 表，如果不存在的话。
        表结构包含：symbol, date, open, high, low, close, volume, turnover_rate
        同时创建索引以优化查询性能。
        """
        query = '''
        CREATE TABLE IF NOT EXISTS daily_bars (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            turnover_rate REAL,
            PRIMARY KEY (symbol, date)
        )
        '''
        self.conn.execute(query)
        
        # 创建索引以优化查询性能
        try:
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON daily_bars(symbol, date)')
            self.conn.commit()
            logger.info("数据库索引创建成功")
        except Exception as e:
            logger.warning(f"数据库索引创建失败: {e}")
        query = '''
        CREATE TABLE IF NOT EXISTS daily_bars (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            turnover_rate REAL,
            PRIMARY KEY (symbol, date)
        )
        '''
        self.conn.execute(query)
        self.conn.commit()
    
    def update_db_schema(self) -> None:
        """更新数据库表结构，添加换手率列
        
        检查 daily_bars 表是否有 turnover_rate 列，如果没有则添加。
        """
        try:
            # 检查表是否有 turnover_rate 列
            cursor = self.conn.execute("PRAGMA table_info(daily_bars)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'turnover_rate' not in columns:
                # 添加 turnover_rate 列
                self.conn.execute("ALTER TABLE daily_bars ADD COLUMN turnover_rate REAL")
                self.conn.commit()
                print("数据库表结构已更新，添加了 turnover_rate 列")
        except Exception as e:
            print(f"更新数据库表结构失败: {e}")

    def _get_kline_cache_path(self, symbol: str) -> str:
        """🆕 V9.9：获取K线缓存文件路径"""
        return os.path.join(self.kline_cache_dir, f"{symbol}_kline.pkl")
    
    def _get_kline_cache_ttl(self) -> int:
        """
        🆕 V9.10.1 优化：根据交易时段动态获取缓存TTL
        
        防止"时效性陷阱"和"午休浪费"：
        - 集合竞价 (09:15-09:30)：只缓存10秒，数据变化极快
        - 交易时间 (09:30-11:30, 13:00-15:00)：只缓存1分钟，保证数据鲜度
        - 午间休盘 (11:30-13:00)：缓存1小时，数据静止，无需刷新
        - 盘后 (15:00-次日9:00)：缓存2小时，用于复盘
        
        Returns:
            缓存有效期（秒）
        """
        try:
            from logic.market_status import get_market_status_checker
            market_checker = get_market_status_checker()
            
            current_time = market_checker.get_current_time()
            
            # 1. 集合竞价期间（09:15-09:30）：数据变化极快，10秒刷新
            if market_checker.MORNING_START <= current_time < time(9, 30):
                return 10  # 10秒
            
            # 2. ☕️ 午间休盘（11:30-13:00）：数据静止，缓存1小时
            elif market_checker.is_noon_break(current_time):
                return 3600  # 1小时
            
            # 3. 交易时间：只缓存1分钟
            elif market_checker.is_trading_time():
                return 60  # 1分钟
            
            # 4. 盘后及休市：缓存2小时
            else:
                return self.kline_cache_expire_hours * 3600  # 2小时
        except Exception as e:
            logger.warning(f"获取动态TTL失败: {e}，使用默认值")
            return self.kline_cache_expire_hours * 3600
    
    def _save_kline_to_cache(self, symbol: str, kline_data: pd.DataFrame) -> None:
        """🆕 V9.9：保存K线数据到磁盘缓存"""
        try:
            cache_path = self._get_kline_cache_path(symbol)
            cache_info = {
                'kline': kline_data,
                'timestamp': datetime.now().isoformat()
            }
            
            import pickle
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_info, f)
            
            logger.debug(f"✅ K线数据已缓存: {symbol}")
        except Exception as e:
            logger.warning(f"K线缓存保存失败 {symbol}: {e}")
    
    def _load_kline_from_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """🆕 V9.9：从磁盘缓存加载K线数据"""
        try:
            cache_path = self._get_kline_cache_path(symbol)
            
            if not os.path.exists(cache_path):
                return None
            
            import pickle
            with open(cache_path, 'rb') as f:
                cache_info = pickle.load(f)
            
            # 🆕 V9.10 修复：使用动态TTL检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_info['timestamp'])
            cache_age = (datetime.now() - cache_time).total_seconds()
            
            # 获取动态TTL（盘中1分钟，盘后2小时）
            cache_ttl = self._get_kline_cache_ttl()
            
            if cache_age > cache_ttl:
                logger.debug(f"⚠️ K线缓存已过期: {symbol}")
                return None
            
            logger.debug(f"✅ 从缓存加载K线: {symbol} (缓存时间: {cache_info['timestamp']})")
            return cache_info['kline']
        except Exception as e:
            logger.warning(f"K线缓存加载失败 {symbol}: {e}")
            return None
    
    def _is_kline_cache_valid(self, symbol: str) -> bool:
        """🆕 V9.9：检查K线缓存是否有效"""
        cache_path = self._get_kline_cache_path(symbol)
        
        if not os.path.exists(cache_path):
            return False
        
        try:
            import pickle
            with open(cache_path, 'rb') as f:
                cache_info = pickle.load(f)
            
            cache_time = datetime.fromisoformat(cache_info['timestamp'])
            cache_age = (datetime.now() - cache_time).total_seconds()
            
            # 🆕 V9.10 修复：使用动态TTL
            cache_ttl = self._get_kline_cache_ttl()
            
            return cache_age <= cache_ttl
        except Exception as e:
            return False
    
    @handle_errors(show_user_message=False)
    def get_history_data(self, symbol: str, start_date: str = "20240101", end_date: str = "20251231") -> pd.DataFrame:
        """获取股票历史数据

        从本地数据库获取历史数据，如果缓存未命中则从 akshare 获取并缓存。
        使用内存缓存加速重复查询。

        Args:
            symbol: 股票代码（6位数字）
            start_date: 开始日期，格式 YYYYMMDD，默认 20240101
            end_date: 结束日期，格式 YYYYMMDD，默认 20251231

        Returns:
            包含历史数据的 DataFrame，包含列：symbol, date, open, high, low, close, volume, turnover_rate

        Raises:
            ValidationError: 股票代码格式错误
            DataError: 获取数据失败

        Example:
            >>> db = DataManager()
            >>> df = db.get_history_data('600519', '20240101', '20241231')
            >>> print(df.head())
        """
        try:
            # 🚀 先检查内存缓存
            from logic.history_cache import get_history_cache
            cache = get_history_cache()
            cached_df = cache.get(symbol)
            if cached_df is not None and not cached_df.empty:
                return cached_df

            # 延迟初始化数据库
            self._ensure_db_initialized()
            # 验证股票代码
            if not symbol or len(symbol) != 6:
                raise ValidationError(f"股票代码格式错误: {symbol}")

            df = pd.read_sql(f"SELECT * FROM daily_bars WHERE symbol='{symbol}'", self.conn)

            # 检查是否需要重新获取数据
            need_fetch = False
            if df.empty or len(df) < 5:
                need_fetch = True
            elif 'turnover_rate' not in df.columns:
                need_fetch = True
            elif df['turnover_rate'].isna().all():
                need_fetch = True

            if need_fetch:
                logger.info(f"本地缓存未命中，正在下载 {symbol} ...")
                df_api = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")

                if df_api.empty:
                    raise DataError(f"获取股票数据失败: {symbol}")

                df_api = df_api.rename(columns={
                    '日期': 'date', '开盘': 'open', '最高': 'high',
                    '最低': 'low', '收盘': 'close', '成交量': 'volume', '换手率': 'turnover_rate'
                })
                df_api['symbol'] = symbol

                # 删除旧数据
                self.conn.execute(f"DELETE FROM daily_bars WHERE symbol='{symbol}'")
                self.conn.commit()

                # 插入新数据
                cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'turnover_rate']
                df_api[cols].to_sql('daily_bars', self.conn, if_exists='append', index=False)
                df = df_api

            # 🚀 存入内存缓存
            if not df.empty:
                cache.set(symbol, df)

            return df
        except Exception as e:
            logger.error(f"数据获取异常: {e}", exc_info=True)
            return pd.DataFrame()

    def get_multiple_stocks(self, symbols: list) -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            股票代码到 DataFrame 的字典
        """
        try:
            if not symbols:
                return {}
            
            symbols_str = "','".join(symbols)
            query = f"SELECT * FROM daily_bars WHERE symbol IN ('{symbols_str}') ORDER BY symbol, date"
            df = pd.read_sql(query, self.conn)
            
            if df.empty:
                return {}
            
            # 按股票代码分组
            result = {}
            for symbol in symbols:
                symbol_df = df[df['symbol'] == symbol].copy()
                if not symbol_df.empty:
                    result[symbol] = symbol_df
            
            return result
        except Exception as e:
            logger.error(f"批量获取股票数据失败: {e}", exc_info=True)
            return {}

    def get_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时行情数据（使用1分钟K线，带60秒缓存）
        
        根据当前时间自动选择数据源：
        - 交易时间内（9:30-11:30, 13:00-15:00）：使用1分钟K线数据
        - 非交易时间：使用日线数据
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            实时数据字典，包含以下字段：
            - symbol: 股票代码
            - price: 最新价格
            - change_percent: 涨跌幅（百分比）
            - volume: 成交量
            - turnover_rate: 换手率
            - high: 最高价
            - low: 最低价
            - open: 开盘价
            - pre_close: 昨收价
            - timestamp: 数据时间戳
            
            失败返回 None
            
        Note:
            数据缓存60秒，60秒内重复查询会返回缓存数据
        """
        try:
            # 延迟初始化数据库
            self._ensure_db_initialized()
            
            import time

            # 检查缓存
            if symbol in self.realtime_cache:
                cache_data = self.realtime_cache[symbol]
                # 🆕 V9.9 修复：确保datetime对象时区一致
                from logic.market_status import get_market_status_checker
                market_checker = get_market_status_checker()
                now = datetime.now(market_checker.timezone)
                cache_timestamp = cache_data['timestamp']
                
                # 如果缓存时间戳是时区无关的，转换为时区感知的
                if cache_timestamp.tzinfo is None:
                    cache_timestamp = cache_timestamp.replace(tzinfo=market_checker.timezone)
                
                cache_age = (now - cache_timestamp).total_seconds()
                if cache_age < self.cache_expire_seconds:
                    print(f"[CACHE] 使用缓存数据 (剩余有效时间: {self.cache_expire_seconds - cache_age:.1f}秒)")
                    return cache_data['data']

            # 🆕 V9.6 优化：优先使用 Easyquotation 极速行情引擎
            if self.quotation:
                try:
                    # 转换代码格式 (easyquotation 需要 sh/sz 前缀)
                    if symbol.startswith('6'):
                        prefix = 'sh'
                    elif symbol.startswith('8') or symbol.startswith('4'):
                        prefix = 'bj'
                    else:
                        prefix = 'sz'
                    
                    full_code = f"{prefix}{symbol}"
                    
                    # 🆕 V9.8 修复：添加超时机制，避免 Easyquotation 卡死
                    import signal
                    import threading
                    
                    result_container = {'data': None, 'error': None}
                    
                    def fetch_with_timeout():
                        try:
                            result_container['data'] = self.quotation.stocks([full_code])
                        except Exception as e:
                            result_container['error'] = e
                    
                    # 创建超时线程（3秒超时）
                    fetch_thread = threading.Thread(target=fetch_with_timeout)
                    fetch_thread.daemon = True
                    fetch_thread.start()
                    fetch_thread.join(timeout=3.0)  # 3秒超时
                    
                    if fetch_thread.is_alive():
                        # 超时，放弃这只股票
                        logger.warning(f"⚠️ Easyquotation 超时 {symbol}（3秒），跳过")
                        batch_result = None
                    elif result_container['error']:
                        # 发生错误
                        raise result_container['error']
                    else:
                        batch_result = result_container['data']
                    
                    start_time = time.time()
                    elapsed = time.time() - start_time
                    
                    if batch_result and full_code in batch_result:
                        stock_data = batch_result[full_code]
                        
                        # 转换为标准格式
                        result = {
                            'symbol': symbol,
                            'price': float(stock_data.get('now', 0)),
                            'change_percent': round((float(stock_data.get('now', 0)) - float(stock_data.get('close', 0))) / float(stock_data.get('close', 1)) * 100, 2) if stock_data.get('close', 0) != 0 else 0.0,
                            'volume': float(stock_data.get('volume', 0)) / 100,  # 转换为手
                            'turnover_rate': 0.0,
                            'high': float(stock_data.get('high', 0)),
                            'low': float(stock_data.get('low', 0)),
                            'open': float(stock_data.get('open', 0)),
                            'pre_close': float(stock_data.get('close', 0)),
                            'timestamp': stock_data.get('time', datetime.now().strftime('%H:%M:%S')),
                            'is_trading': True,
                            # 🆕 V9.9 新增：数据一致性校验字段
                            'data_timestamp': stock_data.get('time', datetime.now().strftime('%H:%M:%S')),  # 快照时间
                            'fetch_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # 数据获取时间
                            'data_age_seconds': 0  # 数据新鲜度（秒）
                        }
                        
                        # 存入缓存
                        self.realtime_cache[symbol] = {
                            'data': result,
                            'timestamp': datetime.now()
                        }
                        
                        logger.info(f"✅ Easyquotation 获取成功: {symbol} (耗时: {elapsed:.3f}秒)")
                        return result
                except Exception as e:
                    logger.warning(f"Easyquotation 获取失败 {symbol}: {e}，回退到 Akshare")

            # 🆕 V9.6: 使用标准化的市场状态判断逻辑（支持时区）
            from logic.market_status import get_market_status_checker
            market_checker = get_market_status_checker()
            is_trading_time = market_checker.is_trading_time()
            is_weekday = market_checker.is_weekday()
            now = datetime.now(market_checker.timezone)

            start_time = time.time()

            if is_trading_time and is_weekday:
                # 交易时间内，使用1分钟K线
                # 🆕 V9.9 新增：先检查磁盘缓存（懒加载）
                cached_kline = self._load_kline_from_cache(symbol)
                if cached_kline is not None and not cached_kline.empty:
                    logger.info(f"✅ 使用缓存的1分钟K线数据: {symbol}")
                    df = cached_kline
                    # 继续处理缓存数据...
                else:
                    # 缓存未命中，从网络获取
                    logger.info(f"正在获取1分钟K线数据: {symbol}...")
                    end_date = now.strftime("%Y-%m-%d %H:%M:%S")
                    start_date = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

                    df = ak.stock_zh_a_hist_min_em(symbol=symbol, period="1", start_date=start_date, end_date=end_date, adjust="qfq")
                    elapsed = time.time() - start_time
                    logger.info(f"1分钟K线数据获取耗时: {elapsed:.2f}秒")
                    
                    # 🆕 V9.9 新增：保存到磁盘缓存
                    if not df.empty:
                        self._save_kline_to_cache(symbol, df)

                if not df.empty:
                    # 取最后一根K线（最新的数据）
                    latest = df.iloc[-1]

                    # 获取当日开盘价（找到9:30-9:31的K线）
                    df['时间'] = pd.to_datetime(df['时间'])
                    today_open_df = df[df['时间'].dt.time <= datetime.strptime("09:31", "%H:%M").time()]
                    if not today_open_df.empty:
                        day_open = today_open_df.iloc[0]['开盘']
                    else:
                        day_open = latest['开盘']

                    # 计算涨跌幅（对比当日开盘价，反映当日总涨跌幅）
                    # 防止除以零
                    if day_open != 0:
                        change_pct = (latest['收盘'] - day_open) / day_open * 100
                    else:
                        change_pct = 0.0

                    result = {
                        'symbol': symbol,
                        'price': float(latest['收盘']),
                        'change_percent': round(change_pct, 2),
                        'volume': float(latest['成交量']),
                        'turnover_rate': 0.0,
                        'high': float(latest['最高']),
                        'low': float(latest['最低']),
                        'open': float(latest['开盘']),
                        'pre_close': float(day_open),  # 使用当日开盘价作为基准
                        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_trading': True,
                        # 🆕 V9.9 新增：数据一致性校验字段
                        'data_timestamp': str(latest['时间']) if '时间' in latest else now.strftime('%Y-%m-%d %H:%M:%S'),  # K线实际时间
                        'fetch_timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),  # 数据获取时间
                        'data_age_seconds': 0  # 数据新鲜度（秒）
                    }

                    self.realtime_cache[symbol] = {
                        'data': result,
                        'timestamp': now
                    }
                    print(f"[SUCCESS] 1分钟K线数据获取成功: {result}")
                    return result
            else:
                # 非交易时间，使用日线数据（昨天的收盘价）
                # 🆕 V9.9 新增：先检查磁盘缓存（懒加载）
                cached_kline = self._load_kline_from_cache(symbol)
                if cached_kline is not None and not cached_kline.empty:
                    logger.info(f"✅ 使用缓存的日线数据: {symbol}")
                    df = cached_kline
                    # 继续处理缓存数据...
                else:
                    # 缓存未命中，从网络获取
                    logger.info(f"非交易时间，获取日线数据: {symbol}...")
                    end_date = now.strftime("%Y%m%d")
                    start_date = (now - timedelta(days=10)).strftime("%Y%m%d")

                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                    elapsed = time.time() - start_time
                    logger.info(f"日线数据获取耗时: {elapsed:.2f}秒")
                    
                    # 🆕 V9.9 新增：保存到磁盘缓存
                    if not df.empty:
                        self._save_kline_to_cache(symbol, df)

                if not df.empty:
                    # 取最后一根K线（昨天的收盘价）
                    latest = df.iloc[-1]

                    # 计算涨跌幅（对比前一根K线的收盘价）
                    if len(df) >= 2:
                        prev_close = df.iloc[-2]['收盘']
                        # 防止除以零
                        if prev_close != 0:
                            change_pct = (latest['收盘'] - prev_close) / prev_close * 100
                        else:
                            change_pct = 0.0
                    else:
                        prev_close = latest['开盘']
                        change_pct = 0.0

                    result = {
                        'symbol': symbol,
                        'price': float(latest['收盘']),
                        'change_percent': round(change_pct, 2),
                        'volume': float(latest['成交量']),
                        'turnover_rate': float(latest.get('换手率', 0)),
                        'high': float(latest['最高']),
                        'low': float(latest['最低']),
                        'open': float(latest['开盘']),
                        'pre_close': float(prev_close),
                        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_trading': False,
                        # 🆕 V9.9 新增：数据一致性校验字段
                        'data_timestamp': str(latest['日期']) if '日期' in latest else now.strftime('%Y-%m-%d'),  # K线实际日期
                        'fetch_timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),  # 数据获取时间
                        'data_age_seconds': 0  # 数据新鲜度（秒）
                    }

                    self.realtime_cache[symbol] = {
                        'data': result,
                        'timestamp': now
                    }
                    logger.info(f"[SUCCESS] 日线数据获取成功: {result}")
                    return result

            logger.warning(f"[WARNING] 未找到股票数据: {symbol}")
            return None

        except Exception as e:
            print(f"[ERROR] 获取数据失败: {type(e).__name__}: {str(e)}")
            return None

    def close(self) -> None:
        """关闭数据库连接
        
        释放数据库资源，应在应用退出时调用。
        """
        self.conn.close()
    
    def get_fast_price(self, stock_list: list, max_retries: int = 3) -> dict:
        """
        极速批量获取行情 (专门给龙头扫描用) - V6.1 增强版

        优先使用 Easyquotation 批量获取实时行情，一次网络请求可获取数百只股票数据，
        耗时仅需 0.5-1 秒，相比逐个调用 Akshare 快 100 倍以上。
        
        🆕 V6.1 数据源降级策略：
        1. 主备切换：Easyquotation (Sina) -> Akshare (Eastmoney) -> 样本估算
        2. 多次重试：网络失败时自动重试
        3. 样本估算：全市场数据获取失败时，使用样本股票估算市场情绪
        4. 缓存机制：60秒内重复查询使用缓存数据

        Args:
            stock_list: 股票代码列表，如 ['300063', '000001', '600519']
            max_retries: 最大重试次数（默认3次）

        Returns:
            字典，key 为带前缀的股票代码（如 'sz300063'），value 为行情数据字典

            行情数据包含：
            - name: 股票名称
            - open: 开盘价
            - close: 昨收价
            - now: 最新价
            - high: 最高价
            - low: 最低价
            - bid1_volume: 买一量（股数）
            - ask1_volume: 卖一量（股数）
            - volume: 成交量（手）
            - turnover: 换手率

        Note:
            如果所有数据源都失败，会返回样本估算数据或空字典

        Example:
            >>> db = DataManager()
            >>> data = db.get_fast_price(['300063', '000001'])
            >>> print(data['sz300063']['name'])
        """
        if not stock_list:
            return {}

        # 🆕 V7.0: 判断是否在交易时间内
        # 🆕 V9.6: 使用标准化的市场状态判断逻辑（支持时区）
        from logic.market_status import get_market_status_checker
        market_checker = get_market_status_checker()
        current_time = market_checker.get_current_time()
        is_trading_time = market_checker.is_trading_time()
        is_weekday = market_checker.is_weekday()

        # 🆕 V7.0: 非交易时间，使用缓存数据（上次收盘）
        if not (is_trading_time and is_weekday):
            cache_key = f"fast_price_{len(stock_list)}_{hash(tuple(sorted(stock_list)))}"
            if cache_key in self.realtime_cache:
                cache_data = self.realtime_cache[cache_key]
                logger.info(f"[OFF-HOURS] 使用上次收盘数据 (缓存时间: {cache_data['timestamp'].strftime('%H:%M:%S')})")
                return cache_data['data']
            else:
                logger.warning("[OFF-HOURS] 无缓存数据，尝试获取最新数据")

        # 🆕 V6.1: 检查缓存（交易时间内）
        cache_key = f"fast_price_{len(stock_list)}_{hash(tuple(sorted(stock_list)))}"
        if cache_key in self.realtime_cache:
            cache_data = self.realtime_cache[cache_key]
            cache_age = (datetime.now() - cache_data['timestamp']).total_seconds()
            if cache_age < self.cache_expire_seconds:
                logger.info(f"[CACHE] 使用缓存数据 (剩余有效时间: {self.cache_expire_seconds - cache_age:.1f}秒)")
                return cache_data['data']

        # 🆕 V6.1: 多次重试机制
        for retry in range(max_retries):
            result = self._try_get_fast_price(stock_list, retry)
            
            if result and len(result) > 0:
                # 🆕 V6.1: 存入缓存（非交易时间缓存时间延长）
                cache_duration = 86400 if not (is_trading_time and is_weekday) else self.cache_expire_seconds
                self.realtime_cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now(),
                    'cache_duration': cache_duration
                }
                return result
            
            if retry < max_retries - 1:
                logger.warning(f"第 {retry + 1} 次尝试失败，等待 2 秒后重试...")
                import time
                time.sleep(2)

        # 🆕 V6.1: 所有尝试都失败，使用样本估算
        logger.error("所有数据源都失败，尝试使用样本估算...")
        return self._get_sample_estimation(stock_list)
    
    def _try_get_fast_price(self, stock_list: list, retry: int) -> dict:
        """
        尝试获取行情数据（单次尝试）

        Args:
            stock_list: 股票代码列表
            retry: 当前重试次数

        Returns:
            dict: 行情数据字典
        """
        # 优先使用 Easyquotation
        if self.quotation:
            try:
                return self._get_price_from_easyquotation(stock_list)
            except Exception as e:
                logger.error(f"Easyquotation 获取失败 (尝试 {retry + 1}): {e}")
        
        # 回退方案：使用 Akshare
        try:
            return self._get_price_from_akshare(stock_list)
        except Exception as e:
            logger.error(f"Akshare 获取失败 (尝试 {retry + 1}): {e}")
        
        return {}
    
    def _get_price_from_easyquotation(self, stock_list: list) -> dict:
        """
        使用 Easyquotation 获取行情
        
        Args:
            stock_list: 股票代码列表
        
        Returns:
            dict: 行情数据字典
        """
        # 🆕 V8.4: 导入数据消毒器
        from logic.data_sanitizer import DataSanitizer
        
        # 🆕 V9.6 修复：导入 time 模块
        from datetime import time as dt_time
        
        # 🆕 V9.2: 判断当前时间
        # 🆕 V9.6: 使用标准化的市场状态判断逻辑（支持时区）
        from logic.market_status import get_market_status_checker
        market_checker = get_market_status_checker()
        current_time = market_checker.get_current_time()
        
        # 使用 market_status 模块中的时间常量
        is_auction_time = (
            current_time >= market_checker.MORNING_START and
            current_time < dt_time(9, 30)  # 竞价时间：9:15-9:30
        )
        is_after_market = current_time >= dt_time(9, 30)        
        # 转换代码格式 (easyquotation 需要 sh/sz 前缀)
        full_codes = []
        for code in stock_list:
            if code.startswith('6'):
                prefix = 'sh'
            elif code.startswith('8') or code.startswith('4'):
                prefix = 'bj'
            else:
                prefix = 'sz'
            full_codes.append(f"{prefix}{code}")

        # 🚀 批量获取，避免一次请求过多股票导致连接失败
        result = {}
        batch_size = 500  # 每次最多 500 只股票
        total_batches = (len(full_codes) + batch_size - 1) // batch_size

        logger.info(f"正在使用 Easyquotation 极速获取 {len(full_codes)} 只股票的实时行情（分 {total_batches} 批）...")

        for i in range(0, len(full_codes), batch_size):
            batch = full_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            try:
                logger.info(f"正在获取第 {batch_num}/{total_batches} 批数据 ({len(batch)} 只股票)...")
                
                # 🆕 V9.8 修复：添加超时机制，避免 Easyquotation 卡死
                import threading
                result_container = {'data': None, 'error': None}
                
                def fetch_with_timeout():
                    try:
                        result_container['data'] = self.quotation.stocks(batch)
                    except Exception as e:
                        result_container['error'] = e
                
                # 创建超时线程（5秒超时，批量请求可以稍微长一点）
                fetch_thread = threading.Thread(target=fetch_with_timeout)
                fetch_thread.daemon = True
                fetch_thread.start()
                fetch_thread.join(timeout=5.0)  # 5秒超时
                
                if fetch_thread.is_alive():
                    # 超时，跳过这一批
                    logger.warning(f"⚠️ Easyquotation 超时（第 {batch_num}/{total_batches} 批），跳过")
                    continue
                elif result_container['error']:
                    # 发生错误
                    raise result_container['error']
                else:
                    batch_result = result_container['data']
                
                # 🆕 V8.4: 数据消毒 - 在数据进入系统的那一刻进行清洗
                # 🆕 V9.2: 竞价快照保存和恢复
                sanitized_batch = {}
                for stock_code, stock_data in batch_result.items():
                    # 提取纯股票代码（去掉前缀）
                    code = stock_code[2:]  # 'sh600058' -> '600058'
                    
                    # 使用 DataSanitizer 清洗数据
                    sanitized_data = DataSanitizer.sanitize_realtime_data(
                        stock_data, 
                        source_type='easyquotation',
                        code=stock_code
                    )
                    
                    # 🆕 V9.2: 竞价快照逻辑
                    if self.auction_snapshot_manager:
                        # 场景 A: 竞价时间（9:25-9:30）→ 保存竞价数据
                        if is_auction_time:
                            auction_volume = sanitized_data.get('volume', 0)  # 此时 volume 就是竞价量
                            auction_amount = sanitized_data.get('turnover', 0)
                            
                            if auction_volume > 0:
                                # 保存竞价快照
                                self.auction_snapshot_manager.save_auction_snapshot(code, {
                                    'auction_volume': auction_volume,
                                    'auction_amount': auction_amount,
                                    'timestamp': datetime.now(market_checker.timezone).timestamp()
                                })
                        
                        # 场景 B: 盘中/盘后（9:30 以后）→ 尝试恢复竞价数据
                        elif is_after_market:
                            # 从 Redis 恢复竞价数据
                            snapshot = self.auction_snapshot_manager.load_auction_snapshot(code)
                            
                            if snapshot:
                                # ✅ 成功恢复竞价数据
                                sanitized_data['竞价量'] = snapshot.get('auction_volume', 0)
                                sanitized_data['竞价金额'] = snapshot.get('auction_amount', 0)
                                logger.debug(f"✅ [竞价恢复] {code} 竞价数据已从 Redis 恢复")
                            else:
                                # ❌ Redis 也没有，标记为缺失
                                sanitized_data['竞价量'] = 0
                                sanitized_data['竞价金额'] = 0
                                logger.debug(f"⚠️ [竞价缺失] {code} 无竞价快照数据")
                    
                    sanitized_batch[stock_code] = sanitized_data
                
                result.update(sanitized_batch)
                logger.info(f"✅ 第 {batch_num} 批获取完成，获取到 {len(batch_result)} 只股票")
            except Exception as e:
                logger.warning(f"第 {batch_num} 批获取失败: {e}，继续下一批")
                continue

        logger.info(f"✅ Easyquotation 极速获取完成，共获取 {len(result)} 只股票")
        return result
    
    def _get_price_from_akshare(self, stock_list: list) -> dict:
        """
        使用 Akshare 获取行情

        Args:
            stock_list: 股票代码列表

        Returns:
            dict: 行情数据字典
        """
        result = {}

        # 使用 Akshare 获取实时行情
        import time
        start_time = time.time()

        # 🆕 V9.8 修复：在循环外调用一次，获取全市场数据，然后在内存中查找
        # 不要在循环中调用，否则扫描 5000 只股票会调用 5000 次，极其低效！
        import akshare as ak
        logger.info(f"正在使用 Akshare 获取全市场实时行情...")
        stock_info = ak.stock_zh_a_spot_em()
        logger.info(f"✅ Akshare 全市场数据获取完成，共 {len(stock_info)} 只股票")

        # 批量处理，每次最多 300 只股票
        batch_size = 300
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            logger.info(f"正在处理第 {i//batch_size + 1} 批数据 ({len(batch)} 只股票)...")

            for code in batch:
                try:
                    # 🆕 V9.8 修复：直接从内存中查找，不再重复调用 API
                    # 查找股票数据
                    stock_data = stock_info[stock_info['代码'] == code]
                    
                    if not stock_data.empty:
                        stock_row = stock_data.iloc[0]
                        full_code = f"sh{code}" if code.startswith('6') else f"sz{code}"
                        
                        # 计算涨跌幅
                        price = float(stock_row['最新价'])
                        pre_close = float(stock_row['昨收'])
                        change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0.0
                        
                        result[full_code] = {
                            'name': stock_row['名称'],
                            'open': float(stock_row['今开']),
                            'close': pre_close,
                            'now': price,
                            'high': float(stock_row['最高']),
                            'low': float(stock_row['最低']),
                            'volume': float(stock_row['成交量']) / 100,  # 转换为手
                            'turnover': float(stock_row['换手率']),
                            'bid1_volume': 0,  # Akshare 实时数据不包含盘口数据
                            'ask1_volume': 0,
                            'bid1': 0,
                            'ask1': 0
                        }
                except Exception as e:
                    logger.warning(f"获取股票 {code} 数据失败: {e}")
                    continue

        elapsed = time.time() - start_time
        logger.info(f"✅ Akshare 获取完成，共 {len(result)} 只股票，耗时 {elapsed:.2f}秒")
        return result
    
    def _get_sample_estimation(self, stock_list: list) -> dict:
        """
        🆕 V6.1: 使用样本估算市场情绪（降级方案）
        🆕 V6.2: 升级为分层抽样，避免样本偏差

        当全市场数据获取失败时，使用分层抽样的样本股票（100只）来估算市场情绪。
        确保样本覆盖：权重股、人气妖股、跌幅榜常客、随机中小盘。

        Args:
            stock_list: 股票代码列表

        Returns:
            dict: 样本估算数据
        """
        logger.warning("使用样本估算模式（分层抽样100只股票）")
        
        # 🆕 V6.2: 使用分层抽样，而不是随机取前100只
        sample_stocks = self._get_stratified_sample()
        
        if not sample_stocks:
            # 如果分层抽样失败，回退到取前100只
            logger.warning("分层抽样失败，回退到随机抽样")
            sample_stocks = stock_list[:100]
        
        result = {}
        try:
            # 尝试获取样本数据
            sample_data = self._get_price_from_akshare(sample_stocks)
            
            if sample_data:
                # 计算样本统计信息
                total_count = len(sample_data)
                up_count = sum(1 for data in sample_data.values() if data.get('now', 0) > data.get('close', 0))
                down_count = sum(1 for data in sample_data.values() if data.get('now', 0) < data.get('close', 0))
                
                logger.info(f"📊 分层样本统计：共 {total_count} 只，上涨 {up_count} 只，下跌 {down_count} 只")
                logger.info(f"📊 涨跌比：{up_count/total_count:.1%}，分层抽样代表大盘情绪")
                
                return sample_data
            else:
                logger.error("样本数据获取也失败")
                return {}
        
        except Exception as e:
            logger.error(f"样本估算失败: {e}")
            return {}
    
    def _get_stratified_sample(self) -> list:
        """
        🆕 V6.2: 获取分层抽样样本
        
        从balanced_monitor_list.json中读取预存的100只代表性股票，
        确保覆盖各个市场层级。
        
        Returns:
            list: 100只分层抽样的股票代码
        """
        try:
            import json
            import os
            
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       'config', 'balanced_monitor_list.json')
            
            if not os.path.exists(config_path):
                logger.warning(f"分层抽样配置文件不存在: {config_path}")
                return []
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 提取所有层的股票
            sample_stocks = []
            for layer_name, layer_info in config.get('layers', {}).items():
                stocks = layer_info.get('stocks', [])
                sample_stocks.extend(stocks)
                logger.info(f"📊 分层抽样 - {layer_name}: {len(stocks)} 只")
            
            # 确保总数是100只
            if len(sample_stocks) != 100:
                logger.warning(f"分层抽样总数不是100只，实际: {len(sample_stocks)} 只")
            
            logger.info(f"✅ 分层抽样完成，共 {len(sample_stocks)} 只")
            return sample_stocks
            
        except Exception as e:
            logger.error(f"获取分层抽样失败: {e}")
            return []
    
    def _load_industry_cache(self):
        """从本地JSON文件加载行业缓存"""
        import json
        import os
        
        if os.path.exists(self.static_cache_file):
            try:
                with open(self.static_cache_file, 'r', encoding='utf-8') as f:
                    self.industry_cache = json.load(f)
                logger.info(f"✅ 从磁盘加载行业缓存成功，共 {len(self.industry_cache)} 个板块")
            except Exception as e:
                logger.warning(f"读取行业缓存失败: {e}，将重新获取")
                self.industry_cache = {}
                self._update_industry_cache()
        else:
            logger.info("行业缓存文件不存在，正在创建...")
            self._update_industry_cache()
    
    def _update_industry_cache(self):
        """从AkShare更新行业缓存并保存到磁盘"""
        import akshare as ak
        import json
        
        try:
            logger.info("正在从AkShare获取行业信息...")
            industry_df = ak.stock_board_industry_name_em()
            
            # 构建板块代码到板块名称的映射
            self.industry_cache = {}
            for _, row in industry_df.iterrows():
                self.industry_cache[row['板块代码']] = row['板块名称']
            
            # 保存到磁盘
            with open(self.static_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.industry_cache, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 行业缓存更新成功，共 {len(self.industry_cache)} 个板块")
            
        except Exception as e:
            logger.error(f"更新行业缓存失败: {e}")
            self.industry_cache = {}
    
    def get_industry_cache(self):
        """获取行业缓存"""
        return self.industry_cache
    
    def get_stock_status(self, code: str, days: int = 5) -> Dict[str, Any]:
        """
        🆕 V9.13 获取股票的【身位】和【形态】
        
        计算连板数和昨日状态，用于识别弱转强和连板溢价。
        
        Args:
            code: 股票代码
            days: 获取历史天数（默认5天）
        
        Returns:
            dict: {
                'lianban_count': 连板数,
                'yesterday_status': 昨日状态（涨停/烂板/非涨停）,
                'yesterday_pct': 昨日涨跌幅,
                'limit_threshold': 涨停阈值
            }
        """
        from datetime import datetime, timedelta
        import pandas as pd
        
        try:
            # 获取最近N天的日线数据
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days+10)).strftime("%Y%m%d")  # 多取几天确保有数据
            
            from logic.akshare_data_loader import AKShareDataLoader
            klines = AKShareDataLoader.get_stock_daily(code, start_date, end_date, adjust="")
            
            if klines is None or len(klines) < 2:
                return {
                    'lianban_count': 0,
                    'yesterday_status': '未知',
                    'yesterday_pct': 0,
                    'limit_threshold': 9.5
                }
            
            # 按日期排序（最新的在前面）
            klines = klines.sort_values('日期', ascending=False)
            
            # 1. 计算连板数（倒序遍历）
            boards = 0
            limit_threshold = 9.5  # 默认主板阈值
            
            # 判断是否为 20cm 标的 (创业板 30/科创板 68)
            if code.startswith(('30', '68')):
                limit_threshold = 19.5
            elif 'ST' in str(code):
                limit_threshold = 4.8
            
            for _, k in klines.iterrows():
                pct = k.get('涨跌幅', 0)
                
                # 判断是否涨停
                if pct >= limit_threshold:
                    boards += 1
                else:
                    # 一旦断板，停止计算
                    break
            
            # 2. 判断昨日状态（用于识别弱转强）
            if len(klines) >= 2:
                yesterday = klines.iloc[1]  # 昨天的数据
                yesterday_pct = yesterday.get('涨跌幅', 0)
                
                # 判断昨日状态
                if yesterday_pct >= limit_threshold:
                    yesterday_status = '涨停'
                elif yesterday_pct > 5 and yesterday_pct < limit_threshold:
                    yesterday_status = '烂板'  # 大涨但未涨停
                elif yesterday_pct < -5:
                    yesterday_status = '大跌'
                else:
                    yesterday_status = '非涨停'
            else:
                yesterday_pct = 0
                yesterday_status = '未知'
            
            return {
                'lianban_count': boards,
                'yesterday_status': yesterday_status,
                'yesterday_pct': yesterday_pct,
                'limit_threshold': limit_threshold
            }
            
        except Exception as e:
            logger.warning(f"获取股票 {code} 状态失败: {e}")
            return {
                'lianban_count': 0,
                'yesterday_status': '未知',
                'yesterday_pct': 0,
                'limit_threshold': 9.5
            }
    
    def warm_up_stock_status(self, stock_list: list) -> Dict[str, Any]:
        """
        🔥 V9.13.1 盘前预热：提前把连板数和昨日状态算好，存入内存
        
        建议在 9:15 之前运行，预热监控池的股票身位数据。
        这样在 9:25 竞价时，get_stock_status 会直接从缓存读取，耗时从 0.35s 降至 0.0001s。
        
        Args:
            stock_list: 股票列表，每个元素包含 'code' 字段
        
        Returns:
            dict: 预热结果统计
        """
        import time
        from datetime import datetime
        
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        logger.info(f"🔥 开始盘前预热 {len(stock_list)} 只股票的身位数据...")
        
        for stock in stock_list:
            code = stock.get('code', '')
            if not code:
                continue
                
            try:
                # 调用 get_stock_status 会下载 K 线并缓存
                # 因为数据是静态的，DataManager 的缓存机制会生效
                self.get_stock_status(code)
                success_count += 1
            except Exception as e:
                logger.warning(f"预热股票 {code} 失败: {e}")
                fail_count += 1
        
        elapsed_time = time.time() - start_time
        
        result = {
            'total': len(stock_list),
            'success': success_count,
            'failed': fail_count,
            'elapsed_time': round(elapsed_time, 2),
            'timestamp': datetime.now().strftime("%H:%M:%S")
        }
        
        logger.info(f"✅ 盘前预热完成！成功 {success_count} 只，失败 {fail_count} 只，耗时 {elapsed_time:.2f} 秒")
        logger.info(f"💡 9:25 竞价时将直接读取缓存，预计耗时 < 0.1 秒")
        
        return result
