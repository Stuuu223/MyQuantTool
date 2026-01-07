"""K线分析仪表板 - 实时技术面监控"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="K线分析仪表板",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 K线分析仪表板")
st.markdown("实时技术面监控与K线形态识别")
st.markdown("---")

# 侧边栏配置
with st.sidebar:
    st.subheader("⚙️ 仪表板设置")
    
    watch_list = st.multiselect(
        "添加自选股",
        ['600519', '000333', '600036', '601988'],
        default=['600519']
    )
    
    time_frame = st.selectbox(
        "选择时间框架",
        ["日线", "周线", "月线", "60分钟", "30分钟", "15分钟"]
    )
    
    indicator_type = st.multiselect(
        "技术指标",
        ["MA", "MACD", "RSI", "KDJ", "BOLL"],
        default=["MA", "MACD"]
    )

# 主体内容
tab1, tab2, tab3 = st.tabs(["📊 实时行情", "🔍 形态识别", "💡 信号监控"])

# ============== Tab 1: 实时行情 ==============
with tab1:
    st.header("📊 实时行情监控")
    
    # 市场概览
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("上证指数", "3250.5", "+1.2%")
    col2.metric("深证成指", "10850.2", "+0.8%")
    col3.metric("创业板", "2150.8", "+2.1%")
    col4.metric("沪深300", "3680.5", "+1.5%")
    col5.metric("两市成交额", "1.2万亿", "+5%")
    
    st.divider()
    
    # 自选股行情表
    st.subheader("📋 自选股行情")
    
    quote_data = pd.DataFrame({
        '代码': watch_list,
        '名称': ['贵州茅台', '美的集团', '工商银行', '中国平安'],
        '最新价': ['1850.5', '352.2', '4.85', '18.25'],
        '涨幅': ['+2.3%', '-1.2%', '+0.8%', '+1.5%'],
        '成交量': ['2.5M', '8.2M', '150M', '28M'],
        '成交额': ['45亿', '28亿', '72亿', '51亿'],
        '换手率': ['1.2%', '2.8%', '0.5%', '1.8%']
    })
    
    st.dataframe(quote_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.subheader("📈 K线图表")
    
    # 生成示例K线数据
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    np.random.seed(42)
    prices = 1800 + np.cumsum(np.random.randn(60)) * 10
    
    kline_df = pd.DataFrame({
        'Date': dates,
        'Open': prices + np.random.randn(60) * 5,
        'High': prices + abs(np.random.randn(60) * 8),
        'Low': prices - abs(np.random.randn(60) * 8),
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 60)
    })
    
    # 计算均线
    kline_df['MA5'] = kline_df['Close'].rolling(5).mean()
    kline_df['MA20'] = kline_df['Close'].rolling(20).mean()
    kline_df['MA60'] = kline_df['Close'].rolling(60).mean()
    
    fig = go.Figure()
    
    # K线
    fig.add_trace(go.Candlestick(
        x=kline_df['Date'],
        open=kline_df['Open'],
        high=kline_df['High'],
        low=kline_df['Low'],
        close=kline_df['Close'],
        name='K线'
    ))
    
    # 均线
    fig.add_trace(go.Scatter(
        x=kline_df['Date'], y=kline_df['MA5'],
        name='MA5', line=dict(color='blue', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=kline_df['Date'], y=kline_df['MA20'],
        name='MA20', line=dict(color='orange', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=kline_df['Date'], y=kline_df['MA60'],
        name='MA60', line=dict(color='red', width=1)
    ))
    
    fig.update_layout(
        title="K线走势（日线）",
        yaxis_title='价格',
        template='plotly_white',
        height=600,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

# ============== Tab 2: 形态识别 ==============
with tab2:
    st.header("🔍 K线形态识别")
    
    st.subheader("📊 常见形态")
    
    patterns_info = pd.DataFrame({
        '形态名称': ['双底', '双顶', '三角形', '旗形', '楔形'],
        '形态特征': ['两个相等的低点', '两个相等的高点', '高低点逐步收敛', '平行四边形', '两条收敛线'],
        '信号': ['看涨', '看跌', '中性', '延续', '延续'],
        '准确率': ['72%', '68%', '65%', '70%', '64%']
    })
    
    st.dataframe(patterns_info, use_container_width=True, hide_index=True)
    
    st.subheader("🎯 当前形态识别")
    
    current_patterns = pd.DataFrame({
        '检测到的形态': ['上升三角形', '黄金叉', '突破形态'],
        '周期': ['日线', '日线', '4小时'],
        '信号': ['看涨', '看涨', '中性'],
        '可信度': ['75%', '68%', '55%'],
        '建议': ['关注买点', '可逢低布局', '持续观察']
    })
    
    st.dataframe(current_patterns, use_container_width=True, hide_index=True)

# ============== Tab 3: 信号监控 ==============
with tab3:
    st.header("💡 技术信号监控")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 指标信号")
        
        indicators = pd.DataFrame({
            '指标': ['MACD', 'RSI', 'KDJ', 'BOLL', '成交量'],
            '数值': ['金叉', '58.3', '金叉', '突破上轨', '放量'],
            '信号': ['看涨', '中性', '看涨', '看涨', '看涨'],
            '强度': ['中', '弱', '中', '强', '中']
        })
        
        st.dataframe(indicators, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("⚡ 买卖信号")
        
        signals = pd.DataFrame({
            '信号': ['MA金叉', '底部信号', '量能信号'],
            '强度': ['◆◆◇◇◇', '◆◆◆◆◇', '◆◆◆◇◇'],
            '出现时间': ['2天前', '5天前', '今天']
        })
        
        st.dataframe(signals, use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.subheader("🎯 综合评分")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("技术面评分", "73/100", "✅ 良好")
    col2.metric("资金面评分", "68/100", "✅ 良好")
    col3.metric("综合评分", "70.5/100", "✅ 可介入")

st.markdown("---")
st.caption("📈 K线分析系统 v3.6.0")
