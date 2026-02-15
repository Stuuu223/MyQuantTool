"""
样本外检验模块 - 检测过拟合
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class OutOfSampleValidator:
    """
    样本外检验器
    
    用于检测策略是否过拟合
    """
    
    def __init__(self, train_ratio: float = 0.8):
        """
        初始化样本外检验器
        
        Args:
            train_ratio: 训练集比例 (默认 0.8)
        """
        self.train_ratio = train_ratio
    
    def split_data(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        分割数据为训练集和测试集
        
        Args:
            df: 原始数据
        
        Returns:
            (训练集, 测试集)
        """
        train_size = int(len(df) * self.train_ratio)
        
        df_train = df[:train_size].copy()
        df_test = df[train_size:].copy()
        
        logger.info(f"数据分割: 训练集 {len(df_train)} 天, 测试集 {len(df_test)} 天")
        
        return df_train, df_test
    
    def validate_overfitting(
        self,
        train_metrics: Dict,
        test_metrics: Dict
    ) -> Tuple[bool, str]:
        """
        检测过拟合
        
        Args:
            train_metrics: 训练集指标
            test_metrics: 测试集指标
        
        Returns:
            (是否过拟合, 检测结果消息)
        """
        issues = []
        
        # 1. 夏普比率检查
        train_sharpe = train_metrics.get('sharpe_ratio', 0)
        test_sharpe = test_metrics.get('sharpe_ratio', 0)
        
        if test_sharpe < train_sharpe * 0.7:
            issues.append(f"夏普比率下降 {((train_sharpe - test_sharpe) / train_sharpe * 100):.1f}%")
        elif test_sharpe < train_sharpe * 0.85:
            issues.append(f"夏普比率轻微下降 {((train_sharpe - test_sharpe) / train_sharpe * 100):.1f}%")
        
        # 2. 收益率检查
        train_return = train_metrics.get('annual_return', 0)
        test_return = test_metrics.get('annual_return', 0)
        
        if test_return < train_return * 0.7:
            issues.append(f"年化收益下降 {((train_return - test_return) / train_return * 100):.1f}%")
        elif test_return < train_return * 0.85:
            issues.append(f"年化收益轻微下降 {((train_return - test_return) / train_return * 100):.1f}%")
        
        # 3. 最大回撤检查
        train_dd = train_metrics.get('max_drawdown', 0)
        test_dd = test_metrics.get('max_drawdown', 0)
        
        if abs(test_dd) > abs(train_dd) * 1.3:
            issues.append(f"最大回撤扩大 {((abs(test_dd) - abs(train_dd)) / abs(train_dd) * 100):.1f}%")
        
        # 4. 胜率检查
        train_winrate = train_metrics.get('win_rate', 0)
        test_winrate = test_metrics.get('win_rate', 0)
        
        if test_winrate < train_winrate * 0.8:
            issues.append(f"胜率下降 {((train_winrate - test_winrate) / train_winrate * 100):.1f}%")
        
        # 判断是否过拟合
        is_overfitted = len(issues) >= 2 or any("下降" in issue and float(issue.split()[1]) > 30 for issue in issues)
        
        if is_overfitted:
            return True, "⚠️ 检测到强烈过拟合: " + "; ".join(issues)
        elif len(issues) > 0:
            return False, "⚠️ 轻微性能下降: " + "; ".join(issues)
        else:
            return False, "✅ 样本外表现良好，无明显过拟合"
    
    def cross_validation(
        self,
        df: pd.DataFrame,
        backtest_func,
        n_folds: int = 5
    ) -> Dict:
        """
        交叉验证
        
        Args:
            df: 原始数据
            backtest_func: 回测函数
            n_folds: 折叠数
        
        Returns:
            交叉验证结果
        """
        fold_size = len(df) // n_folds
        results = []
        
        for i in range(n_folds):
            # 测试集
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < n_folds - 1 else len(df)
            df_test = df.iloc[test_start:test_end].copy()
            
            # 训练集 (其他所有数据)
            df_train = pd.concat([df.iloc[:test_start], df.iloc[test_end:]]).copy()
            
            # 运行回测
            try:
                result = backtest_func(df_train, df_test)
                results.append(result)
            except Exception as e:
                logger.error(f"第 {i+1} 折交叉验证失败: {e}")
                results.append(None)
        
        # 计算平均指标
        valid_results = [r for r in results if r is not None]
        
        if not valid_results:
            return {}
        
        avg_metrics = {}
        for key in valid_results[0].keys():
            values = [r[key] for r in valid_results if key in r]
            if values and all(isinstance(v, (int, float)) for v in values):
                avg_metrics[key] = np.mean(values)
        
        logger.info(f"交叉验证完成: {len(valid_results)}/{n_folds} 折成功")
        
        return avg_metrics
    
    def get_validation_report(
        self,
        train_metrics: Dict,
        test_metrics: Dict
    ) -> str:
        """
        获取验证报告
        
        Args:
            train_metrics: 训练集指标
            test_metrics: 测试集指标
        
        Returns:
            格式化的验证报告
        """
        is_overfitted, message = self.validate_overfitting(train_metrics, test_metrics)
        
        report = f"""
🔬 样本外检验报告
================

📊 训练集指标:
  - 夏普比率: {train_metrics.get('sharpe_ratio', 0):.2f}
  - 年化收益: {train_metrics.get('annual_return', 0):.2%}
  - 最大回撤: {train_metrics.get('max_drawdown', 0):.2%}
  - 胜率: {train_metrics.get('win_rate', 0):.2%}

📊 测试集指标:
  - 夏普比率: {test_metrics.get('shrpe_ratio', 0):.2f}
  - 年化收益: {test_metrics.get('annual_return', 0):.2%}
  - 最大回撤: {test_metrics.get('max_drawdown', 0):.2%}
  - 胜率: {test_metrics.get('win_rate', 0):.2%}

🎯 检验结果:
{message}
"""
        return report