"""半路战法UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.midway_strategy import MidwayStrategyAnalyzer, MidwaySignal
from logic.data_source_manager import DataSourceManager
from logic.formatter import Formatter  # 假设存在格式化工具类


def render_midway_strategy_tab(db, config):
    """渲染半路战法标签页"""
    
    st.subheader("🎯 半路战法")
    st.caption("识别个股在上涨过程中的回调买点")
    st.markdown("---")
    
    # 主内容区 - 配置面板
    with st.expander("⚙️ 策略配置", expanded=True):
        col_config1, col_config2, col_config3 = st.columns(3)
        
        with col_config1:
            stock_count = st.slider(
                "扫描股票数量",
                min_value=10,
                max_value=200,
                value=50,
                step=10,
                help="按成交量排序选择前N只最活跃的股票进行扫描"
            )
        
        with col_config2:
            lookback_days = st.slider(
                "回看天数",
                min_value=20,
                max_value=120,
                value=30,
                step=10,
                help="分析历史数据的天数范围（建议值：30-60天）"
            )
            
            signal_strength_threshold = st.slider(
                "信号强度阈值",
                0.0, 1.0, 0.6,
                step=0.1,
                help="信号强度低于此值将被过滤（建议值：0.4-0.6）"
            )
        
        with col_config3:
            risk_tolerance = st.selectbox(
                "风险容忍度",
                ["低", "中", "高"],
                help="选择可接受的风险等级",
                key="midway_strategy_risk_tolerance"
            )
    
    # 主内容区 - 扫描结果
    st.subheader("📊 半路战法信号")

    # 添加调试模式开关
    debug_mode = st.checkbox("调试模式（显示详细日志）", value=False, key="midway_debug_mode")

    # 获取股票数据并分析
    if st.button("🔍 扫描半路战法机会", key="scan_midway"):
        with st.spinner('正在扫描半路战法机会...'):
            try:
                # 获取全市场数据（简化实现，实际应从数据库获取）
                analyzer = MidwayStrategyAnalyzer(lookback_days=lookback_days)
                
                # 获取全市场股票列表
                import akshare as ak
                stock_list_df = ak.stock_zh_a_spot_em()
                
                # 按成交量排序，取成交量最大的N只股票（活跃股票）
                if '成交量' in stock_list_df.columns:
                    stock_list_df = stock_list_df.sort_values('成交量', ascending=False)
                elif '成交额' in stock_list_df.columns:
                    stock_list_df = stock_list_df.sort_values('成交额', ascending=False)
                
                stock_codes = stock_list_df['代码'].tolist()[:stock_count]  # 取成交量最大的N只
                
                # 创建数据管理器
                data_manager = DataSourceManager(db)
                
                # 获取股票数据
                stock_data = {}
                stock_info = {}

                if debug_mode:
                    st.info(f"[调试] 开始获取 {len(stock_codes)} 只股票的数据...")

                for idx, code in enumerate(stock_codes):
                    # 获取最近lookback_days天的数据
                    import datetime
                    end_date = datetime.datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.datetime.now() - datetime.timedelta(days=lookback_days + 10)).strftime('%Y%m%d')  # 多取10天确保有足够数据

                    df = data_manager.get_stock_data(code, start_date, end_date)
                    if df is not None and len(df) >= 20:  # 降低要求到20天
                        stock_data[code] = df
                        # 从股票列表中获取真实股票名称
                        stock_name = stock_list_df[stock_list_df['代码'] == code]['名称'].values[0] if code in stock_list_df['代码'].values else f"股票{code}"
                        stock_info[code] = stock_name

                        if debug_mode and idx < 5:  # 只打印前5个
                            st.text(f"[调试] {code} - {stock_name}, 数据行数: {len(df)}")
                    else:
                        if debug_mode and idx < 5:  # 只打印前5个
                            st.text(f"[调试] {code} - 数据不足或为空 (len={len(df) if df is not None else 0})")

                if debug_mode:
                    st.info(f"[调试] 成功获取 {len(stock_data)} 只股票的数据")
                
                # 扫描半路战法信号
                if debug_mode:
                    st.info(f"[调试] 开始扫描 {len(stock_data)} 只股票...")

                signals = analyzer.scan_midway_opportunities(stock_data, stock_info)

                if debug_mode:
                    st.info(f"[调试] 扫描完成，发现 {len(signals)} 个原始信号")

                # 过滤信号
                if debug_mode:
                    st.info(f"[调试] 开始过滤信号...")
                    st.text(f"[调试] 信号强度阈值: {signal_strength_threshold}")
                    st.text(f"[调试] 风险容忍度: {risk_tolerance}")

                filtered_signals = []
                for s in signals:
                    # 检查信号强度
                    if s.signal_strength < signal_strength_threshold:
                        if debug_mode:
                            st.text(f"[调试] {s.stock_code} - 信号强度不足: {s.signal_strength:.2f}")
                        continue

                    # 检查风险等级
                    if risk_tolerance == "低" and s.risk_level != "低":
                        if debug_mode:
                            st.text(f"[调试] {s.stock_code} - 风险等级不符合: {s.risk_level}")
                        continue
                    elif risk_tolerance == "中" and s.risk_level == "高":
                        if debug_mode:
                            st.text(f"[调试] {s.stock_code} - 风险等级不符合: {s.risk_level}")
                        continue
                    # "高" 风险容忍度接受所有风险等级

                    filtered_signals.append(s)
                    if debug_mode:
                        st.text(f"[调试] {s.stock_code} - 通过过滤: 强度={s.signal_strength:.2f}, 风险={s.risk_level}")

                if debug_mode:
                    st.info(f"[调试] 过滤完成，保留 {len(filtered_signals)} 个信号")
                filtered_signals = []
                for s in signals:
                    # 检查信号强度
                    if s.signal_strength < signal_strength_threshold:
                        continue

                    # 检查风险等级
                    if risk_tolerance == "低" and s.risk_level != "低":
                        continue
                    elif risk_tolerance == "中" and s.risk_level == "高":
                        continue
                    # "高" 风险容忍度接受所有风险等级

                    filtered_signals.append(s)
                
                if filtered_signals:
                    st.success(f"✅ 发现 {len(filtered_signals)} 个半路战法信号")
                    
                    # 显示信号列表
                    signal_df = pd.DataFrame([{
                        '股票代码': s.stock_code,
                        '股票名称': s.stock_name,
                        '信号日期': s.signal_date,
                        '入场价': f"¥{s.entry_price:.2f}",
                        '止损价': f"¥{s.stop_loss:.2f}",
                        '目标价': f"¥{s.target_price:.2f}",
                        '信号强度': f"{s.signal_strength:.2f}",
                        '风险等级': s.risk_level,
                        '置信度': f"{s.confidence:.2f}"
                    } for s in filtered_signals])
                    
                    st.dataframe(
                        signal_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 详细分析
                    for i, signal in enumerate(filtered_signals[:5], 1):
                        with st.expander(f"#{i} {signal.stock_name} ({signal.stock_code}) - 信号强度: {signal.signal_strength:.2f}"):
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("入场价", f"¥{signal.entry_price:.2f}")
                            with col_b:
                                st.metric("止损价", f"¥{signal.stop_loss:.2f}")
                            with col_c:
                                st.metric("目标价", f"¥{signal.target_price:.2f}")
                            
                            st.write(f"**风险等级**: {signal.risk_level}")
                            st.write(f"**置信度**: {signal.confidence:.2f}")
                            
                            st.write("**信号理由**:")
                            for reason in signal.reasons:
                                st.write(f"- {reason}")
                            
                            # 绘制K线图
                            if signal.stock_code in stock_data:
                                fig = _plot_kline_with_signal(stock_data[signal.stock_code], signal)
                                st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.info("👍 未发现符合条件的半路战法信号")
                    
            except Exception as e:
                st.error(f"❌ 扫描失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏 - 战术说明
    with st.sidebar:
        st.markdown("---")
        st.subheader("📖 战术要点")
        
        st.info("""
        **入场条件**：
        - 股价突破后回调
        - 接近重要支撑位
        - 成交量萎缩后放大
        - RSI未超买
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 风险提醒")
        
        st.warning("""
        1. 市场趋势变化
        2. 消息面影响
        3. 个股基本面变化
        4. 严格止损纪律
        """)
        
        st.markdown("---")
        st.subheader("📈 成功要素")
        
        st.success("""
        1. 精准的支撑位判断
        2. 量价关系确认
        3. 市场情绪配合
        4. 风险控制严格
        """)


def _plot_kline_with_signal(df, signal: MidwaySignal):
    """绘制带信号的K线图"""
    fig = go.Figure()
    
    # 添加K线
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线'
    ))
    
    # 添加移动平均线
    if 'ma5' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma5'], mode='lines', name='MA5', line=dict(color='orange', width=1)
        ))
    if 'ma10' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma10'], mode='lines', name='MA10', line=dict(color='blue', width=1)
        ))
    if 'ma20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma20'], mode='lines', name='MA20', line=dict(color='purple', width=1)
        ))
    
    # 添加信号点
    signal_date_idx = df.index[df['date'] == signal.signal_date] if 'date' in df.columns else [df.index[-1]]
    if len(signal_date_idx) > 0:
        signal_date = signal_date_idx[0]
        fig.add_trace(go.Scatter(
            x=[signal_date], y=[df.loc[signal_date, 'close']] if signal_date in df.index else [signal.entry_price],
            mode='markers', name='半路战法信号', marker=dict(symbol='star', size=15, color='red')
        ))
    
    # 添加入场价、止损价、目标价线
    fig.add_hline(y=signal.entry_price, line_dash="dash", line_color="green", annotation_text="入场价")
    fig.add_hline(y=signal.stop_loss, line_dash="dash", line_color="red", annotation_text="止损价")
    fig.add_hline(y=signal.target_price, line_dash="dash", line_color="blue", annotation_text="目标价")
    
    fig.update_layout(
        title=f"{signal.stock_name} ({signal.stock_code}) - 半路战法信号",
        height=600,
        xaxis_title="日期",
        yaxis_title="价格",
        showlegend=True
    )
    
    return fig