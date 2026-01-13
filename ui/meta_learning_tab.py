"""
元学习系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.meta_learning_system import MetaLearningSystem
from logic.data_manager import DataManager


def render_meta_learning_tab(db: DataManager, config):
    """渲染元学习标签页"""
    
    st.title("🧠 元学习系统 (MAML)")
    st.markdown("---")
    
    # 初始化系统
    if 'meta_learning_system' not in st.session_state:
        st.session_state.meta_learning_system = MetaLearningSystem()
    
    system = st.session_state.meta_learning_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 元训练参数
        st.subheader("🎓 元训练")
        n_epochs = st.slider("训练轮数", 10, 100, 20, 10, help="元训练的轮数")
        tasks_per_epoch = st.slider("每轮任务数", 1, 10, 3, 1, help="每轮采样的任务数")
        n_support = st.slider("支持集大小", 3, 10, 5, 1, help="每个任务的支持集样本数")
        n_query = st.slider("查询集大小", 3, 10, 5, 1, help="每个任务的查询集样本数")
        
        # 适应参数
        st.subheader("⚡ 快速适应")
        n_adapt_steps = st.slider("适应步数", 1, 10, 5, 1, help="适应新任务的步数")
        
        # 模型状态
        st.subheader("📊 模型状态")
        if 'meta_training_result' in st.session_state:
            result = st.session_state.meta_training_result
            st.metric("最终损失", f"{result['final_loss']:.4f}")
            st.metric("训练轮数", result['n_epochs'])
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("输入维度", 10)
    
    with col2:
        st.metric("隐藏层", 64)
    
    with col3:
        st.metric("输出维度", 1)
    
    # 元训练
    st.markdown("---")
    st.header("🎓 元训练")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 开始元训练", use_container_width=True):
            with st.spinner("正在训练..."):
                # 创建训练任务
                n_tasks = 20
                n_samples_per_task = 20
                n_features = 10
                
                tasks = []
                for i in range(n_tasks):
                    X = np.random.randn(n_samples_per_task, n_features)
                    y = np.random.randn(n_samples_per_task, 1)
                    tasks.append({'X': X, 'y': y})
                
                # 训练
                training_result = system.meta_train(
                    tasks=tasks,
                    n_epochs=n_epochs,
                    tasks_per_epoch=tasks_per_epoch,
                    n_support=n_support,
                    n_query=n_query
                )
                
                st.session_state.meta_training_result = training_result
                st.success("训练完成！")
    
    # 显示训练结果
    if 'meta_training_result' in st.session_state:
        result = st.session_state.meta_training_result
        
        with col2:
            st.subheader("📊 训练结果")
            
            st.info(f"**最终损失**: {result['final_loss']:.4f}")
            st.info(f"**训练轮数**: {result['n_epochs']}")
            st.info(f"**总任务数**: {result['n_tasks']}")
    
    # 训练曲线
    if 'meta_training_result' in st.session_state:
        result = st.session_state.meta_training_result
        
        st.markdown("---")
        st.header("📈 训练曲线")
        
        if result['loss_history']:
            fig = go.Figure(data=[
                go.Scatter(
                    x=list(range(len(result['loss_history']))),
                    y=result['loss_history'],
                    mode='lines+markers',
                    name='损失',
                    line=dict(color='#2196F3', width=2)
                )
            ])
            
            fig.update_layout(
                title="元训练损失曲线",
                xaxis_title="轮数",
                yaxis_title="损失",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # 快速适应
    st.markdown("---")
    st.header("⚡ 快速适应")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🎯 适应新任务", use_container_width=True):
            with st.spinner("正在适应..."):
                # 创建新任务
                n_samples = 15
                n_features = 10
                X_new = np.random.randn(n_samples, n_features)
                y_new = np.random.randn(n_samples, 1)
                
                # 适应
                adaptation_result = system.adapt_to_new_task(
                    X_support=X_new[:n_support],
                    y_support=y_new[:n_support],
                    X_query=X_new[n_support:],
                    y_query=y_new[n_support:],
                    n_adapt_steps=n_adapt_steps
                )
                
                st.session_state.adaptation_result = adaptation_result
                st.success("适应完成！")
    
    # 显示适应结果
    if 'adaptation_result' in st.session_state:
        result = st.session_state.adaptation_result
        
        with col2:
            st.subheader("📊 适应结果")
            
            st.info(f"**适应损失**: {result['adaptation_loss']:.4f}")
            st.info(f"**测试损失**: {result['test_loss']:.4f}")
            st.info(f"**适应步数**: {result['n_adapt_steps']}")
    
    # 预测结果
    if 'adaptation_result' in st.session_state:
        result = st.session_state.adaptation_result
        
        st.markdown("---")
        st.header("🎯 预测结果")
        
        predictions = result['predictions']
        
        # 预测表格
        pred_df = pd.DataFrame({
            '样本': range(1, len(predictions) + 1),
            '预测值': predictions.flatten()
        })
        
        st.dataframe(pred_df, use_container_width=True)
        
        # 预测可视化
        fig = go.Figure(data=[
            go.Bar(
                x=pred_df['样本'],
                y=pred_df['预测值'],
                marker_color='#4CAF50'
            )
        ])
        
        fig.update_layout(
            title="预测结果",
            xaxis_title="样本",
            yaxis_title="预测值",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 模型说明
    st.markdown("---")
    st.header("📋 MAML原理说明")
    
    maml_info = pd.DataFrame([
        {
            '概念': '元学习',
            '说明': '学习如何学习，通过多任务训练获得快速适应能力',
            '优势': '少样本学习、快速适应、泛化能力强'
        },
        {
            '概念': 'MAML',
            '说明': 'Model-Agnostic Meta-Learning，模型无关的元学习算法',
            '优势': '适用于任何模型、端到端训练、计算效率高'
        },
        {
            '概念': '支持集',
            '说明': '用于适应新任务的少量样本',
            '优势': '模拟真实场景、降低数据需求'
        },
        {
            '概念': '查询集',
            '说明': '用于评估适应效果的样本',
            '优势': '验证适应能力、指导元训练'
        }
    ])
    
    st.dataframe(maml_info, use_container_width=True)
    
    # 训练流程
    st.markdown("---")
    st.header("🔄 训练流程")
    
    st.markdown("""
    **元训练流程**:
    1. 从任务分布中采样一批任务
    2. 对每个任务，分为支持集和查询集
    3. 在支持集上进行梯度下降，得到任务特定参数
    4. 在查询集上计算损失
    5. 对所有任务的损失进行元更新
    6. 重复步骤1-5，直到收敛
    
    **快速适应流程**:
    1. 获取新任务的支持集样本
    2. 使用元训练得到的初始化参数
    3. 在支持集上进行少量梯度更新
    4. 得到适应后的参数
    5. 使用适应后的参数进行预测
    """)
    
    st.info("💡 MAML通过元训练获得一个好的初始化参数，使得模型能够通过少量梯度步骤快速适应新任务")