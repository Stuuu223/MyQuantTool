"""
K线形态识别器UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.kline_pattern_recognizer import get_kline_pattern_recognizer
from logic.data_manager import DataManager


def render_kline_patterns_tab(db, config):
    """渲染K线形态识别器标签页"""
    
    st.header("📊 K线形态识别")
    st.markdown("自动识别5种经典K线形态，提供买卖信号和目标价位")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 识别配置")
        
        symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="kline_symbol")
        
        lookback = st.slider(
            "回溯天数",
            min_value=30,
            max_value=120,
            value=60,
            help="用于识别形态的历史数据天数"
        )
        
        min_confidence = st.slider(
            "最小置信度",
            min_value=0.5,
            max_value=0.9,
            value=0.6,
            step=0.05,
            help="只显示置信度高于此值的形态"
        )
        
        st.markdown("---")
        st.subheader("📈 形态说明")
        st.markdown("""
        **头肩顶/底**:
        - 头肩顶: 看跌信号，目标位-5%
        - 头肩底: 看涨信号，目标位+5%
        
        **双重顶/底**:
        - 双重顶: 看跌信号
        - 双重底: 看涨信号
        
        **三角形**:
        - 上升三角形: 看涨突破
        - 下降三角形: 看跌突破
        - 对称三角形: 方向不明
        
        **旗形**:
        - 看涨旗形: 继续上涨
        - 看跌旗形: 继续下跌
        
        **楔形**:
        - 上升楔形: 看跌反转
        - 下降楔形: 看涨反转
        """)
    
    # 主内容区
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 K线图表")
        
        if st.button("🔍 识别形态", key="recognize_patterns"):
            with st.spinner("正在识别K线形态..."):
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=lookback)
                    
                    # 获取K线数据
                    df = db.get_history_data(
                        symbol,
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d")
                    )
                    
                    if df is not None and not df.empty:
                        # 识别形态
                        recognizer = get_kline_pattern_recognizer(min_confidence=min_confidence)
                        patterns = recognizer.recognize_patterns(df, lookback=lookback)
                        
                        # 显示K线图
                        fig = go.Figure()
                        
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name='K线'
                        ))
                        
                        # 标记形态
                        for pattern in patterns:
                            fig.add_vrect(
                                x0=pattern.start_date,
                                x1=pattern.end_date,
                                fillcolor="rgba(255, 107, 107, 0.3)" if pattern.signal.value == "卖出" else "rgba(107, 255, 107, 0.3)",
                                layer="below",
                                line_width=0,
                                annotation_text=f"{pattern.pattern_type.value}",
                                annotation_position="top left"
                            )
                        
                        fig.update_layout(
                            title=f"{symbol} K线形态分析",
                            xaxis_title="日期",
                            yaxis_title="价格",
                            height=500,
                            template="plotly_dark"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 显示形态结果
                        if patterns:
                            st.subheader(f"🎯 识别到 {len(patterns)} 个形态")
                            
                            for i, pattern in enumerate(patterns, 1):
                                with st.expander(f"{i}. {pattern.pattern_type.value} - {pattern.signal.value}"):
                                    col_a, col_b, col_c = st.columns(3)
                                    
                                    col_a.metric("置信度", f"{pattern.confidence:.1%}")
                                    col_b.metric("信号", pattern.signal.value)
                                    col_c.metric("开始日期", pattern.start_date)
                                    
                                    if pattern.target_price:
                                        st.info(f"🎯 目标价位: ¥{pattern.target_price:.2f}")
                                    if pattern.stop_loss:
                                        st.warning(f"🛑 止损价位: ¥{pattern.stop_loss:.2f}")
                                    
                                    st.markdown(f"**描述**: {pattern.description}")
                        else:
                            st.info("未识别到符合条件的形态")
                    else:
                        st.error("无法获取股票数据，请检查股票代码")
                
                except Exception as e:
                    st.error(f"识别失败: {str(e)}")
    
    with col2:
        st.subheader("📊 形态统计")
        
        # 模拟统计数据
        st.metric("总识别次数", "156")
        st.metric("平均置信度", "72.5%")
        st.metric("买入信号", "89")
        st.metric("卖出信号", "67")
        
        st.markdown("---")
        st.subheader("📈 最近形态")
        
        # 模拟最近形态记录
        recent_patterns = [
            {"形态": "头肩顶", "信号": "卖出", "置信度": "85%", "日期": "2026-01-05"},
            {"形态": "双重底", "信号": "买入", "置信度": "78%", "日期": "2026-01-04"},
            {"形态": "上升三角形", "信号": "买入", "置信度": "72%", "日期": "2026-01-03"},
            {"形态": "看涨旗形", "信号": "买入", "置信度": "68%", "日期": "2026-01-02"},
        ]
        
        for pattern in recent_patterns:
            with st.container():
                cols = st.columns([2, 1, 1, 1])
                cols[0].write(f"**{pattern['形态']}**")
                cols[1].write(pattern['信号'])
                cols[2].write(pattern['置信度'])
                cols[3].write(pattern['日期'])
                st.divider()