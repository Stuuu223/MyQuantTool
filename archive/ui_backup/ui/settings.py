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
    settings_mode = st.radio("选择设置", ["显示设置", "分析设置", "预警设置", "风险设置", "性能监控", "代理设置", "其他设置"], horizontal=True)

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

    elif settings_mode == "性能监控":
        st.divider()
        st.subheader("📊 性能监控面板")

        # 获取性能指标
        import psutil
        import time
        from datetime import datetime

        # 系统资源使用情况
        col1, col2, col3 = st.columns(3)
        with col1:
            cpu_percent = psutil.cpu_percent(interval=1)
            st.metric("CPU 使用率", f"{cpu_percent}%", delta=f"{cpu_percent - 50:.1f}%")
        with col2:
            mem = psutil.virtual_memory()
            st.metric("内存使用率", f"{mem.percent}%", delta=f"{mem.percent - 50:.1f}%")
        with col3:
            disk = psutil.disk_usage('/')
            st.metric("磁盘使用率", f"{disk.percent}%")

        # Streamlit 缓存统计
        st.divider()
        st.subheader("🚀 Streamlit 缓存统计")

        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            from streamlit.runtime.caching import cache_data, cache_resource

            # 缓存统计
            cache_stats = {
                "数据缓存命中": st.session_state.get('cache_hits', 0),
                "数据缓存未命中": st.session_state.get('cache_misses', 0),
                "命中率": f"{(st.session_state.get('cache_hits', 0) / max(st.session_state.get('cache_hits', 0) + st.session_state.get('cache_misses', 1), 1) * 100):.1f}%"
            }

            col4, col5 = st.columns(2)
            with col4:
                st.metric("缓存命中次数", cache_stats["数据缓存命中"])
            with col5:
                st.metric("缓存未命中次数", cache_stats["数据缓存未命中"])

            st.metric("缓存命中率", cache_stats["命中率"])
        except Exception as e:
            st.warning(f"无法获取缓存统计: {e}")

        # 应用运行时间
        st.divider()
        st.subheader("⏱️ 应用运行时间")

        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = time.time()

        elapsed_time = time.time() - st.session_state.app_start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        col6, col7 = st.columns(2)
        with col6:
            st.metric("运行时长", f"{minutes}分{seconds}秒")
        with col7:
            st.metric("启动时间", datetime.now().strftime("%H:%M:%S"))

        # 性能建议
        st.divider()
        st.subheader("💡 性能优化建议")

        suggestions = []

        if cpu_percent > 80:
            suggestions.append("⚠️ CPU 使用率过高，建议关闭不必要的应用")
        if mem.percent > 80:
            suggestions.append("⚠️ 内存使用率过高，建议清理缓存或重启应用")
        if cache_stats.get("命中率", 0) < 50 and cache_stats.get("数据缓存命中", 0) > 0:
            suggestions.append("💡 缓存命中率较低，建议增加缓存时间或优化缓存策略")

        if suggestions:
            for suggestion in suggestions:
                st.info(suggestion)
        else:
            st.success("✅ 系统运行状态良好")

        # 清理缓存按钮
        st.divider()
        if st.button("🧹 清理所有缓存", key="clear_all_cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.cache_hits = 0
            st.session_state.cache_misses = 0
            st.success("✅ 所有缓存已清理")
            time.sleep(1)
            st.rerun()

    elif settings_mode == "代理设置":
        st.divider()
        st.subheader("🌐 代理设置")
        st.caption("配置网络代理，绕过Clash等VPN工具，避免IP封禁")

        # 导入代理管理器
        from logic.proxy_manager import get_proxy_manager, ProxyMode

        proxy_mgr = get_proxy_manager()

        # 显示当前代理配置
        st.divider()
        st.subheader("📊 当前代理配置")

        config_info = proxy_mgr.get_proxy_config()
        
        col1, col2 = st.columns(2)
        with col1:
            mode_map = {
                "direct": "直连模式（推荐）",
                "system": "系统代理模式",
                "custom": "自定义代理"
            }
            st.metric("代理模式", mode_map.get(config_info['mode'], '未知'))
            st.metric("HTTP代理", config_info.get('http_proxy', '未设置'))
        with col2:
            st.metric("HTTPS代理", config_info.get('https_proxy', '未设置'))
            st.metric("NO_PROXY", config_info.get('no_proxy', '未设置'))

        # 显示健康检查状态
        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            health_status = "启用" if config_info.get('health_check_enabled') else "禁用"
            st.metric("健康检查", health_status)
        with col4:
            failure_count = config_info.get('failure_count', 0)
            max_failures = proxy_mgr.max_failures
            st.metric("失败次数", f"{failure_count}/{max_failures}")

        # 代理模式选择
        st.divider()
        st.subheader("🔧 代理模式配置")

        proxy_mode = st.radio(
            "选择代理模式",
            ["直连模式（推荐）", "系统代理模式", "自定义代理"],
            horizontal=True,
            help="直连模式可以绕过Clash等VPN，避免IP封禁"
        )

        if proxy_mode == "直连模式（推荐）":
            st.info("🛡️ 直连模式：绕过所有代理，直接使用本地宽带访问")
            st.info("💡 推荐理由：避免使用共享VPN节点导致的IP封禁")
            
            if st.button("🚀 切换到直连模式", key="switch_direct"):
                if proxy_mgr.set_direct_mode():
                    st.success("✅ 已切换到直连模式")
                    st.rerun()
                else:
                    st.error("❌ 切换失败")

        elif proxy_mode == "系统代理模式":
            st.warning("🔄 系统代理模式：使用系统配置的代理")
            st.warning("⚠️ 注意：如果使用Clash等VPN，可能会导致IP被封")
            
            if st.button("🔄 切换到系统代理", key="switch_system"):
                if proxy_mgr.set_system_proxy_mode():
                    st.success("✅ 已切换到系统代理模式")
                    st.rerun()
                else:
                    st.error("❌ 切换失败")

        elif proxy_mode == "自定义代理":
            st.info("🔗 自定义代理：使用指定的代理服务器")
            
            custom_proxy_url = st.text_input(
                "代理URL",
                placeholder="例如：http://127.0.0.1:7890",
                help="支持HTTP和HTTPS代理"
            )
            
            if st.button("🔗 应用自定义代理", key="apply_custom") and custom_proxy_url:
                if proxy_mgr.set_custom_proxy(custom_proxy_url):
                    st.success(f"✅ 已应用自定义代理: {custom_proxy_url}")
                    st.rerun()
                else:
                    st.error("❌ 应用失败")

        # 网络连接测试
        st.divider()
        st.subheader("🧪 网络连接测试")

        col5, col6 = st.columns(2)
        with col5:
            if st.button("🌐 测试百度连接", key="test_baidu"):
                with st.spinner("正在测试连接..."):
                    if proxy_mgr.test_connection("https://www.baidu.com"):
                        st.success("✅ 百度连接测试成功")
                    else:
                        st.error("❌ 百度连接测试失败")

        with col6:
            if st.button("📈 测试东方财富连接", key="test_eastmoney"):
                with st.spinner("正在测试连接..."):
                    if proxy_mgr.test_eastmoney_connection():
                        st.success("✅ 东方财富连接测试成功")
                    else:
                        st.error("❌ 东方财富连接测试失败")

        # 健康检查配置
        st.divider()
        st.subheader("🏥 健康检查配置")

        health_check_enabled = st.checkbox(
            "启用自动降级",
            value=config_info.get('health_check_enabled', True),
            help="启用后，连续失败5次将自动切换到直连模式"
        )

        if health_check_enabled:
            proxy_mgr.enable_health_check()
        else:
            proxy_mgr.disable_health_check()

        if st.button("💾 保存健康检查设置", key="save_health_check"):
            st.success("✅ 健康检查设置已保存")

        # 状态摘要
        st.divider()
        st.subheader("📋 状态摘要")
        
        with st.expander("查看详细状态", expanded=False):
            st.code(proxy_mgr.get_status_summary(), language="text")

        # 使用建议
        st.divider()
        st.subheader("💡 使用建议")

        st.markdown("""
        ### 🎯 推荐配置
        
        1. **直连模式（推荐）**
           - 适用于大多数情况
           - 避免使用共享VPN节点导致的IP封禁
           - 如果家里宽带IP被封，可以重启光猫获取新IP

        2. **手机热点（备选）**
           - 如果直连模式失败，可以尝试连接手机热点
           - 手机4G/5G网络的IP是动态的，极难被封
           - 成本为0，是最快的解封方案

        3. **国内短效代理（付费）**
           - 如果以上方案都失败，可以考虑购买国内代理
           - 推荐服务商：青果网络、阿布云、芝麻代理
           - 价格：几块钱到十几块钱（1000 IP/天）

        ### ⚠️ 注意事项
        
        - 不要使用国外代理（Smartproxy/BrightData）
        - 国外IP访问东方财富速度慢且容易被封
        - 如果使用Clash，建议关闭系统代理或使用直连模式
        - 定期检查网络连接状态，及时发现IP封禁
        """)

    elif settings_mode == "其他设置":
        st.divider()
        st.subheader("🔧 其他设置")

        auto_refresh = st.checkbox("自动刷新", value=user_prefs.get('other', '自动刷新', False))
        save_history = st.checkbox("保存历史记录", value=user_prefs.get('other', '保存历史记录', True))
        history_days = st.slider("历史记录保留天数", 7, 90, user_prefs.get('other', '历史记录保留天数', 30), 1)

        # 🆕 V19.6: 调试模式
        st.divider()
        st.subheader("🐛 调试模式")
        debug_mode = st.checkbox(
            "启用调试模式",
            value=user_prefs.get('other', '调试模式', False),
            help="启用后，战法将忽略时间限制，允许在非交易时间测试战法功能"
        )
        if debug_mode:
            st.warning("⚠️ 调试模式已启用！战法将忽略时间限制，仅在测试环境中使用。")

        if st.button("💾 保存其他设置", key="save_other_settings"):
            user_prefs.set('other', '自动刷新', auto_refresh)
            user_prefs.set('other', '保存历史记录', save_history)
            user_prefs.set('other', '历史记录保留天数', history_days)
            user_prefs.set('other', '调试模式', debug_mode)
            
            # 🆕 V19.6: 动态更新config_system的DEBUG_MODE
            try:
                import config.config_system as config
                config.DEBUG_MODE = debug_mode
                logger.info(f"DEBUG_MODE已更新为: {debug_mode}")
            except Exception as e:
                logger.warning(f"更新DEBUG_MODE失败: {e}")
            
            st.success("✅ 其他设置已保存")
            st.rerun()

    # 重置设置
    st.divider()
    if st.button("🔄 重置为默认设置", key="reset_settings"):
        user_prefs.reset_to_default()
        st.success("✅ 已重置为默认设置")