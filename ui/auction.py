"""集合竞价模块"""
import streamlit as st
import pandas as pd
from logic.algo import QuantAlgo
from logic.formatter import Formatter

def render_auction_tab(db, config):
    st.subheader("⚡ 集合竞价")
    st.caption("基于雪球集合竞价选股法：竞价看方向，弱转强战法，竞价扩散法")
    
    st.info("""
    **集合竞价选股核心要点：**
    - 🕐 关注9:20之后的竞价情况（不可撤单，真实反映资金博弈）
    - 📊 重点关注放量的股票（量比>1.5）
    - 🔄 竞价弱转强：烂板/炸板股次日竞价超预期
    - 📈 竞价扩散法：通过一字板强势股挖掘同题材概念股
    """)
    
    # 功能选择
    auction_mode = st.radio("选择功能", ["竞价选股扫描", "竞价弱转强检测", "竞价扩散法"], horizontal=True)
    
    if auction_mode == "竞价选股扫描":
        st.divider()
        st.subheader("🔍 竞价选股扫描")
        
        # 扫描参数
        col_scan1, col_scan2 = st.columns(2)
        with col_scan1:
            scan_limit = st.slider("扫描股票数量", 50, 200, 100, 10)
        with col_scan2:
            if st.button("🔍 开始扫描", key="scan_auction_btn"):
                st.session_state.scan_auction = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_auction', False):
            with st.spinner('正在扫描集合竞价股票...'):
                scan_result = QuantAlgo.scan_auction_stocks(limit=scan_limit)
            
            if scan_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！共扫描 {scan_result['扫描数量']} 只股票，发现 {scan_result['符合条件数量']} 只竞价活跃股票")
                
                if scan_result['竞价股票列表']:
                    # 按评级分组显示
                    strong_stocks = [s for s in scan_result['竞价股票列表'] if s['评分'] >= 80]
                    active_stocks = [s for s in scan_result['竞价股票列表'] if 60 <= s['评分'] < 80]
                    normal_stocks = [s for s in scan_result['竞价股票列表'] if 40 <= s['评分'] < 60]
                    
                    # 强势股票
                    if strong_stocks:
                        st.divider()
                        st.subheader("🔥 强势股票（重点关注）")
                        for stock in strong_stocks:
                            with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3, col4, col5 = st.columns(5)
                                col1.metric("最新价", f"¥{stock['最新价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("量比", stock['量比'])
                                col4.metric("换手率", f"{stock['换手率']:.2f}%")
                                col5.metric("竞价量", f"{stock.get('竞价量', 0)} 手")
                                
                                # 显示买卖盘口数据
                                st.write("**买卖盘口：**")
                                col6, col7, col8, col9 = st.columns(4)
                                
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
                                    col6.metric("买一价", f"¥{stock.get('买一价', 0):.2f}", delta="涨停")
                                    col7.metric("卖一价", "涨停板", delta="无卖单")
                                    col8.metric("买一量", f"{stock.get('买一量', 0)} 手", delta="封单")
                                    col9.metric("卖一量", "0 手", delta="无卖单")
                                else:
                                    col6.metric("买一价", f"¥{stock.get('买一价', 0):.2f}")
                                    col7.metric("卖一价", f"¥{stock.get('卖一价', 0):.2f}")
                                    col8.metric("买一量", f"{stock.get('买一量', 0)} 手")
                                    col9.metric("卖一量", f"{stock.get('卖一量', 0)} 手")
                                
                                # 显示开盘涨幅、竞价抢筹度和买卖价差
                                st.write("**其他指标：**")
                                col10, col11, col12, col13 = st.columns(4)
                                col10.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
                                col11.metric("竞价抢筹度", f"{stock.get('竞价抢筹度', 0):.2%}")
                                
                                if is_limit_up:
                                    # 涨停时，封单金额 = 买一量（手数）× 100（股/手）× 价格
                                    seal_amount = stock.get('买一量', 0) * 100 * stock.get('最新价', 0) / 10000  # 转换为万
                                    col12.metric("封单金额", f"¥{seal_amount:.2f} 万", delta="涨停封单")
                                    col13.metric("买卖价差", "N/A", delta="涨停")
                                else:
                                    col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
                                    # 买卖价差
                                    price_gap = stock.get('买一价', 0) and stock.get('卖一价', 0)
                                    if price_gap and stock.get('买一价', 0) > 0:
                                        gap_pct = (stock.get('卖一价', 0) - stock.get('买一价', 0)) / stock.get('买一价', 0) * 100
                                        col13.metric("买卖价差", f"{gap_pct:.2f}%")
                                    else:
                                        col13.metric("买卖价差", "N/A")
                                
                                # 显示信号
                                st.write("**竞价信号：**")
                                for signal in stock['信号']:
                                    st.write(f"- {signal}")
                                
                                # 显示操作建议
                                st.info(f"**操作建议：** {stock['操作建议']}")
                                
                                # 弱转强标记
                                if stock['弱转强']:
                                    st.success("🔄 竞价弱转强！")
                                
                                # 添加到自选股按钮
                                if st.button(f"⭐ 添加到自选", key=f"add_auction_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                    
                    # 活跃股票
                    if active_stocks:
                        st.divider()
                        st.subheader("🟡 活跃股票（可关注）")
                        for stock in active_stocks:
                            with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
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
                                
                                # 显示开盘涨幅、封单金额和买卖价差
                                st.write("**其他指标：**")
                                col11, col12, col13, col14 = st.columns(4)
                                col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
                                col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
                                col13.metric("买卖价差", f"{stock.get('买卖价差', 0):.2f}%")
                                col14.metric("评分", f"{stock['评分']}/100")
                                
                                # 显示信号
                                st.write("**竞价信号：**")
                                for signal in stock['信号']:
                                    st.write(f"- {signal}")
                                
                                # 显示操作建议
                                st.info(f"**操作建议：** {stock['操作建议']}")
                                
                                # 弱转强标记
                                if stock['弱转强']:
                                    st.success("🔄 竞价弱转强！")
                                
                                # 添加到自选股按钮
                                if st.button(f"⭐ 添加到自选", key=f"add_active_{stock['代码']}"):
                                    watchlist = config.get('watchlist', [])
                                    if stock['代码'] not in watchlist:
                                        watchlist.append(stock['代码'])
                                        config.set('watchlist', watchlist)
                                        st.success(f"已添加 {stock['名称']} ({stock['代码']}) 到自选股")
                                    else:
                                        st.info(f"{stock['名称']} ({stock['代码']}) 已在自选股中")
                    
                    # 一般股票
                    if normal_stocks:
                        st.divider()
                        st.subheader("🟢 一般股票（观望）")
                        for stock in normal_stocks[:20]:  # 最多显示20只，避免页面过长
                            with st.expander(f"{stock['评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
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
                                
                                # 显示开盘涨幅、封单金额和买卖价差
                                st.write("**其他指标：**")
                                col11, col12, col13, col14 = st.columns(4)
                                col11.metric("开盘涨幅", f"{stock.get('开盘涨幅', 0):.2f}%")
                                col12.metric("封单金额", f"¥{stock.get('封单金额', 0):.2f} 万")
                                col13.metric("买卖价差", f"{stock.get('买卖价差', 0):.2f}%")
                                col14.metric("评分", f"{stock['评分']}/100")
                                
                                # 显示信号
                                st.write("**竞价信号：**")
                                for signal in stock['信号']:
                                    st.write(f"- {signal}")
                                
                                # 显示操作建议
                                st.info(f"**操作建议：** {stock['操作建议']}")
                                
                                # 弱转强标记
                                if stock['弱转强']:
                                    st.success("🔄 竞价弱转强！")
                        
                        if len(normal_stocks) > 20:
                            st.info(f"还有 {len(normal_stocks) - 20} 只一般股票未显示，请提高评分门槛以筛选更优质的股票")
                else:
                    st.warning("⚠️ 未发现符合条件的竞价股票")
                    st.info("💡 提示：当前市场可能没有明显的竞价异动")
            else:
                st.error(f"❌ {scan_result['数据状态']}")
                if '错误信息' in scan_result:
                    st.caption(scan_result['错误信息'])
                if '说明' in scan_result:
                    st.info(scan_result['说明'])
        else:
            st.info("👆 点击「开始扫描」按钮，系统将自动扫描市场中的竞价活跃股票")
    
    elif auction_mode == "竞价弱转强检测":
        st.divider()
        st.subheader("🔄 竞价弱转强检测")
        
        st.info("""
        **竞价弱转强战法：**
        - 适用于烂板、炸板股次日竞价超预期的情况
        - 前一天烂板/炸板（弱势），次日竞价放量高开（超预期）
        - 说明有资金抢筹，值得重点关注
        """)
        
        # 股票选择
        col_stock1, col_stock2 = st.columns(2)
        with col_stock1:
            check_symbol = st.text_input("股票代码", placeholder="输入6位股票代码", help="例如：600519", key="auction_symbol")
        with col_stock2:
            if st.button("🔍 检测弱转强", key="check_weak_to_strong_btn"):
                if check_symbol:
                    st.session_state.check_symbol = check_symbol
                    st.session_state.check_weak_to_strong = True
                    st.rerun()
                else:
                    st.warning("请输入股票代码")
        
        # 执行检测
        if st.session_state.get('check_weak_to_strong', False) and st.session_state.get('check_symbol'):
            check_symbol = st.session_state.check_symbol
            
            with st.spinner(f'正在检测 {check_symbol} 的竞价弱转强情况...'):
                df = db.get_history_data(check_symbol)
                
                if not df.empty and len(df) > 5:
                    weak_to_strong_result = QuantAlgo.detect_auction_weak_to_strong(df, check_symbol)
                    
                    if weak_to_strong_result['检测状态'] == '正常':
                        st.success(f"✅ 检测完成！")
                        
                        stock_name = QuantAlgo.get_stock_name(check_symbol)
                        st.subheader(f"📊 {stock_name} ({check_symbol}) - 弱转强检测结果")
                        
                        # 显示基本信息
                        col1, col2, col3 = st.columns(3)
                        col1.metric("前一天类型", weak_to_strong_result.get('前一天类型', '-'))
                        col2.metric("昨日涨跌幅", f"{weak_to_strong_result.get('昨日涨跌幅', 0):.2f}%")
                        col3.metric("今日开盘涨跌幅", f"{weak_to_strong_result.get('今日开盘涨跌幅', 0):.2f}%")
                        
                        # 显示量比
                        st.metric("量比", weak_to_strong_result.get('量比', 0))
                        
                        # 显示评级
                        if weak_to_strong_result.get('是否弱转强'):
                            st.success(f"🔥 {weak_to_strong_result['评级']}")
                        else:
                            st.warning(f"⚠️ {weak_to_strong_result['评级']}")
                        
                        # 显示信号
                        st.divider()
                        st.subheader("📋 检测信号")
                        for signal in weak_to_strong_result.get('信号', []):
                            st.write(f"- {signal}")
                        
                        # 显示操作建议
                        st.divider()
                        st.info(f"**操作建议：** {weak_to_strong_result.get('操作建议', '')}")
                    else:
                        st.warning(f"⚠️ {weak_to_strong_result['检测状态']}")
                        if '说明' in weak_to_strong_result:
                            st.info(weak_to_strong_result['说明'])
                else:
                    st.error("❌ 无法获取股票数据")
                    st.info("💡 请检查股票代码是否正确")
        else:
            st.info("👆 输入股票代码并点击「检测弱转强」按钮")
    
    elif auction_mode == "竞价扩散法":
        st.divider()
        st.subheader("📈 竞价扩散法")
        
        st.info("""
        **竞价扩散法：**
        - 通过一字板强势股挖掘同题材概念股
        - 筛选首板、二板，且封单金额超过流通盘5%
        - 剔除热炒题材，保留新题材
        - 根据题材找出同概念股，关注未涨停但高开的股票
        """)
        
        # 扫描参数
        col_diff1, col_diff2 = st.columns(2)
        with col_diff1:
            diffusion_limit = st.slider("扫描股票数量", 20, 100, 50, 10)
        with col_diff2:
            if st.button("🔍 扫描一字板", key="scan_diffusion_btn"):
                st.session_state.scan_diffusion = True
                st.rerun()
        
        # 执行扫描
        if st.session_state.get('scan_diffusion', False):
            with st.spinner('正在扫描强势一字板股票...'):
                diffusion_result = QuantAlgo.auction_diffusion_method(limit=diffusion_limit)
            
            if diffusion_result['数据状态'] == '正常':
                st.success(f"✅ 扫描完成！发现 {len(diffusion_result['强势一字板股票'])} 只强势一字板股票")
                
                if diffusion_result['强势一字板股票']:
                    # 显示强势一字板股票
                    st.divider()
                    st.subheader("🔥 强势一字板股票")
                    
                    df_strong = pd.DataFrame(diffusion_result['强势一字板股票'])
                    df_strong['封单金额'] = df_strong['封单金额'].apply(lambda x: f"{x/10000:.2f}万" if x < 100000000 else f"{x/100000000:.2f}亿")
                    df_strong['流通市值'] = df_strong['流通市值'].apply(lambda x: f"{x/100000000:.2f}亿")
                    
                    st.dataframe(df_strong, width="stretch", hide_index=True)
                    
                    # 显示操作建议
                    st.divider()
                    st.subheader("💡 操作建议")
                    for i, suggestion in enumerate(diffusion_result['操作建议'], 1):
                        st.write(f"{i}. {suggestion}")
                    
                    # 说明
                    st.info(diffusion_result['说明'])
                else:
                    st.warning("⚠️ 未发现符合条件的强势一字板股票")
                    st.info("💡 提示：当前市场可能没有封单充足的一字板股票")
            else:
                st.error(f"❌ {diffusion_result['数据状态']}")
                if '错误信息' in diffusion_result:
                    st.caption(diffusion_result['错误信息'])
                if '说明' in diffusion_result:
                    st.info(diffusion_result['说明'])
        else:
            st.info("👆 点击「扫描一字板」按钮，系统将自动扫描强势一字板股票")
    
    # 显示集合竞价选股说明
    st.divider()
    st.subheader("📖 集合竞价选股详解")
    
    with st.expander("🕐 集合竞价规则"):
        st.markdown("""
        **时间规则：**
        
        **9:15 - 9:20：自由报价**
        - 既可以下单，也可以撤单
        - 可能存在诱多诱空，大资金在9:19分最后一秒撤单
        
        **9:20 - 9:25：不可撤单**
        - 可以下单，不能撤单
        - 真实显示当天该股在竞价期间资金的博弈情况
        - **重点关注这个时间段**
        
        **9:25 - 9:30：接受报价但不处理**
        - 系统接受报价，但不做处理
        - 等待正式开盘
        
        **成交原则：**
        - 最大成交量优先，决定当天的开盘价
        - 竞价异常（放量）的股票，基本都是大资金背后作为推手
        """)
    
    with st.expander("📊 集合竞价图形解读"):
        st.markdown("""
        **理想的竞价图形：**
        
        **1. 股价走势**
        - 集合竞价期间，股价逐步抬高为好
        - 最好的情况是最后时刻，股价被大单买入快速拉升
        
        **2. 成交量柱**
        - 柱子代表竞价的成交量
        - 量能最好是随着股价的抬升放大
        - 绿色代表向下的卖盘
        - 红色代表资金主动向上买入
        - 成交量逐渐放大，且红色柱子连续排列，较好
        
        **3. 诱空示例**
        - 大资金在竞价期间诱空，骗取散户筹码
        - 股价先拉升，然后在9:19分快速撤单，股价回落
        - 这种情况要警惕，不要盲目追高
        """)
    
    with st.expander("🔄 竞价弱转强战法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"弱"？**
        - 烂板：涨停板上抛压不断，持筹者不看好后续走势
        - 炸板：涨停板打开，板上介入的资金全部被套
        - 即使封板，第二天也很难有溢价
        
        **什么是"弱转强"？**
        - 前一天烂板或炸板（弱势）
        - 第二天竞价应该是没有溢价，以一种很弱的表现形式
        - **但是第二天开盘资金出现放量抢筹的情况**
        - 这就是超预期，超出市场预期
        
        **为什么有效？**
        - 烂板/炸板股，次日拉升起来压力非常大
        - 一般没有资金愿意去做多
        - 如果竞价直接放量高开，完全不惧前一天板上被套牢的资金
        - 说明有新资金强势介入，值得重点关注
        
        **操作要点：**
        - 关注前一天烂板或炸板的股票
        - 次日9:20之后观察竞价情况
        - 如果竞价放量高开（>2%），且量比>1.5，考虑参与
        - 设置好止损点，严格执行
        """)
    
    with st.expander("📈 竞价扩散法"):
        st.markdown("""
        **核心逻辑：**
        
        **什么是"竞价扩散"？**
        - 通过对个股封单的观测，以及对个股属性的识别
        - 找到所对应的板块，提前预判当天资金的主攻方向
        - 通过竞价期间一字板的强势股去做挖掘
        - "扩散"到同题材概念还未涨停的个股
        
        **使用时间：**
        - 9:20 - 9:30之间（9:20之后不能撤单）
        
        **使用方法：**
        
        **1. 筛选一字涨停股票**
        - 9:20之后，对当天一字涨停的股票进行浏览
        - 选出首板股、二板股（首板股做参考最好）
        - 记录涨停板上的封单金额
        
        **2. 进一步筛选**
        - 首板股里面属于热炒题材的剔除
        - 必须是新题材
        - 一字板封单不足真实流通盘5%的剔除
        
        **3. 锁定题材**
        - 剩下的是"集合竞价强势涨停（一字板）的新题材"
        - 通过个股，找为什么当天他能一字板的原因
        - 迅速锁定题材
        
        **4. 挖掘同概念股**
        - 搜索同题材的概念股
        - 按涨幅排序（集合竞价的涨幅）
        - 把还未涨停的，但是高开的同概念其他股加入自选
        - 观察竞价是否有资金异动抢筹
        - 竞价后直接参与，或选择第一个上板的股去做打板
        
        **为什么有效？**
        - 很多股票开盘秒板，是因为竞价期间强势的一字板新题材获得了市场资金的认可
        - 其他聪明的大资金快速锁定相关概念的其他个股
        - 开盘后立即抢筹买入造成的
        - 我们跟着聪明资金走，"他们吃肉，我们喝汤"
        """)
