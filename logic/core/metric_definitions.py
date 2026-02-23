"""
全局指标定义库 - 系统唯一可信的计算来源
禁止任何文件自行计算这些指标！

使用方法:
    from logic.core.metric_definitions import MetricDefinitions
    
    # 计算真实涨跌幅
    change = MetricDefinitions.TRUE_CHANGE(current_price, pre_close)
    
    # 计算高开溢价
    gap = MetricDefinitions.GAP_UP_PREMIUM(open_price, pre_close)
    
    # 计算VWAP
    vwap = MetricDefinitions.VWAP(df, price_col='price', volume_col='volume')

设计原则:
    1. 唯一可信源 - 所有指标必须从此类获取
    2. 严格校验 - 绝不返回None，无效输入直接抛出异常
    3. 文档完备 - 每个指标都有清晰的文档和公式说明
    4. 类型安全 - 完整的类型注解
"""
from typing import Union
import pandas as pd
import numpy as np


class MetricDefinitions:
    """
    指标定义字典 - CTO指定的不可违背的契约
    
    此类包含系统中所有核心金融指标的标准计算公式。
    任何计算涨跌幅、振幅、换手率等指标的地方都应该使用这些方法，
    禁止自行编写计算逻辑。
    """
    
    @staticmethod
    def TRUE_CHANGE(current_price: Union[int, float], pre_close: Union[int, float]) -> float:
        """
        真实涨跌幅 - 唯一公式：(今价-昨收)/昨收 * 100
        
        这是计算股票价格涨跌幅的标准方法，以昨收价为基准。
        
        Args:
            current_price: 当前价格（最新成交价或当前价格）
            pre_close: 昨收价（昨日收盘价）
        
        Returns:
            float: 涨跌幅百分比（例如：涨5%返回5.0，跌3%返回-3.0）
        
        Raises:
            ValueError: 昨收价<=0时，或输入为负数时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(current_price, (int, float)):
            raise TypeError(f"current_price必须是数字类型，当前类型：{type(current_price)}")
        if not isinstance(pre_close, (int, float)):
            raise TypeError(f"pre_close必须是数字类型，当前类型：{type(pre_close)}")
        
        # 数值有效性检查
        if pre_close <= 0:
            raise ValueError(f"昨收价必须>0，当前值：{pre_close}")
        if current_price < 0:
            raise ValueError(f"当前价格不能为负数，当前值：{current_price}")
        
        return (current_price - pre_close) / pre_close * 100
    
    @staticmethod
    def GAP_UP_PREMIUM(open_price: Union[int, float], pre_close: Union[int, float]) -> float:
        """
        高开溢价 - 唯一公式：(今开-昨收)/昨收 * 100
        
        用于衡量开盘相对昨收的跳空幅度。
        
        Args:
            open_price: 今日开盘价
            pre_close: 昨收价（昨日收盘价）
            
        Returns:
            float: 高开溢价百分比（正数为高开，负数为低开）
            
        Raises:
            ValueError: 昨收价<=0时，或开盘价为负数时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(open_price, (int, float)):
            raise TypeError(f"open_price必须是数字类型，当前类型：{type(open_price)}")
        if not isinstance(pre_close, (int, float)):
            raise TypeError(f"pre_close必须是数字类型，当前类型：{type(pre_close)}")
        
        # 数值有效性检查
        if pre_close <= 0:
            raise ValueError(f"昨收价必须>0，当前值：{pre_close}")
        if open_price < 0:
            raise ValueError(f"开盘价不能为负数，当前值：{open_price}")
        
        return (open_price - pre_close) / pre_close * 100
    
    @staticmethod
    def TRUE_AMPLITUDE(
        high: Union[int, float], 
        low: Union[int, float], 
        pre_close: Union[int, float]
    ) -> float:
        """
        真实振幅 - 基于昨收价计算
        
        公式：(最高价-最低价)/昨收 * 100
        
        这是计算日内振幅的标准方法，反映当日价格波动的剧烈程度。
        
        Args:
            high: 当日最高价
            low: 当日最低价
            pre_close: 昨收价（昨日收盘价）
            
        Returns:
            float: 振幅百分比（总是非负值）
            
        Raises:
            ValueError: 昨收价<=0时，或最低价>最高价时，或价格为负数时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(high, (int, float)):
            raise TypeError(f"high必须是数字类型，当前类型：{type(high)}")
        if not isinstance(low, (int, float)):
            raise TypeError(f"low必须是数字类型，当前类型：{type(low)}")
        if not isinstance(pre_close, (int, float)):
            raise TypeError(f"pre_close必须是数字类型，当前类型：{type(pre_close)}")
        
        # 数值有效性检查
        if pre_close <= 0:
            raise ValueError(f"昨收价必须>0，当前值：{pre_close}")
        if high < 0 or low < 0:
            raise ValueError(f"价格不能为负数，最高价：{high}，最低价：{low}")
        if low > high:
            raise ValueError(f"最低价不能大于最高价，最低价：{low}，最高价：{high}")
        
        return (high - low) / pre_close * 100
    
    @staticmethod
    def VWAP(
        df: pd.DataFrame, 
        price_col: str = 'price', 
        volume_col: str = 'volume'
    ) -> float:
        """
        成交量加权平均价 (Volume Weighted Average Price)
        
        公式：SUM(价格 * 成交量) / SUM(成交量)
        
        VWAP是衡量交易期间平均执行价格的常用指标，被广泛应用于
        算法交易和执行分析。
        
        Args:
            df: 包含价格和成交量数据的DataFrame
            price_col: 价格列的列名，默认为'price'
            volume_col: 成交量列的列名，默认为'volume'
            
        Returns:
            float: VWAP值
            
        Raises:
            ValueError: DataFrame为空、缺少必要列、成交量为0时
            TypeError: df不是DataFrame时
        """
        # 类型检查
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"df必须是pandas.DataFrame，当前类型：{type(df)}")
        
        # 空数据检查
        if df.empty:
            raise ValueError("DataFrame为空，无法计算VWAP")
        
        # 列存在性检查
        if price_col not in df.columns:
            raise ValueError(f"缺少价格列：'{price_col}'，可用列：{list(df.columns)}")
        if volume_col not in df.columns:
            raise ValueError(f"缺少成交量列：'{volume_col}'，可用列：{list(df.columns)}")
        
        # 数据有效性检查
        prices = df[price_col]
        volumes = df[volume_col]
        
        if prices.isna().all():
            raise ValueError(f"价格列'{price_col}'全部为NaN")
        if volumes.isna().all():
            raise ValueError(f"成交量列'{volume_col}'全部为NaN")
        
        # 计算VWAP（忽略NaN值）
        total_amount = (prices * volumes).sum()
        total_volume = volumes.sum()
        
        if total_volume == 0:
            raise ValueError("成交量总和为0，无法计算VWAP")
        
        vwap = total_amount / total_volume
        
        # 检查结果有效性
        if pd.isna(vwap) or np.isinf(vwap):
            raise ValueError(f"VWAP计算结果无效: {vwap}")
        
        return float(vwap)
    
    @staticmethod
    def TURNOVER_RATE(
        volume: Union[int, float], 
        float_volume: Union[int, float]
    ) -> float:
        """
        换手率 - 成交量/流通股本 * 100
        
        换手率是衡量股票流动性的重要指标，表示当日成交量占流通股本的比例。
        
        Args:
            volume: 当日成交量（股数）
            float_volume: 流通股本（股数）
            
        Returns:
            float: 换手率百分比
            
        Raises:
            ValueError: 流通股本<=0时，或成交量为负数时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(volume, (int, float)):
            raise TypeError(f"volume必须是数字类型，当前类型：{type(volume)}")
        if not isinstance(float_volume, (int, float)):
            raise TypeError(f"float_volume必须是数字类型，当前类型：{type(float_volume)}")
        
        # 数值有效性检查
        if float_volume <= 0:
            raise ValueError(f"流通股本必须>0，当前值：{float_volume}")
        if volume < 0:
            raise ValueError(f"成交量不能为负数，当前值：{volume}")
        
        return volume / float_volume * 100
    
    @staticmethod
    def LIMIT_UP_PRICE(pre_close: Union[int, float], limit_percent: float = 10.0) -> float:
        """
        计算涨停价
        
        A股主板涨停通常为10%，创业板/科创板为20%，ST股票为5%
        计算结果需要按交易所规则进行价格舍入（四舍五入到分）
        
        Args:
            pre_close: 昨收价
            limit_percent: 涨停百分比，默认为10.0
            
        Returns:
            float: 涨停价（已舍入到2位小数）
            
        Raises:
            ValueError: 昨收价<=0时，或涨停百分比<=0时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(pre_close, (int, float)):
            raise TypeError(f"pre_close必须是数字类型，当前类型：{type(pre_close)}")
        if not isinstance(limit_percent, (int, float)):
            raise TypeError(f"limit_percent必须是数字类型，当前类型：{type(limit_percent)}")
        
        # 数值有效性检查
        if pre_close <= 0:
            raise ValueError(f"昨收价必须>0，当前值：{pre_close}")
        if limit_percent <= 0:
            raise ValueError(f"涨停百分比必须>0，当前值：{limit_percent}")
        
        limit_price = pre_close * (1 + limit_percent / 100)
        
        # 舍入到2位小数（四舍五入）
        return round(limit_price, 2)
    
    @staticmethod
    def LIMIT_DOWN_PRICE(pre_close: Union[int, float], limit_percent: float = 10.0) -> float:
        """
        计算跌停价
        
        Args:
            pre_close: 昨收价
            limit_percent: 跌停百分比，默认为10.0
            
        Returns:
            float: 跌停价（已舍入到2位小数）
            
        Raises:
            ValueError: 昨收价<=0时，或跌停百分比<=0时
            TypeError: 输入类型不正确时
        """
        # 类型检查
        if not isinstance(pre_close, (int, float)):
            raise TypeError(f"pre_close必须是数字类型，当前类型：{type(pre_close)}")
        if not isinstance(limit_percent, (int, float)):
            raise TypeError(f"limit_percent必须是数字类型，当前类型：{type(limit_percent)}")
        
        # 数值有效性检查
        if pre_close <= 0:
            raise ValueError(f"昨收价必须>0，当前值：{pre_close}")
        if limit_percent <= 0:
            raise ValueError(f"跌停百分比必须>0，当前值：{limit_percent}")
        
        limit_price = pre_close * (1 - limit_percent / 100)
        
        # 舍入到2位小数（四舍五入）
        return round(limit_price, 2)
    
    @staticmethod
    def PRICE_CHANGE_RANGE(
        current_price: Union[int, float], 
        pre_close: Union[int, float]
    ) -> str:
        """
        判断价格变动区间
        
        Args:
            current_price: 当前价格
            pre_close: 昨收价
            
        Returns:
            str: 变动区间描述
                - 'limit_up': 涨停（>=9.9%）
                - 'up_strong': 强势上涨（5% ~ 9.9%）
                - 'up_normal': 正常上涨（0% ~ 5%）
                - 'flat': 平盘（-0.5% ~ 0.5%）
                - 'down_normal': 正常下跌（-5% ~ -0.5%）
                - 'down_strong': 强势下跌（-9.9% ~ -5%）
                - 'limit_down': 跌停（<=-9.9%）
        """
        change_pct = MetricDefinitions.TRUE_CHANGE(current_price, pre_close)
        
        if change_pct >= 9.9:
            return 'limit_up'
        elif change_pct >= 5:
            return 'up_strong'
        elif change_pct > 0.5:
            return 'up_normal'
        elif change_pct >= -0.5:
            return 'flat'
        elif change_pct > -5:
            return 'down_normal'
        elif change_pct > -9.9:
            return 'down_strong'
        else:
            return 'limit_down'
