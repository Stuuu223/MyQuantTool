#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三漏斗扫描系统 - UI 集成

功能：
1. 观察池管理 - 添加/移除股票
2. 盘后扫描 - 运行 Level 1-3 筛选
3. 盘中监控 - 实时显示信号
4. 信号历史 - 查看最近的信号
5. 统计分析 - 显示信号统计

作者: iFlow CLI
版本: V1.0
日期: 2026-02-05
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from logic.logger import get_logger
from logic.triple_funnel_scanner import TripleFunnelScanner, WatchlistItem, RiskLevel, SignalType
from logic.signal_manager import get_signal_manager, SignalHistory

logger = get_logger(__name__)


def render_triple_funnel_tab(db_instance=None, config=None):
    """渲染三漏斗扫描标签页"""
    st.title("🎯 三漏斗扫描系统")
    st.markdown("---")

    # 创建扫描器
    scanner = TripleFunnelScanner()
    signal_manager = get_signal_manager()

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")

        # 运行模式
        mode = st.radio(
            "运行模式",
            ["观察池管理", "盘后扫描", "盘中监控", "信号历史"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 快捷操作
        st.subheader("🚀 快捷操作")

        if st.button("刷新观察池", key="refresh_watchlist"):
            st.rerun()

        if st.button("清空信号通知", key="clear_notifications"):
            _clear_notifications()

        st.markdown("---")

        # 统计信息
        st.subheader("📊 统计")

        watchlist = scanner.watchlist_manager.get_all()
        st.metric("观察池股票", len(watchlist))

        recent_signals = signal_manager.get_recent_signals(hours=24)
        st.metric("24小时信号", len(recent_signals))

        stats = signal_manager.get_signal_stats()
        st.metric("总触发次数", sum(s['count'] for s in stats))

    # 根据模式显示不同页面
    if mode == "观察池管理":
        _render_watchlist_management(scanner)
    elif mode == "盘后扫描":
        _render_post_market_scan(scanner)
    elif mode == "盘中监控":
        _render_intraday_monitor(scanner, signal_manager)
    elif mode == "信号历史":
        _render_signal_history(signal_manager)


def _render_watchlist_management(scanner: TripleFunnelScanner):
    """观察池管理页面"""
    st.header("📋 观察池管理")

    # 添加股票表单
    with st.expander("➕ 添加股票", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            code = st.text_input("股票代码", placeholder="000001", key="add_code")

        with col2:
            name = st.text_input("股票名称", placeholder="平安银行", key="add_name")

        with col3:
            reason = st.text_input("添加原因", placeholder="测试用", key="add_reason")

        if st.button("添加", key="btn_add"):
            if code and name:
                scanner.watchlist_manager.add(code, name, reason or "手动添加")
                st.success(f"✅ 已添加: {code} {name}")
                st.rerun()
            else:
                st.error("❌ 请输入股票代码和名称")

    st.markdown("---")

    # 观察池列表
    st.subheader("📊 观察池列表")

    watchlist = scanner.watchlist_manager.get_all()

    if not watchlist:
        st.info("观察池为空，请添加股票")
        return

    # 转换为 DataFrame
    data = []
    for item in watchlist:
        row = {
            "代码": item.code,
            "名称": item.name,
            "原因": item.reason,
            "添加时间": item.added_at[:10],
            "Level1": "✅" if item.level1_result and item.level1_result.passed else "❌",
            "Level2": "✅" if item.level2_result and item.level2_result.passed else "❌",
            "Level3": "✅" if item.level3_result and item.level3_result.passed else "❌",
        }

        if item.level2_result:
            row["资金流得分"] = f"{item.level2_result.fund_flow_score:.0f}"

        if item.level3_result:
            row["综合得分"] = f"{item.level3_result.comprehensive_score:.0f}"
            row["风险等级"] = item.level3_result.risk_level.value

        data.append(row)

    df = pd.DataFrame(data)

    # 显示表格
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "代码": st.column_config.TextColumn("代码", width="small"),
            "名称": st.column_config.TextColumn("名称", width="medium"),
            "原因": st.column_config.TextColumn("原因", width="medium"),
            "添加时间": st.column_config.DateColumn("添加时间", width="small"),
            "Level1": st.column_config.TextColumn("Level1", width="small"),
            "Level2": st.column_config.TextColumn("Level2", width="small"),
            "Level3": st.column_config.TextColumn("Level3", width="small"),
            "资金流得分": st.column_config.ProgressColumn("资金流得分", min_value=0, max_value=100),
            "综合得分": st.column_config.ProgressColumn("综合得分", min_value=0, max_value=100),
            "风险等级": st.column_config.TextColumn("风险等级", width="small"),
        }
    )

    # 移除股票
    st.markdown("---")
    st.subheader("❌ 移除股票")

    code_to_remove = st.text_input("输入要移除的股票代码", key="remove_code")

    if st.button("移除", key="btn_remove"):
        if code_to_remove:
            scanner.watchlist_manager.remove(code_to_remove)
            st.success(f"✅ 已移除: {code_to_remove}")
            st.rerun()
        else:
            st.error("❌ 请输入股票代码")


def _render_post_market_scan(scanner: TripleFunnelScanner):
    """盘后扫描页面"""
    st.header("🔍 盘后扫描 (Level 1-3)")

    st.info("📝 说明: 盘后扫描会对观察池中的股票进行三级筛选，过滤出优质标的。")

    # 配置
    col1, col2 = st.columns(2)

    with col1:
        max_stocks = st.number_input("最大扫描股票数", min_value=1, max_value=500, value=100)

    with col2:
        st.info(f"当前观察池: {len(scanner.watchlist_manager.get_all())} 只股票")

    # 运行扫描
    if st.button("🚀 开始扫描", type="primary", key="btn_scan"):
        with st.spinner("正在扫描..."):
            passed = scanner.run_post_market_scan(max_stocks=max_stocks)

            if passed:
                st.success(f"✅ 扫描完成: {len(passed)} 只股票通过筛选")
            else:
                st.warning("⚠️ 扫描完成: 没有股票通过筛选")

            # 显示通过筛选的股票
            if passed:
                st.markdown("---")
                st.subheader("✅ 通过筛选的股票")

                data = []
                for code in passed:
                    item = scanner.watchlist_manager.watchlist.get(code)
                    if item:
                        row = {
                            "代码": code,
                            "名称": item.name,
                            "Level1得分": f"{item.level1_result.metrics.get('turnover_rate', 0):.2f}%" if item.level1_result else "-",
                            "Level2得分": f"{item.level2_result.fund_flow_score:.0f}" if item.level2_result else "-",
                            "Level3得分": f"{item.level3_result.comprehensive_score:.0f}" if item.level3_result else "-",
                            "风险等级": item.level3_result.risk_level.value if item.level3_result else "-",
                        }
                        data.append(row)

                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

    # 显示最近一次扫描结果
    st.markdown("---")
    st.subheader("📊 最近扫描结果")

    watchlist = scanner.watchlist_manager.get_all()

    if not watchlist:
        st.info("暂无扫描结果")
        return

    # 统计
    passed_count = sum(1 for item in watchlist if item.level3_result and item.level3_result.passed)
    failed_count = len(watchlist) - passed_count

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总扫描", len(watchlist))

    with col2:
        st.metric("通过", passed_count, delta_color="normal")

    with col3:
        st.metric("未通过", failed_count, delta_color="inverse")

    # 详细结果
    data = []
    for item in watchlist:
        row = {
            "代码": item.code,
            "名称": item.name,
            "Level1": "✅" if item.level1_result and item.level1_result.passed else "❌",
            "Level2": "✅" if item.level2_result and item.level2_result.passed else "❌",
            "Level3": "✅" if item.level3_result and item.level3_result.passed else "❌",
        }

        if item.level1_result and not item.level1_result.passed:
            row["Level1原因"] = ", ".join(item.level1_result.reasons)

        if item.level2_result and not item.level2_result.passed:
            row["Level2原因"] = ", ".join(item.level2_result.reasons)

        if item.level3_result and not item.level3_result.passed:
            row["Level3原因"] = ", ".join(item.level3_result.reasons)

        data.append(row)

    df = pd.DataFrame(data)

    st.dataframe(
        df,
        use_container_width=True,
        height=400
    )


def _render_intraday_monitor(scanner: TripleFunnelScanner, signal_manager):
    """盘中监控页面"""
    st.header("⚡ 盘中监控 (Level 4)")

    st.info("📝 说明: 盘中监控会实时检测 VWAP 突破、扫单、竞价爆量等信号。")

    # 配置
    col1, col2 = st.columns(2)

    with col1:
        interval = st.number_input("监控间隔 (秒)", min_value=1, max_value=60, value=3)

    with col2:
        st.info(f"当前观察池: {len(scanner.watchlist_manager.get_all())} 只股票")

    # 自动刷新
    if st.button("🔄 开始监控", type="primary", key="btn_monitor"):
        st.info("监控已启动，请保持页面打开...")

        # 使用 streamlit-autorefresh 自动刷新
        try:
            from streamlit_autorefresh import st_autorefresh

            count = st_autorefresh(interval=interval * 1000, limit=None, key="monitor_refresh")

            # 运行监控
            signals = scanner.run_intraday_monitor()

            # 处理信号
            for signal in signals:
                triggered = signal_manager.process_signal(signal)

                if triggered:
                    # 显示信号通知
                    with st.container():
                        st.error(f"🚀 信号触发: {signal.stock_name} {signal.signal_type.value}")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("价格", f"{signal.price:.2f}")

                        with col2:
                            st.metric("触发价", f"{signal.trigger_price:.2f}")

                        with col3:
                            st.metric("强度", f"{signal.signal_strength:.2f}")

                        st.json(signal.details)

        except ImportError:
            st.warning("⚠️ streamlit-autorefresh 未安装，请运行: pip install streamlit-autorefresh")

    # 显示当前交易阶段
    from logic.intraday_monitor import IntraDayMonitor
    monitor = IntraDayMonitor()
    phase = monitor.get_trading_phase()

    st.markdown("---")
    st.subheader("📊 当前状态")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("交易阶段", phase)

    with col2:
        st.metric("监控间隔", f"{interval} 秒")

    # 实时价格
    st.markdown("---")
    st.subheader("💹 实时价格")

    watchlist = scanner.watchlist_manager.get_all()

    if not watchlist:
        st.info("观察池为空")
        return

    codes = [item.code for item in watchlist[:20]]  # 限制显示20只

    try:
        from logic.data_source_manager import get_smart_data_manager
        data_manager = get_smart_data_manager()

        df_quotes = data_manager.get_realtime_quotes(codes)

        if not df_quotes.empty:
            st.dataframe(
                df_quotes[["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额"]],
                use_container_width=True
            )
        else:
            st.warning("⚠️ 无法获取实时数据")
    except Exception as e:
        st.error(f"❌ 获取实时数据失败: {e}")


def _render_signal_history(signal_manager):
    """信号历史页面"""
    st.header("📜 信号历史")

    # 筛选选项
    col1, col2, col3 = st.columns(3)

    with col1:
        hours = st.number_input("时间范围 (小时)", min_value=1, max_value=168, value=24)

    with col2:
        stock_filter = st.text_input("股票代码筛选 (可选)", placeholder="000001")

    with col3:
        signal_type_filter = st.selectbox(
            "信号类型筛选",
            ["全部", "VWAP_BREAKOUT", "VOLUME_SURGE", "AUCTION_SPIKE", "BREAKOUT_CONFIRM", "DIP_BUY"]
        )

    # 获取信号
    signals = signal_manager.get_recent_signals(hours=hours)

    # 筛选
    if stock_filter:
        signals = [s for s in signals if stock_filter in s.stock_code]

    if signal_type_filter != "全部":
        signals = [s for s in signals if s.signal_type == signal_type_filter]

    # 统计
    st.markdown("---")
    st.subheader("📊 信号统计")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总信号数", len(signals))

    with col2:
        unique_stocks = len(set(s.stock_code for s in signals))
        st.metric("涉及股票", unique_stocks)

    with col3:
        # 按类型统计
        type_counts = {}
        for s in signals:
            type_counts[s.signal_type] = type_counts.get(s.signal_type, 0) + 1

        most_common = max(type_counts.items(), key=lambda x: x[1]) if type_counts else ("无", 0)
        st.metric("最常见信号", f"{most_common[0]} ({most_common[1]})")

    # 信号列表
    st.markdown("---")
    st.subheader("🚀 信号列表")

    if not signals:
        st.info("暂无信号")
        return

    # 转换为 DataFrame
    data = []
    for signal in signals:
        row = {
            "股票": f"{signal.stock_name} ({signal.stock_code})",
            "信号": signal.signal_type,
            "时间": signal.timestamp,
            "价格": f"{signal.price:.2f}",
            "触发价": f"{signal.trigger_price:.2f}",
            "强度": f"{signal.signal_strength:.2f}",
            "风险": signal.risk_level,
        }
        data.append(row)

    df = pd.DataFrame(data)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "股票": st.column_config.TextColumn("股票", width="medium"),
            "信号": st.column_config.TextColumn("信号", width="small"),
            "时间": st.column_config.DatetimeColumn("时间", format="YYYY-MM-DD HH:mm:ss"),
            "价格": st.column_config.NumberColumn("价格", format="%.2f"),
            "触发价": st.column_config.NumberColumn("触发价", format="%.2f"),
            "强度": st.column_config.ProgressColumn("强度", min_value=0, max_value=1),
            "风险": st.column_config.TextColumn("风险", width="small"),
        }
    )

    # 详细信息
    st.markdown("---")
    st.subheader("📋 信号详情")

    selected_signal = st.selectbox(
        "选择信号查看详情",
        options=range(len(signals)),
        format_func=lambda i: f"{signals[i].stock_name} - {signals[i].signal_type} @ {signals[i].timestamp}"
    )

    if selected_signal is not None:
        signal = signals[selected_signal]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("股票", f"{signal.stock_name} ({signal.stock_code})")
            st.metric("信号类型", signal.signal_type)
            st.metric("时间", signal.timestamp)

        with col2:
            st.metric("价格", f"{signal.price:.2f}")
            st.metric("触发价", f"{signal.trigger_price:.2f}")
            st.metric("强度", f"{signal.signal_strength:.2f}")

        st.json(signal.details)


def _clear_notifications():
    """清空通知队列"""
    try:
        queue_file = Path("data/signal_queue/notifications.jsonl")
        if queue_file.exists():
            queue_file.unlink()
            st.success("✅ 通知队列已清空")
    except Exception as e:
        st.error(f"❌ 清空通知失败: {e}")


if __name__ == "__main__":
    render_triple_funnel_tab()