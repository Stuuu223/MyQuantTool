"""
多模态融合决策系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.multimodal_fusion_system import MultimodalFusionSystem
from logic.data_manager import DataManager


def render_multimodal_fusion_tab(db: DataManager, config):
    """渲染多模态融合决策标签页"""
    
    st.title("🔀 多模态融合决策系统")
    st.markdown("---")
    
    # 初始化系统
    if 'multimodal_fusion_system' not in st.session_state:
        st.session_state.multimodal_fusion_system = MultimodalFusionSystem()
    
    system = st.session_state.multimodal_fusion_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 股票输入
        st.subheader("📊 股票分析")
        stock_code = st.text_input("股票代码", value="600000", help="输入股票代码")
        
        # 文本输入
        st.subheader("📝 文本输入")
        text_input = st.text_area("输入文本（新闻、公告等）", 
                                 value="公司发布重大利好，业绩大幅增长，创新高，市场看好",
                                 height=100,
                                 help="输入相关的新闻、公告或评论")
        
        # 融合权重设置
        st.subheader("⚖️ 融合权重")
        with st.expander("调整融合权重"):
            text_weight = st.slider("文本权重", 0.0, 1.0, 0.3, 0.05)
            image_weight = st.slider("图像权重", 0.0, 1.0, 0.4, 0.05)
            ts_weight = st.slider("时间序列权重", 0.0, 1.0, 0.3, 0.05)
            
            if st.button("应用权重"):
                total = text_weight + image_weight + ts_weight
                if abs(total - 1.0) > 0.01:
                    st.error(f"权重总和必须为1，当前为{total:.2f}")
                else:
                    system.set_fusion_weights({
                        'text': text_weight,
                        'image': image_weight,
                        'time_series': ts_weight
                    })
                    st.success("权重已更新")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        history = system.get_history(limit=10)
        st.metric("分析记录", f"{len(history)} 条")
    
    with col2:
        st.metric("分析股票", stock_code)
    
    with col3:
        if 'last_fusion_result' in st.session_state:
            result = st.session_state.last_fusion_result
            st.metric("当前决策", result['decision'])
    
    # 分析股票
    st.markdown("---")
    st.header("🔍 多模态分析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔀 融合分析", use_container_width=True):
            with st.spinner("正在分析..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30)
                kline_data = pd.DataFrame({
                    'date': dates,
                    'open': np.linspace(10, 15, 30),
                    'close': np.linspace(10.5, 15.5, 30),
                    'high': np.linspace(10.6, 15.6, 30),
                    'low': np.linspace(9.9, 14.9, 30),
                    'volume': np.linspace(1000000, 5000000, 30)
                })
                
                ts_data = kline_data.copy()
                
                result = system.analyze(
                    stock_code=stock_code,
                    text=text_input,
                    kline_data=kline_data,
                    ts_data=ts_data
                )
                
                st.session_state.last_fusion_result = result
                st.success("分析完成！")
    
    # 显示分析结果
    if 'last_fusion_result' in st.session_state:
        result = st.session_state.last_fusion_result
        
        with col2:
            st.subheader("📊 融合结果")
            
            # 决策
            decision_colors = {
                '买入': '🟢',
                '持有': '🟡',
                '观望': '⚪',
                '减仓': '🟠',
                '卖出': '🔴'
            }
            
            st.info(f"{decision_colors.get(result['decision'], '')} **决策**: {result['decision']}")
            st.info(f"**置信度**: {result['confidence']:.2f}")
    
    # 详细分析
    if 'last_fusion_result' in st.session_state:
        result = st.session_state.last_fusion_result
        
        st.markdown("---")
        st.header("📈 详细分析")
        
        # 贡献度分析
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📝 文本贡献")
            text_features = result['features']['text']
            st.metric("情绪得分", f"{text_features['sentiment']:.2f}")
            st.metric("正面关键词", text_features['positive_count'])
            st.metric("负面关键词", text_features['negative_count'])
            st.metric("贡献度", f"{result['text_contribution']:.2f}")
        
        with col2:
            st.subheader("📊 图像贡献")
            image_features = result['features']['image']
            st.metric("趋势", f"{image_features['trend']:.2f}")
            st.metric("波动率", f"{image_features['volatility']:.2f}")
            st.metric("动量", f"{image_features['momentum']:.2f}")
            st.metric("贡献度", f"{result['image_contribution']:.2f}")
        
        with col3:
            st.subheader("📈 时序贡献")
            ts_features = result['features']['time_series']
            st.metric("MA比率", f"{ts_features['ma_ratio']:.2f}")
            st.metric("RSI", f"{ts_features['rsi']:.2f}")
            st.metric("MACD", f"{ts_features['macd']:.4f}")
            st.metric("贡献度", f"{result['ts_contribution']:.2f}")
        
        # 贡献度图表
        st.markdown("---")
        st.header("🎯 贡献度分析")
        
        contribution_data = {
            '模态': ['文本', '图像', '时间序列'],
            '贡献度': [
                result['text_contribution'],
                result['image_contribution'],
                result['ts_contribution']
            ]
        }
        
        fig = go.Figure(data=[
            go.Bar(
                x=contribution_data['模态'],
                y=contribution_data['贡献度'],
                marker_color=['#4CAF50', '#2196F3', '#FF9800']
            )
        ])
        
        fig.update_layout(
            title="各模态贡献度",
            yaxis_title="贡献度",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 历史记录
    st.markdown("---")
    st.header("📜 分析历史")
    
    history = system.get_history(limit=20)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['timestamp', 'stock_code', 'decision', 'confidence']],
            use_container_width=True
        )
        
        # 决策分布
        decision_counts = df['decision'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=decision_counts.index,
                values=decision_counts.values,
                hole=0.3
            )
        ])
        
        fig.update_layout(
            title="决策分布",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史记录")
    
    # 融合说明
    st.markdown("---")
    st.header("📋 融合机制说明")
    
    fusion_info = pd.DataFrame([
        {
            '模态': '文本',
            '特征': '情绪分析、关键词统计',
            '权重': '30%',
            '说明': '分析新闻、公告等文本的情绪倾向'
        },
        {
            '模态': '图像',
            '特征': 'K线图趋势、波动率、形态',
            '权重': '40%',
            '说明': '分析K线图的走势和形态特征'
        },
        {
            '模态': '时间序列',
            '特征': 'MA、RSI、MACD、布林带',
            '权重': '30%',
            '说明': '分析技术指标的时间序列特征'
        }
    ])
    
    st.dataframe(fusion_info, use_container_width=True)
    
    st.info("💡 系统通过跨模态注意力机制融合三种模态的特征，综合做出决策")