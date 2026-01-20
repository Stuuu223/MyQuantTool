# -*- coding: utf-8 -*-
"""
盘前预计算缓存管理UI模块

功能：
- 显示缓存状态
- 手动触发预计算
- 清空缓存
- 查看缓存统计信息

Author: iFlow CLI
Version: V19.1
"""

import streamlit as st
from logic.pre_market_cache import get_pre_market_cache, auto_precompute_if_needed
from logic.logger import get_logger

logger = get_logger(__name__)


def render_pre_market_cache_tab():
    """
    渲染盘前预计算缓存管理标签页
    """
    st.markdown("## 📊 盘前预计算缓存管理")
    st.info("""
    💡 **功能说明**：
    - 盘前预计算所有股票的MA4，存入缓存
    - 盘中实时计算MA5时无需下载历史数据，避免系统卡顿
    - 公式：Realtime_MA5 = (Pre_Market_MA4 * 4 + Current_Price) / 5
    """)

    # 获取缓存实例
    cache = get_pre_market_cache()

    # 显示缓存状态
    st.divider()
    st.subheader("📈 缓存状态")

    # 获取缓存统计信息
    stats = cache.get_cache_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("缓存股票数量", f"{stats['total_stocks']} 只")

    with col2:
        cache_time_str = stats['cache_time'] if stats['cache_time'] else "未缓存"
        st.metric("缓存时间", cache_time_str)

    with col3:
        status = "✅ 有效" if stats['cache_valid'] else "❌ 无效"
        st.metric("缓存状态", status)

    with col4:
        expired = "⚠️ 已过期" if stats['is_expired'] else "✅ 未过期"
        st.metric("是否过期", expired)

    # 缓存详情
    if stats['cache_valid'] and stats['total_stocks'] > 0:
        st.success(f"✅ 缓存有效，包含 {stats['total_stocks']} 只股票的MA4数据")
    else:
        st.warning("⚠️ 缓存无效或为空，建议执行预计算")

    # 操作区域
    st.divider()
    st.subheader("🔧 缓存操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 执行预计算", use_container_width=True):
            with st.spinner("🔄 正在预计算MA4，请稍候..."):
                success_count = cache.precompute_ma4(max_stocks=1000)
                if success_count > 0:
                    st.success(f"✅ 预计算完成！成功计算 {success_count} 只股票")
                    st.rerun()
                else:
                    st.error("❌ 预计算失败，请查看日志")

    with col2:
        if st.button("🗑️ 清空缓存", use_container_width=True):
            cache.clear_cache()
            st.success("✅ 缓存已清空")
            st.rerun()

    with col3:
        if st.button("🔄 自动预计算", use_container_width=True):
            executed = auto_precompute_if_needed(max_stocks=1000)
            if executed:
                st.info("ℹ️ 已触发自动预计算")
            else:
                st.info("ℹ️ 当前时间不需要自动预计算")

    # 高级选项
    st.divider()
    st.subheader("⚙️ 高级选项")

    with st.expander("查看缓存详情"):
        if stats['total_stocks'] > 0:
            st.write(f"**缓存股票列表（前100只）：**")
            stock_list = list(cache.ma4_cache.keys())[:100]
            for i, code in enumerate(stock_list, 1):
                ma4 = cache.ma4_cache[code]
                st.write(f"{i}. {code}: MA4 = {ma4:.2f}")

            if stats['total_stocks'] > 100:
                st.info(f"ℹ️ 还有 {stats['total_stocks'] - 100} 只股票未显示")
        else:
            st.info("缓存为空")

    # 测试功能
    st.divider()
    st.subheader("🧪 测试功能")

    test_code = st.text_input("输入股票代码进行测试", value="000001")

    if st.button("🔍 测试MA5计算"):
        if test_code:
            try:
                # 模拟当前价格
                current_price = st.number_input("当前价格", value=10.0, step=0.01)

                # 计算MA5
                ma5 = cache.calculate_ma5_realtime(test_code, current_price)

                # 计算乖离率
                bias = cache.calculate_bias_realtime(test_code, current_price)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("当前价格", f"¥{current_price:.2f}")

                with col2:
                    if ma5 is not None:
                        st.metric("实时MA5", f"{ma5:.2f}")
                    else:
                        st.metric("实时MA5", "N/A")

                with col3:
                    if bias is not None:
                        st.metric("乖离率", f"{bias:.2f}%")
                    else:
                        st.metric("乖离率", "N/A")

                if ma5 is None:
                    st.warning(f"⚠️ 股票 {test_code} 的MA4不在缓存中，请先执行预计算")

            except Exception as e:
                st.error(f"❌ 测试失败: {e}")

    # 使用说明
    st.divider()
    st.subheader("📖 使用说明")

    st.markdown("""
    ### 何时执行预计算？

    - **盘前（9:25之前）**：建议在9:25之前执行一次预计算，获取全市场股票的MA4
    - **缓存过期后**：如果缓存超过24小时，建议重新执行预计算
    - **手动触发**：随时可以手动点击"执行预计算"按钮更新缓存

    ### 预计算的好处？

    1. **避免盘中卡顿**：盘中不需要下载历史数据，纯数学计算，耗时极短（0.000001秒）
    2. **降低网络压力**：避免盘中大量请求历史数据，减少被限流的风险
    3. **提升系统稳定性**：防止因网络波动导致系统卡顿或崩溃

    ### 注意事项

    - 预计算需要一定时间（取决于股票数量和网络速度）
    - 建议在非交易时间执行预计算
    - 缓存有效期为24小时，过期后需要重新计算
    """)