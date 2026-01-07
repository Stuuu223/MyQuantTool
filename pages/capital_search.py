"""
智能搜索页面
提供多维度的游资操作查询功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter
from logic.logger import get_logger

logger = get_logger(__name__)


def search_with_filters(query: str, date_range: tuple, operation_type: list, sector: list, fund_range: tuple):
    """
    根据过滤条件搜索游资操作

    Args:
        query: 搜索查询
        date_range: 日期范围
        operation_type: 操作类型
        sector: 行业板块
        fund_range: 资金量级

    Returns:
        搜索结果 DataFrame
    """
    # 这里实现搜索逻辑
    # 暂时返回空 DataFrame
    return pd.DataFrame()


def render_search_page():
    """渲染智能搜索页面"""

    # 页面配置
    st.set_page_config(
        page_title="智能搜索",
        layout="wide"
    )

    st.title("🔍 游资操作智能搜索")
    st.caption("支持模糊匹配和多条件过滤")

    # 搜索框 - 模糊匹配
    st.subheader("📝 搜索查询")

    search_query = st.text_input(
        "输入游资名称/股票代码/营业部（支持模糊匹配）",
        placeholder="如：章盟主、000001、北京中关村",
        help="输入关键词，系统将自动匹配相关结果"
    )

    # 高级过滤
    with st.expander("⚙️ 高级过滤条件"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**📅 日期范围**")
            date_start = st.date_input("开始日期", value=datetime.now().date() - timedelta(days=30))
            date_end = st.date_input("结束日期", value=datetime.now().date())

        with col2:
            st.write("**💰 操作类型**")
            operation_type = st.multiselect(
                "操作类型",
                ["买入", "卖出", "净买入", "净卖出"],
                default=["买入", "卖出"]
            )

            st.write("**💵 资金量级**")
            fund_range = st.slider(
                "资金量级（亿元）",
                0, 100, (10, 50),
                help="筛选指定金额范围的操作"
            )

        with col3:
            st.write("**🏭 行业板块**")
            sector = st.multiselect(
                "行业板块",
                ["新能源", "医药生物", "高端制造", "芯片半导体", "人工智能", "消费", "金融"],
                default=[]
            )

            st.write("**📊 成功率阈值**")
            win_rate = st.slider(
                "成功率阈值 (%)",
                0, 100, 60,
                help="只显示成功率高于此值的游资"
            )

    # 搜索按钮
    col_search, col_clear = st.columns([1, 1])

    with col_search:
        search_button = st.button("🔍 开始搜索", type="primary", key="search_btn")

    with col_clear:
        clear_button = st.button("🗑️ 清除条件", key="clear_btn")

    # 视图保存
    st.markdown("---")
    st.subheader("💾 视图管理")

    if 'saved_views' not in st.session_state:
        st.session_state.saved_views = []

    view_name = st.text_input("视图名称", placeholder="输入视图名称")

    col_save, col_load = st.columns(2)

    with col_save:
        if st.button("💾 保存当前查询条件", key="save_view_btn"):
            if view_name:
                st.session_state.saved_views.append({
                    'name': view_name,
                    'filters': {
                        'query': search_query,
                        'date_range': (date_start, date_end),
                        'operation_type': operation_type,
                        'sector': sector,
                        'fund_range': fund_range,
                        'win_rate': win_rate
                    },
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success(f"✅ 已保存视图: {view_name}")
            else:
                st.warning("请输入视图名称")

    with col_load:
        if st.session_state.saved_views:
            view_names = [v['name'] for v in st.session_state.saved_views]
            selected_view = st.selectbox("加载已保存的视图", options=["-- 选择视图 --"] + view_names)

            if selected_view != "-- 选择视图 --" and st.button("📂 加载视图", key="load_view_btn"):
                view = next(v for v in st.session_state.saved_views if v['name'] == selected_view)
                st.info(f"已加载视图: {view['name']}")

    # 显示已保存的视图
    if st.session_state.saved_views:
        st.write("**已保存的视图：**")
        for i, view in enumerate(st.session_state.saved_views):
            with st.expander(f"📋 {view['name']} ({view['created_at']})"):
                st.json(view['filters'])

                if st.button(f"🗑️ 删除", key=f"delete_view_{i}"):
                    st.session_state.saved_views.pop(i)
                    st.success(f"已删除视图: {view['name']}")
                    st.rerun()

    # 搜索结果
    st.markdown("---")
    st.subheader("📊 搜索结果")

    if search_button or search_query:
        with st.spinner('正在搜索...'):
            # 模糊匹配游资名称
            matched_capitals = []
            if search_query:
                for capital_name in CapitalAnalyzer.FAMOUS_CAPITALISTS.keys():
                    similarity = fuzz.ratio(search_query.lower(), capital_name.lower())
                    if similarity >= 60:  # 相似度阈值
                        matched_capitals.append({
                            '游资名称': capital_name,
                            '相似度': similarity
                        })

                # 按相似度排序
                matched_capitals.sort(key=lambda x: x['相似度'], reverse=True)

            if matched_capitals:
                st.write(f"找到 {len(matched_capitals)} 个匹配的游资：")

                # 显示匹配结果
                for match in matched_capitals:
                    with st.expander(f"🎯 {match['游资名称']} (相似度: {match['相似度']}%)"):
                        # 获取该游资的操作数据
                        days = (date_end - date_start).days
                        capital_data = CapitalAnalyzer.track_capital_pattern(
                            match['游资名称'],
                            days=days
                        )

                        if capital_data['数据状态'] == '正常':
                            operations = capital_data.get('操作记录', [])

                            if operations:
                                df_operations = pd.DataFrame(operations)

                                # 应用过滤条件
                                # 日期过滤
                                df_operations['日期'] = pd.to_datetime(df_operations['日期'])
                                df_operations = df_operations[
                                    (df_operations['日期'] >= pd.Timestamp(date_start)) &
                                    (df_operations['日期'] <= pd.Timestamp(date_end))
                                ]

                                # 操作类型过滤
                                if operation_type:
                                    mask = pd.Series(False, index=df_operations.index)
                                    if "买入" in operation_type:
                                        mask |= df_operations['买入金额'] > 0
                                    if "卖出" in operation_type:
                                        mask |= df_operations['卖出金额'] > 0
                                    df_operations = df_operations[mask]

                                # 资金量级过滤
                                min_fund, max_fund = fund_range
                                df_operations = df_operations[
                                    (df_operations['净买入'].abs() / 100000000 >= min_fund) &
                                    (df_operations['净买入'].abs() / 100000000 <= max_fund)
                                ]

                                # 显示结果
                                if not df_operations.empty:
                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        st.metric("操作次数", len(df_operations))

                                    with col2:
                                        total_buy = df_operations['买入金额'].sum() / 100000000
                                        st.metric("总买入", f"¥{total_buy:.2f}亿")

                                    with col3:
                                        total_sell = df_operations['卖出金额'].sum() / 100000000
                                        st.metric("总卖出", f"¥{total_sell:.2f}亿")

                                    # 详细数据表
                                    df_operations['买入金额(亿元)'] = (df_operations['买入金额'] / 100000000).round(2)
                                    df_operations['卖出金额(亿元)'] = (df_operations['卖出金额'] / 100000000).round(2)
                                    df_operations['净买入(亿元)'] = (df_operations['净买入'] / 100000000).round(2)

                                    display_cols = ['日期', '股票代码', '股票名称', '买入金额(亿元)', '卖出金额(亿元)', '净买入(亿元)']
                                    st.dataframe(
                                        df_operations[display_cols],
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                else:
                                    st.info("没有符合过滤条件的操作记录")
                            else:
                                st.info("该游资在指定时间段内无操作记录")
                        else:
                            st.error(f"❌ {capital_data['数据状态']}")
                            if '说明' in capital_data:
                                st.info(capital_data['说明'])
            else:
                st.info("未找到匹配的游资")
    else:
        st.info("请输入搜索关键词或设置过滤条件")

    # 页脚
    st.markdown("---")
    st.caption("💡 提示：使用模糊匹配可以快速找到相关游资，支持中文和数字")