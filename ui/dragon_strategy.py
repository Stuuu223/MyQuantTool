"""
龙头战法模块 V3.0 增强版

基于游资战法精髓：竞价抢筹、板块地位、弱转强、分时强承接
"""

import streamlit as st
import pandas as pd
import numpy as np
from logic.dragon_tactics import DragonTactics
from logic.dragon_tracking_system import DragonTrackingSystem
from logic.data_manager import DataManager
from logic.logger import get_logger
from config import Config

logger = get_logger(__name__)


def render_dragon_strategy_tab(db, config):
    """
    渲染龙头战法标签页（V3.0 增强版）

    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("🔥 龙头战法 V3.0 - 捕捉市场最强龙头")
    st.caption("基于游资战法精髓：竞价抢筹、板块地位、弱转强、分时强承接")

    st.info("""
    **龙头战法 V3.0 核心要点：**
    - 🎯 **竞价抢筹度**：9:25分成交量 / 昨天全天成交量 ≥ 2%（极强≥5%，强≥3%）
    - 👑 **板块地位**：龙一（板块核心龙头）、前三（板块前排）
    - 🔄 **弱转强/强更强**：昨天炸板/大阴线+今天高开，或昨天涨停+今天高开（连板加速）
    - 📊 **分时强承接**：股价在均线上方，下跌缩量，上涨放量
    - 🚫 **ST股过滤**：自动过滤 ST/*ST 退市风险股
    """)

    # 扫描参数
    col_scan1, col_scan2, col_scan3, col_scan4 = st.columns(4)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 500, 100, 10, key="dragon_scan_limit")
    with col_scan2:
        min_score = st.slider("最低评分门槛", 30, 90, 40, 5, key="dragon_min_score")
    with col_scan3:
        show_only_dragon = st.checkbox("只显示龙头股", value=False, key="show_only_dragon")
    with col_scan4:
        scan_scope = st.selectbox("扫描范围", ["自选股", "全市场（前N只）"], key="scan_scope")
    with col_scan4:
        if st.button("🔍 开始扫描", key="dragon_scan_btn"):
            st.session_state.scan_dragon = True
            st.rerun()

    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        # 添加调试信息
        st.info("🔍 开始扫描...")

        with st.spinner('正在扫描市场中的潜在龙头股...'):
            try:
                # 根据扫描范围获取股票列表
                if scan_scope == "自选股":
                    stock_list = config.get('watchlist', [])
                    st.info(f"📋 配置文件中的股票列表：{stock_list}")
                else:
                    # 全市场扫描：使用 akshare 获取股票列表
                    st.info("📡 正在获取全市场股票列表...")
                    try:
                        import akshare as ak
                        # 获取所有A股列表
                        stock_list_df = ak.stock_info_a_code_name()
                        # 只取前 scan_limit 只股票
                        stock_list = stock_list_df['code'].head(scan_limit).tolist()
                        st.info(f"📋 获取到 {len(stock_list)} 只股票（全市场前{scan_limit}只）")
                    except Exception as e:
                        st.error(f"❌ 获取股票列表失败：{str(e)}")
                        logger.error(f"获取股票列表失败: {str(e)}")
                        # 重置扫描状态
                        st.session_state.scan_dragon = False
                        return

                if not stock_list:
                    st.warning("⚠️ 没有股票列表，请先添加股票到自选股或检查网络连接")
                    # 重置扫描状态
                    st.session_state.scan_dragon = False
                else:
                    # 🔥🔥🔥 使用极速批量接口扫描市场 🔥🔥🔥
                    st.info(f"🚀 正在极速扫描 {len(stock_list)} 只标的...")
                    
                    # 初始化 DataManager 和 DragonTrackingSystem
                    data_manager = DataManager()
                    tracking_system = DragonTrackingSystem(data_manager)
                    
                    # 使用极速批量接口扫描
                    results = tracking_system.scan_market(stock_list, min_score=min_score)
                    
                    # 重置扫描状态
                    st.session_state.scan_dragon = False
                    
                    # 过滤
                    if show_only_dragon:
                        # 只显示龙头股（角色为核心龙）
                        filtered_stocks = [s for s in results if s['role'] == '核心龙']
                    else:
                        # 显示所有符合条件的股票
                        filtered_stocks = results

                    # 显示结果
                    st.success(f"扫描完成！共扫描 {len(stock_list)} 只股票，发现 {len(filtered_stocks)} 只符合条件股票")

                    if filtered_stocks:
                        # 按评分分组显示
                        strong_dragons = [s for s in filtered_stocks if s['score'] >= 85]
                        potential_dragons = [s for s in filtered_stocks if 75 <= s['score'] < 85]

                        # 强龙头
                        if strong_dragons:
                            st.divider()
                            st.subheader("🔥 真龙（猛干）")
                            for stock in strong_dragons:
                                with st.expander(f"{stock['name']} ({stock['code']}) - 评分: {stock['score']:.1f}"):
                                    # 基本信息
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("最新价", f"¥{stock['price']:.2f}")
                                    col2.metric("涨跌幅", f"{stock['change_percent']:.2f}%", delta_color="normal")
                                    col3.metric("评分", f"{stock['score']:.1f}/100")
                                    col4.metric("信号", stock['signal'])

                                    # 核心特征
                                    st.write("**🎯 核心特征：**")
                                    col1, col2, col3, col4 = st.columns(4)

                                    with col1:
                                        if stock['auction_intensity'] == '极强':
                                            st.success(f"🔥 竞价: {stock['auction_intensity']}")
                                        elif stock['auction_intensity'] == '强':
                                            st.info(f"💪 竞价: {stock['auction_intensity']}")
                                        else:
                                            st.warning(f"⚠️ 竞价: {stock['auction_intensity']}")

                                    with col2:
                                        if stock['sector_role'] == '龙一' or '龙一' in stock['sector_role']:
                                            st.success(f"👑 地位: {stock['sector_role']}")
                                        elif '前三' in stock['sector_role']:
                                            st.info(f"⭐ 地位: {stock['sector_role']}")
                                        else:
                                            st.warning(f"📍 地位: {stock['sector_role']}")

                                    with col3:
                                        if stock['weak_to_strong']:
                                            st.success("✅ 弱转强")
                                        else:
                                            st.info("❌ 无弱转强")

                                    with col4:
                                        if stock['intraday_support'] == '强' or stock['intraday_support'] == '极强':
                                            st.success("✅ 强承接")
                                        else:
                                            st.info("❌ 无强承接")

                                    # 操作建议
                                    st.info(f"**💡 操作建议：** {stock['reason']}")
                                    st.info(f"**📏 建议仓位：** {stock.get('position', '观望')}")
                                    st.warning(f"**🎯 置信度：** {stock['confidence']}")

                                    # 20cm 标记
                                    if stock.get('is_20cm'):
                                        st.info("🚀 20cm 创业板/科创板标的")

                        # 潜力龙头
                        if potential_dragons:
                            st.divider()
                            st.subheader("⭐ 潜力龙头（关注）")
                            for stock in potential_dragons:
                                with st.expander(f"{stock['name']} ({stock['code']}) - 评分: {stock['score']:.1f}"):
                                    # 基本信息
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("最新价", f"¥{stock['price']:.2f}")
                                    col2.metric("涨跌幅", f"{stock['change_percent']:.2f}%", delta_color="normal")
                                    col3.metric("评分", f"{stock['score']:.1f}/100")
                                    col4.metric("信号", stock['signal'])

                                    # 核心特征
                                    st.write("**🎯 核心特征：**")
                                    col1, col2, col3, col4 = st.columns(4)

                                    with col1:
                                        st.info(f"📊 竞价: {stock['auction_intensity']}")

                                    with col2:
                                        st.info(f"📍 地位: {stock['sector_role']}")

                                    with col3:
                                        if stock['weak_to_strong']:
                                            st.success("✅ 弱转强")
                                        else:
                                            st.info("❌ 无弱转强")

                                    with col4:
                                        st.info(f"📈 承接: {stock['intraday_support']}")

                                    # 操作建议
                                    st.info(f"**💡 操作建议：** {stock['reason']}")
                                    st.info(f"**📏 建议仓位：** {stock.get('position', '观望')}")
                                    st.warning(f"**🎯 置信度：** {stock['confidence']}")

                        # 其他股票
                        other_stocks = [s for s in filtered_stocks if s['score'] < 75]
                        if other_stocks:
                            st.divider()
                            st.subheader("📋 其他符合条件股票")
                            
                            # 使用表格显示
                            df = pd.DataFrame(other_stocks)
                            display_cols = ['code', 'name', 'price', 'change_percent', 'score', 'role', 'signal']
                            df_display = df[display_cols].copy()
                            df_display.columns = ['代码', '名称', '最新价', '涨跌幅', '评分', '角色', '信号']
                            st.dataframe(df_display, use_container_width=True)
                    else:
                        st.warning("⚠️ 未发现符合条件股票")
                        st.info("💡 建议：降低最低评分门槛或扩大扫描范围")

            except Exception as e:
                st.error(f"❌ 扫描失败：{str(e)}")
                logger.error(f"扫描失败: {str(e)}", exc_info=True)
                # 重置扫描状态
                st.session_state.scan_dragon = False

            except Exception as e:
                st.error(f"❌ 扫描失败：{str(e)}")
                logger.error(f"扫描失败: {str(e)}", exc_info=True)
                # 重置扫描状态
                st.session_state.scan_dragon = False
    else:
        st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的潜在龙头股")

        # 显示龙头战法说明
        st.divider()
        st.subheader("📖 龙头战法 V3.0 详解")

        with st.expander("🎯 决策矩阵"):
            st.markdown("""
            **1. 龙头地位（40%）**
            - 龙一（板块核心龙头）：80-100分
            - 前三（板块前排）：60-80分
            - 中军（板块中坚）：40-60分
            - 跟风（板块后排）：0-40分

            **2. 竞价强度（20%）**
            - 极强（≥5%）：100分 - 爆量高开
            - 强（≥3%）：80分 - 强抢筹
            - 中等（≥2%）：60分 - 中等抢筹
            - 弱（≥1%）：40分 - 弱抢筹
            - 极弱（<1%）：20分

            **3. 弱转强形态（20%）**
            - 昨天大跌，今天高开：100分 - 弱转强
            - 昨日收阴，今日高开：70分 - 弱转强迹象
            - 昨天涨停，今天高开：90分 - 强更强（连板加速）
            - 昨天涨停，今天维持：60分 - 连板形态
            - 无明显特征：0分

            **4. 分时承接（20%）**
            - 股价在均线上方，下跌缩量，上涨放量：100分
            - 股价在均线下方：0分
            """)

        with st.expander("💡 买入技巧"):
            st.markdown("""
            **买入时机：**

            **1. 真龙 + 竞价极强 + 涨幅>10%**
            - 🟢 扫板/排板（满仓/重仓）
            - 直接追，不要犹豫

            **2. 真龙 + 烂板/分歧 + 涨幅<5%**
            - 🟡 低吸博弈（半仓）
            - 水下捞，等待回封

            **3. 中军 + 图形漂亮**
            - 🟢 打板/跟随（半仓）
            - 趋势交易

            **4. 跟风 + 任意**
            - 🔵 只看不买（0）
            - 避免接盘

            **操作要点：**
            - 禁止建议"等待回调"：龙头启动时不会回调
            - 禁止使用 KDJ、MACD 金叉：这些指标太慢
            - 禁止看市盈率：短线博弈只看情绪和资金
            - 禁止 ST 股：退市风险股，流动性枯竭
            """)

        with st.expander("⚠️ 风险控制"):
            st.markdown("""
            **止损点设定：**

            **真龙（核心龙）：**
            - 止损价：当前价格 × 0.95
            - 或：跌破 5 日均线

            **中军/支线：**
            - 止损价：当前价格 × 0.93
            - 或：跌破 10 日均线

            **跟风：**
            - 不建议持有
            - 如果买入，止损价：当前价格 × 0.90

            **严格纪律：**
            - 绝对不允许个股跌幅超过10%
            - 如果跌幅超过10%，立即止损
            - 情绪过热时（群魔乱舞），停止开仓
            """)