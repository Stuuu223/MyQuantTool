"""
股票池构建器 - Tushare粗筛
三层漏斗：静态过滤 → 金额过滤 → 量比过滤

Author: iFlow CLI
Date: 2026-02-23
Version: 1.0.0
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from dotenv import load_dotenv

from logic.core.path_resolver import PathResolver
from logic.core.sanity_guards import SanityGuards

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器
    
    三漏斗粗筛 (全市场5000 → ~500):
    1. 静态过滤: 剔除ST、退市、北交所
    2. 金额过滤: 5日平均成交额 > 3000万
    3. 量比过滤: 当日量比 > 3.0
    """
    
    # 过滤阈值
    MIN_AMOUNT = 30000000  # 3000万
    MIN_VOLUME_RATIO = 3.0  # 量比3.0
    
    def __init__(self):
        self.tushare_token = self._load_tushare_token()
        
    def _load_tushare_token(self) -> str:
        """
        加载Tushare Token - CTODict: 优先环境变量，其次配置文件
        
        Returns:
            Tushare Token字符串
        """
        # 1. 优先从环境变量读取 (CTO: 能放env的就env)
        env_token = os.getenv('TUSHARE_TOKEN')
        if env_token and env_token.strip():
            logger.info("【UniverseBuilder】从环境变量读取Tushare Token")
            return env_token.strip()
        
        # 2. 从.env文件读取 (python-dotenv已加载)
        # load_dotenv()已在模块级别调用
        
        # 3. 从配置文件读取 (兼容旧版本)
        try:
            config_path = PathResolver.get_config_dir() / 'config.json'
            if config_path.exists():
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    token = config.get('tushare_token', '')
                    if token:
                        logger.info("【UniverseBuilder】从config.json读取Tushare Token")
                        return token
        except Exception as e:
            logger.error(f"加载Tushare配置失败: {e}")
        
        logger.warning("【UniverseBuilder】未找到Tushare Token，请设置TUSHARE_TOKEN环境变量或config.json")
        return ''
    
    def _init_tushare(self):
        """初始化Tushare接口"""
        try:
            import tushare as ts
            if not self.tushare_token:
                raise ValueError("Tushare token未配置")
            ts.set_token(self.tushare_token)
            return ts.pro_api()
        except ImportError:
            raise ImportError("tushare未安装，请执行: pip install tushare")
        except Exception as e:
            raise RuntimeError(f"Tushare初始化失败: {e}")
    
    def get_daily_universe(self, date: str) -> List[str]:
        """
        获取当日股票池 (三漏斗粗筛)
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            股票代码列表 (约500只)
            
        Raises:
            RuntimeError: 无法获取数据时抛出
        """
        logger.info(f"【UniverseBuilder】开始构建 {date} 股票池")
        
        pro = self._init_tushare()
        
        # 获取前5个交易日 (用于计算5日平均成交额)
        trade_dates = self._get_trade_dates(pro, date, days=5)
        if len(trade_dates) < 5:
            raise RuntimeError(f"无法获取足够的交易日数据: {date}")
            
        logger.info(f"【UniverseBuilder】使用交易日: {trade_dates}")
        
        # 第一层: 静态过滤 (剔除ST、退市、北交所)
        static_pool = self._filter_static(pro, date)
        logger.info(f"【UniverseBuilder】第一层静态过滤: {len(static_pool)} 只")
        
        # 第二层: 金额过滤 (5日平均成交额 > 3000万)
        amount_pool = self._filter_amount(pro, static_pool, trade_dates)
        logger.info(f"【UniverseBuilder】第二层金额过滤: {len(amount_pool)} 只")
        
        # 第三层: 量比过滤 (量比 > 3.0)
        final_pool = self._filter_volume_ratio(pro, amount_pool, date)
        logger.info(f"【UniverseBuilder】第三层量比过滤: {len(final_pool)} 只")
        
        # 转换为标准格式
        result = [self._to_standard_code(code) for code in final_pool]
        
        logger.info(f"【UniverseBuilder】最终股票池: {len(result)} 只")
        return result
    
    def _get_trade_dates(self, pro, end_date: str, days: int = 5) -> List[str]:
        """获取交易日列表"""
        # 计算开始日期 (往前推30天确保覆盖)
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=30)
        start_date = start_dt.strftime('%Y%m%d')
        
        # 获取交易日历
        df = pro.trade_cal(
            exchange='SSE',
            start_date=start_date,
            end_date=end_date
        )
        
        # 筛选交易日
        trade_days = df[df['is_open'] == 1]['cal_date'].tolist()
        trade_days.sort()
        
        # 返回最后N个交易日
        return trade_days[-days:] if len(trade_days) >= days else trade_days
    
    def _filter_static(self, pro, date: str) -> List[str]:
        """
        静态过滤 - 剔除ST、退市、北交所
        
        Returns:
            股票代码列表
        """
        # 获取当日股票列表
        df = pro.stock_basic(
            exchange='',
            list_status='L',  # 上市
            fields='ts_code,name,industry,market'
        )
        
        # 剔除ST (名称包含ST或*ST)
        df = df[~df['name'].str.contains('ST', na=False)]
        
        # 剔除北交所 (BJ)
        df = df[df['market'] != '北交所']
        
        # 剔除科创板 (可选，保留)
        # df = df[~df['ts_code'].str.startswith('688')]
        
        return df['ts_code'].tolist()
    
    def _filter_amount(self, pro, stock_pool: List[str], trade_dates: List[str]) -> List[str]:
        """
        金额过滤 - 5日平均成交额 > 3000万
        
        Args:
            pro: Tushare pro接口
            stock_pool: 第一层过滤后的股票池
            trade_dates: 最近5个交易日
            
        Returns:
            符合条件的股票代码列表
        """
        result = []
        
        start_date = trade_dates[0]
        end_date = trade_dates[-1]
        
        # 批量获取日线数据
        df_list = []
        for i in range(0, len(stock_pool), 100):  # 每批100只
            batch = stock_pool[i:i+100]
            try:
                df = pro.daily(
                    ts_code=','.join(batch),
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,amount'
                )
                df_list.append(df)
            except Exception as e:
                logger.warning(f"获取日线数据失败 (批次 {i}): {e}")
                continue
        
        if not df_list:
            raise RuntimeError("无法获取日线数据")
            
        df_all = pd.concat(df_list, ignore_index=True)
        
        # 计算每只股票5日平均成交额
        avg_amount = df_all.groupby('ts_code')['amount'].mean()
        
        # 筛选 > 3000万 (Tushare amount单位是千，所以是30000)
        MIN_AMOUNT_K = self.MIN_AMOUNT / 1000  # 30000
        valid_stocks = avg_amount[avg_amount >= MIN_AMOUNT_K].index.tolist()
        
        return valid_stocks
    
    def _filter_volume_ratio(self, pro, stock_pool: List[str], date: str) -> List[str]:
        """
        量比过滤 - 当日量比 > 3.0
        
        Args:
            pro: Tushare pro接口
            stock_pool: 第二层过滤后的股票池
            date: 日期 'YYYYMMDD'
            
        Returns:
            符合条件的股票代码列表
        """
        result = []
        
        # 获取当日5分钟线数据计算量比
        for stock in stock_pool:
            try:
                # 获取当日分钟线
                df_today = pro.stk_mins(
                    ts_code=stock,
                    start_date=date,
                    end_date=date,
                    freq='5min'
                )
                
                if df_today.empty or len(df_today) < 10:
                    continue
                
                # 计算当日早盘成交量 (09:35-09:40)
                morning_volume = df_today[df_today['trade_time'] <= '09:40:00']['vol'].sum()
                
                # 获取前5日平均早盘成交量
                prev_dates = self._get_previous_dates(pro, date, 5)
                prev_volumes = []
                
                for prev_date in prev_dates:
                    try:
                        df_prev = pro.stk_mins(
                            ts_code=stock,
                            start_date=prev_date,
                            end_date=prev_date,
                            freq='5min'
                        )
                        if not df_prev.empty:
                            prev_vol = df_prev[df_prev['trade_time'] <= '09:40:00']['vol'].sum()
                            if prev_vol > 0:
                                prev_volumes.append(prev_vol)
                    except:
                        continue
                
                if not prev_volumes:
                    continue
                
                avg_prev_volume = sum(prev_volumes) / len(prev_volumes)
                
                # 计算量比
                if avg_prev_volume > 0:
                    volume_ratio = morning_volume / avg_prev_volume
                    
                    if volume_ratio >= self.MIN_VOLUME_RATIO:
                        result.append(stock)
                        
            except Exception as e:
                logger.debug(f"计算量比失败 {stock}: {e}")
                continue
        
        return result
    
    def _get_previous_dates(self, pro, date: str, days: int) -> List[str]:
        """获取前N个交易日"""
        dt = datetime.strptime(date, '%Y%m%d')
        start_dt = dt - timedelta(days=30)
        start_date = start_dt.strftime('%Y%m%d')
        
        df = pro.trade_cal(
            exchange='SSE',
            start_date=start_date,
            end_date=date
        )
        
        trade_days = df[df['is_open'] == 1]['cal_date'].tolist()
        trade_days.sort()
        
        # 返回最后N个交易日的之前日期
        if len(trade_days) >= days + 1:
            return trade_days[-(days+1):-1]  # 不包括date当天
        return trade_days[:-1] if len(trade_days) > 1 else []
    
    @staticmethod
    def _to_standard_code(ts_code: str) -> str:
        """转换为标准格式 (#######.SH/SZ)"""
        if '.' in ts_code:
            code, exchange = ts_code.split('.')
            if exchange == 'SH':
                return f"{code}.SH"
            elif exchange == 'SZ':
                return f"{code}.SZ"
        return ts_code


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """
    获取当日股票池 (便捷函数)
    
    Args:
        date: 日期 'YYYYMMDD'
        
    Returns:
        股票代码列表
        
    Raises:
        RuntimeError: 无法获取数据时抛出
    """
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    try:
        universe = get_daily_universe('20251231')
        print(f"股票池: {len(universe)} 只")
        print(f"前10只: {universe[:10]}")
    except Exception as e:
        print(f"错误: {e}")
