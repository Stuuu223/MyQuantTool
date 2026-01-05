"""
龙头战法模块

基于财联社龙头战法精髓：快、狠、准、捕食
"""

import streamlit as st
import pandas as pd
from logic.algo import QuantAlgo
from logic.logger import get_logger
from config import Config

logger = get_logger(__name__)


def render_dragon_strategy_tab(db, config):
    """
    渲染龙头战法标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("🔥 龙头战法 - 捕捉潜在龙头股")
    st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
    
    st.info("""
    **龙头战法核心要点：**
    - 🎯 只做涨停板股票
    - 💰 优选低价股（≤10元）
    - 📊 关注攻击性放量
    - 📈 等待KDJ金叉
    - 🔄 换手率适中（5-15%）
    """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 100, 50, 10, key="dragon_scan_limit")
    with col_scan2:
        min_score = st.slider("最低评分门槛", 40, 80, 60, 5, key="dragon_min_score")
    with col_scan3:
        if st.button("🔍 开始扫描", key="dragon_scan_btn"):
            st.session_state.scan_dragon = True
            st.rerun()
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        with st.spinner('正在扫描市场中的潜在龙头股...'):
            scan_result = QuantAlgo.scan_dragon_stocks(limit=scan_limit, min_score=min_score)
        
        if scan_result['数据状态'] == '正常':
            st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只潜在龙头股")
            
            if scan_result['龙头股列表']:
                # 按评级分组显示
                strong_dragons = [s for s in scan_result['龙头股列表'] if s['评级得分'] >= 80]
                potential_dragons = [s for s in scan_result['龙头股列表'] if 60 <= s['评级得分'] < 80]
                weak_dragons = [s for s in scan_result['龙头股列表'] if 40 <= s['评级得分'] < 60]
                
                # 强龙头
                if strong_dragons:
                    st.divider()
                    st.subheader("🔥 强龙头（重点关注）")
                    for stock in strong_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}", key=f"dragon_strong_{stock['代码']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("评级得分", f"{stock['评级得分']}/100")
                            
                            # 显示五个条件得分
                            st.write("**五个条件得分：**")
                            details = stock['详情']
                            st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/20")
                            st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
                            st.write(f"- 成交量: {details['条件3_成交量']['得分']}/20")
                            st.write(f"- KDJ: {details['条件4_KDJ']['得分']}/20")
                            st.write(f"- 换手率: {details['条件5_换手率']['得分']}/20")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in details['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"添加到自选", key=f"add_dragon_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 潜力龙头
                if potential_dragons:
                    st.divider()
                    st.subheader("📈 潜力龙头（可关注）")
                    for stock in potential_dragons:
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}", key=f"dragon_potential_{stock['代码']}"):
                            col1, col2 = st.columns(2)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            
                            st.write(f"评级得分: {stock['评级得分']}/100")
                            st.info(f"评级说明: {stock['评级说明']}")
                            
                            # 显示操作建议
                            st.info("**操作建议：**")
                            for suggestion in stock['详情']['操作建议']:
                                st.write(suggestion)
                            
                            # 添加到自选股按钮
                            if st.button(f"添加到自选", key=f"add_potential_{stock['代码']}"):
                                watchlist = config.get('watchlist', [])
                                if stock['代码'] not in watchlist:
                                    watchlist.append(stock['代码'])
                                    config.set('watchlist', watchlist)
                                    st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                else:
                                    st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                
                # 弱龙头
                if weak_dragons:
                    st.divider()
                    st.subheader("⚠️ 弱龙头（谨慎关注）")
                    df_weak = pd.DataFrame([
                        {
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评级得分': s['评级得分'],
                            '评级说明': s['评级说明']
                        }
                        for s in weak_dragons
                    ])
                    st.dataframe(df_weak, width="stretch", hide_index=True)
            else:
                st.warning("未发现符合条件的龙头股")
                st.info("💡 提示：可以降低最低评分门槛或增加扫描数量")
        else:
            st.error(f"❌ {scan_result['数据状态']}")
            if '错误信息' in scan_result:
                st.caption(scan_result['错误信息'])
            if '说明' in scan_result:
                st.info(scan_result['说明'])
    else:
        st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的潜在龙头股")
        
        # 显示龙头战法说明
        st.divider()
        st.subheader("📖 龙头战法详解")
        
        with st.expander("🎯 龙头股五个条件"):
            st.markdown("""
            **1. 涨停板（20分）**
            - 必须从涨停板开始
            - 涨停板是多空双方最准确的攻击信号
            - 是所有黑马的摇篮，是龙头的发源地
            
            **2. 价格（20分）**
            - 低价股（≤10元）：20分
            - 适中价格（10-15元）：10分
            - 高价股（>15元）：0分
            - 高价股不具备炒作空间，只有低价股才能得到股民追捧
            
            **3. 成交量（20分）**
            - 攻击性放量（量比>2）：20分
            - 温和放量（量比1.5-2）：15分
            - 缩量或正常：0分
            - 龙头一般出现三日以上的攻击性放量特征
            
            **4. KDJ（20分）**
            - KDJ金叉：20分
            - KDJ低位（K<30）：10分
            - KDJ不在低位：0分
            - 日线、周线、月线KDJ同时低位金叉更安全
            
            **5. 换手率（20分）**
            - 适中换手率（5-15%）：20分
            - 偏低换手率（2-5%）：15分
            - 过高或过低换手率：10分或0分
            - 换手率适中显示资金活跃度
            """)
        
        with st.expander("💡 买入技巧"):
            st.markdown("""
            **买入时机：**
            
            **1. 涨停开闸放水时买入**
            - 涨停板打开时，如果量能充足，可以介入
            
            **2. 高开时买入**
            - 未开板的个股，第二天若高开1.5-3.5%，可以买入
            
            **3. 回调买入**
            - 龙头股回到第一个涨停板的启涨点，构成回调买点
            - 比第一个买点更稳、更准、更狠
            
            **操作要点：**
            - 只做第一个涨停板
            - 只做第一次放量的涨停板
            - 相对股价不高，流通市值不大
            - 指标从低位上穿，短线日KDJ低位金叉
            """)
        
        with st.expander("⚠️ 风险控制"):
            st.markdown("""
            **止损点设定：**
            
            **强势市场：**
            - 以该股的第一个涨停板为止损点
            
            **弱势市场：**
            - 以3%为止损点
            
            **严格纪律：**
            - 绝对不允许个股跌幅超过10%
            - 如果跌幅超过10%，立即止损，不要找任何理由
            """)