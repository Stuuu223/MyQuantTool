"""
强化学习优化系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.rl_optimization_system import RLOptimizationSystem, TradingEnvironment
from logic.data_manager import DataManager


def render_rl_optimization_tab(db: DataManager, config):
    """渲染强化学习优化标签页"""
    
    st.title("🎮 强化学习优化系统")
    st.markdown("---")
    
    # 初始化系统
    if 'rl_optimization_system' not in st.session_state:
        st.session_state.rl_optimization_system = RLOptimizationSystem()
    
    system = st.session_state.rl_optimization_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 算法选择
        st.subheader("🧠 算法选择")
        algorithm = st.selectbox("选择算法", ["DQN", "PPO"], help="选择强化学习算法")
        
        # 训练参数
        st.subheader("🎓 训练参数")
        n_episodes = st.slider("训练轮数", 10, 100, 20, 10, help="训练的轮数")
        max_steps = st.slider("最大步数", 100, 1000, 500, 50, help="每轮最大步数")
        learning_rate = st.slider("学习率", 0.0001, 0.01, 0.001, 0.0001, help="学习率")
        
        # 环境参数
        st.subheader("🌍 环境参数")
        initial_balance = st.number_input("初始资金", value=100000, min_value=10000, max_value=1000000, step=10000)
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history = system.get_training_history(limit=10)
        st.metric("训练记录", f"{len(history)} 条")
    
    with col2:
        best_perf = system.get_best_performance()
        if best_perf:
            st.metric("最佳收益", f"{max(best_perf.values()):.2%}")
    
    with col3:
        st.metric("算法", algorithm)
    
    # 创建环境和智能体
    st.markdown("---")
    st.header("🔧 环境和智能体设置")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🌍 创建环境", use_container_width=True):
            with st.spinner("正在创建环境..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
                data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
                    'volume': np.linspace(1000000, 5000000, 100)
                })
                
                env = system.create_environment('main_env', data, initial_balance)
                st.success(f"环境创建成功！数据量: {len(data)} 条")
    
    with col2:
        if st.button("🧠 创建智能体", use_container_width=True):
            with st.spinner("正在创建智能体..."):
                state_size = 10
                action_size = 3  # 持有、买入、卖出
                
                if algorithm == "DQN":
                    agent = system.create_dqn_agent('main_agent', state_size, action_size, learning_rate)
                else:
                    agent = system.create_ppo_agent('main_agent', state_size, action_size, learning_rate)
                
                st.success(f"{algorithm}智能体创建成功！")
    
    # 训练
    st.markdown("---")
    st.header("🎓 训练")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 开始训练", key="rl_start_training", use_container_width=True):
            with st.spinner("正在训练..."):
                if algorithm == "DQN":
                    result = system.train_dqn('main_env', 'main_agent', n_episodes, max_steps)
                else:
                    result = system.train_ppo('main_env', 'main_agent', n_episodes, max_steps)
                
                st.session_state.training_result = result
                st.success("训练完成！")
    
    # 显示训练结果
    if 'training_result' in st.session_state:
        result = st.session_state.training_result
        
        with col2:
            st.subheader("📊 训练结果")
            
            st.info(f"**平均收益**: {result['avg_return']:.2%}")
            st.info(f"**最佳收益**: {result['best_return']:.2%}")
            st.info(f"**最差收益**: {result['worst_return']:.2%}")
            st.info(f"**收益标准差**: {result['std_return']:.2%}")
    
    # 训练历史
    st.markdown("---")
    st.header("📈 训练历史")
    
    history = system.get_training_history(limit=50)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['timestamp', 'reward', 'return']],
            use_container_width=True
        )
        
        # 收益曲线
        fig = go.Figure(data=[
            go.Scatter(
                x=df.index,
                y=df['return'],
                mode='lines+markers',
                name='收益',
                line=dict(color='#2196F3', width=2)
            )
        ])
        
        fig.update_layout(
            title="训练收益曲线",
            xaxis_title="轮数",
            yaxis_title="收益率",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无训练记录")
    
    # 算法说明
    st.markdown("---")
    st.header("📋 算法说明")
    
    algo_info = pd.DataFrame([
        {
            '算法': 'DQN',
            '全称': 'Deep Q-Network',
            '说明': '基于深度学习的Q学习，适用于离散动作空间',
            '优势': '稳定、易于实现、经验回放'
        },
        {
            '算法': 'PPO',
            '全称': 'Proximal Policy Optimization',
            '说明': '近端策略优化，适用于连续和离散动作空间',
            '优势': '样本效率高、性能稳定、易于调参'
        }
    ])
    
    st.dataframe(algo_info, use_container_width=True)
    
    st.info("💡 强化学习通过与环境交互学习最优策略，适用于复杂的交易决策场景")