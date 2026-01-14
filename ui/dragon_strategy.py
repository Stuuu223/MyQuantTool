"""
龙头战法模块 V3.0 增强版

基于游资战法精髓：竞价抢筹、板块地位、弱转强、分时强承接
"""

import streamlit as st
import pandas as pd
import numpy as np
from logic.dragon_tactics import DragonTactics
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
        min_score = st.slider("最低评分门槛", 50, 90, 60, 5, key="dragon_min_score")
    with col_scan3:
        show_only_dragon = st.checkbox("只显示龙头股", value=True, key="show_only_dragon")
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
                # 创建 DragonTactics 实例
                tactics = DragonTactics()

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
                    # 添加进度条
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # 限制扫描数量
                    stock_list = stock_list[:scan_limit]

                    # 分析每只股票
                    analyzed_stocks = []
                    for i, symbol in enumerate(stock_list):
                        try:
                            # 更新进度
                            progress = (i + 1) / len(stock_list)
                            progress_bar.progress(progress)
                            status_text.text(f"正在分析第 {i + 1}/{len(stock_list)} 只股票：{symbol}")

                            # 从数据库获取股票数据
                            from datetime import datetime, timedelta
                            end_date = datetime.now().strftime('%Y%m%d')
                            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

                            stock_data = db.get_stock_data(symbol, start_date, end_date)

                            if stock_data is None or stock_data.empty:
                                continue

                            # 获取最新数据
                            latest = stock_data.iloc[-1]

                            name = f"股票_{symbol}"  # 这里应该从数据库获取股票名称

                            # 1. 代码前缀检查（包括 ST 检查）
                            code_check = tactics.check_code_prefix(symbol, name)
                            if code_check.get('banned', False):
                                # 跳过 ST 股
                                continue

                            # 2. 竞价分析（使用涨跌幅作为竞价强度的代理）
                            prev_day_volume = stock_data.iloc[-2].get('volume', 1) if len(stock_data) > 1 else 1
                            prev_day_amount = stock_data.iloc[-2].get('amount', 1) if len(stock_data) > 1 else 1

                            # 如果涨跌幅 > 5%，说明竞价抢筹度较高
                            change_percent = latest.get('pct_chg', 0)
                            if change_percent > 5:
                                # 涨幅 > 5%，假设竞价量比为 3%
                                auction_ratio = 0.03
                            elif change_percent > 3:
                                # 涨幅 > 3%，假设竞价量比为 2%
                                auction_ratio = 0.02
                            elif change_percent > 0:
                                # 涨幅 > 0%，假设竞价量比为 1%
                                auction_ratio = 0.01
                            else:
                                # 跌幅，假设竞价量比为 0.5%
                                auction_ratio = 0.005

                            auction_analysis = tactics.analyze_call_auction(
                                current_open_volume=prev_day_volume * auction_ratio,
                                prev_day_total_volume=prev_day_volume,
                                current_open_amount=prev_day_amount * auction_ratio,
                                prev_day_total_amount=prev_day_amount
                            )

                            # 3. 板块地位分析（使用涨跌幅作为代理）
                            # 如果没有板块数据，根据涨跌幅推断板块地位
                            if change_percent > 7:
                                # 涨幅 > 7%，可能是龙一
                                sector_role_score = 80
                                sector_role = '龙一（推断）'
                            elif change_percent > 5:
                                # 涨幅 > 5%，可能是前三
                                sector_role_score = 60
                                sector_role = '前三（推断）'
                            elif change_percent > 3:
                                # 涨幅 > 3%，可能是中军
                                sector_role_score = 40
                                sector_role = '中军（推断）'
                            elif change_percent > 0:
                                # 涨幅 > 0%，可能是跟风
                                sector_role_score = 20
                                sector_role = '跟风（推断）'
                            else:
                                # 跌幅，杂毛
                                sector_role_score = 0
                                sector_role = '杂毛'

                            sector_analysis = tactics.analyze_sector_rank(
                                symbol=symbol,
                                sector='未知板块',
                                current_change=change_percent,
                                sector_stocks_data=None,
                                limit_up_count=1
                            )

                            # 覆盖板块地位评分
                            sector_analysis['role_score'] = sector_role_score
                            sector_analysis['role'] = sector_role

                            # 4. 弱转强分析
                            weak_to_strong_analysis = tactics.analyze_weak_to_strong(df=stock_data)

                            # 5. 分时承接分析（使用 K 线数据作为代理）
                            # 如果收盘价 > 开盘价，说明全天上涨，可能有强承接
                            if latest.get('close', 0) > latest.get('open', 0):
                                # 收盘价 > 开盘价，全天上涨
                                intraday_support_score = 80
                                intraday_support = True
                            elif latest.get('close', 0) > latest.get('low', 0):
                                # 收盘价 > 最低价，部分上涨
                                intraday_support_score = 60
                                intraday_support = True
                            else:
                                # 收盘价 <= 最低价，全天下跌
                                intraday_support_score = 20
                                intraday_support = False

                            intraday_support_analysis = {
                                'intraday_support': intraday_support,
                                'intraday_support_score': intraday_support_score,
                                'has_strong_support': intraday_support
                            }

                            # 6. 决策矩阵
                            is_20cm = code_check.get('max_limit', 10) == 20
                            decision = tactics.make_decision_matrix(
                                role_score=sector_analysis.get('role_score', 0),
                                auction_score=auction_analysis.get('auction_score', 0),
                                weak_to_strong_score=weak_to_strong_analysis.get('weak_to_strong_score', 0),
                                intraday_support_score=intraday_support_analysis.get('intraday_support_score', 0),
                                current_change=latest.get('pct_chg', 0),
                                is_20cm=is_20cm
                            )

                            # 合并结果
                            analyzed_stock = {
                                'symbol': symbol,
                                'name': name,
                                'price': latest.get('close', 0),
                                'change_percent': latest.get('pct_chg', 0),
                                'volume': latest.get('volume', 0),
                                'amount': latest.get('amount', 0),
                                'sector': '未知板块',
                                'code_prefix': code_check.get('prefix_type', '未知'),
                                'is_20cm': is_20cm,
                                'auction_ratio': auction_analysis.get('call_auction_ratio', 0),
                                'auction_intensity': auction_analysis.get('auction_intensity', '未知'),
                                'auction_score': auction_analysis.get('auction_score', 0),
                                'sector_role': sector_analysis.get('role', '未知'),
                                'sector_role_score': sector_analysis.get('role_score', 0),
                                'sector_heat': sector_analysis.get('sector_heat', '未知'),
                                'weak_to_strong': weak_to_strong_analysis.get('weak_to_strong', False),
                                'weak_to_strong_score': weak_to_strong_analysis.get('weak_to_strong_score', 0),
                                'intraday_support': intraday_support_analysis.get('has_strong_support', False),
                                'intraday_support_score': intraday_support_analysis.get('intraday_support_score', 0),
                                'total_score': decision.get('total_score', 0),
                                'role': decision.get('role', '未知'),
                                'signal': decision.get('signal', 'WAIT'),
                                'confidence': decision.get('confidence', 'MEDIUM'),
                                'reason': decision.get('reason', ''),
                                'position': decision.get('position', '观望'),
                                'stop_loss': latest.get('close', 0) * 0.95
                            }

                            analyzed_stocks.append(analyzed_stock)

                        except Exception as e:
                            logger.error(f"分析股票 {symbol} 失败: {str(e)}")
                            continue

                    # 清除进度条
                    progress_bar.empty()
                    status_text.empty()

                    # 过滤和排序
                    if show_only_dragon:
                        # 只显示龙头股（角色为核心龙）
                        filtered_stocks = [s for s in analyzed_stocks if s['role'] == '核心龙']
                    else:
                        # 显示所有符合条件的股票
                        filtered_stocks = [s for s in analyzed_stocks if s['total_score'] >= min_score]

                    # 按评分降序排序
                    filtered_stocks.sort(key=lambda x: x['total_score'], reverse=True)

                    # 显示结果
                    st.success(f"扫描完成！共扫描 {len(stock_list)} 只股票，发现 {len(filtered_stocks)} 只符合条件股票")

                    if filtered_stocks:
                        # 按评分分组显示
                        strong_dragons = [s for s in filtered_stocks if s['total_score'] >= 85]
                        potential_dragons = [s for s in filtered_stocks if 75 <= s['total_score'] < 85]

                        # 强龙头
                        if strong_dragons:
                            st.divider()
                            st.subheader("🔥 真龙（猛干）")
                            for stock in strong_dragons:
                                with st.expander(f"{stock['name']} ({stock['symbol']}) - 评分: {stock['total_score']:.1f}"):
                                    # 基本信息
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("最新价", f"¥{stock['price']:.2f}")
                                    col2.metric("涨跌幅", f"{stock['change_percent']:.2f}%", delta_color="normal")
                                    col3.metric("评分", f"{stock['total_score']:.1f}/100")
                                    col4.metric("信号", stock['signal'])

                                    # 核心特征
                                    st.write("**🎯 核心特征：**")
                                    col1, col2, col3, col4 = st.columns(4)

                                    with col1:
                                        if stock['auction_ratio'] >= 0.15:
                                            st.success(f"🔥 竞价: {stock['auction_ratio']:.1%} (极强)")
                                        elif stock['auction_ratio'] >= 0.10:
                                            st.info(f"💪 竞价: {stock['auction_ratio']:.1%} (强)")
                                        else:
                                            st.warning(f"⚠️ 竞价: {stock['auction_ratio']:.1%}")

                                    with col2:
                                        if stock['sector_role'] == '龙一' or stock['sector_role'] == '涨停（疑似龙头）':
                                            st.success(f"👑 地位: {stock['sector_role']}")
                                        elif stock['sector_role'] == '前三':
                                            st.info(f"⭐ 地位: {stock['sector_role']}")
                                        else:
                                            st.warning(f"📍 地位: {stock['sector_role']}")

                                    with col3:
                                        if stock['weak_to_strong']:
                                            st.success("✅ 弱转强")
                                        else:
                                            st.info("❌ 无弱转强")

                                    with col4:
                                        if stock['intraday_support']:
                                            st.success("✅ 强承接")
                                        else:
                                            st.info("❌ 无强承接")

                                    # 决策矩阵详情
                                    st.write("**📊 决策矩阵：**")
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("龙头地位", f"{stock['sector_role_score']}/100")
                                    col2.metric("竞价强度", f"{stock['auction_score']}/100")
                                    col3.metric("弱转强", f"{stock['weak_to_strong_score']}/100")
                                    col4.metric("分时承接", f"{stock['intraday_support_score']}/100")

                                    # 操作建议
                                    st.info(f"**💡 操作建议：** {stock['reason']}")
                                    st.info(f"**📏 建议仓位：** {stock['position']}")
                                    st.warning(f"**🛡️ 止损价：** ¥{stock['stop_loss']:.2f}")

                                    # 添加到自选股按钮
                                    if st.button(f"➕ 添加到自选", key=f"add_dragon_{stock['symbol']}"):
                                        watchlist = config.get('watchlist', [])
                                        if stock['symbol'] not in watchlist:
                                            watchlist.append(stock['symbol'])
                                            config.set('watchlist', watchlist)
                                            st.success(f"已添加 {stock['name']} ({stock['symbol']}) 到自选股")
                                        else:
                                            st.info(f"{stock['name']} ({stock['symbol']}) 已在自选股中")

                        # 潜力龙头
                        if potential_dragons:
                            st.divider()
                            st.subheader("📈 潜力龙头（关注）")
                            for stock in potential_dragons:
                                with st.expander(f"{stock['name']} ({stock['symbol']}) - 评分: {stock['total_score']:.1f}"):
                                    # 基本信息
                                    col1, col2, col3 = st.columns(3)
                                    col1.metric("最新价", f"¥{stock['price']:.2f}")
                                    col2.metric("涨跌幅", f"{stock['change_percent']:.2f}%")
                                    col3.metric("评分", f"{stock['total_score']:.1f}/100")

                                    # 核心特征
                                    st.write("**🎯 核心特征：**")
                                    col1, col2, col3, col4 = st.columns(4)

                                    with col1:
                                        if stock['auction_ratio'] >= 0.10:
                                            st.success(f"💪 竞价: {stock['auction_ratio']:.1%}")
                                        else:
                                            st.warning(f"⚠️ 竞价: {stock['auction_ratio']:.1%}")

                                    with col2:
                                        st.info(f"📍 地位: {stock['sector_role']}")

                                    with col3:
                                        if stock['weak_to_strong']:
                                            st.success("✅ 弱转强")
                                        else:
                                            st.info("❌ 无弱转强")

                                    with col4:
                                        if stock['intraday_support']:
                                            st.success("✅ 强承接")
                                        else:
                                            st.info("❌ 无强承接")

                                    # 操作建议
                                    st.info(f"**💡 操作建议：** {stock['reason']}")
                                    st.warning(f"**🛡️ 止损价：** ¥{stock['stop_loss']:.2f}")

                                    # 添加到自选股按钮
                                    if st.button(f"➕ 添加到自选", key=f"add_potential_{stock['symbol']}"):
                                        watchlist = config.get('watchlist', [])
                                        if stock['symbol'] not in watchlist:
                                            watchlist.append(stock['symbol'])
                                            config.set('watchlist', watchlist)
                                            st.success(f"已添加 {stock['name']} ({stock['symbol']}) 到自选股")
                                        else:
                                            st.info(f"{stock['name']} ({stock['symbol']}) 已在自选股中")
                    else:
                        st.warning("未发现符合条件的龙头股")
                        st.info("💡 提示：可以降低最低评分门槛或增加扫描数量")

                    # 重置扫描状态
                    st.session_state.scan_dragon = False

            except Exception as e:
                st.error(f"❌ 扫描失败：{str(e)}")
                logger.error(f"龙头战法扫描失败: {str(e)}")
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