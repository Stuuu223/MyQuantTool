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

    st.subheader("📋 A股市场复盘")
    st.caption("自动生成市场复盘报告，分析市场走势、热点板块、资金流向")
    st.markdown("---")

    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 复盘配置")

        review_date = st.date_input("复盘日期", value=pd.to_datetime("today").date(), help="选择要复盘的日期")

        st.markdown("---")
        st.subheader("💡 复盘内容")
        st.info("""
        **复盘包含**：
        - 市场整体表现
        - 热点板块分析
        - 涨跌停统计
        - 资金流向分析
        - 龙虎榜分析
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📊 市场复盘报告")

        # 执行复盘
        if st.button("🔍 生成市场复盘", key="generate_review"):
            with st.spinner('正在生成市场复盘报告...'):
                try:
                    import akshare as ak
                    from logic.algo_sentiment import MarketSentimentAnalyzer
                    from logic.sector_rotation_analyzer import get_sector_rotation_analyzer

                    date_str = review_date.strftime("%Y%m%d")

                    # 获取市场数据
                    sentiment_analyzer = MarketSentimentAnalyzer()
                    sector_analyzer = get_sector_rotation_analyzer(history_days=30)

                    # 1. 市场整体表现
                    st.subheader("📈 市场整体表现")

                    # 获取主要指数数据
                    try:
                        index_data = ak.stock_zh_index_spot_em()
                        major_indices = index_data[index_data['代码'].isin(['000001', '399001', '399006'])]
                        major_indices = major_indices[['名称', '最新价', '涨跌幅', '成交量', '成交额']]

                        for _, row in major_indices.iterrows():
                            change_color = "📈" if row['涨跌幅'] > 0 else "📉" if row['涨跌幅'] < 0 else "➡️"
                            st.metric(
                                f"{change_color} {row['名称']}",
                                f"{row['最新价']:.2f}",
                                f"{row['涨跌幅']:+.2f}%"
                            )
                    except Exception as e:
                        st.warning(f"获取指数数据失败: {e}")

                    st.markdown("---")

                    # 2. 涨跌停统计
                    st.subheader("🎯 涨跌停统计")

                    try:
                        limit_up_data = ak.stock_zt_pool_em(date=date_str)
                        limit_down_data = ak.stock_dt_pool_em(date=date_str)

                        col_zt, col_dt = st.columns(2)
                        with col_zt:
                            st.metric("涨停数量", len(limit_up_data))
                            if not limit_up_data.empty:
                                st.write("**涨停TOP5**:")
                                top5_zt = limit_up_data.head(5)
                                for _, row in top5_zt.iterrows():
                                    st.write(f"• {row['名称']} ({row['代码']}) {row['涨跌幅']:+.2f}%")

                        with col_dt:
                            st.metric("跌停数量", len(limit_down_data))
                            if not limit_down_data.empty:
                                st.write("**跌停TOP5**:")
                                top5_dt = limit_down_data.head(5)
                                for _, row in top5_dt.iterrows():
                                    st.write(f"• {row['名称']} ({row['代码']}) {row['涨跌幅']:+.2f}%")
                    except Exception as e:
                        st.warning(f"获取涨跌停数据失败: {e}")

                    st.markdown("---")

                    # 3. 热点板块分析
                    st.subheader("🔥 热点板块分析")

                    try:
                        sector_strength = sector_analyzer.calculate_sector_strength(date_str)

                        if sector_strength:
                            # 转换为DataFrame并排序
                            sector_df = pd.DataFrame([
                                {
                                    '板块': sector,
                                    '综合评分': strength.total_score,
                                    '涨幅因子': strength.price_score,
                                    '资金因子': strength.capital_score,
                                    '轮动阶段': strength.phase.value
                                }
                                for sector, strength in sector_strength.items()
                            ])
                            sector_df = sector_df.sort_values('综合评分', ascending=False)

                            # 显示TOP10板块
                            st.dataframe(
                                sector_df.head(10),
                                use_container_width=True,
                                hide_index=True
                            )

                            # 板块强度图表
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=sector_df['板块'].head(10),
                                y=sector_df['综合评分'].head(10),
                                marker_color=sector_df['综合评分'].head(10).apply(
                                    lambda x: '#00C853' if x >= 70 else '#FFC107' if x >= 50 else '#FF5252'
                                ),
                                text=sector_df['综合评分'].head(10).apply(lambda x: f'{x:.1f}'),
                                textposition='auto',
                            ))
                            fig.update_layout(
                                title='板块强度TOP10',
                                xaxis_title='板块',
                                yaxis_title='综合评分',
                                yaxis_range=[0, 100],
                                height=500
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("暂无板块数据")
                    except Exception as e:
                        st.warning(f"获取板块数据失败: {e}")

                    st.markdown("---")

                    # 4. 龙虎榜分析
                    st.subheader("🏆 龙虎榜分析")

                    try:
                        lhb_data = ak.stock_lhb_detail_em(date=date_str)

                        if not lhb_data.empty:
                            # 统计上榜次数
                            stock_counts = lhb_data['代码'].value_counts().head(10)

                            st.write("**上榜次数TOP10**:")
                            for code, count in stock_counts.items():
                                stock_name = lhb_data[lhb_data['代码'] == code]['名称'].iloc[0]
                                st.write(f"• {stock_name} ({code}) - 上榜{count}次")

                            # 净买入统计
                            if '净买入' in lhb_data.columns:
                                net_buy = lhb_data.groupby('代码')['净买入'].sum().sort_values(ascending=False).head(10)

                                st.write("**净买入TOP10**:")
                                for code, amount in net_buy.items():
                                    stock_name = lhb_data[lhb_data['代码'] == code]['名称'].iloc[0]
                                    st.write(f"• {stock_name} ({code}) - ¥{amount:,.0f}")
                        else:
                            st.info("当日无龙虎榜数据")
                    except Exception as e:
                        st.warning(f"获取龙虎榜数据失败: {e}")

                    st.markdown("---")

                    # 5. 市场情绪
                    st.subheader("😊 市场情绪")

                    try:
                        sentiment_data = sentiment_analyzer.get_market_sentiment_index()

                        if sentiment_data['数据状态'] == '正常':
                            col_sentiment = st.columns(3)
                            with col_sentiment[0]:
                                st.metric("情绪指数", f"{sentiment_data['情绪指数']:.1f}")
                            with col_sentiment[1]:
                                st.metric("涨停数量", sentiment_data['涨停数量'])
                            with col_sentiment[2]:
                                st.metric("跌停数量", sentiment_data['跌停数量'])

                            st.write(f"**市场阶段**: {sentiment_data['市场阶段']}")
                            st.write(f"**情绪描述**: {sentiment_data['情绪描述']}")
                        else:
                            st.info("暂无情绪数据")
                    except Exception as e:
                        st.warning(f"获取情绪数据失败: {e}")

                except Exception as e:
                    st.error(f"❌ 生成市场复盘失败: {str(e)}")
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