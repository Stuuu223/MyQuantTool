"""
V8.0 物理执行优化展示页面

功能：
1. 滑点与冲击成本模型可视化
2. VWAP/TWAP算法交易展示
3. 大单拆分逻辑展示
4. 紧急清仓策略展示
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, Any

from logic.slippage_model import (
    VWAPExecutor, TWAPExecutor, 
    OrderSplitter, EmergencyExitExecutor,
    MarketDepth, ExecutionCost
)


def render_v80_features_tab(db, config):
    """渲染V8.0新功能标签页"""
    st.subheader("🔮 V8.0 物理执行优化 - 从数字世界到物理执行")
    
    # 初始化模块
    vwap_executor = VWAPExecutor(db)
    twap_executor = TWAPExecutor()
    order_splitter = OrderSplitter()
    emergency_exit_executor = EmergencyExitExecutor()
    
    # 创建四个子标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 滑点与冲击成本",
        "⏱️ VWAP/TWAP算法",
        "🔪 大单拆分逻辑",
        "🚨 紧急清仓策略"
    ])
    
    # Tab 1: 滑点与冲击成本
    with tab1:
        st.markdown("### 📊 滑点与冲击成本模型 (V8.0)")
        st.markdown("""
        **核心功能**：从数字世界到物理执行的桥梁
        
        - **正常买入**: 预留0.2%滑点
        - **闪崩逃命**: 预留1.0%-2.0%滑点
        - **大单冲击**: 根据订单规模动态计算冲击成本
        - **流动性影响**: 考虑市场流动性对滑点的影响
        """)
        
        # 模拟订单参数
        st.markdown("#### 📝 订单参数")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            order_quantity = st.number_input("订单数量（股）", 100, 1000000, 10000)
            order_price = st.number_input("当前价格（元）", 1.0, 1000.0, 10.0)
        
        with col2:
            order_value = st.number_input("订单金额（元）", 1000, 10000000, 100000)
            is_buy = st.selectbox("交易方向", ["买入", "卖出"])
        
        with col3:
            market_condition = st.selectbox(
                "市场条件",
                ["normal", "volatile", "illiquid", "flash_crash"]
            )
        
        # 计算订单规模
        calculated_value = order_quantity * order_price
        
        st.markdown(f"#### 💰 订单规模")
        st.metric("计算订单金额", f"¥{calculated_value:,.2f}")
        
        # 模拟市场深度
        st.markdown("#### 📊 模拟市场深度")
        
        # 模拟订单簿
        base_price = order_price
        bid_prices = [base_price * (1 - i*0.001) for i in range(5)]
        bid_volumes = [5000 - i*1000 for i in range(5)]
        ask_prices = [base_price * (1 + i*0.001) for i in range(5)]
        ask_volumes = [5000 - i*1000 for i in range(5)]
        
        market_depth = MarketDepth(
            bid_prices=bid_prices,
            bid_volumes=bid_volumes,
            ask_prices=ask_prices,
            ask_volumes=ask_volumes,
            timestamp=datetime.now()
        )
        
        # 计算滑点
        from logic.slippage_model import SlippageModel
        slippage_model = SlippageModel()
        slippage = slippage_model.calculate_market_slippage(
            order_quantity, 
            'buy' if is_buy == '买入' else 'sell', 
            market_depth
        )
        
        # 计算冲击成本
        impact_cost = slippage_model.estimate_impact_cost(
            calculated_value, 
            order_value * 10,  # 假设日成交量为订单金额的10倍
            0.02  # 假设波动率为2%
        )
        
        # 显示结果
        col1, col2, col3 = st.columns(3)
        
        with col1:
            slippage_pct = slippage * 100
            if abs(slippage_pct) > 1.0:
                st.error(f"滑点: {slippage_pct:.2f}%")
            elif abs(slippage_pct) > 0.5:
                st.warning(f"滑点: {slippage_pct:.2f}%")
            else:
                st.success(f"滑点: {slippage_pct:.2f}%")
        
        with col2:
            impact_pct = impact_cost * 100
            if impact_pct > 1.0:
                st.error(f"冲击成本: {impact_pct:.2f}%")
            elif impact_pct > 0.5:
                st.warning(f"冲击成本: {impact_pct:.2f}%")
            else:
                st.success(f"冲击成本: {impact_pct:.2f}%")
        
        with col3:
            total_cost = abs(slippage + impact_cost) * 100
            if total_cost > 2.0:
                st.error(f"总成本: {total_cost:.2f}%")
            elif total_cost > 1.0:
                st.warning(f"总成本: {total_cost:.2f}%")
            else:
                st.success(f"总成本: {total_cost:.2f}%")
        
        # 可视化订单簿
        st.markdown("#### 📈 订单簿可视化")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='买盘',
            x=bid_prices,
            y=bid_volumes,
            marker_color='green',
            orientation='h'
        ))
        fig.add_tracego.Bar(
            name='卖盘',
            x=ask_prices,
            y=ask_volumes,
            marker_color='red',
            orientation='h'
        ))
        
        fig.update_layout(
            title=f'市场深度（当前价格: ¥{order_price:.2f}）',
            xaxis_title='价格',
            yaxis_title='数量',
            barmode='overlay'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: VWAP/TWAP算法
    with tab2:
        st.markdown("### ⏱️ VWAP/TWAP算法交易 (V8.0)")
        st.markdown("""
        **核心功能**：算法交易，降低冲击成本
        
        - **VWAP (成交量加权平均价)**：根据成交量分布智能执行
        - **TWAP (时间加权平均价)**：按时间间隔均匀执行
        - **大单拆分**：避免一次性冲击市场
        - **智能调度**：根据市场状况选择最优策略
        """)
        
        # 模拟大单参数
        st.markdown("#### 📝 大单参数")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_quantity = st.number_input("总数量（股）", 100, 1000000, 100000)
            execution_window = st.slider("执行窗口（分钟）", 5, 120, 30)
        
        with col2:
            num_slices = st.slider("拆分份数", 2, 50, 10)
            execution_method = st.selectbox("执行方法", ["VWAP", "TWAP", "MARKET"])
        
        with col3:
            current_price = st.number_input("当前价格（元）", 1.0, 1000.0, 10.0)
            slippage_rate = st.slider("滑点率", 0.001, 0.01, 0.002, 0.001)
        
        # 计算拆分策略
        if st.button("🔄 计算拆分策略"):
            split_strategy = order_splitter.calculate_optimal_split(
                total_quantity,
                total_quantity * current_price,
                market_condition='normal'
            )
            
            st.markdown("---")
            st.markdown("#### 🎯 拆分策略")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("拆分份数", split_strategy['num_slices'])
            
            with col2:
                st.metric("单笔数量", split_strategy['slice_quantity'])
            
            with col3:
                st.metric("执行方法", split_strategy['execution_method'])
            
            with col4:
                st.metric("执行窗口", f"{split_strategy['execution_window_minutes']}分钟")
            
            st.markdown(f"**策略原因**: {split_strategy['reason']}")
            
            # 生成执行计划
            if execution_method == "VWAP":
                schedule = vwap_executor.calculate_vwap_schedule(
                    "300063",
                    total_quantity,
                    "buy",
                    execution_window,
                    num_slices
                )
            elif execution_method == "TWAP":
                schedule = twap_executor.calculate_twap_schedule(
                    total_quantity,
                    "buy",
                    execution_window,
                    num_slices
                )
            else:
                schedule = [{
                    'slice_index': 0,
                    'quantity': total_quantity,
                    'target_time': datetime.now(),
                    'method': 'MARKET',
                    'side': 'buy'
                }]
            
            # 显示执行计划
            st.markdown("#### 📋 执行计划")
            
            schedule_df = pd.DataFrame(schedule)
            schedule_df['target_time'] = pd.to_datetime(schedule_df['target_time']).dt.strftime('%H:%M:%S')
            schedule_df['quantity'] = schedule_df['quantity'].astype(int)
            
            st.dataframe(schedule_df, use_container_width=True)
            
            # 可视化执行计划
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[s['target_time'] for s in schedule],
                y=[s['quantity'] for s in schedule],
                mode='lines+markers',
                name='执行计划',
                text=[f"第{s['slice_index']+1}笔" for s in schedule],
                textposition='top center'
            ))
            
            fig.update_layout(
                title='算法交易执行计划',
                xaxis_title='时间',
                yaxis_title='数量（股）',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 计算预期执行结果
            st.markdown("#### 📊 预期执行结果")
            
            total_slippage = slippage_rate * total_quantity * current_price
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总滑点成本", f"¥{total_slippage:.2f}")
            
            with col2:
                st.metric("平均成交价", f"¥{current_price*(1+slippage_rate):.2f}")
            
            with col3:
                st.metric("总成交金额", f"¥{total_quantity*current_price*(1+slippage_rate):,.2f}")
    
    # Tab 3: 大单拆分逻辑
    with tab3:
        st.markdown("### 🔪 大单拆分逻辑 (V8.0)")
        st.markdown("""
        **核心功能**：智能拆分，降低冲击
        
        - **小单（<10万）**: 直接市价单，快速执行
        - **中单（10-50万）**: TWAP拆分，均匀执行
        **大单（50-200万）**: VWAP拆分，智能执行
        - **超大单（>200万）**: VWAP深度拆分，大幅降低冲击
        """)
        
        # 订单规模测试
        st.markdown("#### 📊 订单规模测试")
        
        order_values = [10000, 50000, 100000, 500000, 1000000, 5000000]
        split_results = []
        
        for value in order_values:
            split_strategy = order_splitter.calculate_optimal_split(
                10000,  # 假设数量
                value,
                market_condition='normal'
            )
            split_results.append({
                '订单金额': value,
                '拆分份数': split_strategy['num_slices'],
                '执行方法': split_strategy['execution_method'],
                '窗口时间': f"{split_strategy['execution_window_minutes']}分钟",
                '策略原因': split_strategy['reason']
            })
        
        df = pd.DataFrame(split_results)
        st.dataframe(df, use_container_width=True)
        
        # 可视化拆分策略
        fig = px.bar(
            df,
            x='订单金额',
            y='拆分份数',
            color='执行方法',
            title='不同订单规模的拆分策略',
            hover_data=['窗口时间', '策略原因']
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 拆分效果对比
        st.markdown("#### 📈 拆分效果对比")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("小单滑点", "0.2%", "直接市价单")
        
        with col2:
            st.metric("中单滑点", "0.5%", "TWAP拆分")
        
        with col3:
            st.metric("大单滑点", "1.0%", "VWAP拆分")
        
        st.markdown("""
        **拆分优势**:
        - 降低市场冲击
        - 减少滑点成本
        - 提高成交效率
        - 避免地板价成交
        """)
    
    # Tab 4: 紧急清仓策略
    with tab4:
        st.markdown("### 🚨 紧急清仓策略 (V8.0)")
        st.markdown("""
        **核心功能**：闪崩时的紧急熔断，避免地板价成交
        
        - **市价单清仓**: 恐慌性抛售，快速清仓，保命第一
        - **限价单清仓**: 一般清仓，逐步卖出
        - **冰山单清仓**: 闪崩清仓，逐步卖出，避免地板价
        - **滑点预留**: 根据市场状况预留不同滑点
        """)
        
        # 模拟持仓
        st.markdown("#### 📊 模拟持仓")
        
        sample_positions = [
            {'code': '300063', 'name': '天龙集团', 'quantity': 10000, 'current_price': 10.0, 'cost_price': 8.0},
            {'code': '002415', 'name': '海康威视', 'quantity': 5000, 'current_price': 30.0, 'cost_price': 28.0},
            {'code': '000858', 'name': '五粮液', 'quantity': 3000, 'current_price': 150.0, 'cost_price': 140.0}
        ]
        
        df = pd.DataFrame(sample_positions)
        st.dataframe(df, use_container_width=True)
        
        # 市场条件选择
        st.markdown("#### 🌤️ 市场条件")
        
        market_condition = st.selectbox(
            "市场条件",
            ["normal", "flash_crash", "panic"]
        )
        
        # 计算清仓策略
        if st.button("🚨 计算清仓策略"):
            exit_strategy = emergency_exit_executor.calculate_emergency_exit_strategy(
                sample_positions,
                market_condition
            )
            
            st.markdown("---")
            st.markdown("#### 🎯 清仓策略")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("清仓方法", exit_strategy['exit_method'])
            
            with col2:
                st.metric("清仓速度", exit_strategy['exit_speed'])
            
            with col3:
                st.metric("滑点预留", f"{exit_strategy['slippage_allowance']*100:.1f}%")
            
            with col4:
                st.metric("预期损失", f"-{exit_strategy['slippage_allowance']*100:.1f}% 至 -{exit_strategy['slippage_allowance']*2*100:.1f}%")
            
            st.markdown(f"**策略原因**: {exit_strategy['reason']}")
            
            # 模拟执行清仓
            st.markdown("#### 📋 清仓执行详情")
            
            # 模拟市场深度
            market_depth = MarketDepth(
                bid_prices=[9.5, 9.4, 9.3, 9.2, 9.1],
                bid_volumes=[1000, 2000, 3000, 5000, 8000],
                ask_prices=[10.5, 10.6, 10.7, 10.8, 10.9],
                ask_volumes=[8000, 5000, 3000, 2000, 1000],
                timestamp=datetime.now()
            )
            
            exit_result = emergency_exit_executor.execute_emergency_exit(
                sample_positions,
                exit_strategy,
                market_depth
            )
            
            # 显示清仓结果
            exit_df = pd.DataFrame(exit_result['exit_details'])
            exit_df['盈亏'] = (exit_df['exit_price'] - exit_df['exit_df'].apply(lambda x: x['cost_price'])) * exit_df['quantity']
            
            st.dataframe(exit_df, use_container_width=True)
            
            # 汇总
            total_value = exit_result['total_value']
            total_cost = sum(pos['quantity'] * pos['cost_price'] for pos in sample_positions)
            total_pnl = total_value - total_cost
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("清仓总价值", f"¥{total_value:,.2f}")
            
            with col2:
                st.metric("持仓总成本", f"¥{total_cost:,.2f}")
            
            with col3:
                if total_pnl >= 0:
                    st.metric("总盈亏", f"+¥{total_pnl:,.2f}", delta=f"+¥{total_pnl:,.2f}")
                else:
                    st.metric("总盈亏", f"-¥{abs(total_pnl):,.2f}", delta=f"-¥{abs(total_pnl):,.2f}")
            
            # 清仓建议
            st.markdown("#### 💡 清仓建议")
            
            if exit_strategy['exit_method'] == 'MARKET':
                st.error("🚨 市价单快速清仓，保命第一！")
            elif exit_strategy['exit_method'] == 'LIMIT':
                st.info("📊 限价单逐步卖出，控制成本")
            elif exit_strategy['exit_strategy'] == 'ICEBERG':
                st.warning("🧊 冰山单逐步清仓，避免地板价成交")
    
    # 关闭资源
    vwap_executor.close()
    emergency_exit_executor.close()


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="V8.0 新功能", layout="wide")
    render_v80_features_tab(None, None)