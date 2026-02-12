"""量价关系模块"""
import streamlit as st
import pandas as pd
from logic.algo_advanced import AdvancedAlgo

def render_volume_price_tab(db, config):
    st.subheader("📊 量价关系战法")
    st.caption("检测缩量回调、放量突破、顶背离、底背离等量价信号")

    # 股票代码输入
    vp_symbol = st.text_input("股票代码", value="600519", help="输入6位A股代码", key="vp_symbol")

    if st.button("📊 分析量价关系", key="analyze_vp"):
        with st.spinner('正在分析量价关系...'):
            start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(vp_symbol, start_date=s_date_str, end_date=e_date_str)

            if not df.empty and len(df) > 20:
                vp_result = AdvancedAlgo.detect_volume_price_signals(df)

                if vp_result['数据状态'] == '正常':
                    st.success(f"✅ 分析完成！发现 {vp_result['信号数量']} 个量价信号")

                    if vp_result['信号列表']:
                        for signal in vp_result['信号列表']:
                            level_color = {
                                '强': '🔥',
                                '中': '🟡',
                                '弱': '🟢'
                            }
                            with st.expander(f"{level_color.get(signal['信号强度'], '⚪')} {signal['信号类型']} - {signal['信号强度']}"):
                                st.write(f"**操作建议：** {signal['操作建议']}")
                                st.write(f"**说明：** {signal['说明']}")
                    else:
                        st.info("👍 当前未发现明显的量价信号")
                else:
                    st.error(f"❌ {vp_result['数据状态']}")
            else:
                st.warning("⚠️ 数据不足，需要至少20天数据")

