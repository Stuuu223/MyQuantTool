import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.ai_agent import DeepSeekAgent
from logic.comparator import StockComparator
from logic.backtest import BacktestEngine
from config import Config
import os

st.set_page_config(page_title="个人化A股智能终端", layout="wide", page_icon="📈", menu_items={
    'Get Help': None,
    'Report a bug': None,
    'About': None
})

# 添加自定义说明
st.markdown("""
<style>
.stAppHeader {
    background-color: #f0f2f6;
}
</style>
""", unsafe_allow_html=True)

# --- 加载配置 ---
config = Config()

# API Key 优先级：环境变量 > 配置文件 > 默认值
API_KEY = os.getenv("SILICONFLOW_API_KEY") or config.get('api_key', 'sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet')

db = DataManager()
ai_agent = DeepSeekAgent(api_key=API_KEY)
comparator = StockComparator(db)
backtest_engine = BacktestEngine()

# 全局辅助函数：格式化金额显示
def format_amount(amount):
    """格式化金额显示，自动转换为万或亿单位"""
    abs_amount = abs(amount)
    if abs_amount >= 100000000:  # 1亿以上
        return f"{amount/100000000:.2f}亿"
    elif abs_amount >= 10000:  # 1万以上
        return f"{amount/10000:.2f}万"
    else:
        return f"{amount:.0f}"

st.title("🚀 个人化A股智能投研终端")
st.markdown("基于 DeepSeek AI & AkShare 数据 | 专为股市小白设计")

# 初始化session state
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

# 添加系统菜单说明
# st.caption("💡 右上角菜单说明：")
# st.caption("  • ⚙️ Settings（设置）：调整显示主题、字体大小等")
# st.caption("  • 🚀 Deploy（部署）：将应用部署到云端（需要账号）")
# st.caption("  • ❌ Clear cache（清除缓存）：刷新数据和重置状态")

# 添加功能标签页
tab_single, tab_compare, tab_backtest, tab_sector, tab_lhb, tab_dragon, tab_auction = st.tabs(["📊 单股分析", "🔍 多股对比", "🧪 策略回测", "🔄 板块轮动", "🏆 龙虎榜", "🔥 龙头战法", "⚡ 集合竞价"])

with st.sidebar:
    st.header("🎮 控制台")
    
    # 获取自选股列表
    watchlist = config.get('watchlist', [])
    
    # 从配置文件加载默认值，如果session state中有选中的股票，则使用选中的
    # 如果没有选中的股票，优先使用自选股最后一个，否则使用配置文件的默认值
    if st.session_state.selected_stock:
        default_symbol = st.session_state.selected_stock
    elif watchlist:
        default_symbol = watchlist[-1]  # 使用自选股最后一个
    else:
        default_symbol = config.get('default_symbol', '600519')
    
    # 搜索模式选择
    search_mode = st.radio("搜索方式", ["按代码", "按名称"], horizontal=True)
    
    if search_mode == "按代码":
        symbol = st.text_input("股票代码", value=default_symbol, help="请输入6位A股代码")
    else:
        # 按名称搜索
        search_name = st.text_input("股票名称", placeholder="输入股票名称，如：贵州茅台", help="支持模糊搜索")
        
        if search_name:
            with st.spinner('正在搜索...'):
                matched_codes = QuantAlgo.get_stock_code_by_name(search_name)
            
            if matched_codes:
                # 显示匹配的股票列表
                st.write(f"找到 {len(matched_codes)} 只匹配的股票：")
                stock_options = []
                for code in matched_codes:
                    name = QuantAlgo.get_stock_name(code)
                    stock_options.append(f"{name} ({code})")
                
                selected_stock = st.selectbox("选择股票", stock_options)
                
                # 从选中项中提取股票代码
                if selected_stock:
                    symbol = selected_stock.split('(')[1].rstrip(')')
            else:
                st.warning("未找到匹配的股票")
                symbol = default_symbol
        else:
            symbol = default_symbol
    
    start_date = st.date_input("开始日期", pd.to_datetime(config.get('default_start_date', '2024-01-01')))
    
    # 策略参数
    st.subheader("⚙️ 策略参数")
    atr_mult = st.slider("ATR 倍数", 0.1, 2.0, float(config.get('atr_multiplier', 0.5)), 0.1)
    grid_ratio = st.slider("网格比例", 0.05, 0.5, float(config.get('grid_ratio', 0.1)), 0.05)
    
    run_ai = st.button("🧠 智能分析")
    
    st.markdown("---")
    
    # 自选股管理
    st.subheader("⭐ 自选股")
    
    if watchlist:
        st.write("已关注的股票：")
        for stock in watchlist:
            stock_name = QuantAlgo.get_stock_name(stock)
            col_watch, col_remove = st.columns([3, 1])
            with col_watch:
                if st.button(f"📌 {stock_name} ({stock})", key=f"select_{stock}"):
                    st.session_state.selected_stock = stock
                    st.rerun()
            with col_remove:
                if st.button("❌", key=f"remove_{stock}"):
                    watchlist.remove(stock)
                    config.set('watchlist', watchlist)
                    st.success(f"已删除 {stock_name} ({stock})")
                    st.rerun()
    
    add_stock = st.text_input("添加自选股", placeholder="输入股票代码", help="例如：600519")
    if st.button("➕ 添加") and add_stock:
        if add_stock not in watchlist:
            stock_name = QuantAlgo.get_stock_name(add_stock)
            watchlist.append(add_stock)
            config.set('watchlist', watchlist)
            st.success(f"已添加 {stock_name} ({add_stock}) 到自选股")
        else:
            stock_name = QuantAlgo.get_stock_name(add_stock)
            st.warning(f"{stock_name} ({add_stock}) 已在自选股中")
    
    st.markdown("---")
    
    # 配置管理
    with st.expander("🔧 配置管理"):
        new_api_key = st.text_input("API Key", type="password", value=API_KEY if API_KEY else "")
        
        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("保存配置"):
                config.update({
                    'api_key': new_api_key,
                    'default_symbol': symbol,
                    'default_start_date': str(start_date),
                    'atr_multiplier': atr_mult,
                    'grid_ratio': grid_ratio
                })
                st.success("配置已保存！")
        
        with col_reset:
            if st.button("重置配置"):
                config.reset()
                st.success("配置已重置！")
    
    st.caption("数据来源: AkShare 开源接口")
    
    # 提示用户使用本地分析系统
    st.info("💡 现在使用本地智能分析系统，无需 API Key，分析更快速、更稳定！")

with tab_single:
    # 自选股快速切换
    watchlist = config.get('watchlist', [])
    if watchlist:
        st.subheader("⭐ 自选股快速切换")
        selected_watch = st.selectbox("选择自选股", ["手动输入"] + watchlist)
        if selected_watch != "手动输入":
            symbol = selected_watch
    
    # 添加指标解释按钮
    with st.expander("📖 技术指标解释（小白必读）"):
        st.markdown("""
        ### 📌 基础指标
        
        **最新价格**：股票当前的市场价格，这是买卖的基准价
        
        **涨跌幅**：今日相比昨日的涨跌百分比，红色表示上涨，绿色表示下跌
        
        **ATR 波动率**：衡量股价波动的剧烈程度，ATR 越大风险越高
        
        ---
        
        ### 📦 形态识别
        
        **箱体震荡（Box Pattern）**：
        - 股价在固定区间内上下波动
        - **箱体内**：在下沿买入，上沿卖出，做波段
        - **向上突破**：可能迎来上涨，注意观察
        - **向下突破**：注意风险，考虑止损
        - 💡 最常见的形态，适合短线操作
        
        **双底/双顶**：
        - **双底**：W形，两次探底不创新低，底部确认
        - **双顶**：M形，两次冲高不创新高，顶部确认
        - 💡 重要的反转信号
        
        **头肩顶/头肩底**：
        - **头肩顶**：三高形态，中间最高，看跌信号
        - **头肩底**：三低形态，中间最低，看涨信号
        - 💡 经典的反转形态，可靠性高
        
        ---
        
        ### 🎯 技术指标
        
        **MACD（异同移动平均线）**：
        - 判断趋势方向
        - MACD > 信号线：趋势向上，适合买入
        - MACD < 信号线：趋势向下，适合卖出
        
        **RSI（相对强弱指标）**：
        - 判断超买超卖
        - RSI > 70：超买，价格过高，注意风险
        - RSI < 30：超卖，价格过低，可能反弹
        
        **布林带**：
        - 判断价格高低
        - 价格接近上轨：偏高，考虑减仓
        - 价格接近下轨：偏低，考虑买入
        
        **KDJ 指标**：
        - 超买超卖指标，结合动量和强弱
        - K > D 且 J > 0：金叉，买入信号
        - K < D 且 J < 0：死叉，卖出信号
        - K > 80 且 D > 80：超买，注意风险
        - K < 20 且 D < 20：超卖，可能反弹
        
        **成交量分析**：
        - 量比 > 2：放量显著，关注主力动向
        - 量比 1.5-2：温和放量，资金参与度提升
        - 量比 < 0.5：缩量，观望为主
        - 💡 量价配合是关键
        
        **资金流向**：
        - 流入：价格上涨，资金净流入
        - 流出：价格下跌，资金净流出
        - 持平：价格持平，资金无明显流向
        - 💡 反映主力资金动向
        
        ---
        
        ### ⚙️ 策略参数
        
        **ATR 倍数**：调整网格宽度
        - 保守型：1.0-1.5（交易少，风险低）
        - 激进型：0.3-0.5（交易多，风险高）
        - 推荐值：0.5
        
        **网格比例**：每次交易的资金比例
        - 保守型：5%-10%
        - 激进型：20%-30%
        - 推荐值：10%
        
        ---
        
        💡 **新手建议**：不要只看一个指标，要综合判断。先用模拟盘练习，从小资金开始！
        """)
    
    if symbol:
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在连接交易所数据管道...'):
            df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)
        
        if not df.empty and len(df) > 30:
            current_price = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close']
            change_pct = (current_price - prev_close) / prev_close * 100
            
            # 计算各项技术指标
            atr = QuantAlgo.calculate_atr(df)
            resistance_levels = QuantAlgo.calculate_resistance_support(df)
            grid_plan = QuantAlgo.generate_grid_strategy(current_price, atr)
            macd_data = QuantAlgo.calculate_macd(df)
            rsi_data = QuantAlgo.calculate_rsi(df)
            bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
            box_pattern = QuantAlgo.detect_box_pattern(df)
            kdj_data = QuantAlgo.calculate_kdj(df)
            volume_data = QuantAlgo.analyze_volume(df)
            turnover_data = QuantAlgo.get_turnover_rate(df)
            turnover_volume_analysis = QuantAlgo.analyze_turnover_and_volume(
                turnover_data.get('换手率'), 
                volume_data.get('量比', 1)
            )
            money_flow_data = QuantAlgo.analyze_money_flow(df, symbol=symbol, market="sh" if symbol.startswith("6") else "sz")
            double_bottom = QuantAlgo.detect_double_bottom(df)
            double_top = QuantAlgo.detect_double_top(df)
            head_shoulders = QuantAlgo.detect_head_shoulders(df)
            
            # 分离支撑位和阻力位
            support_levels = [x for x in resistance_levels if x < current_price]
            resistance_levels = [x for x in resistance_levels if x > current_price]

            # 获取股票名称
            stock_name = QuantAlgo.get_stock_name(symbol)

            # 顶部指标卡片
            col_title, col_add = st.columns([3, 1])
            with col_title:
                st.subheader(f"📈 核心指标看板 - {stock_name} ({symbol})")
            with col_add:
                if st.button("⭐ 加自选", key=f"add_to_watchlist_{symbol}"):
                    watchlist = config.get('watchlist', [])
                    if symbol not in watchlist:
                        watchlist.append(symbol)
                        config.set('watchlist', watchlist)
                        st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
                    else:
                        st.info(f"{stock_name} ({symbol}) 已在自选股中")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("最新价格", f"¥{current_price}", f"{change_pct:.2f}%")
            col2.metric("日内波动 (ATR)", f"{atr:.2f}")
            col3.metric("网格密度", f"¥{grid_plan['网格宽度']}")
            col4.metric("AI模型", "DeepSeek-V3")

            # 箱体震荡提示
            st.divider()
            if box_pattern['is_box']:
                st.success(f"📦 **{box_pattern['message']}**")
                col_box1, col_box2, col_box3 = st.columns(3)
                with col_box1:
                    st.metric("箱体上沿", f"¥{box_pattern['box_high']}")
                with col_box2:
                    st.metric("箱体下沿", f"¥{box_pattern['box_low']}")
                with col_box3:
                    st.metric("箱体宽度", f"¥{box_pattern['box_width']}")
                st.info(f"💡 当前价格在箱体 {box_pattern['position_pct']}% 位置，建议在箱体下沿附近买入，上沿附近卖出")
            elif box_pattern.get('is_breakout_up'):
                st.warning(f"🚀 **{box_pattern['message']}**")
                st.info(f"💡 向上突破 {box_pattern['breakout_pct']:.2f}%，注意观察是否有效突破，可能迎来上涨行情")
            elif box_pattern.get('is_breakout_down'):
                st.error(f"⚠️ **{box_pattern['message']}**")
                st.info(f"💡 向下突破 {box_pattern['breakout_pct']:.2f}%，注意风险控制，可能继续下跌")
            else:
                st.info(f"📊 **{box_pattern['message']}**")

            # 个股扫雷
            st.divider()
            st.subheader("⚡ 个股扫雷")
            with st.spinner('正在扫描股票风险...'):
                risk_check = QuantAlgo.check_stock_risks(symbol)
            
            # 显示风险等级
            risk_colors = {
                '低': '🟢',
                '中': '🟡',
                '高': '🔴',
                '未知': '⚪'
            }
            col_risk_level, col_risk_count = st.columns(2)
            with col_risk_level:
                st.metric("风险等级", f"{risk_colors.get(risk_check['风险等级'], '⚪')} {risk_check['风险等级']}")
            with col_risk_count:
                risk_count = len([r for r in risk_check['风险列表'] if not r.startswith('✅')])
                st.metric("风险项数", f"{risk_count} 项")
            
            # 显示详细风险列表
            if risk_check['风险列表']:
                for risk in risk_check['风险列表']:
                    if risk.startswith('🔴'):
                        st.error(risk)
                    elif risk.startswith('🟠'):
                        st.warning(risk)
                    elif risk.startswith('🟡'):
                        st.warning(risk)
                    elif risk.startswith('🟢'):
                        st.info(risk)
                    else:
                        st.success(risk)
            
            # 根据风险等级给出建议
            if risk_check['风险等级'] == '高':
                st.error("⚠️ 风险等级较高，建议谨慎操作或避开")
            elif risk_check['风险等级'] == '中':
                st.warning("⚠️ 风险等级中等，建议控制仓位")
            else:
                st.success("✅ 风险等级较低，可正常关注")

            # 技术指标详情
            st.subheader("📊 技术指标分析")
            st.caption("💡 点击上方「📖 技术指标解释」查看详细说明")
            
            col_macd, col_rsi, col_bb = st.columns(3)
            
            with col_macd:
                st.info("**MACD 指标**")
                st.write(f"MACD: {macd_data['MACD']}")
                st.write(f"信号线: {macd_data['Signal']}")
                st.write(f"柱状图: {macd_data['Histogram']}")
                st.write(f"趋势: {macd_data['Trend']}")
                if macd_data['Trend'] == "多头":
                    st.success("✅ 趋势向上，适合买入")
                else:
                    st.warning("⚠️ 趋势向下，注意风险")
            
            with col_rsi:
                st.info("**RSI 指标**")
                st.write(f"RSI: {rsi_data['RSI']}")
                st.write(f"信号: {rsi_data['Signal']}")
                if rsi_data['RSI'] > 70:
                    st.warning("⚠️ 超买区域（>70），价格偏高，考虑减仓")
                elif rsi_data['RSI'] < 30:
                    st.success("✅ 超卖区域（<30），价格偏低，考虑买入")
                else:
                    st.info("正常区间（30-70），继续持有")
            
            with col_bb:
                st.info("**布林带**")
                st.write(f"上轨: {bollinger_data['上轨']:.2f}")
                st.write(f"中轨: {bollinger_data['中轨']:.2f}")
                st.write(f"下轨: {bollinger_data['下轨']:.2f}")
                st.write(f"位置: {bollinger_data['当前位置']}%")
                st.write(f"解读: {bollinger_data['解读']}")
                if current_price > bollinger_data['上轨']:
                    st.warning("⚠️ 价格突破上轨，注意回调风险")
                elif current_price < bollinger_data['下轨']:
                    st.success("✅ 价格接近下轨，可能反弹")
                else:
                    st.info("价格在布林带内，正常波动")

            # 第二行：KDJ、成交量、资金流向
            col_kdj, col_vol, col_flow = st.columns(3)
            
            with col_kdj:
                st.info("**KDJ 指标**")
                st.write(f"K: {kdj_data['K']}")
                st.write(f"D: {kdj_data['D']}")
                st.write(f"J: {kdj_data['J']}")
                st.write(f"信号: {kdj_data['信号']}")
                if "金叉" in kdj_data['信号']:
                    st.success("✅ 金叉，买入信号")
                elif "死叉" in kdj_data['信号']:
                    st.warning("⚠️ 死叉，卖出信号")
                elif "超买" in kdj_data['信号']:
                    st.warning("⚠️ 超买，注意风险")
                elif "超卖" in kdj_data['信号']:
                    st.success("✅ 超卖，可能反弹")
            
            with col_vol:
                st.info("**成交量与换手率**")
                st.write(f"量比: {volume_data['量比']}")
                st.write(f"换手率: {turnover_data.get('换手率', 'N/A')}%")
                st.write(f"信号: {volume_data['信号']}")
                st.caption(volume_data['含义'])
                if volume_data['量比'] > 2:
                    st.warning("⚠️ 放量显著，关注主力动向")
                elif volume_data['量比'] < 0.5:
                    st.info("📉 缩量，观望为主")
            
            with col_flow:
                st.info("**资金流向（真实数据）**")
                
                # 添加CSS样式调整字体大小
                st.markdown("""
                <style>
                div[data-testid="stMetricValue"] {
                    font-size: 22px !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if money_flow_data['数据状态'] == '正常':
                    # 显示总流向
                    if money_flow_data['资金流向'] == "净流入":
                        st.success(f"✅ {money_flow_data['资金流向']}")
                    elif money_flow_data['资金流向'] == "净流出":
                        st.warning(f"⚠️ {money_flow_data['资金流向']}")
                    else:
                        st.info(f"📊 {money_flow_data['资金流向']}")
                    
                    st.caption(money_flow_data['说明'])
                    
                    # 显示主力资金
                    col_main, col_large, col_medium, col_small = st.columns(4)
                    
                    with col_main:
                        st.metric("主力净流入", format_amount(money_flow_data['主力净流入-净额']), 
                                 f"{money_flow_data['主力净流入-净占比']:.2f}%")
                    with col_large:
                        st.metric("超大单", format_amount(money_flow_data['超大单净流入-净额']),
                                 f"{money_flow_data['超大单净流入-净占比']:.2f}%")
                    with col_medium:
                        st.metric("大单", format_amount(money_flow_data['大单净流入-净额']),
                                 f"{money_flow_data['大单净流入-净占比']:.2f}%")
                    with col_small:
                        st.metric("小单", format_amount(money_flow_data['小单净流入-净额']),
                                 f"{money_flow_data['小单净流入-净占比']:.2f}%")
                    
                    # 资金分析
                    main_flow = money_flow_data['主力净流入-净额']
                    if abs(main_flow) > 10000000:  # 主力资金超过1000万
                        st.success("💰 主力资金大幅介入，值得关注！")
                    elif abs(main_flow) > 5000000:
                        st.info("📈 主力资金参与度较高")
                    elif abs(main_flow) > 1000000:
                        st.caption("💡 主力资金温和参与")
                    else:
                        st.caption("💡 主力资金参与度较低")
                    
                    # 散户资金分析
                    small_flow = money_flow_data['小单净流入-净额']
                    if small_flow > 0:
                        st.caption("👥 散户资金流入，跟风情绪浓厚")
                    elif small_flow < 0:
                        st.caption("👥 散户资金流出，情绪低迷")
                
                else:
                    st.error(f"❌ {money_flow_data['数据状态']}")
                    if '错误信息' in money_flow_data:
                        st.caption(money_flow_data['错误信息'])
                    else:
                        st.caption(money_flow_data['说明'])

            # 换手率和量比综合分析
            st.divider()
            st.subheader("📊 换手率与量比综合分析")
            
            if turnover_volume_analysis.get('分析状态') == '换手率数据缺失':
                st.error("❌ 换手率数据缺失，无法进行综合分析")
                if '说明' in turnover_data and turnover_data['说明']:
                    st.info(f"💡 {turnover_data['说明']}")
                    st.info("📌 提示：请选择更早的日期重新获取数据，系统会自动更新换手率信息")
            else:
                # 显示基本信息
                col_turnover, col_volume, col_risk = st.columns(3)
                
                with col_turnover:
                    st.metric("换手率", f"{turnover_volume_analysis['换手率']}%", 
                             turnover_volume_analysis['换手率等级'])
                    st.caption(turnover_volume_analysis['换手率说明'])
                
                with col_volume:
                    st.metric("量比", turnover_volume_analysis['量比'], 
                             turnover_volume_analysis['量比等级'])
                    st.caption(turnover_volume_analysis['量比说明'])
                
                with col_risk:
                    risk_colors = {
                        '低': '🟢',
                        '中等': '🟡',
                        '中等偏高': '🟠',
                        '高': '🔴'
                    }
                    st.metric("风险等级", 
                             f"{risk_colors.get(turnover_volume_analysis['风险等级'], '⚪')} {turnover_volume_analysis['风险等级']}")
                
                # 显示综合分析结果
                st.subheader("🔍 综合分析")
                for i, analysis in enumerate(turnover_volume_analysis['综合分析'], 1):
                    st.write(f"{i}. {analysis}")
                
                # 根据风险等级给出建议
                if turnover_volume_analysis['风险等级'] == '高':
                    st.warning("⚠️ 当前风险较高，建议谨慎操作，可考虑减仓或观望")
                elif turnover_volume_analysis['风险等级'] == '中等偏高':
                    st.info("💡 风险偏高，建议控制仓位，密切关注走势")
                elif turnover_volume_analysis['风险等级'] == '中等':
                    st.success("✅ 风险适中，可正常操作")
                else:
                    st.success("✅ 风险较低，适合稳健操作")

            # 形态识别提示
            st.divider()
            st.subheader("🎨 形态识别")
            
            # 双底/双顶
            if double_bottom['is_double_bottom']:
                st.success(double_bottom['message'])
            elif double_top['is_double_top']:
                st.warning(double_top['message'])
            
            # 头肩形态
            if head_shoulders['pattern'] == 'head_shoulders_top':
                st.error(head_shoulders['message'])
            elif head_shoulders['pattern'] == 'head_shoulders_bottom':
                st.success(head_shoulders['message'])

            # 个股操作预案
            st.divider()
            st.subheader("📋 个股操作预案")
            
            with st.spinner('正在生成操作预案...'):
                trading_plan = QuantAlgo.generate_trading_plan(df, symbol=symbol)
                
                if '错误' not in trading_plan:
                    # 显示操作建议
                    col1, col2, col3 = st.columns(3)
                    
                    # 根据操作建议设置颜色
                    if trading_plan['操作建议'] == '买入':
                        col1.metric("操作建议", trading_plan['操作建议'], delta="看多")
                        col1.markdown('<style>div[data-testid="stMetricValue"] {color: green;}</style>', unsafe_allow_html=True)
                    elif trading_plan['操作建议'] == '卖出':
                        col1.metric("操作建议", trading_plan['操作建议'], delta="看空")
                        col1.markdown('<style>div[data-testid="stMetricValue"] {color: red;}</style>', unsafe_allow_html=True)
                    else:
                        col1.metric("操作建议", trading_plan['操作建议'])
                    
                    col2.metric("当前价格", f"¥{trading_plan['当前价格']:.2f}")
                    
                    # 风险等级
                    risk_colors = {
                        '高': '🔴',
                        '中等': '🟡',
                        '低': '🟢'
                    }
                    col3.metric("风险等级", f"{risk_colors.get(trading_plan['风险等级'], '⚪')} {trading_plan['风险等级']}")
                    
                    # 显示买卖点
                    if trading_plan['买入点']:
                        col_buy, col_sell, col_stop, col_profit = st.columns(4)
                        col_buy.metric("买入点", f"¥{trading_plan['买入点']:.2f}")
                        col_sell.metric("卖出点", f"¥{trading_plan['卖出点']:.2f}" if trading_plan['卖出点'] else "-")
                        col_stop.metric("止损点", f"¥{trading_plan['止损点']:.2f}")
                        col_profit.metric("止盈点", f"¥{trading_plan['止盈点']:.2f}")
                    
                    # 显示持仓周期
                    st.info(f"📅 建议持仓周期：{trading_plan['持仓周期']}")
                    
                    # 显示分析依据
                    if trading_plan['分析依据']:
                        st.subheader("🔍 分析依据")
                        for i, signal in enumerate(trading_plan['分析依据'], 1):
                            signal_color = {
                                '强': '🔴',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            st.write(f"{i}. **{signal['指标']}**: {signal['信号']} ({signal_color.get(signal['强度'], '⚪')} 强度: {signal['强度']})")
                    
                    # 显示做T机会
                    if '做T机会' in trading_plan:
                        st.divider()
                        st.subheader("🎯 做T机会分析")
                        
                        t_data = trading_plan['做T机会']
                        t_col1, t_col2, t_col3 = st.columns(3)
                        
                        # 做T机会等级
                        t_col1.metric("做T机会", t_data['操作建议'], delta=f"评分: {t_data['做T评分']}")
                        
                        # 做T信号
                        if t_data['做T信号']:
                            t_col2.write("**做T信号**")
                            for signal in t_data['做T信号']:
                                t_col2.write(f"• {signal}")
                        
                        # 风险提示
                        t_col3.warning(t_data['风险提示'])
                        
                        # 做T点位
                        if t_data['做T买入点'] and t_data['做T卖出点']:
                            st.subheader("📍 做T参考点位")
                            st.info(f"💡 **买入点（低吸）**: ¥{t_data['做T买入点'][0]:.2f} / ¥{t_data['做T买入点'][1]:.2f} / ¥{t_data['做T买入点'][2]:.2f}")
                            st.info(f"💡 **卖出点（高抛）**: ¥{t_data['做T卖出点'][0]:.2f} / ¥{t_data['做T卖出点'][1]:.2f} / ¥{t_data['做T卖出点'][2]:.2f}")
                            st.caption("注：做T点位仅供参考，实际操作请结合实时行情和仓位管理")
                else:
                    st.error(f"❌ 生成操作预案失败: {trading_plan['错误']}")

            # K线图
            st.subheader("📊 K线图与支撑阻力位")
            fig = go.Figure(data=[go.Candlestick(x=df['date'],
                            open=df['open'], high=df['high'],
                            low=df['low'], close=df['close'], name='K线')])
            
            # 绘制阻力位（红色）
            for level in resistance_levels[:3]:  # 只显示最近的3个阻力位
                fig.add_hline(y=level, line_dash="dash", line_color="rgba(255, 0, 0, 0.6)", 
                              annotation_text=f"阻力 {level:.2f}")
            
            # 绘制支撑位（绿色）
            for level in support_levels[-3:]:  # 只显示最近的3个支撑位
                fig.add_hline(y=level, line_dash="dash", line_color="rgba(0, 255, 0, 0.6)", 
                              annotation_text=f"支撑 {level:.2f}")
            
            # 绘制箱体（如果存在）
            if box_pattern['is_box']:
                # 箱体上沿（黄色）
                fig.add_hline(y=box_pattern['box_high'], line_dash="solid", line_color="rgba(255, 193, 7, 0.8)", 
                              line_width=2, annotation_text=f"箱体上沿 {box_pattern['box_high']:.2f}")
                # 箱体下沿（黄色）
                fig.add_hline(y=box_pattern['box_low'], line_dash="solid", line_color="rgba(255, 193, 7, 0.8)", 
                              line_width=2, annotation_text=f"箱体下沿 {box_pattern['box_low']:.2f}")
                # 添加箱体背景
                fig.add_hrect(y0=box_pattern['box_low'], y1=box_pattern['box_high'], 
                             fillcolor="rgba(255, 193, 7, 0.1)", layer="below", line_width=0)
            
            # 绘制布林带
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['close'].rolling(20).mean() + df['close'].rolling(20).std() * 2,
                mode='lines',
                name='布林上轨',
                line=dict(color='rgba(0, 0, 255, 0.3)', width=1)
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['close'].rolling(20).mean() - df['close'].rolling(20).std() * 2,
                mode='lines',
                name='布林下轨',
                line=dict(color='rgba(0, 0, 255, 0.3)', width=1)
            ))
                
            fig.update_layout(xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)

            # 龙头战法分析
            st.divider()
            st.subheader("🔥 龙头战法分析")
            st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
            
            dragon_analysis = QuantAlgo.analyze_dragon_stock(df, current_price)
            
            if dragon_analysis.get('龙头评级'):
                # 显示龙头评级
                col_dragon_rating, col_dragon_score = st.columns(2)
                with col_dragon_rating:
                    st.metric("龙头评级", dragon_analysis['龙头评级'], delta=dragon_analysis['评级说明'])
                with col_dragon_score:
                    st.metric("评级得分", f"{dragon_analysis['评级得分']}/100")
                
                # 显示五个条件
                st.subheader("📋 龙头股五个条件")
                
                col_cond1, col_cond2 = st.columns(2)
                with col_cond1:
                    st.info("**条件1：涨停板**")
                    for desc in dragon_analysis['条件1_涨停板']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件1_涨停板']['得分']}/20")
                
                with col_cond2:
                    st.info("**条件2：价格**")
                    for desc in dragon_analysis['条件2_价格']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件2_价格']['得分']}/20")
                
                col_cond3, col_cond4 = st.columns(2)
                with col_cond3:
                    st.info("**条件3：成交量**")
                    for desc in dragon_analysis['条件3_成交量']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件3_成交量']['得分']}/20")
                
                with col_cond4:
                    st.info("**条件4：KDJ**")
                    for desc in dragon_analysis['条件4_KDJ']['说明']:
                        st.write(desc)
                    st.caption(f"得分: {dragon_analysis['条件4_KDJ']['得分']}/20")
                
                st.info("**条件5：换手率**")
                for desc in dragon_analysis['条件5_换手率']['说明']:
                    st.write(desc)
                st.caption(f"得分: {dragon_analysis['条件5_换手率']['得分']}/20")
                
                # 显示综合分析
                st.divider()
                st.subheader("🔍 综合分析")
                for i, analysis in enumerate(dragon_analysis['综合分析'], 1):
                    st.write(f"{i}. {analysis}")
                
                # 显示操作建议
                st.divider()
                st.subheader("💡 操作建议")
                for suggestion in dragon_analysis['操作建议']:
                    st.write(suggestion)
            else:
                st.error(f"❌ {dragon_analysis.get('评级得分', '无法分析')}")

            # 策略和AI分析
            col_strategy, col_ai = st.columns([1, 1])
            
            with col_strategy:
                st.subheader("🛠️ 网格交易策略")
                st.info("基于 ATR 波动率自适应计算：")
                st.table(pd.DataFrame([grid_plan]).T.rename(columns={0: '数值/建议'}))
            
            with col_ai:
                st.subheader("🤖 智能分析")
                if run_ai:
                    with st.spinner("正在智能分析..."):
                        # 准备技术数据
                        tech_data = {
                            'current_price': current_price,
                            'resistance_levels': resistance_levels[:3],
                            'support_levels': support_levels[-3:],
                            'atr': atr,
                            'macd': macd_data,
                            'rsi': rsi_data,
                            'bollinger': bollinger_data,
                            'kdj': kdj_data,
                            'volume': volume_data,
                            'money_flow': money_flow_data,
                            'box_pattern': box_pattern,
                            'patterns': {
                                'double_bottom': double_bottom,
                                'double_top': double_top,
                                'head_shoulders': head_shoulders
                            }
                        }
                        analysis = ai_agent.analyze_stock(symbol, round(change_pct, 2), tech_data)
                        st.success(analysis)
                else:
                    st.write("点击侧边栏的「🧠 智能分析」按钮，获取智能投资建议。")

with tab_backtest:
    st.subheader("🧪 网格策略回测")
    
    st.info("⚠️ 注意：回测结果仅供参考，不构成投资建议。实际交易中存在滑点、手续费等额外成本。")
    
    # 回测参数设置
    backtest_symbol = st.text_input("回测股票代码", value="600519")
    backtest_start = st.date_input("回测开始日期", pd.to_datetime("2023-01-01"))
    
    col_atr, col_ratio, col_cost = st.columns(3)
    with col_atr:
        bt_atr_mult = st.slider("ATR 倍数", 0.1, 2.0, 0.5, 0.1)
    with col_ratio:
        bt_grid_ratio = st.slider("网格比例", 0.05, 0.5, 0.1, 0.05)
    with col_cost:
        bt_cost = st.slider("交易手续费", 0.000, 0.01, 0.001, 0.001)
    
    if st.button("运行回测"):
        s_date_str = backtest_start.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在运行回测...'):
            df = db.get_history_data(backtest_symbol, start_date=s_date_str, end_date=e_date_str)
            
            if not df.empty and len(df) > 50:
                result = backtest_engine.run_grid_strategy_backtest(
                    df, 
                    atr_multiplier=bt_atr_mult, 
                    grid_ratio=bt_grid_ratio,
                    transaction_cost=bt_cost
                )
                
                # 显示回测报告
                report = backtest_engine.generate_backtest_report(result)
                st.markdown(report)
                
                # 显示交易记录
                if not result['交易记录'].empty:
                    st.subheader("📝 交易记录")
                    st.dataframe(result['交易记录'], use_container_width=True)
                
                # 显示资金曲线
                st.subheader("💰 资金曲线")
                # 简单的资金曲线可视化
                capital_curve = []
                running_capital = result['初始资金']
                capital_curve.append(running_capital)
                
                for _, trade in result['交易记录'].iterrows():
                    running_capital = trade['capital']
                    capital_curve.append(running_capital)
                
                fig_capital = go.Figure()
                fig_capital.add_trace(go.Scatter(
                    y=capital_curve,
                    mode='lines+markers',
                    name='资金曲线',
                    line=dict(color='blue', width=2)
                ))
                
                fig_capital.update_layout(
                    title="资金变化曲线",
                    xaxis_title="交易次数",
                    yaxis_title="资金（元）",
                    height=400
                )
                st.plotly_chart(fig_capital, use_container_width=True)
                
            else:
                st.error("数据不足，无法进行回测。请选择更早的日期或检查股票代码。")

with tab_compare:
    st.subheader("🔍 多股票技术指标对比")
    
    # 股票代码输入
    compare_symbols_input = st.text_input("输入要对比的股票代码（用逗号分隔）", 
                                         value="600519,000001,600036",
                                         help="例如：600519,000001,600036")
    
    compare_symbols = [s.strip() for s in compare_symbols_input.split(',') if s.strip()]
    
    if st.button("开始对比分析") and compare_symbols:
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        with st.spinner('正在分析多只股票...'):
            # 技术指标对比
            comparison_df = comparator.compare_stocks(compare_symbols, s_date_str, e_date_str)
            
            if not comparison_df.empty:
                st.dataframe(comparison_df, use_container_width=True)
                
                # 收益率对比图
                st.subheader("📈 收益率曲线对比")
                performance_df = comparator.get_performance_comparison(compare_symbols, s_date_str, e_date_str)
                
                if not performance_df.empty:
                    fig_perf = go.Figure()
                    
                    for symbol in performance_df.columns:
                        fig_perf.add_trace(go.Scatter(
                            x=performance_df.index,
                            y=performance_df[symbol],
                            mode='lines',
                            name=symbol
                        ))
                    
                    fig_perf.update_layout(
                        title="累计收益率对比",
                        xaxis_title="日期",
                        yaxis_title="累计收益率",
                        height=400
                    )
                    st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.warning("未能获取到有效的对比数据，请检查股票代码是否正确。")

with tab_sector:
    st.subheader("🔄 板块轮动分析")
    st.caption("实时监控各行业板块资金流向，发现热点板块")
    
    # 自动加载数据
    with st.spinner('正在获取板块轮动数据...'):
        sector_data = QuantAlgo.get_sector_rotation()
        
        if sector_data['数据状态'] == '正常':
            sectors = sector_data['板块列表']
            
            # 格式化数据用于显示
            display_sectors = []
            for sector in sectors:
                display_sectors.append({
                    '板块名称': sector['板块名称'],
                    '涨跌幅': sector['涨跌幅'],
                    '主力净流入': format_amount(sector['主力净流入']),
                    '主力净流入占比': sector['主力净流入占比']
                })
            
            # 显示板块资金流向表格
            st.dataframe(
                pd.DataFrame(display_sectors),
                column_config={
                    '板块名称': st.column_config.TextColumn('板块名称', width='medium'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '主力净流入': st.column_config.TextColumn('主力净流入', width='medium'),
                    '主力净流入占比': st.column_config.NumberColumn('净流入占比', format='%.2f%%')
                },
                use_container_width=True,
                hide_index=True
            )
            
            # 热点板块分析
            st.subheader("🔥 热点板块分析")
            hot_sectors = sorted(sectors, key=lambda x: x['主力净流入'], reverse=True)[:5]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("**资金流入最多的板块**")
                for i, sector in enumerate(hot_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            with col2:
                cold_sectors = sorted(sectors, key=lambda x: x['主力净流入'])[:5]
                st.warning("**资金流出最多的板块**")
                for i, sector in enumerate(cold_sectors, 1):
                    st.metric(f"{i}. {sector['板块名称']}", 
                            format_amount(sector['主力净流入']),
                            f"{sector['涨跌幅']:.2f}%")
            
            # 板块资金流向图
            st.subheader("📊 板块资金流向分布")
            fig_sector = go.Figure()
            
            fig_sector.add_trace(go.Bar(
                x=[s['板块名称'][:4] for s in sectors[:10]],  # 只显示前10个，名称截取
                y=[s['主力净流入'] for s in sectors[:10]],
                marker_color=['green' if s['主力净流入'] > 0 else 'red' for s in sectors[:10]]
            ))
            
            fig_sector.update_layout(
                title="前10大板块资金流向",
                xaxis_title="板块",
                yaxis_title="主力净流入（元）",
                height=400
            )
            st.plotly_chart(fig_sector, use_container_width=True)
        else:
            st.error(f"❌ {sector_data['数据状态']}")
            if '错误信息' in sector_data:
                st.caption(sector_data['错误信息'])

with tab_lhb:
    st.subheader("🏆 龙虎榜分析")
    st.caption("监控市场活跃股票和机构动向")
    
    # 日期选择
    lhb_date = st.date_input("选择日期", value=pd.Timestamp.now().date())
    
    # 自动加载数据
    with st.spinner('正在获取龙虎榜数据...'):
        date_str = lhb_date.strftime("%Y%m%d")
        lhb_data = QuantAlgo.get_lhb_data(date_str)
        
        if lhb_data['数据状态'] == '正常':
            stocks = lhb_data['股票列表']
            
            # 显示数据日期
            if '数据日期' in lhb_data:
                st.info(f"📅 数据日期：{lhb_data['数据日期']}")
            
            # 排序选项
            col_sort1, col_sort2 = st.columns(2)
            with col_sort1:
                sort_by = st.selectbox("排序方式", ["净买入额", "涨跌幅", "收盘价"])
            with col_sort2:
                sort_order = st.selectbox("排序顺序", ["降序", "升序"])
            
            # 排序
            reverse_order = (sort_order == "降序")
            if sort_by == "净买入额":
                stocks_sorted = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=reverse_order)
            elif sort_by == "涨跌幅":
                stocks_sorted = sorted(stocks, key=lambda x: x['涨跌幅'], reverse=reverse_order)
            else:  # 收盘价
                stocks_sorted = sorted(stocks, key=lambda x: x['收盘价'], reverse=reverse_order)
            
            # 格式化数据用于显示
            display_stocks = []
            for stock in stocks_sorted:
                display_stocks.append({
                    '代码': stock['代码'],
                    '名称': stock['名称'],
                    '收盘价': stock['收盘价'],
                    '涨跌幅': stock['涨跌幅'],
                    '龙虎榜净买入': format_amount(stock['龙虎榜净买入']),
                    '上榜原因': stock['上榜原因']
                })
            
            # 显示数据表格
            st.dataframe(
                pd.DataFrame(display_stocks),
                column_config={
                    '代码': st.column_config.TextColumn('代码', width='small'),
                    '名称': st.column_config.TextColumn('名称', width='medium'),
                    '收盘价': st.column_config.NumberColumn('收盘价', format='%.2f'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '龙虎榜净买入': st.column_config.TextColumn('净买入', width='medium'),
                    '上榜原因': st.column_config.TextColumn('上榜原因', width='large')
                },
                use_container_width=True,
                hide_index=True
            )
            
            # 龙虎榜净买入排行
            st.subheader("📈 龙虎榜净买入排行")
            top_stocks = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=True)[:10]
            
            for i, stock in enumerate(top_stocks, 1):
                with st.container():
                    cols = st.columns([1, 3, 2, 2, 3])
                    cols[0].write(f"**{i}**")
                    cols[1].write(f"**{stock['名称']}** ({stock['代码']})")
                    cols[2].metric("净买入", format_amount(stock['龙虎榜净买入']))
                    cols[3].metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                    cols[4].caption(stock['上榜原因'])
                    st.divider()
            
            # 龙虎榜解析
            st.divider()
            st.subheader("📊 龙虎榜深度解析")
            
            with st.spinner('正在分析龙虎榜数据...'):
                summary = QuantAlgo.analyze_lhb_summary()
                
                if summary['数据状态'] == '正常':
                    # 总体数据
                    col1, col2, col3 = st.columns(3)
                    col1.metric("上榜股票数量", f"{summary['上榜股票数量']} 只")
                    col2.metric("龙虎榜净买入总额", format_amount(summary['龙虎榜净买入总额']))
                    col3.metric("总成交额", format_amount(summary['总成交额']))
                    
                    # 上榜原因统计
                    if summary['上榜原因统计']:
                        st.subheader("🔍 上榜原因统计")
                        reason_df = pd.DataFrame([
                            {'上榜原因': reason, '数量': count}
                            for reason, count in summary['上榜原因统计'].items()
                        ])
                        st.dataframe(reason_df, use_container_width=True, hide_index=True)
                    
                    # 机构统计
                    if summary['机构统计'] is not None and not summary['机构统计'].empty:
                        st.subheader("🏢 机构席位统计")
                        st.dataframe(summary['机构统计'].head(10), use_container_width=True)
                    
                    # 活跃营业部
                    if summary['活跃营业部'] is not None and not summary['活跃营业部'].empty:
                        st.subheader("🏪 活跃营业部")
                        st.dataframe(summary['活跃营业部'].head(10), use_container_width=True)
                    
                    # 资金流向分析
                    st.subheader("💰 资金流向分析")
                    net_buy_ratio = summary['龙虎榜净买入总额'] / summary['总成交额'] * 100 if summary['总成交额'] > 0 else 0
                    
                    if net_buy_ratio > 5:
                        st.success(f"✅ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金积极介入")
                    elif net_buy_ratio > 0:
                        st.info(f"📊 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏多")
                    elif net_buy_ratio > -5:
                        st.warning(f"⚠️ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏空")
                    else:
                        st.error(f"❌ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金大幅流出")
                else:
                    st.error(f"❌ {summary['数据状态']}")
                    if '错误信息' in summary:
                        st.caption(summary['错误信息'])
        else:
            st.error(f"❌ {lhb_data['数据状态']}")
            if '错误信息' in lhb_data:
                st.caption(lhb_data['错误信息'])
            else:
                st.caption(lhb_data['说明'])
        
        # 龙虎榜质量分析
        st.divider()
        st.subheader("🎯 龙虎榜质量分析")
        st.caption("区分好榜和坏榜，推荐值得次日介入的股票")
        
        with st.spinner('正在分析龙虎榜质量...'):
            quality_analysis = QuantAlgo.analyze_lhb_quality()
            
            if quality_analysis['数据状态'] == '正常':
                stats = quality_analysis['统计']
                
                # 显示统计
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("优质榜", f"{stats['优质榜数量']} 只", delta="强烈推荐")
                col2.metric("良好榜", f"{stats['良好榜数量']} 只", delta="推荐关注")
                col3.metric("一般榜", f"{stats['劣质榜数量']} 只", delta="谨慎观望")
                col4.metric("总数", f"{stats['总数']} 只")
                
                # 推荐股票
                st.subheader("⭐ 推荐关注（优质榜）")
                recommended_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] >= 70]
                
                if recommended_stocks:
                    for stock in recommended_stocks:
                        with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("净买入", format_amount(stock['净买入']))
                            
                            st.write("**上榜原因：**", stock['上榜原因'])
                            st.write("**评分原因：**", "、".join(stock['评分原因']))
                            st.success(f"📈 推荐操作：{stock['推荐']}")
                else:
                    st.info("暂无优质榜单")
                
                # 良好榜
                if len(recommended_stocks) < 10:
                    st.subheader("🟡 良好榜（可关注）")
                    good_stocks = [s for s in quality_analysis['股票分析'] if 50 <= s['评分'] < 70]
                    
                    if good_stocks:
                        for stock in good_stocks[:5]:  # 只显示前5只
                            with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3 = st.columns(3)
                                col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("净买入", format_amount(stock['净买入']))
                                
                                st.write("**上榜原因：**", stock['上榜原因'])
                                st.write("**评分原因：**", "、".join(stock['评分原因']))
                                st.info(f"📊 推荐操作：{stock['推荐']}")
                
                # 劣质榜（可选显示）
                with st.expander("🔴 劣质榜（不建议介入）"):
                    poor_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] < 30]
                    if poor_stocks:
                        st.dataframe(
                            pd.DataFrame([
                                {
                                    '代码': s['代码'],
                                    '名称': s['名称'],
                                    '评分': s['评分'],
                                    '上榜原因': s['上榜原因'],
                                    '推荐': s['推荐']
                                }
                                for s in poor_stocks
                            ]),
                            use_container_width=True,
                            hide_index=True
                            )
                    else:
                        st.info("暂无劣质榜单")
                
                # 评分说明
                st.divider()
                st.caption("**评分说明：**")
                st.caption("- 净买入额（30分）：净买入>1亿得30分，>5000万得20分，>0得10分")
                st.caption("- 涨跌幅（20分）：3-7%得20分，7-10%得10分，>10%扣10分")
                st.caption("- 成交额（15分）：>5亿得15分，>2亿得10分，>1亿得5分")
                st.caption("- 上榜原因（20分）：机构买入等优质原因得20分，ST等劣质原因扣20分")
                st.caption("- 净买入占比（15分）：>10%得15分，>5%得10分，>0得5分")
                st.caption("- 优质榜（≥70分）：强烈推荐次日介入")
                st.caption("- 良好榜（50-69分）：推荐关注")
                st.caption("- 一般榜（30-49分）：谨慎观望")
                st.caption("- 劣质榜（<30分）：不建议介入")
            else:
                st.error(f"❌ {quality_analysis['数据状态']}")

with tab_dragon:
    st.subheader("🔥 龙头战法 - 捕捉潜在龙头股")
    st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
    
    st.info("""
    **龙头战法核心要点：**
    - 🎯 只做涨停板股票
    - 💰 优选低价股（≤10元）
    - 📊 关注攻击性放量
    - 📈 等待KDJ金叉
    - 🔄 换手率适中（5-15%）
    """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 100, 50, 10)
    with col_scan2:
        min_score = st.slider("最低评分门槛", 40, 80, 60, 5)
    with col_scan3:
        if st.button("🔍 开始扫描"):
            st.session_state.scan_dragon = True
            st.rerun()
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        with st.spinner('正在扫描市场中的潜在龙头股...'):
            scan_result = QuantAlgo.scan_dragon_stocks(limit=scan_limit, min_score=min_score)
        
        if scan_result['数据状态'] == '正常':
            st.success(f"✅ 扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只潜在龙头股")
            
            if scan_result['龙头股列表']:
                # 按评级分组显示
                strong_dragons = [s for s in scan_result['龙头股列表'] if s['评级得分'] >= 80]
                potential_dragons = [s for s in scan_result['龙头股列表'] if 60 <= s['评级得分'] < 80]
                weak_dragons = [s for s in scan_result['龙头股列表'] if 40 <= s['评级得分'] < 60]
                
                # 强龙头
                if strong_dragons:
                    st.divider()
                    st.subheader("🔥 强龙头（重点关注）")
                    for stock in strong_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("评级得分", f"{stock['评级得分']}/100")
                            
                            # 显示五个条件得分
                            st.write("**五个条件得分：**")
                            details = stock['详情']
                            st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/20")
                            st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
                            st.write(f"- 成交量: {details['条件3_成交量']['得分']}/20")
                            st.write(f"- KDJ: {details['条件4_KDJ']['得分']}/20")
                            st.write(f"- 换手率: {details['条件5_换手率']['得分']}/20")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in details['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"⭐ 添加到自选", key=f"add_dragon_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 潜力龙头
                if potential_dragons:
                    st.divider()
                    st.subheader("📈 潜力龙头（可关注）")
                    for stock in potential_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
                            col1, col2 = st.columns(2)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            
                            st.write(f"评级得分: {stock['评级得分']}/100")
                            st.info(f"评级说明: {stock['评级说明']}")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in stock['详情']['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"⭐ 添加到自选", key=f"add_potential_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 弱龙头
                if weak_dragons:
                    st.divider()
                    st.subheader("⚠️ 弱龙头（谨慎关注）")
                    df_weak = pd.DataFrame([
                        {
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评级得分': s['评级得分'],
                            '评级说明': s['评级说明']
                        }
                        for s in weak_dragons
                    ])
                    st.dataframe(df_weak, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ 未发现符合条件的龙头股")
                st.info("💡 提示：可以降低最低评分门槛或增加扫描数量")
        else:
            st.error(f"❌ {scan_result['数据状态']}")
            if '错误信息' in scan_result:
                st.caption(scan_result['错误信息'])
            if '说明' in scan_result:
                st.info(scan_result['说明'])
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
            - 低价股（≤10元）：20分
            - 适中价格（10-15元）：10分
            - 高价股（>15元）：0分
            - 高价股不具备炒作空间，只有低价股才能得到股民追捧
            
            **3. 成交量（20分）**
            - 攻击性放量（量比>2）：20分
            - 温和放量（量比1.5-2）：15分
            - 缩量或正常：0分
            - 龙头一般出现三日以上的攻击性放量特征
            
            **4. KDJ（20分）**
            - KDJ金叉：20分
            - KDJ低位（K<30）：10分
            - KDJ不在低位：0分
            - 日线、周线、月线KDJ同时低位金叉更安全
            
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
            - 如果跌幅超过10%，立即止损，不要找任何理由
            - 破止损的个股，不要做补仓动作
            - 补仓是实盘操作中最蠢的行为
            """)

with tab_auction:
    st.subheader("⚡ 集合竞价选股 - 捕捉开盘机会")
    st.caption("基于雪球集合竞价选股法：竞价看方向，弱转强战法，竞价扩散法")
    
    st.info("""
    **集合竞价选股核心要点：**
    - 🕐 关注9:20之后的竞价情况（不可撤单，真实反映资金博弈）
    - 📊 重点关注放量的股票（量比>1.5）
    - 🔄 竞价弱转强：烂板/炸板股次日竞价超预期
    - 📈 竞价扩散法：通过一字板强势股挖掘同题材概念股
    """)
    
    # 功能选择
    auction_mode = st.radio("选择功能", ["竞价选股扫描", "竞价弱转强检测", "竞价扩散法"], horizontal=True)
    
    if auction_mode == "竞价选股扫描":
        st.divider()
        st.subheader("🔍 竞价选股扫描")
        
        # 扫描参数
        col_scan1, col_scan2 = st.columns(2)
        with col_scan1:
            scan_limit = st.slider("扫描股票数量", 50, 200, 100, 10)
        with col_scan2:
            if st.button("🔍 开始扫描", key="scan_auction"):
                st.session_state.scan_auction = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_auction', False):
            with st.spinner('正在扫描集合竞价股票...'):
                scan_result = QuantAlgo.scan_auction_stocks(limit=scan_limit)
            
            if scan_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只竞价活跃股票")
                
                if scan_result['竞价股票列表']:
                    # 按评级分组显示
                    strong_stocks = [s for s in scan_result['竞价股票列表'] if s['评分'] >= 80]
                    active_stocks = [s for s in scan_result['竞价股票列表'] if 60 <= s['评分'] < 80]
                    normal_stocks = [s for s in scan_result['竞价股票列表'] if 40 <= s['评分'] < 60]
                    
                    # 强势股票
                    if strong_stocks:
                        st.divider()
                        st.subheader("🔥 强势股票（重点关注）")
                        for stock in strong_stocks:
                            with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("量比", stock['量比'])
                                col4.metric("换手率", f"{stock['换手率']:.2f}%")
                                
                                # 显示信号
                                st.write("**竞价信号：**")
                                for signal in stock['信号']:
                                    st.write(f"- {signal}")
                                
                                # 显示操作建议
                                st.info(f"**操作建议：** {stock['操作建议']}")
                                
                                # 弱转强标记
                                if stock['弱转强']:
                                    st.success("🔄 竞价弱转强！")
                                
                                # 添加到自选股按钮
                                if st.button(f"⭐ 添加到自选", key=f"add_auction_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                    
                    # 活跃股票
                    if active_stocks:
                        st.divider()
                        st.subheader("🟡 活跃股票（可关注）")
                        df_active = pd.DataFrame([
                            {
                                '代码': s['代码'],
                                '名称': s['名称'],
                                '最新价': f"¥{s['最新价']:.2f}",
                                '涨跌幅': f"{s['涨跌幅']:.2f}%",
                                '量比': s['量比'],
                                '换手率': f"{s['换手率']:.2f}%",
                                '评分': s['评分'],
                                '评级': s['评级']
                            }
                            for s in active_stocks
                        ])
                        st.dataframe(df_active, use_container_width=True, hide_index=True)
                    
                    # 一般股票
                    if normal_stocks:
                        st.divider()
                        st.subheader("🟢 一般股票（观望）")
                        df_normal = pd.DataFrame([
                            {
                                '代码': s['代码'],
                                '名称': s['名称'],
                                '最新价': f"¥{s['最新价']:.2f}",
                                '涨跌幅': f"{s['涨跌幅']:.2f}%",
                                '量比': s['量比'],
                                '评分': s['评分']
                            }
                            for s in normal_stocks
                        ])
                        st.dataframe(df_normal, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ 未发现符合条件的竞价股票")
                    st.info("💡 提示：当前市场可能没有明显的竞价异动")
            else:
                st.error(f"❌ {scan_result['数据状态']}")
                if '错误信息' in scan_result:
                    st.caption(scan_result['错误信息'])
                if '说明' in scan_result:
                    st.info(scan_result['说明'])
        else:
            st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的竞价活跃股票")
    
    elif auction_mode == "竞价弱转强检测":
        st.divider()
        st.subheader("🔄 竞价弱转强检测")
        
        st.info("""
        **竞价弱转强战法：**
        - 适用于烂板、炸板股次日竞价超预期的情况
        - 前一天烂板/炸板（弱势），次日竞价放量高开（超预期）
        - 说明有资金抢筹，值得重点关注
        """)
        
        # 股票选择
        col_stock1, col_stock2 = st.columns(2)
        with col_stock1:
            check_symbol = st.text_input("股票代码", placeholder="输入6位股票代码", help="例如：600519")
        with col_stock2:
            if st.button("🔍 检测弱转强", key="check_weak_to_strong"):
                if check_symbol:
                    st.session_state.check_symbol = check_symbol
                    st.session_state.check_weak_to_strong = True
                    st.rerun()
                else:
                    st.warning("请输入股票代码")
        
        # 执行检测
        if st.session_state.get('check_weak_to_strong', False) and st.session_state.get('check_symbol'):
            check_symbol = st.session_state.check_symbol
            
            with st.spinner(f'正在检测 {check_symbol} 的竞价弱转强情况...'):
                df = db.get_history_data(check_symbol)
                
                if not df.empty and len(df) > 5:
                    weak_to_strong_result = QuantAlgo.detect_auction_weak_to_strong(df, check_symbol)
                    
                    if weak_to_strong_result['检测状态'] == '正常':
                        st.success(f"✅ 检测完成！")
                        
                        stock_name = QuantAlgo.get_stock_name(check_symbol)
                        st.subheader(f"📊 {stock_name} ({check_symbol}) - 弱转强检测结果")
                        
                        # 显示基本信息
                        col1, col2, col3 = st.columns(3)
                        col1.metric("前一天类型", weak_to_strong_result.get('前一天类型', '-'))
                        col2.metric("昨日涨跌幅", f"{weak_to_strong_result.get('昨日涨跌幅', 0):.2f}%")
                        col3.metric("今日开盘涨跌幅", f"{weak_to_strong_result.get('今日开盘涨跌幅', 0):.2f}%")
                        
                        # 显示量比
                        st.metric("量比", weak_to_strong_result.get('量比', 0))
                        
                        # 显示评级
                        if weak_to_strong_result.get('是否弱转强'):
                            st.success(f"🔥 {weak_to_strong_result['评级']}")
                        else:
                            st.warning(f"⚠️ {weak_to_strong_result['评级']}")
                        
                        # 显示信号
                        st.divider()
                        st.subheader("📋 检测信号")
                        for signal in weak_to_strong_result.get('信号', []):
                            st.write(f"- {signal}")
                        
                        # 显示操作建议
                        st.divider()
                        st.info(f"**操作建议：** {weak_to_strong_result.get('操作建议', '')}")
                    else:
                        st.warning(f"⚠️ {weak_to_strong_result['检测状态']}")
                        if '说明' in weak_to_strong_result:
                            st.info(weak_to_strong_result['说明'])
                else:
                    st.error("❌ 无法获取股票数据")
                    st.info("💡 请检查股票代码是否正确")
        else:
            st.info("👆 输入股票代码并点击「检测弱转强」按钮")
    
    elif auction_mode == "竞价扩散法":
        st.divider()
        st.subheader("📈 竞价扩散法")
        
        st.info("""
        **竞价扩散法：**
        - 通过一字板强势股挖掘同题材概念股
        - 筛选首板、二板，且封单金额超过流通盘5%
        - 剔除热炒题材，保留新题材
        - 根据题材找出同概念股，关注未涨停但高开的股票
        """)
        
        # 扫描参数
        col_diff1, col_diff2 = st.columns(2)
        with col_diff1:
            diffusion_limit = st.slider("扫描股票数量", 20, 100, 50, 10)
        with col_diff2:
            if st.button("🔍 扫描一字板", key="scan_diffusion"):
                st.session_state.scan_diffusion = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_diffusion', False):
            with st.spinner('正在扫描强势一字板股票...'):
                diffusion_result = QuantAlgo.auction_diffusion_method(limit=diffusion_limit)
            
            if diffusion_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！发现 {len(diffusion_result['强势一字板股票'])} 只强势一字板股票")
                
                if diffusion_result['强势一字板股票']:
                    # 显示强势一字板股票
                    st.divider()
                    st.subheader("🔥 强势一字板股票")
                    
                    df_strong = pd.DataFrame(diffusion_result['强势一字板股票'])
                    df_strong['封单金额'] = df_strong['封单金额'].apply(lambda x: f"{x/10000:.2f}万" if x < 100000000 else f"{x/100000000:.2f}亿")
                    df_strong['流通市值'] = df_strong['流通市值'].apply(lambda x: f"{x/100000000:.2f}亿")
                    
                    st.dataframe(df_strong, use_container_width=True, hide_index=True)
                    
                    # 显示操作建议
                    st.divider()
                    st.subheader("💡 操作建议")
                    for i, suggestion in enumerate(diffusion_result['操作建议'], 1):
                        st.write(f"{i}. {suggestion}")
                    
                    # 说明
                    st.info(diffusion_result['说明'])
                else:
                    st.warning("⚠️ 未发现符合条件的强势一字板股票")
                    st.info("💡 提示：当前市场可能没有封单充足的一字板股票")
            else:
                st.error(f"❌ {diffusion_result['数据状态']}")
                if '错误信息' in diffusion_result:
                    st.caption(diffusion_result['错误信息'])
                if '说明' in diffusion_result:
                    st.info(diffusion_result['说明'])
        else:
            st.info("👆 点击「扫描一字板」按钮，系统将自动扫描强势一字板股票")
    
    # 显示集合竞价选股说明
    st.divider()
    st.subheader("📖 集合竞价选股详解")
    
    with st.expander("🕐 集合竞价规则"):
        st.markdown("""
        **时间规则：**
        
        **9:15 - 9:20：自由报价**
        - 既可以下单，也可以撤单
        - 可能存在诱多诱空，大资金在9:19分最后一秒撤单
        
        **9:20 - 9:25：不可撤单**
        - 可以下单，不能撤单
        - 真实显示当天该股在竞价期间资金的博弈情况
        - **重点关注这个时间段**
        
        **9:25 - 9:30：接受报价但不处理**
        - 系统接受报价，但不做处理
        - 等待正式开盘
        
        **成交原则：**
        - 最大成交量优先，决定当天的开盘价
        - 竞价异常（放量）的股票，基本都是大资金背后作为推手
        """)
    
    with st.expander("📊 集合竞价图形解读"):
        st.markdown("""
        **理想的竞价图形：**
        
        **1. 股价走势**
        - 集合竞价期间，股价逐步抬高为好
        - 最好的情况是最后时刻，股价被大单买入快速拉升
        
        **2. 成交量柱**
        - 柱子代表竞价的成交量
        - 量能最好是随着股价的抬升放大
        - 绿色代表向下的卖盘
        - 红色代表资金主动向上买入
        - 成交量逐渐放大，且红色柱子连续排列，较好
        
        **3. 诱空示例**
        - 大资金在竞价期间诱空，骗取散户筹码
        - 股价先拉升，然后在9:19分快速撤单，股价回落
        - 这种情况要警惕，不要盲目追高
        """)
    
    with st.expander("🔄 竞价弱转强战法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"弱"？**
        - 烂板：涨停板上抛压不断，持筹者不看好后续走势
        - 炸板：涨停板打开，板上介入的资金全部被套
        - 即使封板，第二天也很难有溢价
        
        **什么是"弱转强"？**
        - 前一天烂板或炸板（弱势）
        - 第二天竞价应该是没有溢价，以一种很弱的表现形式
        - **但是第二天开盘资金出现放量抢筹的情况**
        - 这就是超预期，超出市场预期
        
        **为什么有效？**
        - 烂板/炸板股，次日拉升起来压力非常大
        - 一般没有资金愿意去做多
        - 如果竞价直接放量高开，完全不惧前一天板上被套牢的资金
        - 说明有新资金强势介入，值得重点关注
        
        **操作要点：**
        - 关注前一天烂板或炸板的股票
        - 次日9:20之后观察竞价情况
        - 如果竞价放量高开（>2%），且量比>1.5，考虑参与
        - 设置好止损点，严格执行
        """)
    
    with st.expander("📈 竞价扩散法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"竞价扩散"？**
        - 通过对个股封单的观测，以及对个股属性的识别
        - 找到所对应的板块，提前预判当天资金的主攻方向
        - 通过竞价期间一字板的强势股去做挖掘
        - "扩散"到同题材概念还未涨停的个股
        
        **使用时间：**
        - 9:20 - 9:30之间（9:20之后不能撤单）
        
        **使用方法：**
        
        **1. 筛选一字涨停股票**
        - 9:20之后，对当天一字涨停的股票进行浏览
        - 选出首板股、二板股（首板股做参考最好）
        - 记录涨停板上的封单金额
        
        **2. 进一步筛选**
        - 首板股里面属于热炒题材的剔除
        - 必须是新题材
        - 一字板封单不足真实流通盘5%的剔除
        
        **3. 锁定题材**
        - 剩下的是"集合竞价强势涨停（一字板）的新题材"
        - 通过个股，找为什么当天他能一字板的原因
        - 迅速锁定题材
        
        **4. 挖掘同概念股**
        - 搜索同题材的概念股
        - 按涨幅排序（集合竞价的涨幅）
        - 把还未涨停的，但是高开的同概念其他股加入自选
        - 观察竞价是否有资金异动抢筹
        - 竞价后直接参与，或选择第一个上板的股去做打板
        
        **为什么有效？**
        - 很多股票开盘秒板，是因为竞价期间强势的一字板新题材获得了市场资金的认可
        - 其他聪明的大资金快速锁定相关概念的其他个股
        - 开盘后立即抢筹买入造成的
        - 我们跟着聪明资金走，"他们吃肉，我们喝汤"
        """)
