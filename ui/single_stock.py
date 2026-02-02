"""
单股分析模块

提供单只股票的详细分析功能
[V13 Iron Rule] 集成铁律监控和预警系统
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.data_manager import DataManager
from logic.algo import QuantAlgo
from logic.formatter import Formatter
from logic.logger import get_logger
from logic.iron_rule_monitor import IronRuleMonitor
from logic.iron_rule_alert import IronRuleAlert
from config_system import Config

logger = get_logger(__name__)


def format_amount(amount):
    """格式化金额显示"""
    abs_amount = abs(amount)
    if abs_amount >= 100000000:
        return f"{amount/100000000:.2f}亿"
    elif abs_amount >= 10000:
        return f"{amount/10000:.2f}万"
    else:
        return f"{amount:.0f}"


def render_single_stock_tab(db: DataManager, config: Config):
    """
    渲染单股分析标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("📊 单股分析")
    
    # 股票代码输入
    col_input, col_button = st.columns([3, 1])
    with col_input:
        symbol = st.text_input("股票代码", value="600519", help="输入6位股票代码，如600519", key="single_stock_symbol")
    with col_button:
        if st.button("🚀 开始分析", key="single_analyze"):
            st.session_state.analysis_symbol = symbol
    
    # 使用session state保存当前分析的股票
    if 'analysis_symbol' not in st.session_state:
        st.session_state.analysis_symbol = "600519"
    
    symbol = st.session_state.analysis_symbol
    
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
    
    # 获取股票数据
    with st.spinner(f'正在获取 {symbol} 数据...'):
        df =history_db.get_history_data(symbol) 
    
    # 获取实时数据（带缓存，60秒内直接使用缓存）
    realtime_data = db.get_realtime_data(symbol)
    
    if not df.empty and len(df) > 30:
        # 优先使用实时数据
        if realtime_data:
            current_price = realtime_data['price']
            change_pct = realtime_data['change_percent']
            st.success(f"实时数据已更新 ({realtime_data['timestamp']})")
        else:
            current_price = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close']
            # 防止除以零
            if prev_close != 0:
                change_pct = (current_price - prev_close) / prev_close * 100
            else:
                change_pct = 0.0
            st.info("使用历史数据（实时数据获取失败）")
        
        # 计算技术指标
        atr = QuantAlgo.calculate_atr(df)
        macd_data = QuantAlgo.calculate_macd(df)
        rsi_data = QuantAlgo.calculate_rsi(df)
        bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
        kdj_data = QuantAlgo.calculate_kdj(df)
        
        # 显示基本信息
        stock_name = QuantAlgo.get_stock_name(symbol)
        st.markdown(f"### {stock_name} ({symbol})")
        
        # [V13 Iron Rule] 铁律状态显示
        st.markdown("---")
        st.markdown("### 🛡️ [V13 Iron Rule] 铁律状态")
        
        try:
            # 初始化铁律监控和预警系统
            iron_monitor = IronRuleMonitor()
            iron_alert = IronRuleAlert()
            
            # 获取铁律状态
            iron_status = iron_monitor.get_stock_iron_status(symbol)
            
            # 显示铁律状态
            col_lock, col_warning, col_recommendation = st.columns(3)
            
            with col_lock:
                if iron_status['is_locked']:
                    st.metric(
                        "铁律状态",
                        "🔒 已锁定",
                        delta=f"{iron_status['lock_reason']}",
                        delta_color="inverse"
                    )
                else:
                    st.metric(
                        "铁律状态",
                        "✅ 正常",
                        delta="未触发铁律",
                        delta_color="normal"
                    )
            
            with col_warning:
                warning_level = iron_status['warning_level']
                if warning_level == 0:
                    warning_text = "正常"
                    warning_emoji = "✅"
                elif warning_level == 1:
                    warning_text = "预警"
                    warning_emoji = "⚡"
                elif warning_level == 2:
                    warning_text = "危险"
                    warning_emoji = "⚠️"
                else:
                    warning_text = "熔断"
                    warning_emoji = "🚨"
                
                st.metric(
                    "预警级别",
                    f"{warning_emoji} {warning_text}",
                    delta=f"DDE: {iron_status['dde_net_flow']:.2f}亿",
                    delta_color="inverse" if warning_level >= 2 else "normal"
                )
            
            with col_recommendation:
                st.metric(
                    "操作建议",
                    iron_status['recommendation'],
                    delta=iron_status['logic_status'],
                    delta_color="inverse" if iron_status['warning_level'] >= 2 else "normal"
                )
            
            # 显示预警消息
            if iron_status['warning_messages']:
                st.warning("⚠️ 预警消息：")
                for message in iron_status['warning_messages']:
                    st.markdown(f"  - {message}")
            
            # 显示新闻关键词
            if iron_status['news_keywords']:
                st.info(f"📰 新闻关键词：{', '.join(iron_status['news_keywords'])}")
            
            # 显示铁律规则说明
            with st.expander("📖 铁律规则说明"):
                st.markdown("""
                **V13 Iron Rule 核心原则：**
                
                1. **逻辑证伪 + 资金背离 = 永久熔断**
                   - 如果核心利好逻辑被官方证伪（澄清、监管函、风险提示等）
                   - 且 DDE/主力资金大幅流出（净额 < -1亿）
                   - 则触发铁律，该股票被锁定24小时，禁止买入
                
                2. **物理阉割亏损加仓**
                   - 浮亏超过 -3%：禁止加仓，只准割肉
                   - 浮亏超过 -8%：强制止损，立即平仓
                
                3. **战前三问审计**
                   - 核心利好逻辑是否依然成立？
                   - 盘中DDE/主力大单流出是否处于可控红线内？
                   - 是否坚决执行-3%禁止补仓、-8%物理止损？
                """)
            
            # 显示监控历史
            with st.expander("📊 铁律监控历史（最近7天）"):
                monitor_history = iron_monitor.get_monitor_history(symbol, days=7)
                if monitor_history:
                    history_df = pd.DataFrame(monitor_history)
                    st.dataframe(
                        history_df[['timestamp', 'warning_level', 'dde_net_flow', 'logic_status', 'recommendation']].rename(columns={
                            'timestamp': '时间',
                            'warning_level': '预警级别',
                            'dde_net_flow': 'DDE净额(亿)',
                            'logic_status': '逻辑状态',
                            'recommendation': '建议操作'
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("暂无监控历史")
            
        except Exception as e:
            logger.error(f"获取铁律状态失败: {e}")
            st.error(f"获取铁律状态失败: {e}")
        
        st.markdown("---")
        
        # [V13.1 Reality Priority] 事实一票否决制信号生成
        st.markdown("### 🎯 [V13.1 Reality Priority] 事实一票否决制")
        
        try:
            from logic.signal_generator import SignalGenerator
            
            # 获取V13.1信号生成器实例
            signal_gen = SignalGenerator()
            
            # 获取资金流向和流通市值
            capital_flow, market_cap = signal_gen.get_capital_flow(symbol, db)
            
            # 获取趋势状态
            trend_status = signal_gen.get_trend_status(df)
            
            # 模拟AI叙事分数（实际应该从LLM接口获取）
            ai_score = 75  # 默认分数
            
            # 计算最终信号
            signal_result = signal_gen.calculate_final_signal(
                stock_code=symbol,
                ai_narrative_score=ai_score,
                capital_flow_data=capital_flow,
                trend_status=trend_status,
                circulating_market_cap=market_cap
            )
            
            # 显示V13.1信号
            col_signal, col_score, col_risk = st.columns(3)
            
            with col_signal:
                signal_emoji = "🟢" if signal_result['signal'] == 'BUY' else "🔴" if signal_result['signal'] == 'SELL' else "🟡"
                st.metric(
                    "最终信号",
                    f"{signal_emoji} {signal_result['signal']}",
                    delta="事实优先" if signal_result['fact_veto'] else "综合评分",
                    delta_color="inverse" if signal_result['signal'] == 'SELL' else "normal"
                )
            
            with col_score:
                st.metric(
                    "最终评分",
                    f"{signal_result['final_score']:.1f}",
                    delta=f"AI基准: {ai_score}",
                    delta_color="normal" if signal_result['final_score'] >= 85 else "inverse"
                )
            
            with col_risk:
                risk_emoji = "🟢" if signal_result['risk_level'] == 'LOW' else "🟡" if signal_result['risk_level'] == 'MEDIUM' else "🔴"
                st.metric(
                    "风险等级",
                    f"{risk_emoji} {signal_result['risk_level']}",
                    delta=signal_result['reason'],
                    delta_color="inverse" if signal_result['risk_level'] == 'HIGH' else "normal"
                )
            
            # 显示一级事实
            st.markdown("#### 📊 一级事实（物理定律）")
            col_capital, col_trend, col_market = st.columns(3)
            
            with col_capital:
                capital_emoji = "🟢" if capital_flow > 0 else "🔴"
                st.metric(
                    "资金流向",
                    f"{capital_emoji} {format_amount(capital_flow)}",
                    delta="流入" if capital_flow > 0 else "流出",
                    delta_color="normal" if capital_flow > 0 else "inverse"
                )
            
            with col_trend:
                trend_emoji = "📈" if trend_status == 'UP' else "📉" if trend_status == 'DOWN' else "➡️"
                st.metric(
                    "价格趋势",
                    f"{trend_emoji} {trend_status}",
                    delta="多头" if trend_status == 'UP' else "空头" if trend_status == 'DOWN' else "震荡",
                    delta_color="normal" if trend_status == 'UP' else "inverse" if trend_status == 'DOWN' else "off"
                )
            
            with col_market:
                st.metric(
                    "流通市值",
                    format_amount(market_cap),
                    delta=f"占盘比例: {capital_flow/market_cap*100:.2f}%" if market_cap > 0 else "N/A",
                    delta_color="inverse" if capital_flow < 0 and market_cap > 0 else "normal"
                )
            
            # 显示信号生成逻辑说明
            with st.expander("📖 V13.1 信号生成逻辑说明"):
                st.markdown("""
                **V13.1 Reality Priority 核心原则：**
                
                **一级事实（物理定律） > 二级观点（AI分析）**
                
                1. **动态熔断机制：**
                   - **绝对阈值**：资金净流出 > 5000万 → 强制 SELL
                   - **相对阈值**：资金净流出 / 流通市值 < -1% → 强制 SELL
                   - **趋势熔断**：趋势 = DOWN → 强制 WAIT（不接飞刀）
                
                2. **背离识别（V13.1新增）：**
                   - 如果趋势 = UP 但资金流出 → 识别为"诱多"
                   - AI分数打折到 0.4（极度保守）
                
                3. **共振奖励：**
                   - 资金流入 + 趋势向上 → AI分数 × 1.2（完美共振）
                   - 资金流入 + 趋势震荡 → AI分数 × 0.9（潜伏观察）
                
                4. **最终裁决：**
                   - 评分 ≥ 85 → BUY
                   - 评分 < 85 → WAIT
                
                **禁止辩证：** 严禁"虽然资金流出，但利好极大，所以买入"的逻辑
                """)
            
            # 如果触发事实熔断，显示警告
            if signal_result['fact_veto']:
                st.error(f"🚨 [事实熔断] {signal_result['reason']}")
                st.warning("一级事实为负，AI叙事无效化，建议立即执行相应操作！")
            
        except Exception as e:
            logger.error(f"获取V13.1信号失败: {e}")
            st.error(f"获取V13.1信号失败: {e}")
        
        st.markdown("---")
        
        # 价格信息
        col_price, col_change, col_atr = st.columns(3)
        with col_price:
            st.metric("最新价格", f"¥{current_price:.2f}")
        with col_change:
            color = "🔴" if change_pct > 0 else "🟢"
            st.metric("涨跌幅", f"{color} {change_pct:+.2f}%")
        with col_atr:
            st.metric("ATR 波动率", f"{atr:.2f}")
        
        # 技术指标分析
        st.markdown("---")
        st.subheader("📈 技术指标分析")
        
        # MACD
        col_macd, col_rsi, col_kdj = st.columns(3)
        with col_macd:
            # macd_data是字典，直接访问值
            macd_value = float(macd_data['MACD'])
            signal_value = float(macd_data['Signal'])
            
            macd_status = "看涨" if macd_value > signal_value else "看跌"
            st.metric("MACD", f"{macd_value:.2f}")
            st.caption(f"信号线: {signal_value:.2f} | {macd_status}")
        
        with col_rsi:
            # rsi_data是字典
            rsi_value = float(rsi_data['RSI'])
            
            if rsi_value > 70:
                rsi_status = "超买"
            elif rsi_value < 30:
                rsi_status = "超卖"
            else:
                rsi_status = "正常"
            st.metric("RSI", f"{rsi_value:.2f}")
            st.caption(rsi_status)
        
        with col_kdj:
            # kdj_data是字典
            k_value = float(kdj_data['K'])
            d_value = float(kdj_data['D'])
            j_value = float(kdj_data['J'])
            
            kdj_status = "金叉" if k_value > d_value else "死叉"
            st.metric("KDJ", f"K:{k_value:.2f} D:{d_value:.2f}")
            st.caption(f"J:{j_value:.2f} | {kdj_status}")
        
        # 布林带
        st.markdown("---")
        st.subheader("📊 布林带分析")
        if isinstance(bollinger_data, dict):
            col_upper, col_middle, col_lower = st.columns(3)
            with col_upper:
                st.metric("上轨", f"¥{float(bollinger_data['上轨']):.2f}")
            with col_middle:
                st.metric("中轨", f"¥{float(bollinger_data['中轨']):.2f}")
            with col_lower:
                st.metric("下轨", f"¥{float(bollinger_data['下轨']):.2f}")
            
            # 显示当前位置
            st.caption(f"当前位置: {bollinger_data['当前位置']}% - {bollinger_data['解读']}")
        
        # 价格走势图
        st.markdown("---")
        st.subheader("📈 价格走势")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线'
        ))
        
        # 添加布林带
        if isinstance(bollinger_data, dict):
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[float(bollinger_data['上轨'])] * len(df),
                name='上轨',
                line=dict(color='rgba(255,0,0,0.5)')
            ))
            fig.add_trace(go.Scatter(
                x=df.index,
                y=[float(bollinger_data['下轨'])] * len(df),
                name='下轨',
                line=dict(color='rgba(0,255,0,0.5)')
            ))
        
        fig.update_layout(
            title=f"{stock_name} 价格走势",
            xaxis_title="日期",
            yaxis_title="价格",
            height=400
        )
        st.plotly_chart(fig, width="stretch")
        
        # 操作建议
        st.markdown("---")
        st.subheader("💡 操作建议")
        
        suggestions = []
        
        # [V13 Iron Rule] 铁律优先检查
        try:
            iron_monitor = IronRuleMonitor()
            iron_status = iron_monitor.get_stock_iron_status(symbol)
            
            # 如果铁律锁定或熔断，优先显示铁律建议
            if iron_status['is_locked'] or iron_status['warning_level'] >= 3:
                st.error(f"🚨 [V13 Iron Rule] {iron_status['recommendation']}")
                st.warning("铁律优先：禁止任何买入操作，建议立即清仓或观望")
                suggestions.append(f"铁律锁定：{iron_status['lock_reason']}")
            elif iron_status['warning_level'] >= 2:
                st.warning(f"⚠️ [V13 Iron Rule] {iron_status['recommendation']}")
                suggestions.append(f"铁律预警：{iron_status['warning_messages'][0] if iron_status['warning_messages'] else '接近熔断阈值'}")
        except Exception as e:
            logger.error(f"获取铁律状态失败: {e}")
        
        # MACD建议
        if macd_value > signal_value:
            suggestions.append("MACD金叉，趋势向上")
        else:
            suggestions.append("MACD死叉，趋势向下")
        
        # RSI建议
        if rsi_value > 70:
            suggestions.append("RSI超买，注意风险")
        elif rsi_value < 30:
            suggestions.append("RSI超卖，可能反弹")
        
        # KDJ建议
        if k_value > d_value and j_value > 0:
            suggestions.append("KDJ金叉，买入信号")
        elif k_value < d_value and j_value < 0:
            suggestions.append("KDJ死叉，卖出信号")
        
        # 布林带建议
        if isinstance(bollinger_data, dict):
            if current_price > float(bollinger_data['上轨']):
                suggestions.append("突破上轨，注意回调")
            elif current_price < float(bollinger_data['下轨']):
                suggestions.append("跌破下轨，可能反弹")
        
        if suggestions:
            for suggestion in suggestions:
                st.write(suggestion)
        else:
            st.info("暂无明显信号，建议观望")
        
        # 添加到自选股按钮
        if st.button(f"添加 {stock_name} 到自选股", key=f"add_{symbol}"):
            watchlist = config.get('watchlist', [])
            if symbol not in watchlist:
                watchlist.append(symbol)
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock_name} ({symbol}) 到自选股")
            else:
                st.info(f"{stock_name} ({symbol}) 已在自选股中")
    else:
        st.warning("数据不足,无法分析")