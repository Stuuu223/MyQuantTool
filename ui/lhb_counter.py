#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V14.4 龙虎榜反制 (LHB Counter-Strike) UI 模块
展示龙虎榜博弈逻辑，识别陷阱和弱转强机会
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from logic.signal_generator import get_signal_generator_v14_4
from logic.logger import get_logger

logger = get_logger(__name__)


def render_lhb_counter(data_manager=None):
    """
    渲染龙虎榜反制展示面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("🎯 V14.4 龙虎榜反制 (LHB Counter-Strike)")

    st.markdown("""
    **V14.4 核心变革**：
    - ❌ V14.3: 被动跟随龙虎榜
    - ✅ V14.4: 主动博弈，识别陷阱和弱转强
    
    **博弈策略**：
    - 🚨 陷阱识别：豪华榜 + 高开 > 6% → WAIT（警惕兑现）
    - 🚀 弱转强：豪华榜 + 平开 (-2%~3%) → BUY + 30%溢价
    - 📉 不及预期：豪华榜 + 低开 < -3% → 50%信心
    """)

    # 侧边栏配置
    with st.sidebar:
        st.markdown("### ⚙️ 测试配置")
        
        stock_code = st.text_input("股票代码", value="600000", help="例如：600000")
        
        # 模拟数据输入
        st.markdown("#### 📊 模拟数据")
        
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
        
        st.markdown("#### 🎯 龙虎榜数据")
        
        yesterday_lhb_net_buy = st.slider(
            "昨日龙虎榜净买入（万元）",
            min_value=0,
            max_value=100000,
            value=6000,
            help="昨日龙虎榜净买入额，>5000万为豪华榜"
        )
        
        open_pct_change = st.slider(
            "今日开盘涨幅（%）",
            min_value=-10.0,
            max_value=10.0,
            value=0.5,
            step=0.1,
            help="今日开盘涨跌幅"
        )
        
        circulating_market_cap = st.number_input(
            "流通市值（亿元）",
            min_value=0,
            max_value=10000,
            value=100,
            help="流通市值，用于计算失血比例"
        )
        
        st.markdown("---")
        st.markdown("### 💡 博弈策略说明")
        st.info("""
        **V14.4 龙虎榜博弈逻辑**：
        
        **1. 陷阱识别（The Trap）**
        - 条件：豪华榜（>5000万）+ 高开（>6%）
        - 信号：WAIT
        - 理由：警惕主力兑现
        
        **2. 弱转强（Weak-to-Strong）**
        - 条件：豪华榜（>5000万）+ 平开（-2%~3%）
        - 信号：BUY + 30%溢价
        - 理由：主力承接有力
        
        **3. 不及预期**
        - 条件：豪华榜（>5000万）+ 低开（<-3%）
        - 信号：WAIT（50%信心）
        - 理由：豪华榜被核
        
        **4. 普通榜单**
        - 条件：净买入 <= 5000万
        - 信号：正常计算
        - 理由：无博弈价值
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 开始博弈分析")

        if st.button("🚀 运行 V14.4 分析", type="primary"):
            with st.spinner("正在运行龙虎榜博弈分析..."):
                try:
                    # V14.4 决策
                    sg = get_signal_generator_v14_4()
                    result = sg.calculate_final_signal(
                        stock_code=stock_code,
                        ai_score=ai_score,
                        capital_flow=capital_flow * 10000,  # 转换为元
                        trend=trend_status,
                        current_pct_change=current_pct_change,
                        yesterday_lhb_net_buy=yesterday_lhb_net_buy * 10000,  # 转换为元
                        open_pct_change=open_pct_change,
                        circulating_market_cap=circulating_market_cap * 100000000  # 转换为元
                    )
                    
                    # 保存到 session state
                    st.session_state['v14_4_result'] = result
                    st.session_state['input_params'] = {
                        'stock_code': stock_code,
                        'ai_score': ai_score,
                        'capital_flow': capital_flow,
                        'trend': trend_status,
                        'current_pct_change': current_pct_change,
                        'yesterday_lhb_net_buy': yesterday_lhb_net_buy,
                        'open_pct_change': open_pct_change,
                        'circulating_market_cap': circulating_market_cap
                    }
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    logger.error(f"V14.4 分析失败: {e}")
                    st.error(f"V14.4 分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'v14_4_result' in st.session_state:
            result = st.session_state['v14_4_result']
            
            st.metric(
                "V14.4 最终得分",
                f"{result['score']:.1f}",
                delta=f"信号: {result['signal']}",
                delta_color="normal" if result['signal'] == 'BUY' else "inverse"
            )
            
            st.metric(
                "风险等级",
                f"{result['risk']}",
                delta="博弈策略"
            )
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'v14_4_result' in st.session_state:
        result = st.session_state['v14_4_result']
        params = st.session_state['input_params']
        
        # 1. 博弈场景识别
        st.markdown("### 🎯 博弈场景识别")
        
        # 判断博弈场景
        lhb_net_buy = params['yesterday_lhb_net_buy']
        open_pct = params['open_pct_change']
        
        scenario = "普通榜单"
        scenario_color = "gray"
        scenario_emoji = "📊"
        
        if lhb_net_buy > 50:  # > 5000万，豪华榜
            if open_pct > 6.0:
                scenario = "陷阱识别（The Trap）"
                scenario_color = "red"
                scenario_emoji = "🚨"
            elif -2.0 <= open_pct <= 3.0:
                scenario = "弱转强（Weak-to-Strong）"
                scenario_color = "green"
                scenario_emoji = "🚀"
            elif open_pct < -3.0:
                scenario = "不及预期"
                scenario_color = "orange"
                scenario_emoji = "📉"
        
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
            st.write(f"**豪华榜净买入**: {lhb_net_buy}万元")
            st.write(f"**今日开盘涨幅**: {open_pct}%")
        
        st.markdown("---")
        
        # 2. V14.4 决策详情
        st.markdown("### 🎯 V14.4 决策详情")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📊 输入参数")
            st.write(f"- **股票代码**: {params['stock_code']}")
            st.write(f"- **AI 评分**: {params['ai_score']}")
            st.write(f"- **资金流向**: {params['capital_flow']}万元")
            st.write(f"- **趋势状态**: {params['trend']}")
            st.write(f"- **当前涨幅**: {params['current_pct_change']}%")
            st.write(f"- **昨日龙虎榜净买入**: {params['yesterday_lhb_net_buy']}万元")
            st.write(f"- **今日开盘涨幅**: {params['open_pct_change']}%")
            st.write(f"- **流通市值**: {params['circulating_market_cap']}亿元")
            
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
            if lhb_net_buy > 50:  # 豪华榜
                if open_pct > 6.0:
                    st.warning("⚠️ **陷阱惩罚**: AI 分数被打折至 10 分")
                elif -2.0 <= open_pct <= 3.0:
                    st.success("🚀 **弱转强溢价**: AI 分数 x1.3")
                elif open_pct < -3.0:
                    st.warning("📉 **不及预期**: AI 分数 x0.5")
            else:
                st.info("📊 **普通榜单**: 正常计算")
            
            # 资金流向分析
            if params['capital_flow'] < 0 and params['trend'] == 'UP':
                st.warning("⚠️ **量价背离**: 缩量/流出上涨，AI 分数 x0.4")
            elif params['capital_flow'] > 0:
                st.success("✅ **资金流入**: 逻辑+资金双强")
            
            st.markdown("---")
            st.markdown("#### 💡 V14.4 核心优势")
            st.info("""
            **1. 陷阱识别**
            - 豪华榜 + 高开 → 警惕兑现
            - 避免成为接盘侠
            
            **2. 弱转强博弈**
            - 豪华榜 + 平开 → 主力承接有力
            - 给予 30% 溢价
            
            **3. 不及预期**
            - 豪华榜 + 低开 → 被核
            - 降低信心至 50%
            
            **4. 普通榜单**
            - 无博弈价值
            - 正常计算
            """)
        
        st.markdown("---")
        
        # 3. 博弈场景对比图
        st.markdown("### 📊 博弈场景对比")
        
        # 创建对比表
        scenarios_data = {
            '场景': ['陷阱识别', '弱转强', '不及预期', '普通榜单'],
            '豪华榜净买入': ['>5000万', '>5000万', '>5000万', '≤5000万'],
            '开盘涨幅': ['>6%', '-2%~3%', '<-3%', '任意'],
            '信号': ['WAIT', 'BUY', 'WAIT', '正常计算'],
            '得分调整': ['AI x0.0', 'AI x1.3', 'AI x0.5', '正常'],
            '理由': ['警惕兑现', '主力承接有力', '被核', '无博弈价值']
        }
        
        df_scenarios = pd.DataFrame(scenarios_data)
        st.dataframe(df_scenarios, use_container_width=True)
        
        # 创建对比图
        fig = go.Figure()
        
        # 不同场景的得分调整
        fig.add_trace(go.Bar(
            name='陷阱识别',
            x=['AI 评分'],
            y=[10],
            marker_color='#ff7f0e'
        ))
        
        fig.add_trace(go.Bar(
            name='弱转强',
            x=['AI 评分'],
            y=[params['ai_score'] * 1.3],
            marker_color='#1f77b4'
        ))
        
        fig.add_trace(go.Bar(
            name='不及预期',
            x=['AI 评分'],
            y=[params['ai_score'] * 0.5],
            marker_color='#ff7f0e'
        ))
        
        fig.add_trace(go.Bar(
            name='普通榜单',
            x=['AI 评分'],
            y=[params['ai_score']],
            marker_color='#2ca02c'
        ))
        
        fig.update_layout(
            title="V14.4 博弈场景得分对比",
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
                'v14_4_result': result,
                'input_params': params,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"v14_4_lhb_counter_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            md_report = f"""# V14.4 龙虎榜反制分析报告

**股票代码**: {params['stock_code']}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 V14.4 决策结果

- **最终得分**: {result['score']:.1f}
- **信号**: {result['signal']}
- **风险等级**: {result['risk']}
- **理由**: {result['reason']}

---

## 🎯 博弈场景识别

**场景**: {scenario}

**输入参数**:
- AI 评分: {params['ai_score']}
- 资金流向: {params['capital_flow']}万元
- 趋势状态: {params['trend']}
- 当前涨幅: {params['current_pct_change']}%
- 昨日龙虎榜净买入: {params['yesterday_lhb_net_buy']}万元
- 今日开盘涨幅: {params['open_pct_change']}%
- 流通市值: {params['circulating_market_cap']}亿元

---

## 💡 V14.4 博弈策略

**陷阱识别（The Trap）**:
- 条件：豪华榜（>5000万）+ 高开（>6%）
- 信号：WAIT
- 理由：警惕主力兑现

**弱转强（Weak-to-Strong）**:
- 条件：豪华榜（>5000万）+ 平开（-2%~3%）
- 信号：BUY + 30%溢价
- 理由：主力承接有力

**不及预期**:
- 条件：豪华榜（>5000万）+ 低开（<-3%）
- 信号：WAIT（50%信心）
- 理由：豪华榜被核

**普通榜单**:
- 条件：净买入 <= 5000万
- 信号：正常计算
- 理由：无博弈价值

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*V14.4 LHB Counter-Strike v1.0*
"""
            
            st.download_button(
                label="📝 下载 Markdown 报告",
                data=md_report,
                file_name=f"v14_4_lhb_counter_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("👈 点击左侧按钮开始分析")


if __name__ == '__main__':
    # 测试运行
    render_lhb_counter()