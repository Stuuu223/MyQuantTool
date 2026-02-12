"""
在线参数调整系统 UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.online_parameter_adjustment import OnlineParameterAdjustmentSystem
from logic.data_manager import DataManager


def render_online_parameter_tab(db: DataManager, config):
    """渲染在线参数调整标签页"""
    
    st.title("🔧 在线参数调整系统")
    st.markdown("---")
    
    # 初始化系统
    if 'online_parameter_system' not in st.session_state:
        st.session_state.online_parameter_system = OnlineParameterAdjustmentSystem()
        # 注册默认策略
        st.session_state.online_parameter_system.register_strategy('midway_strategy')
        st.session_state.online_parameter_system.register_strategy('dragon_strategy')
    
    system = st.session_state.online_parameter_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 策略选择
        st.subheader("📊 策略管理")
        strategies = system.get_all_strategies()
        selected_strategy = st.selectbox("选择策略", strategies)
        
        # 注册新策略
        with st.expander("注册新策略"):
            new_strategy_name = st.text_input("策略名称")
            if st.button("注册策略"):
                if new_strategy_name:
                    system.register_strategy(new_strategy_name)
                    st.success(f"策略 {new_strategy_name} 已注册")
                    st.rerun()
                else:
                    st.warning("请输入策略名称")
        
        # 性能输入
        st.subheader("📈 性能输入")
        sharpe_ratio = st.slider("夏普比率", -1.0, 3.0, 1.0, 0.1, help="策略夏普比率")
        win_rate = st.slider("胜率", 0.0, 1.0, 0.5, 0.05, help="策略胜率")
        max_drawdown = st.slider("最大回撤", 0.0, 0.5, 0.1, 0.01, help="最大回撤")
        total_return = st.slider("总收益率", -0.5, 1.0, 0.15, 0.05, help="总收益率")
        
        st.info("💡 提示: 输入策略近期性能指标，系统将自动调整参数")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("已注册策略", len(strategies))
    
    with col2:
        params = system.get_strategy_params(selected_strategy)
        st.metric("当前策略", selected_strategy)
    
    with col3:
        if params:
            st.metric("仓位大小", f"{params.get('position_size', 0.5):.0%}")
    
    # 调整参数
    st.markdown("---")
    st.header("🔧 参数调整")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 调整参数", use_container_width=True):
            with st.spinner("正在调整参数..."):
                # 构建性能指标
                recent_performance = {
                    'sharpe_ratio': sharpe_ratio,
                    'win_rate': win_rate,
                    'max_drawdown': max_drawdown,
                    'return': total_return
                }
                
                result = system.adjust_strategy(selected_strategy, recent_performance)
                
                st.session_state.last_adjustment_result = result
                st.success("参数调整完成！")
    
    # 显示调整结果
    if 'last_adjustment_result' in st.session_state:
        result = st.session_state.last_adjustment_result
        
        with col2:
            st.subheader("📊 调整结果")
            
            if result.get('error'):
                st.error(result['error'])
            else:
                if result['adjustment_made']:
                    st.success(f"✅ 参数已调整 (第 {result['adjustment_count']} 次)")
                    
                    if result['adjustments']:
                        st.info("调整详情:")
                        for adj in result['adjustments']:
                            st.info(f"  - {adj['rule']}")
                else:
                    st.info("ℹ️ 参数未调整，性能稳定")
    
    # 当前参数
    if 'last_adjustment_result' in st.session_state:
        result = st.session_state.last_adjustment_result
        
        st.markdown("---")
        st.header("📋 当前参数")
        
        if 'current_params' in result:
            params = result['current_params']
            
            param_data = []
            for key, value in params.items():
                param_data.append({
                    '参数': key,
                    '数值': f"{value:.4f}" if isinstance(value, float) else value,
                    '说明': _get_param_description(key)
                })
            
            st.dataframe(
                pd.DataFrame(param_data),
                use_container_width=True
            )
    
    # 性能摘要
    st.markdown("---")
    st.header("📈 性能摘要")
    
    performance = system.get_strategy_performance(selected_strategy)
    
    if performance and 'avg_metrics' in performance:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'sharpe_ratio' in performance['avg_metrics']:
                st.metric("夏普比率", f"{performance['avg_metrics']['sharpe_ratio']:.2f}")
        
        with col2:
            if 'win_rate' in performance['avg_metrics']:
                st.metric("胜率", f"{performance['avg_metrics']['win_rate']:.2%}")
        
        with col3:
            if 'max_drawdown' in performance['avg_metrics']:
                st.metric("最大回撤", f"{performance['avg_metrics']['max_drawdown']:.2%}")
        
        with col4:
            if 'return' in performance['avg_metrics']:
                st.metric("收益率", f"{performance['avg_metrics']['return']:.2%}")
        
        # 性能下降检测
        if performance.get('degradation'):
            st.error(f"⚠️ {performance['degradation']['message']}")
        else:
            st.success("✅ 性能稳定")
        
        # 调整统计
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("调整次数", performance['adjustment_count'])
        
        with col2:
            st.metric("上次调整", performance['last_adjustment_time'].strftime("%Y-%m-%d %H:%M:%S"))
    else:
        st.info("暂无性能数据")
    
    # 性能历史
    st.markdown("---")
    st.header("📜 性能历史")
    
    if selected_strategy:
        # 获取性能历史
        adjuster = system.strategies.get(selected_strategy)
        if adjuster:
            records = adjuster.performance_tracker.get_recent_performance(selected_strategy, limit=50)
            
            if records:
                df = pd.DataFrame(records)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # 性能指标图表
                fig = go.Figure()
                
                if 'sharpe_ratio' in df['metrics'].iloc[0]:
                    sharpe_data = [m['sharpe_ratio'] for m in df['metrics']]
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=sharpe_data,
                        mode='lines+markers',
                        name='夏普比率',
                        line=dict(color='#4CAF50', width=2)
                    ))
                
                if 'win_rate' in df['metrics'].iloc[0]:
                    win_rate_data = [m['win_rate'] for m in df['metrics']]
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=win_rate_data,
                        mode='lines+markers',
                        name='胜率',
                        line=dict(color='#2196F3', width=2)
                    ))
                
                if 'return' in df['metrics'].iloc[0]:
                    return_data = [m['return'] for m in df['metrics']]
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=return_data,
                        mode='lines+markers',
                        name='收益率',
                        line=dict(color='#FF9800', width=2)
                    ))
                
                fig.update_layout(
                    title=f"{selected_strategy} 性能历史",
                    xaxis_title="时间",
                    yaxis_title="指标值",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 历史记录表格
                st.subheader("详细记录")
                historical_data = []
                for record in records:
                    historical_data.append({
                        '时间': record['timestamp'],
                        '夏普比率': f"{record['metrics'].get('sharpe_ratio', 0):.2f}",
                        '胜率': f"{record['metrics'].get('win_rate', 0):.2%}",
                        '最大回撤': f"{record['metrics'].get('max_drawdown', 0):.2%}",
                        '收益率': f"{record['metrics'].get('return', 0):.2%}"
                    })
                
                st.dataframe(
                    pd.DataFrame(historical_data),
                    use_container_width=True
                )
            else:
                st.info("暂无历史记录")
    
    # 参数说明
    st.markdown("---")
    st.header("📋 参数说明")
    
    param_info = pd.DataFrame([
        {
            '参数': 'min_turnover',
            '说明': '最小换手率',
            '范围': '1.0% - 20.0%',
            '默认': '5.0%'
        },
        {
            '参数': 'min_volume',
            '说明': '最小成交金额',
            '范围': '5000万 - 5亿',
            '默认': '1亿'
        },
        {
            '参数': 'min_limit_ups',
            '说明': '最小涨停天数',
            '范围': '1 - 5天',
            '默认': '2天'
        },
        {
            '参数': 'max_days',
            '说明': '最大持仓天数',
            '范围': '5 - 20天',
            '默认': '10天'
        },
        {
            '参数': 'stop_loss',
            '说明': '止损比例',
            '范围': '2% - 10%',
            '默认': '5%'
        },
        {
            '参数': 'take_profit',
            '说明': '止盈比例',
            '范围': '10% - 30%',
            '默认': '15%'
        },
        {
            '参数': 'position_size',
            '说明': '仓位大小',
            '范围': '10% - 90%',
            '默认': '50%'
        }
    ])
    
    st.dataframe(param_info, use_container_width=True)
    
    st.info("💡 系统会根据策略表现自动调整这些参数，以优化策略性能")


def _get_param_description(param_name: str) -> str:
    """获取参数说明"""
    descriptions = {
        'min_turnover': '最小换手率阈值',
        'min_volume': '最小成交金额阈值',
        'min_limit_ups': '最小连续涨停天数',
        'max_days': '最大持仓天数',
        'stop_loss': '止损比例',
        'take_profit': '止盈比例',
        'position_size': '建议仓位大小'
    }
    return descriptions.get(param_name, '未知参数')