#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16 战场指挥官 (The Commander) UI 模块
展示市场情绪和环境熔断效果，实现"看天吃饭"功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from logic.signal_generator import get_signal_generator_v14_4
from logic.market_sentiment import MarketSentiment
from logic.logger import get_logger

logger = get_logger(__name__)


def render_market_commander(data_manager=None):
    """
    渲染战场指挥官展示面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("⚔️ V16 战场指挥官 (The Commander)")

    st.markdown("""
    **V16 核心变革**：
    - ❌ V15: 关注"单兵作战能力"（这只股票好不好？）
    - ✅ V16: 关注"战场环境"（今天适合打仗吗？）
    
    **环境公理**：
    - ❄️ 冰点熔断：市场情绪 < 20，禁止开仓
    - 🌊 退潮减权：市场退潮期，评分降级
    - 🚀 共振加强：市场情绪高昂 + 趋势向上，评分 +10
    """)

    # 侧边栏配置
    with st.sidebar:
        st.markdown("### ⚙️ 测试配置")
        
        stock_code = st.text_input("股票代码", value="603056", help="例如：603056", key="market_commander_stock_code")
        
        # 模拟数据输入
        st.markdown("#### 📊 个股数据")
        
        ai_score = st.slider(
            "AI 评分",
            min_value=0,
            max_value=100,
            value=90,
            help="AI 基于新闻和技术面的评分"
        )
        
        capital_flow = st.slider(
            "资金流向（万元）",
            min_value=-10000,
            max_value=10000,
            value=1000,
            help="正数为流入，负数为流出"
        )
        
        trend_status = st.selectbox(
            "趋势状态",
            options=['UP', 'DOWN', 'SIDEWAY'],
            index=0,
            help="技术面趋势"
        )
        
        current_pct_change = st.slider(
            "当前涨幅（%）",
            min_value=-10.0,
            max_value=20.0,
            value=5.0,
            step=0.1,
            help="当前价格涨跌幅"
        )
        
        st.markdown("#### 🌤️ 市场环境")
        
        market_sentiment_score = st.slider(
            "市场情绪分数",
            min_value=0,
            max_value=100,
            value=50,
            help="市场情绪分数（0-100），0=极度恐慌，100=极度兴奋"
        )
        
        market_status = st.selectbox(
            "市场状态",
            options=['主升', '退潮', '震荡', '冰点'],
            index=2,
            help="市场状态"
        )
        
        st.markdown("---")
        st.markdown("### 💡 环境公理说明")
        st.info("""
        **V16 环境熔断逻辑**：
        
        **1. 冰点熔断（Ice Age）**
        - 条件：市场情绪 < 20
        - 信号：WAIT
        - 豁免：涨停股可以穿越冰点
        - 理由：市场极度恐慌，禁止开仓
        
        **2. 退潮减权（Ebb Tide）**
        - 条件：市场退潮期
        - 信号：AI 分数 x 0.5
        - 理由：市场正在退潮，可能是补涨或诱多
        
        **3. 共振加强（Resonance）**
        - 条件：市场情绪 > 60 + 趋势向上
        - 信号：最终评分 +10
        - 理由：顺势而为，共振加强
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 开始环境分析")

        if st.button("🚀 运行 V16 分析", type="primary"):
            with st.spinner("正在运行环境熔断分析..."):
                try:
                    # V16 决策
                    sg = get_signal_generator_v14_4()
                    result = sg.calculate_final_signal(
                        stock_code=stock_code,
                        ai_score=ai_score,
                        capital_flow=capital_flow * 10000,  # 转换为元
                        trend=trend_status,
                        current_pct_change=current_pct_change,
                        market_sentiment_score=market_sentiment_score,
                        market_status=market_status
                    )
                    
                    # 保存到 session state
                    st.session_state['v16_result'] = result
                    st.session_state['input_params'] = {
                        'stock_code': stock_code,
                        'ai_score': ai_score,
                        'capital_flow': capital_flow,
                        'trend': trend_status,
                        'current_pct_change': current_pct_change,
                        'market_sentiment_score': market_sentiment_score,
                        'market_status': market_status
                    }
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    logger.error(f"V16 分析失败: {e}")
                    st.error(f"V16 分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'v16_result' in st.session_state:
            result = st.session_state['v16_result']
            
            st.metric(
                "V16 最终得分",
                f"{result['score']:.1f}",
                delta=f"信号: {result['signal']}",
                delta_color="normal" if result['signal'] == 'BUY' else "inverse"
            )
            
            st.metric(
                "市场情绪",
                f"{result['market_sentiment_score']:.1f}",
                delta=f"状态: {result['market_status']}"
            )
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'v16_result' in st.session_state:
        result = st.session_state['v16_result']
        params = st.session_state['input_params']
        
        # 1. 环境熔断分析
        st.markdown("### ❄️ 环境熔断分析")
        
        # 判断环境熔断场景
        market_score = params['market_sentiment_score']
        market_state = params['market_status']
        
        scenario = "正常环境"
        scenario_color = "gray"
        scenario_emoji = "📊"
        
        if market_score < 20:
            if params['current_pct_change'] > 9.5:
                scenario = "冰点 + 涨停豁免"
                scenario_color = "green"
                scenario_emoji = "🚀"
            else:
                scenario = "冰点熔断"
                scenario_color = "red"
                scenario_emoji = "❄️"
        elif market_state == "退潮":
            scenario = "退潮减权"
            scenario_color = "orange"
            scenario_emoji = "🌊"
        elif market_score > 60 and params['trend'] == 'UP':
            scenario = "共振加强"
            scenario_color = "green"
            scenario_emoji = "🚀"
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if scenario_color == "red":
                st.error(f"{scenario_emoji} **{scenario}**")
            elif scenario_color == "green":
                st.success(f"{scenario_emoji} **{scenario}**")
            elif scenario_color == "orange":
                st.warning(f"{scenario_emoji} **{scenario}**")
            else:
                st.info(f"{scenario_emoji} **{scenario}**")
        
        with col_b:
            st.write(f"**市场情绪分数**: {market_score}")
            st.write(f"**市场状态**: {market_state}")
        
        st.markdown("---")
        
        # 2. V16 决策详情
        st.markdown("### 🎯 V16 决策详情")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📊 输入参数")
            st.write(f"- **股票代码**: {params['stock_code']}")
            st.write(f"- **AI 评分**: {params['ai_score']}")
            st.write(f"- **资金流向**: {params['capital_flow']}万元")
            st.write(f"- **趋势状态**: {params['trend']}")
            st.write(f"- **当前涨幅**: {params['current_pct_change']}%")
            st.write(f"- **市场情绪分数**: {params['market_sentiment_score']}")
            st.write(f"- **市场状态**: {params['market_status']}")
            
            st.markdown("#### 🚦 信号")
            if result['signal'] == 'BUY':
                st.success(f"**信号**: {result['signal']}")
            elif result['signal'] == 'SELL':
                st.error(f"**信号**: {result['signal']}")
            else:
                st.warning(f"**信号**: {result['signal']}")
            
            st.markdown(f"**理由**: {result['reason']}")
            
            if result['risk'] == 'HIGH':
                st.error("⚠️ 高风险")
            elif result['risk'] == 'MEDIUM':
                st.warning("⚠️ 中等风险")
            else:
                st.success("✅ 低风险")
        
        with col_b:
            st.markdown("#### 📊 得分分析")
            st.write(f"- **最终得分**: {result['score']:.1f}")
            
            # 分析得分构成
            if market_score < 20:
                if params['current_pct_change'] > 9.5:
                    st.success("🚀 **冰点豁免**: 涨停股可以穿越冰点")
                else:
                    st.error("❄️ **冰点熔断**: 市场极度恐慌，禁止开仓")
            elif market_state == "退潮":
                st.warning("🌊 **退潮减权**: AI 分数 x 0.5")
                st.write(f"   原始分数: {params['ai_score']}")
                st.write(f"   降级分数: {result['score']:.1f}")
            elif market_score > 60 and params['trend'] == 'UP':
                st.success("🚀 **共振加强**: 最终评分 +10")
                st.write(f"   基础分数: {result['score'] - 10:.1f}")
                st.write(f"   共振加分: +10")
            
            st.markdown("---")
            st.markdown("#### 💡 V16 核心优势")
            st.info("""
            **1. 冰点熔断**
            - 市场情绪 < 20，禁止开仓
            - 避免在极度恐慌时买入
            
            **2. 退潮减权**
            - 市场退潮期，评分降级
            - 避免补涨或诱多陷阱
            
            **3. 共振加强**
            - 市场情绪高昂 + 趋势向上
            - 顺势而为，共振加强
            
            **4. 涨停豁免**
            - 涨停股可以穿越冰点
            - 只有真龙能穿越冰点
            """)
        
        st.markdown("---")
        
        # 3. 环境场景对比图
        st.markdown("### 📊 环境场景对比")
        
        # 创建对比表
        scenarios_data = {
            '场景': ['冰点熔断', '退潮减权', '共振加强', '正常环境'],
            '市场情绪分数': ['< 20', '任意', '> 60', '20-60'],
            '市场状态': ['任意', '退潮', '主升', '震荡'],
            '信号': ['WAIT', 'WAIT', 'BUY', '正常计算'],
            '得分调整': ['禁止开仓', 'AI x0.5', '+10', '正常'],
            '理由': ['极度恐慌', '补涨或诱多', '顺势而为', '正常判断']
        }
        
        df_scenarios = pd.DataFrame(scenarios_data)
        st.dataframe(df_scenarios, use_container_width=True)
        
        # 创建对比图
        fig = go.Figure()
        
        # 不同场景的得分调整
        fig.add_trace(go.Bar(
            name='冰点熔断',
            x=['AI 评分'],
            y=[0],
            marker_color='#3498db'
        ))
        
        fig.add_trace(go.Bar(
            name='退潮减权',
            x=['AI 评分'],
            y=[params['ai_score'] * 0.5],
            marker_color='#e74c3c'
        ))
        
        fig.add_trace(go.Bar(
            name='共振加强',
            x=['AI 评分'],
            y=[min(params['ai_score'] + 10, 100)],
            marker_color='#2ecc71'
        ))
        
        fig.add_trace(go.Bar(
            name='正常环境',
            x=['AI 评分'],
            y=[params['ai_score']],
            marker_color='#f39c12'
        ))
        
        fig.update_layout(
            title="V16 环境场景得分对比",
            xaxis_title="场景",
            yaxis_title="最终得分",
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
                'stock_code': params['stock_code'],
                'v16_result': result,
                'input_params': params,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"v16_market_commander_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            md_report = f"""# V16 战场指挥官分析报告

**股票代码**: {params['stock_code']}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 V16 决策结果

- **最终得分**: {result['score']:.1f}
- **信号**: {result['signal']}
- **风险等级**: {result['risk']}
- **理由**: {result['reason']}

---

## 🌤️ 市场环境

**市场情绪分数**: {params['market_sentiment_score']}
**市场状态**: {params['market_status']}

**输入参数**:
- AI 评分: {params['ai_score']}
- 资金流向: {params['capital_flow']}万元
- 趋势状态: {params['trend']}
- 当前涨幅: {params['current_pct_change']}%

---

## 💡 V16 环境熔断逻辑

**冰点熔断（Ice Age）**:
- 条件：市场情绪 < 20
- 信号：WAIT
- 豁免：涨停股可以穿越冰点
- 理由：市场极度恐慌，禁止开仓

**退潮减权（Ebb Tide）**:
- 条件：市场退潮期
- 信号：AI 分数 x 0.5
- 理由：市场正在退潮，可能是补涨或诱多

**共振加强（Resonance）**:
- 条件：市场情绪 > 60 + 趋势向上
- 信号：最终评分 +10
- 理由：顺势而为，共振加强

**涨停豁免**:
- 条件：个股涨停
- 豁免：可以穿越冰点
- 理由：只有真龙能穿越冰点

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*V16 The Commander v1.0*
"""
            
            st.download_button(
                label="📝 下载 Markdown 报告",
                data=md_report,
                file_name=f"v16_market_commander_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("👈 点击左侧按钮开始分析")


if __name__ == '__main__':
    # 测试运行
    render_market_commander()