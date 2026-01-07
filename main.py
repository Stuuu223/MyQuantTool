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

# --- 配置管理器 ---
class ConfigManager:
    """配置管理器 - 集中管理所有默认值"""
    DEFAULT_CONFIGS = {
        'default_symbol': '600519',
        'default_start_date': '2024-01-01',
        'atr_multiplier': 0.5,
        'grid_ratio': 0.1,
        'auto_refresh_interval': 300,  # 秒
    }

    @staticmethod
    def get_safe(key):
        """安全获取配置，自动使用默认值"""
        default = ConfigManager.DEFAULT_CONFIGS.get(key)
        return config.get(key, default)

# --- 数据验证层 ---
class InputValidator:
    """输入数据验证器"""

    @staticmethod
    def validate_stock_code(code, allow_empty=False):
        """
        验证股票代码

        Args:
            code: 股票代码
            allow_empty: 是否允许空值

        Returns:
            (is_valid, error_message)
        """
        if not code:
            if allow_empty:
                return True, None
            return False, "股票代码不能为空"

        if not isinstance(code, str):
            return False, f"股票代码必须是字符串，当前类型: {type(code)}"

        if len(code) != 6:
            return False, f"股票代码必须是6位数字，当前长度: {len(code)}"

        if not code.isdigit():
            return False, f"股票代码必须全是数字，当前值: {code}"

        return True, None

    @staticmethod
    def validate_date(date_str):
        """
        验证日期字符串

        Args:
            date_str: 日期字符串

        Returns:
            (is_valid, error_message)
        """
        if not date_str:
            return False, "日期不能为空"

        try:
            pd.to_datetime(date_str)
            return True, None
        except Exception as e:
            return False, f"日期格式无效: {date_str}, 错误: {e}"

    @staticmethod
    def validate_percentage(value, name="比例"):
        """
        验证百分比（0-100）

        Args:
            value: 百分比值
            name: 参数名称

        Returns:
            (is_valid, error_message)
        """
        try:
            num = float(value)
            if num < 0 or num > 100:
                return False, f"{name}必须在0-100之间，当前值: {num}"
            return True, None
        except (ValueError, TypeError):
            return False, f"{name}必须是数字，当前值: {value}"

    @staticmethod
    def validate_positive_number(value, name="数值"):
        """
        验证正数

        Args:
            value: 数值
            name: 参数名称

        Returns:
            (is_valid, error_message)
        """
        try:
            num = float(value)
            if num <= 0:
                return False, f"{name}必须大于0，当前值: {num}"
            return True, None
        except (ValueError, TypeError):
            return False, f"{name}必须是数字，当前值: {value}"

# --- 性能监控和告警 ---
class PerformanceMonitor:
    """性能监控器"""

    # 性能阈值（秒）
    THRESHOLDS = {
        'ai_init': 2.0,
        'db_init': 1.0,
        'stock_search': 1.0,
        'data_fetch': 3.0,
    }

    @staticmethod
    def measure_time(operation_name, threshold_key=None):
        """
        测量操作耗时并告警

        Args:
            operation_name: 操作名称
            threshold_key: 阈值键名

        Returns:
            装饰器
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                import time
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start

                    # 记录性能
                    logger.info(f"{operation_name} 耗时: {elapsed:.3f}s")

                    # 检查是否超过阈值
                    if threshold_key and threshold_key in PerformanceMonitor.THRESHOLDS:
                        threshold = PerformanceMonitor.THRESHOLDS[threshold_key]
                        if elapsed > threshold:
                            logger.warning(
                                f"⚠️ 性能告警: {operation_name} 耗时 {elapsed:.3f}s "
                                f"超过阈值 {threshold}s"
                            )

                    return result
                except Exception as e:
                    elapsed = time.time() - start
                    logger.error(f"{operation_name} 失败，耗时 {elapsed:.3f}s: {e}")
                    raise

            return wrapper
        return decorator

# --- 工具函数 ---
def get_safe_stock_name(code, name_hint=None):
    """
    安全地获取股票名称，支持缓存

    Args:
        code: 股票代码
        name_hint: 名称提示 (可选)

    Returns:
        股票名称或"未知(代码)"
    """
    if not code:
        return "未知()"

    try:
        # 从 session_state 缓存读取
        cache_key = f"stock_name_{code}"
        if cache_key in st.session_state:
            return st.session_state[cache_key]

        # 从数据库获取
        name = QuantAlgo.get_stock_name(code)

        if not name:
            result = name_hint or f"未知({code})"
        else:
            result = name

        # 缓存结果
        st.session_state[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"获取股票名称失败: code={code}, error={e}")
        return f"未知({code})"

def parse_selected_stock(selected_stock, fallback_symbol):
    """安全地从选择框中解析股票代码"""
    if not selected_stock:
        return fallback_symbol

    try:
        parts = selected_stock.split('(')
        if len(parts) != 2:  # 验证格式
            logger.warning(f"格式异常的股票选择: {selected_stock}")
            return fallback_symbol

        symbol = parts[1].rstrip(')')

        # 验证代码格式
        if not symbol or len(symbol) != 6 or not symbol.isdigit():
            logger.warning(f"无效的股票代码: {symbol}")
            return fallback_symbol

        return symbol

    except Exception as e:
        logger.error(f"解析股票代码异常: {selected_stock}, {e}")
        return fallback_symbol

def ensure_list(value, name="value"):
    """确保返回值是有效的列表"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    logger.warning(f"{name} 类型异常: {type(value)}")
    return []

class AutoRefreshManager:
    """自动刷新管理器"""
    REFRESH_INTERVAL = ConfigManager.get_safe('auto_refresh_interval')

    @staticmethod
    def should_refresh(force=False):
        """判断是否应该刷新"""
        if force:
            return True

        last_refresh = st.session_state.get('last_refresh', 0)
        current_time = pd.Timestamp.now().timestamp()
        elapsed = current_time - last_refresh

        should = elapsed > AutoRefreshManager.REFRESH_INTERVAL

        if should:
            logger.info(f"触发自动刷新，已经过 {elapsed:.0f}s")

        return should

    @staticmethod
    def mark_refreshed():
        """标记已刷新"""
        st.session_state.last_refresh = pd.Timestamp.now().timestamp()

# --- 应用标题 ---
st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

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

    # 控制台（使用 Expander 折叠）
    with st.expander("🎮 控制台", expanded=True):
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
        default_symbol = ConfigManager.get_safe('default_symbol')

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
                    matched_codes = ensure_list(
                        QuantAlgo.get_stock_code_by_name(search_name),
                        name="matched_codes"
                    )

                if not matched_codes:
                    st.info("💡 未找到匹配的股票，请尝试其他搜索条件")
                    st.info("提示: 可以尝试按股票代码搜索")
                    symbol = default_symbol
                else:
                    st.write(f"✅ 找到 {len(matched_codes)} 只匹配的股票")
                    stock_options = []
                    for code in matched_codes:
                        name = get_safe_stock_name(code)
                        stock_options.append(f"{name} ({code})")

                    if stock_options:
                        selected_stock = st.selectbox("选择股票", stock_options)

                        if selected_stock:
                            symbol = parse_selected_stock(selected_stock, default_symbol)
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
    
    start_date = st.date_input("开始日期", pd.to_datetime(ConfigManager.get_safe('default_start_date')))

    # 策略参数（使用 Expander 折叠）
    with st.expander("⚙️ 策略参数"):
        atr_mult = st.slider("ATR 倍数", 0.1, 2.0, float(ConfigManager.get_safe('atr_multiplier')), 0.1)
        grid_ratio = st.slider("网格比例", 0.05, 0.5, float(ConfigManager.get_safe('grid_ratio')), 0.05)

    run_ai = st.button("🧠 智能分析")

    st.markdown("---")

    # 自选股管理（使用 Expander 折叠）
    with st.expander("⭐ 自选股管理", expanded=False):
    
    # 数据刷新功能
        with st.expander("🔄 数据管理"):
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
            if auto_refresh and AutoRefreshManager.should_refresh():
                SessionStateManager.clear_cache()
                AutoRefreshManager.mark_refreshed()
                st.info("⏱️ 自动刷新中...")
                st.rerun()
    
        if watchlist:        st.write("已关注的股票：")
        
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
            # 使用 get_safe_stock_name 获取股票名称（带缓存）
            stock_name = get_safe_stock_name(stock)
            
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
    t1, t2, t3, t4 = st.tabs(["🧪 策略回测", "🧪 高级回测", "📊 K线形态", "🧠 LSTM预测"])
    with t1:
        render_backtest_tab(db, config)
    with t2:
        # 延迟导入高级回测模块
        with st.spinner("正在加载高级回测引擎..."):
            from ui.advanced_backtest import render_advanced_backtest_tab
            render_advanced_backtest_tab(db, config)
    with t3:
        # 延迟导入 K线形态模块
        with st.spinner("正在加载 K线形态识别引擎..."):
            from ui.kline_patterns import render_kline_patterns_tab
            render_kline_patterns_tab(db, config)
    with t4:
        # 延迟导入 LSTM 预测模块（最重）
        with st.spinner("正在加载 AI 深度学习模型..."):
            from ui.lstm_predictor import render_lstm_predictor_tab
            render_lstm_predictor_tab(db, config)

elif app_mode == "💰 资产管理":
    # 资产管理模块
    t1, t2, t3, t4 = st.tabs(["💰 模拟交易", "💰 游资席位", "⚠️ 风险管理", "🤖 智能推荐"])
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