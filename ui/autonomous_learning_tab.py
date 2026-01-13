"""
自主学习系统 UI
支持AutoML、因果推断、在线学习和交易信号生成
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.autonomous_learning_system import AutonomousLearningSystem
from logic.data_manager import DataManager
from logic.akshare_data_loader import AKShareDataLoader
import logging

logger = logging.getLogger(__name__)


def render_autonomous_learning_tab(db: DataManager, config):
    """渲染自主学习标签页"""
    
    st.title("🤖 真正的自主学习系统")
    st.markdown("---")
    
    st.info("""
    **核心特性**:
    - ✅ 自动特征发现: 自动生成100+特征，自动选择最优特征
    - ✅ AutoML: 自动比较4种模型，选择最佳模型
    - ✅ 因果发现: 真正的因果推断（格兰杰因果检验）
    - ✅ 在线学习: 持续从新数据中学习
    - ✅ 元学习: 快速适应新任务（10个样本）
    - ✅ 交易信号: 生成买入/卖出信号
    """)
    
    # 初始化系统
    if 'autonomous_system' not in st.session_state:
        st.session_state.autonomous_system = AutonomousLearningSystem()
        st.session_state.model_trained = False
        st.session_state.trained_data = None
    
    system = st.session_state.autonomous_system
    
    # 侧边栏控制 - 优化布局
    with st.sidebar:
        st.header("⚙️ 控制面板")

        # 数据源选择
        with st.expander("📊 数据源", expanded=True):
            data_source = st.selectbox(
                "选择数据源",
                ["AkShare真实数据", "模拟数据"],
                help="选择使用真实数据还是模拟数据"
            )

            # 股票代码
            if data_source == "AkShare真实数据":
                stock_code = st.text_input(
                    "股票代码",
                    value="000001",
                    help="股票代码，例如：000001（平安银行）"
                )

                period = st.selectbox(
                    "时间周期",
                    ["daily", "weekly", "monthly"],
                    index=0,
                    help="K线周期"
                )

        # 训练参数
        with st.expander("🎓 训练参数"):
            n_days = st.slider(
                "训练天数",
                min_value=30,
                max_value=365,
                value=180,
                step=30,
                help="用于训练的历史数据天数"
            )

        # 交易信号参数
        with st.expander("📈 交易信号"):
            buy_threshold = st.slider(
                "买入阈值",
                min_value=-0.05,
                max_value=0.05,
                value=0.02,
                step=0.005,
                help="预测上涨超过此阈值时买入"
            )

            sell_threshold = st.slider(
                "卖出阈值",
                min_value=-0.05,
                max_value=0.05,
                value=-0.02,
                step=0.005,
                help="预测下跌超过此阈值时卖出"
            )
        
        # 系统状态
        st.subheader("📊 系统状态")
        if st.session_state.model_trained:
            status = system.get_system_status()
            st.metric("训练状态", "✅ 已训练")
            st.metric("特征数量", status['n_features'])
            st.metric("模型类型", status['model_type'] or 'N/A')
            
            if status['system_state'].get('last_update'):
                st.metric("最后更新", status['system_state']['last_update'][:19])
        else:
            st.metric("训练状态", "❌ 未训练")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("AutoML", "4种模型")
    
    with col2:
        st.metric("特征工程", "100+特征")
    
    with col3:
        st.metric("因果推断", "格兰杰检验")
    
    # 数据加载和训练
    st.markdown("---")
    st.header("📊 数据加载与训练")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 加载数据并训练", use_container_width=True):
            with st.spinner("正在加载数据并训练..."):
                try:
                    # 加载数据
                    if data_source == "AkShare真实数据":
                        loader = AKShareDataLoader()
                        data = loader.get_stock_daily(
                            code=stock_code,
                            start_date=(datetime.now() - timedelta(days=n_days*2)).strftime('%Y%m%d'),
                            end_date=datetime.now().strftime('%Y%m%d'),
                            adjust="qfq"
                        )

                        if data is None or len(data) == 0:
                            st.error(f"无法获取股票 {stock_code} 的数据")
                            return

                        # 检查数据列名
                        st.info(f"获取到的数据列: {list(data.columns)}")

                        # 只取最近n_days天
                        data = data.tail(n_days).reset_index(drop=True)

                        # 确保数据包含必要的列
                        required_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
                        missing_columns = [col for col in required_columns if col not in data.columns]

                        if missing_columns:
                            st.error(f"数据缺少必要的列: {missing_columns}")
                            st.error(f"可用列: {list(data.columns)}")
                            return

                        # 重命名列以匹配系统期望的格式
                        column_mapping = {
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close',
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                            '成交额': 'amount'
                        }
                        data = data.rename(columns=column_mapping)

                        st.success(f"成功获取 {len(data)} 条真实数据")
                    else:
                        # 使用模拟数据
                        np.random.seed(42)
                        dates = pd.date_range(start=datetime.now() - timedelta(days=n_days), periods=n_days)
                        data = pd.DataFrame({
                            'date': dates,
                            'open': 100 + np.cumsum(np.random.normal(0, 1, n_days)),
                            'high': 100 + np.cumsum(np.random.normal(0, 1, n_days)) + np.random.uniform(0, 2, n_days),
                            'low': 100 + np.cumsum(np.random.normal(0, 1, n_days)) - np.random.uniform(0, 2, n_days),
                            'close': 100 + np.cumsum(np.random.normal(0, 1, n_days)),
                            'volume': np.random.uniform(1000000, 5000000, n_days),
                            'amount': (100 + np.cumsum(np.random.normal(0, 1, n_days))) * np.random.uniform(1000000, 5000000, n_days)
                        })
                        st.success(f"生成 {len(data)} 条模拟数据")

                    st.session_state.trained_data = data
                    
                    # 训练系统
                    result = system.initialize(data, target='close')
                    
                    st.session_state.model_trained = True
                    st.success(f"训练完成！")
                    st.info(f"特征数量: {result['n_features']}")
                    st.info(f"最佳模型: {result['best_model_type']}")
                    st.info(f"最佳分数: {result['best_score']:.6f}")
                    
                except Exception as e:
                    st.error(f"训练失败: {str(e)}")
                    logger.error(f"训练失败: {e}", exc_info=True)
    
    # 显示数据
    if st.session_state.model_trained and st.session_state.trained_data is not None:
        data = st.session_state.trained_data
        
        with col2:
            st.subheader("📈 数据预览")
            st.dataframe(data.tail(10), use_container_width=True)
            
            # 显示数据统计
            st.subheader("📊 数据统计")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("数据天数", len(data))
            with col2:
                st.metric("价格范围", f"{data['close'].min():.2f} - {data['close'].max():.2f}")
            with col3:
                st.metric("平均成交量", f"{data['volume'].mean():.0f}")
    
    # 交易信号生成
    if st.session_state.model_trained:
        st.markdown("---")
        st.header("📈 交易信号生成")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🎯 生成交易信号", use_container_width=True):
                with st.spinner("正在生成交易信号..."):
                    try:
                        data = st.session_state.trained_data
                        
                        # 获取特征
                        features, feature_df = system.feature_engine.discover_features(data, target='close')
                        
                        # 只选择数值类型的特征
                        numeric_features = []
                        for feat in features:
                            if feat in feature_df.columns and pd.api.types.is_numeric_dtype(feature_df[feat]):
                                numeric_features.append(feat)
                        
                        # 预测
                        X = feature_df[numeric_features].fillna(0).values
                        predictions = system.model.predict(X)
                        
                        # 计算收益率
                        actual_returns = data['close'].pct_change().fillna(0)
                        predicted_returns = pd.Series(predictions).pct_change().fillna(0)
                        
                        # 生成信号
                        signals = pd.DataFrame({
                            'date': data['date'],
                            'close': data['close'],
                            'predicted': predictions,
                            'predicted_return': predicted_returns,
                            'actual_return': actual_returns
                        })
                        
                        signals['signal'] = 'hold'
                        signals.loc[signals['predicted_return'] > buy_threshold, 'signal'] = 'buy'
                        signals.loc[signals['predicted_return'] < sell_threshold, 'signal'] = 'sell'
                        
                        st.session_state.signals = signals
                        
                        # 显示信号统计
                        buy_count = (signals['signal'] == 'buy').sum()
                        sell_count = (signals['signal'] == 'sell').sum()
                        hold_count = (signals['signal'] == 'hold').sum()
                        
                        st.success("交易信号生成完成！")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("买入信号", buy_count, delta=f"{buy_count/len(signals)*100:.1f}%")
                        with col2:
                            st.metric("卖出信号", sell_count, delta=f"{sell_count/len(signals)*100:.1f}%")
                        with col3:
                            st.metric("持有信号", hold_count, delta=f"{hold_count/len(signals)*100:.1f}%")
                        
                    except Exception as e:
                        st.error(f"生成信号失败: {str(e)}")
                        logger.error(f"生成信号失败: {e}", exc_info=True)
        
        # 显示交易信号
        if 'signals' in st.session_state:
            signals = st.session_state.signals
            
            with col2:
                st.subheader("📊 信号分布")
                
                # 信号分布图
                signal_counts = signals['signal'].value_counts()
                fig = go.Figure(data=[
                    go.Bar(name=signal, x=[signal], y=[count])
                    for signal, count in signal_counts.items()
                ])
                fig.update_layout(
                    title="交易信号分布",
                    xaxis_title="信号类型",
                    yaxis_title="数量",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # 显示信号表格
            st.subheader("📋 交易信号详情")
            
            # 只显示有信号的行
            signal_df = signals[signals['signal'] != 'hold'].copy()
            if len(signal_df) > 0:
                # 添加颜色标记
                def highlight_signal(val):
                    if val == 'buy':
                        return 'background-color: #d4edda'
                    elif val == 'sell':
                        return 'background-color: #f8d7da'
                    return ''
                
                styled_df = signal_df.style.applymap(highlight_signal, subset=['signal'])
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("当前没有买入或卖出信号")
            
            # 绘制价格和信号
            st.subheader("📈 价格走势与信号")
            
            fig = go.Figure()
            
            # 添加价格线
            fig.add_trace(go.Scatter(
                x=signals['date'],
                y=signals['close'],
                mode='lines',
                name='价格',
                line=dict(color='blue', width=2)
            ))
            
            # 添加买入信号
            buy_signals = signals[signals['signal'] == 'buy']
            if len(buy_signals) > 0:
                fig.add_trace(go.Scatter(
                    x=buy_signals['date'],
                    y=buy_signals['close'],
                    mode='markers',
                    name='买入',
                    marker=dict(color='green', size=10, symbol='triangle-up')
                ))
            
            # 添加卖出信号
            sell_signals = signals[signals['signal'] == 'sell']
            if len(sell_signals) > 0:
                fig.add_trace(go.Scatter(
                    x=sell_signals['date'],
                    y=sell_signals['close'],
                    mode='markers',
                    name='卖出',
                    marker=dict(color='red', size=10, symbol='triangle-down')
                ))
            
            fig.update_layout(
                title="价格走势与交易信号",
                xaxis_title="日期",
                yaxis_title="价格",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # 因果推理
    if st.session_state.model_trained:
        st.markdown("---")
        st.header("🧠 因果推理")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            question = st.text_area(
                "输入问题",
                value="哪些因素影响股价？",
                height=100,
                help="输入你想了解的因果问题"
            )
            
            if st.button("🔍 进行因果推理", use_container_width=True):
                with st.spinner("正在分析因果关系..."):
                    try:
                        data = st.session_state.trained_data
                        reasoning = system.causal_reasoning(data, question)
                        st.session_state.causal_reasoning = reasoning
                    except Exception as e:
                        st.error(f"因果推理失败: {str(e)}")
                        logger.error(f"因果推理失败: {e}", exc_info=True)
        
        # 显示推理结果
        if 'causal_reasoning' in st.session_state:
            with col2:
                st.subheader("📊 推理结果")
                st.markdown(st.session_state.causal_reasoning)
    
    # 系统状态详情
    if st.session_state.model_trained:
        st.markdown("---")
        st.header("📊 系统状态详情")
        
        status = system.get_system_status()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🎯 特征重要性")
            if status['feature_importance']:
                # 显示Top 10特征
                top_features = sorted(
                    status['feature_importance'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                feature_df = pd.DataFrame(top_features, columns=['特征', '重要性'])
                st.dataframe(feature_df, use_container_width=True)
        
        with col2:
            st.subheader("🔗 因果关系图")
            if status['causal_graph']:
                causal_df = pd.DataFrame([
                    {'原因': cause, '结果': effect, '强度': strength}
                    for cause, effects in status['causal_graph'].items()
                    for effect, strength in effects.items()
                ])
                st.dataframe(causal_df, use_container_width=True)
            else:
                st.info("暂无因果关系数据")
    
    # 持续学习
    if st.session_state.model_trained:
        st.markdown("---")
        st.header("🔄 持续学习")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.info("💡 持续学习可以让系统从新数据中不断改进性能")
            
            if st.button("📥 添加新数据并学习", use_container_width=True):
                with st.spinner("正在添加新数据并学习..."):
                    try:
                        # 生成新数据（模拟）
                        n_new = 10
                        if data_source == "AkShare真实数据":
                            # 获取最新数据
                            loader = AKShareDataLoader()
                            new_data = loader.get_stock_daily(
                                code=stock_code,
                                start_date=datetime.now().strftime('%Y%m%d'),
                                end_date=(datetime.now() + timedelta(days=1)).strftime('%Y%m%d'),
                                adjust="qfq"
                            )
                        else:
                            # 模拟新数据
                            last_price = st.session_state.trained_data['close'].iloc[-1]
                            last_date = st.session_state.trained_data['date'].iloc[-1]
                            # 确保last_date是datetime对象
                            if hasattr(last_date, 'to_pydatetime'):
                                last_date = last_date.to_pydatetime()
                            elif isinstance(last_date, pd.Timestamp):
                                last_date = last_date.to_pydatetime()
                            elif not isinstance(last_date, datetime):
                                last_date = datetime.combine(last_date, datetime.min.time())

                            new_dates = pd.date_range(
                                start=last_date + timedelta(days=1),
                                periods=n_new
                            )
                            new_data = pd.DataFrame({
                                'date': new_dates,
                                'open': last_price + np.cumsum(np.random.normal(0, 1, n_new)),
                                'high': last_price + np.cumsum(np.random.normal(0, 1, n_new)) + np.random.uniform(0, 2, n_new),
                                'low': last_price + np.cumsum(np.random.normal(0, 1, n_new)) - np.random.uniform(0, 2, n_new),
                                'close': last_price + np.cumsum(np.random.normal(0, 1, n_new)),
                                'volume': np.random.uniform(1000000, 5000000, n_new),
                                'amount': (last_price + np.cumsum(np.random.normal(0, 1, n_new))) * np.random.uniform(1000000, 5000000, n_new)
                            })
                        
                        # 持续学习
                        result = system.continuous_learning(new_data, target='close')
                        
                        st.success(f"持续学习完成！")
                        st.info(f"新样本数: {result['n_new_samples']}")
                        st.info(f"新分数: {result['new_score']:.6f}")
                        
                    except Exception as e:
                        st.error(f"持续学习失败: {str(e)}")
                        logger.error(f"持续学习失败: {e}", exc_info=True)
        
        with col2:
            st.subheader("📈 学习历史")
            if len(system.learning_history) > 0:
                history_df = pd.DataFrame(system.learning_history)
                st.dataframe(history_df, use_container_width=True)
            else:
                st.info("暂无学习历史")