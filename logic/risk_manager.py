"""
风险管理器 - 实时风控指标和红绿灯系统
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict
from logic.enhanced_metrics import EnhancedMetrics
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """
    风险管理与风控指标
    
    实时风控提示 (红绿灯系统):
    - GREEN: 风险可控
    - YELLOW: 需要关注
    - RED: 立即止损
    """
    
    def __init__(self, equity_curve, monthly_returns, returns):
        """
        初始化风险管理器
        
        Args:
            equity_curve: 权益曲线
            monthly_returns: 月度收益率
            returns: 日收益率
        """
        self.equity_curve = np.array(equity_curve) if equity_curve is not None else None
        self.monthly_returns = np.array(monthly_returns) if monthly_returns is not None else None
        self.returns = np.array(returns) if returns is not None else None
        
        # 初始化指标系统
        if self.returns is not None:
            self.metrics = EnhancedMetrics(self.returns)
        else:
            self.metrics = None
    
    def assess_risk_level(self) -> Tuple[str, str]:
        """
        整体风险评估 (红绿灯系统)
        
        Returns:
            (风险等级, 风险消息)
            风险等级: 'GREEN', 'YELLOW', 'RED'
        """
        if self.metrics is None:
            return 'GREEN', "无法评估风险"
        
        score = 100
        reasons = []
        
        # 1. 最大回撤检查 (-15% ~ -50%)
        max_dd = self.metrics.max_drawdown
        if max_dd < -0.5:
            score -= 50
            reasons.append(f"最大回撤过大: {max_dd:.1%}")
        elif max_dd < -0.2:
            score -= 30
            reasons.append(f"最大回撤较大: {max_dd:.1%}")
        elif max_dd < -0.15:
            score -= 15
            reasons.append(f"最大回撤: {max_dd:.1%}")
        
        # 2. 夏普比率检查 (0 ~ 2.0)
        sharpe = self.metrics.sharpe_ratio
        if sharpe < 0.5:
            score -= 25
            reasons.append(f"夏普比率过低: {sharpe:.2f}")
        elif sharpe < 1.0:
            score -= 10
            reasons.append(f"夏普比率不足: {sharpe:.2f}")
        elif sharpe > 1.5:
            score += 10
        
        # 3. 连续亏损检查
        consecutive_losses = self.metrics.max_consecutive_losses
        if consecutive_losses > 6:
            score -= 30
            reasons.append(f"连续亏损超过 6 个月")
        elif consecutive_losses > 3:
            score -= 15
            reasons.append(f"连续亏损 {consecutive_losses} 个月")
        
        # 4. VaR 检查
        var_95 = self.metrics.var_95
        if var_95 < -0.05:
            score -= 20
            reasons.append(f"单日最大风险过高: {var_95:.2%}")
        
        # 5. 索提诺比率检查
        sortino = self.metrics.sortino_ratio
        if sortino < 0.5:
            score -= 15
            reasons.append(f"下行风险调整收益过低: {sortino:.2f}")
        
        # 最终评定
        if score > 75:
            level = 'GREEN'
            msg = "风险可控" if not reasons else "风险可控: " + ", ".join(reasons)
        elif score > 50:
            level = 'YELLOW'
            msg = "需要关注: " + ", ".join(reasons)
        else:
            level = 'RED'
            msg = "难以持续: " + ", ".join(reasons)
        
        return level, msg
    
    @property
    def risk_dashboard(self) -> Dict[str, any]:
        """
        风控仪表板 (用于 UI 显示)
        
        Returns:
            风控指标字典
        """
        if self.metrics is None:
            return {}
        
        return {
            '最大回撤': f"{self.metrics.max_drawdown:.2%}",
            '夏普比率': f"{self.metrics.sharpe_ratio:.2f}",
            '索提诺比率': f"{self.metrics.sortino_ratio:.2f}",
            '卡玛比率': f"{self.metrics.calmar_ratio:.2f}",
            '信息比率': f"{self.metrics.information_ratio:.2f}",
            '连续亏损': f"{self.metrics.max_consecutive_losses} 个月",
            'VaR@95%': f"{self.metrics.var_95:.2%}",
            '恢复时间': f"{self.metrics.recovery_time} 天",
            '年化收益': f"{self.metrics.annual_return:.2%}",
            '总收益': f"{self.metrics.total_return:.2%}",
            '胜率': f"{self.metrics.win_rate:.2%}",
            '风险等级': self.assess_risk_level()[0],
        }
    
    def check_trading_limits(self) -> Tuple[bool, str]:
        """
        检查是否触发了交易限制
        
        Returns:
            (是否允许交易, 原因)
        """
        if self.metrics is None:
            return True, "无法检查限制"
        
        # 1. 最大回撤限制
        if self.metrics.max_drawdown < -0.2:
            return False, f"触发风控止损：最大回撤达到 {self.metrics.max_drawdown:.1%}"
        
        # 2. 连续亏损限制
        if self.metrics.max_consecutive_losses > 6:
            return False, f"触发风控止损：连续亏损 {self.metrics.max_consecutive_losses} 个月"
        
        # 3. VaR 限制
        if self.metrics.var_95 < -0.08:
            return False, f"触发风控止损：单日风险价值 {self.metrics.var_95:.1%}"
        
        return True, "风控检查通过"
    
    def get_risk_summary(self) -> str:
        """
        获取风险摘要
        
        Returns:
            格式化的摘要字符串
        """
        if self.metrics is None:
            return "无法生成风险摘要"
        
        level, msg = self.assess_risk_level()
        dashboard = self.risk_dashboard
        
        summary = f"""
🛡️ 风险评估报告
================
🚦 风险等级: {level}
📊 风险消息: {msg}

📈 收益指标:
  - 年化收益: {dashboard['年化收益']}
  - 总收益: {dashboard['总收益']}
  - 胜率: {dashboard['胜率']}

🎯 风险调整收益:
  - 夏普比率: {dashboard['夏普比率']}
  - 索提诺比率: {dashboard['索提诺比率']}
  - 卡玛比率: {dashboard['卡玛比率']}
  - 信息比率: {dashboard['信息比率']}

⚠️ 风险指标:
  - 最大回撤: {dashboard['最大回撤']}
  - VaR@95%: {dashboard['VaR@95%']}
  - 连续亏损: {dashboard['连续亏损']}
  - 恢复时间: {dashboard['恢复时间']}
"""
        return summary