"""
策略工厂模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

from logic.strategy_factory import StrategyFactory
from logic.backtest_engine import BacktestEngine


def render_strategy_factory_tab(db, config):
    """渲染策略工厂标签页"""
    st.subheader("⚙️ 策略工厂")
    
    # 初始化模块
    factory = StrategyFactory()
    backtest_engine = BacktestEngine()
    
    # 选择策略模板
    templates = factory.list_all_templates()
    template_names = [t.name for t in templates]
    selected_template_name = st.selectbox("选择策略模板", template_names)
    
    selected_template = next(t for t in templates if t.name == selected_template_name)
    
    # 参数设置
    st.subheader("策略参数设置")
    params = {}
    cols = st.columns(2)
    
    for i, param in enumerate(selected_template.parameters):
        col = cols[i % 2]
        if param.type == 'int':
            value = col.number_input(
                param.name,
                value=int(param.default_value),
                min_value=int(param.min_value) if param.min_value is not None else None,
                max_value=int(param.max_value) if param.max_value is not None else None,
                step=1,
                help=param.description
            )
        elif param.type == 'float':
            value = col.number_input(
                param.name,
                value=float(param.default_value),
                min_value=float(param.min_value) if param.min_value is not None else None,
                max_value=float(param.max_value) if param.max_value is not None else None,
                step=0.1,
                help=param.description
            )
        else:
            value = col.text_input(param.name, value=str(param.default_value), help=param.description)
        
        params[param.name] = value
    
    # 生成模拟数据进行回测
    st.subheader("策略回测")
    start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))
    end_date = st.date_input("结束日期", value=datetime.now())
    initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000)
    
    if st.button("运行回测"):
        with st.spinner("正在运行回测..."):
            try:
                # 创建策略
                strategy = factory.create_strategy_from_template(selected_template.template_id, params)
                
                # 生成模拟数据（实际应用中应从数据源获取）
                dates = pd.date_range(start=start_date, end=end_date)
                n_days = len(dates)
                np.random.seed(42)
                prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, n_days))
                
                data = pd.DataFrame({
                    'date': dates,
                    'open': prices + np.random.normal(0, 0.1, n_days),
                    'high': prices + abs(np.random.normal(0, 0.15, n_days)),
                    'low': prices - abs(np.random.normal(0, 0.15, n_days)),
                    'close': prices,
                    'volume': np.random.normal(1000000, 200000, n_days)
                }).set_index('date')
                
                # 运行回测
                result = backtest_engine.run_backtest(strategy, data, initial_capital=initial_capital)
                
                # 显示结果
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("总收益率", f"{result.metrics.get('total_return', 0):.2%}")
                col2.metric("夏普比率", f"{result.metrics.get('sharpe_ratio', 0):.2f}")
                col3.metric("最大回撤", f"{result.metrics.get('max_drawdown', 0):.2%}")
                col4.metric("胜率", f"{result.metrics.get('win_rate', 0):.2%}")
                
                # 显示详细指标
                st.subheader("详细指标")
                metrics_df = pd.DataFrame(list(result.metrics.items()), columns=['指标', '值'])
                metrics_df['值'] = metrics_df['值'].round(4)
                st.dataframe(metrics_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="策略工厂", layout="wide")
    render_strategy_factory_tab(None, {})