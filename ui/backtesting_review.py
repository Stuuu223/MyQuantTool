"""复盘助手UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.backtesting_review import BacktestingReview, ReviewReport, TradeRecord
from logic.backtest_engine import BacktestMetrics
from logic.formatter import Formatter  # 假设存在格式化工具类
import json


def render_backtesting_review_tab(db, config):
    """渲染复盘助手标签页"""
    
    st.subheader("📋 智能复盘助手")
    st.caption("自动生成回测报告，分析策略优缺点，提供改进建议")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 复盘配置")
        
        strategy_name = st.text_input("策略名称", "示例策略", help="要复盘的策略名称")
        
        start_date = st.date_input("回测开始日期", value=pd.to_datetime("2023-01-01").date())
        end_date = st.date_input("回测结束日期", value=pd.to_datetime("2024-12-31").date())
        
        backtest_id = st.text_input("回测ID（可选）", help="指定特定回测进行复盘")
        
        st.markdown("---")
        st.subheader("💡 复盘内容")
        st.info("""
        **复盘包含**：
        - 收益分析
        - 风险评估
        - 交易行为分析
        - 策略改进建议
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 复盘报告")
        
        # 执行复盘
        if st.button("🔍 生成复盘报告", key="generate_review"):
            with st.spinner('正在生成复盘报告...'):
                try:
                    # 创建复盘助手
                    reviewer = BacktestingReview()
                    
                    # 这里需要获取实际的交易记录和回测指标
                    # 为了演示，我们创建一些示例数据
                    # 在实际应用中，这里应该从数据库或回测引擎获取真实的交易记录
                    trade_records = _generate_sample_trades()
                    metrics = _generate_sample_metrics()
                    
                    # 生成复盘报告
                    report = reviewer.generate_review_report(
                        trade_records=trade_records,
                        metrics=metrics,
                        strategy_name=strategy_name,
                        backtest_period=(str(start_date), str(end_date))
                    )
                    
                    # 显示报告摘要
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("总收益率", f"{report.total_return:.2%}")
                    with col_b:
                        st.metric("年化收益率", f"{report.annual_return:.2%}")
                    with col_c:
                        st.metric("夏普比率", f"{report.sharpe_ratio:.2f}")
                    with col_d:
                        st.metric("最大回撤", f"{report.max_drawdown:.2%}")
                    
                    col_e, col_f, col_g, col_h = st.columns(4)
                    with col_e:
                        st.metric("胜率", f"{report.win_rate:.2%}")
                    with col_f:
                        st.metric("盈亏比", f"{report.profit_factor:.2f}")
                    with col_g:
                        st.metric("总交易数", report.total_trades)
                    with col_h:
                        st.metric("盈利交易", report.winning_trades)
                    
                    st.markdown("---")
                    
                    # 显示关键见解
                    st.subheader("💡 关键见解")
                    for insight in report.key_insights:
                        st.info(insight)
                    
                    st.markdown("---")
                    
                    # 显示改进建议
                    st.subheader("🔧 改进建议")
                    for suggestion in report.improvement_suggestions:
                        st.warning(suggestion)
                    
                    st.markdown("---")
                    
                    # 显示交易分析
                    st.subheader("📈 交易分析")
                    if report.trade_analysis:
                        trade_analysis = report.trade_analysis
                        
                        # 显示交易统计
                        stats_cols = st.columns(3)
                        with stats_cols[0]:
                            st.metric("总盈亏", f"¥{trade_analysis['total_pnl']:,.2f}")
                            st.metric("平均盈亏", f"¥{trade_analysis['avg_pnl']:,.2f}")
                        with stats_cols[1]:
                            st.metric("最大盈利", f"¥{trade_analysis['max_profit']:,.2f}")
                            st.metric("最大亏损", f"¥{trade_analysis['max_loss']:,.2f}")
                        with stats_cols[2]:
                            st.metric("胜率", f"{trade_analysis['win_rate']:.2%}")
                            st.metric("盈亏比", f"{abs(trade_analysis['avg_win']/trade_analysis['avg_loss']):.2f}" if trade_analysis['avg_loss'] != 0 else "N/A")
                        
                        # 显示连续盈亏情况
                        if 'consecutive_analysis' in trade_analysis:
                            consec_cols = st.columns(2)
                            with consec_cols[0]:
                                st.metric("最大连盈", trade_analysis['consecutive_analysis']['max_consecutive_wins'])
                            with consec_cols[1]:
                                st.metric("最大连亏", trade_analysis['consecutive_analysis']['max_consecutive_losses'])
                    
                    st.markdown("---")
                    
                    # 显示性能图表
                    st.subheader("📈 性能图表")
                    if report.performance_chart:
                        st.plotly_chart(report.performance_chart, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # 显示风险分析
                    st.subheader("⚠️ 风险分析")
                    if report.risk_analysis:
                        risk_analysis = report.risk_analysis
                        
                        risk_cols = st.columns(3)
                        with risk_cols[0]:
                            st.metric("年化波动率", f"{risk_analysis['volatility']:.2%}")
                            st.metric("下行标准差", f"{risk_analysis['downside_deviation']:.2%}")
                        with risk_cols[1]:
                            st.metric("索提诺比率", f"{risk_analysis['sortino_ratio']:.2f}")
                            st.metric("95% VaR", f"{risk_analysis['var_95']:.2%}")
                        with risk_cols[2]:
                            st.metric("最大单笔损失", f"¥{risk_analysis['max_single_loss']:,.2f}")
                            st.metric("期望不足", f"{risk_analysis['expected_shortfall_95']:.2%}")
                        
                        st.write(f"**风险总结**: {risk_analysis['risk_summary']}")
                    
                except Exception as e:
                    st.error(f"❌ 生成复盘报告失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    with col2:
        st.subheader("🎯 复盘流程")
        
        st.info("""
        **1. 数据准备**：
        - 交易记录
        - 回测指标
        - 市场数据
        """)
        
        st.markdown("---")
        st.subheader("🔍 分析维度")
        
        st.info("""
        **2. 多维度分析**：
        - 收益分析
        - 风险评估
        - 交易行为
        - 策略优化
        """)
        
        st.markdown("---")
        st.subheader("📋 生成报告")
        
        st.success("""
        **3. 智能报告**：
        - 关键见解
        - 改进建议
        - 可视化图表
        """)
        
        st.markdown("---")
        st.subheader("💡 优化建议")
        
        st.warning("""
        1. 策略参数优化
        2. 风险管理改进
        3. 交易时机选择
        4. 资金配置优化
        """)


def _generate_sample_trades() -> list:
    """生成示例交易记录（实际应用中应从数据库获取真实数据）"""
    import random
    from datetime import datetime, timedelta
    
    trades = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(50):  # 生成50笔交易
        date = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d')  # 每隔3天一笔交易
        stock_code = f"000{random.randint(1, 999):03d}"
        stock_name = f"股票_{stock_code}"
        action = "BUY" if i % 2 == 0 else "SELL"  # 买入卖出交替
        price = 10 + random.uniform(-2, 5)  # 价格在8-15之间
        quantity = 1000
        amount = price * quantity
        pnl = (random.random() - 0.4) * amount * 0.02  # 随机盈亏，略偏向盈利
        pnl_ratio = pnl / amount
        
        trades.append(TradeRecord(
            date=date,
            stock_code=stock_code,
            stock_name=stock_name,
            action=action,
            price=price,
            quantity=quantity,
            amount=amount,
            pnl=pnl,
            pnl_ratio=pnl_ratio,
            strategy="示例策略"
        ))
    
    return trades


def _generate_sample_metrics() -> BacktestMetrics:
    """生成示例回测指标（实际应用中应从回测引擎获取真实数据）"""
    return BacktestMetrics(
        initial_capital=100000.0,
        final_capital=125000.0,
        total_return=0.25,  # 25%总收益
        annual_return=0.15,  # 15%年化收益
        sharpe_ratio=1.2,    # 夏普比率
        max_drawdown=-0.08,  # 8%最大回撤
        max_drawdown_duration=15,  # 最大回撤持续时间
        win_rate=0.62,       # 62%胜率
        profit_factor=1.8,   # 1.8盈亏比
        avg_win=1200.0,      # 平均盈利
        avg_loss=-800.0,     # 平均亏损
        total_trades=50,     # 总交易数
        winning_trades=31,   # 盈利交易数
        losing_trades=19,    # 亏损交易数
        avg_holding_period=5.0,  # 平均持仓周期
        benchmark_return=0.10,   # 基准收益
        excess_return=0.05     # 超额收益
    )