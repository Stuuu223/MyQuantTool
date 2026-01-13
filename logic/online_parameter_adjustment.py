"""
在线参数调整系统
实现参数优化器、在线调整和性能追踪
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3
from collections import deque
import json


class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, strategy_name: str):
        """
        初始化参数优化器
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        self.base_params = self._get_base_params()
        self.param_bounds = self._get_param_bounds()
        self.optimization_history = deque(maxlen=100)
    
    def _get_base_params(self) -> Dict:
        """获取基础参数"""
        # 这里可以根据不同策略返回不同的基础参数
        return {
            'min_turnover': 5.0,
            'min_volume': 100000000,
            'min_limit_ups': 2,
            'max_days': 10,
            'stop_loss': 0.05,
            'take_profit': 0.15,
            'position_size': 0.5
        }
    
    def _get_param_bounds(self) -> Dict:
        """获取参数边界"""
        return {
            'min_turnover': (1.0, 20.0),
            'min_volume': (50000000, 500000000),
            'min_limit_ups': (1, 5),
            'max_days': (5, 20),
            'stop_loss': (0.02, 0.10),
            'take_profit': (0.10, 0.30),
            'position_size': (0.1, 0.9)
        }
    
    def optimize(self, 
                 historical_data: pd.DataFrame,
                 objective: str = 'sharpe_ratio',
                 n_iterations: int = 50) -> Dict:
        """
        优化参数
        
        Args:
            historical_data: 历史数据
            objective: 优化目标
            n_iterations: 迭代次数
            
        Returns:
            优化结果
        """
        best_params = self.base_params.copy()
        best_score = self._evaluate_params(best_params, historical_data, objective)
        
        # 网格搜索 + 随机搜索混合优化
        for iteration in range(n_iterations):
            # 生成新参数
            new_params = self._generate_params(best_params)
            
            # 评估参数
            score = self._evaluate_params(new_params, historical_data, objective)
            
            # 记录历史
            self.optimization_history.append({
                'iteration': iteration,
                'params': new_params,
                'score': score
            })
            
            # 更新最佳参数
            if score > best_score:
                best_score = score
                best_params = new_params
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'iterations': n_iterations,
            'improvement': best_score - self._evaluate_params(self.base_params, historical_data, objective)
        }
    
    def _generate_params(self, current_params: Dict) -> Dict:
        """生成新参数"""
        new_params = current_params.copy()
        
        # 随机调整每个参数
        for param_name in current_params:
            bounds = self.param_bounds.get(param_name, None)
            if bounds is None:
                continue
            
            lower, upper = bounds
            current_value = current_params[param_name]
            
            # 在当前值附近随机调整
            adjustment_range = (upper - lower) * 0.2
            new_value = current_value + np.random.uniform(-adjustment_range, adjustment_range)
            
            # 确保在边界内
            new_value = max(lower, min(upper, new_value))
            
            new_params[param_name] = new_value
        
        return new_params
    
    def _evaluate_params(self, 
                        params: Dict,
                        historical_data: pd.DataFrame,
                        objective: str) -> float:
        """
        评估参数
        
        Args:
            params: 参数字典
            historical_data: 历史数据
            objective: 优化目标
            
        Returns:
            评分
        """
        # 这里可以调用回测系统评估参数
        # 暂时返回模拟评分
        
        # 模拟回测
        n_trades = np.random.randint(10, 100)
        win_rate = np.random.uniform(0.3, 0.7)
        avg_return = np.random.uniform(-0.05, 0.15)
        max_drawdown = np.random.uniform(0.05, 0.20)
        
        # 计算夏普比率
        sharpe_ratio = (avg_return - 0.03) / (max_drawdown if max_drawdown > 0 else 0.01)
        
        if objective == 'sharpe_ratio':
            return sharpe_ratio
        elif objective == 'win_rate':
            return win_rate
        elif objective == 'return':
            return avg_return
        elif objective == 'max_drawdown':
            return -max_drawdown  # 负值，越小越好
        else:
            return sharpe_ratio
    
    def get_optimization_history(self) -> List[Dict]:
        """获取优化历史"""
        return list(self.optimization_history)


class PerformanceTracker:
    """性能追踪器"""
    
    def __init__(self, db_path: str = 'data/performance_cache.db'):
        """
        初始化性能追踪器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_db()
        self.metrics = deque(maxlen=1000)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                params TEXT,
                metrics TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def track(self, 
             strategy_name: str,
             params: Dict,
             metrics: Dict):
        """
        追踪性能
        
        Args:
            strategy_name: 策略名称
            params: 参数
            metrics: 性能指标
        """
        record = {
            'strategy_name': strategy_name,
            'timestamp': datetime.now(),
            'params': params,
            'metrics': metrics
        }
        
        self.metrics.append(record)
        self._save_to_db(record)
    
    def _save_to_db(self, record: Dict):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO performance_metrics (strategy_name, params, metrics)
            VALUES (?, ?, ?)
        ''', (
            record['strategy_name'],
            json.dumps(record['params']),
            json.dumps(record['metrics'])
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_performance(self, 
                              strategy_name: str,
                              limit: int = 100) -> List[Dict]:
        """
        获取最近性能
        
        Args:
            strategy_name: 策略名称
            limit: 返回数量
            
        Returns:
            性能记录列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, params, metrics
            FROM performance_metrics
            WHERE strategy_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (strategy_name, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'params': json.loads(row[1]),
                'metrics': json.loads(row[2])
            }
            for row in rows
        ]
    
    def calculate_avg_metrics(self, 
                             strategy_name: str,
                             window_size: int = 10) -> Dict:
        """
        计算平均性能指标
        
        Args:
            strategy_name: 策略名称
            window_size: 窗口大小
            
        Returns:
            平均指标
        """
        records = self.get_recent_performance(strategy_name, window_size)
        
        if not records:
            return {}
        
        # 计算平均值
        avg_metrics = {}
        for key in records[0]['metrics']:
            values = [r['metrics'][key] for r in records if key in r['metrics']]
            if values:
                avg_metrics[key] = np.mean(values)
        
        return avg_metrics
    
    def detect_performance_degradation(self, 
                                     strategy_name: str,
                                     threshold: float = 0.2) -> Optional[Dict]:
        """
        检测性能下降
        
        Args:
            strategy_name: 策略名称
            threshold: 下降阈值
            
        Returns:
            下降信息，如果没有下降则返回None
        """
        recent_records = self.get_recent_performance(strategy_name, 10)
        
        if len(recent_records) < 10:
            return None
        
        # 计算最近5次和前5次的平均性能
        recent_5 = recent_records[:5]
        previous_5 = recent_records[5:10]
        
        recent_avg = self._calculate_avg_return(recent_5)
        previous_avg = self._calculate_avg_return(previous_5)
        
        # 检查下降
        if recent_avg < previous_avg * (1 - threshold):
            return {
                'degradation': True,
                'recent_avg': recent_avg,
                'previous_avg': previous_avg,
                'drop_pct': (previous_avg - recent_avg) / previous_avg * 100,
                'message': f'性能下降 {((previous_avg - recent_avg) / previous_avg * 100):.2f}%'
            }
        
        return None
    
    def _calculate_avg_return(self, records: List[Dict]) -> float:
        """计算平均收益率"""
        returns = [r['metrics'].get('return', 0) for r in records]
        return np.mean(returns) if returns else 0


class OnlineParameterAdjuster:
    """在线参数调整器"""
    
    def __init__(self, strategy_name: str):
        """
        初始化在线参数调整器
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        self.params = self._get_base_params()
        self.optimizer = ParameterOptimizer(strategy_name)
        self.performance_tracker = PerformanceTracker()
        self.adjustment_rules = self._load_adjustment_rules()
        self.last_adjustment_time = datetime.now()
        self.adjustment_count = 0
    
    def _get_base_params(self) -> Dict:
        """获取基础参数"""
        return {
            'min_turnover': 5.0,
            'min_volume': 100000000,
            'min_limit_ups': 2,
            'max_days': 10,
            'stop_loss': 0.05,
            'take_profit': 0.15,
            'position_size': 0.5
        }
    
    def _load_adjustment_rules(self) -> List[Dict]:
        """加载调整规则"""
        return [
            {
                'condition': lambda metrics: metrics.get('sharpe_ratio', 0) < 1.0,
                'action': self._reduce_position_size
            },
            {
                'condition': lambda metrics: metrics.get('win_rate', 0) < 0.4,
                'action': self._tighten_stop_loss
            },
            {
                'condition': lambda metrics: metrics.get('max_drawdown', 0) > 0.15,
                'action': self._reduce_position_size
            },
            {
                'condition': lambda metrics: metrics.get('return', 0) > 0.2,
                'action': self._loosen_take_profit
            }
        ]
    
    def adjust_params(self, recent_performance: Dict) -> Dict:
        """
        根据近期表现调整参数
        
        Args:
            recent_performance: 近期性能指标
            
        Returns:
            调整结果
        """
        # 追踪性能
        self.performance_tracker.track(
            self.strategy_name,
            self.params,
            recent_performance
        )
        
        # 检查是否需要调整
        adjustment_made = False
        adjustments = []
        
        for rule in self.adjustment_rules:
            if rule['condition'](recent_performance):
                old_params = self.params.copy()
                new_params = rule['action'](self.params)
                
                if new_params != old_params:
                    self.params = new_params
                    adjustment_made = True
                    adjustments.append({
                        'rule': rule['action'].__name__,
                        'old_params': old_params,
                        'new_params': new_params
                    })
        
        if adjustment_made:
            self.adjustment_count += 1
            self.last_adjustment_time = datetime.now()
        
        return {
            'adjustment_made': adjustment_made,
            'adjustments': adjustments,
            'current_params': self.params,
            'adjustment_count': self.adjustment_count
        }
    
    def _reduce_position_size(self, params: Dict) -> Dict:
        """降低仓位"""
        new_params = params.copy()
        new_params['position_size'] = max(0.1, params['position_size'] * 0.8)
        return new_params
    
    def _tighten_stop_loss(self, params: Dict) -> Dict:
        """收紧止损"""
        new_params = params.copy()
        new_params['stop_loss'] = max(0.02, params['stop_loss'] * 0.8)
        return new_params
    
    def _loosen_take_profit(self, params: Dict) -> Dict:
        """放宽止盈"""
        new_params = params.copy()
        new_params['take_profit'] = min(0.30, params['take_profit'] * 1.2)
        return new_params
    
    def auto_optimize(self, 
                     historical_data: pd.DataFrame,
                     min_hours_between_adjustments: int = 24) -> Dict:
        """
        自动优化参数
        
        Args:
            historical_data: 历史数据
            min_hours_between_adjustments: 最小调整间隔（小时）
            
        Returns:
            优化结果
        """
        # 检查是否达到最小调整间隔
        time_since_last = (datetime.now() - self.last_adjustment_time).total_seconds() / 3600
        if time_since_last < min_hours_between_adjustments:
            return {
                'optimized': False,
                'reason': f'距离上次调整仅 {time_since_last:.1f} 小时，未达到最小间隔 {min_hours_between_adjustments} 小时'
            }
        
        # 检测性能下降
        degradation = self.performance_tracker.detect_performance_degradation(
            self.strategy_name
        )
        
        if degradation is None:
            return {
                'optimized': False,
                'reason': '性能稳定，无需优化'
            }
        
        # 优化参数
        optimization_result = self.optimizer.optimize(
            historical_data,
            objective='sharpe_ratio',
            n_iterations=50
        )
        
        # 应用优化后的参数
        old_params = self.params.copy()
        self.params = optimization_result['best_params']
        
        self.adjustment_count += 1
        self.last_adjustment_time = datetime.now()
        
        return {
            'optimized': True,
            'degradation': degradation,
            'old_params': old_params,
            'new_params': self.params,
            'improvement': optimization_result['improvement'],
            'adjustment_count': self.adjustment_count
        }
    
    def get_current_params(self) -> Dict:
        """获取当前参数"""
        return self.params.copy()
    
    def set_params(self, params: Dict):
        """
        设置参数
        
        Args:
            params: 参数字典
        """
        self.params = params.copy()
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        recent_records = self.performance_tracker.get_recent_performance(
            self.strategy_name,
            10
        )
        
        if not recent_records:
            return {
                'message': '暂无性能数据'
            }
        
        avg_metrics = self.performance_tracker.calculate_avg_metrics(
            self.strategy_name,
            10
        )
        
        degradation = self.performance_tracker.detect_performance_degradation(
            self.strategy_name
        )
        
        return {
            'avg_metrics': avg_metrics,
            'degradation': degradation,
            'adjustment_count': self.adjustment_count,
            'last_adjustment_time': self.last_adjustment_time,
            'current_params': self.params
        }


class OnlineParameterAdjustmentSystem:
    """在线参数调整系统（整合类）"""
    
    def __init__(self):
        """初始化系统"""
        self.strategies = {}  # {strategy_name: OnlineParameterAdjuster}
    
    def register_strategy(self, strategy_name: str, base_params: Optional[Dict] = None):
        """
        注册策略
        
        Args:
            strategy_name: 策略名称
            base_params: 基础参数
        """
        if strategy_name not in self.strategies:
            self.strategies[strategy_name] = OnlineParameterAdjuster(strategy_name)
            
            if base_params is not None:
                self.strategies[strategy_name].set_params(base_params)
    
    def adjust_strategy(self, 
                       strategy_name: str,
                       recent_performance: Dict) -> Dict:
        """
        调整策略参数
        
        Args:
            strategy_name: 策略名称
            recent_performance: 近期性能
            
        Returns:
            调整结果
        """
        if strategy_name not in self.strategies:
            return {
                'error': f'策略 {strategy_name} 未注册'
            }
        
        adjuster = self.strategies[strategy_name]
        return adjuster.adjust_params(recent_performance)
    
    def auto_optimize_strategy(self,
                               strategy_name: str,
                               historical_data: pd.DataFrame) -> Dict:
        """
        自动优化策略
        
        Args:
            strategy_name: 策略名称
            historical_data: 历史数据
            
        Returns:
            优化结果
        """
        if strategy_name not in self.strategies:
            return {
                'error': f'策略 {strategy_name} 未注册'
            }
        
        adjuster = self.strategies[strategy_name]
        return adjuster.auto_optimize(historical_data)
    
    def get_strategy_params(self, strategy_name: str) -> Optional[Dict]:
        """
        获取策略参数
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            参数字典
        """
        if strategy_name not in self.strategies:
            return None
        
        return self.strategies[strategy_name].get_current_params()
    
    def get_strategy_performance(self, strategy_name: str) -> Optional[Dict]:
        """
        获取策略性能
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            性能摘要
        """
        if strategy_name not in self.strategies:
            return None
        
        return self.strategies[strategy_name].get_performance_summary()
    
    def get_all_strategies(self) -> List[str]:
        """获取所有已注册策略"""
        return list(self.strategies.keys())


# 使用示例
if __name__ == '__main__':
    # 创建系统
    system = OnlineParameterAdjustmentSystem()
    
    # 注册策略
    system.register_strategy('midway_strategy')
    system.register_strategy('dragon_strategy')
    
    # 模拟近期性能
    recent_performance = {
        'sharpe_ratio': 0.8,
        'win_rate': 0.35,
        'max_drawdown': 0.18,
        'return': 0.15
    }
    
    # 调整参数
    result = system.adjust_strategy('midway_strategy', recent_performance)
    
    print("参数调整结果:")
    print(f"调整状态: {'已调整' if result['adjustment_made'] else '未调整'}")
    if result['adjustment_made']:
        print(f"调整次数: {result['adjustment_count']}")
        print("调整详情:")
        for adj in result['adjustments']:
            print(f"  - {adj['rule']}")
    
    print("\n当前参数:")
    for key, value in result['current_params'].items():
        print(f"  {key}: {value}")
    
    # 获取性能摘要
    performance = system.get_strategy_performance('midway_strategy')
    print("\n性能摘要:")
    if 'avg_metrics' in performance:
        print("平均指标:")
        for key, value in performance['avg_metrics'].items():
            print(f"  {key}: {value:.4f}")
    
    if performance.get('degradation'):
        print(f"\n性能下降: {performance['degradation']['message']}")
    
    print(f"\n调整次数: {performance['adjustment_count']}")
    print(f"上次调整时间: {performance['last_adjustment_time']}")