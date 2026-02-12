"""多智能体分析UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.multi_agent_system import MultiAgentSystem
from logic.data_manager import DataManager


def render_multi_agent_analysis_tab(db, config):
    """渲染多智能体分析标签页"""
    
    st.subheader("🤖 多智能体分析系统")
    st.caption("基于多智能体协作的智能化股票分析")
    st.markdown("---")
    
    # 说明
    st.info("""
    **多智能体分析系统**由以下智能体协作完成：
    - **数据分析师**：评估数据质量和完整性
    - **技术分析师**：分析技术指标和趋势
    - **风险评估师**：评估风险和止损建议
    - **决策协调员**：协调各智能体，生成综合建议
    """)
    
    # 输入区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        stock_code = st.text_input(
            "股票代码",
            value="600519",
            max_chars=6,
            help="请输入6位股票代码，如：600519"
        )
    
    with col2:
        days = st.slider(
            "分析天数",
            min_value=30,
            max_value=120,
            value=60,
            step=10,
            help="分析历史数据的天数"
        )
    
    # 分析按钮
    if st.button("🔍 开始分析", key="multi_agent_analyze"):
        with st.spinner('多智能体正在协作分析...'):
            try:
                # 验证股票代码
                if not stock_code or len(stock_code) != 6:
                    st.error("❌ 请输入有效的6位股票代码")
                    return
                
                # 获取股票数据
                data_manager = DataManager()
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y%m%d')
                
                df = data_manager.get_history_data(stock_code, start_date, end_date)
                
                if df is None or df.empty:
                    st.error(f"❌ 未找到股票 {stock_code} 的数据")
                    return
                
                if len(df) < 20:
                    st.warning(f"⚠️ 数据量不足（{len(df)}天），建议至少20天")
                
                # 创建多智能体系统
                mas = MultiAgentSystem()
                
                # 执行分析
                result = mas.analyze_stock(df, stock_code)
                
                if not result['success']:
                    st.error(f"❌ {result['message']}")
                    return
                
                # 显示结果
                st.success(f"✅ 分析完成！综合得分: {result['final_score']:.1f}/100")
                
                # 显示最终建议
                st.markdown("---")
                st.subheader("🎯 最终建议")
                st.markdown(f"### {result['final_recommendation']}")
                
                # 显示综合评分
                col_score1, col_score2, col_score3 = st.columns(3)
                with col_score1:
                    st.metric("综合得分", f"{result['final_score']:.1f}/100")
                with col_score2:
                    st.metric("参与智能体", f"{len(result['results']) - 1}个")
                with col_score3:
                    max_score = max(r.score for r in result['results'].values() if r.agent_name != '决策协调员')
                    st.metric("最高单项得分", f"{max_score:.1f}/100")
                
                # 显示综合报告
                st.markdown("---")
                st.subheader("📊 综合分析报告")
                st.markdown(result['report'])
                
                # 显示各智能体详细分析
                st.markdown("---")
                st.subheader("🤖 各智能体详细分析")
                
                # 创建选项卡
                tab_names = [name for name in result['results'].keys() if name != '决策协调员']
                tabs = st.tabs(tab_names)
                
                for i, agent_name in enumerate(tab_names):
                    with tabs[i]:
                        agent_result = result['results'][agent_name]
                        
                        # 显示得分和置信度
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("得分", f"{agent_result.score:.1f}/100")
                        with col_b:
                            st.metric("置信度", f"{agent_result.confidence*100:.0f}%")
                        
                        # 显示发现
                        if agent_result.findings:
                            st.write("**发现**:")
                            for finding in agent_result.findings:
                                st.write(f"- {finding}")
                        
                        # 显示建议
                        if agent_result.recommendations:
                            st.write("**建议**:")
                            for rec in agent_result.recommendations:
                                st.write(f"- {rec}")
                        
                        # 显示详细数据
                        if agent_result.data:
                            with st.expander("查看详细数据"):
                                st.json(agent_result.data)
                
                # 绘制K线图
                st.markdown("---")
                st.subheader("📈 K线图")
                fig = _plot_kline(df, result['results'])
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏 - 系统说明
    with st.sidebar:
        st.markdown("---")
        st.subheader("📖 系统说明")
        
        st.info("""
        **多智能体架构**：
        
        每个智能体专注于特定领域，通过协作提供更全面、准确的分析结果。
        
        **工作流程**：
        1. 数据分析师评估数据质量
        2. 技术分析师分析技术指标
        3. 风险评估师评估风险
        4. 决策协调员综合各智能体意见
        """)
        
        st.markdown("---")
        st.subheader("🎯 评分说明")
        
        st.info("""
        **综合得分**：
        - 70-100：建议买入
        - 50-70：建议持有
        - 30-50：建议观望
        - 0-30：建议卖出
        
        **置信度**：
        表示分析结果的可信程度，越高越可靠。
        """)


def _plot_kline(df, results):
    """绘制K线图"""
    fig = go.Figure()
    
    # 添加K线
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线'
    ))
    
    # 添加均线
    if len(df) >= 5:
        df['ma5'] = df['close'].rolling(5).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma5'], mode='lines', name='MA5', line=dict(color='orange', width=1)
        ))
    
    if len(df) >= 10:
        df['ma10'] = df['close'].rolling(10).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma10'], mode='lines', name='MA10', line=dict(color='blue', width=1)
        ))
    
    if len(df) >= 20:
        df['ma20'] = df['close'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ma20'], mode='lines', name='MA20', line=dict(color='purple', width=1)
        ))
    
    # 添加支撑阻力位
    tech_result = results.get('技术分析师')
    if tech_result and tech_result.data:
        if 'volatility' in tech_result.data:
            volatility = tech_result.data['volatility']
            if volatility > 0:
                latest_price = df['close'].iloc[-1]
                # 支撑位
                support_level = latest_price * (1 - volatility * 2)
                fig.add_hline(y=support_level, line_dash="dash", line_color="green", 
                             annotation_text=f"支撑位 {support_level:.2f}")
                # 阻力位
                resistance_level = latest_price * (1 + volatility * 2)
                fig.add_hline(y=resistance_level, line_dash="dash", line_color="red", 
                             annotation_text=f"阻力位 {resistance_level:.2f}")
    
    fig.update_layout(
        title="K线图",
        height=600,
        xaxis_title="日期",
        yaxis_title="价格",
        showlegend=True
    )
    
    return fig