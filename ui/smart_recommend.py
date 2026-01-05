"""智能推荐模块"""
import streamlit as st
import pandas as pd

def render_smart_recommend_tab(db, config):
    st.subheader("🤖 智能推荐")
    st.subheader("🤖 智能推荐系统")
    st.caption("根据市场行情自动推荐相关战法")

    # 导入智能推荐器
    from logic.smart_recommender import SmartRecommender

    # 功能选择
    smart_mode = st.radio("选择功能", ["每日报告", "战法推荐", "市场分析"], horizontal=True)

    if smart_mode == "每日报告":
        st.divider()
        st.subheader("📊 每日报告")

        if st.button("📊 生成今日报告", key="generate_daily_report"):
            with st.spinner('正在生成今日报告...'):
                report = SmartRecommender.generate_daily_report()

            if '日期' in report:
                st.success(f"✅ 报告生成成功！")

                # 显示市场情绪
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("市场情绪", report['市场情绪'])
                with col2:
                    st.metric("平均涨跌幅", report['市场数据']['平均涨跌幅'])
                with col3:
                    st.metric("涨跌比", report['市场数据']['涨跌比'])

                # 显示情绪描述
                st.divider()
                st.write("**📝 情绪描述：**")
                st.info(report['情绪描述'])

                # 显示操作建议
                st.divider()
                st.write("**💡 操作建议：**")
                st.success(report['操作建议'])

                # 显示推荐战法
                if report['推荐战法']:
                    st.divider()
                    st.subheader("🎯 推荐战法")

                    for strategy in report['推荐战法']:
                        priority_color = {
                            '高': '🔥',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{priority_color.get(strategy['优先级'], '⚪')} {strategy['战法名称']} - {strategy['优先级']}"):
                            st.write(f"**推荐理由：** {strategy['推荐理由']}")
                            st.write(f"**适用场景：** {strategy['适用场景']}")
            else:
                st.error(f"❌ {report.get('数据状态', '生成失败')}")
                if '说明' in report:
                    st.info(f"💡 {report['说明']}")

    elif smart_mode == "战法推荐":
        st.divider()
        st.subheader("🎯 战法推荐")

        st.info("💡 根据当前市场情况推荐最适合的战法")

        if st.button("🎯 获取推荐", key="get_strategy_recommendations"):
            with st.spinner('正在分析市场并推荐战法...'):
                # 分析市场情况
                market_condition = SmartRecommender.analyze_market_condition()

                if market_condition['数据状态'] == '正常':
                    # 推荐战法
                    recommendations = SmartRecommender.recommend_strategies(market_condition)

                    st.success(f"✅ 分析完成！为您推荐 {recommendations['推荐数量']} 个战法")

                    # 显示市场情况
                    st.divider()
                    st.subheader("📊 市场情况")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("市场情绪", market_condition['市场情绪'])
                    with col2:
                        st.metric("涨跌比", market_condition['涨跌比'])
                    with col3:
                        st.metric("涨停数", market_condition['涨停股票'])
                    with col4:
                        st.metric("跌停数", market_condition['跌停股票'])

                    # 显示推荐战法
                    st.divider()
                    for strategy in recommendations['推荐列表']:
                        priority_color = {
                            '高': '🔥',
                            '中': '🟡',
                            '低': '🟢'
                        }
                        with st.expander(f"{priority_color.get(strategy['优先级'], '⚪')} {strategy['战法名称']} - {strategy['优先级']}"):
                            st.write(f"**推荐理由：** {strategy['推荐理由']}")
                            st.write(f"**适用场景：** {strategy['适用场景']}")
                else:
                    st.error(f"❌ {market_condition['数据状态']}")
                    if '说明' in market_condition:
                        st.info(f"💡 {market_condition['说明']}")

    elif smart_mode == "市场分析":
        st.divider()
        st.subheader("📈 市场分析")

        if st.button("📊 分析市场", key="analyze_market"):
            with st.spinner('正在分析市场...'):
                market_condition = SmartRecommender.analyze_market_condition()

            if market_condition['数据状态'] == '正常':
                st.success("✅ 分析完成！")

                # 显示市场指标
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("总股票数", market_condition['总股票数'])
                with col2:
                    st.metric("上涨股票", market_condition['上涨股票'])
                with col3:
                    st.metric("下跌股票", market_condition['下跌股票'])
                with col4:
                    st.metric("涨停股票", market_condition['涨停股票'])
                with col5:
                    st.metric("跌停股票", market_condition['跌停股票'])

                # 显示详细数据
                st.divider()
                st.subheader("📊 详细数据")

                market_df = pd.DataFrame({
                    '指标': ['市场情绪', '涨跌比', '平均涨跌幅', '涨停数', '跌停数'],
                    '数值': [
                        market_condition['市场情绪'],
                        market_condition['涨跌比'],
                        f"{market_condition['平均涨跌幅']}%",
                        market_condition['涨停股票'],
                        market_condition['跌停股票']
                    ]
                })
                st.dataframe(market_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {market_condition['数据状态']}")
                if '说明' in market_condition:
                    st.info(f"💡 {market_condition['说明']}")

