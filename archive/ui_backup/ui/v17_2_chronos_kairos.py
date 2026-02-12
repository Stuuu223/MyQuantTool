#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17.2 Chronos-Kairos Fusion - 时空融合 UI 模块
展示情绪覆盖时间策略的功能，实现"情绪 > 时间"的优先级机制
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from logic.utils import Utils
from logic.time_strategy_manager import get_time_strategy_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_chronos_kairos_panel():
    """
    渲染 V17.2 时空融合面板
    """
    st.subheader("🌌 V17.2 时空融合 (Chronos-Kairos Fusion)")

    st.markdown("""
    **V17.2 核心变革**：
    - 🕐 Chronos (时间)：分时段策略（黄金半小时、垃圾时间、尾盘偷袭）
    - 🔥 Kairos (情绪)：市场情绪爆发时，打破时间限制
    - 🌌 Fusion (融合)：情绪 > 时间，防止踏空突发利好
    
    **时空融合逻辑**：
    - 情绪爆发（>80）：即使是在垃圾时间，也要强制切换为进攻模式
    - 情绪冰点（<20）：即使是在黄金时间，也要强制切换为防守模式
    - 正常情绪（20-80）：遵循原有时间策略
    """)

    # 侧边栏配置
    with st.sidebar:
        st.markdown("### ⚙️ 测试配置")
        
        # 模拟市场情绪
        st.markdown("#### 📊 市场情绪模拟")
        
        sentiment_score = st.slider(
            "市场情绪分数",
            min_value=0,
            max_value=100,
            value=50,
            step=1,
            help="0-100，分数越高表示市场情绪越热"
        )
        
        # 显示情绪状态
        if sentiment_score >= 80:
            st.error(f"🔥 情绪爆发 ({sentiment_score})")
            st.info("将打破时间限制，强制进攻")
        elif sentiment_score <= 20:
            st.warning(f"❄️ 情绪冰点 ({sentiment_score})")
            st.info("将强制防守，规避风险")
        else:
            st.success(f"✅ 正常情绪 ({sentiment_score})")
            st.info("遵循原有时间策略")
        
        # 模拟时间
        st.markdown("#### 🕐 时间模拟")
        
        current_hour = st.slider(
            "当前小时",
            min_value=0,
            max_value=23,
            value=11,
            step=1
        )
        
        current_minute = st.slider(
            "当前分钟",
            min_value=0,
            max_value=59,
            value=0,
            step=5
        )
        
        # 显示时间状态
        simulated_time = datetime(2026, 1, 18, current_hour, current_minute)
        time_str = simulated_time.strftime('%H:%M')
        
        if 9 <= current_hour < 10:
            st.success(f"🌅 黄金半小时 ({time_str})")
        elif 10 <= current_hour < 14 or (current_hour == 14 and current_minute < 30):
            st.warning(f"🗑️ 垃圾时间 ({time_str})")
        elif 14 <= current_hour < 15:
            st.success(f"🎯 尾盘偷袭 ({time_str})")
        else:
            st.info(f"😴 非交易时间 ({time_str})")
        
        st.markdown("---")
        st.markdown("### 💡 时空融合策略说明")
        st.info("""
        **V17.2 时空融合逻辑**：
        
        **1. 情绪爆发（>80）**
        - 条件：市场情绪分数 > 80
        - 行为：打破时间限制，强制进攻
        - 场景：突发重大利好，市场情绪瞬间飙升
        
        **2. 情绪冰点（<20）**
        - 条件：市场情绪分数 < 20
        - 行为：强制防守，规避风险
        - 场景：突发重大利空，市场恐慌
        
        **3. 正常情绪（20-80）**
        - 条件：市场情绪分数在 20-80 之间
        - 行为：遵循原有时间策略
        - 场景：正常的市场波动
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 时空融合分析")

        if st.button("🚀 运行 V17.2 分析", type="primary"):
            with st.spinner("正在运行时空融合分析..."):
                try:
                    # 获取时间策略管理器
                    time_manager = get_time_strategy_manager()
                    
                    # 获取当前模式（传入情绪分数）
                    mode_info = time_manager.get_current_mode(
                        current_time=simulated_time,
                        sentiment_score=sentiment_score
                    )
                    
                    # 保存到 session state
                    st.session_state['v17_2_result'] = mode_info
                    st.session_state['input_params'] = {
                        'sentiment_score': sentiment_score,
                        'simulated_time': simulated_time
                    }
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    logger.error(f"V17.2 分析失败: {e}")
                    st.error(f"V17.2 分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'v17_2_result' in st.session_state:
            result = st.session_state['v17_2_result']
            
            st.metric(
                "当前模式",
                result['mode_name'],
                delta="情绪覆盖" if result['sentiment_override'] else "时间策略",
                delta_color="normal" if result['sentiment_override'] else "inverse"
            )
            
            st.metric(
                "允许买入",
                "✅" if result['allow_buy'] else "❌",
                delta=f"情绪分数: {result['sentiment_score']:.1f}"
            )
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'v17_2_result' in st.session_state:
        result = st.session_state['v17_2_result']
        params = st.session_state['input_params']
        
        # 1. 时空融合状态
        st.markdown("### 🌌 时空融合状态")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.metric(
                "市场情绪",
                f"{params['sentiment_score']:.1f}",
                delta="爆发" if params['sentiment_score'] >= 80 else "冰点" if params['sentiment_score'] <= 20 else "正常",
                delta_color="normal" if params['sentiment_score'] >= 80 else "inverse" if params['sentiment_score'] <= 20 else "off"
            )
        
        with col_b:
            st.metric(
                "当前时间",
                params['simulated_time'].strftime('%H:%M'),
                delta=result['mode_name']
            )
        
        with col_c:
            if result['sentiment_override']:
                st.success("🔥 情绪覆盖时间")
            else:
                st.info("⏰ 遵循时间策略")
        
        st.markdown("---")
        
        # 2. V17.2 决策详情
        st.markdown("### 🎯 V17.2 决策详情")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📊 输入参数")
            st.write(f"- **市场情绪分数**: {params['sentiment_score']:.1f}")
            st.write(f"- **模拟时间**: {params['simulated_time'].strftime('%H:%M')}")
            
            st.markdown("#### 🚦 交易模式")
            if result['sentiment_override']:
                st.warning(f"⚠️ **情绪覆盖**: {result['mode_name']}")
            else:
                st.info(f"⏰ **时间策略**: {result['mode_name']}")
            
            st.markdown(f"**描述**: {result['description']}")
            st.markdown(f"**建议**: {result['recommendation']}")
            
            st.markdown("#### ✅ 操作权限")
            st.write(f"- **允许买入**: {'✅' if result['allow_buy'] else '❌'}")
            st.write(f"- **允许卖出**: {'✅' if result['allow_sell'] else '❌'}")
            st.write(f"- **扫描间隔**: {result['scan_interval']} 秒")
        
        with col_b:
            st.markdown("#### 📊 模式分析")
            
            # 情绪分析
            if params['sentiment_score'] >= 80:
                st.error("🔥 **情绪爆发**")
                st.write("市场情绪极热，打破时间限制，强制进攻！")
                st.write("即使是在垃圾时间，也要积极买入，抓住主升浪机会。")
            elif params['sentiment_score'] <= 20:
                st.warning("❄️ **情绪冰点**")
                st.write("市场情绪极冷，强制防守，规避风险。")
                st.write("即使是在黄金时间，也要谨慎操作，只卖不买。")
            else:
                st.success("✅ **正常情绪**")
                st.write("市场情绪正常，遵循原有时间策略。")
                st.write("根据不同时间段采取相应的交易策略。")
            
            st.markdown("---")
            st.markdown("#### 💡 V17.2 核心优势")
            st.info("""
            **1. 防止踏空**
            - 突发重大利好时，情绪飙升 > 80
            - 打破垃圾时间限制，强制进攻
            - 避免因时间策略而踏空
            
            **2. 规避风险**
            - 突发重大利空时，情绪暴跌 < 20
            - 强制防守，规避风险
            - 避免因时间策略而盲目买入
            
            **3. 智能融合**
            - 情绪 > 时间，灵活应变
            - 正常情况下遵循时间策略
            - 极端情况下情绪覆盖时间
            """)
        
        st.markdown("---")
        
        # 3. 时空融合对比图
        st.markdown("### 📊 时空融合对比")
        
        # 创建对比表
        scenarios_data = {
            '情绪状态': ['情绪爆发', '情绪冰点', '正常情绪'],
            '情绪分数': ['> 80', '< 20', '20-80'],
            '时间策略': ['覆盖', '覆盖', '遵循'],
            '垃圾时间行为': ['进攻', '防守', '防守'],
            '黄金时间行为': ['进攻', '防守', '进攻']
        }
        
        df_scenarios = pd.DataFrame(scenarios_data)
        st.dataframe(df_scenarios, use_container_width=True)
        
        # 创建对比图
        fig = go.Figure()
        
        # 不同情绪状态下的行为
        time_periods = ['黄金半小时', '垃圾时间', '尾盘偷袭']
        
        fig.add_trace(go.Bar(
            name='情绪爆发 (>80)',
            x=time_periods,
            y=[1, 1, 1],  # 1 表示进攻
            marker_color='#ff7f0e'
        ))
        
        fig.add_trace(go.Bar(
            name='正常情绪 (20-80)',
            x=time_periods,
            y=[1, 0, 1],  # 1 表示进攻，0 表示防守
            marker_color='#1f77b4'
        ))
        
        fig.add_trace(go.Bar(
            name='情绪冰点 (<20)',
            x=time_periods,
            y=[0, 0, 0],  # 0 表示防守
            marker_color='#2ca02c'
        ))
        
        fig.update_layout(
            title="V17.2 时空融合：不同情绪状态下的交易行为",
            xaxis_title="时间段",
            yaxis_title="允许买入 (1=是, 0=否)",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 4. 导出功能
        st.markdown("### 📥 导出分析结果")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # 导出 JSON
            import json
            export_data = {
                'v17_2_result': result,
                'input_params': {
                    'sentiment_score': params['sentiment_score'],
                    'simulated_time': params['simulated_time'].strftime('%H:%M')
                },
                'timestamp': Utils.get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"v17_2_chronos_kairos_{Utils.get_beijing_time().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            md_report = f"""# V17.2 时空融合分析报告

**分析时间**: {Utils.get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 V17.2 决策结果

- **当前模式**: {result['mode_name']}
- **描述**: {result['description']}
- **允许买入**: {'✅' if result['allow_buy'] else '❌'}
- **允许卖出**: {'✅' if result['allow_sell'] else '❌'}
- **建议**: {result['recommendation']}

---

## 🌌 时空融合状态

**情绪状态**: {'爆发' if params['sentiment_score'] >= 80 else '冰点' if params['sentiment_score'] <= 20 else '正常'}
**情绪分数**: {params['sentiment_score']:.1f}
**模拟时间**: {params['simulated_time'].strftime('%H:%M')}
**情绪覆盖**: {'✅ 是' if result['sentiment_override'] else '❌ 否'}

---

## 💡 V17.2 时空融合策略

**情绪爆发（>80）**:
- 条件：市场情绪分数 > 80
- 行为：打破时间限制，强制进攻
- 场景：突发重大利好，市场情绪瞬间飙升

**情绪冰点（<20）**:
- 条件：市场情绪分数 < 20
- 行为：强制防守，规避风险
- 场景：突发重大利空，市场恐慌

**正常情绪（20-80）**:
- 条件：市场情绪分数在 20-80 之间
- 行为：遵循原有时间策略
- 场景：正常的市场波动

---

*报告生成时间: {Utils.get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}*
*V17.2 Chronos-Kairos Fusion v1.0*
"""
            
            st.download_button(
                label="📝 下载 Markdown 报告",
                data=md_report,
                file_name=f"v17_2_chronos_kairos_{Utils.get_beijing_time().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("👈 点击左侧按钮开始分析")


if __name__ == "__main__":
    # 测试
    render_chronos_kairos_panel()