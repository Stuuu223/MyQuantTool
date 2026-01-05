"""
单股分析模块

提供单只股票的详细分析功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.formatter import Formatter
from logic.logger import get_logger
from config import Config

logger = get_logger(__name__)


def render_single_stock_tab(db: DataManager, config: Config):
    """
    渲染单股分析标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("📊 单股分析")
    
    # 自选股快速切换
    watchlist = config.get('watchlist', [])
    if watchlist:
        st.subheader("⭐ 自选股快速切换")
        selected_watch = st.selectbox("选择自选股", ["手动输入"] + watchlist)
        if selected_watch != "手动输入":
            symbol = selected_watch
    
    # 股票代码输入
    if 'symbol' not in locals():
        symbol = st.text_input("股票代码", value="600519", help="输入6位股票代码，如：600519")
    
    # 日期范围选择
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=60))
    with col_date2:
        end_date = st.date_input("结束日期", value=datetime.now())
    
    # 添加"开始分析"按钮
    if symbol and st.button("🚀 开始分析", key="start_analysis"):
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        # 进度条
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        progress_text.text("📡 正在连接交易所数据管道...")
        progress_bar.progress(10)
        df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
        
        progress_text.text("📊 正在获取实时行情...")
        progress_bar.progress(30)
        # 获取实时数据（带缓存，60秒内直接使用缓存）
        realtime_data = db.get_realtime_data(symbol)
        
        progress_text.text("🔍 正在分析数据...")
        progress_bar.progress(50)
        
        progress_bar.empty()
        progress_text.empty()
        
        if not df.empty and len(df) > 30:
            # 优先使用实时数据
            if realtime_data:
                current_price = realtime_data['price']
                change_pct = realtime_data['change_percent']
                
                # 根据是否在交易时间显示不同的提示
                is_trading = realtime_data.get('is_trading', False)
                if is_trading:
                    st.success(f"🟢 实时数据已更新 ({realtime_data['timestamp']})")
                else:
                    st.info(f"⚪ 使用收盘价数据 ({realtime_data['timestamp']})")
            else:
                current_price = df.iloc[-1]['close']
                prev_close = df.iloc[-2]['close']
                change_pct = (current_price - prev_close) / prev_close * 100
                st.info("⚪ 使用历史数据（实时数据获取失败）")
            
            # 计算技术指标
            atr = QuantAlgo.calculate_atr(df)
            resistance_levels = QuantAlgo.calculate_resistance_support(df)
            macd_data = QuantAlgo.calculate_macd(df)
            rsi_data = QuantAlgo.calculate_rsi(df)
            bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
            kdj_data = QuantAlgo.calculate_kdj(df)
            volume_data = QuantAlgo.analyze_volume(df)
            money_flow_data = QuantAlgo.analyze_money_flow(df, symbol=symbol, market="sh" if symbol.startswith("6") else "sz")
            
            # 显示基本信息
            stock_name = QuantAlgo.get_stock_name(symbol)
            st.markdown(f"### {stock_name} ({symbol})")
            
            # 价格信息
            col_price, col_change, col_atr = st.columns(3)
            with col_price:
                st.metric("最新价格", f"¥{current_price:.2f}")
            with col_change:
                color = "🔴" if change_pct > 0 else "🟢"
                st.metric("涨跌幅", f"{color} {change_pct:+.2f}%")
            with col_atr:
                st.metric("ATR 波动率", f"{atr:.2f}")
            
            # 技术指标分析
            st.markdown("---")
            st.subheader("📈 技术指标分析")
            
            # MACD
            col_macd, col_rsi, col_kdj = st.columns(3)
            with col_macd:
                macd_value = macd_data['MACD'].iloc[-1]
                signal_value = macd_data['Signal'].iloc[-1]
                macd_status = "🔴 看涨" if macd_value > signal_value else "🟢 看跌"
                st.metric("MACD", f"{macd_value:.2f}")
                st.caption(f"信号线: {signal_value:.2f} | {macd_status}")
            
            with col_rsi:
                rsi_value = rsi_data['RSI'].iloc[-1]
                if rsi_value > 70:
                    rsi_status = "⚠️ 超买"
                elif rsi_value < 30:
                    rsi_status = "⚠️ 超卖"
                else:
                    rsi_status = "✅ 正常"
                st.metric("RSI", f"{rsi_value:.2f}")
                st.caption(rsi_status)
            
            with col_kdj:
                k_value = kdj_data['K'].iloc[-1]
                d_value = kdj_data['D'].iloc[-1]
                j_value = kdj_data['J'].iloc[-1]
                kdj_status = "🔴 金叉" if k_value > d_value else "🟢 死叉"
                st.metric("KDJ", f"K:{k_value:.2f} D:{d_value:.2f}")
                st.caption(f"J:{j_value:.2f} | {kdj_status}")
            
            # 支撑阻力位
            st.markdown("---")
            st.subheader("🎯 支撑阻力位")
            col_support, col_resistance = st.columns(2)
            with col_support:
                st.metric("支撑位", f"¥{resistance_levels['support']:.2f}", help="价格下跌时可能反弹的位置")
            with col_resistance:
                st.metric("阻力位", f"¥{resistance_levels['resistance']:.2f}", help="价格上涨时可能受阻的位置")
            
            # 成交量分析
            st.markdown("---")
            st.subheader("📊 成交量分析")
            col_volume, col_ratio, col_flow = st.columns(3)
            with col_volume:
                vol = volume_data['当前成交量'] if '当前成交量' in volume_data else 0
                st.metric("成交量", Formatter.format_volume(vol))
            with col_ratio:
                ratio = volume_data['量比'] if '量比' in volume_data else 1.0
                st.metric("量比", f"{ratio:.2f}")
            with col_flow:
                flow = money_flow_data.get('status', '未知')
                flow_emoji = "🟢" if flow == "流入" else "🔴" if flow == "流出" else "⚪"
                st.metric("资金流向", f"{flow_emoji} {flow}")
            
            # 价格走势图
            st.markdown("---")
            st.subheader("📈 价格走势")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='K线'
            ))
            fig.add_trace(go.Scatter(
                x=df.index,
                y=bollinger_data['上轨'],
                name='布林带上轨',
                line=dict(color='rgba(255,0,0,0.5)')
            ))
            fig.add_trace(go.Scatter(
                x=df.index,
                y=bollinger_data['下轨'],
                name='布林带下轨',
                line=dict(color='rgba(0,255,0,0.5)')
            ))
            fig.update_layout(
                title=f"{stock_name} 价格走势",
                xaxis_title="日期",
                yaxis_title="价格",
                height=400
            )
            st.plotly_chart(fig, width="stretch")
            
            # 添加到自选股按钮
            if st.button(f"⭐ 添加 {stock_name} 到自选股", key=f"add_{symbol}"):
                watchlist = config.get('watchlist', [])
                if symbol not in watchlist:
                    watchlist.append(symbol)
                    config.set('watchlist', watchlist)
                    st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
                else:
                    st.info(f"{stock_name} ({symbol}) 已在自选股中")
        else:
            st.warning("数据不足,无法分析")
            st.info("💡 请检查股票代码是否正确，或选择更长的日期范围")