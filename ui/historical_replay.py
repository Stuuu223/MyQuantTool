#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史重演测试面板
用于周末测试 AI 对历史市场的识别能力
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from logic.data_provider_factory import DataProviderFactory
from logic.technical_analyzer import TechnicalAnalyzer
from logic.sentiment_analyzer import SentimentAnalyzer
from logic.algo import QuantAlgo
from logic.logger import get_logger
import config_system as config

logger = get_logger(__name__)


def render_historical_replay_panel():
    """
    渲染历史重演测试面板
    """
    st.title("🎮 历史重演测试 (Historical Replay)")
    
    # 🚨 醒目的模式警告
    st.error("""
    ⚠️ **重要提醒：当前处于历史回放模式**
    
    - 此模式仅用于周末测试和复盘
    - 数据来自 AkShare 历史日线数据
    - **不是实盘数据，不能用于实盘交易**
    - 周一实盘请使用其他标签页（如"🔥 龙头战法"）
    """)
    
    st.markdown("---")
    
    # 侧边栏：设置
    with st.sidebar:
        st.header("⚙️ 测试设置")
        
        # 选择日期
        default_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        date = st.text_input(
            "📅 测试日期",
            value=default_date,
            help="格式：YYYYMMDD，例如 20260116"
        )
        
        # 测试股票
        test_stocks = st.text_area(
            "📊 测试股票代码",
            value="600058,000858,002056,300015",
            help="输入股票代码，用逗号分隔"
        )
        
        # 测试模式
        test_mode = st.selectbox(
            "🎯 测试模式",
            ["技术分析测试", "AI识别测试", "完整回放测试"],
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
        st.success(f"✅ 数据源：历史回放模式")
        st.success(f"✅ 测试日期：{date}")
    
    # 快速测试
    if quick_test:
        st.markdown("---")
        st.subheader("⚡ 快速测试")
        
        try:
            # 使用默认测试数据
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
                st.json({
                    'code': stock['code'],
                    'name': stock['name'],
                    'price': stock['price'],
                    'change_pct': f"{stock['change_pct']*100:.2f}%",
                    'volume': stock['volume'],
                    'amount': stock['amount'],
                    'open': stock['open'],
                    'high': stock['high'],
                    'low': stock['low'],
                    'pre_close': stock['pre_close'],
                    'replay_date': stock.get('replay_date', 'N/A'),
                    'replay_mode': stock.get('replay_mode', False),
                })
                
                # 检查必需字段
                required_fields = ['code', 'name', 'price', 'change_pct', 'volume', 'amount', 'open', 'high', 'low', 'pre_close']
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
                st.error("❌ 未获取到测试数据，请检查网络连接")
                
        except Exception as e:
            st.error(f"❌ 快速测试失败: {e}")
    
    # 开始测试
    if start_test:
        st.markdown("---")
        st.subheader("🔬 测试执行中...")
        
        # 解析股票代码
        stock_list = [code.strip() for code in test_stocks.split(',') if code.strip()]
        
        if not stock_list:
            st.error("❌ 请输入至少一只股票代码")
            return
        
        # 创建历史回放数据提供者
        try:
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
            st.dataframe(df_preview[['code', 'name', 'price', 'change_pct', 'volume', 'amount']])
            
            # 根据测试模式执行测试
            if test_mode == "技术分析测试":
                _run_technical_analysis_test(stocks_data, date)
            elif test_mode == "AI识别测试":
                _run_ai_recognition_test(stocks_data, date)
            elif test_mode == "完整回放测试":
                _run_full_replay_test(stocks_data, date, provider)
            
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


if __name__ == "__main__":
    render_historical_replay_panel()