"""游资关系图谱UI页面"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from logic.capital_network import CapitalNetworkBuilder
from logic.algo_capital import CapitalAnalyzer
from logic.formatter import Formatter


def render_capital_network_tab(db, config):
    """渲染游资关系图谱标签页"""
    
    st.subheader("🕸️ 游资关系图谱")
    st.caption("构建游资-股票二部图，分析游资网络结构和对手关系")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 图谱配置")
        
        lookback_days = st.slider("回溯天数", 7, 90, 30, help="分析最近多少天的龙虎榜数据")
        
        include_competitive = st.checkbox("包含对手关系", value=True, help="是否分析游资之间的竞争关系")
        
        min_operations = st.slider("最小操作次数", 1, 10, 2, help="游资最少操作次数才纳入分析")
        
        st.markdown("---")
        st.subheader("📊 分析维度")
        
        analysis_mode = st.selectbox(
            "分析模式",
            ["网络概览", "中心节点分析", "对手关系分析", "群组聚类分析"],
            help="选择不同的分析维度"
        )
        
        st.markdown("---")
        st.subheader("💡 图谱说明")
        st.info("""
        **游资关系图谱功能**：
        
        - 📈 二部图：游资-股票关系网络
        - 🎯 中心节点：识别核心游资
        - ⚔️ 对手关系：同一股票上的买卖博弈
        - 📊 群组聚类：使用谱聚类算法分组
        """)
    
    # 主内容区
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 关系图谱分析")
        
        # 获取龙虎榜数据
        if st.button("🔍 构建关系图谱", key="build_network"):
            with st.spinner('正在构建游资关系图谱...'):
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
                    
                    # 过滤操作次数
                    capital_counts = df_lhb['游资名称'].value_counts()
                    active_capitals = capital_counts[capital_counts >= min_operations].index.tolist()
                    df_lhb_filtered = df_lhb[df_lhb['游资名称'].isin(active_capitals)]
                    
                    if df_lhb_filtered.empty:
                        st.warning("⚠️ 过滤后无数据，请降低最小操作次数")
                        return
                    
                    # 添加操作方向列（根据净买入判断）
                    df_lhb_filtered['操作方向'] = df_lhb_filtered['净买入'].apply(
                        lambda x: '买' if x > 0 else '卖'
                    )
                    
                    # 构建图谱
                    builder = CapitalNetworkBuilder(lookback_days=lookback_days)
                    graph = builder.build_graph_from_lhb(
                        df_lhb_filtered,
                        include_competitive=include_competitive
                    )
                    
                    # 计算节点指标
                    node_metrics = builder.calculate_node_metrics()
                    
                    # 获取网络摘要
                    summary = builder.get_network_summary()
                    
                    st.success(f"✅ 图谱构建完成！")
                    
                    # 显示网络摘要
                    st.divider()
                    st.subheader("📋 网络摘要")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("游资节点数", summary['total_capitals'])
                    with col_b:
                        st.metric("股票节点数", summary['total_stocks'])
                    with col_c:
                        st.metric("关系边数", summary['total_edges'])
                    
                    col_d, col_e, col_f = st.columns(3)
                    with col_d:
                        st.metric("网络密度", f"{summary['network_density']:.4f}")
                    with col_e:
                        st.metric("平均聚类系数", f"{summary['average_clustering']:.4f}")
                    with col_f:
                        st.metric("连通分量数", summary['connected_components'])
                    
                    # 根据分析模式显示不同内容
                    if analysis_mode == "网络概览":
                        st.divider()
                        st.subheader("🕸️ 网络可视化")
                        
                        # 创建交互式网络图
                        fig = _create_network_plotly(graph, node_metrics)
                        st.plotly_chart(fig, use_container_width=True)
                        
                    elif analysis_mode == "中心节点分析":
                        st.divider()
                        st.subheader("🎯 中心节点分析")
                        
                        # 提取中心游资
                        hub_capitals = summary['hub_capitals']
                        
                        if hub_capitals:
                            st.write("**核心游资节点**：")
                            for i, hub in enumerate(hub_capitals[:10], 1):
                                metrics = node_metrics[hub]
                                with st.expander(f"#{i} {hub}"):
                                    col_x, col_y, col_z = st.columns(3)
                                    with col_x:
                                        st.metric("度数", metrics.degree)
                                    with col_y:
                                        st.metric("中介中心度", f"{metrics.betweenness_centrality:.4f}")
                                    with col_z:
                                        st.metric("强度", f"{metrics.strength:.2f}")
                                    
                                    st.write(f"**节点类型**: {metrics.node_type}")
                                    st.write(f"**加权度数**: {metrics.weighted_degree:.2f}")
                                    st.write(f"**接近中心度**: {metrics.closeness_centrality:.4f}")
                                    st.write(f"**聚类系数**: {metrics.clustering_coefficient:.4f}")
                        else:
                            st.info("👍 未发现中心节点")
                        
                        # 游资排名
                        st.divider()
                        st.subheader("📊 游资影响力排名")
                        
                        capital_ranking = []
                        for node, metrics in node_metrics.items():
                            if metrics.node_type == 'capital':
                                capital_ranking.append({
                                    '游资名称': node,
                                    '度数': metrics.degree,
                                    '加权度数': metrics.weighted_degree,
                                    '中介中心度': metrics.betweenness_centrality,
                                    '接近中心度': metrics.closeness_centrality,
                                    '强度': metrics.strength
                                })
                        
                        ranking_df = pd.DataFrame(capital_ranking).sort_values(
                            '加权度数', ascending=False
                        )
                        
                        st.dataframe(
                            ranking_df.head(20),
                            column_config={
                                '中介中心度': st.column_config.NumberColumn('中介中心度', format="%.4f"),
                                '接近中心度': st.column_config.NumberColumn('接近中心度', format="%.4f"),
                                '强度': st.column_config.NumberColumn('强度', format="%.2f")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                    
                    elif analysis_mode == "对手关系分析":
                        st.divider()
                        st.subheader("⚔️ 对手关系分析")
                        
                        # 分析竞争格局
                        competitive_analysis = builder.analyze_competitive_landscape(df_lhb_filtered)
                        
                        # 显示有竞争关系的游资
                        competitive_capitals = {
                            k: v for k, v in competitive_analysis.items()
                            if v['battle_count'] > 0
                        }
                        
                        if competitive_capitals:
                            st.write(f"发现 {len(competitive_capitals)} 个游资存在竞争关系")
                            
                            for capital, analysis in competitive_capitals.items():
                                with st.expander(f"{capital} - {analysis['battle_count']} 次竞争"):
                                    st.write(f"**主要对手**：")
                                    for opponent, count in analysis['main_opponents']:
                                        st.write(f"- {opponent}: {count} 次")
                                    
                                    st.write(f"**竞争成功率**: {analysis['battle_success_rate']:.2%}")
                                    st.write(f"**主导股票数**: {len(analysis['dominated_stocks'])}")
                                    
                                    if analysis['dominated_stocks']:
                                        st.write(f"**主导股票**: {', '.join(analysis['dominated_stocks'][:5])}")
                        else:
                            st.info("👍 未发现明显的竞争关系")
                        
                        # 对手关系网络图
                        if include_competitive:
                            st.divider()
                            st.subheader("🕸️ 对手关系网络")
                            
                            fig = _create_competitive_network_plotly(graph, node_metrics)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif analysis_mode == "群组聚类分析":
                        st.divider()
                        st.subheader("📊 群组聚类分析")
                        
                        # 使用谱聚类分组
                        clusters = builder.get_capital_clusters(k=min(5, summary['total_capitals']))
                        
                        if clusters:
                            st.write(f"将游资分为 {len(clusters)} 个群组")
                            
                            for group_id, capitals in clusters.items():
                                with st.expander(f"群组 {group_id + 1} - {len(capitals)} 个游资"):
                                    for capital in capitals:
                                        metrics = node_metrics[capital]
                                        col_p, col_q = st.columns(2)
                                        with col_p:
                                            st.write(f"**{capital}**")
                                        with col_q:
                                            st.metric("度数", metrics.degree)
                            
                            # 群组特征分析
                            st.divider()
                            st.subheader("📈 群组特征对比")
                            
                            cluster_stats = []
                            for group_id, capitals in clusters.items():
                                total_degree = sum(node_metrics[c].degree for c in capitals)
                                avg_strength = sum(node_metrics[c].strength for c in capitals) / len(capitals)
                                
                                cluster_stats.append({
                                    '群组': f"群组{group_id + 1}",
                                    '游资数': len(capitals),
                                    '总度数': total_degree,
                                    '平均强度': avg_strength
                                })
                            
                            cluster_df = pd.DataFrame(cluster_stats)
                            
                            fig = px.bar(
                                cluster_df,
                                x='群组',
                                y=['总度数', '平均强度'],
                                title="群组特征对比",
                                barmode='group'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("👍 数据不足，无法进行聚类分析")
                
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    with col2:
        st.subheader("💡 分析建议")
        
        st.info("""
        **关系图谱解读**：
        
        1. **中心节点**：度数高、连接多的游资
        
        2. **对手关系**：同一股票上买卖博弈
        
        3. **群组聚类**：操作模式相似的游资
        
        4. **网络密度**：反映市场活跃度
        """)
        
        st.markdown("---")
        st.subheader("📊 指标说明")
        
        st.markdown("""
        **节点指标**：
        
        - **度数**：连接数量
        
        - **中介中心度**：信息流通能力
        
        - **接近中心度**：与其他节点的距离
        
        - **聚类系数**：局部连接密度
        
        - **强度**：加权连接强度
        """)


def _create_network_plotly(graph, node_metrics):
    """创建Plotly网络图"""
    import networkx as nx
    
    # 使用Spring布局
    pos = nx.spring_layout(graph, k=1.5, iterations=50, seed=42)
    
    # 提取节点和边
    capital_nodes = [n for n in graph.nodes() if graph.nodes[n].get('node_type') == 'capital']
    stock_nodes = [n for n in graph.nodes() if graph.nodes[n].get('node_type') == 'stock']
    
    # 创建节点轨迹
    node_trace = go.Scatter(
        x=[pos[n][0] for n in graph.nodes()],
        y=[pos[n][1] for n in graph.nodes()],
        mode='markers+text',
        text=[str(n) for n in graph.nodes()],
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(
            size=[node_metrics[n].degree * 3 + 10 for n in graph.nodes()],
            color=['#FF6B6B' if graph.nodes[n].get('node_type') == 'capital' else '#4ECDC4' 
                   for n in graph.nodes()],
            line=dict(width=1, color='#888')
        ),
        hovertemplate='<b>%{text}</b><br>度数: %{marker.size}<extra></extra>'
    )
    
    # 创建边轨迹
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode='lines',
        line=dict(width=0.5, color='#888'),
        hoverinfo='none'
    )
    
    # 创建图表
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=dict(text='游资关系网络图', font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        annotations=[
                            dict(
                                text="红色=游资, 蓝色=股票",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002,
                                xanchor='left', yanchor='bottom',
                                font=dict(size=12)
                            )
                        ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                    ))
    
    return fig


def _create_competitive_network_plotly(graph, node_metrics):
    """创建竞争关系网络图"""
    import networkx as nx
    
    # 只显示游资之间的竞争关系
    capital_nodes = [n for n in graph.nodes() if graph.nodes[n].get('node_type') == 'capital']
    subgraph = graph.subgraph(capital_nodes).copy()
    
    # 使用Spring布局
    pos = nx.spring_layout(subgraph, k=1.5, iterations=50, seed=42)
    
    # 创建节点轨迹
    node_trace = go.Scatter(
        x=[pos[n][0] for n in subgraph.nodes()],
        y=[pos[n][1] for n in subgraph.nodes()],
        mode='markers+text',
        text=[str(n) for n in subgraph.nodes()],
        textposition="top center",
        textfont=dict(size=10),
        marker=dict(
            size=[node_metrics[n].degree * 5 + 15 for n in subgraph.nodes()],
            color='#FF6B6B',
            line=dict(width=2, color='#333')
        ),
        hovertemplate='<b>%{text}</b><br>度数: %{marker.size}<extra></extra>'
    )
    
    # 创建边轨迹（只显示竞争关系）
    edge_x = []
    edge_y = []
    edge_weights = []
    
    for edge in subgraph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(subgraph[edge[0]][edge[1]].get('competitive_count', 1))
    
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode='lines',
        line=dict(width=1.0, color='#FF4444'),
        hoverinfo='none'
    )
    
    # 创建图表
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=dict(text='游资竞争关系网络图', font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        annotations=[
                            dict(
                                text="连线粗细=竞争次数",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002,
                                xanchor='left', yanchor='bottom',
                                font=dict(size=12)
                            )
                        ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                    ))
    
    return fig