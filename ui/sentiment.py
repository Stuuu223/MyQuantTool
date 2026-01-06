"""情绪分析模块"""
import streamlit as st
import pandas as pd
from logic.algo_sentiment import MarketSentimentAnalyzer
from logic.formatter import Formatter
import plotly.graph_objects as go

def render_sentiment_tab(db, config):
    st.subheader("📈 情绪分析")
    st.caption("基于拾荒网技术文章:情绪指数、涨停板分析、龙虎榜深度分析")
    
    # 初始化情绪分析器
    from logic.algo_sentiment import MarketSentimentAnalyzer
    sentiment_analyzer = MarketSentimentAnalyzer()
    
    # 情绪分析类型选择
    sentiment_type = st.radio("分析类型", ["情绪周期", "情绪指数", "涨停板分析", "龙虎榜分析", "反包模式", "板块轮动", "连板高度"], horizontal=True, key="sentiment_type_select")
    
    if sentiment_type == "情绪周期":
        st.subheader("🔄 情绪周期分析")
        
        st.info("💡 情绪周期五阶段论:冰点期→复苏期→活跃期→高潮期→退潮期")
        
        if st.button("分析情绪周期", key="analyze_sentiment_cycle"):
            with st.spinner('正在分析情绪周期...'):
                cycle_data = sentiment_analyzer.analyze_sentiment_cycle()
                
                if cycle_data['数据状态'] == '正常':
                    # 显示情绪周期阶段
                    col_stage, col_height, col_zt = st.columns(3)
                    
                    with col_stage:
                        st.metric("当前阶段", cycle_data['情绪周期阶段'])
                    
                    with col_height:
                        st.metric("空间板高度", f"{cycle_data['空间板高度']}板")
                    
                    with col_zt:
                        st.metric("涨停数量", cycle_data['涨停数量'])
                    
                    # 显示阶段描述
                    st.subheader("📝 阶段描述")
                    st.info(cycle_data['阶段描述'])
                    
                    # 显示周期特征
                    if cycle_data.get('周期特征'):
                        st.subheader("🔍 周期特征")
                        for feature in cycle_data['周期特征']:
                            st.write(f"• {feature}")
                    
                    # 显示操作建议
                    st.subheader("💡 操作建议")
                    st.success(cycle_data['操作建议'])
                    
                    # 显示连板分布
                    if cycle_data['连板分布']:
                        st.subheader("📊 连板分布")
                        
                        board_df = pd.DataFrame(list(cycle_data['连板分布'].items()), 
                                               columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数', ascending=False)
                        st.dataframe(board_df, width="stretch")
                        
                        # 连板分布图
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='数量',
                            marker=dict(
                                color=board_df['数量'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="数量")
                            ),
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度分布",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 显示情绪指数
                    st.subheader("🎯 情绪指数")
                    col_idx, col_lvl = st.columns(2)
                    with col_idx:
                        st.metric("情绪指数", f"{cycle_data['情绪指数']:.2f}")
                    with col_lvl:
                        st.metric("情绪等级", cycle_data['情绪等级'])
                else:
                    st.error(f"❌ {cycle_data['数据状态']}")
                    if '说明' in cycle_data:
                        st.info(f"💡 {cycle_data['说明']}")
    
    elif sentiment_type == "情绪指数":
        st.subheader("🎯 市场情绪指数")
        
        st.info("💡 情绪指数说明:综合涨停数量、连板高度、打开率等指标,评估市场整体情绪")
        
        if st.button("获取情绪指数", key="get_sentiment_index"):
            with st.spinner('正在获取市场情绪数据...'):
                sentiment_data = sentiment_analyzer.get_market_sentiment_index()
                
                if sentiment_data['数据状态'] == '正常':
                    # 显示情绪指数
                    col_score, col_level, col_desc = st.columns(3)
                    
                    with col_score:
                        st.metric("情绪指数", f"{sentiment_data['情绪指数']:.2f}", delta="满分100")
                    
                    with col_level:
                        st.metric("情绪等级", sentiment_data['情绪等级'])
                    
                    with col_desc:
                        st.info(sentiment_data['情绪描述'])
                    
                    # 显示详细指标
                    st.subheader("📊 详细指标")
                    
                    col_zt, col_open, col_board = st.columns(3)
                    
                    with col_zt:
                        st.metric("涨停数量", sentiment_data['涨停数量'])
                    
                    with col_open:
                        st.metric("涨停打开数", sentiment_data['涨停打开数'])
                    
                    with col_board:
                        st.metric("涨停打开率", f"{sentiment_data['涨停打开率']}%")
                    
                    # 连板分布
                    if sentiment_data['连板分布']:
                        st.subheader("🔗 连板高度分布")
                        
                        board_df = pd.DataFrame(list(sentiment_data['连板分布'].items()), columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数')
                        
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='连板数量',
                            marker_color='orange',
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度分布",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 涨停股票列表
                    if not sentiment_data['详细数据'].empty:
                        st.subheader("📝 涨停股票列表")
                        st.dataframe(sentiment_data['详细数据'], width="stretch")
                else:
                    st.error(f"❌ {sentiment_data['数据状态']}")
                    if '说明' in sentiment_data:
                        st.info(f"💡 {sentiment_data['说明']}")
    
    elif sentiment_type == "涨停板分析":
        st.subheader("🎯 涨停板深度分析")
        
        st.info("💡 涨停板分析:识别龙头股、分析封板强度、统计板块分布")
        
        if st.button("分析涨停板", key="analyze_limit_up"):
            with st.spinner('正在分析涨停板数据...'):
                limit_data = sentiment_analyzer.analyze_limit_up_stocks()
                
                if limit_data['数据状态'] == '正常':
                    # 显示总体统计
                    col_total, col_dragon = st.columns(2)
                    
                    with col_total:
                        st.metric("涨停总数", limit_data['涨停总数'])
                    
                    with col_dragon:
                        dragon_count = len(limit_data['龙头股'])
                        st.metric("龙头股数量", dragon_count)
                    
                    # 龙头股列表
                    if limit_data['龙头股']:
                        st.subheader("🔥 龙头股列表")

                        dragon_df = pd.DataFrame(limit_data['龙头股'])

                        # 打印调试信息
                        print(f"龙头股数据列名: {dragon_df.columns.tolist()}")
                        print(f"龙头股数据示例: {dragon_df.head(1).to_dict() if not dragon_df.empty else '空'}")

                        # 检查实际列名并选择要显示的列
                        available_cols = dragon_df.columns.tolist()
                        required_cols = ['代码', '名称', '最新价', '涨跌幅', '成交额', '换手率', '龙头评分']

                        # 只选择存在的列
                        display_cols = [col for col in required_cols if col in available_cols]
                        display_df = dragon_df[display_cols].copy()

                        # 格式化成交额（如果存在）
                        if '成交额' in display_df.columns:
                            display_df['成交额'] = display_df['成交额'].apply(Formatter.format_amount)

                        # 格式化涨跌幅（如果存在）
                        if '涨跌幅' in display_df.columns:
                            display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:+.2f}%")

                        # 格式化换手率（如果存在）
                        if '换手率' in display_df.columns:
                            display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")

                        # 显示表格
                        st.dataframe(display_df, width="stretch")
                        
                        # 显示最佳龙头
                        if not dragon_df.empty:
                            best_dragon = dragon_df.iloc[0]
                            st.success(f"🏆 **最佳龙头**: {best_dragon['名称']} ({best_dragon['代码']}) - 评分: {best_dragon['龙头评分']:.1f}")
                        
                        # 添加股票选择和分析
                        st.subheader("📊 单股涨停分析")
                        selected_stock = st.selectbox(
                            "选择股票查看详细分析",
                            options=dragon_df['代码'].tolist(),
                            format_func=lambda x: f"{dragon_df[dragon_df['代码']==x]['名称'].values[0]} ({x})",
                            key="select_limit_stock"
                        )
                        
                        if selected_stock:
                            # 显示选中股票的详细信息
                            stock_info = dragon_df[dragon_df['代码'] == selected_stock].iloc[0]
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("代码", stock_info['代码'])
                            with col2:
                                st.metric("名称", stock_info['名称'])
                            with col3:
                                st.metric("最新价", f"¥{stock_info['最新价']:.2f}")
                            with col4:
                                st.metric("龙头评分", f"{stock_info['龙头评分']:.1f}")
                            
                            # 详细信息
                            st.subheader("📋 详细信息")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**涨跌幅**: {stock_info['涨跌幅']:+.2f}%")
                                st.write(f"**成交额**: {Formatter.format_amount(stock_info['成交额'])}")
                            with col_b:
                                st.write(f"**换手率**: {stock_info['换手率']:.2f}%")
                                st.write(f"**封板强度**: {'强' if stock_info['涨跌幅'] >= 9.9 else '中' if stock_info['涨跌幅'] >= 9.5 else '弱'}")
                            
                            # 单股分析按钮
                            if st.button("📊 查看技术分析", key=f"analyze_limit_{selected_stock}"):
                                st.session_state.analyze_stock = selected_stock
                                st.rerun()
                        
                        # 显示单股分析
                        if 'analyze_stock' in st.session_state:
                            show_stock_analysis_modal(st.session_state.analyze_stock)
                    
                    # 板块分布
                    if limit_data['板块分布']:
                        st.subheader("📊 板块分布")
                        
                        sector_df = pd.DataFrame(list(limit_data['板块分布'].items()), columns=['板块', '数量'])
                        sector_df = sector_df.sort_values('数量', ascending=False)
                        
                        fig_sector = go.Figure()
                        fig_sector.add_trace(go.Bar(
                            x=sector_df['板块'],
                            y=sector_df['数量'],
                            name='板块数量',
                            marker_color='blue',
                            text=sector_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_sector.update_layout(
                            title="涨停板块分布",
                            xaxis_title="板块",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_sector, width="stretch")
                    
                    # 连板统计
                    if limit_data['连板统计']:
                        st.subheader("🔗 连板统计")
                        
                        board_df = pd.DataFrame(list(limit_data['连板统计'].items()), columns=['连板数', '数量'])
                        board_df = board_df.sort_values('连板数')
                        
                        fig_board = go.Figure()
                        fig_board.add_trace(go.Bar(
                            x=board_df['连板数'].astype(str),
                            y=board_df['数量'],
                            name='连板数量',
                            marker=dict(
                                color=board_df['数量'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="数量")
                            ),
                            text=board_df['数量'],
                            textposition='outside'
                        ))
                        
                        fig_board.update_layout(
                            title="连板高度统计",
                            xaxis_title="连板数",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_board, width="stretch")
                    
                    # 详细数据
                    if not limit_data['详细数据'].empty:
                        st.subheader("📝 涨停详细数据")
                        st.dataframe(limit_data['详细数据'], width="stretch")
                else:
                    st.error(f"❌ {limit_data['数据状态']}")
                    if '说明' in limit_data:
                        st.info(f"💡 {limit_data['说明']}")
    
    elif sentiment_type == "龙虎榜分析":
        st.subheader("🏆 龙虎榜深度分析")
        
        st.info("💡 龙虎榜分析:机构vs游资动向、热门营业部追踪、质量评估")
        
        if st.button("分析龙虎榜", key="analyze_lhb"):
            with st.spinner('正在分析龙虎榜数据...'):
                lhb_data = sentiment_analyzer.deep_analyze_lhb()
                
                if lhb_data['数据状态'] == '正常':
                    # 显示总体统计
                    col_count, col_inst, col_hot = st.columns(3)
                    
                    with col_count:
                        st.metric("上榜数量", lhb_data['上榜数量'])
                    
                    with col_inst:
                        st.metric("机构净买入", Formatter.format_amount(lhb_data['机构净买入']))
                    
                    with col_hot:
                        st.metric("热门营业部净买入", Formatter.format_amount(lhb_data['热门营业部净买入']))
                    
                    st.caption(f"数据日期: {lhb_data['数据日期']}")
                    
                    # 热门营业部交易
                    if lhb_data['热门营业部交易']:
                        st.subheader("🔥 热门营业部交易")
                        
                        hot_seat_df = pd.DataFrame(lhb_data['热门营业部交易'])
                        
                        # 去重(按股票代码)
                        hot_seat_df = hot_seat_df.drop_duplicates(subset=['股票代码'], keep='first')
                        
                        # 格式化净买入
                        hot_seat_df['净买入'] = hot_seat_df['净买入'].apply(Formatter.format_amount)
                        
                        # 重命名列
                        hot_seat_df.columns = ['营业部', '股票代码', '股票名称', '净买入']
                        
                        # 显示表格
                        st.dataframe(hot_seat_df, width="stretch")
                        
                        # 添加股票选择和分析
                        st.subheader("📊 单股龙虎榜分析")
                        selected_stock = st.selectbox(
                            "选择股票查看详细分析",
                            options=hot_seat_df['股票代码'].tolist(),
                            format_func=lambda x: f"{hot_seat_df[hot_seat_df['股票代码']==x]['股票名称'].values[0]} ({x})",
                            key="select_hot_seat_stock"
                        )
                        
                        if selected_stock:
                            # 显示选中股票的详细信息
                            stock_info = hot_seat_df[hot_seat_df['股票代码'] == selected_stock].iloc[0]
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("代码", stock_info['股票代码'])
                            with col2:
                                st.metric("名称", stock_info['股票名称'])
                            with col3:
                                st.metric("净买入", stock_info['净买入'])
                            
                            # 详细信息
                            st.subheader("📋 详细信息")
                            st.write(f"**营业部**: {stock_info['营业部']}")
                            
                            # 单股分析按钮
                            if st.button("📊 查看技术分析", key=f"analyze_hot_seat_{selected_stock}"):
                                st.session_state.analyze_stock = selected_stock
                                st.rerun()
                        
                        # 显示单股分析
                        if 'analyze_stock' in st.session_state:
                            show_stock_analysis_modal(st.session_state.analyze_stock)
                    
                    # 龙虎榜质量分析
                    if '质量分析' in lhb_data and lhb_data['质量分析']['数据状态'] == '正常':
                        st.subheader("📊 龙虎榜质量分析")
                        
                        quality_stats = lhb_data['质量分析']['统计']
                        col_good, col_medium, col_poor = st.columns(3)
                        
                        with col_good:
                            st.metric("优质榜", quality_stats['优质榜数量'], delta="强烈推荐")
                        
                        with col_medium:
                            st.metric("良好榜", quality_stats['良好榜数量'], delta="推荐关注")
                        
                        with col_poor:
                            st.metric("劣质榜", quality_stats['劣质榜数量'], delta="谨慎观望")
                        
                        # 详细股票分析
                        if lhb_data['质量分析']['股票分析']:
                            st.subheader("📝 股票质量分析")
                            
                            quality_df = pd.DataFrame(lhb_data['质量分析']['股票分析'])
                            
                            # 去重(按股票代码)
                            quality_df = quality_df.drop_duplicates(subset=['代码'], keep='first')
                            
                            # 选择要显示的列
                            display_df = quality_df[['代码', '名称', '榜单质量', '上榜原因', '净买入', '评分']].copy()
                            
                            # 格式化净买入
                            display_df['净买入'] = display_df['净买入'].apply(Formatter.format_amount)
                            
                            # 重命名列
                            display_df.columns = ['代码', '名称', '榜单质量', '上榜原因', '净买入', '评分']
                            
                            # 显示表格
                            st.dataframe(display_df, width="stretch")
                            
                            # 添加股票选择和分析
                            st.subheader("📊 单股龙虎榜分析")
                            selected_stock = st.selectbox(
                                "选择股票查看详细分析",
                                options=quality_df['代码'].tolist(),
                                format_func=lambda x: f"{quality_df[quality_df['代码']==x]['名称'].values[0]} ({x})",
                                key="select_lhb_stock"
                            )
                            
                            if selected_stock:
                                # 显示选中股票的详细信息
                                stock_info = quality_df[quality_df['代码'] == selected_stock].iloc[0]
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("代码", stock_info['代码'])
                                with col2:
                                    st.metric("名称", stock_info['名称'])
                                with col3:
                                    st.metric("榜单质量", stock_info['榜单质量'])
                                with col4:
                                    st.metric("评分", f"{stock_info['评分']:.1f}")
                                
                                # 详细信息
                                st.subheader("📋 详细信息")
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.write(f"**收盘价**: ¥{stock_info['收盘价']:.2f}")
                                    st.write(f"**涨跌幅**: {stock_info['涨跌幅']:+.2f}%")
                                    st.write(f"**净买入**: {Formatter.format_amount(stock_info['净买入'])}")
                                with col_b:
                                    st.write(f"**净买入占比**: {stock_info['净买入占比']:.2f}%")
                                    st.write(f"**成交额**: {Formatter.format_amount(stock_info['成交额'])}")
                                    st.write(f"**上榜原因**: {stock_info['上榜原因']}")
                                
                                # 单股分析按钮
                                if st.button("📊 查看技术分析", key=f"analyze_lhb_{selected_stock}"):
                                    st.session_state.analyze_stock = selected_stock
                                    st.rerun()
                            
                            # 显示单股分析
                            if 'analyze_stock' in st.session_state:
                                show_stock_analysis_modal(st.session_state.analyze_stock)
                else:
                    st.error(f"❌ {lhb_data['数据状态']}")
                    if '说明' in lhb_data:
                        st.info(f"💡 {lhb_data['说明']}")
    
    elif sentiment_type == "反包模式":
        st.subheader("🔄 反包模式识别")
        
        st.info("💡 反包模式:首板炸板→次日反包→二板加速,捕捉短期反弹机会")
        
        # 股票选择
        fanbao_symbol = st.text_input("分析股票代码", value="600519", key="fanbao_symbol")
        
        if st.button("识别反包模式", key="detect_fanbao"):
            with st.spinner('正在识别反包模式...'):
                df = db.get_history_data(fanbao_symbol)
                
                if not df.empty and len(df) > 10:
                    from logic.algo_advanced import AdvancedPatternAnalyzer
                    
                    # 识别反包信号
                    signals = AdvancedPatternAnalyzer.detect_fanbao_pattern(df, fanbao_symbol)
                    
                    if signals:
                        st.success(f"✅ 发现 {len(signals)} 个反包信号")
                        
                        # 显示反包信号
                        fanbao_df = pd.DataFrame(signals)
                        st.dataframe(fanbao_df, width="stretch")
                        
                        # 对每个信号进行走势预测
                        st.subheader("🔮 走势预测")
                        
                        for i, signal in enumerate(signals):
                            with st.expander(f"反包信号 {i+1}: {signal['反包日期']}"):
                                prediction = AdvancedPatternAnalyzer.predict_fanbao_future(df, signal['反包日期'])
                                
                                col_pred, col_score = st.columns(2)
                                with col_pred:
                                    st.metric("预测", prediction['预测'])
                                with col_score:
                                    st.metric("评分", prediction['评分'])
                                
                                st.info(f"操作建议: {prediction['建议']}")
                                
                                st.write("**分析原因:**")
                                for reason in prediction['原因']:
                                    st.write(f"• {reason}")
                    else:
                        st.info("未发现反包模式信号")
                else:
                    st.error("数据不足,无法识别反包模式")
    
    elif sentiment_type == "板块轮动":
        if "sector_rotation_data" not in st.session_state:
            st.session_state.sector_rotation_data = None
            st.info("💡 板块轮动:监控板块资金流向、热度排名、追踪龙头股")
        
        if st.button("监控板块轮动", key="monitor_sector"):
            with st.spinner('正在监控板块轮动...'):
                from logic.algo_advanced import AdvancedPatternAnalyzer
                st.session_state.sector_rotation_data = AdvancedPatternAnalyzer.monitor_sector_rotation()
        
        # 从session_state获取数据
        sector_data = st.session_state.get('sector_rotation_data') or {}
        
        if sector_data.get('数据状态') == '正常':
                    # 显示最强板块
                    if sector_data.get('最强板块'):
                        strongest = sector_data['最强板块']
                        st.success(f"🔥 **最强板块**: {strongest['板块名称']} - 热度评分: {strongest['热度评分']}")
                    
                    # 显示热门板块
                    if sector_data.get('热门板块'):
                        st.subheader("🔥 热门板块")
                        
                        # 格式化主力净流入
                        formatted_hot = []
                        for s in sector_data['热门板块']:
                            formatted_s = s.copy()
                            formatted_s['主力净流入'] = Formatter.format_amount(s['主力净流入'])
                            formatted_hot.append(formatted_s)
                        
                        hot_df = pd.DataFrame(formatted_hot)
                        st.dataframe(hot_df, width="stretch")
                        
                        # 板块热度对比图
                        fig_heat = go.Figure()
                        fig_heat.add_trace(go.Bar(
                            x=hot_df['板块名称'],
                            y=hot_df['热度评分'],
                            name='热度评分',
                            marker=dict(
                                color=hot_df['热度评分'],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="热度评分")
                            ),
                            text=hot_df['热度评分'],
                            textposition='outside'
                        ))
                        
                        fig_heat.update_layout(
                            title="板块热度排名",
                            xaxis_title="板块",
                            yaxis_title="热度评分",
                            height=400
                        )
                        st.plotly_chart(fig_heat, width="stretch")
            
            # 显示冷门板块
        if  sector_data.get('冷门板块'):
                st.subheader("❄️ 冷门板块")
                
                # 格式化主力净流入
                formatted_cold = []
                for s in sector_data['冷门板块']:
                    formatted_s = s.copy()
                    formatted_s['主力净流入'] = format_amount(s['主力净流入'])
                    formatted_cold.append(formatted_s)
                
                cold_df = pd.DataFrame(formatted_cold)
                st.dataframe(cold_df, width="stretch")
        
        # 板块龙头追踪
        if sector_data.get('热门板块'):
            from logic.algo_advanced import AdvancedPatternAnalyzer
            
            st.subheader("🏆 板块龙头追踪")
            
            selected_sector = st.selectbox(
                "选择板块追踪龙头",
                [s['板块名称'] for s in sector_data.get('热门板块')],
                key="select_sector_for_leader"
            )
            
            if st.button("追踪龙头", key="track_leader"):
                with st.spinner('正在追踪龙头股...'):
                    st.session_state.leader_data = AdvancedPatternAnalyzer.track_sector_leaders(selected_sector)
        
        # 显示龙头追踪结果
        if 'leader_data' in st.session_state:
            leader_data = st.session_state.leader_data
            
            if leader_data.get('数据状态') == '正常':
                if leader_data.get('龙头股'):
                    # 格式化成交额
                    formatted_leaders = []
                    for leader in leader_data['龙头股']:
                        formatted_leader = leader.copy()
                        formatted_leader['成交额'] = Formatter.format_amount(leader['成交额'])
                        formatted_leaders.append(formatted_leader)
                    
                    leader_df = pd.DataFrame(formatted_leaders)
                    st.dataframe(leader_df, width="stretch")
                    
                    # 显示最佳龙头
                    best_leader = leader_df.iloc[0]
                    st.success(f"🏆 **最佳龙头**: {best_leader['名称']} ({best_leader['代码']}) - 评分: {best_leader['龙头评分']}")
                else:
                    st.info("该板块暂无龙头股")
            else:
                st.error(f"❌ {leader_data.get('数据状态', '未知错误')}")
                if '说明' in leader_data:
                    st.info(f"💡 {leader_data['说明']}")
    
    elif sentiment_type == "连板高度":
        st.subheader("🔗 连板高度分析")
        
        st.info("💡 连板高度:分析不同板数的胜率、连板股特征、高度预警系统")
        
        if st.button("分析连板高度", key="analyze_board_height"):
            with st.spinner('正在分析连板高度...'):
                from logic.algo_advanced import AdvancedPatternAnalyzer
                
                board_data = AdvancedPatternAnalyzer.analyze_board_height()
                
                if board_data['数据状态'] == '正常':
                    # 显示连板统计(放在最前面)
                    if not board_data['连板统计'].empty:
                        st.subheader("📊 连板高度统计")
                        
                        board_df = board_data['连板统计'].copy()
                        # 按连板数降序排序
                        board_df = board_df.sort_index(ascending=False)
                        st.dataframe(board_df, width="stretch")
                        
                        # 胜率对比图
                        fig_win_rate = go.Figure()
                        fig_win_rate.add_trace(go.Bar(
                            x=board_df.index.astype(str),
                            y=board_df['胜率'],
                            name='胜率',
                            marker_color='green',
                            text=board_df['胜率'],
                            textposition='outside'
                        ))
                        
                        fig_win_rate.update_layout(
                            title="不同板数胜率对比",
                            xaxis_title="连板数",
                            yaxis_title="胜率(%)",
                            height=400
                        )
                        st.plotly_chart(fig_win_rate, width="stretch")
                    
                    # 显示风险预警
                    if board_data['风险预警']:
                        st.subheader("⚠️ 风险预警")
                        for warning in board_data['风险预警']:
                            st.warning(warning)
                    
                    # 显示连板特征
                    if board_data['连板特征']:
                        st.subheader("🔍 连板股特征分析")
                        
                        feature_df = pd.DataFrame(board_data['连板特征'])
                        st.dataframe(feature_df, width="stretch")
                        
                        # 风险等级分布
                        risk_dist = feature_df['风险等级'].value_counts()
                        
                        fig_risk = go.Figure()
                        fig_risk.add_trace(go.Bar(
                            x=risk_dist.index,
                            y=risk_dist.values,
                            name='数量',
                            marker=dict(
                                color=['rgba(255, 99, 132, 0.8)', 'rgba(255, 159, 64, 0.8)', 'rgba(255, 205, 86, 0.8)', 'rgba(75, 192, 192, 0.8)'],
                            ),
                            text=risk_dist.values,
                            textposition='outside'
                        ))
                        
                        fig_risk.update_layout(
                            title="连板股风险等级分布",
                            xaxis_title="风险等级",
                            yaxis_title="数量",
                            height=400
                        )
                        st.plotly_chart(fig_risk, width="stretch")
                    
                    # 高板数股票
                    if not board_data['高板数股票'].empty:
                        st.subheader("🔴 高板数股票(风险较高)")
                        
                        high_risk_df = board_data['高板数股票']
                        st.dataframe(high_risk_df, width="stretch")
                else:
                    st.error(f"❌ {board_data['数据状态']}")
                    if '说明' in board_data:
                        st.info(f"💡 {board_data['说明']}")

