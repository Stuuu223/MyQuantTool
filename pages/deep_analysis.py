"""
MyQuantTool 第3阶段 - 深度分析前端页面
集成游资画像 + 龙虎榜预测 + 风险监控三个核心模块
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from logic.capital_profiler import CapitalProfiler
    from logic.opportunity_predictor import OpportunityPredictor
    from logic.risk_monitor import RiskMonitor
    MODULES_LOADED = True
except ImportError as e:
    st.error(f"模块加载失败: {e}")
    MODULES_LOADED = False

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    st.warning("没有安装 akshare，不能下载真实数据。但会使用示例数据演示。")


def load_sample_data():
    """生成示例数据用于演示"""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=100)
    capitals = ['章盟主', '万洲股份', '上海齐粗', '晨兴洲会', '中根汿上']
    stocks = [
        ('000001', '平安银行', '金融'),
        ('000002', '万科A', '房地产'),
        ('000333', '美的集团', '家电'),
        ('300059', '东方财富', '计算机'),
        ('601888', '中国国旅', '旅游'),
    ]
    
    data = []
    for _ in range(100):
        date = np.random.choice(dates)
        capital = np.random.choice(capitals)
        stock_code, stock_name, industry = np.random.choice(len(stocks))
        stock_code, stock_name, industry = stocks[stock_code]
        amount = np.random.randint(1000, 10000)
        direction = np.random.choice(['买入', '卖出'])
        
        data.append({
            '日期': date,
            '游资名称': capital,
            '股票代码': stock_code,
            '股票名称': stock_name,
            '成交额': amount,
            '操作方向': direction,
            '行业': industry
        })
    
    return pd.DataFrame(data)


def init_session_state():
    """初始化 session state"""
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = '游资画像'
    if 'sample_data' not in st.session_state:
        st.session_state.sample_data = load_sample_data()


def render_capital_profiler():
    """游资画像分析页面"""
    st.header("🎯 游资画像分析")
    st.markdown("""
    基于5维度评分模型，顱国情地识别游资操作风格、资金实力、成功能力。
    """)
    
    # 新建 两标 提民上
    col1, col2 = st.columns(2)
    
    with col1:
        capital_name = st.selectbox(
            "选择游资",
            st.session_state.sample_data['游资名称'].unique(),
            key='capital_select'
        )
    
    with col2:
        data_source = st.radio(
            "数据来源",
            ["示例数据", "真实数据 (akshare)"],
            horizontal=True
        )
    
    if st.button("🔠 开始分析", key='profile_btn', use_container_width=True):
        try:
            # 获取数据
            if data_source == "示例数据":
                df_lhb = st.session_state.sample_data
                st.info("ℹ️ 使用示例数据演示 (真实数据需要安装 akshare)")
            else:
                if not AKSHARE_AVAILABLE:
                    st.error("❣️ akshare 未安装，请运行: pip install akshare")
                    return
                
                with st.spinner("正在从真实数据院拓..."):
                    today = datetime.now().strftime('%Y%m%d')
                    df_lhb = ak.stock_lhb_daily_em(date=today)
                    st.success("✅ 数据拓取成功")
            
            # 计算游资画像
            profiler = CapitalProfiler()
            profile = profiler.calculate_profile(capital_name, df_lhb)
            
            # 国外的展示区域一
            st.success(f"✅ 成功加载游资: {capital_name}")
            
            # 综合评分卡片
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "🌟 综合评分",
                    f"{profile.overall_score:.0f}/100",
                    f"等级: {profile.capital_grade}"
                )
            with col2:
                st.metric(
                    "📈 成功率",
                    f"{profile.success_rate:.1f}%",
                    f"类型: {profile.capital_type}"
                )
            with col3:
                st.metric(
                    "📄 总操作数",
                    f"{profile.operation_stats['总操作数']}",
                    f"买/卖: {profile.operation_stats['买入次数']}/{profile.operation_stats['卖出次数']}"
                )
            
            st.divider()
            
            # 5维度评分雷达图
            st.subheader("5维度评分雷达图")
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[
                    profile.focus_continuity_score,
                    profile.capital_strength_score,
                    profile.success_rate,
                    min(profile.sector_concentration * 100, 100),
                    profile.timing_ability_score
                ],
                theta=[
                    '连续关注指数',
                    '资金实力评分',
                    '操作成功率',
                    '行业浓度',
                    '选时能力评分'
                ],
                fill='toself',
                name=capital_name,
                line_color='#667eea'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        tickfont=dict(size=10)
                    )
                ),
                height=500,
                font=dict(size=12, color='#333'),
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # 偏好板块 vs 常操作股票
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 偏好行业 TOP 5")
                for i, sector in enumerate(profile.top_sectors, 1):
                    st.write(f"{i}. **{sector['行业']}**: {sector['频率']:.1%}")
            
            with col2:
                st.subheader("💰 常操作股票 TOP 10")
                for i, stock in enumerate(profile.top_stocks[:5], 1):
                    st.write(f"{i}. {stock['名称']} ({stock['代码']}): {stock['频率']:.1%}")
            
            st.divider()
            
            # 最近30天表现
            st.subheader("📅 最近30天表现")
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            with perf_col1:
                st.metric(
                    "🙋 盈利天数",
                    profile.recent_performance['盈利天数']
                )
            with perf_col2:
                st.metric(
                    "😢 亏损天数",
                    profile.recent_performance['亏损天数']
                )
            with perf_col3:
                st.metric(
                    "😐 平手天数",
                    profile.recent_performance['平手天数']
                )
            
            # 风险提示
            if profile.risk_warnings and profile.risk_warnings[0] != "暂无风险提示":
                st.warning(f"⚠️ **风险提示**: {profile.risk_warnings[0]}")
            else:
                st.success("✅ 暂无风险提示")
        
        except ValueError as e:
            st.error(f"❌ 敲邻: {str(e)}")
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")


def render_opportunity_predictor():
    """龙虎榜预测页面"""
    st.header("🔮 明日龙虎榜预测")
    st.markdown("""
    基于三層特征融合 (历史规律40% + 技术面35% + 情緒指数25%)，
    预测明天龙虎榜的高概率游资和股票。
    """)
    
    data_source = st.radio(
        "数据来源",
        ["示例数据", "真实数据 (akshare)"],
        horizontal=True
    )
    
    if st.button("🔮 开始预测", key='predict_btn', use_container_width=True):
        try:
            # 获取数据
            if data_source == "示例数据":
                df_history = st.session_state.sample_data
                st.info("ℹ️ 使用示例数据演示")
            else:
                if not AKSHARE_AVAILABLE:
                    st.error("❣️ akshare 未安装")
                    return
                
                with st.spinner("正在拓取数据..."):
                    today = datetime.now().strftime('%Y%m%d')
                    df_history = ak.stock_lhb_daily_em(date=today)
                    st.success("✅ 数据拓取成功")
            
            # 预测
            predictor = OpportunityPredictor()
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            prediction = predictor.predict_tomorrow(
                tomorrow_date=tomorrow,
                df_lhb_history=df_history
            )
            
            st.success(f"✅ 预测完成 ({tomorrow})")
            
            # 整体活跃度
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "🌟 整体活跃度",
                    f"{prediction.overall_activity}/100",
                    delta=None
                )
            with col2:
                st.metric(
                    "📐 预测可信度",
                    f"{prediction.prediction_confidence:.0%}"
                )
            with col3:
                sentiment_emoji = {'豪笕': '🙋', '中符': '😐', '俊煦': '😢'}
                st.metric(
                    "📈 市场情緒",
                    prediction.market_sentiment,
                    delta=sentiment_emoji.get(prediction.market_sentiment, '')
                )
            
            st.divider()
            
            # 高概率游资
            st.subheader("🎯 高概率游资 (TOP 5)")
            
            if prediction.predicted_capitals:
                for capital in prediction.predicted_capitals[:5]:
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(f"**{capital.capital_name}**")
                        with col2:
                            st.write(f"📈 {capital.appearance_probability:.0%}")
                        with col3:
                            risk_emoji = {'低': '🟢', '中': '🟡', '高': '🔴'}
                            st.write(f"{risk_emoji.get(capital.risk_level, '⚪')} {capital.risk_level}")
                        with col4:
                            st.write(f"💵 {capital.expected_amount:,.0f}")
                        
                        st.caption(f"📄 理由: {', '.join(capital.predict_reasons[:2])}")
            else:
                st.info("⚠️ 没有预测游资")
            
            st.divider()
            
            # 高概率股票
            st.subheader("💰 高概率股票 (TOP 10)")
            
            if prediction.predicted_stocks:
                stocks_df = pd.DataFrame([
                    {
                        '股票': f"{s.name} ({s.code})",
                        '出现概率': f"{s.appearance_probability:.1%}",
                        '可能游资': ', '.join(s.likely_capitals[:2]) or '未知',
                        '预测理由': s.predicted_reason[:30] + '...'
                    }
                    for s in prediction.predicted_stocks[:10]
                ])
                st.dataframe(stocks_df, use_container_width=True, hide_index=True)
            else:
                st.info("⚠️ 没有预测股票")
            
            st.divider()
            
            # 核心洛见
            st.subheader("💡 核心洛见")
            for insight in prediction.key_insights:
                st.info(insight)
        
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")


def render_risk_monitor():
    """风险监控页面"""
    st.header("⚠️ 风险监控讯号板")
    st.markdown("""
    实时监控游资三类风险: 风格突变、对抭失利、流动性风险。
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        capital_name = st.selectbox(
            "选择游资",
            st.session_state.sample_data['游资名称'].unique(),
            key='risk_capital_select'
        )
    
    with col2:
        data_source = st.radio(
            "数据来源",
            ["示例数据", "真实数据 (akshare)"],
            horizontal=True,
            key='risk_data_source'
        )
    
    if st.button("🔍 缀索索风险", key='risk_btn', use_container_width=True):
        try:
            # 获取数据
            if data_source == "示例数据":
                df_all = st.session_state.sample_data
                st.info("ℹ️ 使用示例数据演示")
            else:
                if not AKSHARE_AVAILABLE:
                    st.error("❣️ akshare 未安装")
                    return
                
                with st.spinner("正在拓取数据..."):
                    today = datetime.now().strftime('%Y%m%d')
                    df_all = ak.stock_lhb_daily_em(date=today)
                    st.success("✅ 数据拓取成功")
            
            # 数据筛选
            df_current = df_all[df_all['游资名称'] == capital_name]
            
            if len(df_current) == 0:
                st.warning(f"⚠️ 没有找到 {capital_name} 的操作记录")
                return
            
            # 生成风险报告
            monitor = RiskMonitor()
            report = monitor.generate_risk_report(
                capital_name=capital_name,
                df_current_ops=df_current,
                df_history_ops=df_all
            )
            
            st.success(f"✅ 报告生成成功")
            
            # 风险仪表板
            st.subheader("📈 风险指数")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "😐 风格突变",
                    f"{report.style_drift_score:.0f}/100"
                )
            with col2:
                st.metric(
                    "⚡ 对抭失利",
                    f"{report.confrontation_risk_score:.0f}/100"
                )
            with col3:
                st.metric(
                    "🌪️ 流动性风险",
                    f"{report.liquidity_risk_score:.0f}/100"
                )
            with col4:
                st.metric(
                    "🚨 综合风险",
                    f"{report.overall_risk_score:.0f}/100",
                    delta=report.overall_risk_level
                )
            
            st.divider()
            
            # 风险等级与报告
            risk_level_colors = {
                '低风险': '🟢',
                '中等风险': '🟡',
                '高风险': '🔴',
                '严重风险': '🔴🔴'
            }
            
            st.subheader("🚨 风险等级")
            risk_col = st.container(border=True)
            with risk_col:
                st.write(f"{risk_level_colors.get(report.overall_risk_level, '⚪')} "
                        f"**{report.overall_risk_level}**")
            
            st.divider()
            
            # 风险清单
            st.subheader("📋 风险清单")
            
            if report.risk_alerts:
                for i, alert in enumerate(report.risk_alerts, 1):
                    with st.expander(
                        f"{risk_level_colors.get(alert.risk_level, '⚪')} "
                        f"{i}. {alert.risk_type} - **{alert.risk_level}**"
                    ):
                        st.write(f"**描述**: {alert.description}")
                        st.info(f"**建议**: {alert.recommendation}")
                        if alert.trigger_conditions:
                            st.caption(f"**触发条件**: {', '.join(alert.trigger_conditions)}")
            else:
                st.info("⚠️ 暂无风险清单")
            
            st.divider()
            
            # 投资建议
            st.subheader("💡 投资建议")
            st.info(report.investment_advice)
        
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")


def render_settings():
    """设置页面"""
    st.header("⚙️ 设置")
    
    st.subheader("📄 关于本程序")
    st.write("""
    **MyQuantTool 第3阶段 - 深度分析模块**
    
    这个页面整合了三个核心分析模块:
    
    1. **游资画像分析**: 5维度评分模型, 全面识别游资操作风格
    2. **龙虎榜预测**: 三層特征融合, 预测明天龙虎榜活跃情况
    3. **风险监控**: 系统化的风险评估和预警機制
    
    ---
    
    📄 **技术信息**
    """) 
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("📄 模块位置\n\n`logic/capital_profiler.py` (408行)\n\n`logic/opportunity_predictor.py` (456行)\n\n`logic/risk_monitor.py` (503行)")
    
    with col2:
        st.info("📄 前端位置\n\n`pages/deep_analysis.py`\n\n🐸 GitHub Branch:\n\n`feature/phase-3-deep-analysis`")
    
    st.divider()
    
    st.subheader("📈 数据管理")
    
    if st.button("🔄 刷新示例数据", use_container_width=True):
        st.session_state.sample_data = load_sample_data()
        st.success("✅ 示例数据已刷新")
    
    if st.button("🗑️ 清空会话", use_container_width=True):
        st.session_state.clear()
        st.success("✅ 会话已清空")


def main():
    """主程序入口"""
    # 页面鲍最后配置
    st.set_page_config(
        page_title="📈 MyQuantTool - 深度分析",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 页面样式
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tabs"] button {
        font-size: 16px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 初始化
    init_session_state()
    
    # 页面声明
    st.title("📈 MyQuantTool 第3阶段 - 深度分析平式")
    
    st.markdown("""
    **桔景描述**: 我们為 MyQuantTool 引入了 AI 马马师的模式。根据游资的历史操作记录,
    不仅能理解游资的操作风格、丈量实力、成功率,
    还能控预明天龙虎榜上突您会出霸的游资、股票,
    且可帮您控预游资的风险。
    """)
    
    st.divider()
    
    # 常首、tab位置
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 游资画像",
        "🔮 龙虎榜预测",
        "⚠️ 风险监控",
        "⚙️ 设置"
    ])
    
    with tab1:
        render_capital_profiler()
    
    with tab2:
        render_opportunity_predictor()
    
    with tab3:
        render_risk_monitor()
    
    with tab4:
        render_settings()
    
    # 页脚信息
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("💾 版本: 3.0.0")
    with col2:
        st.caption("📄 作者: MyQuantTool Team")
    with col3:
        st.caption("🔗 [GitHub](https://github.com/Stuuu223/MyQuantTool)")


if __name__ == "__main__":
    main()
