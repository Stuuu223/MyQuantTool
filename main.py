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
    gap: 4px;
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 8px;
    scrollbar-width: thin;
    scrollbar-color: #FF6B6B #f0f2f6;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
    height: 6px;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-track {
    background: #f0f2f6;
    border-radius: 3px;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
    background: #FF6B6B;
    border-radius: 3px;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb:hover {
    background: #ff5252;
}
.stTabs [data-baseweb="tab"] {
    flex-shrink: 0;
    white-space: nowrap;
    padding: 8px 12px;
    font-size: 13px;
}
/* 隐藏默认的英文侧边栏导航 */
[data-testid="stSidebarNav"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# --- 加载配置 ---
config = Config()

# API Key 安全获取
API_KEY = os.getenv("SILICONFLOW_API_KEY") or config.get('api_key')

# API Key 安全检查
if not API_KEY:
    st.error("❌ 缺少 API Key 配置")
    st.info("请设置环境变量: `export SILICONFLOW_API_KEY='your-key'`")
    st.info("或在配置文件中设置 `api_key` 字段")
    st.stop()

# 检查 API Key 格式（简单验证）
if not API_KEY.startswith('sk-'):
    logger.warning("API Key 格式可能不正确，建议以 'sk-' 开头")

# --- 初始化核心组件（智能缓存）---
@st.cache_resource
def get_db():
    """获取数据库管理器实例（缓存）"""
    return DataManager()

@st.cache_resource
def get_ai_agent():
    """获取 AI 代理实例（缓存）"""
    try:
        return DeepSeekAgent(api_key=API_KEY)
    except Exception as e:
        logger.warning(f"AI 初始化失败: {e}")
        return None

@st.cache_resource
def get_comparator():
    """获取股票对比器实例（缓存）"""
    return StockComparator(get_db())

@st.cache_resource
def get_backtest_engine():
    """获取回测引擎实例（缓存）"""
    return BacktestEngine()

# 初始化组件
db = get_db()
ai_agent = get_ai_agent()
comparator = get_comparator()
backtest_engine = get_backtest_engine()

logger.info("核心组件初始化完成")

# --- Session State 集中管理 ---
class SessionStateManager:
    """Session State 集中管理器"""
    DEFAULTS = {
        'selected_stock': None,
        'pattern_backtest_result': None,
        'portfolio_backtest_result': None,
        'parameter_optimization_result': None,
        'pattern_combination_result': None,
        'loading': False,
        'auto_refresh': False,
        'last_refresh': 0,
        'cache_hits': 0,
        'cache_misses': 0,
    }

    @staticmethod
    def init():
        """初始化所有 session_state 变量"""
        for key, value in SessionStateManager.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def clear_cache():
        """清理所有缓存数据"""
        # 清理 Streamlit 缓存
        st.cache_data.clear()
        st.cache_resource.clear()

        # 清理 session state 中的缓存数据
        st.session_state.cache_hits = 0
        st.session_state.cache_misses = 0
        st.session_state.pattern_backtest_result = None
        st.session_state.portfolio_backtest_result = None
        st.session_state.parameter_optimization_result = None
        st.session_state.pattern_combination_result = None

        logger.info("所有缓存已清理")

# 初始化 session state
SessionStateManager.init()

# --- 应用标题 ---
st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# --- 辅助函数 ---
def parse_selected_stock(selected_stock, fallback_symbol=None):
    """
    安全的股票代码解析函数
    
    Args:
        selected_stock: 例如 "中国平安 (600519)"
        fallback_symbol: 失败时的备用 (e.g., '600519')
    
    Returns:
        稳定的代码 (e.g., '600519')
    """
    if not selected_stock:
        return fallback_symbol
    
    try:
        # 第 1 步: 简单的格式验证
        parts = selected_stock.split('(')
        if len(parts) != 2:
            logger.warning(f"股票格式不常: {selected_stock}")
            return fallback_symbol
        
        # 第 2 步: 提取代码部分
        symbol = parts[1].rstrip(')')
        
        # 第 3 步: 验证代码不为空且是 6 位数字
        if not symbol or len(symbol) != 6 or not symbol.isdigit():
            logger.warning(f"代码无效: {symbol}")
            return fallback_symbol
        
        return symbol
    except Exception as e:
        logger.error(f"解析股票失败: {e}")
        return fallback_symbol


def ensure_list(value, name="value"):
    """
    将不同类型统一成 list
    
    Args:
        value: None, list, tuple, set 或 str
        name: 出错时的变量名
    
    Returns:
        list 或 []
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value]
    
    # 未预期的整数类型，记录警告
    logger.warning(f"{name} 类型不预期: {type(value)}, 返回 []")
    return []


@st.cache_data(ttl=3600)  # 缓存 1 小时
def get_safe_stock_name(code):
    """
    安全地获取股票名称，有双层缓存
    
    Args:
        code: 股票代码 e.g. '600519'
    
    Returns:
        股票名称 e.g. '贵州茅台'
    """
    try:
        # 第 1 层缓存: session_state (单会话级)
        cache_key = f"stock_name_{code}"
        if cache_key in st.session_state:
            logger.debug(f"从 session 缓存中获取 {code}")
            return st.session_state[cache_key]
        
        # 第 2 层缓存: @st.cache_data (函数级)
        name = QuantAlgo.get_stock_name(code)
        result = name or f"未知({code})"
        
        # 下次同一次会话中无需重新调用 API，速度 ~1ms
        st.session_state[cache_key] = result
        
        logger.debug(f"函数缓存中获取 {code} -> {result}")
        return result
    except Exception as e:
        logger.error(f"获取股票名称失败: {code}, {e}")
        return f"未知({code})"


# --- 数据验证层 ---
class InputValidator:
    """输入数据验证器"""
    
    @staticmethod
    def validate_stock_code(code: str) -> bool:
        """验证股票代码格式（6位数字）"""
        if not code or not isinstance(code, str):
            return False
        return len(code) == 6 and code.isdigit()
    
    @staticmethod
    def validate_percentage(value: float) -> bool:
        """验证百分比范围（0-100）"""
        return 0 <= value <= 100
    
    @staticmethod
    def validate_positive(value: float) -> bool:
        """验证正数"""
        return value > 0

# --- 性能监控 ---
class PerformanceMonitor:
    """性能监控和告警"""
    
    # 性能阈值（秒）
    THRESHOLDS = {
        'ai_init': 2.0,
        'db_init': 1.0,
        'data_fetch': 5.0,
    }
    
    @staticmethod
    def measure_time(operation_name: str):
        """测量操作耗时并记录告警"""
        import time
        start_time = time.time()
        
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # 检查是否超过阈值
                threshold = PerformanceMonitor.THRESHOLDS.get(operation_name)
                if threshold and elapsed > threshold:
                    logger.warning(f"⚠️ 性能告警: {operation_name} 耗时 {elapsed:.2f}s (阈值: {threshold}s)")
                else:
                    logger.debug(f"✅ {operation_name} 耗时 {elapsed:.2f}s")
                
                return result
            return wrapper
        return decorator


# --- 自动刷新管理 ---
class AutoRefreshManager:
    """自动刷新管理器"""
    REFRESH_INTERVAL = config.get('auto_refresh_interval', 300)  # 个性化
    
    @staticmethod
    def should_refresh(force=False):
        if force:
            return True
        last = st.session_state.get('last_refresh', 0)
        elapsed = pd.Timestamp.now().timestamp() - last
        return elapsed > AutoRefreshManager.REFRESH_INTERVAL
    
    @staticmethod
    def mark_refreshed():
        st.session_state.last_refresh = pd.Timestamp.now().timestamp()


# --- 配置管理 ---
class ConfigManager:
    """配置管理器 - 集中管理所有默认值"""
    DEFAULT_CONFIGS = {
        'default_symbol': '600519',
        'default_start_date': '2024-01-01',
        'atr_multiplier': 0.5,
        'grid_ratio': 0.1,
        'auto_refresh_interval': 300,
    }
    
    @staticmethod
    def get_safe(key):
        """安全获取配置，自动使用默认值"""
        default = ConfigManager.DEFAULT_CONFIGS.get(key)
        return config.get(key, default)

# --- 导入基础UI模块（轻量级） ---
# 注意：ui.single_stock 导入时间较长（~1.6s），已改为延迟导入
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

# --- 导入高级UI模块（延迟导入） ---
# 以下模块将在需要时才导入，以提升启动速度
# from ui.single_stock import render_single_stock_tab  # 重型模块，延迟导入
# from ui.kline_patterns import render_kline_patterns_tab
# from ui.advanced_backtest import render_advanced_backtest_tab
# from ui.paper_trading import render_paper_trading_tab
# from ui.performance_optimizer import render_performance_optimizer_tab
# from ui.lstm_predictor import render_lstm_predictor_tab
# from ui.hot_topics_enhanced import render_hot_topics_enhanced_tab
# from ui.limit_up_enhanced import render_limit_up_enhanced_tab

# --- 侧边栏 ---
with st.sidebar:
    # 功能导航
    st.header("🧭 功能导航")
    app_mode = st.radio(
        "选择功能模块",
        [
            "📈 市场分析",   # 包含：单股、多股、板块、情绪、热点
            "🔥 交易策略",   # 包含：龙头战法、均线、打板、竞价、量价
            "🧪 量化回测",   # 包含：策略回测、高级回测、K线形态、LSTM
            "💰 资产管理",   # 包含：虚拟交易、游资席位、风险、智能推荐
            "⚙️ 系统工具"    # 包含：性能优化、设置、历史记录
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # 控制台
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
            try:
                with st.spinner('正在搜索...'):
                    matched_codes = QuantAlgo.get_stock_code_by_name(search_name)
                
                if matched_codes:
                    st.write(f"找到 {len(matched_codes)} 只匹配的股票：")
                    stock_options = []
                    for code in matched_codes:
                        try:
                            name = QuantAlgo.get_stock_name(code) or f"未知({code})"
                            stock_options.append(f"{name} ({code})")
                        except Exception as e:
                            logger.error(f"获取股票名称失败: {code}, {e}")
                            stock_options.append(f"未知({code})")
                    
                    if stock_options:
                        selected_stock = st.selectbox("选择股票", stock_options)
                        
                        if selected_stock:
                            try:
                                symbol = selected_stock.split('(')[1].rstrip(')')
                            except (IndexError, AttributeError) as e:
                                logger.error(f"解析股票代码失败: {selected_stock}, {e}")
                                symbol = default_symbol
                    else:
                        st.warning("未找到匹配的股票")
                        symbol = default_symbol
                else:
                    st.warning("未找到匹配的股票")
                    symbol = default_symbol
            except Exception as e:
                st.error(f"搜索失败: {str(e)}")
                logger.error(f"股票搜索错误: {e}", exc_info=True)
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
            SessionStateManager.clear_cache()
            st.success("✅ 数据已刷新")
            st.rerun()
    
    with col_auto:
        if st.button("🧹 清理缓存"):
            SessionStateManager.clear_cache()
            st.success("✅ 缓存已清理")
            st.rerun()
    
    st.markdown("---")
    
    # 自动刷新
    auto_refresh = st.checkbox("自动刷新（每5分钟）", value=st.session_state.get('auto_refresh', False))
    st.session_state.auto_refresh = auto_refresh
    if auto_refresh:
        last_refresh = st.session_state.get('last_refresh', 0)
        current_time = pd.Timestamp.now().timestamp()
        if current_time - last_refresh > 300:
            SessionStateManager.clear_cache()
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
            try:
                stock_name = QuantAlgo.get_stock_name(stock) or f"未知({stock})"
            except Exception as e:
                logger.error(f"获取股票名称失败: {stock}, {e}")
                stock_name = f"未知({stock})"
            
            col_watch, col_remove = st.columns([3, 1])
            with col_watch:
                if st.button(f"📌 {stock_name} ({stock})", key=f"select_{stock}"):
                    st.session_state.selected_stock = stock
                    st.session_state.last_refresh = pd.Timestamp.now().timestamp()
                    st.rerun()
            with col_remove:
                if st.button("❌", key=f"remove_{stock}"):
                    try:
                        watchlist.remove(stock)
                        config.set('watchlist', watchlist)
                        st.success(f"已删除 {stock_name} ({stock})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {str(e)}")
                        logger.error(f"删除自选股失败: {stock}, {e}")
    
    add_stock = st.text_input("添加自选股", placeholder="输入股票代码", help="例如：600519")
    if st.button("➕ 添加") and add_stock:
        try:
            if add_stock not in watchlist:
                stock_name = QuantAlgo.get_stock_name(add_stock) or f"未知({add_stock})"
                watchlist.append(add_stock)
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock_name} ({add_stock}) 到自选股")
            else:
                st.warning("该股票已在自选股中")
        except Exception as e:
            st.error(f"添加失败: {str(e)}")
            logger.error(f"添加自选股失败: {add_stock}, {e}")

# --- 按功能大类渲染（Lazy Rendering）---
if app_mode == "📈 市场分析":
    # 只渲染这 5 个 Tab，其他模块代码不执行！性能提升 5 倍
    t1, t2, t3, t4, t5 = st.tabs(["📊 单股分析", "🔍 多股对比", "🔄 板块轮动", "📈 情绪分析", "🎯 热点题材"])
    with t1:
        # 延迟导入重型模块（~1.6s）
        with st.spinner("正在加载单股分析模块..."):
            from ui.single_stock import render_single_stock_tab
            render_single_stock_tab(db, config)
    with t2:
        render_multi_compare_tab(db, config)
    with t3:
        render_sector_rotation_tab(db, config)
    with t4:
        render_sentiment_tab(db, config)
    with t5:
        render_hot_topics_tab(db, config)

elif app_mode == "🔥 交易策略":
    # 交易策略模块
    t1, t2, t3, t4, t5 = st.tabs(["🔥 龙头战法", "📈 均线战法", "🎯 打板预测", "⚡ 集合竞价", "📊 量价关系"])
    with t1:
        render_dragon_strategy_tab(db, config)
    with t2:
        render_ma_strategy_tab(db, config)
    with t3:
        render_limit_up_tab(db, config)
    with t4:
        render_auction_tab(db, config)
    with t5:
        render_volume_price_tab(db, config)

elif app_mode == "🧪 量化回测":
    # 量化回测模块 - 包含高级功能，使用延迟导入
    t1, t2, t3, t4, t5 = st.tabs(["🧪 策略回测", "🧪 高级回测", "🔧 参数优化", "📊 K线形态", "🧠 LSTM预测"])
    with t1:
        render_backtest_tab(db, config)
    with t2:
        # 延迟导入高级回测模块
        with st.spinner("正在加载高级回测引擎..."):
            from ui.advanced_backtest import render_advanced_backtest_tab
            render_advanced_backtest_tab(db, config)
    with t3:
        # 延迟导入参数优化模块
        with st.spinner("正在加载参数优化引擎..."):
            from ui.parameter_optimization import render_parameter_optimization_tab
            render_parameter_optimization_tab(db, config)
    with t4:
        # 延迟导入 K线形态模块
        with st.spinner("正在加载 K线形态识别引擎..."):
            from ui.kline_patterns import render_kline_patterns_tab
            render_kline_patterns_tab(db, config)
    with t5:
        # 延迟导入 LSTM 预测模块（最重）
        with st.spinner("正在加载 AI 深度学习模型..."):
            from ui.lstm_predictor import render_lstm_predictor_tab
            render_lstm_predictor_tab(db, config)

elif app_mode == "💰 资产管理":
    # 资产管理模块
    t1, t2, t3, t4, t5 = st.tabs(["💰 模拟交易", "💰 游资席位", "⚠️ 风险管理", "🤖 智能推荐", "📡 实时监控"])
    with t1:
        # 延迟导入模拟交易模块
        with st.spinner("正在加载模拟交易系统..."):
            from ui.paper_trading import render_paper_trading_tab
            render_paper_trading_tab(db, config)
    with t2:
        render_capital_tab(db, config)
    with t3:
        render_risk_tab(db, config)
    with t4:
        render_smart_recommend_tab(db, config)
    with t5:
        # 延迟导入实时监控模块
        with st.spinner("正在加载实时监控系统..."):
            from ui.live_monitoring import render_live_monitoring_tab
            render_live_monitoring_tab(db, config)

elif app_mode == "⚙️ 系统工具":
    # 系统工具模块
    t1, t2, t3 = st.tabs(["⚡ 性能优化", "⚙️ 系统设置", "📜 历史记录"])
    with t1:
        # 延迟导入性能优化模块
        with st.spinner("正在加载性能优化工具..."):
            from ui.performance_optimizer import render_performance_optimizer_tab
            render_performance_optimizer_tab(db, config)
    with t2:
        render_settings_tab(db, config)
    with t3:
        render_history_tab(db, config)

logger.info("应用渲染完成")