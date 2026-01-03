import akshare as ak
import pandas as pd
import sqlite3
import os
from datetime import datetime

class DataManager:
    def __init__(self, db_path='data/stock_data.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()

    def init_db(self):
        query = '''
        CREATE TABLE IF NOT EXISTS daily_bars (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, date)
        )
        '''
        self.conn.execute(query)
        self.conn.commit()

    def get_history_data(self, symbol, start_date="20240101", end_date="20251231"):
        try:
            df = pd.read_sql(f"SELECT * FROM daily_bars WHERE symbol='{symbol}'", self.conn)
            
            if df.empty or len(df) < 5:
                # print(f"本地缓存未命中，正在下载 {symbol} ...") # 保持界面清爽
                df_api = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                
                df_api = df_api.rename(columns={
                    '日期': 'date', '开盘': 'open', '最高': 'high', 
                    '最低': 'low', '收盘': 'close', '成交量': 'volume'
                })
                df_api['symbol'] = symbol
                
                cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                df_api[cols].to_sql('daily_bars', self.conn, if_exists='append', index=False)
                return df_api
            
            return df
        except Exception as e:
            print(f"数据获取异常: {e}")
            return pd.DataFrame()

    def close(self):
        self.conn.close()
