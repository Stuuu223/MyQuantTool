"""
实时监控仪表板页面
提供多维度的游资和龙虎榜监控功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from logic.visualizers import (
    plot_capital_sankey,
    plot_capital_timeline,
    plot_activity_heatmap,
    plot_performance_timeseries
)
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter
from logic.logger import get_logger

logger = get_logger(__name__)


def get_capital_list():
    """获取游资列表"""
    return list(CapitalAnalyzer.FAMOUS_CAPITALISTS.keys())


def render_dashboard():
    """渲染实时监控仪表板"""

    # 页面配置
    st.set_page_config(
        page_title="实时监控",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📊 实时监控仪表板")
    st.caption("多维度监控游资动向和龙虎榜数据")

    # 左侧过滤器
    with st.sidebar:
        st.header("📊 监控设置")

        # 日期范围选择
        st.subheader("📅 日期范围")
        end_date = st.date_input("结束日期", value=datetime.now().date())
        days_back = st.slider("回溯天数", 7, 90, 30)
        start_date = end_date - timedelta(days=days_back)

        # 游资选择
        st.subheader("💰 游资选择")
        selected_capital = st.multiselect(
            "选择游资",
            options=get_capital_list(),
            default=['章盟主', '方新侠']
        )

        # 过滤条件
        st.subheader("⚙️ 过滤条件")

        # 资金量级
        fund_range = st.slider(
            "资金量级（亿元）",
            0, 100, (10, 50)
        )

        # 行业板块
        sector_filter = st.selectbox(
            "行业板块",
            options=['全部', '新能源', '医药生物', '高端制造', '芯片半导体', '人工智能', '消费']
        )

        # 数据刷新
        st.markdown("---")
        if st.button("🔄 刷新数据", key="monitor_refresh"):
            st.rerun()

        # 缓存统计
        if st.checkbox("显示缓存统计"):
            from logic.algo_capital import DiskCacheManager
            cache = DiskCacheManager()
            stats = cache.get_stats()
            st.json(stats)

    # 主内容区
    st.markdown("---")

    # 核心指标行
    st.subheader("📈 核心指标")

    # 获取数据
    with st.spinner('正在加载数据...'):
        # 获取龙虎榜数据
        from logic.algo import QuantAlgo
        lhb_data = QuantAlgo.get_lhb_data(end_date.strftime("%Y%m%d"))

        if lhb_data['数据状态'] == '正常':
            stocks = lhb_data['股票列表']

            # 计算指标
            total_stocks = len(stocks)
            total_net_buy = sum(s['龙虎榜净买入'] for s in stocks)
            avg_amount = total_net_buy / total_stocks if total_stocks > 0 else 0

            # 显示指标
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "龙虎榜股票数",
                    f"{total_stocks} 只",
                    delta="今日上榜"
                )

            with col2:
                st.metric(
                    "净买入总额",
                    Formatter.format_amount(total_net_buy),
                    delta=f"¥{avg_amount/100000000:.2f}亿/股"
                )

            with col3:
                st.metric(
                    "监控游资数",
                    f"{len(selected_capital)} 个",
                    delta=f"活跃追踪"
                )

            with col4:
                st.metric(
                    "数据日期",
                    end_date.strftime("%Y-%m-%d"),
                    delta=f"近{days_back}天"
                )
        else:
            st.error(f"❌ {lhb_data['数据状态']}")
            if '说明' in lhb_data:
                st.info(lhb_data['说明'])

    st.markdown("---")

    # 上行：资金流向 Sankey 和时间轴
    st.subheader("💰 资金流向追踪")

    if selected_capital:
        col1, col2 = st.columns(2)

        # 获取游资追踪数据
        with st.spinner('正在获取游资数据...'):
            capital_data = CapitalAnalyzer.track_capital_pattern(
                selected_capital[0],
                days=days_back
            )

            if capital_data['数据状态'] == '正常':
                operations = capital_data.get('操作记录', [])

                if operations:
                    df_operations = pd.DataFrame(operations)

                    # Sankey 图
                    with col1:
                        fig_sankey = plot_capital_sankey(df_operations, selected_capital[0])
                        if fig_sankey:
                            st.plotly_chart(fig_sankey, use_container_width=True)
                        else:
                            st.info("暂无资金流向数据")

                    # 时间轴图
                    with col2:
                        fig_timeline = plot_capital_timeline(df_operations, selected_capital[0])
                        if fig_timeline:
                            st.plotly_chart(fig_timeline, use_container_width=True)
                        else:
                            st.info("暂无时间轴数据")
                else:
                    st.info("暂无操作记录")
            else:
                st.error(f"❌ {capital_data['数据状态']}")
                if '说明' in capital_data:
                    st.info(capital_data['说明'])
    else:
        st.info("请选择要监控的游资")

    st.markdown("---")

    # 中行：活跃度热力图和业绩表现
    st.subheader("📊 活跃度与业绩分析")

    if selected_capital:
        col1, col2 = st.columns(2)

        with col1:
            st.write("**游资活跃度热力图**")
            with st.spinner('正在生成活跃度热力图...'):
                if capital_data['数据状态'] == '正常':
                    df_operations = pd.DataFrame(capital_data.get('操作记录', []))
                    if not df_operations.empty:
                        fig_heatmap = plot_activity_heatmap(df_operations, by='day')
                        if fig_heatmap:
                            st.plotly_chart(fig_heatmap, use_container_width=True)
                        else:
                            st.info("暂无活跃度数据")
                    else:
                        st.info("暂无操作记录")

        with col2:
            st.write("**业绩表现趋势**")
            with st.spinner('正在生成业绩趋势图...'):
                if capital_data['数据状态'] == '正常':
                    df_operations = pd.DataFrame(capital_data.get('操作记录', []))
                    if not df_operations.empty:
                        fig_performance = plot_performance_timeseries(df_operations, selected_capital[0])
                        if fig_performance:
                            st.plotly_chart(fig_performance, use_container_width=True)
                        else:
                            st.info("暂无业绩数据")
                    else:
                        st.info("暂无操作记录")
    else:
        st.info("请选择要监控的游资")

    st.markdown("---")

    # 下行：详细操作明细
    st.subheader("📋 详细操作明细")

    if selected_capital and capital_data['数据状态'] == '正常':
        operations = capital_data.get('操作记录', [])

        if operations:
            df_details = pd.DataFrame(operations)

            # 格式化金额
            df_details['买入金额(亿元)'] = (df_details['买入金额'] / 100000000).round(2)
            df_details['卖出金额(亿元)'] = (df_details['卖出金额'] / 100000000).round(2)
            df_details['净买入(亿元)'] = (df_details['净买入'] / 100000000).round(2)

            # 显示数据表
            display_cols = ['日期', '股票代码', '股票名称', '买入金额(亿元)', '卖出金额(亿元)', '净买入(亿元)']
            st.dataframe(
                df_details[display_cols],
                use_container_width=True,
                hide_index=True
            )

            # 数据下载
            csv = df_details.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 下载 CSV",
                data=csv,
                file_name=f'capital_operations_{selected_capital[0]}_{end_date}.csv',
                mime='text/csv'
            )
        else:
            st.info("暂无操作记录")
    else:
        st.info("请选择要监控的游资")

    # 页脚
    st.markdown("---")
    st.caption("💡 提示：数据每5分钟自动刷新，点击刷新按钮可立即更新")