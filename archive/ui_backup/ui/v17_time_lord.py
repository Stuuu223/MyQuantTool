#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17 Time-Lord - 时间策略监控面板
显示当前时间策略和模式切换倒计时
"""

import streamlit as st
from datetime import datetime
from logic.time_strategy_manager import get_time_strategy_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_time_lord_panel():
    """
    渲染 V17 Time-Lord 时间策略监控面板
    
    功能：
    1. 显示当前交易模式
    2. 显示模式切换倒计时
    3. 显示操作建议
    4. 显示模式历史
    """
    
    st.markdown("### ⏰ V17 Time-Lord (时间领主)")
    st.caption("分时段策略：黄金半小时、垃圾时间、尾盘偷袭")
    
    try:
        # 获取时间策略管理器
        time_manager = get_time_strategy_manager()
        
        # 获取当前模式
        current_time = datetime.now()
        mode_info = time_manager.get_current_mode(current_time)
        
        # 获取下一次切换时间
        next_switch = time_manager.get_next_mode_switch(current_time)
        
        # 显示当前模式
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if mode_info['mode'].value == "AGGRESSIVE":
                st.success(f"🔥 {mode_info['mode_name']}")
            elif mode_info['mode'].value == "DEFENSIVE":
                st.warning(f"🛡️ {mode_info['mode_name']}")
            elif mode_info['mode'].value == "SNIPE":
                st.info(f"🎯 {mode_info['mode_name']}")
            else:
                st.error(f"😴 {mode_info['mode_name']}")
        
        with col2:
            st.metric(
                "允许买入",
                "✅" if mode_info['allow_buy'] else "❌",
                help="当前时间段是否允许买入"
            )
        
        with col3:
            st.metric(
                "允许卖出",
                "✅" if mode_info['allow_sell'] else "❌",
                help="当前时间段是否允许卖出"
            )
        
        # 显示模式描述和建议
        st.markdown(f"**{mode_info['description']}**")
        st.info(f"💡 {mode_info['recommendation']}")
        
        st.markdown("---")
        
        # 显示模式切换倒计时
        st.markdown("### ⏱️ 下一次模式切换")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "切换到",
                next_switch['next_mode_name'],
                delta=f"剩余 {next_switch['remaining_minutes']} 分钟"
            )
        
        with col2:
            st.metric(
                "切换时间",
                next_switch['switch_time'].strftime('%H:%M')
            )
        
        with col3:
            st.metric(
                "剩余秒数",
                f"{next_switch['remaining_seconds']} 秒"
            )
        
        st.markdown("---")
        
        # 显示模式历史
        st.markdown("### 📊 模式历史（最近 10 次）")
        
        if time_manager.mode_history:
            history_data = []
            for i, record in enumerate(reversed(time_manager.mode_history)):
                history_data.append({
                    '序号': i + 1,
                    '时间': record['timestamp'].strftime('%H:%M:%S'),
                    '模式': record['mode_name']
                })
            
            # 转换为 DataFrame
            import pandas as pd
            df = pd.DataFrame(history_data)
            
            # 显示表格
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("暂无模式历史记录")
        
        st.markdown("---")
        
        # 显示时间策略说明
        st.markdown("### 📖 时间策略说明")
        
        with st.expander("🔥 09:25 - 10:00 (黄金半小时)"):
            st.markdown("""
            **模式**: 进攻模式
            **操作**: 全功率运行，进攻模式
            **扫描间隔**: 30秒
            **建议**: 🔥 积极寻找买入机会，关注弱转强、龙虎榜反制
            """)
        
        with st.expander("🛡️ 10:00 - 14:30 (垃圾时间)"):
            st.markdown("""
            **模式**: 防守模式
            **操作**: 低功耗监控，只卖不买
            **扫描间隔**: 2分钟
            **建议**: 🛡️ 只卖不买，或者做 T，避免在震荡中被磨损
            """)
        
        with st.expander("🎯 14:30 - 15:00 (尾盘偷袭)"):
            st.markdown("""
            **模式**: 尾盘偷袭
            **操作**: 扫描首板或尾盘抢筹机会
            **扫描间隔**: 15秒
            **建议**: 🎯 扫描首板或尾盘抢筹机会，准备明日竞价
            """)
        
        with st.expander("😴 非交易时间"):
            st.markdown("""
            **模式**: 休眠模式
            **操作**: 系统休眠
            **扫描间隔**: 5分钟
            **建议**: 😴 系统休眠，等待交易时间
            """)
        
        # 刷新按钮
        if st.button("🔄 刷新时间策略"):
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ 获取时间策略失败: {e}")
        logger.error(f"获取时间策略失败: {e}")


if __name__ == "__main__":
    # 测试
    render_time_lord_panel()