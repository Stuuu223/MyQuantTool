import akshare as ak
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from logic.logger import get_logger
from logic.error_handler import handle_errors, DataError, NetworkError, ValidationError

logger = get_logger(__name__)

class DataManager:
    def __init__(self, db_path: str = 'data/stock_data.db') -> None:
        logger.info(f"初始化 DataManager，数据库路径: {db_path}")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()
        self.update_db_schema()
        # 实时数据缓存：{symbol: {'data': {...}, 'timestamp': datetime}}
        self.realtime_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expire_seconds: int = 60  # 缓存60秒
        logger.info("DataManager 初始化完成")

    def init_db(self) -> None:
        """初始化数据库表结构
        
        创建 daily_bars 表，如果不存在的话。
        表结构包含：symbol, date, open, high, low, close, volume, turnover_rate
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
                return df_api
            
            return df
        except Exception as e:
            logger.error(f"数据获取异常: {e}", exc_info=True)
            return pd.DataFrame()

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
            import time

            # 检查缓存
            if symbol in self.realtime_cache:
                cache_data = self.realtime_cache[symbol]
                cache_age = (datetime.now() - cache_data['timestamp']).total_seconds()
                if cache_age < self.cache_expire_seconds:
                    print(f"📦 使用缓存数据 (剩余有效时间: {self.cache_expire_seconds - cache_age:.1f}秒)")
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

                    # 计算涨跌幅（对比前一根K线的收盘价）
                    if len(df) >= 2:
                        prev_close = df.iloc[-2]['收盘']
                        change_pct = (latest['收盘'] - prev_close) / prev_close * 100
                    else:
                        prev_close = latest['开盘']
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
                        'pre_close': float(prev_close),
                        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_trading': True
                    }

                    self.realtime_cache[symbol] = {
                        'data': result,
                        'timestamp': now
                    }
                    print(f"✅ 1分钟K线数据获取成功: {result}")
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
                        change_pct = (latest['收盘'] - prev_close) / prev_close * 100
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
                    logger.info(f"✅ 日线数据获取成功: {result}")
                    return result

            logger.warning(f"⚠️ 未找到股票数据: {symbol}")
            return None

        except Exception as e:
            print(f"❌ 获取数据失败: {type(e).__name__}: {str(e)}")
            return None

    def close(self) -> None:
        """关闭数据库连接
        
        释放数据库资源，应在应用退出时调用。
        """
        self.conn.close()
