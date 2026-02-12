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
    
    # 主内容区 - 配置面板
    with st.expander("⚙️ 分析配置", expanded=True):
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
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
        
        with col_config2:
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
    
    # 主内容区 - 分析结果
    st.subheader("📊 分析结果")
    
    # 执行分析
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
                
                # 创建分析器
                analyzer = ShortTermTrendAnalyzer()
                
                # 根据分析类型执行不同的分析
                if analysis_type == "弱势回调":
                    # 弱势回调分析
                    weak_recovery = analyzer.analyze_weak_recovery(
                        df_lhb,
                        decline_threshold=decline_threshold / 100,
                        recovery_threshold=recovery_threshold / 100
                    )
                    
                    if weak_recovery:
                        st.success(f"✅ 发现 {len(weak_recovery)} 个弱势回调机会")
                        
                        # 显示结果表格
                        recovery_df = pd.DataFrame(weak_recovery)
                        st.dataframe(
                            recovery_df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("👍 未发现弱势回调机会")
                
                elif analysis_type == "接力竞争":
                    # 接力竞争分析
                    competitive = analyzer.analyze_competitive_battle(
                        df_lhb,
                        competition_ratio=competition_ratio
                    )
                    
                    if competitive:
                        st.success(f"✅ 发现 {len(competitive)} 个接力竞争机会")
                        
                        # 显示结果表格
                        competitive_df = pd.DataFrame(competitive)
                        st.dataframe(
                            competitive_df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("👍 未发现接力竞争机会")
                
                elif analysis_type == "综合分析":
                    # 综合分析
                    weak_recovery = analyzer.analyze_weak_recovery(
                        df_lhb,
                        decline_threshold=decline_threshold / 100,
                        recovery_threshold=recovery_threshold / 100
                    )
                    
                    competitive = analyzer.analyze_competitive_battle(
                        df_lhb,
                        competition_ratio=competition_ratio
                    )
                    
                    # 显示结果
                    if weak_recovery:
                        st.success(f"✅ 弱势回调: {len(weak_recovery)} 个机会")
                        recovery_df = pd.DataFrame(weak_recovery)
                        st.dataframe(recovery_df, use_container_width=True, hide_index=True)
                    
                    if competitive:
                        st.success(f"✅ 接力竞争: {len(competitive)} 个机会")
                        competitive_df = pd.DataFrame(competitive)
                        st.dataframe(competitive_df, use_container_width=True, hide_index=True)
                    
                    if not weak_recovery and not competitive:
                        st.info("👍 未发现明显机会")
                
            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    
    # 侧边栏内容
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