"""
游资操作风格识别模块
5维度综合评估: 连续关注指数、资金实力评分、操作成功率、行业浓度、选时能力
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class CapitalProfile:
    """游资画像数据类"""
    capital_name: str
    overall_score: float  # 综合评分 0-100
    capital_grade: str  # A/B/C/D
    capital_type: str  # 短线客 / 趋势客 / 对抗手 / 机构化
    
    # 5维度评分
    focus_continuity_score: float  # 连续关注指数
    capital_strength_score: float  # 资金实力评分
    success_rate: float  # 操作成功率
    sector_concentration: float  # 行业浓度 (0-1)
    timing_ability_score: float  # 选时能力评分
    
    top_sectors: List[Dict]  # 偏好板块 [{'行业': '新能源', '频率': 0.35}]
    top_stocks: List[Dict]  # 常操作股票 [{'代码': '000001', '频率': 0.12}]
    risk_warnings: List[str]  # 风险提示
    
    recent_performance: Dict  # 最近30天表现 {'盈利天数': 15, '亏损天数': 8, '平手天数': 7}
    operation_stats: Dict  # 操作统计 {'总操作数': 100, '买入次数': 60, '卖出次数': 40}


class CapitalProfiler:
    """游资画像分析器"""
    
    def __init__(self, min_operations: int = 5, lookback_days: int = 180):
        """
        初始化分析器
        
        Args:
            min_operations: 最少操作次数阈值
            lookback_days: 历史查看天数
        """
        self.min_operations = min_operations
        self.lookback_days = lookback_days
    
    def calculate_profile(self, capital_name: str, df_lhb: pd.DataFrame) -> CapitalProfile:
        """
        计算游资画像
        
        Args:
            capital_name: 游资名称
            df_lhb: 龙虎榜数据 (包含: 日期, 游资名称, 股票代码, 股票名称, 成交额, 操作方向, 行业)
        
        Returns:
            CapitalProfile: 游资画像对象
        """
        
        # 数据过滤
        if '游资名称' not in df_lhb.columns:
            raise ValueError("数据缺少 '游资名称' 列")
        
        df_capital = df_lhb[df_lhb['游资名称'] == capital_name].copy()
        
        if len(df_capital) < self.min_operations:
            raise ValueError(f"游资 {capital_name} 操作次数少于 {self.min_operations}")
        
        # 1. 连续关注指数 (操作频度, 加权最近操作)
        focus_continuity_score = self._calculate_focus_continuity(df_capital)
        
        # 2. 资金实力评分 (平均成交额, 最大成交额)
        capital_strength_score = self._calculate_capital_strength(df_capital)
        
        # 3. 操作成功率 (买入后上涨 / 总买入)
        success_rate = self._calculate_success_rate(df_capital)
        
        # 4. 行业浓度 (Herfindahl指数)
        sector_concentration = self._calculate_sector_concentration(df_capital)
        
        # 5. 选时能力 (操作时机是否靠近高点/低点)
        timing_ability_score = self._calculate_timing_ability(df_capital)
        
        # 综合评分 (加权平均)
        weights = {'focus': 0.20, 'strength': 0.25, 'success': 0.30, 'sector': 0.10, 'timing': 0.15}
        overall_score = (
            focus_continuity_score * weights['focus'] +
            capital_strength_score * weights['strength'] +
            success_rate * weights['success'] +
            sector_concentration * 100 * weights['sector'] +
            timing_ability_score * weights['timing']
        )
        
        # 评级
        capital_grade = self._get_grade(overall_score)
        
        # 游资类型识别
        capital_type = self._identify_capital_type(
            focus_continuity_score, 
            sector_concentration, 
            success_rate
        )
        
        # 偏好板块
        top_sectors = self._get_top_sectors(df_capital)
        
        # 常操作股票
        top_stocks = self._get_top_stocks(df_capital)
        
        # 最近30天表现
        recent_performance = self._get_recent_performance(df_capital)
        
        # 操作统计
        operation_stats = self._get_operation_stats(df_capital)
        
        # 风险提示
        risk_warnings = self._generate_risk_warnings(
            overall_score, success_rate, sector_concentration, df_capital
        )
        
        return CapitalProfile(
            capital_name=capital_name,
            overall_score=overall_score,
            capital_grade=capital_grade,
            capital_type=capital_type,
            focus_continuity_score=focus_continuity_score,
            capital_strength_score=capital_strength_score,
            success_rate=success_rate,
            sector_concentration=sector_concentration,
            timing_ability_score=timing_ability_score,
            top_sectors=top_sectors,
            top_stocks=top_stocks,
            risk_warnings=risk_warnings,
            recent_performance=recent_performance,
            operation_stats=operation_stats
        )
    
    def _calculate_focus_continuity(self, df: pd.DataFrame) -> float:
        """连续关注指数: 操作频度 + 最近操作加权"""
        if '日期' not in df.columns:
            return 50.0
        
        # 操作频度 (每周平均操作次数)
        date_range = (pd.to_datetime(df['日期']).max() - pd.to_datetime(df['日期']).min()).days
        if date_range == 0:
            return 50.0
        
        weekly_freq = len(df) / (date_range / 7)
        freq_score = min(weekly_freq * 10, 100)  # 每周10次为满分
        
        # 最近操作加权 (最近操作权重更高)
        df_sorted = df.sort_values('日期', ascending=False)
        recent_count = len(df_sorted[pd.to_datetime(df_sorted['日期']) >= 
                                      pd.to_datetime(df_sorted['日期'].iloc[0]) - timedelta(days=30)])
        recent_score = min(recent_count * 3, 100)
        
        return freq_score * 0.6 + recent_score * 0.4
    
    def _calculate_capital_strength(self, df: pd.DataFrame) -> float:
        """资金实力评分: 平均成交额 + 最大成交额"""
        if '成交额' not in df.columns:
            return 50.0
        
        # 转换成交额为浮点数 (亿元)
        amounts = pd.to_numeric(df['成交额'], errors='coerce')
        amounts = amounts.dropna()
        
        if len(amounts) == 0:
            return 50.0
        
        avg_amount = amounts.mean()
        max_amount = amounts.max()
        
        # 对标: 平均0.5亿为50分, 5亿为100分
        avg_score = min((avg_amount / 5) * 100, 100)
        max_score = min((max_amount / 20) * 100, 100)
        
        return avg_score * 0.6 + max_score * 0.4
    
    def _calculate_success_rate(self, df: pd.DataFrame) -> float:
        """操作成功率: 盈利操作次数 / 总操作次数"""
        if '操作方向' not in df.columns:
            return 50.0
        
        # 简化模型: 假设买入后上涨即为成功 (实际需要与K线数据对接)
        # 这里用代理指标: 相同股票多次买入 = 看好 = 成功率高
        
        buy_count = len(df[df['操作方向'].str.contains('买', na=False)])
        sell_count = len(df[df['操作方向'].str.contains('卖', na=False)])
        
        # 理想状态: 买卖比接近0.5 (先买后卖)
        if buy_count == 0:
            return 50.0
        
        buy_sell_ratio = min(sell_count / buy_count, 1.0)
        base_rate = buy_sell_ratio * 50 + 50  # 50-100
        
        # 重复操作同一股票 = 信心 = 成功率高
        repeat_bonus = len(df.groupby('股票代码')) < len(df) * 0.5
        if repeat_bonus:
            base_rate = min(base_rate * 1.1, 100)
        
        return base_rate
    
    def _calculate_sector_concentration(self, df: pd.DataFrame) -> float:
        """行业浓度: Herfindahl指数 (0-1, 1为完全集中)"""
        if '行业' not in df.columns:
            return 0.5
        
        sector_counts = df['行业'].value_counts()
        total_ops = len(df)
        
        # Herfindahl指数: Σ(份额^2)
        herfindahl = sum((count / total_ops) ** 2 for count in sector_counts)
        
        return herfindahl
    
    def _calculate_timing_ability(self, df: pd.DataFrame) -> float:
        """选时能力: 操作时机是否靠近高点/低点"""
        if '股票代码' not in df.columns:
            return 50.0
        
        # 简化模型: 同一股票多个操作, 间隔时间越短越说明积极择时
        df_sorted = df.sort_values(['股票代码', '日期'])
        
        same_stock = df_sorted.groupby('股票代码').size()
        if len(same_stock) == 0 or same_stock.max() == 1:
            return 50.0
        
        # 多操作股票的比例越高, 说明择时能力越强
        multi_ops_ratio = (same_stock > 1).sum() / len(same_stock)
        
        return multi_ops_ratio * 100
    
    def _get_grade(self, score: float) -> str:
        """根据分数返回等级"""
        if score >= 80:
            return 'A'
        elif score >= 60:
            return 'B'
        elif score >= 40:
            return 'C'
        else:
            return 'D'
    
    def _identify_capital_type(self, focus: float, concentration: float, success: float) -> str:
        """识别游资类型"""
        if concentration > 0.6 and success > 70:
            return '对抗手'  # 集中行业, 高成功率
        elif focus > 70 and success > 65:
            return '趋势客'  # 高频操作, 高成功率
        elif concentration < 0.3:
            return '机构化'  # 分散行业
        else:
            return '短线客'  # 通用类型
    
    def _get_top_sectors(self, df: pd.DataFrame, top_n: int = 5) -> List[Dict]:
        """获取偏好行业"""
        if '行业' not in df.columns:
            return []
        
        sector_counts = df['行业'].value_counts()
        total = len(df)
        
        return [
            {'行业': sector, '频率': count / total}
            for sector, count in sector_counts.head(top_n).items()
        ]
    
    def _get_top_stocks(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """获取常操作股票"""
        if '股票代码' not in df.columns or '股票名称' not in df.columns:
            return []
        
        stock_counts = df.groupby(['股票代码', '股票名称']).size()
        total = len(df)
        
        result = []
        for (code, name), count in stock_counts.head(top_n).items():
            result.append({
                '代码': code,
                '名称': name,
                '频率': count / total
            })
        
        return result
    
    def _get_recent_performance(self, df: pd.DataFrame) -> Dict:
        """最近30天表现"""
        if '日期' not in df.columns or '操作方向' not in df.columns:
            return {'盈利天数': 0, '亏损天数': 0, '平手天数': 0}
        
        df_recent = df[pd.to_datetime(df['日期']) >= 
                       pd.to_datetime(df['日期']).max() - timedelta(days=30)]
        
        # 简化: 买入操作视为盈利
        profit_days = len(df_recent[df_recent['操作方向'].str.contains('买', na=False)])
        loss_days = len(df_recent[df_recent['操作方向'].str.contains('卖', na=False)])
        
        return {
            '盈利天数': profit_days,
            '亏损天数': loss_days,
            '平手天数': len(df_recent) - profit_days - loss_days
        }
    
    def _get_operation_stats(self, df: pd.DataFrame) -> Dict:
        """操作统计"""
        if '操作方向' not in df.columns:
            return {'总操作数': 0, '买入次数': 0, '卖出次数': 0}
        
        total_ops = len(df)
        buy_count = len(df[df['操作方向'].str.contains('买', na=False)])
        sell_count = len(df[df['操作方向'].str.contains('卖', na=False)])
        
        return {
            '总操作数': total_ops,
            '买入次数': buy_count,
            '卖出次数': sell_count
        }
    
    def _generate_risk_warnings(self, score: float, success_rate: float, 
                                concentration: float, df: pd.DataFrame) -> List[str]:
        """生成风险提示"""
        warnings = []
        
        if score < 40:
            warnings.append("综合评分过低，操作风格不稳定")
        
        if success_rate < 40:
            warnings.append("操作成功率较低，盈利能力较弱")
        
        if concentration > 0.7:
            warnings.append("行业集中度过高，分散风险较低")
        
        if len(df) < 10:
            warnings.append("操作记录不足，分析结果可信度有限")
        
        return warnings if warnings else ["暂无风险提示"]
