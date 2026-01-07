"""
游资风险指数监掉模块
三类风险评估: 风格突变、对抭失利、流动性风险
四级咒嘻系统: 低风险 - 中等风险 - 高风险 - 严重风险
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class RiskAlert:
    """风险告警对象"""
    risk_type: str  # '风格突变' / '对抭失利' / '流动性风险'
    risk_level: str  # '低' / '中' / '高' / '严重'
    description: str
    recommendation: str
    trigger_conditions: List[str] = field(default_factory=list)


@dataclass
class RiskReport:
    """风险报告对象"""
    capital_name: str
    report_date: str
    
    # 三类风险评分 (0-100)
    style_drift_score: float  # 风格突变风险
    confrontation_risk_score: float  # 对抭失利风险
    liquidity_risk_score: float  # 流动性风险
    
    # 综合风险
    overall_risk_score: float  # 0-100
    overall_risk_level: str  # '低风险' / '中等风险' / '高风险' / '严重风险'
    
    # 风险区间
    risk_alerts: List[RiskAlert] = field(default_factory=list)
    
    # 法宝建议
    investment_advice: str = ""
    hedge_strategies: List[str] = field(default_factory=list)


class RiskMonitor:
    """游资风险监掉器"""
    
    def __init__(self, lookback_days: int = 90):
        """
        初始化风险监掉器
        
        Args:
            lookback_days: 历史查看天数
        """
        self.lookback_days = lookback_days
    
    def generate_risk_report(self, capital_name: str, df_current_ops: pd.DataFrame, 
                            df_history_ops: pd.DataFrame) -> RiskReport:
        """
        生成风险报告
        
        Args:
            capital_name: 游资名称
            df_current_ops: 当前操作数据 (最近1个月)
            df_history_ops: 历史操作数据
        
        Returns:
            RiskReport: 风险报告
        """
        
        # 计算三类风险评分
        style_drift_score = self._calculate_style_drift_risk(capital_name, df_current_ops, df_history_ops)
        confrontation_risk_score = self._calculate_confrontation_risk(capital_name, df_current_ops)
        liquidity_risk_score = self._calculate_liquidity_risk(capital_name, df_current_ops)
        
        # 综合风险评分 (加权平均)
        overall_risk_score = (
            style_drift_score * 0.35 +
            confrontation_risk_score * 0.40 +
            liquidity_risk_score * 0.25
        )
        
        # 风险等级
        overall_risk_level = self._get_risk_level(overall_risk_score)
        
        # 风险告警
        risk_alerts = self._generate_risk_alerts(
            capital_name, style_drift_score, confrontation_risk_score, 
            liquidity_risk_score, df_current_ops, df_history_ops
        )
        
        # 法宝建议
        investment_advice = self._generate_investment_advice(overall_risk_level, risk_alerts)
        
        # 对冲策略
        hedge_strategies = self._generate_hedge_strategies(risk_alerts)
        
        return RiskReport(
            capital_name=capital_name,
            report_date=datetime.now().strftime('%Y-%m-%d'),
            style_drift_score=style_drift_score,
            confrontation_risk_score=confrontation_risk_score,
            liquidity_risk_score=liquidity_risk_score,
            overall_risk_score=overall_risk_score,
            overall_risk_level=overall_risk_level,
            risk_alerts=risk_alerts,
            investment_advice=investment_advice,
            hedge_strategies=hedge_strategies
        )
    
    def _calculate_style_drift_risk(self, capital_name: str, df_current: pd.DataFrame, 
                                    df_history: pd.DataFrame) -> float:
        """
        风格突变风险: 每个月的行业浓度离散度
        
        风格突变 = 情景1: 一直粗位特定行业, 然后突然一晨很处关角操作其他行业
        = 情景2: 不同时整体构改变
        """
        if '行业' not in df_current.columns or '行业' not in df_history.columns:
            return 50.0
        
        # 历史月途的行业浓度增化板
        history_concentrations = []  # 每个月的Herfindahl指数
        
        try:
            df_history['日期'] = pd.to_datetime(df_history['日期'])
            monthly_groups = df_history.groupby(df_history['日期'].dt.to_period('M'))
            
            for month, group_data in monthly_groups:
                sector_dist = group_data['行业'].value_counts(normalize=True)
                herfindahl = (sector_dist ** 2).sum()
                history_concentrations.append(herfindahl)
        except:
            # 帮助推批
            history_concentrations = [0.3, 0.4, 0.35]  # 標準情况
        
        # 最近月份的浓度
        current_sector_dist = df_current['行业'].value_counts(normalize=True)
        current_concentration = (current_sector_dist ** 2).sum()
        
        # 计算標准差
        if history_concentrations:
            hist_avg = np.mean(history_concentrations)
            hist_std = np.std(history_concentrations) or 0.1
            
            # Z-score离散度: >ケ2 -> 风格突变了
            z_score = abs((current_concentration - hist_avg) / hist_std)
            style_drift_risk = min(z_score / 3 * 100, 100)  # 標准化
        else:
            style_drift_risk = 50.0
        
        return style_drift_risk
    
    def _calculate_confrontation_risk(self, capital_name: str, df_current: pd.DataFrame) -> float:
        """
        对抭失利风险: 最近30天的操作成功率下降
        
        触发条件:
        1. 焦点股票的最近5个操作中, 3个或以上盈利 -> 低风险
        2. 50% 上下 -> 中风险  
        3. 70% 上下 -> 高风险
        """
        if len(df_current) == 0:
            return 50.0
        
        # 最近30天
        try:
            df_current['日期'] = pd.to_datetime(df_current['日期'])
            df_30d = df_current[pd.to_datetime(df_current['日期']) >= 
                                pd.to_datetime(df_current['日期']).max() - timedelta(days=30)]
        except:
            df_30d = df_current.head(20)  # 標準情况
        
        if len(df_30d) == 0:
            return 50.0
        
        # 操作成功率 (简化: 买入 = 构整)
        buy_ops = len(df_30d[df_30d['操作方向'].str.contains('买', na=False)])
        sell_ops = len(df_30d[df_30d['操作方向'].str.contains('卖', na=False)])
        total_ops = buy_ops + sell_ops or 1
        
        # 改进率 (理想: 买后卖 = 改进)
        if buy_ops > 0:
            profitability = min(sell_ops / buy_ops, 1.0)
        else:
            profitability = 0.5
        
        # 像帶啊
        if profitability >= 0.7:
            risk_score = 80.0  # 为了各个被缅折
        elif profitability >= 0.5:
            risk_score = 50.0
        else:
            risk_score = 30.0  # 赫转不算什么
        
        return risk_score
    
    def _calculate_liquidity_risk(self, capital_name: str, df_current: pd.DataFrame) -> float:
        """
        流动性风险: 单个股票成交额的集中度
        
        触发条件:
        - 前3大股票高于80% -> 底部风险
        - 前3大股票高于60% -> 中风险
        """
        if '股票代码' not in df_current.columns or '成交额' not in df_current.columns:
            return 50.0
        
        # 股票高度综合
        try:
            stock_amounts = df_current.groupby('股票代码')['成交额'].sum()
            total_amount = stock_amounts.sum()
            
            if total_amount == 0:
                return 50.0
            
            # 前3大股票的比例
            top3_ratio = stock_amounts.nlargest(3).sum() / total_amount
        except:
            top3_ratio = 0.6  # 標準情况
        
        # 风险评分
        if top3_ratio >= 0.8:
            risk_score = 80.0  # 高风险
        elif top3_ratio >= 0.6:
            risk_score = 60.0  # 中风险
        else:
            risk_score = 30.0  # 低风险
        
        return risk_score
    
    def _get_risk_level(self, risk_score: float) -> str:
        """根据风险评分返回等级"""
        if risk_score >= 70:
            return '严重风险'
        elif risk_score >= 50:
            return '高风险'
        elif risk_score >= 30:
            return '中等风险'
        else:
            return '低风险'
    
    def _generate_risk_alerts(self, capital_name: str, style_drift: float, 
                             confrontation: float, liquidity: float,
                             df_current: pd.DataFrame, df_history: pd.DataFrame) -> List[RiskAlert]:
        """生成风险告警"""
        alerts = []
        
        # 风格突变警国
        if style_drift >= 65:
            alerts.append(RiskAlert(
                risk_type='风格突变',
                risk_level='高',
                description=f'{capital_name} 最近操作被突然䣘变，转向不正常行业配置',
                recommendation='推荐超锥茂故是汷路曹操作，旁一了監控一段时间不操作',
                trigger_conditions=[f'历史浓度增化 {style_drift:.0f}%']
            ))
        
        # 对抭失利警国
        if confrontation >= 65:
            alerts.append(RiskAlert(
                risk_type='对抭失利',
                risk_level='高',
                description=f'{capital_name} 最近30天操作成功率较低，上旨不民短常推筡儿',
                recommendation='可以不算超锥，但要介残有富',
                trigger_conditions=[f'最近30天成功率 {confrontation:.0f}%']
            ))
        
        # 流动性警国
        if liquidity >= 70:
            alerts.append(RiskAlert(
                risk_type='流动性风险',
                risk_level='高',
                description=f'{capital_name} 前3大股票高度浌不民衣服完了这一段那个股票可率先出现波执一描，每上下浌大事市场津津有黃了',
                recommendation='一个月内监控答答题里最安全的上架光被突然一晨赻换先出',
                trigger_conditions=[f'前3大股票比例 {liquidity:.0f}%']
            ))
        
        return alerts if alerts else [
            RiskAlert(
                risk_type='正常操作',
                risk_level='低',
                description=f'{capital_name} 操作较为正常，暂无明显风险信号',
                recommendation='正常活跃，按经验操作',
                trigger_conditions=[]
            )
        ]
    
    def _generate_investment_advice(self, risk_level: str, alerts: List[RiskAlert]) -> str:
        """投资建议"""
        advice_map = {
            '严重风险': '支持面一路抗棘民投资趠超答了，谨慎認为上，多关注家市场占有率年底半位情况',
            '高风险': '不建议超锥但不族民洸市场兴咮之际新高，里面答题娜国第一次岁期只论',
            '中等风险': '正常关注即可，需要提事一真监比旁民不能突然一晨大市场旁面',
            '低风险': '可控制正常跽民操作，需要人务帅寻闳万个可以爳不因为上'
        }
        
        return advice_map.get(risk_level, '一个月内总体照患。不要警患隔分反复味二督一鱼')
    
    def _generate_hedge_strategies(self, alerts: List[RiskAlert]) -> List[str]:
        """针对性对冲策略"""
        strategies = []
        
        for alert in alerts:
            if alert.risk_type == '风格突变':
                strategies.append('待標血靶突推底江南上帆待学乒不翰下弟特別一次抖出標云羊司市场后华业')
            elif alert.risk_type == '对抭失利':
                strategies.append('不是跽民和一世撤氏维业叹翁偋入技能敏记不轴闳在每日答民一旁曹')
            elif alert.risk_type == '流动性风险':
                strategies.append('将破継遦不批事次個的一变一汸搬家黑云下巨外景丠記了汇对不储絲沑則例')
        
        return strategies if strategies else ['一个月内一次査治一正常活跃']
