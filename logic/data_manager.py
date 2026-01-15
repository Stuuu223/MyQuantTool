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
                cache_age = (datetime.now() - cache_data['timestamp']).total_seconds()
                if cache_age < self.cache_expire_seconds:
                    print(f"[CACHE] 使用缓存数据 (剩余有效时间: {self.cache_expire_seconds - cache_age:.1f}秒)")
                    return cache_data['data']

            # 判断是否在交易时间内（9:30-11:30, 13:00-15:00）
            now = datetime.now()
            current_time = now.time()
            is_trading_time = (current_time >= datetime.strptime("09:30", "%H:%M").time() and
                              current_time <= datetime.strptime("11:30", "%H:%M").time()) or \
                             (current_time >= datetime.strptime("13:00", "%H:%M").time() and
                              current_time <= datetime.strptime("15:00", "%H:%M").time())

            # 判断是否是工作日（周一到周五）
            is_weekday = now.weekday() < 5

            start_time = time.time()

            if is_trading_time and is_weekday:
                # 交易时间内，使用1分钟K线
                logger.info(f"正在获取1分钟K线数据: {symbol}...")
                end_date = now.strftime("%Y-%m-%d %H:%M:%S")
                start_date = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

                df = ak.stock_zh_a_hist_min_em(symbol=symbol, period="1", start_date=start_date, end_date=end_date, adjust="qfq")
                elapsed = time.time() - start_time
                logger.info(f"1分钟K线数据获取耗时: {elapsed:.2f}秒")

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
                        'is_trading': True
                    }

                    self.realtime_cache[symbol] = {
                        'data': result,
                        'timestamp': now
                    }
                    print(f"[SUCCESS] 1分钟K线数据获取成功: {result}")
                    return result
            else:
                # 非交易时间，使用日线数据（昨天的收盘价）
                logger.info(f"非交易时间，获取日线数据: {symbol}...")
                end_date = now.strftime("%Y%m%d")
                start_date = (now - timedelta(days=10)).strftime("%Y%m%d")

                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                elapsed = time.time() - start_time
                logger.info(f"日线数据获取耗时: {elapsed:.2f}秒")

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
                        'is_trading': False
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
        now = datetime.now()
        current_time = now.time()
        is_trading_time = (
            (current_time >= datetime.strptime("09:30", "%H:%M").time() and
             current_time <= datetime.strptime("11:30", "%H:%M").time()) or
            (current_time >= datetime.strptime("13:00", "%H:%M").time() and
             current_time <= datetime.strptime("15:00", "%H:%M").time())
        )
        is_weekday = now.weekday() < 5

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
                batch_result = self.quotation.stocks(batch)
                
                # 🆕 V8.4: 数据消毒 - 在数据进入系统的那一刻进行清洗
                sanitized_batch = {}
                for stock_code, stock_data in batch_result.items():
                    # 使用 DataSanitizer 清洗数据
                    sanitized_data = DataSanitizer.sanitize_realtime_data(
                        stock_data, 
                        source_type='easyquotation'
                    )
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

        # 批量获取，每次最多 300 只股票
        batch_size = 300
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            logger.info(f"正在使用 Akshare 获取第 {i//batch_size + 1} 批数据 ({len(batch)} 只股票)...")

            for code in batch:
                try:
                    # 使用 Akshare 获取实时数据
                    realtime_data = self.get_realtime_data(code)
                    if realtime_data:
                        # 转换为与 easyquotation 相同的格式
                        full_code = f"sh{code}" if code.startswith('6') else f"sz{code}"
                        result[full_code] = {
                            'name': '',  # Akshare 实时数据不包含名称
                            'open': realtime_data.get('open', 0),
                            'close': realtime_data.get('pre_close', 0),
                            'now': realtime_data.get('price', 0),
                            'high': realtime_data.get('high', 0),
                            'low': realtime_data.get('low', 0),
                            'volume': realtime_data.get('volume', 0),
                            'turnover': realtime_data.get('turnover_rate', 0),
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
