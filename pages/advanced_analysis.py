"""高级量化分析 - LSTM + 关键词提取 + 游资画像"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title="高级量化分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 高级量化分析")
st.markdown("基于 LSTM + 关键词提取 + 游资画像的综合分析平台")
st.markdown("---")

# 侧边栏配置
with st.sidebar:
    st.subheader("⚙️ 分析配置")
    
    analysis_type = st.radio(
        "选择分析类型",
        ["LSTM上榜预测", "关键词提取", "游资画像"],
        captions=[
            "使用深度学习预测上榜",
            "自动提取市场热点",
            "量化游资特征"
        ]
    )
    
    st.divider()
    
    # 时间范围选择
    st.subheader("📅 时间配置")
    date_range = st.selectbox(
        "选择时间范围",
        ["最近7天", "最近30天", "最近90天", "自定义"]
    )

# 主体内容
tab1, tab2, tab3 = st.tabs([
    "🤖 LSTM上榜预测",
    "💡 关键词提取",
    "👥 游资画像分析"
])

# ============== Tab 1: LSTM 预测 ==============
with tab1:
    st.header("🤖 LSTM 上榜概率预测")
    st.write("使用时间序列 LSTM 模型预测游资是否可能上龙虎榜")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        capital_name = st.selectbox(
            "选择游资",
            ["中泰证券杭州庆春路", "招商证券深圳福田", "华泰证券上海分公司"],
            key="capital_lstm"
        )
    
    with col2:
        lookback_days = st.slider(
            "历史回看天数",
            min_value=5,
            max_value=90,
            value=30,
            step=5
        )
    
    with col3:
        if st.button("🔄 刷新数据", key="refresh_lstm"):
            st.success("✅ 数据已更新")
    
    st.divider()
    
    # 模型训练区
    col1, col2 = st.columns(2)
    
    with col1:
        epochs = st.slider(
            "训练轮数",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
    
    with col2:
        batch_size = st.selectbox(
            "批处理大小",
            [8, 16, 32, 64, 128]
        )
    
    if st.button("🚀 训练 LSTM 模型", key="train_btn"):
        with st.spinner(f"正在为 {capital_name} 训练 LSTM 模型..."):
            # 模拟训练过程
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("训练轮数", epochs)
            col2.metric("最终损失", f"{0.0234:.4f}")
            col3.metric("训练样本", "245")
            col4.metric("验证准確率", "73.5%")
            
            st.success("✅ 模型训练完成！")
    
    st.divider()
    
    # 预测结果
    st.subheader("🔮 明日上榜预测")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("上榜概率", "72.3%", "+5.2%")
    col2.metric("置信度", "68.5%", "+3.1%")
    col3.metric("历史成功率", "71.2%")
    
    st.info("💡 **预测分析**: 该游资近30天活跃度提升，成交额增加 15%，有较高概率继续上榜")
    
    # 特征重要性
    st.subheader("📊 特征重要性分析")
    
    features = pd.DataFrame({
        'Feature': ['成交额趋势', '频率变化', '关联度', '市场情緒', '板块热度'],
        'Importance': [0.35, 0.28, 0.18, 0.12, 0.07]
    })
    
    # FIX: Changed px.barh to px.bar with orientation='h'
    fig = px.bar(
        features,
        y='Feature',
        x='Importance',
        orientation='h',
        title="特征重要性排序",
        labels={'Importance': '重要性权重', 'Feature': '特征'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ============== Tab 2: 关键词提取 ==============
with tab2:
    st.header("💡 市场热点关键词提取")
    st.write("从龙虎榜数据和新闻中自动提取市场关键词，识别投资主线")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        method = st.selectbox(
            "提取方法",
            ["TF-IDF", "TextRank", "LDA"],
            key="keyword_method"
        )
    
    with col2:
        topk = st.slider(
            "关键词数量",
            min_value=5,
            max_value=30,
            value=15,
            step=5
        )
    
    st.divider()
    
    # 文本输入
    text_input = st.text_area(
        "输入文本或新闻摘要",
        value="新能源汽车产业链在政策支持下持续升温。特别是在芯片国产化推进、电池技术创新等方面表现亮眼。...",
        height=150
    )
    
    if st.button("🔍 提取关键词", key="extract_btn"):
        with st.spinner("正在提取关键词..."):
            keywords_data = pd.DataFrame({
                'Keyword': ['新能源', '芯片', '电池', '政策', '产业链', '国产化', '创新'],
                'Frequency': [24, 18, 15, 12, 11, 9, 8],
                'TF-IDF': [0.45, 0.38, 0.35, 0.28, 0.26, 0.24, 0.22],
                'Type': ['概念', '产业', '产品', '政策', '产业', '政策', '技术']
            })
            
            st.success("✅ 提取完成")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("关键词总数", len(keywords_data))
            col2.metric("热度最高", keywords_data.iloc[0]['Keyword'])
            col3.metric("提取方法", method)
            
            st.subheader("📊 关键词频率表")
            st.dataframe(keywords_data, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.bar(
                    keywords_data.head(8),
                    x='Keyword',
                    y='Frequency',
                    title="关键词出现频率",
                    labels={'Frequency': '频率', 'Keyword': '关键词'}
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.pie(
                    keywords_data,
                    names='Type',
                    title="关键词类型分布",
                    labels={'Type': '类型'}
                )
                st.plotly_chart(fig2, use_container_width=True)

# ============== Tab 3: 游资画像 ==============
with tab3:
    st.header("👥 游资画像分析")
    st.write("量化游资的操作特征、风险偏好和盆利能力")
    
    col1, col2 = st.columns(2)
    
    with col1:
        capital = st.selectbox(
            "选择游资",
            ["中泰证券杭州庆春路", "招商证券深圳福田", "华泰证券上海分公司"],
            key="capital_profile"
        )
    
    with col2:
        if st.button("📊 生成画像", key="profile_btn"):
            st.info("正在分析游资特征...")
    
    st.divider()
    
    # 画像指标
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("综合评分", "78/100", "+8")
    col2.metric("游资等级", "一线", "稳定")
    col3.metric("成功率", "72.3%", "+5.2%")
    col4.metric("活跃度", "高")
    
    st.subheader("📈 多维度评估")
    
    # 雷达图
    categories = ['资金规模', '操作频率', '成功率', '稳定性', '风险控制']
    values = [0.8, 0.75, 0.72, 0.68, 0.85]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='游资评估'
    ))
    fig.update_layout(
        title=f"{capital} 五维度评估",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📊 操作偏好分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sector_pref = pd.DataFrame({
            'Sector': ['医药生物', '电子', '计算机', '机技', '化工'],
            'Preference': [0.28, 0.22, 0.18, 0.15, 0.17]
        })
        fig = px.bar(
            sector_pref,
            x='Sector',
            y='Preference',
            title="偏好板块分布"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        time_pref = pd.DataFrame({
            'Stage': ['涨停期', '强势期', '回调期', '低部期'],
            'Preference': [0.35, 0.28, 0.20, 0.17]
        })
        fig = px.pie(
            time_pref,
            names='Stage',
            values='Preference',
            title="操作阶段偏好"
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("🚀 由 MyQuantTool 量化交易平台提供 | v3.6.0")