"""游资席位模块"""
import streamlit as st
import pandas as pd
from logic.formatter import Formatter

def render_capital_tab(db, config):
    st.subheader("💰 游资席位分析")
    st.caption("分析龙虎榜游资、追踪操作模式、识别知名游资")

    # 导入游资分析器
    from logic.algo_capital import CapitalAnalyzer

    # 功能选择
    capital_mode = st.radio("选择功能", ["龙虎榜游资分析", "游资操作模式追踪", "游资下一步预测"], horizontal=True)

    if capital_mode == "龙虎榜游资分析":
        st.divider()
        st.subheader("🏆 龙虎榜游资分析")

        st.info("💡 分析当日龙虎榜中的游资席位操作")

        # 日期选择
        analysis_date = st.date_input("分析日期", value=pd.Timestamp.now(), key="capital_date")

        if st.button("🔍 分析龙虎榜", key="analyze_lhb_capital"):
            with st.spinner('正在分析龙虎榜游资...'):
                date_str = analysis_date.strftime("%Y%m%d")
                capital_result = CapitalAnalyzer.analyze_longhubu_capital(date=date_str)

            if capital_result['数据状态'] == '正常':
                # 检查返回的数据类型
                if '龙虎榜股票' in capital_result:
                    # 返回的是龙虎榜股票列表（无营业部信息）
                    st.success(f"✅ 分析完成！共发现 {capital_result['股票数量']} 只龙虎榜股票")
                    st.info(capital_result.get('说明', ''))

                    # 显示龙虎榜股票列表
                    if capital_result['龙虎榜股票']:
                        st.divider()
                        st.subheader("📊 龙虎榜股票列表")

                        stock_df = pd.DataFrame(capital_result['龙虎榜股票'])
                        st.dataframe(stock_df, width="stretch", hide_index=True)
                elif '活跃营业部' in capital_result:
                    # 返回的是活跃营业部数据
                    st.success(f"✅ 分析完成！共发现 {capital_result['营业部数量']} 个活跃营业部")
                    st.info(capital_result.get('说明', ''))

                    # 显示活跃营业部列表
                    if capital_result['活跃营业部'] is not None and not capital_result['活跃营业部'].empty:
                        st.divider()
                        st.subheader("🏪 活跃营业部")

                        yyb_df = capital_result['活跃营业部'].head(20)
                        st.dataframe(yyb_df, width="stretch", hide_index=True)
                else:
                    # 返回的是游资分析结果
                    active_capital_count = capital_result.get('游资数量', 0)
                    total_operations = capital_result.get('匹配记录数', 0)
                    st.success(f"✅ 分析完成！发现 {active_capital_count} 个活跃游资，共 {total_operations} 次操作")

                    # 显示游资统计汇总
                    if capital_result.get('游资统计'):
                        st.divider()
                        st.subheader("📊 游资统计汇总")

                        summary_df = pd.DataFrame(capital_result['游资统计'])
                        st.dataframe(summary_df, width="stretch", hide_index=True)

                    # 显示详细操作记录
                    if capital_result.get('游资操作记录'):
                        st.divider()
                        st.subheader("📝 详细操作记录")

                        for record in capital_result['游资操作记录'][:20]:  # 只显示前20条
                            with st.expander(f"{record['游资名称']} - {record['股票名称']} ({record['股票代码']})"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("买入金额", Formatter.format_amount(record['买入金额']))
                                with col2:
                                    st.metric("卖出金额", Formatter.format_amount(record['卖出金额']))
                                with col3:
                                    st.metric("净买入", Formatter.format_amount(record['净买入']))
                                st.write(f"**上榜日：** {record['上榜日']}")
                                st.write(f"**营业部：** {record['营业部名称']}")
                    else:
                        st.info("👍 今日龙虎榜中无知名游资操作")
            else:
                st.error(f"❌ {capital_result['数据状态']}")
                if '说明' in capital_result:
                    st.info(f"💡 {capital_result['说明']}")

    elif capital_mode == "游资操作模式追踪":
        st.divider()
        st.subheader("📈 游资操作模式追踪")

        st.info("💡 追踪特定游资在指定时间内的操作规律")

        # 游资选择
        capital_name = st.selectbox("选择游资", list(CapitalAnalyzer.FAMOUS_CAPITALISTS.keys()), key="select_capital")

        # 分析天数
        track_days = st.slider("分析天数", 7, 90, 30, 1)

        if st.button("📊 追踪操作模式", key="track_capital_pattern"):
            with st.spinner(f'正在追踪 {capital_name} 的操作模式...'):
                pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=track_days)

            if pattern_result['数据状态'] == '正常':
                st.success(f"✅ 追踪完成！{capital_name} 在最近 {track_days} 天内有 {pattern_result['操作次数']} 次操作")

                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("操作次数", pattern_result['操作次数'])
                with col2:
                    st.metric("操作频率", f"{pattern_result['操作频率']:.2f}次/天")
                with col3:
                    st.metric("买入比例", f"{pattern_result['买入比例']}%")
                with col4:
                    st.metric("操作成功率", f"{pattern_result['操作成功率']}%")

                # 显示操作风格
                st.divider()
                st.write("**🎭 操作风格：**")
                st.info(pattern_result['操作风格'])

                # 显示资金流向
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总买入金额", Formatter.format_amount(pattern_result['总买入金额']))
                with col2:
                    st.metric("总卖出金额", Formatter.format_amount(pattern_result['总卖出金额']))
                # 显示操作记录
                if pattern_result['操作记录']:
                    st.divider()
                    st.subheader("📝 操作记录")

                    for record in pattern_result['操作记录'][-10:]:  # 只显示最近10条
                        with st.expander(f"{record['日期']} - {record['股票名称']} ({record['股票代码']})"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("买入金额", Formatter.format_amount(record['买入金额']))
                            with col2:
                                st.metric("卖出金额", Formatter.format_amount(record['卖出金额']))
                            with col3:
                                st.metric("净买入", Formatter.format_amount(record['净买入']))
            else:
                st.error(f"❌ {pattern_result['数据状态']}")
                if '说明' in pattern_result:
                    st.info(f"💡 {pattern_result['说明']}")

    elif capital_mode == "游资下一步预测":
        st.divider()
        st.subheader("🔮 游资下一步预测")

        st.info("💡 基于历史操作模式预测游资下一步操作")

        # 游资选择
        predict_capital = st.selectbox("选择游资", list(CapitalAnalyzer.FAMOUS_CAPITALISTS.keys()), key="predict_capital")

        if st.button("🔮 预测下一步操作", key="predict_capital_next"):
            with st.spinner(f'正在预测 {predict_capital} 的下一步操作...'):
                prediction_result = CapitalAnalyzer.predict_capital_next_move(predict_capital)

            if prediction_result['数据状态'] == '正常':
                st.success(f"✅ 预测完成！")

                # 显示预测结果
                for prediction in prediction_result['预测列表']:
                    level_color = {
                        '高': '🔥',
                        '中': '🟡',
                        '低': '🟢'
                    }
                    with st.expander(f"{level_color.get(prediction['概率'], '⚪')} {prediction['预测类型']} - {prediction['概率']}"):
                        st.write(f"**说明：** {prediction['说明']}")
            else:
                st.error(f"❌ {prediction_result['数据状态']}")
                if '说明' in prediction_result:
                    st.info(f"💡 {prediction_result['说明']}")

