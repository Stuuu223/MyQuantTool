"""数据质量监控UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from logic.data_monitor import DataQualityMonitor, get_monitor
from logic.formatter import Formatter


def render_data_monitor_tab(db, config):
    """渲染数据质量监控标签页"""
    
    st.subheader("🔍 数据质量监控")
    st.caption("实时监控API可用性、数据完整性、响应时间等指标")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 监控配置")
        
        check_date = st.date_input("检查日期", value=datetime.now(), key="monitor_date")
        
        auto_refresh = st.checkbox("自动刷新", value=False, help="每隔一段时间自动检查")
        
        if auto_refresh:
            refresh_interval = st.slider("刷新间隔(秒)", 30, 300, 60, 5)
        
        st.markdown("---")
        st.subheader("📊 健康标准")
        
        st.info("""
        **健康分数标准**：
        
        - **80-100**：优秀
        
        - **60-79**：良好
        
        - **40-59**：一般
        
        - **<40**：不佳
        """)
        
        st.markdown("---")
        st.subheader("💡 监控说明")
        st.info("""
        **检查项目**：
        
        1. 龙虎榜数据可用性
        
        2. 营业部明细可用性
        
        3. 列名正确性
        
        4. API响应时间
        
        5. 数据完整性
        
        6. 重复记录检测
        
        7. 数据新鲜度
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 质量检查")
        
        # 执行数据质量检查
        if st.button("🔍 开始检查", key="check_data_quality"):
            with st.spinner('正在检查数据质量...'):
                try:
                    # 获取监控器实例
                    monitor = get_monitor()
                    
                    # 执行检查
                    date_str = check_date.strftime("%Y%m%d")
                    report = monitor.check_data_quality(date=date_str)
                    
                    # 显示整体评分
                    st.divider()
                    st.subheader("📋 整体评分")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("健康分数", f"{report['健康分数']}/100")
                    with col_b:
                        st.metric("整体质量", report['整体质量'])
                    with col_c:
                        st.metric("检查时间", report['检查时间'].split('T')[1][:8])
                    
                    # 健康分数可视化
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=report['健康分数'],
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "数据健康分数"},
                        gauge={
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "#4CAF50"},
                            'steps': [
                                {'range': [0, 40], 'color': "#FFEBEE"},
                                {'range': [40, 60], 'color': "#FFF3E0"},
                                {'range': [60, 80], 'color': "#E8F5E9"},
                                {'range': [80, 100], 'color': "#C8E6C9"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': 80
                            }
                        }
                    ))
                    
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 详细检查项目
                    st.divider()
                    st.subheader("🔍 详细检查项目")
                    
                    check_items_df = pd.DataFrame(report['检查项目'])
                    
                    # 添加状态列
                    check_items_df['状态'] = check_items_df['正常'].apply(
                        lambda x: '✅ 正常' if x else '❌ 异常'
                    )
                    
                    # 重新排列列
                    check_items_df = check_items_df[['项目', '分数', '状态', '信息']]
                    
                    st.dataframe(
                        check_items_df,
                        column_config={
                            '分数': st.column_config.NumberColumn('分数', format="%.0f"),
                            '状态': st.column_config.TextColumn('状态')
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 检查项目分布图
                    fig = px.bar(
                        check_items_df,
                        x='项目',
                        y='分数',
                        title='各检查项目得分',
                        color='正常',
                        color_discrete_map={True: '#4CAF50', False: '#F44336'}
                    )
                    
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 警告信息
                    if report['警告']:
                        st.divider()
                        st.subheader("⚠️ 警告信息")
                        
                        for warning in report['警告']:
                            st.warning(warning)
                    
                    # 错误信息
                    if report['错误']:
                        st.divider()
                        st.subheader("❌ 错误信息")
                        
                        for error in report['错误']:
                            st.error(error)
                    
                    # 健康趋势
                    st.divider()
                    st.subheader("📈 健康趋势")
                    
                    trend_data = monitor.get_health_trend()
                    
                    if trend_data['历史记录']:
                        trend_df = pd.DataFrame({
                            '检查次数': range(1, len(trend_data['历史记录']) + 1),
                            '健康分数': trend_data['历史记录']
                        })
                        
                        fig = px.line(
                            trend_df,
                            x='检查次数',
                            y='健康分数',
                            title='健康分数趋势',
                            markers=True
                        )
                        
                        # 添加阈值线
                        fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="优秀")
                        fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="良好")
                        fig.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="一般")
                        
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 趋势统计
                        col_x, col_y, col_z = st.columns(3)
                        with col_x:
                            st.metric("当前分数", trend_data['当前分数'])
                        with col_y:
                            st.metric("平均分数", f"{trend_data['平均分数']:.1f}")
                        with col_z:
                            st.metric("最高分", trend_data['最高分'])
                    else:
                        st.info("👍 暂无历史记录")
                    
                    # 生成健康报告
                    st.divider()
                    st.subheader("📄 健康报告")
                    
                    health_report = monitor.generate_health_report()
                    
                    st.text(health_report)
                
                except Exception as e:
                    st.error(f"❌ 检查失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        
        # 缓存统计
        st.divider()
        st.subheader("💾 缓存统计")
        
        if st.button("📊 查看缓存统计", key="view_cache_stats"):
            try:
                monitor = get_monitor()
                cache_stats = monitor.cache.get_stats()
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("总缓存数", cache_stats.get('total_keys', 0))
                with col_b:
                    st.metric("命中率", cache_stats.get('hit_rate', '0%'))
                with col_c:
                    st.metric("缓存状态", "启用" if cache_stats.get('enabled') else "禁用")
                
                # 缓存性能图表
                if cache_stats.get('enabled'):
                    fig = go.Figure(data=[
                        go.Bar(
                            name='命中',
                            x=['缓存'],
                            y=[cache_stats.get('hits', 0)],
                            marker_color='#4CAF50'
                        ),
                        go.Bar(
                            name='未命中',
                            x=['缓存'],
                            y=[cache_stats.get('misses', 0)],
                            marker_color='#FF9800'
                        )
                    ])
                    
                    fig.update_layout(
                        title='缓存命中情况',
                        barmode='stack',
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"❌ 获取缓存统计失败: {str(e)}")
    
    with col2:
        st.subheader("💡 监控建议")
        
        st.info("""
        **健康分数解读**：
        
        - **80+**：系统健康
        
        - **60-79**：基本健康
        
        - **40-59**：有问题
        
        - **<40**：严重问题
        """)
        
        st.markdown("---")
        st.subheader("📊 检查频率")
        
        st.info("""
        **建议频率**：
        
        - 日常：每天1次
        
        - 交易时段：每小时1次
        
        - 异常时：立即检查
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 异常处理")
        
        st.warning("""
        **发现异常时**：
        
        1. 检查网络连接
        
        2. 验证API状态
        
        3. 查看错误日志
        
        4. 联系技术支持
        
        5. 记录问题详情
        """)
        
        st.markdown("---")
        st.subheader("🔧 维护建议")
        
        st.info("""
        **定期维护**：
        
        1. 清理过期缓存
        
        2. 更新API密钥
        
        3. 优化查询策略
        
        4. 监控性能指标
        
        5. 备份重要数据
        """)