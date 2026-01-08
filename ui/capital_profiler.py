"""游资画像识别UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from logic.capital_profiler import CapitalProfiler
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter


def render_capital_profiler_tab(db, config):
    """渲染游资画像识别标签页"""
    
    st.subheader("👤 游资画像识别")
    st.caption("5维度综合评估：连续关注、资金实力、成功率、行业浓度、选时能力")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 画像配置")
        
        min_operations = st.slider("最小操作次数", 3, 20, 5, help="游资最少操作次数才进行画像分析")
        
        lookback_days = st.slider("回溯天数", 30, 365, 180, help="分析历史数据的天数")
        
        st.markdown("---")
        st.subheader("📊 评分权重")
        
        weight_focus = st.slider("连续关注权重", 0.0, 1.0, 0.20, 0.05)
        weight_strength = st.slider("资金实力权重", 0.0, 1.0, 0.25, 0.05)
        weight_success = st.slider("成功率权重", 0.0, 1.0, 0.30, 0.05)
        weight_sector = st.slider("行业浓度权重", 0.0, 1.0, 0.10, 0.05)
        weight_timing = st.slider("选时能力权重", 0.0, 1.0, 0.15, 0.05)
        
        # 归一化权重
        total_weight = weight_focus + weight_strength + weight_success + weight_sector + weight_timing
        if total_weight > 0:
            weight_focus /= total_weight
            weight_strength /= total_weight
            weight_success /= total_weight
            weight_sector /= total_weight
            weight_timing /= total_weight
        
        st.markdown("---")
        st.subheader("💡 画像说明")
        st.info(f"""
        **5维度评分系统**：
        
        1. 连续关注 ({weight_focus:.0%})：操作频度
        
        2. 资金实力 ({weight_strength:.0%})：平均成交额
        
        3. 成功率 ({weight_success:.0%})：盈利能力
        
        4. 行业浓度 ({weight_sector:.0%})：专注程度
        
        5. 选时能力 ({weight_timing:.0%})：时机把握
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 画像分析")
        
        # 获取龙虎榜数据
        if st.button("🔍 生成游资画像", key="generate_profile"):
            with st.spinner('正在分析游资画像...'):
                try:
                    # 获取龙虎榜数据
                    capital_result = CapitalAnalyzer.analyze_longhubu_capital()
                    
                    if capital_result['数据状态'] != '正常':
                        st.error(f"❌ 获取龙虎榜数据失败: {capital_result.get('说明', '未知错误')}")
                        return
                    
                    # 转换为DataFrame
                    if capital_result.get('游资操作记录'):
                        df_lhb = pd.DataFrame(capital_result['游资操作记录'])
                    else:
                        st.warning("⚠️ 暂无游资操作记录")
                        return
                    
                    # 添加必要的列
                    if '日期' not in df_lhb.columns:
                        df_lhb['日期'] = df_lhb['上榜日']
                    
                    if '行业' not in df_lhb.columns:
                        df_lhb['行业'] = '未知'
                    
                    # 创建画像分析器
                    profiler = CapitalProfiler(
                        min_operations=min_operations,
                        lookback_days=lookback_days
                    )
                    
                    # 统计每个游资的操作次数
                    capital_counts = df_lhb['游资名称'].value_counts()
                    active_capitals = capital_counts[capital_counts >= min_operations].index.tolist()
                    
                    if not active_capitals:
                        st.warning(f"⚠️ 没有游资操作次数达到 {min_operations} 次")
                        return
                    
                    st.success(f"✅ 发现 {len(active_capitals)} 个活跃游资")
                    
                    # 为每个游资生成画像
                    profiles = []
                    failed_capitals = []
                    
                    for capital_name in active_capitals:
                        try:
                            profile = profiler.calculate_profile(capital_name, df_lhb)
                            profiles.append(profile)
                        except Exception as e:
                            failed_capitals.append((capital_name, str(e)))
                    
                    if failed_capitals:
                        st.warning(f"⚠️ {len(failed_capitals)} 个游资画像生成失败")
                    
                    if not profiles:
                        st.error("❌ 没有成功生成任何游资画像")
                        return
                    
                    # 显示画像汇总
                    st.divider()
                    st.subheader("📋 游资画像汇总")
                    
                    # 创建画像汇总表格
                    profile_summary = []
                    for profile in profiles:
                        profile_summary.append({
                            '游资名称': profile.capital_name,
                            '综合评分': f"{profile.overall_score:.1f}",
                            '等级': profile.capital_grade,
                            '类型': profile.capital_type,
                            '连续关注': f"{profile.focus_continuity_score:.1f}",
                            '资金实力': f"{profile.capital_strength_score:.1f}",
                            '成功率': f"{profile.success_rate:.1f}%",
                            '行业浓度': f"{profile.sector_concentration:.2f}",
                            '选时能力': f"{profile.timing_ability_score:.1f}",
                            '操作次数': profile.operation_stats['总操作数']
                        })
                    
                    summary_df = pd.DataFrame(profile_summary).sort_values('综合评分', ascending=False)
                    
                    st.dataframe(
                        summary_df,
                        column_config={
                            '综合评分': st.column_config.NumberColumn('综合评分', format="%.1f"),
                            '连续关注': st.column_config.NumberColumn('连续关注', format="%.1f"),
                            '资金实力': st.column_config.NumberColumn('资金实力', format="%.1f"),
                            '成功率': st.column_config.NumberColumn('成功率', format="%.1f%%"),
                            '行业浓度': st.column_config.NumberColumn('行业浓度', format="%.2f"),
                            '选时能力': st.column_config.NumberColumn('选时能力', format="%.1f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 评分分布图
                    st.divider()
                    st.subheader("📈 评分分布")
                    
                    fig = px.histogram(
                        summary_df,
                        x='综合评分',
                        nbins=10,
                        title="游资综合评分分布",
                        color='等级',
                        color_discrete_map={
                            'A': '#4CAF50',
                            'B': '#2196F3',
                            'C': '#FF9800',
                            'D': '#F44336'
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 5维度雷达图对比
                    st.divider()
                    st.subheader("🕸️ 5维度能力对比")
                    
                    # 选择Top 5游资进行对比
                    top_profiles = sorted(profiles, key=lambda x: x.overall_score, reverse=True)[:5]
                    
                    fig = go.Figure()
                    
                    for profile in top_profiles:
                        fig.add_trace(go.Scatterpolar(
                            r=[
                                profile.focus_continuity_score,
                                profile.capital_strength_score,
                                profile.success_rate,
                                profile.sector_concentration * 100,
                                profile.timing_ability_score
                            ],
                            theta=['连续关注', '资金实力', '成功率', '行业浓度', '选时能力'],
                            fill='toself',
                            name=profile.capital_name
                        ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100]
                            )
                        ),
                        showlegend=True,
                        title="Top 5 游资5维度能力对比"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 详细画像展示
                    st.divider()
                    st.subheader("👤 详细画像")
                    
                    # 选择游资查看详细画像
                    selected_capital = st.selectbox(
                        "选择游资查看详细画像",
                        [p.capital_name for p in profiles],
                        key="select_profile_capital"
                    )
                    
                    if selected_capital:
                        selected_profile = next(p for p in profiles if p.capital_name == selected_capital)
                        
                        # 显示综合评分
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("综合评分", f"{selected_profile.overall_score:.1f}")
                        with col_b:
                            st.metric("等级", selected_profile.capital_grade)
                        with col_c:
                            st.metric("类型", selected_profile.capital_type)
                        
                        # 5维度评分
                        st.divider()
                        st.write("### 📊 5维度评分")
                        
                        col_x, col_y = st.columns(2)
                        with col_x:
                            st.metric("连续关注指数", f"{selected_profile.focus_continuity_score:.1f}/100")
                            st.metric("资金实力评分", f"{selected_profile.capital_strength_score:.1f}/100")
                            st.metric("操作成功率", f"{selected_profile.success_rate:.1f}%")
                        with col_y:
                            st.metric("行业浓度", f"{selected_profile.sector_concentration:.2f}")
                            st.metric("选时能力", f"{selected_profile.timing_ability_score:.1f}/100")
                        
                        # 偏好板块
                        if selected_profile.top_sectors:
                            st.divider()
                            st.write("### 🏢 偏好板块")
                            
                            sector_df = pd.DataFrame(selected_profile.top_sectors)
                            fig = px.bar(
                                sector_df,
                                x='频率',
                                y='行业',
                                orientation='h',
                                title=f"{selected_capital} 的偏好板块",
                                color='频率',
                                color_continuous_scale='Viridis'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # 常操作股票
                        if selected_profile.top_stocks:
                            st.divider()
                            st.write("### 📈 常操作股票")
                            
                            stock_df = pd.DataFrame(selected_profile.top_stocks)
                            st.dataframe(
                                stock_df,
                                column_config={
                                    '频率': st.column_config.NumberColumn('频率', format="%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                        
                        # 最近表现
                        st.divider()
                        st.write("### 📊 最近30天表现")
                        
                        col_p, col_q, col_r = st.columns(3)
                        with col_p:
                            st.metric("盈利天数", selected_profile.recent_performance['盈利天数'])
                        with col_q:
                            st.metric("亏损天数", selected_profile.recent_performance['亏损天数'])
                        with col_r:
                            st.metric("平手天数", selected_profile.recent_performance['平手天数'])
                        
                        # 操作统计
                        st.divider()
                        st.write("### 📝 操作统计")
                        
                        col_s, col_t, col_u = st.columns(3)
                        with col_s:
                            st.metric("总操作数", selected_profile.operation_stats['总操作数'])
                        with col_t:
                            st.metric("买入次数", selected_profile.operation_stats['买入次数'])
                        with col_u:
                            st.metric("卖出次数", selected_profile.operation_stats['卖出次数'])
                        
                        # 风险提示
                        if selected_profile.risk_warnings:
                            st.divider()
                            st.write("### ⚠️ 风险提示")
                            
                            for warning in selected_profile.risk_warnings:
                                st.warning(warning)
                
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    with col2:
        st.subheader("💡 画像解读")
        
        st.info("""
        **等级说明**：
        
        - **A级** (80+)：优秀游资
        
        - **B级** (60-79)：良好游资
        
        - **C级** (40-59)：一般游资
        
        - **D级** (<40)：风险较高
        """)
        
        st.markdown("---")
        st.subheader("📊 类型说明")
        
        st.markdown("""
        **游资类型**：
        
        1. **对抗手**：集中行业，高成功率
        
        2. **趋势客**：高频操作，高成功率
        
        3. **机构化**：分散行业，稳健操作
        
        4. **短线客**：通用类型，风格多样
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 注意事项")
        
        st.warning("""
        1. 画像基于历史数据
        
        2. 操作风格可能变化
        
        3. 需要结合市场环境
        
        4. 仅供参考，不构成投资建议
        """)