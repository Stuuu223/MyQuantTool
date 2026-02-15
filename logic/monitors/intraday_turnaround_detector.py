"""
日内弱转强探测器 - V9.0

核心功能：
1. 检测竞价弱但开盘后承接强的股票
2. 捕捉"日内弱转强"机会（如神思电子案例）
3. 修正竞价评分，发出"半路追涨"信号

触发条件：
1. 竞价弱（成交少）：竞价金额<500万，竞价抢筹度<2%
2. 开盘5分钟内，股价不跌破开盘价（承接强）
3. 5分钟内的成交量迅速放大，超过竞价成交量的5-10倍（主力进场换手）
4. 必须有主线板块效应（ThemeDetector确认是今日主线）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from logic.utils.logger import get_logger
from logic.sectors.theme_detector import ThemeDetector

logger = get_logger(__name__)


class IntradayTurnaroundDetector:
    """
    日内弱转强探测器
    
    功能：
    1. 检测竞价弱但开盘后承接强的股票
    2. 捕捉"日内弱转强"机会
    3. 修正竞价评分，发出"半路追涨"信号
    """
    
    def __init__(self):
        """初始化日内弱转强探测器"""
        self.theme_detector = ThemeDetector()
        
        # 配置参数
        self.config = {
            # 竞价弱阈值
            'weak_auction_amount': 500,  # 竞价金额<500万（万元）
            'weak_auction_ratio': 0.02,  # 竞价抢筹度<2%
            
            # 承接强阈值
            'support_time_minutes': 5,  # 开盘5分钟内
            'support_price_ratio': 0.995,  # 股价不跌破开盘价的99.5%（允许小幅波动）
            
            # 成交量放大阈值
            'volume_surge_min': 5,  # 成交量至少放大5倍
            'volume_surge_max': 10,  # 成交量最多放大10倍
            
            # 主线板块效应
            'main_theme_heat_threshold': 60,  # 主线热度>60
        }
        
        logger.info("日内弱转强探测器初始化完成")
    
    def detect_turnaround(
        self,
        symbol: str,
        auction_data: Dict[str, Any],
        intraday_data: Optional[pd.DataFrame] = None,
        main_theme: Optional[str] = None,
        theme_heat: float = 0.0
    ) -> Tuple[bool, str, float]:
        """
        检测日内弱转强
        
        Args:
            symbol: 股票代码
            auction_data: 竞价数据
                {
                    'auction_amount': float,  # 竞价金额（万元）
                    'auction_ratio': float,  # 竞价抢筹度
                    'auction_volume': float,  # 竞价量（手）
                    'open_price': float,  # 开盘价
                    'open_gap_pct': float,  # 开盘涨幅
                }
            intraday_data: 日内数据（开盘后5分钟的分时数据）
                DataFrame包含列：time, price, volume
            main_theme: 主线板块名称
            theme_heat: 主线热度
        
        Returns:
            tuple: (是否弱转强, 原因, 修正评分)
        """
        try:
            # 1. 检查前提条件：竞价弱
            is_weak_auction, weak_reason = self._check_weak_auction(auction_data)
            if not is_weak_auction:
                return False, "竞价不弱，不触发弱转强检测", 0.0
            
            # 2. 检查条件1：开盘5分钟内，股价不跌破开盘价（承接强）
            if intraday_data is None or intraday_data.empty:
                return False, "缺少日内数据，无法检测承接强度", 0.0
            
            is_strong_support, support_reason = self._check_strong_support(
                auction_data['open_price'],
                intraday_data
            )
            if not is_strong_support:
                return False, support_reason, 0.0
            
            # 3. 检查条件2：5分钟内的成交量迅速放大
            is_volume_surge, volume_reason = self._check_volume_surge(
                auction_data['auction_volume'],
                intraday_data
            )
            if not is_volume_surge:
                return False, volume_reason, 0.0
            
            # 4. 检查条件3：必须有主线板块效应
            is_main_theme, theme_reason = self._check_main_theme_effect(
                main_theme,
                theme_heat,
                symbol
            )
            if not is_main_theme:
                return False, theme_reason, 0.0
            
            # 5. 所有条件满足，确认弱转强
            turnaround_score = self._calculate_turnaround_score(
                auction_data,
                intraday_data,
                theme_heat
            )
            
            reason = (
                f"✅ 日内弱转强确认：{weak_reason}，{support_reason}，"
                f"{volume_reason}，{theme_reason}，修正评分+{turnaround_score:.0f}分"
            )
            
            return True, reason, turnaround_score
        
        except Exception as e:
            logger.error(f"检测弱转强失败: {e}", exc_info=True)
            return False, f"检测失败: {e}", 0.0
    
    def _check_weak_auction(self, auction_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查竞价弱
        
        Args:
            auction_data: 竞价数据
        
        Returns:
            tuple: (是否弱, 原因)
        """
        auction_amount = auction_data.get('auction_amount', 0)
        auction_ratio = auction_data.get('auction_ratio', 0)
        
        # 竞价弱条件：竞价金额<500万 或 竞价抢筹度<2%
        if auction_amount < self.config['weak_auction_amount'] or \
           auction_ratio < self.config['weak_auction_ratio']:
            return True, f"竞价弱（金额{auction_amount:.0f}万<500万或抢筹度{auction_ratio*100:.2f}%<2%）"
        
        return False, "竞价不弱"
    
    def _check_strong_support(
        self,
        open_price: float,
        intraday_data: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        检查承接强
        
        Args:
            open_price: 开盘价
            intraday_data: 日内数据
        
        Returns:
            tuple: (是否强, 原因)
        """
        # 筛选开盘后5分钟内的数据
        support_time_minutes = self.config['support_time_minutes']
        support_threshold = self.config['support_price_ratio']
        
        # 获取开盘后5分钟内的数据
        early_data = intraday_data.head(support_time_minutes)
        
        if early_data.empty:
            return False, "开盘后5分钟内无数据"
        
        # 检查股价是否跌破开盘价
        min_price = early_data['price'].min()
        price_ratio = min_price / open_price if open_price > 0 else 0
        
        if price_ratio >= support_threshold:
            return True, f"承接强（开盘后5分钟内最低价{min_price:.2f}未跌破开盘价{open_price:.2f}的{support_threshold*100:.1f}%）"
        else:
            return False, f"承接弱（开盘后5分钟内最低价{min_price:.2f}跌破开盘价{open_price:.2f}的{support_threshold*100:.1f}%）"
    
    def _check_volume_surge(
        self,
        auction_volume: float,
        intraday_data: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        检查成交量放大
        
        Args:
            auction_volume: 竞价量（手）
            intraday_data: 日内数据
        
        Returns:
            tuple: (是否放大, 原因)
        """
        # 筛选开盘后5分钟内的数据
        support_time_minutes = self.config['support_time_minutes']
        volume_surge_min = self.config['volume_surge_min']
        volume_surge_max = self.config['volume_surge_max']
        
        # 获取开盘后5分钟内的数据
        early_data = intraday_data.head(support_time_minutes)
        
        if early_data.empty:
            return False, "开盘后5分钟内无数据"
        
        # 计算5分钟内的成交量
        intraday_volume = early_data['volume'].sum()
        
        # 计算成交量放大倍数
        if auction_volume > 0:
            surge_ratio = intraday_volume / auction_volume
        else:
            surge_ratio = float('inf')
        
        # 检查成交量放大倍数是否在合理范围内
        if volume_surge_min <= surge_ratio <= volume_surge_max:
            return True, f"成交量放大{surge_ratio:.1f}倍（5分钟内{intraday_volume:.0f}手 vs 竞价{auction_volume:.0f}手）"
        elif surge_ratio < volume_surge_min:
            return False, f"成交量放大不足（仅{surge_ratio:.1f}倍<{volume_surge_min}倍）"
        else:
            return False, f"成交量过度放大（{surge_ratio:.1f}倍>{volume_surge_max}倍，可能是诱多）"
    
    def _check_main_theme_effect(
        self,
        main_theme: Optional[str],
        theme_heat: float,
        symbol: str
    ) -> Tuple[bool, str]:
        """
        检查主线板块效应
        
        Args:
            main_theme: 主线板块名称
            theme_heat: 主线热度
            symbol: 股票代码
        
        Returns:
            tuple: (是否有主线效应, 原因)
        """
        # 检查主线热度
        if theme_heat < self.config['main_theme_heat_threshold']:
            return False, f"主线热度不足（{theme_heat:.0f}<{self.config['main_theme_heat_threshold']}）"
        
        # 检查股票是否在主线板块内
        if main_theme is None or main_theme == '':
            return False, "未识别到主线板块"
        
        # 这里简化处理，实际需要判断股票是否属于主线板块
        # 可以通过股票名称或代码判断（如神思电子属于AI/低空经济）
        # 这里假设只要主线热度够高，就认为有主线效应
        
        return True, f"主线板块效应强（主线{main_theme}，热度{theme_heat:.0f}）"
    
    def _calculate_turnaround_score(
        self,
        auction_data: Dict[str, Any],
        intraday_data: pd.DataFrame,
        theme_heat: float
    ) -> float:
        """
        计算弱转强修正评分
        
        Args:
            auction_data: 竞价数据
            intraday_data: 日内数据
            theme_heat: 主线热度
        
        Returns:
            float: 修正评分
        """
        base_score = 20.0  # 基础分
        
        # 1. 根据开盘涨幅加分
        open_gap_pct = auction_data.get('open_gap_pct', 0)
        if open_gap_pct > 10:
            base_score += 10  # 高开加分
        elif open_gap_pct > 5:
            base_score += 5
        
        # 2. 根据主线热度加分
        if theme_heat > 80:
            base_score += 10  # 主线极热加分
        elif theme_heat > 60:
            base_score += 5
        
        # 3. 根据承接强度加分
        if intraday_data is not None and not intraday_data.empty:
            early_data = intraday_data.head(5)
            if not early_data.empty:
                min_price = early_data['price'].min()
                open_price = auction_data.get('open_price', 0)
                if open_price > 0:
                    price_ratio = min_price / open_price
                    if price_ratio >= 1.0:
                        base_score += 10  # 完全承接加分
                    elif price_ratio >= 0.995:
                        base_score += 5  # 基本承接加分
        
        # 4. 根据成交量放大倍数加分
        auction_volume = auction_data.get('auction_volume', 0)
        if auction_volume > 0 and intraday_data is not None and not intraday_data.empty:
            early_data = intraday_data.head(5)
            if not early_data.empty:
                intraday_volume = early_data['volume'].sum()
                surge_ratio = intraday_volume / auction_volume
                if surge_ratio >= 8:
                    base_score += 10  # 大幅放量加分
                elif surge_ratio >= 5:
                    base_score += 5
        
        return base_score
    
    def batch_detect_turnaround(
        self,
        stocks_data: List[Dict[str, Any]],
        main_theme: Optional[str] = None,
        theme_heat: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        批量检测日内弱转强
        
        Args:
            stocks_data: 股票数据列表
                [
                    {
                        'symbol': str,
                        'name': str,
                        'auction_data': Dict,
                        'intraday_data': Optional[pd.DataFrame]
                    },
                    ...
                ]
            main_theme: 主线板块名称
            theme_heat: 主线热度
        
        Returns:
            list: 弱转强股票列表
        """
        turnaround_stocks = []
        
        for stock in stocks_data:
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            auction_data = stock.get('auction_data', {})
            intraday_data = stock.get('intraday_data', None)
            
            # 检测弱转强
            is_turnaround, reason, score = self.detect_turnaround(
                symbol,
                auction_data,
                intraday_data,
                main_theme,
                theme_heat
            )
            
            if is_turnaround:
                turnaround_stocks.append({
                    'symbol': symbol,
                    'name': name,
                    'auction_data': auction_data,
                    'reason': reason,
                    'score': score,
                    'signal': 'HALFTIME_BUY'  # 半路追涨信号
                })
        
        # 按修正评分排序
        turnaround_stocks.sort(key=lambda x: x['score'], reverse=True)
        
        return turnaround_stocks


# 测试代码
if __name__ == "__main__":
    detector = IntradayTurnaroundDetector()
    
    # 模拟神思电子数据
    auction_data = {
        'auction_amount': 104,  # 竞价金额104万
        'auction_ratio': 0.0112,  # 竞价抢筹度1.12%
        'auction_volume': 449,  # 竞价量449手
        'open_price': 23.31,  # 开盘价
        'open_gap_pct': 12.83,  # 开盘涨幅12.83%
    }
    
    # 模拟日内数据（开盘后5分钟）
    intraday_data = pd.DataFrame({
        'time': ['09:30', '09:31', '09:32', '09:33', '09:34', '09:35'],
        'price': [23.31, 23.35, 23.40, 23.45, 23.50, 23.55],
        'volume': [1000, 1500, 2000, 2500, 3000, 4000]
    })
    
    # 检测弱转强
    is_turnaround, reason, score = detector.detect_turnaround(
        '300479',
        auction_data,
        intraday_data,
        main_theme='低空经济',
        theme_heat=75
    )
    
    print(f"是否弱转强: {is_turnaround}")
    print(f"原因: {reason}")
    print(f"修正评分: {score}")