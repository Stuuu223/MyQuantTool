# =============== 🚨 必须放在最第一行：强制直连 ===============
import os
import sys

# 🚀 [最高优先级] 强杀代理：必须在 import 其他库之前执行！
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(key, None)
os.environ['NO_PROXY'] = '*'
print("🛡️ [System] 代理已强制清除，启动直连模式...")
# ==========================================================

import streamlit as st
import pandas as pd
import time
from logic.logger import get_logger
from logic.data_source_manager import DataSourceManager
from logic.data_maintenance import DataMaintenance

logger = get_logger(__name__)

# --- 页面配置 ---
st.set_page_config(
    page_title="MyQuantTool V19.11",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    st.sidebar.title("🚀 量化指挥中心 V19.11")
    
    # --- 1. 自动维护 (启动时清理旧文件) ---
    try:
        # 清理 3 天前的 CSV，防止硬盘爆炸
        DataMaintenance.clean_old_files("data/scan_results", days_to_keep=3)
        logger.info("✅ 自动维护：旧数据清理完成")
    except Exception as e:
        logger.warning(f"⚠️ 自动维护失败: {e}")
    
    # --- 2. 侧边栏菜单 ---
    app_mode = st.sidebar.radio(
        "选择功能模块",
        [
            "🏠 仪表盘 (Dashboard)",
            "🔥 交易策略",
            "📊 市场情绪",
            "💼 交易执行",
            "🧪 量化回测",
            "⚙️ 系统设置 (Settings)"
        ]
    )
    
    # --- 3. 路由分发 ---
    if app_mode == "🏠 仪表盘 (Dashboard)":
        from ui.dashboard_home import render_dashboard_home
        render_dashboard_home()
    
    elif app_mode == "🔥 交易策略":
        # 交易策略模块
        t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18, t19 = st.tabs([
            "🔮 预测雷达", "🔥 龙头战法", "📈 均线战法", "🎯 打板预测", "⚡ 集合竞价", "📊 量价关系", 
            "💰 游资席位", "🔍 买点扫描", "🕸️ 关系图谱", "👤 游资画像", "📈 短期涨跌", "🔮 机会预测", 
            "🤖 多智能体", "📰 智能新闻", "🧠 实时情绪感知", "🐉 龙头识别跟踪", "⚡ 竞价预测系统", 
            "🔧 在线参数调整", "🎮 历史重演"
        ])
        
        with t1:
            from ui.predictive_radar import render_predictive_radar
            render_predictive_radar(get_db_instance())
        
        with t2:
            from ui.dragon_strategy import render_dragon_strategy_tab
            dragon_strategy = __import__('ui.dragon_strategy', fromlist=['render_dragon_strategy_tab'])
            dragon_strategy.render_dragon_strategy_tab(get_db_instance(), get_config())
        
        with t3:
            from ui.ma_strategy import render_ma_strategy_tab
            ma_strategy = __import__('ui.ma_strategy', fromlist=['render_ma_strategy_tab'])
            ma_strategy.render_ma_strategy_tab(get_db_instance(), get_config())
        
        with t4:
            from ui.limit_up import render_limit_up_tab
            limit_up = __import__('ui.limit_up', fromlist=['render_limit_up_tab'])
            limit_up.render_limit_up_tab(get_db_instance(), get_config())
        
        with t5:
            from ui.auction import render_auction_tab
            auction = __import__('ui.auction', fromlist=['render_auction_tab'])
            auction.render_auction_tab(get_db_instance(), get_config())
        
        with t6:
            from ui.volume_price import render_volume_price_tab
            volume_price = __import__('ui.volume_price', fromlist=['render_volume_price_tab'])
            volume_price.render_volume_price_tab(get_db_instance(), get_config())
        
        with t7:
            from ui.capital import render_capital_tab
            capital = __import__('ui.capital', fromlist=['render_capital_tab'])
            capital.render_capital_tab(get_db_instance(), get_config())
        
        with t8:
            from ui.buy_point_scanner import render_buy_point_scanner_tab
            buy_point_scanner = __import__('ui.buy_point_scanner', fromlist=['render_buy_point_scanner_tab'])
            buy_point_scanner.render_buy_point_scanner_tab(get_db_instance(), get_config())
        
        with t9:
            from ui.capital_network import render_capital_network_tab
            capital_network = __import__('ui.capital_network', fromlist=['render_capital_network_tab'])
            capital_network.render_capital_network_tab(get_db_instance(), get_config())
        
        with t10:
            from ui.capital_profiler import render_capital_profiler_tab
            capital_profiler = __import__('ui.capital_profiler', fromlist=['render_capital_profiler_tab'])
            capital_profiler.render_capital_profiler_tab(get_db_instance(), get_config())
        
        with t11:
            from ui.short_term_trend import render_short_term_trend_tab
            short_term_trend = __import__('ui.short_term_trend', fromlist=['render_short_term_trend_tab'])
            short_term_trend.render_short_term_trend_tab(get_db_instance(), get_config())
        
        with t12:
            from ui.opportunity_predictor import render_opportunity_predictor_tab
            opportunity_predictor = __import__('ui.opportunity_predictor', fromlist=['render_opportunity_predictor_tab'])
            opportunity_predictor.render_opportunity_predictor_tab(get_db_instance(), get_config())
        
        with t13:
            from ui.multi_agent_analysis import render_multi_agent_analysis_tab
            multi_agent_analysis = __import__('ui.multi_agent_analysis', fromlist=['render_multi_agent_analysis_tab'])
            multi_agent_analysis.render_multi_agent_analysis_tab(get_db_instance(), get_config())
        
        with t14:
            st.info("📝 智能新闻分析模块已归档，请使用其他新闻分析功能")
        
        with t15:
            from ui.realtime_sentiment_tab import render_realtime_sentiment_tab
            realtime_sentiment_tab = __import__('ui.realtime_sentiment_tab', fromlist=['render_realtime_sentiment_tab'])
            realtime_sentiment_tab.render_realtime_sentiment_tab(get_db_instance(), get_config())
        
        with t16:
            st.info("📝 龙头识别跟踪模块已归档，请使用其他龙头分析功能")
        
        with t17:
            from ui.auction_prediction_tab import render_auction_prediction_tab
            auction_prediction_tab = __import__('ui.auction_prediction_tab', fromlist=['render_auction_prediction_tab'])
            auction_prediction_tab.render_auction_prediction_tab(get_db_instance(), get_config())
        
        with t18:
            from ui.online_parameter_tab import render_online_parameter_tab
            online_parameter_tab = __import__('ui.online_parameter_tab', fromlist=['render_online_parameter_tab'])
            online_parameter_tab.render_online_parameter_tab(get_db_instance(), get_config())
        
        with t19:
            from ui.historical_replay import render_historical_replay_panel
            historical_replay = __import__('ui.historical_replay', fromlist=['render_historical_replay_panel'])
            historical_replay.render_historical_replay_panel()
    
    elif app_mode == "📊 市场情绪":
        t1 = st.tabs(["🧠 市场情绪分析"])
        with t1[0]:
            from ui.market_sentiment_tab import render_market_sentiment_tab
            market_sentiment_tab = __import__('ui.market_sentiment_tab', fromlist=['render_market_sentiment_tab'])
            market_sentiment_tab.render_market_sentiment_tab(get_db_instance(), get_config())
    
    elif app_mode == "💼 交易执行":
        t1 = st.tabs(["💼 交易执行"])
        with t1[0]:
            from ui.trading_execution_tab import render_trading_execution_tab
            trading_execution_tab = __import__('ui.trading_execution_tab', fromlist=['render_trading_execution_tab'])
            trading_execution_tab.render_trading_execution_tab(get_db_instance(), get_config())
    
    elif app_mode == "🧪 量化回测":
        t1, t2, t3, t4, t5, t6 = st.tabs([
            "🧪 策略回测", "🧪 高级回测", "🧠 LSTM预测", "⚖️ 组合优化", "🤖 自主学习", "📋 更多功能"
        ])
        
        with t1:
            from ui.backtest import render_backtest_tab
            backtest = __import__('ui.backtest', fromlist=['render_backtest_tab'])
            backtest.render_backtest_tab(get_db_instance(), get_config())
        
        with t2:
            st.info("📝 高级回测模块已归档，请使用策略回测功能")
        
        with t3:
            from ui.lstm_predictor import render_lstm_predictor_tab
            lstm_predictor = __import__('ui.lstm_predictor', fromlist=['render_lstm_predictor_tab'])
            lstm_predictor.render_lstm_predictor_tab(get_db_instance(), get_config())
        
        with t4:
            from ui.portfolio_optimizer_tab import render_portfolio_optimizer_tab
            portfolio_optimizer_tab = __import__('ui.portfolio_optimizer_tab', fromlist=['render_portfolio_optimizer_tab'])
            portfolio_optimizer_tab.render_portfolio_optimizer_tab(get_db_instance(), get_config())
        
        with t5:
            from ui.autonomous_learning_tab import render_autonomous_learning_tab
            autonomous_learning_tab = __import__('ui.autonomous_learning_tab', fromlist=['render_autonomous_learning_tab'])
            autonomous_learning_tab.render_autonomous_learning_tab(get_db_instance(), get_config())
        
        with t6:
            st.subheader("📋 更多功能")
            st.info("选择下面的功能模块：")
            
            function_category = st.selectbox(
                "选择功能类别",
                ["🔧 基础工具", "🧮 策略系统", "🤖 AI智能系统", "🖥️ 分布式系统"],
                key="more_function_category"
            )
            
            if function_category == "🔧 基础工具":
                selected_function = st.selectbox(
                    "选择功能",
                    ["🧠 智能复盘", "参数优化", "K线形态识别"],
                    key="basic_tools_function"
                )
                
                if selected_function == "🧠 智能复盘":
                    with st.spinner("正在加载智能复盘系统..."):
                        v18_7_review_dashboard = __import__('ui.v18_7_review_dashboard', fromlist=['render_review_dashboard'])
                        v18_7_review_dashboard.render_review_dashboard()
                elif selected_function == "参数优化":
                    with st.spinner("正在加载参数优化引擎..."):
                        parameter_optimization = __import__('ui.parameter_optimization', fromlist=['render_parameter_optimization_tab'])
                        parameter_optimization.render_parameter_optimization_tab(get_db_instance(), get_config())
                elif selected_function == "K线形态识别":
                    with st.spinner("正在加载 K线形态识别引擎..."):
                        kline_patterns = __import__('ui.kline_patterns', fromlist=['render_kline_patterns_tab'])
                        kline_patterns.render_kline_patterns_tab(get_db_instance(), get_config())
    
    elif app_mode == "⚙️ 系统设置 (Settings)":
        st.write("### 🔧 快捷工具")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("更新概念库 (修复过期警告)"):
                with st.spinner("正在更新概念数据..."):
                    try:
                        os.system("python scripts/generate_concept_map.py")
                        st.success("概念库更新指令已发送！")
                    except Exception as e:
                        st.error(f"执行失败: {e}")
        
        with col2:
            if st.button("🚜 数据收割机 (增量更新)"):
                with st.spinner("正在收割活跃股数据..."):
                    try:
                        from logic.data_harvester import get_data_harvester

                        harvester = get_data_harvester()

                        st.info("📋 开始收割活跃股数据（增量更新，慢慢存、不封号）...")

                        result = harvester.harvest_active_stocks(
                            limit=300,
                            days=60,
                            force_update=False,
                            delay=0.5
                        )

                        # 显示结果
                        st.success(f"✅ 收割完成！")
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("总数", result['total'])
                        col_b.metric("成功", result['success'])
                        col_c.metric("失败", result['failed'])

                        # 显示详情
                        if result['failed'] > 0:
                            with st.expander("查看失败详情"):
                                failed_details = [d for d in result['details'] if d['status'] != 'success']
                                for detail in failed_details:
                                    st.write(f"❌ {detail['code']} {detail['name']}: {detail['message']}")

                    except Exception as e:
                        st.error(f"启动失败: {e}")
                        import traceback
                        traceback.print_exc()
        
        st.divider()
        st.write("### 📊 数据库统计")

        try:
            from logic.data_harvester import get_data_harvester

            harvester = get_data_harvester()
            stats = harvester.get_database_stats()

            col3, col4, col5, col6 = st.columns(4)
            with col3:
                st.metric("股票数量", stats['stock_count'])
            with col4:
                st.metric("数据总量", f"{stats['total_records']:,}")
            with col5:
                st.metric("最新日期", stats['latest_date'] or "无")
            with col6:
                st.metric("数据库大小", f"{stats['db_size_mb']} MB")

        except Exception as e:
            st.warning(f"⚠️ 无法获取数据库统计: {e}")

        st.divider()
        st.write("### 📁 文件系统状态")

        # 显示文件夹大小
        col7, col8, col9 = st.columns(3)
        with col7:
            scan_results_size = DataMaintenance.get_folder_size("data/scan_results")
            st.metric("扫描结果", scan_results_size)

        with col8:
            history_size = DataMaintenance.get_folder_size("data/history_kline")
            st.metric("历史K线", history_size)

        with col9:
            auction_size = DataMaintenance.get_folder_size("data/auction_snapshots")
            st.metric("竞价快照", auction_size)


def get_db_instance():
    """获取数据库实例"""
    from logic.database_manager import DatabaseManager
    return DatabaseManager()


def get_config():
    """获取配置实例"""
    from config.config_system import Config
    return Config()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"💥 系统崩溃: {e}")
        logger.critical(f"系统未捕获异常: {e}", exc_info=True)