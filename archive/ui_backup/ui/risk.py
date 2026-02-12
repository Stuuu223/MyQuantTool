"""风险管理模块"""
import streamlit as st
import pandas as pd
from logic.formatter import Formatter

def render_risk_tab(db, config):
    st.subheader("⚠️ 风险管理")
    st.caption("仓位管理、止损止盈提醒")

    # 导入风险管理器
    from logic.risk_manager import RiskManager

    # 功能选择
    risk_mode = st.radio("选择功能", ["仓位计算", "止损止盈检查", "组合风险评估", "风险预警"], horizontal=True)

    if risk_mode == "仓位计算":
        st.divider()
        st.subheader("💰 仓位计算")

        # 输入参数
        col1, col2, col3 = st.columns(3)
        with col1:
            capital = st.number_input("总资金", value=100000, min_value=0, step=1000)
        with col2:
            risk_per_trade = st.slider("单笔风险比例(%)", 1.0, 10.0, 2.0, 0.5) / 100
        with col3:
            stop_loss_pct = st.slider("止损比例(%)", 2.0, 10.0, 5.0, 0.5) / 100

        if st.button("📊 计算仓位", key="calculate_position"):
            position_result = RiskManager.calculate_position_size(capital, risk_per_trade, stop_loss_pct)

            st.success("✅ 计算完成！")

            # 显示结果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("单笔风险比例", position_result['单笔风险比例'])
            with col2:
                st.metric("止损比例", position_result['止损比例'])
            with col3:
                st.metric("建议仓位", Formatter.format_amount(position_result['建议仓位']))

            st.write(f"**仓位占比：** {position_result['仓位占比']}")
            st.write(f"**单笔最大损失：** {Formatter.format_amount(position_result['单笔最大损失'])}")

    elif risk_mode == "止损止盈检查":
        st.divider()
        st.subheader("📉 止损止盈检查")

        # 输入参数
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            check_symbol = st.text_input("股票代码", value="600519", key="risk_check_symbol")
        with col2:
            current_price = st.number_input("当前价格", value=0.0, min_value=0.0, step=0.01)
        with col3:
            buy_price = st.number_input("买入价格", value=0.0, min_value=0.0, step=0.01)
        with col4:
            stop_loss_pct = st.slider("止损比例(%)", 2.0, 10.0, 5.0, 0.5) / 100

        if st.button("📊 检查", key="check_stop_loss"):
            if current_price > 0 and buy_price > 0:
                check_result = RiskManager.check_stop_loss(check_symbol, current_price, buy_price, stop_loss_pct)

                # 根据状态显示不同颜色
                if check_result['状态'] == '止损':
                    st.error(f"⚠️ {check_result['状态']}")
                elif check_result['状态'] == '止盈':
                    st.success(f"✅ {check_result['状态']}")
                else:
                    st.info(f"📊 {check_result['状态']}")

                # 显示详细信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("当前价格", Formatter.format_price(check_result['当前价格']))
                with col2:
                    st.metric("买入价格", Formatter.format_price(check_result['买入价格']))
                with col3:
                    st.metric("盈亏比例", check_result['盈亏比例'])

                st.write(f"**止损价：** {Formatter.format_price(check_result['止损价'])}")
                st.write(f"**止盈价：** {Formatter.format_price(check_result['止盈价'])}")

                if check_result['状态'] == '持有':
                    st.write(f"**距离止损：** {check_result['距离止损']}")
                    st.write(f"**距离止盈：** {check_result['距离止盈']}")

                st.write(f"**建议：** {check_result['建议']}")
            else:
                st.warning("⚠️ 请输入有效的价格")

    elif risk_mode == "组合风险评估":
        st.divider()
        st.subheader("📊 组合风险评估")

        st.info("💡 输入持仓信息，评估整体风险")

        # 这里可以添加持仓输入功能
        # 由于篇幅限制，简化处理
        st.warning("⚠️ 此功能需要输入详细持仓信息，请使用自选股管理")

    elif risk_mode == "风险预警":
        st.divider()
        st.subheader("🚨 风险预警")

        st.info("💡 检查自选股中的风险预警")

        if watchlist:
            if st.button("🔍 检查风险", key="check_risk_alerts"):
                st.warning("⚠️ 需要输入持仓成本价才能进行风险预警")
        else:
            st.warning("⚠️ 自选股列表为空")

