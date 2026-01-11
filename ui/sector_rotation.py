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
    st.caption("30个行业板块实时强度评分 | 5因子加权模型 | 轮动机会识别")
    
    # 侧边栏配置
    with st.sidebar:
        st.subheader("⚙️ 分析配置")

        date = st.date_input("分析日期", value=datetime.now().date(), key="sector_date")
        date_str = date.strftime("%Y%m%d")

        # 市场概览
        st.markdown("---")
        st.subheader("📊 市场概览")

        try:
            import akshare as ak

            # 获取主要指数
            index_data = ak.stock_zh_index_spot_em()
            major_indices = index_data[index_data['代码'].isin(['000001', '399001', '399006'])]

            for _, row in major_indices.iterrows():
                change_color = "📈" if row['涨跌幅'] > 0 else "📉" if row['涨跌幅'] < 0 else "➡️"
                st.metric(
                    f"{change_color} {row['名称']}",
                    f"{row['涨跌幅']:+.2f}%"
                )

            # 涨跌停统计
            st.markdown("---")
            st.subheader("🎯 涨跌停统计")

            limit_up = ak.stock_zt_pool_em(date=date_str)
            limit_down = ak.stock_dt_pool_em(date=date_str)

            col_zt, col_dt = st.columns(2)
            with col_zt:
                st.metric("涨停", len(limit_up))
            with col_dt:
                st.metric("跌停", len(limit_down))

        except Exception as e:
            st.warning(f"获取市场数据失败: {e}")

        st.markdown("---")
        st.markdown("### 📊 因子权重")
        price_weight = st.slider("涨幅因子", 0, 50, 30, 5) / 100
        capital_weight = st.slider("资金因子", 0, 50, 25, 5) / 100
        leader_weight = st.slider("龙头因子", 0, 50, 20, 5) / 100
        topic_weight = st.slider("题材因子", 0, 50, 15, 5) / 100
        volume_weight = st.slider("成交因子", 0, 50, 10, 5) / 100

        total_weight = price_weight + capital_weight + leader_weight + topic_weight + volume_weight
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"⚠️ 权重总和应为100%，当前为{total_weight*100:.1f}%")
    
    # 主要内容
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 板块强度排行")
        
        # 自动加载分析数据
        with st.spinner("正在分析板块轮动..."):
            try:
                # 延迟导入分析器
                from logic.sector_rotation_analyzer import get_sector_rotation_analyzer
                
                # 延迟初始化分析器
                analyzer = get_sector_rotation_analyzer(history_days=30)
                
                # 计算板块强度
                strength_scores = analyzer.calculate_sector_strength(date_str)
                
                if strength_scores:
                    # 获取原始板块数据
                    industry_df = analyzer._get_industry_data()
                    is_real_data = len(industry_df) > 0 and len(industry_df) > 10

                    if is_real_data:
                        st.info(f"💡 数据来源：AkShare 实时数据（共{len(industry_df)}个板块）")
                    else:
                        st.warning("⚠️ 提示：当前使用演示数据，可能是非交易时间或数据源异常")

                    # 转换为DataFrame，包含原始数据
                    df_strength = pd.DataFrame([
                        {
                            '板块': sector,
                            '综合评分': strength.total_score,
                            '涨跌幅': 0,
                            '成交额': 0,
                            '换手率': 0,
                            '最新价': 0,
                            '涨幅因子': strength.price_score,
                            '资金因子': strength.capital_score,
                            '龙头因子': strength.leader_score,
                            '题材因子': strength.topic_score,
                            '成交因子': strength.volume_score,
                            '轮动阶段': strength.phase.value,
                            '领跑股票': strength.leading_stock or '-',
                            '强度变化': strength.delta
                        }
                        for sector, strength in strength_scores.items()
                    ])

                    # 显示数据质量提示
                    if is_real_data:
                        zero_leading = len(df_strength[df_strength['领跑股票'] == '-'])
                        zero_delta = len(df_strength[df_strength['强度变化'] == 0])

                        tips = []
                        if zero_leading > 0:
                            tips.append(f"{zero_leading}个板块暂无领跑股票数据")
                        if zero_delta > 0:
                            tips.append(f"{zero_delta}个板块强度变化为0（首次运行或非交易日）")
                        
                        if tips:
                            st.info("💡 提示：" + "；".join(tips))

                    # 从原始数据中填充实际值
                    for idx, row in df_strength.iterrows():
                        sector_name = row['板块']
                        # 查找匹配的板块数据
                        mask = industry_df.apply(
                            lambda r: sector_name in str(r.get('名称', '') if r.get('名称', '') is not None else ''),
                            axis=1
                        )
                        if mask.any():
                            sector_data = industry_df[mask].iloc[0]
                            df_strength.at[idx, '涨跌幅'] = sector_data.get('涨跌幅', 0)
                            df_strength.at[idx, '成交额'] = sector_data.get('成交额', 0)
                            df_strength.at[idx, '换手率'] = sector_data.get('换手率', 0)
                            df_strength.at[idx, '最新价'] = sector_data.get('最新价', 0)

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
                    # 检测轮动信号
                    st.markdown("---")
                    st.subheader("🎯 轮动信号识别")

                    signals = analyzer.detect_rotation_signals(date_str)

                    # 统计各阶段板块数量
                    rising_count = len(signals['rising'])
                    falling_count = len(signals['falling'])
                    leading_count = len(signals['leading'])
                    lagging_count = len(signals['lagging'])
                    stable_count = len(strength_scores) - rising_count - falling_count - leading_count - lagging_count

                    col_a, col_b, col_c, col_d = st.columns(4)

                    with col_a:
                        st.metric("📈 上升中", rising_count)
                        if signals['rising']:
                            st.write(", ".join(signals['rising'][:3]))

                    with col_b:
                        st.metric("📉 下降中", falling_count)
                        if signals['falling']:
                            st.write(", ".join(signals['falling'][:3]))

                    with col_c:
                        st.metric("🏆 领跑", leading_count)
                        if signals['leading']:
                            st.write(", ".join(signals['leading'][:3]))

                    with col_d:
                        st.metric("⚠️ 落后", lagging_count)
                        if signals['lagging']:
                            st.write(", ".join(signals['lagging'][:3]))

                    # 显示稳定板块数量
                    if stable_count > 0:
                        st.info(f"📊 稳定板块: {stable_count} 个")
                    
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

                    # 因子雷达图
                    st.markdown("---")
                    st.subheader("📊 TOP3板块因子分析")

                    top3_sectors = df_strength.head(3)

                    for _, row in top3_sectors.iterrows():
                        with st.expander(f"🏆 {row['板块']} - {row['综合评分']:.1f}分"):
                            col_f1, col_f2, col_f3 = st.columns(3)

                            col_f1.metric("涨幅因子", f"{row['涨幅因子']:.1f}")
                            col_f2.metric("资金因子", f"{row['资金因子']:.1f}")
                            col_f3.metric("龙头因子", f"{row['龙头因子']:.1f}")
                            
                            col_f4, col_f5 = st.columns(2)
                            col_f4.metric("题材因子", f"{row['题材因子']:.1f}")
                            col_f5.metric("成交因子", f"{row['成交因子']:.1f}")
                            
                            if row['领跑股票'] != '-':
                                st.info(f"📌 领跑股票: {row['领跑股票']}")
                            
                            if row['强度变化'] > 5:
                                st.success(f"📈 强度快速上升 (+{row['强度变化']:.1f})")
                            elif row['强度变化'] < -5:
                                st.warning(f"📉 强度快速下降 ({row['强度变化']:.1f})")
                    
                else:
                    st.warning("⚠️ 未能获取板块数据，请稍后重试")
            
            except Exception as e:
                st.error(f"❌ 分析失败: {str(e)}")
    
    with col2:
        st.subheader("📋 操作建议")
        
        st.markdown("""
        ### 💡 轮动策略
        
        **📈 上升中板块**
        - 关注龙头股
        - 适度追涨
        - 设置止损
        
        **🏆 领跑板块**
        - 重点配置
        - 持有待涨
        - 注意分化
        
        **📉 下降中板块**
        - 减仓规避
        - 等待企稳
        - 不建议抄底
        
        **⚠️ 落后板块**
        - 避免参与
        - 观望为主
        - 等待轮动
        """)
        
        st.markdown("---")
        st.markdown("""
        ### 🎯 因子解读
        
        **涨幅因子 (30%)**
        - 反映板块整体涨幅
        - 越强说明市场关注度越高
        
        **资金因子 (25%)**
        - 反映主力资金流入
        - 资金流入越多越强
        
        **龙头因子 (20%)**
        - 反映龙虎榜活跃度
        - 龙头股表现决定板块强度
        
        **题材因子 (15%)**
        - 反映热点题材关联
        - 题材越热板块越强
        
        **成交因子 (10%)**
        - 反映成交量活跃度
        - 放量上涨更可靠
        """)