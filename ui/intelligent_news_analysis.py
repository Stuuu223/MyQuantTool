"""智能新闻分析UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.intelligent_news_analyzer import IntelligentNewsAnalyzer, NewsItem, NewsAnalysisResult
from logic.llm_interface import LLMManager, LLMMessage, get_llm_manager
from datetime import datetime


def render_intelligent_news_analysis_tab(db, config):
    """渲染智能新闻分析标签页"""
    
    st.subheader("📰 智能新闻分析")
    st.caption("基于多层过滤机制的智能新闻分析系统")
    st.markdown("---")
    
    # 说明
    st.info("""
    **多层过滤机制**：
    1. **质量评估**：来源可信度、时效性、完整性、信息密度、标题质量
    2. **相关性评估**：股票相关性、行业相关性、主题相关性
    3. **情绪分析**：正面/负面/中性，情绪强度，关键词提取
    4. **影响度评估**：市场影响、行业影响、个股影响、持续时间
    """)
    
    # 输入区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 新闻信息")
        
        news_title = st.text_input(
            "新闻标题",
            value="某公司发布业绩预告，净利润同比增长50%",
            help="输入新闻标题"
        )
        
        news_content = st.text_area(
            "新闻内容",
            value="某公司今日发布业绩预告，预计2024年上半年净利润同比增长50%，主要受益于主营业务增长和新产品推出。公司表示，将继续加大研发投入，提升市场竞争力。受此消息影响，相关概念股有望受益。",
            height=150,
            help="输入新闻内容"
        )
        
        news_source = st.text_input(
            "新闻来源",
            value="证券时报",
            help="输入新闻来源"
        )
    
    with col2:
        st.subheader("⚙️ 分析配置")
        
        target_stocks = st.text_input(
            "目标股票代码",
            value="600519,000858",
            help="输入目标股票代码，用逗号分隔"
        )
        
        # 过滤阈值
        st.write("**过滤阈值**")
        quality_threshold = st.slider(
            "质量阈值",
            0, 100, 60,
            help="质量评分低于此值将被过滤"
        )
        
        relevance_threshold = st.slider(
            "相关性阈值",
            0, 100, 50,
            help="相关性评分低于此值将被过滤"
        )
        
        impact_threshold = st.slider(
            "影响度阈值",
            0, 100, 50,
            help="影响度评分低于此值将被过滤"
        )
        
        # LLM提供商选择
        st.write("**LLM提供商**")
        llm_provider = st.selectbox(
            "选择提供商",
            ["local", "openai", "deepseek"],
            help="选择用于情绪分析的LLM提供商"
        )
        
        if llm_provider != "local":
            api_key = st.text_input(
                "API密钥",
                type="password",
                help=f"输入{llm_provider.upper()}的API密钥"
            )
    
    # 分析按钮
    if st.button("🔍 开始分析", key="analyze_news"):
        with st.spinner('智能分析系统正在工作...'):
            try:
                # 验证输入
                if not news_title or not news_content:
                    st.error("❌ 请输入新闻标题和内容")
                    return
                
                # 创建新闻项
                news = NewsItem(
                    title=news_title,
                    content=news_content,
                    source=news_source,
                    publish_time=datetime.now(),
                    url="",
                    related_stocks=[s.strip() for s in target_stocks.split(',') if s.strip()]
                )
                
                # 获取目标股票列表
                target_list = [s.strip() for s in target_stocks.split(',') if s.strip()]
                
                # 配置LLM管理器
                llm_manager = get_llm_manager()
                
                if llm_provider != "local" and api_key:
                    from logic.llm_interface import OpenAIProvider, DeepSeekProvider
                    
                    if llm_provider == "openai":
                        provider = OpenAIProvider(api_key=api_key)
                    elif llm_provider == "deepseek":
                        provider = DeepSeekProvider(api_key=api_key)
                    
                    llm_manager.add_provider(llm_provider, provider)
                    llm_manager.set_default(llm_provider, llm_manager.providers[llm_provider].list_models()[0])
                
                # 创建分析器
                analyzer = IntelligentNewsAnalyzer(llm_manager=llm_manager)
                
                # 设置过滤阈值
                analyzer.quality_threshold = quality_threshold
                analyzer.relevance_threshold = relevance_threshold
                analyzer.impact_threshold = impact_threshold
                
                # 执行分析
                result = analyzer.analyze(news, target_list)
                
                # 显示结果
                st.success(f"✅ 分析完成！综合评分: {result.overall_score:.1f}/100")
                
                # 显示综合建议
                st.markdown("---")
                st.subheader("🎯 综合建议")
                
                # 根据通过状态显示不同颜色
                if result.passed_filters:
                    st.markdown(f"### ✅ {result.recommendation}")
                else:
                    st.markdown(f"### ❌ {result.recommendation}")
                
                # 显示过滤状态
                if not result.passed_filters:
                    st.warning("**未通过过滤原因**：")
                    for reason in result.filter_reasons:
                        st.write(f"- {reason}")
                
                # 显示综合评分
                col_score1, col_score2, col_score3, col_score4 = st.columns(4)
                with col_score1:
                    st.metric("综合评分", f"{result.overall_score:.1f}/100")
                with col_score2:
                    st.metric("质量评分", f"{result.quality_score:.1f}/100")
                with col_score3:
                    st.metric("相关性评分", f"{result.relevance_score:.1f}/100")
                with col_score4:
                    st.metric("影响度评分", f"{result.impact_score:.1f}/100")
                
                # 显示情绪分析
                col_sent1, col_sent2 = st.columns(2)
                with col_sent1:
                    sentiment_emoji = "😊" if result.sentiment == "positive" else "😟" if result.sentiment == "negative" else "😐"
                    st.metric("情绪倾向", f"{sentiment_emoji} {result.sentiment}")
                with col_sent2:
                    st.metric("情绪强度", f"{abs(result.sentiment_score)*100:.0f}%")
                
                # 显示四层过滤详细结果
                st.markdown("---")
                st.subheader("📊 四层过滤详细结果")
                
                # 创建选项卡
                tab1, tab2, tab3, tab4 = st.tabs(["第一层：质量评估", "第二层：相关性评估", "第三层：情绪分析", "第四层：影响度评估"])
                
                with tab1:
                    st.write("**质量评估详情**")
                    
                    # 质量评分雷达图
                    quality_data = {
                        '维度': ['来源可信度', '时效性', '内容完整性', '信息密度', '标题质量'],
                        '得分': [
                            result.quality_details.get('source', {}).get('score', 0),
                            result.quality_details.get('timeliness', {}).get('score', 0),
                            result.quality_details.get('completeness', {}).get('score', 0),
                            result.quality_details.get('density', {}).get('score', 0),
                            result.quality_details.get('title', {}).get('score', 0)
                        ],
                        '满分': [
                            result.quality_details.get('source', {}).get('max', 30),
                            result.quality_details.get('timeliness', {}).get('max', 25),
                            result.quality_details.get('completeness', {}).get('max', 20),
                            result.quality_details.get('density', {}).get('max', 15),
                            result.quality_details.get('title', {}).get('max', 10)
                        ]
                    }
                    
                    quality_df = pd.DataFrame(quality_data)
                    st.dataframe(quality_df, use_container_width=True, hide_index=True)
                    
                    # 质量评分进度条
                    st.write("**质量评分**")
                    st.progress(result.quality_score / 100)
                    st.write(f"{result.quality_score:.1f}/100")
                    
                    # 详细说明
                    with st.expander("查看详细说明"):
                        if 'source' in result.quality_details:
                            st.write(f"**来源**: {result.quality_details['source']['source']}")
                            st.write(f"得分: {result.quality_details['source']['score']:.1f}/{result.quality_details['source']['max']}")
                        
                        if 'timeliness' in result.quality_details:
                            st.write(f"**发布时间**: {result.quality_details['timeliness']['publish_time']}")
                            st.write(f"得分: {result.quality_details['timeliness']['score']:.1f}/{result.quality_details['timeliness']['max']}")
                        
                        if 'completeness' in result.quality_details:
                            st.write(f"**内容长度**: {result.quality_details['completeness']['content_length']} 字符")
                            st.write(f"得分: {result.quality_details['completeness']['score']:.1f}/{result.quality_details['completeness']['max']}")
                
                with tab2:
                    st.write("**相关性评估详情**")
                    
                    # 相关性评分雷达图
                    relevance_data = {
                        '维度': ['股票相关性', '行业相关性', '主题相关性'],
                        '得分': [
                            result.relevance_details.get('stock_relevance', {}).get('score', 0),
                            result.relevance_details.get('industry_relevance', {}).get('score', 0),
                            result.relevance_details.get('topic_relevance', {}).get('score', 0)
                        ],
                        '满分': [
                            result.relevance_details.get('stock_relevance', {}).get('max', 40),
                            result.relevance_details.get('industry_relevance', {}).get('max', 30),
                            result.relevance_details.get('topic_relevance', {}).get('max', 30)
                        ]
                    }
                    
                    relevance_df = pd.DataFrame(relevance_data)
                    st.dataframe(relevance_df, use_container_width=True, hide_index=True)
                    
                    # 相关性评分进度条
                    st.write("**相关性评分**")
                    st.progress(result.relevance_score / 100)
                    st.write(f"{result.relevance_score:.1f}/100")
                    
                    # 相关股票
                    if news.related_stocks:
                        st.write(f"**相关股票**: {', '.join(news.related_stocks)}")
                    
                    # 目标股票匹配度
                    if target_list:
                        matched = set(news.related_stocks) & set(target_list)
                        st.write(f"**匹配股票**: {', '.join(matched) if matched else '无'}")
                
                with tab3:
                    st.write("**情绪分析详情**")
                    
                    # 情绪可视化
                    col_sent_a, col_sent_b = st.columns(2)
                    with col_sent_a:
                        sentiment_emoji = "😊" if result.sentiment == "positive" else "😟" if result.sentiment == "negative" else "😐"
                        st.metric("情绪倾向", f"{sentiment_emoji} {result.sentiment}")
                    with col_sent_b:
                        st.metric("情绪分数", f"{result.sentiment_score:.2f}")
                    
                    # 情绪强度条
                    st.write("**情绪强度**")
                    intensity = abs(result.sentiment_score)
                    if result.sentiment == "positive":
                        st.success(f"正面情绪强度: {intensity*100:.0f}%")
                        st.progress(intensity)
                    elif result.sentiment == "negative":
                        st.error(f"负面情绪强度: {intensity*100:.0f}%")
                        st.progress(intensity)
                    else:
                        st.info(f"中性情绪: {intensity*100:.0f}%")
                        st.progress(intensity)
                    
                    # 关键词
                    keywords = result.sentiment_details.get('keywords', [])
                    if keywords:
                        st.write("**关键情绪词**:")
                        for kw in keywords:
                            st.write(f"- {kw}")
                
                with tab4:
                    st.write("**影响度评估详情**")
                    
                    # 影响度评分雷达图
                    impact_data = {
                        '维度': ['市场影响', '行业影响', '个股影响', '持续时间'],
                        '得分': [
                            result.impact_details.get('market_impact', {}).get('score', 0),
                            result.impact_details.get('industry_impact', {}).get('score', 0),
                            result.impact_details.get('stock_impact', {}).get('score', 0),
                            result.impact_details.get('duration', {}).get('score', 0)
                        ],
                        '满分': [
                            result.impact_details.get('market_impact', {}).get('max', 30),
                            result.impact_details.get('industry_impact', {}).get('max', 25),
                            result.impact_details.get('stock_impact', {}).get('max', 25),
                            result.impact_details.get('duration', {}).get('max', 20)
                        ]
                    }
                    
                    impact_df = pd.DataFrame(impact_data)
                    st.dataframe(impact_df, use_container_width=True, hide_index=True)
                    
                    # 影响度评分进度条
                    st.write("**影响度评分**")
                    st.progress(result.impact_score / 100)
                    st.write(f"{result.impact_score:.1f}/100")
                    
                    # 相关股票数量
                    st.write(f"**相关股票数量**: {len(news.related_stocks)}")
                
                # 综合评分可视化
                st.markdown("---")
                st.subheader("📈 综合评分可视化")
                
                fig = _create_score_chart(result)
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏 - 系统说明
    with st.sidebar:
        st.markdown("---")
        st.subheader("📖 系统说明")
        
        st.info("""
        **多层过滤机制**：
        
        每层过滤都有独立的评分系统，只有通过所有层的新闻才会被推荐。
        
        **综合评分计算**：
        - 质量评分 × 30%
        - 相关性评分 × 25%
        - 情绪强度 × 20%
        - 影响度评分 × 25%
        """)
        
        st.markdown("---")
        st.subheader("🎯 评分标准")
        
        st.info("""
        **综合评分**：
        - 80-100分：强烈推荐关注
        - 60-80分：推荐关注
        - 0-60分：可以关注
        - 未通过过滤：不建议关注
        """)
        
        st.markdown("---")
        st.subheader("🤖 LLM提供商")
        
        st.info("""
        **支持的提供商**：
        - Local：本地规则（免费）
        - OpenAI：GPT系列（需要API密钥）
        - DeepSeek：DeepSeek系列（需要API密钥）
        
        可以根据需要选择不同的提供商进行情绪分析。
        """)


def _create_score_chart(result: NewsAnalysisResult):
    """创建评分图表"""
    fig = go.Figure()
    
    # 添加综合评分
    fig.add_trace(go.Bar(
        x=['综合评分'],
        y=[result.overall_score],
        name='综合评分',
        marker_color='rgba(55, 128, 191, 0.8)'
    ))
    
    # 添加各层评分
    fig.add_trace(go.Bar(
        x=['质量评估', '相关性评估', '影响度评估'],
        y=[result.quality_score, result.relevance_score, result.impact_score],
        name='各层评分',
        marker_color='rgba(219, 64, 82, 0.8)'
    ))
    
    # 添加阈值线
    fig.add_hline(y=result.quality_threshold, line_dash="dash", line_color="orange", 
                 annotation_text=f"质量阈值 {result.quality_threshold}")
    fig.add_hline(y=result.relevance_threshold, line_dash="dash", line_color="green", 
                 annotation_text=f"相关性阈值 {result.relevance_threshold}")
    fig.add_hline(y=result.impact_threshold, line_dash="dash", line_color="blue", 
                 annotation_text=f"影响度阈值 {result.impact_threshold}")
    
    fig.update_layout(
        title="新闻分析评分对比",
        height=400,
        xaxis_title="评分类型",
        yaxis_title="分数",
        yaxis_range=[0, 100],
        showlegend=True,
        barmode='group'
    )
    
    return fig