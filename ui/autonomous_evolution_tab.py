"""
自主进化系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.autonomous_evolution_system import AutonomousEvolutionSystem
from logic.data_manager import DataManager


def render_autonomous_evolution_tab(db: DataManager, config):
    """渲染自主进化标签页"""
    
    st.title("🧬 自主进化系统")
    st.markdown("---")
    
    # 初始化系统
    if 'autonomous_evolution_system' not in st.session_state:
        st.session_state.autonomous_evolution_system = AutonomousEvolutionSystem()
    
    system = st.session_state.autonomous_evolution_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 进化参数
        st.subheader("🧬 进化参数")
        population_size = st.slider("种群大小", 20, 100, 50, 10, help="种群中个体数量")
        mutation_rate = st.slider("变异率", 0.01, 0.3, 0.1, 0.01, help="变异概率")
        crossover_rate = st.slider("交叉率", 0.5, 1.0, 0.8, 0.05, help="交叉概率")
        n_generations = st.slider("进化代数", 10, 100, 50, 10, help="进化代数")
        
        # 策略参数
        st.subheader("📊 策略参数")
        min_turnover = st.slider("最小换手率(%)", 1.0, 20.0, 5.0, 0.5)
        max_turnover = st.slider("最大换手率(%)", 10.0, 50.0, 20.0, 0.5)
        stop_loss = st.slider("止损(%)", 2.0, 10.0, 5.0, 0.5)
        take_profit = st.slider("止盈(%)", 10.0, 30.0, 15.0, 1.0)
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history = system.get_evolution_history(limit=10)
        st.metric("进化记录", f"{len(history)} 条")
    
    with col2:
        st.metric("种群大小", population_size)
    
    with col3:
        st.metric("进化代数", n_generations)
    
    # 注册策略
    st.markdown("---")
    st.header("📊 策略管理")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("➕ 注册策略", use_container_width=True):
            with st.spinner("正在注册策略..."):
                strategy_params = {
                    'min_turnover': (min_turnover, max_turnover),
                    'stop_loss': (stop_loss * 0.8, stop_loss * 1.2),
                    'take_profit': (take_profit * 0.8, take_profit * 1.2),
                    'position_size': (0.2, 0.8)
                }
                
                strategy_id = f"strategy_{len(system.strategy_optimizers) + 1}"
                system.register_strategy(strategy_id, strategy_params)
                st.success(f"策略 {strategy_id} 注册成功！")
    
    with col2:
        if st.button("🚀 开始进化", use_container_width=True):
            with st.spinner("正在进化..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
                data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
                    'volume': np.linspace(1000000, 5000000, 100)
                })
                
                # 进化所有策略
                result = system.evolve_all_strategies(data, n_generations)
                st.session_state.evolution_result = result
                st.success("进化完成！")
    
    # 策略列表
    st.markdown("---")
    st.header("📋 策略列表")
    
    if system.strategy_optimizers:
        strategy_ids = list(system.strategy_optimizers.keys())
        st.write(f"已注册 {len(strategy_ids)} 个策略:")
        for sid in strategy_ids:
            best_strategy = system.get_best_strategy(sid)
            if best_strategy:
                st.info(f"**{sid}**: 最佳参数已优化")
            else:
                st.warning(f"**{sid}**: 尚未进化")
    else:
        st.info("暂无策略")
    
    # 进化结果
    if 'evolution_result' in st.session_state:
        result = st.session_state.evolution_result
        
        st.subheader("📊 进化结果")
        
        for strategy_id, strategy_result in result.items():
            with st.expander(f"策略 {strategy_id}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("最佳适应度", f"{strategy_result['best_fitness']:.4f}")
                
                with col2:
                    st.metric("进化代数", strategy_result['n_generations'])
                
                with col3:
                    best_metrics = strategy_result.get('best_metrics', {})
                    if best_metrics:
                        st.metric("最佳收益", f"{best_metrics.get('total_return', 0):.2%}")
    
    # 进化历史
    st.markdown("---")
    st.header("📈 进化历史")
    
    history = system.get_evolution_history(limit=50)
    
    if history:
        df = pd.DataFrame([{
            'strategy_id': h['strategy_id'],
            'timestamp': h['timestamp'],
            'best_fitness': h['result']['best_fitness'],
            'n_generations': h['result']['n_generations']
        } for h in history])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(df, use_container_width=True)
        
        # 适应度曲线
        fig = go.Figure(data=[
            go.Scatter(
                x=df.index,
                y=df['best_fitness'],
                mode='lines+markers',
                name='适应度',
                line=dict(color='#2196F3', width=2)
            )
        ])
        
        fig.update_layout(
            title="进化适应度曲线",
            xaxis_title="进化次数",
            yaxis_title="适应度",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无进化记录")
    
    # 系统说明
    st.markdown("---")
    st.header("📋 系统说明")
    
    system_info = pd.DataFrame([
        {
            '概念': '遗传算法',
            '说明': '模拟自然选择和遗传机制，通过选择、交叉、变异进化策略',
            '优势': '全局搜索、避免局部最优、自动优化'
        },
        {
            '概念': '选择',
            '说明': '根据适应度选择优秀个体，保留优良基因',
            '优势': '提高种群质量、加速收敛'
        },
        {
            '概念': '交叉',
            '说明': '组合两个父代的基因，生成新的子代',
            '优势': '探索新解空间、保持多样性'
        },
        {
            '概念': '变异',
            '说明': '随机改变个体基因，引入新的变化',
            '优势': '避免早熟收敛、跳出局部最优'
        }
    ])
    
    st.dataframe(system_info, use_container_width=True)
    
    st.info("💡 自主进化系统通过遗传算法自动优化策略参数，实现策略的持续改进")