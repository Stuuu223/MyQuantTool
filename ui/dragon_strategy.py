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
from config_system import Config

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
    
# 🆕 V10.1.3：初始化 Session State 持久化
    if 'ai_decision' not in st.session_state:
        st.session_state.ai_decision = None
    if 'ai_error' not in st.session_state:
        st.session_state.ai_error = False
    if 'ai_timestamp' not in st.session_state:
        st.session_state.ai_timestamp = None
    
    # 🆕 V9.11.2 修复：自动刷新机制（带暂停开关）
    try:
        from streamlit_autorefresh import st_autorefresh
        
        # 🆕 V19 优化：禁用自动刷新，避免重复扫描导致卡顿
        # 原因：自动刷新会导致每30秒重新执行扫描，扫描全市场5000+只股票非常慢
        st.sidebar.subheader("⚙️ 系统设置")
        auto_refresh_enabled = st.sidebar.checkbox("开启自动刷新 (300秒)", value=False, help="每5分钟自动刷新市场数据（已禁用以避免卡顿）")
        
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
                    from config_system import Config
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
        
        # 🆕 V19 优化：根据开关决定是否刷新
        if auto_refresh_enabled:
            # 增加刷新间隔到300秒（5分钟），避免频繁扫描导致卡顿
            count = st_autorefresh(interval=300000, key="market_radar_refresh")
        else:
            st.sidebar.warning("⚠️ 自动刷新已暂停（推荐，避免卡顿）")
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

    # 显示资金管理面板
    render_position_management_panel()
    
    # 1. 模式选择
    st.divider()
    strategy_mode = st.radio(
        "⚔️ 选择作战模式",
        ("🔥 龙头掠食者 (抓连板/妖股)", "🛡️ 趋势中军猎手 (抓机构/业绩/诺思格)", "🚀 激进半路 (抓20cm 10%-18.5%加速逼空)", "🛡️ 保守半路 (主板2.5%-8% / 20cm 5%-12%)", "🛡️ 低吸战法 (回踩均线/弱转强)", "🌙 尾盘选股 (14:30-15:00)"),
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
    elif "激进半路" in strategy_mode:
        st.info("""
        **激进半路核心要点：**
        - 🎯 专门抓20cm股票在10%-18.5%区间的半路板
        - 🚀 加速逼空段，半路扫货博弈20%涨停
        - 📊 攻击性放量（量比 > 3.0）
        - 🔄 买盘强（买一量 > 卖一量）
        - ⚠️ **风险较高，适合激进投资者**
        """)
    elif "保守半路" in strategy_mode:
        st.info("""
        **保守半路核心要点：**
        - 🎯 主板股票涨幅2.5%-8.0%，20cm股票涨幅5.0%-12.0%
        - 📊 温和放量（量比 > 1.5）
        - 🔄 站稳分时均线或5日均线
        - 🛡️ **风险较低，适合稳健投资者**
        """)
    elif "低吸" in strategy_mode:
        st.info("""
        **低吸战法核心要点：**
        - 🎯 回踩5日均线或分时均线低吸
        - 📊 成交量萎缩（<前日70%）+ DDE资金净流入
        - 🔄 弱转强：监控昨日炸板/烂板，今日竞价超预期高开
        - 📈 分歧转一致：高位回撤5%-15% + 缩量 + 逻辑未死
        - 🛡️ **风险较低，适合稳健投资者**
        """)
    elif "尾盘" in strategy_mode:
        st.info("""
        **尾盘选股核心要点：**
        - 🕐 时间窗口：14:30 - 15:00
        - 📊 高位横盘：全天在均线上方，3%-7%涨幅，窄幅震荡
        - 🚀 尾盘抢筹：14:30后突然放量拉升
        - 🔄 首板回封：早盘涨停后炸板，尾盘再次回封
        - 💰 **用时间换确定性，博次日早盘溢价**
        """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 500, 100, 10, key="dragon_scan_limit")
    with col_scan2:
        min_score = st.slider("最低评分门槛", 30, 90, 60, 5, key="dragon_min_score")
    with col_scan3:
        if st.button("🔍 开始扫描", key="dragon_scan_btn"):
            # 🆕 V10.1.5：扫描新数据前，清除旧的 AI 决策，避免误导
            st.session_state.ai_decision = None
            st.session_state.ai_error = False
            st.session_state.ai_timestamp = None
            
            st.session_state.scan_dragon = True
            st.session_state.strategy_mode = strategy_mode
            st.rerun()
    
    # 🆕 V9.9 新增：股票池过滤选项
    with st.expander("🎯 股票池过滤设置（减少扫描时间）", expanded=False):
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            min_change_pct = st.slider("最小涨幅 (%)", 0.0, 20.0, 7.0, 0.5, key="filter_min_change_pct", help="龙头战法建议7%以上，支持扫描20cm股票（10%-20%区间）")
        with col_filter2:
            min_volume = st.number_input("最小成交量 (手)", min_value=1000, max_value=100000, value=2000, step=1000, key="filter_min_volume", help="降低门槛以捕捉小盘龙头")
        with col_filter3:
            min_amount = st.number_input("最小成交额 (万元)", min_value=1000, max_value=50000, value=1000, step=1000, key="filter_min_amount", help="降低门槛以捕捉小盘龙头")
        
        # 🆕 V19.6 新增：高级筛选选项
        st.write("**🔍 高级筛选选项**")
        col_adv1, col_adv2, col_adv3 = st.columns(3)
        with col_adv1:
            min_turnover = st.slider("最小换手率 (%)", 0.0, 20.0, 0.0, 0.5, key="filter_min_turnover", help="过滤换手率不足的股票，0表示不限制")
        with col_adv2:
            check_dde = st.checkbox("检查DDE资金流向", value=False, key="filter_check_dde", help="检查DDE资金流向，需要额外请求，较慢")
        with col_adv3:
            enable_hot_sectors = st.checkbox("启用热点板块筛选", value=False, key="filter_enable_hot_sectors", help="只扫描热点板块的股票")
        
        # 🆕 V19.6 新增：热点板块选择
        if enable_hot_sectors:
            hot_sectors_input = st.text_input(
                "热点板块（用逗号分隔）",
                value="AI,机器人,低空经济,固态电池,新能源汽车",
                help="例如：AI,机器人,低空经济",
                key="filter_hot_sectors"
            )
            hot_sectors = [s.strip() for s in hot_sectors_input.split(",") if s.strip()]
        else:
            hot_sectors = None
        
        # 🚀 V19.4.9 新增：自动检测收盘后，自动使用收盘数据
        st.write("**🔄 复盘模式**")
        st.info("💡 复盘模式使用历史数据进行分析，适合收盘后复盘当天的涨停板股票。")
        
        # 检测是否收盘后（15:00 之后）
        from datetime import datetime, time as dt_time
        now = datetime.now()
        current_time = now.time()
        market_close_time = dt_time(15, 0)
        is_after_close = current_time >= market_close_time
        
        # 🚀 V19.4.9 优化：收盘后自动使用收盘数据
        if is_after_close:
            # 收盘后，自动使用收盘数据（数据库/Redis中的数据）
            use_history = True
            review_date = now.strftime("%Y%m%d")
            
            # 显示提示信息
            st.success(f"⏰ 已收盘（{current_time.strftime('%H:%M')}），自动使用 {review_date} 的收盘数据进行分析（数据库/Redis）")
        else:
            # 盘中，用户可以选择是否使用复盘模式
            use_history = st.checkbox("启用复盘模式", value=False, key="use_history_mode", help="使用历史数据进行分析，适合收盘后复盘")
            
            if use_history:
                default_date = datetime.now().strftime("%Y%m%d")
                review_date = st.text_input("复盘日期", value=default_date, help="格式：YYYYMMDD，例如：20260120", key="review_date")
            else:
                review_date = None
        
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
        
        st.info("💡 提示：如果扫描结果为0，请尝试：\n1. 降低最小涨幅（如从7%降到5%）\n2. 降低最小成交量/成交额\n3. 增加扫描股票数量\n4. 添加目标股票到监控池（白名单）")
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        current_mode = st.session_state.get('strategy_mode', strategy_mode)
        
        # 获取过滤参数（默认值与UI slider保持一致）
        filter_min_change_pct = st.session_state.get('filter_min_change_pct', 7.0)
        filter_min_volume = st.session_state.get('filter_min_volume', 2000)
        filter_min_amount = st.session_state.get('filter_min_amount', 1000)
        
        # 根据模式调用不同的扫描函数
        # 🚀 V19.4.4 新增：获取复盘模式参数
        use_history = st.session_state.get('use_history_mode', False)
        review_date = st.session_state.get('review_date', None)
        
        if "龙头" in current_mode:
            with st.spinner('🔥 正在执行龙头战法筛选 (竞价爆量)...'):
                scan_result = QuantAlgo.scan_dragon_stocks(
                    limit=scan_limit, 
                    min_score=min_score,
                    min_change_pct=filter_min_change_pct,
                    min_volume=filter_min_volume,
                    min_amount=filter_min_amount,
                    watchlist=watchlist,  # 🆕 V9.10 新增：传递监控池
                    use_history=use_history,  # 🚀 V19.4.4 新增：复盘模式
                    date=review_date  # 🚀 V19.4.4 新增：复盘日期
                )
        elif "趋势" in current_mode:
            with st.spinner('🛡️ 正在执行趋势中军筛选 (均线多头 + 温和放量)...'):
                scan_result = QuantAlgo.scan_trend_stocks(limit=scan_limit, min_score=min_score)
        elif "激进半路" in current_mode:
            with st.spinner('🚀 正在执行激进半路筛选 (20cm 10%-18.5%加速逼空)...'):
                scan_result = QuantAlgo.scan_halfway_stocks(limit=scan_limit, min_score=min_score)
        elif "保守半路" in current_mode:
            with st.spinner('🛡️ 正在执行保守半路筛选 (主板2.5%-8% / 20cm 5%-12%)...'):
                from logic.midway_strategy import get_midway_strategy_instance
                strategy = get_midway_strategy_instance()
                results = strategy.scan_market(
                    min_change_pct=2.5,  # 主板最小涨幅
                    max_change_pct=8.0,  # 主板最大涨幅
                    min_score=0.6,
                    stock_limit=scan_limit,
                    only_20cm=False,  # 包含主板和20cm（20cm会自动扩展到5%-12%）
                    use_active_filter=True  # 🆕 V19.13: 使用活跃股筛选器，提高效率
                )
                scan_result = {
                    '数据状态': '正常',
                    '扫描数量': len(results) if results else 0,
                    '符合条件数量': len(results) if results else 0,
                    '半路股票列表': results if results else []
                }
        elif "低吸" in current_mode:
            with st.spinner('🛡️ 正在扫描低吸机会 (活跃股 TOP{})...'.format(scan_limit)):
                from logic.low_suction_engine import get_low_suction_engine
                from logic.data_manager import DataManager
                from logic.active_stock_filter import get_active_stocks
                
                engine = get_low_suction_engine()
                dm = DataManager()
                
                # 1. 获取活跃股池（🆕 V19.3: 修复选股池，跳过前30只大家伙）
                active_stocks = get_active_stocks(
                    limit=scan_limit,
                    sort_by='amount',  # 按成交额排序，主力战场
                    skip_top=30,  # 🆕 V19.3: 跳过前30只大家伙
                    min_amplitude=3.0,  # 🆕 V19.3: 最小振幅3%，过滤织布机
                    exclude_st=True,
                    exclude_delisting=True
                )
                
                suction_stocks = []
                failed_stocks = []  # 🆕 V19.3: 记录失败的股票
                progress_bar = st.progress(0)
                
                for i, stock_info in enumerate(active_stocks):
                    code = stock_info['code']
                    progress_bar.progress((i + 1) / len(active_stocks))
                    
                    try:
                        # 2. 获取K线数据（用于判断均线和昨日状态）
                        kline = dm.get_history_data(code, period='daily')
                        if kline is None or len(kline) < 2:
                            failed_stocks.append(f"{stock_info['name']}({code}): K线数据不足")
                            continue
                        
                        # 3. 补全昨日状态（修复：弱转强逻辑需要）
                        yesterday = kline.iloc[-2]
                        # 简单判断：昨日振幅 > 8% 且 未涨停，疑似炸板/烂板/大长腿
                        yesterday_limit_up = yesterday['high'] > yesterday['close'] * 1.05 and \
                                           (yesterday['high'] - yesterday['close']) / yesterday['close'] > 0.03
                        
                        # 4. 执行分析
                        result = engine.analyze_low_suction(
                            code,
                            stock_info['price'],
                            stock_info['close'],
                            intraday_data=None,  # 暂时为了速度仍传None
                            logic_keywords=['机器人', 'AI', '低空', '固态', '并购'],  # 热点逻辑
                            yesterday_limit_up=yesterday_limit_up  # ✅ 修复：传入昨日状态
                        )
                        
                        if result['has_suction']:
                            suction_stocks.append({
                                '代码': code,
                                '名称': stock_info['name'],
                                '最新价': stock_info['price'],
                                '涨跌幅': stock_info['change_pct'],
                                '置信度': result['overall_confidence'],
                                '建议': result['recommendation'],
                                '原因': result['reason'],
                                '信号': result.get('suction_signals', []),
                                '弱转强': result.get('weak_to_strong_signal', {})
                            })
                        else:
                            # 🆕 V19.3: 记录失败原因
                            fail_reason = result.get('fail_reason', '未知原因')
                            failed_stocks.append(f"{stock_info['name']}({code}): {fail_reason}")
                    
                    except Exception as e:
                        failed_stocks.append(f"{stock_info['name']}({code}): 异常({str(e)[:30]})")
                        continue
                
                progress_bar.empty()
                
                # 🆕 V19.3: 添加调试日志显示
                if failed_stocks:
                    with st.expander("🔍 扫描日志 (Debug) - 未触发低吸的股票", expanded=False):
                        st.write(f"共扫描 {len(active_stocks)} 只股票，{len(suction_stocks)} 只符合条件，{len(failed_stocks)} 只不符合条件")
                        st.dataframe(pd.DataFrame({'失败原因': failed_stocks}), use_container_width=True, height=200)
                
                scan_result = {
                    '数据状态': '正常',
                    '扫描数量': len(active_stocks),
                    '符合条件数量': len(suction_stocks),
                    '低吸股票列表': suction_stocks
                }
        elif "尾盘" in current_mode:
            with st.spinner('🌙 正在执行尾盘突袭扫描 (活跃股 TOP{})...'.format(scan_limit)):
                from logic.late_trading_scanner import get_late_trading_scanner
                from logic.active_stock_filter import get_active_stocks
                
                scanner = get_late_trading_scanner()
                
                # 1. 强制时间检查（调试模式可注释）
                # if not scanner.is_late_trading_time():
                #     st.warning("⚠️ 提示：当前非尾盘时段，仅做逻辑演示")
                
                # 2. 获取活跃股池（🆕 V19.3: 修复选股池，跳过前30只大家伙）
                active_stocks = get_active_stocks(
                    limit=scan_limit * 2,  # 多取点备选
                    sort_by='amount',  # 按成交额排序
                    min_change_pct=2.0,  # 只看涨幅 > 2% 的票
                    skip_top=30,  # 🆕 V19.3: 跳过前30只大家伙
                    min_amplitude=3.0,  # 🆕 V19.3: 最小振幅3%，过滤织布机
                    exclude_st=True,
                    exclude_delisting=True
                )
                
                # 提取代码和名称
                candidates = [s['code'] for s in active_stocks[:scan_limit]]
                stock_name_dict = {s['code']: s['name'] for s in active_stocks}
                
                # 3. 批量扫描
                scan_result = scanner.scan_late_trading_opportunities(
                    candidates,
                    stock_name_dict=stock_name_dict,
                    max_stocks=scan_limit
                )
                
                # 转换为统一格式
                scan_result['数据状态'] = '正常' if scan_result.get('is_late_trading_time') else '非尾盘时段'
                scan_result['扫描数量'] = len(candidates)
                scan_result['符合条件数量'] = len(scan_result.get('opportunities', []))
                scan_result['尾盘机会列表'] = scan_result.get('opportunities', [])
        
        if scan_result['数据状态'] == '正常':
            # 根据模式显示不同的成功消息
            if "龙头" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，分析了 {scan_result['分析数量']} 只，发现 {scan_result['符合条件数量']} 只符合龙头战法条件")
                stock_list_key = '龙头股列表'
            elif "趋势" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只符合趋势中军特征")
                stock_list_key = '趋势股票列表'
            elif "激进半路" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只激进半路板机会")
                stock_list_key = '半路板列表'
            elif "保守半路" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只保守半路机会")
                stock_list_key = '半路股票列表'
            elif "低吸" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只低吸机会")
                stock_list_key = '低吸股票列表'
            elif "尾盘" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只尾盘机会")
                stock_list_key = '尾盘机会列表'
            
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
                            _render_dragon_stock(stock, config, review_mode=review_mode)
                    
                    # 潜力龙头
                    if potential_dragons:
                        st.divider()
                        st.subheader("📈 潜力龙头（可关注）")
                        for stock in potential_dragons:
                            _render_dragon_stock(stock, config, review_mode=review_mode)
                    
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
                            '角色': s.get('role', '未知'),  # 🆕 V10.1.6：显示角色
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
                            '角色': s.get('role', '未知'),  # 🆕 V10.1.6：显示角色
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_trends])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                elif "低吸" in current_mode:
                    # 按置信度分组
                    strong_suction = [s for s in stocks if s['置信度'] >= 0.8]
                    potential_suction = [s for s in stocks if 0.6 <= s['置信度'] < 0.8]
                    weak_suction = [s for s in stocks if s['置信度'] < 0.6]
                    
                    # 强低吸信号
                    if strong_suction:
                        st.divider()
                        st.subheader("🔥 强低吸信号（重点关注）")
                        for stock in strong_suction:
                            with st.expander(f"🛡️ {stock['名称']} ({stock['代码']}) - 置信度: {stock['置信度']:.2%}"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("最新价", f"¥{stock['最新价']:.2f}")
                                with col2:
                                    st.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                with col3:
                                    st.metric("建议", stock['建议'])
                                
                                st.info(f"📋 **原因**: {stock['原因']}")
                                
                                # 显示信号详情
                                if stock.get('信号'):
                                    st.markdown("**低吸信号详情**:")
                                    for signal in stock['信号']:
                                        st.text(f"• {signal.get('reason', 'N/A')}")
                                
                                # 显示弱转强信号
                                if stock.get('弱转强') and stock['弱转强'].get('has_weak_to_strong'):
                                    st.success(f"🔄 **弱转强信号**: {stock['弱转强'].get('reason', 'N/A')}")
                    
                    # 潜在低吸信号
                    if potential_suction:
                        st.divider()
                        st.subheader("📈 潜在低吸信号（可关注）")
                        for stock in potential_suction:
                            with st.expander(f"🛡️ {stock['名称']} ({stock['代码']}) - 置信度: {stock['置信度']:.2%}"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("最新价", f"¥{stock['最新价']:.2f}")
                                with col2:
                                    st.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                with col3:
                                    st.metric("建议", stock['建议'])
                                
                                st.info(f"📋 **原因**: {stock['原因']}")
                    
                    # 弱低吸信号
                    if weak_suction:
                        st.divider()
                        st.subheader("⚠️ 弱低吸信号（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '置信度': f"{s['置信度']:.2%}",
                            '建议': s['建议']
                        } for s in weak_suction])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                elif "尾盘" in current_mode:
                    # 按信号类型分组
                    stable_hold = [s for s in stocks if s['signal']['signal_type'] == 'STABLE_HOLD']
                    sneak_attack = [s for s in stocks if s['signal']['signal_type'] == 'SNEAK_ATTACK']
                    reseal = [s for s in stocks if s['signal']['signal_type'] == 'RESEAL']
                    
                    # 高位横盘
                    if stable_hold:
                        st.divider()
                        st.subheader("📊 高位横盘（稳健型）")
                        for stock in stable_hold:
                            with st.expander(f"📊 {stock['stock_name']} ({stock['stock_code']})"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("最新价", f"¥{stock['current_price']:.2f}")
                                with col2:
                                    st.metric("涨跌幅", f"{stock['change_pct']*100:.2f}%")
                                with col3:
                                    st.metric("置信度", f"{stock['signal']['confidence']:.2%}")
                                
                                st.info(f"📋 **原因**: {stock['signal']['reason']}")
                                st.text(f"• 分时均价: ¥{stock['signal']['vwap']:.2f}")
                                st.text(f"• 波动率: {stock['signal']['volatility']:.2%}")
                    
                    # 尾盘抢筹
                    if sneak_attack:
                        st.divider()
                        st.subheader("🚀 尾盘抢筹（激进型）")
                        for stock in sneak_attack:
                            with st.expander(f"🚀 {stock['stock_name']} ({stock['stock_code']})"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("最新价", f"¥{stock['current_price']:.2f}")
                                with col2:
                                    st.metric("涨跌幅", f"{stock['change_pct']*100:.2f}%")
                                with col3:
                                    st.metric("置信度", f"{stock['signal']['confidence']:.2%}")
                                
                                st.info(f"📋 **原因**: {stock['signal']['reason']}")
                                st.text(f"• 量比: {stock['signal']['volume_ratio']:.2f}倍")
                                st.text(f"• 价格拉升: {stock['signal']['price_gain']*100:.2f}%")
                    
                    # 首板回封
                    if reseal:
                        st.divider()
                        st.subheader("🔄 首板回封（弱转强）")
                        for stock in reseal:
                            with st.expander(f"🔄 {stock['stock_name']} ({stock['stock_code']})"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("最新价", f"¥{stock['current_price']:.2f}")
                                with col2:
                                    st.metric("涨跌幅", f"{stock['change_pct']*100:.2f}%")
                                with col3:
                                    st.metric("置信度", f"{stock['signal']['confidence']:.2%}")
                                
                                st.info(f"📋 **原因**: {stock['signal']['reason']}")
                                st.text(f"• 炸板次数: {stock['signal']['explosion_count']}")
                                st.text(f"• 回封时间: {stock['signal']['reseal_time']}")
                
                else:  # 激进半路或保守半路
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
                            '角色': s.get('role', '未知'),  # 🆕 V10.1.6：显示角色
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_halfway])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                # 🆕 V10.1.3：添加 AI 指挥官按钮
                st.divider()
                st.subheader("🧠 AI 指挥官")
                
                # 保存扫描结果到 session state，供 AI 使用
                st.session_state.last_scan_result = scan_result
                st.session_state.last_scan_mode = current_mode
                
                if st.button("🧠 呼叫 AI 指挥官", key="call_ai_commander", use_container_width=True):
                    st.session_state.call_ai_commander = True
                    st.rerun()
            else:
                # 🚀 V19.4.6 新增：显示没有找到符合条件的股票
                st.info("💡 没有找到符合条件的股票")
                
                # 显示建议
                if "龙头" in current_mode:
                    st.warning("📋 建议：降低涨幅要求或调整过滤条件，重新扫描")
                elif "趋势" in current_mode:
                    st.warning("📋 建议：降低评分要求或调整过滤条件，重新扫描")
                else:  # 激进半路或保守半路
                    st.warning("📋 建议：降低评分要求或调整过滤条件，重新扫描")
                
                # 显示统计信息
                if '扫描数量' in scan_result:
                    st.info(f"📊 扫描统计：")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("全市场数量", scan_result.get('全市场数量', 0))
                    with col2:
                        st.metric("涨停板数量", scan_result.get('涨停板数量', 0))
                    with col3:
                        st.metric("过滤后数量", scan_result.get('过滤后数量', 0))
        else:
            # 🚀 V19.4.3 新增：显示扫描失败信息
            st.error(f"❌ 扫描失败：{scan_result.get('数据状态', '未知错误')}")
            st.warning(f"📋 说明：{scan_result.get('说明', '无详细说明')}")
            
            # 显示详细信息
            if '扫描数量' in scan_result:
                st.info(f"📊 扫描统计：")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("全市场数量", scan_result.get('全市场数量', 0))
                with col2:
                    st.metric("涨停板数量", scan_result.get('涨停板数量', 0))
                with col3:
                    st.metric("过滤后数量", scan_result.get('过滤后数量', 0))
                
                # 处理 AI 调用
                if st.session_state.get('call_ai_commander', False):
                    try:
                        # 获取扫描结果
                        last_scan_result = st.session_state.get('last_scan_result', {})
                        last_scan_mode = st.session_state.get('last_scan_mode', '')
                        
                        if not last_scan_result or not last_scan_result.get(stock_list_key):
                            st.warning("⚠️ 没有可分析的股票数据，请先执行扫描")
                        else:
                            # 获取第一名股票作为分析对象
                            stocks = last_scan_result[stock_list_key]
                            if stocks:
                                top_stock = stocks[0]
                                
                                # 生成 AI 上下文
                                market_sentiment = MarketSentiment()
                                ai_context = market_sentiment.generate_ai_context(stocks)
                                
                                # 尝试调用 AI
                                with st.spinner("🧠 指挥官正在决策..."):
                                    try:
                                        # 这里应该调用 AI 代理，但是由于没有配置，我们使用降级方案
                                        # 如果有 AI 代理配置，可以在这里调用
                                        # agent = get_ai_agent_instance()
                                        # decision = agent.analyze(ai_context)
                                        
                                        # 降级方案：显示战术映射表
                                        raise Exception("AI 代理未配置，使用降级方案")
                                        
                                    except Exception as ai_error:
                                        # 🆕 V10.1.3：API 失败时的降级方案（脊髓反射）
                                        st.error(f"⚠️ 指挥官失联 ({ai_error})，切换至【机械战术模式】")
                                        
                                        # 显示降级方案：战术映射表
                                        st.markdown("### 🛠️ 战术映射表 (脊髓反射)")
                                        
                                        # 使用真实数据，不硬编码
                                        col_t1, col_t2, col_t3 = st.columns(3)
                                        
                                        with col_t1:
                                            st.metric("标的", f"{top_stock.get('名称', '未知')} ({top_stock.get('代码', 'N/A')})")
                                        
                                        with col_t2:
                                            # 根据模式显示不同的身位
                                            if "龙头" in last_scan_mode:
                                                lianban_status = top_stock.get('lianban_status', '首板')
                                                st.metric("身位", lianban_status)
                                            else:
                                                st.metric("评分", f"{top_stock.get('评级得分', top_stock.get('评分', 0))}分")
                                        
                                        with col_t3:
                                            # 根据真实数据计算战术
                                            change_pct = top_stock.get('涨跌幅', 0)
                                            if change_pct >= 9.5:
                                                tactic = "涨停封死"
                                            elif change_pct >= 7.0:
                                                tactic = "强势拉升"
                                            elif change_pct >= 3.0:
                                                tactic = "温和上涨"
                                            else:
                                                tactic = "弱势震荡"
                                            st.metric("战术", tactic)
                                        
                                        # 显示详细信息
                                        st.info(f"""
                                        **核心指标：**
                                        - 最新价: ¥{top_stock.get('最新价', 0):.2f}
                                        - 涨跌幅: {change_pct:.2f}%
                                        - 量比: {top_stock.get('量比', 0):.2f}
                                        - 换手率: {top_stock.get('换手率', 0):.2f}%
                                        
                                        **乖离率（V18.5）：**
                                        - 5日乖离: {top_stock.get('bias_5', 0):.2f}%
                                        - 10日乖离: {top_stock.get('bias_10', 0):.2f}%
                                        - 20日乖离: {top_stock.get('bias_20', 0):.2f}%
                                        
                                        **概念标签：**
                                        {', '.join(top_stock.get('concept_tags', ['无']))}
                                        
                                        **市场主线：**
                                        {', '.join(ai_context.get('hot_themes', ['无']))}
                                        """)
                                        
                                        # 显示操作建议（基于真实数据）
                                        st.success("✅ 机械战术已激活")
                                        st.info("""
                                        **操作建议：**
                                        - 当前市场主线明确，建议关注主线板块
                                        - 该股票符合当前战法特征，可适量参与
                                        - 严格止损，控制仓位
                                        """)
                                        
                                        # 显示市场情绪
                                        st.markdown("---")
                                        st.markdown("### 📊 市场情绪")
                                        col_m1, col_m2, col_m3 = st.columns(3)
                                        with col_m1:
                                            st.metric("市场天气", ai_context.get('market_weather', '未知'))
                                        with col_m2:
                                            st.metric("市场状态", ai_context.get('description', '未知'))
                                        with col_m3:
                                            st.metric("主线聚焦度", ai_context.get('hot_themes_detailed', '无明显主线'))
                                        
                                        # 显示概念库过期警告
                                        if ai_context.get('concept_map_expired', False):
                                            st.warning("⚠️ 概念库已过期超过7天，建议运行 `python scripts/generate_concept_map.py` 更新")
                                        
                                        # 🆕 V10.1.3：保存降级结果到 session state（持久化）
                                        from datetime import datetime
                                        fallback_msg = f"""
### 🛠️ 战术映射表 (脊髓反射)

**标的**: {top_stock.get('名称', '未知')} ({top_stock.get('代码', 'N/A')})
**身位**: {lianban_status if "龙头" in last_scan_mode else f"{top_stock.get('评级得分', top_stock.get('评分', 0))}分"}
**战术**: {tactic}

**核心指标：**
- 最新价: ¥{top_stock.get('最新价', 0):.2f}
- 涨跌幅: {change_pct:.2f}%
- 量比: {top_stock.get('量比', 0):.2f}
- 换手率: {top_stock.get('换手率', 0):.2f}%

**概念标签：**
{', '.join(top_stock.get('concept_tags', ['无']))}

**市场主线：**
{', '.join(ai_context.get('hot_themes', ['无']))}

**操作建议：**
- 当前市场主线明确，建议关注主线板块
- 该股票符合当前战法特征，可适量参与
- 严格止损，控制仓位

**市场情绪：**
- 市场天气: {ai_context.get('market_weather', '未知')}
- 市场状态: {ai_context.get('description', '未知')}
- 主线聚焦度: {ai_context.get('hot_themes_detailed', '无明显主线')}
"""
                                        st.session_state.ai_decision = fallback_msg
                                        st.session_state.ai_error = True
                                        st.session_state.ai_timestamp = datetime.now()
                                        
                    except Exception as e:
                        logger.error(f"AI 指挥官调用失败: {e}")
                        st.error(f"❌ 系统错误: {str(e)}")
                    
                    # 重置 AI �调用状态
                    st.session_state.call_ai_commander = False
        
        # 🆕 V10.1.3：渲染持久化的 AI 决策（放在按钮逻辑外面，保证刷新后还在）
        if st.session_state.ai_decision:
            st.divider()
            st.subheader("🧠 指挥官决策记录")
            
            if st.session_state.get('ai_error'):
                st.info("🛠️ [脊髓反射模式] 战术建议：")
            else:
                st.success("🦁 [AI 指挥官] 指令：")
            
            # 显示时间戳
            if st.session_state.ai_timestamp:
                from datetime import datetime
                time_str = st.session_state.ai_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                st.caption(f"决策时间: {time_str}")
            
            # 显示决策内容
            st.markdown(st.session_state.ai_decision)
            
            # 添加清空按钮
            if st.button("🗑️ 清空决策记录", key="clear_ai_decision"):
                st.session_state.ai_decision = None
                st.session_state.ai_error = False
                st.session_state.ai_timestamp = None
                st.rerun()
        
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
def _render_dragon_stock(stock, config, review_mode=False):
    """渲染龙头股票详情
    
    Args:
        stock: 股票数据字典
        config: 配置对象
        review_mode: 复盘模式开关
    """
    with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 🆕 V10.1：显示概念标签
        concepts = stock.get('concept_tags', [])
        if concepts:
            # 使用 Streamlit 的 markdown 模拟标签样式
            tags_html = " ".join([f"<span style='background-color:#eee; padding:2px 8px; border-radius:4px; font-size:12px; margin-right:5px'>{c}</span>" for c in concepts])
            st.markdown(f"**题材:** {tags_html}", unsafe_allow_html=True)
        
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
        
        # 🆕 V18.5 新增：乖离率显示
        bias_5 = stock.get('bias_5', 0)
        bias_10 = stock.get('bias_10', 0)
        bias_20 = stock.get('bias_20', 0)
        st.write("**乖离率（V18.5）：**")
        col_b1, col_b2, col_b3 = st.columns(3)
        col_b1.metric("5日乖离", f"{bias_5:.2f}%")
        col_b2.metric("10日乖离", f"{bias_10:.2f}%")
        col_b3.metric("20日乖离", f"{bias_20:.2f}%")
        
        # 乖离率警告
        if bias_5 > 20:
            st.error(f"🚨 [极度超买] 乖离率过高（{bias_5:.1f}%），追高风险极大，禁止买入")
        elif bias_5 > 15:
            st.warning(f"⚠️ [严重超买] 乖离率过高（{bias_5:.1f}%），大幅降低评分")
        elif bias_5 > 10:
            st.warning(f"⚠️ [轻度超买] 乖离率偏高（{bias_5:.1f}%），适度降低评分")
        
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
                
                # 🆕 V18.5: 显示历史数据
                if 'historical_data' in status_info and status_info['historical_data']:
                    hist = status_info['historical_data']
                    st.markdown(f"**历史数据（{hist['date']}）**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("收盘价", f"¥{hist['close']:.2f}")
                    col2.metric("最高价", f"¥{hist['high']:.2f}")
                    col3.metric("最低价", f"¥{hist['low']:.2f}")
                    col4, col5 = st.columns(2)
                    col4.metric("成交量", f"{hist['volume']:.0f}")
                    col5.metric("换手率", f"{hist['turnover_rate']:.2f}%")
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
        
        # 🔥 V10.1.9 [新增] 显示技术形态标签
        trend = stock.get('kline_trend', '')
        if trend:
            # 根据好坏显示不同颜色
            if '📈' in trend or '🟢' in trend:
                st.info(f"📊 技术面: {trend}")  # 蓝色/绿色
            elif '📉' in trend or '🔴' in trend:
                st.error(f"📊 技术面: {trend}") # 红色警示
            else:
                st.caption(f"📊 技术面: {trend}") # 灰色
        
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
        
        # ==========================================
        # 🆕 V10.1.8 [新增] 风险扫描 (Risk Scanner)
        # ==========================================
        st.divider()
        st.write("☠️ **风险扫描** (Prey Alert System)")
        
        try:
            from logic.risk_scanner import RiskScanner
            from datetime import datetime, timezone, timedelta
            from logic.data_sanitizer import DataSanitizer
            
            scanner = RiskScanner()
            
            # 🆕 V10.1.8 修复：正确计算封单金额（基于买一量）
            # 公式：bid_amount = bid_vol * 100 * current_price
            bid1_volume_lots = stock.get('买一量', 0)  # 买一量（手数）
            current_price = stock.get('最新价', 0)
            seal_amount_yuan = DataSanitizer.calculate_amount_from_volume(bid1_volume_lots, current_price)
            
            # 🆕 V10.1.8 修复：确保使用本地时区的时间（兼容 UTC/北京时间）
            # 如果系统是 UTC，手动转换为北京时间（+8 小时）
            now = datetime.now()
            if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
                # 没有时区信息，假设是本地时间（可能是 UTC）
                # 手动检查：如果小时数 < 8，可能是 UTC 时间，转换为北京时间
                if now.hour < 8:
                    # 假设是 UTC 时间，转换为北京时间（+8 小时）
                    now = now + timedelta(hours=8)
            
            # 构建风险扫描所需的数据
            risk_stock_data = {
                'name': stock.get('名称', ''),
                'code': stock.get('代码', ''),
                'open_pct': stock.get('开盘涨幅', 0),
                'pct': stock.get('涨跌幅', 0),
                'turnover': stock.get('成交额', 0) * 10000,  # 转换为元
                'bid_amount': seal_amount_yuan,  # 🆕 V10.1.8 修复：使用正确计算的封单金额（元）
                'is_limit_up': stock.get('涨跌幅', 0) >= 9.5,
                'timestamp': now.timestamp(),  # 🆕 V10.1.8 修复：使用时区修正后的时间
                'average_pct_before_1430': stock.get('涨跌幅', 0) * 0.5  # 简化：假设前半段涨幅是当前的一半
            }
            
            # 执行风险扫描
            risk_result = scanner.scan_stock_risk(risk_stock_data)
            
            # 显示风险等级
            risk_level = risk_result.get('risk_level', '无')
            risk_colors = {
                '无': 'green',
                '低': 'blue',
                '中': 'orange',
                '高': 'red',
                '极高': 'red'
            }
            
            if risk_level == '无':
                st.success(f"✅ 风险等级: {risk_level}")
            elif risk_level == '低':
                st.info(f"🟡 风险等级: {risk_level}")
            elif risk_level == '中':
                st.warning(f"🟠 风险等级: {risk_level}")
            elif risk_level == '高':
                st.error(f"🔴 风险等级: {risk_level}")
            elif risk_level == '极高':
                st.error(f"🚨 风险等级: {risk_level}")
            
            # 显示预警信息
            warnings = risk_result.get('warnings', [])
            if warnings:
                st.write("**预警详情：**")
                for warning in warnings:
                    st.warning(warning)
            
            # 显示操作建议
            advice = risk_result.get('advice', '')
            if advice:
                st.write("**风险建议：**")
                if '严禁' in advice or '撤单' in advice:
                    st.error(advice)
                elif '谨慎' in advice:
                    st.warning(advice)
                else:
                    st.info(advice)
            
        except Exception as e:
            st.info("风险扫描功能暂时不可用")
        
        st.divider()
        # ==========================================
        # 🆕 V10.1.8 逻辑结束
        # ==========================================
        
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
        
        # 🆕 V10.1：显示概念标签
        concepts = stock.get('concept_tags', [])
        if concepts:
            # 使用 Streamlit 的 markdown 模拟标签样式
            tags_html = " ".join([f"<span style='background-color:#eee; padding:2px 8px; border-radius:4px; font-size:12px; margin-right:5px'>{c}</span>" for c in concepts])
            st.markdown(f"**题材:** {tags_html}", unsafe_allow_html=True)
        
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
        
        # 🆕 V18.5 新增：乖离率显示
        current_price = stock.get('最新价', 0)
        ma5 = stock.get('MA5', 0)
        ma10 = stock.get('MA10', 0)
        ma20 = stock.get('MA20', 0)
        
        bias_5 = 0.0
        bias_10 = 0.0
        bias_20 = 0.0
        
        if ma5 > 0:
            bias_5 = (current_price - ma5) / ma5 * 100
        if ma10 > 0:
            bias_10 = (current_price - ma10) / ma10 * 100
        if ma20 > 0:
            bias_20 = (current_price - ma20) / ma20 * 100
        
        st.write("**乖离率（V18.5）：**")
        col_b1, col_b2, col_b3 = st.columns(3)
        col_b1.metric("5日乖离", f"{bias_5:.2f}%")
        col_b2.metric("10日乖离", f"{bias_10:.2f}%")
        col_b3.metric("20日乖离", f"{bias_20:.2f}%")
        
        # 乖离率警告
        if bias_5 > 20:
            st.error(f"🚨 [极度超买] 乖离率过高（{bias_5:.1f}%），追高风险极大，禁止买入")
        elif bias_5 > 15:
            st.warning(f"⚠️ [严重超买] 乖离率过高（{bias_5:.1f}%），大幅降低评分")
        elif bias_5 > 10:
            st.warning(f"⚠️ [轻度超买] 乖离率偏高（{bias_5:.1f}%），适度降低评分")
        
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
        
        # 🆕 V10.1：显示概念标签
        concepts = stock.get('concept_tags', [])
        if concepts:
            # 使用 Streamlit 的 markdown 模拟标签样式
            tags_html = " ".join([f"<span style='background-color:#eee; padding:2px 8px; border-radius:4px; font-size:12px; margin-right:5px'>{c}</span>" for c in concepts])
            st.markdown(f"**题材:** {tags_html}", unsafe_allow_html=True)
        
        # 显示量比、换手率
        st.write("**实时数据：**")
        col3, col4 = st.columns(2)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
        # 🆕 V18.5 新增：乖离率显示
        bias_5 = stock.get('bias_5', 0)
        bias_10 = stock.get('bias_10', 0)
        bias_20 = stock.get('bias_20', 0)
        st.write("**乖离率（V18.5）：**")
        col_b1, col_b2, col_b3 = st.columns(3)
        col_b1.metric("5日乖离", f"{bias_5:.2f}%")
        col_b2.metric("10日乖离", f"{bias_10:.2f}%")
        col_b3.metric("20日乖离", f"{bias_20:.2f}%")
        
        # 乖离率警告
        if bias_5 > 20:
            st.error(f"🚨 [极度超买] 乖离率过高（{bias_5:.1f}%），追高风险极大，禁止买入")
        elif bias_5 > 15:
            st.warning(f"⚠️ [严重超买] 乖离率过高（{bias_5:.1f}%），大幅降低评分")
        elif bias_5 > 10:
            st.warning(f"⚠️ [轻度超买] 乖离率偏高（{bias_5:.1f}%），适度降低评分")
        
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
                
                # 🆕 V18.5: 显示历史数据
                if 'historical_data' in status_info and status_info['historical_data']:
                    hist = status_info['historical_data']
                    st.markdown(f"**历史数据（{hist['date']}）**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("收盘价", f"¥{hist['close']:.2f}")
                    col2.metric("最高价", f"¥{hist['high']:.2f}")
                    col3.metric("最低价", f"¥{hist['low']:.2f}")
                    col4, col5 = st.columns(2)
                    col4.metric("成交量", f"{hist['volume']:.0f}")
                    col5.metric("换手率", f"{hist['turnover_rate']:.2f}%")
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