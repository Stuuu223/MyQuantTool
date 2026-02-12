"""历史记录模块"""
import streamlit as st
import pandas as pd

def render_history_tab(db, config):
    st.subheader("📜 历史记录")
    st.caption("查看和导出分析历史")

    # 导入历史记录管理器
    from logic.history_manager import HistoryManager

    history_manager = HistoryManager()

    # 功能选择
    history_mode = st.radio("选择功能", ["查看历史", "导出记录", "清理旧记录"], horizontal=True)

    if history_mode == "查看历史":
        st.divider()
        st.subheader("📋 查看历史")

        # 筛选条件
        col1, col2, col3 = st.columns(3)
        with col1:
            analysis_type = st.selectbox("分析类型", ["全部", "单股分析", "热点题材", "智能预警", "量价关系"])
        with col2:
            history_symbol = st.text_input("股票代码（可选）", key="history_symbol")
        with col3:
            history_limit = st.slider("显示数量", 5, 50, 10, 5)

        if st.button("🔍 查询", key="query_history"):
            type_filter = None if analysis_type == "全部" else analysis_type
            symbol_filter = None if not history_symbol else history_symbol

            history_result = history_manager.get_history(type_filter, symbol_filter, history_limit)

            if history_result['状态'] == '成功':
                st.success(f"✅ 找到 {history_result['记录数量']} 条记录")

                if history_result['记录列表']:
                    for record in history_result['记录列表']:
                        with st.expander(f"{record['timestamp']} - {record['analysis_type']} - {record['symbol']}"):
                            st.json(record['result'])
                else:
                    st.info("👍 暂无历史记录")
            else:
                st.error(f"❌ {history_result['状态']}")
                if '错误信息' in history_result:
                    st.info(f"💡 {history_result['错误信息']}")

    elif history_mode == "导出记录":
        st.divider()
        st.subheader("📤 导出记录")

        # 筛选条件
        col1, col2 = st.columns(2)
        with col1:
            export_type = st.selectbox("分析类型", ["单股分析", "热点题材", "智能预警", "量价关系"])
        with col2:
            export_symbol = st.text_input("股票代码（可选）", key="export_symbol")

        if st.button("📤 导出Excel", key="export_history"):
            symbol_filter = None if not export_symbol else export_symbol
            export_result = history_manager.export_to_excel(export_type, symbol_filter)

            if export_result['状态'] == '成功':
                st.success(f"✅ 导出成功！共 {export_result['记录数量']} 条记录")
                st.info(f"📁 文件路径：{export_result['文件路径']}")
            else:
                st.error(f"❌ {export_result['状态']}")
                if '说明' in export_result:
                    st.info(f"💡 {export_result['说明']}")

    elif history_mode == "清理旧记录":
        st.divider()
        st.subheader("🗑️ 清理旧记录")

        keep_days = st.slider("保留天数", 7, 90, 30, 1)

        if st.button("🗑️ 清理", key="clear_old_history"):
            clear_result = history_manager.clear_old_history(keep_days)

            if clear_result['状态'] == '成功':
                st.success(f"✅ 清理完成！删除了 {clear_result['删除数量']} 条记录")
            else:
                st.error(f"❌ {clear_result['状态']}")

