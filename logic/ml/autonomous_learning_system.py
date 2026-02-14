"""
自主学习系统（Lite 版）
基于增量学习的轻量级系统
删除复杂的因果推断和 AutoML，改为增量微调
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
import pickle
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class IncrementalLearningEngine:
    """
    增量学习引擎（改进版）
    支持模型的持续微调，防止灾难性遗忘
    """

    def __init__(self,
                 model: Any,
                 update_interval: int = 1,
                 window_size: int = 1000,
                 min_samples: int = 100,
                 memory_size: int = 2000,
                 enable_validation: bool = True,
                 validation_ratio: float = 0.2):
        """
        初始化增量学习引擎

        Args:
            model: 基础模型（LightGBM/XGBoost/CatBoost）
            update_interval: 更新间隔（天数）
            window_size: 滑动窗口大小
            min_samples: 最小样本数
            memory_size: 历史记忆库大小（防止灾难性遗忘）
            enable_validation: 是否启用验证集回滚
            validation_ratio: 验证集比例
        """
        self.model = model
        self.update_interval = update_interval
        self.window_size = window_size
        self.min_samples = min_samples
        self.memory_size = memory_size
        self.enable_validation = enable_validation
        self.validation_ratio = validation_ratio

        # 数据缓冲区（新数据）
        self.data_buffer = []
        self.last_update_date = None

        # 历史记忆库（防止灾难性遗忘）
        self.memory_bank = []
        self.memory_bank_size = memory_size

        # 性能追踪
        self.update_history = []
        self.performance_metrics = []

        # 模型备份（用于回滚）
        self.model_backup = None
        self.best_validation_score = None

    def add_data(self, X: np.ndarray, y: np.ndarray):
        """
        添加新数据

        Args:
            X: 特征数据
            y: 标签数据
        """
        # 将数据添加到缓冲区
        for i in range(len(X)):
            self.data_buffer.append({
                'features': X[i],
                'target': y[i],
                'timestamp': datetime.now()
            })

        # 限制缓冲区大小（滑动窗口）
        if len(self.data_buffer) > self.window_size:
            # 将溢出的数据移到记忆库
            overflow = self.data_buffer[:-self.window_size]
            self.memory_bank.extend(overflow)
            self.data_buffer = self.data_buffer[-self.window_size:]

        # 限制记忆库大小
        if len(self.memory_bank) > self.memory_bank_size:
            self.memory_bank = self.memory_bank[-self.memory_bank_size:]

    def should_update(self) -> bool:
        """
        判断是否需要更新模型

        Returns:
            是否需要更新
        """
        # 检查样本数量
        if len(self.data_buffer) < self.min_samples:
            return False

        # 检查更新间隔
        if self.last_update_date is None:
            return True

        days_since_last = (datetime.now() - self.last_update_date).days
        return days_since_last >= self.update_interval

    def update_model(self) -> Dict[str, Any]:
        """
        增量更新模型（带验证集回滚）

        Returns:
            更新结果
        """
        if not self.should_update():
            logger.info("无需更新模型")
            return {'updated': False, 'reason': 'Not enough data or too soon'}

        try:
            # 备份当前模型
            import copy
            self.model_backup = copy.deepcopy(self.model)

            # 准备训练数据（新数据 + 记忆库）
            X_buffer = np.array([item['features'] for item in self.data_buffer])
            y_buffer = np.array([item['target'] for item in self.data_buffer])

            if len(self.memory_bank) > 0:
                X_memory = np.array([item['features'] for item in self.memory_bank])
                y_memory = np.array([item['target'] for item in self.memory_bank])
                # 混合新数据和记忆库数据
                X_train = np.vstack([X_buffer, X_memory])
                y_train = np.hstack([y_buffer, y_memory])
            else:
                X_train = X_buffer
                y_train = y_buffer

            logger.info(f"开始增量更新，新数据: {len(X_buffer)}, 记忆库: {len(self.memory_bank)}, 总计: {len(X_train)}")

            # 如果启用验证集，划分训练集和验证集
            if self.enable_validation and len(X_train) >= self.min_samples * 2:
                split_idx = int(len(X_train) * (1 - self.validation_ratio))
                X_train_split, X_val = X_train[:split_idx], X_train[split_idx:]
                y_train_split, y_val = y_train[:split_idx], y_train[split_idx:]

                # 训练模型
                if hasattr(self.model, 'fit'):
                    if hasattr(self.model, 'refit'):
                        self.model.refit(X_train_split, y_train_split)
                    elif hasattr(self.model, 'update'):
                        self.model.update(X_train_split, y_train_split)
                    else:
                        self.model.fit(X_train_split, y_train_split)

                # 验证模型
                y_pred = self.model.predict(X_val)
                validation_score = np.mean((y_val - y_pred) ** 2)  # MSE

                # 如果验证集性能下降，回滚模型
                if self.best_validation_score is not None and validation_score > self.best_validation_score * 1.1:
                    logger.warning(f"验证集性能下降 ({validation_score:.4f} vs {self.best_validation_score:.4f})，回滚模型")
                    self.model = copy.deepcopy(self.model_backup)
                    return {
                        'updated': False,
                        'reason': 'Validation score degraded, model rolled back',
                        'validation_score': validation_score,
                        'best_score': self.best_validation_score
                    }

                # 更新最佳分数
                self.best_validation_score = validation_score
                logger.info(f"验证集 MSE: {validation_score:.4f}")

            else:
                # 不使用验证集，直接训练
                if hasattr(self.model, 'fit'):
                    if hasattr(self.model, 'refit'):
                        self.model.refit(X_train, y_train)
                    elif hasattr(self.model, 'update'):
                        self.model.update(X_train, y_train)
                    else:
                        self.model.fit(X_train, y_train)

            # 记录更新历史
            update_record = {
                'timestamp': datetime.now(),
                'samples_used': len(X_train),
                'buffer_size': len(self.data_buffer),
                'memory_size': len(self.memory_bank)
            }

            self.update_history.append(update_record)
            self.last_update_date = datetime.now()

            # 清空缓冲区（保留记忆库）
            self.data_buffer = []

            logger.info("增量更新完成")

            return {
                'updated': True,
                'samples_used': len(X_train),
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"增量更新失败: {str(e)}")
            # 回滚模型
            if self.model_backup is not None:
                self.model = copy.deepcopy(self.model_backup)
            return {
                'updated': False,
                'error': str(e)
            }

    def get_update_history(self) -> pd.DataFrame:
        """
        获取更新历史

        Returns:
            更新历史 DataFrame
        """
        if not self.update_history:
            return pd.DataFrame()

        return pd.DataFrame(self.update_history)


class SimpleAutoML:
    """
    简化的 AutoML 系统
    基于预定义的模型池和参数网格
    """

    def __init__(self, model_pool: Optional[List[Any]] = None):
        """
        初始化 AutoML

        Args:
            model_pool: 模型池，None 则使用默认模型
        """
        self.model_pool = model_pool or self._get_default_models()
        self.best_model = None
        self.best_score = None
        self.trial_history = []

    def _get_default_models(self) -> List[Any]:
        """
        获取默认模型池

        Returns:
            模型列表
        """
        models = []

        try:
            import lightgbm as lgb
            models.append(('LightGBM', lgb.LGBMRegressor(
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                n_jobs=-1,
                verbose=-1
            )))
        except ImportError:
            pass

        try:
            import xgboost as xgb
            models.append(('XGBoost', xgb.XGBRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=6,
                n_jobs=-1,
                verbosity=0
            )))
        except ImportError:
            pass

        try:
            from catboost import CatBoostRegressor
            models.append(('CatBoost', CatBoostRegressor(
                iterations=200,
                learning_rate=0.05,
                depth=6,
                verbose=False,
                thread_count=-1
            )))
        except ImportError:
            pass

        return models

    def auto_train(self, X_train: np.ndarray, y_train: np.ndarray,
                   X_val: np.ndarray, y_val: np.ndarray,
                   metric: str = 'rmse') -> Dict[str, Any]:
        """
        自动训练并选择最佳模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
            metric: 评估指标 ('rmse', 'mae', 'r2')

        Returns:
            训练结果
        """
        logger.info(f"开始 AutoML，模型池大小: {len(self.model_pool)}")

        best_score = float('inf') if metric in ['rmse', 'mae'] else float('-inf')
        best_model = None
        best_model_name = None

        results = []

        for model_name, model in self.model_pool:
            try:
                logger.info(f"训练 {model_name}...")

                # 训练模型
                model.fit(X_train, y_train)

                # 预测
                y_pred = model.predict(X_val)

                # 计算指标
                score = self._calculate_metric(y_val, y_pred, metric)

                logger.info(f"{model_name} {metric}: {score:.4f}")

                # 记录结果
                results.append({
                    'model': model_name,
                    'score': score,
                    'timestamp': datetime.now()
                })

                # 更新最佳模型
                if metric in ['rmse', 'mae']:
                    if score < best_score:
                        best_score = score
                        best_model = model
                        best_model_name = model_name
                else:
                    if score > best_score:
                        best_score = score
                        best_model = model
                        best_model_name = model_name

            except Exception as e:
                logger.error(f"{model_name} 训练失败: {str(e)}")
                results.append({
                    'model': model_name,
                    'score': None,
                    'error': str(e),
                    'timestamp': datetime.now()
                })

        # 保存最佳模型
        self.best_model = best_model
        self.best_score = best_score
        self.trial_history = results

        logger.info(f"AutoML 完成，最佳模型: {best_model_name}, {metric}: {best_score:.4f}")

        return {
            'best_model': best_model,
            'best_model_name': best_model_name,
            'best_score': best_score,
            'all_results': results
        }

    def _calculate_metric(self, y_true: np.ndarray, y_pred: np.ndarray,
                          metric: str) -> float:
        """
        计算评估指标

        Args:
            y_true: 真实值
            y_pred: 预测值
            metric: 指标名称

        Returns:
            指标值
        """
        if metric == 'rmse':
            return np.sqrt(np.mean((y_true - y_pred) ** 2))
        elif metric == 'mae':
            return np.mean(np.abs(y_true - y_pred))
        elif metric == 'r2':
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            return 1 - (ss_res / ss_tot)
        else:
            raise ValueError(f"Unknown metric: {metric}")


class AutonomousLearningSystem:
    """
    自主学习系统（Lite 版）
    整合增量学习和简化 AutoML
    """

    def __init__(self,
                 base_model: Optional[Any] = None,
                 update_interval: int = 1,
                 enable_automl: bool = True):
        """
        初始化自主学习系统

        Args:
            base_model: 基础模型
            update_interval: 更新间隔（天数）
            enable_automl: 是否启用 AutoML
        """
        self.base_model = base_model
        self.update_interval = update_interval
        self.enable_automl = enable_automl

        # 初始化组件
        self.incremental_engine = None
        self.automl = None

        if base_model is not None:
            self.incremental_engine = IncrementalLearningEngine(
                model=base_model,
                update_interval=update_interval
            )

        if enable_automl:
            self.automl = SimpleAutoML()

        # 系统状态
        self.is_active = False
        self.last_initialization = None

    def initialize(self, X_init: np.ndarray, y_init: np.ndarray):
        """
        初始化系统

        Args:
            X_init: 初始特征数据
            y_init: 初始标签数据
        """
        logger.info("初始化自主学习系统...")

        # 如果没有基础模型，使用 AutoML 选择
        if self.base_model is None and self.enable_automl:
            split_idx = int(len(X_init) * 0.8)
            result = self.automl.auto_train(
                X_init[:split_idx], y_init[:split_idx],
                X_init[split_idx:], y_init[split_idx:]
            )

            self.base_model = result['best_model']
            logger.info(f"AutoML 选择了 {result['best_model_name']}")

        # 初始化增量学习引擎
        if self.base_model is not None:
            self.incremental_engine = IncrementalLearningEngine(
                model=self.base_model,
                update_interval=self.update_interval
            )

            # 初始训练
            self.base_model.fit(X_init, y_init)

        self.is_active = True
        self.last_initialization = datetime.now()

        logger.info("自主学习系统初始化完成")

    def add_new_data(self, X_new: np.ndarray, y_new: np.ndarray):
        """
        添加新数据

        Args:
            X_new: 新特征数据
            y_new: 新标签数据
        """
        if not self.is_active or self.incremental_engine is None:
            logger.warning("系统未初始化，无法添加数据")
            return

        self.incremental_engine.add_data(X_new, y_new)

        # 检查是否需要更新
        if self.incremental_engine.should_update():
            result = self.incremental_engine.update_model()
            logger.info(f"模型更新: {result}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        if not self.is_active or self.base_model is None:
            logger.warning("系统未初始化，无法预测")
            return np.array([])

        return self.base_model.predict(X)

    def get_status(self) -> Dict[str, Any]:
        """
        获取系统状态

        Returns:
            状态信息
        """
        status = {
            'is_active': self.is_active,
            'last_initialization': self.last_initialization,
            'update_interval': self.update_interval,
            'enable_automl': self.enable_automl
        }

        if self.incremental_engine is not None:
            status['buffer_size'] = len(self.incremental_engine.data_buffer)
            status['last_update'] = self.incremental_engine.last_update_date
            status['update_count'] = len(self.incremental_engine.update_history)

        if self.automl is not None and self.automl.best_model is not None:
            status['best_model_score'] = self.automl.best_score

        return status

    def save_system(self, filepath: str):
        """
        保存系统

        Args:
            filepath: 保存路径
        """
        system_data = {
            'base_model': self.base_model,
            'is_active': self.is_active,
            'last_initialization': self.last_initialization,
            'update_interval': self.update_interval,
            'enable_automl': self.enable_automl
        }

        with open(filepath, 'wb') as f:
            pickle.dump(system_data, f)

        logger.info(f"系统已保存到 {filepath}")

    def load_system(self, filepath: str):
        """
        加载系统

        Args:
            filepath: 系统路径
        """
        if not os.path.exists(filepath):
            logger.error(f"系统文件不存在: {filepath}")
            return

        with open(filepath, 'rb') as f:
            system_data = pickle.load(f)

        self.base_model = system_data['base_model']
        self.is_active = system_data['is_active']
        self.last_initialization = system_data['last_initialization']
        self.update_interval = system_data['update_interval']
        self.enable_automl = system_data['enable_automl']

        # 重新初始化增量引擎
        if self.base_model is not None:
            self.incremental_engine = IncrementalLearningEngine(
                model=self.base_model,
                update_interval=self.update_interval
            )

        logger.info(f"系统已从 {filepath} 加载")


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    np.random.seed(42)
    X = np.random.randn(1000, 10)
    y = np.sum(X, axis=1) + np.random.randn(1000) * 0.1

    # 初始化系统
    system = AutonomousLearningSystem(
        update_interval=1,
        enable_automl=True
    )

    # 初始化
    system.initialize(X[:800], y[:800])

    # 添加新数据
    system.add_new_data(X[800:900], y[800:900])

    # 预测
    predictions = system.predict(X[900:])

    print(f"预测结果（前5个）: {predictions[:5]}")

    # 获取状态
    status = system.get_status()
    print(f"\n系统状态: {status}")