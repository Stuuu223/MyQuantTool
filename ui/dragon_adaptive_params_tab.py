"""
龙头战法自适应参数系统 UI
"""

import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.dragon_adaptive_params import DragonAdaptiveParameterSystem
from logic.data_manager import DataManager


def render_dragon_adaptive_params_tab(db: DataManager, config):
    """渲染龙头战法自适应参数标签页"""
    
    st.title("🐉 龙头战法自适应参数系统")
    st.markdown("---")
    
    # 初始化系统
    if 'dragon_adaptive_system' not in st.session_state:
        st.session_state.dragon_adaptive_system = DragonAdaptiveParameterSystem()
    
    system = st.session_state.dragon_adaptive_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 参数优化
        st.subheader("🔧 参数优化")
        n_iterations = st.slider("优化迭代次数", 10, 100, 50, 10)
        
        # 性能输入
        st.subheader("📊 性能输入")
        sharpe_ratio = st.slider("夏普比率", -1.0, 3.0, 1.0, 0.1, help="策略夏普比率")
        win_rate = st.slider("胜率", 0.0, 1.0, 0.5, 0.05, help="策略胜率")
        max_drawdown = st.slider("最大回撤", 0.0, 0.5, 0.1, 0.01, help="最大回撤")
        total_return = st.slider("总收益率", -0.5, 1.0, 0.15, 0.05, help="总收益率")
        
        # 当前参数
        st.subheader("📋 当前参数")
        current_params = system.get_current_params()
        
        st.metric("最小换手率", f"{current_params.get('min_turnover', 0):.2f}%")
        st.metric("最小成交额", f"{current_params.get('min_volume', 0)/100000000:.2f}亿")
        st.metric("最小涨停天数", current_params.get('min_limit_ups', 0))
        st.metric("最大持仓天数", current_params.get('max_days', 0))
        st.metric("止损比例", f"{current_params.get('stop_loss', 0):.2%}")
        st.metric("止盈比例", f"{current_params.get('take_profit', 0):.2%}")
        st.metric("仓位大小", f"{current_params.get('position_size', 0):.0%}")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        opt_history = system.get_optimization_history(limit=10)
        st.metric("优化记录", f"{len(opt_history)} 条")
    
    with col2:
        perf_summary = system.get_performance_summary()
        if perf_summary:
            st.metric("调整次数", perf_summary.get('n_adjustments', 0))
    
    with col3:
        st.metric("优化迭代", n_iterations)
    
    # 参数优化
    st.markdown("---")
    st.header("🔧 参数优化")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 优化参数", use_container_width=True):
            with st.spinner("正在优化..."):
                # 生成模拟历史数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
                historical_data = pd.DataFrame({
                    'date': dates,
                    'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
                    'volume': np.linspace(1000000, 5000000, 100),
                    'pct_chg': np.random.randn(100) * 0.05
                })
                
                optimization_result = system.optimize(historical_data, n_iterations=n_iterations)
                
                st.session_state.last_optimization_result = optimization_result
                st.success("优化完成！")
    
    # 显示优化结果
    if 'last_optimization_result' in st.session_state:
        result = st.session_state.last_optimization_result
        
        with col2:
            st.subheader("📊 优化结果")
            
            st.info(f"**最佳评分**: {result['best_score']:.4f}")
            st.info(f"**迭代次数**: {result['n_iterations']}")
            
            summary = result.get('summary', {})
            if summary:
                st.info(f"**观测次数**: {summary.get('n_observations', 0)}")
                st.info(f"**平均评分**: {summary.get('mean_score', 0):.4f}")
    
    # 详细分析
    if 'last_optimization_result' in st.session_state:
        result = st.session_state.last_optimization_result
        
        st.markdown("---")
        st.header("📈 最佳参数")
        
        best_params = result['best_params']
        
        # 参数表格
        param_data = []
        for key, value in best_params.items():
            param_data.append({
                '参数': key,
                '数值': f"{value:.4f}" if isinstance(value, float) else value,
                '说明': _get_param_description(key)
            })
        
        st.dataframe(
            pd.DataFrame(param_data),
            use_container_width=True
        )
        
        # 参数可视化
        st.markdown("---")
        st.header("📊 参数分布")
        
        param_names = list(best_params.keys())
        param_values = list(best_params.values())
        
        fig = go.Figure(data=[
            go.Bar(
                x=param_names,
                y=param_values,
                marker_color='#4CAF50'
            )
        ])
        
        fig.update_layout(
            title="优化后的参数值",
            yaxis_title="参数值",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 在线调整
    st.markdown("---")
    st.header("🔄 在线调整")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("⚡ 在线调整", use_container_width=True):
            with st.spinner("正在调整..."):
                # 构建性能指标
                recent_performance = {
                    'sharpe_ratio': sharpe_ratio,
                    'win_rate': win_rate,
                    'max_drawdown': max_drawdown,
                    'return': total_return
                }
                
                adjustment = system.online_adjust(recent_performance)
                
                st.session_state.last_adjustment_result = adjustment
                st.success("调整完成！")
    
    # 显示调整结果
    if 'last_adjustment_result' in st.session_state:
        adjustment = st.session_state.last_adjustment_result
        
        with col2:
            st.subheader("📊 调整结果")
            
            if adjustment['adjusted']:
                st.success(f"✅ 参数已调整 (第 {len(adjustment['adjustments'])} 次)")
                
                if adjustment['adjustments']:
                    st.info("调整详情:")
                    for adj in adjustment['adjustments']:
                        st.info(f"  - {adj['rule']}")
            else:
                st.info("ℹ️ 参数未调整，性能稳定")
    
    # 优化历史
    st.markdown("---")
    st.header("📜 优化历史")
    
    opt_history = system.get_optimization_history(limit=20)
    
    if opt_history:
        df = pd.DataFrame(opt_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        st.dataframe(
            df[['timestamp', 'score']].head(10),
            use_container_width=True
        )
        
        # 优化趋势
        fig = go.Figure(data=[
            go.Scatter(
                x=df['timestamp'],
                y=df['score'],
                mode='lines+markers',
                name='评分',
                line=dict(color='#2196F3', width=2)
            )
        ])
        
        fig.update_layout(
            title="参数优化趋势",
            xaxis_title="时间",
            yaxis_title="评分",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无优化记录")
    
    # 参数说明
    st.markdown("---")
    st.header("📋 参数说明")
    
    param_info = pd.DataFrame([
        {
            '参数': 'min_turnover',
            '说明': '最小换手率',
            '范围': '1.0% - 20.0%',
            '影响': '过滤低换手率股票'
        },
        {
            '参数': 'min_volume',
            '说明': '最小成交金额',
            '范围': '5000万 - 5亿',
            '影响': '过滤低成交额股票'
        },
        {
            '参数': 'min_limit_ups',
            '说明': '最小连续涨停天数',
            '范围': '1 - 5天',
            '影响': '筛选强势股票'
        },
        {
            '参数': 'max_days',
            '说明': '最大持仓天数',
            '范围': '5 - 20天',
            '影响': '控制持仓时间'
        },
        {
            '参数': 'stop_loss',
            '说明': '止损比例',
            '范围': '2% - 10%',
            '影响': '控制下行风险'
        },
        {
            '参数': 'take_profit',
            '说明': '止盈比例',
            '范围': '10% - 30%',
            '影响': '锁定收益'
        },
        {
            '参数': 'position_size',
            '说明': '仓位大小',
            '范围': '10% - 90%',
            '影响': '控制风险暴露'
        },
        {
            '参数': 'entry_threshold',
            '说明': '入场阈值',
            '范围': '0.4 - 0.8',
            '影响': '筛选优质标的'
        },
        {
            '参数': 'exit_threshold',
            '说明': '出场阈值',
            '范围': '0.1 - 0.5',
            '影响': '及时止盈止损'
        }
    ])
    
    st.dataframe(param_info, use_container_width=True)
    
    st.info("💡 系统使用贝叶斯优化自动寻找最优参数，并根据表现在线调整")


def _get_param_description(param_name: str) -> str:
    """获取参数说明"""
    descriptions = {
        'min_turnover': '最小换手率阈值',
        'min_volume': '最小成交金额阈值',
        'min_limit_ups': '最小连续涨停天数',
        'max_days': '最大持仓天数',
        'stop_loss': '止损比例',
        'take_profit': '止盈比例',
        'position_size': '建议仓位大小',
        'entry_threshold': '入场评分阈值',
        'exit_threshold': '出场评分阈值'
    }
    return descriptions.get(param_name, '未知参数')