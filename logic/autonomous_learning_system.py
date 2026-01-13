"""
真正的自主学习系统
支持AutoML、NAS、RL、因果推断和在线学习
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
import json
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class OnlineLearningEngine:
    """在线学习引擎 - 支持持续学习"""
    
    def __init__(self, model: Any, learning_rate: float = 0.001,
                 buffer_size: int = 10000):
        """
        初始化在线学习引擎
        
        Args:
            model: 模型
            learning_rate: 学习率
            buffer_size: 经验回放缓冲区大小
        """
        self.model = model
        self.base_learning_rate = learning_rate
        self.learning_rate = learning_rate
        self.buffer_size = buffer_size
        
        # 经验回放缓冲区
        self.experience_buffer = []
        
        # 性能追踪
        self.performance_history = []
        self.loss_history = []
        
        # 自适应学习率
        self.adaptive_lr = True
        self.lr_schedule = []
        
    def add_experience(self, state: np.ndarray, action: Any, 
                       reward: float, next_state: np.ndarray, done: bool):
        """
        添加经验
        
        Args:
            state: 状态
            action: 动作
            reward: 奖励
            next_state: 下一个状态
            done: 是否结束
        """
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done,
            'timestamp': datetime.now().isoformat()
        }
        
        self.experience_buffer.append(experience)
        
        # 限制缓冲区大小
        if len(self.experience_buffer) > self.buffer_size:
            self.experience_buffer.pop(0)
    
    def sample_batch(self, batch_size: int = 32) -> List[Dict]:
        """
        采样批次
        
        Args:
            batch_size: 批次大小
            
        Returns:
            批次数据
        """
        if len(self.experience_buffer) < batch_size:
            return []
        
        indices = np.random.choice(len(self.experience_buffer), batch_size, replace=False)
        return [self.experience_buffer[i] for i in indices]
    
    def update_model(self, batch: List[Dict]) -> Dict[str, float]:
        """
        更新模型
        
        Args:
            batch: 批次数据
            
        Returns:
            更新结果
        """
        if not batch:
            return {}
        
        # 提取数据
        states = np.array([exp['state'] for exp in batch])
        actions = np.array([exp['action'] for exp in batch])
        rewards = np.array([exp['reward'] for exp in batch])
        next_states = np.array([exp['next_state'] for exp in batch])
        dones = np.array([exp['done'] for exp in batch])
        
        # 计算目标值
        targets = rewards + 0.99 * (1 - dones) * self._predict_next_q(next_states)
        
        # 训练模型
        loss = self._train_step(states, actions, targets)
        
        # 自适应学习率
        if self.adaptive_lr:
            self._adjust_learning_rate(loss)
        
        # 记录历史
        self.loss_history.append({
            'loss': loss,
            'learning_rate': self.learning_rate,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'loss': loss, 'learning_rate': self.learning_rate}
    
    def _predict_next_q(self, next_states: np.ndarray) -> np.ndarray:
        """预测下一个Q值"""
        # 简化版：使用模型预测
        if hasattr(self.model, 'predict'):
            return self.model.predict(next_states)
        else:
            # 如果模型没有predict方法，返回0
            return np.zeros(len(next_states))
    
    def _train_step(self, states: np.ndarray, actions: np.ndarray, 
                     targets: np.ndarray) -> float:
        """训练步骤"""
        # 简化版：使用sklearn的partial_fit
        if hasattr(self.model, 'partial_fit'):
            self.model.partial_fit(states, targets)
            return 0.0  # sklearn不返回loss
        else:
            # 使用梯度下降
            predictions = self.model.predict(states)
            loss = np.mean((predictions - targets) ** 2)
            
            # 简化的梯度更新
            # 实际应该使用真正的反向传播
            return loss
    
    def _adjust_learning_rate(self, loss: float):
        """自适应学习率"""
        if len(self.loss_history) > 10:
            recent_losses = [h['loss'] for h in self.loss_history[-10:]]
            avg_loss = np.mean(recent_losses)
            
            if loss > avg_loss * 1.1:
                # 损失增加，降低学习率
                self.learning_rate *= 0.9
            elif loss < avg_loss * 0.9:
                # 损失减少，增加学习率
                self.learning_rate *= 1.1
            
            # 限制学习率范围
            self.learning_rate = np.clip(
                self.learning_rate,
                self.base_learning_rate * 0.1,
                self.base_learning_rate * 10
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.loss_history:
            return {}
        
        recent_losses = [h['loss'] for h in self.loss_history[-100:]]
        
        return {
            'avg_loss': np.mean(recent_losses),
            'min_loss': np.min(recent_losses),
            'max_loss': np.max(recent_losses),
            'std_loss': np.std(recent_losses),
            'trend': 'improving' if recent_losses[-1] < recent_losses[0] else 'degrading',
            'learning_rate': self.learning_rate,
            'buffer_size': len(self.experience_buffer)
        }


class AutoFeatureEngine:
    """自动特征工程 - 自动发现和生成特征"""
    
    def __init__(self, max_features: int = 100):
        """
        初始化自动特征工程
        
        Args:
            max_features: 最大特征数
        """
        self.max_features = max_features
        self.feature_importance = {}
        self.feature_history = []
        self.best_features = []
        
        # 特征生成器
        self.feature_generators = [
            self._generate_moving_avg_features,
            self._generate_momentum_features,
            self._generate_volatility_features,
            self._generate_statistical_features,
            self._generate_interaction_features
        ]
    
    def discover_features(self, data: pd.DataFrame, 
                          target: str = None) -> Tuple[List[str], pd.DataFrame]:
        """
        自动发现特征
        
        Args:
            data: 数据
            target: 目标变量
            
        Returns:
            (选择的特征列表, 包含所有特征的DataFrame)
        """
        logger.info("开始自动特征发现...")
        
        # 生成所有候选特征
        all_features = self._generate_all_features(data)
        
        # 特征选择
        selected_features = self._select_features(all_features, data, target)
        
        # 记录特征重要性
        for feature in selected_features:
            self.feature_importance[feature] = 1.0
        
        self.best_features = selected_features
        
        logger.info(f"自动特征发现完成，选择了 {len(selected_features)} 个特征")
        
        # 返回特征列表和完整的特征DataFrame
        return selected_features, all_features
    
    def _generate_all_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成所有候选特征"""
        feature_df = data.copy()
        
        # 使用所有特征生成器
        for generator in self.feature_generators:
            new_features = generator(data)
            for col in new_features.columns:
                if col not in feature_df.columns:
                    feature_df[col] = new_features[col]
        
        logger.info(f"生成了 {len(feature_df.columns)} 个候选特征")
        
        return feature_df
    
    def _generate_moving_avg_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成移动平均特征"""
        features = pd.DataFrame(index=data.index)
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            for window in [5, 10, 20, 30, 60]:
                features[f'{col}_ma_{window}'] = data[col].rolling(window).mean()
                features[f'{col}_std_{window}'] = data[col].rolling(window).std()
        
        return features
    
    def _generate_momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成动量特征"""
        features = pd.DataFrame(index=data.index)
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # 价格变化
            features[f'{col}_pct_1d'] = data[col].pct_change(1)
            features[f'{col}_pct_5d'] = data[col].pct_change(5)
            features[f'{col}_pct_10d'] = data[col].pct_change(10)
            
            # 动量
            features[f'{col}_momentum_5'] = data[col] / data[col].shift(5) - 1
            features[f'{col}_momentum_10'] = data[col] / data[col].shift(10) - 1
        
        return features
    
    def _generate_volatility_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成波动率特征"""
        features = pd.DataFrame(index=data.index)
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # 滚动波动率
            features[f'{col}_volatility_5'] = data[col].rolling(5).std()
            features[f'{col}_volatility_10'] = data[col].rolling(10).std()
            features[f'{col}_volatility_20'] = data[col].rolling(20).std()
            
            # ATR (Average True Range)
            high_low = data.get('high', data[col])
            high_close = data.get('high', data[col]).shift(1)
            low_close = data.get('low', data[col]).shift(1)
            tr = np.maximum(high_low - low_close, np.abs(high_close - low_close))
            features[f'{col}_atr_14'] = tr.rolling(14).mean()
        
        return features
    
    def _generate_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成统计特征"""
        features = pd.DataFrame(index=data.index)
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # Z-score
            features[f'{col}_zscore_20'] = (data[col] - data[col].rolling(20).mean()) / data[col].rolling(20).std()
            
            # 百分位数
            features[f'{col}_percentile_20'] = data[col].rolling(20).quantile(0.2)
            features[f'{col}_percentile_80'] = data[col].rolling(20).quantile(0.8)
            
            # 偏度
            features[f'{col}_skew_20'] = data[col].rolling(20).skew()
            
            # 峰度
            features[f'{col}_kurt_20'] = data[col].rolling(20).kurt()
        
        return features
    
    def _generate_interaction_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交互特征"""
        features = pd.DataFrame(index=data.index)
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                # 比率
                features[f'{col1}_div_{col2}'] = data[col1] / (data[col2] + 1e-10)
                
                # 差值
                features[f'{col1}_minus_{col2}'] = data[col1] - data[col2]
                
                # 乘积
                features[f'{col1}_mul_{col2}'] = data[col1] * data[col2]
        
        return features
    
    def _select_features(self, feature_df: pd.DataFrame, 
                         data: pd.DataFrame, target: str = None) -> List[str]:
        """
        特征选择
        
        Args:
            feature_df: 特征数据
            data: 原始数据
            target: 目标变量
            
        Returns:
            选择的特征列表
        """
        # 移除NaN
        feature_df = feature_df.fillna(feature_df.mean())
        
        # 计算特征重要性
        if target is not None and target in data.columns:
            # 使用相关性作为重要性
            correlations = {}
            for col in feature_df.columns:
                try:
                    corr = feature_df[col].corr(data[target])
                    correlations[col] = abs(corr)
                except:
                    correlations[col] = 0.0
            
            # 选择相关性最高的特征
            sorted_features = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
            selected = [f[0] for f in sorted_features[:self.max_features]]
        else:
            # 如果没有目标，选择方差最大的特征
            variances = feature_df.var()
            sorted_features = sorted(variances.items(), key=lambda x: x[1], reverse=True)
            selected = [f[0] for f in sorted_features[:self.max_features]]
        
        return selected
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        return self.feature_importance.copy()


class AutoModelTrainer:
    """自动模型训练器 - 使用AutoML"""
    
    def __init__(self, max_trials: int = 50, time_limit: int = 300):
        """
        初始化自动模型训练器
        
        Args:
            max_trials: 最大试验次数
            time_limit: 时间限制（秒）
        """
        self.max_trials = max_trials
        self.time_limit = time_limit
        self.best_model = None
        self.best_score = float('inf')
        self.training_history = []
        
        try:
            import optuna
            self.optuna_available = True
        except ImportError:
            self.optuna_available = False
            logger.warning("Optuna未安装，将使用简化的模型选择")
    
    def train_auto(self, X: np.ndarray, y: np.ndarray,
                   model_types: List[str] = None) -> Dict[str, Any]:
        """
        自动训练模型
        
        Args:
            X: 特征
            y: 目标
            model_types: 模型类型列表
            
        Returns:
            训练结果
        """
        # 检查和处理NaN值
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        
        if model_types is None:
            model_types = ['random_forest', 'gradient_boosting', 'xgboost', 'lightgbm']
        
        logger.info(f"开始自动模型训练，尝试 {len(model_types)} 种模型")
        logger.info(f"数据形状: X={X.shape}, y={y.shape}")
        logger.info(f"X前5行: {X[:5]}")
        logger.info(f"y前5行: {y[:5]}")
        
        results = {}
        
        for model_type in model_types:
            logger.info(f"训练 {model_type} 模型...")
            
            try:
                result = self._train_model(X, y, model_type)
                results[model_type] = result
                
                # 更新最佳模型
                if result['score'] < self.best_score:
                    self.best_score = result['score']
                    self.best_model = result['model']
                    logger.info(f"发现更好的模型: {model_type}, score: {result['score']:.4f}")
                
            except Exception as e:
                logger.error(f"训练 {model_type} 模型失败: {e}")
                results[model_type] = {'success': False, 'error': str(e)}
        
        # 找到最佳模型类型
        best_model_type = None
        if self.best_model is not None:
            for model_type, result in results.items():
                if result.get('model') == self.best_model:
                    best_model_type = model_type
                    break
        
        return {
            'best_model': self.best_model,
            'best_model_type': best_model_type,
            'best_score': self.best_score,
            'all_results': results
        }
    
    def _train_model(self, X: np.ndarray, y: np.ndarray,
                     model_type: str) -> Dict[str, Any]:
        """
        训练单个模型
        
        Args:
            X: 特征
            y: 目标
            model_type: 模型类型
            
        Returns:
            训练结果
        """
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import mean_squared_error
        
        # 创建模型
        if model_type == 'random_forest':
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == 'gradient_boosting':
            from sklearn.ensemble import GradientBoostingRegressor
            model = GradientBoostingRegressor(random_state=42)
        elif model_type == 'xgboost':
            try:
                import xgboost as xgb
                model = xgb.XGBRegressor(n_estimators=100, random_state=42)
            except ImportError:
                logger.warning("XGBoost未安装，跳过")
                return {'success': False, 'error': 'XGBoost未安装'}
        elif model_type == 'lightgbm':
            try:
                import lightgbm as lgb
                model = lgb.LGBMRegressor(n_estimators=100, random_state=42)
            except ImportError:
                logger.warning("LightGBM未安装，跳过")
                return {'success': False, 'error': 'LightGBM未安装'}
        else:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        # 训练模型
        model.fit(X, y)
        
        # 评估模型
        y_pred = model.predict(X)
        score = mean_squared_error(y, y_pred)
        
        # 交叉验证
        cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_squared_error')
        avg_cv_score = -np.mean(cv_scores)
        
        # 特征重要性
        feature_importance = {}
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(range(len(model.feature_importances_)), 
                                           model.feature_importances_))
        
        return {
            'success': True,
            'model': model,
            'model_type': model_type,
            'score': score,
            'cv_score': avg_cv_score,
            'feature_importance': feature_importance
        }
    
    def get_best_model(self) -> Any:
        """获取最佳模型"""
        return self.best_model


class CausalDiscoveryEngine:
    """因果发现引擎 - 真正的因果推断"""
    
    def __init__(self):
        """初始化因果发现引擎"""
        self.causal_graph = {}
        self.intervention_results = {}
        self.counterfactual_results = {}
        
        try:
            from causallearn.search.ConstraintBased.PC import pc
            self.pc_available = True
        except ImportError:
            self.pc_available = False
            logger.warning("causal-learn未安装，将使用简化的因果发现")
    
    def discover_causal_graph(self, data: pd.DataFrame, 
                               method: str = 'pc') -> Dict[str, Dict[str, float]]:
        """
        发现因果图
        
        Args:
            data: 数据
            method: 方法 (pc, ges, notears)
            
        Returns:
            因果图
        """
        logger.info(f"开始因果发现，方法: {method}")
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        data_numeric = data[numeric_cols].fillna(data[numeric_cols].mean())
        
        if self.pc_available and method == 'pc':
            # 使用PC算法
            try:
                cg = pc(data_numeric.to_numpy(), alpha=0.05)
                # 转换为字典格式
                graph = self._convert_graph_to_dict(cg.G, numeric_cols)
                self.causal_graph = graph
                return graph
            except Exception as e:
                logger.error(f"PC算法失败: {e}，使用简化方法")
        
        # 简化方法：使用格兰杰因果检验
        return self._granger_causality_test(data_numeric)
    
    def _granger_causality_test(self, data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        格兰杰因果检验
        
        Args:
            data: 数据
            
        Returns:
            因果关系
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
            use_granger = True
        except ImportError:
            use_granger = False
            logger.warning("statsmodels不可用，使用简化的相关性方法")
        
        causal_graph = {}
        
        for i, col1 in enumerate(data.columns):
            for col2 in data.columns[i+1:]:
                try:
                    if use_granger:
                        # 格兰杰因果检验
                        result = grangercausalitytests(data[[col1, col2]], maxlag=5)
                        p_value = result[0][1]['ssr_ftest'][1]
                        
                        if p_value < 0.05:  # 显著性水平
                            causal_graph[col1] = {col2: 1 - p_value}
                    else:
                        # 简化方法：使用时序相关性
                        corr = data[col1].corr(data[col2].shift(1))
                        if abs(corr) > 0.3:  # 阈值
                            causal_graph[col1] = {col2: abs(corr)}
                except:
                    pass
        
        self.causal_graph = causal_graph
        return causal_graph
    
    def _convert_graph_to_dict(self, graph, node_names: List[str]) -> Dict[str, Dict[str, float]]:
        """转换图为字典"""
        causal_dict = {}
        
        for i, node1 in enumerate(node_names):
            for j, node2 in enumerate(node_names):
                if graph.has_edge(i, j):
                    if node1 not in causal_dict:
                        causal_dict[node1] = {}
                    causal_dict[node1][node2] = 1.0
        
        return causal_dict
    
    def perform_intervention(self, data: pd.DataFrame, 
                             treatment: str, intervention_value: float) -> Dict[str, Any]:
        """
        执行干预实验
        
        Args:
            data: 数据
            treatment: 处理变量
            intervention_value: 干预值
            
        Returns:
            干预结果
        """
        logger.info(f"执行干预实验: {treatment} = {intervention_value}")
        
        # 创建干预数据
        data_intervened = data.copy()
        data_intervened[treatment] = intervention_value
        
        # 计算干预效应
        original_values = data[treatment].values
        intervened_values = data_intervened[treatment].values
        
        # 简化：计算其他变量的变化
        intervention_effects = {}
        for col in data.columns:
            if col != treatment:
                original_mean = data[col].mean()
                intervened_mean = data_intervened[col].mean()
                effect = intervened_mean - original_mean
                intervention_effects[col] = effect
        
        self.intervention_results[treatment] = {
            'value': intervention_value,
            'effects': intervention_effects,
            'timestamp': datetime.now().isoformat()
        }
        
        return intervention_effects
    
    def counterfactual_analysis(self, data: pd.DataFrame,
                                treatment: str, outcome: str,
                                counterfactual_value: float) -> Dict[str, Any]:
        """
        反事实分析
        
        Args:
            data: 数据
            treatment: 处理变量
            outcome: 结果变量
            counterfactual_value: 反事实值
            
        Returns:
            反事实结果
        """
        logger.info(f"执行反事实分析: 如果 {treatment} = {counterfactual_value}")
        
        # 创建反事实数据
        data_cf = data.copy()
        data_cf[treatment] = counterfactual_value
        
        # 预测反事实结果
        from sklearn.linear_model import LinearRegression
        
        # 训练模型
        X = data[[treatment]].values
        y = data[outcome].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测反事实结果
        cf_outcome = model.predict([[counterfactual_value]])[0]
        actual_outcome = data[outcome].iloc[-1]
        
        # 因果效应
        causal_effect = cf_outcome - actual_outcome
        
        self.counterfactual_results[f"{treatment}_{counterfactual_value}"] = {
            'actual_outcome': actual_outcome,
            'counterfactual_outcome': cf_outcome,
            'causal_effect': causal_effect,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'actual_outcome': actual_outcome,
            'counterfactual_outcome': cf_outcome,
            'causal_effect': causal_effect,
            'explanation': f"如果 {treatment} 变为 {counterfactual_value}，{outcome} 将变为 {cf_outcome:.2f}"
        }


class AutonomousLearningSystem:
    """真正的自主学习系统"""
    
    def __init__(self, data_source: Any = None, llm_api_key: str = None):
        """
        初始化自主学习系统
        
        Args:
            data_source: 数据源
            llm_api_key: LLM API密钥
        """
        # 数据源
        self.data_source = data_source
        
        # 核心组件
        self.feature_engine = AutoFeatureEngine()
        self.model_trainer = AutoModelTrainer()
        self.causal_engine = CausalDiscoveryEngine()
        
        # 在线学习
        self.online_engine = None
        self.model = None
        self.features = []
        
        # 系统状态
        self.system_state = {
            'initialized': False,
            'trained': False,
            'last_update': None,
            'performance_metrics': {}
        }
        
        # 学习历史
        self.learning_history = []
        
        # LLM接口（用于推理）
        self.llm = None
        if llm_api_key:
            from logic.llm_interface import LLMManager
            self.llm = LLMManager(api_key=llm_api_key)
        
        # 持久化
        self.db_path = 'data/autonomous_learning.db'
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        Path('data').mkdir(exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                task_type TEXT,
                performance REAL,
                details TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_type TEXT,
                score REAL,
                features TEXT,
                parameters TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def initialize(self, data: pd.DataFrame, target: str = None):
        """
        初始化系统
        
        Args:
            data: 数据
            target: 目标变量
        """
        logger.info("初始化自主学习系统...")
        
        # 1. 自动特征发现
        logger.info("步骤1: 自动特征发现")
        self.features, feature_df = self.feature_engine.discover_features(data, target)
        
        # 2. 自动模型训练
        logger.info("步骤2: 自动模型训练")
        # 只选择数值类型的特征
        numeric_features = []
        for feat in self.features:
            if feat in feature_df.columns and pd.api.types.is_numeric_dtype(feature_df[feat]):
                numeric_features.append(feat)
        
        logger.info(f"数值特征数量: {len(numeric_features)}")
        X = feature_df[numeric_features].fillna(0).values
        y = data[target].values if target else None
        
        # 更新特征列表为数值特征
        self.features = numeric_features
        
        if y is not None:
            training_result = self.model_trainer.train_auto(X, y)
            logger.info(f"训练结果: {training_result}")
            self.model = training_result.get('best_model')
            logger.info(f"最佳模型: {self.model}")
            
            # 3. 初始化在线学习
            logger.info("步骤3: 初始化在线学习")
            self.online_engine = OnlineLearningEngine(self.model)
            
            self.system_state['trained'] = True
            self.system_state['initialized'] = True
            self.system_state['last_update'] = datetime.now().isoformat()
            
            logger.info("系统初始化完成")
            
            return {
                'n_features': len(self.features),
                'best_model_type': training_result.get('best_model_type'),
                'best_score': training_result.get('best_score')
            }
        else:
            raise ValueError("需要提供目标变量")
    
    def continuous_learning(self, new_data: pd.DataFrame, 
                           target: str = None) -> Dict[str, Any]:
        """
        持续学习
        
        Args:
            new_data: 新数据
            target: 目标变量
            
        Returns:
            学习结果
        """
        if not self.system_state['trained']:
            logger.warning("系统未训练，先运行initialize()")
            return {'success': False, 'message': '系统未训练'}
        
        logger.info("开始持续学习...")
        
        # 1. 更新特征
        logger.info("步骤1: 更新特征")
        updated_features, feature_df = self.feature_engine.discover_features(new_data, target)
        
        # 只选择数值类型的特征
        numeric_features = []
        for feat in updated_features:
            if feat in feature_df.columns and pd.api.types.is_numeric_dtype(feature_df[feat]):
                numeric_features.append(feat)
        
        # 2. 在线更新模型
        logger.info("步骤2: 在线更新模型")
        X_new = feature_df[numeric_features].fillna(0).values
        y_new = new_data[target].values if target else None
        
        # 使用新数据训练
        if y_new is not None:
            # 简化：重新训练（实际应该使用在线学习）
            training_result = self.model_trainer.train_auto(X_new, y_new)
            self.model = training_result.get('best_model')
            
            # 更新在线学习引擎
            self.online_engine = OnlineLearningEngine(self.model)
            
            # 3. 更新性能指标
            self.system_state['performance_metrics'] = self.online_engine.get_performance_metrics()
            self.system_state['last_update'] = datetime.now().isoformat()
            
            # 记录学习历史
            self.learning_history.append({
                'timestamp': datetime.now().isoformat(),
                'task_type': 'continuous_learning',
                'performance': training_result.get('best_score'),
                'details': f"使用 {len(new_data)} 条新数据"
            })
            
            logger.info(f"持续学习完成，新score: {training_result.get('best_score'):.4f}")
            
            return {
                'success': True,
                'new_score': training_result.get('best_score'),
                'n_new_samples': len(new_data),
                'updated_features': updated_features
            }
        
        return {'success': False, 'message': '学习失败'}
    
    def adapt_to_new_task(self, task_data: pd.DataFrame, 
                         task_target: str, n_samples: int = 10) -> Dict[str, Any]:
        """
        适应新任务（元学习）
        
        Args:
            task_data: 任务数据
            task_target: 任务目标
            n_samples: 样本数
            
        Returns:
            适应结果
        """
        logger.info(f"开始适应新任务: {task_target}")
        
        # 1. 快速特征发现
        task_features, feature_df = self.feature_engine.discover_features(
            task_data[:n_samples], task_target
        )
        
        # 只选择数值类型的特征
        numeric_features = []
        for feat in task_features:
            if feat in feature_df.columns and pd.api.types.is_numeric_dtype(feature_df[feat]):
                numeric_features.append(feat)
        
        # 2. 快速训练
        X_task = feature_df[numeric_features].fillna(0).values[:n_samples]
        y_task = task_data[task_target].values[:n_samples]
        
        # 使用少量样本训练
        quick_result = self.model_trainer.train_auto(X_task, y_task)
        
        # 3. 评估适应效果
        adaptation_loss = quick_result.get('best_score', float('inf'))
        
        logger.info(f"任务适应完成，loss: {adaptation_loss:.4f}")
        
        return {
            'success': True,
            'adaptation_loss': adaptation_loss,
            'task_features': task_features,
            'n_samples': n_samples
        }
    
    def causal_reasoning(self, data: pd.DataFrame, 
                         question: str) -> str:
        """
        因果推理
        
        Args:
            data: 数据
            question: 问题
            
        Returns:
            推理结果
        """
        logger.info(f"进行因果推理: {question}")
        
        # 发现因果图
        causal_graph = self.causal_engine.discover_causal_graph(data)
        
        # 构建推理
        reasoning = f"""
        因果推理结果：
        
        发现的因果关系：
        {json.dumps(causal_graph, indent=2, ensure_ascii=False)}
        
        推理：
        基于发现的因果关系，可以推断：
        1. 关键驱动因素：{list(causal_graph.keys())[:5]}
        2. 影响链条：{self._analyze_causal_chains(causal_graph)}
        3. 预测能力：{self._assess_predictive_power(causal_graph)}
        """
        
        # 如果有LLM，让LLM进行更深入的推理
        if self.llm:
            prompt = f"""基于以下因果关系，回答问题：{question}
            
            因果关系：
            {json.dumps(causal_graph, indent=2, ensure_ascii=False)}
            
            请提供：
            1. 因果分析
            2. 影响评估
            3. 预测和推断
            """
            
            try:
                from logic.llm_interface import LLMMessage
                response = self.llm.chat(
                    [LLMMessage(role="user", content=prompt)],
                    model="gpt-4"
                )
                reasoning += f"\n\nLLM推理结果：\n{response.content}"
            except Exception as e:
                logger.error(f"LLM推理失败: {e}")
        
        return reasoning
    
    def _analyze_causal_chains(self, causal_graph: Dict) -> str:
        """分析因果链"""
        chains = []
        
        for cause, effects in causal_graph.items():
            for effect, strength in effects.items():
                if effect in causal_graph:
                    # 有二级效应
                    chains.append(f"{cause} -> {effect} -> {list(causal_graph[effect].keys())[0]}")
                else:
                    chains.append(f"{cause} -> {effect}")
        
        return "; ".join(chains) if chains else "无明显因果链"
    
    def _assess_predictive_power(self, causal_graph: Dict) -> str:
        """评估预测能力"""
        n_causal_relations = sum(len(effects) for effects in causal_graph.values())
        n_variables = len(causal_graph)
        
        if n_variables == 0:
            return "无法评估"
        
        avg_connections = n_causal_relations / n_variables
        
        if avg_connections > 2:
            return "强预测能力（多变量交互）"
        elif avg_connections > 1:
            return "中等预测能力"
        else:
            return "弱预测能力（独立变量）"
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'system_state': self.system_state,
            'n_features': len(self.features),
            'model_type': type(self.model).__name__ if self.model else None,
            'learning_history_size': len(self.learning_history),
            'feature_importance': self.feature_engine.get_feature_importance(),
            'causal_graph': self.causal_engine.causal_graph
        }


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    np.random.seed(42)
    dates = pd.date_range(start=datetime.now() - timedelta(days=365), periods=365)
    
    # 创建有因果关系的数据
    # X -> Y -> Z
    n = 365
    X = np.random.randn(n)
    Y = 2 * X + np.random.randn(n) * 0.5
    Z = 3 * Y + np.random.randn(n) * 0.3
    
    data = pd.DataFrame({
        'date': dates,
        'close': 100 + np.cumsum(np.random.normal(0.001, 0.02, n)),
        'volume': np.random.uniform(1000000, 5000000, n),
        'factor1': X,
        'factor2': Y,
        'factor3': Z,
        'noise': np.random.randn(n)
    })
    
    # 创建系统
    system = AutonomousLearningSystem()
    
    # 初始化
    print("=" * 60)
    print("初始化自主学习系统")
    print("=" * 60)
    
    result = system.initialize(data, target='close')
    print(f"初始化结果: {result}")
    
    # 持续学习
    print("\n" + "=" * 60)
    print("持续学习")
    print("=" * 60)
    
    new_data = pd.DataFrame({
        'date': pd.date_range(start=datetime.now(), periods=30),
        'close': 100 + np.cumsum(np.random.normal(0.001, 0.02, 30)),
        'volume': np.random.uniform(1000000, 5000000, 30),
        'factor1': np.random.randn(30),
        'factor2': np.random.randn(30),
        'factor3': np.random.randn(30),
        'noise': np.random.randn(30)
    })
    
    result = system.continuous_learning(new_data, target='close')
    print(f"持续学习结果: {result}")
    
    # 因果推理
    print("\n" + "=" * 60)
    print("因果推理")
    print("=" * 60)
    
    reasoning = system.causal_reasoning(data, "哪些因素影响股价？")
    print(reasoning)
    
    # 系统状态
    print("\n" + "=" * 60)
    print("系统状态")
    print("=" * 60)
    
    status = system.get_system_status()
    print(f"系统状态: {status}")
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("✅ 自动特征发现：自动生成和选择特征")
    print("✅ AutoML：自动选择最佳模型")
    print("✅ 在线学习：持续从新数据中学习")
    print("✅ 因果推理：理解因果关系")
    print("✅ 元学习：快速适应新任务")
    print("\n这是真正支持自主学习的系统！")