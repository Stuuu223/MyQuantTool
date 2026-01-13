"""
自适应情绪权重系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.adaptive_sentiment_weights import AdaptiveSentimentWeightsSystem
from logic.data_manager import DataManager


def render_adaptive_sentiment_weights_tab(db: DataManager, config):
    """渲染自适应情绪权重标签页"""
    
    st.title("🧠 自适应情绪权重系统")
    st.markdown("---")
    
    # 初始化系统
    if 'adaptive_sentiment_system' not in st.session_state:
        st.session_state.adaptive_sentiment_system = AdaptiveSentimentWeightsSystem()
    
    system = st.session_state.adaptive_sentiment_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 市场数据输入
        st.subheader("📊 市场数据")
        st.info("💡 系统会自动分析市场数据并分类环境")
        
        # 权重显示
        st.subheader("⚖️ 当前权重")
        current_weights = system.get_current_weights()
        
        st.metric("新闻权重", f"{current_weights.get('news_sentiment', 0):.2f}")
        st.metric("社交媒体权重", f"{current_weights.get('social_sentiment', 0):.2f}")
        st.metric("价格权重", f"{current_weights.get('price_sentiment', 0):.2f}")
        st.metric("资金流向权重", f"{current_weights.get('fund_flow_sentiment', 0):.2f}")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history = system.get_history(limit=10)
        st.metric("环境记录", f"{len(history)} 条")
    
    with col2:
        if 'last_environment_result' in st.session_state:
            result = st.session_state.last_environment_result
            st.metric("当前环境", result['environment'])
    
    with col3:
        if 'last_environment_result' in st.session_state:
            result = st.session_state.last_environment_result
            st.metric("置信度", f"{result['confidence']:.2f}")
    
    # 分析市场环境
    st.markdown("---")
    st.header("🔍 市场环境分析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🧠 分析环境", use_container_width=True):
            with st.spinner("正在分析..."):
                # 生成模拟市场数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30)
                market_data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(3000, 3200, 30) + np.random.randn(30) * 50,
                    'volume': np.linspace(100000000, 150000000, 30),
                    'pct_chg': np.random.randn(30) * 0.02
                })
                
                result = system.analyze_and_adjust(market_data)
                
                st.session_state.last_environment_result = result
                st.success("分析完成！")
    
    # 显示分析结果
    if 'last_environment_result' in st.session_state:
        result = st.session_state.last_environment_result
        
        with col2:
            st.subheader("📊 分析结果")
            
            # 环境显示
            environment_colors = {
                'bull': '🟢',
                'bear': '🔴',
                'sideways': '🟡'
            }
            
            st.info(f"{environment_colors.get(result['environment'], '')} **市场环境**: {result['environment']}")
            st.info(f"**置信度**: {result['confidence']:.2f}")
            st.info(f"**预测持续时间**: {result['duration']} 天")
    
    # 详细分析
    if 'last_environment_result' in st.session_state:
        result = st.session_state.last_environment_result
        
        st.markdown("---")
        st.header("📈 详细分析")
        
        # 市场特征
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 市场特征")
            features = result['features']
            
            feature_names = ['波动率', '趋势', '成交量比率', '市场广度', '动量']
            feature_values = features
            
            for name, value in zip(feature_names, feature_values):
                st.metric(name, f"{value:.4f}")
        
        with col2:
            st.subheader("⚖️ 当前权重")
            weights = result['weights']
            
            for key, value in weights.items():
                st.metric(key, f"{value:.2f}")
            
            if result['adjustment']['adjusted']:
                st.warning("⚠️ 权重已调整")
                
                changes = result['adjustment']['changes']
                for key, change in changes.items():
                    if abs(change) > 0.01:
                        st.info(f"{key}: {change:+.2f}")
        
        # 权重变化图表
        st.markdown("---")
        st.header("📊 权重分析")
        
        weight_data = {
            '权重类型': list(weights.keys()),
            '权重值': list(weights.values())
        }
        
        fig = go.Figure(data=[
            go.Bar(
                x=weight_data['权重类型'],
                y=weight_data['权重值'],
                marker_color=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']
            )
        ])
        
        fig.update_layout(
            title="情绪权重分布",
            yaxis_title="权重值",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 历史记录
    st.markdown("---")
    st.header("📜 环境历史")
    
    history = system.get_history(limit=20)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['timestamp', 'environment', 'confidence', 'duration']],
            use_container_width=True
        )
        
        # 环境分布
        env_counts = df['environment'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=env_counts.index,
                values=env_counts.values,
                hole=0.3
            )
        ])
        
        fig.update_layout(
            title="市场环境分布",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史记录")
    
    # 环境说明
    st.markdown("---")
    st.header("📋 市场环境说明")
    
    env_info = pd.DataFrame([
        {
            '环境': '牛市',
            '说明': '市场上涨趋势明显，投资者情绪乐观',
            '权重调整': '提高价格权重，降低新闻权重',
            '操作建议': '积极布局，控制风险'
        },
        {
            '环境': '熊市',
            '说明': '市场下跌趋势明显，投资者情绪悲观',
            '权重调整': '提高新闻权重，降低价格权重',
            '操作建议': '谨慎观望，控制仓位'
        },
        {
            '环境': '震荡市',
            '说明': '市场波动较大，方向不明确',
            '权重调整': '保持均衡权重',
            '操作建议': '波段操作，灵活应对'
        }
    ])
    
    st.dataframe(env_info, use_container_width=True)
    
    st.info("💡 系统会根据市场环境自动调整情绪计算权重，提高决策准确性")