#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V15 "The AI Demotion" UI 模块
展示 AI 降权效果，对比 V14 和 V15 的决策差异
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from logic.ai_agent import RealAIAgent
from logic.signal_generator import SignalGenerator
from logic.logger import get_logger

logger = get_logger(__name__)


def render_ai_demotion(data_manager=None):
    """
    渲染 AI 降权展示面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("🛡️ V15 AI 降权")

    st.markdown("""
    **V15 核心变革**：
    - ❌ V14: AI 是"决策者"（AI 50% + DDE 30% + Trend 20%）
    - ✅ V15: AI 是"信息提取器"（DDE 60% + Trend 40% + AI Bonus）
    
    **哲学**：相信钱（DDE），相信势，别相信嘴（AI）
    """)

    # 侧边栏配置
    with st.sidebar:
        st.markdown("### ⚙️ 测试配置")
        
        stock_code = st.text_input("股票代码", value="600000", help="例如：600000")
        
        # 模拟数据输入
        st.markdown("#### 📊 模拟数据")
        capital_flow = st.slider(
            "资金流向（万元）",
            min_value=-10000,
            max_value=10000,
            value=5000,
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
        
        circulating_market_cap = st.number_input(
            "流通市值（亿元）",
            min_value=0,
            max_value=10000,
            value=100,
            help="流通市值"
        )
        
        st.markdown("---")
        st.markdown("### 🎯 AI 信息提取")
        
        news_text = st.text_area(
            "新闻文本",
            value="XX股份有限公司关于签订重大合同的公告\n本公司与XX科技有限公司签订战略合作协议，合同金额为15.6亿元，涉及人形机器人研发项目。",
            height=150,
            help="输入新闻文本，AI 将提取结构化信息"
        )
        
        st.markdown("---")
        st.markdown("### 🔥 热门板块")
        
        top_sectors_input = st.text_input(
            "热门板块（逗号分隔）",
            value="机器人,人形机器人,AI芯片",
            help="输入今日热门板块，逗号分隔"
        )
        
        top_sectors = [s.strip() for s in top_sectors_input.split(',') if s.strip()]
        
        st.markdown("---")
        st.markdown("### 💡 说明")
        st.info("""
        **V15 决策权重**：
        - DDE（资金流向）：60%（核心）
        - Trend（趋势）：40%（基础）
        - AI Bonus：仅作为辅助加分
        
        **AI 的唯一权力**：
        1. 风险一票否决：检测到风险关键词 → SELL
        2. 概念匹配：命中热门板块 → +10分
        3. 合同金额：大额合同 → +3~5分
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 开始分析")

        if st.button("🚀 运行 V15 分析", type="primary"):
            with st.spinner("正在运行 V15 分析..."):
                try:
                    # 1. AI 信息提取
                    ai_agent = RealAIAgent(api_key="test_key", provider="deepseek")
                    ai_extracted_info = ai_agent.extract_structured_info(news_text)
                    
                    # 2. V15 决策
                    sg = SignalGenerator()
                    result_v15 = sg.calculate_final_signal(
                        stock_code=stock_code,
                        ai_score=50,  # V15: AI 评分不再重要
                        capital_flow=capital_flow * 10000,  # 转换为元
                        trend=trend_status,
                        circulating_market_cap=circulating_market_cap * 100000000,  # 转换为元
                        current_pct_change=current_pct_change
                    )
                    
                    # 3. V14 对比（模拟）
                    result_v14 = {
                        'signal': 'BUY' if capital_flow > 0 else 'SELL',
                        'final_score': 50 + (capital_flow / 100),  # 模拟 V14 评分
                        'reason': f'V14: AI 评分50 + 资金{(capital_flow/100):.1f}',
                        'fact_veto': False,
                        'risk_level': 'MEDIUM',
                        'limit_up_immunity': False,
                        'ai_bonus': 0,
                        'dde_score': 0,
                        'trend_score': 0
                    }
                    
                    # 保存到 session state
                    st.session_state['v15_result'] = result_v15
                    st.session_state['v14_result'] = result_v14
                    st.session_state['ai_extracted_info'] = ai_extracted_info
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    logger.error(f"V15 分析失败: {e}")
                    st.error(f"V15 分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'v15_result' in st.session_state:
            result_v15 = st.session_state['v15_result']
            
            st.metric(
                "V15 最终得分",
                f"{result_v15['final_score']:.1f}",
                delta=f"信号: {result_v15['signal']}",
                delta_color="normal" if result_v15['signal'] == 'BUY' else "inverse"
            )
            
            st.metric(
                "DDE 得分",
                f"{result_v15['dde_score']}/60",
                delta="60% 权重"
            )
            
            st.metric(
                "趋势得分",
                f"{result_v15['trend_score']}/40",
                delta="40% 权重"
            )
            
            if result_v15['ai_bonus'] > 0:
                st.metric(
                    "AI 加分",
                    f"+{result_v15['ai_bonus']}",
                    delta="辅助加分"
                )
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'v15_result' in st.session_state:
        result_v15 = st.session_state['v15_result']
        result_v14 = st.session_state['v14_result']
        ai_extracted_info = st.session_state['ai_extracted_info']
        
        # 1. AI 信息提取结果
        st.markdown("### 🤖 AI 信息提取结果")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if ai_extracted_info['is_official_announcement']:
                st.success("✅ 官方公告")
            else:
                st.info("📄 普通新闻")
            
            if ai_extracted_info['risk_warning']:
                st.error("⚠️ 风险检测")
            else:
                st.success("✅ 无风险")
        
        with col_b:
            if ai_extracted_info['contract_amount']:
                st.metric(
                    "合同金额",
                    f"{ai_extracted_info['contract_amount']:.1f}亿元"
                )
            else:
                st.info("无合同金额")
        
        with col_c:
            if ai_extracted_info['core_concepts']:
                st.write("**核心概念**：")
                for concept in ai_extracted_info['core_concepts']:
                    st.write(f"- {concept}")
            else:
                st.info("无核心概念")
        
        if ai_extracted_info['risk_keywords']:
            st.warning(f"**风险关键词**：{', '.join(ai_extracted_info['risk_keywords'])}")
        
        st.markdown("---")
        
        # 2. V15 vs V14 对比
        st.markdown("### 📊 V15 vs V14 对比")
        
        # 创建对比表格
        comparison_data = {
            '版本': ['V14 (旧)', 'V15 (新)'],
            'AI 角色': ['决策者 (50%)', '信息提取器 (辅助)'],
            'DDE 权重': ['30%', '60%'],
            'Trend 权重': ['20%', '40%'],
            'AI 权重': ['50%', 'Bonus'],
            '最终得分': [f"{result_v14['final_score']:.1f}", f"{result_v15['final_score']:.1f}"],
            '信号': [result_v14['signal'], result_v15['signal']]
        }
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True)
        
        # 创建对比图
        fig = go.Figure()
        
        # V14 得分分解
        fig.add_trace(go.Bar(
            name='V14',
            x=['AI', 'DDE', 'Trend'],
            y=[50, result_v14['final_score'] * 0.3, result_v14['final_score'] * 0.2],
            marker_color='#ff7f0e'
        ))
        
        # V15 得分分解
        fig.add_trace(go.Bar(
            name='V15',
            x=['AI', 'DDE', 'Trend'],
            y=[result_v15['ai_bonus'], result_v15['dde_score'], result_v15['trend_score']],
            marker_color='#1f77b4'
        ))
        
        fig.update_layout(
            title="V15 vs V14 决策权重对比",
            xaxis_title="决策因子",
            yaxis_title="得分",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 3. V15 决策详情
        st.markdown("### 🎯 V15 决策详情")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📊 得分分解")
            st.write(f"- **DDE 得分**: {result_v15['dde_score']}/60 (60% 权重)")
            st.write(f"- **趋势得分**: {result_v15['trend_score']}/40 (40% 权重)")
            if result_v15['ai_bonus'] > 0:
                st.write(f"- **AI 加分**: +{result_v15['ai_bonus']} (辅助)")
            st.write(f"- **最终得分**: {result_v15['final_score']:.1f}")
            
            st.markdown("#### 🚦 信号")
            if result_v15['signal'] == 'BUY':
                st.success(f"**信号**: {result_v15['signal']}")
            elif result_v15['signal'] == 'SELL':
                st.error(f"**信号**: {result_v15['signal']}")
            else:
                st.warning(f"**信号**: {result_v15['signal']}")
            
            st.markdown(f"**理由**: {result_v15['reason']}")
            
            if result_v15['fact_veto']:
                st.error("⚠️ 触发事实熔断")
            
            if result_v15['limit_up_immunity']:
                st.success("🛡️ 涨停豁免权生效")
        
        with col_b:
            st.markdown("#### 🎯 风险等级")
            if result_v15['risk_level'] == 'LOW':
                st.success(f"**风险**: 低风险")
            elif result_v15['risk_level'] == 'MEDIUM':
                st.warning(f"**风险**: 中等风险")
            else:
                st.error(f"**风险**: 高风险")
            
            st.markdown("---")
            st.markdown("#### 💡 V15 核心优势")
            st.info("""
            **1. 资金为王**
            - DDE 权重提升至 60%
            - 资金流出直接否决
            
            **2. 趋势为基**
            - Trend 权重提升至 40%
            - 拒绝接飞刀
            
            **3. AI 降权**
            - AI 不再参与核心决策
            - 仅作为信息提取器
            - 风险检测一票否决
            
            **4. 数据净化**
            - 优先官方公告
            - 屏蔽自媒体 SEO 软文
            """)
        
        st.markdown("---")
        
        # 4. 导出功能
        st.markdown("### 📥 导出分析结果")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # 导出 JSON
            import json
            export_data = {
                'stock_code': stock_code,
                'v15_result': result_v15,
                'v14_result': result_v14,
                'ai_extracted_info': ai_extracted_info,
                'input_data': {
                    'capital_flow': capital_flow,
                    'trend_status': trend_status,
                    'current_pct_change': current_pct_change,
                    'circulating_market_cap': circulating_market_cap,
                    'top_sectors': top_sectors
                },
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"v15_analysis_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            md_report = f"""# V15 AI Demotion 分析报告

**股票代码**: {stock_code}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 V15 决策结果

- **最终得分**: {result_v15['final_score']:.1f}
- **信号**: {result_v15['signal']}
- **风险等级**: {result_v15['risk_level']}
- **理由**: {result_v15['reason']}

### 得分分解

- **DDE 得分**: {result_v15['dde_score']}/60 (60% 权重)
- **趋势得分**: {result_v15['trend_score']}/40 (40% 权重)
- **AI 加分**: +{result_v15['ai_bonus']} (辅助)

---

## 🤖 AI 信息提取结果

- **官方公告**: {'是' if ai_extracted_info['is_official_announcement'] else '否'}
- **合同金额**: {ai_extracted_info['contract_amount']}亿元
- **风险检测**: {'是' if ai_extracted_info['risk_warning'] else '否'}
- **核心概念**: {', '.join(ai_extracted_info['core_concepts'])}
- **风险关键词**: {', '.join(ai_extracted_info['risk_keywords'])}

---

## 📊 V14 vs V15 对比

| 版本 | AI 角色 | DDE 权重 | Trend 权重 | AI 权重 | 最终得分 | 信号 |
|------|---------|----------|------------|---------|----------|------|
| V14 (旧) | 决策者 (50%) | 30% | 20% | 50% | {result_v14['final_score']:.1f} | {result_v14['signal']} |
| V15 (新) | 信息提取器 (辅助) | 60% | 40% | Bonus | {result_v15['final_score']:.1f} | {result_v15['signal']} |

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*V15 AI Demotion v1.0*
"""
            
            st.download_button(
                label="📝 下载 Markdown 报告",
                data=md_report,
                file_name=f"v15_analysis_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("👈 点击左侧按钮开始分析")


if __name__ == '__main__':
    # 测试运行
    render_ai_demotion()