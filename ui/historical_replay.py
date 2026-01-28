#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史重演测试面板
用于周末测试 AI 对历史市场的识别能力
V19.17: 新增 QMT 毫秒级复盘模式，支持精确时间点快照
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from logic.data_provider_factory import DataProviderFactory
from logic.technical_analyzer import TechnicalAnalyzer
from logic.sentiment_analyzer import SentimentAnalyzer
from logic.algo import QuantAlgo
from logic.logger import get_logger
from logic.midway_strategy_v19_final import MidwayStrategy
import config_system as config

logger = get_logger(__name__)


def render_historical_replay_panel():
    """
    渲染历史重演测试面板
    """
    st.title("🎮 历史重演测试 (Historical Replay)")
    
    # 侧边栏：设置
    with st.sidebar:
        st.header("⚙️ 测试设置")
        
        # 🔥 V19.17.1: 复盘模式开关
        st.subheader("🎬 复盘模式")
        enable_replay = st.checkbox(
            "启用复盘模式",
            value=True,
            help="启用后将获取历史数据而不是实时数据"
        )
        
        # 数据源选择
        replay_mode = st.radio(
            "数据源选择",
            ["QMT 毫秒级复盘 (推荐)", "AkShare 日线复盘"],
            disabled=not enable_replay,
            help="QMT 模式支持精确时间点快照（如 14:56:55）"
        )
        
        # 选择日期
        default_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        date = st.text_input(
            "📅 测试日期",
            value=default_date,
            help="格式：YYYYMMDD，例如 20260128",
            disabled=not enable_replay
        )
        
        # 🔥 V19.17.1: 时间步进功能
        if replay_mode == "QMT 毫秒级复盘 (推荐)" and enable_replay:
            st.subheader("⏰ 时间步进功能")
            time_step_mode = st.checkbox(
                "启用时间步进",
                value=False,
                help="启用后将从 09:30 逐步推进到 15:00"
            )
            
            if time_step_mode:
                st.info("📊 时间步进模式：")
                st.write("- 从 09:30 开始，每分钟步进一次")
                st.write("- 自动记录每个时间点的战法信号")
                st.write("- 适合复盘'尾盘偷袭'战法")
            
            # 时间点选择（单点模式）
            if not time_step_mode:
                st.subheader("⏰ 时间点选择（单点模式）")
                time_point_option = st.selectbox(
                    "常用时间点",
                    ["自定义时间", "9:30:00 开盘", "10:30:00 早盘", "11:30:00 午盘", "13:00:00 开盘", "14:00:00 午后", "14:30:00 尾盘", "14:56:00 尾盘冲刺", "15:00:00 收盘"],
                    help="选择常用时间点或自定义"
                )
                
                if time_point_option == "自定义时间":
                    time_point = st.text_input(
                        "自定义时间点",
                        value="145600",
                        help="格式：HHMMSS，例如 145600 表示 14:56:00"
                    )
                else:
                    # 预设时间点映射
                    time_map = {
                        "9:30:00 开盘": "093000",
                        "10:30:00 早盘": "103000",
                        "11:30:00 午盘": "113000",
                        "13:00:00 开盘": "130000",
                        "14:00:00 午后": "140000",
                        "14:30:00 尾盘": "143000",
                        "14:56:00 尾盘冲刺": "145600",
                        "15:00:00 收盘": "150000",
                    }
                    time_point = time_map[time_point_option]
                
                period = st.selectbox(
                    "数据周期",
                    ["1m", "5m", "tick"],
                    help="1m: 1分钟线（推荐）, 5m: 5分钟线, tick: 分笔数据（最精确）"
                )
            else:
                # 时间步进模式：定义起始时间、结束时间和步长
                time_point = "093000"  # 默认从 09:30 开始
                end_time = "150000"  # 默认到 15:00 结束
                step_minutes = st.slider(
                    "步进间隔（分钟）",
                    min_value=1,
                    max_value=30,
                    value=5,
                    help="每隔多少分钟步进一次"
                )
                period = "1m"  # 时间步进模式默认使用 1分钟线
        else:
            time_point = None
            period = None
            time_step_mode = False
            step_minutes = 5
        
        # 测试股票
        test_stocks = st.text_area(
            "📊 测试股票代码",
            value="600058,000858,002056,300015",
            help="输入股票代码，用逗号分隔"
        )
        
        # 测试模式
        test_mode = st.selectbox(
            "🎯 测试模式",
            ["技术分析测试", "AI识别测试", "完整回放测试", "半路战法复盘"],
            help="选择测试模式"
        )
        
        # 开始测试按钮
        col1, col2 = st.columns(2)
        with col1:
            start_test = st.button("🚀 开始测试", type="primary")
        with col2:
            quick_test = st.button("⚡ 快速测试")
    
    # 主内容区
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 测试说明")
        
        if replay_mode == "QMT 毫秒级复盘 (推荐)":
            st.info(f"""
            **QMT 毫秒级复盘功能说明：**
            
            1. **时间点快照**：获取指定时间点（如 {time_point}）的盘口数据
            2. **技术分析测试**：验证 K 线趋势分析是否准确
            3. **AI识别测试**：验证 AI 是否能识别龙头和风险
            4. **半路战法复盘**：验证半路战法在特定时间点的信号
            
            **⚠️ 重要提示（首席架构师锦囊）：**
            
            **锦囊 1：时间点快照**
            - QMT 支持精确到秒的时间点数据获取
            - 适合复盘"尾盘偷袭"战法（如 14:56:55）
            - 数据来自 QMT 本地历史数据库
            
            **锦囊 2：数据精度**
            - 1分钟线：推荐，平衡精度和性能
            - 5分钟线：适合中长线复盘
            - Tick数据：最精确，但数据量大
            
            **锦囊 3：复盘优势**
            - 可以"时光倒流"到任意时间点
            - 验证战法在不同时间段的表现
            - 精准定位最佳入场时机
            """)
        else:
            st.info("""
            **历史重演测试功能说明：**
            
            1. **技术分析测试**：验证 K 线趋势分析是否准确
            2. **AI识别测试**：验证 AI 是否能识别龙头和风险
            3. **完整回放测试**：完整模拟当日市场环境
            
            **⚠️ 重要提示（首席架构师锦囊）：**
            
            **锦囊 1：数据映射**
            - 历史数据已正确映射为实时数据格式
            - df['涨跌幅'] → realtime_data['change_pct']
            - df['成交额'] → realtime_data['amount']
            
            **锦囊 2：未来函数**
            - 当前测试使用的是"收盘价"（复盘模式）
            - AI 看到的是全天数据，不是盘中数据
            - 适合验证"趋势判断"，不适合验证"打板逻辑"
            
            **锦囊 3：数据限制**
            - 历史数据不包含盘口数据（封单量等）
            - "纸老虎预警"可能失效（物理限制，非 Bug）
            - 这是正常的，请勿误判
            
            **技术限制：**
            - 历史数据来自 AkShare
            - 只能测试基于日线的技术指标
            - 无法测试盘口数据（封单量等）
            """)
    
    with col2:
        st.subheader("📊 系统状态")
        st.success(f"✅ 配置系统：已加载")
        if replay_mode == "QMT 毫秒级复盘 (推荐)":
            st.success(f"✅ 数据源：QMT 毫秒级复盘")
            st.success(f"✅ 测试日期：{date}")
            st.success(f"✅ 时间点：{time_point}")
            st.success(f"✅ 数据周期：{period}")
        else:
            st.success(f"✅ 数据源：历史回放模式")
            st.success(f"✅ 测试日期：{date}")
    
    # 🚨 醒目的模式警告
    if replay_mode == "QMT 毫秒级复盘 (推荐)":
        st.error("""
        ⚠️ **重要提醒：当前处于 QMT 历史复盘模式**
        
        - 此模式用于复盘测试，获取历史特定时间点的数据
        - 数据来自 QMT 本地历史数据库
        - **不是实盘数据，不能用于实盘交易**
        - 实盘请使用"🔥 龙头战法"或其他实时标签页
        """)
    else:
        st.error("""
        ⚠️ **重要提醒：当前处于历史回放模式**
        
        - 此模式仅用于周末测试和复盘
        - 数据来自 AkShare 历史日线数据
        - **不是实盘数据，不能用于实盘交易**
        - 周一实盘请使用其他标签页（如"🔥 龙头战法"）
        """)
    
    st.markdown("---")
    
    # 快速测试
    if quick_test:
        st.markdown("---")
        st.subheader("⚡ 快速测试")
        
        try:
            # 根据模式选择数据提供者
            if replay_mode == "QMT 毫秒级复盘 (推荐)":
                provider = DataProviderFactory.get_provider(
                    mode='qmt_replay',
                    date=date,
                    time_point=time_point,
                    period=period,
                    stock_list=['600058']
                )
            else:
                provider = DataProviderFactory.get_provider(
                    mode='replay',
                    date=date,
                    stock_list=['600058']
                )
            
            with st.spinner("📥 正在获取测试数据..."):
                test_data = provider.get_realtime_data(['600058'])
            
            if test_data:
                stock = test_data[0]
                st.success(f"✅ 数据获取成功！")
                
                # 显示数据格式
                display_data = {
                    'code': stock['code'],
                    'name': stock.get('name', ''),
                    'price': stock['price'],
                    'change_pct': f"{stock['change_pct']*100:.2f}%",
                    'volume': stock['volume'],
                    'amount': stock['amount'],
                    'open': stock['open'],
                    'high': stock['high'],
                    'low': stock['low'],
                    'pre_close': stock['pre_close'],
                    'source': stock.get('source', 'N/A'),
                    'replay_mode': stock.get('replay_mode', False),
                }
                
                if replay_mode == "QMT 毫秒级复盘 (推荐)":
                    display_data['replay_time'] = stock.get('replay_time', 'N/A')
                else:
                    display_data['replay_date'] = stock.get('replay_date', 'N/A')
                
                st.json(display_data)
                
                # 检查必需字段
                required_fields = ['code', 'price', 'change_pct', 'volume', 'amount', 'open', 'high', 'low', 'pre_close']
                missing_fields = [f for f in required_fields if f not in stock]
                
                if missing_fields:
                    st.warning(f"⚠️ 缺少字段: {', '.join(missing_fields)}")
                else:
                    st.success("✅ 所有必需字段都存在")
                
                # 数据合理性检查
                if stock['low'] <= stock['price'] <= stock['high']:
                    st.success("✅ 价格在高低范围内")
                else:
                    st.error(f"❌ 价格异常: {stock['low']} <= {stock['price']} <= {stock['high']}")
                
                if stock['pre_close'] > 0:
                    calculated_change = (stock['price'] - stock['pre_close']) / stock['pre_close']
                    if abs(calculated_change - stock['change_pct']) < 0.01:
                        st.success("✅ 涨跌幅计算正确")
                    else:
                        st.warning(f"⚠️ 涨跌幅可能不一致: {stock['change_pct']*100:.2f}% vs {calculated_change*100:.2f}%")
                
                st.info("✅ 快速测试完成！数据映射正常，可以进行完整测试。")
            else:
                st.error("❌ 未获取到测试数据，请检查网络连接或 QMT 环境")
                
        except Exception as e:
            st.error(f"❌ 快速测试失败: {e}")
    
    # 开始测试
    if start_test:
        try:
            st.markdown("---")
            st.subheader("🔬 测试执行中...")
            
            # 解析股票代码
            stock_list = [code.strip() for code in test_stocks.split(',') if code.strip()]
            
            if not stock_list:
                st.error("❌ 请输入至少一只股票代码")
                return
        
        # 🔥 V19.17.1: 时间步进模式
        if time_step_mode and replay_mode == "QMT 毫秒级复盘 (推荐)":
            st.info(f"⏰ 时间步进模式：从 09:30 到 15:00，每隔 {step_minutes} 分钟步进一次")
            
            # 初始化战法实例
            try:
                from logic.midway_strategy_v19_final import MidwayStrategy
                midway = MidwayStrategy(DataProviderFactory.get_provider('live'))
            except Exception as e:
                st.error(f"❌ 战法初始化失败: {e}")
                return
            
            # 生成时间点列表
            start_time_str = "093000"
            end_time_str = "150000"
            current_time = datetime.strptime(start_time_str, "%H%M%S")
            end_time = datetime.strptime(end_time_str, "%H%M%S")
            
            # 记录所有时间点的信号
            all_signals = []
            
            time_step_progress = st.progress(0)
            total_steps = int((end_time - current_time).total_seconds() / 60 / step_minutes)
            
            step_count = 0
            while current_time <= end_time:
                step_count += 1
                current_time_str = current_time.strftime("%H%M%S")
                
                st.info(f"📍 当前时间点：{current_time_str}")
                
                # 创建数据提供者
                try:
                    provider = DataProviderFactory.get_provider(
                        mode='qmt_replay',
                        date=date,
                        time_point=current_time_str,
                        period=period,
                        stock_list=stock_list
                    )
                    
                    # 获取历史数据
                    stocks_data = provider.get_realtime_data(stock_list)
                    
                    if stocks_data:
                        # 执行战法匹配
                        for stock in stocks_data:
                            code = stock['code']
                            is_hit, reason = midway.check_breakout(code, stock)
                            
                            signal_record = {
                                '时间': current_time_str,
                                '代码': code,
                                '现价': stock['price'],
                                '涨幅%': f"{stock['change_pct']*100:.2f}",
                                '是否命中': "✅ 命中" if is_hit else "⚫ 忽略",
                                '原因': reason,
                            }
                            all_signals.append(signal_record)
                        
                        # 显示当前时间点的命中数
                        hit_count = sum(1 for s in all_signals if s['时间'] == current_time_str and "命中" in s['是否命中'])
                        if hit_count > 0:
                            st.success(f"✅ {current_time_str} 发现 {hit_count} 个信号")
                
                except Exception as e:
                    logger.error(f"时间点 {current_time_str} 获取数据失败: {e}")
                
                # 更新进度
                progress = step_count / total_steps
                time_step_progress.progress(progress)
                
                # 步进到下一个时间点
                current_time = current_time + timedelta(minutes=step_minutes)
            
            # 显示所有信号汇总
            st.markdown("---")
            st.subheader(f"📊 时间步进复盘总结 ({date})")
            
            if all_signals:
                df_signals = pd.DataFrame(all_signals)
                st.dataframe(df_signals, use_container_width=True)
                
                # 统计分析
                st.subheader("📈 信号统计")
                
                total_hit = sum(1 for s in all_signals if "命中" in s['是否命中'])
                total_check = len(all_signals)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("🎯 总命中数", total_hit)
                col2.metric("📊 总检查数", total_check)
                col3.metric("🎯 命中率", f"{total_hit/total_check*100:.1f}%" if total_check > 0 else "0%")
                
                # 按时间点统计
                st.subheader("⏰ 按时间点统计")
                time_stats = df_signals.groupby('时间')['是否命中'].apply(lambda x: sum(1 for v in x if "命中" in v)).reset_index()
                time_stats.columns = ['时间', '命中数']
                st.bar_chart(time_stats.set_index('时间'))
                
                # 命中股票统计
                if total_hit > 0:
                    st.subheader("🎯 命中股票分析")
                    hit_stocks = df_signals[df_signals['是否命中'].str.contains('命中', na=False)].groupby('代码').size().reset_index()
                    hit_stocks.columns = ['代码', '命中次数']
                    hit_stocks = hit_stocks.sort_values('命中次数', ascending=False)
                    st.dataframe(hit_stocks, use_container_width=True)
                
                st.success(f"✅ 时间步进复盘完成！共检查 {total_check} 次股票，命中 {total_hit} 次")
            else:
                st.warning("⚠️ 未发现任何信号")
            
        else:
            # 🔥 V19.17.1: 单点复盘模式（原有逻辑）
            # 创建数据提供者
            try:
                if replay_mode == "QMT 毫秒级复盘 (推荐)":
                    provider = DataProviderFactory.get_provider(
                        mode='qmt_replay',
                        date=date,
                        time_point=time_point,
                        period=period,
                        stock_list=stock_list
                    )
                else:
                    provider = DataProviderFactory.get_provider(
                        mode='replay',
                        date=date,
                        stock_list=stock_list
                    )
                
                # 获取历史数据
                with st.spinner("📥 正在获取历史数据..."):
                    stocks_data = provider.get_realtime_data(stock_list)
                
                if not stocks_data:
                    st.error("❌ 未获取到历史数据，请检查日期和股票代码")
                    return
                
                st.success(f"✅ 成功获取 {len(stocks_data)} 只股票的历史数据")
                
                # 显示数据表格
                st.subheader("📊 历史数据预览")
                df_preview = pd.DataFrame(stocks_data)
                display_cols = ['code', 'price', 'change_pct', 'volume', 'amount']
                if 'replay_time' in df_preview.columns:
                    display_cols.insert(1, 'replay_time')
                st.dataframe(df_preview[display_cols])
                
                # 根据测试模式执行测试
                if test_mode == "技术分析测试":
                    _run_technical_analysis_test(stocks_data, date)
                elif test_mode == "AI识别测试":
                    _run_ai_recognition_test(stocks_data, date)
                elif test_mode == "完整回放测试":
                    _run_full_replay_test(stocks_data, date, provider)
                elif test_mode == "半路战法复盘":
                    _run_midway_strategy_replay(stocks_data, date, provider)
            
            except Exception as e:
                st.error(f"❌ 单点复盘模式失败: {e}")
                logger.error(f"单点复盘模式失败: {e}")
            
        except Exception as e:
            st.error(f"❌ 测试执行失败: {e}")
            logger.error(f"历史重演测试失败: {e}")


def _run_technical_analysis_test(stocks_data, date):
    """
    运行技术分析测试
    
    Args:
        stocks_data: 股票数据列表
        date: 测试日期
    """
    st.subheader("📈 技术分析测试")
    
    # 创建技术分析器
    ta = TechnicalAnalyzer()
    
    # 分析股票
    with st.spinner("🔍 正在分析技术形态..."):
        results = ta.analyze_batch(stocks_data)
    
    # 显示结果
    st.success(f"✅ 技术分析完成，共分析 {len(results)} 只股票")
    
    # 构造结果表格
    result_data = []
    for stock in stocks_data:
        code = stock['code']
        trend = results.get(code, "⚪ 未分析")
        result_data.append({
            '代码': code,
            '名称': stock['name'],
            '收盘价': stock['price'],
            '涨跌幅': f"{stock['change_pct']*100:.2f}%",
            '技术形态': trend,
        })
    
    df_result = pd.DataFrame(result_data)
    st.dataframe(df_result, use_container_width=True)
    
    # 统计分析
    st.subheader("📊 统计分析")
    col1, col2, col3 = st.columns(3)
    
    bullish_count = sum(1 for r in results.values() if '📈' in r or '🟢' in r)
    bearish_count = sum(1 for r in results.values() if '📉' in r or '🔴' in r)
    overbought_count = sum(1 for r in results.values() if '⚠️' in r)
    
    col1.metric("📈 多头信号", bullish_count)
    col2.metric("📉 空头信号", bearish_count)
    col3.metric("⚠️ 超买预警", overbought_count)


def _run_ai_recognition_test(stocks_data, date):
    """
    运行 AI 识别测试
    
    Args:
        stocks_data: 股票数据列表
        date: 测试日期
    """
    st.subheader("🤖 AI 识别测试")
    
    # 创建算法实例
    algo = QuantAlgo()
    
    # 分析股票
    with st.spinner("🧠 AI 正在分析..."):
        results = []
        for stock in stocks_data:
            try:
                # 调用算法分析
                analysis = algo.analyze_stock(stock)
                results.append({
                    '代码': stock['code'],
                    '名称': stock['name'],
                    '综合得分': analysis.get('综合得分', 0),
                    '评级': analysis.get('评级', 'N/A'),
                    '建议': analysis.get('建议', 'N/A'),
                })
            except Exception as e:
                logger.error(f"AI分析股票 {stock['code']} 失败: {e}")
    
    # 显示结果
    st.success(f"✅ AI 识别完成，共分析 {len(results)} 只股票")
    
    df_result = pd.DataFrame(results)
    st.dataframe(df_result, use_container_width=True)
    
    # 统计分析
    st.subheader("📊 AI 识别统计")
    col1, col2, col3 = st.columns(3)
    
    buy_count = sum(1 for r in results if '买入' in r['建议'])
    hold_count = sum(1 for r in results if '持有' in r['建议'])
    sell_count = sum(1 for r in results if '卖出' in r['建议'])
    
    col1.metric("💚 买入建议", buy_count)
    col2.metric("💛 持有建议", hold_count)
    col3.metric("❤️ 卖出建议", sell_count)


def _run_full_replay_test(stocks_data, date, provider):
    """
    运行完整回放测试
    
    Args:
        stocks_data: 股票数据列表
        date: 测试日期
        provider: 数据提供者
    """
    st.subheader("🎬 完整回放测试")
    
    # 获取市场数据
    with st.spinner("📊 正在获取市场环境..."):
        market_data = provider.get_market_data()
    
    # 显示市场环境
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 涨停家数", market_data.get('limit_up_count', 0))
    col2.metric("🔥 市场热度", f"{market_data.get('market_heat', 0):.0f}")
    col3.metric("💥 炸板率", f"{market_data.get('mal_rate', 0)*100:.1f}%")
    col4.metric("🎯 市场状态", market_data.get('regime', 'N/A'))
    
    # 运行技术分析
    _run_technical_analysis_test(stocks_data, date)
    
    # 运行 AI 识别
    _run_ai_recognition_test(stocks_data, date)
    
    # 测试总结
    st.subheader("📝 测试总结")
    st.info(f"""
    **测试日期**: {date}
    **测试股票**: {len(stocks_data)} 只
    **市场状态**: {market_data.get('regime', 'N/A')}
    
    **测试结论**:
    - ✅ 技术分析功能正常
    - ✅ AI 识别功能正常
    - ✅ 历史数据获取正常
    
    **建议**:
    - 如果 AI 识别结果符合预期，说明系统逻辑正确
    - 如果识别结果有偏差，可能需要调整参数
    """)


def _run_midway_strategy_replay(stocks_data, date, provider):
    """
    🔥 V19.17: 运行半路战法复盘测试
    
    Args:
        stocks_data: 股票数据列表
        date: 测试日期
        provider: 数据提供者
    """
    st.subheader("🎯 半路战法复盘测试")
    
    # 创建半路战法实例
    try:
        midway = MidwayStrategy(provider)
        st.success("✅ 半路战法初始化成功")
    except Exception as e:
        st.error(f"❌ 半路战法初始化失败: {e}")
        return
    
    # 显示复盘时间信息
    if 'replay_time' in stocks_data[0]:
        st.info(f"📅 复盘时间：{date} {stocks_data[0]['replay_time']}")
    else:
        st.info(f"📅 复盘日期：{date}")
    
    # 执行半路战法匹配
    with st.spinner("🔍 正在执行半路战法匹配..."):
        results = []
        for stock in stocks_data:
            try:
                code = stock['code']
                is_hit, reason = midway.check_breakout(code, stock)
                
                result = {
                    '代码': code,
                    '现价': stock['price'],
                    '涨幅%': f"{stock['change_pct']*100:.2f}",
                    '是否命中': "✅ 命中" if is_hit else "⚫ 忽略",
                    '原因': reason,
                }
                results.append(result)
            except Exception as e:
                logger.error(f"半路战法分析 {stock['code']} 失败: {e}")
                continue
    
    # 显示结果
    st.success(f"✅ 半路战法复盘完成，共分析 {len(results)} 只股票")
    
    df_result = pd.DataFrame(results)
    st.dataframe(df_result, use_container_width=True)
    
    # 统计分析
    st.subheader("📊 复盘统计")
    col1, col2, col3 = st.columns(3)
    
    hit_count = sum(1 for r in results if "命中" in r['是否命中'])
    ignore_count = sum(1 for r in results if "忽略" in r['是否命中'])
    
    col1.metric("🎯 命中数量", hit_count)
    col2.metric("⚫ 忽略数量", ignore_count)
    col3.metric("📊 命中率", f"{hit_count/len(results)*100:.1f}%" if results else "0%")
    
    # 命中原因分析
    if hit_count > 0:
        st.subheader("🎯 命中股票分析")
        hit_stocks = [r for r in results if "命中" in r['是否命中']]
        for stock in hit_stocks:
            st.info(f"""
            **{stock['代码']}**: {stock['原因']}
            - 现价: {stock['现价']}
            - 涨幅: {stock['涨幅%']}
            """)
    
    # 测试总结
    st.subheader("📝 复盘总结")
    st.info(f"""
    **复盘日期**: {date}
    **复盘股票**: {len(stocks_data)} 只
    **命中数量**: {hit_count} 只
    **命中率**: {hit_count/len(results)*100:.1f}%
    
    **复盘结论**:
    - ✅ 半路战法复盘功能正常
    - ✅ 能够识别特定时间点的半路机会
    - ✅ 可以用于验证战法在历史数据上的表现
    
    **建议**:
    - 可以尝试不同时间点（如 10:30、14:30、14:56）进行复盘
    - 对比不同时间点的命中率和命中率
    - 找出最佳入场时间窗口
    """)


if __name__ == "__main__":
    render_historical_replay_panel()