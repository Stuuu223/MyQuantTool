"""
龙头战法模块

基于财联社龙头战法精髓：快、狠、准、捕食
"""

import streamlit as st
import pandas as pd
from logic.algo import QuantAlgo
from logic.market_sentiment import MarketSentiment
from logic.market_status import get_market_status_checker, MarketStatus
from logic.position_manager import PositionManager
from logic.trade_log import TradeLog
from logic.logger import get_logger
from logic.sentiment_analyzer import SentimentAnalyzer
from config import Config

logger = get_logger(__name__)

# 获取市场状态检查器单例
market_checker = get_market_status_checker()


def render_market_dashboard(data_manager):
    """
    🆕 V9.11: 渲染市场情绪仪表盘
    
    Args:
        data_manager: 数据管理器实例
    """
    try:
        analyzer = SentimentAnalyzer(data_manager)
        metrics = analyzer.analyze_market_mood()
        
        if metrics:
            # 市场温度和核心指标
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                temperature = analyzer.get_market_temperature()
                st.metric("🌡️ 市场温度", temperature, delta=f"{metrics['score']}分", help="上涨家数占比")
            
            with col2:
                st.metric("🔥 涨停家数", f"{metrics['limit_up']} 家", delta_color="normal")
            
            with col3:
                st.metric("🧊 跌停家数", f"{metrics['limit_down']} 家", delta_color="inverse")
            
            with col4:
                st.metric("📈 上涨家数", f"{metrics['up']} 家")
            
            # 赚钱效应进度条
            st.write("**💰 赚钱效应**")
            st.progress(metrics['score'] / 100)
            st.caption(f"上涨家数占比: {metrics['score']}%")
            
            # 详细指标（可展开）
            with st.expander("📊 详细指标"):
                col5, col6, col7, col8 = st.columns(4)
                with col5:
                    st.metric("平均涨跌幅", f"{metrics['avg_pct']}%")
                with col6:
                    st.metric("中位数涨跌幅", f"{metrics['median_pct']}%")
                with col7:
                    st.metric("强势股占比", f"{metrics['strong_up_ratio']}%", help="涨幅>5%的股票占比")
                with col8:
                    st.metric("弱势股占比", f"{metrics['weak_down_ratio']}%", help="跌幅<-5%的股票占比")
                
                # 🆕 V9.12 修复：ST股和北交所单独统计
                st.divider()
                st.write("**🆕 分板块统计**")
                col9, col10, col11, col12 = st.columns(4)
                with col9:
                    st.metric("ST涨停", f"{metrics.get('st_limit_up', 0)} 家", help="ST股5%涨停")
                with col10:
                    st.metric("ST跌停", f"{metrics.get('st_limit_down', 0)} 家", help="ST股5%跌停")
                with col11:
                    st.metric("北交所涨停", f"{metrics.get('bj_limit_up', 0)} 家", help="北交所30%涨停")
                with col12:
                    st.metric("北交所跌停", f"{metrics.get('bj_limit_down', 0)} 家", help="北交所30%跌停")
            
            # 交易建议
            advice = analyzer.get_trading_advice()
            st.info(f"💡 {advice}")
            
            # 🆕 V9.11.1: 情绪共振报警
            # 检查个股与大盘情绪是否共振
            market_score = metrics['score']
            
            # 如果市场极热（>70分），提示风险
            if market_score > 70:
                st.warning(f"🔥 市场极热（{market_score}分），注意追高风险")
            # 如果市场冰点（<30分），提示机会
            elif market_score < 30:
                st.success(f"🧊 市场冰点（{market_score}分），可能存在低吸机会")
            # 如果市场平衡
            else:
                st.info(f"😐 市场平衡（{market_score}分），可适度参与")
            
            st.divider()
        else:
            st.warning("⚠️ 暂无市场数据")
    
    except Exception as e:
        logger.error(f"市场情绪仪表盘加载失败: {e}")
        st.error(f"⚠️ 情绪仪表盘加载失败: {e}")


def render_market_weather_panel():
    """
    渲染市场天气面板
    """
    st.divider()
    st.subheader("🌤️ 市场天气")
    
    # 创建市场情绪分析器
    market_sentiment = MarketSentiment()
    
    # 获取市场状态
    with st.spinner("正在分析市场天气..."):
        regime_info = market_sentiment.get_market_regime()
    
    # 显示市场天气图标
    col1, col2, col3 = st.columns(3)
    with col1:
        weather_icon = market_sentiment.get_market_weather_icon()
        st.metric("市场天气", weather_icon)
    
    with col2:
        st.metric("市场状态", regime_info['description'])
    
    with col3:
        st.metric("策略建议", regime_info['strategy'])
    
    # 显示详细指标
    market_data = regime_info.get('market_data', {})
    if market_data:
        st.write("**市场指标：**")
        col4, col5, col6 = st.columns(3)
        col4.metric("涨停家数", f"{market_data.get('limit_up_count', 0)} 家")
        col5.metric("跌停家数", f"{market_data.get('limit_down_count', 0)} 家")
        col6.metric("昨日溢价", f"{market_data.get('prev_profit', 0):.2%}")
        
        if market_data.get('max_board', 0) > 0:
            st.metric("最高板数", f"{market_data.get('max_board', 0)} 板")
    
    # 显示当前策略参数
    strategy_params = market_sentiment.get_strategy_parameters(regime_info['regime'])
    st.write("**当前策略参数：**")
    
    with st.expander("查看详细参数"):
        if "龙头" in st.session_state.get('strategy_mode', ''):
            params = strategy_params['dragon']
        elif "趋势" in st.session_state.get('strategy_mode', ''):
            params = strategy_params['trend']
        else:
            params = strategy_params['halfway']
        
        st.json(params)
    
    market_sentiment.close()


def render_position_management_panel():
    """
    渲染资金管理面板
    """
    st.divider()
    st.subheader("💰 资金管理")
    
    # 获取账户资金
    account_value = st.number_input("账户总资金（元）", value=100000, min_value=10000)
    
    # 创建仓位管理器
    position_manager = PositionManager(account_value)
    
    # 显示风险敞口
    risk_exposure = position_manager.get_risk_exposure()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总仓位", f"{risk_exposure['total_position_ratio']:.2%}")
    col2.metric("可用资金", f"¥{risk_exposure['available_cash']:,.2f}")
    col3.metric("持仓数量", f"{risk_exposure['position_count']} 只")
    
    # 显示风险控制参数
    st.info(f"""
    **风险控制参数：**
    - 单笔交易最大亏损：{position_manager.MAX_SINGLE_LOSS_RATIO * 100}%（¥{account_value * position_manager.MAX_SINGLE_LOSS_RATIO:,.2f}）
    - 最大总仓位：{position_manager.MAX_TOTAL_POSITION * 100}%
    - 默认止损比例：{position_manager.DEFAULT_STOP_LOSS_RATIO * 100}%
    """)


def render_dragon_strategy_tab(db, config):
    """
    渲染龙头战法标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("🏹 游资/机构双模作战系统")
    st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
    
    # 🆕 V9.11.2 修复：自动刷新机制（带暂停开关）
    try:
        from streamlit_autorefresh import st_autorefresh
        
        # 🆕 V9.11.2 修复：添加暂停刷新开关
        st.sidebar.subheader("⚙️ 系统设置")
        auto_refresh_enabled = st.sidebar.checkbox("开启自动刷新 (30秒)", value=True, help="每30秒自动刷新市场数据，保持情绪雷达实时更新")
        
        # 🆕 V9.11.2 修复：添加安全模式开关
        use_advanced_features = st.sidebar.checkbox("启用 V9.11 高级特性 (Beta)", value=True, help="启用市场情绪仪表盘等高级功能")
        
        # 🆕 V9.12.1 修复：添加复盘模式开关
        # 默认为 False (实盘)，但在非交易时间建议自动检测并设为 True
        import datetime
        now = datetime.datetime.now().time()
        is_after_hours = now > datetime.time(15, 30) or now < datetime.time(9, 0)
        
        review_mode = st.sidebar.checkbox(
            "📝 开启复盘模式 (禁用时间衰减)", 
            value=is_after_hours,  # 盘后自动开启
            help="开启后，所有股票的时间权重将设为 1.0，便于分析全天涨停质量"
        )
        
        # 🆕 V9.13.1 修复：添加盘前准备按钮
        st.sidebar.divider()
        st.sidebar.subheader("🚀 盘前准备")
        
        warm_up_clicked = st.sidebar.button(
            "🔥 盘前预热 (9:15前运行)",
            help="提前计算监控池股票的连板数和昨日状态，9:25 竞价时将直接读取缓存，大幅提升速度"
        )
        
        if warm_up_clicked:
            with st.spinner("🔥 正在预热监控池股票的身位数据..."):
                try:
                    # 获取监控池股票列表
                    from config import Config
                    config = Config()
                    watchlist = config.get_watchlist()
                    
                    if not watchlist:
                        st.warning("⚠️ 监控池为空，请先添加股票到监控池")
                    else:
                        # 构建股票列表
                        stock_list = [{'code': code} for code in watchlist]
                        
                        # 执行预热
                        result = db.warm_up_stock_status(stock_list)
                        
                        # 显示结果
                        st.success(f"✅ 盘前预热完成！")
                        st.info(f"📊 预热统计：")
                        st.write(f"- 总数：{result['total']} 只")
                        st.write(f"- 成功：{result['success']} 只")
                        st.write(f"- 失败：{result['failed']} 只")
                        st.write(f"- 耗时：{result['elapsed_time']} 秒")
                        st.write(f"- 时间：{result['timestamp']}")
                        st.info(f"💡 9:25 竞价时将直接读取缓存，预计耗时 < 0.1 秒")
                except Exception as e:
                    st.error(f"❌ 盘前预热失败: {e}")
                    logger.error(f"盘前预热失败: {e}")
        
        # 🆕 V9.11.2 修复：根据开关决定是否刷新
        if auto_refresh_enabled:
            count = st_autorefresh(interval=30000, key="market_radar_refresh")
        else:
            st.sidebar.warning("⚠️ 自动刷新已暂停 (输入模式)")
            count = 0
    except ImportError:
        st.sidebar.warning("⚠️ 自动刷新功能未安装，请运行: pip install streamlit-autorefresh")
        count = 0
        st.sidebar.subheader("⚙️ 系统设置")
        use_advanced_features = st.sidebar.checkbox("启用 V9.11 高级特性 (Beta)", value=True, help="启用市场情绪仪表盘等高级功能")
        
        # 🆕 V9.12.1 修复：添加复盘模式开关（无自动刷新时的版本）
        import datetime
        now = datetime.datetime.now().time()
        is_after_hours = now > datetime.time(15, 30) or now < datetime.time(9, 0)
        
        review_mode = st.sidebar.checkbox(
            "📝 开启复盘模式 (禁用时间衰减)", 
            value=is_after_hours,  # 盘后自动开启
            help="开启后，所有股票的时间权重将设为 1.0，便于分析全天涨停质量"
        )
    
    # 🆕 V9.11: 市场情绪仪表盘
    if use_advanced_features:
        try:
            render_market_dashboard(db)
        except Exception as e:
            logger.error(f"市场情绪仪表盘加载失败: {e}")
            st.error(f"⚠️ 情绪仪表盘加载失败，已自动回退: {e}")
    else:
        st.info("已启用安全模式，仅显示基础数据。")
    
    # 显示市场天气面板
    render_market_weather_panel()
    
    # 显示资金管理面板
    render_position_management_panel()
    
    # 1. 模式选择
    st.divider()
    strategy_mode = st.radio(
        "⚔️ 选择作战模式",
        ("🔥 龙头掠食者 (抓连板/妖股)", "🛡️ 趋势中军猎手 (抓机构/业绩/诺思格)", "🚀 半路战法 (抓20cm加速逼空)"),
        index=0,
        horizontal=True
    )
    
    # 保存选择的模式
    st.session_state.strategy_mode = strategy_mode
    
    # 根据模式显示不同的说明
    if "龙头" in strategy_mode:
        st.info("""
        **龙头战法核心要点：**
        - 🎯 只做涨停板股票或即将涨停的股票（涨幅 >= 7%）
        - 💰 优选低价股（≤10元）
        - 📊 关注攻击性放量
        - 📈 等待KDJ金叉
        - 🔄 换手率适中（5-15%）
        - 🚀 **扫描全市场，按涨跌幅排序，分析前N只**
        """)
    elif "趋势" in strategy_mode:
        st.info("""
        **趋势中军战法核心要点：**
        - 🎯 专门抓机构票（诺思格、宁德时代等）
        - 📈 沿着5日线/10日线不停涨
        - 💰 不限制价格，机构喜欢高价股
        - 📊 温和放量（量比 1.0 - 3.0）
        - 🔄 均线多头排列（价格 > MA5 > MA10 > MA20）
        - 🚀 **适合稳健投资，长期持有**
        """)
    else:  # 半路战法
        st.info("""
        **半路战法核心要点：**
        - 🎯 专门抓20cm股票在10%-19%区间的半路板
        - 🚀 加速逼空段，半路扫货博弈20%涨停
        - 📊 攻击性放量（量比 > 3.0）
        - 🔄 买盘强（买一量 > 卖一量）
        - ⚠️ **风险较高，适合激进投资者**
        """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 500, 100, 10, key="dragon_scan_limit")
    with col_scan2:
        min_score = st.slider("最低评分门槛", 30, 90, 60, 5, key="dragon_min_score")
    with col_scan3:
        if st.button("🔍 开始扫描", key="dragon_scan_btn"):
            st.session_state.scan_dragon = True
            st.session_state.strategy_mode = strategy_mode
            st.rerun()
    
    # 🆕 V9.9 新增：股票池过滤选项
    with st.expander("🎯 股票池过滤设置（减少扫描时间）", expanded=False):
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            min_change_pct = st.slider("最小涨幅 (%)", 0.0, 10.0, 3.0, 0.5, key="filter_min_change_pct")
        with col_filter2:
            min_volume = st.number_input("最小成交量 (手)", min_value=1000, max_value=100000, value=5000, step=1000, key="filter_min_volume")
        with col_filter3:
            min_amount = st.number_input("最小成交额 (万元)", min_value=1000, max_value=50000, value=3000, step=1000, key="filter_min_amount")
        
        # 🆕 V9.10.1 新增：核心监控池配置
        st.write("**🎯 核心监控池（白名单）**")
        st.info("💡 监控池中的股票将跳过过滤条件，强制下载K线。适合昨晚复盘选出的目标股。")
        
        # 🆕 V9.10.1 修复：从配置文件加载监控池（持久化）
        watchlist = config.get_watchlist()
        watchlist_str = ",".join(watchlist) if watchlist else ""
        
        # 允许用户编辑监控池
        new_watchlist_str = st.text_input(
            "监控池股票代码（用逗号分隔）",
            value=watchlist_str,
            help="例如：300568,000001,600519",
            key="watchlist_input"
        )
        
        # 解析监控池
        if new_watchlist_str:
            new_watchlist = [code.strip() for code in new_watchlist_str.split(",") if code.strip()]
        else:
            new_watchlist = []
        
        # 🆕 V9.10.1 修复：监控池发生变化时，自动保存到配置文件
        if new_watchlist != watchlist:
            if config.set_watchlist(new_watchlist):
                st.success(f"✅ 监控池已更新：{len(new_watchlist)} 只股票")
                watchlist = new_watchlist
            else:
                st.warning("⚠️ 监控池保存失败")
        
        st.write(f"当前监控池：{len(watchlist)} 只股票")
        
        st.info("💡 提示：设置过滤条件可以大幅减少需要下载K线的股票数量，提升扫描速度。建议：龙头战法使用默认值，趋势战法可降低涨幅要求。")
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        current_mode = st.session_state.get('strategy_mode', strategy_mode)
        
        # 获取过滤参数
        filter_min_change_pct = st.session_state.get('filter_min_change_pct', 9.9)
        filter_min_volume = st.session_state.get('filter_min_volume', 5000)
        filter_min_amount = st.session_state.get('filter_min_amount', 3000)
        
        # 根据模式调用不同的扫描函数
        if "龙头" in current_mode:
            with st.spinner('🔥 正在执行龙头战法筛选 (竞价爆量)...'):
                scan_result = QuantAlgo.scan_dragon_stocks(
                    limit=scan_limit, 
                    min_score=min_score,
                    min_change_pct=filter_min_change_pct,
                    min_volume=filter_min_volume,
                    min_amount=filter_min_amount,
                    watchlist=watchlist  # 🆕 V9.10 新增：传递监控池
                )
        elif "趋势" in current_mode:
            with st.spinner('🛡️ 正在执行趋势中军筛选 (均线多头 + 温和放量)...'):
                scan_result = QuantAlgo.scan_trend_stocks(limit=scan_limit, min_score=min_score)
        else:  # 半路战法
            with st.spinner('🚀 正在执行半路战法筛选 (20cm加速逼空)...'):
                scan_result = QuantAlgo.scan_halfway_stocks(limit=scan_limit, min_score=min_score)
        
        if scan_result['数据状态'] == '正常':
            # 根据模式显示不同的成功消息
            if "龙头" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，分析了 {scan_result['分析数量']} 只，发现 {scan_result['符合条件数量']} 只符合龙头战法条件")
                stock_list_key = '龙头股列表'
            elif "趋势" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只符合趋势中军特征")
                stock_list_key = '趋势股票列表'
            else:  # 半路战法
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只半路板机会")
                stock_list_key = '半路板列表'
            
            if scan_result.get(stock_list_key):
                stocks = scan_result[stock_list_key]
                
                # 根据模式分组显示
                if "龙头" in current_mode:
                    strong_dragons = [s for s in stocks if s['评级得分'] >= 80]
                    potential_dragons = [s for s in stocks if 60 <= s['评级得分'] < 80]
                    weak_dragons = [s for s in stocks if 40 <= s['评级得分'] < 60]
                    
                    # 强龙头
                    if strong_dragons:
                        st.divider()
                        st.subheader("🔥 强龙头（重点关注）")
                        for stock in strong_dragons:
                            _render_dragon_stock(stock, config)
                    
                    # 潜力龙头
                    if potential_dragons:
                        st.divider()
                        st.subheader("📈 潜力龙头（可关注）")
                        for stock in potential_dragons:
                            _render_dragon_stock(stock, config)
                    
                    # 弱龙头
                    if weak_dragons:
                        st.divider()
                        st.subheader("⚠️ 弱龙头（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评级得分': s['评级得分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_dragons])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                elif "趋势" in current_mode:
                    strong_trends = [s for s in stocks if s['评分'] >= 80]
                    potential_trends = [s for s in stocks if 70 <= s['评分'] < 80]
                    weak_trends = [s for s in stocks if 60 <= s['评分'] < 70]
                    
                    # 强趋势中军
                    if strong_trends:
                        st.divider()
                        st.subheader("🔥 强趋势中军（重点关注）")
                        for stock in strong_trends:
                            _render_trend_stock(stock, config)
                    
                    # 趋势中军
                    if potential_trends:
                        st.divider()
                        st.subheader("📈 趋势中军（可关注）")
                        for stock in potential_trends:
                            _render_trend_stock(stock, config)
                    
                    # 弱趋势
                    if weak_trends:
                        st.divider()
                        st.subheader("⚠️ 弱趋势（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评分': s['评分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_trends])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                else:  # 半路战法
                    strong_halfway = [s for s in stocks if s['评分'] >= 80]
                    potential_halfway = [s for s in stocks if 70 <= s['评分'] < 80]
                    weak_halfway = [s for s in stocks if 60 <= s['评分'] < 70]
                    
                    # 强半路板
                    if strong_halfway:
                        st.divider()
                        st.subheader("🔥 强半路板（重点关注）")
                        for stock in strong_halfway:
                            _render_halfway_stock(stock, config)
                    
                    # 半路板
                    if potential_halfway:
                        st.divider()
                        st.subheader("📈 半路板（可关注）")
                        for stock in potential_halfway:
                            _render_halfway_stock(stock, config)
                    
                    # 弱半路板
                    if weak_halfway:
                        st.divider()
                        st.subheader("⚠️ 弱半路板（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评分': s['评分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_halfway])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
            else:
                st.warning("⚠️ 未发现符合条件的半路板股票")
                st.info("""
                💡 **当前市场情况分析：**
                - 大部分20cm股票已封板涨停（无法半路扫货）
                - 半路区间（10%-18.5%）股票数量较少
                - 可能被V9.0游资掠食者系统过滤（触发生死红线）
                
                📌 **建议操作：**
                1. 等待新的20cm股票启动（集合竞价后）
                2. 或降低最低评分门槛（从60分降至40-50分）
                3. 或转向龙头战法（抓连板/妖股）
                """)
        
        # 重置扫描状态
        st.session_state.scan_dragon = False
    else:
        st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的潜在龙头股")
        
        # 显示龙头战法说明
        st.divider()
        st.subheader("📖 龙头战法详解")
        
        with st.expander("🎯 龙头股五个条件"):
            st.markdown("""
            **1. 涨停板（20分）**
            - 必须从涨停板开始
            - 涨停板是多空双方最准确的攻击信号
            - 是所有黑马的摇篮，是龙头的发源地
            
            **2. 价格（20分）**
            - 龙头战法不看价格，直接给满分
            - 价格不影响龙头地位
            
            **3. 成交量（20分）**
            - 攻击性放量（量比>2）：20分
            - 温和放量（量比1.5-2）：15分
            - 缩量或正常：0分
            - 龙头一般出现三日以上的攻击性放量特征
            
            **4. 加速段（20分）**
            - 20cm 加速逼空段（10%-19%）：25分
            - 涨停封死：20分
            - 涨幅 5% 以上：15分
            - 涨幅不足：0分
            
            **5. 换手率（20分）**
            - 适中换手率（5-15%）：20分
            - 偏低换手率（2-5%）：15分
            - 过高或过低换手率：10分或0分
            - 换手率适中显示资金活跃度
            """)
        
        with st.expander("💡 买入技巧"):
            st.markdown("""
            **买入时机：**
            
            **1. 涨停开闸放水时买入**
            - 涨停板打开时，如果量能充足，可以介入
            
            **2. 高开时买入**
            - 未开板的个股，第二天若高开1.5-3.5%，可以买入
            
            **3. 回调买入**
            - 龙头股回到第一个涨停板的启涨点，构成回调买点
            - 比第一个买点更稳、更准、更狠
            
            **操作要点：**
            - 只做第一个涨停板
            - 只做第一次放量的涨停板
            - 相对股价不高，流通市值不大
            - 指标从低位上穿，短线日KDJ低位金叉
            """)
        
        with st.expander("⚠️ 风险控制"):
            st.markdown("""
            **止损点设定：**
            
            **强势市场：**
            - 以该股的第一个涨停板为止损点
            
            **弱势市场：**
            - 以3%为止损点
            
            **严格纪律：**
            - 绝对不允许个股跌幅超过10%
            """)
def _render_dragon_stock(stock, config):
    """渲染龙头股票详情"""
    with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率、竞价量
        st.write("**实时数据：**")
        col3, col4, col5, col6 = st.columns(4)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
# 🆕 V9.2 新增：竞价量显示优化
        auction_volume = stock.get('竞价量', 0)
        
        # 🆕 V9.10 修复：竞价数据回退机制
        if auction_volume == 0:
            # 尝试从第一根K线获取竞价量（近似值）
            try:
                from logic.data_manager import DataManager
                db = DataManager()
                symbol = stock.get('代码', '')
                
                # 获取今天的1分钟K线数据
                kline_data = db.get_realtime_data(symbol)
                
                # 如果K线数据中有成交量，使用第一根K线的成交量作为近似值
                if kline_data and kline_data.get('volume', 0) > 0:
                    # 09:30的第一根K线通常包含了09:25的竞价撮合量
                    auction_volume = int(kline_data.get('volume', 0))
                    stock['竞价量'] = auction_volume  # 更新股票数据
                    col5.metric("竞价量", f"{auction_volume} 手", delta="估算值")
                else:
                    col5.metric("竞价量", "未捕捉", help="程序未在09:25运行，数据已流失")
            except Exception as e:
                # 如果获取失败，显示友好的提示
                col5.metric("竞价量", "未捕捉", help="程序未在09:25运行，数据已流失")
        else:
            col5.metric("竞价量", f"{auction_volume} 手")
        
        # 🆕 V9.2 新增：竞价抢筹度显示优化
        auction_aggression = stock.get('竞价抢筹度', 0)
        if auction_volume == 0 and auction_aggression == 0:
            col6.metric("竞价抢筹度", "N/A", delta="数据缺失")
        else:
            col6.metric("竞价抢筹度", f"{auction_aggression:.2f}%")
        
        # 🆕 V9.12 修复：显示时间权重
        from logic.algo import get_time_weight
        time_weight = get_time_weight(is_review_mode=review_mode)
        time_weight_desc = ""
        if review_mode:
            time_weight_desc = "📝 复盘模式 (不衰减)"
        elif time_weight == 1.0:
            time_weight_desc = "👑 黄金时段"
        elif time_weight == 0.9:
            time_weight_desc = "⚔️ 激战时段"
        elif time_weight == 0.7:
            time_weight_desc = "💤 垃圾时间"
        elif time_weight == 0.4:
            time_weight_desc = "🦊 偷袭时段"
        elif time_weight == 0.0:
            time_weight_desc = "☠️ 最后一击"
        
        # 在竞价抢筹度下方显示时间权重
        if review_mode:
            st.caption(f"⏰ 时间权重: {time_weight_desc}")
        elif time_weight < 1.0:
            st.caption(f"⏰ 时间权重: {time_weight_desc} ({time_weight:.0%})")
        else:
            st.caption(f"⏰ 时间权重: {time_weight_desc}")
        
        # 🆕 V9.13 修复：显示连板身位和弱转强标记
        try:
            from logic.data_manager import DataManager
            db = DataManager()
            symbol = stock.get('代码', '')
            
            # 获取股票状态
            stock_status = db.get_stock_status(symbol)
            lianban_count = stock_status.get('lianban_count', 0)
            yesterday_status = stock_status.get('yesterday_status', '未知')
            yesterday_pct = stock_status.get('yesterday_pct', 0)
            
            # 判断弱转强
            is_weak_to_strong = False
            if yesterday_status in ['烂板', '非涨停', '大跌'] and stock.get('涨跌幅', 0) > 5:
                is_weak_to_strong = True
            
            # 显示连板信息
            st.write("**🆕 连板身位：**")
            col7, col8, col9 = st.columns(3)
            
            if lianban_count >= 5:
                lianban_desc = f"🔥 {lianban_count}连板 (妖股)"
            elif lianban_count >= 3:
                lianban_desc = f"⚔️ {lianban_count}连板 (成妖)"
            elif lianban_count >= 2:
                lianban_desc = f"📈 {lianban_count}连板 (确认)"
            elif lianban_count >= 1:
                lianban_desc = f"🆕 {lianban_count}连板 (首板)"
            else:
                lianban_desc = "📊 未连板"
            
            col7.metric("连板数", lianban_count, delta=lianban_desc)
            col8.metric("昨日状态", yesterday_status, delta=f"{yesterday_pct:.2f}%")
            
            # 弱转强标记
            if is_weak_to_strong:
                col9.metric("弱转强", "✅ 是", delta_color="normal", help="昨日烂板/断板，今日高开超预期")
            else:
                col9.metric("弱转强", "❌ 否", delta_color="off")
            
            # 弱转强提示
            if is_weak_to_strong:
                st.success(f"🔥 弱转强信号：昨日{yesterday_status}，今日强势高开，关注机会！")
            
        except Exception as e:
            # 如果获取失败，不影响主流程
            pass
        
        # 显示买卖盘口数据
        st.write("**买卖盘口：**")
        col7, col8, col9, col10 = st.columns(4)
        
        # 判断是否涨停
        symbol = stock.get('代码', '')
        change_pct = stock.get('涨跌幅', 0)
        
        # 根据股票代码判断涨停阈值
        if symbol.startswith('30') or symbol.startswith('68'):
            # 创业板/科创板：20% 涨停
            is_limit_up = change_pct >= 19.5
        else:
            # 主板：10% 涨停
            is_limit_up = change_pct >= 9.5

        # 🆕 V9.6 修复：使用新的市场状态判断逻辑（支持时区、跌停板）
        # 🆕 V9.7: 支持ST股识别和竞价真空期处理
        bid1_volume = stock.get('买一量', 0)
        ask1_volume = stock.get('卖一量', 0)
        bid1_price = stock.get('买一价', 0)
        ask1_price = stock.get('卖一价', 0)
        stock_name = stock.get('名称', '')

        status_info = market_checker.check_market_status(
            bid1_volume=bid1_volume,
            ask1_volume=ask1_volume,
            change_pct=change_pct,
            symbol=symbol,
            name=stock_name,
            bid1_price=bid1_price,
            ask1_price=ask1_price
        )

        # 🆕 V9.10 修复：根据不同状态显示不同颜色
        if status_info['message']:
            if status_info['status'] == MarketStatus.NOON_BREAK:
                st.info(status_info['message'])  # 午间休盘显示蓝色信息
            elif status_info['status'] in [MarketStatus.CLOSED, MarketStatus.OFF_HOURS]:
                st.warning(status_info['message'])  # 收盘显示黄色警告
            else:
                st.warning(status_info['message'])  # 其他状态显示警告
        
        if is_limit_up:
            col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}", delta="涨停")
            col8.metric("卖一价", "涨停板", delta="无卖单")
            col9.metric("买一量", f"{stock.get('买一量', 0)} 手", delta="封单")
            col10.metric("卖一量", "0 手", delta="无卖单")
        else:
            col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
            col8.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
            col9.metric("买一量", f"{stock.get('买一量', 0)} 手")
            col10.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
        
        # 显示开盘涨幅和封单金额
        st.write("**其他指标：**")
        col11, col12, col13 = st.columns(3)
        col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
        
        if is_limit_up:
            # 涨停时，封单金额 = 买一量（手数）× 100（股/手）× 价格
            # 🆕 使用 DataSanitizer 确保计算正确
            from logic.data_sanitizer import DataSanitizer
            bid1_volume_lots = stock.get('买一量', 0)  # 买一量（手数）
            auction_volume_lots = stock.get('竞价量', 0)  # 竞价量（手数）
            current_price = stock.get('最新价', 0)
            
            # 计算封单金额（基于买一量）
            seal_amount_yuan = DataSanitizer.calculate_amount_from_volume(bid1_volume_lots, current_price)
            seal_amount_wan = seal_amount_yuan / 10000  # 转换为万
            
            # 计算竞价金额（基于竞价量）
            auction_amount_yuan = DataSanitizer.calculate_amount_from_volume(auction_volume_lots, current_price)
            auction_amount_wan = auction_amount_yuan / 10000  # 转换为万
            
            # 🆕 V9.10 修复：竞价金额显示优化
            if auction_volume_lots > 0 and current_price > 0:
                col12.metric("竞价金额", f"¥{auction_amount_wan:.2f} 万", delta="竞价抢筹")
            else:
                col12.metric("竞价金额", "未捕捉", help="程序未在09:25运行，数据已流失")
            col13.metric("封单金额", f"¥{seal_amount_wan:.2f} 万", delta="涨停封单")
        else:
            # 非涨停时，也使用 DataSanitizer 重新计算金额
            from logic.data_sanitizer import DataSanitizer
            bid1_volume_lots = stock.get('买一量', 0)  # 买一量（手数）
            auction_volume_lots = stock.get('竞价量', 0)  # 竞价量（手数）
            current_price = stock.get('最新价', 0)
            
            # 显示竞价金额
            if auction_volume_lots > 0 and current_price > 0:
                auction_amount_yuan = DataSanitizer.calculate_amount_from_volume(auction_volume_lots, current_price)
                auction_amount_wan = auction_amount_yuan / 10000  # 转换为万
                col12.metric("竞价金额", f"¥{auction_amount_wan:.2f} 万")
            else:
                col12.metric("竞价金额", "N/A", delta="数据缺失")
            
            # 显示封单金额
            if bid1_volume_lots > 0 and current_price > 0:
                seal_amount_yuan = DataSanitizer.calculate_amount_from_volume(bid1_volume_lots, current_price)
                seal_amount_wan = seal_amount_yuan / 10000  # 转换为万
                col13.metric("封单金额", f"¥{seal_amount_wan:.2f} 万")
            else:
                col13.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
        
        # 显示评级得分和评级说明
        st.write(f"**评级得分**: {stock['评级得分']}/100")
        st.info(f"**评级说明**: {stock['评级说明']}")
        
        # 显示五个条件得分
        st.write("**五个条件得分：**")
        details = stock['详情']
        st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/25")
        st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
        st.write(f"- 成交量: {details['条件3_成交量']['得分']}/25")
        st.write(f"- 加速段: {details['条件4_加速段']['得分']}/25")
        st.write(f"- 换手率: {details['条件5_换手率']['得分']}/20")
        
        # 显示操作建议
        st.info("**操作建议：**")
        for suggestion in details['操作建议']:
            st.write(suggestion)
        
        # 添加到自选股按钮
        if st.button(f"添加到自选", key=f"add_dragon_{stock['代码']}"):
            watchlist = config.get('watchlist', [])
            if stock['代码'] not in watchlist:
                watchlist.append(stock['代码'])
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
            else:
                st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")


def _render_trend_stock(stock, config):
    """渲染趋势中军股票详情"""
    with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率
        st.write("**实时数据：**")
        col3, col4 = st.columns(2)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
        # 显示均线
        st.write("**均线系统：**")
        col5, col6, col7 = st.columns(3)
        col5.metric("MA5", f"¥{stock.get('MA5', 0):.2f}")
        col6.metric("MA10", f"¥{stock.get('MA10', 0):.2f}")
        col7.metric("MA20", f"¥{stock.get('MA20', 0):.2f}")
        
        # 显示买卖盘口
        st.write("**买卖盘口：**")
        col8, col9, col10, col11 = st.columns(4)
        col8.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
        col9.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
        col10.metric("买一量", f"{stock.get('买一量', 0)} 手")
        col11.metric("卖一量", f"{stock.get('卖一量', 0)} 手")

        # 🆕 V9.6 修复：使用新的市场状态判断逻辑（支持时区、跌停板）
        # 🆕 V9.7: 支持ST股识别和竞价真空期处理
        bid1_volume = stock.get('买一量', 0)
        ask1_volume = stock.get('卖一量', 0)
        change_pct = stock.get('涨跌幅', 0)
        symbol = stock.get('代码', '')
        stock_name = stock.get('名称', '')
        bid1_price = stock.get('买一价', 0)
        ask1_price = stock.get('卖一价', 0)

        status_info = market_checker.check_market_status(
            bid1_volume=bid1_volume,
            ask1_volume=ask1_volume,
            change_pct=change_pct,
            symbol=symbol,
            name=stock_name,
            bid1_price=bid1_price,
            ask1_price=ask1_price
        )

        if status_info['message']:
            st.warning(status_info['message'])
        
        # 显示信号
        st.write(f"**评级得分**: {stock['评分']}/100")
        st.info(f"**信号**: {stock['信号']}")
        
        # 添加到自选股按钮
        if st.button(f"添加到自选", key=f"add_trend_{stock['代码']}"):
            watchlist = config.get('watchlist', [])
            if stock['代码'] not in watchlist:
                watchlist.append(stock['代码'])
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
            else:
                st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")


def _render_halfway_stock(stock, config):
    """渲染半路板股票详情"""
    with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率
        st.write("**实时数据：**")
        col3, col4 = st.columns(2)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
        # 显示买卖盘口
        st.write("**买卖盘口：**")
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
        col6.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
        col7.metric("买一量", f"{stock.get('买一量', 0)} 手")
        col8.metric("卖一量", f"{stock.get('卖一量', 0)} 手")

        # 🆕 V9.6 修复：使用新的市场状态判断逻辑（支持时区、跌停板）
        bid1_volume = stock.get('买一量', 0)
        ask1_volume = stock.get('卖一量', 0)
        change_pct = stock.get('涨跌幅', 0)
        symbol = stock.get('代码', '')
        stock_name = stock.get('名称', '')
        bid1_price = stock.get('买一价', 0)
        ask1_price = stock.get('卖一价', 0)

        status_info = market_checker.check_market_status(
            bid1_volume=bid1_volume,
            ask1_volume=ask1_volume,
            change_pct=change_pct,
            symbol=symbol,
            name=stock_name,
            bid1_price=bid1_price,
            ask1_price=ask1_price
        )

        # 🆕 V9.10 修复：根据不同状态显示不同颜色
        if status_info['message']:
            if status_info['status'] == MarketStatus.NOON_BREAK:
                st.info(status_info['message'])  # 午间休盘显示蓝色信息
            elif status_info['status'] in [MarketStatus.CLOSED, MarketStatus.OFF_HOURS]:
                st.warning(status_info['message'])  # 收盘显示黄色警告
            else:
                st.warning(status_info['message'])  # 其他状态显示警告
        
        # 显示信号和操作建议
        st.write(f"**评级得分**: {stock['评分']}/100")
        st.info(f"**信号**: {stock['信号']}")
        st.success(f"**操作建议**: {stock['操作建议']}")
        
        # 添加到自选股按钮
        if st.button(f"添加到自选", key=f"add_halfway_{stock['代码']}"):
            watchlist = config.get('watchlist', [])
            if stock['代码'] not in watchlist:
                watchlist.append(stock['代码'])
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
            else:
                st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")