"""
MyQuantTool - 个人化A股智能终端

精简版入口文件，使用模块化UI结构
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.ai_agent import DeepSeekAgent
from logic.comparator import StockComparator
from logic.backtest import BacktestEngine
from logic.formatter import Formatter
from logic.logger import get_logger
from config import Config
import os

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

# 加载配置
config = Config()

# API Key 优先级：环境变量 > 配置文件 > 默认值
API_KEY = os.getenv("SILICONFLOW_API_KEY") or config.get('api_key', 'sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet')

# 初始化核心组件
db = DataManager()
ai_agent = DeepSeekAgent(api_key=API_KEY)
comparator = StockComparator(db)
backtest_engine = BacktestEngine()

logger.info("核心组件初始化完成")

# 主标题
st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# 初始化session state
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

# 主要功能标签页
tab_single, tab_compare, tab_backtest, tab_sector, tab_lhb, tab_dragon, tab_auction, tab_sentiment, tab_hot_topics, tab_alert, tab_vp, tab_ma, tab_new_stock, tab_capital, tab_limit_up, tab_smart, tab_risk, tab_history, tab_settings = st.tabs([
    "📊 单股分析", "🔍 多股对比", "🧪 策略回测", "🔄 板块轮动", "🏆 龙虎榜", "🔥 龙头战法", 
    "⚡ 集合竞价", "📈 情绪分析", "🎯 热点题材", "🔔 智能预警", "📊 量价关系", "📈 均线战法", 
    "🆕 次新股", "💰 游资席位", "🎯 打板预测", "🤖 智能推荐", "⚠️ 风险管理", "📜 历史记录", "⚙️ 系统设置"
])

# 导入UI模块
from ui.single_stock import render_single_stock_tab
from ui.multi_compare import render_multi_compare_tab
from ui.backtest import render_backtest_tab
from ui.sector_rotation import render_sector_rotation_tab
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

# 渲染各个标签页
with tab_single:
    render_single_stock_tab(db, config)

with tab_compare:
    render_multi_compare_tab(db, config)

with tab_backtest:
    render_backtest_tab(backtest_engine, config)

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

with tab_settings:
    render_settings_tab(db, config)

logger.info("应用渲染完成")