import numpy as np
import pandas as pd
from typing import Dict, List, Any, Callable, Tuple
from itertools import product
import random
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy.optimize import minimize, differential_evolution
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("警告: 未安装scipy，部分优化功能将受限")

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("警告: 未安装optuna，高级优化功能将受限")


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    best_params: Dict[str, Any]
    best_value: float
    optimization_trace: List[Tuple[Dict[str, Any], float]]  # (参数, 目标值) 的历史记录
    optimization_method: str
    execution_time: float


class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self):
        self.optimization_history = []
    
    def grid_search(self, 
                   objective_function: Callable[[Dict[str, Any]], float], 
                   param_grid: Dict[str, List[Any]], 
                   maximize: bool = True) -> OptimizationResult:
        """
        网格搜索优化
        
        Args:
            objective_function: 目标函数，接受参数字典返回数值
            param_grid: 参数网格，格式为 {param_name: [possible_values]}
            maximize: 是否最大化目标函数
        
        Returns:
            OptimizationResult: 优化结果
        """
        import time
        start_time = time.time()
        
        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        combinations = list(product(*param_values))
        best_params = None
        best_value = float('-inf') if maximize else float('inf')
        optimization_trace = []
        
        print(f"开始网格搜索，共 {len(combinations)} 种参数组合")
        
        for i, values in enumerate(combinations):
            params = dict(zip(param_names, values))
            
            try:
                value = objective_function(params)
                
                if maximize and value > best_value:
                    best_value = value
                    best_params = params.copy()
                elif not maximize and value < best_value:
                    best_value = value
                    best_params = params.copy()
                
                optimization_trace.append((params.copy(), value))
                
                if (i + 1) % 10 == 0:
                    print(f"已完成 {i + 1}/{len(combinations)} 种组合")
                    
            except Exception as e:
                print(f"参数组合 {params} 评估失败: {e}")
                continue
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            optimization_trace=optimization_trace,
            optimization_method='Grid Search',
            execution_time=execution_time
        )
    
    def random_search(self, 
                     objective_function: Callable[[Dict[str, Any]], float], 
                     param_space: Dict[str, Tuple[Any, Any, str]],  # (min, max, type)
                     n_trials: int = 100,
                     maximize: bool = True) -> OptimizationResult:
        """
        随机搜索优化
        
        Args:
            objective_function: 目标函数
            param_space: 参数空间，格式为 {param_name: (min_val, max_val, type)}
            n_trials: 试验次数
            maximize: 是否最大化目标函数
        
        Returns:
            OptimizationResult: 优化结果
        """
        import time
        start_time = time.time()
        
        best_params = None
        best_value = float('-inf') if maximize else float('inf')
        optimization_trace = []
        
        print(f"开始随机搜索，共 {n_trials} 次试验")
        
        for i in range(n_trials):
            # 随机生成参数
            params = {}
            for param_name, (min_val, max_val, param_type) in param_space.items():
                if param_type == 'int':
                    value = random.randint(min_val, max_val)
                elif param_type == 'float':
                    value = random.uniform(min_val, max_val)
                elif param_type == 'choice':
                    # 假设min_val是可选值列表
                    value = random.choice(min_val)
                else:
                    raise ValueError(f"不支持的参数类型: {param_type}")
                
                params[param_name] = value
            
            try:
                value = objective_function(params)
                
                if maximize and value > best_value:
                    best_value = value
                    best_params = params.copy()
                elif not maximize and value < best_value:
                    best_value = value
                    best_params = params.copy()
                
                optimization_trace.append((params.copy(), value))
                
                if (i + 1) % 20 == 0:
                    print(f"已完成 {i + 1}/{n_trials} 次试验")
                    
            except Exception as e:
                print(f"参数组合 {params} 评估失败: {e}")
                continue
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            optimization_trace=optimization_trace,
            optimization_method='Random Search',
            execution_time=execution_time
        )
    
    def differential_evolution_optimization(self, 
                                          objective_function: Callable[[Dict[str, Any]], float], 
                                          param_space: Dict[str, Tuple[float, float]],  # (min, max)
                                          maximize: bool = True,
                                          popsize: int = 15,
                                          max_iter: int = 1000) -> OptimizationResult:
        """
        差分进化优化（需要scipy）
        
        Args:
            objective_function: 目标函数
            param_space: 参数空间，格式为 {param_name: (min_val, max_val)}
            maximize: 是否最大化目标函数
            popsize: 种群大小
            max_iter: 最大迭代次数
            
        Returns:
            OptimizationResult: 优化结果
        """
        if not SCIPY_AVAILABLE:
            raise ImportError("需要安装scipy以使用差分进化优化")
        
        import time
        start_time = time.time()
        
        # 将参数空间转换为差分进化所需的格式
        bounds = list(param_space.values())
        param_names = list(param_space.keys())
        
        # 定义优化目标函数
        def opt_func(params_array):
            # 将数组参数转换为字典
            params = {name: val for name, val in zip(param_names, params_array)}
            
            try:
                value = objective_function(params)
                # 最小化算法，如果是最大化则取负值
                return -value if maximize else value
            except Exception:
                # 如果评估失败，返回一个较差的值
                return float('inf') if not maximize else float('-inf')
        
        # 执行差分进化优化
        result = differential_evolution(
            opt_func,
            bounds,
            maxiter=max_iter,
            popsize=popsize,
            seed=42,
            disp=True
        )
        
        # 获取最优参数
        best_params = {name: val for name, val in zip(param_names, result.x)}
        
        # 计算最优值
        final_value = objective_function(best_params)
        if maximize:
            final_value = -result.fun  # 转换回原始最大化问题的值
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_value=final_value,
            optimization_trace=[(best_params, final_value)],  # 差分进化返回最终结果
            optimization_method='Differential Evolution',
            execution_time=execution_time
        )
    
    def genetic_algorithm_optimization(self, 
                                     objective_function: Callable[[Dict[str, Any]], float], 
                                     param_space: Dict[str, Tuple[Any, Any, str]],  # (min, max, type)
                                     population_size: int = 50,
                                     generations: int = 100,
                                     mutation_rate: float = 0.1,
                                     crossover_rate: float = 0.8,
                                     maximize: bool = True) -> OptimizationResult:
        """
        遗传算法优化
        
        Args:
            objective_function: 目标函数
            param_space: 参数空间
            population_size: 种群大小
            generations: 代数
            mutation_rate: 变异率
            crossover_rate: 交叉率
            maximize: 是否最大化目标函数
            
        Returns:
            OptimizationResult: 优化结果
        """
        import time
        start_time = time.time()
        
        def random_individual():
            """随机生成个体（参数组合）"""
            individual = {}
            for param_name, (min_val, max_val, param_type) in param_space.items():
                if param_type == 'int':
                    value = random.randint(min_val, max_val)
                elif param_type == 'float':
                    value = random.uniform(min_val, max_val)
                else:
                    raise ValueError(f"不支持的参数类型: {param_type}")
                individual[param_name] = value
            return individual
        
        def evaluate_fitness(individual):
            """评估个体适应度"""
            try:
                value = objective_function(individual)
                return value if maximize else -value  # 最大化问题直接返回，最小化问题取负值
            except Exception:
                return float('-inf') if maximize else float('-inf')
        
        def select_parent(population, fitnesses):
            """选择父代（轮盘赌选择）"""
            total_fitness = sum(fitnesses)
            if total_fitness <= 0:
                # 如果所有适应度都非正，随机选择
                return random.choice(population)
            
            pick = random.uniform(0, total_fitness)
            current = 0
            for individual, fitness in zip(population, fitnesses):
                current += fitness
                if current >= pick:
                    return individual
            return population[-1]  # 保险起见返回最后一个
        
        def crossover(parent1, parent2):
            """交叉操作"""
            if random.random() > crossover_rate:
                return parent1.copy()
            
            child = {}
            for param_name in param_space.keys():
                if random.random() < 0.5:
                    child[param_name] = parent1[param_name]
                else:
                    child[param_name] = parent2[param_name]
            return child
        
        def mutate(individual):
            """变异操作"""
            mutated = individual.copy()
            for param_name, (min_val, max_val, param_type) in param_space.items():
                if random.random() < mutation_rate:
                    if param_type == 'int':
                        # 小幅度变异
                        current_val = mutated[param_name]
                        # 在一定范围内随机变化
                        new_val = current_val + random.randint(-abs(max_val-min_val)//10, abs(max_val-min_val)//10)
                        new_val = max(min_val, min(new_val, max_val))
                        mutated[param_name] = new_val
                    elif param_type == 'float':
                        current_val = mutated[param_name]
                        # 按比例变异
                        range_val = max_val - min_val
                        mutation_delta = random.uniform(-0.1 * range_val, 0.1 * range_val)
                        new_val = current_val + mutation_delta
                        new_val = max(min_val, min(new_val, max_val))
                        mutated[param_name] = new_val
            return mutated
        
        # 初始化种群
        population = [random_individual() for _ in range(population_size)]
        optimization_trace = []
        
        print(f"开始遗传算法优化，种群大小: {population_size}，代数: {generations}")
        
        for generation in range(generations):
            # 计算适应度
            fitnesses = [evaluate_fitness(individual) for individual in population]
            
            # 记录当前最优个体
            best_idx = np.argmax(fitnesses) if maximize else np.argmin(fitnesses) if not maximize else np.argmax(fitnesses)
            best_individual = population[best_idx]
            best_fitness = fitnesses[best_idx]
            
            optimization_trace.append((best_individual.copy(), best_fitness if maximize else -best_fitness))
            
            if generation % 20 == 0:
                print(f"第 {generation} 代，当前最优适应度: {best_fitness}")
            
            # 生成新种群
            new_population = []
            
            # 精英保留
            elite_count = max(1, population_size // 10)
            elite_indices = np.argsort(fitnesses)[-elite_count:] if maximize else np.argsort(fitnesses)[:elite_count]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # 通过选择、交叉、变异生成剩余个体
            while len(new_population) < population_size:
                parent1 = select_parent(population, fitnesses)
                parent2 = select_parent(population, fitnesses)
                child = crossover(parent1, parent2)
                child = mutate(child)
                new_population.append(child)
            
            population = new_population
        
        # 最终评估整个种群，找到最优个体
        final_fitnesses = [evaluate_fitness(individual) for individual in population]
        final_best_idx = np.argmax(final_fitnesses) if maximize else np.argmin(final_fitnesses) if not maximize else np.argmax(final_fitnesses)
        best_params = population[final_best_idx]
        best_value = final_fitnesses[final_best_idx] if maximize else -final_fitnesses[final_best_idx]
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            optimization_trace=optimization_trace,
            optimization_method='Genetic Algorithm',
            execution_time=execution_time
        )
    
    def bayesian_optimization(self, 
                            objective_function: Callable[[Dict[str, Any]], float], 
                            param_space: Dict[str, Tuple[float, float]],  # (min, max)
                            n_trials: int = 100,
                            maximize: bool = True) -> OptimizationResult:
        """
        贝叶斯优化（需要optuna）
        
        Args:
            objective_function: 目标函数
            param_space: 参数空间
            n_trials: 试验次数
            maximize: 是否最大化目标函数
        
        Returns:
            OptimizationResult: 优化结果
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("需要安装optuna以使用贝叶斯优化")
        
        import time
        start_time = time.time()
        
        optimization_trace = []
        
        def optuna_objective(trial):
            # 根据参数空间建议参数
            params = {}
            for param_name, (min_val, max_val) in param_space.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = trial.suggest_int(param_name, min_val, max_val)
                else:
                    params[param_name] = trial.suggest_float(param_name, float(min_val), float(max_val))
            
            try:
                value = objective_function(params)
                optimization_trace.append((params.copy(), value))
                return value if maximize else -value  # Optuna 默认最小化
            except Exception as e:
                print(f"参数 {params} 评估失败: {e}")
                return float('inf') if maximize else float('-inf')  # 返回一个差值
        
        # 创建优化研究
        study = optuna.create_study(direction='maximize' if maximize else 'minimize')
        study.optimize(optuna_objective, n_trials=n_trials)
        
        # 获取最佳参数和值
        best_params = study.best_params
        best_value = study.best_value
        if not maximize:  # 如果原问题是最大化，Optuna最小化的是负值
            best_value = -best_value
        
        execution_time = time.time() - start_time
        
        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            optimization_trace=optimization_trace,
            optimization_method='Bayesian Optimization (Optuna)',
            execution_time=execution_time
        )


class BacktestObjectiveFunction:
    """用于回测的优化目标函数生成器"""
    
    def __init__(self, strategy_factory, backtest_engine, data, target_metric='sharpe_ratio'):
        self.strategy_factory = strategy_factory
        self.backtest_engine = backtest_engine
        self.data = data
        self.target_metric = target_metric
    
    def create_objective_function(self, template_id: str):
        """创建目标函数"""
        def objective(params: Dict[str, Any]) -> float:
            try:
                # 创建策略
                strategy = self.strategy_factory.create_strategy_from_template(template_id, params)
                
                # 运行回测
                result = self.backtest_engine.run_backtest(strategy, self.data)
                
                # 返回目标指标值
                metrics = result.metrics
                return metrics.get(self.target_metric, 0.0)
            except Exception as e:
                # 如果回测失败，返回一个较差的值
                print(f"回测失败: {e}")
                return float('-inf') if self.target_metric in ['sharpe_ratio', 'total_return', 'win_rate'] else float('inf')
        
        return objective


# 使用示例
def demo_parameter_optimization():
    """演示参数优化"""
    print("=== 参数优化演示 ===")
    
    # 创建优化器
    optimizer = ParameterOptimizer()
    
    # 示例目标函数：简单的二次函数
    def sample_objective(params):
        x = params.get('x', 0)
        y = params.get('y', 0)
        # 最大化 -(x-3)^2 -(y-2)^2 + 10（最大值在x=3, y=2处）
        return -(x-3)**2 -(y-2)**2 + 10
    
    # 网格搜索
    print("\n1. 网格搜索:")
    param_grid = {
        'x': [1, 2, 3, 4, 5],
        'y': [1, 2, 3, 4]
    }
    grid_result = optimizer.grid_search(sample_objective, param_grid, maximize=True)
    print(f"最佳参数: {grid_result.best_params}")
    print(f"最佳值: {grid_result.best_value:.4f}")
    print(f"执行时间: {grid_result.execution_time:.4f}秒")
    
    # 随机搜索
    print("\n2. 随机搜索:")
    param_space = {
        'x': (1, 5, 'float'),  # (min, max, type)
        'y': (1, 5, 'float')
    }
    random_result = optimizer.random_search(sample_objective, param_space, n_trials=50, maximize=True)
    print(f"最佳参数: {random_result.best_params}")
    print(f"最佳值: {random_result.best_value:.4f}")
    
    # 遗传算法（如果scipy可用）
    if SCIPY_AVAILABLE:
        print("\n3. 差分进化优化:")
        bounds = {
            'x': (1, 5),
            'y': (1, 5)
        }
        try:
            de_result = optimizer.differential_evolution_optimization(
                sample_objective, bounds, maximize=True, max_iter=100
            )
            print(f"最佳参数: {de_result.best_params}")
            print(f"最佳值: {de_result.best_value:.4f}")
        except Exception as e:
            print(f"差分进化优化失败: {e}")
    
    # 遗传算法
    print("\n4. 遗传算法优化:")
    ga_param_space = {
        'x': (1, 5, 'float'),
        'y': (1, 5, 'float')
    }
    ga_result = optimizer.genetic_algorithm_optimization(
        sample_objective, ga_param_space, 
        population_size=30, generations=50, maximize=True
    )
    print(f"最佳参数: {ga_result.best_params}")
    print(f"最佳值: {ga_result.best_value:.4f}")
    
    # 如果optuna可用，演示贝叶斯优化
    if OPTUNA_AVAILABLE:
        print("\n5. 贝叶斯优化:")
        bayes_bounds = {
            'x': (1.0, 5.0),
            'y': (1.0, 5.0)
        }
        try:
            bayes_result = optimizer.bayesian_optimization(
                sample_objective, bayes_bounds, n_trials=50, maximize=True
            )
            print(f"最佳参数: {bayes_result.best_params}")
            print(f"最佳值: {bayes_result.best_value:.4f}")
        except Exception as e:
            print(f"贝叶斯优化失败: {e}")


if __name__ == "__main__":
    demo_parameter_optimization()
