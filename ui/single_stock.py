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


def format_amount(amount):
    """格式化金额显示"""
    abs_amount = abs(amount)
    if abs_amount >= 100000000:
        return f"{amount/100000000:.2f}亿"
    elif abs_amount >= 10000:
        return f"{amount/10000:.2f}万"
    else:
        return f"{amount:.0f}"


def render_single_stock_tab(db: DataManager, config: Config):
    """
    渲染单股分析标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("📊 单股分析")
    
    # 股票代码输入
    col_input, col_button = st.columns([3, 1])
    with col_input:
        symbol = st.text_input("股票代码", value="600519", help="输入6位股票代码，如600519", key="single_stock_symbol")
    with col_button:
        if st.button("🚀 开始分析", key="single_analyze"):
            st.session_state.analysis_symbol = symbol
    
    # 使用session state保存当前分析的股票
    if 'analysis_symbol' not in st.session_state:
        st.session_state.analysis_symbol = "600519"
    
    symbol = st.session_state.analysis_symbol
    
    # 添加指标解释按钮
    with st.expander("📖 技术指标解释（小白必读）"):
        st.markdown("""
        ### 📌 基础指标
        
        **最新价格**：股票当前的市场价格，这是买卖的基准价
        
        **涨跌幅**：今日相比昨日的涨跌百分比，红色表示上涨，绿色表示下跌
        
        **ATR 波动率**：衡量股价波动的剧烈程度，ATR 越大风险越高
        
        ---
        
        ### 📦 形态识别
        
        **箱体震荡（Box Pattern）**：
        - 股价在固定区间内上下波动
        - **箱体内**：在下沿买入，上沿卖出，做波段
        - **向上突破**：可能迎来上涨，注意观察
        - **向下突破**：注意风险，考虑止损
        - 💡 最常见的形态，适合短线操作
        
        **双底/双顶**：
        - **双底**：W形，两次探底不创新低，底部确认
        - **双顶**：M形，两次冲高不创新高，顶部确认
        - 💡 重要的反转信号
        
        **头肩顶/头肩底**：
        - **头肩顶**：三高形态，中间最高，看跌信号
        - **头肩底**：三低形态，中间最低，看涨信号
        - 💡 经典的反转形态，可靠性高
        
        ---
        
        ### 🎯 技术指标
        
        **MACD（异同移动平均线）**：
        - 判断趋势方向
        - MACD > 信号线：趋势向上，适合买入
        - MACD < 信号线：趋势向下，适合卖出
        
        **RSI（相对强弱指标）**：
        - 判断超买超卖
        - RSI > 70：超买，价格过高，注意风险
        - RSI < 30：超卖，价格过低，可能反弹
        
        **布林带**：
        - 判断价格高低
        - 价格接近上轨：偏高，考虑减仓
        - 价格接近下轨：偏低，考虑买入
        
        **KDJ 指标**：
        - 超买超卖指标，结合动量和强弱
        - K > D 且 J > 0：金叉，买入信号
        - K < D 且 J < 0：死叉，卖出信号
        - K > 80 且 D > 80：超买，注意风险
        - K < 20 且 D < 20：超卖，可能反弹
        
        **成交量分析**：
        - 量比 > 2：放量显著，关注主力动向
        - 量比 1.5-2：温和放量，资金参与度提升
        - 量比 < 0.5：缩量，观望为主
        - 💡 量价配合是关键
        
        **资金流向**：
        - 流入：价格上涨，资金净流入
        - 流出：价格下跌，资金净流出
        - 持平：价格持平，资金无明显流向
        - 💡 反映主力资金动向
        
        ---
        
        ### ⚙️ 策略参数
        
        **ATR 倍数**：调整网格宽度
        - 保守型：1.0-1.5（交易少，风险低）
        - 激进型：0.3-0.5（交易多，风险高）
        - 推荐值：0.5
        
        **网格比例**：每次交易的资金比例
        - 保守型：5%-10%
        - 激进型：20%-30%
        - 推荐值：10%
        
        ---
        
        💡 **新手建议**：不要只看一个指标，要综合判断。先用模拟盘练习，从小资金开始！
        """)
    
    # 获取股票数据
    start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
    s_date_str = start_date.strftime("%Y%m%d")
    e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
    
    with st.spinner(f'正在获取 {symbol} 数据...'):
        df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
    
    # 获取实时数据（带缓存，60秒内直接使用缓存）
    realtime_data = db.get_realtime_data(symbol)
    
    if not df.empty and len(df) > 30:
        # 优先使用实时数据
        if realtime_data:
            current_price = realtime_data['price']
            change_pct = realtime_data['change_percent']
            st.success(f"实时数据已更新 ({realtime_data['timestamp']})")
        else:
            current_price = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close']
            # 防止除以零
            if prev_close != 0:
                change_pct = (current_price - prev_close) / prev_close * 100
            else:
                change_pct = 0.0
            st.info("使用历史数据（实时数据获取失败）")
        
        # 计算技术指标
        atr = QuantAlgo.calculate_atr(df)
        macd_data = QuantAlgo.calculate_macd(df)
        rsi_data = QuantAlgo.calculate_rsi(df)
        bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
        kdj_data = QuantAlgo.calculate_kdj(df)
        
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
            # macd_data是字典，直接访问值
            macd_value = float(macd_data['MACD'])
            signal_value = float(macd_data['Signal'])
            
            macd_status = "看涨" if macd_value > signal_value else "看跌"
            st.metric("MACD", f"{macd_value:.2f}")
            st.caption(f"信号线: {signal_value:.2f} | {macd_status}")
        
        with col_rsi:
            # rsi_data是字典
            rsi_value = float(rsi_data['RSI'])
            
            if rsi_value > 70:
                rsi_status = "超买"
            elif rsi_value < 30:
                rsi_status = "超卖"
            else:
                rsi_status = "正常"
            st.metric("RSI", f"{rsi_value:.2f}")
            st.caption(rsi_status)
        
        with col_kdj:
            # kdj_data是字典
            k_value = float(kdj_data['K'])
            d_value = float(kdj_data['D'])
            j_value = float(kdj_data['J'])
            
            kdj_status = "金叉" if k_value > d_value else "死叉"
            st.metric("KDJ", f"K:{k_value:.2f} D:{d_value:.2f}")
            st.caption(f"J:{j_value:.2f} | {kdj_status}")
        
        # 布林带
        st.markdown("---")
        st.subheader("📊 布林带分析")
        if isinstance(bollinger_data, dict):
            col_upper, col_middle, col_lower = st.columns(3)
            with col_upper:
                st.metric("上轨", f"¥{float(bollinger_data['上轨']):.2f}")
            with col_middle:
                st.metric("中轨", f"¥{float(bollinger_data['中轨']):.2f}")
            with col_lower:
                st.metric("下轨", f"¥{float(bollinger_data['下轨']):.2f}")
            
            # 显示当前位置
            st.caption(f"当前位置: {bollinger_data['当前位置']}% - {bollinger_data['解读']}")
        
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
        
        # 添加布林带
        if isinstance(bollinger_data, dict):
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[float(bollinger_data['上轨'])] * len(df),
                name='上轨',
                line=dict(color='rgba(255,0,0,0.5)')
            ))
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[float(bollinger_data['下轨'])] * len(df),
                name='下轨',
                line=dict(color='rgba(0,255,0,0.5)')
            ))
        
        fig.update_layout(
            title=f"{stock_name} 价格走势",
            xaxis_title="日期",
            yaxis_title="价格",
            height=400
        )
        st.plotly_chart(fig, width="stretch")
        
        # 操作建议
        st.markdown("---")
        st.subheader("💡 操作建议")
        
        suggestions = []
        
        # MACD建议
        if macd_value > signal_value:
            suggestions.append("MACD金叉，趋势向上")
        else:
            suggestions.append("MACD死叉，趋势向下")
        
        # RSI建议
        if rsi_value > 70:
            suggestions.append("RSI超买，注意风险")
        elif rsi_value < 30:
            suggestions.append("RSI超卖，可能反弹")
        
        # KDJ建议
        if k_value > d_value and j_value > 0:
            suggestions.append("KDJ金叉，买入信号")
        elif k_value < d_value and j_value < 0:
            suggestions.append("KDJ死叉，卖出信号")
        
        # 布林带建议
        if isinstance(bollinger_data, dict):
            if current_price > float(bollinger_data['上轨']):
                suggestions.append("突破上轨，注意回调")
            elif current_price < float(bollinger_data['下轨']):
                suggestions.append("跌破下轨，可能反弹")
        
        if suggestions:
            for suggestion in suggestions:
                st.write(suggestion)
        else:
            st.info("暂无明显信号，建议观望")
        
        # 添加到自选股按钮
        if st.button(f"添加 {stock_name} 到自选股", key=f"add_{symbol}"):
            watchlist = config.get('watchlist', [])
            if symbol not in watchlist:
                watchlist.append(symbol)
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
            else:
                st.info(f"{stock_name} ({symbol}) 已在自选股中")
    else:
        st.warning("数据不足,无法分析")