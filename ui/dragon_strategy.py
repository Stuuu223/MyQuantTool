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
    st.subheader("🏹 游资/机构双模作战系统")
    st.caption("基于财联社龙头战法精髓：快、狠、准、捕食")
    
    # 1. 模式选择
    st.divider()
    strategy_mode = st.radio(
        "⚔️ 选择作战模式",
        ("🔥 龙头掠食者 (抓连板/妖股)", "🛡️ 趋势中军猎手 (抓机构/业绩/诺思格)", "🚀 半路战法 (抓20cm加速逼空)"),
        index=0,
        horizontal=True
    )
    
    # 根据模式显示不同的说明
    if "龙头" in strategy_mode:
        st.info("""
        **龙头战法核心要点：**
        - 🎯 只做涨停板股票或即将涨停的股票（涨幅 >= 7%）
        - 💰 优选低价股（≤10元）
        - 📊 关注攻击性放量
        - 📈 等待KDJ金叉
        - 🔄 换手率适中（5-15%）
        - 🚀 **扫描全市场，按涨跌幅排序，分析前N只**
        """)
    elif "趋势" in strategy_mode:
        st.info("""
        **趋势中军战法核心要点：**
        - 🎯 专门抓机构票（诺思格、宁德时代等）
        - 📈 沿着5日线/10日线不停涨
        - 💰 不限制价格，机构喜欢高价股
        - 📊 温和放量（量比 1.0 - 3.0）
        - 🔄 均线多头排列（价格 > MA5 > MA10 > MA20）
        - 🚀 **适合稳健投资，长期持有**
        """)
    else:  # 半路战法
        st.info("""
        **半路战法核心要点：**
        - 🎯 专门抓20cm股票在10%-19%区间的半路板
        - 🚀 加速逼空段，半路扫货博弈20%涨停
        - 📊 攻击性放量（量比 > 3.0）
        - 🔄 买盘强（买一量 > 卖一量）
        - ⚠️ **风险较高，适合激进投资者**
        """)
    
    # 扫描参数
    col_scan1, col_scan2, col_scan3 = st.columns(3)
    with col_scan1:
        scan_limit = st.slider("扫描股票数量", 10, 500, 100, 10, key="dragon_scan_limit")
    with col_scan2:
        min_score = st.slider("最低评分门槛", 30, 90, 60, 5, key="dragon_min_score")
    with col_scan3:
        if st.button("🔍 开始扫描", key="dragon_scan_btn"):
            st.session_state.scan_dragon = True
            st.session_state.strategy_mode = strategy_mode
            st.rerun()
    
    # 执行扫描
    if st.session_state.get('scan_dragon', False):
        current_mode = st.session_state.get('strategy_mode', strategy_mode)
        
        # 根据模式调用不同的扫描函数
        if "龙头" in current_mode:
            with st.spinner('🔥 正在执行龙头战法筛选 (竞价爆量)...'):
                scan_result = QuantAlgo.scan_dragon_stocks(limit=scan_limit, min_score=min_score)
        elif "趋势" in current_mode:
            with st.spinner('🛡️ 正在执行趋势中军筛选 (均线多头 + 温和放量)...'):
                scan_result = QuantAlgo.scan_trend_stocks(limit=scan_limit, min_score=min_score)
        else:  # 半路战法
            with st.spinner('🚀 正在执行半路战法筛选 (20cm加速逼空)...'):
                scan_result = QuantAlgo.scan_halfway_stocks(limit=scan_limit, min_score=min_score)
        
        if scan_result['数据状态'] == '正常':
            # 根据模式显示不同的成功消息
            if "龙头" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，分析了 {scan_result['分析数量']} 只，发现 {scan_result['符合条件数量']} 只符合龙头战法条件")
                stock_list_key = '龙头股列表'
            elif "趋势" in current_mode:
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只符合趋势中军特征")
                stock_list_key = '趋势股票列表'
            else:  # 半路战法
                st.success(f"扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只半路板机会")
                stock_list_key = '半路板列表'
            
            if scan_result.get(stock_list_key):
                stocks = scan_result[stock_list_key]
                
                # 根据模式分组显示
                if "龙头" in current_mode:
                    strong_dragons = [s for s in stocks if s['评级得分'] >= 80]
                    potential_dragons = [s for s in stocks if 60 <= s['评级得分'] < 80]
                    weak_dragons = [s for s in stocks if 40 <= s['评级得分'] < 60]
                    
                    # 强龙头
                    if strong_dragons:
                        st.divider()
                        st.subheader("🔥 强龙头（重点关注）")
                        for stock in strong_dragons:
                            _render_dragon_stock(stock, config)
                    
                    # 潜力龙头
                    if potential_dragons:
                        st.divider()
                        st.subheader("📈 潜力龙头（可关注）")
                        for stock in potential_dragons:
                            _render_dragon_stock(stock, config)
                    
                    # 弱龙头
                    if weak_dragons:
                        st.divider()
                        st.subheader("⚠️ 弱龙头（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评级得分': s['评级得分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_dragons])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                elif "趋势" in current_mode:
                    strong_trends = [s for s in stocks if s['评分'] >= 80]
                    potential_trends = [s for s in stocks if 70 <= s['评分'] < 80]
                    weak_trends = [s for s in stocks if 60 <= s['评分'] < 70]
                    
                    # 强趋势中军
                    if strong_trends:
                        st.divider()
                        st.subheader("🔥 强趋势中军（重点关注）")
                        for stock in strong_trends:
                            _render_trend_stock(stock, config)
                    
                    # 趋势中军
                    if potential_trends:
                        st.divider()
                        st.subheader("📈 趋势中军（可关注）")
                        for stock in potential_trends:
                            _render_trend_stock(stock, config)
                    
                    # 弱趋势
                    if weak_trends:
                        st.divider()
                        st.subheader("⚠️ 弱趋势（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评分': s['评分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_trends])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
                
                else:  # 半路战法
                    strong_halfway = [s for s in stocks if s['评分'] >= 80]
                    potential_halfway = [s for s in stocks if 70 <= s['评分'] < 80]
                    weak_halfway = [s for s in stocks if 60 <= s['评分'] < 70]
                    
                    # 强半路板
                    if strong_halfway:
                        st.divider()
                        st.subheader("🔥 强半路板（重点关注）")
                        for stock in strong_halfway:
                            _render_halfway_stock(stock, config)
                    
                    # 半路板
                    if potential_halfway:
                        st.divider()
                        st.subheader("📈 半路板（可关注）")
                        for stock in potential_halfway:
                            _render_halfway_stock(stock, config)
                    
                    # 弱半路板
                    if weak_halfway:
                        st.divider()
                        st.subheader("⚠️ 弱半路板（谨慎关注）")
                        df_weak = pd.DataFrame([{
                            '代码': s['代码'],
                            '名称': s['名称'],
                            '最新价': f"¥{s['最新价']:.2f}",
                            '涨跌幅': f"{s['涨跌幅']:.2f}%",
                            '评分': s['评分'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%"
                        } for s in weak_halfway])
                        st.dataframe(df_weak, width="stretch", hide_index=True)
            else:
                st.warning("未发现符合条件的股票")
                st.info("💡 提示：可以降低最低评分门槛或增加扫描数量")
                            col1, col2 = st.columns(2)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            
                            # 显示量比、换手率、竞价量
                            st.write("**实时数据：**")
                            col3, col4, col5, col6 = st.columns(4)
                            col3.metric("量比", f"{stock.get('量比', 0):.2f}")
                            col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
                            col5.metric("竞价量", f"{stock.get('竞价量', 0)} 手")
                            col6.metric("竞价抢筹度", f"{stock.get('竞价抢筹度', 0):.2%}")
                            
                            # 显示买卖盘口数据
                            st.write("**买卖盘口：**")
                            col7, col8, col9, col10 = st.columns(4)
                            
                            # 判断是否涨停
                            symbol = stock.get('代码', '')
                            change_pct = stock.get('涨跌幅', 0)
                            
                            # 根据股票代码判断涨停阈值
                            if symbol.startswith('30') or symbol.startswith('68'):
                                # 创业板/科创板：20% 涨停
                                is_limit_up = change_pct >= 19.5
                            else:
                                # 主板：10% 涨停
                                is_limit_up = change_pct >= 9.5
                            
                            if is_limit_up:
                                col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}", delta="涨停")
                                col8.metric("卖一价", "涨停板", delta="无卖单")
                                col9.metric("买一量", f"{stock.get('买一量', 0)} 手", delta="封单")
                                col10.metric("卖一量", "0 手", delta="无卖单")
                            else:
                                col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
                                col8.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
                                col9.metric("买一量", f"{stock.get('买一量', 0)} 手")
                                col10.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
                            
                            # 显示开盘涨幅和封单金额
                            st.write("**其他指标：**")
                            col11, col12, col13 = st.columns(3)
                            col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
                            
                            if is_limit_up:
                                # 涨停时，封单金额 = 买一量 * 价格
                                seal_amount = stock.get('买一量', 0) * stock.get('最新价', 0) / 10000  # 转换为万
                                col12.metric("封单金额", f"¥{seal_amount:.2f} 万", delta="涨停封单")
                                col13.metric("买卖价差", "N/A", delta="涨停")
                            else:
                                col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
                                col13.metric("买卖价差", f"{stock.get('买卖价差', 0):.2f}%")
                            
                            # 显示评级得分和评级说明
                            st.write(f"**评级得分**: {stock['评级得分']}/100")
                            st.info(f"**评级说明**: {stock['评级说明']}")
                            
                            # 显示五个条件得分
                            st.write("**五个条件得分：**")
                            details = stock['详情']
                            st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/25")
                            st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
                            st.write(f"- 成交量: {details['条件3_成交量']['得分']}/25")
                            st.write(f"- 加速段: {details['条件4_加速段']['得分']}/25")
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
                        with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
                            col1, col2 = st.columns(2)
                            col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            
                            # 显示量比、换手率、竞价量
                            st.write("**实时数据：**")
                            col3, col4, col5, col6 = st.columns(4)
                            col3.metric("量比", f"{stock.get('量比', 0):.2f}")
                            col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
                            col5.metric("竞价量", f"{stock.get('竞价量', 0)} 手")
                            col6.metric("竞价抢筹度", f"{stock.get('竞价抢筹度', 0):.2%}")
                            
                            # 显示买卖盘口数据
                            st.write("**买卖盘口：**")
                            col7, col8, col9, col10 = st.columns(4)
                            col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
                            col8.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
                            col9.metric("买一量", f"{stock.get('买一量', 0)} 手")
                            col10.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
                            
                            # 显示开盘涨幅和封单金额
                            st.write("**其他指标：**")
                            col11, col12, col13 = st.columns(3)
                            col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
                            col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
                            col13.metric("买卖价差", f"{stock.get('买卖价差', 0):.2f}%")
                            
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
                            '评级说明': s['评级说明'],
                            '量比': f"{s.get('量比', 0):.2f}",
                            '换手率': f"{s.get('换手率', 0):.2f}%",
                            '竞价量': f"{s.get('竞价量', 0)} 手"
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
        
        # 重置扫描状态
        st.session_state.scan_dragon = False
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
            """)
        
        with st.expander("📊 趋势中军战法详解"):
            st.markdown("""
            **核心特征：**
            - 沿着5日线、10日线不停涨
            - 温和放量（量比1.0-3.0）
            - 均线多头排列（价格 > MA5 > MA10 > MA20）
            - 机构资金推土机式买入
            
            **适合人群：**
            - 稳健投资者
            - 长期持有者
            - 追求稳定收益
            
            **操作建议：**
            - 沿5日线低吸
            - 不要追高
            - 长期持有
            """)
        
        with st.expander("🚀 半路战法详解"):
            st.markdown("""
            **核心特征：**
            - 20cm股票在10%-19%区间
            - 加速逼空段
            - 攻击性放量（量比>3.0）
            - 买盘强（买一量 > 卖一量）
            
            **适合人群：**
            - 激进投资者
            - 短线交易者
            - 追求高收益
            
            **操作建议：**
            - 半路扫货
            - 博弈20%涨停
            - 严格止损
            """)


def _render_dragon_stock(stock, config):
    """渲染龙头股票详情"""
    with st.expander(f"{stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率、竞价量
        st.write("**实时数据：**")
        col3, col4, col5, col6 = st.columns(4)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        col5.metric("竞价量", f"{stock.get('竞价量', 0)} 手")
        col6.metric("竞价抢筹度", f"{stock.get('竞价抢筹度', 0):.2%}")
        
        # 显示买卖盘口数据
        st.write("**买卖盘口：**")
        col7, col8, col9, col10 = st.columns(4)
        
        # 判断是否涨停
        symbol = stock.get('代码', '')
        change_pct = stock.get('涨跌幅', 0)
        
        # 根据股票代码判断涨停阈值
        if symbol.startswith('30') or symbol.startswith('68'):
            # 创业板/科创板：20% 涨停
            is_limit_up = change_pct >= 19.5
        else:
            # 主板：10% 涨停
            is_limit_up = change_pct >= 9.5
        
        if is_limit_up:
            col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}", delta="涨停")
            col8.metric("卖一价", "涨停板", delta="无卖单")
            col9.metric("买一量", f"{stock.get('买一量', 0)} 手", delta="封单")
            col10.metric("卖一量", "0 手", delta="无卖单")
        else:
            col7.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
            col8.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
            col9.metric("买一量", f"{stock.get('买一量', 0)} 手")
            col10.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
        
        # 显示开盘涨幅和封单金额
        st.write("**其他指标：**")
        col11, col12, col13 = st.columns(3)
        col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
        
        if is_limit_up:
            # 涨停时，封单金额 = 买一量 * 价格
            seal_amount = stock.get('买一量', 0) * stock.get('最新价', 0) / 10000  # 转换为万
            col12.metric("封单金额", f"¥{seal_amount:.2f} 万", delta="涨停封单")
            col13.metric("买卖价差", "N/A", delta="涨停")
        else:
            col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
            col13.metric("买卖价差", f"{stock.get('买卖价差', 0):.2f}%")
        
        # 显示评级得分和评级说明
        st.write(f"**评级得分**: {stock['评级得分']}/100")
        st.info(f"**评级说明**: {stock['评级说明']}")
        
        # 显示五个条件得分
        st.write("**五个条件得分：**")
        details = stock['详情']
        st.write(f"- 涨停板: {details['条件1_涨停板']['得分']}/25")
        st.write(f"- 价格: {details['条件2_价格']['得分']}/20")
        st.write(f"- 成交量: {details['条件3_成交量']['得分']}/25")
        st.write(f"- 加速段: {details['条件4_加速段']['得分']}/25")
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


def _render_trend_stock(stock, config):
    """渲染趋势中军股票详情"""
    with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率
        st.write("**实时数据：**")
        col3, col4 = st.columns(2)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
        # 显示均线
        st.write("**均线系统：**")
        col5, col6, col7 = st.columns(3)
        col5.metric("MA5", f"¥{stock.get('MA5', 0):.2f}")
        col6.metric("MA10", f"¥{stock.get('MA10', 0):.2f}")
        col7.metric("MA20", f"¥{stock.get('MA20', 0):.2f}")
        
        # 显示买卖盘口
        st.write("**买卖盘口：**")
        col8, col9, col10, col11 = st.columns(4)
        col8.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
        col9.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
        col10.metric("买一量", f"{stock.get('买一量', 0)} 手")
        col11.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
        
        # 显示信号
        st.write(f"**评级得分**: {stock['评分']}/100")
        st.info(f"**信号**: {stock['信号']}")
        
        # 添加到自选股按钮
        if st.button(f"添加到自选", key=f"add_trend_{stock['代码']}"):
            watchlist = config.get('watchlist', [])
            if stock['代码'] not in watchlist:
                watchlist.append(stock['代码'])
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
            else:
                st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")


def _render_halfway_stock(stock, config):
    """渲染半路板股票详情"""
    with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
        col1, col2 = st.columns(2)
        col1.metric("最新价", f"¥{stock['最新价']:.2f}")
        col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
        
        # 显示量比、换手率
        st.write("**实时数据：**")
        col3, col4 = st.columns(2)
        col3.metric("量比", f"{stock.get('量比', 0):.2f}")
        col4.metric("换手率", f"{stock.get('换手率', 0):.2f}%")
        
        # 显示买卖盘口
        st.write("**买卖盘口：**")
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
        col6.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
        col7.metric("买一量", f"{stock.get('买一量', 0)} 手")
        col8.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
        
        # 显示信号和操作建议
        st.write(f"**评级得分**: {stock['评分']}/100")
        st.info(f"**信号**: {stock['信号']}")
        st.success(f"**操作建议**: {stock['操作建议']}")
        
        # 添加到自选股按钮
        if st.button(f"添加到自选", key=f"add_halfway_{stock['代码']}"):
            watchlist = config.get('watchlist', [])
            if stock['代码'] not in watchlist:
                watchlist.append(stock['代码'])
                config.set('watchlist', watchlist)
                st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
            else:
                st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
            - 如果跌幅超过10%，立即止损，不要找任何理由
            """)