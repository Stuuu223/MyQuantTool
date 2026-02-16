# -*- coding: utf-8 -*-
"""
PortfolioMetrics - 账户级业务指标

核心功能：
1. 每日业务报告（账户收益、调仓次数、换仓收益、退出原因分布）
2. 实时仪表盘
3. 业务指标追踪

版本：V17.0.0
创建日期：2026-02-16
作者：MyQuantTool Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DailyMetrics:
    """每日业务指标"""
    date: str
    起爆点捕捉数: int = 0
    调仓次数: int = 0
    换仓收益: float = 0.0  # 因为换仓而获得的额外收益
    持仓天数分布: Dict[int, int] = field(default_factory=dict)  # {1天: 5次, 2天: 3次, ...}
    退出原因分布: Dict[str, int] = field(default_factory=dict)  # {'主力出逃': 2, '换仓': 3, ...}
    账户收益: float = 0.0
    最大回撤: float = 0.0
    资金利用率: float = 0.0
    
    def add_退出原因(self, reason: str):
        """记录退出原因"""
        self.退出原因分布[reason] = self.退出原因分布.get(reason, 0) + 1
    
    def add_持仓天数(self, days: int):
        """记录持仓天数"""
        self.持仓天数分布[days] = self.持仓天数分布.get(days, 0) + 1


class PortfolioMetrics:
    """
    账户级业务指标
    
    核心功能：
    1. 每日业务报告
    2. 实时仪表盘
    3. 业务指标追踪
    """
    
    def __init__(self):
        # 每日指标
        self.daily_metrics: Dict[str, DailyMetrics] = {}
        
        # 当前指标
        self.current_metrics = DailyMetrics(date=datetime.now().strftime('%Y-%m-%d'))
        
        # 累计指标
        self.total_metrics = {
            '总收益': 0.0,
            '最大回撤': 0.0,
            '调仓次数': 0,
            '起爆点捕捉数': 0
        }
        
        logger.info("✅ PortfolioMetrics初始化成功")
    
    def record_opportunity(self, code: str, reason: str):
        """
        记录起爆点捕捉
        
        Args:
            code: 股票代码
            reason: 捕捉原因
        """
        self.current_metrics.起爆点捕捉数 += 1
        logger.info(f"🎯 起爆点捕捉: {code} ({reason})")
    
    def record_rebalance(self, from_code: str, to_code: str, profit_rate: float):
        """
        记录调仓操作
        
        Args:
            from_code: 卖出股票代码
            to_code: 买入股票代码
            profit_rate: 卖出股票的收益率
        """
        self.current_metrics.调仓次数 += 1
        self.current_metrics.换仓收益 += profit_rate
        logger.info(f"🔄 调仓: {from_code} → {to_code} (收益: {profit_rate:.2%})")
    
    def record_exit(self, code: str, reason: str, hold_days: int, profit_rate: float):
        """
        记录平仓操作
        
        Args:
            code: 股票代码
            reason: 退出原因
            hold_days: 持仓天数
            profit_rate: 收益率
        """
        self.current_metrics.add_退出原因(reason)
        self.current_metrics.add_持仓天数(hold_days)
        logger.info(f"🚪 平仓: {code} ({reason}, 持有{hold_days}天, 收益{profit_rate:.2%})")
    
    def update_account_metrics(self, account_value: float, peak_value: float, available_capital: float):
        """
        更新账户指标
        
        Args:
            account_value: 当前账户价值
            peak_value: 历史最高净值
            available_capital: 可用资金
        """
        # 计算账户收益
        if 'initial_capital' not in self.total_metrics:
            self.total_metrics['initial_capital'] = account_value
        
        self.current_metrics.账户收益 = (account_value - self.total_metrics['initial_capital']) / self.total_metrics['initial_capital']
        
        # 计算最大回撤
        self.current_metrics.最大回撤 = (account_value - peak_value) / peak_value
        
        # 更新历史最大回撤
        if self.current_metrics.最大回撤 < self.total_metrics['最大回撤']:
            self.total_metrics['最大回撤'] = self.current_metrics.最大回撤
        
        # 计算资金利用率
        self.current_metrics.资金利用率 = 1 - (available_capital / account_value)
    
    def generate_daily_report(self) -> str:
        """
        生成每日业务报告
        
        Returns:
            每日报告字符串
        """
        report = f"""
{'═' * 60}
      MyQuantTool 每日业务报告
         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'═' * 60}

📊 账户表现
  - 账户收益: {self.current_metrics.账户收益:.2%}
  - 最大回撤: {self.current_metrics.最大回撤:.2%}
  - 资金利用率: {self.current_metrics.资金利用率:.2%}

📈 交易统计
  - 起爆点捕捉: {self.current_metrics.起爆点捕捉数}次
  - 调仓次数: {self.current_metrics.调仓次数}次
  - 换仓收益: {self.current_metrics.换仓收益:.2%}

⏱️ 持仓天数分布
{self._format_distribution(self.current_metrics.持仓天数分布)}

🚪 退出原因分布
{self._format_distribution(self.current_metrics.退出原因分布)}

{'═' * 60}
        """
        return report
    
    def _format_distribution(self, distribution: Dict[str, int]) -> str:
        """
        格式化分布数据
        
        Args:
            distribution: 分布字典
        
        Returns:
            格式化后的字符串
        """
        if not distribution:
            return "  (无数据)"
        
        lines = []
        for key, value in sorted(distribution.items()):
            lines.append(f"  - {key}: {value}次")
        
        return '\n'.join(lines)
    
    def generate_realtime_dashboard(self) -> Dict:
        """
        生成实时仪表盘数据
        
        Returns:
            仪表盘数据字典
        """
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '账户表现': {
                '账户收益': f"{self.current_metrics.账户收益:.2%}",
                '最大回撤': f"{self.current_metrics.最大回撤:.2%}",
                '资金利用率': f"{self.current_metrics.资金利用率:.2%}"
            },
            '交易统计': {
                '起爆点捕捉': self.current_metrics.起爆点捕捉数,
                '调仓次数': self.current_metrics.调仓次数,
                '换仓收益': f"{self.current_metrics.换仓收益:.2%}"
            },
            '持仓天数分布': self.current_metrics.持仓天数分布,
            '退出原因分布': self.current_metrics.退出原因分布
        }
    
    def end_of_day(self):
        """当日结算，将当前指标存入历史"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 复制当前指标
        self.daily_metrics[today] = DailyMetrics(
            date=today,
            起爆点捕捉数=self.current_metrics.起爆点捕捉数,
            调仓次数=self.current_metrics.调仓次数,
            换仓收益=self.current_metrics.换仓收益,
            持仓天数分布=self.current_metrics.持仓天数分布.copy(),
            退出原因分布=self.current_metrics.退出原因分布.copy(),
            账户收益=self.current_metrics.账户收益,
            最大回撤=self.current_metrics.最大回撤,
            资金利用率=self.current_metrics.资金利用率
        )
        
        # 更新累计指标
        self.total_metrics['总收益'] += self.current_metrics.账户收益
        self.total_metrics['调仓次数'] += self.current_metrics.调仓次数
        self.total_metrics['起爆点捕捉数'] += self.current_metrics.起爆点捕捉数
        
        # 重置当前指标
        self.current_metrics = DailyMetrics(date=datetime.now().strftime('%Y-%m-%d'))
        
        logger.info(f"✅ 当日结算完成: {today}")