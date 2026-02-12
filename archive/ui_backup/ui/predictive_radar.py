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
    st.subheader("🔮 预测雷达 (V13)")

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

    # [V13 新增] 板块记忆展示
    st.markdown("### 🏆 板块记忆 (V13)")
    
    try:
        # 获取昨日复盘数据
        from logic.review_manager import ReviewManager
        rm = ReviewManager()
        yesterday_stats = rm.get_yesterday_stats()
        
        if yesterday_stats and yesterday_stats.get('top_sectors'):
            top_sectors = yesterday_stats['top_sectors']
            
            st.info(f"📅 昨日 ({yesterday_stats['date']}) 领涨板块: {', '.join(top_sectors)}")
            
            # 板块忠诚度分析
            st.markdown("#### 🎯 板块忠诚度分析")
            
            for sector in top_sectors[:3]:  # 只显示前3个
                loyalty = pe.get_sector_loyalty(sector)
                
                # 根据忠诚度设置样式
                if loyalty['status'] == "真命天子":
                    emoji = "👑"
                    color = "🟢"
                elif loyalty['status'] == "一般":
                    emoji = "⚖️"
                    color = "🟡"
                elif loyalty['status'] == "短命渣男":
                    emoji = "💔"
                    color = "🔴"
                else:
                    emoji = "⏳"
                    color = "⚪"
                
                with st.expander(f"{emoji} {sector} - {color} {loyalty['status']}"):
                    st.metric("忠诚度评分", loyalty['loyalty_score'])
                    st.metric("出现次数", loyalty['appearance_count'])
                    st.metric("次日平均表现", f"{loyalty['avg_next_day_profit']:+.2f}")
                    
                    if loyalty['status'] == "数据积累中...":
                        st.caption("⚠️ 数据积累中，需要至少3天历史数据")
                    elif loyalty['status'] == "真命天子":
                        st.success("✅ 该板块持续性较强，可重点关注")
                    elif loyalty['status'] == "短命渣男":
                        st.warning("⚠️ 该板块持续性较差，谨慎参与")
        else:
            st.info("📊 暂无板块数据，请在交易时段后查看")
    
    except Exception as e:
        logger.error(f"获取板块记忆失败: {e}")
        st.error(f"获取板块记忆失败: {e}")

    st.markdown("---")

    # [V13 Iron Rule] 铁律状态展示
    st.markdown("### 🛡️ [V13 Iron Rule] 铁律状态")
    
    try:
        from logic.iron_rule_engine import IronRuleEngine
        iron_engine = IronRuleEngine()
        
        # 获取锁定股票列表
        locked_stocks = iron_engine.get_locked_stocks()
        
        # 显示铁律引擎状态
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "铁律引擎",
                "✅ 激活",
                delta="V13 Iron Rule 模式",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "锁定股票",
                f"{len(locked_stocks)} 只",
                delta="逻辑证伪+资金背离",
                delta_color="inverse" if locked_stocks else "off"
            )
        
        # 显示锁定股票详情
        if locked_stocks:
            st.warning(f"⚠️ 当前有 {len(locked_stocks)} 只股票被铁律锁定")
            
            # 创建锁定股票表格
            locked_df = pd.DataFrame(locked_stocks)
            st.dataframe(
                locked_df[['code', 'reason', 'lock_time', 'remaining_hours']].rename(columns={
                    'code': '股票代码',
                    'reason': '锁定原因',
                    'lock_time': '锁定时间',
                    'remaining_hours': '剩余锁定时间(小时)'
                }),
                use_container_width=True
            )
        else:
            st.success("✅ 当前无股票被铁律锁定")
        
        # 显示铁律规则说明
        with st.expander("📖 铁律规则说明"):
            st.markdown("""
            **V13 Iron Rule 核心原则：**
            
            1. **逻辑证伪 + 资金背离 = 永久熔断**
               - 如果核心利好逻辑被官方证伪（澄清、监管函、风险提示等）
               - 且 DDE/主力资金大幅流出（净额 < -1亿）
               - 则触发铁律，该股票被锁定24小时，禁止买入
            
            2. **物理阉割亏损加仓**
               - 浮亏超过 -3%：禁止加仓，只准割肉
               - 浮亏超过 -8%：强制止损，立即平仓
            
            3. **战前三问审计**
               - 核心利好逻辑是否依然成立？
               - 盘中DDE/主力大单流出是否处于可控红线内？
               - 是否坚决执行-3%禁止补仓、-8%物理止损？
            """)
    
    except Exception as e:
        logger.error(f"获取铁律状态失败: {e}")
        st.error(f"获取铁律状态失败: {e}")

    st.markdown("---")

    # 可视化：历史高度走势
    st.markdown("### 📈 市场高度周期演变")

    try:
        # 从 DB 读取最近 20 天的高度数据
        # 🆕 V18.8 修复：使用新的数据库访问方式
        history = data_manager.sqlite_query(
            "SELECT date, highest_board, top_sectors FROM market_summary ORDER BY date DESC LIMIT 20"
        )

        if history and len(history) > 1:
            # 转换为 DataFrame
            df_hist = pd.DataFrame(history, columns=['日期', '最高板', '领涨板块'])
            df_hist = df_hist.sort_values('日期')
            
            # 解析领涨板块
            import json
            df_hist['领涨板块'] = df_hist['领涨板块'].apply(lambda x: ', '.join(json.loads(x)) if x else '无')

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
                hovertemplate='<b>%{x}</b><br>最高板: %{y}<br>领涨板块: %{text}<extra></extra>',
                text=df_hist['领涨板块']
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
                title='最近20天市场最高板高度走势（含领涨板块）',
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

    # [V13 第二阶段] 实时感知心电图
    st.markdown("---")
    st.markdown("### 💓 实时感知心电图 (V13)")
    
    try:
        from logic.sector_pulse_monitor import SectorPulseMonitor
        from logic.sector_capital_tracker import SectorCapitalTracker
        from logic.sector_rotation_detector import SectorRotationDetector
        
        # 初始化实时监控组件
        spm = SectorPulseMonitor()
        sct = SectorCapitalTracker()
        srd = SectorRotationDetector()
        
        # 使用列布局：左侧板块热度，右侧资金流向
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔥 实时板块热度")
            pulse = spm.get_sector_pulse()
            
            if pulse['top_sectors']:
                st.info(f"📊 监控到 {pulse['total_sectors']} 个板块")
                
                # 显示热度最高的板块
                for i, sector in enumerate(pulse['top_sectors'][:5], 1):
                    # 根据心跳状态设置图标
                    if sector['pulse_status'] == '加速':
                        emoji = "🚀"
                        color = "🔴"
                    elif sector['pulse_status'] == '平稳':
                        emoji = "⚖️"
                        color = "🟡"
                    else:
                        emoji = "📉"
                        color = "🔵"
                    
                    st.metric(
                        f"{i}. {sector['name']}",
                        f"{sector['change_pct']:.2f}%",
                        delta=f"{emoji} 心跳: {sector['pulse_score']:.1f}",
                        help=f"成交量: {sector['volume']:,}, 成交额: {sector['amount']:,}"
                    )
            else:
                st.warning("⚠️ 暂无板块热度数据")
            
            # 显示预警板块
            if pulse['alert_sectors']:
                st.warning("⚠️ 板块预警:")
                for sector in pulse['alert_sectors']:
                    st.caption(f"  • {sector['name']}: {sector['alert_type']} ({sector['alert_level']})")
        
        with col2:
            st.markdown("#### 💰 实时资金流向")
            capital_flow = sct.get_sector_capital_flow()
            
            if capital_flow['top_inflow']:
                st.info(f"📊 监控到 {capital_flow['total_sectors']} 个板块")
                
                # 显示净流入最多的板块
                if capital_flow['top_inflow']:
                    st.success(f"💵 净流入最多: {capital_flow['top_inflow']['name']}")
                    st.metric(
                        "净流入",
                        f"{capital_flow['top_inflow']['net_inflow']:.2f}亿元",
                        delta=f"排名: #{capital_flow['top_inflow']['inflow_rank']}"
                    )
                
                # 显示净流出最多的板块
                if capital_flow['top_outflow']:
                    st.error(f"💸 净流出最多: {capital_flow['top_outflow']['name']}")
                    st.metric(
                        "净流出",
                        f"{capital_flow['top_outflow']['net_inflow']:.2f}亿元",
                        delta=f"排名: #{capital_flow['top_outflow']['inflow_rank']}"
                    )
            else:
                st.warning("⚠️ 暂无资金流向数据")
            
            # 显示资金预警板块
            if capital_flow['alert_sectors']:
                st.warning("⚠️ 资金预警:")
                for sector in capital_flow['alert_sectors']:
                    st.caption(f"  • {sector['name']}: {sector['alert_type']} ({sector['alert_level']})")
        
        # 板块轮动检测
        st.markdown("#### 🔄 板块轮动检测")
        
        # 获取当前热度最高的板块
        current_top_sectors = [s['name'] for s in pulse['top_sectors'][:3]] if pulse['top_sectors'] else []
        
        if current_top_sectors:
            rotation = srd.detect_rotation(current_top_sectors)
            
            if rotation['is_rotating']:
                # 显示轮动预警
                if rotation['alert_level'] == '高':
                    st.error(f"🚨 {rotation['rotation_type']} (强度: {rotation['rotation_strength']:.1%})")
                else:
                    st.warning(f"⚠️ {rotation['rotation_type']} (强度: {rotation['rotation_strength']:.1%})")
                
                st.info(f"💡 建议: {rotation['recommendation']}")
                
                # 显示主线切换信息
                if rotation['rotation_type'] == '主线切换':
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("旧主线", rotation['old_main'])
                    with col_b:
                        st.metric("新主线", rotation['new_main'])
            else:
                st.success(f"✅ {rotation['rotation_type']} - 市场稳定")
                st.info(f"💡 建议: {rotation['recommendation']}")
        else:
            st.warning("⚠️ 暂无板块数据，无法检测轮动")
    
    except Exception as e:
        logger.error(f"获取实时感知数据失败: {e}")
        st.error(f"获取实时感知数据失败: {e}")

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

        3. **🏆 板块记忆 (V13 新增)**
           - 显示昨日领涨板块
           - 板块忠诚度分析：判断板块是"真命天子"还是"短命渣男"
           - 基于历史出现次数和次日表现计算忠诚度评分

        4. **市场高度周期演变**
           - 显示最近20天的最高板高度走势
           - 帮助判断当前处于哪个周期阶段
           - 配合情绪转折预判，辅助决策

        **⚠️ 风险提示：**
        - 历史概率不代表未来表现
        - 仅作为参考工具，不构成投资建议
        - 请结合市场实际情况综合判断
        """)

    logger.info("✅ 预测雷达渲染完成")