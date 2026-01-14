"""
AI 智能代理 UI（Lite 版）
集成 LLM API 和规则代理
"""

import streamlit as st
import pandas as pd
from logic.ai_agent import RealAIAgent, RuleBasedAgent


def render_ai_agent_lite_tab(db, config):
    """渲染 AI 智能代理标签页"""

    st.title("🤖 AI 智能代理（Lite 版）")
    st.markdown("---")
    st.info("🚀 使用 LLM API 替代硬编码规则，实现真正的智能分析")

    # 初始化
    if 'ai_agent_mode' not in st.session_state:
        st.session_state.ai_agent_mode = 'rule'
        st.session_state.ai_agent = None
        st.session_state.analysis_history = []

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 配置")

        # 模式选择
        st.subheader("🎯 分析模式")
        mode = st.radio(
            "选择模式",
            ['rule', 'llm'],
            format_func=lambda x: '规则代理（快速）' if x == 'rule' else 'LLM API（智能）',
            help="规则代理无需 API，响应快速；LLM API 需要配置密钥，但分析更智能"
        )

        st.session_state.ai_agent_mode = mode

        # LLM 配置
        if mode == 'llm':
            st.subheader("🔑 LLM 配置")

            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="输入你的 API Key",
                help="支持 OpenAI、DeepSeek、智谱 AI 等主流 LLM"
            )

            provider = st.selectbox(
                "提供商",
                ['openai', 'anthropic', 'deepseek', 'zhipu', 'qwen'],
                help="选择 LLM 服务提供商"
            )

            model = st.text_input(
                "模型名称",
                value="gpt-4",
                placeholder="例如: gpt-4, deepseek-chat, glm-4"
            )

            st.warning("⚠️ 注意：API Key 不会被保存，仅用于当前会话")

        else:
            st.info("ℹ️ 规则代理无需配置，直接使用即可")

        st.markdown("---")

        # 分析参数
        st.subheader("📊 分析参数")

        enable_rsi = st.checkbox("RSI", value=True)
        enable_macd = st.checkbox("MACD", value=True)
        enable_bollinger = st.checkbox("布林带", value=True)
        enable_kdj = st.checkbox("KDJ", value=True)
        enable_money_flow = st.checkbox("资金流向", value=True)

        st.info("💡 提示: 勾选要分析的技术指标")

    # 主内容区
    col1, col2 = st.columns(2)

    with col1:
        st.metric("分析模式", "规则代理" if mode == 'rule' else "LLM API")

    with col2:
        st.metric("历史记录", len(st.session_state.analysis_history))

    st.markdown("---")

    # 股票分析表单
    st.subheader("📈 股票分析")

    col1, col2, col3 = st.columns(3)

    with col1:
        symbol = st.text_input("股票代码", value="000001", placeholder="例如: 000001")

    with col2:
        current_price = st.number_input("当前价格", value=10.50, min_value=0.0, step=0.01)

    with col3:
        change_percent = st.number_input("涨跌幅(%)", value=3.2, step=0.1)

    col1, col2 = st.columns(2)

    with col1:
        volume = st.number_input("成交量", value=5000000, min_value=0, step=100000)

    with col2:
        st.empty()

    # 技术指标输入
    st.markdown("#### 技术指标")

    col1, col2, col3 = st.columns(3)

    with col1:
        if enable_rsi:
            rsi_value = st.slider("RSI", 0, 100, 65, 1)

        if enable_macd:
            macd_trend = st.selectbox("MACD 趋势", ['多头', '空头', '中性'])
            macd_hist = st.slider("MACD 柱", -1.0, 1.0, 0.05, 0.01)

    with col2:
        if enable_bollinger:
            bb_upper = st.number_input("布林带上轨", value=10.80, min_value=0.0, step=0.01)
            bb_lower = st.number_input("布林带下轨", value=9.50, min_value=0.0, step=0.01)
            bb_trend = st.selectbox("布林带趋势", ['上行', '下行', '横盘'])

        if enable_kdj:
            kdj_k = st.slider("KDJ K", 0, 100, 60, 1)
            kdj_d = st.slider("KDJ D", 0, 100, 55, 1)

    with col3:
        if enable_money_flow:
            money_flow_type = st.selectbox("资金流向", ['流入', '流出', '大幅流入', '大幅流出', '中性'])
            net_inflow = st.number_input("主力净流入", value=1000000, min_value=0, step=100000)

    # 分析按钮
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("🔍 开始分析", type="primary", use_container_width=True):
            with st.spinner("正在分析..."):
                # 构建数据
                price_data = {
                    'current_price': current_price,
                    'change_percent': change_percent,
                    'volume': volume
                }

                technical_data = {}

                if enable_rsi:
                    technical_data['rsi'] = {'RSI': rsi_value}

                if enable_macd:
                    technical_data['macd'] = {
                        'Trend': macd_trend,
                        'Histogram': macd_hist
                    }

                if enable_bollinger:
                    technical_data['bollinger'] = {
                        '上轨': bb_upper,
                        '下轨': bb_lower,
                        'Trend': bb_trend
                    }

                if enable_kdj:
                    technical_data['kdj'] = {
                        'K': kdj_k,
                        'D': kdj_d,
                        'J': kdj_k + kdj_d - 50  # 简化计算
                    }

                if enable_money_flow:
                    technical_data['money_flow'] = {
                        '资金流向': money_flow_type,
                        '主力净流入': net_inflow
                    }

                # 执行分析
                try:
                    if mode == 'llm' and api_key:
                        agent = RealAIAgent(api_key=api_key, provider=provider, model=model)
                        result = agent.analyze_stock(symbol, price_data, technical_data)
                    else:
                        agent = RuleBasedAgent()
                        result = agent.analyze_stock(symbol, price_data, technical_data)

                    # 保存历史
                    st.session_state.analysis_history.append({
                        'time': pd.Timestamp.now(),
                        'symbol': symbol,
                        'mode': mode,
                        'result': result
                    })

                    # 显示结果
                    st.success("✅ 分析完成！")
                    st.markdown("---")
                    st.markdown(result)

                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")

    with col2:
        if st.button("🗑️ 清空历史", use_container_width=True):
            st.session_state.analysis_history = []
            st.rerun()

    with col3:
        if st.button("📊 导出历史", use_container_width=True):
            if st.session_state.analysis_history:
                df = pd.DataFrame(st.session_state.analysis_history)
                csv = df.to_csv(index=False)
                st.download_button(
                    "下载 CSV",
                    csv,
                    "analysis_history.csv",
                    "text/csv"
                )

    st.markdown("---")

    # 历史记录
    if st.session_state.analysis_history:
        st.subheader("📋 分析历史")

        # 显示最近 5 条
        recent = st.session_state.analysis_history[-5:][::-1]

        for i, record in enumerate(recent):
            with st.expander(f"{record['symbol']} - {record['time'].strftime('%Y-%m-%d %H:%M:%S')} ({'LLM' if record['mode'] == 'llm' else '规则'})"):
                st.markdown(record['result'])

    # 使用说明
    st.markdown("---")
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### 🤖 AI 智能代理（Lite 版）

        **功能特点：**
        - ✅ 支持两种分析模式：规则代理和 LLM API
        - ✅ 规则代理快速响应，无需 API
        - ✅ LLM API 智能分析，语义理解
        - ✅ 支持多种技术指标组合分析

        **模式对比：**

        | 特性 | 规则代理 | LLM API |
        |------|---------|---------|
        | 响应速度 | ⚡ 毫秒级 | 🐢 秒级 |
        | 智能程度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
        | API 需求 | ❌ 不需要 | ✅ 需要 |
        | 成本 | 💰 免费 | 💵 按次付费 |
        | 适用场景 | 快速筛查 | 深度分析 |

        **使用流程：**
        1. 在侧边栏选择分析模式
        2. 如果选择 LLM API，配置 API Key 和模型
        3. 输入股票代码和价格数据
        4. 配置技术指标参数
        5. 点击"开始分析"按钮
        6. 查看分析结果

        **技术指标说明：**
        - **RSI**: 相对强弱指标，0-100，30 以下超卖，70 以上超买
        - **MACD**: 指数平滑异同移动平均线，判断趋势方向
        - **布林带**: 价格通道，判断价格相对位置
        - **KDJ**: 随机指标，判断超买超卖
        - **资金流向**: 主力资金进出情况

        **注意事项：**
        - 规则代理基于固定规则，适合快速筛查
        - LLM API 需要配置密钥，支持 OpenAI、DeepSeek 等
        - API Key 仅在当前会话有效，不会保存
        - 分析结果仅供参考，不构成投资建议
        """)