"""
市场情绪分析模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any

from logic.market_sentiment import MarketSentimentIndexCalculator


def render_market_sentiment_tab(db, config):
    """渲染市场情绪分析标签页"""
    st.subheader("🧠 市场情绪分析")
    
    # 初始化模块
    sentiment_calculator = MarketSentimentIndexCalculator()
    
    st.subheader("市场情绪指数")
    
    # 生成模拟情绪数据
    dates = pd.date_range(end=datetime.now(), periods=30)
    
    # 创建模拟情绪数据
    np.random.seed(42)
    news_sentiment = np.random.uniform(-1, 1, 30)
    social_sentiment = np.random.uniform(-1, 1, 30)
    volume_sentiment = np.random.uniform(-1, 1, 30)
    price_sentiment = np.random.uniform(-1, 1, 30)
    
    sentiment_data = pd.DataFrame({
        'date': dates,
        'news_sentiment': news_sentiment,
        'social_sentiment': social_sentiment,
        'volume_sentiment': volume_sentiment,
        'price_sentiment': price_sentiment
    }).set_index('date')
    
    # 计算综合情绪指数
    sentiment_data['composite_index'] = sentiment_calculator.calculate_composite_index(
        sentiment_data['news_sentiment'],
        sentiment_data['social_sentiment'],
        sentiment_data['volume_sentiment'],
        sentiment_data['price_sentiment']
    )
    
    st.write("情绪指标趋势:")
    st.line_chart(sentiment_data[['news_sentiment', 'social_sentiment', 'volume_sentiment', 'price_sentiment', 'composite_index']])
    
    # 显示最新情绪数据
    latest_data = sentiment_data.iloc[-1]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("新闻情绪", f"{latest_data['news_sentiment']:.3f}")
    col2.metric("社交媒体情绪", f"{latest_data['social_sentiment']:.3f}")
    col3.metric("量价情绪", f"{latest_data['volume_sentiment']:.3f}")
    col4.metric("价格情绪", f"{latest_data['price_sentiment']:.3f}")
    col5.metric("综合情绪指数", f"{latest_data['composite_index']:.3f}")
    
    # 情绪构成分析
    st.subheader("情绪构成分析")
    composition_data = {
        '指标': ['新闻情绪', '社交媒体情绪', '量价情绪', '价格情绪'],
        '权重': [
            sentiment_calculator.news_weight,
            sentiment_calculator.social_weight,
            sentiment_calculator.volume_weight,
            sentiment_calculator.price_weight
        ],
        '当前值': [
            latest_data['news_sentiment'],
            latest_data['social_sentiment'],
            latest_data['volume_sentiment'],
            latest_data['price_sentiment']
        ]
    }
    
    composition_df = pd.DataFrame(composition_data)
    fig = px.bar(composition_df, x='指标', y='当前值', title='各情绪指标当前值')
    st.plotly_chart(fig, use_container_width=True)
    
    # 情绪分布直方图
    st.subheader("情绪分布")
    all_sentiment_values = np.concatenate([
        sentiment_data['news_sentiment'].values,
        sentiment_data['social_sentiment'].values,
        sentiment_data['volume_sentiment'].values,
        sentiment_data['price_sentiment'].values
    ])
    
    fig_hist = px.histogram(x=all_sentiment_values, nbins=20, title='情绪分数分布')
    st.plotly_chart(fig_hist, use_container_width=True)


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="市场情绪", layout="wide")
    render_market_sentiment_tab(None, {})