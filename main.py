"""
MyQuantTool - 个人化A股智能投研终端
主入口文件
"""

# 禁用 tqdm 进度条，避免停止应用时的 asyncio 错误
import os
os.environ['TQDM_DISABLE'] = '1'

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
import streamlit as st

# 初始化日志系统
logger = get_logger(__name__)
logger.info("=" * 50)
logger.info("应用启动")

# 页面配置
st.set_page_config(page_title="个人化A股智能终端", layout="wide", page_icon="📈", menu_items={
    'Get Help': None,
    'Report a bug': None,
    'About': None
})

# 添加自定义样式
st.markdown("""
<style>
.stAppHeader {
    background-color: #f0f2f6;
}
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

# --- 加载配置 ---
config = Config()

# API Key 优先级：环境变量 > 配置文件 > 默认值
API_KEY = os.getenv("SILICONFLOW_API_KEY") or config.get('api_key', 'sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet')

# --- 初始化核心组件 ---
db = DataManager()
ai_agent = DeepSeekAgent(api_key=API_KEY)
comparator = StockComparator(db)
backtest_engine = BacktestEngine()

logger.info("核心组件初始化完成")

# --- 初始化session state ---
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

if 'pattern_backtest_result' not in st.session_state:
    st.session_state.pattern_backtest_result = None
if 'portfolio_backtest_result' not in st.session_state:
    st.session_state.portfolio_backtest_result = None
if 'parameter_optimization_result' not in st.session_state:
    st.session_state.parameter_optimization_result = None
if 'pattern_combination_result' not in st.session_state:
    st.session_state.pattern_combination_result = None

# --- 应用标题 ---
st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# --- 导入UI模块 ---
from ui.single_stock import render_single_stock_tab
from ui.multi_compare import render_multi_compare_tab
from ui.sector_rotation import render_sector_rotation_tab
from ui.backtest import render_backtest_tab
from ui.long_hu_bang import render_long_hu_bang_tab
from ui.dragon_strategy import render_dragon_strategy_tab
from ui.auction import render_auction_tab
from ui.sentiment import render_sentiment_tab
from ui.hot_topics import render_hot_topics_tab
from ui.alert import render_alert_tab
from ui.volume_price import render_volume_price_tab
from ui.ma_strategy import render_ma_strategy_tab
from ui.new_stock import render_new_stock_tab
from ui.capital import render_capital_tab
from ui.limit_up import render_limit_up_tab
from ui.smart_recommend import render_smart_recommend_tab
from ui.risk import render_risk_tab
from ui.history import render_history_tab
from ui.settings import render_settings_tab

# --- 导入新页面模块 ---
from pages.monitor_dashboard import render_dashboard
from pages.capital_search import render_search_page

# --- 侧边栏 ---
with st.sidebar:
    st.header("🎮 控制台")
    
    # 全局加载状态
    if st.session_state.get('loading', False):
        st.info("⏳ 数据加载中...")
    
    # 获取自选股列表
    watchlist = config.get('watchlist', [])
    
    # 从配置文件加载默认值
    if st.session_state.selected_stock:
        default_symbol = st.session_state.selected_stock
    elif watchlist:
        default_symbol = watchlist[-1]
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
                st.write(f"找到 {len(matched_codes)} 只匹配的股票：")
                stock_options = []
                for code in matched_codes:
                    name = QuantAlgo.get_stock_name(code)
                    stock_options.append(f"{name} ({code})")
                
                selected_stock = st.selectbox("选择股票", stock_options)
                
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
            if current_time - last_refresh > 300:
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
            st.warning("该股票已在自选股中")

# --- 主要功能标签页 ---
tab_single, tab_compare, tab_backtest, tab_sector, tab_lhb, tab_dragon, tab_auction, tab_sentiment, tab_hot_topics, tab_alert, tab_vp, tab_ma, tab_new_stock, tab_capital, tab_limit_up, tab_smart, tab_risk, tab_history, tab_monitor, tab_search, tab_settings = st.tabs([
    "📊 单股分析", "🔍 多股对比", "🧪 策略回测", "🔄 板块轮动", "🏆 龙虎榜",
    "🔥 龙头战法", "⚡ 集合竞价", "📈 情绪分析", "🎯 热点题材", "🔔 智能预警",
    "📊 量价关系", "📈 均线战法", "🆕 次新股", "💰 游资席位", "🎯 打板预测",
    "🤖 智能推荐", "⚠️ 风险管理", "📜 历史记录", "📊 实时监控", "🔍 智能搜索", "⚙️ 系统设置"
])

# --- 渲染各个标签页 ---
with tab_single:
    render_single_stock_tab(db, config)

with tab_compare:
    render_multi_compare_tab(db, config)

with tab_backtest:
    render_backtest_tab(db, config)

with tab_sector:
    render_sector_rotation_tab(db, config)

with tab_lhb:
    render_long_hu_bang_tab(db, config)

with tab_dragon:
    render_dragon_strategy_tab(db, config)

with tab_auction:
    render_auction_tab(db, config)

with tab_sentiment:
    render_sentiment_tab(db, config)

with tab_hot_topics:
    render_hot_topics_tab(db, config)

with tab_alert:
    render_alert_tab(db, config)

with tab_vp:
    render_volume_price_tab(db, config)

with tab_ma:
    render_ma_strategy_tab(db, config)

with tab_new_stock:
    render_new_stock_tab(db, config)

with tab_capital:
    render_capital_tab(db, config)

with tab_limit_up:
    render_limit_up_tab(db, config)

with tab_smart:
    render_smart_recommend_tab(db, config)

with tab_risk:
    render_risk_tab(db, config)

with tab_history:
    render_history_tab(db, config)

with tab_monitor:
    render_dashboard()

with tab_search:
    render_search_page()

with tab_settings:
    render_settings_tab(db, config)

logger.info("应用渲染完成")