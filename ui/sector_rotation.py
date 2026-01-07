"""
板块轮动分析系统UI
功能：30个行业板块实时强度评分、轮动识别、趋势预测
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from logic.sector_rotation_analyzer import get_sector_rotation_analyzer
from logic.data_manager import DataManager


def render_sector_rotation_tab(db, config):
    """渲染板块轮动分析标签页"""
    
    st.header("🔄 板块轮动分析")
    st.caption("30个行业板块实时强度评分 | 5因子加权模型 | 轮动机会识别")
    
    # 初始化分析器
    analyzer = get_sector_rotation_analyzer(history_days=30)
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 分析配置")
        
        date = st.date_input("分析日期", value=datetime.now().date(), key="sector_date")
        date_str = date.strftime("%Y%m%d")
        
        st.markdown("---")
        st.markdown("### 📊 因子权重")
        price_weight = st.slider("涨幅因子", 0, 50, 30, 5) / 100
        capital_weight = st.slider("资金因子", 0, 50, 25, 5) / 100
        leader_weight = st.slider("龙头因子", 0, 50, 20, 5) / 100
        topic_weight = st.slider("题材因子", 0, 50, 15, 5) / 100
        volume_weight = st.slider("成交因子", 0, 50, 10, 5) / 100
        
        total_weight = price_weight + capital_weight + leader_weight + topic_weight + volume_weight
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"⚠️ 权重总和应为100%，当前为{total_weight*100:.1f}%")
    
    # 主要内容
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 板块强度排行")
        
        if st.button("🔄 刷新分析", key="refresh_sector", type="primary"):
            with st.spinner("正在分析板块轮动..."):
                try:
                    # 计算板块强度
                    strength_scores = analyzer.calculate_sector_strength(date_str)
                    
                    if strength_scores:
                        st.info("💡 提示：当前使用演示数据，实际数据需要等待股市开盘")
                        
                        # 转换为DataFrame
                        df_strength = pd.DataFrame([
                            {
                                '板块': sector,
                                '综合评分': strength.total_score,
                                '涨幅因子': strength.price_score,
                                '资金因子': strength.capital_score,
                                '龙头因子': strength.leader_score,
                                '题材因子': strength.topic_score,
                                '成交因子': strength.volume_score,
                                '轮动阶段': strength.phase.value,
                                '领跑股票': strength.leading_stock or '-',
                                '强度变化': strength.delta
                            }
                            for sector, strength in strength_scores.items()
                        ])
                        
                        # 按综合评分排序
                        df_strength = df_strength.sort_values('综合评分', ascending=False)
                        
                        # 显示排行榜
                        st.dataframe(
                            df_strength.head(15),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                '综合评分': st.column_config.ProgressColumn(
                                    '综合评分',
                                    help='0-100分，分数越高板块越强',
                                    format='%.1f',
                                    min_value=0,
                                    max_value=100
                                ),
                                '强度变化': st.column_config.NumberColumn(
                                    '强度变化',
                                    help='与前一日的强度变化',
                                    format='%.1f'
                                )
                            }
                        )
                        
                        # 检测轮动信号
                        st.markdown("---")
                        st.subheader("🎯 轮动信号识别")
                        
                        signals = analyzer.detect_rotation_signals(date_str)
                        
                        col_a, col_b, col_c, col_d = st.columns(4)
                        
                        with col_a:
                            st.metric("📈 上升中", len(signals['rising']))
                            if signals['rising']:
                                st.write(", ".join(signals['rising'][:3]))
                        
                        with col_b:
                            st.metric("📉 下降中", len(signals['falling']))
                            if signals['falling']:
                                st.write(", ".join(signals['falling'][:3]))
                        
                        with col_c:
                            st.metric("🏆 领跑", len(signals['leading']))
                            if signals['leading']:
                                st.write(", ".join(signals['leading'][:3]))
                        
                        with col_d:
                            st.metric("⚠️ 落后", len(signals['lagging']))
                            if signals['lagging']:
                                st.write(", ".join(signals['lagging'][:3]))
                        
                        # 板块强度可视化
                        st.markdown("---")
                        st.subheader("📈 板块强度可视化")
                        
                        fig = go.Figure()
                        
                        # 添加柱状图
                        fig.add_trace(go.Bar(
                            x=df_strength['板块'].head(15),
                            y=df_strength['综合评分'].head(15),
                            marker_color=df_strength['综合评分'].head(15).apply(
                                lambda x: '#00C853' if x >= 70 else '#FFC107' if x >= 50 else '#FF5252'
                            ),
                            text=df_strength['综合评分'].head(15).apply(lambda x: f'{x:.1f}'),
                            textposition='auto',
                        ))
                        
                        fig.update_layout(
                            title='板块综合评分TOP15',
                            xaxis_title='板块',
                            yaxis_title='综合评分',
                            yaxis_range=[0, 100],
                            height=500,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 因子雷达图
                        st.markdown("---")
                        st.subheader("📊 TOP3板块因子分析")
                        
                        top3_sectors = df_strength.head(3)
                        
                        for _, row in top3_sectors.iterrows():
                            with st.expander(f"🏆 {row['板块']} - {row['综合评分']:.1f}分"):
                                col_f1, col_f2, col_f3 = st.columns(3)
                                
                                col_f1.metric("涨幅因子", f"{row['涨幅因子']:.1f}")
                                col_f2.metric("资金因子", f"{row['资金因子']:.1f}")
                                col_f3.metric("龙头因子", f"{row['龙头因子']:.1f}")
                                
                                col_f4, col_f5 = st.columns(2)
                                col_f4.metric("题材因子", f"{row['题材因子']:.1f}")
                                col_f5.metric("成交因子", f"{row['成交因子']:.1f}")
                                
                                if row['领跑股票'] != '-':
                                    st.info(f"📌 领跑股票: {row['领跑股票']}")
                                
                                if row['强度变化'] > 5:
                                    st.success(f"📈 强度快速上升 (+{row['强度变化']:.1f})")
                                elif row['强度变化'] < -5:
                                    st.warning(f"📉 强度快速下降 ({row['强度变化']:.1f})")
                        
                    else:
                        st.warning("⚠️ 未能获取板块数据，请稍后重试")
                
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
    
    with col2:
        st.subheader("📋 操作建议")
        
        st.markdown("""
        ### 💡 轮动策略
        
        **📈 上升中板块**
        - 关注龙头股
        - 适度追涨
        - 设置止损
        
        **🏆 领跑板块**
        - 重点配置
        - 持有待涨
        - 注意分化
        
        **📉 下降中板块**
        - 减仓规避
        - 等待企稳
        - 不建议抄底
        
        **⚠️ 落后板块**
        - 避免参与
        - 观望为主
        - 等待轮动
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 🎯 因子解读
        
        **涨幅因子 (30%)**
        - 反映板块整体涨幅
        - 越强说明市场关注度越高
        
        **资金因子 (25%)**
        - 反映主力资金流入
        - 资金流入越多越强
        
        **龙头因子 (20%)**
        - 反映龙虎榜活跃度
        - 龙头股表现决定板块强度
        
        **题材因子 (15%)**
        - 反映热点题材关联
        - 题材越热板块越强
        
        **成交因子 (10%)**
        - 反映成交量活跃度
        - 放量上涨更可靠
        """)