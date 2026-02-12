"""
实时情绪感知系统 UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.realtime_sentiment_system import RealtimeSentimentProcessor
from logic.data_manager import DataManager


def render_realtime_sentiment_tab(db: DataManager, config):
    """渲染实时情绪感知标签页"""
    
    st.title("🧠 实时情绪感知系统")
    st.markdown("---")
    
    # 初始化处理器
    if 'sentiment_processor' not in st.session_state:
        st.session_state.sentiment_processor = RealtimeSentimentProcessor()
    
    processor = st.session_state.sentiment_processor
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 情绪输入
        st.subheader("📊 情绪输入")
        news_score = st.slider("新闻情绪", -1.0, 1.0, 0.0, 0.1, help="新闻情绪得分 (-1 到 1)")
        social_score = st.slider("社交媒体情绪", -1.0, 1.0, 0.0, 0.1, help="社交媒体情绪得分 (-1 到 1)")
        price_score = st.slider("价格情绪", -1.0, 1.0, 0.0, 0.1, help="价格情绪得分 (-1 到 1)")
        fund_flow_score = st.slider("资金流向情绪", -1.0, 1.0, 0.0, 0.1, help="资金流向情绪得分 (-1 到 1)")
        
        # 当前仓位
        current_position = st.slider("当前仓位", 0.0, 1.0, 0.5, 0.1, help="当前仓位比例")
        
        # 权重设置
        st.subheader("⚖️ 权重设置")
        with st.expander("调整权重"):
            news_weight = st.slider("新闻权重", 0.0, 1.0, 0.35, 0.05)
            social_weight = st.slider("社交媒体权重", 0.0, 1.0, 0.25, 0.05)
            price_weight = st.slider("价格权重", 0.0, 1.0, 0.25, 0.05)
            fund_weight = st.slider("资金流向权重", 0.0, 1.0, 0.15, 0.05)
            
            if st.button("应用权重"):
                total = news_weight + social_weight + price_weight + fund_weight
                if abs(total - 1.0) > 0.01:
                    st.error(f"权重总和必须为1，当前为{total:.2f}")
                else:
                    processor.set_weights({
                        'news_sentiment': news_weight,
                        'social_sentiment': social_weight,
                        'price_sentiment': price_weight,
                        'fund_flow_sentiment': fund_weight
                    })
                    st.success("权重已更新")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("情绪状态", processor.emotion_state.current_state)
    
    with col2:
        state_info = processor.emotion_state.get_state_info()
        st.metric("情绪得分", f"{state_info['state_score']:.2f}")
    
    with col3:
        st.metric("历史记录", f"{state_info['history_size']} 条")
    
    # 处理情绪
    if st.button("🔄 更新情绪", use_container_width=True):
        with st.spinner("正在处理情绪..."):
            result = processor.process_sentiment(
                news_score=news_score,
                social_score=social_score,
                price_score=price_score,
                fund_flow_score=fund_flow_score,
                current_position=current_position
            )
            
            st.session_state.last_sentiment_result = result
            
            # 显示结果
            st.success("情绪已更新！")
    
    # 显示最新结果
    if 'last_sentiment_result' in st.session_state:
        result = st.session_state.last_sentiment_result
        
        st.markdown("---")
        st.header("📈 分析结果")
        
        # 情绪状态
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 情绪状态")
            st.info(f"**当前状态**: {result['emotion_state']}")
            st.info(f"**情绪得分**: {result['sentiment_score']:.2f}")
            
            if result['state_update'].get('transition'):
                st.warning(f"⚠️ 状态转换: {result['state_update']['old_state']} → {result['state_update']['new_state']}")
        
        with col2:
            st.subheader("💡 策略建议")
            strategy = result['strategy']
            st.info(f"**策略**: {strategy['strategy']}")
            st.info(f"**风险等级**: {strategy['risk_level']}")
            st.info(f"**操作**: {strategy['action']}")
            st.info(f"**说明**: {strategy['description']}")
        
        # 仓位建议
        st.subheader("📊 仓位建议")
        position = result['position_suggestion']
        
        col1, col2, col3 = st.columns(3)
        col1.metric("当前仓位", f"{position['current_position']:.0%}")
        col2.metric("目标仓位", f"{position['target_position']:.0%}")
        col3.metric("操作", position['action'])
        
        if position['action'] != '保持':
            delta = position['delta']
            if position['action'] == '加仓':
                st.success(f"建议加仓 {delta:.0%}")
            else:
                st.warning(f"建议减仓 {delta:.0%}")
        
        # 异常检测
        if result['anomaly']:
            st.error(f"⚠️ 异常检测: {result['anomaly']['message']}")
    
    # 情绪历史
    st.markdown("---")
    st.header("📜 情绪历史")
    
    history = processor.get_history(limit=50)
    
    if history:
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 情绪得分图表
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['sentiment_score'],
            mode='lines+markers',
            name='情绪得分',
            line=dict(color='#FF6B6B', width=2)
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        fig.update_layout(
            title="情绪得分历史",
            xaxis_title="时间",
            yaxis_title="情绪得分",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 历史记录表格
        st.subheader("详细记录")
        st.dataframe(
            df[['timestamp', 'sentiment_score', 'emotion_state', 'strategy', 'position']],
            use_container_width=True
        )
    else:
        st.info("暂无历史记录")
    
    # 策略映射表
    st.markdown("---")
    st.header("📋 策略映射表")
    
    mapping_data = []
    for state, strategy in processor.strategy_mapper.mapping.items():
        mapping_data.append({
            '情绪状态': state,
            '策略': strategy['strategy'],
            '目标仓位': f"{strategy['position']:.0%}",
            '风险等级': strategy['risk_level'],
            '操作': strategy['action'],
            '说明': strategy['description']
        })
    
    st.dataframe(
        pd.DataFrame(mapping_data),
        use_container_width=True
    )