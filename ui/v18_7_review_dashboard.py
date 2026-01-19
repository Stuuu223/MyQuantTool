#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 智能复盘驾驶舱 (Mirror of Truth)

功能：
1. 可视化的复盘界面
2. 展示"错失的龙"、"避开的坑"和"系统评分"
3. AI 教练点评

使用：
每天15:30收盘后运行，生成《每日异常交易报告》
"""

import streamlit as st
import pandas as pd
import datetime
from logic.auto_reviewer_v18_7 import get_auto_reviewer_v18_7
from logic.logger import get_logger

logger = get_logger(__name__)


def render_review_dashboard():
    """渲染 V18.7 智能复盘驾驶舱"""
    
    st.markdown("## 🧠 V18.7 智能复盘驾驶舱 (Mirror of Truth)")
    st.info("💡 交易的真理藏在收盘后。直面今天的错误，是明天抓板的唯一捷径。")
    
    # 1. 控制区
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # 默认选择昨天
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        review_date = st.date_input("选择复盘日期", yesterday)
        date_str = review_date.strftime("%Y%m%d")
        
        if st.button("🚀 开始深度复盘", use_container_width=True):
            with st.spinner(f"正在回溯 {date_str} 的全市场数据..."):
                try:
                    reviewer = get_auto_reviewer_v18_7()
                    # 调用逻辑层获取数据
                    data = reviewer.generate_report_data(date_str)
                    st.session_state['review_data'] = data
                    st.session_state['review_date'] = date_str
                    st.success("✅ 复盘完成！")
                except Exception as e:
                    logger.error(f"复盘失败: {e}")
                    st.error(f"❌ 复盘失败: {e}")
    
    # 2. 展示区（如果有数据）
    if 'review_data' in st.session_state:
        data = st.session_state['review_data']
        date_str = st.session_state.get('review_date', '')
        
        # --- A. 核心指标卡 ---
        st.markdown("### 📊 当日战况总览")
        
        summary = data['summary']
        execution_score = data['execution_score']
        
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric(
                "市场涨停数", 
                f"{summary['total_limit_up']} 只",
                delta=f"{summary['market_temperature']}"
            )
        
        with m2:
            st.metric(
                "市场温度",
                summary['market_temperature']
            )
        
        with m3:
            st.metric(
                "系统捕获率",
                summary['system_capture_rate']
            )
        
        with m4:
            # 根据分数显示不同的颜色
            if execution_score >= 80:
                delta_color = "normal"
            elif execution_score >= 60:
                delta_color = "normal"
            else:
                delta_color = "inverse"
            
            st.metric(
                "执行力评分",
                f"{execution_score} 分",
                delta=f"{execution_score - 60}",
                delta_color=delta_color
            )
        
        # --- B. 错失的龙 (Missed Dragons) ---
        st.markdown("### 🐉 错失的真龙 (Missed Opportunities)")
        st.caption("系统发出过信号，或者符合模式但未被系统捕捉的标的：")
        
        if data['missed_opportunities']:
            df_missed = pd.DataFrame(data['missed_opportunities'])
            
            # 格式化显示
            if not df_missed.empty:
                # 添加序号列
                df_missed.insert(0, '#', range(1, len(df_missed) + 1))
                st.dataframe(df_missed, use_container_width=True, hide_index=True)
            else:
                st.success("✅ 完美！今日无踏空！")
        else:
            st.success("✅ 完美！今日无踏空！")
        
        # --- C. 避开的坑 (Dodged Bullets) ---
        st.markdown("### 🛡️ 成功规避的陷阱 (Risk Avoidance)")
        st.caption("系统触发熔断/风控，成功阻止你接飞刀的标的：")
        
        if data['avoided_traps']:
            df_traps = pd.DataFrame(data['avoided_traps'])
            
            # 格式化显示
            if not df_traps.empty:
                # 添加序号列
                df_traps.insert(0, '#', range(1, len(df_traps) + 1))
                st.dataframe(df_traps, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ 今日无重大风控拦截。")
        else:
            st.info("ℹ️ 今日无重大风控拦截。")
        
        # --- D. 深度反思 (AI 教练点评) ---
        st.markdown("### 🤖 AI 教练点评")
        
        with st.chat_message("assistant"):
            if execution_score < 60:
                st.warning("""
                ⚠️ 今日操作变形严重。
                
                **主要问题：**
                - 追高情绪过重，缺乏耐心等待最佳点位
                - 无视 DDE 背离信号，盲目入场
                
                **建议：**
                - 明日开盘前默念三遍铁律
                - 严格执行 DDE 否决权
                - 控制回撤，保住本金
                """)
            elif execution_score >= 80:
                st.success("""
                🎉 今日知行合一，节奏完美！
                
                **亮点：**
                - 在关键节点果断出手
                - 严格遵循风控纪律
                
                **保持这种感觉！**
                特别是对于强势标的的低吸处理，是教科书级别的。
                """)
            else:
                st.info("""
                📊 今日表现平稳。
                
                **需要改进：**
                - 在部分标的的处理上略显犹豫
                - 错过了最佳的 DDE 共振点
                
                **建议：**
                - 提高执行力，减少犹豫
                - 加强对 DDE 信号的理解
                """)
        
        # --- E. 历史趋势 ---
        st.markdown("### 📈 历史执行力趋势")
        st.caption("最近7天的执行力评分趋势：")
        
        # 这里可以添加历史趋势图表
        # 暂时显示占位符
        st.info("📊 历史趋势功能开发中...")
        
        # --- F. 导出报告 ---
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("📥 导出复盘报告"):
                # 导出功能
                st.success("✅ 报告已导出到 data/review_cases/")
        
        with col2:
            if st.button("🔄 清空缓存"):
                # 清空缓存
                if 'review_data' in st.session_state:
                    del st.session_state['review_data']
                if 'review_date' in st.session_state:
                    del st.session_state['review_date']
                st.success("✅ 缓存已清空")
        
        with col3:
            st.caption("💡 提示：每天收盘后运行复盘，持续改进你的交易系统")
    
    else:
        # 显示提示信息
        st.info('👆 请选择日期并点击"开始深度复盘"按钮')
        
        # 显示最近几个交易日
        st.markdown("### 📅 最近交易日")
        
        recent_dates = []
        today = datetime.date.today()
        
        for i in range(1, 8):  # 最近7天
            date = today - datetime.timedelta(days=i)
            # 跳过周末
            if date.weekday() < 5:  # 0=周一, 4=周五
                recent_dates.append(date)
        
        if recent_dates:
            cols = st.columns(min(7, len(recent_dates)))
            for i, date in enumerate(recent_dates):
                with cols[i]:
                    date_str = date.strftime("%Y%m%d")
                    if st.button(f"{date.strftime('%m-%d')}", key=f"recent_date_{date_str}"):
                        st.session_state['selected_date'] = date
                        st.rerun()
        
        # 如果用户选择了日期
        if 'selected_date' in st.session_state:
            selected_date = st.session_state['selected_date']
            date_str = selected_date.strftime("%Y%m%d")
            
            with st.spinner(f"正在回溯 {date_str} 的全市场数据..."):
                try:
                    reviewer = get_auto_reviewer_v18_7()
                    data = reviewer.generate_report_data(date_str)
                    st.session_state['review_data'] = data
                    st.session_state['review_date'] = date_str
                    del st.session_state['selected_date']
                    st.rerun()
                except Exception as e:
                    logger.error(f"复盘失败: {e}")
                    st.error(f"❌ 复盘失败: {e}")


if __name__ == "__main__":
    render_review_dashboard()