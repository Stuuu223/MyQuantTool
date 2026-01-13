"""
交互式策略分析界面

功能：
- 基于Streamlit的交互式策略分析
- 实时参数调整
- 策略性能对比可视化
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from logic.strategy_factory import StrategyFactory, Strategy
from logic.backtest_engine import BacktestEngine
from logic.strategy_comparison import StrategyComparator
from logic.parameter_optimizer import ParameterOptimizer


class InteractiveStrategyAnalyzer:
    """交互式策略分析器"""
    
    def __init__(self):
        self.factory = StrategyFactory()
        self.backtest_engine = BacktestEngine()
        self.comparator = StrategyComparator()
        self.optimizer = ParameterOptimizer()
        
        # 设置页面配置
        st.set_page_config(
            page_title="量化策略交互式分析平台",
            page_icon="📊",
            layout="wide"
        )
    
    def run_streamlit_app(self):
        """运行Streamlit应用"""
        st.title("📊 量化策略交互式分析平台")
        
        # 侧边栏
        st.sidebar.header("导航")
        app_mode = st.sidebar.selectbox(
            "选择功能",
            ["首页", "策略回测", "参数优化", "策略对比", "市场情绪分析", "组合优化"]
        )
        
        if app_mode == "首页":
            self.show_home()
        elif app_mode == "策略回测":
            self.strategy_backtest_page()
        elif app_mode == "参数优化":
            self.parameter_optimization_page()
        elif app_mode == "策略对比":
            self.strategy_comparison_page()
        elif app_mode == "市场情绪分析":
            self.market_sentiment_page()
        elif app_mode == "组合优化":
            self.portfolio_optimization_page()
    
    def show_home(self):
        """首页"""
        st.header("欢迎使用量化策略交互式分析平台")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 功能特点")
            st.markdown("""
            - **策略回测**: 支持多种经典策略的回测分析
            - **参数优化**: 提供网格搜索、遗传算法等优化方法
            - **策略对比**: 可视化对比不同策略的表现
            - **实时分析**: 市场情绪和资金流向分析
            - **组合优化**: 现代投资组合理论实现
            """)
        
        with col2:
            st.subheader("🔧 支持的策略类型")
            st.markdown("""
            - 移动平均线交叉策略
            - RSI均值回归策略
            - 布林带策略
            - 自定义策略模板
            """)
        
        # 显示可用策略模板
        st.subheader("可用策略模板")
        templates = self.factory.list_all_templates()
        for template in templates:
            with st.expander(f"**{template.name}**"):
                st.write(f"**ID**: {template.template_id}")
                st.write(f"**描述**: {template.description}")
                st.write(f"**类别**: {template.category}")
                st.write(f"**参数**:")
                for param in template.parameters:
                    st.write(f"  - {param.name}: {param.description}")
    
    def strategy_backtest_page(self):
        """策略回测页面"""
        st.header("🔍 策略回测")
        
        # 选择策略模板
        templates = self.factory.list_all_templates()
        template_names = [t.name for t in templates]
        selected_template_name = st.selectbox("选择策略模板", template_names)
        
        # 获取选中的模板
        selected_template = next(t for t in templates if t.name == selected_template_name)
        
        # 显示参数输入
        st.subheader("策略参数设置")
        params = {}
        cols = st.columns(2)
        
        for i, param in enumerate(selected_template.parameters):
            col = cols[i % 2]
            if param.type == 'int':
                value = col.number_input(
                    param.name,
                    value=int(param.default_value),
                    min_value=int(param.min_value) if param.min_value is not None else None,
                    max_value=int(param.max_value) if param.max_value is not None else None,
                    step=1,
                    help=param.description
                )
            elif param.type == 'float':
                value = col.number_input(
                    param.name,
                    value=float(param.default_value),
                    min_value=float(param.min_value) if param.min_value is not None else None,
                    max_value=float(param.max_value) if param.max_value is not None else None,
                    step=0.1,
                    help=param.description
                )
            else:
                value = col.text_input(param.name, value=str(param.default_value), help=param.description)
            
            params[param.name] = value
        
        # 生成模拟数据
        st.subheader("回测设置")
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365), key="interactive_analyzer_backtest1_start")
        end_date = st.date_input("结束日期", value=datetime.now(), key="interactive_analyzer_backtest1_end")
        initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000, key="interactive_analyzer_backtest1_capital")
        
        if st.button("开始回测"):
            with st.spinner("正在运行回测..."):
                try:
                    # 创建策略
                    strategy = self.factory.create_strategy_from_template(selected_template.template_id, params)
                    
                    # 生成模拟数据
                    dates = pd.date_range(start=start_date, end=end_date)
                    n_days = len(dates)
                    np.random.seed(42)
                    prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, n_days))
                    
                    data = pd.DataFrame({
                        'date': dates,
                        'open': prices + np.random.normal(0, 0.1, n_days),
                        'high': prices + abs(np.random.normal(0, 0.15, n_days)),
                        'low': prices - abs(np.random.normal(0, 0.15, n_days)),
                        'close': prices,
                        'volume': np.random.normal(1000000, 200000, n_days)
                    }).set_index('date')
                    
                    # 运行回测
                    result = self.backtest_engine.run_backtest(strategy, data, initial_capital=initial_capital)
                    
                    # 显示结果
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("总收益率", f"{result.metrics.get('total_return', 0):.2%}")
                    col2.metric("夏普比率", f"{result.metrics.get('sharpe_ratio', 0):.2f}")
                    col3.metric("最大回撤", f"{result.metrics.get('max_drawdown', 0):.2%}")
                    col4.metric("胜率", f"{result.metrics.get('win_rate', 0):.2%}")
                    
                    # 绘制权益曲线
                    st.subheader("权益曲线")
                    if result.equity_curve is not None and not result.equity_curve.empty:
                        fig, ax = plt.subplots(figsize=(10, 6))
                        ax.plot(result.equity_curve.index, result.equity_curve.values)
                        ax.set_title(f"{strategy.name} 权益曲线")
                        ax.set_xlabel("日期")
                        ax.set_ylabel("权益")
                        st.pyplot(fig)
                        plt.close()
                    
                    # 显示详细指标
                    st.subheader("详细指标")
                    metrics_df = pd.DataFrame(list(result.metrics.items()), columns=['指标', '值'])
                    st.dataframe(metrics_df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"回测失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    def parameter_optimization_page(self):
        """参数优化页面"""
        st.header("⚙️ 参数优化")
        
        # 选择策略模板
        templates = self.factory.list_all_templates()
        template_names = [t.name for t in templates]
        selected_template_name = st.selectbox("选择策略模板", template_names)
        
        selected_template = next(t for t in templates if t.name == selected_template_name)
        
        # 参数范围设置
        st.subheader("参数范围设置")
        param_ranges = {}
        
        for param in selected_template.parameters:
            if param.type in ['int', 'float']:
                col1, col2 = st.columns(2)
                min_val = col1.number_input(f"{param.name} 最小值", value=float(param.min_value or 1))
                max_val = col2.number_input(f"{param.name} 最大值", value=float(param.max_value or 10))
                
                if param.type == 'int':
                    step = 1
                else:
                    step = 0.1
                
                # 步长
                step_val = st.number_input(f"{param.name} 步长", value=step, min_value=0.01)
                
                # 生成参数列表
                if step_val > 0:
                    values = []
                    current = min_val
                    while current <= max_val:
                        values.append(current)
                        current += step_val
                        if param.type == 'int':
                            current = int(current)
                    
                    param_ranges[param.name] = values
        
        # 优化设置
        st.subheader("优化设置")
        optimization_method = st.selectbox("优化方法", ["网格搜索", "随机搜索", "遗传算法"])
        target_metric = st.selectbox("目标指标", ["sharpe_ratio", "total_return", "win_rate", "profit_factor"])
        max_evals = st.slider("最大评估次数", 10, 200, 50)
        
        if st.button("开始优化"):
            with st.spinner("正在运行参数优化..."):
                try:
                    # 生成模拟数据
                    dates = pd.date_range(end=datetime.now(), periods=252)  # 一年数据
                    n_days = len(dates)
                    np.random.seed(42)
                    prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, n_days))
                    
                    data = pd.DataFrame({
                        'date': dates,
                        'open': prices + np.random.normal(0, 0.1, n_days),
                        'high': prices + abs(np.random.normal(0, 0.15, n_days)),
                        'low': prices - abs(np.random.normal(0, 0.15, n_days)),
                        'close': prices,
                        'volume': np.random.normal(1000000, 200000, n_days)
                    }).set_index('date')
                    
                    # 创建目标函数
                    def objective_function(params):
                        try:
                            strategy = self.factory.create_strategy_from_template(selected_template.template_id, params)
                            result = self.backtest_engine.run_backtest(strategy, data)
                            return result.metrics.get(target_metric, 0)
                        except:
                            return float('-inf') if target_metric in ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor'] else float('inf')
                    
                    # 执行优化
                    if optimization_method == "网格搜索":
                        result = self.optimizer.grid_search(objective_function, param_ranges, maximize=True)
                    elif optimization_method == "随机搜索":
                        # 为随机搜索构建参数空间
                        random_param_space = {}
                        for param_name, values in param_ranges.items():
                            if values:
                                random_param_space[param_name] = (min(values), max(values), 'float' if isinstance(values[0], float) else 'int')
                        result = self.optimizer.random_search(objective_function, random_param_space, n_trials=max_evals, maximize=True)
                    elif optimization_method == "遗传算法":
                        # 为遗传算法构建参数空间
                        ga_param_space = {}
                        for param_name, values in param_ranges.items():
                            if values:
                                ga_param_space[param_name] = (min(values), max(values), 'float' if isinstance(values[0], float) else 'int')
                        result = self.optimizer.genetic_algorithm_optimization(
                            objective_function, ga_param_space, 
                            population_size=min(50, max_evals//2), generations=max(10, max_evals//50), maximize=True
                        )
                    
                    # 显示优化结果
                    st.success(f"优化完成！最佳参数: {result.best_params}")
                    st.metric(f"最佳{target_metric}", f"{result.best_value:.4f}")
                    
                    # 显示优化历史
                    if result.optimization_trace:
                        trace_df = pd.DataFrame(result.optimization_trace, columns=['params', 'value'])
                        trace_df['eval'] = range(len(trace_df))
                        
                        fig, ax = plt.subplots()
                        ax.plot(trace_df['eval'], trace_df['value'])
                        ax.set_xlabel('评估次数')
                        ax.set_ylabel(target_metric)
                        ax.set_title(f'{optimization_method}优化过程')
                        st.pyplot(fig)
                        plt.close()
                
                except Exception as e:
                    st.error(f"优化失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    def strategy_comparison_page(self):
        """策略对比页面"""
        st.header("⚖️ 策略对比")
        
        # 选择要对比的策略
        templates = self.factory.list_all_templates()
        
        selected_strategy_names = st.multiselect(
            "选择要对比的策略",
            [t.name for t in templates],
            default=[t.name for t in templates[:2]] if len(templates) >= 2 else []
        )
        
        # 为每个选中的策略设置参数
        strategies = []
        for name in selected_strategy_names:
            template = next(t for t in templates if t.name == name)
            
            with st.expander(f"{name} 参数设置"):
                params = {}
                cols = st.columns(2)
                
                for i, param in enumerate(template.parameters):
                    col = cols[i % 2]
                    if param.type == 'int':
                        value = col.number_input(
                            param.name,
                            value=int(param.default_value),
                            min_value=int(param.min_value) if param.min_value is not None else None,
                            max_value=int(param.max_value) if param.max_value is not None else None,
                            step=1,
                            key=f"{name}_{param.name}"
                        )
                    elif param.type == 'float':
                        value = col.number_input(
                            param.name,
                            value=float(param.default_value),
                            min_value=float(param.min_value) if param.min_value is not None else None,
                            max_value=float(param.max_value) if param.max_value is not None else None,
                            step=0.1,
                            key=f"{name}_{param.name}"
                        )
                    else:
                        value = col.text_input(param.name, value=str(param.default_value), key=f"{name}_{param.name}")
                    
                    params[param.name] = value
                
                # 创建策略实例
                strategy = self.factory.create_strategy_from_template(template.template_id, params)
                strategies.append(strategy)
        
        # 数据设置
        st.subheader("回测设置")
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365), key="interactive_analyzer_backtest2_start")
        end_date = st.date_input("结束日期", value=datetime.now(), key="interactive_analyzer_backtest2_end")
        initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000, key="interactive_analyzer_backtest2_capital")
        
        if st.button("开始对比回测") and strategies:
            with st.spinner("正在运行对比回测..."):
                try:
                    # 生成模拟数据
                    dates = pd.date_range(start=start_date, end=end_date)
                    n_days = len(dates)
                    np.random.seed(42)
                    prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, n_days))
                    
                    data = pd.DataFrame({
                        'date': dates,
                        'open': prices + np.random.normal(0, 0.1, n_days),
                        'high': prices + abs(np.random.normal(0, 0.15, n_days)),
                        'low': prices - abs(np.random.normal(0, 0.15, n_days)),
                        'close': prices,
                        'volume': np.random.normal(1000000, 200000, n_days)
                    }).set_index('date')
                    
                    # 运行对比回测
                    comparison_df = self.comparator.run_strategy_comparison(strategies, data, self.backtest_engine)
                    
                    if not comparison_df.empty:
                        # 显示对比结果
                        st.subheader("策略性能对比")
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        # 显示排名
                        st.subheader("综合排名")
                        rank_cols = ['strategy_name', 'composite_rank', 'composite_score', 'sharpe_ratio', 'total_return', 'max_drawdown']
                        rank_df = comparison_df[rank_cols].sort_values('composite_rank')
                        st.dataframe(rank_df, use_container_width=True)
                        
                        # 绘制权益曲线对比
                        st.subheader("权益曲线对比")
                        fig = go.Figure()
                        
                        for strategy in strategies:
                            try:
                                result = self.backtest_engine.run_backtest(strategy, data, initial_capital=initial_capital)
                                if result.equity_curve is not None and not result.equity_curve.empty:
                                    fig.add_trace(go.Scatter(
                                        x=result.equity_curve.index,
                                        y=result.equity_curve.values,
                                        mode='lines',
                                        name=strategy.name
                                    ))
                            except:
                                continue
                        
                        fig.update_layout(
                            title="策略权益曲线对比",
                            xaxis_title="日期",
                            yaxis_title="权益",
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 性能指标雷达图
                        st.subheader("性能指标雷达图")
                        metrics_for_radar = ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor']
                        radar_df = pd.DataFrame()
                        
                        for idx, row in comparison_df.iterrows():
                            strategy_metrics = [row[metric] for metric in metrics_for_radar]
                            # 标准化到[0,1]区间
                            normalized_metrics = [(m - comparison_df[metric].min()) / (comparison_df[metric].max() - comparison_df[metric].min() or 1) 
                                                  for m, metric in zip(strategy_metrics, metrics_for_radar)]
                            radar_df[row['strategy_name']] = normalized_metrics
                        
                        radar_df.index = metrics_for_radar
                        
                        fig = go.Figure()
                        for col in radar_df.columns:
                            fig.add_trace(go.Scatterpolar(
                                r=radar_df[col].tolist() + [radar_df[col].iloc[0]],  # 闭合图形
                                theta=metrics_for_radar + [metrics_for_radar[0]],
                                fill='toself',
                                name=col
                            ))
                        
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 1]
                                )),
                            showlegend=True,
                            title="策略性能雷达图"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"对比回测失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    def market_sentiment_page(self):
        """市场情绪分析页面"""
        st.header("🧠 市场情绪分析")
        
        # 这里可以集成市场情绪分析功能
        st.info("市场情绪分析功能将在后续版本中实现")
        
        # 展示一些示例图表
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("情绪指标趋势")
            dates = pd.date_range(end=datetime.now(), periods=30)
            sentiment_data = pd.DataFrame({
                'date': dates,
                'news_sentiment': np.random.uniform(-1, 1, 30),
                'social_sentiment': np.random.uniform(-1, 1, 30),
                'market_sentiment': np.random.uniform(-1, 1, 30)
            }).set_index('date')
            
            st.line_chart(sentiment_data)
        
        with col2:
            st.subheader("情绪分布")
            sentiment_values = np.random.uniform(-1, 1, 100)
            fig, ax = plt.subplots()
            ax.hist(sentiment_values, bins=20, edgecolor='black')
            ax.set_xlabel('情绪分数')
            ax.set_ylabel('频次')
            ax.set_title('情绪分数分布')
            st.pyplot(fig)
            plt.close()
    
    def portfolio_optimization_page(self):
        """组合优化页面"""
        st.header("💼 投资组合优化")
        
        # 这里可以集成组合优化功能
        st.info("投资组合优化功能将在后续版本中实现")
        
        # 示例：展示资产相关性热力图
        st.subheader("资产相关性分析")
        assets = ['股票A', '股票B', '债券C', '商品D', '外汇E']
        n_assets = len(assets)
        
        # 生成随机相关性矩阵
        np.random.seed(42)
        corr_matrix = np.random.uniform(-0.5, 0.8, (n_assets, n_assets))
        # 确保矩阵对称且对角线为1
        for i in range(n_assets):
            corr_matrix[i, i] = 1
            for j in range(i+1, n_assets):
                corr_matrix[j, i] = corr_matrix[i, j]
        
        corr_df = pd.DataFrame(corr_matrix, index=assets, columns=assets)
        
        # 绘制热力图
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr_df, annot=True, cmap='RdBu', center=0, ax=ax, 
                    square=True, cbar_kws={'label': '相关系数'})
        ax.set_title('资产相关性热力图')
        st.pyplot(fig)
        plt.close()


def run_interactive_analyzer():
    """运行交互式策略分析器"""
    analyzer = InteractiveStrategyAnalyzer()
    analyzer.run_streamlit_app()


if __name__ == "__main__":
    # 如果直接运行，启动Streamlit应用
    run_interactive_analyzer()