"""机会预测UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from logic.opportunity_predictor import OpportunityPredictor
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter


def render_opportunity_predictor_tab(db, config):
    """渲染机会预测标签页"""
    
    st.subheader("🔮 龙虎榜机会预测")
    st.caption("三层特征融合：历史规律(40%) + 技术面(35%) + 情绪指数(25%)")
    st.markdown("---")
    
    # 主内容区 - 配置面板
    with st.expander("⚙️ 预测配置", expanded=True):
        col_config1, col_config2, col_config3 = st.columns(3)
        
        with col_config1:
            lookback_days = st.slider("回溯天数", 30, 365, 180, help="分析历史数据的天数", key="opportunity_predictor_lookback")
            min_history = st.slider("最小历史记录", 5, 20, 5, help="最少历史记录数", key="opportunity_predictor_min_history")
        
        with col_config2:
            prediction_date = st.date_input(
                "预测日期",
                value=datetime.now() + timedelta(days=1),
                help="预测哪一天的机会"
            )
        
        with col_config3:
            weight_history = st.slider("历史规律权重", 0.0, 1.0, 0.40, 0.05, key="opportunity_history_weight")
            weight_technical = st.slider("技术面权重", 0.0, 1.0, 0.35, 0.05, key="opportunity_technical_weight")
            weight_sentiment = st.slider("情绪指数权重", 0.0, 1.0, 0.25, 0.05, key="opportunity_sentiment_weight")
        
        # 归一化权重
        total_weight = weight_history + weight_technical + weight_sentiment
        if total_weight > 0:
            weight_history /= total_weight
            weight_technical /= total_weight
            weight_sentiment /= total_weight
    
    # 主内容区 - 预测结果
    st.subheader("🔮 机会预测")
    
    # 获取历史龙虎榜数据
    if st.button("🔍 生成预测", key="generate_prediction"):
        with st.spinner('正在生成预测...'):
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
                
                if '操作方向' not in df_lhb.columns:
                    df_lhb['操作方向'] = df_lhb['净买入'].apply(
                        lambda x: '买' if x > 0 else '卖'
                    )
                
                # 创建预测器
                predictor = OpportunityPredictor(
                    lookback_days=lookback_days,
                    min_history=min_history
                )
                
                # 生成预测
                tomorrow_str = prediction_date.strftime("%Y-%m-%d")
                prediction = predictor.predict_tomorrow(tomorrow_str, df_lhb)
                
                # 显示预测结果
                st.success(f"✅ 预测生成完成！")
                
                # 整体活跃度
                st.divider()
                st.subheader("📊 整体预测")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("活跃度评分", f"{prediction.overall_activity}/100")
                with col_b:
                    st.metric("预测置信度", f"{prediction.prediction_confidence:.2%}")
                with col_c:
                    st.metric("市场情绪", prediction.market_sentiment)
                
                # 活跃度可视化
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=prediction.overall_activity,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "明日活跃度评分"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#FF6B6B"},
                        'steps': [
                            {'range': [0, 30], 'color': "#FFE5E5"},
                            {'range': [30, 70], 'color': "#E8F5E9"},
                            {'range': [70, 100], 'color': "#C8E6C9"}
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
                
                # 预测游资
                if prediction.predicted_capitals:
                    st.divider()
                    st.subheader("👤 预测游资")
                    
                    capital_df = pd.DataFrame([
                        {
                            '游资名称': cap.capital_name,
                            '出现概率': f"{cap.appearance_probability:.2%}",
                            '风险等级': cap.risk_level,
                            '预测成交额': Formatter.format_amount(cap.expected_amount),
                            '预测理由': ', '.join(cap.predict_reasons)
                        }
                        for cap in prediction.predicted_capitals
                    ])
                    
                    st.dataframe(
                        capital_df,
                        column_config={
                            '出现概率': st.column_config.NumberColumn('出现概率', format="%.2%")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 游资概率分布图
                    fig = px.bar(
                        capital_df,
                        x='游资名称',
                        y='出现概率',
                        title="预测游资出现概率",
                        color='出现概率',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("👍 暂无预测游资")
                
                # 预测股票
                if prediction.predicted_stocks:
                    st.divider()
                    st.subheader("📈 预测股票")
                    
                    stock_df = pd.DataFrame([
                        {
                            '股票代码': stock.code,
                            '股票名称': stock.name,
                            '出现概率': f"{stock.appearance_probability:.2%}",
                            '可能游资': ', '.join(stock.likely_capitals[:3]),
                            '预测理由': stock.predicted_reason
                        }
                        for stock in prediction.predicted_stocks
                    ])
                    
                    st.dataframe(
                        stock_df,
                        column_config={
                            '出现概率': st.column_config.NumberColumn('出现概率', format="%.2%")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("👍 暂无预测股票")
                
                # 核心洞察
                if prediction.key_insights:
                    st.divider()
                    st.subheader("💡 核心洞察")
                    
                    for i, insight in enumerate(prediction.key_insights, 1):
                        st.info(f"**{i}.** {insight}")
                
                # 特征分解
                st.divider()
                st.subheader("🔍 特征分解")
                
                # 重新计算特征以显示详细信息
                feature_1 = predictor._feature_1_history_patterns(df_lhb)
                feature_2 = predictor._feature_2_technical_signals(df_lhb)
                feature_3 = predictor._feature_3_sentiment_index(df_lhb)
                
                col_x, col_y, col_z = st.columns(3)
                with col_x:
                    st.metric("历史规律", f"{feature_1['activity']:.1f}/100")
                    st.caption(f"置信度: {feature_1.get('confidence', 0):.2%}")
                with col_y:
                    st.metric("技术面", f"{feature_2['activity']:.1f}/100")
                    st.caption(f"置信度: {feature_2.get('confidence', 0):.2%}")
                with col_z:
                    st.metric("情绪指数", f"{feature_3['activity']:.1f}/100")
                    st.caption(f"置信度: {feature_3.get('confidence', 0):.2%}")
                
                # 特征对比图
                fig = go.Figure(data=[
                    go.Bar(
                        name='历史规律',
                        x=['历史规律', '技术面', '情绪指数'],
                        y=[feature_1['activity'], 0, 0],
                        marker_color='#4CAF50'
                    ),
                    go.Bar(
                        name='技术面',
                        x=['历史规律', '技术面', '情绪指数'],
                        y=[0, feature_2['activity'], 0],
                        marker_color='#2196F3'
                    ),
                    go.Bar(
                        name='情绪指数',
                        x=['历史规律', '技术面', '情绪指数'],
                        y=[0, 0, feature_3['activity']],
                        marker_color='#FF9800'
                    )
                ])
                
                fig.update_layout(
                    title='特征得分对比',
                    barmode='group',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"❌ 预测失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏内容
    st.markdown("---")
    st.subheader("💡 预测解读")
    
    st.info("""
    **活跃度评分**：
    
    - **70+**：高度活跃
    
    - **40-70**：中度活跃
    
    - **<40**：低度活跃
    """)
    
    st.markdown("---")
    st.subheader("📊 市场情绪")
    
    st.info("""
    **情绪类型**：
    
    - **豪势**：看涨
    
    - **中性**：平衡
    
    - **谨慎**：看跌
    """)
    
    st.markdown("---")
    st.subheader("⚠️ 风险提示")
    
    st.warning("""
    1. 预测基于历史数据
    
    2. 不保证准确性
    
    3. 需结合其他分析
    
    4. 仅供参考
    
    5. 不构成投资建议
    """)