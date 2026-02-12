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
from logic.sentiment_analyzer import SentimentAnalyzer
from logic.data_manager import DataManager


def render_market_sentiment_tab(db, config):
    """渲染市场情绪分析标签页"""
    st.subheader("🧠 市场情绪分析")
    
    # 初始化模块
    sentiment_calculator = MarketSentimentIndexCalculator()
    
    # 🆕 V10.0 新增：使用 SentimentAnalyzer 获取真实市场数据
    try:
        dm = DataManager()
        sa = SentimentAnalyzer(dm)
        market_mood = sa.analyze_market_mood(force_refresh=True)
    except Exception as e:
        st.error(f"获取市场情绪数据失败: {e}")
        market_mood = None
    
    # 🆕 V10.0 新增：显示真实市场情绪数据
    if market_mood:
        st.subheader("📊 实时市场情绪")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("市场温度", sa.get_market_temperature(), f"得分: {market_mood['score']}")
        col2.metric("涨停家数", f"{market_mood['limit_up']}家")
        col3.metric("跌停家数", f"{market_mood['limit_down']}家")
        col4.metric("上涨家数", f"{market_mood['up']}家")
        col5.metric("下跌家数", f"{market_mood['down']}家")
        
        # 🆕 V10.0 新增：炸板统计
        st.subheader("💥 炸板统计")
        col1, col2 = st.columns(2)
        col1.metric("炸板家数", f"{market_mood['zhaban_count']}家", 
                   help="最高价触及涨停但现价低于涨停价的股票数量")
        col2.metric("炸板率", f"{market_mood['zhaban_rate']}%", 
                   help="炸板数 / (涨停数 + 炸板数)，反映市场抛压和分歧程度")
        
        # 🆕 V10.0 深化：炸板类型统计
        if market_mood['zhaban_count'] > 0:
            col1, col2, col3 = st.columns(3)
            col1.metric("良性炸板", f"{market_mood.get('benign_zhaban_count', 0)}家", 
                       help="烂板/高位震荡，回撤<2%，可能是主力洗盘")
            col2.metric("恶性炸板", f"{market_mood.get('malignant_zhaban_count', 0)}家", 
                       help="炸板回落，回撤>=2%，可能是主力出货")
            col3.metric("平均回撤", f"{market_mood.get('avg_drop_pct', 0)}%", 
                       help="炸板股票的平均回撤幅度")
            
            # 炸板类型解读
            malignant_ratio = market_mood.get('malignant_zhaban_count', 0) / market_mood['zhaban_count'] * 100
            if malignant_ratio > 60:
                st.error("🔴 恶性炸板占比高（>60%），市场抛压极大，防止A杀，建议空仓")
            elif malignant_ratio > 40:
                st.warning("⚠️ 恶性炸板占比较高（40%-60%），市场分歧严重，建议防守")
            else:
                st.info("🟢 良性炸板占主导（<40%），市场分歧较小，可关注回封机会")
        
        # 炸板率解读
        if market_mood['zhaban_rate'] > 30:
            st.warning("⚠️ 炸板率较高（>30%），市场抛压极大，主力分歧严重，建议防守")
        elif market_mood['zhaban_rate'] > 20:
            st.info("📉 炸板率中等（20%-30%），市场有一定分歧，谨慎操作")
        else:
            st.success("✅ 炸板率较低（<20%），市场分歧较小，情绪较好")
        
        st.divider()
    
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
    
    # 计算综合情绪指数（加权平均）
    # 默认权重：新闻 0.35, 社交 0.25, 量价 0.25, 价格 0.15
    news_weight = 0.35
    social_weight = 0.25
    volume_weight = 0.25
    price_weight = 0.15

    sentiment_data['composite_index'] = (
        news_weight * sentiment_data['news_sentiment'] +
        social_weight * sentiment_data['social_sentiment'] +
        volume_weight * sentiment_data['volume_sentiment'] +
        price_weight * sentiment_data['price_sentiment']
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
        '权重': [news_weight, social_weight, volume_weight, price_weight],
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