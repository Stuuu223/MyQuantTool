"""
策略工厂模块

功能：
- 策略模板化系统
- 参数优化与网格搜索
- 策略回测对比
"""

import json
import uuid
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import inspect
import copy

from logic.backtest_engine import BacktestEngine, BacktestMetrics
from logic.parameter_optimizer import ParameterOptimizer  # 假设已存在参数优化器


@dataclass
class StrategyParameter:
    """策略参数定义"""
    name: str
    type: str  # 'int', 'float', 'str', 'bool', 'list', 'dict'
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    description: str = ""


@dataclass
class StrategyTemplate:
    """策略模板定义"""
    template_id: str
    name: str
    description: str
    parameters: List[StrategyParameter]
    implementation: str  # 策略实现代码，可以是类名或函数名
    category: str  # 策略类别，如 'trend_following', 'mean_reversion', 'arbitrage' 等
    tags: List[str]  # 策略标签
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class Strategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.name = name
        self.parameters = parameters
        self.indicators = {}
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        pass
    
    @abstractmethod
    def get_indicators(self) -> Dict[str, Any]:
        """获取策略使用的指标"""
        pass


class MovingAverageCrossoverStrategy(Strategy):
    """移动平均线交叉策略"""
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__("MovingAverageCrossover", parameters)
        self.short_window = parameters.get('short_window', 10)
        self.long_window = parameters.get('long_window', 30)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        # 计算移动平均线
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        # 生成交易信号
        df['signal'] = 0
        df['signal'][self.short_window:] = np.where(
            df['short_ma'][self.short_window:] > df['long_ma'][self.short_window:], 1, 0
        )
        
        # 生成实际交易信号（1为买入，-1为卖出）
        df['position'] = df['signal'].diff()
        
        # 记录指标
        self.indicators = {
            'short_ma': df['short_ma'],
            'long_ma': df['long_ma']
        }
        
        return df[['signal', 'position'] + list(self.indicators.keys())]
    
    def get_indicators(self) -> Dict[str, Any]:
        """获取策略使用的指标"""
        return self.indicators


class RSIReversionStrategy(Strategy):
    """RSI均值回归策略"""
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__("RSIReversion", parameters)
        self.rsi_period = parameters.get('rsi_period', 14)
        self.overbought_level = parameters.get('overbought_level', 70)
        self.oversold_level = parameters.get('oversold_level', 30)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 生成交易信号
        df['signal'] = 0
        df.loc[df['rsi'] < self.oversold_level, 'signal'] = 1  # 超卖，买入
        df.loc[df['rsi'] > self.overbought_level, 'signal'] = 0  # 超买，卖出
        
        # 生成实际交易信号
        df['position'] = df['signal'].diff()
        
        # 记录指标
        self.indicators = {
            'rsi': df['rsi']
        }
        
        return df[['signal', 'position'] + list(self.indicators.keys())]
    
    def get_indicators(self) -> Dict[str, Any]:
        """获取策略使用的指标"""
        return self.indicators


class BollingerBandsStrategy(Strategy):
    """布林带策略"""
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__("BollingerBands", parameters)
        self.period = parameters.get('period', 20)
        self.std_dev = parameters.get('std_dev', 2.0)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        # 计算布林带
        df['middle_band'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper_band'] = df['middle_band'] + (df['std'] * self.std_dev)
        df['lower_band'] = df['middle_band'] - (df['std'] * self.std_dev)
        
        # 生成交易信号
        df['signal'] = 0
        df.loc[df['close'] <= df['lower_band'], 'signal'] = 1  # 价格触及下轨，买入
        df.loc[df['close'] >= df['upper_band'], 'signal'] = 0  # 价格触及上轨，卖出
        
        # 生成实际交易信号
        df['position'] = df['signal'].diff()
        
        # 记录指标
        self.indicators = {
            'middle_band': df['middle_band'],
            'upper_band': df['upper_band'],
            'lower_band': df['lower_band']
        }
        
        return df[['signal', 'position'] + list(self.indicators.keys())]
    
    def get_indicators(self) -> Dict[str, Any]:
        """获取策略使用的指标"""
        return self.indicators


class StrategyFactory:
    """策略工厂类"""
    
    def __init__(self):
        self.templates: Dict[str, StrategyTemplate] = {}
        self.registered_strategies: Dict[str, Callable] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy_template(
            StrategyTemplate(
                template_id="ma_crossover",
                name="移动平均线交叉策略",
                description="通过短期和长期移动平均线交叉产生交易信号",
                parameters=[
                    StrategyParameter("short_window", "int", 10, 5, 50, "短期移动平均线窗口"),
                    StrategyParameter("long_window", "int", 30, 10, 200, "长期移动平均线窗口")
                ],
                implementation="MovingAverageCrossoverStrategy",
                category="trend_following",
                tags=["moving_average", "trend", "simple"]
            )
        )
        
        self.register_strategy_template(
            StrategyTemplate(
                template_id="rsi_reversion",
                name="RSI均值回归策略",
                description="利用RSI指标识别超买超卖状态进行均值回归交易",
                parameters=[
                    StrategyParameter("rsi_period", "int", 14, 5, 30, "RSI计算周期"),
                    StrategyParameter("overbought_level", "int", 70, 50, 95, "超买水平"),
                    StrategyParameter("oversold_level", "int", 30, 5, 50, "超卖水平")
                ],
                implementation="RSIReversionStrategy",
                category="mean_reversion",
                tags=["rsi", "reversion", "oscillator"]
            )
        )
        
        self.register_strategy_template(
            StrategyTemplate(
                template_id="bollinger_bands",
                name="布林带策略",
                description="利用布林带的上下轨进行交易决策",
                parameters=[
                    StrategyParameter("period", "int", 20, 10, 50, "布林带周期"),
                    StrategyParameter("std_dev", "float", 2.0, 1.0, 3.0, "标准差倍数")
                ],
                implementation="BollingerBandsStrategy",
                category="mean_reversion",
                tags=["bollinger", "bands", "volatility"]
            )
        )
        
        # 注册策略类
        self.register_strategy_class("MovingAverageCrossoverStrategy", MovingAverageCrossoverStrategy)
        self.register_strategy_class("RSIReversionStrategy", RSIReversionStrategy)
        self.register_strategy_class("BollingerBandsStrategy", BollingerBandsStrategy)
    
    def register_strategy_template(self, template: StrategyTemplate):
        """注册策略模板"""
        self.templates[template.template_id] = template
    
    def register_strategy_class(self, class_name: str, strategy_class: Callable):
        """注册策略类"""
        self.registered_strategies[class_name] = strategy_class
    
    def create_strategy_from_template(self, template_id: str, parameters: Dict[str, Any]) -> Strategy:
        """根据模板创建策略实例"""
        if template_id not in self.templates:
            raise ValueError(f"模板不存在: {template_id}")
        
        template = self.templates[template_id]
        
        # 验证参数
        validated_params = self._validate_parameters(parameters, template.parameters)
        
        # 创建策略实例
        if template.implementation not in self.registered_strategies:
            raise ValueError(f"未注册的策略类: {template.implementation}")
        
        strategy_class = self.registered_strategies[template.implementation]
        return strategy_class(validated_params)
    
    def _validate_parameters(self, params: Dict[str, Any], template_params: List[StrategyParameter]) -> Dict[str, Any]:
        """验证参数"""
        validated = {}
        
        for template_param in template_params:
            if template_param.name in params:
                value = params[template_param.name]
            else:
                # 使用默认值
                value = template_param.default_value
            
            # 类型检查和范围检查
            if template_param.type == "int" and isinstance(value, (int, float)):
                value = int(value)
                if template_param.min_value is not None and value < template_param.min_value:
                    value = template_param.min_value
                if template_param.max_value is not None and value > template_param.max_value:
                    value = template_param.max_value
            elif template_param.type == "float" and isinstance(value, (int, float)):
                value = float(value)
                if template_param.min_value is not None and value < template_param.min_value:
                    value = template_param.min_value
                if template_param.max_value is not None and value > template_param.max_value:
                    value = template_param.max_value
            elif template_param.type == "str" and isinstance(value, str):
                pass  # 字符串无需额外验证
            elif template_param.type == "bool" and isinstance(value, bool):
                pass  # 布尔值无需额外验证
            else:
                raise ValueError(f"参数类型不匹配: {template_param.name}")
            
            validated[template_param.name] = value
        
        return validated
    
    def get_template_by_id(self, template_id: str) -> Optional[StrategyTemplate]:
        """根据ID获取策略模板"""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[StrategyTemplate]:
        """根据类别获取策略模板"""
        return [template for template in self.templates.values() if template.category == category]
    
    def get_templates_by_tags(self, tags: List[str]) -> List[StrategyTemplate]:
        """根据标签获取策略模板"""
        return [template for template in self.templates.values() 
                if any(tag in template.tags for tag in tags)]
    
    def list_all_templates(self) -> List[StrategyTemplate]:
        """列出所有策略模板"""
        return list(self.templates.values())


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, backtest_engine: BacktestEngine):
        self.backtest_engine = backtest_engine
        self.parameter_optimizer = ParameterOptimizer()
    
    def optimize_strategy(self, 
                         strategy_template_id: str, 
                         data: pd.DataFrame, 
                         parameter_ranges: Dict[str, List[Any]], 
                         optimization_metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """
        优化策略参数
        
        Args:
            strategy_template_id: 策略模板ID
            data: 回测数据
            parameter_ranges: 参数范围，格式为 {param_name: [possible_values]}
            optimization_metric: 优化指标
            
        Returns:
            优化结果
        """
        # 获取策略工厂实例
        factory = StrategyFactory()
        
        # 创建网格搜索参数组合
        param_combinations = self._generate_param_combinations(parameter_ranges)
        
        best_result = None
        best_params = None
        best_metric_value = float('-inf')
        
        print(f"开始优化策略 {strategy_template_id}，共 {len(param_combinations)} 种参数组合")
        
        for i, params in enumerate(param_combinations):
            print(f"测试参数组合 {i+1}/{len(param_combinations)}: {params}")
            
            try:
                # 创建策略实例
                strategy = factory.create_strategy_from_template(strategy_template_id, params)
                
                # 运行回测
                result = self.backtest_engine.run_backtest(strategy, data)
                
                # 获取优化指标值
                metric_value = self._get_metric_value(result, optimization_metric)
                
                # 更新最佳结果
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_params = params
                    best_result = result
                    
            except Exception as e:
                print(f"参数组合 {params} 测试失败: {e}")
                continue
        
        return {
            'best_params': best_params,
            'best_metric_value': best_metric_value,
            'best_result': best_result,
            'optimization_metric': optimization_metric
        }
    
    def _generate_param_combinations(self, parameter_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """生成参数组合"""
        from itertools import product
        
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        combinations = []
        for values in product(*param_values):
            combination = dict(zip(param_names, values))
            combinations.append(combination)
        
        return combinations
    
    def _get_metric_value(self, backtest_result: BacktestMetrics, metric_name: str) -> float:
        """获取回测结果中的指标值"""
        if hasattr(backtest_result, metric_name):
            return getattr(backtest_result, metric_name)
        else:
            # 如果找不到指定指标，返回默认值
            return 0.0


class StrategyComparison:
    """策略对比器"""
    
    def __init__(self):
        self.comparison_results = []
    
    def compare_strategies(self, 
                          strategies: List[Strategy], 
                          data: pd.DataFrame, 
                          backtest_engine: BacktestEngine) -> pd.DataFrame:
        """
        对比多个策略的表现
        
        Args:
            strategies: 策略列表
            data: 回测数据
            backtest_engine: 回测引擎
            
        Returns:
            对比结果DataFrame
        """
        comparison_data = []
        
        for i, strategy in enumerate(strategies):
            print(f"回测策略 {i+1}/{len(strategies)}: {strategy.name}")
            
            try:
                # 运行回测
                result = backtest_engine.run_backtest(strategy, data)
                
                # 提取关键指标
                metrics = result.metrics
                comparison_data.append({
                    'strategy_name': strategy.name,
                    'total_return': metrics.get('total_return', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'total_trades': metrics.get('total_trades', 0),
                    'start_date': result.start_date,
                    'end_date': result.end_date
                })
            except Exception as e:
                print(f"策略 {strategy.name} 回测失败: {e}")
                continue
        
        if comparison_data:
            return pd.DataFrame(comparison_data)
        else:
            return pd.DataFrame()  # 返回空DataFrame
    
    def generate_comparison_report(self, comparison_df: pd.DataFrame) -> str:
        """生成策略对比报告"""
        if comparison_df.empty:
            return "没有可比较的策略结果"
        
        report = "策略对比报告\n"
        report += "=" * 50 + "\n\n"
        
        # 按夏普比率排序
        sorted_df = comparison_df.sort_values('sharpe_ratio', ascending=False)
        
        for idx, row in sorted_df.iterrows():
            report += f"策略: {row['strategy_name']}\n"
            report += f"  总收益率: {row['total_return']:.4f}\n"
            report += f"  夏普比率: {row['sharpe_ratio']:.4f}\n"
            report += f"  最大回撤: {row['max_drawdown']:.4f}\n"
            report += f"  胜率: {row['win_rate']:.4f}\n"
            report += f"  盈利因子: {row['profit_factor']:.4f}\n"
            report += f"  总交易次数: {row['total_trades']}\n"
            report += f"  回测期间: {row['start_date']} 到 {row['end_date']}\n\n"
        
        return report


# 使用示例
def demo_strategy_factory():
    """演示策略工厂使用"""
    # 创建策略工厂
    factory = StrategyFactory()
    
    print("=== 策略模板列表 ===")
    templates = factory.list_all_templates()
    for template in templates:
        print(f"ID: {template.template_id}")
        print(f"名称: {template.name}")
        print(f"类别: {template.category}")
        print(f"描述: {template.description}")
        print(f"参数: {[p.name for p in template.parameters]}")
        print("-" * 30)
    
    print("\n=== 创建策略实例 ===")
    # 使用模板创建策略
    ma_params = {'short_window': 10, 'long_window': 30}
    ma_strategy = factory.create_strategy_from_template('ma_crossover', ma_params)
    print(f"创建策略: {ma_strategy.name}")
    print(f"参数: {ma_strategy.parameters}")
    
    # 创建示例数据
    dates = pd.date_range(end=datetime.now(), periods=100)
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.normal(0, 1, 100))
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.normal(0, 0.5, 100),
        'high': prices + abs(np.random.normal(0, 0.8, 100)),
        'low': prices - abs(np.random.normal(0, 0.8, 100)),
        'close': prices,
        'volume': np.random.normal(1000000, 200000, 100)
    })
    
    print("\n=== 生成交易信号 ===")
    signals = ma_strategy.generate_signals(data)
    print(f"信号形状: {signals.shape}")
    print(f"交易信号示例:\n{signals.tail(10)}")
    
    print("\n=== 策略对比示例 ===")
    # 创建多个策略进行对比
    strategies = [
        factory.create_strategy_from_template('ma_crossover', {'short_window': 5, 'long_window': 20}),
        factory.create_strategy_from_template('rsi_reversion', {'rsi_period': 14, 'overbought_level': 70, 'oversold_level': 30}),
        factory.create_strategy_from_template('bollinger_bands', {'period': 20, 'std_dev': 2.0})
    ]
    
    # 这里需要导入回测引擎
    try:
        from logic.backtest_engine import BacktestEngine
        backtest_engine = BacktestEngine()
        
        comparator = StrategyComparison()
        comparison_results = comparator.compare_strategies(strategies, data, backtest_engine)
        report = comparator.generate_comparison_report(comparison_results)
        print(report)
    except ImportError:
        print("回测引擎未找到，跳过策略对比演示")


if __name__ == "__main__":
    demo_strategy_factory()
