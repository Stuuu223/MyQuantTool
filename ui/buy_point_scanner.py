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
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 扫描配置")
        
        scan_type = st.selectbox(
            "扫描类型",
            ["全市场", "自选股", "板块"],
            help="选择扫描范围",
            key="buy_point_scan_type"
        )
        
        signal_score_threshold = st.slider(
            "信号评分阈值",
            0, 100, 60,
            help="信号评分低于此值将被过滤"
        )
        
        risk_tolerance = st.selectbox(
            "风险容忍度",
            ["低", "中", "高"],
            help="选择可接受的风险等级",
            key="buy_point_risk_tolerance"
        )
        
        tech_indicators = st.multiselect(
            "关注的技术指标",
            ["RSI", "MACD", "KDJ", "均线", "成交量"],
            default=["RSI", "MACD", "均线"]
        )
        
        st.markdown("---")
        st.subheader("💡 扫描逻辑")
        st.info("""
        **扫描类型说明**：
        
        1. **突破买点**：股价向上突破关键技术位置
        2. **回调买点**：股价回调到支撑位附近
        3. **金叉买点**：技术指标出现金叉信号
        4. **背离买点**：价格与指标出现底背离
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🎯 扫描结果")
        
        # 执行扫描
        if st.button("🔄 开始扫描", key="scan_buy_points"):
            with st.spinner('正在扫描买点信号...'):
                try:
                    scanner = BuyPointScanner(db=db)
                    
                    # 根据扫描类型获取股票列表
                    if scan_type == "全市场":
                        stock_list = None  # None表示全市场
                    elif scan_type == "自选股":
                        # 这里应该从用户配置中获取自选股列表
                        stock_list = ['000001', '000002', '600000', '600036']  # 示例
                    else:  # 板块
                        # 这里应该根据板块获取股票列表
                        stock_list = ['000001', '000002']  # 示例
                    
                    # 执行扫描
                    signals = scanner.scan_buy_signals(stock_list=stock_list)
                    
                    # 过滤信号
                    filtered_signals = [s for s in signals if 
                                      s.signal_score >= signal_score_threshold and
                                      (risk_tolerance == "高" or s.risk_level in ["低", "中"][:["低", "中", "高"].index(risk_tolerance)+1])]
                    
                    if filtered_signals:
                        st.success(f"✅ 发现 {len(filtered_signals)} 个买点信号")
                        
                        # 显示信号列表
                        signal_df = pd.DataFrame([{
                            '股票代码': s.stock_code,
                            '股票名称': s.stock_name,
                            '信号类型': s.signal_type,
                            '扫描日期': s.scan_date,
                            '入场价': f"¥{s.entry_price:.2f}",
                            '止损价': f"¥{s.stop_loss:.2f}",
                            '目标价': f"¥{s.target_price:.2f}",
                            '信号评分': s.signal_score,
                            '风险等级': s.risk_level
                        } for s in filtered_signals])
                        
                        st.dataframe(
                            signal_df,
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
    
    with col2:
        st.subheader("🎯 扫描策略")
        
        st.info("""
        **突破策略**：
        - 向上突破关键技术位
        - 成交量确认
        - 动量指标支持
        """)
        
        st.markdown("---")
        st.subheader("🎯 回调策略")
        
        st.info("""
        **回调策略**：
        - 价格回调至支撑位
        - RSI超卖回升
        - 量缩价稳
        """)
        
        st.markdown("---")
        st.subheader("🎯 金叉策略")
        
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