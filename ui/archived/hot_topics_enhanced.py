"""
热点题材提取系统UI
功能：新闻爬取、NLP分析、题材分类、股票映射、生命周期追踪
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from logic.hot_topic_extractor import get_hot_topic_extractor
from logic.data_manager import DataManager


def render_hot_topics_enhanced_tab(db, config):
    """渲染热点题材提取标签页"""
    
    st.header("🎯 热点题材提取")
    st.caption("新闻爬取 + NLP智能分析 + 自动股票映射 + 生命周期追踪")
    
    # 初始化提取器
    extractor = get_hot_topic_extractor()
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 提取配置")
        
        date = st.date_input("分析日期", value=datetime.now().date(), key="topic_date")
        date_str = date.strftime("%Y%m%d")
        
        st.markdown("---")
        st.markdown("### 📰 新闻源")
        
        use_sina = st.checkbox("新浪财经", value=True, key="use_sina")
        use_netease = st.checkbox("网易财经", value=True, key="use_netease")
        use_tencent = st.checkbox("腾讯财经", value=True, key="use_tencent")
        
        news_sources = []
        if use_sina:
            news_sources.append('sina')
        if use_netease:
            news_sources.append('netease')
        if use_tencent:
            news_sources.append('tencent')
        
        st.markdown("---")
        st.markdown("### 🔍 筛选条件")
        
        min_heat = st.slider("最小热度", 0, 100, 20, 5, key="min_heat")
        
        category_filter = st.multiselect(
            "题材类别",
            ["政策面", "技术面", "消息面", "市场面", "外部面"],
            default=["政策面", "技术面", "消息面"],
            key="category_filter"
        )
    
    # 主要内容
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🔥 今日热点题材")
        
        if st.button("🔄 提取热点题材", key="extract_topics", type="primary"):
            with st.spinner("正在爬取新闻并分析题材..."):
                try:
                    # 提取热点题材
                    topics = extractor.extract_topics(date_str, news_sources)
                    
                    if topics:
                        st.info("💡 提示：当前使用演示数据，实际数据需要等待股市开盘")
                        
                        # 转换为DataFrame
                        df_topics = pd.DataFrame([
                            {
                                '题材名称': topic.name,
                                '热度': topic.heat,
                                '频次': topic.frequency,
                                '类别': topic.category.value,
                                '生命周期': topic.stage.value,
                                '综合评分': topic.total_score,
                                '相关股票': len(topic.related_stocks),
                                '龙虎榜股票': len(topic.lhb_stocks),
                                '领跑股票': topic.leading_stock or '-',
                                '关键词': ", ".join(topic.keywords[:5])
                            }
                            for topic in topics
                        ])
                        
                        # 筛选
                        df_topics = df_topics[df_topics['热度'] >= min_heat]
                        
                        if category_filter:
                            df_topics = df_topics[df_topics['类别'].isin(category_filter)]
                        
                        # 按热度排序
                        df_topics = df_topics.sort_values('热度', ascending=False)
                        
                        # 显示排行榜
                        st.dataframe(
                            df_topics.head(20),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                '热度': st.column_config.ProgressColumn(
                                    '热度',
                                    help='0-100，热度越高题材越热门',
                                    format='%.1f',
                                    min_value=0,
                                    max_value=100
                                ),
                                '综合评分': st.column_config.NumberColumn(
                                    '综合评分',
                                    help='热度 × 消息权重',
                                    format='%.1f'
                                )
                            }
                        )
                        
                        # 题材热度分布图
                        st.markdown("---")
                        st.subheader("📊 题材热度分布")
                        
                        fig = go.Figure()
                        
                        # 添加柱状图
                        fig.add_trace(go.Bar(
                            x=df_topics['题材名称'].head(15),
                            y=df_topics['热度'].head(15),
                            marker_color=df_topics['热度'].head(15).apply(
                                lambda x: '#FF5252' if x >= 70 else '#FFC107' if x >= 50 else '#4CAF50'
                            ),
                            text=df_topics['热度'].head(15).apply(lambda x: f'{x:.1f}'),
                            textposition='auto',
                        ))
                        
                        fig.update_layout(
                            title='题材热度TOP15',
                            xaxis_title='题材',
                            yaxis_title='热度',
                            yaxis_range=[0, 100],
                            height=500,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 题材分类统计
                        st.markdown("---")
                        col_cat1, col_cat2, col_cat3 = st.columns(3)
                        
                        category_stats = df_topics.groupby('类别').agg({
                            '题材名称': 'count',
                            '热度': 'mean'
                        }).round(1)
                        
                        with col_cat1:
                            st.metric("📰 消息面", 
                                    f"{category_stats.loc['消息面', '题材名称'] if '消息面' in category_stats.index else 0} 个",
                                    f"平均热度 {category_stats.loc['消息面', '热度'] if '消息面' in category_stats.index else 0:.1f}")
                        
                        with col_cat2:
                            st.metric("🏛️ 政策面",
                                    f"{category_stats.loc['政策面', '题材名称'] if '政策面' in category_stats.index else 0} 个",
                                    f"平均热度 {category_stats.loc['政策面', '热度'] if '政策面' in category_stats.index else 0:.1f}")
                        
                        with col_cat3:
                            st.metric("🔬 技术面",
                                    f"{category_stats.loc['技术面', '题材名称'] if '技术面' in category_stats.index else 0} 个",
                                    f"平均热度 {category_stats.loc['技术面', '热度'] if '技术面' in category_stats.index else 0:.1f}")
                        
                        # 题材详情
                        st.markdown("---")
                        st.subheader("📋 题材详情分析")
                        
                        for idx, row in df_topics.head(10).iterrows():
                            with st.expander(f"🔥 {row['题材名称']} - 热度 {row['热度']:.1f}"):
                                col_d1, col_d2, col_d3 = st.columns(3)
                                
                                col_d1.metric("类别", row['类别'])
                                col_d2.metric("生命周期", row['生命周期'])
                                col_d3.metric("综合评分", f"{row['综合评分']:.1f}")
                                
                                col_d4, col_d5, col_d6 = st.columns(3)
                                col_d4.metric("出现频次", row['频次'])
                                col_d5.metric("相关股票", row['相关股票'])
                                col_d6.metric("龙虎榜股票", row['龙虎榜股票'])
                                
                                if row['领跑股票'] != '-':
                                    st.info(f"🏆 领跑股票: {row['领跑股票']}")
                                
                                st.markdown(f"**🔑 关键词**: {row['关键词']}")
                        
                        # 生命周期分布
                        st.markdown("---")
                        st.subheader("📈 题材生命周期分布")
                        
                        lifecycle_counts = df_topics['生命周期'].value_counts()
                        
                        fig_lifecycle = go.Figure()
                        
                        fig_lifecycle.add_trace(go.Pie(
                            labels=lifecycle_counts.index,
                            values=lifecycle_counts.values,
                            hole=0.4,
                            marker=dict(colors=['#4CAF50', '#FFC107', '#FF5252', '#9E9E9E'])
                        ))
                        
                        fig_lifecycle.update_layout(
                            title='题材生命周期分布',
                            height=400
                        )
                        
                        st.plotly_chart(fig_lifecycle, use_container_width=True)
                        
                    else:
                        st.info("ℹ️ 今日暂无热点题材")
                
                except Exception as e:
                    st.error(f"❌ 提取失败: {str(e)}")
    
    with col2:
        st.subheader("💡 操作建议")
        
        st.markdown("""
        ### 🎯 生命周期策略
        
        **🌱 孕育期 (热度 < 20)**
        - 提前布局
        - 低吸潜伏
        - 等待爆发
        
        **📈 成长期 (20-50)**
        - 重点关注
        - 适度追涨
        - 快进快出
        
        **🔥 爆发期 (50-80)**
        - 谨慎参与
        - 控制仓位
        - 及时止盈
        
        **📉 衰退期 (> 80)**
        - 避免追高
        - 减仓规避
        - 等待下一轮
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 📰 新闻源说明
        
        **新浪财经**
        - 覆盖面广
        - 更新及时
        - 权威性高
        
        **网易财经**
        - 深度分析
        - 研报丰富
        - 数据详细
        
        **腾讯财经**
        - 实时性强
        - 互动活跃
        - 用户参与度高
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 🔬 NLP分析流程
        
        1. **新闻爬取**
           - 多源采集
           - 实时更新
           - 去重过滤
        
        2. **分词处理**
           - 中文分词
           - 停用词过滤
           - 关键词提取
        
        3. **TextRank排序**
           - 重要性评分
           - 关联度计算
           - 热度排序
        
        4. **题材分类**
           - 自动分类
           - 类别标注
           - 权重计算
        
        5. **股票映射**
           - 龙虎榜关联
           - K线匹配
           - 资金追踪
        """)