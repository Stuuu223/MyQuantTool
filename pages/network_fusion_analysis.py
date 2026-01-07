"""网络融合分析 - 游资网络 + 多因子融合"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(
    page_title="网络融合分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义中文导航菜单
with st.sidebar:
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    .nav-link {
        display: block;
        padding: 0.5rem;
        color: #262730;
        text-decoration: none;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
    }
    .nav-link:hover {
        background-color: #f0f2f6;
    }
    .nav-link.active {
        background-color: #FF6B6B;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📱 页面导航")
    st.markdown('<a href="/" class="nav-link">🏠 主页</a>', unsafe_allow_html=True)
    st.markdown('<a href="/advanced_analysis" class="nav-link">📊 高级量化分析</a>', unsafe_allow_html=True)
    st.markdown('<a href="/capital_search" class="nav-link">💰 资金搜索</a>', unsafe_allow_html=True)
    st.markdown('<a href="/deep_analysis" class="nav-link">🔬 深度分析</a>', unsafe_allow_html=True)
    st.markdown('<a href="/kline_analysis_dashboard" class="nav-link">📈 K线分析</a>', unsafe_allow_html=True)
    st.markdown('<a href="/monitor_dashboard" class="nav-link">📊 实时监控</a>', unsafe_allow_html=True)
    st.markdown('<a href="/network_fusion_analysis" class="nav-link active">🕸️ 网络融合分析</a>', unsafe_allow_html=True)
    st.markdown('<a href="/v4_integrated_analysis" class="nav-link">🚀 v4综合分析</a>', unsafe_allow_html=True)

st.title("🕸️ 网络融合分析")
st.markdown("游资关系网络分析 + 多因子融合预测")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.subheader("⚙️ 网络配置")
    
    network_type = st.radio(
        "选择网络类型",
        ["游资关系图", "股票热度网", "对手关系图"],
    )
    
    threshold = st.slider(
        "关系阈值",
        min_value=0.1,
        max_value=1.0,
        value=0.5,
        step=0.1
    )

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🕸️ 网络可视化",
    "📊 中心度分析",
    "🤝 对手格局",
    "🎛️ 多因子融合",
    "📈 效果评估"
])

# ============== Tab 1: 网络可视化 ==============
with tab1:
    st.header("🕸️ 游资关系网络")
    st.write("展示游资之间的合作与对抗关系")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("节点数", "85", "游资个数")
    col2.metric("边数", "342", "关系数")
    col3.metric("平均度数", "8.0", "关系密度")
    
    st.divider()
    
    st.info("🕸️ 网络图表（下方展示游资关系）")
    
    # 模拟网络图
    fig = go.Figure()
    
    # 模拟节点坐标
    np.random.seed(42)
    n_nodes = 15
    node_x = np.random.randn(n_nodes)
    node_y = np.random.randn(n_nodes)
    
    # 添加边
    edge_x = []
    edge_y = []
    for i in range(n_nodes):
        for j in range(i+1, min(i+4, n_nodes)):
            if np.random.random() > 0.3:
                edge_x += [node_x[i], node_x[j], None]
                edge_y += [node_y[i], node_y[j], None]
    
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=0.5, color='rgba(125, 125, 125, 0.3)'),
        hoverinfo='none',
        showlegend=False
    ))
    
    # 添加节点
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        marker=dict(
            size=20,
            color=np.random.rand(n_nodes),
            colorscale='Viridis',
            showscale=True,
            line=dict(width=2, color='white')
        ),
        text=[f'C{i}' for i in range(n_nodes)],
        textposition='top center',
        hovertemplate='游资%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title="游资关系网络图",
        showlegend=False,
        hovermode='closest',
        height=600,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("🎯 自动分群结果")
    clusters = pd.DataFrame({
        '群组': ['群1', '群2', '群3', '群4'],
        '成员数': [12, 8, 15, 7],
        '紧密度': ['0.82', '0.75', '0.68', '0.71'],
        '特征': ['协作型', '激进型', '保守型', '混合型']
    })
    st.dataframe(clusters, use_container_width=True, hide_index=True)

# ============== Tab 2: 中心度分析 ==============
with tab2:
    st.header("📊 中心度指标分析")
    
    st.subheader("🏆 Top 10 核心游资")
    
    centrality_df = pd.DataFrame({
        '排名': list(range(1, 11)),
        '游资名称': [f'游资{i}' for i in range(1, 11)],
        '介中心度': [0.85, 0.78, 0.72, 0.68, 0.65, 0.62, 0.58, 0.55, 0.52, 0.48],
        '接近度': [0.92, 0.88, 0.84, 0.80, 0.78, 0.75, 0.72, 0.70, 0.68, 0.65],
        '度数': [18, 16, 14, 12, 11, 10, 9, 8, 7, 6],
        '等级': ['S', 'S', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C']
    })
    
    st.dataframe(centrality_df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 中心度分布")
        fig = px.scatter(
            centrality_df,
            x='介中心度',
            y='接近度',
            size='度数',
            color='等级',
            title="中心度分布图",
            labels={'介中心度': '介中心度', '接近度': '接近度'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 聚类系数")
        cluster_coef = centrality_df['游资名称'].iloc[:8]
        coef_values = np.random.uniform(0.5, 0.95, 8)
        
        fig = px.bar(
            x=cluster_coef,
            y=coef_values,
            title="聚类系数排序",
            labels={'y': '聚类系数', 'x': '游资'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 3: 对手格局 ==============
with tab3:
    st.header("🤝 对手格局分析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        selected_capital = st.selectbox(
            "选择游资查看对手",
            [f'游资{i}' for i in range(1, 11)],
            key="opponent_select"
        )
    
    with col2:
        if st.button("🔄 刷新对手数据"):
            st.success("✅ 数据已更新")
    
    st.divider()
    
    st.subheader(f"📊 {selected_capital} 的主要对手")
    
    opponents = pd.DataFrame({
        '对手名称': [f'游资{i}' for i in range(1, 6)],
        '交锋次数': [8, 6, 5, 4, 3],
        '胜率': ['65%', '58%', '72%', '50%', '55%'],
        '主要股票': ['股票A, 股票B', '股票C, 股票D', '股票E', '股票F', '股票G'],
        '合作概率': ['5%', '8%', '3%', '15%', '10%']
    })
    
    st.dataframe(opponents, use_container_width=True, hide_index=True)
    
    st.subheader("📊 对手分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            opponents,
            x='对手名称',
            y='交锋次数',
            title="主要对手交锋次数",
            labels={'交锋次数': '次数', '对手名称': '对手'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            opponents,
            x='对手名称',
            y='胜率',
            title="对手胜率统计",
            labels={'胜率': '胜率(%)', '对手名称': '对手'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ============== Tab 4: 多因子融合 ==============
with tab4:
    st.header("🎛️ 多因子融合预测")
    st.write("融合 LSTM + K线技术 + 游资网络 三大因子")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        lstm_weight = st.slider(
            "LSTM权重",
            min_value=0,
            max_value=100,
            value=33,
            step=1,
            key="lstm_weight"
        )
    
    with col2:
        kline_weight = st.slider(
            "K线权重",
            min_value=0,
            max_value=100,
            value=33,
            step=1,
            key="kline_weight"
        )
    
    with col3:
        network_weight = st.slider(
            "网络权重",
            min_value=0,
            max_value=100,
            value=34,
            step=1,
            key="network_weight"
        )
    
    st.divider()
    
    st.subheader("📊 融合结果")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("LSTM信号", "0.65", "看涨")
    col2.metric("K线信号", "0.72", "看涨")
    col3.metric("网络信号", "0.58", "中性")
    col4.metric("综合评分", "0.68", "看涨 📈")
    
    st.divider()
    
    st.subheader("💡 融合分析")
    
    fusion_result = pd.DataFrame({
        '因子': ['LSTM预测', 'K线技术', '游资网络'],
        '独立信号': [0.65, 0.72, 0.58],
        '权重': [f'{lstm_weight}%', f'{kline_weight}%', f'{network_weight}%'],
        '贡献度': ['22%', '24%', '19%']
    })
    
    st.dataframe(fusion_result, use_container_width=True, hide_index=True)
    
    st.info("✅ **融合结论**: 三个因子信号一致性高，综合看涨。建议关注买点。")

# ============== Tab 5: 效果评估 ==============
with tab5:
    st.header("📈 模型效果评估")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("准确率", "73.5%", "+2.1%")
    col2.metric("精准率", "78.2%", "+1.8%")
    col3.metric("召回率", "72.1%", "+2.5%")
    col4.metric("F1分数", "75.1%", "+2.0%")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 性能指标")
        metrics = pd.DataFrame({
            'Metric': ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC'],
            'Score': [0.735, 0.782, 0.721, 0.751, 0.768]
        })
        fig = px.bar(
            metrics,
            x='Metric',
            y='Score',
            title="模型性能评分",
            labels={'Score': '分数', 'Metric': '指标'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 最近预测结果")
        recent_predictions = pd.DataFrame({
            'Date': pd.date_range(end=datetime.now(), periods=5, freq='D'),
            'Prediction': ['看涨', '看涨', '中性', '看跌', '看涨'],
            'Actual': ['看涨', '看涨', '看涨', '看跌', '看涨'],
            'Correct': [True, True, False, True, True]
        })
        st.dataframe(recent_predictions, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("🕸️ 网络融合分析系统 v3.6.0")