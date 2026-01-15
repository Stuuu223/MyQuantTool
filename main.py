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
import importlib

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

# 延迟初始化组件（在首次使用时才初始化）
_db = None
_ai_agent = None
_comparator = None
_backtest_engine = None

def get_db_instance():
    """获取数据库实例（延迟初始化）"""
    global _db
    if _db is None:
        _db = get_db()
    return _db

def get_ai_agent_instance():
    """获取AI代理实例（延迟初始化）"""
    global _ai_agent
    if _ai_agent is None:
        _ai_agent = get_ai_agent()
    return _ai_agent

def get_comparator_instance():
    """获取股票对比器实例（延迟初始化）"""
    global _comparator
    if _comparator is None:
        _comparator = get_comparator()
    return _comparator

def get_backtest_engine_instance():
    """获取回测引擎实例（延迟初始化）"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = get_backtest_engine()
    return _backtest_engine

logger.info("核心组件初始化函数已定义（延迟加载）")

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
    
    @staticmethod
    def clear_data_cache():
        """仅清理数据缓存，保留结果缓存"""
        # 只清理数据相关的缓存，保留计算结果
        st.cache_data.clear()
        st.session_state.cache_hits = 0
        st.session_state.cache_misses = 0
        logger.info("数据缓存已清理")

# 初始化 session state
SessionStateManager.init()

# --- 应用标题 ---
st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据")

# --- V6.0 逻辑深化：市场情绪周期和主线识别展示 ---
@st.cache_resource
def get_market_cycle_manager():
    """获取市场周期管理器实例（缓存）"""
    try:
        from logic.market_cycle import MarketCycleManager
        return MarketCycleManager()
    except Exception as e:
        logger.warning(f"市场周期管理器初始化失败: {e}")
        return None

@st.cache_resource
def get_theme_detector():
    """获取主线识别器实例（缓存）"""
    try:
        from logic.theme_detector import ThemeDetector
        return ThemeDetector()
    except Exception as e:
        logger.warning(f"主线识别器初始化失败: {e}")
        return None

# 显示市场情绪周期和主线识别
def show_market_weather():
    """在主页显示市场"天气"（情绪周期和主线）"""
    try:
        # 获取实例
        cycle_manager = get_market_cycle_manager()
        theme_detector = get_theme_detector()
        
        if not cycle_manager and not theme_detector:
            return
        
        # 创建三列布局
        col1, col2, col3 = st.columns([2, 2, 1])
        
        # 周期类型对应的显示名称和颜色
        cycle_display = {
            'BOOM': {'name': '🔥 高潮期', 'color': '#FF6B6B'},
            'MAIN_RISE': {'name': '🚀 主升期', 'color': '#4ECDC4'},
            'CHAOS': {'name': '🌊 混沌期', 'color': '#FFD93D'},
            'ICE': {'name': '🧊 冰点期', 'color': '#6BCB77'},
            'DECLINE': {'name': '📉 退潮期', 'color': '#FF8C42'},
            'PANIC': {'name': '⛈️ 暴雨期', 'color': '#8B0000'},  # 🆕 V9.2 恐慌期
            'CAUTIOUS': {'name': '🌥️ 谨慎期', 'color': '#FFA500'}  # 🆕 V9.2 谨慎期
        }
        
        with col1:
            if cycle_manager:
                cycle_info = cycle_manager.get_current_phase()
                cycle_type = cycle_info.get('cycle', 'CHAOS')
                display_info = cycle_display.get(cycle_type, cycle_display['CHAOS'])
                
                st.markdown(f"""
                <div style="
                    background-color: {display_info['color']};
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h3 style="color: white; margin: 0; font-size: 18px;">
                        🌤️ 今日天气：{display_info['name']}
                    </h3>
                    <p style="color: white; margin: 5px 0 0 0; font-size: 14px;">
                        {cycle_info.get('description', '')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示策略建议
                st.info(f"💡 策略建议：{cycle_info.get('strategy', '')}")
                
                # 显示风险警告
                risk_warning = cycle_manager.get_risk_warning()
                if risk_warning:
                    st.warning(risk_warning)
        
        with col2:
            if theme_detector:
                # 获取涨停股票
                limit_up_stocks = []
                if cycle_manager:
                    limit_up_stocks = cycle_manager.market_indicators.get('limit_up_stocks', [])
                
                theme_info = theme_detector.analyze_main_theme(limit_up_stocks)
                
                st.markdown(f"""
                <div style="
                    background-color: #667EEA;
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h3 style="color: white; margin: 0; font-size: 18px;">
                        🎯 今日主线：{theme_info.get('main_theme', '未知')}
                    </h3>
                    <p style="color: white; margin: 5px 0 0 0; font-size: 14px;">
                        热度：{theme_info.get('theme_heat', 0):.1%}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示投资建议
                st.info(f"💡 {theme_info.get('suggestion', '')}")
        
        with col3:
            # 显示核心指标
            if cycle_manager:
                indicators = cycle_manager.get_market_emotion()
                
                st.markdown("### 📊 核心指标")
                
                metrics = [
                    ("涨停家数", indicators.get('limit_up_count', 0), "🔥"),
                    ("跌停家数", indicators.get('limit_down_count', 0), "❄️"),
                    ("最高板", indicators.get('highest_board', 0), "🏔️"),
                    ("平均溢价", f"{indicators.get('avg_profit', 0):.1%}", "💰"),
                    ("炸板率", f"{indicators.get('burst_rate', 0):.1%}", "💥"),
                    ("晋级率", f"{indicators.get('promotion_rate', 0):.1%}", "⬆️")
                ]
                
                for label, value, emoji in metrics:
                    st.metric(label, f"{emoji} {value}")
        
        st.markdown("---")
    
    except Exception as e:
        logger.error(f"显示市场天气失败: {e}")
        st.error(f"市场天气显示失败: {e}")

# 调用显示函数
show_market_weather()

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


@st.cache_data(ttl=86400)  # 缓存 24 小时
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
    REFRESH_INTERVAL = config.get('auto_refresh_interval', 600)  # 默认10分钟，减少刷新频率
    
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

# --- UI模块延迟加载函数 ---
# 所有UI模块都改为延迟导入，大幅提升启动速度
# 只在实际使用时才加载对应模块

def load_ui_module(module_name, function_name):
    """动态加载UI模块并返回渲染函数"""
    module = importlib.import_module(module_name)
    return getattr(module, function_name)

# --- 侧边栏 ---
with st.sidebar:
    # 功能导航
    st.header("🧭 功能导航")
    app_mode = st.radio(
        "选择功能模块",
        [
            "📈 市场分析",   # 包含：单股、多股、板块、情绪、热点
            "🧠 市场情绪",   # 包含：新闻、社交媒体、量价情绪分析
            "🔥 交易策略",   # 包含：龙头战法、均线、打板、竞价、量价
            "💼 交易执行",   # 包含：自动化交易、订单管理、滑点优化
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
            SessionStateManager.clear_data_cache()
            st.success("✅ 数据已刷新")
            st.rerun()
    
    with col_auto:
        if st.button("🧹 清理缓存"):
            SessionStateManager.clear_cache()
            st.success("✅ 缓存已清理")
            st.rerun()
    
    st.markdown("---")
    
    # 自动刷新
    auto_refresh = st.checkbox("自动刷新（每10分钟）", value=st.session_state.get('auto_refresh', False))
    st.session_state.auto_refresh = auto_refresh
    if auto_refresh:
        last_refresh = st.session_state.get('last_refresh', 0)
        current_time = pd.Timestamp.now().timestamp()
        if current_time - last_refresh > 600:
            SessionStateManager.clear_data_cache()
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
    # 市场分析模块 - 包含各种分析工具
    t1, t2, t3, t4, t5, t6 = st.tabs(["📈 单股分析", "📊 多股比较", "🔄 板块轮动", "🧠 情绪分析", "🔥 热点追踪", "📋 市场复盘"])
    with t1:
        # 延迟导入单股分析模块（重型模块）
        with st.spinner("正在加载单股分析引擎..."):
            render_single_stock_tab = load_ui_module('ui.single_stock', 'render_single_stock_tab')
            render_single_stock_tab(get_db_instance(), config)
    with t2:
        # 延迟导入多股比较模块
        with st.spinner("正在加载多股比较引擎..."):
            render_multi_compare_tab = load_ui_module('ui.multi_compare', 'render_multi_compare_tab')
            render_multi_compare_tab(get_db_instance(), config)
    with t3:
        # 延迟导入板块轮动模块
        with st.spinner("正在加载板块轮动引擎..."):
            render_sector_rotation_tab = load_ui_module('ui.sector_rotation', 'render_sector_rotation_tab')
            render_sector_rotation_tab(get_db_instance(), config)
    with t4:
        # 延迟导入情绪分析模块
        with st.spinner("正在加载情绪分析引擎..."):
            render_sentiment_tab = load_ui_module('ui.sentiment', 'render_sentiment_tab')
            render_sentiment_tab(get_db_instance(), config)
    with t5:
        # 延迟导入热点追踪模块
        with st.spinner("正在加载热点追踪引擎..."):
            render_hot_topics_tab = load_ui_module('ui.hot_topics', 'render_hot_topics_tab')
            render_hot_topics_tab(get_db_instance(), config)
    with t6:
        # 延迟导入市场复盘模块
        with st.spinner("正在加载市场复盘引擎..."):
            render_backtesting_review_tab = load_ui_module('ui.backtesting_review', 'render_backtesting_review_tab')
            render_backtesting_review_tab(get_db_instance(), config)

elif app_mode == "🔥 交易策略":
    # 交易策略模块
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18 = st.tabs(["🔥 龙头战法", "📈 均线战法", "🎯 打板预测", "⚡ 集合竞价", "📊 量价关系", "💰 游资席位", "🎯 半路战法", "🔍 买点扫描", "🕸️ 关系图谱", "👤 游资画像", "📈 短期涨跌", "🔮 机会预测", "🤖 多智能体", "📰 智能新闻", "🧠 实时情绪感知", "🐉 龙头识别跟踪", "⚡ 竞价预测系统", "🔧 在线参数调整"])
    with t1:
        # 延迟导入龙头战法模块
        with st.spinner("正在加载龙头战法引擎..."):
            dragon_strategy = __import__('ui.dragon_strategy', fromlist=['render_dragon_strategy_tab'])
            dragon_strategy.render_dragon_strategy_tab(get_db_instance(), config)
    with t2:
        # 延迟导入均线战法模块
        with st.spinner("正在加载均线战法引擎..."):
            ma_strategy = __import__('ui.ma_strategy', fromlist=['render_ma_strategy_tab'])
            ma_strategy.render_ma_strategy_tab(get_db_instance(), config)
    with t3:
        # 延迟导入打板预测模块
        with st.spinner("正在加载打板预测引擎..."):
            limit_up = __import__('ui.limit_up', fromlist=['render_limit_up_tab'])
            limit_up.render_limit_up_tab(get_db_instance(), config)
    with t4:
        # 延迟导入集合竞价模块
        with st.spinner("正在加载集合竞价引擎..."):
            auction = __import__('ui.auction', fromlist=['render_auction_tab'])
            auction.render_auction_tab(get_db_instance(), config)
    with t5:
        # 延迟导入量价关系模块
        with st.spinner("正在加载量价关系引擎..."):
            volume_price = __import__('ui.volume_price', fromlist=['render_volume_price_tab'])
            volume_price.render_volume_price_tab(get_db_instance(), config)
    with t6:
        # 延迟导入游资席位模块
        with st.spinner("正在加载游资席位引擎..."):
            capital = __import__('ui.capital', fromlist=['render_capital_tab'])
            capital.render_capital_tab(get_db_instance(), config)
    with t7:
        # 延迟导入半路战法模块
        with st.spinner("正在加载半路战法引擎..."):
            midway_strategy = __import__('ui.midway_strategy', fromlist=['render_midway_strategy_tab'])
            midway_strategy.render_midway_strategy_tab(get_db_instance(), config)
    with t8:
        # 延迟导入买点扫描模块
        with st.spinner("正在加载买点扫描引擎..."):
            buy_point_scanner = __import__('ui.buy_point_scanner', fromlist=['render_buy_point_scanner_tab'])
            buy_point_scanner.render_buy_point_scanner_tab(get_db_instance(), config)
    with t9:
        # 延迟导入关系图谱模块
        with st.spinner("正在加载关系图谱引擎..."):
            capital_network = __import__('ui.capital_network', fromlist=['render_capital_network_tab'])
            capital_network.render_capital_network_tab(get_db_instance(), config)
    with t10:
        # 延迟导入游资画像模块
        with st.spinner("正在加载游资画像引擎..."):
            capital_profiler = __import__('ui.capital_profiler', fromlist=['render_capital_profiler_tab'])
            capital_profiler.render_capital_profiler_tab(get_db_instance(), config)
    with t11:
        # 延迟导入短期涨跌模块
        with st.spinner("正在加载短期涨跌分析引擎..."):
            short_term_trend = __import__('ui.short_term_trend', fromlist=['render_short_term_trend_tab'])
            short_term_trend.render_short_term_trend_tab(get_db_instance(), config)
    with t12:
        # 延迟导入机会预测模块
        with st.spinner("正在加载机会预测引擎..."):
            opportunity_predictor = __import__('ui.opportunity_predictor', fromlist=['render_opportunity_predictor_tab'])
            opportunity_predictor.render_opportunity_predictor_tab(get_db_instance(), config)
    with t13:
        # 延迟导入多智能体分析模块
        with st.spinner("正在加载多智能体分析引擎..."):
            multi_agent_analysis = __import__('ui.multi_agent_analysis', fromlist=['render_multi_agent_analysis_tab'])
            multi_agent_analysis.render_multi_agent_analysis_tab(get_db_instance(), config)
    with t14:
        # 延迟导入智能新闻分析模块（新版：支持自主爬取和机器学习）
        with st.spinner("正在加载智能新闻分析引擎..."):
            smart_news_analysis = __import__('ui.smart_news_analysis', fromlist=['render_smart_news_analysis_tab'])
            smart_news_analysis.render_smart_news_analysis_tab(get_db_instance(), config)
    with t15:
        # 延迟导入实时情绪感知系统模块
        with st.spinner("正在加载实时情绪感知引擎..."):
            realtime_sentiment_tab = __import__('ui.realtime_sentiment_tab', fromlist=['render_realtime_sentiment_tab'])
            realtime_sentiment_tab.render_realtime_sentiment_tab(get_db_instance(), config)
    with t16:
        # 延迟导入龙头识别与跟踪系统模块
        with st.spinner("正在加载龙头识别跟踪引擎..."):
            dragon_tracking_tab = __import__('ui.dragon_tracking_tab', fromlist=['render_dragon_tracking_tab'])
            dragon_tracking_tab.render_dragon_tracking_tab(get_db_instance(), config)
    with t17:
        # 延迟导入集合竞价预测系统模块
        with st.spinner("正在加载竞价预测引擎..."):
            auction_prediction_tab = __import__('ui.auction_prediction_tab', fromlist=['render_auction_prediction_tab'])
            auction_prediction_tab.render_auction_prediction_tab(get_db_instance(), config)
    with t18:
        # 延迟导入在线参数调整系统模块
        with st.spinner("正在加载在线参数调整引擎..."):
            online_parameter_tab = __import__('ui.online_parameter_tab', fromlist=['render_online_parameter_tab'])
            online_parameter_tab.render_online_parameter_tab(get_db_instance(), config)

elif app_mode == "🧠 市场情绪":
    # 市场情绪分析模块
    t1 = st.tabs(["🧠 市场情绪分析"])
    with t1[0]:
        # 延迟导入市场情绪分析模块
        with st.spinner("正在加载市场情绪分析引擎..."):
            market_sentiment_tab = __import__('ui.market_sentiment_tab', fromlist=['render_market_sentiment_tab'])
            market_sentiment_tab.render_market_sentiment_tab(get_db_instance(), config)

elif app_mode == "💼 交易执行":
    # 交易执行模块
    t1 = st.tabs(["💼 交易执行"])
    with t1[0]:
        # 延迟导入交易执行模块
        with st.spinner("正在加载交易执行引擎..."):
            trading_execution_tab = __import__('ui.trading_execution_tab', fromlist=['render_trading_execution_tab'])
            trading_execution_tab.render_trading_execution_tab(get_db_instance(), config)

elif app_mode == "🧪 量化回测":
    # 量化回测模块 - 优化后的标签结构（融合方案：6个主标签）
    # 主标签：5个常用功能 + 1个"更多功能"
    t1, t2, t3, t4, t5, t6 = st.tabs(["🧪 策略回测", "🧪 高级回测", "🧠 LSTM预测", "⚖️ 组合优化", "🤖 自主学习", "📋 更多功能"])

    with t1:
        # 延迟导入策略回测模块
        with st.spinner("正在加载策略回测引擎..."):
            backtest = __import__('ui.backtest', fromlist=['render_backtest_tab'])
            backtest.render_backtest_tab(get_db_instance(), config)

    with t2:
        # 延迟导入高级回测模块
        with st.spinner("正在加载高级回测引擎..."):
            advanced_backtest = __import__('ui.advanced_backtest', fromlist=['render_advanced_backtest_tab'])
            advanced_backtest.render_advanced_backtest_tab(get_db_instance(), config)

    with t3:
        # 延迟导入 LSTM 预测模块
        with st.spinner("正在加载 AI 深度学习模型..."):
            lstm_predictor = __import__('ui.lstm_predictor', fromlist=['render_lstm_predictor_tab'])
            lstm_predictor.render_lstm_predictor_tab(get_db_instance(), config)

    with t4:
        # 延迟导入组合优化模块
        with st.spinner("正在加载组合优化引擎..."):
            portfolio_optimizer_tab = __import__('ui.portfolio_optimizer_tab', fromlist=['render_portfolio_optimizer_tab'])
            portfolio_optimizer_tab.render_portfolio_optimizer_tab(get_db_instance(), config)

    with t5:
        # 延迟导入自主学习系统
        with st.spinner("正在加载自主学习系统..."):
            autonomous_learning_tab = __import__('ui.autonomous_learning_tab', fromlist=['render_autonomous_learning_tab'])
            autonomous_learning_tab.render_autonomous_learning_tab(get_db_instance(), config)

    with t6:
        st.subheader("📋 更多功能")
        st.info("选择下面的功能模块：")

        # 使用selectbox选择功能，按分组显示
        function_category = st.selectbox(
            "选择功能类别",
            ["🔧 基础工具", "🧮 策略系统", "🤖 AI智能系统", "🖥️ 分布式系统"],
            key="more_function_category"
        )

        if function_category == "🔧 基础工具":
            selected_function = st.selectbox(
                "选择功能",
                ["参数优化", "K线形态识别"],
                key="basic_tools_function"
            )

            if selected_function == "参数优化":
                with st.spinner("正在加载参数优化引擎..."):
                    parameter_optimization = __import__('ui.parameter_optimization', fromlist=['render_parameter_optimization_tab'])
                    parameter_optimization.render_parameter_optimization_tab(get_db_instance(), config)
            elif selected_function == "K线形态识别":
                with st.spinner("正在加载 K线形态识别引擎..."):
                    kline_patterns = __import__('ui.kline_patterns', fromlist=['render_kline_patterns_tab'])
                    kline_patterns.render_kline_patterns_tab(get_db_instance(), config)

        elif function_category == "🧮 策略系统":
            selected_function = st.selectbox(
                "选择功能",
                ["策略工厂", "策略对比"],
                key="strategy_systems_function"
            )

            if selected_function == "策略工厂":
                with st.spinner("正在加载策略工厂引擎..."):
                    strategy_factory_tab = __import__('ui.strategy_factory_tab', fromlist=['render_strategy_factory_tab'])
                    strategy_factory_tab.render_strategy_factory_tab(get_db_instance(), config)
            elif selected_function == "策略对比":
                with st.spinner("正在加载策略对比引擎..."):
                    strategy_comparison_tab = __import__('ui.strategy_comparison_tab', fromlist=['render_strategy_comparison_tab'])
                    strategy_comparison_tab.render_strategy_comparison_tab(get_db_instance(), config)

        elif function_category == "🤖 AI智能系统":
            selected_function = st.selectbox(
                "选择功能",
                ["多模态融合", "自适应权重", "龙头自适应", "元学习", "强化学习"],
                key="ai_systems_function"
            )

            if selected_function == "多模态融合":
                with st.spinner("正在加载多模态融合决策系统..."):
                    multimodal_fusion_tab = __import__('ui.multimodal_fusion_tab', fromlist=['render_multimodal_fusion_tab'])
                    multimodal_fusion_tab.render_multimodal_fusion_tab(get_db_instance(), config)
            elif selected_function == "自适应权重":
                with st.spinner("正在加载自适应情绪权重系统..."):
                    adaptive_sentiment_weights_tab = __import__('ui.adaptive_sentiment_weights_tab', fromlist=['render_adaptive_sentiment_weights_tab'])
                    adaptive_sentiment_weights_tab.render_adaptive_sentiment_weights_tab(get_db_instance(), config)
            elif selected_function == "龙头自适应":
                with st.spinner("正在加载龙头战法自适应参数系统..."):
                    dragon_adaptive_params_tab = __import__('ui.dragon_adaptive_params_tab', fromlist=['render_dragon_adaptive_params_tab'])
                    dragon_adaptive_params_tab.render_dragon_adaptive_params_tab(get_db_instance(), config)
            elif selected_function == "元学习":
                with st.spinner("正在加载元学习系统..."):
                    meta_learning_tab = __import__('ui.meta_learning_tab', fromlist=['render_meta_learning_tab'])
                    meta_learning_tab.render_meta_learning_tab(get_db_instance(), config)
            elif selected_function == "强化学习":
                with st.spinner("正在加载强化学习优化系统..."):
                    rl_optimization_tab = __import__('ui.rl_optimization_tab', fromlist=['render_rl_optimization_tab'])
                    rl_optimization_tab.render_rl_optimization_tab(get_db_instance(), config)

        elif function_category == "🖥️ 分布式系统":
            selected_function = st.selectbox(
                "选择功能",
                ["分布式训练", "联邦学习", "自主进化"],
                key="distributed_systems_function"
            )

            if selected_function == "分布式训练":
                with st.spinner("正在加载分布式训练系统..."):
                    distributed_training_tab = __import__('ui.distributed_training_tab', fromlist=['render_distributed_training_tab'])
                    distributed_training_tab.render_distributed_training_tab(get_db_instance(), config)
            elif selected_function == "联邦学习":
                with st.spinner("正在加载联邦学习系统..."):
                    federated_learning_tab = __import__('ui.federated_learning_tab', fromlist=['render_federated_learning_tab'])
                    federated_learning_tab.render_federated_learning_tab(get_db_instance(), config)
            elif selected_function == "自主进化":
                with st.spinner("正在加载自主进化系统..."):
                    autonomous_evolution_tab = __import__('ui.autonomous_evolution_tab', fromlist=['render_autonomous_evolution_tab'])
                    autonomous_evolution_tab.render_autonomous_evolution_tab(get_db_instance(), config)
    with t1:
        # 延迟导入策略回测模块
        with st.spinner("正在加载策略回测引擎..."):
            backtest = __import__('ui.backtest', fromlist=['render_backtest_tab'])
            backtest.render_backtest_tab(get_db_instance(), config)
    with t2:
        # 延迟导入高级回测模块
        with st.spinner("正在加载高级回测引擎..."):
            advanced_backtest = __import__('ui.advanced_backtest', fromlist=['render_advanced_backtest_tab'])
            advanced_backtest.render_advanced_backtest_tab(get_db_instance(), config)
    with t3:
        # 延迟导入参数优化模块
        with st.spinner("正在加载参数优化引擎..."):
            parameter_optimization = __import__('ui.parameter_optimization', fromlist=['render_parameter_optimization_tab'])
            parameter_optimization.render_parameter_optimization_tab(get_db_instance(), config)
    with t4:
        # 延迟导入 K线形态模块
        with st.spinner("正在加载 K线形态识别引擎..."):
            kline_patterns = __import__('ui.kline_patterns', fromlist=['render_kline_patterns_tab'])
            kline_patterns.render_kline_patterns_tab(get_db_instance(), config)
    with t5:
        # 延迟导入 LSTM 预测模块（最重）
        with st.spinner("正在加载 AI 深度学习模型..."):
            lstm_predictor = __import__('ui.lstm_predictor', fromlist=['render_lstm_predictor_tab'])
            lstm_predictor.render_lstm_predictor_tab(get_db_instance(), config)
    with t6:
        # 延迟导入策略工厂模块
        with st.spinner("正在加载策略工厂引擎..."):
            strategy_factory_tab = __import__('ui.strategy_factory_tab', fromlist=['render_strategy_factory_tab'])
            strategy_factory_tab.render_strategy_factory_tab(get_db_instance(), config)
    with t7:
        # 延迟导入组合优化模块
        with st.spinner("正在加载组合优化引擎..."):
            portfolio_optimizer_tab = __import__('ui.portfolio_optimizer_tab', fromlist=['render_portfolio_optimizer_tab'])
            portfolio_optimizer_tab.render_portfolio_optimizer_tab(get_db_instance(), config)
    with t8:
        # 延迟导入策略对比模块
        with st.spinner("正在加载策略对比引擎..."):
            strategy_comparison_tab = __import__('ui.strategy_comparison_tab', fromlist=['render_strategy_comparison_tab'])
            strategy_comparison_tab.render_strategy_comparison_tab(get_db_instance(), config)
    with t9:
        # 延迟导入多模态融合决策系统
        with st.spinner("正在加载多模态融合决策系统..."):
            multimodal_fusion_tab = __import__('ui.multimodal_fusion_tab', fromlist=['render_multimodal_fusion_tab'])
            multimodal_fusion_tab.render_multimodal_fusion_tab(get_db_instance(), config)
    with t10:
        # 延迟导入自适应情绪权重系统
        with st.spinner("正在加载自适应情绪权重系统..."):
            adaptive_sentiment_weights_tab = __import__('ui.adaptive_sentiment_weights_tab', fromlist=['render_adaptive_sentiment_weights_tab'])
            adaptive_sentiment_weights_tab.render_adaptive_sentiment_weights_tab(get_db_instance(), config)
    with t11:
        # 延迟导入龙头战法自适应参数系统
        with st.spinner("正在加载龙头战法自适应参数系统..."):
            dragon_adaptive_params_tab = __import__('ui.dragon_adaptive_params_tab', fromlist=['render_dragon_adaptive_params_tab'])
            dragon_adaptive_params_tab.render_dragon_adaptive_params_tab(get_db_instance(), config)
    with t12:
        # 延迟导入元学习系统
        with st.spinner("正在加载元学习系统..."):
            meta_learning_tab = __import__('ui.meta_learning_tab', fromlist=['render_meta_learning_tab'])
            meta_learning_tab.render_meta_learning_tab(get_db_instance(), config)
    with t13:
        # 延迟导入强化学习优化系统
        with st.spinner("正在加载强化学习优化系统..."):
            rl_optimization_tab = __import__('ui.rl_optimization_tab', fromlist=['render_rl_optimization_tab'])
            rl_optimization_tab.render_rl_optimization_tab(get_db_instance(), config)
    with t14:
        # 延迟导入分布式训练系统
        with st.spinner("正在加载分布式训练系统..."):
            distributed_training_tab = __import__('ui.distributed_training_tab', fromlist=['render_distributed_training_tab'])
            distributed_training_tab.render_distributed_training_tab(get_db_instance(), config)
    with t15:
        # 延迟导入联邦学习系统
        with st.spinner("正在加载联邦学习系统..."):
            federated_learning_tab = __import__('ui.federated_learning_tab', fromlist=['render_federated_learning_tab'])
            federated_learning_tab.render_federated_learning_tab(get_db_instance(), config)
    with t16:
        # 延迟导入自主进化系统
        with st.spinner("正在加载自主进化系统..."):
            autonomous_evolution_tab = __import__('ui.autonomous_evolution_tab', fromlist=['render_autonomous_evolution_tab'])
            autonomous_evolution_tab.render_autonomous_evolution_tab(get_db_instance(), config)
    with t17:
        # 延迟导入自主学习系统
        with st.spinner("正在加载自主学习系统..."):
            autonomous_learning_tab = __import__('ui.autonomous_learning_tab', fromlist=['render_autonomous_learning_tab'])
            autonomous_learning_tab.render_autonomous_learning_tab(get_db_instance(), config)

elif app_mode == "💰 资产管理":
    # 资产管理模块
    t1, t2, t3, t4 = st.tabs(["💰 模拟交易", "⚠️ 风险管理", "🤖 智能推荐", "📡 实时监控"])
    with t1:
        # 延迟导入模拟交易模块
        with st.spinner("正在加载模拟交易系统..."):
            paper_trading = __import__('ui.paper_trading', fromlist=['render_paper_trading_tab'])
            paper_trading.render_paper_trading_tab(get_db_instance(), config)
    with t2:
        # 延迟导入风险管理模块
        with st.spinner("正在加载风险管理引擎..."):
            risk = __import__('ui.risk', fromlist=['render_risk_tab'])
            risk.render_risk_tab(get_db_instance(), config)
    with t3:
        # 延迟导入智能推荐模块
        with st.spinner("正在加载智能推荐引擎..."):
            smart_recommend = __import__('ui.smart_recommend', fromlist=['render_smart_recommend_tab'])
            smart_recommend.render_smart_recommend_tab(get_db_instance(), config)
    with t4:
        # 延迟导入实时监控模块
        with st.spinner("正在加载实时监控系统..."):
            live_monitoring = __import__('ui.live_monitoring', fromlist=['render_live_monitoring_tab'])
            live_monitoring.render_live_monitoring_tab(get_db_instance(), config)

elif app_mode == "⚙️ 系统工具":
    # 系统工具模块
    t1, t2, t3, t4 = st.tabs(["⚡ 性能优化", "⚙️ 系统设置", "📜 历史记录", "🔍 数据监控"])
    with t1:
        # 延迟导入性能优化模块
        with st.spinner("正在加载性能优化工具..."):
            performance_optimizer = __import__('ui.performance_optimizer', fromlist=['render_performance_optimizer_tab'])
            performance_optimizer.render_performance_optimizer_tab(get_db_instance(), config)
    with t2:
        # 延迟导入系统设置模块
        with st.spinner("正在加载系统设置引擎..."):
            settings = __import__('ui.settings', fromlist=['render_settings_tab'])
            settings.render_settings_tab(get_db_instance(), config)
    with t3:
        # 延迟导入历史记录模块
        with st.spinner("正在加载历史记录引擎..."):
            history = __import__('ui.history', fromlist=['render_history_tab'])
            history.render_history_tab(get_db_instance(), config)
    with t4:
        # 延迟导入数据质量监控模块
        with st.spinner("正在加载数据质量监控工具..."):
            data_monitor = __import__('ui.data_monitor', fromlist=['render_data_monitor_tab'])
            data_monitor.render_data_monitor_tab(get_db_instance(), config)

logger.info("应用渲染完成")