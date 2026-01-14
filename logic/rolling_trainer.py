"""
滚动训练引擎 (Walk-Forward Optimization)
模拟真实的时间流逝，防止未来数据泄漏，评估模型在样本外的真实表现
这是解决"过拟合"和"未来函数"的神器
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Type, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RollingTrainer:
    """
    滚动训练引擎 (Walk-Forward Optimization)
    
    核心思想：
    - 模拟真实的每一天：站在今天，用过去的数据训练，预测明天
    - 防止未来数据泄漏（Backtest Overfitting）
    - 评估模型在样本外的真实表现
    
    工作流程：
    1. 用过去 N 天数据训练模型
    2. 用训练好的模型预测未来 M 天
    3. 滚动窗口，重复步骤 1-2
    4. 统计所有预测结果，计算真实性能指标
    """
    
    def __init__(self, 
                 predictor_class: Type,
                 predictor_params: Optional[Dict] = None,
                 train_window: int = 252,  # 1年交易日
                 test_window: int = 20,    # 1个月
                 min_train_size: int = 100):
        """
        初始化滚动训练器
        
        Args:
            predictor_class: 预测器类（如 LightGBMPredictor, CatBoostPredictor）
            predictor_params: 预测器初始化参数
            train_window: 训练窗口大小（天）
            test_window: 测试窗口大小（天）
            min_train_size: 最小训练样本数
        """
        self.predictor_class = predictor_class
        self.predictor_params = predictor_params or {}
        self.train_window = train_window
        self.test_window = test_window
        self.min_train_size = min_train_size
        
        # 存储训练历史
        self.training_history = []
        self.predictions = []
        self.actuals = []
        self.dates = []
        
    def run(self, 
            df: pd.DataFrame,
            target_col: str = 'target_next_return',
            verbose: bool = True) -> Dict[str, Any]:
        """
        执行滚动训练
        
        Args:
            df: 包含特征和标签的完整数据（必须按时间排序）
            target_col: 目标列名
            verbose: 是否打印详细日志
            
        Returns:
            包含评估指标的字典
        """
        if len(df) < self.min_train_size + self.test_window:
            logger.warning(f"数据量太少（{len(df)}），无法进行滚动训练")
            return {}
        
        # 确保按时间排序
        df = df.reset_index(drop=True)
        n_samples = len(df)
        
        # 清空历史记录
        self.training_history = []
        self.predictions = []
        self.actuals = []
        self.dates = []
        
        # 滚动游标
        current_idx = self.train_window
        
        if verbose:
            logger.info(f"开始滚动训练:")
            logger.info(f"  总样本: {n_samples}")
            logger.info(f"  训练窗口: {self.train_window} 天")
            logger.info(f"  测试窗口: {self.test_window} 天")
            logger.info(f"  预计 Fold 数: {(n_samples - self.train_window) // self.test_window}")
        
        fold = 0
        while current_idx < n_samples - self.test_window:
            # 1. 切分数据
            start_train = max(0, current_idx - self.train_window)
            end_train = current_idx
            end_test = min(n_samples, current_idx + self.test_window)
            
            train_data = df.iloc[start_train:end_train].copy()
            test_data = df.iloc[end_train:end_test].copy()
            
            if len(test_data) == 0:
                break
            
            # 2. 初始化新模型
            try:
                model = self.predictor_class(**self.predictor_params)
                
                # 3. 训练
                if verbose:
                    logger.info(f"Fold {fold}: 训练 [{start_train}:{end_train}] -> 预测 [{end_train}:{end_test}]")
                
                model.train(train_data)
                
                # 4. 预测
                preds = model.predict(test_data)
                
                # 收集结果
                self.predictions.extend(preds)
                self.actuals.extend(test_data[target_col].values)
                
                if 'date' in test_data.columns:
                    self.dates.extend(test_data['date'].values)
                else:
                    self.dates.extend(test_data.index.values)
                
                # 记录训练历史
                self.training_history.append({
                    'fold': fold,
                    'train_start': start_train,
                    'train_end': end_train,
                    'test_start': end_train,
                    'test_end': end_test,
                    'train_samples': len(train_data),
                    'test_samples': len(test_data)
                })
                
            except Exception as e:
                logger.error(f"Fold {fold} 训练失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 5. 移动窗口
            current_idx += self.test_window
            fold += 1
        
        if verbose:
            logger.info(f"滚动训练完成，共 {fold} 个 Fold")
        
        # 6. 计算统计指标
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """
        计算评估指标
        
        Returns:
            包含各种评估指标的字典
        """
        if len(self.actuals) == 0 or len(self.predictions) == 0:
            return {}
        
        y_true = np.array(self.actuals)
        y_pred = np.array(self.predictions)
        
        # 将连续预测转为分类信号（假设 > 0 是涨）
        y_pred_class = (y_pred > 0).astype(int)
        y_true_class = (y_true > 0).astype(int)
        
        # 计算指标
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        metrics = {
            # 分类指标
            'accuracy': accuracy_score(y_true_class, y_pred_class),
            'precision': precision_score(y_true_class, y_pred_class, zero_division=0),
            'recall': recall_score(y_true_class, y_pred_class, zero_division=0),
            'f1_score': f1_score(y_true_class, y_pred_class, zero_division=0),
            # 回归指标
            'ic': np.corrcoef(y_true, y_pred)[0, 1] if len(y_true) > 1 else 0,  # Information Coefficient
            'mae': np.mean(np.abs(y_true - y_pred)),
            'rmse': np.sqrt(np.mean((y_true - y_pred) ** 2)),
            # 样本统计
            'total_samples': len(y_true),
            'total_folds': len(self.training_history),
            # 方向准确率
            'direction_accuracy': np.mean((y_true * y_pred) > 0)
        }
        
        # 计算 IC Rank（排序能力）
        if len(y_true) > 10:
            ic_rank = np.corrcoef(y_true, y_pred)[0, 1]
            metrics['ic_rank'] = ic_rank
        
        # 计算累计收益（假设按预测方向交易）
        if len(y_true) > 0:
            # 预测涨就买入，预测跌就卖出
            returns = np.where(y_pred > 0, y_true, -y_true)
            metrics['cumulative_return'] = np.sum(returns)
            metrics['sharpe_ratio'] = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        return metrics
    
    def get_predictions_df(self) -> pd.DataFrame:
        """
        获取预测结果的 DataFrame
        
        Returns:
            包含日期、实际值、预测值的 DataFrame
        """
        if len(self.dates) == 0:
            return pd.DataFrame()
        
        return pd.DataFrame({
            'date': self.dates,
            'actual': self.actuals,
            'predicted': self.predictions
        })
    
    def get_training_history(self) -> pd.DataFrame:
        """
        获取训练历史
        
        Returns:
            训练历史 DataFrame
        """
        if len(self.training_history) == 0:
            return pd.DataFrame()
        
        return pd.DataFrame(self.training_history)


class CrossSectionalRollingTrainer(RollingTrainer):
    """
    截面滚动训练器
    
    用于多股票场景：
    - 每个时间点，用所有股票的历史数据训练
    - 预测所有股票的未来收益
    - 评估模型的截面选股能力
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock_predictions = {}
    
    def run_cross_sectional(self,
                           df: pd.DataFrame,
                           stock_col: str = 'symbol',
                           target_col: str = 'target_next_return',
                           verbose: bool = True) -> Dict[str, Any]:
        """
        执行截面滚动训练
        
        Args:
            df: 包含多股票的数据
            stock_col: 股票代码列名
            target_col: 目标列名
            verbose: 是否打印详细日志
            
        Returns:
            包含评估指标的字典
        """
        if stock_col not in df.columns:
            logger.error(f"数据中缺少股票列: {stock_col}")
            return {}
        
        # 获取所有股票
        stocks = df[stock_col].unique()
        
        if verbose:
            logger.info(f"开始截面滚动训练:")
            logger.info(f"  股票数量: {len(stocks)}")
            logger.info(f"  总样本: {len(df)}")
        
        # 对每只股票进行滚动训练
        all_predictions = []
        all_actuals = []
        all_dates = []
        all_stocks = []
        
        for stock in stocks:
            stock_data = df[df[stock_col] == stock].copy()
            stock_data = stock_data.sort_values('date').reset_index(drop=True)
            
            if len(stock_data) < self.min_train_size + self.test_window:
                if verbose:
                    logger.warning(f"股票 {stock} 数据不足，跳过")
                continue
            
            # 对单只股票进行滚动训练
            results = self.run(stock_data, target_col=target_col, verbose=False)
            
            if len(self.predictions) > 0:
                all_predictions.extend(self.predictions)
                all_actuals.extend(self.actuals)
                all_dates.extend(self.dates)
                all_stocks.extend([stock] * len(self.predictions))
            
            # 清空当前预测，为下一只股票做准备
            self.predictions = []
            self.actuals = []
            self.dates = []
        
        # 合并所有预测
        self.predictions = all_predictions
        self.actuals = all_actuals
        self.dates = all_dates
        self.stock_predictions['stock'] = all_stocks
        
        if verbose:
            logger.info(f"截面滚动训练完成，总预测数: {len(all_predictions)}")
        
        # 计算指标
        return self._calculate_metrics()
    
    def get_cross_sectional_predictions_df(self) -> pd.DataFrame:
        """
        获取截面预测结果的 DataFrame
        
        Returns:
            包含日期、股票、实际值、预测值的 DataFrame
        """
        if len(self.dates) == 0:
            return pd.DataFrame()
        
        return pd.DataFrame({
            'date': self.dates,
            'stock': self.stock_predictions.get('stock', []),
            'actual': self.actuals,
            'predicted': self.predictions
        })