"""
参数优化可视化界面
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from logic.parameter_optimizer import ParameterGridSearch, BayesianOptimization
from logic.backtest_engine import get_backtest_engine


def render_parameter_optimization_tab(db, config):
    """渲染参数优化标签页"""
    
    st.header("🔧 参数优化")
    st.markdown("自动寻找最优策略参数")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 优化配置")
        
        symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="opt_symbol")
        
        start_date = st.date_input("开始日期", value=pd.to_datetime("2024-01-01"), key="opt_start")
        end_date = st.date_input("结束日期", value=pd.to_datetime("2024-12-31"), key="opt_end")
        
        signal_type = st.selectbox(
            "信号类型",
            ["MA", "MACD", "RSI"],
            help="选择要优化的策略类型"
        )
        
        optimization_method = st.selectbox(
            "优化方法",
            ["网格搜索", "贝叶斯优化"],
            help="选择参数优化方法"
        )
        
        initial_capital = st.number_input(
            "初始资金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
        
        # 优化目标
        optimization_target = st.selectbox(
            "优化目标",
            ["sharpe_ratio", "annual_return", "max_drawdown", "win_rate"],
            help="选择优化目标指标"
        )
        
        st.markdown("---")
        st.subheader("📊 参数范围")
        
        if signal_type == "MA":
            fast_min = st.number_input("快线最小值", value=5, min_value=1, max_value=60)
            fast_max = st.number_input("快线最大值", value=20, min_value=1, max_value=60)
            slow_min = st.number_input("慢线最小值", value=20, min_value=1, max_value=120)
            slow_max = st.number_input("慢线最大值", value=60, min_value=1, max_value=120)
            
            param_grid = {
                'fast_window': list(range(fast_min, fast_max + 1, 5)),
                'slow_window': list(range(slow_min, slow_max + 1, 10))
            }
        
        elif signal_type == "MACD":
            fast_min = st.number_input("快线最小值", value=8, min_value=1, max_value=30)
            fast_max = st.number_input("快线最大值", value=16, min_value=1, max_value=30)
            slow_min = st.number_input("慢线最小值", value=20, min_value=1, max_value=60)
            slow_max = st.number_input("慢线最大值", value=40, min_value=1, max_value=60)
            
            param_grid = {
                'fast_period': list(range(fast_min, fast_max + 1, 2)),
                'slow_period': list(range(slow_min, slow_max + 1, 5)),
                'signal_period': [9]
            }
        
        elif signal_type == "RSI":
            period_min = st.number_input("周期最小值", value=10, min_value=5, max_value=30)
            period_max = st.number_input("周期最大值", value=20, min_value=5, max_value=30)
            
            param_grid = {
                'period': list(range(period_min, period_max + 1, 2))
            }
        
        st.markdown("---")
        st.subheader("💡 优化说明")
        st.info(f"""
        **{optimization_method}说明**:
        
        网格搜索: 遍历所有参数组合，结果准确但耗时
        
        贝叶斯优化: 智能采样，效率更高
        
        **预计搜索次数**: {len(list(__import__('itertools').product(*param_grid.values())))} 个组合
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 优化结果")
        
        if st.button("🚀 开始优化", key="start_optimization"):
            with st.spinner("正在优化参数..."):
                try:
                    # 创建回测引擎
                    engine = get_backtest_engine(initial_capital=initial_capital)
                    
                    # 加载数据
                    start_str = start_date.strftime("%Y%m%d")
                    end_str = end_date.strftime("%Y%m%d")
                    
                    df = engine.load_historical_data(symbol, start_str, end_str)
                    
                    if df is not None and not df.empty:
                        # 执行优化
                        if optimization_method == "网格搜索":
                            optimizer = ParameterGridSearch(engine, metric=optimization_target)
                            result = optimizer.search(symbol, df, param_grid, signal_type)
                        else:
                            optimizer = BayesianOptimization(engine, n_iter=20)
                            param_bounds = {k: (min(v), max(v)) for k, v in param_grid.items()}
                            result = optimizer.optimize(symbol, df, param_bounds, signal_type)
                        
                        # 显示最优参数
                        st.success("✅ 优化完成！")
                        
                        st.subheader("🏆 最优参数")
                        
                        best_params = result.get('best_params', {})
                        best_metrics = result.get('best_metrics', {})
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.markdown("**参数配置**")
                            for param, value in best_params.items():
                                st.write(f"- {param}: {value}")
                        
                        with col_b:
                            st.markdown("**优化指标**")
                            if best_metrics:
                                st.metric("夏普比率", f"{best_metrics.get('sharpe_ratio', 0):.4f}")
                                st.metric("年化收益", f"{best_metrics.get('annual_return', 0):.2%}")
                                st.metric("最大回撤", f"{best_metrics.get('max_drawdown', 0):.2%}")
                                st.metric("胜率", f"{best_metrics.get('win_rate', 0):.2%}")
                        
                        # 显示所有结果
                        if optimization_method == "网格搜索":
                            results_df = optimizer.get_results_dataframe()
                            
                            st.subheader("📋 所有参数组合")
                            st.dataframe(
                                results_df,
                                column_config={
                                    "fast_window": "快线",
                                    "slow_window": "慢线",
                                    "sharpe_ratio": st.column_config.NumberColumn("夏普比率", format="%.4f"),
                                    "annual_return": st.column_config.NumberColumn("年化收益", format="%.2%"),
                                    "max_drawdown": st.column_config.NumberColumn("最大回撤", format="%.2%"),
                                    "win_rate": st.column_config.NumberColumn("胜率", format="%.2%")
                                },
                                use_container_width=True
                            )
                            
                            # 参数热力图
                            if signal_type == "MA":
                                st.subheader("🔥 参数热力图")
                                
                                # 透视表
                                pivot_df = results_df.pivot_table(
                                    index='fast_window',
                                    columns='slow_window',
                                    values=optimization_target,
                                    aggfunc='mean'
                                )
                                
                                fig = px.imshow(
                                    pivot_df,
                                    labels=dict(x="慢线", y="快线", color=optimization_target),
                                    title=f"{optimization_target} 热力图",
                                    color_continuous_scale='RdYlGn'
                                )
                                fig.update_layout(height=500)
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # 参数散点图
                            st.subheader("📈 参数散点图")
                            
                            fig = px.scatter(
                                results_df,
                                x='fast_window' if 'fast_window' in results_df.columns else results_df.columns[0],
                                y='slow_window' if 'slow_window' in results_df.columns else results_df.columns[1],
                                size=optimization_target,
                                color=optimization_target,
                                title="参数组合分布",
                                color_continuous_scale='Viridis'
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Top 10 参数组合
                            st.subheader("🥇 Top 10 参数组合")
                            top_10 = optimizer.get_top_n(10)
                            
                            for i, result in enumerate(top_10, 1):
                                with st.expander(f"#{i} - {optimization_target}: {result[optimization_target]:.4f}"):
                                    st.write(f"**参数**: {result.get('params', {})}")
                                    st.write(f"夏普比率: {result.get('sharpe_ratio', 0):.4f}")
                                    st.write(f"年化收益: {result.get('annual_return', 0):.2%}")
                                    st.write(f"最大回撤: {result.get('max_drawdown', 0):.2%}")
                                    st.write(f"胜率: {result.get('win_rate', 0):.2%}")
                        
                        else:  # 贝叶斯优化
                            history = result.get('history', [])
                            
                            if history:
                                st.subheader("📈 优化历史")
                                
                                history_df = pd.DataFrame(history)
                                
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=list(range(len(history_df))),
                                    y=history_df['score'],
                                    mode='lines+markers',
                                    name='优化得分',
                                    line=dict(color='#FF6B6B', width=2)
                                ))
                                
                                fig.update_layout(
                                    title="贝叶斯优化收敛曲线",
                                    xaxis_title="迭代次数",
                                    yaxis_title="夏普比率",
                                    height=400,
                                    template="plotly_dark"
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("无法获取历史数据，请检查日期范围和股票代码")
                
                except Exception as e:
                    st.error(f"优化失败: {str(e)}")
    
    with col2:
        st.subheader("💡 优化建议")
        
        st.info("""
        **参数优化技巧**:
        
        1. 从宽范围开始，逐步缩小
        
        2. 优先优化夏普比率
        
        3. 关注最大回撤 < 20%
        
        4. 避免过拟合 (样本外检验)
        
        5. 使用网格搜索验证
        """)
        
        st.markdown("---")
        st.subheader("📊 参数说明")
        
        if signal_type == "MA":
            st.markdown("""
            **快线**: 短期均线
            
            **慢线**: 长期均线
            
            **金叉**: 快线上穿慢线 (买入)
            
            **死叉**: 快线下穿慢线 (卖出)
            """)
        elif signal_type == "MACD":
            st.markdown("""
            **快线**: 12日EMA
            
            **慢线**: 26日EMA
            
            **信号线**: 9日EMA
            
            **金叉**: MACD上穿信号线
            """)
        elif signal_type == "RSI":
            st.markdown("""
            **超买**: RSI > 70 (卖出)
            
            **超卖**: RSI < 30 (买入)
            
            **中性**: 30-70 (持有)
            """)
        
        st.markdown("---")
        st.subheader("⚠️ 注意事项")
        st.warning("""
        1. 过度优化会导致过拟合
        
        2. 样本外检验必不可少
        
        3. 参数需要定期重新优化
        
        4. 不同股票参数可能不同
        """)