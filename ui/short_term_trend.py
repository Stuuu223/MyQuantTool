"""短期涨跌分析UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.market_tactics import ShortTermTrendAnalyzer
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter


def render_short_term_trend_tab(db, config):
    """渲染短期涨跌分析标签页"""
    
    st.subheader("📈 短期涨跌分析")
    st.caption("弱势回调 + 接力竞争 - 识别短期交易机会")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 分析配置")
        
        analysis_type = st.selectbox(
            "分析类型",
            ["弱势回调", "接力竞争", "综合分析"],
            help="选择分析类型"
        )
        
        decline_threshold = st.slider(
            "深跌阈值(%)",
            1, 10, 3,
            help="上一交易日跌幅超过此值才触发弱势回调分析"
        )
        
        recovery_threshold = st.slider(
            "回春阈值(%)",
            1, 10, 2,
            help="当日涨幅超过此值才视为回春"
        )
        
        competition_ratio = st.slider(
            "竞争比例阈值",
            0.3, 0.9, 0.5,
            help="买卖金额比例超过此值才视为竞争"
        )
        
        st.markdown("---")
        st.subheader("💡 战术说明")
        st.info(f"""
        **短期涨跌战术**：
        
        1. **弱势回调**：
           - 上一日深跌 > {decline_threshold}%
           - 当日回春 > {recovery_threshold}%
           - 游资接力操作
        
        2. **接力竞争**：
           - 同一股票买卖博弈
           - 金额比例 > {competition_ratio*100:.0f}%
           - 预测胜负方
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 涨跌分析")
        
        # 获取龙虎榜数据
        if st.button("🔍 开始分析", key="analyze_short_term"):
            with st.spinner('正在分析短期涨跌...'):
                try:
                    # 获取龙虎榜数据
                    capital_result = CapitalAnalyzer.analyze_longhubu_capital()
                    
                    if capital_result['数据状态'] != '正常':
                        st.error(f"❌ 获取龙虎榜数据失败: {capital_result.get('说明', '未知错误')}")
                        return
                    
                    # 转换为DataFrame
                    if capital_result.get('游资操作记录'):
                        df_lhb = pd.DataFrame(capital_result['游资操作记录'])
                    else:
                        st.warning("⚠️ 暂无游资操作记录")
                        return
                    
                    # 添加必要的列
                    if '日期' not in df_lhb.columns:
                        df_lhb['日期'] = df_lhb['上榜日']
                    
                    if '操作方向' not in df_lhb.columns:
                        df_lhb['操作方向'] = df_lhb['净买入'].apply(
                            lambda x: '买' if x > 0 else '卖'
                        )
                    
                    # 创建分析器
                    analyzer = ShortTermTrendAnalyzer()
                    
                    if analysis_type in ["弱势回调", "综合分析"]:
                        st.divider()
                        st.subheader("🔄 弱势回调分析")
                        
                        # 分析弱势回调
                        recovery_signals = []
                        
                        # 按股票分组分析
                        for stock_code in df_lhb['股票代码'].unique():
                            stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
                            
                            # 从数据源获取价格信息进行真正的弱势回调分析
                            # 这里需要获取前一日收盘价、今日开盘价和当前价格
                            try:
                                # 获取股票价格数据
                                from logic.data_source_manager import DataSourceManager
                                from datetime import datetime, timedelta
                                
                                # 使用传入的db参数来创建DataSourceManager
                                data_manager = DataSourceManager(db)
                                
                                # 计算日期范围 - 获取最近5天的数据
                                end_date = datetime.now().strftime('%Y-%m-%d')
                                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                                
                                recent_data = data_manager.get_stock_data(
                                    stock_code, 
                                    start_date,
                                    end_date
                                )
                                
                                if recent_data is not None and len(recent_data) >= 2:
                                    # 获取前一日收盘价和当日数据
                                    prev_day_data = recent_data.iloc[-2]  # 前一日
                                    current_day_data = recent_data.iloc[-1]  # 当日
                                    
                                    price_prev_close = prev_day_data['close']
                                    price_open = current_day_data['open']
                                    price_current = current_day_data['close']
                                    
                                    # 使用正确的分析器进行弱势回调分析
                                    analyzer = ShortTermTrendAnalyzer()
                                    result = analyzer.analyze_overnight_recovery(
                                        df_lhb, stock_code, price_prev_close, price_open, price_current
                                    )
                                    
                                    if result is not None:
                                        # 检查跌幅和回涨幅度是否符合阈值
                                        if (abs(result['prev_decline_pct']) > decline_threshold / 100 and 
                                            result['today_recovery_pct'] > recovery_threshold / 100):
                                            
                                            recovery_signals.append({
                                                '股票代码': stock_code,
                                                '股票名称': stock_data.iloc[0]['股票名称'],
                                                '上一日跌幅': f"{result['prev_decline_pct'] * 100:.2f}%",
                                                '当日涨幅': f"{result['today_recovery_pct'] * 100:.2f}%",
                                                '救援游资': ', '.join(result['rescue_capitals']),
                                                '信号': result['signal'],
                                                '置信度': result['confidence']
                                            })
                            except Exception as e:
                                # 如果获取价格数据失败，跳过该股票
                                st.warning(f"获取股票 {stock_code} 价格数据失败: {e}")
                                continue
                        
                        if recovery_signals:
                            st.success(f"✅ 发现 {len(recovery_signals)} 个弱势回调信号")
                            
                            # 显示信号列表
                            recovery_df = pd.DataFrame(recovery_signals)
                            st.dataframe(
                                recovery_df,
                                column_config={
                                    '置信度': st.column_config.NumberColumn('置信度', format="%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # 详细分析
                            if len(recovery_signals) > 0:
                                st.divider()
                                st.write("### 📊 详细分析")
                                
                                for i, signal in enumerate(recovery_signals[:5], 1):
                                    with st.expander(f"#{i} {signal['股票名称']} ({signal['股票代码']})"):
                                        col_a, col_b, col_c = st.columns(3)
                                        with col_a:
                                            st.metric("上一日跌幅", signal['上一日跌幅'])
                                        with col_b:
                                            st.metric("当日涨幅", signal['当日涨幅'])
                                        with col_c:
                                            st.metric("置信度", f"{signal['置信度']:.2f}")
                                        
                                        st.write(f"**救援游资**: {signal['救援游资']}")
                                        st.write(f"**信号**: {signal['信号']}")
                        else:
                            st.info("👍 未发现弱势回调信号")
                    
                    if analysis_type in ["接力竞争", "综合分析"]:
                        st.divider()
                        st.subheader("⚔️ 接力竞争分析")
                        
                        # 分析接力竞争
                        competition_signals = []
                        
                        # 按股票分组分析
                        for stock_code in df_lhb['股票代码'].unique():
                            stock_data = df_lhb[df_lhb['股票代码'] == stock_code]
                            
                            # 使用正确的分析器进行接力竞争分析
                            analyzer = ShortTermTrendAnalyzer()
                            result = analyzer.analyze_power_competition(df_lhb, stock_code)
                            
                            if result is not None and result['amount_ratio'] >= competition_ratio:
                                competition_signals.append({
                                    '股票代码': stock_code,
                                    '股票名称': stock_data.iloc[0]['股票名称'],
                                    '买入方': result['top_buyer'],
                                    '买入金额': Formatter.format_amount(result['buyer_amount']),
                                    '卖出方': result['top_seller'],
                                    '卖出金额': Formatter.format_amount(result['seller_amount']),
                                    '金额比例': f"{result['amount_ratio']:.2%}",
                                    '预测胜者': result['predicted_winner'],
                                    '信号类型': result['signal'],
                                    '置信度': result['confidence']
                                })
                        
                        if competition_signals:
                            st.success(f"✅ 发现 {len(competition_signals)} 个接力竞争信号")
                            
                            # 显示信号列表
                            competition_df = pd.DataFrame(competition_signals)
                            st.dataframe(
                                competition_df,
                                column_config={
                                    '金额比例': st.column_config.NumberColumn('金额比例', format="%.2%"),
                                    '置信度': st.column_config.NumberColumn('置信度', format="%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # 详细分析
                            if len(competition_signals) > 0:
                                st.divider()
                                st.write("### 📊 详细分析")
                                
                                for i, signal in enumerate(competition_signals[:5], 1):
                                    with st.expander(f"#{i} {signal['股票名称']} ({signal['股票代码']})"):
                                        col_a, col_b, col_c = st.columns(3)
                                        with col_a:
                                            st.metric("买入方", signal['买入方'])
                                            st.write(f"买入金额: {signal['买入金额']}")
                                        with col_b:
                                            st.metric("卖出方", signal['卖出方'])
                                            st.write(f"卖出金额: {signal['卖出金额']}")
                                        with col_c:
                                            st.metric("金额比例", signal['金额比例'])
                                            st.metric("置信度", f"{signal['置信度']:.2f}")
                                        
                                        st.write(f"**预测胜者**: {signal['预测胜者']}")
                                        st.write(f"**信号类型**: {signal['信号类型']}")
                        else:
                            st.info("👍 未发现接力竞争信号")
                    
                    # 综合统计
                    if analysis_type == "综合分析":
                        st.divider()
                        st.subheader("📈 综合统计")
                        
                        total_signals = len(recovery_signals) + len(competition_signals)
                        
                        col_x, col_y, col_z = st.columns(3)
                        with col_x:
                            st.metric("弱势回调信号", len(recovery_signals))
                        with col_y:
                            st.metric("接力竞争信号", len(competition_signals))
                        with col_z:
                            st.metric("总信号数", total_signals)
                        
                        # 信号分布图
                        if total_signals > 0:
                            fig = go.Figure(data=[
                                go.Bar(
                                    name='弱势回调',
                                    x=['弱势回调', '接力竞争'],
                                    y=[len(recovery_signals), 0],
                                    marker_color='#4CAF50'
                                ),
                                go.Bar(
                                    name='接力竞争',
                                    x=['弱势回调', '接力竞争'],
                                    y=[0, len(competition_signals)],
                                    marker_color='#FF6B6B'
                                )
                            ])
                            
                            fig.update_layout(
                                title='信号类型分布',
                                barmode='stack',
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    with col2:
        st.subheader("💡 战术解读")
        
        st.info("""
        **弱势回调**：
        
        - 深跌后快速回春
        
        - 游资接力操作
        
        - 短期反弹机会
        
        - 适合快进快出
        """)
        
        st.markdown("---")
        st.subheader("⚔️ 竞争分析")
        
        st.info("""
        **接力竞争**：
        
        - 买卖双方博弈
        
        - 金额接近更激烈
        
        - 预测胜负方
        
        - 关注胜者操作
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 风险提示")
        
        st.warning("""
        1. 短期波动大
        
        2. 需要快速决策
        
        3. 严格止损
        
        4. 控制仓位
        
        5. 仅供参考
        """)