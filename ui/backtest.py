"""
策略回测模块

提供量化策略的回测功能
"""

import streamlit as st
from logic.backtest import BacktestEngine
from logic.logger import get_logger
from config_system import Config

logger = get_logger(__name__)


def render_backtest_tab(backtest_engine: BacktestEngine, config: Config):
    """
    渲染策略回测标签页
    
    Args:
        backtest_engine: 回测引擎实例
        config: 配置实例
    """
    st.subheader("🧪 策略回测")
    st.info("💡 策略回测功能正在开发中，敬请期待...")
    
    # TODO: 实现完整的回测功能
    # 1. 选择策略类型
    # 2. 设置策略参数
    # 3. 选择回测时间范围
    # 4. 运行回测
    # 5. 显示回测结果