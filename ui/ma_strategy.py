"""均线战法模块"""
import streamlit as st
import pandas as pd
from logic.algo_advanced import AdvancedAlgo

def render_ma_strategy_tab(db, config):
    st.subheader("📈 均线战法")
    st.caption("分析均线多头排列、金叉死叉、支撑压力")

    # 股票代码输入
    ma_symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="ma_symbol")

    # 均线参数设置
    col_ma1, col_ma2, col_ma3 = st.columns(3)
    with col_ma1:
        ma_short = st.number_input("短期均线", value=5, min_value=3, max_value=20)
    with col_ma2:
        ma_medium = st.number_input("中期均线", value=10, min_value=5, max_value=30)
    with col_ma3:
        ma_long = st.number_input("长期均线", value=20, min_value=10, max_value=60)

    if st.button("📊 分析均线", key="analyze_ma"):
        with st.spinner('正在分析均线...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=90)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(ma_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > ma_long:
                ma_result = AdvancedAlgo.analyze_moving_average(df, short=ma_short, medium=ma_medium, long=ma_long)

                if ma_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！发现 {ma_result['信号数量']} 个均线信号")

                    # 显示均线值
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"MA{ma_short}", f"¥{ma_result['MA{ma_short}']:.2f}")
                    with col2:
                        st.metric(f"MA{ma_medium}", f"¥{ma_result['MA{ma_medium}']:.2f}")
                    with col3:
                        st.metric(f"MA{ma_long}", f"¥{ma_result['MA{ma_long}']:.2f}")

                    if ma_result['信号列表']:
                        st.divider()
                        for signal in ma_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                    else:
                        st.info("👍 当前未发现明显的均线信号")
                else:
                    st.error(f"❌ {ma_result['数据状态']}")
            else:
                st.warning(f"⚠️ 数据不足，需要至少{ma_long}天数据")

