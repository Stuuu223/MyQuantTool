#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V12 第三阶段：预测雷达 UI 模块
基于历史复盘数据计算概率模型，可视化展示
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.predictive_engine import PredictiveEngine
from logic.market_sentiment import MarketSentiment
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_predictive_radar(data_manager=None):
    """
    渲染预测雷达面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("🔮 预测雷达 (V12)")

    # 初始化组件
    if data_manager is None:
        data_manager = DataManager()

    pe = PredictiveEngine()
    ms = MarketSentiment()

    # 使用列布局：左侧概率仪表盘，右侧情绪转折预判
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 晋级成功率")
        # 1. 获取实时状态
        try:
            sentiment_data = ms.get_consecutive_board_height()
            current_height = sentiment_data.get('max_board', 0)

            # 2. 获取预测概率
            prob = pe.get_promotion_probability(current_height)

            # 3. 显示概率
            if prob >= 0:
                # 根据概率设置颜色
                if prob >= 50:
                    color = "normal"
                    emoji = "🚀"
                elif prob >= 30:
                    color = "normal"
                    emoji = "⚡"
                else:
                    color = "inverse"
                    emoji = "⚠️"

                st.metric(
                    f"{current_height}板 ➜ {current_height+1}板",
                    f"{prob}%",
                    delta=f"{emoji} 历史同高度",
                    delta_color=color
                )

                # 显示样本信息
                st.caption(f"基于最近60天历史数据计算")
            else:
                st.metric(
                    f"{current_height}板 晋级率",
                    "数据不足",
                    delta="样本量少于10天",
                    delta_color="off"
                )
                st.warning("⚠️ 历史数据样本不足，无法计算准确概率")

        except Exception as e:
            logger.error(f"获取晋级概率失败: {e}")
            st.error(f"获取晋级概率失败: {e}")

    with col2:
        st.markdown("### 🎯 情绪转折预判")
        try:
            # 获取情绪转折点
            pivot = pe.detect_sentiment_pivot()

            # 设置颜色和图标
            if pivot['action'] == "DEFENSE":
                color = "inverse"
                emoji = "🛡️"
                help_text = "市场高度连降，建议防守"
            elif pivot['action'] == "NORMAL":
                color = "normal"
                emoji = "✅"
                help_text = "情绪稳定，正常操作"
            else:  # HOLD
                color = "off"
                emoji = "⏸️"
                help_text = "样本不足，保持观望"

            st.metric(
                "当前状态",
                f"{emoji} {pivot['action']}",
                delta=pivot['reason'],
                delta_color=color,
                help=help_text
            )

        except Exception as e:
            logger.error(f"获取情绪转折预判失败: {e}")
            st.error(f"获取情绪转折预判失败: {e}")

    st.markdown("---")

    # 可视化：历史高度走势
    st.markdown("### 📈 市场高度周期演变")

    try:
        # 从 DB 读取最近 20 天的高度数据
        history = data_manager.sqlite_query(
            "SELECT date, highest_board FROM market_summary ORDER BY date DESC LIMIT 20"
        )

        if history and len(history) > 1:
            # 转换为 DataFrame
            df_hist = pd.DataFrame(history, columns=['日期', '最高板'])
            df_hist = df_hist.sort_values('日期')

            # 创建图表
            fig = go.Figure()

            # 添加折线
            fig.add_trace(go.Scatter(
                x=df_hist['日期'],
                y=df_hist['最高板'],
                mode='lines+markers',
                name='最高板',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8, color='#FF6B6B'),
                hovertemplate='<b>%{x}</b><br>最高板: %{y}<extra></extra>'
            ))

            # 添加填充区域
            fig.add_trace(go.Scatter(
                x=df_hist['日期'],
                y=df_hist['最高板'],
                mode='none',
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.2)',
                showlegend=False
            ))

            # 更新布局
            fig.update_layout(
                title='最近20天市场最高板高度走势',
                xaxis_title='日期',
                yaxis_title='连板高度',
                hovermode='x unified',
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(
                    tickangle=-45,
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.1)'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(0,0,0,0.1)',
                    dtick=1  # 整数刻度
                )
            )

            st.plotly_chart(fig, use_container_width=True)

            # 显示统计信息
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("当前高度", f"{df_hist['最高板'].iloc[-1]}板")
            with col_b:
                avg_height = df_hist['最高板'].mean()
                st.metric("平均高度", f"{avg_height:.1f}板")
            with col_c:
                max_height = df_hist['最高板'].max()
                st.metric("历史最高", f"{max_height}板")

        else:
            st.info("📊 暂无历史数据，请在交易时段后查看")

    except Exception as e:
        logger.error(f"获取历史高度数据失败: {e}")
        st.error(f"获取历史高度数据失败: {e}")

    # 概率分析说明
    st.markdown("---")
    st.markdown("### 📖 概率分析说明")

    with st.expander("查看详细说明"):
        st.markdown("""
        **🔮 预测雷达功能说明：**

        1. **晋级成功率**
           - 基于最近60天历史数据计算
           - 统计当最高板达到 N 时，次日出现 N+1 的次数
           - 样本量少于10天时显示"数据不足"

        2. **情绪转折预判**
           - **DEFENSE (防守)**：市场高度连降，情绪退潮期，建议只卖不买
           - **NORMAL (正常)**：情绪稳定，按原策略操作
           - **HOLD (观望)**：样本不足，保持观望

        3. **市场高度周期演变**
           - 显示最近20天的最高板高度走势
           - 帮助判断当前处于哪个周期阶段
           - 配合情绪转折预判，辅助决策

        **⚠️ 风险提示：**
        - 历史概率不代表未来表现
        - 仅作为参考工具，不构成投资建议
        - 请结合市场实际情况综合判断
        """)

    # 关闭连接
    if data_manager:
        data_manager.close()

    logger.info("✅ 预测雷达渲染完成")