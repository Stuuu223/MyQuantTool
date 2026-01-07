"""资金搜索 - 游资席位追踪和分析"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(
    page_title="资金搜索",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💰 资金搜索")
st.markdown("追踪游资席位，发现市场主力")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.subheader("🔍 搜索条件")
    
    search_type = st.radio(
        "搜索类型",
        ["按游资", "按股票", "按板块"],
        captions=["搜索特定游资", "搜索股票上的游资", "搜索板块内游资"]
    )

tab1, tab2, tab3 = st.tabs(["🔍 高级搜索", "📊 数据对比", "📈 趋势分析"])

# ============== Tab 1: 高级搜索 ==============
with tab1:
    st.header("🔍 高级搜索")
    
    if st.session_state.get('search_type', '按游资') == '按游资':
        col1, col2 = st.columns([2, 1])
        
        with col1:
            capital_name = st.text_input(
                "输入游资名称",
                placeholder="例如：中泰证券杭州庆春路"
            )
        
        with col2:
            if st.button("🔍 搜索", key="search_btn"):
                st.info("正在搜索...")
    
    st.divider()
    
    # 搜索结果
    st.subheader("📊 搜索结果")
    
    results_df = pd.DataFrame({
        '游资名称': [
            '中泰证券杭州庆春路',
            '招商证券深圳福田',
            '华泰证券上海分公司',
            '中信证券北京总部',
            '申万宏源厚门'
        ],
        '最近30日出现次数': [15, 12, 8, 10, 6],
        '平均成交额(万)': [2450, 1850, 1200, 1600, 950],
        '成功率': ['72.3%', '68.5%', '65.2%', '70.1%', '62.8%'],
        '等级': ['一线', '一线', '二线', '一线', '二线'],
        '活跃度': ['高', '中高', '中', '中高', '中']
    })
    
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    st.subheader("📈 游资排行榜")
    
    col1, col2 = st.columns(2)
    
    with col1:
        top_df = results_df.nlargest(5, '平均成交额(万)')
        fig1 = px.bar(
            top_df,
            x='游资名称',
            y='平均成交额(万)',
            title="Top5 资金规模",
            labels={'平均成交额(万)': '成交额(万元)', '游资名称': '游资'}
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.bar(
            results_df,
            x='游资名称',
            y='最近30日出现次数',
            title="活跃度排序",
            labels={'最近30日出现次数': '出现次数', '游资名称': '游资'}
        )
        st.plotly_chart(fig2, use_container_width=True)

# ============== Tab 2: 数据对比 ==============
with tab2:
    st.header("📊 游资对比分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        capital1 = st.selectbox(
            "选择游资1",
            ['中泰证券杭州庆春路', '招商证券深圳福田', '华泰证券上海分公司'],
            key="cap1"
        )
    
    with col2:
        capital2 = st.selectbox(
            "选择游资2",
            ['招商证券深圳福田', '华泰证券上海分公司', '中泰证券杭州庆春路'],
            key="cap2"
        )
    
    st.divider()
    
    # 对比指标
    compare_df = pd.DataFrame({
        '指标': ['30日出现次数', '平均成交额', '成功率', '累计收益', '最大回撤', '风险等级'],
        capital1: [15, '2450万', '72.3%', '18.5%', '8.2%', '低'],
        capital2: [12, '1850万', '68.5%', '15.2%', '10.5%', '中']
    })
    
    st.dataframe(compare_df, use_container_width=True, hide_index=True)
    
    st.subheader("⚠️ 对比发现")
    col1, col2 = st.columns(2)
    
    col1.info(f"✅ {capital1} 出现频率更高，资金规模更大")
    col2.info(f"💡 {capital2} 成功率相对较低，但稳定性更好")

# ============== Tab 3: 趋势分析 ==============
with tab3:
    st.header("📈 游资趋势分析")
    
    selected_capital = st.selectbox(
        "选择游资查看趋势",
        ['中泰证券杭州庆春路', '招商证券深圳福田', '华泰证券上海分公司'],
        key="trend_capital"
    )
    
    time_period = st.selectbox(
        "时间周期",
        ["最近7天", "最近30天", "最近90天", "最近1年"]
    )
    
    st.divider()
    
    # FIX: Corrected array operations - use pd.Series for operations
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    frequency_raw = np.random.randint(5, 20, 30)
    trend_df = pd.DataFrame({
        'Date': dates,
        'Frequency': frequency_raw.cumsum() % 50,
        'Turnover': np.random.randint(1000, 3000, 30),
        'WinRate': np.random.uniform(0.6, 0.8, 30)
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.line(
            trend_df,
            x='Date',
            y='Frequency',
            title=f"{selected_capital} 出现频率趋势",
            labels={'Frequency': '出现次数', 'Date': '日期'}
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.line(
            trend_df,
            x='Date',
            y='WinRate',
            title="成功率趋势",
            labels={'WinRate': '成功率', 'Date': '日期'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 统计汇总
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均出现次数", f"{trend_df['Frequency'].mean():.0f}")
    col2.metric("平均成交额", f"{trend_df['Turnover'].mean():.0f}万")
    col3.metric("平均成功率", f"{trend_df['WinRate'].mean():.1%}")
    col4.metric("趋势", "📈 向上")

st.markdown("---")
st.caption("💰 资金追踪系统 v3.6.0")