"""
V7.0 新功能展示页面

功能：
1. 板块轮动强度比值可视化
2. 策略仲裁庭决策展示
3. 动态凯利公式仓位计算
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, Any

from logic.strategy_orchestrator import StrategyOrchestrator, DecisionType
from logic.theme_detector import ThemeDetector
from logic.market_cycle import MarketCycleManager


def render_v70_features_tab(db, config):
    """渲染V7.0新功能标签页"""
    st.subheader("🚀 V7.0 统合优化 - 从能赚钱到稳定复利")
    
    # 初始化模块
    orchestrator = StrategyOrchestrator()
    theme_detector = ThemeDetector()
    market_cycle_manager = MarketCycleManager()
    
    # 创建三个子标签页
    tab1, tab2, tab3 = st.tabs([
        "📊 板块轮动强度比值",
        "⚖️ 策略仲裁庭",
        "💰 动态凯利公式"
    ])
    
    # Tab 1: 板块轮动强度比值
    with tab1:
        st.markdown("### 📊 板块轮动强度比值 (V7.0)")
        st.markdown("""
        **核心改进**：从"看时间切换"改为"看强度差切换"
        
        - **强度比值 >= 1.5**：新板块强度是主线的1.5倍以上，确认切换
        - **强度比值 >= 1.0**：新板块强度接近主线，密切关注
        - **强度比值 < 1.0**：主线依然比新板块强，坚决不切
        """)
        
        # 模拟数据展示
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 当前主线")
            main_theme = st.text_input("主线板块", "华为鸿蒙")
            main_strength = st.slider("主线强度", 0, 100, 80)
        
        with col2:
            st.markdown("#### 🆕 新兴板块")
            new_theme = st.text_input("新兴板块", "医药")
            new_strength = st.slider("新板块强度", 0, 100, 60)
        
        # 计算强度比值
        strength_ratio = new_strength / main_strength if main_strength > 0 else 0
        
        # 判断轮动信号
        if strength_ratio >= 1.5:
            signal = "🟢 ROTATE_NOW (确认切换)"
            color = "green"
            advice = f"果断切换到{new_theme}，避免踏空"
        elif strength_ratio >= 1.0:
            signal = "🟡 WATCH_CLOSELY (密切关注)"
            color = "yellow"
            advice = f"主线未死，继续在主线做T，同时观察{new_theme}动向"
        else:
            signal = "🔴 STAY_WITH_MAIN (坚守主线)"
            color = "red"
            advice = f"主线未死，继续在此做T，不要去抓杂毛"
        
        # 显示结果
        st.markdown(f"#### 📈 强度比值: {strength_ratio:.2f}")
        st.markdown(f"#### 🎯 轮动信号: {signal}")
        st.markdown(f"#### 💡 操作建议: {advice}")
        
        # 可视化强度对比
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='主线',
            x=[main_theme],
            y=[main_strength],
            marker_color='blue'
        ))
        fig.add_trace(go.Bar(
            name='新兴板块',
            x=[new_theme],
            y=[new_strength],
            marker_color='orange'
        ))
        
        fig.update_layout(
            title='板块强度对比',
            yaxis_title='强度值',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: 策略仲裁庭
    with tab2:
        st.markdown("### ⚖️ 策略仲裁庭 (V7.0)")
        st.markdown("""
        **核心功能**：解决策略打架问题，统一决策大脑
        
        - **一票否决权**：退潮期、高潮期、ST股票强制拒绝
        - **加权打分**：市场环境(50%) + 板块地位(30%) + 个股技术(20%)
        - **动态仓位**：根据综合得分输出最佳仓位
        """)
        
        # 模拟输入
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🌤️ 市场环境")
            market_cycle = st.selectbox(
                "市场周期",
                ["MAIN_RISE", "BOOM", "CHAOS", "ICE", "DECLINE"]
            )
            risk_level = st.slider("风险等级", 1, 5, 3)
        
        with col2:
            st.markdown("#### 🎯 板块地位")
            is_in_main_theme = st.checkbox("在主线板块", True)
            sector_rank = st.slider("板块排名", 1, 10, 1)
            theme_heat = st.slider("板块热度", 0.0, 0.2, 0.1, 0.01)
        
        with col3:
            st.markdown("#### 📈 个股技术")
            stock_score = st.slider("个股评分", 0, 100, 85)
            is_dragon = st.checkbox("是龙头股", True)
            is_limit_up = st.checkbox("是涨停板", False)
            is_anti_nuclear = st.checkbox("是反核模式", False)
        
        # 构建信号数据
        stock_signal = {
            'signal': 'BUY',
            'score': stock_score * 1.2 if is_dragon else stock_score,
            'is_limit_up': is_limit_up,
            'is_anti_nuclear': is_anti_nuclear,
            'is_dragon': is_dragon,
            'strategy_type': 'MAIN_RISE' if not is_anti_nuclear else 'ANTI_NUCLEAR'
        }
        
        market_status = {
            'cycle': market_cycle,
            'risk_level': risk_level,
            'limit_up_count': 0,
            'limit_down_count': 0
        }
        
        theme_info = {
            'main_theme': '华为鸿蒙',
            'theme_heat': theme_heat,
            'is_in_main_theme': is_in_main_theme,
            'sector_rank': sector_rank
        }
        
        # 执行最终裁决
        if st.button("⚖️ 执行最终裁决"):
            decision, reason, position = orchestrator.final_judgement(
                stock_signal, market_status, theme_info, use_kelly=True
            )
            
            # 显示结果
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("最终决策", decision.value)
            
            with col2:
                st.metric("决策原因", reason[:20] + "...")
            
            with col3:
                st.metric("建议仓位", f"{position*100:.1f}%")
            
            # 详细说明
            st.markdown(f"#### 📝 决策详情")
            st.markdown(f"- **最终决策**: {decision.value}")
            st.markdown(f"- **决策原因**: {reason}")
            st.markdown(f"- **建议仓位**: {position*100:.1f}%")
            
            # 显示一票否决检查
            veto_result, veto_reason = orchestrator._check_veto_power(stock_signal, market_status)
            if veto_result:
                st.error(f"🚫 触发一票否决: {veto_reason}")
            else:
                st.success("✅ 通过一票否决检查")
    
    # Tab 3: 动态凯利公式
    with tab3:
        st.markdown("### 💰 动态凯利公式 (V7.0)")
        st.markdown("""
        **核心功能**：智能仓位管理，根据胜率和赔率自动计算最佳仓位
        
        - **反核战法**：胜率低(35%)，赔率高(1:2) → 小仓位(10%)博弈
        - **龙回头战法**：胜率中(55%)，赔率中(1:1.5) → 中仓位(30%)
        - **主升浪龙头**：胜率高(70%)，赔率稳(1:1.2) → 重仓(50%+)猛干
        """)
        
        # 模拟输入
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 策略参数")
            strategy_type = st.selectbox(
                "策略类型",
                ["MAIN_RISE", "ANTI_NUCLEAR", "DRAGON_RETURN"]
            )
            market_cycle = st.selectbox(
                "市场周期",
                ["MAIN_RISE", "BOOM", "CHAOS", "ICE", "DECLINE"]
            )
        
        with col2:
            st.markdown("#### 🎯 历史参数（模拟）")
            win_rate = st.slider("历史胜率", 0.0, 1.0, 0.55, 0.05)
            odds = st.slider("历史赔率", 0.5, 3.0, 1.5, 0.1)
        
        # 凯利公式计算
        if st.button("💰 计算最佳仓位"):
            q = 1 - win_rate
            
            if odds > 0:
                kelly_position = (odds * win_rate - q) / odds
            else:
                kelly_position = 0
            
            # 半凯利
            real_position = kelly_position * 0.5
            real_position = max(0.0, min(real_position, 0.8))
            
            # 显示结果
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("胜率", f"{win_rate*100:.1f}%")
            
            with col2:
                st.metric("赔率", f"1:{odds:.1f}")
            
            with col3:
                st.metric("凯利仓位", f"{kelly_position*100:.1f}%")
            
            with col4:
                st.metric("实战仓位", f"{real_position*100:.1f}%")
            
            # 可视化仓位分配
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = real_position * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "建议仓位 (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 20], 'color': "lightgray"},
                        {'range': [20, 40], 'color': "gray"},
                        {'range': [40, 60], 'color': "lightblue"},
                        {'range': [60, 80], 'color': "blue"},
                        {'range': [80, 100], 'color': "darkblue"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 仓位建议说明
            if real_position >= 0.5:
                st.success(f"🚀 建议重仓 ({real_position*100:.1f}%)：高胜率机会，可以猛干")
            elif real_position >= 0.3:
                st.info(f"⚡ 建议中仓 ({real_position*100:.1f}%)：中等机会，适度参与")
            elif real_position >= 0.1:
                st.warning(f"⚠️ 建议轻仓 ({real_position*100:.1f}%)：低胜率机会，小仓位博弈")
            else:
                st.error(f"🚫 建议空仓 (0%)：风险过高，放弃机会")
    
    # 关闭资源
    orchestrator.close()
    theme_detector.close()
    market_cycle_manager.close()


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="V7.0 新功能", layout="wide")
    render_v70_features_tab(None, None)