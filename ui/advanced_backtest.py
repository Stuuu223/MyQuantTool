"""
增强版回测引擎UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.backtest_engine import get_backtest_engine
from logic.data_manager import DataManager


def render_advanced_backtest_tab(db, config):
    """渲染增强版回测引擎标签页"""
    
    st.header("🧪 增强版回测引擎")
    st.markdown("支持T+1清算、滑点模拟、完整绩效指标的历史回测")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 回测配置")
        
        symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="backtest_symbol")
        
        start_date = st.date_input("开始日期", value=pd.to_datetime("2024-01-01"), key="backtest_start")
        end_date = st.date_input("结束日期", value=pd.to_datetime("2024-12-31"), key="backtest_end")
        
        initial_capital = st.number_input(
            "初始资金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
        
        signal_type = st.selectbox(
            "信号类型",
            ["MA", "MACD", "RSI", "LSTM"],
            help="选择要回测的交易信号类型"
        )
        
        st.markdown("---")
        st.subheader("💰 交易成本")
        
        commission_rate = st.slider(
            "手续费率",
            min_value=0.0,
            max_value=0.01,
            value=0.001,
            step=0.0001,
            format="%.4f"
        )
        
        slippage_rate = st.slider(
            "滑点率",
            min_value=0.0,
            max_value=0.01,
            value=0.001,
            step=0.0001,
            format="%.4f"
        )
        
        t_plus_one = st.checkbox("启用T+1交易", value=True, help="A股T+1交易规则")
        
        st.markdown("---")
        st.subheader("📊 绩效指标说明")
        st.markdown("""
        **夏普比率**: 风险调整后收益，>1为优秀
        
        **最大回撤**: 最大亏损幅度，<20%为理想
        
        **胜率**: 盈利交易占比，>50%为合格
        
        **盈亏比**: 盈利/亏损，>1为正期望
        
        **年化收益**: 年化收益率
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 回测结果")
        
        if st.button("🚀 开始回测", key="start_backtest"):
            with st.spinner("正在运行回测..."):
                try:
                    # 创建回测引擎
                    engine = get_backtest_engine(
                        initial_capital=initial_capital,
                        commission_rate=commission_rate,
                        slippage_rate=slippage_rate,
                        t_plus_one=t_plus_one
                    )
                    
                    # 加载数据
                    start_str = start_date.strftime("%Y%m%d")
                    end_str = end_date.strftime("%Y%m%d")
                    
                    df = engine.load_historical_data(symbol, start_str, end_str)
                    
                    if df is not None and not df.empty:
                        # 生成信号
                        signals = engine.generate_signals(df, signal_type)
                        
                        # 运行回测
                        metrics = engine.backtest(symbol, df, signals, signal_type)
                        
                        # 显示绩效指标
                        st.success("✅ 回测完成！")
                        
                        # 核心指标
                        col_a, col_b, col_c, col_d = st.columns(4)
                        col_a.metric("总收益率", f"{metrics.total_return:.2%}")
                        col_b.metric("年化收益", f"{metrics.annual_return:.2%}")
                        col_c.metric("夏普比率", f"{metrics.sharpe_ratio:.4f}")
                        col_d.metric("最大回撤", f"{metrics.max_drawdown:.2%}")
                        
                        col_e, col_f, col_g, col_h = st.columns(4)
                        col_e.metric("胜率", f"{metrics.win_rate:.2%}")
                        col_f.metric("盈亏比", f"{metrics.profit_factor:.2f}")
                        col_g.metric("交易次数", metrics.total_trades)
                        col_h.metric("超额收益", f"{metrics.excess_return:.2%}")
                        
                        # 净值曲线
                        if len(engine.equity_curve) > 0:
                            fig = go.Figure()
                            
                            fig.add_trace(go.Scatter(
                                x=list(range(len(engine.equity_curve))),
                                y=engine.equity_curve,
                                mode='lines',
                                name='净值曲线',
                                line=dict(color='#FF6B6B', width=2)
                            ))
                            
                            # 添加基准线
                            benchmark_curve = [initial_capital * (1 + metrics.benchmark_return * (i / len(engine.equity_curve))) 
                                             for i in range(len(engine.equity_curve))]
                            fig.add_trace(go.Scatter(
                                x=list(range(len(engine.equity_curve))),
                                y=benchmark_curve,
                                mode='lines',
                                name='基准（买入持有）',
                                line=dict(color='#4ECDC4', width=2, dash='dash')
                            ))
                            
                            fig.update_layout(
                                title="净值曲线对比",
                                xaxis_title="交易日",
                                yaxis_title="净值",
                                height=400,
                                template="plotly_dark",
                                hovermode='x unified'
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # 交易记录
                        st.subheader("📝 交易记录")
                        trades_df = engine.get_trades_summary()
                        
                        if not trades_df.empty:
                            st.dataframe(
                                trades_df,
                                column_config={
                                    "trade_id": "交易ID",
                                    "symbol": "股票代码",
                                    "direction": "方向",
                                    "quantity": "数量",
                                    "price": st.column_config.NumberColumn("价格", format="¥%.2f"),
                                    "commission": st.column_config.NumberColumn("手续费", format="¥%.2f"),
                                    "pnl": st.column_config.NumberColumn("盈亏", format="¥%.2f")
                                },
                                use_container_width=True
                            )
                            
                            # 下载交易记录
                            csv = trades_df.to_csv(index=False)
                            st.download_button(
                                label="📥 下载交易记录",
                                data=csv,
                                file_name=f"backtest_trades_{symbol}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("回测期间无交易")
                        
                        # 详细分析
                        with st.expander("📊 详细分析"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**交易统计**")
                                st.write(f"- 总交易次数: {metrics.total_trades}")
                                st.write(f"- 盈利交易: {metrics.winning_trades}")
                                st.write(f"- 亏损交易: {metrics.losing_trades}")
                                st.write(f"- 平均持仓周期: {metrics.avg_holding_period:.1f} 天")
                            
                            with col2:
                                st.markdown("**盈亏分析**")
                                st.write(f"- 平均盈利: ¥{metrics.avg_win:.2f}")
                                st.write(f"- 平均亏损: ¥{metrics.avg_loss:.2f}")
                                st.write(f"- 盈亏比: {metrics.profit_factor:.2f}")
                                st.write(f"- 初始资金: ¥{metrics.initial_capital:,.2f}")
                                st.write(f"- 最终资金: ¥{metrics.final_capital:,.2f}")
                    else:
                        st.error("无法获取历史数据，请检查日期范围和股票代码")
                
                except Exception as e:
                    st.error(f"回测失败: {str(e)}")
    
    with col2:
        st.subheader("📈 策略对比")
        
        # 模拟策略对比
        strategies = [
            {"策略": "MA交叉", "收益率": "15.2%", "夏普": "1.25", "回撤": "-12.5%"},
            {"策略": "MACD", "收益率": "18.7%", "夏普": "1.42", "回撤": "-15.3%"},
            {"策略": "RSI", "收益率": "12.3%", "夏普": "0.98", "回撤": "-10.8%"},
            {"策略": "LSTM", "收益率": "22.5%", "夏普": "1.68", "回撤": "-14.2%"},
        ]
        
        for strategy in strategies:
            with st.container():
                st.markdown(f"**{strategy['策略']}**")
                cols = st.columns(3)
                cols[0].metric("收益", strategy['收益率'])
                cols[1].metric("夏普", strategy['夏普'])
                cols[2].metric("回撤", strategy['回撤'])
                st.divider()
        
        st.markdown("---")
        st.subheader("💡 回测建议")
        st.info("""
        1. 建议至少使用1年历史数据
        2. 测试不同参数组合
        3. 关注最大回撤和夏普比率
        4. 避免过度拟合
        5. 实盘前进行充分验证
        """)