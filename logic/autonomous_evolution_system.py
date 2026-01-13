"""
自主进化系统
基于遗传算法和自动优化的系统
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
import json
import random
from dataclasses import dataclass


@dataclass
class Individual:
    """个体（策略）"""
    genome: Dict[str, Any]
    fitness: float = 0.0
    age: int = 0


class GeneticAlgorithm:
    """遗传算法"""
    
    def __init__(self, population_size: int = 50, mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8, elitism_rate: float = 0.1):
        """
        初始化遗传算法
        
        Args:
            population_size: 种群大小
            mutation_rate: 变异率
            crossover_rate: 交叉率
            elitism_rate: 精英保留率
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_rate = elitism_rate
        self.population = []
        self.generation = 0
        self.best_individual = None
        self.history = []
    
    def initialize_population(self, genome_template: Dict[str, Any]):
        """
        初始化种群
        
        Args:
            genome_template: 基因模板（参数范围）
        """
        self.population = []
        
        for _ in range(self.population_size):
            genome = {}
            for key, value in genome_template.items():
                if isinstance(value, tuple):
                    # 参数范围
                    genome[key] = np.random.uniform(value[0], value[1])
                else:
                    # 固定值
                    genome[key] = value
            
            individual = Individual(genome=genome)
            self.population.append(individual)
    
    def evaluate_fitness(self, fitness_func: Callable[[Dict[str, Any]], float]):
        """
        评估适应度
        
        Args:
            fitness_func: 适应度函数
        """
        for individual in self.population:
            individual.fitness = fitness_func(individual.genome)
        
        # 更新最佳个体
        current_best = max(self.population, key=lambda x: x.fitness)
        if self.best_individual is None or current_best.fitness > self.best_individual.fitness:
            self.best_individual = current_best
    
    def selection(self, method: str = 'tournament') -> List[Individual]:
        """
        选择
        
        Args:
            method: 选择方法 ('tournament', 'roulette', 'rank')
            
        Returns:
            选中的个体列表
        """
        selected = []
        
        if method == 'tournament':
            # 锦标赛选择
            tournament_size = 3
            for _ in range(self.population_size):
                tournament = np.random.choice(self.population, tournament_size, replace=False)
                winner = max(tournament, key=lambda x: x.fitness)
                selected.append(winner)
        
        elif method == 'roulette':
            # 轮盘赌选择
            total_fitness = sum(ind.fitness for ind in self.population)
            if total_fitness > 0:
                probabilities = [ind.fitness / total_fitness for ind in self.population]
                selected = np.random.choice(self.population, self.population_size, 
                                           p=probabilities, replace=True)
            else:
                selected = np.random.choice(self.population, self.population_size, replace=True)
        
        elif method == 'rank':
            # 排序选择
            sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
            ranks = np.arange(1, len(sorted_pop) + 1)
            total_rank = sum(ranks)
            probabilities = ranks / total_rank
            selected = np.random.choice(sorted_pop, self.population_size, 
                                       p=probabilities, replace=True)
        
        else:
            raise ValueError(f"未知的选择方法: {method}")
        
        return selected
    
    def crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """
        交叉
        
        Args:
            parent1: 父代1
            parent2: 父代2
            
        Returns:
            子代1, 子代2
        """
        genome1 = {}
        genome2 = {}
        
        for key in parent1.genome.keys():
            if np.random.random() < 0.5:
                genome1[key] = parent1.genome[key]
                genome2[key] = parent2.genome[key]
            else:
                genome1[key] = parent2.genome[key]
                genome2[key] = parent1.genome[key]
        
        child1 = Individual(genome=genome1)
        child2 = Individual(genome=genome2)
        
        return child1, child2
    
    def mutate(self, individual: Individual, genome_template: Dict[str, Any]):
        """
        变异
        
        Args:
            individual: 个体
            genome_template: 基因模板
        """
        for key, value in individual.genome.items():
            if np.random.random() < self.mutation_rate:
                if isinstance(genome_template[key], tuple):
                    # 参数范围内的随机变异
                    min_val, max_val = genome_template[key]
                    individual.genome[key] = np.random.uniform(min_val, max_val)
                else:
                    # 高斯变异
                    individual.genome[key] += np.random.normal(0, 0.1 * abs(value))
    
    def evolve(self, fitness_func: Callable[[Dict[str, Any]], float],
               genome_template: Dict[str, Any], n_generations: int = 100) -> Dict[str, Any]:
        """
        进化
        
        Args:
            fitness_func: 适应度函数
            genome_template: 基因模板
            n_generations: 进化代数
            
        Returns:
            进化结果
        """
        # 初始化种群
        if not self.population:
            self.initialize_population(genome_template)
        
        # 评估初始适应度
        self.evaluate_fitness(fitness_func)
        
        for gen in range(n_generations):
            # 选择
            selected = self.selection()
            
            # 交叉
            new_population = []
            
            # 精英保留
            n_elites = int(self.population_size * self.elitism_rate)
            elites = sorted(self.population, key=lambda x: x.fitness, reverse=True)[:n_elites]
            new_population.extend(elites)
            
            # 生成新个体
            while len(new_population) < self.population_size:
                parent1, parent2 = np.random.choice(selected, 2, replace=False)
                
                if np.random.random() < self.crossover_rate:
                    child1, child2 = self.crossover(parent1, parent2)
                else:
                    child1 = Individual(genome=parent1.genome.copy())
                    child2 = Individual(genome=parent2.genome.copy())
                
                self.mutate(child1, genome_template)
                self.mutate(child2, genome_template)
                
                new_population.extend([child1, child2])
            
            # 截断到种群大小
            self.population = new_population[:self.population_size]
            
            # 评估适应度
            self.evaluate_fitness(fitness_func)
            
            # 记录历史
            avg_fitness = np.mean([ind.fitness for ind in self.population])
            best_fitness = self.best_individual.fitness
            
            self.history.append({
                'generation': self.generation,
                'avg_fitness': avg_fitness,
                'best_fitness': best_fitness,
                'best_genome': self.best_individual.genome,
                'timestamp': datetime.now().isoformat()
            })
            
            self.generation += 1
            
            if (gen + 1) % 10 == 0:
                print(f"Generation {gen + 1}/{n_generations}, "
                      f"Avg Fitness: {avg_fitness:.4f}, "
                      f"Best Fitness: {best_fitness:.4f}")
        
        return {
            'n_generations': self.generation,
            'best_fitness': self.best_individual.fitness,
            'best_genome': self.best_individual.genome,
            'history': self.history
        }


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, strategy_params: Dict[str, Any]):
        """
        初始化策略优化器
        
        Args:
            strategy_params: 策略参数
        """
        self.strategy_params = strategy_params
        self.performance_history = []
    
    def evaluate_strategy(self, params: Dict[str, Any], data: pd.DataFrame) -> Dict[str, float]:
        """
        评估策略
        
        Args:
            params: 策略参数
            data: 历史数据
            
        Returns:
            性能指标
        """
        # 简化的策略评估
        # 实际应该根据策略参数执行回测
        
        # 模拟收益率
        base_return = 0.1
        param_influence = sum(params.values()) * 0.01
        random_factor = np.random.normal(0, 0.05)
        
        total_return = base_return + param_influence + random_factor
        
        # 计算其他指标
        sharpe_ratio = total_return / 0.15  # 简化计算
        max_drawdown = abs(min(0, total_return * 0.5))
        win_rate = 0.5 + total_return * 0.2
        
        metrics = {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': min(max(win_rate, 1.0), 0.0)
        }
        
        return metrics
    
    def optimize(self, data: pd.DataFrame, n_generations: int = 50) -> Dict[str, Any]:
        """
        优化策略
        
        Args:
            data: 历史数据
            n_generations: 进化代数
            
        Returns:
            优化结果
        """
        # 定义基因模板
        genome_template = {}
        for key, value in self.strategy_params.items():
            if isinstance(value, tuple):
                genome_template[key] = value
            else:
                genome_template[key] = (value * 0.5, value * 1.5)
        
        # 定义适应度函数
        def fitness_func(genome: Dict[str, Any]) -> float:
            metrics = self.evaluate_strategy(genome, data)
            # 综合评分
            score = (metrics['total_return'] * 0.4 + 
                    metrics['sharpe_ratio'] * 0.3 - 
                    metrics['max_drawdown'] * 0.2 + 
                    metrics['win_rate'] * 0.1)
            return score
        
        # 运行遗传算法
        ga = GeneticAlgorithm(population_size=50, mutation_rate=0.1, 
                             crossover_rate=0.8, elitism_rate=0.1)
        
        result = ga.evolve(fitness_func, genome_template, n_generations)
        
        # 评估最佳策略
        best_metrics = self.evaluate_strategy(result['best_genome'], data)
        
        return {
            **result,
            'best_metrics': best_metrics
        }


class AutonomousEvolutionSystem:
    """自主进化系统"""
    
    def __init__(self):
        """初始化系统"""
        self.strategy_optimizers = {}
        self.evolution_history = []
        self.best_strategies = {}
    
    def register_strategy(self, strategy_id: str, strategy_params: Dict[str, Any]):
        """
        注册策略
        
        Args:
            strategy_id: 策略ID
            strategy_params: 策略参数
        """
        optimizer = StrategyOptimizer(strategy_params)
        self.strategy_optimizers[strategy_id] = optimizer
        self.best_strategies[strategy_id] = None
    
    def evolve_strategy(self, strategy_id: str, data: pd.DataFrame,
                       n_generations: int = 50) -> Dict[str, Any]:
        """
        进化策略
        
        Args:
            strategy_id: 策略ID
            data: 历史数据
            n_generations: 进化代数
            
        Returns:
            进化结果
        """
        if strategy_id not in self.strategy_optimizers:
            raise ValueError(f"策略不存在: {strategy_id}")
        
        optimizer = self.strategy_optimizers[strategy_id]
        result = optimizer.optimize(data, n_generations)
        
        # 保存最佳策略
        self.best_strategies[strategy_id] = result['best_genome']
        
        # 记录历史
        self.evolution_history.append({
            'strategy_id': strategy_id,
            'timestamp': datetime.now().isoformat(),
            'result': result
        })
        
        return result
    
    def evolve_all_strategies(self, data: pd.DataFrame,
                             n_generations: int = 50) -> Dict[str, Any]:
        """
        进化所有策略
        
        Args:
            data: 历史数据
            n_generations: 进化代数
            
        Returns:
            进化结果
        """
        results = {}
        
        for strategy_id in self.strategy_optimizers.keys():
            result = self.evolve_strategy(strategy_id, data, n_generations)
            results[strategy_id] = result
        
        return results
    
    def get_best_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取最佳策略"""
        return self.best_strategies.get(strategy_id)
    
    def get_evolution_history(self, strategy_id: str = None, 
                            limit: int = 100) -> List[Dict]:
        """
        获取进化历史
        
        Args:
            strategy_id: 策略ID（None表示全部）
            limit: 限制数量
            
        Returns:
            进化历史
        """
        history = self.evolution_history
        
        if strategy_id is not None:
            history = [h for h in history if h['strategy_id'] == strategy_id]
        
        return history[-limit:]
    
    def auto_tune(self, data: pd.DataFrame, performance_threshold: float = 0.1,
                 n_generations: int = 30) -> Dict[str, Any]:
        """
        自动调优
        
        Args:
            data: 历史数据
            performance_threshold: 性能阈值
            n_generations: 进化代数
            
        Returns:
            调优结果
        """
        results = {}
        improved_strategies = []
        
        for strategy_id, optimizer in self.strategy_optimizers.items():
            # 评估当前策略
            current_params = self.best_strategies.get(strategy_id, 
                                                      {k: v[0] if isinstance(v, tuple) else v 
                                                       for k, v in optimizer.strategy_params.items()})
            current_metrics = optimizer.evaluate_strategy(current_params, data)
            
            # 进化策略
            result = self.evolve_strategy(strategy_id, data, n_generations)
            best_metrics = result['best_metrics']
            
            # 检查是否改进
            improvement = best_metrics['total_return'] - current_metrics['total_return']
            
            results[strategy_id] = {
                'current_return': current_metrics['total_return'],
                'best_return': best_metrics['total_return'],
                'improvement': improvement,
                'improved': improvement > performance_threshold
            }
            
            if improvement > performance_threshold:
                improved_strategies.append(strategy_id)
        
        return {
            'results': results,
            'improved_strategies': improved_strategies,
            'n_improved': len(improved_strategies)
        }
    
    def save_system(self, filepath: str):
        """保存系统状态"""
        system_data = {
            'n_strategies': len(self.strategy_optimizers),
            'best_strategies': self.best_strategies,
            'evolution_history': self.evolution_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(system_data, f)
    
    def load_system(self, filepath: str):
        """加载系统状态"""
        with open(filepath, 'r') as f:
            system_data = json.load(f)
        
        self.best_strategies = system_data['best_strategies']
        self.evolution_history = system_data['evolution_history']
        
        return self