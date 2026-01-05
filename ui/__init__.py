"""
UI 模块

包含所有用户界面相关的功能模块
"""

from .single_stock import render_single_stock_tab
from .long_hu_bang import render_long_hu_bang_tab
from .dragon_strategy import render_dragon_strategy_tab
from .sentiment import render_sentiment_tab

__all__ = [
    'render_single_stock_tab',
    'render_long_hu_bang_tab',
    'render_dragon_strategy_tab',
    'render_sentiment_tab',
]