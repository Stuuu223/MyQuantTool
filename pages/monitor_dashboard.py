"""实时监控面板 - 市场全景监控"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(
    page_title="实时监控面板",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 实时监控面板")
st.markdown("全市场行情监控、龙虎榜跟踪、资金流向分析")
st.markdown("---")

# 自动刷新
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

# 侧边栏设置
with st.sidebar:
    st.subheader("🔔 监控设置")
    
    auto_refresh = st.toggle("自动刷新", value=True)
    refresh_interval = st.selectbox(
        "刷新频率",
        ["1分钟", "5分钟", "15分钟", "30分钟"]
    )
    
    alert_enabled = st.toggle("启用告警", value=True)
    alert_threshold = st.slider(
        "告警涨幅阈值",
        min_value=1,
        max_value=20,
        value=10,
        step=1
    )

# 主体标签页
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 市场概览",
    "🏆 龙虎榜",
    "💰 资金流向",
    "⚡ 涨停池",
    "🎯 智能告警"
])

# ============== Tab 1: 市场概览 ==============
with tab1:
    st.header("🏠 市场概览")
    
    # 三大指数
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("上证指数", "3250.5", "+1.2%", "🔴")
    col2.metric("深证成指", "10850.2", "+0.8%", "🟢")
    col3.metric("创业板", "2150.8", "+2.1%", "🟢")
    col4.metric("沪深300", "3680.5", "+1.5%", "🟢")
    col5.metric("两市成交", "1.2万亿", "+5%", "🟢")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 涨跌家数")
        market_stats = pd.DataFrame({
            'Status': ['上升', '平盘', '下降'],
            'Count': [2240, 85, 1045]
        })
        fig = px.pie(
            market_stats,
            names='Status',
            values='Count',
            title="A股涨跌分布"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏢 行业涨幅")
        sectors = pd.DataFrame({
            'Sector': ['新能源', '医药', '消费', '电子', '金融', '房地产'],
            'Change': [3.2, 1.8, 0.5, -0.2, -1.2, -2.5]
        })
        fig = px.barh(
            sectors,
            x='Change',
            y='Sector',
            title="行业涨跌排序",
            labels={'Change': '涨幅(%)', 'Sector': '行业'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    st.subheader("📊 分钟成交额")
    
    # 模拟成交额数据
    minutes = pd.date_range(end=datetime.now(), periods=120, freq='1min')
    volumes = np.random.randint(500, 1500, 120)
    
    volume_df = pd.DataFrame({
        'Time': minutes,
        'Volume': volumes
    })
    
    fig = px.area(
        volume_df,
        x='Time',
        y='Volume',
        title="实时成交量",
        labels={'Volume': '成交额(万)', 'Time': '时间'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ============== Tab 2: 龙虎榜 ==============
with tab2:
    st.header("🏆 龙虎榜实时跟踪")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("上榜股票", "45", "+5 vs 昨日")
    col2.metric("平均涨幅", "3.2%", "+0.5%")
    col3.metric("资金净流入", "8.2亿", "+2.1亿")
    
    st.divider()
    
    st.subheader("📋 今日龙虎榜")
    
    lhb_df = pd.DataFrame({
        '股票': ['股票A', '股票B', '股票C', '股票D', '股票E'],
        '代码': ['600001', '000002', '000333', '600519', '601988'],
        '价格': ['10.25', '18.50', '25.80', '1850.50', '35.25'],
        '涨幅': ['+3.2%', '+5.8%', '+2.1%', '+1.5%', '+4.3%'],
        '成交额': ['2.5亿', '4.2亿', '1.8亿', '5.5亿', '1.2亿'],
        '上榜家数': [8, 12, 6, 10, 7],
        '类型': ['机构抱团', '游资合作', '机构接力', '游资狙击', '机构建仓']
    })
    
    st.dataframe(lhb_df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 上榜类型分布")
        
        types_dist = pd.DataFrame({
            'Type': ['机构抱团', '游资合作', '机构接力', '游资狙击'],
            'Count': [12, 8, 15, 10]
        })
        
        fig = px.pie(
            types_dist,
            names='Type',
            values='Count',
            title="上榜类型分布"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 资金净流")
        
        net_flow = pd.DataFrame({
            'Capital': ['游资A', '机构B', '游资C', '机构D'],
            'Flow': [2.5, -1.2, 1.8, 0.5]
        })
        
        fig = px.bar(
            net_flow,
            x='Capital',
            y='Flow',
            title="游资资金净流",
            labels={'Flow': '净流入(亿)', 'Capital': '游资/机构'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 3: 资金流向 ==============
with tab3:
    st.header("💰 市场资金流向")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("主力净流入", "+25.2亿", "+8.2%")
    col2.metric("散户净流入", "-12.5亿", "-5.3%")
    col3.metric("机构净流入", "+8.5亿", "+2.1%")
    col4.metric("游资净流入", "+3.2亿", "+1.5%")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 资金类型流向")
        
        # 时间序列资金流向
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        flows = pd.DataFrame({
            'Date': dates,
            'Main': np.random.randint(-50, 100, 30),
            'Retail': np.random.randint(-30, 30, 30),
            'Institution': np.random.randint(-20, 50, 30)
        })
        
        fig = px.line(
            flows,
            x='Date',
            y=['Main', 'Retail', 'Institution'],
            title="资金流向趋势",
            labels={'value': '流入(亿)', 'Date': '日期'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏢 行业资金流向")
        
        sector_flow = pd.DataFrame({
            'Sector': ['新能源', '医药', '消费', '科技', '金融'],
            'Flow': [12.5, 8.2, -3.5, 6.8, -2.1]
        })
        
        fig = px.bar(
            sector_flow,
            x='Sector',
            y='Flow',
            title="行业资金净流（亿元）",
            labels={'Flow': '净流入', 'Sector': '行业'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 4: 涨停池 ==============
with tab4:
    st.header("⚡ 涨停池监控")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("今日涨停", "68", "+12 vs 昨日")
    col2.metric("一字板", "25", "-5 vs 昨日")
    col3.metric("跳空高开", "35", "+8 vs 昨日")
    
    st.divider()
    
    st.subheader("📋 涨停池")
    
    limit_up = pd.DataFrame({
        '股票': ['T股1', 'T股2', 'T股3', 'T股4', 'T股5'],
        '代码': ['600001', '000002', '000333', '600519', '601988'],
        '价格': ['10.50', '19.00', '26.29', '1885.50', '36.00'],
        '涨幅': ['+10.0%', '+10.0%', '+10.0%', '+10.0%', '+10.0%'],
        '板强': [3, 5, 2, 8, 1],
        '成交量': ['2.1M', '4.5M', '1.2M', '3.8M', '0.8M']
    })
    
    st.dataframe(limit_up, use_container_width=True, hide_index=True)

# ============== Tab 5: 智能告警 ==============
with tab5:
    st.header("🎯 智能告警系统")
    
    st.subheader("📢 实时告警")
    
    alerts = pd.DataFrame({
        '时间': ['09:35', '10:12', '10:45', '11:20', '11:58'],
        '告警类型': ['涨停突破', '资金异常', '龙虎榜新增', '快速跳水', '放量涨停'],
        '股票': ['股票A', '股票B', '股票C', '股票D', '股票E'],
        '信号': ['看涨', '关注', '看涨', '看跌', '看涨'],
        '强度': ['强', '中', '强', '中', '强']
    })
    
    st.dataframe(alerts, use_container_width=True, hide_index=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 告警设置")
        
        st.checkbox("涨停突破告警", value=True)
        st.checkbox("龙虎榜新增告警", value=True)
        st.checkbox("资金异常告警", value=True)
        st.checkbox("技术面突破告警", value=True)
    
    with col2:
        st.subheader("📊 告警统计")
        
        alert_stats = pd.DataFrame({
            'Type': ['涨停突破', '资金异常', '龙虎榜', '技术突破'],
            'Count': [12, 8, 15, 10]
        })
        
        fig = px.bar(
            alert_stats,
            x='Type',
            y='Count',
            title="告警类型分布",
            labels={'Count': '告警次数', 'Type': '告警类型'}
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(f"📊 监控面板 v3.6.0 | 最后更新: {st.session_state.last_update.strftime('%H:%M:%S')}")
