"""
实时交易监控面板
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from logic.risk_monitor import RiskMonitor, AlertLevel
from logic.live_trading_interface import PaperTradingSystem, OrderDirection, OrderType
from logic.data_manager import DataManager


def render_live_monitoring_tab(db, config):
    """渲染实时交易监控标签页"""
    
    st.header("📡 实时交易监控")
    st.markdown("实时监控持仓、订单、风险指标")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 监控配置")
        
        # 刷新间隔
        refresh_interval = st.slider(
            "刷新间隔 (秒)",
            min_value=1,
            max_value=60,
            value=5,
            help="数据刷新间隔"
        )
        
        # 自动刷新
        auto_refresh = st.checkbox("自动刷新", value=True)
        
        # 风险阈值
        st.markdown("---")
        st.subheader("🛡️ 风险阈值")
        
        max_position_ratio = st.slider(
            "最大持仓比例",
            min_value=0.5,
            max_value=1.0,
            value=0.95,
            step=0.05
        )
        
        max_daily_loss_ratio = st.slider(
            "单日最大亏损",
            min_value=0.01,
            max_value=0.2,
            value=0.05,
            step=0.01
        )
        
        max_drawdown_ratio = st.slider(
            "最大回撤",
            min_value=0.1,
            max_value=0.5,
            value=0.2,
            step=0.05
        )
        
        # 邮件告警配置
        st.markdown("---")
        st.subheader("📧 邮件告警")
        
        enable_email_alert = st.checkbox("启用邮件告警", value=False)
        
        if enable_email_alert:
            smtp_host = st.text_input("SMTP服务器", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP端口", value=587)
            smtp_username = st.text_input("用户名")
            smtp_password = st.text_input("密码", type="password")
            smtp_to = st.text_input("收件人", value="your_email@example.com")
            
            smtp_config = {
                'host': smtp_host,
                'port': smtp_port,
                'username': smtp_username,
                'password': smtp_password,
                'from_addr': smtp_username,
                'to_addrs': [smtp_to]
            }
    
    # 主内容区
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 账户概览
        st.subheader("💰 账户概览")
        
        # 创建模拟交易系统
        if 'trading_system' not in st.session_state:
            st.session_state.trading_system = PaperTradingSystem(initial_capital=100000)
        
        system = st.session_state.trading_system
        
        # 检查是否有equity_curve属性（兼容旧版本）
        if not hasattr(system, 'equity_curve'):
            # 重新创建系统对象
            st.session_state.trading_system = PaperTradingSystem(initial_capital=100000)
            system = st.session_state.trading_system
        
        # 更新市场价格（如果有持仓）
        positions = system.get_positions()
        if positions:
            # 模拟市场价格更新（实际应该从数据源获取）
            # 这里使用当前市场价格作为示例
            prices = {pos.symbol: pos.market_price for pos in positions}
            system.update_market_prices(prices)
        
        # 获取账户摘要
        account_summary = system.get_account_summary()
        
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("总资产", f"¥{account_summary['total_equity']:,.2f}")
        col_b.metric("可用资金", f"¥{account_summary['capital']:,.2f}")
        col_c.metric("持仓市值", f"¥{account_summary['market_value']:,.2f}")
        col_d.metric("总盈亏", f"¥{account_summary['total_pnl']:,.2f}")
        
        # 收益率
        pnl_ratio = account_summary['pnl_ratio']
        pnl_color = "🟢" if pnl_ratio >= 0 else "🔴"
        st.metric("收益率", f"{pnl_color} {pnl_ratio:.2%}")
        
        # 持仓列表
        st.subheader("📊 持仓列表")
        
        positions = system.get_positions()
        
        if positions:
            positions_df = pd.DataFrame(positions)
            st.dataframe(
                positions_df,
                column_config={
                    "symbol": "股票代码",
                    "quantity": "数量",
                    "avg_price": st.column_config.NumberColumn("成本价", format="¥%.2f"),
                    "market_value": st.column_config.NumberColumn("市值", format="¥%.2f"),
                    "pnl": st.column_config.NumberColumn("盈亏", format="¥%.2f"),
                    "pnl_ratio": st.column_config.NumberColumn("盈亏比例", format="%.2%")
                },
                use_container_width=True
            )
        else:
            st.info("当前无持仓")
        
        # 订单列表
        st.subheader("📝 订单列表")
        
        orders = system.get_orders()
        
        if orders:
            orders_df = pd.DataFrame(orders)
            st.dataframe(
                orders_df,
                column_config={
                    "order_id": "订单ID",
                    "symbol": "股票代码",
                    "direction": "方向",
                    "order_type": "类型",
                    "quantity": "数量",
                    "price": st.column_config.NumberColumn("价格", format="¥%.2f"),
                    "status": "状态"
                },
                use_container_width=True
            )
        else:
            st.info("当前无订单")
    
    with col2:
        # 风险监控
        st.subheader("🛡️ 风险监控")
        
        # 创建风险监控器
        if 'risk_monitor' not in st.session_state:
            st.session_state.risk_monitor = RiskMonitor({
                'max_position_ratio': max_position_ratio,
                'max_daily_loss_ratio': max_daily_loss_ratio,
                'max_drawdown_ratio': max_drawdown_ratio
            })
            
            # 添加邮件告警处理器
            if enable_email_alert:
                from logic.risk_monitor import EmailAlertHandler
                alert_handler = EmailAlertHandler(smtp_config)
                st.session_state.risk_monitor.add_alert_handler(alert_handler)
        
        monitor = st.session_state.risk_monitor
        
        # 监控持仓风险
        for position in positions:
            monitor.monitor_position(
                position['symbol'],
                position['market_value'],
                account_summary['total_equity']
            )
        
        # 监控回撤风险
        if account_summary['total_equity'] > 0:
            monitor.monitor_drawdown(
                account_summary['total_equity'],
                account_summary['total_equity']  # 简化: 使用当前权益作为最高权益
            )
        
        # 获取风险摘要
        risk_summary = monitor.get_risk_summary()
        
        # 显示告警统计
        alert_count = risk_summary.get('alert_count', 0)
        critical_alerts = risk_summary.get('critical_alerts', 0)
        warning_alerts = risk_summary.get('warning_alerts', 0)
        
        col_e, col_f, col_g = st.columns(3)
        col_e.metric("总告警", alert_count)
        col_f.metric("严重告警", critical_alerts, delta_color="inverse")
        col_g.metric("警告", warning_alerts)
        
        # 最近告警
        st.subheader("📢 最近告警")
        
        recent_alerts = risk_summary.get('recent_alerts', [])
        
        if recent_alerts:
            for alert in recent_alerts[-5:]:  # 显示最近5条
                level_color = {
                    AlertLevel.INFO: "🔵",
                    AlertLevel.WARNING: "🟡",
                    AlertLevel.CRITICAL: "🔴",
                    AlertLevel.EMERGENCY: "🚨"
                }.get(alert['level'], "⚪")
                
                st.markdown(f"""
                **{level_color} {alert['level'].value}**
                
                时间: {alert['timestamp'].strftime('%H:%M:%S')}  
                消息: {alert['message']}
                """)
                st.divider()
        else:
            st.info("暂无告警")
        
        # 快速下单
        st.subheader("⚡ 快速下单")

        symbol = st.text_input("股票代码", value="600519", key="live_monitoring_symbol")
        direction = st.selectbox("方向", ["买入", "卖出"])
        order_type = st.selectbox("订单类型", ["市价单", "限价单"])
        quantity = st.number_input("数量", value=100, step=100)
        price = st.number_input("价格", value=0.0, step=0.01) if order_type == "限价单" else 0.0
        
        if st.button("🚀 下单"):
            try:
                order_dir = OrderDirection.BUY if direction == "买入" else OrderDirection.SELL
                order_type_enum = OrderType.MARKET if order_type == "市价单" else OrderType.LIMIT
                
                order = system.place_order(
                    symbol=symbol,
                    direction=order_dir,
                    order_type=order_type_enum,
                    quantity=quantity,
                    price=price if order_type == "限价单" else None
                )
                
                if order:
                    # 模拟执行订单
                    import random
                    market_price = price if order_type == "限价单" else random.uniform(95, 105)
                    system.execute_order(order, market_price)
                    
                    st.success(f"✅ 订单已执行: {order.order_id}")
                    st.rerun()
                else:
                    st.error("❌ 下单失败")
            
            except Exception as e:
                st.error(f"❌ 下单异常: {e}")
    
    # 历史记录
    st.subheader("📈 净值曲线")
    
    # 模拟净值曲线
    if hasattr(system, 'equity_curve') and len(system.equity_curve) > 0:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=list(range(len(system.equity_curve))),
            y=system.equity_curve,
            mode='lines',
            name='净值曲线',
            line=dict(color='#FF6B6B', width=2)
        ))
        
        fig.update_layout(
            title="净值曲线",
            xaxis_title="时间",
            yaxis_title="净值",
            height=400,
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 自动刷新
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()