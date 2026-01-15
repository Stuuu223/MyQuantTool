"""
V7.1 终极展望展示页面

功能：
1. 组合对冲逻辑可视化
2. 闪崩探测器展示
3. 紧急干预信号展示
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, Any

from logic.strategy_orchestrator import StrategyOrchestrator
from logic.monitor import FlashCrashDetector


def render_v71_features_tab(db, config):
    """渲染V7.1新功能标签页"""
    st.subheader("🚀 V7.1 终极展望 - 从猎手进化为军队")
    
    # 初始化模块
    orchestrator = StrategyOrchestrator()
    flash_crash_detector = FlashCrashDetector()
    
    # 创建两个子标签页
    tab1, tab2 = st.tabs([
        "🛡️ 组合对冲逻辑",
        "⚡ 闪崩探测器"
    ])
    
    # Tab 1: 组合对冲逻辑
    with tab1:
        st.markdown("### 🛡️ 组合对冲逻辑 (V7.1)")
        st.markdown("""
        **核心功能**：Beta对冲，平滑波动，降低系统性风险
        
        - **高潮期**：情绪极度高涨，配置20%宽基ETF对冲
        - **行业集中度过高**：单一行业暴露>80%，配置15%防御性板块
        - **退潮期高风险**：配置30%红利低波ETF作为压舱石
        - **主升期集中度较高**：配置10%防御性板块
        """)
        
        # 模拟持仓数据
        st.markdown("#### 📊 当前持仓")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("添加持仓股票：")
            stock_code = st.text_input("股票代码", "300063")
            stock_name = st.text_input("股票名称", "天龙集团")
            stock_sector = st.selectbox(
                "所属板块",
                ["AI", "科技", "医药", "新能源", "芯片", "汽车", "军工", "消费", "软件", "传媒"]
            )
            stock_weight = st.slider("仓位权重", 0.0, 1.0, 0.3, 0.05)
            
            if st.button("➕ 添加持仓"):
                st.success(f"已添加 {stock_name} ({stock_sector})，权重 {stock_weight*100:.1f}%")
        
        with col2:
            st.markdown("#### 📈 持仓分布（模拟）")
            
            # 模拟持仓数据
            sample_positions = [
                {'code': '300063', 'name': '天龙集团', 'sector': 'AI', 'weight': 0.4},
                {'code': '002415', 'name': '海康威视', 'sector': '科技', 'weight': 0.3},
                {'code': '000858', 'name': '五粮液', 'sector': '消费', 'weight': 0.2},
                {'code': '601318', 'name': '中国平安', 'sector': '金融', 'weight': 0.1}
            ]
            
            # 显示持仓表格
            df = pd.DataFrame(sample_positions)
            st.dataframe(df, use_container_width=True)
            
            # 行业暴露饼图
            sector_exposure = {}
            for pos in sample_positions:
                sector = pos['sector']
                weight = pos['weight']
                sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
            
            fig = go.Figure(data=[go.Pie(
                labels=list(sector_exposure.keys()),
                values=list(sector_exposure.values()),
                hole=0.3
            )])
            fig.update_layout(title="行业暴露分布")
            st.plotly_chart(fig, use_container_width=True)
        
        # 市场状态输入
        st.markdown("---")
        st.markdown("#### 🌤️ 市场状态")
        
        col1, col2 = st.columns(2)
        
        with col1:
            market_cycle = st.selectbox(
                "市场周期",
                ["MAIN_RISE", "BOOM", "CHAOS", "ICE", "DECLINE"]
            )
            risk_level = st.slider("风险等级", 1, 5, 3)
        
        with col2:
            st.markdown("#### 📊 行业暴露分析")
            max_sector = max(sector_exposure, key=sector_exposure.get)
            max_exposure = sector_exposure.get(max_sector, 0)
            
            st.metric("最大暴露行业", max_sector)
            st.metric("暴露比例", f"{max_exposure*100:.1f}%")
        
        # 获取对冲建议
        market_status = {
            'cycle': market_cycle,
            'risk_level': risk_level
        }
        
        if st.button("🛡️ 获取对冲建议"):
            hedging_advice = orchestrator.get_hedging_advice(sample_positions, market_status)
            
            # 显示对冲建议
            st.markdown("---")
            st.markdown("#### 🎯 对冲建议")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if hedging_advice['need_hedging']:
                    st.metric("需要对冲", "✅ 是")
                else:
                    st.metric("需要对冲", "❌ 否")
            
            with col2:
                st.metric("对冲类型", hedging_advice['hedging_type'])
            
            with col3:
                st.metric("对冲权重", f"{hedging_advice['hedging_weight']*100:.1f}%")
            
            with col4:
                st.metric("目标数量", str(len(hedging_advice['hedging_targets'])))
            
            # 详细说明
            st.markdown(f"#### 📝 对冲详情")
            st.markdown(f"- **是否需要对冲**: {'是' if hedging_advice['need_hedging'] else '否'}")
            st.markdown(f"- **对冲类型**: {hedging_advice['hedging_type']}")
            st.markdown(f"- **对冲权重**: {hedging_advice['hedging_weight']*100:.1f}%")
            st.markdown(f"- **对冲目标**: {', '.join(hedging_advice['hedging_targets'])}")
            st.markdown(f"- **对冲原因**: {hedging_advice['reason']}")
            
            # 显示行业暴露详情
            st.markdown("#### 📊 行业暴露详情")
            for sector, exposure in hedging_advice.get('sector_exposure', {}).items():
                st.markdown(f"- **{sector}**: {exposure*100:.1f}%")
            
            # 对冲建议可视化
            if hedging_advice['need_hedging']:
                st.success(f"💡 建议: {hedging_advice['reason']}")
                
                # 对冲配置建议
                st.markdown("#### 🎯 对冲配置建议")
                
                if hedging_advice['hedging_type'] == 'ETF':
                    st.markdown("""
                    **宽基ETF配置建议：**
                    - 510300 (沪深300ETF): 平衡配置，降低整体波动
                    - 510500 (中证500ETF): 中小盘对冲，分散风险
                    - 510880 (红利低波ETF): 防御性配置，稳定收益
                    - 159915 (国债ETF): 无风险对冲，保本保值
                    """)
                elif hedging_advice['hedging_type'] == 'SECTOR':
                    st.markdown("""
                    **防御性板块配置建议：**
                    - 512880 (证券ETF): 券商板块，防御性强
                    - 159915 (红利低波ETF): 高分红低波动，压舱石
                    - 银行、电力、公用事业板块: 防御性行业
                    """)
    
    # Tab 2: 闪崩探测器
    with tab2:
        st.markdown("### ⚡ 闪崩探测器 (V7.1)")
        st.markdown("""
        **核心功能**：盘中即时干预，紧急熔断，一键清仓
        
        - **高频监控**：60秒间隔监控市场下跌速率
        - **闪崩阈值**：5分钟内指数下跌 > 1% 或 跌停家数激增 > 20家
        - **紧急清仓**：触发闪崩信号时，立即发出清仓指令
        - **严重程度分级**：LOW / MEDIUM / HIGH 三级预警
        """)
        
        # 闪崩阈值配置
        st.markdown("#### ⚙️ 闪崩阈值配置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            index_drop_threshold = st.slider(
                "指数下跌阈值 (5分钟)",
                0.5, 5.0, 1.0, 0.1,
                help="5分钟内指数下跌超过此百分比时触发闪崩警告"
            )
            limit_down_surge_threshold = st.slider(
                "跌停家数激增阈值",
                10, 50, 20, 5,
                help="跌停家数激增超过此数量时触发闪崩警告"
            )
        
        with col2:
            monitoring_interval = st.slider(
                "监控间隔 (秒)",
                30, 300, 60, 30,
                help="闪崩探测器的监控频率"
            )
        
        # 模拟闪崩数据
        st.markdown("---")
        st.markdown("#### 📊 模拟闪崩信号")
        
        # 模拟指数数据
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("指数数据（模拟）")
            index_drop_rate = st.slider(
                "5分钟内指数下跌 (%)",
                0.0, 5.0, 0.5, 0.1
            )
        
        with col2:
            st.markdown("跌停家数（模拟）")
            limit_down_surge = st.slider(
                "跌停家数激增",
                0, 100, 5, 5
            )
        
        # 判断闪崩信号
        is_flash_crash = False
        severity = "LOW"
        reason = ""
        
        if index_drop_rate >= index_drop_threshold:
            is_flash_crash = True
            reason += f"指数5分钟内下跌{index_drop_rate:.2f}%；"
            
            if index_drop_rate >= 2.0:
                severity = "HIGH"
            elif index_drop_rate >= 1.5:
                severity = "MEDIUM"
        
        if limit_down_surge >= limit_down_surge_threshold:
            is_flash_crash = True
            reason += f"跌停家数激增{limit_down_surge}家；"
            
            if limit_down_surge >= 50:
                severity = "HIGH"
            elif limit_down_surge >= 30:
                severity = "MEDIUM"
        
        # 显示闪崩检测结果
        st.markdown("---")
        st.markdown("#### 🚨 闪崩检测结果")
        
        if is_flash_crash:
            if severity == "HIGH":
                st.error(f"🚨🚨🚨 严重闪崩警告！{reason}")
            elif severity == "MEDIUM":
                st.warning(f"⚠️ 中度闪崩警告！{reason}")
            else:
                st.info(f"📢 轻度闪崩警告！{reason}")
            
            # 紧急操作建议
            st.markdown("#### 🎯 紧急操作建议")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("建议操作", "🔴 一键清仓")
            
            with col2:
                st.metric("预期损失", f"-{index_drop_rate*2:.1f}% 至 -{index_drop_rate*5:.1f}%")
            
            with col3:
                st.metric("恢复时间", "1-3个交易日")
            
            # 清仓按钮
            if st.button("🚨 执行紧急清仓", type="primary"):
                st.error("🚨 已执行紧急清仓操作！")
                st.markdown("""
                **清仓详情：**
                - 已清空所有持仓
                - 已止损所有亏损头寸
                - 已锁定所有盈利头寸
                - 等待市场稳定后再入场
                """)
        else:
            st.success("✅ 当前市场状态正常，未检测到闪崩信号")
            
            st.markdown("""
            **市场监控中...**
            - 指数下跌速率: 正常
            - 跌停家数变化: 正常
            - 市场流动性: 充足
            - 可以继续正常交易
            """)
        
        # 闪崩历史记录
        st.markdown("---")
        st.markdown("#### 📜 闪崩历史记录（模拟）")
        
        # 模拟历史记录
        flash_crash_history = [
            {
                'timestamp': '2024-01-15 14:30:00',
                'severity': 'HIGH',
                'index_drop_rate': 2.5,
                'limit_down_surge': 45,
                'reason': '地缘政治突发利空，指数5分钟内下跌2.5%，跌停家数激增45家'
            },
            {
                'timestamp': '2024-01-10 10:45:00',
                'severity': 'MEDIUM',
                'index_drop_rate': 1.8,
                'limit_down_surge': 25,
                'reason': '科技板块分歧，指数5分钟内下跌1.8%，跌停家数激增25家'
            },
            {
                'timestamp': '2024-01-05 13:20:00',
                'severity': 'LOW',
                'index_drop_rate': 1.2,
                'limit_down_surge': 22,
                'reason': '获利盘回吐，指数5分钟内下跌1.2%，跌停家数激增22家'
            }
        ]
        
        df_history = pd.DataFrame(flash_crash_history)
        st.dataframe(df_history, use_container_width=True)
        
        # 闪崩频率统计
        st.markdown("#### 📊 闪崩频率统计")
        
        severity_counts = df_history['severity'].value_counts()
        
        fig = go.Figure(data=[
            go.Bar(name='HIGH', x=['HIGH'], y=[severity_counts.get('HIGH', 0)], marker_color='red'),
            go.Bar(name='MEDIUM', x=['MEDIUM'], y=[severity_counts.get('MEDIUM', 0)], marker_color='orange'),
            go.Bar(name='LOW', x=['LOW'], y=[severity_counts.get('LOW', 0)], marker_color='yellow')
        ])
        fig.update_layout(
            title='闪崩严重程度分布',
            barmode='group',
            yaxis_title='次数'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 关闭资源
    orchestrator.close()
    flash_crash_detector.close()


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="V7.1 新功能", layout="wide")
    render_v71_features_tab(None, None)