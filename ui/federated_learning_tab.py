"""
联邦学习系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.federated_learning_system import FederatedLearningSystem, SimpleModel
from logic.data_manager import DataManager


def render_federated_learning_tab(db: DataManager, config):
    """渲染联邦学习标签页"""
    
    st.title("🔐 联邦学习系统")
    st.markdown("---")
    
    # 初始化系统
    if 'federated_learning_system' not in st.session_state:
        model = SimpleModel(input_size=10, hidden_size=64, output_size=1)
        st.session_state.federated_learning_system = FederatedLearningSystem(model)
    
    system = st.session_state.federated_learning_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 训练参数
        st.subheader("🎓 训练参数")
        n_rounds = st.slider("训练轮数", 5, 50, 10, 5, help="联邦训练轮数")
        client_fraction = st.slider("客户端选择比例", 0.1, 1.0, 1.0, 0.1, help="每轮选择的客户端比例")
        learning_rate = st.slider("学习率", 0.001, 0.1, 0.01, 0.001, help="学习率")
        
        # 隐私保护
        st.subheader("🔒 隐私保护")
        use_dp = st.checkbox("使用差分隐私", value=False, help="是否添加差分隐私噪声")
        dp_epsilon = st.slider("隐私参数(ε)", 0.1, 10.0, 1.0, 0.1, help="差分隐私参数")
        
        # 聚合策略
        st.subheader("🔄 聚合策略")
        aggregation_strategy = st.selectbox("聚合策略", ["fedavg", "fedprox", "fednova"], help="聚合方法")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        client_info = system.get_client_info()
        st.metric("客户端数", f"{len(client_info)} 个")
    
    with col2:
        st.metric("聚合策略", aggregation_strategy)
    
    with col3:
        st.metric("差分隐私", "开启" if use_dp else "关闭")
    
    # 添加客户端
    st.markdown("---")
    st.header("👥 客户端管理")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("➕ 添加客户端", use_container_width=True):
            with st.spinner("正在添加客户端..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
                data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
                    'volume': np.linspace(1000000, 5000000, 100)
                })
                
                client_id = f"client_{len(system.clients) + 1}"
                system.add_client(client_id, data, privacy_budget=1.0)
                st.success(f"客户端 {client_id} 添加成功！")
    
    with col2:
        if st.button("🚀 开始联邦训练", use_container_width=True):
            with st.spinner("正在训练..."):
                result = system.train(n_rounds, epochs_per_round=1, 
                                   client_fraction=client_fraction, 
                                   learning_rate=learning_rate,
                                   use_dp=use_dp, dp_epsilon=dp_epsilon)
                
                st.session_state.training_result = result
                st.success("训练完成！")
    
    # 客户端信息
    st.markdown("---")
    st.header("📊 客户端信息")
    
    client_info = system.get_client_info()
    
    if client_info:
        df = pd.DataFrame(client_info)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无客户端")
    
    # 训练结果
    if 'training_result' in st.session_state:
        result = st.session_state.training_result
        
        st.subheader("📊 训练结果")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总时间", f"{result['total_time']:.2f}s")
        
        with col2:
            st.metric("平均轮时间", f"{result['avg_round_time']:.2f}s")
        
        with col3:
            st.metric("总隐私消耗", f"{result['total_privacy_used']:.4f}")
    
    # 训练历史
    st.markdown("---")
    st.header("📈 训练历史")
    
    round_history = system.server.get_round_history(limit=50)
    
    if round_history:
        df = pd.DataFrame(round_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['round', 'n_clients', 'total_samples', 'round_time']],
            use_container_width=True
        )
        
        # 训练曲线
        fig = go.Figure(data=[
            go.Scatter(
                x=df['round'],
                y=df['round_time'],
                mode='lines+markers',
                name='轮时间',
                line=dict(color='#2196F3', width=2)
            )
        ])
        
        fig.update_layout(
            title="训练轮时间曲线",
            xaxis_title="轮数",
            yaxis_title="时间(秒)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无训练记录")
    
    # 系统说明
    st.markdown("---")
    st.header("📋 系统说明")
    
    system_info = pd.DataFrame([
        {
            '概念': '联邦学习',
            '说明': '在客户端本地训练，只上传模型更新，保护数据隐私',
            '优势': '隐私保护、数据安全、合规性'
        },
        {
            '概念': 'FedAvg',
            '说明': '加权平均聚合，根据样本数加权',
            '优势': '简单高效、收敛稳定'
        },
        {
            '概念': 'FedProx',
            '说明': '添加正则化项，减少客户端差异',
            '优势': '提高收敛速度、提升性能'
        },
        {
            '概念': '差分隐私',
            '说明': '添加噪声保护隐私，防止模型反推数据',
            '优势': '隐私保护、安全性高'
        }
    ])
    
    st.dataframe(system_info, use_container_width=True)
    
    st.info("💡 联邦学习在保护数据隐私的同时实现协同训练，适用于敏感数据场景")