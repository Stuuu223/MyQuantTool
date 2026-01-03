import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.ai_agent import DeepSeekAgent
from logic.comparator import StockComparator
from logic.backtest import BacktestEngine
from config import Config
import os

st.set_page_config(page_title="个人化A股智能终端", layout="wide", page_icon="📈", menu_items={
    'Get Help': None,
    'Report a bug': None,
    'About': None
})

# 添加自定义说明
st.markdown("""
<style>
.stAppHeader {
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

# --- 加载配置 ---
config = Config()

# API Key 优先级：环境变量 > 配置文件 > 默认值
API_KEY = os.getenv("SILICONFLOW_API_KEY") or config.get('api_key', 'sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet')

db = DataManager()
ai_agent = DeepSeekAgent(api_key=API_KEY)
comparator = StockComparator(db)
backtest_engine = BacktestEngine()

st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# 添加系统菜单说明
# st.caption("💡 右上角菜单说明：")
# st.caption("  • ⚙️ Settings（设置）：调整显示主题、字体大小等")
# st.caption("  • 🚀 Deploy（部署）：将应用部署到云端（需要账号）")
# st.caption("  • ❌ Clear cache（清除缓存）：刷新数据和重置状态")

# 添加功能标签页
tab_single, tab_compare, tab_backtest = st.tabs(["📊 单股分析", "🔍 多股对比", "🧪 策略回测"])

with st.sidebar:
    st.header("🎮 控制台")
    
    # 从配置文件加载默认值
    symbol = st.text_input("股票代码", value=config.get('default_symbol', '600519'), help="请输入6位A股代码")
    start_date = st.date_input("开始日期", pd.to_datetime(config.get('default_start_date', '2024-01-01')))
    
    # 策略参数
    st.subheader("⚙️ 策略参数")
    atr_mult = st.slider("ATR 倍数", 0.1, 2.0, float(config.get('atr_multiplier', 0.5)), 0.1)
    grid_ratio = st.slider("网格比例", 0.05, 0.5, float(config.get('grid_ratio', 0.1)), 0.05)
    
    run_ai = st.button("🧠 呼叫 AI 投顾")
    
    st.markdown("---")
    
    # 自选股管理
    st.subheader("⭐ 自选股")
    watchlist = config.get('watchlist', [])
    
    if watchlist:
        st.write("已关注的股票：")
        for stock in watchlist:
            col_watch, col_remove = st.columns([3, 1])
            with col_watch:
                st.write(f"📌 {stock}")
            with col_remove:
                if st.button("❌", key=f"remove_{stock}"):
                    watchlist.remove(stock)
                    config.set('watchlist', watchlist)
                    st.rerun()
    
    add_stock = st.text_input("添加自选股", placeholder="输入股票代码", help="例如：600519")
    if st.button("➕ 添加") and add_stock:
        if add_stock not in watchlist:
            watchlist.append(add_stock)
            config.set('watchlist', watchlist)
            st.success(f"已添加 {add_stock} 到自选股")
        else:
            st.warning(f"{add_stock} 已在自选股中")
    
    st.markdown("---")
    
    # 配置管理
    with st.expander("🔧 配置管理"):
        new_api_key = st.text_input("API Key", type="password", value=API_KEY if API_KEY else "")
        
        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("保存配置"):
                config.update({
                    'api_key': new_api_key,
                    'default_symbol': symbol,
                    'default_start_date': str(start_date),
                    'atr_multiplier': atr_mult,
                    'grid_ratio': grid_ratio
                })
                st.success("配置已保存！")
        
        with col_reset:
            if st.button("重置配置"):
                config.reset()
                st.success("配置已重置！")
    
    st.caption("数据来源: AkShare 开源接口")
    
    # 检查 API Key 是否有效
    if not API_KEY or len(API_KEY) < 10:
        st.warning("⚠️ 未检测到有效 Key，AI 功能将不可用。请访问 https://siliconflow.cn/ 获取免费 API Key（2000万tokens）。")

with tab_single:
    # 自选股快速切换
    watchlist = config.get('watchlist', [])
    if watchlist:
        st.subheader("⭐ 自选股快速切换")
        selected_watch = st.selectbox("选择自选股", ["手动输入"] + watchlist)
        if selected_watch != "手动输入":
            symbol = selected_watch
    
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
    
    if symbol:
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在连接交易所数据管道...'):
            df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
        
        if not df.empty and len(df) > 30:
            current_price = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close']
            change_pct = (current_price - prev_close) / prev_close * 100
            
            # 计算各项技术指标
            atr = QuantAlgo.calculate_atr(df)
            resistance_levels = QuantAlgo.calculate_resistance_support(df)
            grid_plan = QuantAlgo.generate_grid_strategy(current_price, atr)
            macd_data = QuantAlgo.calculate_macd(df)
            rsi_data = QuantAlgo.calculate_rsi(df)
            bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
            box_pattern = QuantAlgo.detect_box_pattern(df)
            
            # 分离支撑位和阻力位
            support_levels = [x for x in resistance_levels if x < current_price]
            resistance_levels = [x for x in resistance_levels if x > current_price]

            # 顶部指标卡片
            st.subheader("📈 核心指标看板")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("最新价格", f"¥{current_price}", f"{change_pct:.2f}%")
            col2.metric("日内波动 (ATR)", f"{atr:.2f}")
            col3.metric("网格密度", f"¥{grid_plan['网格宽度']}")
            col4.metric("AI模型", "DeepSeek-V3")

            # 箱体震荡提示
            st.divider()
            if box_pattern['is_box']:
                st.success(f"📦 **{box_pattern['message']}**")
                col_box1, col_box2, col_box3 = st.columns(3)
                with col_box1:
                    st.metric("箱体上沿", f"¥{box_pattern['box_high']}")
                with col_box2:
                    st.metric("箱体下沿", f"¥{box_pattern['box_low']}")
                with col_box3:
                    st.metric("箱体宽度", f"¥{box_pattern['box_width']}")
                st.info(f"💡 当前价格在箱体 {box_pattern['position_pct']}% 位置，建议在箱体下沿附近买入，上沿附近卖出")
            elif box_pattern.get('is_breakout_up'):
                st.warning(f"🚀 **{box_pattern['message']}**")
                st.info(f"💡 向上突破 {box_pattern['breakout_pct']:.2f}%，注意观察是否有效突破，可能迎来上涨行情")
            elif box_pattern.get('is_breakout_down'):
                st.error(f"⚠️ **{box_pattern['message']}**")
                st.info(f"💡 向下突破 {box_pattern['breakout_pct']:.2f}%，注意风险控制，可能继续下跌")
            else:
                st.info(f"📊 **{box_pattern['message']}**")

            # 技术指标详情
            st.subheader("📊 技术指标分析")
            st.caption("💡 点击上方「📖 技术指标解释」查看详细说明")
            
            col_macd, col_rsi, col_bb = st.columns(3)
            
            with col_macd:
                st.info("**MACD 指标**")
                st.write(f"MACD: {macd_data['MACD']}")
                st.write(f"信号线: {macd_data['Signal']}")
                st.write(f"柱状图: {macd_data['Histogram']}")
                st.write(f"趋势: {macd_data['Trend']}")
                if macd_data['Trend'] == "多头":
                    st.success("✅ 趋势向上，适合买入")
                else:
                    st.warning("⚠️ 趋势向下，注意风险")
            
            with col_rsi:
                st.info("**RSI 指标**")
                st.write(f"RSI: {rsi_data['RSI']}")
                st.write(f"信号: {rsi_data['Signal']}")
                if rsi_data['RSI'] > 70:
                    st.warning("⚠️ 超买区域（>70），价格偏高，考虑减仓")
                elif rsi_data['RSI'] < 30:
                    st.success("✅ 超卖区域（<30），价格偏低，考虑买入")
                else:
                    st.info("正常区间（30-70），继续持有")
            
            with col_bb:
                st.info("**布林带**")
                st.write(f"上轨: {bollinger_data['上轨']:.2f}")
                st.write(f"中轨: {bollinger_data['中轨']:.2f}")
                st.write(f"下轨: {bollinger_data['下轨']:.2f}")
                st.write(f"位置: {bollinger_data['当前位置']}%")
                st.write(f"解读: {bollinger_data['解读']}")
                if current_price > bollinger_data['上轨']:
                    st.warning("⚠️ 价格突破上轨，注意回调风险")
                elif current_price < bollinger_data['下轨']:
                    st.success("✅ 价格接近下轨，可能反弹")
                else:
                    st.info("价格在布林带内，正常波动")

            # K线图
            st.subheader("📊 K线图与支撑阻力位")
            fig = go.Figure(data=[go.Candlestick(x=df['date'],
                            open=df['open'], high=df['high'],
                            low=df['low'], close=df['close'], name='K线')])
            
            # 绘制阻力位（红色）
            for level in resistance_levels[:3]:  # 只显示最近的3个阻力位
                fig.add_hline(y=level, line_dash="dash", line_color="rgba(255, 0, 0, 0.6)", 
                              annotation_text=f"阻力 {level:.2f}")
            
            # 绘制支撑位（绿色）
            for level in support_levels[-3:]:  # 只显示最近的3个支撑位
                fig.add_hline(y=level, line_dash="dash", line_color="rgba(0, 255, 0, 0.6)", 
                              annotation_text=f"支撑 {level:.2f}")
            
            # 绘制箱体（如果存在）
            if box_pattern['is_box']:
                # 箱体上沿（黄色）
                fig.add_hline(y=box_pattern['box_high'], line_dash="solid", line_color="rgba(255, 193, 7, 0.8)", 
                              line_width=2, annotation_text=f"箱体上沿 {box_pattern['box_high']:.2f}")
                # 箱体下沿（黄色）
                fig.add_hline(y=box_pattern['box_low'], line_dash="solid", line_color="rgba(255, 193, 7, 0.8)", 
                              line_width=2, annotation_text=f"箱体下沿 {box_pattern['box_low']:.2f}")
                # 添加箱体背景
                fig.add_hrect(y0=box_pattern['box_low'], y1=box_pattern['box_high'], 
                             fillcolor="rgba(255, 193, 7, 0.1)", layer="below", line_width=0)
            
            # 绘制布林带
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['close'].rolling(20).mean() + df['close'].rolling(20).std() * 2,
                mode='lines',
                name='布林上轨',
                line=dict(color='rgba(0, 0, 255, 0.3)', width=1)
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['close'].rolling(20).mean() - df['close'].rolling(20).std() * 2,
                mode='lines',
                name='布林下轨',
                line=dict(color='rgba(0, 0, 255, 0.3)', width=1)
            ))
                
            fig.update_layout(xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)

            # 策略和AI分析
            col_strategy, col_ai = st.columns([1, 1])
            
            with col_strategy:
                st.subheader("🛠️ 网格交易策略")
                st.info("基于 ATR 波动率自适应计算：")
                st.table(pd.DataFrame([grid_plan]).T.rename(columns={0: '数值/建议'}))
            
            with col_ai:
                st.subheader("🤖 AI 智能分析")
                if run_ai:
                    with st.spinner("DeepSeek 正在深度分析..."):
                        # 准备技术数据
                        tech_data = {
                            'current_price': current_price,
                            'resistance_levels': resistance_levels[:3],
                            'support_levels': support_levels[-3:],
                            'atr': atr,
                            'macd': macd_data,
                            'rsi': rsi_data,
                            'bollinger': bollinger_data
                        }
                        analysis = ai_agent.analyze_stock(symbol, round(change_pct, 2), tech_data)
                        st.success(analysis)
                else:
                    st.write("点击侧边栏的「呼叫 AI 投顾」按钮，获取专业投资建议。")

with tab_backtest:
    st.subheader("🧪 网格策略回测")
    
    st.info("⚠️ 注意：回测结果仅供参考，不构成投资建议。实际交易中存在滑点、手续费等额外成本。")
    
    # 回测参数设置
    backtest_symbol = st.text_input("回测股票代码", value="600519")
    backtest_start = st.date_input("回测开始日期", pd.to_datetime("2023-01-01"))
    
    col_atr, col_ratio, col_cost = st.columns(3)
    with col_atr:
        bt_atr_mult = st.slider("ATR 倍数", 0.1, 2.0, 0.5, 0.1)
    with col_ratio:
        bt_grid_ratio = st.slider("网格比例", 0.05, 0.5, 0.1, 0.05)
    with col_cost:
        bt_cost = st.slider("交易手续费", 0.000, 0.01, 0.001, 0.001)
    
    if st.button("运行回测"):
        s_date_str = backtest_start.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在运行回测...'):
            df = db.get_history_data(backtest_symbol, start_date=s_date_str, end_date=e_date_str)
            
            if not df.empty and len(df) > 50:
                result = backtest_engine.run_grid_strategy_backtest(
                    df, 
                    atr_multiplier=bt_atr_mult, 
                    grid_ratio=bt_grid_ratio,
                    transaction_cost=bt_cost
                )
                
                # 显示回测报告
                report = backtest_engine.generate_backtest_report(result)
                st.markdown(report)
                
                # 显示交易记录
                if not result['交易记录'].empty:
                    st.subheader("📝 交易记录")
                    st.dataframe(result['交易记录'], use_container_width=True)
                
                # 显示资金曲线
                st.subheader("💰 资金曲线")
                # 简单的资金曲线可视化
                capital_curve = []
                running_capital = result['初始资金']
                capital_curve.append(running_capital)
                
                for _, trade in result['交易记录'].iterrows():
                    running_capital = trade['capital']
                    capital_curve.append(running_capital)
                
                fig_capital = go.Figure()
                fig_capital.add_trace(go.Scatter(
                    y=capital_curve,
                    mode='lines+markers',
                    name='资金曲线',
                    line=dict(color='blue', width=2)
                ))
                
                fig_capital.update_layout(
                    title="资金变化曲线",
                    xaxis_title="交易次数",
                    yaxis_title="资金（元）",
                    height=400
                )
                st.plotly_chart(fig_capital, use_container_width=True)
                
            else:
                st.error("数据不足，无法进行回测。请选择更早的日期或检查股票代码。")

with tab_compare:
    st.subheader("🔍 多股票技术指标对比")
    
    # 股票代码输入
    compare_symbols_input = st.text_input("输入要对比的股票代码（用逗号分隔）", 
                                         value="600519,000001,600036",
                                         help="例如：600519,000001,600036")
    
    compare_symbols = [s.strip() for s in compare_symbols_input.split(',') if s.strip()]
    
    if st.button("开始对比分析") and compare_symbols:
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在分析多只股票...'):
            # 技术指标对比
            comparison_df = comparator.compare_stocks(compare_symbols, s_date_str, e_date_str)
            
            if not comparison_df.empty:
                st.dataframe(comparison_df, use_container_width=True)
                
                # 收益率对比图
                st.subheader("📈 收益率曲线对比")
                performance_df = comparator.get_performance_comparison(compare_symbols, s_date_str, e_date_str)
                
                if not performance_df.empty:
                    fig_perf = go.Figure()
                    
                    for symbol in performance_df.columns:
                        fig_perf.add_trace(go.Scatter(
                            x=performance_df.index,
                            y=performance_df[symbol],
                            mode='lines',
                            name=symbol
                        ))
                    
                    fig_perf.update_layout(
                        title="累计收益率对比",
                        xaxis_title="日期",
                        yaxis_title="累计收益率",
                        height=400
                    )
                    st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.warning("未能获取到有效的对比数据，请检查股票代码是否正确。")
