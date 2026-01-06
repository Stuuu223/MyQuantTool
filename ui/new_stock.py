"""次新股模块"""
import streamlit as st
import pandas as pd
from logic.algo_advanced import AdvancedAlgo

def render_new_stock_tab(db, config):
    st.subheader("🆕 次新股战法")
    st.caption("分析开板次新股、情绪周期、换手率")

    # 股票代码输入
    new_stock_symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="new_stock_symbol")

    if st.button("📊 分析次新股", key="analyze_new_stock"):
        with st.spinner('正在分析次新股...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=180)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(new_stock_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > 10:
                new_stock_result = AdvancedAlgo.analyze_new_stock(df, new_stock_symbol)

                if new_stock_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！上市{new_stock_result['上市天数']}天")

                    # 显示基本信息
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("上市天数", f"{new_stock_result['上市天数']}天")
                    with col2:
                        st.metric("当前阶段", new_stock_result['当前阶段'])

                    # 显示操作建议
                    st.divider()
                    st.write("**💡 操作建议：**")
                    st.success(new_stock_result['操作建议'])

                    # 显示信号列表
                    if new_stock_result['信号列表']:
                        st.divider()
                        for signal in new_stock_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                else:
                    st.error(f"❌ {new_stock_result['数据状态']}")
                    if '说明' in new_stock_result:
                        st.info(f"💡 {new_stock_result['说明']}")
            else:
                st.warning("⚠️ 数据不足，需要至少10天数据")

