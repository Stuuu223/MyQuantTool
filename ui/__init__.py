"""
UI模块包

提供所有Streamlit UI组件的模块化实现
"""

# 导入所有UI模块的渲染函数
from .single_stock import render_single_stock_tab
from .multi_compare import render_multi_compare_tab
from .sector_rotation import render_sector_rotation_tab

# 导入其他模块（框架）
from .backtest import render_backtest_tab
from .long_hu_bang import render_long_hu_bang_tab
from .dragon_strategy import render_dragon_strategy_tab
from .auction import render_auction_tab
from .sentiment import render_sentiment_tab
from .hot_topics import render_hot_topics_tab
from .alert import render_alert_tab
from .volume_price import render_volume_price_tab
from .ma_strategy import render_ma_strategy_tab
from .new_stock import render_new_stock_tab
from .capital import render_capital_tab
from .limit_up import render_limit_up_tab
from .smart_recommend import render_smart_recommend_tab
from .risk import render_risk_tab
from .history import render_history_tab
from .settings import render_settings_tab

# 导入新增的UI模块
from .capital_network import render_capital_network_tab
from .capital_profiler import render_capital_profiler_tab
from .short_term_trend import render_short_term_trend_tab
from .opportunity_predictor import render_opportunity_predictor_tab
from .data_monitor import render_data_monitor_tab

__all__ = [
    'render_single_stock_tab',
    'render_multi_compare_tab',
    'render_sector_rotation_tab',
    'render_backtest_tab',
    'render_long_hu_bang_tab',
    'render_dragon_strategy_tab',
    'render_auction_tab',
    'render_sentiment_tab',
    'render_hot_topics_tab',
    'render_alert_tab',
    'render_volume_price_tab',
    'render_ma_strategy_tab',
    'render_new_stock_tab',
    'render_capital_tab',
    'render_limit_up_tab',
    'render_smart_recommend_tab',
    'render_risk_tab',
    'render_history_tab',
    'render_settings_tab',
    'render_capital_network_tab',
    'render_capital_profiler_tab',
    'render_short_term_trend_tab',
    'render_opportunity_predictor_tab',
    'render_data_monitor_tab',
]