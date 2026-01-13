"""
龙头识别与跟踪系统 UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.dragon_tracking_system import DragonTrackingSystem
from logic.data_manager import DataManager


def render_dragon_tracking_tab(db: DataManager, config):
    """渲染龙头识别与跟踪标签页"""
    
    st.title("🐉 龙头识别与跟踪系统")
    st.markdown("---")
    
    # 初始化系统
    if 'dragon_tracking_system' not in st.session_state:
        st.session_state.dragon_tracking_system = DragonTrackingSystem()
    
    system = st.session_state.dragon_tracking_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 市场环境
        st.subheader("🌍 市场环境")
        market_environment = st.selectbox(
            "选择市场环境",
            ['neutral', 'bull', 'bear'],
            format_func=lambda x: {
                'neutral': '中性市场',
                'bull': '牛市',
                'bear': '熊市'
            }[x]
        )
        
        if st.button("应用市场环境"):
            system.set_market_environment(market_environment)
            st.success(f"市场环境已设置为: {market_environment}")
        
        # 股票输入
        st.subheader("📊 股票分析")
        stock_code = st.text_input("股票代码", value="600000", help="输入股票代码，如 600000")
        
        # 模拟数据生成
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dragons = system.lifecycle_manager.get_all_dragons()
        st.metric("跟踪龙头数", len(dragons))
    
    with col2:
        top_dragons = system.get_top_dragons(limit=5)
        avg_days = sum(d['limit_up_days'] for d in top_dragons) / len(top_dragons) if top_dragons else 0
        st.metric("平均涨停天数", f"{avg_days:.1f}")
    
    with col3:
        st.metric("市场环境", market_environment)
    
    # 分析股票
    st.markdown("---")
    st.header("🔍 单股分析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔎 分析龙头", use_container_width=True):
            with st.spinner("正在分析..."):
                # 生成模拟数据
                dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=10)
                stock_data = pd.DataFrame({
                    'date': dates,
                    'open': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
                    'close': [10.5, 11.0, 11.5, 12.0, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5],
                    'high': [10.6, 11.1, 11.6, 12.1, 12.6, 13.6, 14.6, 15.6, 16.6, 17.6],
                    'low': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
                    'volume': [1000000, 1200000, 1500000, 1800000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000],
                    'pct_chg': [5.0, 4.8, 4.5, 4.3, 4.2, 8.3, 7.4, 6.9, 6.5, 6.1]
                })
                
                stock_info = {
                    'market_cap': 50000000000,
                    'social_heat': 0.8
                }
                
                sector_data = {
                    'change_pct': 5.0
                }
                
                news_data = [
                    {'publish_time': datetime.now() - timedelta(hours=2), 'title': '公司发布重大利好'},
                    {'publish_time': datetime.now() - timedelta(hours=5), 'title': '行业前景看好'}
                ]
                
                result = system.analyze_stock(
                    stock_code=stock_code,
                    stock_data=stock_data,
                    stock_info=stock_info,
                    sector_data=sector_data,
                    news_data=news_data
                )
                
                st.session_state.last_dragon_result = result
                st.success("分析完成！")
    
    # 显示分析结果
    if 'last_dragon_result' in st.session_state:
        result = st.session_state.last_dragon_result
        
        with col2:
            st.subheader("📊 分析结果")
            
            # 龙头判断
            if result['is_dragon']:
                st.success(f"✅ **{result['stock_code']} 是龙头股**")
            else:
                st.warning(f"⚠️ **{result['stock_code']} 不是龙头股**")
            
            # 评分
            col1, col2, col3 = st.columns(3)
            col1.metric("评分", f"{result['score']:.2f}")
            col2.metric("置信度", f"{result['confidence']:.2f}")
            col3.metric("潜力", result['potential'])
    
    # 详细分析
    if 'last_dragon_result' in st.session_state:
        result = st.session_state.last_dragon_result
        
        st.markdown("---")
        st.header("📈 详细分析")
        
        # 特征分析
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 龙头特征")
            features = result['features']
            
            feature_data = []
            for key, value in features.items():
                if isinstance(value, (int, float)):
                    feature_data.append({
                        '特征': key,
                        '数值': f"{value:.4f}" if isinstance(value, float) else value,
                        '评分': f"{min(1.0, max(0, value)):.2f}"
                    })
            
            st.dataframe(
                pd.DataFrame(feature_data),
                use_container_width=True
            )
        
        with col2:
            st.subheader("🔄 生命周期")
            lifecycle = result['lifecycle']
            
            st.info(f"**当前阶段**: {lifecycle['current_stage']}")
            st.info(f"**下一阶段**: {lifecycle['next_stage']}")
            st.info(f"**持续时间**: {lifecycle['stage_duration']} 天")
            st.info(f"**涨停天数**: {lifecycle['limit_up_days']} 天")
            st.info(f"**操作建议**: {lifecycle['action']}")
            
            if lifecycle['stage_changed']:
                st.warning("⚠️ 阶段已发生变化！")
    
    # 龙头列表
    st.markdown("---")
    st.header("🐉 跟踪龙头列表")
    
    dragons = system.get_top_dragons(limit=10)
    
    if dragons:
        df = pd.DataFrame(dragons)
        
        # 阶段颜色映射
        stage_colors = {
            '启动': '#4CAF50',
            '加速': '#2196F3',
            '分歧': '#FF9800',
            '衰竭': '#F44336',
            '退潮': '#9E9E9E'
        }
        
        # 显示表格
        st.dataframe(
            df[['stock_code', 'current_stage', 'limit_up_days', 'total_days', 'current_price', 'peak_price']],
            use_container_width=True
        )
        
        # 龙头分布图表
        stage_counts = df['current_stage'].value_counts()
        
        fig = go.Figure(data=[
            go.Bar(
                x=stage_counts.index,
                y=stage_counts.values,
                marker_color=[stage_colors.get(stage, '#9E9E9E') for stage in stage_counts.index]
            )
        ])
        
        fig.update_layout(
            title="龙头生命周期分布",
            xaxis_title="阶段",
            yaxis_title="数量",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无跟踪的龙头")
    
    # 生命周期说明
    st.markdown("---")
    st.header("📋 生命周期说明")
    
    lifecycle_info = pd.DataFrame([
        {
            '阶段': '启动',
            '说明': '首次涨停，市场开始关注',
            '操作建议': '关注，等待确认',
            '持续时间': '2天'
        },
        {
            '阶段': '加速',
            '说明': '连续涨停，市场情绪高涨',
            '操作建议': '积极参与，控制仓位',
            '持续时间': '4天'
        },
        {
            '阶段': '分歧',
            '说明': '涨停断档，市场出现分歧',
            '操作建议': '谨慎，考虑减仓',
            '持续时间': '3天'
        },
        {
            '阶段': '衰竭',
            '说明': '价格下跌，动能衰竭',
            '操作建议': '清仓，锁定利润',
            '持续时间': '2天'
        },
        {
            '阶段': '退潮',
            '说明': '热度消退，寻找新机会',
            '操作建议': '观望，寻找新机会',
            '持续时间': '5天'
        }
    ])
    
    st.dataframe(lifecycle_info, use_container_width=True)