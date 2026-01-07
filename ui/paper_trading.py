"""
模拟交易系统UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.paper_trading_system import (
    get_paper_trading_system,
    OrderType,
    OrderDirection
)
from datetime import datetime


def render_paper_trading_tab(db, config):
    """渲染模拟交易系统标签页"""
    
    st.header("💰 模拟交易系统")
    st.markdown("完整的订单管理、持仓管理、T+1结算模拟")
    st.markdown("---")
    
    # 初始化session state
    if 'pts' not in st.session_state:
        st.session_state.pts = get_paper_trading_system(
            initial_capital=100000,
            commission_rate=0.001,
            t_plus_one=True
        )
    
    pts = st.session_state.pts
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("💼 账户设置")
        
        initial_capital = st.number_input(
            "初始资金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000,
            key="pts_initial_capital"
        )
        
        if st.button("🔄 重置账户", key="reset_account"):
            st.session_state.pts = get_paper_trading_system(
                initial_capital=initial_capital,
                commission_rate=0.001,
                t_plus_one=True
            )
            pts = st.session_state.pts
            st.success("✅ 账户已重置")
            st.rerun()
        
        st.markdown("---")
        st.subheader("📊 下单设置")
        
        order_symbol = st.text_input("股票代码", value="600519", key="pts_symbol")
        
        col_a, col_b = st.columns(2)
        with col_a:
            order_direction = st.selectbox(
                "方向",
                [OrderDirection.BUY, OrderDirection.SELL],
                format_func=lambda x: x.value,
                key="pts_direction"
            )
        
        with col_b:
            order_type = st.selectbox(
                "类型",
                [OrderType.MARKET, OrderType.LIMIT],
                format_func=lambda x: x.value,
                key="pts_type"
            )
        
        order_quantity = st.number_input(
            "数量（手）",
            min_value=1,
            max_value=1000,
            value=1,
            step=1,
            key="pts_quantity"
        )
        
        order_price = st.number_input(
            "价格",
            min_value=0.0,
            max_value=10000.0,
            value=10.0,
            step=0.01,
            key="pts_price",
            disabled=(order_type == OrderType.MARKET)
        )
        
        if st.button("📝 提交订单", key="submit_order", type="primary"):
            try:
                order_id = pts.submit_order(
                    symbol=order_symbol,
                    order_type=order_type,
                    direction=order_direction,
                    quantity=order_quantity,
                    price=order_price
                )
                st.success(f"✅ 订单已提交: {order_id}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 提交失败: {str(e)}")
        
        st.markdown("---")
        st.subheader("⚙️ 交易设置")
        
        commission_rate = st.slider(
            "手续费率",
            min_value=0.0,
            max_value=0.01,
            value=0.001,
            step=0.0001,
            format="%.4f",
            key="pts_commission"
        )
        
        risk_limit = st.slider(
            "风险限制",
            min_value=0.5,
            max_value=1.0,
            value=0.95,
            step=0.05,
            format="%.2f",
            key="pts_risk_limit"
        )
    
    # 主内容区
    # 账户状态
    status = pts.get_account_status()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总资产", f"¥{status.total_equity:,.2f}")
    col2.metric("可用资金", f"¥{status.cash_balance:,.2f}")
    col3.metric("持仓市值", f"¥{status.total_market_value:,.2f}")
    col4.metric("风险等级", status.risk_level)
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("持仓数量", status.positions_count)
    col6.metric("浮动盈亏", f"¥{status.total_unrealized_pnl:,.2f}")
    col7.metric("已实现盈亏", f"¥{status.total_realized_pnl:,.2f}")
    col8.metric("总收益率", f"{(status.total_equity - pts.initial_capital) / pts.initial_capital * 100:.2f}%")
    
    st.markdown("---")
    
    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📋 持仓管理", "📝 订单管理", "📊 成交记录", "📈 账户报表"])
    
    with tab1:
        st.subheader("📋 持仓管理")
        
        positions = pts.get_positions()
        
        if positions:
            # 更新市场价格（模拟）
            prices = {pos.symbol: pos.market_price * (1 + np.random.normal(0, 0.01)) for pos in positions}
            pts.update_market_prices(prices)
            positions = pts.get_positions()
            
            # 显示持仓表格
            position_data = []
            for pos in positions:
                position_data.append({
                    "股票代码": pos.symbol,
                    "数量": pos.quantity,
                    "成本价": f"¥{pos.avg_cost:.2f}",
                    "现价": f"¥{pos.market_price:.2f}",
                    "市值": f"¥{pos.market_value:,.2f}",
                    "浮动盈亏": f"¥{pos.unrealized_pnl:,.2f}",
                    "盈亏比例": f"{(pos.unrealized_pnl / (pos.avg_cost * pos.quantity)) * 100:.2f}%"
                })
            
            st.dataframe(
                pd.DataFrame(position_data),
                use_container_width=True
            )
            
            # 快速操作
            st.markdown("### ⚡ 快速操作")
            
            for pos in positions:
                with st.expander(f"{pos.symbol} - {pos.quantity}股"):
                    col_a, col_b = st.columns(2)
                    
                    sell_quantity = col_a.number_input(
                        "卖出数量（手）",
                        min_value=1,
                        max_value=pos.quantity // 100,
                        value=1,
                        step=1,
                        key=f"sell_{pos.symbol}"
                    )
                    
                    if col_b.button("📤 卖出", key=f"sell_btn_{pos.symbol}"):
                        try:
                            order_id = pts.submit_order(
                                symbol=pos.symbol,
                                order_type=OrderType.MARKET,
                                direction=OrderDirection.SELL,
                                quantity=sell_quantity,
                                price=pos.market_price
                            )
                            st.success(f"✅ 卖出订单已提交: {order_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 卖出失败: {str(e)}")
        else:
            st.info("当前无持仓")
    
    with tab2:
        st.subheader("📝 订单管理")
        
        orders = pts.get_orders()
        
        if orders:
            # 按状态分组显示
            pending_orders = [o for o in orders if o.status.value == "待成交"]
            filled_orders = [o for o in orders if o.status.value == "已成交"]
            cancelled_orders = [o for o in orders if o.status.value == "已取消"]
            
            # 待成交订单
            if pending_orders:
                st.markdown("### ⏳ 待成交订单")
                for order in pending_orders:
                    with st.container():
                        cols = st.columns([3, 2, 2, 2, 1])
                        cols[0].write(f"**{order.symbol}**")
                        cols[1].write(order.direction.value)
                        cols[2].write(f"{order.quantity}股")
                        cols[3].write(f"¥{order.price:.2f}")
                        
                        if cols[4].button("❌", key=f"cancel_{order.order_id}"):
                            if pts.cancel_order(order.order_id):
                                st.success(f"✅ 订单已取消")
                                st.rerun()
                            else:
                                st.error("❌ 取消失败")
                        st.divider()
            
            # 已成交订单
            if filled_orders:
                st.markdown("### ✅ 已成交订单")
                filled_data = []
                for order in filled_orders:
                    filled_data.append({
                        "订单ID": order.order_id,
                        "股票代码": order.symbol,
                        "方向": order.direction.value,
                        "数量": order.filled_quantity,
                        "成交价": f"¥{order.filled_price:.2f}",
                        "手续费": f"¥{order.commission:.2f}",
                        "时间": order.update_time
                    })
                
                st.dataframe(pd.DataFrame(filled_data), use_container_width=True)
            
            # 已取消订单
            if cancelled_orders:
                with st.expander("🚫 已取消订单"):
                    cancelled_data = []
                    for order in cancelled_orders:
                        cancelled_data.append({
                            "订单ID": order.order_id,
                            "股票代码": order.symbol,
                            "方向": order.direction.value,
                            "数量": order.quantity,
                            "时间": order.update_time
                        })
                    
                    st.dataframe(pd.DataFrame(cancelled_data), use_container_width=True)
        else:
            st.info("暂无订单")
    
    with tab3:
        st.subheader("📊 成交记录")
        
        trades = pts.get_trades()
        
        if trades:
            trade_data = []
            for trade in trades:
                trade_data.append({
                    "成交ID": trade.trade_id,
                    "订单ID": trade.order_id,
                    "股票代码": trade.symbol,
                    "方向": trade.direction.value,
                    "数量": trade.quantity,
                    "价格": f"¥{trade.price:.2f}",
                    "手续费": f"¥{trade.commission:.2f}",
                    "盈亏": f"¥{trade.pnl:.2f}",
                    "时间": trade.trade_time
                })
            
            st.dataframe(pd.DataFrame(trade_data), use_container_width=True)
        else:
            st.info("暂无成交记录")
    
    with tab4:
        st.subheader("📈 账户报表")
        
        if st.button("📊 生成报表", key="generate_report"):
            statement = pts.generate_account_statement()
            
            # 账户状态
            st.markdown("### 💼 账户状态")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.json(statement['account_status'])
            
            with col_b:
                st.markdown("### 📊 交易统计")
                st.json(statement['trading_statistics'])
            
            # 持仓明细
            if statement['positions']:
                st.markdown("### 📋 持仓明细")
                st.dataframe(pd.DataFrame(statement['positions']), use_container_width=True)
            
            # 最近交易
            if statement['recent_trades']:
                st.markdown("### 📝 最近交易")
                st.dataframe(pd.DataFrame(statement['recent_trades']), use_container_width=True)
            
            # 保存报表
            if st.button("💾 保存报表", key="save_report"):
                import json
                filepath = f"paper_trading_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                pts.save_to_file(filepath)
                st.success(f"✅ 报表已保存: {filepath}")
        else:
            st.info("点击按钮生成账户报表")