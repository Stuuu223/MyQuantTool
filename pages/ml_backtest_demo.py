"""Streamlit Demo Page - ML, Pattern Recognition, Backtesting & Paper Trading

Integrated demonstration of all advanced modules.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

from logic.lstm_predictor import get_lstm_predictor
from logic.kline_pattern_recognizer import get_kline_pattern_recognizer
from logic.backtest_engine import get_backtest_engine
from logic.paper_trading_system import get_paper_trading_system
from logic.performance_optimizer import get_performance_optimizer

# Page config
st.set_page_config(
    page_title="ML Backtest & Paper Trading",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 ML Backtest & Paper Trading Demo")
st.markdown("Integrated LSTM + Pattern Recognition + Backtesting + Paper Trading")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    tab_selection = st.radio(
        "Select Module:",
        ["LSTM Predictor", "Pattern Recognition", "Backtest Engine", "Paper Trading", "Performance Optimizer"]
    )
    
    stock_code = st.text_input("Stock Code (e.g., 000001):", "000001")
    initial_capital = st.number_input("Initial Capital:", value=100000, step=10000)

# Tab 1: LSTM Predictor
if tab_selection == "LSTM Predictor":
    st.header("🔠 LSTM Price Predictor")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Configuration")
        look_back = st.slider("Look-back Period:", 10, 60, 30)
        epochs = st.slider("Training Epochs:", 10, 100, 50)
        batch_size = st.select_slider("Batch Size:", [8, 16, 32, 64])
    
    with col2:
        st.subheader("Model Status")
        lstm = get_lstm_predictor(look_back=look_back)
        
        # Generate synthetic data
        prices = np.cumsum(np.random.normal(0.001, 0.02, 100)) + 10
        
        st.info(
            f"""
            **Status**: ✅ Ready
            **Look-back**: {look_back} days
            **Data Points**: {len(prices)}
            **Price Range**: {prices.min():.2f} - {prices.max():.2f}
            """
        )
    
    # Prediction
    if st.button("🚀 Generate Prediction"):
        try:
            result = lstm.predict(prices)
            
            st.success("Prediction Generated!")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Price", f"{result['current_price']:.2f}")
            with col2:
                st.metric("Predicted Price", f"{result['predicted_price']:.2f}")
            with col3:
                st.metric("Change %", f"{result['price_change_pct']:.2f}%")
            with col4:
                st.metric("Signal", result['signal'], f"Score: {result['signal_score']:.2f}")
            
            # Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=prices, mode='lines', name='Historical Price'))
            fig.add_hline(y=result['current_price'], line_dash="dash", name="Current")
            fig.add_hline(y=result['predicted_price'], line_dash="dot", name="Predicted")
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error: {e}")

# Tab 2: Pattern Recognition
elif tab_selection == "Pattern Recognition":
    st.header("📈 K-line Pattern Recognition")
    
    recognizer = get_kline_pattern_recognizer()
    
    # Generate synthetic K-line data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    prices = np.cumsum(np.random.normal(0, 0.02, 50)) + 10
    
    df = pd.DataFrame({
        'date': dates,
        'high': prices * np.random.uniform(1.00, 1.03, 50),
        'low': prices * np.random.uniform(0.97, 1.00, 50),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 50)
    })
    
    if st.button(🔍 Recognize Patterns"):
        patterns = recognizer.recognize_patterns(df)
        
        if patterns:
            st.success(f"Found {len(patterns)} pattern(s)")
            
            for i, pattern in enumerate(patterns, 1):
                with st.expander(f"Pattern {i}: {pattern['pattern']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Pattern", pattern['pattern'])
                    with col2:
                        st.metric("Signal", pattern['signal'])
                    with col3:
                        st.metric("Score", f"{pattern['score']:.2f}")
                    
                    st.json(pattern)
        else:
            st.info("No clear patterns detected in current data.")
    
    # K-line chart
    st.subheader("K-line Chart")
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['low'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])
    st.plotly_chart(fig, use_container_width=True)

# Tab 3: Backtest Engine
elif tab_selection == "Backtest Engine":
    st.header("📁 Historical Backtest")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date:", value=datetime(2023, 1, 1))
    with col2:
        end_date = st.date_input("End Date:", value=datetime(2024, 12, 31))
    
    signal_type = st.selectbox("Signal Type:", ["LSTM", "Pattern", "Fusion"])
    
    if st.button("🏁 Run Backtest"):
        try:
            engine = get_backtest_engine(initial_capital=initial_capital)
            
            # Load data
            df = engine.load_historical_data(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            # Generate signals
            signals = engine.generate_signals(df, signal_type=signal_type)
            
            # Backtest
            results = engine.backtest(stock_code, df, signals, signal_type=signal_type)
            
            st.success("Backtest Complete!")
            
            # Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Trades", results.get('total_trades', 0))
            with col2:
                st.metric("Win Rate", f"{results.get('win_rate', 0):.2%}")
            with col3:
                st.metric("Sharpe Ratio", f"{results.get('sharpe_ratio', 0):.4f}")
            with col4:
                st.metric("Max Drawdown", f"{results.get('max_drawdown', 0):.2%}")
            with col5:
                st.metric("Total Return", f"{results.get('total_return_pct', 0):.2f}%")
            
            # Trades table
            trades = engine.get_trades_summary()
            if not trades.empty:
                st.subheader("Trades")
                st.dataframe(trades.head(10), use_container_width=True)
            
            # Results JSON
            st.json(results)
            
        except Exception as e:
            st.error(f"Error: {e}")

# Tab 4: Paper Trading
elif tab_selection == "Paper Trading":
    st.header("📄 Paper Trading System")
    
    # Initialize session state
    if 'pts' not in st.session_state:
        st.session_state.pts = get_paper_trading_system(initial_capital=initial_capital)
    
    pts = st.session_state.pts
    
    # Account Status
    st.subheader("Account Status")
    status = pts.get_account_status()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cash Balance", f"${status.get('cash_balance', 0):,.2f}")
    with col2:
        st.metric("Positions Value", f"${status.get('total_positions_value', 0):,.2f}")
    with col3:
        st.metric("Total Equity", f"${status.get('total_equity', 0):,.2f}")
    with col4:
        st.metric("Positions Count", status.get('positions_count', 0))
    
    # Order Submission
    st.subheader("Submit Order")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        order_type = st.selectbox("Order Type:", ["BUY", "SELL"])
    with col2:
        quantity = st.number_input("Quantity (100x):", value=10, step=1) * 100
    with col3:
        price = st.number_input("Price:", value=10.50, step=0.01)
    with col4:
        submit = st.button("📤 Submit Order")
    
    if submit:
        order_id = pts.submit_order(stock_code, order_type, int(quantity), float(price))
        if order_id:
            st.success(f"Order Submitted: {order_id}")
            # Auto-fill
            pts.fill_order(order_id, float(price), int(quantity))
            st.info("Order Filled!")
            st.rerun()
    
    # Positions
    st.subheader("Current Positions")
    positions = pts.get_positions()
    if not positions.empty:
        st.dataframe(positions, use_container_width=True)
    else:
        st.info("No open positions.")
    
    # Orders
    st.subheader("Orders")
    orders = pts.get_orders()
    if not orders.empty:
        st.dataframe(orders, use_container_width=True)
    
    # Trades
    st.subheader("Closed Trades")
    trades = pts.get_trades()
    if not trades.empty:
        st.dataframe(trades, use_container_width=True)

# Tab 5: Performance Optimizer
elif tab_selection == "Performance Optimizer":
    st.header("🚀 Performance Optimization")
    
    opt = get_performance_optimizer(num_workers=4)
    
    # Vectorized MA
    st.subheader("1. Vectorized Moving Averages")
    
    prices = np.cumsum(np.random.normal(0.001, 0.02, 200)) + 10
    mas = opt.vectorized_ma(prices, [5, 20, 60])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=prices, mode='lines', name='Price'))
    for period in [5, 20, 60]:
        fig.add_trace(go.Scatter(y=mas[period], mode='lines', name=f'MA{period}'))
    st.plotly_chart(fig, use_container_width=True)
    
    # Grid Search
    st.subheader("2. Grid Search Parameter Optimization")
    
    if st.button(🔍 Run Grid Search"):
        def objective(ma_period, threshold):
            return ma_period / 10 + threshold
        
        result = opt.grid_search(
            param_grid={
                'ma_period': [5, 10, 15, 20],
                'threshold': [0.01, 0.02, 0.05, 0.10]
            },
            objective_func=objective
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Best Score", f"{result.get('best_score', 0):.4f}")
        with col2:
            st.metric("Tested Combinations", result.get('tested', 0))
        
        st.json(result)
    
    st.success("✅ All modules loaded successfully!")

# Footer
st.markdown("---")
st.markdown(
    """
    **MyQuantTool** - Advanced ML Backtesting & Paper Trading
    
    v3.5.0 | Developed by Stuuu223
    """
)
