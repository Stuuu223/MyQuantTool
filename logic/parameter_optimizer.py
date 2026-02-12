"""
参数优化模块

根据回测结果优化参数阈值
"""

import numpy as np
from typing import Dict, List, Tuple
from logic.utils.logger import get_logger
from logic.backtest_engine import BacktestEngine

logger = get_logger(__name__)


class ParameterOptimizer:
    """
    参数优化器
    
    功能：
    1. 网格搜索优化参数
    2. 遗传算法优化参数
    3. 贝叶斯优化参数
    """
    
    def __init__(self):
        """初始化参数优化器"""
        self.best_params = None
        self.best_metrics = None
        self.optimization_history = []
    
    def grid_search(self, strategy_func, stock_codes: List[str], start_date: str, end_date: str,
                   param_grid: Dict, objective: str = 'sharpe_ratio') -> Dict:
        """
        网格搜索优化参数
        
        Args:
            strategy_func: 策略函数
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            param_grid: 参数网格
            objective: 优化目标（'sharpe_ratio', 'total_return', 'max_drawdown'）
        
        Returns:
            dict: 最佳参数和指标
        """
        logger.info(f"开始网格搜索优化，目标: {objective}")
        
        # 生成所有参数组合
        param_combinations = self._generate_param_combinations(param_grid)
        
        best_score = -np.inf
        best_params = None
        best_metrics = None
        
        for i, params in enumerate(param_combinations):
            logger.info(f"测试参数组合 {i+1}/{len(param_combinations)}: {params}")
            
            # 运行回测
            engine = BacktestEngine(initial_capital=100000)
            result = engine.run_backtest(
                strategy_func=strategy_func,
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                strategy_params=params
            )
            
            if not result['success']:
                continue
            
            metrics = result['metrics']
            
            # 计算得分
            if objective == 'sharpe_ratio':
                score = metrics['sharpe_ratio']
            elif objective == 'total_return':
                score = metrics['total_return']
            elif objective == 'max_drawdown':
                score = -metrics['max_drawdown']  # 最小化回撤
            else:
                score = metrics['sharpe_ratio']
            
            # 记录历史
            self.optimization_history.append({
                'params': params,
                'metrics': metrics,
                'score': score
            })
            
            # 更新最佳参数
            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics
                logger.info(f"找到更好的参数: {params}, 得分: {score:.4f}")
        
        self.best_params = best_params
        self.best_metrics = best_metrics
        
        logger.info(f"网格搜索完成，最佳得分: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_metrics': best_metrics,
            'optimization_history': self.optimization_history
        }
    
    def _generate_param_combinations(self, param_grid: Dict) -> List[Dict]:
        """
        生成所有参数组合
        
        Args:
            param_grid: 参数网格
        
        Returns:
            list: 参数组合列表
        """
        import itertools
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        combinations = list(itertools.product(*param_values))
        
        return [
            {name: value for name, value in zip(param_names, combo)}
            for combo in combinations
        ]
    
    def genetic_algorithm(self, strategy_func, stock_codes: List[str], start_date: str, end_date: str,
                         param_ranges: Dict, objective: str = 'sharpe_ratio',
                         population_size=20, generations=10, mutation_rate=0.1) -> Dict:
        """
        遗传算法优化参数
        
        Args:
            strategy_func: 策略函数
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            param_ranges: 参数范围
            objective: 优化目标
            population_size: 种群大小
            generations: 迭代代数
            mutation_rate: 变异率
        
        Returns:
            dict: 最佳参数和指标
        """
        logger.info(f"开始遗传算法优化，目标: {objective}")
        
        # 初始化种群
        population = self._initialize_population(param_ranges, population_size)
        
        best_individual = None
        best_score = -np.inf
        
        for generation in range(generations):
            logger.info(f"第 {generation+1}/{generations} 代")
            
            # 评估种群
            fitness_scores = []
            for individual in population:
                # 运行回测
                engine = BacktestEngine(initial_capital=100000)
                result = engine.run_backtest(
                    strategy_func=strategy_func,
                    stock_codes=stock_codes,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_params=individual
                )
                
                if result['success']:
                    metrics = result['metrics']
                    if objective == 'sharpe_ratio':
                        score = metrics['sharpe_ratio']
                    elif objective == 'total_return':
                        score = metrics['total_return']
                    elif objective == 'max_drawdown':
                        score = -metrics['max_drawdown']
                    else:
                        score = metrics['sharpe_ratio']
                else:
                    score = -np.inf
                
                fitness_scores.append(score)
                
                # 更新最佳个体
                if score > best_score:
                    best_score = score
                    best_individual = individual.copy()
                    logger.info(f"找到更好的个体，得分: {score:.4f}")
            
            # 选择
            selected = self._selection(population, fitness_scores, population_size // 2)
            
            # 交叉
            offspring = self._crossover(selected, population_size)
            
            # 变异
            population = self._mutation(offspring, param_ranges, mutation_rate)
        
        # 最终评估最佳个体
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run_backtest(
            strategy_func=strategy_func,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            strategy_params=best_individual
        )
        
        self.best_params = best_individual
        self.best_metrics = result['metrics'] if result['success'] else None
        
        logger.info(f"遗传算法完成，最佳得分: {best_score:.4f}")
        
        return {
            'best_params': best_individual,
            'best_metrics': self.best_metrics,
            'best_score': best_score
        }
    
    def _initialize_population(self, param_ranges: Dict, population_size: int) -> List[Dict]:
        """
        初始化种群
        
        Args:
            param_ranges: 参数范围
            population_size: 种群大小
        
        Returns:
            list: 种群
        """
        population = []
        
        for _ in range(population_size):
            individual = {}
            for param_name, (min_val, max_val) in param_ranges.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    individual[param_name] = np.random.randint(min_val, max_val + 1)
                else:
                    individual[param_name] = np.random.uniform(min_val, max_val)
            population.append(individual)
        
        return population
    
    def _selection(self, population: List[Dict], fitness_scores: List[float], num_selected: int) -> List[Dict]:
        """
        选择操作（轮盘赌选择）
        
        Args:
            population: 种群
            fitness_scores: 适应度得分
            num_selected: 选择数量
        
        Returns:
            list: 选中的个体
        """
        # 转换适应度为正数
        min_score = min(fitness_scores)
        adjusted_scores = []
        for s in fitness_scores:
            if np.isnan(s):
                adjusted_scores.append(0)
            elif np.isinf(s):
                adjusted_scores.append(0)
            else:
                adjusted_scores.append(s - min_score + 1)
        
        # 计算概率
        total = sum(adjusted_scores)
        if total == 0:
            # 如果所有适应度都是无效的，随机选择
            selected_indices = np.random.choice(
                len(population),
                size=num_selected,
                replace=True
            )
        else:
            probabilities = [s / total for s in adjusted_scores]
            # 轮盘赌选择
            selected_indices = np.random.choice(
                len(population),
                size=num_selected,
                replace=True,
                p=probabilities
            )
        
        return [population[i] for i in selected_indices]
    
    def _crossover(self, parents: List[Dict], population_size: int) -> List[Dict]:
        """
        交叉操作
        
        Args:
            parents: 父代
            population_size: 种群大小
        
        Returns:
            list: 子代
        """
        offspring = []
        
        while len(offspring) < population_size:
            # 随机选择两个父代
            parent1, parent2 = np.random.choice(parents, 2, replace=False)
            
            # 单点交叉
            child = {}
            for param_name in parent1.keys():
                if np.random.random() < 0.5:
                    child[param_name] = parent1[param_name]
                else:
                    child[param_name] = parent2[param_name]
            
            offspring.append(child)
        
        return offspring
    
    def _mutation(self, population: List[Dict], param_ranges: Dict, mutation_rate: float) -> List[Dict]:
        """
        变异操作
        
        Args:
            population: 种群
            param_ranges: 参数范围
            mutation_rate: 变异率
        
        Returns:
            list: 变异后的种群
        """
        for individual in population:
            for param_name, (min_val, max_val) in param_ranges.items():
                if np.random.random() < mutation_rate:
                    if isinstance(min_val, int) and isinstance(max_val, int):
                        individual[param_name] = np.random.randint(min_val, max_val + 1)
                    else:
                        individual[param_name] = np.random.uniform(min_val, max_val)
        
        return population
    
    def get_optimization_report(self) -> str:
        """
        获取优化报告
        
        Returns:
            str: 优化报告文本
        """
        report = "# 参数优化报告\n\n"
        
        if self.best_params:
            report += "## 最佳参数\n\n"
            for param_name, param_value in self.best_params.items():
                report += f"- {param_name}: {param_value}\n"
            
            report += "\n## 最佳指标\n\n"
            if self.best_metrics:
                for metric_name, metric_value in self.best_metrics.items():
                    report += f"- {metric_name}: {metric_value}\n"
        else:
            report += "尚未进行优化\n"
        
        if self.optimization_history:
            report += f"\n## 优化历史\n\n"
            report += f"总测试次数: {len(self.optimization_history)}\n\n"
            
            # 显示前10次最佳结果
            sorted_history = sorted(self.optimization_history, key=lambda x: x['score'], reverse=True)
            for i, record in enumerate(sorted_history[:10]):
                report += f"{i+1}. 得分: {record['score']:.4f}, 参数: {record['params']}\n"
        
        return report