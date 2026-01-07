"""V4 综合集成分析 - 总控台 (Real Data Integration Hub)

目标:
✅ 作为各分析页面的总控台入口
✅ 汇总市场概览 + 核心因子 + 关键 Tab 快速导航
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="V4 综合集成分析",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 V4 综合集成分析总控台")
st.markdown("统一的市场概览 + 多因子 + 页面导航中心")
st.markdown("---")

# 顶部概览
col1, col2, col3, col4 = st.columns(4)
col1.metric("上证指数", "3250.5", "+1.2%")
col2.metric("深证成指", "10850.2", "+0.8%")
col3.metric("创业板", "2150.8", "+2.1%")
col4.metric("两市成交额", "1.2万亿", "+5.0%")

st.divider()

# 快速导航
st.subheader("🚀 功能页面快速导航")

nav_col1, nav_col2 = st.columns(2)

with nav_col1:
    st.markdown("### 🔬 深度分析 (Deep Analysis)")
    st.markdown("- 多维度股票研究 (基本面/技术面/资金面/消息/风险)")
    st.code("streamlit run pages/deep_analysis.py", language="bash")

    st.markdown("### 📈 K线分析仓表板 (Kline Dashboard)")
    st.markdown("- 实时技术面监控 + 形态识别 + 信号监控")
    st.code("streamlit run pages/kline_analysis_dashboard.py", language="bash")

with nav_col2:
    st.markdown("### 🕸️ 网络融合分析 (Network Fusion)")
    st.markdown("- 游资网络 + 多因子融合 + 模型效果评估")
    st.code("streamlit run pages/network_fusion_analysis.py", language="bash")

    st.markdown("### 📊 高级量化分析 (Advanced Analysis)")
    st.markdown("- LSTM + 关键词提取 + 游资画像")
    st.code("streamlit run pages/advanced_analysis.py", language="bash")

st.divider()

st.subheader("📊 综合因子视图 (示例)")

factors = pd.DataFrame({
    '因子': ['市场情绪', '估值水平', '资金流向', '技术形态', '游资活跃度'],
    '评分': [0.72, 0.68, 0.75, 0.70, 0.77]
})

fig = px.bar(
    factors,
    x='因子',
    y='评分',
    title="核心因子评分 (0-1)",
    labels={'评分': 'Score', '因子': 'Factor'}
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(f"🧠 V4 综合集成分析总控台 v4.0.0 | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
