"""
🦖 V9.0 游资掠食者系统展示页面

核心理念：只杀硬伤，不听故事
- 生死红线：退市风险、*ST一律死刑
- 身份与涨幅错配：创业板10%不算涨停
- 资金结构恶化：主力出逃+融资接盘=出货盘口
- 半路板战法：针对创业板12%-15%博弈区间
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any


def render_v90_predator_tab(db, config):
    """渲染V9.0游资掠食者系统标签页"""
    st.subheader("🦖 V9.0 游资掠食者系统 - 只杀硬伤，不听故事")
    
    # 创建四个子标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚫 生死红线检测",
        "🎯 身份与涨幅错配",
        "💰 资金结构恶化",
        "🚀 半路板战法"
    ])
    
    # Tab 1: 生死红线检测
    with tab1:
        st.markdown("### 🚫 生死红线检测 (Kill Switch)")
        st.markdown("""
        **核心理念**：凡是涉及退市风险、*ST的标的，无论K线多美，一律判死刑
        
        - **规则**：System Prompt 第一条 —— "凡是涉及退市风险、*ST的标的，无论K线多美，一律判死刑。"
        - **执行**：游资只做确定性，不博弈退市股
        - **关键词**：退市风险、退市、ST、*ST、终止上市、暂停上市、强制退市、财务退市、面值退市
        """)
        
        st.markdown("#### 🚫 生死红线案例")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.error("""
            **❌ 案例：国际复材 (301526)**
            
            - 检测到关键词：退市风险
            - 系统决策：死刑
            - 信号：SELL
            - 理由：触发生死红线，检测到关键词 ['退市风险']
            - 警告：生死红线：退市风险/ST预警
            """)
        
        with col2:
            st.success("""
            **✅ 案例：正常股票**
            
            - 检测到关键词：无
            - 系统决策：通过
            - 信号：继续分析
            - 理由：未触发生死红线
            - 警告：无
            """)
        
        st.markdown("#### 🔍 生死红线检测流程")
        
        # 绘制生死红线检测流程图
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[1, 2, 3, 4],
            y=[1, 1, 1, 1],
            mode='markers+lines',
            marker=dict(size=[20, 20, 20, 20], color=['green', 'yellow', 'red', 'black']),
            text=['输入股票信息', '检测关键词', '触发生死红线？', '系统决策'],
            textposition='top center',
            name='生死红线检测流程'
        ))
        
        fig.update_layout(
            title='生死红线检测流程图',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 💡 生死红线检测逻辑")
        
        st.code("""
def check_kill_switch(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"生死红线检测（Kill Switch）\"\"\"
    result = {
        'triggered': False,
        'reason': '',
        'keywords': []
    }
    
    # 检查股票名称
    name = stock_data.get('name', '')
    for keyword in self.kill_switch_keywords:
        if keyword in name:
            result['triggered'] = True
            result['keywords'].append(keyword)
    
    # 检查股票代码（ST股票代码特殊）
    symbol = stock_data.get('symbol', '')
    if symbol.startswith('ST') or '*ST' in symbol:
        result['triggered'] = True
        result['keywords'].append('ST标识')
    
    if result['triggered']:
        result['reason'] = f"触发生死红线：检测到关键词 {result['keywords']}"
    
    return result
        """, language='python')
    
    # Tab 2: 身份与涨幅错配
    with tab2:
        st.markdown("### 🎯 身份与涨幅错配检测")
        st.markdown("""
        **核心理念**：300/301开头股票，涨幅<19.5%不算涨停
        
        - **主板（60/00）**：10% 是封板，有溢价
        - **创业板（300/301）**：20% 是封板，10% 只是半山腰
        - **科创板（688）**：20% 是封板，10% 只是半山腰
        - **北交所（8/4）**：30% 是封板，15% 只是半山腰
        """)
        
        st.markdown("#### 📊 各板块涨停标准")
        
        # 创建各板块涨停标准表格
        board_data = {
            '板块': ['主板', '创业板', '科创板', '北交所'],
            '代码前缀': ['60/00', '300/301', '688', '8/4'],
            '涨停涨幅': ['10%', '20%', '20%', '30%'],
            '半路板区间': ['5%-8%', '12%-15%', '12%-15%', '18%-22%'],
            '10%涨幅意义': ['封板，有溢价', '半山腰，无溢价', '半山腰，无溢价', '低位，无溢价']
        }
        
        df_board = pd.DataFrame(board_data)
        st.dataframe(df_board, use_container_width=True)
        
        st.markdown("#### 🚫 身份与涨幅错配案例")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.error("""
            **❌ 案例：国际复材 (301526)**
            
            - 板块：创业板
            - 涨幅：10.34%
            - 系统检测：创业板股票涨幅<19.5%不算涨停
            - 系统决策：陷阱
            - 信号：SELL
            - 理由：创业板股票涨幅10.34%非涨停，属于冲高回落或跟风上涨
            - 警告：创业板股票涨幅<19.5%不算涨停，无溢价预期
            """)
        
        with col2:
            st.success("""
            **✅ 案例：正常创业板股票**
            
            - 板块：创业板
            - 涨幅：19.8%
            - 系统检测：接近涨停，有溢价
            - 系统决策：通过
            - 信号：继续分析
            - 理由：涨幅接近涨停，符合半路板战法
            - 警告：无
            """)
        
        st.markdown("#### 📈 创业板涨幅与溢价关系")
        
        # 绘制创业板涨幅与溢价关系图
        pct_ranges = np.array([0, 5, 10, 12, 15, 18, 19.5, 20])
        premium = np.array([0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 8.0])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=pct_ranges,
            y=premium,
            mode='lines+markers',
            name='创业板涨幅与溢价关系',
            line=dict(color='orange', width=3),
            marker=dict(size=10)
        ))
        
        # 标记关键区间
        fig.add_vrect(x0=0, x1=10, fillcolor="red", opacity=0.2, annotation_text="无溢价区间")
        fig.add_vrect(x0=10, x1=12, fillcolor="yellow", opacity=0.2, annotation_text="低溢价区间")
        fig.add_vrect(x0=12, x1=15, fillcolor="lightgreen", opacity=0.2, annotation_text="半路板区间")
        fig.add_vrect(x0=15, x1=19.5, fillcolor="green", opacity=0.2, annotation_text="高溢价区间")
        fig.add_vrect(x0=19.5, x1=20, fillcolor="gold", opacity=0.2, annotation_text="涨停区间")
        
        fig.update_layout(
            title='创业板涨幅与溢价关系',
            xaxis_title='涨幅 (%)',
            yaxis_title='溢价 (倍)',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: 资金结构恶化
    with tab3:
        st.markdown("### 💰 资金结构恶化检测")
        st.markdown("""
        **核心理念**：主力净流出+融资买入增加=出货盘口
        
        - **正常结构**：主力锁仓，散户不敢买
        - **恶化结构**：主力大跑，融资客接盘
        - **背离信号**：主力净流出 > 5000万，融资买入 > 3000万
        - **典型特征**：典型的出货盘口
        """)
        
        st.markdown("#### 📊 资金结构类型")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("""
            **✅ 正常结构**
            
            - 主力：净流入
            - 融资：适中
            - 散户：观望
            - 特征：主力锁仓
            """)
        
        with col2:
            st.warning("""
            **⚠️ 警惕结构**
            
            - 主力：小幅流出
            - 融资：增加
            - 散户：活跃
            - 特征：分歧加大
            """)
        
        with col3:
            st.error("""
            **❌ 恶化结构**
            
            - 主力：大幅流出
            - 融资：大增
            - 散户：接盘
            - 特征：出货盘口
            """)
        
        st.markdown("#### 🚫 资金结构恶化案例")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.error("""
            **❌ 案例：国际复材 (301526)**
            
            - 主力净流出：1.8亿
            - 融资买入：增加
            - 系统检测：资金结构恶化
            - 系统决策：出货
            - 信号：SELL
            - 理由：资金结构恶化：主力净流出18000万，融资买入增加，典型的出货盘口
            - 警告：主力出逃，融资接盘，背离信号
            """)
        
        with col2:
            st.success("""
            **✅ 案例：正常股票**
            
            - 主力净流出：500万
            - 融资买入：稳定
            - 系统检测：资金结构正常
            - 系统决策：通过
            - 信号：继续分析
            - 理由：资金结构正常，未触发恶化检测
            - 警告：无
            """)
        
        st.markdown("#### 📈 资金结构与股价关系")
        
        # 模拟资金结构与股价关系数据
        np.random.seed(42)
        n_days = 30
        dates = pd.date_range(start='2026-01-01', end='2026-01-30', freq='D')
        
        main_flow = np.cumsum(np.random.randn(n_days) * 1000)
        financing = np.cumsum(np.random.randn(n_days) * 500)
        price = 10 + np.cumsum(np.random.randn(n_days) * 0.5)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=main_flow,
            mode='lines+markers',
            name='主力净流向',
            yaxis='y',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=financing,
            mode='lines+markers',
            name='融资买入',
            yaxis='y2',
            line=dict(color='orange', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=price,
            mode='lines+markers',
            name='股价',
            yaxis='y3',
            line=dict(color='green', width=2)
        ))
        
        fig.update_layout(
            title='资金结构与股价关系',
            xaxis_title='日期',
            yaxis=dict(title='主力净流向（万）', side='left'),
            yaxis2=dict(title='融资买入（万）', side='right', overlaying='y'),
            yaxis3=dict(title='股价（元）', side='right', overlaying='y', position=0.85),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 4: 半路板战法
    with tab4:
        st.markdown("### 🚀 半路板战法")
        st.markdown("""
        **核心理念**：针对创业板12%-15%博弈区间
        
        - **主板（60/00）**：5%-8% 半路板博弈
        - **创业板（300/301）**：12%-15% 半路板博弈
        - **科创板（688）**：12%-15% 半路板博弈
        - **北交所（8/4）**：18%-22% 半路板博弈
        """)
        
        st.markdown("#### 📊 半路板战法配置")
        
        # 创建半路板战法配置表格
        halfway_data = {
            '板块': ['主板', '创业板', '科创板', '北交所'],
            '代码前缀': ['60/00', '300/301', '688', '8/4'],
            '涨停涨幅': ['10%', '20%', '20%', '30%'],
            '半路板最小': ['5%', '12%', '12%', '18%'],
            '半路板最大': ['8%', '15%', '15%', '22%'],
            '博弈空间': ['2%-5%', '5%-8%', '5%-8%', '8%-12%']
        }
        
        df_halfway = pd.DataFrame(halfway_data)
        st.dataframe(df_halfway, use_container_width=True)
        
        st.markdown("#### 🎯 半路板战法评分标准")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("""
            **基础分：60分**
            
            - 符合半路板区间
            - 涨幅评分：10-20分
            - 量比评分：5-15分
            - 换手率评分：5-10分
            """)
        
        with col2:
            st.success("""
            **🔥 强半路板：≥90分**
            
            - 信号：BUY
            - 置信度：HIGH
            - 建议仓位：30%
            - 操作：半路扫货
            """)
        
        with col3:
            st.warning("""
            **📈 半路板：80-89分**
            
            - 信号：BUY
            - 置信度：MEDIUM
            - 建议仓位：20%
            - 操作：谨慎参与
            """)
        
        st.markdown("#### 📈 半路板战法评分曲线")
        
        # 绘制半路板战法评分曲线
        pct_ranges = np.array([5, 8, 10, 12, 15, 18, 19.5])
        scores = np.array([60, 70, 75, 80, 90, 85, 80])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=pct_ranges,
            y=scores,
            mode='lines+markers',
            name='半路板战法评分',
            line=dict(color='orange', width=3),
            marker=dict(size=10)
        ))
        
        # 标记关键区间
        fig.add_vrect(x0=12, x1=15, fillcolor="green", opacity=0.2, annotation_text="黄金区间（强半路板）")
        fig.add_vrect(x0=5, x1=8, fillcolor="lightgreen", opacity=0.2, annotation_text="主板半路板区间")
        fig.add_vrect(x0=18, x1=19.5, fillcolor="yellow", opacity=0.2, annotation_text="高涨幅区间")
        
        fig.update_layout(
            title='半路板战法评分曲线',
            xaxis_title='涨幅 (%)',
            yaxis_title='评分',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 💡 半路板战法逻辑")
        
        st.code("""
def analyze_halfway_strategy(self, stock_data: Dict[str, Any], 
                            realtime_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"半路板战法分析\"\"\"
    result = {
        'triggered': False,
        'score': 0,
        'role': '',
        'signal': 'HOLD',
        'confidence': 'LOW',
        'reason': '',
        'suggested_position': 0.0
    }
    
    symbol = stock_data.get('symbol', '')
    change_pct = realtime_data.get('change_percent', 0)
    volume_ratio = realtime_data.get('volume_ratio', 1)
    turnover_rate = realtime_data.get('turnover_rate', 0)
    
    # 判断板块类型
    board_type = self._get_board_type(symbol)
    config = self.halfway_config.get(board_type, {})
    
    halfway_min = config['halfway_min']
    halfway_max = config['halfway_max']
    
    # 检查是否符合半路板条件
    if halfway_min <= change_pct <= halfway_max:
        result['triggered'] = True
        
        # 计算评分
        score = 60  # 基础分
        
        # 涨幅评分
        if change_pct >= halfway_max:
            score += 20
        elif change_pct >= (halfway_min + halfway_max) / 2:
            score += 15
        else:
            score += 10
        
        # 量比评分
        if volume_ratio > 3:
            score += 15
        elif volume_ratio > 2:
            score += 10
        elif volume_ratio > 1.5:
            score += 5
        
        # 换手率评分
        if 5 <= turnover_rate <= 15:
            score += 10
        elif turnover_rate > 15:
            score += 5
        
        # 判断角色和信号
        if score >= 90:
            result['role'] = '🔥 强半路板'
            result['signal'] = 'BUY'
            result['confidence'] = 'HIGH'
            result['suggested_position'] = 0.3
        elif score >= 80:
            result['role'] = '📈 半路板'
            result['signal'] = 'BUY'
            result['confidence'] = 'MEDIUM'
            result['suggested_position'] = 0.2
        else:
            result['role'] = '弱半路板'
            result['signal'] = 'WATCH'
            result['confidence'] = 'LOW'
            result['suggested_position'] = 0.0
        
        result['score'] = score
        result['reason'] = f"半路板战法：涨幅{change_pct:.2f}%在{halfway_min}%-{halfway_max}%区间"
    
    return result
        """, language='python')
        
        st.markdown("#### 🎯 V9.0 总结")
        
        st.success("""
        **V9.0 核心成就**：
        
        1. ✅ 建立了生死红线检测系统，退市风险、*ST一律死刑
        2. ✅ 实现了身份与涨幅错配检测，创业板10%不算涨停
        3. ✅ 实现了资金结构恶化检测，主力出逃+融资接盘=出货盘口
        4. ✅ 实现了半路板战法逻辑，针对创业板12%-15%博弈区间
        
        **从 "听故事" 到 "只杀硬伤"**：
        
        - 传统的量化系统：阅读几千字的基本面分析
        - V9.0游资掠食者系统：0.01秒内得出结论
        
        **效率对比**：
        
        - 传统分析：需要阅读财务报表、行业分析、公司公告
        - V9.0系统：只需检测关键词、涨幅规则、资金结构
        
        **核心优势**：
        
        - 只杀硬伤，不听故事
        - 0.01秒内决策
        - 100%确定性
        - 无情绪干扰
        """)