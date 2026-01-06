"""系统设置模块"""
import streamlit as st
import pandas as pd

def render_settings_tab(db, config):
    st.subheader("⚙️ 系统设置")
    st.caption("个性化设置和系统配置")

    # 导入用户偏好管理器
    from logic.user_preferences import UserPreferences

    user_prefs = UserPreferences()

    # 功能选择
    settings_mode = st.radio("选择设置", ["显示设置", "分析设置", "预警设置", "风险设置", "其他设置"], horizontal=True)

    if settings_mode == "显示设置":
        st.divider()
        st.subheader("🎨 显示设置")

        theme = st.selectbox("主题", ["light", "dark"], index=0 if user_prefs.get('display', '主题') == 'light' else 1)
        show_grid = st.checkbox("显示网格", value=user_prefs.get('display', '显示网格', True))
        show_volume = st.checkbox("显示成交量", value=user_prefs.get('display', '显示成交量', True))

        if st.button("💾 保存显示设置", key="save_display_settings"):
            user_prefs.set('display', '主题', theme)
            user_prefs.set('display', '显示网格', show_grid)
            user_prefs.set('display', '显示成交量', show_volume)
            st.success("✅ 显示设置已保存")

    elif settings_mode == "分析设置":
        st.divider()
        st.subheader("📊 分析设置")

        analysis_days = st.slider("默认分析天数", 30, 180, user_prefs.get('analysis', '默认分析天数', 60), 10)
        stop_loss_pct = st.slider("默认止损比例(%)", 2.0, 10.0, user_prefs.get('analysis', '默认止损比例', 0.05) * 100, 0.5) / 100
        take_profit_pct = st.slider("默认止盈比例(%)", 5.0, 20.0, user_prefs.get('analysis', '默认止盈比例', 0.10) * 100, 0.5) / 100

        if st.button("💾 保存分析设置", key="save_analysis_settings"):
            user_prefs.set('analysis', '默认分析天数', analysis_days)
            user_prefs.set('analysis', '默认止损比例', stop_loss_pct)
            user_prefs.set('analysis', '默认止盈比例', take_profit_pct)
            st.success("✅ 分析设置已保存")

    elif settings_mode == "预警设置":
        st.divider()
        st.subheader("🔔 预警设置")

        enable_sound = st.checkbox("启用声音提醒", value=user_prefs.get('alert', '启用声音提醒', False))
        enable_popup = st.checkbox("启用弹窗提醒", value=user_prefs.get('alert', '启用弹窗提醒', True))
        refresh_interval = st.slider("刷新间隔(秒)", 30, 300, user_prefs.get('alert', '预警刷新间隔', 60), 10)

        if st.button("💾 保存预警设置", key="save_alert_settings"):
            user_prefs.set('alert', '启用声音提醒', enable_sound)
            user_prefs.set('alert', '启用弹窗提醒', enable_popup)
            user_prefs.set('alert', '预警刷新间隔', refresh_interval)
            st.success("✅ 预警设置已保存")

    elif settings_mode == "风险设置":
        st.divider()
        st.subheader("⚠️ 风险设置")

        risk_per_trade = st.slider("单笔风险比例(%)", 1.0, 5.0, user_prefs.get('risk', '单笔风险比例', 0.02) * 100, 0.5) / 100
        max_positions = st.slider("最大持仓数量", 3, 10, user_prefs.get('risk', '最大持仓数量', 5), 1)
        max_drawdown = st.slider("最大回撤限制(%)", 5.0, 20.0, user_prefs.get('risk', '最大回撤限制', 0.10) * 100, 1.0) / 100

        if st.button("💾 保存风险设置", key="save_risk_settings"):
            user_prefs.set('risk', '单笔风险比例', risk_per_trade)
            user_prefs.set('risk', '最大持仓数量', max_positions)
            user_prefs.set('risk', '最大回撤限制', max_drawdown)
            st.success("✅ 风险设置已保存")

    elif settings_mode == "其他设置":
        st.divider()
        st.subheader("🔧 其他设置")

        auto_refresh = st.checkbox("自动刷新", value=user_prefs.get('other', '自动刷新', False))
        save_history = st.checkbox("保存历史记录", value=user_prefs.get('other', '保存历史记录', True))
        history_days = st.slider("历史记录保留天数", 7, 90, user_prefs.get('other', '历史记录保留天数', 30), 1)

        if st.button("💾 保存其他设置", key="save_other_settings"):
            user_prefs.set('other', '自动刷新', auto_refresh)
            user_prefs.set('other', '保存历史记录', save_history)
            user_prefs.set('other', '历史记录保留天数', history_days)
            st.success("✅ 其他设置已保存")

    # 重置设置
    st.divider()
    if st.button("🔄 重置为默认设置", key="reset_settings"):
        user_prefs.reset_to_default()
        st.success("✅ 已重置为默认设置")