"""深度分析 - 多维度股票研究"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="深度分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔬 深度分析")
st.markdown("从基本面、技术面、资金面深度研究股票")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.subheader("🎯 分析配置")
    
    stock = st.text_input(
        "股票代码",
        value="600519",
        placeholder="输入股票代码"
    )
    
    analysis_type = st.multiselect(
        "选择分析维度",
        ["基本面", "技术面", "资金面", "消息面", "风险评估"],
        default=["基本面", "技术面", "资金面"]
    )

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 基本面",
    "📈 技术面",
    "💰 资金面",
    "📰 消息面",
    "⚠️ 风险评估"
])

# ============== Tab 1: 基本面 ==============
with tab1:
    st.header("📊 基本面分析")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("PE 比率", "28.5", "-2.1")
    col2.metric("PB 比率", "8.2", "+0.5")
    col3.metric("ROE", "24.3%", "+1.2%")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 财务指标")
        financial_df = pd.DataFrame({
            '指标': ['营收', '净利润', '毛利率', '净利率', '资产负债率'],
            '2024Q3': ['1250亿', '285亿', '52.3%', '22.8%', '18.5%'],
            '同比增长': ['+15.2%', '+18.5%', '+2.1%', '+1.8%', '-2.3%']
        })
        st.dataframe(financial_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("💵 估值对比")
        valuation_df = pd.DataFrame({
            '公司': ['当前公司', '行业平均', '历史中位数'],
            'PE': [28.5, 22.3, 25.8],
            'PB': [8.2, 6.5, 7.2]
        })
        fig = px.bar(
            valuation_df,
            x='公司',
            y=['PE', 'PB'],
            title="估值对比分析",
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 2: 技术面 ==============
with tab2:
    st.header("📈 技术面分析")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("当前价格", "¥1850.5", "+2.3%")
    col2.metric("MA20", "¥1835.2", "-0.8%")
    col3.metric("RSI(14)", "58.3", "中性")
    col4.metric("MACD", "金叉", "看涨")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 技术指标")
        
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = 1800 + (range(60) * 0.8 + pd.Series(range(60)).rolling(5).mean())
        
        tech_df = pd.DataFrame({
            'Date': dates,
            'Price': prices,
            'MA5': prices.rolling(5).mean(),
            'MA20': prices.rolling(20).mean()
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tech_df['Date'],
            y=tech_df['Price'],
            name='收盘价',
            mode='lines'
        ))
        fig.add_trace(go.Scatter(
            x=tech_df['Date'],
            y=tech_df['MA5'],
            name='MA5',
            mode='lines'
        ))
        fig.add_trace(go.Scatter(
            x=tech_df['Date'],
            y=tech_df['MA20'],
            name='MA20',
            mode='lines'
        ))
        fig.update_layout(title="K线走势", hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔍 形态识别")
        patterns = pd.DataFrame({
            '形态': ['上升三角形', '双顶', '抄底信号', '突破形态'],
            '信号': ['看涨', '看跌', '中性', '看涨'],
            '可信度': ['70%', '45%', '55%', '75%']
        })
        st.dataframe(patterns, use_container_width=True, hide_index=True)

# ============== Tab 3: 资金面 ==============
with tab3:
    st.header("💰 资金面分析")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("主力净流入", "+2.5亿", "+8.2%")
    col2.metric("散户净流入", "-1.2亿", "-5.3%")
    col3.metric("机构持仓", "32.5%", "+2.1%")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💵 资金流向")
        
        flow_df = pd.DataFrame({
            'Date': pd.date_range(end=datetime.now(), periods=20, freq='D'),
            'Main Flow': pd.Series(range(20)) * 0.3 - 1.5,
            'Retail Flow': -pd.Series(range(20)) * 0.15 + 0.5
        })
        
        fig = px.bar(
            flow_df,
            x='Date',
            y=['Main Flow', 'Retail Flow'],
            title="主力 vs 散户资金对比",
            labels={'value': '净流入(亿元)', 'Date': '日期'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 持仓结构")
        
        holdings = pd.DataFrame({
            'Type': ['基金', '社保', '产业方', '股东', '其他'],
            'Ratio': [15, 8, 28, 35, 14]
        })
        
        fig = px.pie(
            holdings,
            names='Type',
            values='Ratio',
            title="主要股东持仓"
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 4: 消息面 ==============
with tab4:
    st.header("📰 消息面分析")
    
    st.subheader("📢 最新公告")
    
    news_df = pd.DataFrame({
        '时间': ['2026-01-07', '2026-01-06', '2026-01-05', '2026-01-02'],
        '标题': [
            '发布2025年度业绩预告',
            '完成大额并购交易',
            '获得新产品认证',
            '入选MSCI指数'
        ],
        '类型': ['业绩预告', '重大事件', '新产品', '指数调整'],
        '影响': ['中性', '利好', '利好', '利好']
    })
    
    st.dataframe(news_df, use_container_width=True, hide_index=True)
    
    st.subheader("😊 市场情绪")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sentiment_df = pd.DataFrame({
            'Sentiment': ['利好', '中性', '利空'],
            'Count': [65, 25, 10]
        })
        fig = px.pie(
            sentiment_df,
            names='Sentiment',
            values='Count',
            title="市场评论情绪分布"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔮 预期")
        col1, col2 = st.columns(2)
        col1.metric("看涨投资者", "68%", "+5%")
        col2.metric("看跌投资者", "12%", "-2%")

# ============== Tab 5: 风险评估 ==============
with tab5:
    st.header("⚠️ 风险评估")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("综合风险等级", "中低", "✅")
    col2.metric("波动率", "22.5%", "偏低")
    col3.metric("最大回撤", "8.5%", "可控")
    col4.metric("夏普比率", "1.85", "良好")
    
    st.divider()
    
    st.subheader("🚨 风险因子")
    
    risks = pd.DataFrame({
        '风险因子': ['政策风险', '产业风险', '竞争风险', '流动性风险', '汇率风险'],
        '风险等级': ['中', '低', '中', '低', '中'],
        '影响度': ['20%', '15%', '25%', '10%', '30%'],
        '应对措施': ['关注政策', '持续研发', '提升竞争力', '保持流动', '对冲操作']
    })
    
    st.dataframe(risks, use_container_width=True, hide_index=True)
    
    st.subheader("📊 风险评分")
    
    risk_scores = pd.DataFrame({
        'Risk Type': ['系统性风险', '非系统性风险', '流动性风险', '信用风险'],
        'Score': [4, 5, 3, 2]
    })
    
    fig = px.bar(
        risk_scores,
        x='Risk Type',
        y='Score',
        title="风险评分（1-10分制）",
        labels={'Score': '风险评分', 'Risk Type': '风险类型'}
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("🔬 深度研究系统 v3.6.0")
