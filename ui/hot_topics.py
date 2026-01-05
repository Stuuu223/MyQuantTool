"""热点题材模块"""
import streamlit as st
import pandas as pd
from logic.algo_advanced import AdvancedAlgo
from logic.formatter import Formatter

def render_hot_topics_tab(db, config):
    st.subheader("🎯 热点题材")
    st.caption("实时检测板块异动、识别龙头股、分析题材持续度")
    st.caption("实时检测板块异动、识别龙头股、分析题材持续度")

    # 功能选择
    topic_mode = st.radio("选择功能", ["热点题材扫描", "题材持续度分析"], horizontal=True)

    if topic_mode == "热点题材扫描":
        st.divider()
        st.subheader("🔍 热点题材扫描")

        # 扫描参数
        col_topic1, col_topic2 = st.columns(2)
        with col_topic1:
            topic_limit = st.slider("扫描板块数量", 10, 50, 20, 5)
        with col_topic2:
            if st.button("🔍 开始扫描", key="scan_hot_topics_btn"):
                st.session_state.scan_hot_topics = True
                st.rerun()

        # 执行扫描
        if st.session_state.get('scan_hot_topics', False):
            with st.spinner('正在扫描热点题材...'):
                topic_result = AdvancedAlgo.scan_hot_topics(limit=topic_limit)

            if topic_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！发现 {len(topic_result['热点题材'])} 个热点题材")

                if topic_result['热点题材']:
                    # 显示热点题材列表
                    st.divider()
                    st.subheader("📊 热点题材列表")

                    for topic_name, topic_data in topic_result['热点题材'].items():
                        with st.expander(f"{topic_data['板块类型']} {topic_name} - 涨幅: {topic_data['涨跌幅']:.2f}%"):
                            # 显示板块基本信息
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("涨跌幅", f"{topic_data['涨跌幅']:.2f}%")
                            with col2:
                                st.metric("涨家数", topic_data['涨家数'])
                            with col3:
                                st.metric("跌家数", topic_data['跌家数'])
                            with col4:
                                st.metric("量比", f"{topic_data['量比']:.2f}")

                            # 显示龙头股
                            st.write("**🔥 龙头股：**")
                            for idx, stock in enumerate(topic_data['龙头股'], 1):
                                st.write(f"{idx}. {stock['名称']} ({stock['代码']}) - 涨幅: {stock['涨跌幅']:.2f}%, 成交额: {Formatter.format_amount(stock['成交额'])}")

                            # 分析题材持续度按钮
                            if st.button(f"📈 分析题材持续度", key=f"analyze_continuity_{topic_name}"):
                                st.session_state.analyze_topic = topic_name
                                st.rerun()

                            # 添加到自选股按钮
                            for stock in topic_data['龙头股']:
                                if st.button(f"⭐ 添加 {stock['名称']} 到自选", key=f"add_topic_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                else:
                    st.warning("⚠️ 未发现热点题材")
                    st.info("💡 提示：当前市场无明显热点，建议观望")
            else:
                st.error(f"❌ {topic_result['数据状态']}")
                if '说明' in topic_result:
                    st.info(f"💡 {topic_result['说明']}")
        else:
            st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的热点题材")

    elif topic_mode == "题材持续度分析":
        st.divider()
        st.subheader("📈 题材持续度分析")

        st.info("""
        **题材持续度分析：**
        - 分析题材的历史表现和持续性
        - 判断题材所处的阶段（上升期、活跃期、衰退期、震荡期）
        - 提供操作建议
        """)

        # 输入板块名称
        topic_name_input = st.text_input("输入板块名称", placeholder="如：人工智能、新能源汽车、半导体...")

        # 分析天数
        analysis_days = st.slider("分析天数", 10, 90, 30, 5)

        if st.button("📊 开始分析", key="analyze_topic_continuity"):
            if topic_name_input:
                with st.spinner(f'正在分析 {topic_name_input} 的持续度...'):
                    continuity_result = AdvancedAlgo.analyze_topic_continuity(topic_name_input, days=analysis_days)

                if continuity_result['数据状态'] == '正常':
                    # 显示持续度指标
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("平均涨跌幅", f"{continuity_result['平均涨跌幅']:.2f}%")
                    with col2:
                        st.metric("上涨概率", f"{continuity_result['上涨概率']}%")
                    with col3:
                        st.metric("波动率", f"{continuity_result['波动率']:.2f}")
                    with col4:
                        st.metric("趋势强度", f"{continuity_result['趋势强度']:.2f}")

                    # 显示当前阶段
                    st.divider()
                    st.subheader("🔄 当前阶段")
                    stage_color = {
                        "上升期": "🔥",
                        "活跃期": "🟡",
                        "衰退期": "🔴",
                        "震荡期": "🟢"
                    }
                    st.info(f"{stage_color.get(continuity_result['当前阶段'], '📊')} **{continuity_result['当前阶段']}**")

                    # 显示操作建议
                    st.subheader("💡 操作建议")
                    st.success(continuity_result['操作建议'])

                    # 显示详细指标
                    st.divider()
                    st.subheader("📊 详细指标")

                    detail_df = pd.DataFrame({
                        '指标': ['平均涨跌幅', '最大涨幅', '最大跌幅', '上涨天数', '总天数', '上涨概率', '波动率', '趋势强度'],
                        '数值': [
                            f"{continuity_result['平均涨跌幅']:.2f}%",
                            f"{continuity_result['最大涨幅']:.2f}%",
                            f"{continuity_result['最大跌幅']:.2f}%",
                            continuity_result['上涨天数'],
                            continuity_result['总天数'],
                            f"{continuity_result['上涨概率']}%",
                            continuity_result['波动率'],
                            continuity_result['趋势强度']
                        ]
                    })
                    st.dataframe(detail_df, width="stretch", hide_index=True)
                else:
                    st.error(f"❌ {continuity_result['数据状态']}")
                    if '说明' in continuity_result:
                        st.info(f"💡 {continuity_result['说明']}")
            else:
                st.warning("⚠️ 请输入板块名称")

