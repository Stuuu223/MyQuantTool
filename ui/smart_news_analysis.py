"""
智能新闻分析UI页面
集成新闻爬虫、机器学习分析、反馈学习等功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

from logic.news_crawler_akshare import NewsCrawlerManager, NewsItem
from logic.ml_news_analyzer import MLNewsAnalyzer, MLPredictionResult
from logic.feedback_learning import FeedbackLearningSystem


def render_smart_news_analysis_tab(db, config):
    """渲染智能新闻分析标签页"""
    
    st.subheader("🤖 智能新闻分析系统")
    st.caption("自主爬取新闻 + 机器学习分析 + 反馈学习优化")
    st.markdown("---")
    
    # 初始化session state
    if 'ml_analyzer' not in st.session_state:
        st.session_state.ml_analyzer = MLNewsAnalyzer()
        # 尝试加载已有模型
        if st.session_state.ml_analyzer.is_trained():
            st.session_state.ml_analyzer.load_models()
        else:
            # 使用示例数据训练
            with st.spinner('首次使用，正在初始化模型...'):
                sample_data = st.session_state.ml_analyzer.create_sample_training_data()
                st.session_state.ml_analyzer.train_models(sample_data)
    
    if 'feedback_system' not in st.session_state:
        st.session_state.feedback_system = FeedbackLearningSystem(st.session_state.ml_analyzer)
    
    if 'crawled_news' not in st.session_state:
        st.session_state.crawled_news = []
    
    # 创建选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["📰 新闻爬取", "🧠 智能分析", "📊 反馈学习", "⚙️ 模型管理"])
    
    # ==================== 选项卡1: 新闻爬取 ====================
    with tab1:
        st.subheader("📰 新闻爬取")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("**选择新闻源**")
            crawler_manager = NewsCrawlerManager()
            available_sources = crawler_manager.get_available_sources()
            source_names = crawler_manager.get_source_names()
            
            # 使用中文名称显示
            source_options = [source_names.get(s, s) for s in available_sources]
            
            selected_source_names = st.multiselect(
                "选择要爬取的新闻源",
                source_options,
                default=source_options,
                help="可以选择多个新闻源"
            )
            
            # 转换为代码
            selected_sources = [s for s in available_sources if source_names.get(s) in selected_source_names]
        
        with col2:
            st.write("**爬取配置**")
            limit_per_source = st.slider(
                "每个源爬取数量",
                min_value=5,
                max_value=50,
                value=10,
                step=5
            )
        
        # 爬取按钮
        if st.button("🕷️ 开始爬取新闻", key="crawl_news"):
            if not selected_sources:
                st.error("❌ 请至少选择一个新闻源")
                return
            
            with st.spinner('正在爬取新闻...'):
                all_news = []
                
                for source in selected_sources:
                    try:
                        news = crawler_manager.crawl_from_source(source, limit_per_source)
                        all_news.extend(news)
                        st.success(f"✅ 从 {source} 爬取了 {len(news)} 条新闻")
                    except Exception as e:
                        st.error(f"❌ 从 {source} 爬取失败: {str(e)}")
                
                # 按时间排序
                all_news.sort(key=lambda x: x.publish_time, reverse=True)
                st.session_state.crawled_news = all_news
                
                st.success(f"🎉 总共爬取了 {len(all_news)} 条新闻")
        
        # 显示爬取的新闻
        if st.session_state.crawled_news:
            st.markdown("---")
            st.subheader("📋 爬取结果")
            
            # 显示统计
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("总新闻数", len(st.session_state.crawled_news))
            with col_stat2:
                related_stocks = set()
                for news in st.session_state.crawled_news:
                    related_stocks.update(news.related_stocks)
                st.metric("涉及股票数", len(related_stocks))
            with col_stat3:
                sources = set(news.source for news in st.session_state.crawled_news)
                st.metric("新闻源数", len(sources))
            
            # 显示新闻列表
            st.write("**新闻列表**")
            
            for i, news in enumerate(st.session_state.crawled_news, 1):
                with st.expander(f"{i}. {news.title} - {news.source} ({news.publish_time.strftime('%Y-%m-%d %H:%M')})"):
                    st.write(f"**来源**: {news.source}")
                    st.write(f"**时间**: {news.publish_time}")
                    st.write(f"**相关股票**: {', '.join(news.related_stocks) if news.related_stocks else '无'}")
                    st.write(f"**内容**: {news.content[:500]}..." if len(news.content) > 500 else f"**内容**: {news.content}")
                    st.write(f"**链接**: {news.url}")
    
    # ==================== 选项卡2: 智能分析 ====================
    with tab2:
        st.subheader("🧠 智能分析")
        
        # 分析模式选择
        analysis_mode = st.radio(
            "选择分析模式",
            ["分析爬取的新闻", "手动输入新闻"],
            horizontal=True
        )
        
        if analysis_mode == "分析爬取的新闻":
            if not st.session_state.crawled_news:
                st.info("💡 请先在「新闻爬取」选项卡中爬取新闻")
                return
            
            st.write(f"当前有 {len(st.session_state.crawled_news)} 条新闻可供分析")
            
            # 选择要分析的新闻
            news_options = [f"{i+1}. {news.title[:50]}..." for i, news in enumerate(st.session_state.crawled_news)]
            selected_news_idx = st.selectbox(
                "选择要分析的新闻",
                range(len(st.session_state.crawled_news)),
                format_func=lambda x: news_options[x]
            )
            
            selected_news = st.session_state.crawled_news[selected_news_idx]
            
            # 显示选中的新闻
            st.info(f"**标题**: {selected_news.title}")
            st.info(f"**来源**: {selected_news.source}")
            st.info(f"**内容**: {selected_news.content[:300]}...")
            
            # 分析按钮
            if st.button("🔍 开始分析", key="analyze_crawled"):
                _analyze_and_display(selected_news)
        
        else:
            # 手动输入模式
            col1, col2 = st.columns([2, 1])
            
            with col1:
                news_title = st.text_input(
                    "新闻标题",
                    value="",
                    help="输入新闻标题"
                )
                
                news_content = st.text_area(
                    "新闻内容",
                    value="",
                    height=150,
                    help="输入新闻内容"
                )
            
            with col2:
                news_source = st.text_input(
                    "新闻来源",
                    value="",
                    help="输入新闻来源"
                )
                
                related_stocks = st.text_input(
                    "相关股票代码",
                    value="",
                    help="输入相关股票代码，用逗号分隔"
                )
            
            # 分析按钮
            if st.button("🔍 开始分析", key="analyze_manual"):
                if not news_title or not news_content:
                    st.error("❌ 请输入新闻标题和内容")
                    return
                
                related_stocks_list = [s.strip() for s in related_stocks.split(',') if s.strip()]
                
                news = NewsItem(
                    title=news_title,
                    content=news_content,
                    source=news_source or "未知来源",
                    publish_time=datetime.now(),
                    url="",
                    related_stocks=related_stocks_list
                )
                
                _analyze_and_display(news)
    
    # ==================== 选项卡3: 反馈学习 ====================
    with tab3:
        st.subheader("📊 反馈学习")
        
        # 性能报告
        st.write("**模型性能报告**")
        
        days = st.slider(
            "查看最近多少天的数据",
            min_value=7,
            max_value=90,
            value=30,
            step=7
        )
        
        report = st.session_state.feedback_system.get_performance_report(days)
        
        col_perf1, col_perf2, col_perf3 = st.columns(3)
        with col_perf1:
            st.metric("总预测数", report['metrics']['total_predictions'])
        with col_perf2:
            st.metric("正确预测数", report['metrics']['correct_predictions'])
        with col_perf3:
            accuracy = report['metrics']['accuracy']
            st.metric("准确率", f"{accuracy:.2%}")
        
        st.info(f"**摘要**: {report['summary']}")
        
        # 情绪分布
        if report['metrics']['sentiment_distribution']:
            st.write("**情绪分布**")
            sentiment_dist = report['metrics']['sentiment_distribution']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(sentiment_dist.keys()),
                    y=list(sentiment_dist.values()),
                    marker_color=['green', 'red', 'gray']
                )
            ])
            fig.update_layout(
                title="情绪分布",
                xaxis_title="情绪",
                yaxis_title="数量"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 待审核的预测
        st.markdown("---")
        st.subheader("📝 待审核的预测")
        
        pending_predictions = st.session_state.feedback_system.get_predictions_for_review(limit=10)
        
        if pending_predictions:
            for pred in pending_predictions:
                with st.expander(f"预测 #{pred['id']} - {pred['news_title'][:40]}... ({pred['timestamp'][:10]})"):
                    st.write(f"**标题**: {pred['news_title']}")
                    st.write(f"**预测情绪**: {pred['predicted_sentiment']} (置信度: {pred['predicted_confidence']:.2%})")
                    st.write(f"**预测影响度**: {pred['predicted_impact']:.2f}")
                    
                    # 添加反馈
                    with st.form(f"feedback_form_{pred['id']}"):
                        col_f1, col_f2 = st.columns(2)
                        
                        with col_f1:
                            actual_sentiment = st.selectbox(
                                "实际情绪",
                                ["positive", "negative", "neutral"],
                                key=f"sentiment_{pred['id']}"
                            )
                        
                        with col_f2:
                            actual_impact = st.slider(
                                "实际影响度",
                                0, 100, int(pred['predicted_impact']),
                                key=f"impact_{pred['id']}"
                            )
                        
                        stock_price_change = st.number_input(
                            "股价实际变化 (%)",
                            value=0.0,
                            key=f"price_{pred['id']}"
                        )
                        
                        notes = st.text_input(
                            "备注",
                            key=f"notes_{pred['id']}"
                        )
                        
                        if st.form_submit_button("提交反馈"):
                            st.session_state.feedback_system.add_feedback(
                                record_id=pred['id'],
                                actual_sentiment=actual_sentiment,
                                actual_impact=actual_impact,
                                stock_price_change=stock_price_change,
                                notes=notes
                            )
                            st.success("✅ 反馈已提交！感谢您的贡献")
                            st.rerun()
        else:
            st.info("暂无待审核的预测")
        
        # 导出数据
        st.markdown("---")
        st.subheader("💾 导出训练数据")
        
        if st.button("导出训练数据"):
            filepath = st.session_state.feedback_system.export_training_data()
            st.success(f"✅ 训练数据已导出到 {filepath}")
    
    # ==================== 选项卡4: 模型管理 ====================
    with tab4:
        st.subheader("⚙️ 模型管理")
        
        # 模型状态
        st.write("**模型状态**")
        
        is_trained = st.session_state.ml_analyzer.is_trained()
        
        if is_trained:
            st.success("✅ 模型已训练并加载")
        else:
            st.warning("⚠️ 模型未训练")
        
        # 重新训练模型
        st.markdown("---")
        st.subheader("🔄 重新训练模型")
        
        st.info("""
        **重新训练说明**：
        - 使用反馈数据库中的历史数据重新训练模型
        - 可以提高模型的预测准确率
        - 建议在有足够反馈数据后进行
        """)
        
        # 获取可用训练数据
        training_data = st.session_state.feedback_system.db.get_training_data()
        
        st.write(f"当前有 {len(training_data)} 条训练数据可用")
        
        if len(training_data) >= 10:
            if st.button("🔄 开始重新训练"):
                with st.spinner('正在重新训练模型...'):
                    try:
                        results = st.session_state.ml_analyzer.train_models(training_data)
                        
                        st.success("✅ 模型重新训练完成！")
                        
                        col_train1, col_train2 = st.columns(2)
                        with col_train1:
                            st.metric("情绪分类准确率", f"{results['sentiment_accuracy']:.4f}")
                        with col_train2:
                            st.metric("影响度预测MSE", f"{results['impact_mse']:.4f}")
                        
                        # 保存模型
                        st.session_state.ml_analyzer.save_models()
                        
                    except Exception as e:
                        st.error(f"❌ 训练失败: {str(e)}")
        else:
            st.warning("⚠️ 训练数据不足（至少需要10条），请先收集更多反馈数据")
        
        # 模型文件管理
        st.markdown("---")
        st.subheader("📁 模型文件")
        
        model_dir = "models"
        if os.path.exists(model_dir):
            model_files = [f for f in os.listdir(model_dir) if f.endswith('.pkl')]
            
            if model_files:
                st.write(f"找到 {len(model_files)} 个模型文件:")
                for file in model_files:
                    file_path = os.path.join(model_dir, file)
                    file_size = os.path.getsize(file_path)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    st.write(f"- {file} ({file_size/1024:.1f} KB, 更新于 {file_time.strftime('%Y-%m-%d %H:%M')})")
            else:
                st.info("暂无模型文件")
        else:
            st.info("模型目录不存在")


def _analyze_and_display(news: NewsItem):
    """分析新闻并显示结果"""
    ml_analyzer = st.session_state.ml_analyzer
    feedback_system = st.session_state.feedback_system
    
    # 使用ML模型分析
    prediction = ml_analyzer.analyze(
        news.title,
        news.content,
        news.source,
        news.related_stocks
    )
    
    # 记录预测
    result = feedback_system.predict_and_record(
        news.title,
        news.content,
        news.source,
        news.related_stocks,
        notes=f"URL: {news.url}" if news.url else None
    )
    
    # 显示结果
    st.success(f"✅ 分析完成！")
    
    # 显示预测结果
    col_pred1, col_pred2, col_pred3 = st.columns(3)
    with col_pred1:
        sentiment_emoji = "😊" if prediction.sentiment == "positive" else "😟" if prediction.sentiment == "negative" else "😐"
        st.metric("情绪倾向", f"{sentiment_emoji} {prediction.sentiment}")
    with col_pred2:
        st.metric("置信度", f"{prediction.sentiment_confidence:.2%}")
    with col_pred3:
        st.metric("影响度", f"{prediction.impact_score:.2f}/100")
    
    # 显示重要特征
    st.markdown("---")
    st.subheader("🔍 重要特征")
    
    if prediction.features_used:
        feature_df = pd.DataFrame(
            list(prediction.features_used.items()),
            columns=['特征', '重要性']
        ).head(10)
        
        st.dataframe(feature_df, use_container_width=True, hide_index=True)
        
        # 可视化特征重要性
        fig = go.Figure(data=[
            go.Bar(
                x=list(prediction.features_used.values())[:10],
                y=list(prediction.features_used.keys())[:10],
                orientation='h'
            )
        ])
        fig.update_layout(
            title="Top 10 重要特征",
            xaxis_title="重要性",
            yaxis_title="特征",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 提供反馈入口
    st.markdown("---")
    st.subheader("📝 提供反馈")
    
    st.info(f"预测记录ID: {result['record_id']} - 您可以在「反馈学习」选项卡中为这条预测提供反馈，帮助模型改进")
    
    # 快速反馈表单
    with st.form(f"quick_feedback_{result['record_id']}"):
        col_q1, col_q2 = st.columns(2)
        
        with col_q1:
            actual_sentiment = st.selectbox(
                "实际情绪（可选）",
                ["", "positive", "negative", "neutral"],
                key=f"quick_sentiment_{result['record_id']}"
            )
        
        with col_q2:
            actual_impact = st.slider(
                "实际影响度（可选）",
                0, 100, int(prediction.impact_score),
                key=f"quick_impact_{result['record_id']}"
            )
        
        if st.form_submit_button("提交快速反馈"):
            if actual_sentiment:
                feedback_system.add_feedback(
                    record_id=result['record_id'],
                    actual_sentiment=actual_sentiment,
                    actual_impact=actual_impact
                )
                st.success("✅ 反馈已提交！感谢您的贡献")
            else:
                st.warning("⚠️ 请至少选择实际情绪")