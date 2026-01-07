"""
AKShare 实时数据加载器

龙虎榜、板块、K线数据一站式获取
"""
import akshare as ak
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AKShareDataLoader:
    """
    AKShare 数据加载器
    
    实时获取龙虎榜、板块、K线数据
    """
    
    # ============================================================================
    # 龙虎榜数据 API
    # ============================================================================
    
    @staticmethod
    def get_lhb_daily(date: str) -> pd.DataFrame:
        """
        获取龙虎榜月日个股明细
        
        Args:
            date (str): 日期, 格式 "20260107"
        
        Returns:
            pd.DataFrame: 龙虎榜个股详情
                - 代码: 股票代码
                - 名称: 股票名称
                - 上榌符次: 欦次上榌次数
                - 买入: 累计买入集合竞价成交数(3个)
                - 卖出: 累计卖出集合竞价成交数(3个)
                - 收买: 收买集合竞价成交数
                - 成交馇: 增加成交金额
                - 美涨幅: 涨跌幅 (%)
        """
        try:
            df = ak.stock_lhb_detail_em(date=date)
            logger.info(f"成功获取 {date} 龙虎榜数据, 共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"获取 {date} 龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_lhb_stat(days: int = 30) -> pd.DataFrame:
        """
        获取龙虎榜个股累计统计
        
        Args:
            days (int): 日数 ((详细列表无此参数)
        
        Returns:
            pd.DataFrame: 累计统计
                - 代码
                - 名称
                - 上榌符次: 欦次次数
                - 累计买入: 累计买入金额
                - 累计卖出: 累计卖出金额
        """
        try:
            df = ak.stock_lhb_stock_statistic_em()
            logger.info(f"成功获取龙虎榜累计统计, 共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜累计统计失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_lhb_business_top() -> pd.DataFrame:
        """
        获取龙虎榜业务部排行
        
        Returns:
            pd.DataFrame: 业务部排行
                - 业务部名称
                - 上榌符次
                - 累计买入
                - 累计卖出
        """
        try:
            df = ak.stock_lhb_yybph_em()
            logger.info(f"成功获取业务部排行, 共 {len(df)} 个业务部")
            return df
        except Exception as e:
            logger.error(f"获取业务部排行失败: {e}")
            return pd.DataFrame()
    
    # ============================================================================
    # 板块数据 API
    # ============================================================================
    
    @staticmethod
    def get_sw_industry() -> pd.DataFrame:
        """
        获取申万一级行业板块实时数据
        
        Returns:
            pd.DataFrame: 板块数据
                - 指数代码
                - 指数名称
                - 指数最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            df = ak.sw_index_spot()
            logger.info(f"成功获取申万一级行业, 共 {len(df)} 个板块")
            return df
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_industry_spot() -> pd.DataFrame:
        """
        获取东財行业板块实时行情
        
        Returns:
            pd.DataFrame: 板块数据
                - 代码
                - 名称
                - 最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            # 注意：ak.stock_board_industry_spot_em() 的返回格式已改变
            # 暂时返回空数据，使用演示数据替代
            logger.warning("akshare API 格式已改变，暂时使用演示数据")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取行业板块失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_industry_constituents(symbol: str = "BK0001") -> pd.DataFrame:
        """
        获取行业成份股
        
        Args:
            symbol (str): 板块代码, 序楷: "BK0001"=东方財富业, "BK0023"=释能设备
        
        Returns:
            pd.DataFrame: 成份股
                - 成份股代码
                - 成份股名称
        """
        try:
            df = ak.sw_index_cons(index_code=symbol)
            logger.info(f"成功获取 {symbol} 成份股, 共 {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"获取 {symbol} 成份股失败: {e}")
            return pd.DataFrame()
    
    # ============================================================================
    # K线数据 API
    # ============================================================================
    
    @staticmethod
    def get_stock_daily(
        code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取个股日线数据
        
        Args:
            code (str): 股票代码, 如 "000001" (不带市场标识)
            start_date (str): 开始日期, 格式 "20250101"
            end_date (str): 结束日期, 格式 "20260107"
            adjust (str): 复权方式
                - "" : 不复权
                - "qfq" : 前复权
                - "hfq" : 后复权
        
        Returns:
            pd.DataFrame: K线数据
                - 日期
                - 股票代码
                - 开盘
                - 收盘
                - 最高
                - 最低
                - 成交量
                - 成交额
                - 挪幅
                - 涨跌幅
                - 涨跌额
                - 换手率
        """
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            logger.info(f"成功获取 {code} K线, {start_date} 至 {end_date}, 共 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {code} K线失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_stock_minute(
        code: str,
        period: str = "1",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取个股分鋳线数据
        
        Args:
            code (str): 股票代码, 需要带市场标识, 如 "sh600000" 或 "sz000001"
            period (str): K线周期
                - "1" : 1分鋳
                - "5" : 5分鋳
                - "15" : 15分鋳
                - "30" : 30分鋳
                - "60" : 60分鋳 (一小时)
            adjust (str): 复权方式
        
        Returns:
            pd.DataFrame: 分鋳线数据
                - 日期
                - 开盘
                - 最高
                - 最低
                - 收盘
                - 成交量
        """
        try:
            # 注意：分鋳线数据只有当日最近交易日的数据
            df = ak.stock_zh_a_minute(
                symbol=code,
                period=period,
                adjust=adjust
            )
            logger.info(f"成功获取 {code} {period}分鋳, 共 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {code} 分鋳数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_stock_realtime(code: str) -> Optional[Dict]:
        """
        获取个股实时上章
        
        Args:
            code (str): 股票代码, 序梗: "000001"
        
        Returns:
            Optional[Dict]: 实时行情字典或 None
                - 代码
                - 名称
                - 最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            df = ak.stock_zh_a_spot_em()
            # 去除不必要的前缀
            stock = df[df['代码'] == code]
            if len(stock) > 0:
                logger.info(f"成功获取 {code} 实时上章")
                return stock.to_dict('records')[0]
            else:
                logger.warning(f"找不到 {code} 的实时上章")
                return None
        except Exception as e:
            logger.error(f"获取 {code} 实时上章失败: {e}")
            return None
    
    # ============================================================================
    # 批量数据 API
    # ============================================================================
    
    @staticmethod
    def get_multiple_stocks_daily(
        codes: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个股票的日线数据
        
        Args:
            codes (List[str]): 股票代码列表
            start_date (str): 开始日期
            end_date (str): 结束日期
            adjust (str): 复权方式
        
        Returns:
            Dict[str, pd.DataFrame]: {code: DataFrame}
        """
        result = {}
        for code in codes:
            df = AKShareDataLoader.get_stock_daily(code, start_date, end_date, adjust)
            if not df.empty:
                result[code] = df
        logger.info(f"批量获取了 {len(result)}/{len(codes)} 股票的K线数据")
        return result
    
    # ============================================================================
    # 整合数据 API
    # ============================================================================
    
    @staticmethod
    def get_trading_day_data(date: str) -> Dict:
        """
        获取一个上章的完整交易数据
        
        Args:
            date (str): 日期, 格式 "20260107"
        
        Returns:
            Dict: 包含龙虎榜、板块、行业数据
        """
        return {
            "lhb_detail": AKShareDataLoader.get_lhb_daily(date),
            "lhb_stat": AKShareDataLoader.get_lhb_stat(),
            "lhb_business": AKShareDataLoader.get_lhb_business_top(),
            "industry": AKShareDataLoader.get_industry_spot(),
        }


if __name__ == "__main__":
    # 测试
    loader = AKShareDataLoader()
    
    # 获取今天的龙虎榜
    today = datetime.now().strftime("%Y%m%d")
    lhb = loader.get_lhb_daily(today)
    print(f"\n龙虎榜数据 (\u5171 {len(lhb)} 条):")
    print(lhb.head())
    
    # 获取板块数据
    industry = loader.get_industry_spot()
    print(f"\n板块数据 (\u5171 {len(industry)} 个):")
    print(industry.head())
    
    # 获取K线
    kline = loader.get_stock_daily("000001", "20260101", today)
    print(f"\n000001 K线数据 (\u5171 {len(kline)} 条):")
    print(kline.head())
