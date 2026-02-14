"""
主力强度指标计算模块 (Main Force Strength)

功能:
1. 计算归一化的主力强度指标（类似DDE DDX）
2. 支持不同市值股票横向对比
3. 持续性分析：看主力是否"一直在"
4. 简化决策：一个数字看懂主力意图

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-03
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MainForceStrength:
    """主力强度指标计算器
    
    基于公开资金流向数据，计算归一化的主力强度指标，类似DDE DDX。
    支持不同市值股票横向对比。
    
    Attributes:
        None
        
    Example:
        >>> calculator = MainForceStrength()
        >>> result = calculator.calculate(fund_flow_data, total_shares=10.5)
        >>> print(result['ddx'])  # 主力强度（-1到1）
        >>> print(result['trend'])  # 趋势判断
    """
    
    def __init__(self):
        """初始化主力强度计算器"""
        pass
    
    def calculate(
        self,
        fund_flow_data: pd.DataFrame,
        total_shares: float,
        current_price: float = None
    ) -> Dict[str, Any]:
        """
        计算主力强度指标（归一化版本）
        
        类似DDE DDX，但基于公开数据
        
        Args:
            fund_flow_data: 资金流向数据（DataFrame）
                必须包含列：['超大单', '大单', '中单', '小单', '机构', '散户']
            total_shares: 流通股本（亿股）
            current_price: 当前股价（元），如果为None则使用平均价格估算
        
        Returns:
            {
                'ddx': float,  # 主力强度（-1到1）
                'trend': str,  # 趋势判断
                'persistence': float,  # 持续性（0-1）
                'main_force_net': float,  # 主力净流入（万元）
                'interpretation': str,  # 解读说明
                'strength_level': str,  # 强度等级
                'buy_days': int,  # 吸筹天数
                'sell_days': int,  # 出货天数
                'total_days': int  # 总天数
            }
        """
        # 数据验证
        if fund_flow_data is None or fund_flow_data.empty:
            logger.warning("资金流向数据为空，无法计算主力强度")
            return self._get_empty_result()
        
        # 检查必需的列
        required_columns = ['超大单', '大单', '中单', '小单', '机构', '散户']
        missing_columns = [col for col in required_columns if col not in fund_flow_data.columns]
        if missing_columns:
            logger.warning(f"缺少必需的列: {missing_columns}")
            return self._get_empty_result()
        
        # 计算主力净流入（超大单+大单）
        main_force_net = fund_flow_data['超大单'].sum() + fund_flow_data['大单'].sum()
        
        # 计算流通市值
        if current_price is None:
            # 估算平均价格（使用最近5天收盘价的平均值）
            if '收盘价' in fund_flow_data.columns:
                current_price = fund_flow_data['收盘价'].tail(5).mean()
            elif '成交额' in fund_flow_data.columns and '成交量' in fund_flow_data.columns:
                # 使用平均成交额/平均成交量估算
                avg_amount = fund_flow_data['成交额'].mean()
                avg_volume = fund_flow_data['成交量'].mean()
                current_price = avg_amount / avg_volume if avg_volume > 0 else 25.0
            else:
                # 使用默认价格
                current_price = 25.0
        
        # 流通市值（万元）
        circulating_value = total_shares * 10000 * current_price
        
        # 防止除以零
        if circulating_value == 0:
            logger.warning("流通市值为0，无法计算主力强度")
            return self._get_empty_result()
        
        # DDX = 主力净流入 / 流通市值（归一化到-1到1）
        # 限制在[-1, 1]范围内
        ddx = main_force_net / circulating_value
        ddx = max(-1.0, min(1.0, ddx))
        
        # 计算持续性（吸筹天数占比）
        main_force_daily = fund_flow_data['超大单'] + fund_flow_data['大单']
        buy_days = (main_force_daily > 0).sum()
        sell_days = (main_force_daily < 0).sum()
        total_days = len(fund_flow_data)
        
        persistence = buy_days / total_days if total_days > 0 else 0
        
        # 计算一致性（主力方向的稳定性）
        # 使用标准差衡量波动性
        daily_ddx = main_force_daily / (total_shares * 10000 * current_price)
        consistency = 1.0 - min(1.0, daily_ddx.std() if len(daily_ddx) > 1 else 0)
        
        # 综合评分（结合强度、持续性、一致性）
        composite_score = (abs(ddx) * 0.5 + persistence * 0.3 + consistency * 0.2)
        
        # 趋势判断
        trend, strength_level, interpretation = self._judge_trend(ddx, persistence, composite_score)
        
        return {
            'ddx': ddx,
            'trend': trend,
            'strength_level': strength_level,
            'persistence': persistence,
            'consistency': consistency,
            'composite_score': composite_score,
            'main_force_net': main_force_net,
            'interpretation': interpretation,
            'buy_days': int(buy_days),
            'sell_days': int(sell_days),
            'total_days': total_days,
            'circulating_value': circulating_value,
            'current_price': current_price
        }
    
    def _judge_trend(
        self,
        ddx: float,
        persistence: float,
        composite_score: float
    ) -> tuple:
        """
        判断主力趋势
        
        Args:
            ddx: 主力强度
            persistence: 持续性
            composite_score: 综合评分
            
        Returns:
            (trend, strength_level, interpretation)
        """
        # 强度等级判断
        abs_ddx = abs(ddx)
        
        if abs_ddx >= 0.05 and composite_score >= 0.6:
            if ddx > 0:
                strength_level = '🟢🟢🟢 极强'
            else:
                strength_level = '🔴🔴🔴 极弱'
        elif abs_ddx >= 0.03 and composite_score >= 0.5:
            if ddx > 0:
                strength_level = '🟢🟢 较强'
            else:
                strength_level = '🔴🔴 较弱'
        elif abs_ddx >= 0.01:
            if ddx > 0:
                strength_level = '🟢 中等'
            else:
                strength_level = '🔴 中等'
        else:
            strength_level = '⚪ 弱'
        
        # 趋势判断
        if ddx > 0.05 and persistence > 0.6:
            trend = '🟢 强势吸筹'
            interpretation = f'主力强势吸筹（强度{ddx:.2%}，持续性{persistence:.1%}），机构持续进场'
        elif ddx > 0.02 and persistence > 0.5:
            trend = '🟢 温和吸筹'
            interpretation = f'主力温和吸筹（强度{ddx:.2%}，持续性{persistence:.1%}），机构逐步建仓'
        elif ddx < -0.05 and persistence < 0.4:
            trend = '⛔ 强势出货'
            interpretation = f'主力强势出货（强度{ddx:.2%}，持续性{persistence:.1%}），机构持续减仓'
        elif ddx < -0.02 and persistence < 0.5:
            trend = '⛔ 温和出货'
            interpretation = f'主力温和出货（强度{ddx:.2%}，持续性{persistence:.1%}），机构逐步减仓'
        elif persistence > 0.6 and abs_ddx > 0.01:
            trend = '🟢 震荡吸筹'
            interpretation = f'震荡中吸筹（强度{ddx:.2%}，持续性{persistence:.1%}），低吸高抛'
        elif persistence < 0.4 and abs_ddx > 0.01:
            trend = '⛔ 震荡出货'
            interpretation = f'震荡中出货（强度{ddx:.2%}，持续性{persistence:.1%}），高抛低吸'
        else:
            trend = '⚪ 震荡横盘'
            interpretation = f'盘面震荡（强度{ddx:.2%}，持续性{persistence:.1%}），多空均衡'
        
        return trend, strength_level, interpretation
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'ddx': 0.0,
            'trend': '⚪ 数据不足',
            'strength_level': '⚪ 弱',
            'persistence': 0.0,
            'consistency': 0.0,
            'composite_score': 0.0,
            'main_force_net': 0.0,
            'interpretation': '数据不足，无法计算主力强度',
            'buy_days': 0,
            'sell_days': 0,
            'total_days': 0,
            'circulating_value': 0.0,
            'current_price': 0.0
        }
    
    def compare_stocks(
        self,
        stock_data: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        横向对比多只股票的主力强度
        
        Args:
            stock_data: 字典，格式：{股票代码: {'fund_flow': df, 'total_shares': float, 'price': float}}
        
        Returns:
            DataFrame，包含所有股票的主力强度对比
        """
        results = []
        
        for stock_code, data in stock_data.items():
            result = self.calculate(
                fund_flow_data=data.get('fund_flow'),
                total_shares=data.get('total_shares', 0),
                current_price=data.get('price')
            )
            result['stock_code'] = stock_code
            results.append(result)
        
        df = pd.DataFrame(results)
        
        # 按DDX降序排列
        df = df.sort_values('ddx', ascending=False)
        
        return df
    
    def get_ranking(self, fund_flow_data: pd.DataFrame, total_shares: float) -> str:
        """
        获取主力强度排名描述
        
        Args:
            fund_flow_data: 资金流向数据
            total_shares: 流通股本（亿股）
        
        Returns:
            排名描述字符串
        """
        result = self.calculate(fund_flow_data, total_shares)
        
        ddx = result['ddx']
        strength_level = result['strength_level']
        trend = result['trend']
        
        return f"{strength_level} | {trend} | DDX: {ddx:+.2%}"
    
    def get_signal(self, fund_flow_data: pd.DataFrame, total_shares: float) -> str:
        """
        获取主力信号
        
        Args:
            fund_flow_data: 资金流向数据
            total_shares: 流通股本（亿股）
        
        Returns:
            信号字符串（BUY/SELL/HOLD）
        """
        result = self.calculate(fund_flow_data, total_shares)
        
        ddx = result['ddx']
        persistence = result['persistence']
        composite_score = result['composite_score']
        
        # 强势吸筹 → 买入信号
        if ddx > 0.03 and persistence > 0.5 and composite_score > 0.6:
            return 'BUY'
        # 强势出货 → 卖出信号
        elif ddx < -0.03 and persistence < 0.5 and composite_score > 0.6:
            return 'SELL'
        # 其他 → 持有信号
        else:
            return 'HOLD'


# 便捷函数
def calculate_main_force_strength(
    fund_flow_data: pd.DataFrame,
    total_shares: float,
    current_price: float = None
) -> Dict[str, Any]:
    """
    计算主力强度指标的便捷函数
    
    Args:
        fund_flow_data: 资金流向数据
        total_shares: 流通股本（亿股）
        current_price: 当前股价
        
    Returns:
        主力强度指标字典
    """
    calculator = MainForceStrength()
    return calculator.calculate(fund_flow_data, total_shares, current_price)


# 导出
__all__ = ['MainForceStrength', 'calculate_main_force_strength']