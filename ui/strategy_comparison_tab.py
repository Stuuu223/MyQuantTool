"""
策略比较模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

from logic.strategy_comparison import StrategyComparator
from logic.strategy_factory import StrategyFactory
from logic.backtest_engine import BacktestEngine


def render_strategy_comparison_tab(db, config):
    """渲染策略比较标签页"""
    st.subheader("📊 策略对比分析")
    
    # 初始化模块
    comparator = StrategyComparator()
    factory = StrategyFactory()
    backtest_engine = BacktestEngine()
    
    # 选择要对比的策略
    templates = factory.list_all_templates()
    
    selected_strategy_names = st.multiselect(
        "选择要对比的策略",
        [t.name for t in templates],
        default=[t.name for t in templates[:2]] if len(templates) >= 2 else []
    )
    
    # 为每个选中的策略设置参数
    strategies = []
    for name in selected_strategy_names:
        template = next(t for t in templates if t.name == name)
        
        with st.expander(f"{name} 参数设置"):
            params = {}
            cols = st.columns(2)
            
            for i, param in enumerate(template.parameters):
                col = cols[i % 2]
                if param.type == 'int':
                    value = col.number_input(
                        param.name,
                        value=int(param.default_value),
                        min_value=int(param.min_value) if param.min_value is not None else None,
                        max_value=int(param.max_value) if param.max_value is not None else None,
                        step=1,
                        key=f"comp_{name}_{param.name}"
                    )
                elif param.type == 'float':
                    value = col.number_input(
                        param.name,
                        value=float(param.default_value),
                        min_value=float(param.min_value) if param.min_value is not None else None,
                        max_value=float(param.max_value) if param.max_value is not None else None,
                        step=0.1,
                        key=f"comp_{name}_{param.name}"
                    )
                else:
                    value = col.text_input(param.name, value=str(param.default_value), key=f"comp_{name}_{param.name}")
                
                params[param.name] = value
            
            # 创建策略实例
            strategy = factory.create_strategy_from_template(template.template_id, params)
            strategies.append(strategy)
    
    # 数据设置
    st.subheader("回测设置")
    start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))
    end_date = st.date_input("结束日期", value=datetime.now())
    initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000)
    
    if st.button("开始对比回测") and strategies:
        with st.spinner("正在运行对比回测..."):
            try:
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
                
                # 运行对比回测
                comparison_df = comparator.run_strategy_comparison(strategies, data, backtest_engine)
                
                if not comparison_df.empty:
                    # 显示对比结果
                    st.subheader("策略性能对比")
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # 显示排名
                    st.subheader("综合排名")
                    rank_cols = ['strategy_name', 'composite_rank', 'composite_score', 'sharpe_ratio', 'total_return', 'max_drawdown']
                    rank_df = comparison_df[rank_cols].sort_values('composite_rank')
                    st.dataframe(rank_df, use_container_width=True)
                    
                    # 显示详细指标
                    st.subheader("详细指标")
                    metrics_cols = [col for col in comparison_df.columns if col not in ['strategy_name', 'start_date', 'end_date']]
                    detailed_df = comparison_df[['strategy_name'] + metrics_cols]
                    st.dataframe(detailed_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"对比回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="策略对比", layout="wide")
    render_strategy_comparison_tab(None, {})