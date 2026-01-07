"""
增强指标系统 - 完整的量化评估指标体系
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricsResult:
    """指标计算结果"""
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    max_drawdown: float
    max_consecutive_losses: int
    var_95: float
    recovery_time: int
    annual_return: float
    total_return: float
    win_rate: float
    monthly_returns: np.ndarray
    equity_curve: np.ndarray


class EnhancedMetrics:
    """
    完整的量化评估指标体系
    
    包含 12 个关键指标:
    - 夏普比率 (Sharpe Ratio)
    - 索提诺比率 (Sortino Ratio)
    - 卡玛比率 (Calmar Ratio)
    - 信息比率 (Information Ratio)
    - 最大回撤 (Max Drawdown)
    - 最大连续亏损 (Max Consecutive Losses)
    - 风险价值 (VaR @ 95%)
    - 恢复时间 (Recovery Time)
    - 年化收益 (Annual Return)
    - 总收益 (Total Return)
    - 胜率 (Win Rate)
    - 月度收益 (Monthly Returns)
    """
    
    def __init__(self, returns, benchmark_returns=None, risk_free_rate=0.03):
        """
        初始化指标系统
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）
            risk_free_rate: 无风险利率（默认 3%）
        """
        self.returns = np.array(returns)
        self.benchmark_returns = np.array(benchmark_returns) if benchmark_returns is not None else None
        self.risk_free_rate = risk_free_rate
        
        # 计算月度收益
        self.monthly_returns = self._calculate_monthly_returns()
        
        # 计算权益曲线
        self.equity_curve = np.cumprod(1 + self.returns)
    
    def _calculate_monthly_returns(self) -> np.ndarray:
        """计算月度收益率"""
        if len(self.returns) < 20:
            return np.array([])
        
        # 假设每天有 252 个交易日，每月约 21 天
        monthly_returns = []
        for i in range(0, len(self.returns), 21):
            month_returns = self.returns[i:i+21]
            if len(month_returns) > 0:
                monthly_returns.append(np.prod(1 + month_returns) - 1)
        
        return np.array(monthly_returns)
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return np.prod(1 + self.returns) - 1
    
    @property
    def annual_return(self) -> float:
        """年化收益率"""
        if len(self.returns) == 0:
            return 0.0
        
        total = self.total_return
        years = len(self.returns) / 252
        if years == 0:
            return 0.0
        
        return (1 + total) ** (1 / years) - 1
    
    @property
    def sharpe_ratio(self) -> float:
        """
        夏普比率 (风险调整后收益)
        
        目标: > 1.0
        优秀: > 2.0
        """
        if len(self.returns) < 2:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / 252
        std = np.std(excess_returns)
        
        if std == 0:
            return 0.0
        
        return np.mean(excess_returns) / std * np.sqrt(252)
    
    @property
    def sortino_ratio(self) -> float:
        """
        索提诺比率 (只考虑下行风险)
        
        比夏普更严格，因为只惩罚亏损
        目标: > 2.0 (比夏普要求高)
        """
        if len(self.returns) < 2:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        downside_vol = np.std(downside_returns) * np.sqrt(252)
        
        if downside_vol == 0:
            return 0.0
        
        return np.mean(excess_returns) / downside_vol * np.sqrt(252)
    
    @property
    def calmar_ratio(self) -> float:
        """
        卡玛比率 (收益/最大回撤)
        
        衡量恢复能力，越高越好
        目标: > 0.5
        """
        annual_return = self.annual_return
        max_drawdown = self.max_drawdown
        
        if max_drawdown == 0:
            return 0.0
        
        return annual_return / abs(max_drawdown)
    
    @property
    def information_ratio(self) -> float:
        """
        信息比率 (超额收益的稳定性)
        
        衡量策略相对基准的稳定性
        IR = 超额收益 / 超额风险
        目标: > 0.5
        优秀: > 1.0
        """
        if self.benchmark_returns is None or len(self.benchmark_returns) < 2:
            return 0.0
        
        excess_returns = self.returns - self.benchmark_returns
        std = np.std(excess_returns)
        
        if std == 0:
            return 0.0
        
        return np.mean(excess_returns) / std * np.sqrt(252)
    
    @property
    def max_drawdown(self) -> float:
        """最大回撤"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        running_max = np.maximum.accumulate(self.equity_curve)
        drawdown = (self.equity_curve - running_max) / running_max
        return np.min(drawdown)
    
    @property
    def max_consecutive_losses(self) -> int:
        """
        最大连续亏损次数
        
        风险指标: 心理承受能力
        目标: < 5 个月
        """
        if len(self.monthly_returns) == 0:
            return 0
        
        consecutive_losses = 0
        max_losses = 0
        
        for ret in self.monthly_returns:
            if ret < 0:
                consecutive_losses += 1
                max_losses = max(max_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        return max_losses
    
    @property
    def var_95(self) -> float:
        """
        风险价值 (95% 置信度)
        
        最坏情况下的最大亏损
        例如: VaR 5% 意味着 95% 概率亏损不超过此数
        """
        if len(self.returns) == 0:
            return 0.0
        
        return np.percentile(self.returns, 5)
    
    @property
    def recovery_time(self) -> int:
        """
        最大回撤恢复时间
        
        从最低点恢复到前高的天数
        越短越好 (表示抗压能力强)
        """
        if len(self.equity_curve) < 2:
            return 0
        
        running_max = np.maximum.accumulate(self.equity_curve)
        drawdown = (self.equity_curve - running_max) / running_max
        
        # 找到最大回撤点
        max_dd_idx = np.argmin(drawdown)
        
        # 找到恢复点 (回到前高)
        recovery_idx = None
        for i in range(max_dd_idx, len(self.equity_curve)):
            if self.equity_curve[i] >= running_max[max_dd_idx]:
                recovery_idx = i
                break
        
        if recovery_idx is None:
            return len(self.equity_curve) - max_dd_idx  # 还未恢复
        
        return recovery_idx - max_dd_idx
    
    @property
    def win_rate(self) -> float:
        """胜率"""
        if len(self.returns) == 0:
            return 0.0
        
        winning_days = np.sum(self.returns > 0)
        return winning_days / len(self.returns)
    
    def calculate_all(self) -> MetricsResult:
        """
        计算所有指标
        
        Returns:
            MetricsResult 对象
        """
        return MetricsResult(
            sharpe_ratio=self.sharpe_ratio,
            sortino_ratio=self.sortino_ratio,
            calmar_ratio=self.calmar_ratio,
            information_ratio=self.information_ratio,
            max_drawdown=self.max_drawdown,
            max_consecutive_losses=self.max_consecutive_losses,
            var_95=self.var_95,
            recovery_time=self.recovery_time,
            annual_return=self.annual_return,
            total_return=self.total_return,
            win_rate=self.win_rate,
            monthly_returns=self.monthly_returns,
            equity_curve=self.equity_curve
        )
    
    def get_summary(self) -> str:
        """
        获取指标摘要
        
        Returns:
            格式化的摘要字符串
        """
        result = self.calculate_all()
        
        summary = f"""
📊 策略评估报告
================
📈 收益指标:
  - 总收益率: {result.total_return:.2%}
  - 年化收益率: {result.annual_return:.2%}
  - 胜率: {result.win_rate:.2%}

🎯 风险调整收益:
  - 夏普比率: {result.sharpe_ratio:.2f}
  - 索提诺比率: {result.sortino_ratio:.2f}
  - 卡玛比率: {result.calmar_ratio:.2f}
  - 信息比率: {result.information_ratio:.2f}

⚠️ 风险指标:
  - 最大回撤: {result.max_drawdown:.2%}
  - VaR@95%: {result.var_95:.2%}
  - 最大连续亏损: {result.max_consecutive_losses} 个月
  - 恢复时间: {result.recovery_time} 天
"""
        return summary