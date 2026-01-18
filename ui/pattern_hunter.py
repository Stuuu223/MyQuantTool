#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V14.3 模式捕获（Pattern Hunter）UI 模块
展示踏空案例的模式聚类分析结果
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from pathlib import Path
from logic.auto_reviewer import AutoReviewer
from logic.data_manager import DataManager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_pattern_hunter(data_manager=None):
    """
    渲染模式捕获面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("🎯 V14.3 模式捕获 (Pattern Hunter)")

    # 初始化组件
    if data_manager is None:
        data_manager = DataManager()

    reviewer = AutoReviewer(data_manager)

    # 侧边栏：分析参数
    with st.sidebar:
        st.markdown("### ⚙️ 分析参数")
        
        days = st.slider(
            "分析天数",
            min_value=1,
            max_value=30,
            value=5,
            help="分析过去N天的踏空案例"
        )
        
        st.markdown("---")
        st.markdown("### 📋 功能说明")
        st.markdown("""
        **模式捕获**会分析踏空案例的：
        - 📊 市值分布（微盘/中小盘/大盘）
        - 🏭 行业分布（Top 3 热门行业）
        - 📈 量价特征（换手率、量比）
        - 🎯 评分分布（系统评分区间）
        
        基于分析结果，系统会自动生成优化建议。
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 开始分析")

        if st.button("🚀 运行模式分析", type="primary"):
            with st.spinner("正在分析踏空案例模式..."):
                try:
                    # 运行模式分析
                    analysis_result = reviewer.analyze_missed_patterns(days=days)
                    
                    # 保存到 session state
                    st.session_state['pattern_analysis'] = analysis_result
                    
                    st.success(f"✅ 分析完成！共发现 {analysis_result['total_cases']} 个踏空案例")
                    
                except Exception as e:
                    logger.error(f"模式分析失败: {e}")
                    st.error(f"模式分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'pattern_analysis' in st.session_state:
            analysis = st.session_state['pattern_analysis']
            
            st.metric(
                "踏空案例总数",
                f"{analysis['total_cases']} 个",
                delta=f"过去 {days} 天"
            )
            
            if analysis['patterns']:
                st.metric(
                    "发现模式数量",
                    f"{len(analysis['patterns'])} 个"
                )
            
            if analysis['recommendations']:
                st.metric(
                    "优化建议数量",
                    f"{len(analysis['recommendations'])} 条"
                )
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'pattern_analysis' in st.session_state:
        analysis = st.session_state['pattern_analysis']
        
        # 1. 模式发现
        st.markdown("### 🎯 模式发现")
        
        if analysis['patterns']:
            for i, pattern in enumerate(analysis['patterns'], 1):
                with st.expander(f"模式 {i}: {pattern['type']} - {pattern['pattern']}", expanded=True):
                    st.write(pattern['description'])
        else:
            st.info("✅ 未发现明显模式，当前策略较为均衡")
        
        st.markdown("---")
        
        # 2. 优化建议
        st.markdown("### 💡 优化建议")
        
        if analysis['recommendations']:
            for i, rec in enumerate(analysis['recommendations'], 1):
                if rec.startswith("⚠️"):
                    st.warning(f"{i}. {rec}")
                elif rec.startswith("✅"):
                    st.success(f"{i}. {rec}")
                else:
                    st.info(f"{i}. {rec}")
        else:
            st.info("暂无优化建议")
        
        st.markdown("---")
        
        # 3. 详细数据可视化
        st.markdown("### 📈 详细数据分析")
        
        # 使用标签页展示不同维度的数据
        tab1, tab2, tab3, tab4 = st.tabs(["市值分布", "行业分布", "量价特征", "评分分布"])
        
        with tab1:
            st.markdown("#### 市值分布分析")
            
            market_cap = analysis['market_cap_distribution']
            
            # 创建饼图
            labels = ['微盘股 (<20亿)', '中小盘股 (20-100亿)', '大盘股 (>100亿)']
            values = [
                market_cap['micro_cap']['percentage'],
                market_cap['small_mid_cap']['percentage'],
                market_cap['large_cap']['percentage']
            ]
            counts = [
                market_cap['micro_cap']['count'],
                market_cap['small_mid_cap']['count'],
                market_cap['large_cap']['count']
            ]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                textinfo='label+percent',
                hovertemplate='%{label}<br>占比: %{percent}<br>数量: %{customdata[0]} 个<extra></extra>',
                customdata=[[c] for c in counts]
            )])
            
            fig.update_layout(
                title="踏空案例市值分布",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示详细数据表格
            st.markdown("##### 详细数据")
            cap_data = {
                '市值区间': labels,
                '案例数量': counts,
                '占比 (%)': values,
                '平均市值 (亿)': [
                    market_cap['micro_cap']['avg_cap'],
                    market_cap['small_mid_cap']['avg_cap'],
                    market_cap['large_cap']['avg_cap']
                ]
            }
            
            st.dataframe(pd.DataFrame(cap_data), use_container_width=True)
        
        with tab2:
            st.markdown("#### 行业分布分析")
            
            industry = analysis['industry_distribution']
            
            if industry['top_3']:
                # 创建柱状图
                industries = [ind['industry'] for ind in industry['top_3']]
                counts = [ind['count'] for ind in industry['top_3']]
                percentages = [ind['percentage'] for ind in industry['top_3']]
                
                fig = go.Figure(data=[go.Bar(
                    x=industries,
                    y=percentages,
                    text=[f"{c} 个 ({p:.1f}%)" for c, p in zip(counts, percentages)],
                    textposition='auto',
                    marker_color=['#1f77b4', '#ff7f0e', '#2ca02c']
                )])
                
                fig.update_layout(
                    title=f"Top {len(industries)} 热门行业分布",
                    xaxis_title="行业",
                    yaxis_title="占比 (%)",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示详细数据表格
                st.markdown("##### 详细数据")
                ind_data = {
                    '行业': industries,
                    '案例数量': counts,
                    '占比 (%)': percentages
                }
                
                st.dataframe(pd.DataFrame(ind_data), use_container_width=True)
                
                st.info(f"共涉及 {industry['total_industries']} 个不同行业")
            else:
                st.warning("暂无行业数据")
        
        with tab3:
            st.markdown("#### 量价特征分析")
            
            volume_price = analysis['volume_price_features']
            
            # 创建两个指标卡片
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric(
                    "平均换手率",
                    f"{volume_price['turnover_rate']['avg']:.2f}%",
                    delta=f"最高: {volume_price['turnover_rate']['max']:.2f}%"
                )
                
                st.caption(f"最低: {volume_price['turnover_rate']['min']:.2f}%")
            
            with col_b:
                st.metric(
                    "平均量比",
                    f"{volume_price['volume_ratio']['avg']:.2f}",
                    delta=f"最高: {volume_price['volume_ratio']['max']:.2f}"
                )
                
                st.caption(f"最低: {volume_price['volume_ratio']['min']:.2f}")
            
            # 创建对比图
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='换手率 (%)',
                x=['平均', '最高', '最低'],
                y=[
                    volume_price['turnover_rate']['avg'],
                    volume_price['turnover_rate']['max'],
                    volume_price['turnover_rate']['min']
                ],
                marker_color='#1f77b4'
            ))
            
            fig.add_trace(go.Bar(
                name='量比',
                x=['平均', '最高', '最低'],
                y=[
                    volume_price['volume_ratio']['avg'],
                    volume_price['volume_ratio']['max'],
                    volume_price['volume_ratio']['min']
                ],
                marker_color='#ff7f0e'
            ))
            
            fig.update_layout(
                title="量价特征对比",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            st.markdown("#### 评分分布分析")
            
            score_dist = analysis['score_distribution']
            
            if 'avg' in score_dist:
                # 创建指标卡片
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric("平均评分", f"{score_dist['avg']:.1f}")
                
                with col_b:
                    st.metric("最高评分", f"{score_dist['max']:.1f}")
                
                with col_c:
                    st.metric("最低评分", f"{score_dist['min']:.1f}")
                
                # 创建评分区间分布图
                dist = score_dist['distribution']
                labels = ['极低 (<40)', '低 (40-50)', '中 (50-60)', '高 (>=60)']
                values = [
                    dist['very_low'],
                    dist['low'],
                    dist['medium'],
                    dist['high']
                ]
                
                fig = go.Figure(data=[go.Bar(
                    x=labels,
                    y=values,
                    text=[f"{v} 个" for v in values],
                    textposition='auto',
                    marker_color=['#d62728', '#ff7f0e', '#ffbb78', '#2ca02c']
                )])
                
                fig.update_layout(
                    title="踏空案例评分区间分布",
                    xaxis_title="评分区间",
                    yaxis_title="案例数量",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("暂无评分数据")
        
        st.markdown("---")
        
        # 4. 导出功能
        st.markdown("### 📥 导出分析结果")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # 导出 JSON
            import json
            json_str = json.dumps(analysis, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"pattern_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            report_file = Path("data/review_cases/pattern_analysis_report.md")
            if report_file.exists():
                with open(report_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                st.download_button(
                    label="📝 下载 Markdown 报告",
                    data=md_content,
                    file_name=f"pattern_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            else:
                st.warning("Markdown 报告文件不存在")
    
    else:
        st.info("👈 点击左侧按钮开始模式分析")


if __name__ == '__main__':
    # 测试运行
    render_pattern_hunter()