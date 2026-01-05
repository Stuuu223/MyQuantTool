import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.algo_advanced import AdvancedAlgo
from logic.ai_agent import DeepSeekAgent
from logic.comparator import StockComparator
from logic.backtest import BacktestEngine
from logic.formatter import Formatter
from logic.logger import get_logger
from logic.error_handler import handle_errors, ValidationError
from config import Config
import os
import concurrent.futures
import threading

# 初始化日志系统
logger = get_logger(__name__)
logger.info("=" * 50)
logger.info("应用启动")

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

logger.info("核心组件初始化完成")

# 全局辅助函数：格式化金额显示
def format_amount(amount):
    """格式化金额显示，自动转换为万或亿单位"""
    abs_amount = abs(amount)
    if abs_amount >= 100000000:  # 1亿以上
        return f"{amount/100000000:.2f}亿"
    elif abs_amount >= 10000:  # 1万以上
        return f"{amount/10000:.2f}万"
    else:
        return f"{amount:.0f}"

# 全局辅助函数：显示加载状态
def show_loading_state(message: str, progress: float = 0):
    """显示加载状态和进度"""
    st.session_state.loading = True
    if progress > 0:
        st.session_state.progress = progress
        st.session_state.progress_text = message
    else:
        st.session_state.loading_message = message

# 全局辅助函数：隐藏加载状态
def hide_loading_state():
    """隐藏加载状态"""
    st.session_state.loading = False
    if 'progress' in st.session_state:
        del st.session_state.progress
    if 'progress_text' in st.session_state:
        del st.session_state.progress_text
    if 'loading_message' in st.session_state:
        del st.session_state.loading_message

# 全局辅助函数：显示单股分析弹窗
def show_stock_analysis_modal(symbol, stock_name=None):
    """显示单股分析弹窗"""
    if not stock_name:
        stock_name = QuantAlgo.get_stock_name(symbol)
    
    with st.expander(f"📊 单股分析 - {stock_name} ({symbol})", expanded=True):
        # 获取股票数据
        start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner(f'正在获取 {stock_name} 数据...'):
            df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
        
        # 尝试获取实时数据
        realtime_data = db.get_realtime_data(symbol)
        
        if not df.empty and len(df) > 30:
            # 优先使用实时数据
            if realtime_data:
                current_price = realtime_data['price']
                change_pct = realtime_data['change_percent']
                st.success(f"🟢 实时数据已更新 ({realtime_data['timestamp']})")
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
            
            # 核心指标
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("最新价", f"¥{current_price:.2f}", f"{change_pct:+.2f}%")
            with col2:
                st.metric("ATR", f"{atr:.2f}", "波动率")
            with col3:
                rsi_val = rsi_data['RSI'].iloc[-1]
                rsi_status = "超买" if rsi_val > 70 else "超卖" if rsi_val < 30 else "正常"
                st.metric("RSI", f"{rsi_val:.2f}", rsi_status)
            with col4:
                k_val, d_val, j_val = kdj_data['K'].iloc[-1], kdj_data['D'].iloc[-1], kdj_data['J'].iloc[-1]
                kdj_status = "金叉" if k_val > d_val else "死叉"
                st.metric("KDJ", f"{k_val:.2f}", kdj_status)
            
            # MACD分析
            st.subheader("📈 MACD分析")
            macd_signal = macd_data['MACD'].iloc[-1] - macd_data['Signal'].iloc[-1]
            macd_status = "多头" if macd_signal > 0 else "空头"
            st.info(f"MACD: {macd_status} (差值: {macd_signal:.4f})")
            
            # 资金流向
            st.subheader("💰 资金流向")
            flow_status = money_flow_data['资金流向']
            flow_emoji = "📈" if flow_status == "净流入" else "📉" if flow_status == "净流出" else "➡️"
            st.metric(f"{flow_emoji} {flow_status}", format_amount(money_flow_data['主力净流入-净额']))
            
            # 操作建议
            st.subheader("💡 操作建议")
            suggestions = []
            
            # 基于多个指标给出建议
            if macd_signal > 0 and rsi_val < 70:
                suggestions.append("✅ MACD多头且RSI未超买,可考虑买入")
            elif macd_signal < 0 and rsi_val > 30:
                suggestions.append("❌ MACD空头且RSI未超卖,建议观望")
            
            if rsi_val > 80:
                suggestions.append("⚠️ RSI严重超买,注意风险")
            elif rsi_val < 20:
                suggestions.append("🎯 RSI严重超卖,可能反弹")
            
            if flow_status == "净流入":
                suggestions.append("💰 主力资金流入,积极信号")
            elif flow_status == "净流出":
                suggestions.append("💸 主力资金流出,谨慎操作")
            
            for suggestion in suggestions:
                st.write(suggestion)
            
            # 价格走势图
            st.subheader("📊 价格走势")
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
                y=bollinger_data['Upper'],
                name='布林带上轨',
                line=dict(color='rgba(255,0,0,0.5)')
            ))
            fig.add_trace(go.Scatter(
                x=df.index,
                y=bollinger_data['Lower'],
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
            if st.button(f"⭐ 添加 {stock_name} 到自选股", key=f"add_modal_{symbol}"):
                watchlist = config.get('watchlist', [])
                if symbol not in watchlist:
                    watchlist.append(symbol)
                    config.set('watchlist', watchlist)
                    st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
                else:
                    st.info(f"{stock_name} ({symbol}) 已在自选股中")
        else:
            st.warning("数据不足,无法分析")

st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# 初始化session state
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

# 初始化回测结果存储
if 'pattern_backtest_result' not in st.session_state:
    st.session_state.pattern_backtest_result = None
if 'portfolio_backtest_result' not in st.session_state:
    st.session_state.portfolio_backtest_result = None
if 'parameter_optimization_result' not in st.session_state:
    st.session_state.parameter_optimization_result = None
if 'pattern_combination_result' not in st.session_state:
    st.session_state.pattern_combination_result = None

# 添加系统菜单说明
# st.caption("💡 右上角菜单说明：")
# st.caption("  • ⚙️ Settings（设置）：调整显示主题、字体大小等")
# st.caption("  • 🚀 Deploy（部署）：将应用部署到云端（需要账号）")
# st.caption("  • ❌ Clear cache（清除缓存）：刷新数据和重置状态")

# 添加功能标签页分组（避免标签过多溢出）
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    overflow-x: auto;
    flex-wrap: nowrap;
}
.stTabs [data-baseweb="tab"] {
    flex-shrink: 0;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# 主要功能标签页
tab_single, tab_compare, tab_backtest, tab_sector, tab_lhb, tab_dragon, tab_auction, tab_sentiment, tab_hot_topics, tab_alert, tab_vp, tab_ma, tab_new_stock, tab_capital, tab_limit_up, tab_smart, tab_risk, tab_history, tab_settings = st.tabs(["📊 单股分析", "🔍 多股对比", "🧪 策略回测", "🔄 板块轮动", "🏆 龙虎榜", "🔥 龙头战法", "⚡ 集合竞价", "📈 情绪分析", "🎯 热点题材", "🔔 智能预警", "📊 量价关系", "📈 均线战法", "🆕 次新股", "💰 游资席位", "🎯 打板预测", "🤖 智能推荐", "⚠️ 风险管理", "📜 历史记录", "⚙️ 系统设置"])

with st.sidebar:
    st.header("🎮 控制台")
    
    # 全局加载状态
    if st.session_state.get('loading', False):
        st.info("⏳ 数据加载中...")
    
    # 获取自选股列表
    watchlist = config.get('watchlist', [])
    
    # 从配置文件加载默认值，如果session state中有选中的股票，则使用选中的
    # 如果没有选中的股票，优先使用自选股最后一个，否则使用配置文件的默认值
    if st.session_state.selected_stock:
        default_symbol = st.session_state.selected_stock
    elif watchlist:
        default_symbol = watchlist[-1]  # 使用自选股最后一个
    else:
        default_symbol = config.get('default_symbol', '600519')
    
    # 搜索模式选择
    search_mode = st.radio("搜索方式", ["按代码", "按名称"], horizontal=True)
    
    if search_mode == "按代码":
        symbol = st.text_input("股票代码", value=default_symbol, help="请输入6位A股代码")
    else:
        # 按名称搜索
        search_name = st.text_input("股票名称", placeholder="输入股票名称，如：贵州茅台", help="支持模糊搜索")
        
        if search_name:
            with st.spinner('正在搜索...'):
                matched_codes = QuantAlgo.get_stock_code_by_name(search_name)
            
            if matched_codes:
                # 显示匹配的股票列表
                st.write(f"找到 {len(matched_codes)} 只匹配的股票：")
                stock_options = []
                for code in matched_codes:
                    name = QuantAlgo.get_stock_name(code)
                    stock_options.append(f"{name} ({code})")
                
                selected_stock = st.selectbox("选择股票", stock_options)
                
                # 从选中项中提取股票代码
                if selected_stock:
                    symbol = selected_stock.split('(')[1].rstrip(')')
            else:
                st.warning("未找到匹配的股票")
                symbol = default_symbol
        else:
            symbol = default_symbol
    
    start_date = st.date_input("开始日期", pd.to_datetime(config.get('default_start_date', '2024-01-01')))
    
    # 策略参数
    st.subheader("⚙️ 策略参数")
    atr_mult = st.slider("ATR 倍数", 0.1, 2.0, float(config.get('atr_multiplier', 0.5)), 0.1)
    grid_ratio = st.slider("网格比例", 0.05, 0.5, float(config.get('grid_ratio', 0.1)), 0.05)
    
    run_ai = st.button("🧠 智能分析")
    
    st.markdown("---")
    
    # 自选股管理
    st.subheader("⭐ 自选股")
    
    # 数据刷新功能
    col_refresh, col_auto = st.columns([1, 1])
    with col_refresh:
        if st.button("🔄 刷新数据"):
            st.session_state.cache_clear()
            st.success("✅ 数据已刷新")
            st.rerun()
    
    with col_auto:
        auto_refresh = st.checkbox("自动刷新（每5分钟）", value=st.session_state.get('auto_refresh', False))
        st.session_state.auto_refresh = auto_refresh
        if auto_refresh:
            last_refresh = st.session_state.get('last_refresh', 0)
            current_time = pd.Timestamp.now().timestamp()
            if current_time - last_refresh > 300:  # 5分钟
                st.session_state.cache_clear()
                st.info("⏱️ 自动刷新中...")
                st.rerun()
    
    st.markdown("---")
    
    if watchlist:
        st.write("已关注的股票：")
        
        # 批量选择
        selected_stocks = st.multiselect("选择要删除的股票", watchlist, key="batch_select")
        
        if selected_stocks:
            if st.button("🗑️ 批量删除", key="batch_remove"):
                new_watchlist = [s for s in watchlist if s not in selected_stocks]
                config.set('watchlist', new_watchlist)
                st.success(f"✅ 已删除 {len(selected_stocks)} 只股票")
                st.rerun()
        
        st.markdown("---")
        
        for stock in watchlist:
            stock_name = QuantAlgo.get_stock_name(stock)
            col_watch, col_remove = st.columns([3, 1])
            with col_watch:
                if st.button(f"📌 {stock_name} ({stock})", key=f"select_{stock}"):
                    st.session_state.selected_stock = stock
                    st.session_state.last_refresh = pd.Timestamp.now().timestamp()
                    st.rerun()
            with col_remove:
                if st.button("❌", key=f"remove_{stock}"):
                    watchlist.remove(stock)
                    config.set('watchlist', watchlist)
                    st.success(f"已删除 {stock_name} ({stock})")
                    st.rerun()
    
    add_stock = st.text_input("添加自选股", placeholder="输入股票代码", help="例如：600519")
    if st.button("➕ 添加") and add_stock:
        if add_stock not in watchlist:
            stock_name = QuantAlgo.get_stock_name(add_stock)
            watchlist.append(add_stock)
            config.set('watchlist', watchlist)
            st.success(f"已添加 {stock_name} ({add_stock}) 到自选股")
        else:
            stock_name = QuantAlgo.get_stock_name(add_stock)
            st.warning(f"{stock_name} ({add_stock}) 已在自选股中")
    
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
    
    # 提示用户使用本地分析系统
    st.info("💡 现在使用本地智能分析系统，无需 API Key，分析更快速、更稳定！")

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

    # 添加"开始分析"按钮，避免首次访问自动加载数据
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
                    st.info(f"📊 收盘数据 ({realtime_data['timestamp']})")
            else:
                current_price = df.iloc[-1]['close']
                prev_close = df.iloc[-2]['close']
                change_pct = (current_price - prev_close) / prev_close * 100
                st.info("⚪ 使用历史数据（数据获取失败）")
                current_price = df.iloc[-1]['close']
                prev_close = df.iloc[-2]['close']
                change_pct = (current_price - prev_close) / prev_close * 100
                st.info("⚪ 使用历史数据（实时数据获取失败）")
            
            # 计算各项技术指标
            atr = QuantAlgo.calculate_atr(df)
            resistance_levels = QuantAlgo.calculate_resistance_support(df)
            grid_plan = QuantAlgo.generate_grid_strategy(current_price, atr)
            macd_data = QuantAlgo.calculate_macd(df)
            rsi_data = QuantAlgo.calculate_rsi(df)
            bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
            box_pattern = QuantAlgo.detect_box_pattern(df)
            kdj_data = QuantAlgo.calculate_kdj(df)
            volume_data = QuantAlgo.analyze_volume(df)
            turnover_data = QuantAlgo.get_turnover_rate(df)
            turnover_volume_analysis = QuantAlgo.analyze_turnover_and_volume(
                turnover_data.get('换手率'), 
                volume_data.get('量比', 1)
            )
            money_flow_data = QuantAlgo.analyze_money_flow(df, symbol=symbol, market="sh" if symbol.startswith("6") else "sz")
            double_bottom = QuantAlgo.detect_double_bottom(df)
            double_top = QuantAlgo.detect_double_top(df)
            head_shoulders = QuantAlgo.detect_head_shoulders(df)
            
            # 分离支撑位和阻力位
            support_levels = [x for x in resistance_levels if x < current_price]
            resistance_levels = [x for x in resistance_levels if x > current_price]

            # 获取股票名称
            stock_name = QuantAlgo.get_stock_name(symbol)

            # 顶部指标卡片
            col_title, col_add = st.columns([3, 1])
            with col_title:
                st.subheader(f"📈 核心指标看板 - {stock_name} ({symbol})")
            with col_add:
                if st.button("⭐ 加自选", key=f"add_to_watchlist_{symbol}"):
                    watchlist = config.get('watchlist', [])
                    if symbol not in watchlist:
                        watchlist.append(symbol)
                        config.set('watchlist', watchlist)
                        st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
                    else:
                        st.info(f"{stock_name} ({symbol}) 已在自选股中")
            
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

            # 个股扫雷
            st.divider()
            st.subheader("⚡ 个股扫雷")
            with st.spinner('正在扫描股票风险...'):
                risk_check = QuantAlgo.check_stock_risks(symbol)
            
            # 显示风险等级
            risk_colors = {
                '低': '🟢',
                '中': '🟡',
                '高': '🔴',
                '未知': '⚪'
            }
            col_risk_level, col_risk_count = st.columns(2)
            with col_risk_level:
                st.metric("风险等级", f"{risk_colors.get(risk_check['风险等级'], '⚪')} {risk_check['风险等级']}")
            with col_risk_count:
                risk_count = len([r for r in risk_check['风险列表'] if not r.startswith('✅')])
                st.metric("风险项数", f"{risk_count} 项")
            
            # 显示详细风险列表
            if risk_check['风险列表']:
                for risk in risk_check['风险列表']:
                    if risk.startswith('🔴'):
                        st.error(risk)
                    elif risk.startswith('🟠'):
                        st.warning(risk)
                    elif risk.startswith('🟡'):
                        st.warning(risk)
                    elif risk.startswith('🟢'):
                        st.info(risk)
                    else:
                        st.success(risk)
            
            # 根据风险等级给出建议
            if risk_check['风险等级'] == '高':
                st.error("⚠️ 风险等级较高，建议谨慎操作或避开")
            elif risk_check['风险等级'] == '中':
                st.warning("⚠️ 风险等级中等，建议控制仓位")
            else:
                st.success("✅ 风险等级较低，可正常关注")

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

            # 第二行：KDJ、成交量、资金流向
            col_kdj, col_vol, col_flow = st.columns(3)
            
            with col_kdj:
                st.info("**KDJ 指标**")
                st.write(f"K: {kdj_data['K']}")
                st.write(f"D: {kdj_data['D']}")
                st.write(f"J: {kdj_data['J']}")
                st.write(f"信号: {kdj_data['信号']}")
                if "金叉" in kdj_data['信号']:
                    st.success("✅ 金叉，买入信号")
                elif "死叉" in kdj_data['信号']:
                    st.warning("⚠️ 死叉，卖出信号")
                elif "超买" in kdj_data['信号']:
                    st.warning("⚠️ 超买，注意风险")
                elif "超卖" in kdj_data['信号']:
                    st.success("✅ 超卖，可能反弹")
            
            with col_vol:
                st.info("**成交量与换手率**")
                st.write(f"量比: {volume_data['量比']}")
                st.write(f"换手率: {turnover_data.get('换手率', 'N/A')}%")
                st.write(f"信号: {volume_data['信号']}")
                st.caption(volume_data['含义'])
                if volume_data['量比'] > 2:
                    st.warning("⚠️ 放量显著，关注主力动向")
                elif volume_data['量比'] < 0.5:
                    st.info("📉 缩量，观望为主")
            
            with col_flow:
                st.info("**资金流向（真实数据）**")
                
                # 添加CSS样式调整字体大小
                st.markdown("""
                <style>
                div[data-testid="stMetricValue"] {
                    font-size: 22px !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if money_flow_data['数据状态'] == '正常':
                    # 显示总流向
                    if money_flow_data['资金流向'] == "净流入":
                        st.success(f"✅ {money_flow_data['资金流向']}")
                    elif money_flow_data['资金流向'] == "净流出":
                        st.warning(f"⚠️ {money_flow_data['资金流向']}")
                    else:
                        st.info(f"📊 {money_flow_data['资金流向']}")
                    
                    st.caption(money_flow_data['说明'])
                    
                    # 显示主力资金
                    col_main, col_large, col_medium, col_small = st.columns(4)
                    
                    with col_main:
                        st.metric("主力净流入", format_amount(money_flow_data['主力净流入-净额']), 
                                 f"{money_flow_data['主力净流入-净占比']:.2f}%")
                    with col_large:
                        st.metric("超大单", format_amount(money_flow_data['超大单净流入-净额']),
                                 f"{money_flow_data['超大单净流入-净占比']:.2f}%")
                    with col_medium:
                        st.metric("大单", format_amount(money_flow_data['大单净流入-净额']),
                                 f"{money_flow_data['大单净流入-净占比']:.2f}%")
                    with col_small:
                        st.metric("小单", format_amount(money_flow_data['小单净流入-净额']),
                                 f"{money_flow_data['小单净流入-净占比']:.2f}%")
                    
                    # 资金分析
                    main_flow = money_flow_data['主力净流入-净额']
                    if abs(main_flow) > 10000000:  # 主力资金超过1000万
                        st.success("💰 主力资金大幅介入，值得关注！")
                    elif abs(main_flow) > 5000000:
                        st.info("📈 主力资金参与度较高")
                    elif abs(main_flow) > 1000000:
                        st.caption("💡 主力资金温和参与")
                    else:
                        st.caption("💡 主力资金参与度较低")
                    
                    # 散户资金分析
                    small_flow = money_flow_data['小单净流入-净额']
                    if small_flow > 0:
                        st.caption("👥 散户资金流入，跟风情绪浓厚")
                    elif small_flow < 0:
                        st.caption("👥 散户资金流出，情绪低迷")
                
                else:
                    st.error(f"❌ {money_flow_data['数据状态']}")
                    if '错误信息' in money_flow_data:
                        st.caption(money_flow_data['错误信息'])
                    else:
                        st.caption(money_flow_data['说明'])

            # 换手率和量比综合分析
            st.divider()
            st.subheader("📊 换手率与量比综合分析")
            
            if turnover_volume_analysis.get('分析状态') == '换手率数据缺失':
                st.error("❌ 换手率数据缺失，无法进行综合分析")
                if '说明' in turnover_data and turnover_data['说明']:
                    st.info(f"💡 {turnover_data['说明']}")
                    st.info("📌 提示：请选择更早的日期重新获取数据，系统会自动更新换手率信息")
            else:
                # 显示基本信息
                col_turnover, col_volume, col_risk = st.columns(3)
                
                with col_turnover:
                    st.metric("换手率", f"{turnover_volume_analysis['换手率']}%", 
                             turnover_volume_analysis['换手率等级'])
                    st.caption(turnover_volume_analysis['换手率说明'])
                
                with col_volume:
                    st.metric("量比", turnover_volume_analysis['量比'], 
                             turnover_volume_analysis['量比等级'])
                    st.caption(turnover_volume_analysis['量比说明'])
                
                with col_risk:
                    risk_colors = {
                        '低': '🟢',
                        '中等': '🟡',
                        '中等偏高': '🟠',
                        '高': '🔴'
                    }
                    st.metric("风险等级", 
                             f"{risk_colors.get(turnover_volume_analysis['风险等级'], '⚪')} {turnover_volume_analysis['风险等级']}")
                
                # 显示综合分析结果
                st.subheader("🔍 综合分析")
                for i, analysis in enumerate(turnover_volume_analysis['综合分析'], 1):
                    st.write(f"{i}. {analysis}")
                
                # 根据风险等级给出建议
                if turnover_volume_analysis['风险等级'] == '高':
                    st.warning("⚠️ 当前风险较高，建议谨慎操作，可考虑减仓或观望")
                elif turnover_volume_analysis['风险等级'] == '中等偏高':
                    st.info("💡 风险偏高，建议控制仓位，密切关注走势")
                elif turnover_volume_analysis['风险等级'] == '中等':
                    st.success("✅ 风险适中，可正常操作")
                else:
                    st.success("✅ 风险较低，适合稳健操作")

            # 形态识别提示
            st.divider()
            st.subheader("🎨 形态识别")
            
            # 双底/双顶
            if double_bottom['is_double_bottom']:
                st.success(double_bottom['message'])
            elif double_top['is_double_top']:
                st.warning(double_top['message'])
            
            # 头肩形态
            if head_shoulders['pattern'] == 'head_shoulders_top':
                st.error(head_shoulders['message'])
            elif head_shoulders['pattern'] == 'head_shoulders_bottom':
                st.success(head_shoulders['message'])

            # 个股操作预案
            st.divider()
            st.subheader("📋 个股操作预案")
            
            with st.spinner('正在生成操作预案...'):
                trading_plan = QuantAlgo.generate_trading_plan(df, symbol=symbol)
                
                if '错误' not in trading_plan:
                    # 显示操作建议
                    col1, col2, col3 = st.columns(3)
                    
                    # 根据操作建议设置颜色
                    if trading_plan['操作建议'] == '买入':
                        col1.metric("操作建议", trading_plan['操作建议'], delta="看多")
                        col1.markdown('<style>div[data-testid="stMetricValue"] {color: green;}</style>', unsafe_allow_html=True)
                    elif trading_plan['操作建议'] == '卖出':
                        col1.metric("操作建议", trading_plan['操作建议'], delta="看空")
                        col1.markdown('<style>div[data-testid="stMetricValue"] {color: red;}</style>', unsafe_allow_html=True)
                    else:
                        col1.metric("操作建议", trading_plan['操作建议'])
                    
                    col2.metric("当前价格", f"¥{trading_plan['当前价格']:.2f}")
                    
                    # 风险等级
                    risk_colors = {
                        '高': '🔴',
                        '中等': '🟡',
                        '低': '🟢'
                    }
                    col3.metric("风险等级", f"{risk_colors.get(trading_plan['风险等级'], '⚪')} {trading_plan['风险等级']}")
                    
                    # 显示买卖点
                    if trading_plan['买入点']:
                        col_buy, col_sell, col_stop, col_profit = st.columns(4)
                        col_buy.metric("买入点", f"¥{trading_plan['买入点']:.2f}")
                        col_sell.metric("卖出点", f"¥{trading_plan['卖出点']:.2f}" if trading_plan['卖出点'] else "-")
                        col_stop.metric("止损点", f"¥{trading_plan['止损点']:.2f}")
                        col_profit.metric("止盈点", f"¥{trading_plan['止盈点']:.2f}")
                    
                    # 显示持仓周期
                    st.info(f"📅 建议持仓周期：{trading_plan['持仓周期']}")
                    
                    # 显示分析依据
                    if trading_plan['分析依据']:
                        st.subheader("🔍 分析依据")
                        for i, signal in enumerate(trading_plan['分析依据'], 1):
                            signal_color = {
                                '强': '🔴',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            st.write(f"{i}. **{signal['指标']}**: {signal['信号']} ({signal_color.get(signal['强度'], '⚪')} 强度: {signal['强度']})")
                    
                    # 显示做T机会
                    if '做T机会' in trading_plan:
                        st.divider()
                        st.subheader("🎯 做T机会分析")
                        
                        t_data = trading_plan['做T机会']
                        t_col1, t_col2, t_col3 = st.columns(3)
                        
                        # 做T机会等级
                        t_col1.metric("做T机会", t_data['操作建议'], delta=f"评分: {t_data['做T评分']}")
                        
                        # 做T信号
                        if t_data['做T信号']:
                            t_col2.write("**做T信号**")
                            for signal in t_data['做T信号']:
                                t_col2.write(f"• {signal}")
                        
                        # 风险提示
                        t_col3.warning(t_data['风险提示'])
                        
                        # 做T点位
                        if t_data['做T买入点'] and t_data['做T卖出点']:
                            st.subheader("📍 做T参考点位")
                            st.info(f"💡 **买入点（低吸）**: ¥{t_data['做T买入点'][0]:.2f} / ¥{t_data['做T买入点'][1]:.2f} / ¥{t_data['做T买入点'][2]:.2f}")
                            st.info(f"💡 **卖出点（高抛）**: ¥{t_data['做T卖出点'][0]:.2f} / ¥{t_data['做T卖出点'][1]:.2f} / ¥{t_data['做T卖出点'][2]:.2f}")
                            st.caption("注：做T点位仅供参考，实际操作请结合实时行情和仓位管理")
                else:
                    st.error(f"❌ 生成操作预案失败: {trading_plan['错误']}")

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
            st.plotly_chart(fig, width="stretch")

            # 龙头战法分析
            st.divider()
            st.subheader("🔥 龙头战法分析")
            st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
            
            dragon_analysis = QuantAlgo.analyze_dragon_stock(df, current_price)
            
            if dragon_analysis.get('龙头评级'):
                # 显示龙头评级
                col_dragon_rating, col_dragon_score = st.columns(2)
                with col_dragon_rating:
                    st.metric("龙头评级", dragon_analysis['龙头评级'], delta=dragon_analysis['评级说明'])
                with col_dragon_score:
                    st.metric("评级得分", f"{dragon_analysis['评级得分']}/100")
                
                # 显示五个条件
                st.subheader("📋 龙头股五个条件")
                
                col_cond1, col_cond2 = st.columns(2)
                with col_cond1:
                    st.info("**条件1：涨停板**")
                    for desc in dragon_analysis['条件1_涨停板']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件1_涨停板']['得分']}/20")
                
                with col_cond2:
                    st.info("**条件2：价格**")
                    for desc in dragon_analysis['条件2_价格']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件2_价格']['得分']}/20")
                
                col_cond3, col_cond4 = st.columns(2)
                with col_cond3:
                    st.info("**条件3：成交量**")
                    for desc in dragon_analysis['条件3_成交量']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件3_成交量']['得分']}/20")
                
                with col_cond4:
                    st.info("**条件4：KDJ**")
                    for desc in dragon_analysis['条件4_KDJ']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件4_KDJ']['得分']}/20")
                
                st.info("**条件5：换手率**")
                for desc in dragon_analysis['条件5_换手率']['说明']:
                    st.write(desc)
                st.caption(f"得分: {dragon_analysis['条件5_换手率']['得分']}/20")
                
                # 显示综合分析
                st.divider()
                st.subheader("🔍 综合分析")
                for i, analysis in enumerate(dragon_analysis['综合分析'], 1):
                    st.write(f"{i}. {analysis}")
                
                # 显示操作建议
                st.divider()
                st.subheader("💡 操作建议")
                for suggestion in dragon_analysis['操作建议']:
                    st.write(suggestion)
            else:
                st.error(f"❌ {dragon_analysis.get('评级得分', '无法分析')}")

            # 策略和AI分析
            col_strategy, col_ai = st.columns([1, 1])
            
            with col_strategy:
                st.subheader("🛠️ 网格交易策略")
                st.info("基于 ATR 波动率自适应计算：")
                st.table(pd.DataFrame([grid_plan]).T.rename(columns={0: '数值/建议'}))
            
            with col_ai:
                st.subheader("🤖 智能分析")
                if run_ai:
                    with st.spinner("正在智能分析..."):
                        # 准备技术数据
                        tech_data = {
                            'current_price': current_price,
                            'resistance_levels': resistance_levels[:3],
                            'support_levels': support_levels[-3:],
                            'atr': atr,
                            'macd': macd_data,
                            'rsi': rsi_data,
                            'bollinger': bollinger_data,
                            'kdj': kdj_data,
                            'volume': volume_data,
                            'money_flow': money_flow_data,
                            'box_pattern': box_pattern,
                            'patterns': {
                                'double_bottom': double_bottom,
                                'double_top': double_top,
                                'head_shoulders': head_shoulders
                            }
                        }
                        analysis = ai_agent.analyze_stock(symbol, round(change_pct, 2), tech_data)
                        st.success(analysis)
                else:
                    st.write("点击侧边栏的「🧠 智能分析」按钮，获取智能投资建议。")

with tab_backtest:
    # 回测类型选择
    backtest_type = st.radio("回测类型", 
                            ["网格策略回测", "战法成功率回测", "策略组合回测", "参数优化", "战法组合分析"],
                            horizontal=True)
    
    if backtest_type == "网格策略回测":
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
        
        if st.button("运行网格回测"):
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
                        st.dataframe(result['交易记录'], width="stretch")
                    
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
                    st.plotly_chart(fig_capital, width="stretch")
                    
                else:
                    st.error("数据不足，无法进行回测。请选择更早的日期或检查股票代码。")
    
    elif backtest_type == "战法成功率回测":
        st.subheader("🎯 战法成功率回测")
        
        st.info("💡 统计历史数据中各种战法信号的成功率，帮助你选择最有效的战法")
        
        # 回测参数设置
        # 搜索模式选择
        pattern_search_mode = st.radio("搜索方式", ["按代码", "按名称"], horizontal=True, key="pattern_search_mode")
        
        if pattern_search_mode == "按代码":
            pattern_symbol = st.text_input("回测股票代码", value="600519", key="pattern_symbol_input")
        else:
            # 按名称搜索
            pattern_search_name = st.text_input("股票名称", placeholder="输入股票名称，如：贵州茅台", key="pattern_search_name", help="支持模糊搜索")
            
            if pattern_search_name:
                with st.spinner('正在搜索...'):
                    pattern_matched_codes = QuantAlgo.get_stock_code_by_name(pattern_search_name)
                
                if pattern_matched_codes:
                    # 显示匹配的股票列表
                    st.write(f"找到 {len(pattern_matched_codes)} 只匹配的股票：")
                    pattern_stock_options = []
                    for code in pattern_matched_codes:
                        name = QuantAlgo.get_stock_name(code)
                        pattern_stock_options.append(f"{name} ({code})")
                    
                    pattern_selected_stock = st.selectbox("选择股票", pattern_stock_options, key="pattern_selected_stock")
                    
                    # 从选中项中提取股票代码
                    if pattern_selected_stock:
                        pattern_symbol = pattern_selected_stock.split('(')[1].rstrip(')')
                else:
                    st.warning("未找到匹配的股票")
                    pattern_symbol = "600519"
            else:
                pattern_symbol = "600519"
        
        pattern_start = st.date_input("回测开始日期", pd.to_datetime("2023-01-01"))
        
        col_pattern, col_hold, col_profit, col_loss = st.columns(4)
        with col_pattern:
            pattern_type = st.selectbox(
                "战法类型",
                ["all", "dragon", "box", "double_bottom", "double_top", "head_shoulders"],
                format_func=lambda x: {
                    "all": "全部战法",
                    "dragon": "龙头战法",
                    "box": "箱体突破",
                    "double_bottom": "双底",
                    "double_top": "双顶",
                    "head_shoulders": "头肩形态"
                }[x],
                key="pattern_type_select"
            )
        
        with col_hold:
            hold_days = st.slider("持有天数", 1, 20, 5, 1)
        
        with col_profit:
            profit_threshold = st.slider("盈利阈值(%)", 1, 10, 3, 1) / 100
        
        with col_loss:
            loss_threshold = st.slider("亏损阈值(%)", -10, -1, -3, 1) / 100
        
        if st.button("运行战法回测"):
            s_date_str = pattern_start.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
            
            with st.spinner('正在运行战法回测...'):
                df = db.get_history_data(pattern_symbol, start_date=s_date_str, end_date=e_date_str)
                
                if not df.empty and len(df) > 60:
                    # 运行战法回测
                    result = backtest_engine.run_pattern_backtest(
                        df, 
                        pattern_type=pattern_type,
                        hold_days=hold_days,
                        profit_threshold=profit_threshold,
                        loss_threshold=loss_threshold
                    )
                    
                    # 保存结果到session_state
                    st.session_state.pattern_backtest_result = result
                    st.session_state.pattern_backtest_symbol = pattern_symbol
                    st.session_state.pattern_backtest_params = {
                        'pattern_type': pattern_type,
                        'hold_days': hold_days,
                        'profit_threshold': profit_threshold,
                        'loss_threshold': loss_threshold
                    }
                    st.success("回测完成!")
        
        # 显示回测结果(如果有)
        if st.session_state.pattern_backtest_result is not None:
            result = st.session_state.pattern_backtest_result
            
            # 显示回测报告
            report = backtest_engine.generate_pattern_backtest_report(result)
            st.markdown(report)
            
            # 计算并显示风险指标
            st.subheader("⚠️ 风险指标")
            risk_metrics = backtest_engine.calculate_risk_metrics(result)
            
            col_risk1, col_risk2, col_risk3, col_risk4 = st.columns(4)
            with col_risk1:
                st.metric("最大回撤", f"{risk_metrics['最大回撤']}%", delta="风险控制")
            with col_risk2:
                st.metric("夏普比率", risk_metrics['夏普比率'], delta="风险收益比")
            with col_risk3:
                st.metric("卡尔马比率", risk_metrics['卡尔马比率'], delta="回撤收益比")
            with col_risk4:
                st.metric("年化收益率", f"{risk_metrics['年化收益率']}%", delta="年化表现")
            
            # 风险等级评估
            if risk_metrics['最大回撤'] < 10:
                risk_level = "🟢 低风险"
            elif risk_metrics['最大回撤'] < 20:
                risk_level = "🟡 中风险"
            else:
                risk_level = "🔴 高风险"
            
            st.info(f"💡 风险等级: {risk_level} | 夏普比率{'优秀' if risk_metrics['夏普比率'] > 1 else '一般' if risk_metrics['夏普比率'] > 0 else '较差'}")
            
            # 显示分战法统计
            if not result['分战法统计'].empty:
                st.subheader("📊 各战法成功率排名")
                
                # 显示排名表格
                pattern_ranking = result['分战法统计'].copy()
                st.dataframe(pattern_ranking, width="stretch")
                
                # 高亮显示成功率最高的战法
                if not pattern_ranking.empty:
                    best_pattern = pattern_ranking.iloc[0]
                    st.success(f"🏆 **成功率最高的战法**: {best_pattern.name} (成功率: {best_pattern['成功率']}%, 信号数: {int(best_pattern['信号数'])})")
                
                # 战法成功率对比图
                st.subheader("📈 各战法成功率对比")
                fig_pattern = go.Figure()
                
                fig_pattern.add_trace(go.Bar(
                    x=pattern_ranking.index,
                    y=pattern_ranking['成功率'],
                    name='成功率',
                    marker_color='blue',
                    text=pattern_ranking['成功率'].apply(lambda x: f"{x}%"),
                    textposition='outside'
                ))
                
                fig_pattern.update_layout(
                    title="各战法成功率对比",
                    xaxis_title="战法类型",
                    yaxis_title="成功率(%)",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_pattern, width="stretch")
                
                # 战法收益率对比图
                st.subheader("💰 各战法平均收益率对比")
                fig_returns = go.Figure()
                
                fig_returns.add_trace(go.Bar(
                    x=pattern_ranking.index,
                    y=pattern_ranking['平均收益率'],
                    name='平均收益率',
                    marker_color='green',
                    text=pattern_ranking['平均收益率'].apply(lambda x: f"{x}%"),
                    textposition='outside'
                ))
                
                fig_returns.update_layout(
                    title="各战法平均收益率对比",
                    xaxis_title="战法类型",
                    yaxis_title="平均收益率(%)",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_returns, width="stretch")
            
            # 显示详细信号记录
            if not result['总体统计']['详细统计'].empty:
                st.subheader("📝 详细信号记录")
                
                # 获取所有战法类型
                all_patterns = result['总体统计']['详细统计']['战法类型'].unique().tolist()
                
                # 添加战法筛选
                col_filter1, col_filter2 = st.columns(2)
                with col_filter1:
                    pattern_filter = st.selectbox("筛选战法", ["全部"] + all_patterns, key="pattern_type_filter")
                
                with col_filter2:
                    result_filter = st.selectbox("筛选结果", ["全部", "盈利", "亏损", "平局"], key="pattern_result_filter")
                
                # 应用筛选
                filtered_df = result['总体统计']['详细统计'].copy()
                
                if pattern_filter != "全部":
                    filtered_df = filtered_df[filtered_df['战法类型'] == pattern_filter]
                
                if result_filter != "全部":
                    filtered_df = filtered_df[filtered_df['结果'] == result_filter]
                
                # 添加触发情景说明
                def get_trigger_context(row):
                    """根据战法类型生成触发情景说明"""
                    pattern = row['战法类型']
                    context = ""
                    
                    if pattern == '龙头战法':
                        context = f"涨停触发:当日涨幅{row.get('change_pct', 0):.2f}%,价格¥{row['信号价格']:.2f},量比{row.get('volume_ratio', 0):.2f}"
                    elif pattern == '箱体突破':
                        if row['信号类型'] == '买入':
                            context = f"向上突破:突破箱体上沿¥{row['box_high']:.2f},当前价¥{row['信号价格']:.2f}"
                        else:
                            context = f"向下突破:跌破箱体下沿¥{row['box_low']:.2f},当前价¥{row['信号价格']:.2f}"
                    elif pattern == '双底':
                        context = f"双底形成:第一底¥{row['first_bottom']:.2f},第二底¥{row['second_bottom']:.2f},突破颈线¥{row['neck_line']:.2f}"
                    elif pattern == '双顶':
                        context = f"双顶形成:第一顶¥{row['first_top']:.2f},第二顶¥{row['second_top']:.2f},跌破颈线¥{row['neck_line']:.2f}"
                    elif pattern == '头肩顶':
                        context = f"头肩顶形成:左肩¥{row['left_shoulder']:.2f},头部¥{row['head']:.2f},右肩¥{row['right_shoulder']:.2f}"
                    elif pattern == '头肩底':
                        context = f"头肩底形成:左肩¥{row['left_shoulder']:.2f},头部¥{row['head']:.2f},右肩¥{row['right_shoulder']:.2f}"
                    else:
                        context = f"{pattern}信号触发于{row['信号日期']}"
                    
                    return context
                
                # 添加触发情景列
                filtered_df['触发情景'] = filtered_df.apply(get_trigger_context, axis=1)
                
                # 重新排列列顺序
                cols = ['信号日期', '战法类型', '信号类型', '触发情景', '信号价格', '收益率', '结果', '持有天数']
                filtered_df = filtered_df[[col for col in cols if col in filtered_df.columns]]
                
                st.dataframe(filtered_df, width="stretch")
                
                # 成功率可视化
                st.subheader("📈 成功率分布")
                success_stats = result['总体统计']
                
                fig_success = go.Figure(data=[
                    go.Bar(
                        name='盈利',
                        x=['成功'],
                        y=[success_stats['盈利信号数']],
                        marker_color='green'
                    ),
                    go.Bar(
                        name='亏损',
                        x=['失败'],
                        y=[success_stats['亏损信号数']],
                        marker=dict(color='rgba(255, 87, 51, 0.8)')
                    ),
                    go.Bar(
                        name='平局',
                        x=['平局'],
                        y=[success_stats['平局信号数']],
                        marker_color='gray'
                    )
                ])
                
                fig_success.update_layout(
                    title=f"信号结果分布 (成功率: {success_stats['成功率']}%)",
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_success, width="stretch")
                
                # 收益率分布图
                if not filtered_df.empty:
                    st.subheader("💰 收益率分布")
                    fig_returns = go.Figure()
                    
                    for pattern in filtered_df['战法类型'].unique():
                        pattern_data = filtered_df[filtered_df['战法类型'] == pattern]
                        fig_returns.add_trace(go.Box(
                            y=pattern_data['收益率'],
                            name=pattern,
                            boxpoints='outliers'
                        ))
                    
                    fig_returns.update_layout(
                        title="各战法收益率分布",
                        yaxis_title="收益率(%)",
                        height=400
                    )
                    st.plotly_chart(fig_returns, width="stretch")
            
            # 显示信号数量趋势
            if result['所有信号']:
                st.subheader("📊 信号数量趋势")
                signal_df = pd.DataFrame(result['所有信号'])
                signal_df['日期'] = pd.to_datetime(signal_df['date'])
                signal_df['月份'] = signal_df['日期'].dt.to_period('M')
                
                monthly_signals = signal_df.groupby(['月份', 'pattern']).size().reset_index(name='信号数')
                monthly_signals['月份'] = monthly_signals['月份'].astype(str)
                
                fig_trend = go.Figure()
                
                for pattern in monthly_signals['pattern'].unique():
                    pattern_data = monthly_signals[monthly_signals['pattern'] == pattern]
                    fig_trend.add_trace(go.Scatter(
                        x=pattern_data['月份'],
                        y=pattern_data['信号数'],
                        mode='lines+markers',
                        name=pattern
                    ))
                
                fig_trend.update_layout(
                    title="月度信号数量趋势",
                    xaxis_title="月份",
                    yaxis_title="信号数量",
                    height=400
                )
                st.plotly_chart(fig_trend, width="stretch")
    
    elif backtest_type == "策略组合回测":
        st.subheader("📊 策略组合回测")
        
        st.info("💡 同时回测多只股票,对比战法在不同股票上的表现")
        
        # 股票选择
        portfolio_symbols_input = st.text_input("输入股票代码列表（用逗号分隔）", 
                                               value="600519,000001,600036",
                                               help="例如：600519,000001,600036")
        
        portfolio_symbols = [s.strip() for s in portfolio_symbols_input.split(',') if s.strip()]
        
        # 或者选择自选股
        use_watchlist = st.checkbox("使用自选股列表")
        if use_watchlist:
            watchlist = config.get('watchlist', [])
            if watchlist:
                portfolio_symbols = watchlist
                st.info(f"已加载 {len(watchlist)} 只自选股")
        
        portfolio_start = st.date_input("回测开始日期", pd.to_datetime("2023-01-01"))
        
        col_pattern, col_hold = st.columns(2)
        with col_pattern:
            portfolio_pattern = st.selectbox(
                "战法类型",
                ["all", "dragon", "box", "double_bottom", "double_top", "head_shoulders"],
                format_func=lambda x: {
                    "all": "全部战法",
                    "dragon": "龙头战法",
                    "box": "箱体突破",
                    "double_bottom": "双底",
                    "double_top": "双顶",
                    "head_shoulders": "头肩形态"
                }[x],
                key="portfolio_pattern_select"
            )
        
        with col_hold:
            portfolio_hold_days = st.slider("持有天数", 1, 20, 5, 1)
        
        if st.button("运行组合回测"):
            s_date_str = portfolio_start.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
            
            with st.spinner('正在运行组合回测...'):
                result = backtest_engine.run_portfolio_backtest(
                    portfolio_symbols,
                    pattern_type=portfolio_pattern,
                    hold_days=portfolio_hold_days,
                    start_date=s_date_str,
                    end_date=e_date_str,
                    data_manager=db
                )
                
                # 显示组合统计
                st.subheader("📈 组合统计")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("股票数量", result['组合统计']['股票数量'])
                with col2:
                    st.metric("总信号数", result['组合统计']['总信号数'])
                with col3:
                    st.metric("平均成功率", f"{result['组合统计']['平均成功率']}%")
                with col4:
                    st.metric("组合成功率", f"{result['组合统计']['组合成功率']}%")
                
                # 显示详细结果
                if not result['详细结果'].empty:
                    st.subheader("📊 各股回测结果")
                    st.dataframe(result['详细结果'], width="stretch")
                    
                    # 成功率对比图
                    st.subheader("📊 成功率对比")
                    fig_portfolio = go.Figure()
                    
                    fig_portfolio.add_trace(go.Bar(
                        x=result['详细结果']['股票名称'],
                        y=result['详细结果']['成功率'],
                        name='成功率',
                        marker_color='blue'
                    ))
                    
                    fig_portfolio.update_layout(
                        title="各股票成功率对比",
                        xaxis_title="股票",
                        yaxis_title="成功率(%)",
                        height=400
                    )
                    st.plotly_chart(fig_portfolio, width="stretch")
                    
                    # 导出功能
                    st.subheader("💾 导出结果")
                    if st.button("导出Excel"):
                        excel_data = backtest_engine.export_backtest_results(
                            result['各股回测'][0] if result['各股回测'] else None
                        )
                        st.download_button(
                            label="下载回测结果",
                            data=excel_data.getvalue(),
                            file_name=f"组合回测结果_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
    
    elif backtest_type == "参数优化":
        st.subheader("🔧 参数优化")
        
        st.info("💡 自动寻找最优的回测参数,提高战法成功率")
        
        # 股票选择
        opt_symbol = st.text_input("优化股票代码", value="600519")
        opt_start = st.date_input("优化数据起始日期", pd.to_datetime("2023-01-01"))
        
        opt_pattern = st.selectbox(
            "战法类型",
            ["all", "dragon", "box", "double_bottom", "double_top", "head_shoulders"],
            format_func=lambda x: {
                "all": "全部战法",
                "dragon": "龙头战法",
                "box": "箱体突破",
                "double_bottom": "双底",
                "double_top": "双顶",
                "head_shoulders": "头肩形态"
            }[x],
            key="opt_pattern_select"
        )
        
        # 参数范围设置
        st.subheader("⚙️ 参数范围设置")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            hold_days_range = st.multiselect("持有天数范围", [3, 5, 7, 10, 15, 20], default=[3, 5, 7, 10])
        
        with col2:
            profit_range = st.multiselect("盈利阈值范围", [0.02, 0.03, 0.05, 0.08, 0.10], default=[0.02, 0.03, 0.05])
        
        with col3:
            loss_range = st.multiselect("亏损阈值范围", [-0.10, -0.08, -0.05, -0.03, -0.02], default=[-0.05, -0.03, -0.02])
        
        if st.button("开始优化"):
            s_date_str = opt_start.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
            
            with st.spinner('正在优化参数...'):
                # 获取数据
                df = db.get_history_data(opt_symbol, start_date=s_date_str, end_date=e_date_str)
                
                if not df.empty and len(df) > 60:
                    # 构建参数范围
                    param_ranges = {
                        'hold_days': hold_days_range,
                        'profit_threshold': profit_range,
                        'loss_threshold': loss_range
                    }
                    
                    # 运行优化
                    opt_result = backtest_engine.optimize_parameters(
                        df, pattern_type=opt_pattern, param_ranges=param_ranges
                    )
                    
                    # 显示最优参数
                    st.subheader("🏆 最优参数")
                    if opt_result['最优参数']:
                        col_opt1, col_opt2, col_opt3 = st.columns(3)
                        with col_opt1:
                            st.metric("持有天数", opt_result['最优_params']['hold_days'])
                        with col_opt2:
                            st.metric("盈利阈值", f"{opt_result['最优_params']['profit_threshold']*100:.1f}%")
                        with col_opt3:
                            st.metric("亏损阈值", f"{opt_result['最优_params']['loss_threshold']*100:.1f}%")
                        
                        # 显示最优结果
                        if opt_result['最优结果']:
                            st.subheader("📊 最优结果")
                            best_stats = opt_result['最优结果']['总体统计']
                            col_best1, col_best2, col_best3 = st.columns(3)
                            with col_best1:
                                st.metric("成功率", f"{best_stats['成功率']}%")
                            with col_best2:
                                st.metric("盈亏比", best_stats['盈亏比'])
                            with col_best3:
                                st.metric("总信号数", best_stats['总信号数'])
                    
                    # 显示所有结果
                    if not opt_result['所有结果'].empty:
                        st.subheader("📋 所有参数组合结果")
                        st.dataframe(opt_result['所有结果'], width="stretch")
                        
                        # 参数热力图
                        st.subheader("🔥 参数组合热力图")
                        pivot_table = opt_result['所有结果'].pivot_table(
                            values='综合评分',
                            index='持有天数',
                            columns='盈利阈值'
                        )
                        
                        fig_heatmap = go.Figure(data=go.Heatmap(
                            z=pivot_table.values,
                            x=pivot_table.columns,
                            y=pivot_table.index,
                            colorscale='Viridis'
                        ))
                        
                        fig_heatmap.update_layout(
                            title="参数组合评分热力图",
                            xaxis_title="盈利阈值",
                            yaxis_title="持有天数",
                            height=400
                        )
                        st.plotly_chart(fig_heatmap, width="stretch")
                else:
                    st.error("数据不足,无法进行参数优化")
    
    elif backtest_type == "战法组合分析":
        st.subheader("🎯 战法组合分析")
        
        st.info("💡 分析多个战法组合使用的效果,寻找最佳战法组合")
        
        # 股票选择
        combo_symbol = st.text_input("分析股票代码", value="600519")
        combo_start = st.date_input("分析数据起始日期", pd.to_datetime("2023-01-01"))
        
        # 选择战法组合
        st.subheader("📌 选择战法组合")
        selected_patterns = st.multiselect(
            "选择要组合的战法",
            ["dragon", "box", "double_bottom", "double_top", "head_shoulders"],
            default=["dragon", "box"],
            format_func=lambda x: {
                "dragon": "龙头战法",
                "box": "箱体突破",
                "double_bottom": "双底",
                "double_top": "双顶",
                "head_shoulders": "头肩形态"
            }[x]
        )
        
        if len(selected_patterns) < 2:
            st.warning("请至少选择2个战法进行分析")
        else:
            combo_hold_days = st.slider("持有天数", 1, 20, 5, 1)
            
            if st.button("开始分析"):
                s_date_str = combo_start.strftime("%Y%m%d")
                e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
                
                with st.spinner('正在分析战法组合...'):
                    # 获取数据
                    df = db.get_history_data(combo_symbol, start_date=s_date_str, end_date=e_date_str)
                    
                    if not df.empty and len(df) > 60:
                        # 运行组合分析
                        combo_result = backtest_engine.analyze_pattern_combination(
                            df, patterns=selected_patterns, hold_days=combo_hold_days
                        )
                        
                        # 显示单个战法结果
                        st.subheader("📊 单个战法结果")
                        single_results = []
                        for pattern in selected_patterns:
                            if pattern in combo_result['单个战法结果']:
                                stats = combo_result['单个战法结果'][pattern]['总体统计']
                                single_results.append({
                                    '战法': pattern,
                                    '成功率': f"{stats['成功率']}%",
                                    '盈亏比': stats['盈亏比'],
                                    '信号数': stats['总信号数']
                                })
                        
                        st.dataframe(pd.DataFrame(single_results), width="stretch")
                        
                        # 显示组合策略结果
                        st.subheader("🎯 组合策略结果")
                        col_combo1, col_combo2 = st.columns(2)
                        with col_combo1:
                            st.metric("组合信号数", combo_result['组合信号数'])
                        with col_combo2:
                            st.metric("组合成功率", f"{combo_result['组合策略成功率']}%")
                        
                        # 显示相关性分析
                        if not combo_result['相关性分析'].empty:
                            st.subheader("🔗 战法相关性分析")
                            st.dataframe(combo_result['相关性分析'], width="stretch")
                            
                            # 相关性热力图
                            correlation_matrix = combo_result['相关性分析'].pivot_table(
                                values='Jaccard相似度',
                                index='战法1',
                                columns='战法2'
                            )
                            
                            fig_corr = go.Figure(data=go.Heatmap(
                                z=correlation_matrix.values,
                                x=correlation_matrix.columns,
                                y=correlation_matrix.index,
                                colorscale='RdYlGn',
                                zmin=0,
                                zmax=1
                            ))
                            
                            fig_corr.update_layout(
                                title="战法相关性热力图 (Jaccard相似度)",
                                height=400
                            )
                            st.plotly_chart(fig_corr, width="stretch")
                            
                            st.info("💡 相似度越高,说明战法信号重叠越多,组合使用效果可能不如预期")
                    else:
                        st.error("数据不足,无法进行战法组合分析")

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
        
        # 进度条
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        progress_text.text(f"📊 正在分析 {len(compare_symbols)} 只股票...")
        # 技术指标对比
        comparison_df = comparator.compare_stocks(compare_symbols, s_date_str, e_date_str)
        progress_bar.progress(50)
        
        progress_text.text("📈 正在生成收益率曲线...")
        # 收益率对比图
        performance_df = comparator.get_performance_comparison(compare_symbols, s_date_str, e_date_str)
        progress_bar.progress(100)
        
        progress_bar.empty()
        progress_text.empty()
        
        if not comparison_df.empty:
            st.dataframe(comparison_df, width="stretch")
            
            # 收益率对比图
            st.subheader("📈 收益率曲线对比")
            
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
                st.plotly_chart(fig_perf, width="stretch")
        else:
            st.warning("未能获取到有效的对比数据，请检查股票代码是否正确。")

with tab_sector:
    st.subheader("🔄 板块轮动分析")
    st.caption("实时监控各行业板块资金流向，发现热点板块")
    # 自动加载数据
    with st.spinner('正在获取板块轮动数据...'):
        sector_data = QuantAlgo.get_sector_rotation()
        if sector_data['数据状态'] == '正常':
            sectors = sector_data['板块列表']
            # 格式化数据用于显示
            display_sectors = []
            for sector in sectors:
                display_sectors.append({
                    '板块名称': sector['板块名称'],
                    '涨跌幅': sector['涨跌幅'],
                    '主力净流入': format_amount(sector['主力净流入']),
                    '主力净流入占比': sector['主力净流入占比']
                })
            # 显示板块资金流向表格
            st.dataframe(
                pd.DataFrame(display_sectors),
                column_config={
                    '板块名称': st.column_config.TextColumn('板块名称', width='medium'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '主力净流入': st.column_config.TextColumn('主力净流入', width='medium'),
                    '主力净流入占比': st.column_config.NumberColumn('净流入占比', format='%.2f%%')
                },
                width="stretch",
                hide_index=True
            )
            
            # 热点板块分析
            st.subheader("🔥 热点板块分析")
            hot_sectors = sorted(sectors, key=lambda x: x['主力净流入'], reverse=True)[:5]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("**资金流入最多的板块**")
                for i, sector in enumerate(hot_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            with col2:
                cold_sectors = sorted(sectors, key=lambda x: x['主力净流入'])[:5]
                st.warning("**资金流出最多的板块**")
                for i, sector in enumerate(cold_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            # 板块资金流向图
            st.subheader("📊 板块资金流向分布")
            fig_sector = go.Figure()
            
            fig_sector.add_trace(go.Bar(
                x=[s['板块名称'][:4] for s in sectors[:10]],  # 只显示前10个，名称截取
                y=[s['主力净流入'] for s in sectors[:10]],
                marker=dict(
                    color=['rgba(75, 192, 192, 0.8)' if s['主力净流入'] > 0 else 'rgba(255, 99, 132, 0.8)' for s in sectors[:10]]
                )
            ))
            
            fig_sector.update_layout(
                title="前10大板块资金流向",
                xaxis_title="板块",
                yaxis_title="主力净流入（元）",
                height=400
            )
            st.plotly_chart(fig_sector, width="stretch")
        else:
            st.error(f"❌ {sector_data['数据状态']}")
            if '错误信息' in sector_data:
                st.caption(sector_data['错误信息'])

with tab_lhb:
    st.subheader("🏆 龙虎榜分析")
    st.caption("监控市场活跃股票和机构动向")
    
    # 日期选择
    lhb_date = st.date_input("选择日期", value=pd.Timestamp.now().date())
    
    # 自动加载数据
    with st.spinner('正在获取龙虎榜数据...'):
        date_str = lhb_date.strftime("%Y%m%d")
        lhb_data = QuantAlgo.get_lhb_data(date_str)
        
        if lhb_data['数据状态'] == '正常':
            stocks = lhb_data['股票列表']
            
            # 显示数据日期
            if '数据日期' in lhb_data:
                st.info(f"📅 数据日期：{lhb_data['数据日期']}")
            
            # 排序选项
            col_sort1, col_sort2 = st.columns(2)
            with col_sort1:
                sort_by = st.selectbox("排序方式", ["净买入额", "涨跌幅", "收盘价"])
            with col_sort2:
                sort_order = st.selectbox("排序顺序", ["降序", "升序"])
            
            # 排序
            reverse_order = (sort_order == "降序")
            if sort_by == "净买入额":
                stocks_sorted = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=reverse_order)
            elif sort_by == "涨跌幅":
                stocks_sorted = sorted(stocks, key=lambda x: x['涨跌幅'], reverse=reverse_order)
            else:  # 收盘价
                stocks_sorted = sorted(stocks, key=lambda x: x['收盘价'], reverse=reverse_order)
            
            # 格式化数据用于显示
            display_stocks = []
            for stock in stocks_sorted:
                display_stocks.append({
                    '代码': stock['代码'],
                    '名称': stock['名称'],
                    '收盘价': stock['收盘价'],
                    '涨跌幅': stock['涨跌幅'],
                    '龙虎榜净买入': format_amount(stock['龙虎榜净买入']),
                    '上榜原因': stock['上榜原因']
                })
            
            # 显示数据表格
            st.dataframe(
                pd.DataFrame(display_stocks),
                column_config={
                    '代码': st.column_config.TextColumn('代码', width='small'),
                    '名称': st.column_config.TextColumn('名称', width='medium'),
                    '收盘价': st.column_config.NumberColumn('收盘价', format='%.2f'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '龙虎榜净买入': st.column_config.TextColumn('净买入', width='medium'),
                    '上榜原因': st.column_config.TextColumn('上榜原因', width='large')
                },
                width="stretch",
                hide_index=True
            )
            
            # 龙虎榜净买入排行
            st.subheader("📈 龙虎榜净买入排行")
            top_stocks = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=True)[:10]
            
            for i, stock in enumerate(top_stocks, 1):
                with st.container():
                    cols = st.columns([1, 3, 2, 2, 3])
                    cols[0].write(f"**{i}**")
                    cols[1].write(f"**{stock['名称']}** ({stock['代码']})")
                    cols[2].metric("净买入", format_amount(stock['龙虎榜净买入']))
                    cols[3].metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                    cols[4].caption(stock['上榜原因'])
                    st.divider()
            
            # 龙虎榜解析
            st.divider()
            st.subheader("📊 龙虎榜深度解析")
            
            with st.spinner('正在分析龙虎榜数据...'):
                summary = QuantAlgo.analyze_lhb_summary()
                
                if summary['数据状态'] == '正常':
                    # 总体数据
                    col1, col2, col3 = st.columns(3)
                    col1.metric("上榜股票数量", f"{summary['上榜股票数量']} 只")
                    col2.metric("龙虎榜净买入总额", format_amount(summary['龙虎榜净买入总额']))
                    col3.metric("总成交额", format_amount(summary['总成交额']))
                    
                    # 上榜原因统计
                    if summary['上榜原因统计']:
                        st.subheader("🔍 上榜原因统计")
                        reason_df = pd.DataFrame([
                            {'上榜原因': reason, '数量': count}
                            for reason, count in summary['上榜原因统计'].items()
                        ])
                        st.dataframe(reason_df, width="stretch", hide_index=True)
                    
                    # 机构统计
                    if summary['机构统计'] is not None and not summary['机构统计'].empty:
                        st.subheader("🏢 机构席位统计")
                        st.dataframe(summary['机构统计'].head(10), width="stretch")
                    
                    # 活跃营业部
                    if summary['活跃营业部'] is not None and not summary['活跃营业部'].empty:
                        st.subheader("🏪 活跃营业部")
                        st.dataframe(summary['活跃营业部'].head(10), width="stretch")
                    
                    # 资金流向分析
                    st.subheader("💰 资金流向分析")
                    net_buy_ratio = summary['龙虎榜净买入总额'] / summary['总成交额'] * 100 if summary['总成交额'] > 0 else 0
                    
                    if net_buy_ratio > 5:
                        st.success(f"✅ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金积极介入")
                    elif net_buy_ratio > 0:
                        st.info(f"📊 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏多")
                    elif net_buy_ratio > -5:
                        st.warning(f"⚠️ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏空")
                    else:
                        st.error(f"❌ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金大幅流出")
                else:
                    st.error(f"❌ {summary['数据状态']}")
                    if '错误信息' in summary:
                        st.caption(summary['错误信息'])
        else:
            st.error(f"❌ {lhb_data['数据状态']}")
            if '错误信息' in lhb_data:
                st.caption(lhb_data['错误信息'])
            else:
                st.caption(lhb_data['说明'])
        
        # 龙虎榜质量分析
        st.divider()
        st.subheader("🎯 龙虎榜质量分析")
        st.caption("区分好榜和坏榜，推荐值得次日介入的股票")
        
        with st.spinner('正在分析龙虎榜质量...'):
            quality_analysis = QuantAlgo.analyze_lhb_quality()
            
            if quality_analysis['数据状态'] == '正常':
                stats = quality_analysis['统计']
                
                # 显示统计
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("优质榜", f"{stats['优质榜数量']} 只", delta="强烈推荐")
                col2.metric("良好榜", f"{stats['良好榜数量']} 只", delta="推荐关注")
                col3.metric("一般榜", f"{stats['劣质榜数量']} 只", delta="谨慎观望")
                col4.metric("总数", f"{stats['总数']} 只")
                
                # 推荐股票
                st.subheader("⭐ 推荐关注（优质榜）")
                recommended_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] >= 70]
                
                if recommended_stocks:
                    for stock in recommended_stocks:
                        with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("净买入", format_amount(stock['净买入']))
                            
                            st.write("**上榜原因：**", stock['上榜原因'])
                            st.write("**评分原因：**", "、".join(stock['评分原因']))
                            st.success(f"📈 推荐操作：{stock['推荐']}")
                else:
                    st.info("暂无优质榜单")
                
                # 良好榜
                if len(recommended_stocks) < 10:
                    st.subheader("🟡 良好榜（可关注）")
                    good_stocks = [s for s in quality_analysis['股票分析'] if 50 <= s['评分'] < 70]
                    
                    if good_stocks:
                        for stock in good_stocks[:5]:  # 只显示前5只
                            with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3 = st.columns(3)
                                col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("净买入", format_amount(stock['净买入']))
                                
                                st.write("**上榜原因：**", stock['上榜原因'])
                                st.write("**评分原因：**", "、".join(stock['评分原因']))
                                st.info(f"📊 推荐操作：{stock['推荐']}")
                
                # 劣质榜（可选显示）
                with st.expander("🔴 劣质榜（不建议介入）"):
                    poor_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] < 30]
                    if poor_stocks:
                        st.dataframe(
                            pd.DataFrame([
                                {
                                    '代码': s['代码'],
                                    '名称': s['名称'],
                                    '评分': s['评分'],
                                    '上榜原因': s['上榜原因'],
                                    '推荐': s['推荐']
                                }
                                for s in poor_stocks
                            ]),
                            width="stretch",
                            hide_index=True
                            )
                    else:
                        st.info("暂无劣质榜单")
                
                # 评分说明
                st.divider()
                st.caption("**评分说明：**")
                st.caption("- 净买入额（30分）：净买入>1亿得30分，>5000万得20分，>0得10分")
                st.caption("- 涨跌幅（20分）：3-7%得20分，7-10%得10分，>10%扣10分")
                st.caption("- 成交额（15分）：>5亿得15分，>2亿得10分，>1亿得5分")
                st.caption("- 上榜原因（20分）：机构买入等优质原因得20分，ST等劣质原因扣20分")
                st.caption("- 净买入占比（15分）：>10%得15分，>5%得10分，>0得5分")
                st.caption("- 优质榜（≥70分）：强烈推荐次日介入")
                st.caption("- 良好榜（50-69分）：推荐关注")
                st.caption("- 一般榜（30-49分）：谨慎观望")
                st.caption("- 劣质榜（<30分）：不建议介入")
            else:
                st.error(f"❌ {quality_analysis['数据状态']}")

with tab_dragon:
    st.subheader("🔥 龙头战法 - 捕捉潜在龙头股")
    st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
    
    st.info("""
    **龙头战法核心要点：**
    - 🎯 只做涨停板股票
    - 💰 优选低价股（≤10元）
    - 📊 关注攻击性放量
    - 📈 等待KDJ金叉
    - 🔄 换手率适中（5-15%）
    """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 100, 50, 10)
    with col_scan2:
        min_score = st.slider("最低评分门槛", 40, 80, 60, 5)
    with col_scan3:
        if st.button("🔍 开始扫描"):
            st.session_state.scan_dragon = True
            st.rerun()
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        with st.spinner('正在扫描市场中的潜在龙头股...'):
            scan_result = QuantAlgo.scan_dragon_stocks(limit=scan_limit, min_score=min_score)
        
        if scan_result['数据状态'] == '正常':
            st.success(f"✅ 扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只潜在龙头股")
            
            if scan_result['龙头股列表']:
                # 按评级分组显示
                strong_dragons = [s for s in scan_result['龙头股列表'] if s['评级得分'] >= 80]
                potential_dragons = [s for s in scan_result['龙头股列表'] if 60 <= s['评级得分'] < 80]
                weak_dragons = [s for s in scan_result['龙头股列表'] if 40 <= s['评级得分'] < 60]
                
                # 强龙头
                if strong_dragons:
                    st.divider()
                    st.subheader("🔥 强龙头（重点关注）")
                    for stock in strong_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("评级得分", f"{stock['评级得分']}/100")
                            
                            # 显示五个条件得分
                            st.write("**五个条件得分：**")
                            details = stock['详情']
                            st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/20")
                            st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
                            st.write(f"- 成交量: {details['条件3_成交量']['得分']}/20")
                            st.write(f"- KDJ: {details['条件4_KDJ']['得分']}/20")
                            st.write(f"- 换手率: {details['条件5_换手率']['得分']}/20")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in details['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"⭐ 添加到自选", key=f"add_dragon_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 潜力龙头
                if potential_dragons:
                    st.divider()
                    st.subheader("📈 潜力龙头（可关注）")
                    for stock in potential_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
                            col1, col2 = st.columns(2)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            
                            st.write(f"评级得分: {stock['评级得分']}/100")
                            st.info(f"评级说明: {stock['评级说明']}")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in stock['详情']['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"⭐ 添加到自选", key=f"add_potential_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 弱龙头
                if weak_dragons:
                    st.divider()
                    st.subheader("⚠️ 弱龙头（谨慎关注）")
                    df_weak = pd.DataFrame([
                        {
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评级得分': s['评级得分'],
                            '评级说明': s['评级说明']
                        }
                        for s in weak_dragons
                    ])
                    st.dataframe(df_weak, width="stretch", hide_index=True)
            else:
                st.warning("⚠️ 未发现符合条件的龙头股")
                st.info("💡 提示：可以降低最低评分门槛或增加扫描数量")
        else:
            st.error(f"❌ {scan_result['数据状态']}")
            if '错误信息' in scan_result:
                st.caption(scan_result['错误信息'])
            if '说明' in scan_result:
                st.info(scan_result['说明'])
    else:
        st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的潜在龙头股")
        
        # 显示龙头战法说明
        st.divider()
        st.subheader("📖 龙头战法详解")
        
        with st.expander("🎯 龙头股五个条件"):
            st.markdown("""
            **1. 涨停板（20分）**
            - 必须从涨停板开始
            - 涨停板是多空双方最准确的攻击信号
            - 是所有黑马的摇篮，是龙头的发源地
            
            **2. 价格（20分）**
            - 低价股（≤10元）：20分
            - 适中价格（10-15元）：10分
            - 高价股（>15元）：0分
            - 高价股不具备炒作空间，只有低价股才能得到股民追捧
            
            **3. 成交量（20分）**
            - 攻击性放量（量比>2）：20分
            - 温和放量（量比1.5-2）：15分
            - 缩量或正常：0分
            - 龙头一般出现三日以上的攻击性放量特征
            
            **4. KDJ（20分）**
            - KDJ金叉：20分
            - KDJ低位（K<30）：10分
            - KDJ不在低位：0分
            - 日线、周线、月线KDJ同时低位金叉更安全
            
            **5. 换手率（20分）**
            - 适中换手率（5-15%）：20分
            - 偏低换手率（2-5%）：15分
            - 过高或过低换手率：10分或0分
            - 换手率适中显示资金活跃度
            """)
        
        with st.expander("💡 买入技巧"):
            st.markdown("""
            **买入时机：**
            
            **1. 涨停开闸放水时买入**
            - 涨停板打开时，如果量能充足，可以介入
            
            **2. 高开时买入**
            - 未开板的个股，第二天若高开1.5-3.5%，可以买入
            
            **3. 回调买入**
            - 龙头股回到第一个涨停板的启涨点，构成回调买点
            - 比第一个买点更稳、更准、更狠
            
            **操作要点：**
            - 只做第一个涨停板
            - 只做第一次放量的涨停板
            - 相对股价不高，流通市值不大
            - 指标从低位上穿，短线日KDJ低位金叉
            """)
        
        with st.expander("⚠️ 风险控制"):
            st.markdown("""
            **止损点设定：**
            
            **强势市场：**
            - 以该股的第一个涨停板为止损点
            
            **弱势市场：**
            - 以3%为止损点
            
            **严格纪律：**
            - 绝对不允许个股跌幅超过10%
            - 如果跌幅超过10%，立即止损，不要找任何理由
            - 破止损的个股，不要做补仓动作
            - 补仓是实盘操作中最蠢的行为
            """)

with tab_auction:
    st.subheader("⚡ 集合竞价选股 - 捕捉开盘机会")
    st.caption("基于雪球集合竞价选股法：竞价看方向，弱转强战法，竞价扩散法")
    
    st.info("""
    **集合竞价选股核心要点：**
    - 🕐 关注9:20之后的竞价情况（不可撤单，真实反映资金博弈）
    - 📊 重点关注放量的股票（量比>1.5）
    - 🔄 竞价弱转强：烂板/炸板股次日竞价超预期
    - 📈 竞价扩散法：通过一字板强势股挖掘同题材概念股
    """)
    
    # 功能选择
    auction_mode = st.radio("选择功能", ["竞价选股扫描", "竞价弱转强检测", "竞价扩散法"], horizontal=True)
    
    if auction_mode == "竞价选股扫描":
        st.divider()
        st.subheader("🔍 竞价选股扫描")
        
        # 扫描参数
        col_scan1, col_scan2 = st.columns(2)
        with col_scan1:
            scan_limit = st.slider("扫描股票数量", 50, 200, 100, 10)
        with col_scan2:
            if st.button("🔍 开始扫描", key="scan_auction_btn"):
                st.session_state.scan_auction = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_auction', False):
            with st.spinner('正在扫描集合竞价股票...'):
                scan_result = QuantAlgo.scan_auction_stocks(limit=scan_limit)
            
            if scan_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只竞价活跃股票")
                
                if scan_result['竞价股票列表']:
                    # 按评级分组显示
                    strong_stocks = [s for s in scan_result['竞价股票列表'] if s['评分'] >= 80]
                    active_stocks = [s for s in scan_result['竞价股票列表'] if 60 <= s['评分'] < 80]
                    normal_stocks = [s for s in scan_result['竞价股票列表'] if 40 <= s['评分'] < 60]
                    
                    # 强势股票
                    if strong_stocks:
                        st.divider()
                        st.subheader("🔥 强势股票（重点关注）")
                        for stock in strong_stocks:
                            with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("量比", stock['量比'])
                                col4.metric("换手率", f"{stock['换手率']:.2f}%")
                                
                                # 显示信号
                                st.write("**竞价信号：**")
                                for signal in stock['信号']:
                                    st.write(f"- {signal}")
                                
                                # 显示操作建议
                                st.info(f"**操作建议：** {stock['操作建议']}")
                                
                                # 弱转强标记
                                if stock['弱转强']:
                                    st.success("🔄 竞价弱转强！")
                                
                                # 添加到自选股按钮
                                if st.button(f"⭐ 添加到自选", key=f"add_auction_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                    
                    # 活跃股票
                    if active_stocks:
                        st.divider()
                        st.subheader("🟡 活跃股票（可关注）")
                        df_active = pd.DataFrame([
                            {
                                '代码': s['代码'],
                                '名称': s['名称'],
                                '最新价': f"¥{s['最新价']:.2f}",
                                '涨跌幅': f"{s['涨跌幅']:.2f}%",
                                '量比': s['量比'],
                                '换手率': f"{s['换手率']:.2f}%",
                                '评分': s['评分'],
                                '评级': s['评级']
                            }
                            for s in active_stocks
                        ])
                        st.dataframe(df_active, width="stretch", hide_index=True)
                    
                    # 一般股票
                    if normal_stocks:
                        st.divider()
                        st.subheader("🟢 一般股票（观望）")
                        df_normal = pd.DataFrame([
                            {
                                '代码': s['代码'],
                                '名称': s['名称'],
                                '最新价': f"¥{s['最新价']:.2f}",
                                '涨跌幅': f"{s['涨跌幅']:.2f}%",
                                '量比': s['量比'],
                                '评分': s['评分']
                            }
                            for s in normal_stocks
                        ])
                        st.dataframe(df_normal, width="stretch", hide_index=True)
                else:
                    st.warning("⚠️ 未发现符合条件的竞价股票")
                    st.info("💡 提示：当前市场可能没有明显的竞价异动")
            else:
                st.error(f"❌ {scan_result['数据状态']}")
                if '错误信息' in scan_result:
                    st.caption(scan_result['错误信息'])
                if '说明' in scan_result:
                    st.info(scan_result['说明'])
        else:
            st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的竞价活跃股票")
    
    elif auction_mode == "竞价弱转强检测":
        st.divider()
        st.subheader("🔄 竞价弱转强检测")
        
        st.info("""
        **竞价弱转强战法：**
        - 适用于烂板、炸板股次日竞价超预期的情况
        - 前一天烂板/炸板（弱势），次日竞价放量高开（超预期）
        - 说明有资金抢筹，值得重点关注
        """)
        
        # 股票选择
        col_stock1, col_stock2 = st.columns(2)
        with col_stock1:
            check_symbol = st.text_input("股票代码", placeholder="输入6位股票代码", help="例如：600519")
        with col_stock2:
            if st.button("🔍 检测弱转强", key="check_weak_to_strong_btn"):
                if check_symbol:
                    st.session_state.check_symbol = check_symbol
                    st.session_state.check_weak_to_strong = True
                    st.rerun()
                else:
                    st.warning("请输入股票代码")
        
        # 执行检测
        if st.session_state.get('check_weak_to_strong', False) and st.session_state.get('check_symbol'):
            check_symbol = st.session_state.check_symbol
            
            with st.spinner(f'正在检测 {check_symbol} 的竞价弱转强情况...'):
                df = db.get_history_data(check_symbol)
                
                if not df.empty and len(df) > 5:
                    weak_to_strong_result = QuantAlgo.detect_auction_weak_to_strong(df, check_symbol)
                    
                    if weak_to_strong_result['检测状态'] == '正常':
                        st.success(f"✅ 检测完成！")
                        
                        stock_name = QuantAlgo.get_stock_name(check_symbol)
                        st.subheader(f"📊 {stock_name} ({check_symbol}) - 弱转强检测结果")
                        
                        # 显示基本信息
                        col1, col2, col3 = st.columns(3)
                        col1.metric("前一天类型", weak_to_strong_result.get('前一天类型', '-'))
                        col2.metric("昨日涨跌幅", f"{weak_to_strong_result.get('昨日涨跌幅', 0):.2f}%")
                        col3.metric("今日开盘涨跌幅", f"{weak_to_strong_result.get('今日开盘涨跌幅', 0):.2f}%")
                        
                        # 显示量比
                        st.metric("量比", weak_to_strong_result.get('量比', 0))
                        
                        # 显示评级
                        if weak_to_strong_result.get('是否弱转强'):
                            st.success(f"🔥 {weak_to_strong_result['评级']}")
                        else:
                            st.warning(f"⚠️ {weak_to_strong_result['评级']}")
                        
                        # 显示信号
                        st.divider()
                        st.subheader("📋 检测信号")
                        for signal in weak_to_strong_result.get('信号', []):
                            st.write(f"- {signal}")
                        
                        # 显示操作建议
                        st.divider()
                        st.info(f"**操作建议：** {weak_to_strong_result.get('操作建议', '')}")
                    else:
                        st.warning(f"⚠️ {weak_to_strong_result['检测状态']}")
                        if '说明' in weak_to_strong_result:
                            st.info(weak_to_strong_result['说明'])
                else:
                    st.error("❌ 无法获取股票数据")
                    st.info("💡 请检查股票代码是否正确")
        else:
            st.info("👆 输入股票代码并点击「检测弱转强」按钮")
    
    elif auction_mode == "竞价扩散法":
        st.divider()
        st.subheader("📈 竞价扩散法")
        
        st.info("""
        **竞价扩散法：**
        - 通过一字板强势股挖掘同题材概念股
        - 筛选首板、二板，且封单金额超过流通盘5%
        - 剔除热炒题材，保留新题材
        - 根据题材找出同概念股，关注未涨停但高开的股票
        """)
        
        # 扫描参数
        col_diff1, col_diff2 = st.columns(2)
        with col_diff1:
            diffusion_limit = st.slider("扫描股票数量", 20, 100, 50, 10)
        with col_diff2:
            if st.button("🔍 扫描一字板", key="scan_diffusion_btn"):
                st.session_state.scan_diffusion = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_diffusion', False):
            with st.spinner('正在扫描强势一字板股票...'):
                diffusion_result = QuantAlgo.auction_diffusion_method(limit=diffusion_limit)
            
            if diffusion_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！发现 {len(diffusion_result['强势一字板股票'])} 只强势一字板股票")
                
                if diffusion_result['强势一字板股票']:
                    # 显示强势一字板股票
                    st.divider()
                    st.subheader("🔥 强势一字板股票")
                    
                    df_strong = pd.DataFrame(diffusion_result['强势一字板股票'])
                    df_strong['封单金额'] = df_strong['封单金额'].apply(lambda x: f"{x/10000:.2f}万" if x < 100000000 else f"{x/100000000:.2f}亿")
                    df_strong['流通市值'] = df_strong['流通市值'].apply(lambda x: f"{x/100000000:.2f}亿")
                    
                    st.dataframe(df_strong, width="stretch", hide_index=True)
                    
                    # 显示操作建议
                    st.divider()
                    st.subheader("💡 操作建议")
                    for i, suggestion in enumerate(diffusion_result['操作建议'], 1):
                        st.write(f"{i}. {suggestion}")
                    
                    # 说明
                    st.info(diffusion_result['说明'])
                else:
                    st.warning("⚠️ 未发现符合条件的强势一字板股票")
                    st.info("💡 提示：当前市场可能没有封单充足的一字板股票")
            else:
                st.error(f"❌ {diffusion_result['数据状态']}")
                if '错误信息' in diffusion_result:
                    st.caption(diffusion_result['错误信息'])
                if '说明' in diffusion_result:
                    st.info(diffusion_result['说明'])
        else:
            st.info("👆 点击「扫描一字板」按钮，系统将自动扫描强势一字板股票")
    
    # 显示集合竞价选股说明
    st.divider()
    st.subheader("📖 集合竞价选股详解")
    
    with st.expander("🕐 集合竞价规则"):
        st.markdown("""
        **时间规则：**
        
        **9:15 - 9:20：自由报价**
        - 既可以下单，也可以撤单
        - 可能存在诱多诱空，大资金在9:19分最后一秒撤单
        
        **9:20 - 9:25：不可撤单**
        - 可以下单，不能撤单
        - 真实显示当天该股在竞价期间资金的博弈情况
        - **重点关注这个时间段**
        
        **9:25 - 9:30：接受报价但不处理**
        - 系统接受报价，但不做处理
        - 等待正式开盘
        
        **成交原则：**
        - 最大成交量优先，决定当天的开盘价
        - 竞价异常（放量）的股票，基本都是大资金背后作为推手
        """)
    
    with st.expander("📊 集合竞价图形解读"):
        st.markdown("""
        **理想的竞价图形：**
        
        **1. 股价走势**
        - 集合竞价期间，股价逐步抬高为好
        - 最好的情况是最后时刻，股价被大单买入快速拉升
        
        **2. 成交量柱**
        - 柱子代表竞价的成交量
        - 量能最好是随着股价的抬升放大
        - 绿色代表向下的卖盘
        - 红色代表资金主动向上买入
        - 成交量逐渐放大，且红色柱子连续排列，较好
        
        **3. 诱空示例**
        - 大资金在竞价期间诱空，骗取散户筹码
        - 股价先拉升，然后在9:19分快速撤单，股价回落
        - 这种情况要警惕，不要盲目追高
        """)
    
    with st.expander("🔄 竞价弱转强战法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"弱"？**
        - 烂板：涨停板上抛压不断，持筹者不看好后续走势
        - 炸板：涨停板打开，板上介入的资金全部被套
        - 即使封板，第二天也很难有溢价
        
        **什么是"弱转强"？**
        - 前一天烂板或炸板（弱势）
        - 第二天竞价应该是没有溢价，以一种很弱的表现形式
        - **但是第二天开盘资金出现放量抢筹的情况**
        - 这就是超预期，超出市场预期
        
        **为什么有效？**
        - 烂板/炸板股，次日拉升起来压力非常大
        - 一般没有资金愿意去做多
        - 如果竞价直接放量高开，完全不惧前一天板上被套牢的资金
        - 说明有新资金强势介入，值得重点关注
        
        **操作要点：**
        - 关注前一天烂板或炸板的股票
        - 次日9:20之后观察竞价情况
        - 如果竞价放量高开（>2%），且量比>1.5，考虑参与
        - 设置好止损点，严格执行
        """)
    
    with st.expander("📈 竞价扩散法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"竞价扩散"？**
        - 通过对个股封单的观测，以及对个股属性的识别
        - 找到所对应的板块，提前预判当天资金的主攻方向
        - 通过竞价期间一字板的强势股去做挖掘
        - "扩散"到同题材概念还未涨停的个股
        
        **使用时间：**
        - 9:20 - 9:30之间（9:20之后不能撤单）
        
        **使用方法：**
        
        **1. 筛选一字涨停股票**
        - 9:20之后，对当天一字涨停的股票进行浏览
        - 选出首板股、二板股（首板股做参考最好）
        - 记录涨停板上的封单金额
        
        **2. 进一步筛选**
        - 首板股里面属于热炒题材的剔除
        - 必须是新题材
        - 一字板封单不足真实流通盘5%的剔除
        
        **3. 锁定题材**
        - 剩下的是"集合竞价强势涨停（一字板）的新题材"
        - 通过个股，找为什么当天他能一字板的原因
        - 迅速锁定题材
        
        **4. 挖掘同概念股**
        - 搜索同题材的概念股
        - 按涨幅排序（集合竞价的涨幅）
        - 把还未涨停的，但是高开的同概念其他股加入自选
        - 观察竞价是否有资金异动抢筹
        - 竞价后直接参与，或选择第一个上板的股去做打板
        
        **为什么有效？**
        - 很多股票开盘秒板，是因为竞价期间强势的一字板新题材获得了市场资金的认可
        - 其他聪明的大资金快速锁定相关概念的其他个股
        - 开盘后立即抢筹买入造成的
        - 我们跟着聪明资金走，"他们吃肉，我们喝汤"
        """)
with tab_sentiment:
    st.subheader("📈 市场情绪分析")
    st.caption("基于拾荒网技术文章:情绪指数、涨停板分析、龙虎榜深度分析")
    
    # 初始化情绪分析器
    from logic.algo_sentiment import MarketSentimentAnalyzer
    sentiment_analyzer = MarketSentimentAnalyzer()
    
    # 情绪分析类型选择
    sentiment_type = st.radio("分析类型", ["情绪周期", "情绪指数", "涨停板分析", "龙虎榜分析", "反包模式", "板块轮动", "连板高度"], horizontal=True, key="sentiment_type_select")
    
    if sentiment_type == "情绪周期":
        st.subheader("🔄 情绪周期分析")
        
        st.info("💡 情绪周期五阶段论:冰点期→复苏期→活跃期→高潮期→退潮期")
        
        if st.button("分析情绪周期", key="analyze_sentiment_cycle"):
            with st.spinner('正在分析情绪周期...'):
                cycle_data = sentiment_analyzer.analyze_sentiment_cycle()
                
                if cycle_data['数据状态'] == '正常':
                    # 显示情绪周期阶段
                    col_stage, col_height, col_zt = st.columns(3)
                    
                    with col_stage:
                        st.metric("当前阶段", cycle_data['情绪周期阶段'])
                    
                    with col_height:
                        st.metric("空间板高度", f"{cycle_data['空间板高度']}板")
                    
                    with col_zt:
                        st.metric("涨停数量", cycle_data['涨停数量'])
                    
                    # 显示阶段描述
                    st.subheader("📝 阶段描述")
                    st.info(cycle_data['阶段描述'])
                    
                    # 显示周期特征
                    if cycle_data.get('周期特征'):
                        st.subheader("🔍 周期特征")
                        for feature in cycle_data['周期特征']:
                            st.write(f"• {feature}")
                    
                    # 显示操作建议
                    st.subheader("💡 操作建议")
                    st.success(cycle_data['操作建议'])
                    
                    # 显示连板分布
                    if cycle_data['连板分布']:
                        st.subheader("📊 连板分布")
                        
                        board_df = pd.DataFrame(list(cycle_data['连板分布'].items()), 
                                               columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数', ascending=False)
                        st.dataframe(board_df, width="stretch")
                        
                        # 连板分布图
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='数量',
                            marker=dict(
                                color=board_df['数量'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="数量")
                            ),
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度分布",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 显示情绪指数
                    st.subheader("🎯 情绪指数")
                    col_idx, col_lvl = st.columns(2)
                    with col_idx:
                        st.metric("情绪指数", f"{cycle_data['情绪指数']:.2f}")
                    with col_lvl:
                        st.metric("情绪等级", cycle_data['情绪等级'])
                else:
                    st.error(f"❌ {cycle_data['数据状态']}")
                    if '说明' in cycle_data:
                        st.info(f"💡 {cycle_data['说明']}")
    
    elif sentiment_type == "情绪指数":
        st.subheader("🎯 市场情绪指数")
        
        st.info("💡 情绪指数说明:综合涨停数量、连板高度、打开率等指标,评估市场整体情绪")
        
        if st.button("获取情绪指数", key="get_sentiment_index"):
            with st.spinner('正在获取市场情绪数据...'):
                sentiment_data = sentiment_analyzer.get_market_sentiment_index()
                
                if sentiment_data['数据状态'] == '正常':
                    # 显示情绪指数
                    col_score, col_level, col_desc = st.columns(3)
                    
                    with col_score:
                        st.metric("情绪指数", f"{sentiment_data['情绪指数']:.2f}", delta="满分100")
                    
                    with col_level:
                        st.metric("情绪等级", sentiment_data['情绪等级'])
                    
                    with col_desc:
                        st.info(sentiment_data['情绪描述'])
                    
                    # 显示详细指标
                    st.subheader("📊 详细指标")
                    
                    col_zt, col_open, col_board = st.columns(3)
                    
                    with col_zt:
                        st.metric("涨停数量", sentiment_data['涨停数量'])
                    
                    with col_open:
                        st.metric("涨停打开数", sentiment_data['涨停打开数'])
                    
                    with col_board:
                        st.metric("涨停打开率", f"{sentiment_data['涨停打开率']}%")
                    
                    # 连板分布
                    if sentiment_data['连板分布']:
                        st.subheader("🔗 连板高度分布")
                        
                        board_df = pd.DataFrame(list(sentiment_data['连板分布'].items()), columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数')
                        
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='连板数量',
                            marker_color='orange',
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度分布",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 涨停股票列表
                    if not sentiment_data['详细数据'].empty:
                        st.subheader("📝 涨停股票列表")
                        st.dataframe(sentiment_data['详细数据'], width="stretch")
                else:
                    st.error(f"❌ {sentiment_data['数据状态']}")
                    if '说明' in sentiment_data:
                        st.info(f"💡 {sentiment_data['说明']}")
    
    elif sentiment_type == "涨停板分析":
        st.subheader("🎯 涨停板深度分析")
        
        st.info("💡 涨停板分析:识别龙头股、分析封板强度、统计板块分布")
        
        if st.button("分析涨停板", key="analyze_limit_up"):
            with st.spinner('正在分析涨停板数据...'):
                limit_data = sentiment_analyzer.analyze_limit_up_stocks()
                
                if limit_data['数据状态'] == '正常':
                    # 显示总体统计
                    col_total, col_dragon = st.columns(2)
                    
                    with col_total:
                        st.metric("涨停总数", limit_data['涨停总数'])
                    
                    with col_dragon:
                        dragon_count = len(limit_data['龙头股'])
                        st.metric("龙头股数量", dragon_count)
                    
                    # 龙头股列表
                    if limit_data['龙头股']:
                        st.subheader("🔥 龙头股列表")

                        dragon_df = pd.DataFrame(limit_data['龙头股'])

                        # 打印调试信息
                        print(f"龙头股数据列名: {dragon_df.columns.tolist()}")
                        print(f"龙头股数据示例: {dragon_df.head(1).to_dict() if not dragon_df.empty else '空'}")

                        # 检查实际列名并选择要显示的列
                        available_cols = dragon_df.columns.tolist()
                        required_cols = ['代码', '名称', '最新价', '涨跌幅', '成交额', '换手率', '龙头评分']

                        # 只选择存在的列
                        display_cols = [col for col in required_cols if col in available_cols]
                        display_df = dragon_df[display_cols].copy()

                        # 格式化成交额（如果存在）
                        if '成交额' in display_df.columns:
                            display_df['成交额'] = display_df['成交额'].apply(format_amount)

                        # 格式化涨跌幅（如果存在）
                        if '涨跌幅' in display_df.columns:
                            display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:+.2f}%")

                        # 格式化换手率（如果存在）
                        if '换手率' in display_df.columns:
                            display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")

                        # 显示表格
                        st.dataframe(display_df, width="stretch")
                        
                        # 显示最佳龙头
                        if not dragon_df.empty:
                            best_dragon = dragon_df.iloc[0]
                            st.success(f"🏆 **最佳龙头**: {best_dragon['名称']} ({best_dragon['代码']}) - 评分: {best_dragon['龙头评分']:.1f}")
                        
                        # 添加股票选择和分析
                        st.subheader("📊 单股涨停分析")
                        selected_stock = st.selectbox(
                            "选择股票查看详细分析",
                            options=dragon_df['代码'].tolist(),
                            format_func=lambda x: f"{dragon_df[dragon_df['代码']==x]['名称'].values[0]} ({x})",
                            key="select_limit_stock"
                        )
                        
                        if selected_stock:
                            # 显示选中股票的详细信息
                            stock_info = dragon_df[dragon_df['代码'] == selected_stock].iloc[0]
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("代码", stock_info['代码'])
                            with col2:
                                st.metric("名称", stock_info['名称'])
                            with col3:
                                st.metric("最新价", f"¥{stock_info['最新价']:.2f}")
                            with col4:
                                st.metric("龙头评分", f"{stock_info['龙头评分']:.1f}")
                            
                            # 详细信息
                            st.subheader("📋 详细信息")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**涨跌幅**: {stock_info['涨跌幅']:+.2f}%")
                                st.write(f"**成交额**: {format_amount(stock_info['成交额'])}")
                            with col_b:
                                st.write(f"**换手率**: {stock_info['换手率']:.2f}%")
                                st.write(f"**封板强度**: {'强' if stock_info['涨跌幅'] >= 9.9 else '中' if stock_info['涨跌幅'] >= 9.5 else '弱'}")
                            
                            # 单股分析按钮
                            if st.button("📊 查看技术分析", key=f"analyze_limit_{selected_stock}"):
                                st.session_state.analyze_stock = selected_stock
                                st.rerun()
                        
                        # 显示单股分析
                        if 'analyze_stock' in st.session_state:
                            show_stock_analysis_modal(st.session_state.analyze_stock)
                    
                    # 板块分布
                    if limit_data['板块分布']:
                        st.subheader("📊 板块分布")
                        
                        sector_df = pd.DataFrame(list(limit_data['板块分布'].items()), columns=['板块', '数量'])
                        sector_df = sector_df.sort_values('数量', ascending=False)
                        
                        fig_sector = go.Figure()
                        fig_sector.add_trace(go.Bar(
                            x=sector_df['板块'],
                            y=sector_df['数量'],
                            name='板块数量',
                            marker_color='blue',
                            text=sector_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_sector.update_layout(
                            title="涨停板块分布",
                            xaxis_title="板块",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_sector, width="stretch")
                    
                    # 连板统计
                    if limit_data['连板统计']:
                        st.subheader("🔗 连板统计")
                        
                        board_df = pd.DataFrame(list(limit_data['连板统计'].items()), columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数')
                        
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='连板数量',
                            marker=dict(
                                color=board_df['数量'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="数量")
                            ),
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度统计",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 详细数据
                    if not limit_data['详细数据'].empty:
                        st.subheader("📝 涨停详细数据")
                        st.dataframe(limit_data['详细数据'], width="stretch")
                else:
                    st.error(f"❌ {limit_data['数据状态']}")
                    if '说明' in limit_data:
                        st.info(f"💡 {limit_data['说明']}")
    
    elif sentiment_type == "龙虎榜分析":
        st.subheader("🏆 龙虎榜深度分析")
        
        st.info("💡 龙虎榜分析:机构vs游资动向、热门营业部追踪、质量评估")
        
        if st.button("分析龙虎榜", key="analyze_lhb"):
            with st.spinner('正在分析龙虎榜数据...'):
                lhb_data = sentiment_analyzer.deep_analyze_lhb()
                
                if lhb_data['数据状态'] == '正常':
                    # 显示总体统计
                    col_count, col_inst, col_hot = st.columns(3)
                    
                    with col_count:
                        st.metric("上榜数量", lhb_data['上榜数量'])
                    
                    with col_inst:
                        st.metric("机构净买入", format_amount(lhb_data['机构净买入']))
                    
                    with col_hot:
                        st.metric("热门营业部净买入", format_amount(lhb_data['热门营业部净买入']))
                    
                    st.caption(f"数据日期: {lhb_data['数据日期']}")
                    
                    # 热门营业部交易
                    if lhb_data['热门营业部交易']:
                        st.subheader("🔥 热门营业部交易")
                        
                        hot_seat_df = pd.DataFrame(lhb_data['热门营业部交易'])
                        
                        # 去重(按股票代码)
                        hot_seat_df = hot_seat_df.drop_duplicates(subset=['股票代码'], keep='first')
                        
                        # 格式化净买入
                        hot_seat_df['净买入'] = hot_seat_df['净买入'].apply(format_amount)
                        
                        # 重命名列
                        hot_seat_df.columns = ['营业部', '股票代码', '股票名称', '净买入']
                        
                        # 显示表格
                        st.dataframe(hot_seat_df, width="stretch")
                        
                        # 添加股票选择和分析
                        st.subheader("📊 单股龙虎榜分析")
                        selected_stock = st.selectbox(
                            "选择股票查看详细分析",
                            options=hot_seat_df['股票代码'].tolist(),
                            format_func=lambda x: f"{hot_seat_df[hot_seat_df['股票代码']==x]['股票名称'].values[0]} ({x})",
                            key="select_hot_seat_stock"
                        )
                        
                        if selected_stock:
                            # 显示选中股票的详细信息
                            stock_info = hot_seat_df[hot_seat_df['股票代码'] == selected_stock].iloc[0]
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("代码", stock_info['股票代码'])
                            with col2:
                                st.metric("名称", stock_info['股票名称'])
                            with col3:
                                st.metric("净买入", stock_info['净买入'])
                            
                            # 详细信息
                            st.subheader("📋 详细信息")
                            st.write(f"**营业部**: {stock_info['营业部']}")
                            
                            # 单股分析按钮
                            if st.button("📊 查看技术分析", key=f"analyze_hot_seat_{selected_stock}"):
                                st.session_state.analyze_stock = selected_stock
                                st.rerun()
                        
                        # 显示单股分析
                        if 'analyze_stock' in st.session_state:
                            show_stock_analysis_modal(st.session_state.analyze_stock)
                    
                    # 龙虎榜质量分析
                    if '质量分析' in lhb_data and lhb_data['质量分析']['数据状态'] == '正常':
                        st.subheader("📊 龙虎榜质量分析")
                        
                        quality_stats = lhb_data['质量分析']['统计']
                        col_good, col_medium, col_poor = st.columns(3)
                        
                        with col_good:
                            st.metric("优质榜", quality_stats['优质榜数量'], delta="强烈推荐")
                        
                        with col_medium:
                            st.metric("良好榜", quality_stats['良好榜数量'], delta="推荐关注")
                        
                        with col_poor:
                            st.metric("劣质榜", quality_stats['劣质榜数量'], delta="谨慎观望")
                        
                        # 详细股票分析
                        if lhb_data['质量分析']['股票分析']:
                            st.subheader("📝 股票质量分析")
                            
                            quality_df = pd.DataFrame(lhb_data['质量分析']['股票分析'])
                            
                            # 去重(按股票代码)
                            quality_df = quality_df.drop_duplicates(subset=['代码'], keep='first')
                            
                            # 选择要显示的列
                            display_df = quality_df[['代码', '名称', '榜单质量', '上榜原因', '净买入', '评分']].copy()
                            
                            # 格式化净买入
                            display_df['净买入'] = display_df['净买入'].apply(format_amount)
                            
                            # 重命名列
                            display_df.columns = ['代码', '名称', '榜单质量', '上榜原因', '净买入', '评分']
                            
                            # 显示表格
                            st.dataframe(display_df, width="stretch")
                            
                            # 添加股票选择和分析
                            st.subheader("📊 单股龙虎榜分析")
                            selected_stock = st.selectbox(
                                "选择股票查看详细分析",
                                options=quality_df['代码'].tolist(),
                                format_func=lambda x: f"{quality_df[quality_df['代码']==x]['名称'].values[0]} ({x})",
                                key="select_lhb_stock"
                            )
                            
                            if selected_stock:
                                # 显示选中股票的详细信息
                                stock_info = quality_df[quality_df['代码'] == selected_stock].iloc[0]
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("代码", stock_info['代码'])
                                with col2:
                                    st.metric("名称", stock_info['名称'])
                                with col3:
                                    st.metric("榜单质量", stock_info['榜单质量'])
                                with col4:
                                    st.metric("评分", f"{stock_info['评分']:.1f}")
                                
                                # 详细信息
                                st.subheader("📋 详细信息")
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.write(f"**收盘价**: ¥{stock_info['收盘价']:.2f}")
                                    st.write(f"**涨跌幅**: {stock_info['涨跌幅']:+.2f}%")
                                    st.write(f"**净买入**: {format_amount(stock_info['净买入'])}")
                                with col_b:
                                    st.write(f"**净买入占比**: {stock_info['净买入占比']:.2f}%")
                                    st.write(f"**成交额**: {format_amount(stock_info['成交额'])}")
                                    st.write(f"**上榜原因**: {stock_info['上榜原因']}")
                                
                                # 单股分析按钮
                                if st.button("📊 查看技术分析", key=f"analyze_lhb_{selected_stock}"):
                                    st.session_state.analyze_stock = selected_stock
                                    st.rerun()
                            
                            # 显示单股分析
                            if 'analyze_stock' in st.session_state:
                                show_stock_analysis_modal(st.session_state.analyze_stock)
                else:
                    st.error(f"❌ {lhb_data['数据状态']}")
                    if '说明' in lhb_data:
                        st.info(f"💡 {lhb_data['说明']}")
    
    elif sentiment_type == "反包模式":
        st.subheader("🔄 反包模式识别")
        
        st.info("💡 反包模式:首板炸板→次日反包→二板加速,捕捉短期反弹机会")
        
        # 股票选择
        fanbao_symbol = st.text_input("分析股票代码", value="600519", key="fanbao_symbol")
        
        if st.button("识别反包模式", key="detect_fanbao"):
            with st.spinner('正在识别反包模式...'):
                df = db.get_history_data(fanbao_symbol)
                
                if not df.empty and len(df) > 10:
                    from logic.algo_advanced import AdvancedPatternAnalyzer
                    
                    # 识别反包信号
                    signals = AdvancedPatternAnalyzer.detect_fanbao_pattern(df, fanbao_symbol)
                    
                    if signals:
                        st.success(f"✅ 发现 {len(signals)} 个反包信号")
                        
                        # 显示反包信号
                        fanbao_df = pd.DataFrame(signals)
                        st.dataframe(fanbao_df, width="stretch")
                        
                        # 对每个信号进行走势预测
                        st.subheader("🔮 走势预测")
                        
                        for i, signal in enumerate(signals):
                            with st.expander(f"反包信号 {i+1}: {signal['反包日期']}"):
                                prediction = AdvancedPatternAnalyzer.predict_fanbao_future(df, signal['反包日期'])
                                
                                col_pred, col_score = st.columns(2)
                                with col_pred:
                                    st.metric("预测", prediction['预测'])
                                with col_score:
                                    st.metric("评分", prediction['评分'])
                                
                                st.info(f"操作建议: {prediction['建议']}")
                                
                                st.write("**分析原因:**")
                                for reason in prediction['原因']:
                                    st.write(f"• {reason}")
                    else:
                        st.info("未发现反包模式信号")
                else:
                    st.error("数据不足,无法识别反包模式")
    
    elif sentiment_type == "板块轮动":
        if "sector_rotation_data" not in st.session_state:
            st.session_state.sector_rotation_data = None
            st.info("💡 板块轮动:监控板块资金流向、热度排名、追踪龙头股")
        
        if st.button("监控板块轮动", key="monitor_sector"):
            with st.spinner('正在监控板块轮动...'):
                from logic.algo_advanced import AdvancedPatternAnalyzer
                st.session_state.sector_rotation_data = AdvancedPatternAnalyzer.monitor_sector_rotation()
        
        # 从session_state获取数据
        sector_data = st.session_state.get('sector_rotation_data') or {}
        
        if sector_data.get('数据状态') == '正常':
                    # 显示最强板块
                    if sector_data.get('最强板块'):
                        strongest = sector_data['最强板块']
                        st.success(f"🔥 **最强板块**: {strongest['板块名称']} - 热度评分: {strongest['热度评分']}")
                    
                    # 显示热门板块
                    if sector_data.get('热门板块'):
                        st.subheader("🔥 热门板块")
                        
                        # 格式化主力净流入
                        formatted_hot = []
                        for s in sector_data['热门板块']:
                            formatted_s = s.copy()
                            formatted_s['主力净流入'] = format_amount(s['主力净流入'])
                            formatted_hot.append(formatted_s)
                        
                        hot_df = pd.DataFrame(formatted_hot)
                        st.dataframe(hot_df, width="stretch")
                        
                        # 板块热度对比图
                        fig_heat = go.Figure()
                        fig_heat.add_trace(go.Bar(
                            x=hot_df['板块名称'],
                            y=hot_df['热度评分'],
                            name='热度评分',
                            marker=dict(
                                color=hot_df['热度评分'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="热度评分")
                            ),
                            text=hot_df['热度评分'],
                            textposition='outside'
                        ))
                        
                        fig_heat.update_layout(
                            title="板块热度排名",
                            xaxis_title="板块",
                            yaxis_title="热度评分",
                            height=400
                        )
                        st.plotly_chart(fig_heat, width="stretch")
            
            # 显示冷门板块
        if  sector_data.get('冷门板块'):
                st.subheader("❄️ 冷门板块")
                
                # 格式化主力净流入
                formatted_cold = []
                for s in sector_data['冷门板块']:
                    formatted_s = s.copy()
                    formatted_s['主力净流入'] = format_amount(s['主力净流入'])
                    formatted_cold.append(formatted_s)
                
                cold_df = pd.DataFrame(formatted_cold)
                st.dataframe(cold_df, width="stretch")
        
        # 板块龙头追踪
        if sector_data.get('热门板块'):
            from logic.algo_advanced import AdvancedPatternAnalyzer
            
            st.subheader("🏆 板块龙头追踪")
            
            selected_sector = st.selectbox(
                "选择板块追踪龙头",
                [s['板块名称'] for s in sector_data.get('热门板块')],
                key="select_sector_for_leader"
            )
            
            if st.button("追踪龙头", key="track_leader"):
                with st.spinner('正在追踪龙头股...'):
                    st.session_state.leader_data = AdvancedPatternAnalyzer.track_sector_leaders(selected_sector)
        
        # 显示龙头追踪结果
        if 'leader_data' in st.session_state:
            leader_data = st.session_state.leader_data
            
            if leader_data.get('数据状态') == '正常':
                if leader_data.get('龙头股'):
                    # 格式化成交额
                    formatted_leaders = []
                    for leader in leader_data['龙头股']:
                        formatted_leader = leader.copy()
                        formatted_leader['成交额'] = format_amount(leader['成交额'])
                        formatted_leaders.append(formatted_leader)
                    
                    leader_df = pd.DataFrame(formatted_leaders)
                    st.dataframe(leader_df, width="stretch")
                    
                    # 显示最佳龙头
                    best_leader = leader_df.iloc[0]
                    st.success(f"🏆 **最佳龙头**: {best_leader['名称']} ({best_leader['代码']}) - 评分: {best_leader['龙头评分']}")
                else:
                    st.info("该板块暂无龙头股")
            else:
                st.error(f"❌ {leader_data.get('数据状态', '未知错误')}")
                if '说明' in leader_data:
                    st.info(f"💡 {leader_data['说明']}")
    
    elif sentiment_type == "连板高度":
        st.subheader("🔗 连板高度分析")
        
        st.info("💡 连板高度:分析不同板数的胜率、连板股特征、高度预警系统")
        
        if st.button("分析连板高度", key="analyze_board_height"):
            with st.spinner('正在分析连板高度...'):
                from logic.algo_advanced import AdvancedPatternAnalyzer
                
                board_data = AdvancedPatternAnalyzer.analyze_board_height()
                
                if board_data['数据状态'] == '正常':
                    # 显示连板统计(放在最前面)
                    if not board_data['连板统计'].empty:
                        st.subheader("📊 连板高度统计")
                        
                        board_df = board_data['连板统计'].copy()
                        # 按连板数降序排序
                        board_df = board_df.sort_index(ascending=False)
                        st.dataframe(board_df, width="stretch")
                        
                        # 胜率对比图
                        fig_win_rate = go.Figure()
                        fig_win_rate.add_trace(go.Bar(
                            x=board_df.index.astype(str),
                            y=board_df['胜率'],
                            name='胜率',
                            marker_color='green',
                            text=board_df['胜率'],
                            textposition='outside'
                        ))
                        
                        fig_win_rate.update_layout(
                            title="不同板数胜率对比",
                            xaxis_title="连板数",
                            yaxis_title="胜率(%)",
                            height=400
                        )
                        st.plotly_chart(fig_win_rate, width="stretch")
                    
                    # 显示风险预警
                    if board_data['风险预警']:
                        st.subheader("⚠️ 风险预警")
                        for warning in board_data['风险预警']:
                            st.warning(warning)
                    
                    # 显示连板特征
                    if board_data['连板特征']:
                        st.subheader("🔍 连板股特征分析")
                        
                        feature_df = pd.DataFrame(board_data['连板特征'])
                        st.dataframe(feature_df, width="stretch")
                        
                        # 风险等级分布
                        risk_dist = feature_df['风险等级'].value_counts()
                        
                        fig_risk = go.Figure()
                        fig_risk.add_trace(go.Bar(
                            x=risk_dist.index,
                            y=risk_dist.values,
                            name='数量',
                            marker=dict(
                                color=['rgba(255, 99, 132, 0.8)', 'rgba(255, 159, 64, 0.8)', 'rgba(255, 205, 86, 0.8)', 'rgba(75, 192, 192, 0.8)'],
                            ),
                            text=risk_dist.values,
                            textposition='outside'
                        ))
                        
                        fig_risk.update_layout(
                            title="连板股风险等级分布",
                            xaxis_title="风险等级",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_risk, width="stretch")
                    
                    # 高板数股票
                    if not board_data['高板数股票'].empty:
                        st.subheader("🔴 高板数股票(风险较高)")
                        
                        high_risk_df = board_data['高板数股票']
                        st.dataframe(high_risk_df, width="stretch")
                else:
                    st.error(f"❌ {board_data['数据状态']}")
                    if '说明' in board_data:
                        st.info(f"💡 {board_data['说明']}")

with tab_hot_topics:
    st.subheader("🎯 热点题材挖掘")
    st.caption("实时检测板块异动、识别龙头股、分析题材持续度")

    # 功能选择
    topic_mode = st.radio("选择功能", ["热点题材扫描", "题材持续度分析"], horizontal=True)

    if topic_mode == "热点题材扫描":
        st.divider()
        st.subheader("🔍 热点题材扫描")

        # 扫描参数
        col_topic1, col_topic2 = st.columns(2)
        with col_topic1:
            topic_limit = st.slider("扫描板块数量", 10, 50, 20, 5)
        with col_topic2:
            if st.button("🔍 开始扫描", key="scan_hot_topics_btn"):
                st.session_state.scan_hot_topics = True
                st.rerun()

        # 执行扫描
        if st.session_state.get('scan_hot_topics', False):
            with st.spinner('正在扫描热点题材...'):
                topic_result = AdvancedAlgo.scan_hot_topics(limit=topic_limit)

            if topic_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！发现 {len(topic_result['热点题材'])} 个热点题材")

                if topic_result['热点题材']:
                    # 显示热点题材列表
                    st.divider()
                    st.subheader("📊 热点题材列表")

                    for topic_name, topic_data in topic_result['热点题材'].items():
                        with st.expander(f"{topic_data['板块类型']} {topic_name} - 涨幅: {topic_data['涨跌幅']:.2f}%"):
                            # 显示板块基本信息
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("涨跌幅", f"{topic_data['涨跌幅']:.2f}%")
                            with col2:
                                st.metric("涨家数", topic_data['涨家数'])
                            with col3:
                                st.metric("跌家数", topic_data['跌家数'])
                            with col4:
                                st.metric("量比", f"{topic_data['量比']:.2f}")

                            # 显示龙头股
                            st.write("**🔥 龙头股：**")
                            for idx, stock in enumerate(topic_data['龙头股'], 1):
                                st.write(f"{idx}. {stock['名称']} ({stock['代码']}) - 涨幅: {stock['涨跌幅']:.2f}%, 成交额: {format_amount(stock['成交额'])}")

                            # 分析题材持续度按钮
                            if st.button(f"📈 分析题材持续度", key=f"analyze_continuity_{topic_name}"):
                                st.session_state.analyze_topic = topic_name
                                st.rerun()

                            # 添加到自选股按钮
                            for stock in topic_data['龙头股']:
                                if st.button(f"⭐ 添加 {stock['名称']} 到自选", key=f"add_topic_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                else:
                    st.warning("⚠️ 未发现热点题材")
                    st.info("💡 提示：当前市场无明显热点，建议观望")
            else:
                st.error(f"❌ {topic_result['数据状态']}")
                if '说明' in topic_result:
                    st.info(f"💡 {topic_result['说明']}")
        else:
            st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的热点题材")

    elif topic_mode == "题材持续度分析":
        st.divider()
        st.subheader("📈 题材持续度分析")

        st.info("""
        **题材持续度分析：**
        - 分析题材的历史表现和持续性
        - 判断题材所处的阶段（上升期、活跃期、衰退期、震荡期）
        - 提供操作建议
        """)

        # 输入板块名称
        topic_name_input = st.text_input("输入板块名称", placeholder="如：人工智能、新能源汽车、半导体...")

        # 分析天数
        analysis_days = st.slider("分析天数", 10, 90, 30, 5)

        if st.button("📊 开始分析", key="analyze_topic_continuity"):
            if topic_name_input:
                with st.spinner(f'正在分析 {topic_name_input} 的持续度...'):
                    continuity_result = AdvancedAlgo.analyze_topic_continuity(topic_name_input, days=analysis_days)

                if continuity_result['数据状态'] == '正常':
                    # 显示持续度指标
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("平均涨跌幅", f"{continuity_result['平均涨跌幅']:.2f}%")
                    with col2:
                        st.metric("上涨概率", f"{continuity_result['上涨概率']}%")
                    with col3:
                        st.metric("波动率", f"{continuity_result['波动率']:.2f}")
                    with col4:
                        st.metric("趋势强度", f"{continuity_result['趋势强度']:.2f}")

                    # 显示当前阶段
                    st.divider()
                    st.subheader("🔄 当前阶段")
                    stage_color = {
                        "上升期": "🔥",
                        "活跃期": "🟡",
                        "衰退期": "🔴",
                        "震荡期": "🟢"
                    }
                    st.info(f"{stage_color.get(continuity_result['当前阶段'], '📊')} **{continuity_result['当前阶段']}**")

                    # 显示操作建议
                    st.subheader("💡 操作建议")
                    st.success(continuity_result['操作建议'])

                    # 显示详细指标
                    st.divider()
                    st.subheader("📊 详细指标")

                    detail_df = pd.DataFrame({
                        '指标': ['平均涨跌幅', '最大涨幅', '最大跌幅', '上涨天数', '总天数', '上涨概率', '波动率', '趋势强度'],
                        '数值': [
                            f"{continuity_result['平均涨跌幅']:.2f}%",
                            f"{continuity_result['最大涨幅']:.2f}%",
                            f"{continuity_result['最大跌幅']:.2f}%",
                            continuity_result['上涨天数'],
                            continuity_result['总天数'],
                            f"{continuity_result['上涨概率']}%",
                            continuity_result['波动率'],
                            continuity_result['趋势强度']
                        ]
                    })
                    st.dataframe(detail_df, width="stretch", hide_index=True)
                else:
                    st.error(f"❌ {continuity_result['数据状态']}")
                    if '说明' in continuity_result:
                        st.info(f"💡 {continuity_result['说明']}")
            else:
                st.warning("⚠️ 请输入板块名称")

with tab_alert:
    st.subheader("🔔 智能预警系统")
    st.caption("自定义条件预警，实时监控价格、量能、技术指标等信号")

    # 导入预警系统
    from logic.algo_alert import AlertSystem

    # 预警模式选择
    alert_mode = st.radio("选择功能", ["单股预警", "自选股批量预警"], horizontal=True)

    if alert_mode == "单股预警":
        st.divider()
        st.subheader("📊 单股预警设置")

        # 股票代码输入
        alert_symbol = st.text_input("股票代码", value=symbol, help="输入6位A股代码")

        # 预警条件设置
        st.write("### 预警条件设置")

        # 1. 价格预警
        with st.expander("💰 价格预警", expanded=False):
            price_alert_enabled = st.checkbox("启用价格预警", key="price_alert_enabled")
            col_price1, col_price2 = st.columns(2)
            with col_price1:
                price_above = st.number_input("突破预警价", value=0.0, min_value=0.0, step=0.01, disabled=not price_alert_enabled)
            with col_price2:
                price_below = st.number_input("跌破预警价", value=0.0, min_value=0.0, step=0.01, disabled=not price_alert_enabled)

        # 2. 涨跌幅预警
        with st.expander("📈 涨跌幅预警", expanded=False):
            change_alert_enabled = st.checkbox("启用涨跌幅预警", key="change_alert_enabled")
            col_change1, col_change2 = st.columns(2)
            with col_change1:
                change_above = st.number_input("涨幅预警(%)", value=5.0, step=0.1, disabled=not change_alert_enabled)
            with col_change2:
                change_below = st.number_input("跌幅预警(%)", value=-5.0, step=0.1, disabled=not change_alert_enabled)

        # 3. 量能预警
        with st.expander("📊 量能预警", expanded=False):
            volume_alert_enabled = st.checkbox("启用量能预警", key="volume_alert_enabled")
            volume_ratio_threshold = st.slider("量比阈值", 1.5, 5.0, 2.0, 0.1, disabled=not volume_alert_enabled)

        # 4. 技术指标预警
        with st.expander("📉 技术指标预警", expanded=False):
            indicator_alert_enabled = st.checkbox("启用技术指标预警", key="indicator_alert_enabled")

            col_rsi1, col_rsi2 = st.columns(2)
            with col_rsi1:
                rsi_overbought = st.checkbox("RSI超买(>70)", value=True, disabled=not indicator_alert_enabled)
            with col_rsi2:
                rsi_oversold = st.checkbox("RSI超卖(<30)", value=True, disabled=not indicator_alert_enabled)

            col_macd1, col_macd2 = st.columns(2)
            with col_macd1:
                macd_golden_cross = st.checkbox("MACD金叉", value=True, disabled=not indicator_alert_enabled)
            with col_macd2:
                macd_death_cross = st.checkbox("MACD死叉", value=True, disabled=not indicator_alert_enabled)

        # 组装预警条件
        alert_conditions = {
            'price_alert_enabled': price_alert_enabled,
            'price_above': price_above,
            'price_below': price_below,
            'change_alert_enabled': change_alert_enabled,
            'change_above': change_above,
            'change_below': change_below,
            'volume_alert_enabled': volume_alert_enabled,
            'volume_ratio_threshold': volume_ratio_threshold,
            'indicator_alert_enabled': indicator_alert_enabled,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'macd_golden_cross': macd_golden_cross,
            'macd_death_cross': macd_death_cross
        }

        # 检查预警按钮
        if st.button("🔍 检查预警", key="check_single_alert"):
            with st.spinner('正在检查预警条件...'):
                alert_result = AlertSystem.check_alerts(alert_symbol, alert_conditions)

            if alert_result['数据状态'] == '正常':
                st.success(f"✅ 检查完成！发现 {alert_result['预警数量']} 个预警")

                if alert_result['预警列表']:
                    for alert in alert_result['预警列表']:
                        level_color = {
                            '高': '🔴',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{level_color.get(alert['预警级别'], '⚪')} {alert['预警类型']} - {alert['预警级别']}级"):
                            st.write(f"**说明：** {alert['说明']}")
                            if '当前价格' in alert:
                                st.write(f"**当前价格：** ¥{alert['当前价格']:.2f}")
                            if '当前涨跌幅' in alert:
                                st.write(f"**当前涨跌幅：** {alert['当前涨跌幅']}")
                            st.write(f"**预警条件：** {alert['预警条件']}")
                else:
                    st.info("👍 当前未触发任何预警条件")
            else:
                st.error(f"❌ {alert_result['数据状态']}")
                if '说明' in alert_result:
                    st.info(f"💡 {alert_result['说明']}")

    elif alert_mode == "自选股批量预警":
        st.divider()
        st.subheader("📋 自选股批量预警")

        st.info("💡 将对自选股中的所有股票进行批量预警检查")

        # 使用相同的预警条件设置（简化版）
        with st.expander("⚙️ 预警条件设置", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                change_above = st.number_input("涨幅预警(%)", value=5.0, step=0.1)
                change_below = st.number_input("跌幅预警(%)", value=-5.0, step=0.1)

            with col2:
                volume_ratio_threshold = st.slider("量比阈值", 1.5, 5.0, 2.0, 0.1)
                rsi_overbought = st.checkbox("RSI超买(>70)", value=True)
                rsi_oversold = st.checkbox("RSI超卖(<30)", value=True)

            with col3:
                macd_golden_cross = st.checkbox("MACD金叉", value=True)
                macd_death_cross = st.checkbox("MACD死叉", value=True)

        alert_conditions = {
            'change_alert_enabled': True,
            'change_above': change_above,
            'change_below': change_below,
            'volume_alert_enabled': True,
            'volume_ratio_threshold': volume_ratio_threshold,
            'indicator_alert_enabled': True,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'macd_golden_cross': macd_golden_cross,
            'macd_death_cross': macd_death_cross
        }

        # 批量检查按钮
        if st.button("🔍 批量检查预警", key="check_batch_alert"):
            if watchlist:
                # 进度条
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                total_stocks = len(watchlist)
                progress_text.text(f"🔍 正在检查 {total_stocks} 只自选股的预警...")
                
                # 批量检查预警
                batch_result = AlertSystem.scan_watchlist_alerts(watchlist, alert_conditions)
                progress_bar.progress(100)
                
                progress_bar.empty()
                progress_text.empty()

                if batch_result['数据状态'] == '正常':
                    st.success(f"✅ 检查完成！发现 {batch_result['预警总数']} 个预警")

                    if batch_result['预警列表']:
                        # 按预警级别分组显示
                        high_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '高']
                        medium_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '中']
                        low_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '低']

                        # 高级预警
                        if high_alerts:
                            st.divider()
                            st.subheader("🔴 高级预警")
                            for alert in high_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")
                                    st.write(f"**当前价格：** ¥{alert['当前价格']:.2f}")
                                    st.write(f"**当前涨跌幅：** {alert['当前涨跌幅']}")

                        # 中级预警
                        if medium_alerts:
                            st.divider()
                            st.subheader("🟡 中级预警")
                            for alert in medium_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")

                        # 低级预警
                        if low_alerts:
                            st.divider()
                            st.subheader("🟢 低级预警")
                            for alert in low_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")
                    else:
                        st.info("👍 自选股中未触发任何预警条件")
            else:
                st.warning("⚠️ 自选股列表为空，请先添加股票到自选股")

with tab_vp:
    st.subheader("📊 量价关系战法")
    st.caption("检测缩量回调、放量突破、顶背离、底背离等量价信号")

    # 股票代码输入
    vp_symbol = st.text_input("股票代码", value=symbol, help="输入6位A股代码", key="vp_symbol")

    if st.button("📊 分析量价关系", key="analyze_vp"):
        with st.spinner('正在分析量价关系...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(vp_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > 20:
                vp_result = AdvancedAlgo.detect_volume_price_signals(df)

                if vp_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！发现 {vp_result['信号数量']} 个量价信号")

                    if vp_result['信号列表']:
                        for signal in vp_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                    else:
                        st.info("👍 当前未发现明显的量价信号")
                else:
                    st.error(f"❌ {vp_result['数据状态']}")
            else:
                st.warning("⚠️ 数据不足，需要至少20天数据")

with tab_ma:
    st.subheader("📈 均线战法")
    st.caption("分析均线多头排列、金叉死叉、支撑压力")

    # 股票代码输入
    ma_symbol = st.text_input("股票代码", value=symbol, help="输入6位A股代码", key="ma_symbol")

    # 均线参数设置
    col_ma1, col_ma2, col_ma3 = st.columns(3)
    with col_ma1:
        ma_short = st.number_input("短期均线", value=5, min_value=3, max_value=20)
    with col_ma2:
        ma_medium = st.number_input("中期均线", value=10, min_value=5, max_value=30)
    with col_ma3:
        ma_long = st.number_input("长期均线", value=20, min_value=10, max_value=60)

    if st.button("📊 分析均线", key="analyze_ma"):
        with st.spinner('正在分析均线...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=90)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(ma_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > ma_long:
                ma_result = AdvancedAlgo.analyze_moving_average(df, short=ma_short, medium=ma_medium, long=ma_long)

                if ma_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！发现 {ma_result['信号数量']} 个均线信号")

                    # 显示均线值
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"MA{ma_short}", f"¥{ma_result['MA{ma_short}']:.2f}")
                    with col2:
                        st.metric(f"MA{ma_medium}", f"¥{ma_result['MA{ma_medium}']:.2f}")
                    with col3:
                        st.metric(f"MA{ma_long}", f"¥{ma_result['MA{ma_long}']:.2f}")

                    if ma_result['信号列表']:
                        st.divider()
                        for signal in ma_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                    else:
                        st.info("👍 当前未发现明显的均线信号")
                else:
                    st.error(f"❌ {ma_result['数据状态']}")
            else:
                st.warning(f"⚠️ 数据不足，需要至少{ma_long}天数据")

with tab_new_stock:
    st.subheader("🆕 次新股战法")
    st.caption("分析开板次新股、情绪周期、换手率")

    # 股票代码输入
    new_stock_symbol = st.text_input("股票代码", value=symbol, help="输入6位A股代码", key="new_stock_symbol")

    if st.button("📊 分析次新股", key="analyze_new_stock"):
        with st.spinner('正在分析次新股...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=180)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(new_stock_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > 10:
                new_stock_result = AdvancedAlgo.analyze_new_stock(df, new_stock_symbol)

                if new_stock_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！上市{new_stock_result['上市天数']}天")

                    # 显示基本信息
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("上市天数", f"{new_stock_result['上市天数']}天")
                    with col2:
                        st.metric("当前阶段", new_stock_result['当前阶段'])

                    # 显示操作建议
                    st.divider()
                    st.write("**💡 操作建议：**")
                    st.success(new_stock_result['操作建议'])

                    # 显示信号列表
                    if new_stock_result['信号列表']:
                        st.divider()
                        for signal in new_stock_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                else:
                    st.error(f"❌ {new_stock_result['数据状态']}")
                    if '说明' in new_stock_result:
                        st.info(f"💡 {new_stock_result['说明']}")
            else:
                st.warning("⚠️ 数据不足，需要至少10天数据")

with tab_capital:
    st.subheader("💰 游资席位分析")
    st.caption("分析龙虎榜游资、追踪操作模式、识别知名游资")

    # 导入游资分析器
    from logic.algo_capital import CapitalAnalyzer

    # 功能选择
    capital_mode = st.radio("选择功能", ["龙虎榜游资分析", "游资操作模式追踪", "游资下一步预测"], horizontal=True)

    if capital_mode == "龙虎榜游资分析":
        st.divider()
        st.subheader("🏆 龙虎榜游资分析")

        st.info("💡 分析当日龙虎榜中的游资席位操作")

        # 日期选择
        analysis_date = st.date_input("分析日期", value=pd.Timestamp.now(), key="capital_date")

        if st.button("🔍 分析龙虎榜", key="analyze_lhb_capital"):
            with st.spinner('正在分析龙虎榜游资...'):
                date_str = analysis_date.strftime("%Y%m%d")
                capital_result = CapitalAnalyzer.analyze_longhubu_capital(date=date_str)

            if capital_result['数据状态'] == '正常':
                st.success(f"✅ 分析完成！发现 {capital_result['活跃游资数']} 个活跃游资，共 {capital_result['总操作次数']} 次操作")

                # 显示游资统计汇总
                if capital_result['游资统计汇总']:
                    st.divider()
                    st.subheader("📊 游资统计汇总")

                    summary_df = pd.DataFrame(capital_result['游资统计汇总'])
                    st.dataframe(summary_df, width="stretch", hide_index=True)

                # 显示详细操作记录
                if capital_result['游资分析列表']:
                    st.divider()
                    st.subheader("📝 详细操作记录")

                    for record in capital_result['游资分析列表'][:20]:  # 只显示前20条
                        with st.expander(f"{record['游资名称']} - {record['股票名称']} ({record['股票代码']})"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("买入金额", format_amount(record['买入金额']))
                            with col2:
                                st.metric("卖出金额", format_amount(record['卖出金额']))
                            with col3:
                                st.metric("净买入", format_amount(record['净买入']))
                            st.write(f"**上榜日：** {record['上榜日']}")
                            st.write(f"**营业部：** {record['营业部名称']}")
                else:
                    st.info("👍 今日龙虎榜中无知名游资操作")
            else:
                st.error(f"❌ {capital_result['数据状态']}")
                if '说明' in capital_result:
                    st.info(f"💡 {capital_result['说明']}")

    elif capital_mode == "游资操作模式追踪":
        st.divider()
        st.subheader("📈 游资操作模式追踪")

        st.info("💡 追踪特定游资在指定时间内的操作规律")

        # 游资选择
        capital_name = st.selectbox("选择游资", list(CapitalAnalyzer.FAMOUS_CAPITALISTS.keys()), key="select_capital")

        # 分析天数
        track_days = st.slider("分析天数", 7, 90, 30, 1)

        if st.button("📊 追踪操作模式", key="track_capital_pattern"):
            with st.spinner(f'正在追踪 {capital_name} 的操作模式...'):
                pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=track_days)

            if pattern_result['数据状态'] == '正常':
                st.success(f"✅ 追踪完成！{capital_name} 在最近 {track_days} 天内有 {pattern_result['操作次数']} 次操作")

                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("操作次数", pattern_result['操作次数'])
                with col2:
                    st.metric("操作频率", f"{pattern_result['操作频率']:.2f}次/天")
                with col3:
                    st.metric("买入比例", f"{pattern_result['买入比例']}%")
                with col4:
                    st.metric("操作成功率", f"{pattern_result['操作成功率']}%")

                # 显示操作风格
                st.divider()
                st.write("**🎭 操作风格：**")
                st.info(pattern_result['操作风格'])

                # 显示资金流向
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总买入金额", format_amount(pattern_result['总买入金额']))
                with col2:
                    st.metric("总卖出金额", format_amount(pattern_result['总卖出金额']))

                # 显示操作记录
                if pattern_result['操作记录']:
                    st.divider()
                    st.subheader("📝 操作记录")

                    for record in pattern_result['操作记录'][-10:]:  # 只显示最近10条
                        with st.expander(f"{record['日期']} - {record['股票名称']} ({record['股票代码']})"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("买入金额", format_amount(record['买入金额']))
                            with col2:
                                st.metric("卖出金额", format_amount(record['卖出金额']))
                            with col3:
                                st.metric("净买入", format_amount(record['净买入']))
            else:
                st.error(f"❌ {pattern_result['数据状态']}")
                if '说明' in pattern_result:
                    st.info(f"💡 {pattern_result['说明']}")

    elif capital_mode == "游资下一步预测":
        st.divider()
        st.subheader("🔮 游资下一步预测")

        st.info("💡 基于历史操作模式预测游资下一步操作")

        # 游资选择
        predict_capital = st.selectbox("选择游资", list(CapitalAnalyzer.FAMOUS_CAPITALISTS.keys()), key="predict_capital")

        if st.button("🔮 预测下一步操作", key="predict_capital_next"):
            with st.spinner(f'正在预测 {predict_capital} 的下一步操作...'):
                prediction_result = CapitalAnalyzer.predict_capital_next_move(predict_capital)

            if prediction_result['数据状态'] == '正常':
                st.success(f"✅ 预测完成！")

                # 显示预测结果
                for prediction in prediction_result['预测列表']:
                    level_color = {
                        '高': '🔥',
                        '中': '🟡',
                        '低': '🟢'
                    }
                    with st.expander(f"{level_color.get(prediction['概率'], '⚪')} {prediction['预测类型']} - {prediction['概率']}"):
                        st.write(f"**说明：** {prediction['说明']}")
            else:
                st.error(f"❌ {prediction_result['数据状态']}")
                if '说明' in prediction_result:
                    st.info(f"💡 {prediction_result['说明']}")

with tab_limit_up:
    st.subheader("🎯 打板成功率预测")
    st.caption("基于历史数据预测次日打板成功率")

    # 导入打板预测器
    from logic.algo_limit_up import LimitUpPredictor

    # 功能选择
    limit_up_mode = st.radio("选择功能", ["单股打板预测", "自选股批量预测", "市场整体分析"], horizontal=True)

    if limit_up_mode == "单股打板预测":
        st.divider()
        st.subheader("📊 单股打板预测")

        # 股票代码输入
        limit_up_symbol = st.text_input("股票代码", value=symbol, help="输入6位A股代码", key="limit_up_symbol")

        if st.button("📊 预测打板成功率", key="predict_limit_up"):
            with st.spinner('正在预测打板成功率...'):
                prediction_result = LimitUpPredictor.predict_limit_up_success_rate(limit_up_symbol)

            if prediction_result['数据状态'] == '正常':
                st.success(f"✅ 预测完成！该股票历史涨停 {prediction_result['总涨停次数']} 次")

                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总涨停次数", prediction_result['总涨停次数'])
                with col2:
                    st.metric("成功率", f"{prediction_result['成功率']}%")
                with col3:
                    st.metric("综合评分", prediction_result['综合评分'])
                with col4:
                    st.metric("评级", prediction_result['评级'])

                # 显示操作建议
                st.divider()
                st.write("**💡 操作建议：**")
                st.success(prediction_result['操作建议'])

                # 显示影响因素
                if prediction_result['影响因素']:
                    st.divider()
                    st.subheader("📊 影响因素")

                    factor_df = pd.DataFrame(prediction_result['影响因素'])
                    st.dataframe(factor_df, width="stretch", hide_index=True)

                # 显示涨停记录
                if prediction_result['涨停记录']:
                    st.divider()
                    st.subheader("📝 最近涨停记录")

                    record_df = pd.DataFrame(prediction_result['涨停记录'])
                    st.dataframe(record_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {prediction_result['数据状态']}")
                if '说明' in prediction_result:
                    st.info(f"💡 {prediction_result['说明']}")

    elif limit_up_mode == "自选股批量预测":
        st.divider()
        st.subheader("📋 自选股批量预测")

        st.info("💡 批量预测自选股中所有股票的打板成功率")

        if watchlist:
            if st.button("📊 批量预测", key="batch_predict_limit_up"):
                # 进度条
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                total_stocks = len(watchlist)
                progress_text.text(f"🔮 正在预测 {total_stocks} 只自选股的打板成功率...")
                
                batch_result = LimitUpPredictor.batch_predict_limit_up(watchlist)
                progress_bar.progress(100)
                
                progress_bar.empty()
                progress_text.empty()

                if batch_result['数据状态'] == '正常':
                    st.success(f"✅ 预测完成！共预测 {batch_result['预测总数']} 只股票")

                    # 显示预测结果
                    prediction_df = pd.DataFrame(batch_result['预测列表'])
                    st.dataframe(prediction_df, width="stretch", hide_index=True)

                    # 按评级分组
                    excellent = [p for p in batch_result['预测列表'] if '优秀' in p['评级']]
                    good = [p for p in batch_result['预测列表'] if '良好' in p['评级']]
                    general = [p for p in batch_result['预测列表'] if '一般' in p['评级']]
                    poor = [p for p in batch_result['预测列表'] if '较差' in p['评级']]

                    # 优秀股票
                    if excellent:
                        st.divider()
                        st.subheader("🔥 优秀股票")
                        for stock in excellent:
                            st.write(f"• {stock['股票代码']} - 成功率: {stock['成功率']}%, 评分: {stock['综合评分']}")
        else:
            st.warning("⚠️ 自选股列表为空，请先添加股票到自选股")

    elif limit_up_mode == "市场整体分析":
        st.divider()
        st.subheader("📈 市场整体分析")

        st.info("💡 分析今日涨停股票的整体打板成功率")

        if st.button("📊 分析市场", key="analyze_market_limit_up"):
            with st.spinner('正在分析市场整体打板成功率...'):
                market_result = LimitUpPredictor.analyze_market_limit_up_success()

            if market_result['数据状态'] == '正常':
                st.success(f"✅ 分析完成！今日涨停 {market_result['今日涨停数']} 只股票")

                # 显示基本信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("今日涨停数", market_result['今日涨停数'])
                with col2:
                    st.metric("分析样本数", market_result['分析样本数'])
                with col3:
                    st.metric("市场平均成功率", f"{market_result['市场平均成功率']}%")

                # 显示评级分布
                if market_result['评级分布']:
                    st.divider()
                    st.subheader("📊 评级分布")

                    rating_df = pd.DataFrame(list(market_result['评级分布'].items()), columns=['评级', '数量'])
                    st.dataframe(rating_df, width="stretch", hide_index=True)

                # 显示详细预测
                if market_result['详细预测']:
                    st.divider()
                    st.subheader("📝 详细预测")

                    prediction_df = pd.DataFrame(market_result['详细预测'])
                    st.dataframe(prediction_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {market_result['数据状态']}")
                if '说明' in market_result:
                    st.info(f"💡 {market_result['说明']}")

with tab_smart:
    st.subheader("🤖 智能推荐系统")
    st.caption("根据市场行情自动推荐相关战法")

    # 导入智能推荐器
    from logic.smart_recommender import SmartRecommender

    # 功能选择
    smart_mode = st.radio("选择功能", ["每日报告", "战法推荐", "市场分析"], horizontal=True)

    if smart_mode == "每日报告":
        st.divider()
        st.subheader("📊 每日报告")

        if st.button("📊 生成今日报告", key="generate_daily_report"):
            with st.spinner('正在生成今日报告...'):
                report = SmartRecommender.generate_daily_report()

            if '日期' in report:
                st.success(f"✅ 报告生成成功！")

                # 显示市场情绪
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("市场情绪", report['市场情绪'])
                with col2:
                    st.metric("平均涨跌幅", report['市场数据']['平均涨跌幅'])
                with col3:
                    st.metric("涨跌比", report['市场数据']['涨跌比'])

                # 显示情绪描述
                st.divider()
                st.write("**📝 情绪描述：**")
                st.info(report['情绪描述'])

                # 显示操作建议
                st.divider()
                st.write("**💡 操作建议：**")
                st.success(report['操作建议'])

                # 显示推荐战法
                if report['推荐战法']:
                    st.divider()
                    st.subheader("🎯 推荐战法")

                    for strategy in report['推荐战法']:
                        priority_color = {
                            '高': '🔥',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{priority_color.get(strategy['优先级'], '⚪')} {strategy['战法名称']} - {strategy['优先级']}"):
                            st.write(f"**推荐理由：** {strategy['推荐理由']}")
                            st.write(f"**适用场景：** {strategy['适用场景']}")
            else:
                st.error(f"❌ {report.get('数据状态', '生成失败')}")
                if '说明' in report:
                    st.info(f"💡 {report['说明']}")

    elif smart_mode == "战法推荐":
        st.divider()
        st.subheader("🎯 战法推荐")

        st.info("💡 根据当前市场情况推荐最适合的战法")

        if st.button("🎯 获取推荐", key="get_strategy_recommendations"):
            with st.spinner('正在分析市场并推荐战法...'):
                # 分析市场情况
                market_condition = SmartRecommender.analyze_market_condition()

                if market_condition['数据状态'] == '正常':
                    # 推荐战法
                    recommendations = SmartRecommender.recommend_strategies(market_condition)

                    st.success(f"✅ 分析完成！为您推荐 {recommendations['推荐数量']} 个战法")

                    # 显示市场情况
                    st.divider()
                    st.subheader("📊 市场情况")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("市场情绪", market_condition['市场情绪'])
                    with col2:
                        st.metric("涨跌比", market_condition['涨跌比'])
                    with col3:
                        st.metric("涨停数", market_condition['涨停股票'])
                    with col4:
                        st.metric("跌停数", market_condition['跌停股票'])

                    # 显示推荐战法
                    st.divider()
                    for strategy in recommendations['推荐列表']:
                        priority_color = {
                            '高': '🔥',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{priority_color.get(strategy['优先级'], '⚪')} {strategy['战法名称']} - {strategy['优先级']}"):
                            st.write(f"**推荐理由：** {strategy['推荐理由']}")
                            st.write(f"**适用场景：** {strategy['适用场景']}")
                else:
                    st.error(f"❌ {market_condition['数据状态']}")
                    if '说明' in market_condition:
                        st.info(f"💡 {market_condition['说明']}")

    elif smart_mode == "市场分析":
        st.divider()
        st.subheader("📈 市场分析")

        if st.button("📊 分析市场", key="analyze_market"):
            with st.spinner('正在分析市场...'):
                market_condition = SmartRecommender.analyze_market_condition()

            if market_condition['数据状态'] == '正常':
                st.success("✅ 分析完成！")

                # 显示市场指标
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("总股票数", market_condition['总股票数'])
                with col2:
                    st.metric("上涨股票", market_condition['上涨股票'])
                with col3:
                    st.metric("下跌股票", market_condition['下跌股票'])
                with col4:
                    st.metric("涨停股票", market_condition['涨停股票'])
                with col5:
                    st.metric("跌停股票", market_condition['跌停股票'])

                # 显示详细数据
                st.divider()
                st.subheader("📊 详细数据")

                market_df = pd.DataFrame({
                    '指标': ['市场情绪', '涨跌比', '平均涨跌幅', '涨停数', '跌停数'],
                    '数值': [
                        market_condition['市场情绪'],
                        market_condition['涨跌比'],
                        f"{market_condition['平均涨跌幅']}%",
                        market_condition['涨停股票'],
                        market_condition['跌停股票']
                    ]
                })
                st.dataframe(market_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {market_condition['数据状态']}")
                if '说明' in market_condition:
                    st.info(f"💡 {market_condition['说明']}")

with tab_risk:
    st.subheader("⚠️ 风险管理")
    st.caption("仓位管理、止损止盈提醒")

    # 导入风险管理器
    from logic.risk_manager import RiskManager

    # 功能选择
    risk_mode = st.radio("选择功能", ["仓位计算", "止损止盈检查", "组合风险评估", "风险预警"], horizontal=True)

    if risk_mode == "仓位计算":
        st.divider()
        st.subheader("💰 仓位计算")

        # 输入参数
        col1, col2, col3 = st.columns(3)
        with col1:
            capital = st.number_input("总资金", value=100000, min_value=0, step=1000)
        with col2:
            risk_per_trade = st.slider("单笔风险比例(%)", 1.0, 10.0, 2.0, 0.5) / 100
        with col3:
            stop_loss_pct = st.slider("止损比例(%)", 2.0, 10.0, 5.0, 0.5) / 100

        if st.button("📊 计算仓位", key="calculate_position"):
            position_result = RiskManager.calculate_position_size(capital, risk_per_trade, stop_loss_pct)

            st.success("✅ 计算完成！")

            # 显示结果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("单笔风险比例", position_result['单笔风险比例'])
            with col2:
                st.metric("止损比例", position_result['止损比例'])
            with col3:
                st.metric("建议仓位", Formatter.format_amount(position_result['建议仓位']))

            st.write(f"**仓位占比：** {position_result['仓位占比']}")
            st.write(f"**单笔最大损失：** {Formatter.format_amount(position_result['单笔最大损失'])}")

    elif risk_mode == "止损止盈检查":
        st.divider()
        st.subheader("📉 止损止盈检查")

        # 输入参数
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            check_symbol = st.text_input("股票代码", value=symbol, key="risk_check_symbol")
        with col2:
            current_price = st.number_input("当前价格", value=0.0, min_value=0.0, step=0.01)
        with col3:
            buy_price = st.number_input("买入价格", value=0.0, min_value=0.0, step=0.01)
        with col4:
            stop_loss_pct = st.slider("止损比例(%)", 2.0, 10.0, 5.0, 0.5) / 100

        if st.button("📊 检查", key="check_stop_loss"):
            if current_price > 0 and buy_price > 0:
                check_result = RiskManager.check_stop_loss(check_symbol, current_price, buy_price, stop_loss_pct)

                # 根据状态显示不同颜色
                if check_result['状态'] == '止损':
                    st.error(f"⚠️ {check_result['状态']}")
                elif check_result['状态'] == '止盈':
                    st.success(f"✅ {check_result['状态']}")
                else:
                    st.info(f"📊 {check_result['状态']}")

                # 显示详细信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("当前价格", Formatter.format_price(check_result['当前价格']))
                with col2:
                    st.metric("买入价格", Formatter.format_price(check_result['买入价格']))
                with col3:
                    st.metric("盈亏比例", check_result['盈亏比例'])

                st.write(f"**止损价：** {Formatter.format_price(check_result['止损价'])}")
                st.write(f"**止盈价：** {Formatter.format_price(check_result['止盈价'])}")

                if check_result['状态'] == '持有':
                    st.write(f"**距离止损：** {check_result['距离止损']}")
                    st.write(f"**距离止盈：** {check_result['距离止盈']}")

                st.write(f"**建议：** {check_result['建议']}")
            else:
                st.warning("⚠️ 请输入有效的价格")

    elif risk_mode == "组合风险评估":
        st.divider()
        st.subheader("📊 组合风险评估")

        st.info("💡 输入持仓信息，评估整体风险")

        # 这里可以添加持仓输入功能
        # 由于篇幅限制，简化处理
        st.warning("⚠️ 此功能需要输入详细持仓信息，请使用自选股管理")

    elif risk_mode == "风险预警":
        st.divider()
        st.subheader("🚨 风险预警")

        st.info("💡 检查自选股中的风险预警")

        if watchlist:
            if st.button("🔍 检查风险", key="check_risk_alerts"):
                st.warning("⚠️ 需要输入持仓成本价才能进行风险预警")
        else:
            st.warning("⚠️ 自选股列表为空")

with tab_history:
    st.subheader("📜 历史记录")
    st.caption("查看和导出分析历史")

    # 导入历史记录管理器
    from logic.history_manager import HistoryManager

    history_manager = HistoryManager()

    # 功能选择
    history_mode = st.radio("选择功能", ["查看历史", "导出记录", "清理旧记录"], horizontal=True)

    if history_mode == "查看历史":
        st.divider()
        st.subheader("📋 查看历史")

        # 筛选条件
        col1, col2, col3 = st.columns(3)
        with col1:
            analysis_type = st.selectbox("分析类型", ["全部", "单股分析", "热点题材", "智能预警", "量价关系"])
        with col2:
            history_symbol = st.text_input("股票代码（可选）", key="history_symbol")
        with col3:
            history_limit = st.slider("显示数量", 5, 50, 10, 5)

        if st.button("🔍 查询", key="query_history"):
            type_filter = None if analysis_type == "全部" else analysis_type
            symbol_filter = None if not history_symbol else history_symbol

            history_result = history_manager.get_history(type_filter, symbol_filter, history_limit)

            if history_result['状态'] == '成功':
                st.success(f"✅ 找到 {history_result['记录数量']} 条记录")

                if history_result['记录列表']:
                    for record in history_result['记录列表']:
                        with st.expander(f"{record['timestamp']} - {record['analysis_type']} - {record['symbol']}"):
                            st.json(record['result'])
                else:
                    st.info("👍 暂无历史记录")
            else:
                st.error(f"❌ {history_result['状态']}")
                if '错误信息' in history_result:
                    st.info(f"💡 {history_result['错误信息']}")

    elif history_mode == "导出记录":
        st.divider()
        st.subheader("📤 导出记录")

        # 筛选条件
        col1, col2 = st.columns(2)
        with col1:
            export_type = st.selectbox("分析类型", ["单股分析", "热点题材", "智能预警", "量价关系"])
        with col2:
            export_symbol = st.text_input("股票代码（可选）", key="export_symbol")

        if st.button("📤 导出Excel", key="export_history"):
            symbol_filter = None if not export_symbol else export_symbol
            export_result = history_manager.export_to_excel(export_type, symbol_filter)

            if export_result['状态'] == '成功':
                st.success(f"✅ 导出成功！共 {export_result['记录数量']} 条记录")
                st.info(f"📁 文件路径：{export_result['文件路径']}")
            else:
                st.error(f"❌ {export_result['状态']}")
                if '说明' in export_result:
                    st.info(f"💡 {export_result['说明']}")

    elif history_mode == "清理旧记录":
        st.divider()
        st.subheader("🗑️ 清理旧记录")

        keep_days = st.slider("保留天数", 7, 90, 30, 1)

        if st.button("🗑️ 清理", key="clear_old_history"):
            clear_result = history_manager.clear_old_history(keep_days)

            if clear_result['状态'] == '成功':
                st.success(f"✅ 清理完成！删除了 {clear_result['删除数量']} 条记录")
            else:
                st.error(f"❌ {clear_result['状态']}")

with tab_settings:
    st.subheader("⚙️ 系统设置")
    st.caption("个性化设置和系统配置")

    # 导入用户偏好管理器
    from logic.user_preferences import UserPreferences

    user_prefs = UserPreferences()

    # 功能选择
    settings_mode = st.radio("选择设置", ["显示设置", "分析设置", "预警设置", "风险设置", "其他设置"], horizontal=True)

    if settings_mode == "显示设置":
        st.divider()
        st.subheader("🎨 显示设置")

        theme = st.selectbox("主题", ["light", "dark"], index=0 if user_prefs.get('display', '主题') == 'light' else 1)
        show_grid = st.checkbox("显示网格", value=user_prefs.get('display', '显示网格', True))
        show_volume = st.checkbox("显示成交量", value=user_prefs.get('display', '显示成交量', True))

        if st.button("💾 保存显示设置", key="save_display_settings"):
            user_prefs.set('display', '主题', theme)
            user_prefs.set('display', '显示网格', show_grid)
            user_prefs.set('display', '显示成交量', show_volume)
            st.success("✅ 显示设置已保存")

    elif settings_mode == "分析设置":
        st.divider()
        st.subheader("📊 分析设置")

        analysis_days = st.slider("默认分析天数", 30, 180, user_prefs.get('analysis', '默认分析天数', 60), 10)
        stop_loss_pct = st.slider("默认止损比例(%)", 2.0, 10.0, user_prefs.get('analysis', '默认止损比例', 0.05) * 100, 0.5) / 100
        take_profit_pct = st.slider("默认止盈比例(%)", 5.0, 20.0, user_prefs.get('analysis', '默认止盈比例', 0.10) * 100, 0.5) / 100

        if st.button("💾 保存分析设置", key="save_analysis_settings"):
            user_prefs.set('analysis', '默认分析天数', analysis_days)
            user_prefs.set('analysis', '默认止损比例', stop_loss_pct)
            user_prefs.set('analysis', '默认止盈比例', take_profit_pct)
            st.success("✅ 分析设置已保存")

    elif settings_mode == "预警设置":
        st.divider()
        st.subheader("🔔 预警设置")

        enable_sound = st.checkbox("启用声音提醒", value=user_prefs.get('alert', '启用声音提醒', False))
        enable_popup = st.checkbox("启用弹窗提醒", value=user_prefs.get('alert', '启用弹窗提醒', True))
        refresh_interval = st.slider("刷新间隔(秒)", 30, 300, user_prefs.get('alert', '预警刷新间隔', 60), 10)

        if st.button("💾 保存预警设置", key="save_alert_settings"):
            user_prefs.set('alert', '启用声音提醒', enable_sound)
            user_prefs.set('alert', '启用弹窗提醒', enable_popup)
            user_prefs.set('alert', '预警刷新间隔', refresh_interval)
            st.success("✅ 预警设置已保存")

    elif settings_mode == "风险设置":
        st.divider()
        st.subheader("⚠️ 风险设置")

        risk_per_trade = st.slider("单笔风险比例(%)", 1.0, 5.0, user_prefs.get('risk', '单笔风险比例', 0.02) * 100, 0.5) / 100
        max_positions = st.slider("最大持仓数量", 3, 10, user_prefs.get('risk', '最大持仓数量', 5), 1)
        max_drawdown = st.slider("最大回撤限制(%)", 5.0, 20.0, user_prefs.get('risk', '最大回撤限制', 0.10) * 100, 1.0) / 100

        if st.button("💾 保存风险设置", key="save_risk_settings"):
            user_prefs.set('risk', '单笔风险比例', risk_per_trade)
            user_prefs.set('risk', '最大持仓数量', max_positions)
            user_prefs.set('risk', '最大回撤限制', max_drawdown)
            st.success("✅ 风险设置已保存")

    elif settings_mode == "其他设置":
        st.divider()
        st.subheader("🔧 其他设置")

        auto_refresh = st.checkbox("自动刷新", value=user_prefs.get('other', '自动刷新', False))
        save_history = st.checkbox("保存历史记录", value=user_prefs.get('other', '保存历史记录', True))
        history_days = st.slider("历史记录保留天数", 7, 90, user_prefs.get('other', '历史记录保留天数', 30), 1)

        if st.button("💾 保存其他设置", key="save_other_settings"):
            user_prefs.set('other', '自动刷新', auto_refresh)
            user_prefs.set('other', '保存历史记录', save_history)
            user_prefs.set('other', '历史记录保留天数', history_days)
            st.success("✅ 其他设置已保存")

    # 重置设置
    st.divider()
    if st.button("🔄 重置为默认设置", key="reset_settings"):
        user_prefs.reset_to_default()
        st.success("✅ 已重置为默认设置")