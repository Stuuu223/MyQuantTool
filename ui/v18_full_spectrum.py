#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.5 全谱系战斗逻辑 UI
集成所有 V18.5 新功能：
1. DDE 核心战法
2. 低吸逻辑引擎
3. 动态涨停系数
4. 逻辑回踩战法
"""

import streamlit as st
import pandas as pd
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.utils import Utils

logger = get_logger(__name__)

# 页面配置
st.set_page_config(
    page_title="V18.5 全谱系战斗逻辑",
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
    return data_manager, money_flow_master, low_suction_engine

data_manager, money_flow_master, low_suction_engine = init_managers()

# 标题
st.title("🦁 V18.5 全谱系战斗逻辑")
st.markdown("---")

# 选项卡
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 DDE 核心战法",
    "🔻 低吸逻辑引擎",
    "🎯 动态涨停系数",
    "🔄 逻辑回踩战法",
    "📈 综合分析"
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

# 页脚
st.markdown("---")
st.markdown("""
**V18.5 全谱系战斗逻辑**  
"追高是在买'确定性'，低吸是在买'性价比'。DDE 则是看透'底牌'。  
如果你只追高，你就是在和游资拼手速；只有学会 DDE 辅助下的低吸，你才是在和主力拼布局。"
""")