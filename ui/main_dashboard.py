"""
主仪表板 - 集成所有功能展示UI
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 导入我们实现的功能模块
from logic.broker_api import MockBrokerAPI
from logic.slippage_model import SlippageModel, AdvancedSlippagePredictor
from logic.portfolio_optimizer import PortfolioOptimizer
from logic.market_sentiment import MarketSentimentIndexCalculator
from logic.strategy_factory import StrategyFactory
from logic.parameter_optimizer import ParameterOptimizer
from logic.strategy_comparison import StrategyComparator
from logic.advanced_visualizer import AdvancedVisualizer
from logic.backtest_engine import BacktestEngine

# 🆕 V6.1 新增
from ui.v61_features_tab import render_v61_features_tab

# 🆕 V7.0 新增
from ui.v70_features_tab import render_v70_features_tab

# 🆕 V7.1 新增
from ui.v71_features_tab import render_v71_features_tab

# 🆕 V8.0 新增
from ui.v80_features_tab import render_v80_features_tab

# 🆕 V8.1 新增
from ui.v81_features_tab import render_v81_features_tab

# 🆕 V8.4 新增
from ui.v84_features_tab import render_v84_features_tab

# 🆕 V9.0 新增
from ui.v90_features_tab import render_v90_features_tab


def main():
    st.set_page_config(
        page_title="量化工具综合仪表板",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 量化工具综合仪表板")
    
    # 侧边栏导航
    st.sidebar.header("导航")
    page = st.sidebar.radio(
        "选择功能页面",
        ["主页", "交易执行", "组合优化", "市场情绪", "策略工厂", "参数优化", "策略对比", "可视化分析", "🚀 V6.1新功能", "🎯 V7.0统合优化", "⚡ V7.1终极展望", "🔮 V8.0物理执行", "🎯 V8.1流动性与真龙识别", "🛡️ V8.4数据防火墙", "🔄 V9.0日内弱转强"]
    )
    
    # 初始化各模块
    broker_api = MockBrokerAPI({'initial_balance': 100000})
    slippage_model = SlippageModel()
    portfolio_optimizer = PortfolioOptimizer()
    sentiment_calculator = MarketSentimentIndexCalculator()
    strategy_factory = StrategyFactory()
    param_optimizer = ParameterOptimizer()
    strategy_comparator = StrategyComparator()
    advanced_visualizer = AdvancedVisualizer()
    backtest_engine = BacktestEngine()
    
    if page == "主页":
        show_home_page()
    elif page == "交易执行":
        show_trading_execution_page(broker_api, slippage_model)
    elif page == "组合优化":
        show_portfolio_optimization_page(portfolio_optimizer)
    elif page == "市场情绪":
        show_market_sentiment_page(sentiment_calculator)
    elif page == "策略工厂":
        show_strategy_factory_page(strategy_factory, backtest_engine)
    elif page == "参数优化":
        show_parameter_optimization_page(param_optimizer, strategy_factory, backtest_engine)
    elif page == "策略对比":
        show_strategy_comparison_page(strategy_comparator, strategy_factory, backtest_engine)
    elif page == "可视化分析":
        show_visualization_page(advanced_visualizer)
    elif page == "🚀 V6.1新功能":
        render_v61_features_tab(None, None)
    elif page == "🎯 V7.0统合优化":
        render_v70_features_tab(None, None)
    elif page == "⚡ V7.1终极展望":
        render_v71_features_tab(None, None)
    elif page == "🔮 V8.0物理执行":
        render_v80_features_tab(None, None)
    elif page == "🎯 V8.1流动性与真龙识别":
        render_v81_features_tab(None, None)
    elif page == "🛡️ V8.4数据防火墙":
        render_v84_features_tab(None, None)
    elif page == "🔄 V9.0日内弱转强":
        render_v90_features_tab(None, None)


def show_home_page():
    """主页"""
    st.header("欢迎使用量化工具综合仪表板")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 功能概览")
        st.markdown("""
        - **交易执行**: 自动化交易、订单管理、滑点优化
        - **组合优化**: 现代投资组合理论实现
        - **市场情绪**: 新闻、社交媒体、量价情绪分析
        - **策略工厂**: 策略模板、参数优化、回测对比
        - **可视化**: 3D图表、交互式分析界面
        """)
    
    with col2:
        st.subheader("📈 最新市场指标")
        # 模拟一些市场数据
        market_data = {
            "上证指数": {"涨跌幅": "+0.85%", "成交量": "3200亿", "情绪": "中性偏乐观"},
            "深证成指": {"涨跌幅": "+1.23%", "成交量": "4100亿", "情绪": "乐观"},
            "创业板指": {"涨跌幅": "+0.67%", "成交量": "1800亿", "情绪": "中性"},
            "市场情绪指数": {"综合得分": 0.32, "趋势": "上升", "信心": "良好"}
        }
        
        for index, data in market_data.items():
            with st.expander(f"**{index}**"):
                for key, value in data.items():
                    st.write(f"{key}: {value}")


def show_trading_execution_page(broker_api, slippage_model):
    """交易执行页面"""
    st.header("💼 交易执行模块")
    
    # 初始化
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
            symbol = st.text_input("股票代码", "000001")
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
                    side='buy' if side == '买入' else 'sell',
                    quantity=quantity,
                    price=price,
                    order_type='market' if order_type == '市价单' else 'limit',
                    status='pending',
                    timestamp=datetime.now()
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


def show_portfolio_optimization_page(portfolio_optimizer):
    """组合优化页面"""
    st.header("⚖️ 投合优化模块")
    
    st.subheader("投资组合优化器")
    
    # 生成模拟收益率数据
    dates = pd.date_range(end=datetime.now(), periods=100)
    assets = ['股票A', '股票B', '股票C', '债券D', '商品E']
    
    # 创建模拟收益率数据
    np.random.seed(42)
    returns_data = {}
    for asset in assets:
        # 生成具有不同特征的收益率数据
        daily_returns = np.random.normal(0.0005, 0.02, 100)  # 均值0.05%，标准差2%
        returns_data[asset] = daily_returns
    
    returns_df = pd.DataFrame(returns_data, index=dates)
    
    st.write("模拟资产收益率数据 (最近10天):")
    st.dataframe(returns_df.tail(10).style.format("{:.4f}"))
    
    # 选择优化方法
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox("优化方法", ["马科维茨均值方差", "风险平价", "Black-Litterman"])
    
    with col2:
        if method == "马科维茨均值方差":
            target_return = st.number_input("目标收益率", value=0.0008, step=0.0001, format="%.4f")
        else:
            target_return = None
    
    if st.button("执行优化"):
        with st.spinner("正在优化投资组合..."):
            method_map = {
                "马科维茨均值方差": "markowitz",
                "风险平价": "risk_parity", 
                "Black-Litterman": "black_litterman"
            }
            
            result = portfolio_optimizer.optimize_portfolio(
                returns_df, 
                method=method_map[method],
                target_return=target_return
            )
        
        # 显示优化结果
        col1, col2, col3 = st.columns(3)
        col1.metric("预期收益率", f"{result.expected_return:.2%}")
        col2.metric("波动率", f"{result.volatility:.2%}")
        col3.metric("夏普比率", f"{result.sharpe_ratio:.3f}")
        
        st.subheader("资产权重分配")
        weights_df = pd.DataFrame(list(result.weights.items()), columns=['资产', '权重'])
        weights_df['权重百分比'] = weights_df['权重'].apply(lambda x: f"{x:.2%}")
        
        # 显示权重图表
        fig = px.pie(weights_df, values='权重', names='资产', title='资产权重分布')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(weights_df)


def show_market_sentiment_page(sentiment_calculator):
    """市场情绪页面"""
    st.header("🧠 市场情绪分析")
    
    st.subheader("综合市场情绪指数")
    
    # 计算市场情绪
    if st.button("计算市场情绪"):
        with st.spinner("分析市场情绪中..."):
            symbols = ["000001", "600000", "300001"]
            sentiment_index = sentiment_calculator.calculate_comprehensive_sentiment(symbols)
        
        # 显示情绪指数
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("整体情绪", f"{sentiment_index.overall_sentiment:.3f}")
        col2.metric("新闻情绪", f"{sentiment_index.news_sentiment:.3f}")
        col3.metric("社交媒体情绪", f"{sentiment_index.social_sentiment:.3f}")
        col4.metric("资金流向情绪", f"{sentiment_index.fund_flow_sentiment:.3f}")
        
        # 情绪水平解释
        overall = sentiment_index.overall_sentiment
        if overall > 0.3:
            sentiment_level = "极度乐观"
            color = "🟢"
        elif overall > 0.1:
            sentiment_level = "乐观"
            color = "🟢"
        elif overall > -0.1:
            sentiment_level = "中性"
            color = "🟡"
        elif overall > -0.3:
            sentiment_level = "悲观"
            color = "🟠"
        else:
            sentiment_level = "极度悲观"
            color = "🔴"
        
        st.subheader(f"{color} 市场情绪水平: {sentiment_level}")
        
        # 情绪构成
        sentiment_breakdown = pd.DataFrame({
            '情绪类别': ['新闻情绪', '社交媒体情绪', '价格情绪', '资金情绪'],
            '情绪分数': [
                sentiment_index.news_sentiment,
                sentiment_index.social_sentiment, 
                sentiment_index.price_sentiment,
                sentiment_index.fund_flow_sentiment
            ]
        })
        
        fig = px.bar(sentiment_breakdown, x='情绪类别', y='情绪分数', 
                     title='情绪构成分析', range_y=[-1, 1])
        st.plotly_chart(fig, use_container_width=True)


def show_strategy_factory_page(strategy_factory, backtest_engine):
    """策略工厂页面"""
    st.header("⚙️ 策略工厂")
    
    # 选择策略模板
    templates = strategy_factory.list_all_templates()
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
    start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365), key="dashboard_backtest_start")
    end_date = st.date_input("结束日期", value=datetime.now(), key="dashboard_backtest_end")
    initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000, key="dashboard_backtest_capital")
    
    if st.button("运行回测"):
        with st.spinner("正在运行回测..."):
            try:
                # 创建策略
                strategy = strategy_factory.create_strategy_from_template(selected_template.template_id, params)
                
                # 生成模拟数据
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
                
                # 绘制权益曲线
                if result.equity_curve is not None and not result.equity_curve.empty:
                    fig = px.line(x=result.equity_curve.index, y=result.equity_curve.values, 
                                 title=f"{strategy.name} 权益曲线", 
                                 labels={'x': '日期', 'y': '权益'})
                    st.plotly_chart(fig, use_container_width=True)
                
                # 显示详细指标
                st.subheader("详细指标")
                metrics_df = pd.DataFrame(list(result.metrics.items()), columns=['指标', '值'])
                metrics_df['值'] = metrics_df['值'].round(4)
                st.dataframe(metrics_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())


def show_parameter_optimization_page(param_optimizer, strategy_factory, backtest_engine):
    """参数优化页面"""
    st.header("🔍 参数优化")
    
    # 选择策略模板
    templates = strategy_factory.list_all_templates()
    template_names = [t.name for t in templates]
    selected_template_name = st.selectbox("选择策略模板", template_names)
    
    selected_template = next(t for t in templates if t.name == selected_template_name)
    
    # 参数范围设置
    st.subheader("参数范围设置")
    param_ranges = {}
    
    for param in selected_template.parameters:
        if param.type in ['int', 'float']:
            col1, col2 = st.columns(2)
            min_val = col1.number_input(f"{param.name} 最小值", value=float(param.min_value or 1))
            max_val = col2.number_input(f"{param.name} 最大值", value=float(param.max_value or 10))
            
            if param.type == 'int':
                step = 1
            else:
                step = 0.1
            
            # 步长
            step_val = st.number_input(f"{param.name} 步长", value=step, min_value=0.01)
            
            # 生成参数列表
            if step_val > 0:
                values = []
                current = min_val
                while current <= max_val:
                    values.append(current)
                    current += step_val
                    if param.type == 'int':
                        current = int(current)
                
                param_ranges[param.name] = values
    
    # 优化设置
    st.subheader("优化设置")
    optimization_method = st.selectbox("优化方法", ["网格搜索", "随机搜索", "遗传算法"])
    target_metric = st.selectbox("目标指标", ["sharpe_ratio", "total_return", "win_rate", "profit_factor"])
    
    if st.button("开始优化"):
        with st.spinner("正在运行参数优化..."):
            try:
                # 生成模拟数据
                dates = pd.date_range(end=datetime.now(), periods=252)  # 一年数据
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
                
                # 创建目标函数
                def objective_function(params):
                    try:
                        strategy = strategy_factory.create_strategy_from_template(selected_template.template_id, params)
                        result = backtest_engine.run_backtest(strategy, data)
                        return result.metrics.get(target_metric, 0)
                    except:
                        return float('-inf') if target_metric in ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor'] else float('inf')
                
                # 执行优化
                if optimization_method == "网格搜索":
                    result = param_optimizer.grid_search(objective_function, param_ranges, maximize=True)
                elif optimization_method == "随机搜索":
                    # 为随机搜索构建参数空间
                    random_param_space = {}
                    for param_name, values in param_ranges.items():
                        if values:
                            random_param_space[param_name] = (min(values), max(values), 'float' if isinstance(values[0], float) else 'int')
                    result = param_optimizer.random_search(objective_function, random_param_space, n_trials=50, maximize=True)
                elif optimization_method == "遗传算法":
                    # 为遗传算法构建参数空间
                    ga_param_space = {}
                    for param_name, values in param_ranges.items():
                        if values:
                            ga_param_space[param_name] = (min(values), max(values), 'float' if isinstance(values[0], float) else 'int')
                    result = param_optimizer.genetic_algorithm_optimization(
                        objective_function, ga_param_space, 
                        population_size=30, generations=50, maximize=True
                    )
                
                # 显示优化结果
                st.success(f"优化完成！最佳参数: {result.best_params}")
                st.metric(f"最佳{target_metric}", f"{result.best_value:.4f}")
                
                # 显示优化历史
                if result.optimization_trace:
                    trace_df = pd.DataFrame(result.optimization_trace, columns=['params', 'value'])
                    trace_df['eval'] = range(len(trace_df))
                    
                    fig = px.line(x=trace_df['eval'], y=trace_df['value'], 
                                 title=f'{optimization_method}优化过程', 
                                 labels={'x': '评估次数', 'y': target_metric})
                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"优化失败: {e}")
                import traceback
                st.code(traceback.format_exc())


def show_strategy_comparison_page(strategy_comparator, strategy_factory, backtest_engine):
    """策略对比页面"""
    st.header("⚖️ 策略对比分析")
    
    # 选择要对比的策略
    templates = strategy_factory.list_all_templates()
    
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
            strategy = strategy_factory.create_strategy_from_template(template.template_id, params)
            strategies.append(strategy)
    
    # 数据设置
    st.subheader("回测设置")
    start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365), key="dashboard_compare_start")
    end_date = st.date_input("结束日期", value=datetime.now(), key="dashboard_compare_end")
    initial_capital = st.number_input("初始资金", value=100000, min_value=1000, step=1000, key="dashboard_compare_capital")
    
    if st.button("开始对比回测") and strategies:
        with st.spinner("正在运行对比回测..."):
            try:
                # 生成模拟数据
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
                comparison_df = strategy_comparator.run_strategy_comparison(strategies, data, backtest_engine)
                
                if not comparison_df.empty:
                    # 显示对比结果
                    st.subheader("策略性能对比")
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # 显示排名
                    st.subheader("综合排名")
                    rank_cols = ['strategy_name', 'composite_rank', 'composite_score', 'sharpe_ratio', 'total_return', 'max_drawdown']
                    rank_df = comparison_df[rank_cols].sort_values('composite_rank')
                    st.dataframe(rank_df, use_container_width=True)
                    
                    # 绘制权益曲线对比
                    st.subheader("权益曲线对比")
                    fig = go.Figure()
                    
                    for strategy in strategies:
                        try:
                            result = backtest_engine.run_backtest(strategy, data, initial_capital=initial_capital)
                            if result.equity_curve is not None and not result.equity_curve.empty:
                                fig.add_trace(go.Scatter(
                                    x=result.equity_curve.index,
                                    y=result.equity_curve.values,
                                    mode='lines',
                                    name=strategy.name
                                ))
                        except:
                            continue
                    
                    fig.update_layout(
                        title="策略权益曲线对比",
                        xaxis_title="日期",
                        yaxis_title="权益",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 性能指标雷达图
                    st.subheader("性能指标雷达图")
                    metrics_for_radar = ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor']
                    radar_df = pd.DataFrame()
                    
                    for idx, row in comparison_df.iterrows():
                        strategy_metrics = [row[metric] for metric in metrics_for_radar]
                        # 标准化到[0,1]区间
                        normalized_metrics = [(m - comparison_df[metric].min()) / (comparison_df[metric].max() - comparison_df[metric].min() or 1) 
                                              for m, metric in zip(strategy_metrics, metrics_for_radar)]
                        radar_df[row['strategy_name']] = normalized_metrics
                    
                    radar_df.index = metrics_for_radar
                    
                    fig = go.Figure()
                    for col in radar_df.columns:
                        fig.add_trace(go.Scatterpolar(
                            r=radar_df[col].tolist() + [radar_df[col].iloc[0]],  # 闭合图形
                            theta=metrics_for_radar + [metrics_for_radar[0]],
                            fill='toself',
                            name=col
                        ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1]
                            )),
                        showlegend=True,
                        title="策略性能雷达图"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"对比回测失败: {e}")
                import traceback
                st.code(traceback.format_exc())


def show_visualization_page(advanced_visualizer):
    """可视化分析页面"""
    st.header("📊 高级可视化分析")
    
    st.subheader("3D参数空间可视化")
    
    # 生成示例优化结果数据
    if st.button("生成3D参数空间图"):
        optimization_results = []
        for i in range(50):
            params = {
                'param1': np.random.uniform(0, 10),
                'param2': np.random.uniform(0, 5),
                'param3': np.random.uniform(1, 3)
            }
            # 模拟指标值，与参数有一定关系
            metric_value = params['param1'] * 0.3 + params['param2'] * 0.5 - params['param3'] * 0.2 + np.random.normal(0, 0.5)
            optimization_results.append((params, metric_value))
        
        # 使用Plotly创建3D散点图
        param1_vals = [r[0]['param1'] for r in optimization_results]
        param2_vals = [r[0]['param2'] for r in optimization_results]
        param3_vals = [r[0]['param3'] for r in optimization_results]
        metric_vals = [r[1] for r in optimization_results]
        
        fig = go.Figure(data=[go.Scatter3d(
            x=param1_vals,
            y=param2_vals,
            z=param3_vals,
            mode='markers',
            marker=dict(
                size=5,
                color=metric_vals,
                colorscale='Viridis',
                opacity=0.8
            ),
            text=[f"值: {v:.3f}" for v in metric_vals],
            hovertemplate='<b>%{text}</b><br>参数1: %{x}<br>参数2: %{y}<br>参数3: %{z}<extra></extra>'
        )])
        
        fig.update_layout(
            title="3D参数空间 - 指标值分布",
            scene=dict(
                xaxis_title='参数1',
                yaxis_title='参数2',
                zaxis_title='参数3'
            ),
            width=800,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("市场指标相关性分析")
    
    if st.button("生成相关性热力图"):
        # 生成模拟市场指标数据
        dates = pd.date_range(end=datetime.now(), periods=100)
        np.random.seed(42)
        
        market_data = pd.DataFrame({
            'date': dates,
            'price': 100 + np.cumsum(np.random.normal(0, 1, 100)),
            'volume': np.random.exponential(1000000, 100),
            'rsi': np.random.uniform(20, 80, 100),
            'macd': np.random.normal(0, 0.1, 100),
            'bollinger_position': np.random.uniform(-2, 2, 100),
            'volatility': np.random.uniform(0.01, 0.05, 100)
        })
        
        # 计算相关性矩阵
        corr_matrix = market_data.select_dtypes(include=[np.number]).corr()
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title='市场指标相关性热力图',
            xaxis_title='指标',
            yaxis_title='指标',
            width=800,
            height=700
        )
        
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()