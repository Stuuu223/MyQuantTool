"""
组合优化器：现代投资组合理论实现

功能：
- 马科维茨均值方差优化
- Black-Litterman模型
- 风险平价策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("警告: 未安装scipy，组合优化功能将受限")

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    print("警告: 未安装cvxpy，部分优化功能将受限")


@dataclass
class PortfolioResult:
    """投资组合结果数据类"""
    weights: Dict[str, float]  # 权重分配
    expected_return: float     # 预期收益
    volatility: float          # 波动率
    sharpe_ratio: float        # 夏普比率
    risk_contribution: Dict[str, float]  # 风险贡献
    optimization_method: str   # 优化方法
    backtest_performance: Dict[str, float]  # 回测表现


class PortfolioOptimizer:
    """投资组合优化器"""

    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化投资组合优化器

        Args:
            risk_free_rate: 无风险利率
        """
        self.risk_free_rate = risk_free_rate

    def markowitz_optimization(self, returns_df: pd.DataFrame, target_return: Optional[float] = None) -> PortfolioResult:
        """
        马科维茨均值方差优化

        Args:
            returns_df: 收益率数据 DataFrame，每列代表一个资产
            target_return: 目标收益率

        Returns:
            PortfolioResult: 优化结果
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("需要安装scipy以使用马科维茨优化")

        # 计算均值和协方差矩阵
        mean_returns = returns_df.mean().values
        cov_matrix = returns_df.cov().values
        n_assets = len(mean_returns)

        if target_return is None:
            target_return = mean_returns.mean()

        # 定义优化目标：最小化方差
        def objective(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))

        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # 权重和为1
            {'type': 'eq', 'fun': lambda x: np.dot(x, mean_returns) - target_return}  # 目标收益率
        ]

        # 权重边界 [0, 1]，不允许卖空
        bounds = tuple((0, 1) for _ in range(n_assets))

        # 初始权重
        init_weights = np.array([1.0 / n_assets] * n_assets)

        # 执行优化
        result = minimize(
            objective, init_weights, method='SLSQP',
            bounds=bounds, constraints=constraints
        )

        if not result.success:
            # 如果优化失败，返回等权重
            weights = np.array([1.0 / n_assets] * n_assets)
        else:
            weights = result.x

        # 计算投资组合指标
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        # 计算风险贡献
        risk_contribution = {}
        for i, col in enumerate(returns_df.columns):
            marginal_risk = np.dot(weights, cov_matrix[:, i]) / portfolio_vol if portfolio_vol > 0 else 0
            risk_contribution[col] = weights[i] * marginal_risk

        return PortfolioResult(
            weights={col: weights[i] for i, col in enumerate(returns_df.columns)},
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=sharpe_ratio,
            risk_contribution=risk_contribution,
            optimization_method='Markowitz Mean-Variance',
            backtest_performance={}
        )

    def risk_parity_optimization(self, returns_df: pd.DataFrame) -> PortfolioResult:
        """
        风险平价优化

        Args:
            returns_df: 收益率数据 DataFrame

        Returns:
            PortfolioResult: 优化结果
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("需要安装scipy以使用风险平价优化")

        # 计算协方差矩阵
        cov_matrix = returns_df.cov().values
        n_assets = len(returns_df.columns)

        # 目标函数：使各资产的风险贡献相等
        def risk_parity_objective(weights, cov_matrix):
            # 计算总风险
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            if portfolio_vol == 0:
                return 0

            # 计算各资产的边际风险贡献
            marginal_risk = np.dot(cov_matrix, weights) / portfolio_vol
            risk_contribution = weights * marginal_risk

            # 目标是最小化风险贡献的差异
            target_risk = np.sum(risk_contribution) / n_assets
            return np.sum((risk_contribution - target_risk) ** 2)

        # 约束条件
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # 权重和为1
        bounds = tuple((1e-6, 1) for _ in range(n_assets))  # 权重边界

        # 初始权重（使用等权重作为初始值）
        init_weights = np.array([1.0 / n_assets] * n_assets)

        # 执行优化
        result = minimize(
            risk_parity_objective, init_weights,
            args=(cov_matrix,), method='SLSQP',
            bounds=bounds, constraints=constraints
        )

        if not result.success:
            weights = np.array([1.0 / n_assets] * n_assets)
        else:
            weights = result.x

        # 标准化权重使其总和为1
        weights = weights / np.sum(weights)

        # 计算其他指标
        mean_returns = returns_df.mean().values
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        # 计算风险贡献
        risk_contribution = {}
        marginal_risk = np.dot(cov_matrix, weights) / portfolio_vol if portfolio_vol > 0 else np.zeros(n_assets)
        for i, col in enumerate(returns_df.columns):
            risk_contribution[col] = weights[i] * marginal_risk[i]

        return PortfolioResult(
            weights={col: weights[i] for i, col in enumerate(returns_df.columns)},
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=sharpe_ratio,
            risk_contribution=risk_contribution,
            optimization_method='Risk Parity',
            backtest_performance={}
        )

    def black_litterman_optimization(self, returns_df: pd.DataFrame, views: Optional[Dict[str, float]] = None) -> PortfolioResult:
        """
        Black-Litterman模型优化

        Args:
            returns_df: 收益率数据 DataFrame
            views: 投资观点 {资产代码: 预期超额收益率}

        Returns:
            PortfolioResult: 优化结果
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("需要安装scipy以使用Black-Litterman优化")

        # 计算市场均衡收益
        market_caps = np.array([1.0 / len(returns_df.columns)] * len(returns_df.columns))  # 假设等权市场
        sigma = returns_df.cov().values
        market_vol = np.sqrt(np.sum(market_caps * np.dot(sigma, market_caps)))
        market_return = self.risk_free_rate + 0.05  # 假设市场超额收益为5%

        # 调整比例参数
        delta = (market_return - self.risk_free_rate) / (market_vol ** 2)  # 风险厌恶系数

        # 先验分布（市场均衡收益）
        pi = np.dot(sigma, market_caps) * delta

        n_assets = len(returns_df.columns)

        # 如果没有提供观点，使用市场均衡收益
        if views is None or not views:
            weights = market_caps  # 返回市场均衡权重
        else:
            # 构建观点矩阵
            tau = 0.025  # 调整参数
            P = np.eye(n_assets)  # 选择矩阵（每个观点对应一个资产）
            Q = np.zeros(n_assets)  # 观点向量

            # 更新观点向量
            for i, asset in enumerate(returns_df.columns):
                if asset in views:
                    Q[i] = views[asset]

            # 观点不确定性矩阵
            Omega = tau * np.dot(P, np.dot(sigma, P.T)) * np.eye(n_assets)  # 简化对角矩阵

            # Black-Litterman后验收益
            A = tau * np.dot(sigma, P.T)
            B = np.dot(P, np.dot(A, P.T)) + Omega
            expected_returns = pi + np.dot(A, np.dot(np.linalg.inv(B), (Q - np.dot(P, pi))))

            # 使用后验收益进行均值方差优化
            weights = self._inverse_variance_weights(sigma, expected_returns)

        # 计算投资组合指标
        mean_returns = returns_df.mean().values
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(sigma, weights)))
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        # 计算风险贡献
        risk_contribution = {}
        marginal_risk = np.dot(sigma, weights) / portfolio_vol if portfolio_vol > 0 else np.zeros(n_assets)
        for i, col in enumerate(returns_df.columns):
            risk_contribution[col] = weights[i] * marginal_risk[i]

        return PortfolioResult(
            weights={col: weights[i] for i, col in enumerate(returns_df.columns)},
            expected_return=portfolio_return,
            volatility=portfolio_vol,
            sharpe_ratio=sharpe_ratio,
            risk_contribution=risk_contribution,
            optimization_method='Black-Litterman',
            backtest_performance={}
        )

    def _inverse_variance_weights(self, cov_matrix: np.ndarray, expected_returns: np.ndarray) -> np.ndarray:
        """
        计算逆方差权重（简化版均值方差优化）
        """
        n = len(cov_matrix)
        weights = np.diag(cov_matrix) ** -1  # 使用对角线方差的倒数
        return weights / np.sum(weights)

    def optimize_portfolio(self, returns_df: pd.DataFrame, method: str = 'markowitz', **kwargs) -> PortfolioResult:
        """
        通用优化接口

        Args:
            returns_df: 收益率数据
            method: 优化方法 ('markowitz', 'risk_parity', 'black_litterman')
            **kwargs: 传递给具体优化方法的参数

        Returns:
            PortfolioResult: 优化结果
        """
        if method == 'markowitz':
            target_return = kwargs.get('target_return', None)
            return self.markowitz_optimization(returns_df, target_return)
        elif method == 'risk_parity':
            return self.risk_parity_optimization(returns_df)
        elif method == 'black_litterman':
            views = kwargs.get('views', None)
            return self.black_litterman_optimization(returns_df, views)
        else:
            raise ValueError(f"不支持的优化方法: {method}")

    def calculate_efficient_frontier(self, returns_df: pd.DataFrame, n_points: int = 50) -> List[PortfolioResult]:
        """
        计算有效前沿

        Args:
            returns_df: 收益率数据
            n_points: 有效前沿上的点数

        Returns:
            List[PortfolioResult]: 有效前沿上的组合列表
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("需要安装scipy以计算有效前沿")

        mean_returns = returns_df.mean()
        min_return = mean_returns.min()
        max_return = mean_returns.max()

        # 在最小和最大收益率之间等间距分布目标收益率
        target_returns = np.linspace(min_return, max_return, n_points)

        efficient_portfolios = []
        for target_ret in target_returns:
            try:
                portfolio = self.markowitz_optimization(returns_df, target_ret)
                efficient_portfolios.append(portfolio)
            except Exception as e:
                # 如果某个目标收益率优化失败，跳过
                continue

        return efficient_portfolios