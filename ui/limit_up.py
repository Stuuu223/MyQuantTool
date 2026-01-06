"""打板预测模块"""
import streamlit as st
import pandas as pd

def render_limit_up_tab(db, config):
    st.subheader("🎯 打板成功率预测")
    st.caption("基于历史数据预测次日打板成功率")

    # 导入打板预测器
    from logic.algo_limit_up import LimitUpPredictor

    # 功能选择
    limit_up_mode = st.radio("选择功能", ["单股打板预测", "自选股批量预测", "市场整体分析"], horizontal=True)

    if limit_up_mode == "单股打板预测":
        st.divider()
        st.subheader("📊 单股打板预测")

        # 股票代码输入
        limit_up_symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="limit_up_symbol")

        if st.button("📊 预测打板成功率", key="predict_limit_up"):
            with st.spinner('正在预测打板成功率...'):
                prediction_result = LimitUpPredictor.predict_limit_up_success_rate(limit_up_symbol)

            if prediction_result['数据状态'] == '正常':
                st.success(f"✅ 预测完成！该股票历史涨停 {prediction_result['总涨停次数']} 次")

                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总涨停次数", prediction_result['总涨停次数'])
                with col2:
                    st.metric("成功率", f"{prediction_result['成功率']}%")
                with col3:
                    st.metric("综合评分", prediction_result['综合评分'])
                with col4:
                    st.metric("评级", prediction_result['评级'])

                # 显示操作建议
                st.divider()
                st.write("**💡 操作建议：**")
                st.success(prediction_result['操作建议'])

                # 显示影响因素
                if prediction_result['影响因素']:
                    st.divider()
                    st.subheader("📊 影响因素")

                    factor_df = pd.DataFrame(prediction_result['影响因素'])
                    st.dataframe(factor_df, width="stretch", hide_index=True)

                # 显示涨停记录
                if prediction_result['涨停记录']:
                    st.divider()
                    st.subheader("📝 最近涨停记录")

                    record_df = pd.DataFrame(prediction_result['涨停记录'])
                    st.dataframe(record_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {prediction_result['数据状态']}")
                if '说明' in prediction_result:
                    st.info(f"💡 {prediction_result['说明']}")

    elif limit_up_mode == "自选股批量预测":
        st.divider()
        st.subheader("📋 自选股批量预测")

        st.info("💡 批量预测自选股中所有股票的打板成功率")

        if watchlist:
            if st.button("📊 批量预测", key="batch_predict_limit_up"):
                # 进度条
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                total_stocks = len(watchlist)
                progress_text.text(f"🔮 正在预测 {total_stocks} 只自选股的打板成功率...")
                
                batch_result = LimitUpPredictor.batch_predict_limit_up(watchlist)
                progress_bar.progress(100)
                
                progress_bar.empty()
                progress_text.empty()

                if batch_result['数据状态'] == '正常':
                    st.success(f"✅ 预测完成！共预测 {batch_result['预测总数']} 只股票")

                    # 显示预测结果
                    prediction_df = pd.DataFrame(batch_result['预测列表'])
                    st.dataframe(prediction_df, width="stretch", hide_index=True)

                    # 按评级分组
                    excellent = [p for p in batch_result['预测列表'] if '优秀' in p['评级']]
                    good = [p for p in batch_result['预测列表'] if '良好' in p['评级']]
                    general = [p for p in batch_result['预测列表'] if '一般' in p['评级']]
                    poor = [p for p in batch_result['预测列表'] if '较差' in p['评级']]

                    # 优秀股票
                    if excellent:
                        st.divider()
                        st.subheader("🔥 优秀股票")
                        for stock in excellent:
                            st.write(f"• {stock['股票代码']} - 成功率: {stock['成功率']}%, 评分: {stock['综合评分']}")
        else:
            st.warning("⚠️ 自选股列表为空，请先添加股票到自选股")

    elif limit_up_mode == "市场整体分析":
        st.divider()
        st.subheader("📈 市场整体分析")

        st.info("💡 分析今日涨停股票的整体打板成功率")

        if st.button("📊 分析市场", key="analyze_market_limit_up"):
            with st.spinner('正在分析市场整体打板成功率...'):
                market_result = LimitUpPredictor.analyze_market_limit_up_success()

            if market_result['数据状态'] == '正常':
                st.success(f"✅ 分析完成！今日涨停 {market_result['今日涨停数']} 只股票")

                # 显示基本信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("今日涨停数", market_result['今日涨停数'])
                with col2:
                    st.metric("分析样本数", market_result['分析样本数'])
                with col3:
                    st.metric("市场平均成功率", f"{market_result['市场平均成功率']}%")

                # 显示评级分布
                if market_result['评级分布']:
                    st.divider()
                    st.subheader("📊 评级分布")

                    rating_df = pd.DataFrame(list(market_result['评级分布'].items()), columns=['评级', '数量'])
                    st.dataframe(rating_df, width="stretch", hide_index=True)

                # 显示详细预测
                if market_result['详细预测']:
                    st.divider()
                    st.subheader("📝 详细预测")

                    prediction_df = pd.DataFrame(market_result['详细预测'])
                    st.dataframe(prediction_df, width="stretch", hide_index=True)
            else:
                st.error(f"❌ {market_result['数据状态']}")
                if '说明' in market_result:
                    st.info(f"💡 {market_result['说明']}")

