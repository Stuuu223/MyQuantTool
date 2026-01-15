"""
分布式训练系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.distributed_training_system import DistributedTrainingSystem, SimpleModel
from logic.data_manager import DataManager


def render_distributed_training_tab(db: DataManager, config):
    """渲染分布式训练标签页"""
    
    st.title("🖥️ 分布式训练系统")
    st.markdown("---")
    
    # 初始化系统
    if 'distributed_training_system' not in st.session_state:
        st.session_state.distributed_training_system = DistributedTrainingSystem(n_workers=4)
    
    system = st.session_state.distributed_training_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 训练参数
        st.subheader("🎓 训练参数")
        n_workers = st.slider("工作节点数", 2, 8, 4, 1, help="并行训练的工作节点数量")
        n_epochs = st.slider("训练轮数", 5, 50, 10, 5, help="训练轮数")
        learning_rate = st.slider("学习率", 0.001, 0.1, 0.01, 0.001, help="学习率")
        
        # 训练模式
        st.subheader("🔄 训练模式")
        training_mode = st.selectbox("训练模式", ["同步训练", "异步训练"], help="同步或异步训练")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history = system.get_training_history(limit=10)
        st.metric("训练记录", f"{len(history)} 条")
    
    with col2:
        st.metric("工作节点", n_workers)
    
    with col3:
        st.metric("训练模式", training_mode)
    
    # 设置分布式训练
    st.markdown("---")
    st.header("🔧 分布式训练设置")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🌍 设置环境", key="distributed_setup_env", use_container_width=True):
            with st.spinner("正在设置环境..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
                data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
                    'volume': np.linspace(1000000, 5000000, 100)
                })
                
                X = np.random.randn(len(data), 10)
                y = np.random.randn(len(data), 1)
                
                model = SimpleModel(input_size=10, hidden_size=64, output_size=1)
                system.setup(data, model)
                st.success(f"环境设置成功！数据量: {len(data)} 条，工作节点: {n_workers}")
    
    with col2:
        if st.button("🚀 开始训练", key="distributed_start_training", use_container_width=True):
            with st.spinner("正在训练..."):
                # 简化的训练函数
                def train_func(model, data, epochs):
                    for _ in range(epochs):
                        for i in range(len(model.weights)):
                            noise = np.random.randn(*model.weights[i].shape) * 0.01
                            model.weights[i] -= learning_rate * noise
                    return {'loss': 0.5}
                
                def loss_func(model, data):
                    return np.random.rand()
                
                if training_mode == "同步训练":
                    result = system.train_synchronous(train_func, loss_func, n_epochs, learning_rate)
                else:
                    result = system.train_asynchronous(train_func, loss_func, n_epochs, learning_rate)
                
                st.session_state.training_result = result
                st.success("训练完成！")
    
    # 显示训练结果
    if 'training_result' in st.session_state:
        result = st.session_state.training_result
        
        st.subheader("📊 训练结果")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总时间", f"{result['total_time']:.2f}s")
        
        with col2:
            st.metric("平均轮时间", f"{result['avg_epoch_time']:.2f}s")
        
        with col3:
            st.metric("最终损失", f"{result['final_loss']:.4f}")
    
    # 训练历史
    st.markdown("---")
    st.header("📈 训练历史")
    
    history = system.get_training_history(limit=50)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['timestamp', 'loss', 'epoch_time']],
            use_container_width=True
        )
        
        # 损失曲线
        fig = go.Figure(data=[
            go.Scatter(
                x=df.index,
                y=df['loss'],
                mode='lines+markers',
                name='损失',
                line=dict(color='#2196F3', width=2)
            )
        ])
        
        fig.update_layout(
            title="训练损失曲线",
            xaxis_title="轮数",
            yaxis_title="损失",
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
            '概念': '数据并行',
            '说明': '将数据分配到多个工作节点，每个节点独立训练',
            '优势': '加速训练、提高吞吐量'
        },
        {
            '概念': '参数服务器',
            '说明': '中心化参数管理，聚合工作节点的梯度',
            '优势': '易于实现、扩展性好'
        },
        {
            '概念': '同步训练',
            '说明': '等待所有工作节点完成后再更新模型',
            '优势': '收敛稳定、易于调参'
        },
        {
            '概念': '异步训练',
            '说明': '工作节点独立训练，随时更新模型',
            '优势': '训练速度快、资源利用率高'
        }
    ])
    
    st.dataframe(system_info, use_container_width=True)
    
    st.info("💡 分布式训练通过多节点并行训练，大幅提升训练速度和模型性能")