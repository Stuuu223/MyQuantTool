"""买点扫描器UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.buy_point_scanner import BuyPointScanner, BuySignal
from logic.formatter import Formatter  # 假设存在格式化工具类


def render_buy_point_scanner_tab(db, config):
    """渲染买点扫描器标签页"""
    
    st.subheader("🔍 买点扫描器")
    st.caption("实时扫描符合买点条件的股票")
    st.markdown("---")
    
    # 主内容区 - 配置面板
    with st.expander("⚙️ 扫描配置", expanded=True):
        col_config1, col_config2, col_config3 = st.columns(3)
        
        with col_config1:
            scan_type = st.selectbox(
                "扫描类型",
                ["全市场", "自选股", "板块"],
                help="选择扫描范围",
                key="buy_point_scan_type"
            )
            
            stock_count = st.slider(
                "扫描股票数量",
                min_value=10,
                max_value=200,
                value=100,
                step=10,
                help="全市场扫描时，按成交量排序选择前N只最活跃的股票"
            )
        
        with col_config2:
            signal_score_threshold = st.slider(
                "信号评分阈值",
                0, 100, 60,
                help="信号评分低于此值将被过滤（建议值：40-60）"
            )
            
            risk_tolerance = st.selectbox(
                "风险容忍度",
                ["低", "中", "高"],
                help="选择可接受的风险等级",
                key="buy_point_risk_tolerance"
            )
        
        with col_config3:
            lookback_days = st.slider(
                "回看天数",
                min_value=20,
                max_value=120,
                value=60,
                step=10,
                help="分析历史数据的天数范围（建议值：30-60天）"
            )
            
            tech_indicators = st.multiselect(
                "关注的技术指标",
                ["RSI", "MACD", "KDJ", "均线", "成交量"],
                default=["RSI", "MACD", "均线"]
            )
    
    # 主内容区 - 扫描结果
    st.subheader("🎯 扫描结果")
    
    # 执行扫描
    if st.button("🔄 开始扫描", key="scan_buy_points"):
        with st.spinner('正在扫描买点信号...'):
            try:
                scanner = BuyPointScanner(db=db)
                
                # 根据扫描类型获取股票列表
                import akshare as ak
                if scan_type == "全市场":
                    stock_list_df = ak.stock_zh_a_spot_em()
                    # 按成交量排序，取成交量最大的N只股票（活跃股票）
                    if '成交量' in stock_list_df.columns:
                        stock_list_df = stock_list_df.sort_values('成交量', ascending=False)
                    elif '成交额' in stock_list_df.columns:
                        stock_list_df = stock_list_df.sort_values('成交额', ascending=False)
                    stock_list = stock_list_df['代码'].tolist()[:stock_count]
                elif scan_type == "自选股":
                    # 这里应该从用户配置中获取自选股列表
                    # 暂时使用成交量最大的50只股票作为示例
                    stock_list_df = ak.stock_zh_a_spot_em()
                    if '成交量' in stock_list_df.columns:
                        stock_list_df = stock_list_df.sort_values('成交量', ascending=False)
                    elif '成交额' in stock_list_df.columns:
                        stock_list_df = stock_list_df.sort_values('成交额', ascending=False)
                    stock_list = stock_list_df['代码'].tolist()[:50]
                else:  # 板块
                    # 这里应该根据板块获取股票列表
                    # 暂时使用行业板块数据
                    import akshare as ak
                    sector_df = ak.stock_board_industry_name_em()
                    if not sector_df.empty:
                        # 获取第一个板块的成分股
                        sector_code = sector_df.iloc[0, 2]  # 板块代码列
                        constituents_df = ak.stock_board_industry_cons_em(symbol=sector_code)
                        if not constituents_df.empty:
                            stock_list = constituents_df['代码'].tolist()[:50]
                        else:
                            stock_list = None
                    else:
                        stock_list = None
                
                # 执行扫描
                signals = scanner.scan_buy_signals(stock_list=stock_list, stock_info=stock_info)
                
                # 过滤信号
                filtered_signals = [s for s in signals if 
                                  s.signal_score >= signal_score_threshold and
                                  (risk_tolerance == "高" or s.risk_level in ["低", "中"][:["低", "中", "高"].index(risk_tolerance)+1])]
                
                if filtered_signals:
                    st.success(f"✅ 发现 {len(filtered_signals)} 个买点信号")

                    # 获取今日涨跌幅
                    import akshare as ak
                    stock_spot_df = ak.stock_zh_a_spot_em()
                    stock_spot_dict = dict(zip(stock_spot_df['代码'], stock_spot_df['涨跌幅']))

                    # 显示信号列表
                    signal_df = pd.DataFrame([{
                        '股票代码': s.stock_code,
                        '股票名称': s.stock_name,
                        '信号类型': s.signal_type,
                        '今日涨跌幅': f"{stock_spot_dict.get(s.stock_code, 0):.2f}%",
                        '入场价': f"¥{s.entry_price:.2f}",
                        '止损价': f"¥{s.stop_loss:.2f}",
                        '目标价': f"¥{s.target_price:.2f}",
                        '信号评分': s.signal_score,
                        '风险等级': s.risk_level
                    } for s in filtered_signals])

                    # 根据涨跌幅设置颜色
                    def highlight_change(val):
                        if isinstance(val, str) and '%' in val:
                            change = float(val.replace('%', ''))
                            if change > 0:
                                return 'color: red'
                            elif change < 0:
                                return 'color: green'
                        return ''

                    # 应用样式
                    styled_df = signal_df.style.applymap(highlight_change, subset=['今日涨跌幅'])

                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 详细分析
                    for i, signal in enumerate(filtered_signals[:5], 1):
                        with st.expander(f"#{i} {signal.stock_name} ({signal.stock_code}) - {signal.signal_type}"):
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("入场价", f"¥{signal.entry_price:.2f}")
                            with col_b:
                                st.metric("止损价", f"¥{signal.stop_loss:.2f}")
                            with col_c:
                                st.metric("目标价", f"¥{signal.target_price:.2f}")
                            
                            col_d, col_e, col_f = st.columns(3)
                            with col_d:
                                st.metric("信号评分", f"{signal.signal_score}/100")
                            with col_e:
                                st.metric("风险等级", signal.risk_level)
                            with col_f:
                                profit_ratio = (signal.target_price - signal.entry_price) / signal.entry_price * 100
                                st.metric("预期收益", f"{profit_ratio:.1f}%")
                            
                            st.write("**信号理由**:")
                            for reason in signal.reasons:
                                st.write(f"- {reason}")
                            
                            # 显示关键技术指标
                            if signal.technical_indicators:
                                st.write("**关键技术指标**:")
                                indicators_cols = st.columns(min(3, len(signal.technical_indicators)))
                                for idx, (indicator, value) in enumerate(signal.technical_indicators.items()):
                                    with indicators_cols[idx % len(indicators_cols)]:
                                        if isinstance(value, float):
                                            st.metric(indicator.upper(), f"{value:.2f}")
                                        else:
                                            st.metric(indicator.upper(), str(value))
                            
                            # 如果需要，可以添加图表显示
                            # fig = _plot_signal_chart(signal)
                            # st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.info("🔍 未发现符合条件的买点信号")
                    
            except Exception as e:
                st.error(f"❌ 扫描失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏 - 策略说明
    with st.sidebar:
        st.markdown("---")
        st.subheader("📖 扫描策略")
        
        st.info("""
        **突破策略**：
        - 向上突破关键技术位
        - 成交量确认
        - 动量指标支持
        """)
        
        st.markdown("---")
        st.subheader("📖 回调策略")
        
        st.info("""
        **回调策略**：
        - 价格回调至支撑位
        - RSI超卖回升
        - 量缩价稳
        """)
        
        st.markdown("---")
        st.subheader("📖 金叉策略")
        
        st.info("""
        **金叉策略**：
        - MACD或KDJ金叉
        - RSI位置适中
        - 成交量配合
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 风险提醒")
        
        st.warning("""
        1. 市场整体趋势
        2. 个股基本面
        3. 消息面影响
        4. 严格资金管理
        """)
        

def _plot_signal_chart(signal: BuySignal):
    """绘制信号图表（示例）"""
    # 这里可以实现具体的图表绘制逻辑
    # 由于我们没有实际的数据，创建一个示例图表
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=[1, 2, 3, 4, 5], 
        y=[signal.entry_price, signal.entry_price*1.02, signal.entry_price*0.99, signal.target_price, signal.entry_price*1.01],
        mode='lines+markers',
        name='价格走势'
    ))
    
    fig.add_hline(y=signal.entry_price, line_dash="dash", line_color="green", annotation_text="入场价")
    fig.add_hline(y=signal.stop_loss, line_dash="dash", line_color="red", annotation_text="止损价")
    fig.add_hline(y=signal.target_price, line_dash="dash", line_color="blue", annotation_text="目标价")
    
    fig.update_layout(
        title=f"{signal.stock_name} ({signal.stock_code}) - {signal.signal_type}",
        height=400,
        xaxis_title="时间",
        yaxis_title="价格",
        showlegend=True
    )
    
    return fig