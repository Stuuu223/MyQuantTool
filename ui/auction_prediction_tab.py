"""
集合竞价预测系统 UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.auction_prediction_system import AuctionPredictionSystem
from logic.data_manager import DataManager


def render_auction_prediction_tab(db: DataManager, config):
    """渲染集合竞价预测标签页"""
    
    st.title("⚡ 集合竞价预测系统")
    st.markdown("---")
    
    # 初始化系统
    if 'auction_prediction_system' not in st.session_state:
        st.session_state.auction_prediction_system = AuctionPredictionSystem()
    
    system = st.session_state.auction_prediction_system
    
    # 侧边栏控制
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 股票输入
        st.subheader("📊 竞价分析")
        stock_code = st.text_input("股票代码", value="600000", help="输入股票代码", key="auction_prediction_stock_code")
        
        # 竞价数据输入
        st.subheader("📈 竞价数据")
        auction_price = st.number_input("匹配价格", value=11.0, help="集合竞价匹配价格")
        auction_volume = st.number_input("匹配成交量", value=2000000, help="集合竞价匹配成交量")
        buy_volume = st.number_input("买盘成交量", value=1500000, help="买盘成交量")
        sell_volume = st.number_input("卖盘成交量", value=500000, help="卖盘成交量")
        auction_high = st.number_input("最高价", value=11.2, help="竞价期间最高价")
        auction_low = st.number_input("最低价", value=10.8, help="竞价期间最低价")
        
        # 前一日数据
        st.subheader("📅 前一日数据")
        prev_close = st.number_input("前收盘价", value=10.5, help="前一日收盘价")
        prev_volume = st.number_input("前成交量", value=1000000, help="前一日成交量")
        
        # 市场情绪
        st.subheader("🧠 市场情绪")
        market_sentiment = st.slider("市场情绪", -1.0, 1.0, 0.5, 0.1, help="市场情绪得分 (-1 到 1)")
        
        # 阈值设置
        st.subheader("⚠️ 预警阈值")
        with st.expander("设置阈值"):
            volume_surge_threshold = st.slider("成交量激增阈值", 1.0, 5.0, 2.0, 0.5)
            price_gap_threshold = st.slider("价格跳空阈值", 0.01, 0.10, 0.05, 0.01)
            order_imbalance_threshold = st.slider("买卖盘不平衡阈值", 0.1, 1.0, 0.5, 0.1)
            
            if st.button("应用阈值"):
                system.monitor.set_threshold('volume_surge', volume_surge_threshold)
                system.monitor.set_threshold('price_gap', price_gap_threshold)
                system.monitor.set_threshold('order_imbalance', order_imbalance_threshold)
                st.success("阈值已更新")
        
        st.info("💡 提示: 当前使用模拟数据，实际使用时请连接真实数据源")
    
    # 主内容区
    col1, col2, col3 = st.columns(3)
    
    with col1:
        alerts = system.get_alerts(limit=10)
        st.metric("最近预警", f"{len(alerts)} 条")
    
    with col2:
        st.metric("分析股票", stock_code)
    
    with col3:
        st.metric("市场情绪", f"{market_sentiment:.2f}")
    
    # 分析竞价
    st.markdown("---")
    st.header("🔍 竞价分析")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("⚡ 分析竞价", use_container_width=True):
            with st.spinner("正在分析..."):
                # 构建竞价数据
                auction_data = {
                    'price': auction_price,
                    'volume': auction_volume,
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume,
                    'high': auction_high,
                    'low': auction_low,
                    'buy_orders': [
                        {'price': auction_price - 0.1, 'volume': buy_volume * 0.3},
                        {'price': auction_price - 0.2, 'volume': buy_volume * 0.7}
                    ],
                    'sell_orders': [
                        {'price': auction_price + 0.1, 'volume': sell_volume * 0.6},
                        {'price': auction_price + 0.2, 'volume': sell_volume * 0.4}
                    ]
                }
                
                # 构建前一日数据
                prev_data = {
                    'close': prev_close,
                    'volume': prev_volume
                }
                
                result = system.analyze(
                    stock_code=stock_code,
                    auction_data=auction_data,
                    prev_data=prev_data,
                    market_sentiment=market_sentiment
                )
                
                st.session_state.last_auction_result = result
                st.success("分析完成！")
    
    # 显示分析结果
    if 'last_auction_result' in st.session_state:
        result = st.session_state.last_auction_result
        
        with col2:
            st.subheader("📊 分析结果")
            
            # 开盘预测
            opening = result['opening_prediction']
            st.info(f"**开盘价**: {opening['opening_price']['price']:.2f}")
            st.info(f"**开盘走势**: {opening['opening_price']['prediction']}")
            st.info(f"**开盘强度**: {opening['strength']:.2f}")
            st.info(f"**预测置信度**: {opening['confidence']:.2f}")
    
    # 详细分析
    if 'last_auction_result' in st.session_state:
        result = st.session_state.last_auction_result
        
        st.markdown("---")
        st.header("📈 详细分析")
        
        # 开盘预测
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("💰 开盘价预测")
            opening_price = result['opening_prediction']['opening_price']
            st.info(f"**价格**: {opening_price['price']:.2f}")
            st.info(f"**涨跌幅**: {opening_price['change_pct']:.2f}%")
            st.info(f"**走势**: {opening_price['prediction']}")
            
            if opening_price['change_pct'] > 0:
                st.success(f"高开 {opening_price['change_pct']:.2f}%")
            elif opening_price['change_pct'] < 0:
                st.warning(f"低开 {opening_price['change_pct']:.2f}%")
            else:
                st.info("平开")
        
        with col2:
            st.subheader("📊 成交量预测")
            opening_volume = result['opening_prediction']['opening_volume']
            st.info(f"**成交量**: {opening_volume['volume']:,}")
            st.info(f"**倍数**: {opening_volume['surge']:.2f}x")
            st.info(f"**走势**: {opening_volume['prediction']}")
            
            if opening_volume['surge'] > 1.5:
                st.success("放量")
            elif opening_volume['surge'] > 1.0:
                st.info("正常")
            else:
                st.warning("缩量")
        
        with col3:
            st.subheader("⚡ 弱转强识别")
            wts = result['weak_to_strong']
            
            if wts['is_wts']:
                st.success(f"✅ **弱转强**")
                st.info(f"**强度**: {wts['strength']:.2f}")
                st.info(f"**原因**: {wts['reason']}")
            else:
                st.warning(f"⚠️ **无弱转强信号**")
                st.info(f"**原因**: {wts['reason']}")
        
        # 竞价特征
        st.markdown("---")
        st.header("🎯 竞价特征")
        
        features = result['features']
        feature_data = []
        for key, value in features.items():
            feature_data.append({
                '特征': key,
                '数值': f"{value:.4f}" if isinstance(value, float) else value
            })
        
        st.dataframe(
            pd.DataFrame(feature_data),
            use_container_width=True
        )
        
        # 监控预警
        st.markdown("---")
        st.header("⚠️ 监控预警")
        
        monitor_result = result['monitor']
        
        if monitor_result['anomalies']:
            st.error("检测到异常:")
            for anomaly in monitor_result['anomalies']:
                st.error(f"  - {anomaly['type']}: {anomaly['message']}")
        else:
            st.success("✅ 未检测到异常")
        
        if monitor_result['alerts']:
            st.warning("预警信息:")
            for alert in monitor_result['alerts']:
                st.warning(f"  - {alert['type']}: {alert['message']}")
        else:
            st.info("无预警信息")
    
    # 预警历史
    st.markdown("---")
    st.header("📜 预警历史")
    
    alerts = system.get_alerts(limit=20)
    
    if alerts:
        df = pd.DataFrame(alerts)
        df['alert_time'] = pd.to_datetime(df['alert_time'])
        
        st.dataframe(
            df[['stock_code', 'alert_type', 'alert_time', 'details']],
            use_container_width=True
        )
        
        # 预警类型分布
        alert_counts = df['alert_type'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=alert_counts.index,
                values=alert_counts.values,
                hole=0.3
            )
        ])
        
        fig.update_layout(
            title="预警类型分布",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无预警记录")
    
    # 弱转强说明
    st.markdown("---")
    st.header("📋 弱转强识别说明")
    
    wts_info = pd.DataFrame([
        {
            '特征': '价格跳空',
            '说明': '竞价价格高于前收盘价',
            '权重': '30%'
        },
        {
            '特征': '成交量放大',
            '说明': '竞价成交量大于前日成交量的1.5倍',
            '权重': '30%'
        },
        {
            '特征': '买盘主导',
            '说明': '买盘成交量远大于卖盘',
            '权重': '30%'
        },
        {
            '特征': '市场情绪好',
            '说明': '市场情绪得分大于0.3',
            '权重': '10%'
        }
    ])
    
    st.dataframe(wts_info, use_container_width=True)
    
    st.info("💡 当满足多个特征时，弱转强信号更强，建议积极关注")