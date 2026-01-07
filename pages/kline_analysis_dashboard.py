"""
K线数据仪表板 + 邮件告警集成
页面: K线分析 + 游资分散度 + 告警设置
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import akshare as ak

from logic.kline_analyzer import KlineAnalyzer, KlineMetrics
from logic.capital_profiler import CapitalProfiler
from logic.email_alert_service import EmailAlertService


st.set_page_config(
    page_title="K线分析 & 高石告警",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = KlineAnalyzer()
if 'alert_service' not in st.session_state:
    st.session_state.alert_service = EmailAlertService()
if 'profiler' not in st.session_state:
    st.session_state.profiler = CapitalProfiler()

analyzer = st.session_state.analyzer
alert_service = st.session_state.alert_service
profiler = st.session_state.profiler

# 主页面
st.title("📊 K线数据实新分析过章章")
st.markdown("""---""")

# 侧边栏 - 配置区域
 with st.sidebar:
    st.subheader("⚙️ 配置中心")
    
    # 1. 邮件配置
    with st.expander("📎 邮件告警配置"):
        st.write("**Gmail配置步骤:**")
        st.code("""
1. 转 Gmail 控制台 (myaccount.google.com)
2. 安全 > 两步验证 (开启)
3. 安全 > 应用专用密码 (app_password)
4. 复制八屋字上憠螺儿
        """)
        
        email_input = st.text_input(
            "📧 发件邮箱",
            type="default",
            placeholder="your@gmail.com"
        )
        
        password_input = st.text_input(
            "🔐 应用密码",
            type="password",
            placeholder="xxxx xxxx xxxx xxxx"
        )
        
        if st.button("🔗 连接邮箱"):
            try:
                alert_service.configure(
                    sender_email=email_input,
                    sender_password=password_input
                )
                st.success("✅ 邮箱配置成功!")
            except Exception as e:
                st.error(f"❌ 配置失败: {str(e)}")
    
    # 2. 接收邮箱
    receiver_email = st.text_input(
        "📩 接收邮箱",
        placeholder="receiver@example.com"
    )
    
    st.divider()

# 主顶部: 市场指数
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 市场指数",
    "📊 K线分析",
    "🎯 游资集中度",
    "📧 告警测试"
])

# Tab 1: 市场指数
with tab1:
    st.subheader("📈 整体市场行情")
    
    if st.button("🔄 刷新整体市场"):
        with st.spinner("正在获取市场数据..."):
            market_overview = analyzer.get_market_overview()
            st.session_state.market_overview = market_overview
    
    if 'market_overview' in st.session_state:
        overview = st.session_state.market_overview
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("📕 上市旨数", overview.get('total_count', 0))
        col2.metric("📈 上涨", f"{overview.get('up_count', 0)} 只")
        col3.metric("📉 下跌", f"{overview.get('down_count', 0)} 去")
        col4.metric("🚨 涨停", f"{overview.get('limit_up_count', 0)}", delta="+1")
        col5.metric("🔶 跌停", f"{overview.get('limit_down_count', 0)}", delta="-1")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💻 平均涨跌幅", f"{overview.get('avg_change', 0):.2f}%")
        col2.metric("💰 成交额", f"{overview.get('total_amount', 0):,.0f} 元")
        col3.metric(💷 总成交量", f"{overview.get('total_volume', 0):,.0f}")

# Tab 2: K线分析
with tab2:
    st.subheader("📊 股票K线技术分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code = st.text_input(
            "📦 输入股票代码",
            value="000001",
            placeholder="000001"
        )
    
    with col2:
        if st.button("🔍 分析股票"):
            st.session_state.analyzing = True
    
    if st.session_state.get('analyzing', False):
        with st.spinner(f"正在分析{stock_code}..."):
            # 获取指标
            metrics = analyzer.get_metrics(stock_code)
            
            if metrics:
                st.success("✅ 分析完成!")
                
                # 技术指标仪表板
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 当前价格", f"{metrics.current_price:.2f}", delta="+0.5")
                col2.metric("📊 技术评分", f"{metrics.get_technical_score():.0f}", delta="+5")
                col3.metric("🎉 趋势", metrics.trend_strength)
                
                # 技术指标详情
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**移动平均线**")
                    st.write(f"MA5: {metrics.ma5:.2f}")
                    st.write(f"MA10: {metrics.ma10:.2f}")
                    st.write(f"MA20: {metrics.ma20:.2f}")
                
                with col2:
                    st.write("**MACD指标**")
                    st.write(f"MACD: {metrics.macd:.4f}")
                    st.write(f"信号线: {metrics.macd_signal:.4f}")
                    st.write(f"枱形: {metrics.macd_histogram:.4f}")
                
                with col3:
                    st.write("**RSI/KDJ**")
                    st.write(f"RSI14: {metrics.rsi14:.1f}")
                    st.write(f"KDJ-K: {metrics.kdj_k:.1f}")
                    st.write(f"KDJ-D: {metrics.kdj_d:.1f}")
                
                # 描纺半籤
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**整理位**")
                    st.write(f"支撒: {metrics.support_level:.2f}")
                    st.write(f"阻力: {metrics.resistance_level:.2f}")
                
                with col2:
                    st.write("**流动性**")
                    st.write(f"波动率: {metrics.volatility:.2f}%")
                    st.write(f"成交量均线: {metrics.volume_sma:,.0f}")
            else:
                st.error("❌ 无法获取数据")

# Tab 3: 游资集中度
with tab3:
    st.subheader("💯 游资集中度分析")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        capital_name = st.text_input(
            "📦 游资名称",
            value="章盟主",
            placeholder="章盟主"
        )
    
    with col2:
        analysis_date = st.date_input(
            "📅 分析日期",
            value=datetime.now() - timedelta(days=1)
        )
    
    with col3:
        if st.button("🔍 市场分梎"):
            st.session_state.analyzing_capital = True
    
    if st.session_state.get('analyzing_capital', False):
        with st.spinner(f"正在分析{capital_name}的集中度..."):
            # 获取龙虎榜数据
            date_str = analysis_date.strftime('%Y%m%d')
            df_lhb = ak.stock_lhb_daily_em(date=date_str)
            
            if not df_lhb.empty:
                # 游资集中度分析
                concentration = analyzer.get_concentration_analysis(
                    capital_name,
                    df_lhb
                )
                
                if concentration:
                    st.success("✅ 分析完成!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("揕噗科目", concentration['total_stocks'])
                    col2.metric("HHI指数", f"{concentration['hhi_index']:.0f}")
                    col3.metric("控板窗口", concentration['concentration_level'])
                    col4.metric("TOP5集中", f"{concentration['top5_concentration']:.1%}")
                    
                    # TOP5股票
                    st.subheader(f"💯 {capital_name} TOP 5 股票")
                    top_stocks = pd.DataFrame([
                        {'股票代码': code, '成交额': amount}
                        for code, amount in concentration['top_stocks'].items()
                    ])
                    st.dataframe(top_stocks, use_container_width=True)
                else:
                    st.warning("⚠️ 没有找到游资")
            else:
                st.error("❌ 无法获取龙虎榜数据")

# Tab 4: 告警测试
with tab4:
    st.subheader("📧 邮件告警测试")
    
    st.warning("🚧 需要先附禮邮箱轮改配置")
    
    if not receiver_email:
        st.error("📎 请先配置接收邮箱")
    elif not alert_service.enabled:
        st.error("🛠️ 邮件服务未配置")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚨 高风险告警")
            if st.button("📎 发送高风险告警"):
                result = alert_service.send_risk_alert(
                    capital_name='章盟主',
                    risk_score=78,
                    risk_level='高风险',
                    risk_factors=[
                        '风格漂离 +50%',
                        '对全失利率上升',
                        '流动性下頜'
                    ],
                    recipient=receiver_email
                )
                if result:
                    st.success("✅ 点放吾告警已发送!")
                else:
                    st.error("❌ 发送失败")
        
        with col2:
            st.subheader("🟢 高机会通知")
            if st.button("🟢 发送高机会告警"):
                result = alert_service.send_opportunity_alert(
                    predicted_capitals=['章盟主', '万洲股份'],
                    activity_score=82,
                    predicted_stocks=['000001', '000002', '000333'],
                    recipient=receiver_email
                )
                if result:
                    st.success("✅ 高机会通知已发送!")
                else:
                    st.error("❌ 发送失败")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 打板突破告警")
            if st.button("📈 发送打板突破"):
                result = alert_service.send_breakout_alert(
                    stock_code='000001',
                    stock_name='平安银行',
                    breakout_price=11.50,
                    breakout_type='up',
                    capitals=['章盟主', '万洲股份'],
                    recipient=receiver_email
                )
                if result:
                    st.success("✅ 打板突破告警已发送!")
                else:
                    st.error("❌ 发送失败")
        
        with col2:
            st.subheader("📊 日线总结")
            if st.button("📊 发送日线总结"):
                result = alert_service.send_daily_summary(
                    date='2026-01-07',
                    limit_up_count=35,
                    limit_down_count=12,
                    top_gainers={'000001': ('平安银行', 9.95)},
                    top_losers={'000002': ('万科A', -9.95)},
                    top_capitals={'章盟主': 5000000},
                    recipient=receiver_email
                )
                if result:
                    st.success("✅ 日线总结已发送!")
                else:
                    st.error("❌ 发送失败")
        
        st.divider()
        st.subheader("📦 告警历史")
        sent_alerts = alert_service.get_sent_alerts()
        if sent_alerts:
            alerts_df = pd.DataFrame(sent_alerts)
            st.dataframe(alerts_df, use_container_width=True)
        else:
            st.info("✅ 还没有发送任何告警")

st.markdown("""---""")
st.caption("Made with ❤️ by MyQuantTool Team")
