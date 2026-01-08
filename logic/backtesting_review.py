"""
复盘助手：智能复盘分析工具

参考文献：
- https://zhuanlan.zhihu.com/p/716389737
- https://xueqiu.com/8189550582/174332015
- http://www.10huang.cn/study/cwjyjz.html

核心功能：
- 自动生成回测报告
- 交易信号复盘
- 策略优缺点分析
- 改进建议
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from .backtest_engine import BacktestMetrics
from .logger import logger


@dataclass
class TradeRecord:
    """交易记录"""
    date: str
    stock_code: str
    stock_name: str
    action: str  # 'BUY' or 'SELL'
    price: float
    quantity: int
    amount: float
    pnl: float  # 盈亏
    pnl_ratio: float  # 盈亏比例
    strategy: str  # 使用的策略


@dataclass
class ReviewReport:
    """复盘报告"""
    report_date: str
    backtest_period: Tuple[str, str]
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    key_insights: List[str]
    improvement_suggestions: List[str]
    trade_analysis: Dict[str, Any]
    performance_chart: go.Figure
    risk_analysis: Dict[str, Any]


class BacktestingReview:
    """智能复盘助手"""

    def __init__(self):
        """初始化复盘助手"""

    def generate_review_report(
        self,
        trade_records: List[TradeRecord],
        metrics: BacktestMetrics,
        strategy_name: str = "Unknown Strategy",
        backtest_period: Tuple[str, str] = ("2020-01-01", "2024-12-31")
    ) -> ReviewReport:
        """
        生成复盘报告

        Args:
            trade_records: 交易记录列表
            metrics: 回测指标
            strategy_name: 策略名称
            backtest_period: 回测期间

        Returns:
            ReviewReport: 复盘报告
        """
        if not trade_records:
            raise ValueError("交易记录不能为空")

        # 分析交易数据
        trade_analysis = self._analyze_trades(trade_records)
        risk_analysis = self._analyze_risk(trade_records, metrics)

        # 生成关键见解
        key_insights = self._generate_key_insights(metrics, trade_analysis, risk_analysis)

        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(metrics, trade_analysis, risk_analysis)

        # 生成性能图表
        performance_chart = self._generate_performance_chart(trade_records, metrics)

        return ReviewReport(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            backtest_period=backtest_period,
            strategy_name=strategy_name,
            total_return=metrics.total_return,
            annual_return=metrics.annual_return,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown=metrics.max_drawdown,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            total_trades=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            key_insights=key_insights,
            improvement_suggestions=improvement_suggestions,
            trade_analysis=trade_analysis,
            performance_chart=performance_chart,
            risk_analysis=risk_analysis
        )

    def _analyze_trades(self, trade_records: List[TradeRecord]) -> Dict[str, Any]:
        """分析交易记录"""
        if not trade_records:
            return {}

        # 转换为DataFrame便于分析
        df = pd.DataFrame([{
            'date': record.date,
            'pnl_ratio': record.pnl_ratio,
            'pnl': record.pnl,
            'action': record.action
        } for record in trade_records])

        # 基础统计
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        avg_pnl_ratio = df['pnl_ratio'].mean()
        max_profit = df['pnl'].max()
        max_loss = df['pnl'].min()

        # 按盈亏分类
        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] < 0]

        # 盈利和亏损的平均值
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0

        # 按月度分析
        df['date'] = pd.to_datetime(df['date'])
        monthly_analysis = df.groupby(df['date'].dt.to_period('M')).agg({
            'pnl': ['count', 'sum', 'mean'],
            'pnl_ratio': 'mean'
        }).round(4)

        # 按胜率分析
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_count = len(df)
        win_rate = win_count / total_count if total_count > 0 else 0

        # 连续盈亏分析
        pnl_signs = df['pnl'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        consecutive_wins = self._calculate_consecutive(pnl_signs, 1)
        consecutive_losses = self._calculate_consecutive(pnl_signs, -1)

        return {
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_pnl_ratio': avg_pnl_ratio,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'monthly_analysis': monthly_analysis.to_dict() if not monthly_analysis.empty else {},
            'consecutive_analysis': {
                'max_consecutive_wins': consecutive_wins,
                'max_consecutive_losses': consecutive_losses
            }
        }

    def _calculate_consecutive(self, series: pd.Series, value: int) -> int:
        """计算连续出现某值的最大次数"""
        if series.empty:
            return 0

        max_count = 0
        current_count = 0

        for val in series:
            if val == value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count

    def _analyze_risk(self, trade_records: List[TradeRecord], metrics: BacktestMetrics) -> Dict[str, Any]:
        """分析风险指标"""
        if not trade_records:
            return {}

        df = pd.DataFrame([{
            'date': record.date,
            'pnl_ratio': record.pnl_ratio,
            'pnl': record.pnl
        } for record in trade_records])

        # 计算风险指标
        daily_returns = df['pnl_ratio']
        volatility = daily_returns.std() * np.sqrt(252)  # 年化波动率
        downside_deviation = daily_returns[daily_returns < 0].std() * np.sqrt(252)  # 下行标准差

        # 计算索提诺比率 (Sortino Ratio)
        if downside_deviation != 0:
            sortino_ratio = metrics.annual_return / downside_deviation
        else:
            sortino_ratio = float('inf') if metrics.annual_return > 0 else 0

        # 最大单笔亏损
        max_single_loss = df['pnl'].min()

        # 风险价值 (VaR) - 95%置信度
        var_95 = df['pnl_ratio'].quantile(0.05)

        # 期望不足 (Expected Shortfall) - 95%置信度
        es_95 = df['pnl_ratio'][df['pnl_ratio'] <= var_95].mean() if not df.empty else 0

        # 赢输比
        winning_pnl = df[df['pnl'] > 0]['pnl']
        losing_pnl = df[df['pnl'] < 0]['pnl']
        profit_risk_ratio = abs(winning_pnl.mean() / losing_pnl.mean()) if not losing_pnl.empty and losing_pnl.mean() != 0 else float('inf')

        return {
            'volatility': volatility,
            'downside_deviation': downside_deviation,
            'sortino_ratio': sortino_ratio,
            'max_single_loss': max_single_loss,
            'var_95': var_95,
            'expected_shortfall_95': es_95,
            'profit_risk_ratio': profit_risk_ratio,
            'risk_summary': self._generate_risk_summary(metrics, var_95, max_single_loss)
        }

    def _generate_risk_summary(self, metrics: BacktestMetrics, var_95: float, max_single_loss: float) -> str:
        """生成风险总结"""
        risk_level = "低" if metrics.max_drawdown > -0.05 else ("中" if metrics.max_drawdown > -0.15 else "高")
        var_level = "低" if var_95 > -0.03 else ("中" if var_95 > -0.08 else "高")
        loss_level = "低" if abs(max_single_loss) < 0.05 else ("中" if abs(max_single_loss) < 0.15 else "高")

        return f"风险等级：{risk_level}，VaR风险：{var_level}，单笔最大损失风险：{loss_level}"

    def _generate_key_insights(self, metrics: BacktestMetrics, trade_analysis: Dict, risk_analysis: Dict) -> List[str]:
        """生成关键见解"""
        insights = []

        # 收益分析
        if metrics.annual_return > 0.15:
            insights.append(f"年化收益率{metrics.annual_return:.2%}，表现优秀")
        elif metrics.annual_return > 0.08:
            insights.append(f"年化收益率{metrics.annual_return:.2%}，表现良好")
        elif metrics.annual_return > 0:
            insights.append(f"年化收益率{metrics.annual_return:.2%}，略高于零")
        else:
            insights.append(f"年化收益率{metrics.annual_return:.2%}，需要改进")

        # 风险调整收益
        if metrics.sharpe_ratio > 1:
            insights.append(f"夏普比率{metrics.sharpe_ratio:.2f}，风险调整收益优秀")
        elif metrics.sharpe_ratio > 0.5:
            insights.append(f"夏普比率{metrics.sharpe_ratio:.2f}，风险调整收益尚可")
        else:
            insights.append(f"夏普比率{metrics.sharpe_ratio:.2f}，风险调整收益需要改善")

        # 胜率分析
        if metrics.win_rate > 0.6:
            insights.append(f"胜率{metrics.win_rate:.2%}，交易成功率较高")
        elif metrics.win_rate > 0.5:
            insights.append(f"胜率{metrics.win_rate:.2%}，交易成功率一般")
        else:
            insights.append(f"胜率{metrics.win_rate:.2%}，交易成功率偏低，需关注盈亏比")

        # 盈亏比
        avg_win = trade_analysis.get('avg_win', 0)
        avg_loss = trade_analysis.get('avg_loss', -1)
        if avg_win > 0 and abs(avg_loss) > 0:
            profit_loss_ratio = avg_win / abs(avg_loss)
            if profit_loss_ratio > 2:
                insights.append(f"盈亏比{profit_loss_ratio:.2f}，盈利单平均是亏损单的{profit_loss_ratio:.1f}倍")
            elif profit_loss_ratio > 1.5:
                insights.append(f"盈亏比{profit_loss_ratio:.2f}，盈利单平均比亏损单高")
            else:
                insights.append(f"盈亏比{profit_loss_ratio:.2f}，需要优化盈亏比")

        # 最大回撤
        if abs(metrics.max_drawdown) < 0.1:
            insights.append(f"最大回撤{metrics.max_drawdown:.2%}，回撤控制良好")
        elif abs(metrics.max_drawdown) < 0.2:
            insights.append(f"最大回撤{metrics.max_drawdown:.2%}，回撤尚可接受")
        else:
            insights.append(f"最大回撤{metrics.max_drawdown:.2%}，回撤过大需要注意风险控制")

        # 连续盈亏
        consecutive_analysis = trade_analysis.get('consecutive_analysis', {})
        max_wins = consecutive_analysis.get('max_consecutive_wins', 0)
        max_losses = consecutive_analysis.get('max_consecutive_losses', 0)
        if max_losses > 5:
            insights.append(f"存在{max_losses}连亏，需要改进风险控制")
        if max_wins > 5:
            insights.append(f"存在{max_wins}连盈，策略在某些时段表现强劲")

        return insights

    def _generate_improvement_suggestions(self, metrics: BacktestMetrics, trade_analysis: Dict, risk_analysis: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于夏普比率的建议
        if metrics.sharpe_ratio < 0.3:
            suggestions.append("夏普比率较低，建议优化风险调整收益，可以考虑改进入场时机或风险控制机制")

        # 基于胜率的建议
        if metrics.win_rate < 0.4:
            suggestions.append("胜率偏低，建议优化交易信号或调整止损策略，更注重盈亏比的管理")

        # 基于最大回撤的建议
        if abs(metrics.max_drawdown) > 0.2:
            suggestions.append("最大回撤过大，建议加强仓位管理和止损机制，考虑加入市场环境过滤器")

        # 基于交易频率的建议
        total_trades = metrics.total_trades
        backtest_days = 252 * 4  # 假设4年回测
        trade_frequency = total_trades / backtest_days
        if trade_frequency > 0.5:  # 每天超过0.5次交易
            suggestions.append("交易频率过高，考虑降低交易频率以减少交易成本和过度拟合风险")
        elif trade_frequency < 0.05:  # 每天少于0.05次交易
            suggestions.append("交易频率过低，可以探索更多交易机会或优化信号生成机制")

        # 基于盈亏比的建议
        avg_win = trade_analysis.get('avg_win', 0)
        avg_loss = trade_analysis.get('avg_loss', -1)
        if avg_win > 0 and abs(avg_loss) > 0:
            profit_loss_ratio = avg_win / abs(avg_loss)
            if profit_loss_ratio < 1.5:
                suggestions.append("盈亏比较低，建议优化盈利目标或加强止损，确保盈利单收益覆盖亏损单损失")

        # 基于风险的建议
        var_95 = risk_analysis.get('var_95', 0)
        if var_95 < -0.1:  # 95%置信度下可能损失超过10%
            suggestions.append("风险价值较高，建议优化资金管理和风险控制模型")

        # 基于连续亏损的建议
        consecutive_analysis = trade_analysis.get('consecutive_analysis', {})
        max_losses = consecutive_analysis.get('max_consecutive_losses', 0)
        if max_losses > 5:
            suggestions.append(f"存在{max_losses}连亏情况，建议设置连亏熔断机制或调整策略参数")

        # 行业/板块轮动建议
        suggestions.append("建议加入行业轮动或板块轮动信号，提升策略在不同市场环境下的适应性")

        # 多策略融合建议
        suggestions.append("考虑将本策略与其他策略融合，构建策略组合以降低回撤和提升收益稳定性")

        # 动态参数优化建议
        suggestions.append("建议实现参数动态优化机制，根据市场状态调整策略参数")

        return suggestions

    def _generate_performance_chart(self, trade_records: List[TradeRecord], metrics: BacktestMetrics) -> go.Figure:
        """生成性能图表"""
        if not trade_records:
            # 返回空白图表
            fig = go.Figure()
            fig.update_layout(title="暂无交易数据")
            return fig

        # 按日期排序交易记录
        sorted_records = sorted(trade_records, key=lambda x: x.date)

        # 生成累计收益曲线
        dates = [record.date for record in sorted_records]
        pnl_values = [record.pnl for record in sorted_records]
        cumulative_pnl = np.cumsum(pnl_values)

        # 计算权益曲线
        initial_capital = 100000  # 假设初始资金
        equity_curve = [initial_capital + pnl for pnl in cumulative_pnl]

        # 计算移动平均线
        df = pd.DataFrame({
            'date': pd.to_datetime(dates),
            'equity': equity_curve
        })

        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('权益曲线', '日收益率分布'),
            vertical_spacing=0.1
        )

        # 权益曲线
        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['equity'],
                mode='lines',
                name='权益曲线',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )

        # 添加买卖点标记
        buy_records = [r for r in trade_records if r.action == 'BUY']
        sell_records = [r for r in trade_records if r.action == 'SELL']

        if buy_records:
            buy_dates = [r.date for r in buy_records]
            buy_equity = [initial_capital + sum(tr.pnl for tr in sorted_records[:sorted_records.index(r)+1]) for r in buy_records]
            fig.add_trace(
                go.Scatter(
                    x=pd.to_datetime(buy_dates), y=buy_equity,
                    mode='markers',
                    name='买入点',
                    marker=dict(symbol='triangle-up', size=10, color='green')
                ),
                row=1, col=1
            )

        if sell_records:
            sell_dates = [r.date for r in sell_records]
            sell_equity = [initial_capital + sum(tr.pnl for tr in sorted_records[:sorted_records.index(r)+1]) for r in sell_records]
            fig.add_trace(
                go.Scatter(
                    x=pd.to_datetime(sell_dates), y=sell_equity,
                    mode='markers',
                    name='卖出点',
                    marker=dict(symbol='triangle-down', size=10, color='red')
                ),
                row=1, col=1
            )

        # 日收益率分布直方图
        daily_returns = [record.pnl_ratio for record in sorted_records]
        fig.add_trace(
            go.Histogram(x=daily_returns, nbinsx=50, name='日收益率分布', marker_color='lightblue'),
            row=2, col=1
        )

        # 更新布局
        fig.update_layout(
            title=f"策略性能分析 - {metrics.total_return:.2%} 总收益, {metrics.max_drawdown:.2%} 最大回撤",
            height=800,
            showlegend=True
        )

        fig.update_xaxes(title_text="日期", row=1, col=1)
        fig.update_yaxes(title_text="权益", row=1, col=1)
        fig.update_xaxes(title_text="日收益率", row=2, col=1)
        fig.update_yaxes(title_text="频次", row=2, col=1)

        return fig

    def analyze_strategy_performance(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析策略性能

        Args:
            strategy_data: 策略数据，包含交易记录、指标等

        Returns:
            Dict[str, Any]: 性能分析结果
        """
        # 提取数据
        trade_records = strategy_data.get('trade_records', [])
        metrics = strategy_data.get('metrics')
        strategy_name = strategy_data.get('strategy_name', 'Unknown')

        if not trade_records or not metrics:
            return {}

        # 生成复盘报告
        report = self.generate_review_report(trade_records, metrics, strategy_name)

        return {
            'summary': {
                'total_return': report.total_return,
                'sharpe_ratio': report.sharpe_ratio,
                'max_drawdown': report.max_drawdown,
                'win_rate': report.win_rate
            },
            'insights': report.key_insights,
            'suggestions': report.improvement_suggestions,
            'trade_analysis': report.trade_analysis,
            'risk_analysis': report.risk_analysis,
            'chart': report.performance_chart
        }

    def compare_strategies(self, strategy_reports: List[ReviewReport]) -> go.Figure:
        """
        比较多个策略的性能

        Args:
            strategy_reports: 策略报告列表

        Returns:
            go.Figure: 比较图表
        """
        if not strategy_reports:
            fig = go.Figure()
            fig.update_layout(title="无策略报告可供比较")
            return fig

        # 提取关键指标用于比较
        strategy_names = [report.strategy_name for report in strategy_reports]
        total_returns = [report.total_return for report in strategy_reports]
        sharpe_ratios = [report.sharpe_ratio for report in strategy_reports]
        max_drawdowns = [abs(report.max_drawdown) for report in strategy_reports]
        win_rates = [report.win_rate for report in strategy_reports]

        # 创建比较图表
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('总收益', '夏普比率', '最大回撤', '胜率'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )

        # 总收益
        fig.add_trace(go.Bar(x=strategy_names, y=total_returns, name='总收益', marker_color='green'), row=1, col=1)

        # 夏普比率
        fig.add_trace(go.Bar(x=strategy_names, y=sharpe_ratios, name='夏普比率', marker_color='blue'), row=1, col=2)

        # 最大回撤
        fig.add_trace(go.Bar(x=strategy_names, y=max_drawdowns, name='最大回撤', marker_color='red'), row=2, col=1)

        # 胜率
        fig.add_trace(go.Bar(x=strategy_names, y=win_rates, name='胜率', marker_color='orange'), row=2, col=2)

        fig.update_layout(height=800, title_text="策略性能比较", showlegend=False)

        return fig