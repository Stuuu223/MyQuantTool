#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 全谱系战斗逻辑 UI
集成所有 V18.5 和 V18.6 新功能：
1. DDE 核心战法
2. 低吸逻辑引擎
3. 动态涨停系数
4. 逻辑回踩战法
5. 🆕 V18.6: BUY_MODE 参数（DRAGON_CHASE / LOW_SUCTION）
6. 🆕 V18.6: 价格缓冲区
7. 🆕 V18.6: 高精度校准
8. 🆕 V18.6: 二波预期识别
9. 🆕 V18.6: 托单套路监控
10. 🆕 V18.6: 国家队护盘指纹
11. 🆕 V18.6: 预判模式（Pre-Buy Signal）
12. 🆕 V18.6: 弹性缓冲（Elastic Buffer）
"""

import streamlit as st
import pandas as pd
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.utils import Utils
from logic.second_wave_detector import get_second_wave_detector
from logic.fake_order_detector import get_fake_order_detector
from logic.national_team_guard import get_national_team_guard

logger = get_logger(__name__)

# 页面配置
st.set_page_config(
    page_title="V18.6 全谱系战斗逻辑",
    page_icon="🦁",
    layout="wide"
)

# 初始化
@st.cache_resource
def init_managers():
    """初始化管理器"""
    data_manager = DataManager()
    money_flow_master = get_money_flow_master()
    low_suction_engine = get_low_suction_engine()
    second_wave_detector = get_second_wave_detector()
    fake_order_detector = get_fake_order_detector()
    national_team_guard = get_national_team_guard()
    return data_manager, money_flow_master, low_suction_engine, second_wave_detector, fake_order_detector, national_team_guard

data_manager, money_flow_master, low_suction_engine, second_wave_detector, fake_order_detector, national_team_guard = init_managers()

# 标题
st.title("🦁 V18.6 全谱系战斗逻辑")
st.markdown("""
**核心理念：**
> "只有平庸的猎人才等猎物死透了才去捡。顶级的掠食者通过风向（资金流）和草动的规律（分时走势）在猎物奔跑时就已经锁定了结局。"

**确定性不一定非要涨停。当资金流向、板块热度和 K 线回踩在一个点重合时，那个点的确定性比任何涨停板都要高。**
""")
st.markdown("---")

# 选项卡
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 DDE 核心战法",
    "🔻 低吸逻辑引擎",
    "🎯 动态涨停系数",
    "🔄 逻辑回踩战法",
    "📈 综合分析",
    "🚀 预判模式",
    "🔮 二波预期",
    "🛡️ 风险监控",
    "🔥 排队打板的真相",
    "💎 V18.6.1 进阶战法"
])

# Tab 1: DDE 核心战法
with tab1:
    st.header("📊 DDE 核心战法")
    st.markdown("""
    **核心战法：**
    1. DDE 背离低吸：股价下跌 2%-3%，但 DDE 净额持续走高（机构压盘吸筹）
    2. DDE 抢筹确认：竞价阶段 DDE 活跃度突破历史均值 5 倍
    3. DDE 否决权：DDE 为负时，禁止发出 BUY 信号
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("DDE 背离低吸检测")
        stock_code = st.text_input("股票代码", value="000001", key="dde_divergence_code")
        current_price = st.number_input("当前价格", value=10.0, key="dde_divergence_price")
        prev_close = st.number_input("昨收价", value=10.0, key="dde_divergence_prev")
        
        if st.button("检测 DDE 背离", key="check_dde_divergence"):
            result = money_flow_master.check_dde_divergence(stock_code, current_price, prev_close)
            
            if result['has_divergence']:
                st.success(f"✅ {result['reason']}")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.subheader("竞价 DDE 抢筹检测")
        stock_code2 = st.text_input("股票代码", value="000001", key="dde_surge_code")
        
        if st.button("检测竞价抢筹", key="check_dde_surge"):
            result = money_flow_master.check_auction_dde_surge(stock_code2)
            
            if result['has_surge']:
                st.success(f"✅ {result['reason']}")
                st.metric("突破倍数", f"{result['surge_ratio']:.1f}x")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    st.markdown("---")
    st.subheader("DDE 否决权测试")
    stock_code3 = st.text_input("股票代码", value="000001", key="dde_veto_code")
    signal = st.selectbox("原始信号", options=["BUY", "SELL", "HOLD"], key="dde_veto_signal")
    
    if st.button("检查 DDE 否决权", key="check_dde_veto"):
        is_vetoed, veto_reason = money_flow_master.check_dde_veto(stock_code3, signal)
        
        if is_vetoed:
            st.error(f"🛑 {veto_reason}")
        elif veto_reason:
            st.warning(f"⚠️ {veto_reason}")
        else:
            st.success("✅ DDE 检查通过，无否决")

# Tab 2: 低吸逻辑引擎
with tab2:
    st.header("🔻 低吸逻辑引擎")
    st.markdown("""
    **核心战法：**
    1. 5日均线低吸：回踩 5日均线下方 -2% 处，且成交量萎缩
    2. 分时均线低吸：回踩分时均线下方 -2% 处，且 DDE 翻红
    3. 逻辑确认：符合核心逻辑（机器人/航天等）+ 龙虎榜机构深度介入
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("5日均线低吸检测")
        stock_code = st.text_input("股票代码", value="000001", key="ma5_suction_code")
        current_price = st.number_input("当前价格", value=10.0, key="ma5_suction_price")
        prev_close = st.number_input("昨收价", value=10.0, key="ma5_suction_prev")
        
        if st.button("检测 5日均线低吸", key="check_ma5_suction"):
            result = low_suction_engine.check_ma5_suction(stock_code, current_price, prev_close)
            
            if result['has_suction']:
                st.success(f"✅ {result['reason']}")
                st.metric("置信度", f"{result['confidence']:.1%}")
                st.metric("成交量比率", f"{result['volume_ratio']:.2%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.subheader("逻辑回踩检测")
        stock_code2 = st.text_input("股票代码", value="000001", key="logic_reversion_code")
        logic_keywords = st.text_input("核心逻辑关键词（逗号分隔）", value="机器人,航天", key="logic_keywords")
        lhb_institutional = st.checkbox("龙虎榜机构深度介入", value=False, key="lhb_institutional")
        
        if st.button("检测逻辑回踩", key="check_logic_reversion"):
            keywords = [k.strip() for k in logic_keywords.split(',') if k.strip()]
            result = low_suction_engine.check_logic_reversion(stock_code2, keywords, lhb_institutional)
            
            if result['has_logic'] and result['has_institutional']:
                st.success(f"✅ {result['reason']}")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    st.markdown("---")
    st.subheader("综合低吸分析")
    stock_code3 = st.text_input("股票代码", value="000001", key="low_suction_code")
    current_price2 = st.number_input("当前价格", value=10.0, key="low_suction_price")
    prev_close2 = st.number_input("昨收价", value=10.0, key="low_suction_prev")
    logic_keywords2 = st.text_input("核心逻辑关键词（逗号分隔）", value="机器人,航天", key="logic_keywords2")
    lhb_institutional2 = st.checkbox("龙虎榜机构深度介入", value=False, key="lhb_institutional2")
    
    if st.button("综合低吸分析", key="analyze_low_suction"):
        keywords2 = [k.strip() for k in logic_keywords2.split(',') if k.strip()]
        result = low_suction_engine.analyze_low_suction(
            stock_code3, current_price2, prev_close2,
            logic_keywords=keywords2, lhb_institutional=lhb_institutional2
        )
        
        if result['has_suction']:
            st.success(f"✅ {result['reason']}")
            st.metric("综合置信度", f"{result['overall_confidence']:.1%}")
            st.metric("建议", result['recommendation'])
        else:
            st.warning(f"⚠️ {result['reason']}")
            st.metric("建议", result['recommendation'])

# Tab 3: 动态涨停系数
with tab3:
    st.header("🎯 动态涨停系数")
    st.markdown("""
    **动态适配：**
    - 创业板(30)、科创板(68): 1.2 (20cm)
    - 北交所(8/4): 1.3 (30cm)
    - 主板: 1.1 (10cm)
    - ST股: 1.05 (5cm)
    """)
    
    stock_codes = st.text_area("股票代码列表（每行一个）", value="000001\n300001\n688001\n830799\n600000", key="limit_ratio_codes")
    
    if st.button("测试涨停系数", key="test_limit_ratio"):
        codes = [code.strip() for code in stock_codes.split('\n') if code.strip()]
        
        results = []
        for code in codes:
            limit_ratio = Utils.get_limit_ratio(code)
            limit_up_pct = (limit_ratio - 1.0) * 100
            results.append({
                '股票代码': code,
                '涨停系数': f"{limit_ratio:.2f}",
                '涨停幅度': f"{limit_up_pct:.1f}%",
                '板块类型': '20cm' if limit_ratio >= 1.2 else ('30cm' if limit_ratio >= 1.3 else ('5cm' if limit_ratio < 1.1 else '10cm'))
            })
        
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)
        
        # 统计
        st.markdown("### 统计")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("10cm", len(df[df['板块类型'] == '10cm']))
        col2.metric("20cm", len(df[df['板块类型'] == '20cm']))
        col3.metric("30cm", len(df[df['板块类型'] == '30cm']))
        col4.metric("5cm", len(df[df['板块类型'] == '5cm']))
        col5.metric("总计", len(df))

# Tab 4: 逻辑回踩战法
with tab4:
    st.header("🔄 逻辑回踩战法")
    st.markdown("""
    **核心战法：**
    1. 触发点：符合核心逻辑（机器人/航天等）+ 龙虎榜机构深度介入
    2. 买入点：次日出现缩量回调，回踩 5日均线 或 分时均线下方 -2% 处
    3. 目标：博弈主力的二波预期
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("核心逻辑配置")
        logic_keywords = st.text_area("核心逻辑关键词（每行一个）", value="机器人\n航天\nAI\n新能源", key="core_logic_keywords")
        
        if st.button("保存核心逻辑", key="save_core_logic"):
            keywords = [k.strip() for k in logic_keywords.split('\n') if k.strip()]
            st.session_state.core_logic_keywords = keywords
            st.success(f"✅ 已保存 {len(keywords)} 个核心逻辑关键词")
    
    with col2:
        st.subheader("监控股票列表")
        stock_list = st.text_area("监控股票列表（每行一个）", value="000001\n300001\n688001", key="monitor_stock_list")
        
        if st.button("保存监控列表", key="save_monitor_list"):
            stocks = [s.strip() for s in stock_list.split('\n') if s.strip()]
            st.session_state.monitor_stock_list = stocks
            st.success(f"✅ 已保存 {len(stocks)} 只监控股票")
    
    st.markdown("---")
    st.subheader("批量检测")
    
    if 'core_logic_keywords' not in st.session_state:
        st.warning("⚠️ 请先配置核心逻辑关键词")
    elif 'monitor_stock_list' not in st.session_state:
        st.warning("⚠️ 请先配置监控股票列表")
    else:
        if st.button("批量检测逻辑回踩", key="batch_check_logic_reversion"):
            keywords = st.session_state.core_logic_keywords
            stocks = st.session_state.monitor_stock_list
            
            results = []
            for stock in stocks:
                # 获取实时数据
                realtime_data = data_manager.get_realtime_data(stock)
                if realtime_data:
                    current_price = realtime_data.get('price', 0)
                    prev_close = realtime_data.get('pre_close', current_price)
                    
                    # 检查逻辑回踩
                    result = low_suction_engine.check_logic_reversion(stock, keywords, False)
                    
                    results.append({
                        '股票代码': stock,
                        '当前价格': f"{current_price:.2f}",
                        '符合逻辑': result['has_logic'],
                        '逻辑类型': result['logic_type'],
                        '置信度': f"{result['confidence']:.1%}" if result['has_logic'] else 'N/A'
                    })
            
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

# Tab 5: 综合分析
with tab5:
    st.header("📈 综合分析")
    st.markdown("""
    **综合分析：**
    1. DDE 核心战法
    2. 低吸逻辑引擎
    3. 动态涨停系数
    4. 逻辑回踩战法
    """)
    
    stock_code = st.text_input("股票代码", value="000001", key="comprehensive_code")
    
    if st.button("综合分析", key="comprehensive_analysis"):
        # 获取实时数据
        realtime_data = data_manager.get_realtime_data(stock_code)
        if not realtime_data:
            st.error("❌ 无法获取实时数据")
        else:
            current_price = realtime_data.get('price', 0)
            prev_close = realtime_data.get('pre_close', current_price)
            
            # 1. DDE 分析
            st.subheader("1. DDE 分析")
            dde_score = money_flow_master.calculate_dde_score(stock_code)
            st.metric("DDE 评分", f"{dde_score:.1f}/100")
            
            dde_divergence = money_flow_master.check_dde_divergence(stock_code, current_price, prev_close)
            if dde_divergence['has_divergence']:
                st.success(f"✅ {dde_divergence['reason']}")
            else:
                st.warning(f"⚠️ {dde_divergence['reason']}")
            
            # 2. 低吸分析
            st.subheader("2. 低吸分析")
            ma5_suction = low_suction_engine.check_ma5_suction(stock_code, current_price, prev_close)
            if ma5_suction['has_suction']:
                st.success(f"✅ {ma5_suction['reason']}")
            else:
                st.warning(f"⚠️ {ma5_suction['reason']}")
            
            # 3. 涨停系数
            st.subheader("3. 涨停系数")
            limit_ratio = Utils.get_limit_ratio(stock_code)
            limit_up_pct = (limit_ratio - 1.0) * 100
            st.metric("涨停系数", f"{limit_ratio:.2f}")
            st.metric("涨停幅度", f"{limit_up_pct:.1f}%")
            
            # 4. 综合建议
            st.subheader("4. 综合建议")
            if dde_divergence['has_divergence'] and ma5_suction['has_suction']:
                st.success("🚀 强烈建议：DDE 背离 + 5日均线低吸 = 强买入信号")
            elif dde_divergence['has_divergence'] or ma5_suction['has_suction']:
                st.info("👀 观察：有单一低吸信号，等待确认")
            else:
                st.warning("⚠️ 等待：暂无低吸信号")

# Tab 6: 预判模式
with tab6:
    st.header("🚀 预判模式（Pre-Buy Signal）")
    st.markdown("""
    **核心理念：**
    > "只有平庸的猎人才等猎物死透了才去捡。顶级的掠食者通过风向（资金流）和草动的规律（分时走势）在猎物奔跑时就已经锁定了结局。"
    
    **预判信号：**
    1. DDE 脉冲预警：涨幅 4%-6% 时，如果 DDE 持续走高，发出预判信号
    2. 弹性缓冲：20cm/30cm 股票涨幅 10% 时，如果 DDE 持续走高，发出弹性缓冲信号，剩余空间作为安全垫
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("DDE 脉冲预警")
        stock_code = st.text_input("股票代码", value="300992", key="pre_buy_code")
        
        # 获取实时数据
        realtime_data = data_manager.get_realtime_data(stock_code)
        if realtime_data:
            current_price = realtime_data.get('price', 0)
            prev_close = realtime_data.get('pre_close', current_price)
            current_pct_change = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            
            st.metric("当前涨幅", f"{current_pct_change:.2f}%")
            
            # 检查是否在预判区间
            if 4.0 <= current_pct_change <= 6.0:
                st.info(f"📊 涨幅 {current_pct_change:.1f}% 在预判区间（4%-6%）")
                
                # 检查 DDE 斜率
                dde_history = money_flow_master._get_dde_history(stock_code, lookback=5)
                if dde_history and len(dde_history) >= 3:
                    recent_dde = dde_history[-3:]
                    dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                    
                    st.metric("DDE 斜率", f"{dde_slope:.3f}")
                    
                    if dde_slope > 0:
                        st.success(f"🔥 [预判信号] DDE 斜率转正，建议提前布局")
                    else:
                        st.warning(f"⚠️ DDE 斜率向下，暂不建议提前布局")
                else:
                    st.warning("⚠️ DDE 历史数据不足，无法判断斜率")
            elif current_pct_change < 4.0:
                st.info(f"📊 涨幅 {current_pct_change:.1f}% 还未达到预判区间（4%-6%）")
            else:
                st.warning(f"📊 涨幅 {current_pct_change:.1f}% 已超过预判区间（4%-6%）")
        else:
            st.error("❌ 无法获取实时数据")
    
    with col2:
        st.subheader("弹性缓冲")
        stock_code2 = st.text_input("股票代码", value="300992", key="elastic_buffer_code")
        
        # 获取实时数据
        realtime_data2 = data_manager.get_realtime_data(stock_code2)
        if realtime_data2:
            current_price2 = realtime_data2.get('price', 0)
            prev_close2 = realtime_data2.get('pre_close', current_price2)
            current_pct_change2 = (current_price2 - prev_close2) / prev_close2 * 100 if prev_close2 > 0 else 0
            
            # 获取涨停系数
            limit_ratio = Utils.get_limit_ratio(stock_code2)
            limit_up_pct = (limit_ratio - 1.0) * 100
            
            st.metric("当前涨幅", f"{current_pct_change2:.2f}%")
            st.metric("涨停幅度", f"{limit_up_pct:.1f}%")
            
            # 检查是否是20cm/30cm股票
            if limit_ratio >= 1.2:
                if 9.0 <= current_pct_change2 <= 11.0:
                    st.info(f"📊 涨幅 {current_pct_change2:.1f}% 在弹性缓冲区间（9%-11%）")
                    
                    # 检查 DDE 斜率
                    dde_history = money_flow_master._get_dde_history(stock_code2, lookback=5)
                    if dde_history and len(dde_history) >= 3:
                        recent_dde = dde_history[-3:]
                        dde_slope = (recent_dde[-1] - recent_dde[0]) / len(recent_dde)
                        
                        st.metric("DDE 斜率", f"{dde_slope:.3f}")
                        
                        if dde_slope > 0:
                            elastic_buffer = limit_up_pct - current_pct_change2
                            st.success(f"🛡️ [弹性缓冲] DDE 斜率转正，剩余空间 {elastic_buffer:.1f}%，安全垫充足")
                        else:
                            st.warning(f"⚠️ DDE 斜率向下，暂不建议追高")
                    else:
                        st.warning("⚠️ DDE 历史数据不足，无法判断斜率")
                elif current_pct_change2 < 9.0:
                    st.info(f"📊 涨幅 {current_pct_change2:.1f}% 还未达到弹性缓冲区间（9%-11%）")
                else:
                    st.warning(f"📊 涨幅 {current_pct_change2:.1f}% 已超过弹性缓冲区间（9%-11%）")
            else:
                st.info(f"📊 该股票不是 20cm/30cm 标的，无需弹性缓冲检查")
        else:
            st.error("❌ 无法获取实时数据")

# Tab 7: 二波预期
with tab7:
    st.header("🔮 二波预期识别")
    st.markdown("""
    **核心理念：**
    > "博弈主力预期，这才是真正的'博弈主力预期'。"
    
    **核心战法：**
    1. 龙虎榜成本区识别：识别顶级游资（如陈小群）或机构专用的持仓成本区
    2. 二波预期信号：如果低吸位恰好是这些成本区，提升信号确定性至 150/100
    3. 博弈主力预期：这才是真正的"博弈主力预期"
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("龙虎榜成本区检测")
        stock_code = st.text_input("股票代码", value="300992", key="second_wave_code")
        current_price = st.number_input("当前价格", value=28.00, key="second_wave_price")
        suction_price = st.number_input("低吸价格", value=26.00, key="second_wave_suction")
        
        if st.button("检测二波预期", key="check_second_wave"):
            result = second_wave_detector.check_second_wave_signal(stock_code, current_price, suction_price)
            
            if result['has_second_wave']:
                st.success(f"✅ {result['reason']}")
                st.metric("置信度", f"{result['confidence']:.1%}")
                st.metric("提升比例", f"{result['boost_ratio']:.1f}x")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.subheader("全域共振检测")
        stock_code2 = st.text_input("股票代码", value="300992", key="global_resonance_code")
        suction_price2 = st.number_input("低吸价格", value=26.00, key="global_resonance_suction")
        
        if st.button("检测全域共振", key="check_global_resonance"):
            result = national_team_guard.check_global_resonance(stock_code2, suction_price2)
            
            if result['has_global_resonance']:
                st.success(f"✅ {result['reason']}")
                st.metric("置信度", f"{result['confidence']:.1%}")
                st.metric("提升比例", f"{result['boost_ratio']:.1f}x")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    st.markdown("---")
    st.subheader("国家队护盘检测")
    if st.button("检测国家队护盘", key="check_national_team_guard"):
        result = national_team_guard.check_national_team_guard()
        
        if result['is_guarding']:
            st.success(f"✅ {result['reason']}")
            st.metric("护盘强度", f"{result['guard_strength']:.1%}")
        else:
            st.warning(f"⚠️ {result['reason']}")

# Tab 8: 风险监控
with tab8:
    st.header("🛡️ 风险监控")
    st.markdown("""
    **核心理念：**
    > "识别'虚假繁荣'，防止被假单欺骗。"
    
    **核心战法：**
    1. 托单套路监控：监控买一到买五的撤单率
    2. 虚假繁荣识别：如果 DDE 巨量流入，但买一到买五出现频繁撤单，判定为"虚假繁荣"
    3. 取消 BUY 信号：识别到假单时，取消 BUY 信号
    """)
    
    st.subheader("假单信号检测")
    stock_code = st.text_input("股票代码", value="300992", key="fake_order_code")
    signal = st.selectbox("原始信号", options=["BUY", "SELL", "HOLD"], value="BUY", key="fake_order_signal")
    
    if st.button("检测假单信号", key="check_fake_order"):
        result = fake_order_detector.check_fake_order_signal(stock_code, signal)
        
        if result['is_fake_prosperity']:
            st.error(f"🚨 {result['reason']}")
            st.metric("撤单率", f"{result['cancellation_rate']:.2%}")
            st.metric("置信度", f"{result['confidence']:.1%}")
        elif result['has_fake_order']:
            st.warning(f"⚠️ {result['reason']}")
            st.metric("撤单率", f"{result['cancellation_rate']:.2%}")
        else:
            st.success(f"✅ {result['reason']}")
            if result['cancellation_rate'] > 0:
                st.metric("撤单率", f"{result['cancellation_rate']:.2%}")
    
    st.markdown("---")
    st.subheader("BUY_MODE 模式测试")
    stock_code2 = st.text_input("股票代码", value="300992", key="buy_mode_code")
    buy_mode = st.selectbox("买入模式", options=["DRAGON_CHASE", "LOW_SUCTION"], key="buy_mode_select")
    
    if st.button("测试 BUY_MODE", key="test_buy_mode"):
        is_vetoed, veto_reason = money_flow_master.check_dde_veto(stock_code2, "BUY", buy_mode)
        
        if is_vetoed:
            st.error(f"🛑 {veto_reason}")
        elif veto_reason:
            st.warning(f"⚠️ {veto_reason}")
        else:
            st.success(f"✅ {buy_mode} 模式下 DDE 检查通过，无否决")

# Tab 9: 排队打板的真相
with tab9:
    st.header("🔥 排队打板的真相")
    st.markdown("""
    **核心理念：**
    > "排队是赌命，潜伏是猎心。既然你有了 DDE 这把显微镜，就没必要再去挤那道窄门了。"
    
    **为什么"排队打板"是平庸猎人的墓地？**
    1. **幸存者偏差**：你看到的"封死涨停"是确定性，但你没看到那些在 9% 被砸回 -5% 的"大面"。
    2. **成本劣势**：排板买入的人，成本是在天花板。次日如果不及预期，哪怕只低开 2%，排板的人瞬间就处于被动，只能被迫止损。
    3. **对手盘陷阱**：游资最喜欢这种"排队共识"。当散户都在涨停价排队时，主力正好可以利用这巨大的承接盘，悄无声息地完成 10 亿级的套现。
    
    **除了排队，游资都在做什么？（V18.6 的三种降维打击）**
    当平庸的人在等涨停时，你的 V18.6 正在这些地方寻找真正的确定性：
    
    1. **价格发现阶段（DDE抢筹战法）**：在股价只有 3%-5% 的时候，主力通过连续的巨量大单（DDE红柱）进行暴力扫货。
    2. **分歧转一致（低吸战法）**：主力故意在高位放手，让股价回踩均线，洗掉不坚定的筹码。
    3. **动态适配的"提前量"（20cm/30cm）**：在创业板，股价从 10% 涨到 20% 有巨大的缓冲带。不需要等它 20cm 封死，当它在 12% 处缩量回踩分时均线，且 DDE 维持强势时，这就是"准涨停确定性"。
    """)
    
    st.markdown("---")
    
    # 1. 价格发现阶段（DDE抢筹战法）
    st.subheader("1. 价格发现阶段（DDE抢筹战法）")
    st.markdown("""
    **逻辑：** 在股价只有 3%-5% 的时候，主力通过连续的巨量大单（DDE红柱）进行暴力扫货。
    **确定性：** 这种确定性来自于"成本压制"。主力花了 2 个亿在 4% 的位置建仓，他今天不把股价顶上板，他自己就出不来。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code = st.text_input("股票代码", value="300992", key="price_discovery_code")
        current_price = st.number_input("当前价格", value=28.00, key="price_discovery_price")
        prev_close = st.number_input("昨收价", value=26.00, key="price_discovery_prev")
        
        if st.button("检测价格发现阶段", key="check_price_discovery"):
            result = money_flow_master.check_price_discovery_stage(stock_code, current_price, prev_close)
            
            if result['in_price_discovery']:
                st.success(f"✅ {result['reason']}")
                st.metric("DDE脉冲强度", f"{result['dde_pulse_strength']:.1f}倍")
                st.metric("成交量放大倍数", f"{result['volume_amplification']:.1f}倍")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.info("""
        **价格发现阶段特征：**
        - 涨幅在 3%-5% 区间
        - DDE 活跃度翻了 5 倍
        - 成交量放大
        - 有连续的巨量大单
        
        **实战建议：**
        - 当检测到价格发现信号时，可以考虑提前布局
        - 不要等到涨停再追，那样成本太高
        - 利用 DDE 脉冲强度判断主力扫货力度
        """)
    
    st.markdown("---")
    
    # 2. 分歧转一致（低吸战法）
    st.subheader("2. 分歧转一致（低吸战法）")
    st.markdown("""
    **逻辑：** 主力故意在高位放手，让股价回踩均线，洗掉不坚定的筹码。
    **确定性：** 这种确定性来自于"逻辑未死"。只要机器人/航天的大背景没变，主力回踩就是为了拿更便宜的筹码。你买在回踩点，比那些等回封涨停再追的人，多了 10% 的安全垫。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code2 = st.text_input("股票代码", value="300992", key="divergence_consensus_code")
        current_price2 = st.number_input("当前价格", value=26.00, key="divergence_consensus_price")
        prev_close2 = st.number_input("昨收价", value=26.00, key="divergence_consensus_prev")
        logic_keywords = st.text_input("核心逻辑关键词（逗号分隔）", value="机器人,航天", key="divergence_logic_keywords")
        
        if st.button("检测分歧转一致", key="check_divergence_consensus"):
            keywords = [k.strip() for k in logic_keywords.split(',') if k.strip()]
            result = low_suction_engine.check_divergence_to_consensus(stock_code2, current_price2, prev_close2, keywords)
            
            if result['has_divergence_to_consensus']:
                st.success(f"✅ {result['reason']}")
                st.metric("回撤幅度", f"{result['pullback_pct']:.1f}%")
                st.metric("是否回踩MA5", "是" if result['ma5_touch'] else "否")
                st.metric("是否缩量", "是" if result['volume_shrink'] else "否")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.info("""
        **分歧转一致特征：**
        - 从高位回撤 5%-15%
        - 回踩 MA5 均线
        - 缩量洗筹
        - 有反弹迹象
        - 逻辑未死（题材还在）
        
        **实战建议：**
        - 泰福泵业这种趋势中军，设好 MA5 或 VWAP 的回踩报警
        - 买在分歧时，博弈主力的二波预期
        - 不要等回封涨停再追，那样成本太高
        """)
    
    st.markdown("---")
    
    # 3. 动态适配的"提前量"（20cm/30cm）
    st.subheader("3. 动态适配的'提前量'（20cm/30cm）")
    st.markdown("""
    **逻辑：** 在创业板，股价从 10% 涨到 20% 有巨大的缓冲带。不需要等它 20cm 封死。
    **确定性：** 当它在 12% 处缩量回踩分时均线，且 DDE 维持强势时，这就是"准涨停确定性"。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code3 = st.text_input("股票代码", value="300992", key="elastic_buffer_code2")
        current_price3 = st.number_input("当前价格", value=28.00, key="elastic_buffer_price2")
        prev_close3 = st.number_input("昨收价", value="26.00", key="elastic_buffer_prev2")
        
        if st.button("检测弹性缓冲", key="check_elastic_buffer2"):
            # 获取分时数据（这里简化处理）
            intraday_data = None
            
            from logic.signal_generator import get_signal_generator_v14_4
            signal_gen = get_signal_generator_v14_4()
            result = signal_gen.check_elastic_buffer_signal(stock_code3, current_price3, prev_close3, intraday_data)
            
            if result['has_elastic_buffer']:
                st.success(f"✅ {result['reason']}")
                st.metric("当前涨幅", f"{result['current_pct_change']:.1f}%")
                st.metric("弹性空间", f"{result['elastic_space']:.1f}%")
                st.metric("DDE强势", "是" if result['dde_strong'] else "否")
                st.metric("置信度", f"{result['confidence']:.1%}")
            else:
                st.warning(f"⚠️ {result['reason']}")
    
    with col2:
        st.info("""
        **弹性缓冲特征：**
        - 是 20cm/30cm 股票
        - 涨幅在 10%-14% 区间
        - 缩量回踩分时均线
        - DDE 维持强势
        - 剩余空间作为安全垫
        
        **实战建议：**
        - 对于 20cm/30cm 股票，在涨幅 10% 时进行逻辑二次确认
        - 如果 DDE 持续走高，剩余的 10% 空间就是你的"安全垫"
        - 不要等 20cm 封死再追，那样成本太高
        """)
    
    st.markdown("---")
    st.subheader("实战建议")
    st.info("""
    **周一 9:25，让我们在水下，看主力如何表演。**
    
    1. **屏蔽"缩量一字板"**：那是别人的博弈，我们不去当流动性耗材。
    2. **寻找"放量分歧点"**：利用 ui/v18_full_spectrum.py 里的"综合分析"，寻找那些 DDE 脉冲极强但涨幅尚未到顶（<10%） 的标的。
    3. **泰福泵业 (300992) 观察**：如果它明天在 MA5 附近出现 DDE 翻红，那就是我们 V18.6 "分歧转一致"的首战目标。
    """)

# Tab 10: V18.6.1 进阶战法
with tab10:
    st.header("💎 V18.6.1 进阶战法")
    st.markdown("""
    **核心理念：**
    > "V18.6 解决了'买得好'，V18.7 要解决'卖得神'。"
    
    **V18.6.1 新增功能：**
    1. **动态止损**：20cm战法的"移动止损"，一旦股价跌破"DDE均价线"，立即触发HARD_EXIT
    2. **主力成本线**：可视化主力成本线，当现价回踩这条线时，就是最硬的低吸点
    3. **诱多陷阱识别**：识别主力"画图"诱多，防止被假单欺骗
    4. **自动止盈**：情绪高潮兑现，当封单极弱或DDE背离流出时触发TP信号
    """)
    
    st.markdown("---")
    
    # 1. 动态止损
    st.subheader("1. 动态止损（20cm战法专用）")
    st.markdown("""
    **逻辑：** 创业板波动极大，从 12% 杀到 -5% 只需要 10 分钟。
    **策略：** 引入 "Trailing Stop (移动止损)"。一旦股价跌破 "DDE 均价线"，立即触发 HARD_EXIT，不要等 -8% 止损。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code = st.text_input("股票代码", value="300992", key="dynamic_stop_loss_code")
        current_price = st.number_input("当前价格", value=28.00, key="dynamic_stop_loss_price")
        entry_price = st.number_input("入场价格", value=26.00, key="dynamic_stop_loss_entry")
        dde_avg_price = st.number_input("DDE均价线", value=26.50, key="dynamic_stop_loss_dde_avg")
        
        if st.button("检查动态止损", key="check_dynamic_stop_loss"):
            from logic.signal_generator import get_signal_generator_v14_4
            signal_gen = get_signal_generator_v14_4()
            result = signal_gen.check_dynamic_stop_loss(stock_code, current_price, entry_price, dde_avg_price)
            
            if result['should_stop_loss']:
                if result['stop_loss_type'] == 'HARD_EXIT':
                    st.error(f"🚨 {result['reason']}")
                else:
                    st.warning(f"⚠️ {result['reason']}")
                
                st.metric("当前亏损", f"{result['current_loss_pct']:.1f}%")
                st.metric("止损类型", result['stop_loss_type'])
                st.metric("止损价格", f"¥{result['stop_loss_price']:.2f}")
                if result['distance_to_dde_avg'] != 0:
                    st.metric("距离DDE均价线", f"{result['distance_to_dde_avg']:.1f}%")
            else:
                st.success(f"✅ {result['reason']}")
                st.metric("当前亏损", f"{result['current_loss_pct']:.1f}%")
    
    with col2:
        st.info("""
        **动态止损特征：**
        - 硬止损：亏损超过 8%
        - 动态止损：跌破DDE均价线超过 2%
        - 软止损：亏损超过 5%
        
        **实战建议：**
        - 对于 20cm 股票，从 12% 杀到 -5% 只需要 10 分钟
        - 不要等 -8% 止损，一旦跌破DDE均价线立即止损
        - 保护本金，活下去才是最重要的
        """)
    
    st.markdown("---")
    
    # 2. 主力成本线
    st.subheader("2. 主力成本线（Institutional Cost Line）")
    st.markdown("""
    **逻辑：** Sum(Price * DDE_Net_Vol) / Sum(DDE_Net_Vol)
    **意义：** 当现价回踩这条线时，就是最硬的低吸点。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code2 = st.text_input("股票代码", value="300992", key="institutional_cost_line_code")
        
        if st.button("计算主力成本线", key="calculate_institutional_cost_line"):
            from logic.signal_generator import get_signal_generator_v14_4
            signal_gen = get_signal_generator_v14_4()
            institutional_cost_line = signal_gen.calculate_institutional_cost_line(stock_code2)
            
            if institutional_cost_line > 0:
                # 获取当前价格
                realtime_data = data_manager.get_realtime_data(stock_code2)
                if realtime_data:
                    current_price = realtime_data.get('price', 0)
                    distance = (current_price - institutional_cost_line) / institutional_cost_line * 100 if institutional_cost_line > 0 else 0
                    
                    st.metric("主力成本线", f"¥{institutional_cost_line:.2f}")
                    st.metric("当前价格", f"¥{current_price:.2f}")
                    st.metric("距离成本线", f"{distance:.1f}%")
                    
                    if abs(distance) <= 2:
                        st.success(f"✅ [黄金低吸点] 当前价格接近主力成本线（{distance:.1f}%），建议低吸")
                    elif distance > 10:
                        st.warning(f"⚠️ [追高风险] 当前价格高于主力成本线{distance:.1f}%，追高风险大")
                    else:
                        st.info(f"📊 [观察中] 当前价格距离主力成本线{distance:.1f}%")
            else:
                st.warning("⚠️ 无法计算主力成本线")
    
    with col2:
        st.info("""
        **主力成本线特征：**
        - 算法：Sum(Price * DDE_Net_Vol) / Sum(DDE_Net_Vol)
        - 意义：主力的平均持仓成本
        - 应用：当现价回踩这条线时，就是最硬的低吸点
        
        **实战建议：**
        - 主力成本线是最硬的支撑位
        - 当股价回踩主力成本线时，如果量能萎缩，可以考虑低吸
        - 不要在主力成本线上方追高，那样成本太高
        """)
    
    st.markdown("---")
    
    # 3. 诱多陷阱识别
    st.subheader("3. 诱多陷阱识别（Trap Pulse Detector）")
    st.markdown("""
    **背景：** 现在很多量化基金会故意在 3% 位置制造 DDE 脉冲来诱多（骗你的 V18.6 系统）。
    **逻辑：** "撤单率 (Cancellation Rate)"。
    **策略：** 如果买一/买二挂单巨大（诱多），但成交时迅速撤单，系统应判定为 FAKE_PULSE 并发出 🚫 [诱多陷阱] 警报。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code3 = st.text_input("股票代码", value="300992", key="trap_pulse_code")
        current_pct_change = st.number_input("当前涨幅（%）", value=4.0, key="trap_pulse_change")
        
        if st.button("检测诱多陷阱", key="check_trap_pulse"):
            result = fake_order_detector.check_trap_pulse(stock_code3, current_pct_change)
            
            if result['is_trap_pulse']:
                st.error(f"🚫 {result['reason']}")
                st.metric("买一/买二挂单巨大", "是" if result['bid1_bid2_huge'] else "否")
                st.metric("买一/买二迅速撤单", "是" if result['bid1_bid2_cancel_fast'] else "否")
                st.metric("撤单率", f"{result['cancellation_rate']:.2%}")
                st.metric("置信度", f"{result['confidence']:.1%}")
            elif result['confidence'] >= 0.5:
                st.warning(f"⚠️ {result['reason']}")
                st.metric("买一/买二挂单巨大", "是" if result['bid1_bid2_huge'] else "否")
                st.metric("买一/买二迅速撤单", "是" if result['bid1_bid2_cancel_fast'] else "否")
                st.metric("撤单率", f"{result['cancellation_rate']:.2%}")
            else:
                st.success(f"✅ {result['reason']}")
    
    with col2:
        st.info("""
        **诱多陷阱特征：**
        - 涨幅在 3%-5% 区间
        - 买一/买二挂单巨大（>10000手）
        - 买一/买二迅速撤单（撤单率 > 50%）
        
        **实战建议：**
        - 如果看到小成交量的票（<5000万）在乱动，直接无视，那是流动性黑洞
        - 识别诱多陷阱，防止被假单欺骗
        - 不要被表面的DDE脉冲迷惑
        """)
    
    st.markdown("---")
    
    # 4. 自动止盈
    st.subheader("4. 自动止盈（The Art of Selling）")
    st.markdown("""
    **背景：** V18.6 解决了"买得好"，V18.7 要解决"卖得神"。
    **逻辑：** "情绪高潮兑现"。
    **策略：** 当股价触及涨停但 "封单量/成交量 < 0.1"（封单极弱），或者 DDE 在高位出现 "背离流出"（股价涨，资金跑），系统应自动触发 TP (Take Profit) 信号，让你在板上把货倒给排队的人。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code4 = st.text_input("股票代码", value="300992", key="take_profit_code")
        current_price2 = st.number_input("当前价格", value=30.00, key="take_profit_price")
        entry_price2 = st.number_input("入场价格", value="26.00, key="take_profit_entry")
        current_pct_change2 = st.number_input("当前涨幅（%）", value=15.0, key="take_profit_change")
        is_limit_up = st.checkbox("是否涨停", value=False, key="take_profit_limit_up")
        
        if st.button("检查止盈信号", key="check_take_profit"):
            from logic.signal_generator import get_signal_generator_v14_4
            signal_gen = get_signal_generator_v14_4()
            result = signal_gen.check_take_profit_signal(stock_code4, current_price2, entry_price2, current_pct_change2, is_limit_up)
            
            if result['should_take_profit']:
                if result['take_profit_type'] == 'HARD_TP':
                    st.error(f"🔔 {result['reason']}")
                else:
                    st.warning(f"⚠️ {result['reason']}")
                
                st.metric("当前盈利", f"{result['current_profit_pct']:.1f}%")
                st.metric("止盈类型", result['take_profit_type'])
                if result['seal_volume_ratio'] > 0:
                    st.metric("封单量/成交量", f"{result['seal_volume_ratio']:.2%}")
                st.metric("DDE背离", "是" if result['dde_divergence'] else "否")
            else:
                st.success(f"✅ {result['reason']}")
                st.metric("当前盈利", f"{result['current_profit_pct']:.1f}%")
    
    with col2:
        st.info("""
        **自动止盈特征：**
        - 硬止盈：封单量/成交量 < 10%
        - 软止盈：DDE背离流出，盈利超过 5%

        **实战建议：**
        - 情绪高潮兑现，在板上把货倒给排队的人
        - 不要贪心，落袋为安
        - 保护利润，活下去才是最重要的
        """)

    st.markdown("---")

    # 5. DDE 加速度（点火信号）
    st.subheader("5. DDE 加速度（Ignition Signal）")
    st.markdown("""
    **背景：** 既然现在 DDE 是后台轮询的，我们可以记录上一次的值。
    **逻辑：** DDE_Velocity = (Current_DDE - Last_DDE) / Time_Interval。
    **意义：** 如果在股价横盘时，DDE 净流入速度突然从 100万/分 暴增到 1000万/分，这就是**"点火信号"**，比单纯看净流入总额更早。
    """)

    col1, col2 = st.columns(2)

    with col1:
        stock_code5 = st.text_input("股票代码", value="300992", key="dde_velocity_code")

        if st.button("检测 DDE 加速度", key="check_dde_velocity"):
            # 从实时数据提供者获取 DDE 加速度
            try:
                from logic.realtime_data_provider import RealtimeDataProvider
                provider = RealtimeDataProvider()

                # 设置监控列表
                provider.set_monitor_list([stock_code5])

                # 等待后台线程更新数据
                import time
                time.sleep(2)

                # 获取 DDE 加速度
                if stock_code5 in provider.dde_velocity_cache:
                    velocity = provider.dde_velocity_cache[stock_code5]
                    st.metric("DDE 加速度", f"{velocity/1000000:.2f}万/秒")

                    if velocity > 1000000:
                        st.error(f"🔥 [点火信号] DDE 加速度暴增: {velocity/1000000:.2f}万/秒")
                        st.success("✅ 建议立即买入！主力正在暴力扫货！")
                    elif velocity > 500000:
                        st.warning(f"⚠️ [加速中] DDE 加速度上升: {velocity/1000000:.2f}万/秒")
                        st.info("📊 建议密切关注，可能即将点火")
                    elif velocity < -1000000:
                        st.error(f"🚨 [恐慌信号] DDE 加速度暴跌: {velocity/1000000:.2f}万/秒")
                        st.warning("⚠️ 建议立即止损！主力正在暴力砸盘！")
                    else:
                        st.info(f"📊 [平稳] DDE 加速度正常: {velocity/1000000:.2f}万/秒")
                else:
                    st.warning("⚠️ 暂无 DDE 加速度数据，请稍后再试")

            except Exception as e:
                st.error(f"❌ 检测失败: {e}")

    with col2:
        st.info("""
        **DDE 加速度特征：**
        - 点火信号：加速度 > 100万/秒
        - 加速中：加速度 > 50万/秒
        - 恐慌信号：加速度 < -100万/秒

        **实战建议：**
        - DDE 加速度比单纯看净流入总额更早
        - 在股价横盘时，如果 DDE 加速度突然暴增，就是点火信号
        - 不要等到涨停才确认，要在点火信号出现时就介入
        - 保护本金，活下去才是最重要的
        """)

# 页脚
st.markdown("---")
st.markdown("""
**V18.6 全谱系战斗逻辑**  
"追高是在买'确定性'，低吸是在买'性价比'。DDE 则是看透'底牌'。  
如果你只追高，你就是在和游资拼手速；只有学会 DDE 辅助下的低吸，你才是在和主力拼布局。  

**V18.6 新增：**  
- 预判模式：在涨停前锁定确定性  
- 弹性缓冲：利用 20cm/30cm 的安全垫  
- 二波预期：博弈主力预期  
- 风险监控：识别虚假繁荣  
""")