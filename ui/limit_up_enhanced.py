"""
打板预测系统UI
功能：14特征工程、XGBoost预测一字板概率、风险预警、操作建议
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from logic.limit_up_predictor import get_limit_up_predictor
from logic.data_manager import DataManager


def render_limit_up_enhanced_tab(db, config):
    """渲染打板预测标签页"""
    
    st.header("🎯 打板预测系统")
    st.caption("14特征工程 + XGBoost预测 + 风险预警 + 智能操作建议")
    
    # 初始化预测器
    predictor = get_limit_up_predictor()
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 预测配置")
        
        date = st.date_input("预测日期", value=datetime.now().date(), key="limit_up_date")
        date_str = date.strftime("%Y%m%d")
        
        st.markdown("---")
        st.markdown("### 📊 风险偏好")
        
        risk_preference = st.radio(
            "风险偏好",
            ["保守", "平衡", "激进"],
            index=1,
            key="risk_preference"
        )
        
        risk_thresholds = {
            "保守": 0.3,  # 只推荐低风险
            "平衡": 0.6,  # 推荐低中风险
            "激进": 0.9   # 推荐所有风险
        }
        
        st.markdown("---")
        st.markdown("### 🎯 预测目标")
        
        min_probability = st.slider("最小一字板概率", 0, 100, 60, 5, key="min_probability") / 100
    
    # 主要内容
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🔮 一字板概率预测")
        
        # 单股预测
        st.markdown("### 📈 单股预测")
        
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            symbol = st.text_input("股票代码", value="600519", key="limit_up_symbol")
        
        with col_p2:
            if st.button("🔮 预测", key="predict_single", type="primary"):
                with st.spinner("正在预测一字板概率..."):
                    try:
                        # 获取当前价格
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=60)
                        
                        df = db.get_history_data(
                            symbol,
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d")
                        )
                        
                        if df is not None and not df.empty:
                            current_price = df['close'].iloc[-1]
                            
                            # 预测
                            prediction = predictor.predict_limit_up(symbol, date_str, current_price)
                            
                            if prediction:
                                st.info("💡 提示：当前使用演示预测数据，实际预测需要训练模型")
                                
                                # 显示预测结果
                                st.success("✅ 预测完成！")
                            
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric("一字板概率", f"{prediction.oneword_probability:.1%}")
                            col_b.metric("置信度", f"{prediction.oneword_confidence:.1%}")
                            col_c.metric("综合评分", f"{prediction.total_score:.1f}")
                            
                            col_d, col_e, col_f = st.columns(3)
                            col_d.metric("风险等级", prediction.risk_level.value)
                            col_e.metric("入场时机", prediction.entry_timing.value)
                            col_f.metric("预期收益", f"{(prediction.take_profit - prediction.entry_price) / prediction.entry_price * 100:.1f}%")
                            
                            # 操作建议
                            st.markdown("---")
                            st.markdown("### 💼 操作建议")
                            
                            col_op1, col_op2, col_op3 = st.columns(3)
                            col_op1.metric("建议入场价", f"¥{prediction.entry_price:.2f}")
                            col_op2.metric("止损位", f"¥{prediction.stop_loss:.2f}")
                            col_op3.metric("止盈位", f"¥{prediction.take_profit:.2f}")
                            
                            # 风险提示
                            if prediction.risk_level.value in ["高风险", "极高风险"]:
                                st.error(f"⚠️ {prediction.risk_reason}")
                            elif prediction.risk_level.value == "中风险":
                                st.warning(f"⚠️ {prediction.risk_reason}")
                            else:
                                st.success(f"✅ {prediction.risk_reason}")
                            
                            # 特征分数
                            st.markdown("---")
                            st.markdown("### 📊 14特征分析")
                            
                            feature_df = pd.DataFrame([
                                {'特征': feature, '分数': score}
                                for feature, score in prediction.features_score.items()
                            ])
                            
                            feature_df = feature_df.sort_values('分数', ascending=False)
                            
                            fig_features = go.Figure()
                            
                            fig_features.add_trace(go.Bar(
                                x=feature_df['分数'],
                                y=feature_df['特征'],
                                orientation='h',
                                marker_color=feature_df['分数'].apply(
                                    lambda x: '#4CAF50' if x >= 70 else '#FFC107' if x >= 50 else '#FF5252'
                                ),
                                text=feature_df['分数'].apply(lambda x: f'{x:.1f}'),
                                textposition='auto',
                            ))
                            
                            fig_features.update_layout(
                                title='特征分数排行',
                                xaxis_title='分数 (0-100)',
                                yaxis_title='特征',
                                xaxis_range=[0, 100],
                                height=600,
                                showlegend=False
                            )
                            
                            st.plotly_chart(fig_features, use_container_width=True)
                            
                        else:
                            st.warning("⚠️ 无法获取股票数据")
                    
                    except Exception as e:
                        st.error(f"❌ 预测失败: {str(e)}")
        
        # 批量预测
        st.markdown("---")
        st.markdown("### 🎯 批量预测")
        
        col_b1, col_b2 = st.columns([2, 1])
        
        with col_b1:
            batch_symbols = st.text_input(
                "股票代码（逗号分隔）",
                value="600519,000001,600036,601988,600111",
                key="batch_symbols"
            )
        
        with col_b2:
            batch_count = st.slider("预测数量", 1, 20, 5, 1, key="batch_count")
        
        if st.button("🚀 批量预测", key="predict_batch"):
            with st.spinner("正在批量预测..."):
                try:
                    symbols = [s.strip() for s in batch_symbols.split(',') if s.strip()][:batch_count]
                    
                    predictions = predictor.batch_predict_limit_ups(symbols, date_str)
                    
                    if predictions:
                        st.info("💡 提示：当前使用演示预测数据，实际预测需要训练模型")
                        
                        # 排序候选股
                        candidates = predictor.rank_candidates(predictions)
                    
                    # 转换为DataFrame
                    df_predictions = pd.DataFrame([
                        {
                            '股票代码': pred.stock_code,
                            '一字板概率': pred.oneword_probability,
                            '置信度': pred.oneword_confidence,
                            '综合评分': pred.total_score,
                            '风险等级': pred.risk_level.value,
                            '入场时机': pred.entry_timing.value,
                            '入场价': pred.entry_price,
                            '止损位': pred.stop_loss,
                            '止盈位': pred.take_profit,
                            '预期收益': (pred.take_profit - pred.entry_price) / pred.entry_price * 100
                        }
                        for pred in predictions
                    ])
                    
                    # 筛选
                    df_predictions = df_predictions[df_predictions['一字板概率'] >= min_probability]
                    
                    risk_level_map = {'低风险': 1, '中风险': 2, '高风险': 3, '极高风险': 4}
                    df_predictions['风险排序'] = df_predictions['风险等级'].map(risk_level_map)
                    df_predictions = df_predictions[df_predictions['风险排序'] <= 
                                                       risk_level_map.get(
                                                           prediction.risk_level.value, 
                                                           4
                                                       ) if risk_preference == '保守' else 4]
                    
                    # 按综合评分排序
                    df_predictions = df_predictions.sort_values('综合评分', ascending=False)
                    
                    # 显示结果
                    st.dataframe(
                        df_predictions,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            '一字板概率': st.column_config.ProgressColumn(
                                '一字板概率',
                                format='%.1%',
                                min_value=0,
                                max_value=1
                            ),
                            '置信度': st.column_config.ProgressColumn(
                                '置信度',
                                format='%.1%',
                                min_value=0,
                                max_value=1
                            ),
                            '综合评分': st.column_config.NumberColumn(
                                '综合评分',
                                format='%.1f'
                            ),
                            '预期收益': st.column_config.NumberColumn(
                                '预期收益',
                                format='%.1f%%'
                            )
                        }
                    )
                    
                    # 概率分布图
                    st.markdown("---")
                    st.subheader("📊 一字板概率分布")
                    
                    fig_prob = go.Figure()
                    
                    fig_prob.add_trace(go.Bar(
                        x=df_predictions['股票代码'],
                        y=df_predictions['一字板概率'],
                        marker_color=df_predictions['一字板概率'].apply(
                            lambda x: '#4CAF50' if x >= 0.8 else '#FFC107' if x >= 0.6 else '#FF5252'
                        ),
                        text=df_predictions['一字板概率'].apply(lambda x: f'{x:.1%}'),
                        textposition='auto',
                    ))
                    
                    fig_prob.update_layout(
                        title='一字板概率分布',
                        xaxis_title='股票代码',
                        yaxis_title='概率',
                        yaxis_range=[0, 1],
                        height=500,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_prob, use_container_width=True)
                    
                    # 风险分布
                    st.markdown("---")
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    
                    risk_counts = df_predictions['风险等级'].value_counts()
                    
                    with col_r1:
                        st.metric("低风险", 
                                risk_counts.get('低风险', 0),
                                help="风险率 < 20%")
                    
                    with col_r2:
                        st.metric("中风险",
                                risk_counts.get('中风险', 0),
                                help="风险率 20-50%")
                    
                    with col_r3:
                        st.metric("高风险",
                                risk_counts.get('高风险', 0),
                                help="风险率 50-80%")
                    
                    with col_r4:
                        st.metric("极高风险",
                                risk_counts.get('极高风险', 0),
                                help="风险率 > 80%")
                
                except Exception as e:
                    st.error(f"❌ 批量预测失败: {str(e)}")
    
    with col2:
        st.subheader("💡 操作指南")
        
        st.markdown("""
        ### 🎯 入场时机
        
        **竞价预上**
        - 一字板概率 > 80%
        - 高置信度
        - 低风险等级
        
        **竞价段位**
        - 一字板概率 60-80%
        - 中高置信度
        - 低中风险等级
        
        **第一小时**
        - 一字板概率 40-60%
        - 中等置信度
        - 中风险等级
        
        **下午断叨上**
        - 一字板概率 < 40%
        - 低置信度
        - 高风险等级
        """)
        
        st.markdown("---")
        st.markdown("""
        ### ⚠️ 风险管理
        
        **止损策略**
        - 严格执行止损
        - 不抱侥幸心理
        - 及时止损出局
        
        **仓位控制**
        - 低风险：30-50%
        - 中风险：20-30%
        - 高风险：10-20%
        - 极高风险：0-10%
        
        **止盈策略**
        - 达到止盈位减半
            - 剩余仓位移动止损
        - 不盲目追高
        - 及时落袋为安
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 📊 14特征说明
        
        **价格特征 (4)**
        - 涨幅
        - 涨速
        - 振幅
        - 相对强弱
        
        **龙虎榜特征 (3)**
        - 上榜次数
        - 成交额
        - 买卖比
        
        **竞价特征 (2)**
        - 竞价涨幅
        - 竞价量比
        
        **K线特征 (2)**
        - 技术形态
        - 趋势强度
        
        **题材特征 (1)**
        - 题材热度
        
        **资金特征 (2)**
        - 资金流入
        - 主力动向
        """)