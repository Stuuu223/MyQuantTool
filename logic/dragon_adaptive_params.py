"""
龙头战法自适应参数系统
实现贝叶斯优化和在线参数调整
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
import sqlite3
from collections import deque
from scipy.optimize import minimize
from scipy.stats import beta


class BayesianOptimizer:
    """贝叶斯优化器"""
    
    def __init__(self, 
                 param_bounds: Dict[str, Tuple[float, float]],
                 n_init: int = 10):
        """
        初始化贝叶斯优化器
        
        Args:
            param_bounds: 参数边界 {param_name: (min, max)}
            n_init: 初始采样数量
        """
        self.param_bounds = param_bounds
        self.param_names = list(param_bounds.keys())
        self.n_init = n_init
        
        # 观测数据
        self.X_observed = []
        self.y_observed = []
        
        # Beta分布参数（用于采集函数）
        self.alpha = 2.0
        self.beta = 2.0
    
    def suggest(self) -> Dict[str, float]:
        """
        建议下一个参数组合
        
        Returns:
            参数字典
        """
        if len(self.X_observed) < self.n_init:
            # 随机采样
            return self._random_sample()
        else:
            # 使用采集函数
            return self._acquisition_function()
    
    def _random_sample(self) -> Dict[str, float]:
        """随机采样"""
        params = {}
        for name in self.param_names:
            min_val, max_val = self.param_bounds[name]
            params[name] = np.random.uniform(min_val, max_val)
        return params
    
    def _acquisition_function(self) -> Dict[str, float]:
        """采集函数（UCB）"""
        # 简化的UCB实现
        best_idx = np.argmax(self.y_observed)
        best_params = self.X_observed[best_idx]
        
        # 在最佳参数附近采样
        new_params = {}
        for i, name in enumerate(self.param_names):
            min_val, max_val = self.param_bounds[name]
            best_val = best_params[i]  # 使用索引而不是参数名
            
            # Beta分布采样
            scale = (max_val - min_val) * 0.2
            new_val = best_val + np.random.beta(self.alpha, self.beta) * scale - scale / 2
            
            # 确保在边界内
            new_params[name] = np.clip(new_val, min_val, max_val)
        
        return new_params
    
    def observe(self, params: Dict[str, float], score: float):
        """
        观测结果
        
        Args:
            params: 参数字典
            score: 评分
        """
        param_values = [params[name] for name in self.param_names]
        self.X_observed.append(param_values)
        self.y_observed.append(score)
    
    def get_best_params(self) -> Dict[str, float]:
        """获取最佳参数"""
        if not self.y_observed:
            return {}
        
        best_idx = np.argmax(self.y_observed)
        best_values = self.X_observed[best_idx]
        
        return {name: value for name, value in zip(self.param_names, best_values)}
    
    def get_observation_summary(self) -> Dict:
        """获取观测摘要"""
        if not self.y_observed:
            return {}
        
        return {
            'n_observations': len(self.y_observed),
            'best_score': max(self.y_observed),
            'mean_score': np.mean(self.y_observed),
            'std_score': np.std(self.y_observed)
        }


class DragonParameterSpace:
    """龙头战法参数空间"""
    
    def __init__(self):
        """初始化参数空间"""
        self.base_params = {
            'min_turnover': 5.0,
            'min_volume': 100000000,
            'min_limit_ups': 2,
            'max_days': 10,
            'stop_loss': 0.05,
            'take_profit': 0.15,
            'position_size': 0.5,
            'entry_threshold': 0.6,
            'exit_threshold': 0.3
        }
        
        self.param_bounds = {
            'min_turnover': (1.0, 20.0),
            'min_volume': (50000000, 500000000),
            'min_limit_ups': (1, 5),
            'max_days': (5, 20),
            'stop_loss': (0.02, 0.10),
            'take_profit': (0.10, 0.30),
            'position_size': (0.1, 0.9),
            'entry_threshold': (0.4, 0.8),
            'exit_threshold': (0.1, 0.5)
        }
    
    def get_bounds(self) -> Dict[str, Tuple[float, float]]:
        """获取参数边界"""
        return self.param_bounds
    
    def get_base_params(self) -> Dict[str, float]:
        """获取基础参数"""
        return self.base_params.copy()


class DragonBacktestEvaluator:
    """龙头战法回测评估器"""
    
    def __init__(self):
        """初始化评估器"""
        pass
    
    def evaluate(self, 
                params: Dict[str, float],
                historical_data: pd.DataFrame) -> Dict:
        """
        评估参数
        
        Args:
            params: 参数字典
            historical_data: 历史数据
            
        Returns:
            评估结果
        """
        # 模拟回测
        n_trades = np.random.randint(10, 100)
        win_rate = np.random.uniform(0.3, 0.7)
        avg_return = np.random.uniform(-0.05, 0.15)
        max_drawdown = np.random.uniform(0.05, 0.20)
        
        # 计算夏普比率
        sharpe_ratio = (avg_return - 0.03) / (max_drawdown if max_drawdown > 0 else 0.01)
        
        # 综合评分
        score = self._calculate_composite_score(
            sharpe_ratio, win_rate, avg_return, max_drawdown
        )
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'max_drawdown': max_drawdown,
            'n_trades': n_trades,
            'score': score
        }
    
    def _calculate_composite_score(self,
                                  sharpe_ratio: float,
                                  win_rate: float,
                                  avg_return: float,
                                  max_drawdown: float) -> float:
        """计算综合评分"""
        # 加权综合
        score = (
            sharpe_ratio * 0.4 +
            win_rate * 0.3 +
            avg_return * 0.2 -
            max_drawdown * 0.1
        )
        
        return score


class OnlineParameterAdjuster:
    """在线参数调整器"""
    
    def __init__(self, 
                 base_params: Dict[str, float],
                 param_bounds: Dict[str, Tuple[float, float]]):
        """
        初始化在线调整器
        
        Args:
            base_params: 基础参数
            param_bounds: 参数边界
        """
        self.base_params = base_params
        self.param_bounds = param_bounds
        self.current_params = base_params.copy()
        
        # 性能追踪
        self.performance_history = deque(maxlen=100)
        self.adjustment_history = deque(maxlen=100)
        
        # 调整规则
        self.adjustment_rules = self._load_adjustment_rules()
    
    def _load_adjustment_rules(self) -> List[Dict]:
        """加载调整规则"""
        return [
            {
                'condition': lambda perf: perf.get('sharpe_ratio', 0) < 1.0,
                'action': lambda params: self._reduce_risk(params)
            },
            {
                'condition': lambda perf: perf.get('win_rate', 0) < 0.4,
                'action': lambda params: self._tighten_entry(params)
            },
            {
                'condition': lambda perf: perf.get('max_drawdown', 0) > 0.15,
                'action': lambda params: self._reduce_position(params)
            },
            {
                'condition': lambda perf: perf.get('avg_return', 0) > 0.2,
                'action': lambda params: self._loosen_exit(params)
            }
        ]
    
    def adjust(self, performance: Dict) -> Dict:
        """
        根据性能调整参数
        
        Args:
            performance: 性能指标
            
        Returns:
            调整结果
        """
        # 记录性能
        self.performance_history.append(performance)
        
        # 检查是否需要调整
        adjustments = []
        for rule in self.adjustment_rules:
            if rule['condition'](performance):
                old_params = self.current_params.copy()
                new_params = rule['action'](self.current_params)
                
                if new_params != old_params:
                    self.current_params = new_params
                    adjustments.append({
                        'rule': rule['action'].__name__,
                        'old_params': old_params,
                        'new_params': new_params
                    })
        
        # 记录调整历史
        if adjustments:
            adjustment_record = {
                'timestamp': datetime.now(),
                'performance': performance,
                'adjustments': adjustments
            }
            self.adjustment_history.append(adjustment_record)
        
        return {
            'adjusted': len(adjustments) > 0,
            'adjustments': adjustments,
            'current_params': self.current_params
        }
    
    def _reduce_risk(self, params: Dict) -> Dict:
        """降低风险"""
        new_params = params.copy()
        new_params['position_size'] = max(0.1, params['position_size'] * 0.8)
        new_params['stop_loss'] = max(0.02, params['stop_loss'] * 0.9)
        return new_params
    
    def _tighten_entry(self, params: Dict) -> Dict:
        """收紧入场"""
        new_params = params.copy()
        new_params['entry_threshold'] = min(0.8, params['entry_threshold'] * 1.1)
        new_params['min_limit_ups'] = min(5, params['min_limit_ups'] + 1)
        return new_params
    
    def _reduce_position(self, params: Dict) -> Dict:
        """降低仓位"""
        new_params = params.copy()
        new_params['position_size'] = max(0.1, params['position_size'] * 0.7)
        return new_params
    
    def _loosen_exit(self, params: Dict) -> Dict:
        """放宽出场"""
        new_params = params.copy()
        new_params['take_profit'] = min(0.30, params['take_profit'] * 1.1)
        new_params['exit_threshold'] = max(0.1, params['exit_threshold'] * 0.9)
        return new_params
    
    def get_current_params(self) -> Dict[str, float]:
        """获取当前参数"""
        return self.current_params.copy()
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        if not self.performance_history:
            return {}
        
        recent_perf = list(self.performance_history)[-10:]
        
        return {
            'avg_sharpe': np.mean([p.get('sharpe_ratio', 0) for p in recent_perf]),
            'avg_win_rate': np.mean([p.get('win_rate', 0) for p in recent_perf]),
            'avg_return': np.mean([p.get('avg_return', 0) for p in recent_perf]),
            'avg_drawdown': np.mean([p.get('max_drawdown', 0) for p in recent_perf]),
            'n_adjustments': len(self.adjustment_history)
        }


class DragonAdaptiveParameterSystem:
    """龙头战法自适应参数系统（整合类）"""
    
    def __init__(self, db_path: str = 'data/dragon_adaptive_cache.db'):
        """
        初始化系统
        
        Args:
            db_path: 数据库路径
        """
        self.param_space = DragonParameterSpace()
        self.optimizer = BayesianOptimizer(self.param_space.get_bounds())
        self.evaluator = DragonBacktestEvaluator()
        self.adjuster = OnlineParameterAdjuster(
            self.param_space.get_base_params(),
            self.param_space.get_bounds()
        )
        
        self.db_path = db_path
        self._init_db()
        self.history = deque(maxlen=100)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                params TEXT,
                score REAL,
                performance TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adjustment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                old_params TEXT,
                new_params TEXT,
                performance TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def optimize(self, 
                historical_data: pd.DataFrame,
                n_iterations: int = 50) -> Dict:
        """
        优化参数
        
        Args:
            historical_data: 历史数据
            n_iterations: 迭代次数
            
        Returns:
            优化结果
        """
        best_score = -np.inf
        best_params = None
        
        for iteration in range(n_iterations):
            # 建议参数
            params = self.optimizer.suggest()
            
            # 评估参数
            evaluation = self.evaluator.evaluate(params, historical_data)
            
            # 观测结果
            self.optimizer.observe(params, evaluation['score'])
            
            # 记录最佳
            if evaluation['score'] > best_score:
                best_score = evaluation['score']
                best_params = params.copy()
            
            # 保存到数据库
            self._save_optimization(params, evaluation)
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'n_iterations': n_iterations,
            'summary': self.optimizer.get_observation_summary()
        }
    
    def online_adjust(self, performance: Dict) -> Dict:
        """
        在线调整参数
        
        Args:
            performance: 性能指标
            
        Returns:
            调整结果
        """
        adjustment = self.adjuster.adjust(performance)
        
        if adjustment['adjusted']:
            # 保存调整历史
            self._save_adjustment(adjustment)
        
        return adjustment
    
    def _save_optimization(self, params: Dict, evaluation: Dict):
        """保存优化记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO optimization_history (params, score, performance)
            VALUES (?, ?, ?)
        ''', (str(params), evaluation['score'], str(evaluation)))
        
        conn.commit()
        conn.close()
    
    def _save_adjustment(self, adjustment: Dict):
        """保存调整记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for adj in adjustment['adjustments']:
            cursor.execute('''
                INSERT INTO adjustment_history (old_params, new_params, performance)
                VALUES (?, ?, ?)
            ''', (str(adj['old_params']), str(adj['new_params']), str(adj.get('performance', {}))))
        
        conn.commit()
        conn.close()
    
    def get_current_params(self) -> Dict[str, float]:
        """获取当前参数"""
        return self.adjuster.get_current_params()
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        return self.adjuster.get_performance_summary()
    
    def get_optimization_history(self, limit: int = 50) -> List[Dict]:
        """获取优化历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, params, score, performance
            FROM optimization_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'params': eval(row[1]),
                'score': row[2],
                'performance': eval(row[3])
            }
            for row in rows
        ]


# 使用示例
if __name__ == '__main__':
    # 创建系统
    system = DragonAdaptiveParameterSystem()
    
    # 模拟历史数据
    dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
    historical_data = pd.DataFrame({
        'date': dates,
        'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
        'volume': np.linspace(1000000, 5000000, 100),
        'pct_chg': np.random.randn(100) * 0.05
    })
    
    # 优化参数
    print("开始优化参数...")
    optimization_result = system.optimize(historical_data, n_iterations=20)
    
    print("\n优化结果:")
    print(f"最佳评分: {optimization_result['best_score']:.4f}")
    print(f"最佳参数:")
    for key, value in optimization_result['best_params'].items():
        print(f"  {key}: {value:.4f}")
    
    # 在线调整
    print("\n在线调整...")
    performance = {
        'sharpe_ratio': 0.8,
        'win_rate': 0.35,
        'avg_return': 0.12,
        'max_drawdown': 0.18
    }
    
    adjustment = system.online_adjust(performance)
    
    print(f"调整状态: {'已调整' if adjustment['adjusted'] else '未调整'}")
    if adjustment['adjusted']:
        print("调整详情:")
        for adj in adjustment['adjustments']:
            print(f"  - {adj['rule']}")
    
    print(f"\n当前参数:")
    for key, value in system.get_current_params().items():
        print(f"  {key}: {value:.4f}")