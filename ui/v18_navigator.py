"""
V18 The Navigator - 全维板块共振系统 UI 组件（完整旗舰版）

功能：
1. 多维板块雷达（行业板块 + 概念板块）
2. 资金热度可视化
3. 龙头溯源展示
4. 个股全维共振诊断
5. 市场主线实时监控
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from logic.logger import get_logger
from logic.sector_analysis_streamlit import FastSectorAnalyzerStreamlit, get_fast_sector_analyzer_streamlit
from logic.data_manager import DataManager

logger = get_logger(__name__)


def render_navigator_panel():
    """渲染 V18 领航员面板"""
    st.markdown("### 🧭 V18 The Navigator - 全维板块共振系统")
    
    # 初始化数据管理器
    try:
        db = DataManager()
        analyzer = get_fast_sector_analyzer_streamlit(db)
        
        # 🚀 V18.1 Turbo Boost 性能监控面板
        with st.expander("🚀 V18.1 Turbo Boost 性能监控", expanded=False):
            # 获取数据状态
            data_status = analyzer.get_data_status()
            
            # 🚨 数据过期状态灯
            st.markdown("### 🚨 数据状态监控")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 数据就绪状态
                if data_status['data_ready']:
                    data_ready_status = "🟢 数据就绪"
                else:
                    data_ready_status = "🔴 数据未就绪"
                st.metric("数据状态", data_ready_status)
            
            with col2:
                # 缓存时间
                cache_age = data_status['cache_age']
                if cache_age > 60:
                    cache_status = f"⚠️ {cache_age:.0f}s (已过期)"
                else:
                    cache_status = f"✅ {cache_age:.0f}s (新鲜)"
                st.metric("缓存时间", cache_status)
            
            with col3:
                # 后台线程状态
                thread_status = "🟢 运行中" if data_status['thread_running'] else "🔴 已停止"
                st.metric("后台刷新", thread_status)
            
            with col4:
                # 静态映射表状态
                static_map_status = "🟢 已加载" if data_status['static_map_loaded'] else "🟡 未加载"
                st.metric("静态映射表", static_map_status)
            
            # 详细信息
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 降级模式状态
                if data_status['fallback_mode']:
                    st.warning("⚠️ 降级模式已启用（概念板块接口超时）")
                else:
                    st.success("✅ 正常模式运行")
            
            with col2:
                # 映射表统计
                map_size = len(analyzer._stock_sector_map)
                if data_status['static_map_loaded']:
                    stocks_with_industry = sum(1 for s in analyzer._stock_sector_map.values() if s.get('industry') != '未知')
                    stocks_with_concepts = sum(1 for s in analyzer._stock_sector_map.values() if s.get('concepts'))
                    st.info(f"📊 映射表: {map_size} 只股票 ({stocks_with_industry} 只有行业, {stocks_with_concepts} 只有概念)")
                else:
                    st.warning(f"📊 映射表: {map_size} 只股票 (动态构建)")
                    st.info("💡 提示: 运行 `python tools/generate_static_map.py` 生成静态映射表")
            
            # 性能开关
            st.markdown("---")
            st.subheader("⚙️ 性能设置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'enable_v18' not in st.session_state:
                    st.session_state.enable_v18 = True
                
                enable_v18 = st.checkbox(
                    "启用 V18 板块共振",
                    value=st.session_state.enable_v18,
                    key="enable_v18_toggle"
                )
                st.session_state.enable_v18 = enable_v18
            
            with col2:
                if st.button("🔄 手动刷新缓存"):
                    analyzer._auto_refresh_data()
                    st.success("✅ 缓存刷新完成！")
                    st.rerun()
        
        # 刷新数据按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("📡 扫描全市场热点", key="scan_sectors_full"):
                analyzer._akshare_industry_cache = None
                analyzer._akshare_concept_cache = None
                analyzer._akshare_cache_timestamp = None
                st.success("✅ 市场热度扫描完成！")
                st.rerun()
        
        with col2:
            st.info(f"📊 板块数量: 86")
        
        with col3:
            st.info(f"⏱️ 缓存TTL: 60秒")
        
        # 获取市场主线
        industries, concepts = analyzer.get_market_main_lines(top_n=10)
        
        # 创建两列布局
        col_ind, col_con = st.columns(2)
        
        with col_ind:
            st.subheader("🔥 领涨行业 Top 10")
            if industries:
                # 创建 DataFrame
                ind_df = pd.DataFrame(industries)
                ind_df['成交额(亿)'] = (ind_df['amount'] / 100000000).round(2)
                ind_df_display = ind_df[['name', 'pct_chg', '成交额(亿)', 'capital_heat', 'leader']].copy()
                ind_df_display.columns = ['板块名称', '涨跌幅(%)', '成交额(亿)', '资金热度', '领涨龙头']
                
                # 颜色映射
                def color_pct_chg(val):
                    if val > 0:
                        return f'color: #FF5252; font-weight: bold;'
                    elif val < 0:
                        return f'color: #00C853; font-weight: bold;'
                    else:
                        return 'color: #757575;'
                
                styled_df = ind_df_display.style.applymap(color_pct_chg, subset=['涨跌幅(%)'])
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # 可视化 Top 5
                if len(industries) >= 5:
                    top_5 = pd.DataFrame(industries[:5])
                    fig = px.bar(
                        top_5,
                        x='name',
                        y='pct_chg',
                        color='capital_heat',
                        color_continuous_scale='RdYlGn',
                        title='Top 5 领涨行业（资金热度加权）',
                        text='pct_chg'
                    )
                    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig.update_layout(xaxis_tickangle=-45, height=350)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无行业数据，请点击扫描")
        
        with col_con:
            st.subheader("🌊 领涨概念 Top 10")
            if concepts:
                # 创建 DataFrame
                con_df = pd.DataFrame(concepts)
                con_df['成交额(亿)'] = (con_df['amount'] / 100000000).round(2)
                con_df_display = con_df[['name', 'pct_chg', '成交额(亿)', 'capital_heat', 'leader']].copy()
                con_df_display.columns = ['概念名称', '涨跌幅(%)', '成交额(亿)', '资金热度', '领涨龙头']
                
                # 颜色映射
                styled_df = con_df_display.style.applymap(color_pct_chg, subset=['涨跌幅(%)'])
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # 可视化 Top 5
                if len(concepts) >= 5:
                    top_5 = pd.DataFrame(concepts[:5])
                    fig = px.bar(
                        top_5,
                        x='name',
                        y='pct_chg',
                        color='capital_heat',
                        color_continuous_scale='Oranges',
                        title='Top 5 领涨概念（资金热度加权）',
                        text='pct_chg'
                    )
                    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig.update_layout(xaxis_tickangle=-45, height=350)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无概念数据，请点击扫描")
        
        # 个股共振诊断
        st.divider()
        st.subheader("🎯 个股全维共振诊断")
        
        col_code, col_btn = st.columns([3, 1])
        
        with col_code:
            stock_code = st.text_input("输入股票代码", placeholder="例如: 000001", max_chars=6, key="stock_code_full")
        
        with col_btn:
            st.write("")
            st.write("")
            diagnose = st.button("🔍 诊断", key="diagnose_full")
        
        if diagnose and stock_code:
            with st.spinner("正在诊断个股板块共振..."):
                try:
                    # 获取股票名称
                    realtime_data = db.get_realtime_data(stock_code)
                    stock_name = realtime_data.get('name', '') if realtime_data else ''
                    
                    # 全维共振分析
                    full_resonance = analyzer.check_stock_full_resonance(stock_code, stock_name)
                    
                    resonance_score = full_resonance.get('resonance_score', 0.0)
                    resonance_details = full_resonance.get('resonance_details', [])
                    is_leader = full_resonance.get('is_leader', False)
                    is_follower = full_resonance.get('is_follower', False)
                    industry_info = full_resonance.get('industry_info', {})
                    concept_info = full_resonance.get('concept_info', {})
                    
                    # 显示结果
                    col_score, col_status = st.columns(2)
                    
                    with col_score:
                        if resonance_score > 0:
                            st.success(f"🚀 共振评分: +{resonance_score:.1f}")
                        elif resonance_score < 0:
                            st.error(f"❄️ 逆风评分: {resonance_score:.1f}")
                        else:
                            st.warning(f"📊 共振评分: {resonance_score:.1f}")
                    
                    with col_status:
                        if is_leader:
                            st.success("👑 龙头地位: 是")
                        elif is_follower:
                            st.info("📈 跟风股: 是")
                        else:
                            st.info("📊 独立行情")
                    
                    # 显示共振详情
                    if resonance_details:
                        st.markdown("### 📋 共振详情")
                        for detail in resonance_details:
                            if '龙头' in detail:
                                st.success(detail)
                            elif '主线' in detail or '强势' in detail:
                                st.info(detail)
                            elif '逆风' in detail or '下跌' in detail:
                                st.error(detail)
                            else:
                                st.write(detail)
                    
                    # 显示行业信息
                    if industry_info:
                        st.markdown("### 🏭 行业板块信息")
                        col_ind_name, col_ind_rank, col_ind_chg = st.columns(3)
                        with col_ind_name:
                            st.metric("行业", industry_info.get('name', '未知'))
                        with col_ind_rank:
                            st.metric("排名", f"{industry_info.get('rank', 0)}/{industry_info.get('total', 0)}")
                        with col_ind_chg:
                            st.metric("涨幅", f"{industry_info.get('pct_chg', 0):.2f}%")
                        
                        if industry_info.get('leader'):
                            st.info(f"👑 领涨龙头: {industry_info['leader']}")
                        
                        # 🚀 V18.2 Money Flow: 显示资金流信息
                        if 'fund_flow' in industry_info:
                            fund_flow = industry_info['fund_flow']
                            net_inflow_yi = fund_flow.get('net_inflow_yi', 0)
                            fund_status = fund_flow.get('status', 'unknown')
                            fund_reason = fund_flow.get('reason', '')
                            
                            st.markdown("### 💰 资金流向")
                            
                            if fund_status == 'strong_inflow':
                                st.success(f"💰 净流入: {net_inflow_yi:.2f}亿")
                                st.info(fund_reason)
                            elif fund_status == 'weak_inflow':
                                st.info(f"📈 净流入: {net_inflow_yi:.2f}亿")
                                st.write(fund_reason)
                            elif fund_status == 'outflow':
                                st.error(f"⚠️ 净流出: {abs(net_inflow_yi):.2f}亿")
                                st.warning(fund_reason)
                            else:
                                st.write(f"📊 资金流: {fund_reason}")
                    
                    # 显示概念信息
                    if concept_info and concept_info.get('details'):
                        st.markdown("### 💡 概念板块信息")
                        for detail in concept_info['details']:
                            st.write(detail)
                    
                    # 板块位置可视化
                    if industry_info and industry_info.get('rank', 0) > 0:
                        rank = industry_info['rank']
                        total = industry_info['total']
                        
                        fig_gauge = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=rank,
                            title={'text': f"行业板块排名 (共{total}个板块)"},
                            gauge={
                                'axis': {'range': [1, total]},
                                'bar': {'color': "darkblue"},
                                'steps': [
                                    {'range': [1, 5], 'color': '#FF5252'},  # Top 5 领涨
                                    {'range': [6, 10], 'color': '#FFC107'},  # Top 10 强势
                                    {'range': [total - 2, total], 'color': '#00C853'},  # Bottom 3 拖累
                                    {'range': [10, total - 2], 'color': '#757575'},  # 中性
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': rank
                                }
                            }
                        ))
                        st.plotly_chart(fig_gauge, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ 诊断失败: {str(e)}")
        
        # 底部说明
        st.divider()
        st.markdown("""
        ### 📖 V18 全维板块共振系统说明
        
        **核心架构**:
        - 🏭 **行业板块**: 基于行业分类的板块分析
        - 💡 **概念板块**: 基于市场热点的概念分析
        - 💰 **资金热度**: 综合涨幅、成交额、换手率的强度系数
        - 👑 **龙头溯源**: 自动识别板块内的领涨个股
        
        **评分规则**:
        - 🔥 **行业主线** (Top 5): +15分
        - 🚀 **行业强势** (Top 10): +8分
        - 👑 **龙头溢价**: +10分 + AI × 1.2
        - 📈 **跟风股**: AI × 0.9
        - ❄️ **行业逆风** (< -1%): -10分
        
        **数据源**: AkShare (stock_board_industry_name_em, stock_board_concept_name_em)
        **更新频率**: 60秒缓存
        **核心思想**: 龙头战法，先看板块，再看个股。站在风口上，猪都能飞。
        """)
        
    except Exception as e:
        logger.error(f"渲染 V18 领航员面板失败: {e}")
        st.error(f"❌ 加载失败: {str(e)}")


def render_sector_resonance_indicator(stock_code: str, resonance_info: dict):
    """
    在其他页面中渲染板块共振指示器（全维版）
    
    Args:
        stock_code: 股票代码
        resonance_info: 全维共振信息字典
    """
    if not resonance_info:
        return
    
    resonance_score = resonance_info.get('resonance_score', 0.0)
    resonance_details = resonance_info.get('resonance_details', [])
    is_leader = resonance_info.get('is_leader', False)
    is_follower = resonance_info.get('is_follower', False)
    
    # 显示共振评分
    if resonance_score > 0:
        st.success(f"🚀 **板块共振评分**: +{resonance_score:.1f}")
    elif resonance_score < 0:
        st.error(f"❄️ **板块共振评分**: {resonance_score:.1f}")
    else:
        st.info(f"📊 **板块共振评分**: {resonance_score:.1f}")
    
    # 显示龙头地位
    if is_leader:
        st.success("👑 **龙头地位**: 是")
    elif is_follower:
        st.info("📈 **跟风股**: 是")
    
    # 显示共振详情
    if resonance_details:
        with st.expander("📋 共振详情", expanded=False):
            for detail in resonance_details:
                if '龙头' in detail:
                    st.success(detail)
                elif '主线' in detail or '强势' in detail:
                    st.info(detail)
                elif '逆风' in detail or '下跌' in detail:
                    st.error(detail)
                else:
                    st.write(detail)


if __name__ == '__main__':
    # 测试代码
    st.set_page_config(
        page_title="V18 The Navigator - 全维板块共振系统",
        layout="wide",
        page_icon="🧭"
    )
    render_navigator_panel()