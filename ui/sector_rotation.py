"""
板块轮动模块

提供板块轮动分析功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.algo import QuantAlgo
from logic.formatter import Formatter
from logic.logger import get_logger

logger = get_logger(__name__)


def render_sector_rotation_tab(db, config):
    """
    渲染板块轮动标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("🔄 板块轮动分析")
    st.caption("实时监控各行业板块资金流向，发现热点板块")
    
    # 自动加载数据
    with st.spinner('正在获取板块轮动数据...'):
        sector_data = QuantAlgo.get_sector_rotation()
        
        if sector_data['数据状态'] == '正常':
            sectors = sector_data['板块列表']
            
            # 格式化数据用于显示
            display_sectors = []
            for sector in sectors:
                display_sectors.append({
                    '板块名称': sector['板块名称'],
                    '涨跌幅': sector['涨跌幅'],
                    '主力净流入': Formatter.format_amount(sector['主力净流入']),
                    '主力净流入占比': sector['主力净流入占比']
                })
            
            # 显示板块资金流向表格
            st.dataframe(
                pd.DataFrame(display_sectors),
                column_config={
                    '板块名称': st.column_config.TextColumn('板块名称', width='medium'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '主力净流入': st.column_config.TextColumn('主力净流入', width='medium'),
                    '主力净流入占比': st.column_config.NumberColumn('净流入占比', format='%.2f%%')
                },
                width="stretch",
                hide_index=True
            )
            
            # 热点板块分析
            st.subheader("🔥 热点板块分析")
            hot_sectors = sorted(sectors, key=lambda x: x['主力净流入'], reverse=True)[:5]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("**资金流入最多的板块**")
                for i, sector in enumerate(hot_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            Formatter.format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            with col2:
                cold_sectors = sorted(sectors, key=lambda x: x['主力净流入'])[:5]
                st.warning("**资金流出最多的板块**")
                for i, sector in enumerate(cold_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            Formatter.format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            # 板块资金流向图
            st.subheader("📊 板块资金流向分布")
            fig_sector = go.Figure()
            
            fig_sector.add_trace(go.Bar(
                x=[s['板块名称'][:4] for s in sectors[:10]],  # 只显示前10个，名称截取
                y=[s['主力净流入'] for s in sectors[:10]],
                marker=dict(
                    color=['rgba(75, 192, 192, 0.8)' if s['主力净流入'] > 0 else 'rgba(255, 99, 132, 0.8)' for s in sectors[:10]]
                )
            ))
            
            fig_sector.update_layout(
                title="前10大板块资金流向",
                xaxis_title="板块",
                yaxis_title="主力净流入（元）",
                height=400
            )
            st.plotly_chart(fig_sector, width="stretch")
        else:
            st.error(f"❌ {sector_data['数据状态']}")
            if '错误信息' in sector_data:
                st.caption(sector_data['错误信息'])