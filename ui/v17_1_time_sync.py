#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17.1 Time-Sync - 时区校准 UI 模块
展示系统时区状态，确保所有交易时间判断都基于北京时间
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from logic.utils import Utils
from logic.time_strategy_manager import get_time_strategy_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_time_sync_panel():
    """
    渲染 V17.1 时区校准面板
    """
    st.subheader("🌐 V17.1 时区校准 (Time-Sync)")

    st.markdown("""
    **V17.1 核心功能**：
    - 🕐 统一系统时钟源，确保所有交易时间判断都基于北京时间（UTC+8）
    - 🛡️ 防止时区漂移导致的"假死"问题
    - 📊 实时显示系统时间状态和时区信息
    """)

    # 获取北京时间
    beijing_time = Utils.get_beijing_time()
    system_time = datetime.now()

    # 计算时差
    time_diff = (beijing_time - system_time.replace(tzinfo=None)).total_seconds() / 3600

    # 显示时间信息
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "系统时间",
            system_time.strftime('%H:%M:%S'),
            delta=None,
            help="本地系统时间"
        )

    with col2:
        st.metric(
            "北京时间",
            beijing_time.strftime('%H:%M:%S'),
            delta=f"{time_diff:+.1f}h" if abs(time_diff) > 0.1 else "✅ 已同步",
            delta_color="normal" if abs(time_diff) < 0.1 else "inverse",
            help="北京时间（UTC+8）"
        )

    with col3:
        st.metric(
            "时区状态",
            "✅ 正常" if abs(time_diff) < 0.1 else "⚠️ 异常",
            delta=None,
            help="系统时区是否正确"
        )

    st.markdown("---")

    # 显示时区详细信息
    with st.expander("📋 时区详细信息", expanded=False):
        st.markdown(f"""
        **系统时间**：
        - 本地时间：{system_time.strftime('%Y-%m-%d %H:%M:%S')}
        - 时区：{datetime.now().astimezone().tzinfo}

        **北京时间**：
        - 北京时间：{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}
        - 时区：Asia/Shanghai (UTC+8)

        **时差**：
        - 差异：{time_diff:.1f} 小时
        - 状态：{'✅ 正常' if abs(time_diff) < 0.1 else '⚠️ 异常 - 可能导致交易时间判断错误'}
        """)

    st.markdown("---")

    # 显示时间策略状态
    st.markdown("### ⏰ 时间策略状态")

    time_manager = get_time_strategy_manager()
    mode_info = time_manager.get_current_mode()
    next_switch = time_manager.get_next_mode_switch()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "当前模式",
            mode_info['mode_name'],
            delta=mode_info['description'],
            help=mode_info['recommendation']
        )

    with col2:
        st.metric(
            "允许买入",
            "✅" if mode_info['allow_buy'] else "❌",
            delta=None,
            help="当前模式是否允许买入"
        )

    with col3:
        st.metric(
            "下次切换",
            next_switch['next_mode_name'],
            delta=f"{next_switch['remaining_minutes']} 分钟",
            help=f"将在 {next_switch['switch_time'].strftime('%H:%M')} 切换"
        )

    st.markdown("---")

    # 显示操作建议
    st.markdown("### 📝 操作建议")
    st.info(mode_info['recommendation'])

    # 显示时区校准建议
    if abs(time_diff) >= 0.1:
        st.warning(f"""
        ⚠️ **时区异常警告**：
        - 系统时间与北京时间相差 {time_diff:.1f} 小时
        - 可能导致交易时间判断错误
        - 建议检查系统时区设置或使用 NTP 同步时间
        """)
    else:
        st.success("✅ **时区校准正常**：系统时间与北京时间已同步")

    st.markdown("---")

    # 显示时间线
    st.markdown("### 📅 今日时间线")

    # 创建时间线数据
    timeline_data = [
        {"时间": "09:25", "事件": "集合竞价开始", "模式": "进攻模式", "状态": "✅"},
        {"时间": "09:30", "事件": "开盘", "模式": "进攻模式", "状态": "✅"},
        {"时间": "10:00", "事件": "黄金半小时结束", "模式": "防守模式", "状态": "⚠️"},
        {"时间": "11:30", "事件": "午间休市", "模式": "休眠模式", "状态": "😴"},
        {"时间": "13:00", "事件": "下午开盘", "模式": "防守模式", "状态": "⚠️"},
        {"时间": "14:30", "事件": "尾盘偷袭开始", "模式": "尾盘偷袭", "状态": "🎯"},
        {"时间": "15:00", "事件": "收盘", "模式": "休眠模式", "状态": "😴"},
    ]

    timeline_df = pd.DataFrame(timeline_data)
    st.dataframe(timeline_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 显示技术说明
    with st.expander("🔧 技术实现说明", expanded=False):
        st.markdown("""
        **V17.1 时区校准实现原理**：

        1. **统一时钟源**：
           - 使用 `Utils.get_beijing_time()` 替代 `datetime.now()`
           - 自动检测系统时区并转换为北京时间（UTC+8）

        2. **关键文件修改**：
           - `logic/utils.py`: 添加 `get_beijing_time()` 方法
           - `logic/time_strategy_manager.py`: 使用北京时间判断交易时段
           - `logic/realtime_data_provider.py`: 使用北京时间进行数据新鲜度检查
           - `logic/iron_rule_monitor.py`: 使用北京时间记录监控历史

        3. **时区转换逻辑**：
           ```python
           # 优先使用 pytz
           utc_now = datetime.now(pytz.utc)
           beijing_tz = pytz.timezone('Asia/Shanghai')
           return utc_now.astimezone(beijing_tz)

           # 降级方案：手动转换
           now = datetime.now()
           if now.hour < 8:  # 可能是 UTC 时间
               now = now.replace(hour=now.hour + 8)
           return now
           ```

        4. **影响范围**：
           - ✅ 交易时段判断
           - ✅ 数据新鲜度检查
           - ✅ 时间策略管理
           - ✅ 监控历史记录
           - ✅ 所有涉及交易时间的逻辑
        """)


if __name__ == "__main__":
    # 测试
    render_time_sync_panel()