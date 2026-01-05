"""智能预警模块"""
import streamlit as st
import pandas as pd
import numpy as np

def render_alert_tab(db, config):
    st.subheader("🔔 智能预警")
    st.subheader("🔔 智能预警系统")
    st.caption("自定义条件预警，实时监控价格、量能、技术指标等信号")

    # 导入预警系统
    from logic.algo_alert import AlertSystem

    # 预警模式选择
    alert_mode = st.radio("选择功能", ["单股预警", "自选股批量预警"], horizontal=True)

    if alert_mode == "单股预警":
        st.divider()
        st.subheader("📊 单股预警设置")

        # 股票代码输入
        alert_symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码")

        # 预警条件设置
        st.write("### 预警条件设置")

        # 1. 价格预警
        with st.expander("💰 价格预警", expanded=False):
            price_alert_enabled = st.checkbox("启用价格预警", key="price_alert_enabled")
            col_price1, col_price2 = st.columns(2)
            with col_price1:
                price_above = st.number_input("突破预警价", value=0.0, min_value=0.0, step=0.01, disabled=not price_alert_enabled)
            with col_price2:
                price_below = st.number_input("跌破预警价", value=0.0, min_value=0.0, step=0.01, disabled=not price_alert_enabled)

        # 2. 涨跌幅预警
        with st.expander("📈 涨跌幅预警", expanded=False):
            change_alert_enabled = st.checkbox("启用涨跌幅预警", key="change_alert_enabled")
            col_change1, col_change2 = st.columns(2)
            with col_change1:
                change_above = st.number_input("涨幅预警(%)", value=5.0, step=0.1, disabled=not change_alert_enabled)
            with col_change2:
                change_below = st.number_input("跌幅预警(%)", value=-5.0, step=0.1, disabled=not change_alert_enabled)

        # 3. 量能预警
        with st.expander("📊 量能预警", expanded=False):
            volume_alert_enabled = st.checkbox("启用量能预警", key="volume_alert_enabled")
            volume_ratio_threshold = st.slider("量比阈值", 1.5, 5.0, 2.0, 0.1, disabled=not volume_alert_enabled)

        # 4. 技术指标预警
        with st.expander("📉 技术指标预警", expanded=False):
            indicator_alert_enabled = st.checkbox("启用技术指标预警", key="indicator_alert_enabled")

            col_rsi1, col_rsi2 = st.columns(2)
            with col_rsi1:
                rsi_overbought = st.checkbox("RSI超买(>70)", value=True, disabled=not indicator_alert_enabled)
            with col_rsi2:
                rsi_oversold = st.checkbox("RSI超卖(<30)", value=True, disabled=not indicator_alert_enabled)

            col_macd1, col_macd2 = st.columns(2)
            with col_macd1:
                macd_golden_cross = st.checkbox("MACD金叉", value=True, disabled=not indicator_alert_enabled)
            with col_macd2:
                macd_death_cross = st.checkbox("MACD死叉", value=True, disabled=not indicator_alert_enabled)

        # 组装预警条件
        alert_conditions = {
            'price_alert_enabled': price_alert_enabled,
            'price_above': price_above,
            'price_below': price_below,
            'change_alert_enabled': change_alert_enabled,
            'change_above': change_above,
            'change_below': change_below,
            'volume_alert_enabled': volume_alert_enabled,
            'volume_ratio_threshold': volume_ratio_threshold,
            'indicator_alert_enabled': indicator_alert_enabled,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'macd_golden_cross': macd_golden_cross,
            'macd_death_cross': macd_death_cross
        }

        # 检查预警按钮
        if st.button("🔍 检查预警", key="check_single_alert"):
            with st.spinner('正在检查预警条件...'):
                alert_result = AlertSystem.check_alerts(alert_symbol, alert_conditions)

            if alert_result['数据状态'] == '正常':
                st.success(f"✅ 检查完成！发现 {alert_result['预警数量']} 个预警")

                if alert_result['预警列表']:
                    for alert in alert_result['预警列表']:
                        level_color = {
                            '高': '🔴',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{level_color.get(alert['预警级别'], '⚪')} {alert['预警类型']} - {alert['预警级别']}级"):
                            st.write(f"**说明：** {alert['说明']}")
                            if '当前价格' in alert:
                                st.write(f"**当前价格：** ¥{alert['当前价格']:.2f}")
                            if '当前涨跌幅' in alert:
                                st.write(f"**当前涨跌幅：** {alert['当前涨跌幅']}")
                            st.write(f"**预警条件：** {alert['预警条件']}")
                else:
                    st.info("👍 当前未触发任何预警条件")
            else:
                st.error(f"❌ {alert_result['数据状态']}")
                if '说明' in alert_result:
                    st.info(f"💡 {alert_result['说明']}")

    elif alert_mode == "自选股批量预警":
        st.divider()
        st.subheader("📋 自选股批量预警")

        st.info("💡 将对自选股中的所有股票进行批量预警检查")

        # 使用相同的预警条件设置（简化版）
        with st.expander("⚙️ 预警条件设置", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                change_above = st.number_input("涨幅预警(%)", value=5.0, step=0.1)
                change_below = st.number_input("跌幅预警(%)", value=-5.0, step=0.1)

            with col2:
                volume_ratio_threshold = st.slider("量比阈值", 1.5, 5.0, 2.0, 0.1)
                rsi_overbought = st.checkbox("RSI超买(>70)", value=True)
                rsi_oversold = st.checkbox("RSI超卖(<30)", value=True)

            with col3:
                macd_golden_cross = st.checkbox("MACD金叉", value=True)
                macd_death_cross = st.checkbox("MACD死叉", value=True)

        alert_conditions = {
            'change_alert_enabled': True,
            'change_above': change_above,
            'change_below': change_below,
            'volume_alert_enabled': True,
            'volume_ratio_threshold': volume_ratio_threshold,
            'indicator_alert_enabled': True,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'macd_golden_cross': macd_golden_cross,
            'macd_death_cross': macd_death_cross
        }

        # 批量检查按钮
        if st.button("🔍 批量检查预警", key="check_batch_alert"):
            if watchlist:
                # 进度条
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                total_stocks = len(watchlist)
                progress_text.text(f"🔍 正在检查 {total_stocks} 只自选股的预警...")
                
                # 批量检查预警
                batch_result = AlertSystem.scan_watchlist_alerts(watchlist, alert_conditions)
                progress_bar.progress(100)
                
                progress_bar.empty()
                progress_text.empty()

                if batch_result['数据状态'] == '正常':
                    st.success(f"✅ 检查完成！发现 {batch_result['预警总数']} 个预警")

                    if batch_result['预警列表']:
                        # 按预警级别分组显示
                        high_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '高']
                        medium_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '中']
                        low_alerts = [a for a in batch_result['预警列表'] if a['预警级别'] == '低']

                        # 高级预警
                        if high_alerts:
                            st.divider()
                            st.subheader("🔴 高级预警")
                            for alert in high_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")
                                    st.write(f"**当前价格：** ¥{alert['当前价格']:.2f}")
                                    st.write(f"**当前涨跌幅：** {alert['当前涨跌幅']}")

                        # 中级预警
                        if medium_alerts:
                            st.divider()
                            st.subheader("🟡 中级预警")
                            for alert in medium_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")

                        # 低级预警
                        if low_alerts:
                            st.divider()
                            st.subheader("🟢 低级预警")
                            for alert in low_alerts:
                                with st.expander(f"{alert['股票名称']} ({alert['股票代码']}) - {alert['预警类型']}"):
                                    st.write(f"**说明：** {alert['说明']}")
                    else:
                        st.info("👍 自选股中未触发任何预警条件")
            else:
                st.warning("⚠️ 自选股列表为空，请先添加股票到自选股")

