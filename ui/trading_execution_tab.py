"""
交易执行模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

from logic.broker_api import MockBrokerAPI
from logic.slippage_model import SlippageModel


def render_trading_execution_tab(db, config):
    """渲染交易执行标签页"""
    st.subheader("💼 交易执行模块")
    
    # 初始化模块
    broker_api = MockBrokerAPI({'initial_balance': 100000})
    slippage_model = SlippageModel()
    
    # 初始化会话状态
    if 'broker_authenticated' not in st.session_state:
        st.session_state.broker_authenticated = False
    
    # 认证
    if st.button("连接券商API"):
        if broker_api.authenticate():
            st.session_state.broker_authenticated = True
            st.success("连接成功！")
        else:
            st.error("连接失败！")
    
    if st.session_state.broker_authenticated:
        st.success("已连接到模拟券商API")
        
        # 获取账户信息
        account_info = broker_api.get_account_info()
        col1, col2, col3 = st.columns(3)
        col1.metric("总资产", f"¥{account_info['total_balance']:,.2f}")
        col2.metric("可用资金", f"¥{account_info['available_balance']:,.2f}")
        col3.metric("持仓市值", f"¥{account_info['market_value']:,.2f}")
        
        # 交易面板
        st.subheader("交易面板")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.text_input("股票代码", "000001", key="trading_execution_symbol")
            side = st.selectbox("交易方向", ["买入", "卖出"])
        
        with col2:
            quantity = st.number_input("数量", min_value=100, max_value=100000, value=1000, step=100)
            order_type = st.selectbox("订单类型", ["市价单", "限价单"])
        
        with col3:
            price = st.number_input("价格", min_value=0.0, value=25.50, step=0.01)
            if st.button("提交订单"):
                # 创建订单
                from logic.broker_api import Order
                order = Order(
                    order_id='',
                    symbol=symbol,
                    direction='buy' if side == '买入' else 'sell',
                    order_type='market' if order_type == '市价单' else 'limit',
                    quantity=quantity,
                    price=price,
                    date=datetime.now().strftime('%Y-%m-%d')
                )
                
                # 预测滑点
                predicted_slippage, confidence = slippage_model.calculate_market_slippage(
                    quantity, 'buy' if side == '买入' else 'sell', 
                    type('MarketDepth', (), {
                        'bid_prices': [price * 0.999, price * 0.998, price * 0.997],
                        'bid_volumes': [1000, 1500, 2000],
                        'ask_prices': [price * 1.001, price * 1.002, price * 1.003],
                        'ask_volumes': [800, 1200, 1600],
                        'timestamp': datetime.now()
                    })()
                )
                
                with st.spinner("提交订单中..."):
                    order_id = broker_api.place_order(order)
                
                st.success(f"订单已提交，ID: {order_id}")
                st.info(f"预计滑点: {predicted_slippage:.4f} ({confidence:.2f}置信度)")
        
        # 持仓显示
        st.subheader("当前持仓")
        positions = broker_api.get_positions()
        if positions:
            pos_data = []
            for pos in positions:
                pos_data.append({
                    "股票代码": pos.symbol,
                    "持仓数量": pos.quantity,
                    "平均成本": f"{pos.avg_price:.2f}",
                    "当前价格": f"{pos.current_price:.2f}",
                    "盈亏": f"{pos.unrealized_pnl:.2f}"
                })
            st.dataframe(pd.DataFrame(pos_data))
        else:
            st.info("暂无持仓")


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="交易执行", layout="wide")
    render_trading_execution_tab(None, {})