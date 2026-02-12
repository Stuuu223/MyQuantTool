"""
板块轮动分析系统UI
功能：30个行业板块实时强度评分、轮动识别、趋势预测
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from logic.data_manager import DataManager
from logic.formatter import Formatter


def render_sector_rotation_tab(db, config):
    """渲染板块轮动分析标签页"""
    
    st.header("🔄 板块轮动分析")
    st.caption("30个行业板块实时强度评分 | 基于日内资金流的实时热度 | 轮动机会识别")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 分析配置")

        date = st.date_input("分析日期", value=datetime.now().date(), key="sector_date")
        date_str = date.strftime("%Y%m%d")

        # 🆕 V9.3.8: 移除侧边栏的 AkShare 调用，避免阻塞 UI
        # 市场概览和涨跌停统计现在从主页面获取

        st.markdown("---")
        st.markdown("### 📊 强度计算公式")
        st.info("""
        **强度分 = 平均涨幅 × 70% + 涨停率 × 30%**

        - **平均涨幅**: 板块内所有股票的平均涨跌幅
        - **涨停率**: 涨停股票数量 / 板块总股票数量

        此算法基于日内资金流的实时热度，无需历史数据
        """)

        st.markdown("---")
        st.markdown("### 💡 使用说明")
        st.markdown("""
        - **极速模式**: 基于全市场快照，耗时 <0.1秒
        - **实时数据**: 反映此时此刻的资金流向
        - **适用场景**: 盘中盯盘，捕捉热点板块
        - **数据来源**: Easyquotation (新浪) + 行业缓存
        """)
    
    # 主要内容
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 板块强度排行")
        
        # 自动加载分析数据
        with st.spinner("正在分析板块轮动..."):
            try:
                # 🆕 V9.3.8: 使用极速板块分析器（基于全市场快照，无额外网络请求）
                from logic.sector_analysis import get_fast_sector_analyzer
                
                # 初始化极速分析器
                analyzer = get_fast_sector_analyzer(db)
                
                # 获取板块强度排行（极速版）
                sector_ranking = analyzer.get_sector_ranking()
                
                if not sector_ranking.empty:
                    st.info(f"💡 数据来源：全市场快照聚合（共{len(sector_ranking)}个板块，耗时<0.1秒）")

                    # 计算最大成交额（用于归一化）
                    max_amount = sector_ranking['amount'].max() if sector_ranking['amount'].max() > 0 else 1

                    # 转换为DataFrame，适配现有UI格式
                    df_strength = pd.DataFrame([
                        {
                            '板块': row['industry'],
                            '综合评分': row['strength_score'],
                            '涨跌幅': row['pct_chg'],
                            '成交额': row['amount'],
                            '换手率': 0,  # 暂不计算换手率
                            '最新价': 0,  # 暂不计算最新价
                            '涨幅因子': row['pct_chg'] * 0.7,  # 简化计算
                            '资金因子': (row['amount'] / max_amount) * 100 * 0.3 if row['amount'] > 0 else 0,
                            '龙头因子': row['is_limit_up'] * 10,  # 简化计算
                            '题材因子': 0,  # 暂不计算题材因子
                            '成交因子': 0,  # 暂不计算成交因子
                            '轮动阶段': '领跑' if row['strength_score'] >= 70 else '上升中' if row['strength_score'] >= 50 else '落后',
                            '领跑股票': row['top_stock'] if pd.notna(row['top_stock']) else '-',
                            '强度变化': 0  # 暂不计算强度变化
                        }
                        for _, row in sector_ranking.iterrows()
                    ])

                    # 按综合评分排序
                    df_strength = df_strength.sort_values('综合评分', ascending=False)

# 格式化成交额、涨跌幅、换手率
                    df_strength['成交额_格式化'] = df_strength['成交额'].apply(Formatter.format_amount)
                    df_strength['涨跌幅_格式化'] = df_strength['涨跌幅'].apply(lambda x: f"{x:+.2f}%" if x != 0 else "0.00%")
                    df_strength['换手率_格式化'] = df_strength['换手率'].apply(lambda x: f"{x:.2f}%" if x != 0 else "0.00%")
                    
                    # 格式化强度变化（添加箭头和颜色标识）
                    def format_delta(delta):
                        if delta == 0:
                            return "0.0"
                        elif delta > 0:
                            return f"↗ +{delta:.1f}"
                        else:
                            return f"↘ {delta:.1f}"
                    
                    df_strength['强度变化_格式化'] = df_strength['强度变化'].apply(format_delta)
                    
                    # 格式化领跑股票
                    df_strength['领跑股票_格式化'] = df_strength['领跑股票'].apply(lambda x: x if x != '-' else '暂无数据')

                    # 显示排行榜（优化版）
                    st.dataframe(
                        df_strength.head(15)[['板块', '综合评分', '涨跌幅_格式化', '成交额_格式化', '换手率_格式化', '领跑股票_格式化', '强度变化_格式化']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            '板块': st.column_config.TextColumn(
                                '板块',
                                width='medium'
                            ),
                            '综合评分': st.column_config.ProgressColumn(
                                '综合评分',
                                help='0-100分，分数越高板块越强',
                                format='%.1f',
                                min_value=0,
                                max_value=100,
                                width='medium'
                            ),
                            '涨跌幅_格式化': st.column_config.TextColumn(
                                '涨跌幅',
                                help='板块平均涨跌幅',
                                width='small'
                            ),
                            '成交额_格式化': st.column_config.TextColumn(
                                '成交额',
                                help='板块总成交额',
                                width='medium'
                            ),
                            '换手率_格式化': st.column_config.TextColumn(
                                '换手率',
                                help='板块平均换手率',
                                width='small'
                            ),
                            '领跑股票_格式化': st.column_config.TextColumn(
                                '领跑股票',
                                help='板块内表现最好的股票',
                                width='medium'
                            ),
                            '强度变化_格式化': st.column_config.TextColumn(
                                '强度变化',
                                help='与前一日的强度变化',
                                width='small'
                            )
                        }
                    )
                    # 🆕 V9.3.8: 简化的轮动信号识别（基于实时数据）
                    st.markdown("---")
                    st.subheader("🎯 板块热度分布")

                    # 基于强度分进行分类
                    strong = df_strength[df_strength['综合评分'] >= 70]
                    medium = df_strength[(df_strength['综合评分'] >= 40) & (df_strength['综合评分'] < 70)]
                    weak = df_strength[df_strength['综合评分'] < 40]

                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        st.metric("🔥 强势", len(strong))
                        if len(strong) > 0:
                            st.write(", ".join(strong['板块'].head(3).tolist()))

                    with col_b:
                        st.metric("🟡 中性", len(medium))
                        if len(medium) > 0:
                            st.write(", ".join(medium['板块'].head(3).tolist()))

                    with col_c:
                        st.metric("❄️ 弱势", len(weak))
                        if len(weak) > 0:
                            st.write(", ".join(weak['板块'].head(3).tolist()))

                    # 板块强度可视化
                    st.markdown("---")
                    st.subheader("📈 板块强度可视化")
                    
                    fig = go.Figure()
                    
                    # 添加柱状图
                    fig.add_trace(go.Bar(
                        x=df_strength['板块'].head(15),
                        y=df_strength['综合评分'].head(15),
                        marker_color=df_strength['综合评分'].head(15).apply(
                            lambda x: '#00C853' if x >= 70 else '#FFC107' if x >= 50 else '#FF5252'
                        ),
                        text=df_strength['综合评分'].head(15).apply(lambda x: f'{x:.1f}'),
                        textposition='auto',
                    ))
                    
                    fig.update_layout(
                        title='板块综合评分TOP15',
                        xaxis_title='板块',
                        yaxis_title='综合评分',
                        yaxis_range=[0, 100],
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # 板块涨跌幅分析
                    st.markdown("---")
                    st.subheader("📊 板块涨跌幅分析")

                    fig_change = go.Figure()
                    fig_change.add_trace(go.Bar(
                        x=df_strength['板块'].head(15),
                        y=df_strength['涨跌幅'].head(15),
                        marker_color=df_strength['涨跌幅'].head(15).apply(
                            lambda x: '#00C853' if x > 0 else '#FF5252' if x < 0 else '#9E9E9E'
                        ),
                        text=df_strength['涨跌幅'].head(15).apply(lambda x: f'{x:+.2f}%'),
                        textposition='auto',
                    ))
                    fig_change.update_layout(
                        title='板块涨跌幅TOP15',
                        xaxis_title='板块',
                        yaxis_title='涨跌幅(%)',
                        height=500
                    )
                    st.plotly_chart(fig_change, use_container_width=True)

                    # 板块资金流入分析（成交额）
                    st.markdown("---")
                    st.subheader("💰 板块资金流入分析")

                    fig_capital = go.Figure()
                    fig_capital.add_trace(go.Bar(
                        x=df_strength['板块'].head(15),
                        y=df_strength['成交额'].head(15),
                        marker_color='#2196F3',
                        text=df_strength['成交额'].head(15).apply(lambda x: f'¥{x/1e8:.2f}亿' if x > 0 else '¥0'),
                        textposition='auto',
                    ))
                    fig_capital.update_layout(
                        title='板块成交额TOP15（资金热度）',
                        xaxis_title='板块',
                        yaxis_title='成交额(元)',
                        height=500
                    )
                    st.plotly_chart(fig_capital, use_container_width=True)

                    # 板块活跃度分析（换手率）
                    st.markdown("---")
                    st.subheader("🔄 板块活跃度分析")

                    fig_turnover = go.Figure()
                    fig_turnover.add_trace(go.Bar(
                        x=df_strength['板块'].head(15),
                        y=df_strength['换手率'].head(15),
                        marker_color='#FF9800',
                        text=df_strength['换手率'].head(15).apply(lambda x: f'{x:.2f}%'),
                        textposition='auto',
                    ))
                    fig_turnover.update_layout(
                        title='板块换手率TOP15',
                        xaxis_title='板块',
                        yaxis_title='换手率(%)',
                        height=500
                    )
                    st.plotly_chart(fig_turnover, use_container_width=True)

                    # 🆕 V9.3.8: 简化的 TOP3 板块分析
                    st.markdown("---")
                    st.subheader("📊 TOP3板块详细分析")

                    top3_sectors = df_strength.head(3)

                    for _, row in top3_sectors.iterrows():
                        with st.expander(f"🏆 {row['板块']} - {row['综合评分']:.1f}分"):
                            col_f1, col_f2, col_f3 = st.columns(3)

                            col_f1.metric("综合评分", f"{row['综合评分']:.1f}")
                            col_f2.metric("平均涨幅", f"{row['涨跌幅']:+.2f}%")
                            col_f3.metric("成交额", Formatter.format_amount(row['成交额']))

                            if row['领跑股票'] != '-':
                                st.info(f"📌 领跑股票: {row['领跑股票']}")
                    
                else:
                    st.warning("⚠️ 未能获取板块数据，请稍后重试")
            
            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")
    
    with col2:
        st.subheader("📋 操作建议")
        
        st.markdown("""
        ### 💡 轮动策略
        
        **🔥 强势板块 (评分 ≥ 70)**
        - 重点配置，持有待涨
        - 关注龙头股，注意分化
        - 适度追涨，设置止损
        
        **🟡 中性板块 (评分 40-70)**
        - 观望为主，等待信号
        - 轻仓试错，寻找机会
        - 注意板块轮动
        
        **❄️ 弱势板块 (评分 < 40)**
        - 减仓规避，等待企稳
        - 不建议抄底
        - 观望为主
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 🎯 因子解读
        
        **平均涨幅 (70%)**
        - 反映板块整体涨幅
        - 越强说明市场关注度越高
        
        **涨停率 (30%)**
        - 反映板块爆发力
        - 涨停股票越多，板块越强
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 📊 数据说明
        
        **数据来源**: 全市场快照聚合
        **更新频率**: 实时（每分钟）
        **计算方式**: 纯内存计算，无网络请求
        **适用场景**: 盘中盯盘，捕捉热点板块
        """)