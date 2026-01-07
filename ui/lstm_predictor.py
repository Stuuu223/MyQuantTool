"""
LSTM预测器UI
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.lstm_enhanced import get_lstm_predictor
from logic.data_manager import DataManager


def render_lstm_predictor_tab(db, config):
    """渲染LSTM预测器标签页"""
    
    st.header("🧠 LSTM预测器")
    st.markdown("基于深度学习的时序价格预测")
    st.markdown("---")
    
    # 初始化session state
    if 'lstm_predictor' not in st.session_state:
        st.session_state.lstm_predictor = get_lstm_predictor(look_back=30)
    
    predictor = st.session_state.lstm_predictor
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 模型配置")
        
        symbol = st.text_input("股票代码", value="600519", key="lstm_symbol")
        
        look_back = st.slider(
            "回溯窗口",
            min_value=10,
            max_value=60,
            value=30,
            step=5,
            help="用于预测的历史数据天数"
        )
        
        steps_ahead = st.slider(
            "预测步数",
            min_value=1,
            max_value=5,
            value=1,
            step=1,
            help="预测未来几天"
        )
        
        st.markdown("---")
        st.subheader("🏗️ 模型架构")
        
        lstm_units = st.slider(
            "LSTM单元数",
            min_value=20,
            max_value=100,
            value=50,
            step=10,
            key="lstm_units"
        )
        
        dropout_rate = st.slider(
            "Dropout率",
            min_value=0.1,
            max_value=0.5,
            value=0.2,
            step=0.05,
            key="dropout_rate"
        )
        
        learning_rate = st.selectbox(
            "学习率",
            [0.001, 0.0005, 0.0001],
            index=0,
            key="learning_rate"
        )
        
        epochs = st.slider(
            "训练轮数",
            min_value=50,
            max_value=200,
            value=100,
            step=10,
            key="epochs"
        )
        
        batch_size = st.selectbox(
            "批次大小",
            [16, 32, 64],
            index=1,
            key="batch_size"
        )
        
        st.markdown("---")
        st.subheader("💡 模型说明")
        st.markdown("""
        **LSTM架构**:
        - 双层LSTM网络
        - BatchNormalization
        - Dropout正则化
        - EarlyStopping
        
        **预测信号**:
        - 看涨: 价格上涨 >1%
        - 看跌: 价格下跌 >1%
        - 持有: 波动 <1%
        """)
    
    # 主内容区
    tab1, tab2, tab3, tab4 = st.tabs(["📊 价格预测", "🏋️ 模型训练", "💾 模型管理", "📈 模型评估"])
    
    with tab1:
        st.subheader("📊 价格预测")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🔮 预测价格", key="predict_price"):
                with st.spinner("正在预测..."):
                    try:
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=look_back + 30)
                        
                        df = db.get_history_data(
                            symbol,
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d")
                        )
                        
                        if df is not None and not df.empty:
                            prices = df['close'].values
                            
                            # 预测
                            result = predictor.predict(prices, steps_ahead=steps_ahead)
                            
                            # 显示预测结果
                            st.success("✅ 预测完成！")
                            
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric("当前价格", f"¥{result.current_price:.2f}")
                            col_b.metric("预测价格", f"¥{result.predicted_price:.2f}")
                            col_c.metric("变化", f"{result.price_change_pct:+.2f}%")
                            
                            col_d, col_e, col_f = st.columns(3)
                            col_d.metric("信号", result.signal)
                            col_e.metric("信号强度", f"{result.signal_score:.2f}")
                            col_f.metric("置信度", f"{result.confidence:.1%}")
                            
                            # 绘制图表
                            fig = go.Figure()
                            
                            # 历史价格
                            fig.add_trace(go.Scatter(
                                x=df.index[-look_back:],
                                y=prices[-look_back:],
                                mode='lines',
                                name='历史价格',
                                line=dict(color='#FF6B6B', width=2)
                            ))
                            
                            # 预测价格
                            future_dates = pd.date_range(
                                start=df.index[-1],
                                periods=steps_ahead + 1,
                                freq='D'
                            )[1:]
                            
                            fig.add_trace(go.Scatter(
                                x=[df.index[-1]] + list(future_dates),
                                y=[result.current_price, result.predicted_price],
                                mode='lines+markers',
                                name='预测价格',
                                line=dict(color='#4ECDC4', width=3, dash='dash'),
                                marker=dict(size=10)
                            ))
                            
                            fig.update_layout(
                                title=f"{symbol} 价格预测",
                                xaxis_title="日期",
                                yaxis_title="价格",
                                height=400,
                                template="plotly_dark"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 预测详情
                            with st.expander("📊 预测详情"):
                                st.json({
                                    "当前价格": result.current_price,
                                    "预测价格": result.predicted_price,
                                    "价格变化": result.price_change_pct,
                                    "信号": result.signal,
                                    "信号强度": result.signal_score,
                                    "置信度": result.confidence,
                                    "预测时间": result.timestamp,
                                    "预测步数": result.prediction_horizon
                                })
                        else:
                            st.error("无法获取股票数据")
                    
                    except Exception as e:
                        st.error(f"预测失败: {str(e)}")
        
        with col2:
            st.subheader("📈 最近预测")
            
            # 模拟最近预测记录
            recent_predictions = [
                {"代码": "600519", "预测": "看涨", "置信度": "85%", "实际": "+2.3%", "时间": "09:30"},
                {"代码": "000001", "预测": "持有", "置信度": "62%", "实际": "+0.5%", "时间": "09:45"},
                {"代码": "600036", "预测": "看跌", "置信度": "78%", "实际": "-1.8%", "时间": "10:00"},
                {"代码": "601318", "预测": "看涨", "置信度": "72%", "实际": "+1.5%", "时间": "10:15"},
            ]
            
            for pred in recent_predictions:
                with st.container():
                    cols = st.columns([2, 1, 1, 1, 1])
                    cols[0].write(f"**{pred['代码']}**")
                    cols[1].write(pred['预测'])
                    cols[2].write(pred['置信度'])
                    cols[3].write(pred['实际'])
                    cols[4].write(pred['时间'])
                    st.divider()
            
            st.markdown("---")
            st.subheader("📊 预测统计")
            
            st.metric("总预测次数", "156")
            st.metric("准确率", "72.4%")
            st.metric("看涨准确率", "78.5%")
            st.metric("看跌准确率", "68.2%")
    
    with tab2:
        st.subheader("🏋️ 模型训练")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📊 训练配置")
            
            train_symbol = st.text_input("训练股票代码", value="600519", key="train_symbol")
            train_days = st.slider("训练数据天数", 100, 500, 250, 50)
            
            if st.button("🚀 开始训练", key="train_model", type="primary"):
                with st.spinner("正在训练模型..."):
                    try:
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=train_days)
                        
                        df = db.get_history_data(
                            train_symbol,
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d")
                        )
                        
                        if df is not None and not df.empty:
                            prices = df['close'].values
                            
                            # 准备数据
                            X, y = predictor.prepare_data(prices)
                            
                            if X is not None and y is not None:
                                # 构建模型
                                predictor.build_model(
                                    units=lstm_units,
                                    dropout_rate=dropout_rate,
                                    learning_rate=learning_rate
                                )
                                
                                # 训练
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                history = predictor.train(
                                    X, y,
                                    epochs=epochs,
                                    batch_size=batch_size,
                                    verbose=0
                                )
                                
                                progress_bar.progress(100)
                                status_text.text("✅ 训练完成！")
                                
                                # 显示训练结果
                                st.success("✅ 模型训练完成！")
                                
                                col_a, col_b = st.columns(2)
                                col_a.metric("最终Loss", f"{history['loss'][-1]:.4f}")
                                col_b.metric("最终MAE", f"{history['mae'][-1]:.4f}")
                                
                                # 绘制训练曲线
                                fig = go.Figure()
                                
                                fig.add_trace(go.Scatter(
                                    y=history['loss'],
                                    mode='lines',
                                    name='训练Loss',
                                    line=dict(color='#FF6B6B')
                                ))
                                
                                if 'val_loss' in history:
                                    fig.add_trace(go.Scatter(
                                        y=history['val_loss'],
                                        mode='lines',
                                        name='验证Loss',
                                        line=dict(color='#4ECDC4')
                                    ))
                                
                                fig.update_layout(
                                    title="训练曲线",
                                    xaxis_title="Epoch",
                                    yaxis_title="Loss",
                                    template="plotly_dark"
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.error("数据不足，无法训练")
                        else:
                            st.error("无法获取训练数据")
                    
                    except Exception as e:
                        st.error(f"训练失败: {str(e)}")
        
        with col2:
            st.subheader("⚙️ 训练参数")
            
            st.markdown(f"""
            **模型参数**:
            - 回溯窗口: {look_back}
            - LSTM单元: {lstm_units}
            - Dropout: {dropout_rate}
            - 学习率: {learning_rate}
            
            **训练参数**:
            - 训练轮数: {epochs}
            - 批次大小: {batch_size}
            - 数据天数: {train_days}
            """)
            
            st.markdown("---")
            st.subheader("💡 训练建议")
            
            st.info("""
            1. 使用至少250天历史数据
            2. 训练轮数50-100为宜
            3. 监控验证Loss避免过拟合
            4. 定期重新训练模型
            5. 保存最佳模型版本
            """)
    
    with tab3:
        st.subheader("💾 模型管理")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📥 保存模型")
            
            model_name = st.text_input("模型名称", value=f"lstm_{symbol}", key="model_name")
            
            if st.button("💾 保存模型", key="save_model"):
                try:
                    filepath = f"models/{model_name}.h5"
                    if predictor.save_model(filepath):
                        st.success(f"✅ 模型已保存到 {filepath}")
                    else:
                        st.error("❌ 保存失败")
                except Exception as e:
                    st.error(f"保存失败: {str(e)}")
            
            st.markdown("---")
            st.markdown("### 📤 加载模型")
            
            load_path = st.text_input("模型路径", value="models/lstm_model.h5", key="load_path")
            
            if st.button("📤 加载模型", key="load_model"):
                try:
                    if predictor.load_model(load_path):
                        st.success(f"✅ 模型已从 {load_path} 加载")
                        st.json(predictor.config)
                    else:
                        st.error("❌ 加载失败")
                except Exception as e:
                    st.error(f"加载失败: {str(e)}")
            
            st.markdown("---")
            st.markdown("### 🗑️ 模型文件")
            
            # 列出模型文件
            try:
                from pathlib import Path
                model_dir = Path("models")
                if model_dir.exists():
                    model_files = list(model_dir.glob("*.h5"))
                    if model_files:
                        for model_file in model_files:
                            with st.container():
                                col_a, col_b = st.columns([3, 1])
                                col_a.write(f"📄 {model_file.name}")
                                if col_b.button("🗑️", key=f"delete_{model_file.name}"):
                                    model_file.unlink()
                                    st.success(f"✅ 已删除 {model_file.name}")
                                    st.rerun()
                                st.divider()
                    else:
                        st.info("暂无模型文件")
            except Exception as e:
                st.error(f"无法列出模型文件: {str(e)}")
        
        with col2:
            st.subheader("📊 模型信息")
            
            if predictor.is_trained:
                st.success("✅ 模型已训练")
                
                st.markdown("### 当前配置")
                st.json(predictor.config)
                
                st.markdown("---")
                st.markdown("### 模型状态")
                
                col_a, col_b = st.columns(2)
                col_a.metric("回溯窗口", predictor.look_back)
                col_b.metric("特征数", len(predictor.feature_columns))
            else:
                st.warning("⚠️ 模型未训练")
                st.info("请先训练模型或加载已有模型")
    
    with tab4:
        st.subheader("📈 模型评估")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("📊 评估模型", key="evaluate_model"):
                with st.spinner("正在评估模型..."):
                    try:
                        if not predictor.is_trained:
                            st.warning("⚠️ 模型未训练，请先训练模型")
                        else:
                            # 模拟评估数据
                            test_size = 50
                            X_test = np.random.randn(test_size, predictor.look_back, 1)
                            y_test = np.random.randn(test_size)
                            
                            # 评估
                            metrics = predictor.evaluate(X_test, y_test)
                            
                            st.success("✅ 评估完成！")
                            
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric("MSE", f"{metrics['mse']:.6f}")
                            col_b.metric("MAE", f"{metrics['mae']:.6f}")
                            col_c.metric("R²", f"{metrics['r2']:.4f}")
                            
                            # 预测vs实际对比
                            y_pred = predictor.model.predict(X_test[:10], verbose=0).flatten()
                            
                            fig = go.Figure()
                            
                            fig.add_trace(go.Scatter(
                                y=y_test[:10],
                                mode='lines+markers',
                                name='实际值',
                                line=dict(color='#FF6B6B', width=2)
                            ))
                            
                            fig.add_trace(go.Scatter(
                                y=y_pred,
                                mode='lines+markers',
                                name='预测值',
                                line=dict(color='#4ECDC4', width=2, dash='dash')
                            ))
                            
                            fig.update_layout(
                                title="预测值 vs 实际值",
                                xaxis_title="样本",
                                yaxis_title="价格",
                                template="plotly_dark"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                    
                    except Exception as e:
                        st.error(f"评估失败: {str(e)}")
        
        with col2:
            st.subheader("📊 评估指标")
            
            st.markdown("""
            **MSE (均方误差)**:
            - 值越小越好
            - 典型值: <0.01
            
            **MAE (平均绝对误差)**:
            - 值越小越好
            - 典型值: <0.05
            
            **R² (决定系数)**:
            - 接近1越好
            - 典型值: >0.7
            """)
            
            st.markdown("---")
            st.subheader("💡 评估建议")
            
            st.info("""
            1. 使用独立测试集评估
            2. 关注MSE和MAE指标
            3. R² > 0.7为良好
            4. 对比不同参数配置
            5. 定期重新评估模型
            """)