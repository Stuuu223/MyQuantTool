"""
LSTM上榜预测 + 关键词提取综合仪表板
页面: 预测模型训练 + 关键词提取 + 構帋分析
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import akshare as ak
import numpy as np
from typing import List

from logic.lstm_predictor import LSTMCapitalPredictor, TimeSeriesFeatureEngineer
from logic.keyword_extractor import KeywordExtractor
from logic.capital_profiler import CapitalProfiler

st.set_page_config(
    page_title="高级分析 - LSTM + 关键词",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化齅会
if 'lstm_predictor' not in st.session_state:
    st.session_state.lstm_predictor = LSTMCapitalPredictor()
if 'keyword_extractor' not in st.session_state:
    st.session_state.keyword_extractor = KeywordExtractor()
if 'profiler' not in st.session_state:
    st.session_state.profiler = CapitalProfiler()

lstm_predictor = st.session_state.lstm_predictor
keyword_extractor = st.session_state.keyword_extractor
profiler = st.session_state.profiler

st.title("🔖 高级量化分析席")
st.markdown("---")

# 侧边栏 - 配置区域
with st.sidebar:
    st.subheader("⚡ 模块选择")
    
    analysis_mode = st.radio(
        "选择分析模式",
        [
            "1. LSTM上榜预测",
            "2. 关键词热一上提取",
            "3. 游资構帋研計"
        ]
    )

# ============== Tab 结构 ==============
tab1, tab2, tab3 = st.tabs([
    "🤖 LSTM上榜予测",
    "💡 关键词提取",
    "📊 游资構帋分析"
])

# ======================== Tab 1: LSTM 预测 ========================
with tab1:
    st.subheader("🤖 LSTM上榜概率预测")
    st.write("使用时间序列LSTM模型预测游资明天是否上龙虎榜")
    
    col1, col2 = st.columns(2)
    
    with col1:
        capital_name = st.selectbox(
            "📦 选择游资",
            ["章盟主", "万洲股份", "千万胠", "真游会客"]
        )
    
    with col2:
        if st.button("🔄 刷新龙虎榜数据"):
            st.session_state.refresh_lhb = True
    
    # 获取数据
    date_str = datetime.now().strftime('%Y%m%d')
    df_lhb = ak.stock_lhb_daily_em(date=date_str)
    
    st.info(f"📦 当日龙虎榜上榜股票数: {len(df_lhb)} 只")
    
    # 模式选择区
    st.subheader("🎙 模式训练")
    
    col1, col2 = st.columns(2)
    
    with col1:
        epochs = st.slider(
            "u8bad练趨代數",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
    
    with col2:
        batch_size = st.selectbox(
            "批处理大小",
            [8, 16, 32, 64]
        )
    
    if st.button("🔍 训练LSTM模型", key="train_lstm"):
        with st.spinner(f"正在训练{capital_name}的LSTM模型..."):
            try:
                train_result = lstm_predictor.train_capital_model(
                    capital_name=capital_name,
                    df_lhb_history=df_lhb,
                    epochs=epochs,
                    batch_size=batch_size
                )
                
                if train_result['status'] == 'success':
                    st.success(✅ 训练完成!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(
                        "训练趨代",
                        train_result.get('epochs_trained', 0)
                    )
                    col2.metric(
                        "最終损失",
                        f"{train_result.get('final_loss', 0):.4f}"
                    )
                    col3.metric(
                        "訓練數據",
                        f"{train_result.get('total_records', 0)} 須"
                    )
                    col4.metric(
                        "歷史成功率",
                        f"{train_result.get('historical_success_rate', 0):.1%}"
                    )
                    
                    st.session_state.model_trained = True
                else:
                    st.error(f"🚠 训练失败: {train_result.get('message', '')}")
            except Exception as e:
                st.error(f"🚠 錯誤: {str(e)}")
    
    st.divider()
    
    # 预测区
    st.subheader("🔫 明日上榜预测")
    
    if st.session_state.get('model_trained', False):
        if st.button("🔍 执行预测", key="predict_lstm"):
            with st.spinner("正在下列预测..."):
                prediction = lstm_predictor.predict_capital_appearance(
                    capital_name=capital_name,
                    df_lhb_recent=df_lhb
                )
                
                if prediction:
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric(
                        "🚲 上榜概率",
                        f"{prediction.appearance_probability:.1%}"
                    )
                    col2.metric(
                        🎉 信安度",
                        f"{prediction.confidence_score:.1%}"
                    )
                    col3.metric(
                        ✅ 歷史成功率",
                        f"{prediction.historical_success_rate:.1%}"
                    )
                    
                    st.write(f"**💡 预测理由:** {prediction.prediction_reason}")
                    st.info(f"**📮 建认:** {prediction.recommended_action}")
                    
                    # 特征重要性
                    st.subheader("📊 特征重要性分析")
                    feature_df = pd.DataFrame(
                        list(prediction.feature_importance.items()),
                        columns=['Feature', 'Importance']
                    ).sort_values('Importance', ascending=True)
                    
                    fig = px.barh(
                        feature_df,
                        x='Importance',
                        y='Feature',
                        title="📊 最重要的3个特征",
                        labels={'Importance': '重要性', 'Feature': '特征'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ 没有足壠的訓練數据")
    else:
        st.warning("⚠️ 請此先训练模式")

# ======================== Tab 2: 关键词提取 ========================
with tab2:
    st.subheader("💡 关键词自动提取")
    st.write("从gdp公告、相关冶告摘要提取关键词，识别市场熙舒")
    
    # 文本输入
    st.subheader("📄 输入文本")
    
    input_method = st.radio(
        "选择文本供给方法",
        ["手动输入", "示例文本"]
    )
    
    if input_method == "手动输入":
        input_text = st.text_area(
            "粘贴文本内容",
            height=150,
            placeholder="粘贴公告、相关冶告等文本..."
        )
    else:
        input_text = """
        公司中欢旆空去带动旆上最优异的旆候的前卫児宐。
        公司停期旆ノ晓来业专业简介上最需要旆上最会手小旆秘释老气名折气前次子
        从2020年勣来旆上、公司前旆处会手小旆秘释老气名折气旆处上最会手小旆秘释老气名监有读篇版书旆处会需要旆秘释老气名折气旆处始上纺午旆够困箇旆一及旆一趋被读亻读箱月旆处一及旆一处上旆秘释老气名折气旆处一及旆一需要读下午旆上旆秘释老气名监有读風姑娘路姑子旆上旆秘释老气名折气旆秘释老气名秘
        公司末旆旆上最新的往旆处上旆秘释老气名上最需要旆上最优异的旆候的前卫児子。
        """
        st.write("示例文本。")
    
    # 提取方法选择
    st.subheader("💧 提取方法")
    
    col1, col2 = st.columns(2)
    
    with col1:
        topk = st.slider(
            "返回关键词数量",
            min_value=5,
            max_value=30,
            value=10,
            step=5
        )
    
    with col2:
        method = st.selectbox(
            "提取方法",
            ["TF-IDF", "TextRank"]
        )
    
    if st.button("🔍 提取关键词", key="extract_keywords"):
        if input_text.strip():
            with st.spinner("正在提取关键词..."):
                keywords = keyword_extractor.extract_keywords(
                    input_text,
                    topk=topk,
                    method=method.lower()
                )
                
                if keywords:
                    # 显示摘要
                    summary = keyword_extractor.get_keywords_summary(input_text, topk)
                    
                    st.success(👋 提取完成!")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric(
                        "提取关键词数",
                        summary['total_keywords']
                    )
                    col2.metric(
                        "主要关键词",
                        summary['top_keyword'] or "N/A"
                    )
                    col3.metric(
                        "洋管方法",
                        method
                    )
                    
                    # 维故上储练一
                    st.subheader("📊 关键词觊情表")
                    
                    keywords_df = pd.DataFrame([
                        {
                            'Keyword': k.keyword,
                            'Frequency': k.frequency,
                            'TF-IDF': f"{k.tfidf_score:.4f}",
                            'Type': k.keyword_type,
                            'Relevance': f"{k.relevance_score:.1%}"
                        }
                        for k in keywords
                    ])
                    
                    st.dataframe(
                        keywords_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 可控特殊图表
                    st.subheader("📊 可控特殊图表")
                    
                    # 关键词云图 (随机尾部效果)
                    keyword_text = ' '.join([k.keyword for k in keywords])
                    keyword_freq = Counter([k.keyword for k in keywords])
                    
                    fig_keywords = px.bar(
                        x=[k.keyword for k in keywords],
                        y=[k.tfidf_score for k in keywords],
                        title="📊 TF-IDF识众下情",
                        labels={'x': 'Keyword', 'y': 'TF-IDF Score'}
                    )
                    st.plotly_chart(fig_keywords, use_container_width=True)
                    
                    # 类別打汽
                    type_dist = {}
                    for k in keywords:
                        type_dist[k.keyword_type] = type_dist.get(k.keyword_type, 0) + 1
                    
                    fig_types = px.pie(
                        names=list(type_dist.keys()),
                        values=list(type_dist.values()),
                        title="📊 关键词类別比例"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                else:
                    st.warning("⚠️ 提取失败")
        else:
            st.warning("⚠️ 请输入文本")

# ======================== Tab 3: 游资構帋分析 ========================
with tab3:
    st.subheader("📊 游资構帋研訐")
    st.write("量化诗氧化长旆培作上恐泛的游资茉氓")
    
    col1, col2 = st.columns(2)
    
    with col1:
        select_capital = st.selectbox(
            "📦 选择游资二",
            ["章盟主", "万洲股份"]
        )
    
    with col2:
        if st.button("🔄 新旧敩索", key="refresh_analysis"):
            pass
    
    date_str = datetime.now().strftime('%Y%m%d')
    df_lhb = ak.stock_lhb_daily_em(date=date_str)
    
    if st.button("🔍 执行游资構帋分析"):
        with st.spinner("正在执行構帋分析..."):
            # 提取游资特征
            profile = profiler.calculate_profile(select_capital, df_lhb)
            
            if profile:
                st.success("✅ 游资構帋断斷中!")
                
                # 杰故话数据嶏
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(
                    "综合识众下情",
                    f"{profile.overall_score:.0f}/100"
                )
                col2.metric(
                    "游资穉级",
                    profile.capital_grade
                )
                col3.metric(
                    "操作模洋",
                    profile.capital_type
                )
                col4.metric(
                    "成功率",
                    f"{profile.success_rate:.1%}"
                )
                
                # 鼂雄图
                fig_radar = go.Figure(data=go.Scatterpolar(
                    r=[
                        profile.focus_continuity_score,
                        profile.capital_strength_score,
                        profile.success_rate * 100,
                        profile.sector_concentration * 100,
                        profile.timing_ability_score
                    ],
                    theta=['Continuity', 'Strength', 'Win Rate', 'Concentration', 'Timing'],
                    fill='toself'
                ))
                fig_radar.update_layout(
                    title=f"{select_capital} 5维度計倠",
                    height=500
                )
                st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")
st.caption("👋 由 MyQuantTool 量化业会敍製")
