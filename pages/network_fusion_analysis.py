"""
游资网络 + 多因子融合分析页面
属性：
- Tab1: 游资网络可載化
- Tab2: 网络中心度指标
- Tab3: 对斗景谱分析
- Tab4: 多因子融合信号
- Tab5: 母帀教客 (accuracy评估)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import logging

try:
    import networkx as nx
except ImportError:
    st.error("不支持NetworkX. 运行: pip install networkx")

try:
    from logic.capital_network import CapitalNetworkBuilder
except ImportError:
    st.error("没有capital_network模块")

try:
    from logic.multifactor_fusion import MultifactorFusionEngine, SignalType
except ImportError:
    st.error("没有multifactor_fusion模块")

logger = logging.getLogger(__name__)


def page_network_fusion():
    st.set_page_config(page_title="游资网络+融合", layout="wide")
    
    st.markdown("""
    # 🔗 游资网络 + 多因子融合分析
    
    正在网络中扫描游资丫赴汽、对斗需来、以及多因子综合信号...
    """)
    
    # 侧边栏
    st.sidebar.subheader("🔢 参数配置")
    
    # 日期输入
    analysis_date = st.sidebar.date_input(
        "分析日期",
        value=datetime.now().date(),
        max_value=datetime.now().date()
    )
    
    # 回须窗口
    lookback_days = st.sidebar.slider(
        "回须窗口 (天)",
        min_value=5,
        max_value=60,
        value=30,
        step=5
    )
    
    # 游资群组数
    num_clusters = st.sidebar.slider(
        "游资群组数",
        min_value=2,
        max_value=10,
        value=3,
        step=1
    )
    
    # 因子权重
    st.sidebar.subheader("⚖️ 多因子权重")
    lstm_weight = st.sidebar.slider(
        "LSTM时间序列",
        min_value=0.1,
        max_value=1.0,
        value=0.33,
        step=0.05
    )
    
    kline_weight = st.sidebar.slider(
        "K线技术",
        min_value=0.1,
        max_value=1.0,
        value=0.33,
        step=0.05
    )
    
    network_weight = st.sidebar.slider(
        "游资网络",
        min_value=0.1,
        max_value=1.0,
        value=0.34,
        step=0.05
    )
    
    # Tab 篇章
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔗 网络可載化",
        "🤏 中心度指标",
        "⚡ 对斗景谱",
        "📊 融合信号",
        "🏱 母帀教客"
    ])
    
    # ==================== Tab1: 网络可載化 ====================
    with tab1:
        st.subheader("游资-股票二部图可載")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 模拟日常数据 (Demo)
            df_lhb_demo = pd.DataFrame({
                '游资名称': ['A游资', 'B游资', 'C游资', 'A游资', 'B游资'],
                '股票代码': ['000001', '000001', '000002', '000002', '000002'],
                '成交额': [10000000, 5000000, 8000000, 7000000, 6000000],
                '操作方向': ['买', '卖', '买', '卖', '买']
            })
            
            # 构建网络
            try:
                builder = CapitalNetworkBuilder(lookback_days=lookback_days)
                G = builder.build_graph_from_lhb(df_lhb_demo, include_competitive=True)
                
                st.success(f✅ 施荐网络成功! 苦酶: {G.number_of_nodes()}, 需来: {G.number_of_edges()}")
                
                # 突来经状批评
                summary = builder.get_network_summary()
                
                col1a, col1b, col1c = st.columns(3)
                with col1a:
                    st.metric("正式游资", summary['total_capitals'])
                with col1b:
                    st.metric("施荐股票", summary['total_stocks'])
                with col1c:
                    st.metric("常流网络", summary['total_edges'])
                
                # 网络简敦指标
                st.metric("市场施荐突深度", f"{summary['network_density']:.1%}")
                
            except Exception as e:
                st.error(f"Network construction failed: {str(e)}")
        
        with col2:
            # 游资群组结果
            st.write("‏游资群组结果♯")
            
            try:
                clusters = builder.get_capital_clusters(k=num_clusters)
                
                for cluster_id, capitals in clusters.items():
                    st.info(f"🔗 笪组 {cluster_id + 1}: {', '.join(capitals)}")
                
            except Exception as e:
                st.warning(f"Clustering encountered issues: {str(e)}")
    
    # ==================== Tab2: 中心度指标 ====================
    with tab2:
        st.subheader(不苦酶中心度指标")
        
        try:
            # 计算节点指标
            node_metrics = builder.calculate_node_metrics()
            
            # Hub游资提取
            hub_capitals = [
                cap for cap, metric in node_metrics.items()
                if metric.is_hub and metric.node_type == 'capital'
            ]
            
            st.success(f👑 检测了 {len(hub_capitals)} 个Hub游资")
            
            # 按中心度排序的游资
            capital_data = []
            for cap, metric in node_metrics.items():
                if metric.node_type == 'capital':
                    capital_data.append({
                        '游资': cap,
                        'Degree': metric.degree,
                        'Weighted Degree': metric.weighted_degree,
                        'Betweenness': metric.betweenness_centrality,
                        'Closeness': metric.closeness_centrality,
                        'Clustering': metric.clustering_coefficient,
                        'Is Hub': metric.is_hub,
                        'Strength': metric.strength
                    })
            
            if capital_data:
                df_metrics = pd.DataFrame(capital_data)
                df_metrics = df_metrics.sort_values('Betweenness', ascending=False)
                
                st.dataframe(df_metrics, use_container_width=True)
                
                # 托线图: 中心度 vs 会对斗
                fig = px.scatter(
                    df_metrics,
                    x='Betweenness',
                    y='Weighted Degree',
                    size='Clustering',
                    color='Is Hub',
                    hover_data=['游资'],
                    title='游资中心度分析'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无游资指标")
        
        except Exception as e:
            st.error(f"Metrics calculation error: {str(e)}")
    
    # ==================== Tab3: 对斗景谱 ====================
    with tab3:
        st.subheader("游资对斗景谱")
        
        try:
            # 分析对斗景谱
            competitive = builder.analyze_competitive_landscape(df_lhb_demo)
            
            for capital, analysis in competitive.items():
                with st.expander(f💫 {capital}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("裔斗集数", analysis['battle_count'])
                    
                    with col2:
                        st.metric(ت斗胜率", f"{analysis['battle_success_rate']:.1%}")
                    
                    with col3:
                        st.metric("主要对手", len(analysis['main_opponents']))
                    
                    # 主要对手游资
                    st.write("💪 主要对手:")
                    for opponent, count in analysis['main_opponents']:
                        st.write(f"  - {opponent}: {count} 次裔斗")
                    
                    # 控汁股票
                    st.write("💫 控汁股票: " + ', '.join(analysis['dominated_stocks'][:5]))
        
        except Exception as e:
            st.error(f"Competitive analysis error: {str(e)}")
    
    # ==================== Tab4: 融合信号 ====================
    with tab4:
        st.subheader(多因子融合信号分析")
        
        try:
            # 初学化融合引擎
            engine = MultifactorFusionEngine(
                lstm_weight=lstm_weight,
                kline_weight=kline_weight,
                network_weight=network_weight
            )
            
            # Demo: 单股票的多因子信号
            st.write("📊 Demo: 台游资对哦股票的融合信号")
            
            # 游资选择
            selected_capital = st.selectbox(
                "选择游资",
                ['A游资', 'B游资', 'C游资']
            )
            
            # 三个案再案
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader(🤬 LSTM因子")
                lstm_prob = st.slider("LSTM预测概率", 0.0, 1.0, 0.65)
                lstm_factor = engine.calculate_lstm_factor(
                    lstm_probability=lstm_prob,
                    historical_accuracy=0.68
                )
                st.info(
                    f"技术: {lstm_factor.signal.name}\n"
                    f估段轻: {lstm_factor.raw_score:.1%}\n"
                    f信信度: {lstm_factor.confidence:.1%}"
                )
            
            with col2:
                st.subheader(📊 K线技术")
                rsi = st.slider("RSI", 0, 100, 65)
                kdj = st.slider("KDJ", 0, 100, 55)
                kline_factor = engine.calculate_kline_factor(
                    ma_signal=SignalType.BULLISH,
                    macd_signal=SignalType.BULLISH,
                    rsi_value=rsi,
                    kdj_value=kdj,
                    volatility=0.025
                )
                st.info(
                    f"技术: {kline_factor.signal.name}\n"
                    f估段轻: {kline_factor.raw_score:.1%}\n"
                    f信信度: {kline_factor.confidence:.1%}"
                )
            
            with col3:
                st.subheader(🔗 网络因子")
                strength = st.slider("需来挺上", 0.0, 1.0, 0.72)
                hub = st.slider("Hub游资", 0.0, 1.0, 0.85)
                network_factor = engine.calculate_network_factor(
                    capital_strength=strength,
                    hub_score=hub,
                    competitive_advantage=0.68,
                    co_action_count=3
                )
                st.info(
                    f"技术: {network_factor.signal.name}\n"
                    f估段轻: {network_factor.raw_score:.1%}\n"
                    f信信度: {network_factor.confidence:.1%}"
                )
            
            # 融合信号
            st.markdown("---")
            st.subheader(🔗 最终信号")
            
            fusion_result = engine.fuse_signals(
                stock='000001',
                capital=selected_capital,
                factor_scores=[
                    lstm_factor,
                    kline_factor,
                    network_factor
                ]
            )
            
            # 色彩指示符
            color_map = {
                SignalType.BULLISH: '🜟',
                SignalType.BEARISH: '🔴',
                SignalType.NEUTRAL: '🜜'
            }
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "多因子轻贡",
                    f"{fusion_result.composite_score:.2f}",
                    f"{color_map[fusion_result.signal]}"
                )
            
            with col2:
                st.metric(
                    "最终信号",
                    fusion_result.signal.name,
                    f"{color_map[fusion_result.signal]}"
                )
            
            with col3:
                st.metric(
                    "信信度",
                    f"{fusion_result.confidence:.1%}"
                )
            
            # 多因子收栉
            st.info(fusion_result.reasoning)
        
        except Exception as e:
            st.error(f"Fusion analysis error: {str(e)}")
    
    # ==================== Tab5: 母帀教客 ====================
    with tab5:
        st.subheader(🏱 模型溙基评估")
        
        st.write("""
        【预考首類】
        
        此额涆展示融合模型的溙基渓種: 
        
        - **溙基率** (溙基 / (溙基 + 错鍛)): 模型溙基上榜信号的渓有率
        - **召回率** (溙基 / (溙基 + 错辨)): 模型抙到溙基上榜的覆泊率
        - **F1轻数**: 溙基率与召回率的貃伐
        - **溙基率**: 模型验配的溙基比会
        
        【齿考性能目标】
        
        根操历史渓种，融合模型的预考溙基目标：
        
        | 估段 | 目标 |
        |------|--------|
        | 溙基率 | 65-80% |
        | 召回率 | 60-75% |
        | F1轻数 | 62-77% |
        | 溙基率 | 65-75% |
        """)
        
        st.markdown("---")
        
        # Demo 市场溙基数据
        df_actual = pd.DataFrame({
            'stock': ['000001', '000002', '000003', '000004', '000005'],
            'actual_change': [2.5, -1.2, 3.1, 0.8, -2.3]
        })
        
        # 评估融合准确性
        try:
            evaluation = engine.evaluate_fusion_accuracy(df_actual)
            
            if evaluation:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("溙基率", f"{evaluation['accuracy']:.1%}")
                
                with col2:
                    st.metric("召回率", f"{evaluation['recall']:.1%}")
                
                with col3:
                    st.metric("F1轻数", f"{evaluation['f1_score']:.1%}")
                
                with col4:
                    st.metric("溙基率", f"{evaluation['hit_rate']:.1%}")
                
                # 溙基数据可載
                st.dataframe(pd.DataFrame([
                    {'metric': 'Accuracy', 'value': evaluation['accuracy']},
                    {'metric': 'Precision', 'value': evaluation['precision']},
                    {'metric': 'Recall', 'value': evaluation['recall']},
                    {'metric': 'F1 Score', 'value': evaluation['f1_score']},
                    {'metric': 'Hit Rate', 'value': evaluation['hit_rate']}
                ]), use_container_width=True)
        
        except Exception as e:
            st.warning(f"Accuracy evaluation requires more historical data.")


if __name__ == "__main__":
    page_network_fusion()
