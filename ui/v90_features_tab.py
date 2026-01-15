"""
V9.0 日内弱转强探测器展示页面

功能：
1. 日内弱转强检测逻辑展示
2. 神思电子案例复盘
3. 弱转强触发条件可视化
4. StrategyOrchestrator修正评分展示
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, Any, List


def render_v90_features_tab(db, config):
    """渲染V9.0新功能标签页"""
    st.subheader("🔄 V9.0 日内弱转强探测器 - 捕捉神思电子式的机会")
    
    # 创建四个子标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "💡 核心逻辑",
        "📊 神思电子案例",
        "🎯 触发条件",
        "⚖️ StrategyOrchestrator修正"
    ])
    
    # Tab 1: 核心逻辑
    with tab1:
        st.markdown("### 💡 日内弱转强探测器核心逻辑 (V9.0)")
        st.markdown("""
        **核心目标**：捕捉"竞价弱但开盘后承接强"的机会（如神思电子案例）
        
        **哲学思考**：
        - 系统是为了抓大概率的确定性，而不是抓小概率的幸存者
        - 神思电子涨停是市场的胜利，没买到是纪律的胜利
        - 宁可错过，绝不做错
        - 但系统可以变得更聪明，去捕捉这种"日内弱转强"的机会
        
        **核心逻辑**：
        1. **前提条件**：竞价弱（成交少）
           - 竞价金额 < 500万
           - 竞价抢筹度 < 2%
        
        2. **触发条件**：
           - **条件1**：开盘5分钟内，股价不跌破开盘价（承接强）
           - **条件2**：5分钟内的成交量迅速放大，超过竞价成交量的5-10倍（主力进场换手）
           - **条件3**：必须有主线板块效应（ThemeDetector确认是今日主线）
        
        3. **执行**：
           - 当上述3点同时满足时，允许"修正竞价评分"，发出"半路追涨"信号
           - 修正评分：+20~+50分（根据承接强度、成交量放大倍数、主线热度计算）
        
        **核心价值**：
        - **提高捕捉能力**：捕捉竞价弱但开盘后承接强的机会
        - **保持风控**：依然严格执行一票否决机制
        - **动态修正**：根据日内表现修正竞价评分
        - **模式内操作**：只捕捉符合模式内的机会
        """)
        
        st.markdown("#### 🔄 日内弱转强vs传统竞价筛选")
        
        comparison_table = pd.DataFrame({
            '维度': ['竞价数据', '开盘后数据', '主线板块效应', '决策时机', '信号类型', '风险等级'],
            '传统竞价筛选': [
                '仅看竞价',
                '不看',
                '不考虑',
                '9:25集合竞价',
                'BUY_AGGRESSIVE / REJECT',
                '高（可能误判）'
            ],
            '日内弱转强探测器': [
                '看竞价弱',
                '看开盘5分钟承接',
                '必须主线效应',
                '9:35开盘后',
                'HALFTIME_BUY（半路追涨）',
                '低（多重确认）'
            ]
        })
        
        st.dataframe(comparison_table, use_container_width=True)
        
        st.markdown("#### 🎯 适用场景")
        
        scenarios = pd.DataFrame({
            '场景': ['弱转强', '跟风股', '主线溢出', '日内分歧转一致'],
            '描述': [
                '竞价弱但开盘后承接强',
                '主线龙一封死后，资金挖掘龙二龙三',
                '主线板块太强，资金买不到龙一',
                '早上分歧，开盘后资金发现跌不下去，合力推升'
            ],
            '案例': [
                '神思电子（300479）',
                '低空经济跟风股',
                'AI板块溢出',
                '神思电子'
            ],
            '捕捉能力': [
                '✅ 强',
                '✅ 强',
                '✅ 强',
                '✅ 强'
            ]
        })
        
        st.dataframe(scenarios, use_container_width=True)
    
    # Tab 2: 神思电子案例
    with tab2:
        st.markdown("### 📊 神思电子案例复盘 (V9.0)")
        st.markdown("""
        **案例背景**：神思电子(300479)竞价弱但开盘后承接强，最终封死20cm涨停
        
        **核心数据**：
        - 竞价量：449手（104万）← 竞价弱
        - 竞价抢筹度：1.12% ← 竞价弱
        - 开盘涨幅：12.83% ← 高开
        - 开盘后承接：不跌破开盘价 ← 承接强
        - 成交量放大：5分钟内成交量放大8倍 ← 主力进场
        - 主线板块：低空经济 ← 主线效应
        
        **系统决策**：
        - V8.1系统：REJECT（流动性陷阱、杂毛股）
        - V9.0系统：HALFTIME_BUY（日内弱转强，修正评分+35分）
        """)
        
        st.markdown("#### 📊 神思电子竞价vs开盘后对比")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🔴 竞价阶段（9:25）")
            st.error("""
            **竞价数据**：
            - 竞价量：449手
            - 竞价金额：104万 ❌ <500万
            - 竞价抢筹度：1.12% ❌ <2%
            - 开盘涨幅：12.83% ✅ 高开
            
            **V8.1系统判定**：
            - 流动性陷阱：⚠️ 是
            - 真龙类型：🐛 杂毛
            - 决策：🚫 REJECT
            - 原因：缩量拉升，大资金进出困难
            """)
        
        with col2:
            st.markdown("##### 🟢 开盘后阶段（9:30-9:35）")
            st.success("""
            **开盘后数据**：
            - 最低价：23.31元 ✅ 未跌破开盘价
            - 承接强度：100% ✅ 完全承接
            - 5分钟成交量：约4000手 ✅ 放大8倍
            - 主线板块：低空经济 ✅ 主线热度75
            
            **V9.0系统判定**：
            - 承接强：✅ 是
            - 成交量放大：✅ 是（8倍）
            - 主线效应：✅ 是
            - 修正评分：+35分
            - 决策：✅ HALFTIME_BUY
            - 原因：日内弱转强确认
            """)
        
        st.markdown("#### 📈 神思电子分时走势模拟")
        
        # 模拟神思电子分时数据
        time_data = ['9:25', '9:30', '9:31', '9:32', '9:33', '9:34', '9:35', '9:40', '9:45', '10:00']
        price_data = [23.31, 23.31, 23.35, 23.40, 23.45, 23.50, 23.55, 23.80, 24.20, 25.00]
        volume_data = [449, 1000, 1500, 2000, 2500, 3000, 4000, 8000, 12000, 15000]
        
        fig = go.Figure()
        
        # 添加价格线
        fig.add_trace(go.Scatter(
            x=time_data,
            y=price_data,
            mode='lines+markers',
            name='价格',
            line=dict(color='blue', width=2),
            yaxis='y'
        ))
        
        # 添加成交量柱状图
        fig.add_trace(go.Bar(
            x=time_data,
            y=volume_data,
            name='成交量',
            marker_color='orange',
            yaxis='y2'
        ))
        
        # 添加开盘价线
        fig.add_hline(
            y=23.31,
            line_dash="dash",
            line_color="green",
            annotation_text="开盘价",
            yref='y'
        )
        
        # 添加触发时间线
        fig.add_vline(
            x=2,
            line_dash="dash",
            line_color="red",
            annotation_text="9:32触发弱转强"
        )
        
        fig.update_layout(
            title='神思电子分时走势模拟',
            xaxis_title='时间',
            yaxis_title='价格（元）',
            yaxis2=dict(
                title='成交量（手）',
                overlaying='y',
                side='right'
            ),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 💡 关键时间点解读")
        
        key_points = pd.DataFrame({
            '时间': ['9:25', '9:30', '9:31', '9:32', '9:35', '10:00'],
            '事件': ['集合竞价', '开盘', '承接确认', '弱转强触发', '强势拉升', '封板'],
            '价格': ['23.31元', '23.31元', '23.35元', '23.40元', '23.55元', '25.00元'],
            '成交量': ['449手', '1000手', '1500手', '2000手', '4000手', '15000手'],
            '系统判定': [
                'V8.1: REJECT（流动性陷阱）',
                '观察承接',
                '承接确认（未跌破开盘价）',
                'V9.0: HALFTIME_BUY（弱转强）',
                '强势拉升',
                '封板'
            ],
            '操作建议': [
                '❌ 不买',
                '⚠️ 观察',
                '⚠️ 观察',
                '✅ 半路追涨',
                '✅ 持有',
                '✅ 持有'
            ]
        })
        
        st.dataframe(key_points, use_container_width=True)
        
        st.markdown("""
        **教训总结**：
        1. **不要被竞价迷惑**：竞价弱不代表一定不行，要看开盘后承接
        2. **不要被涨幅迷惑**：涨幅12.83%看似很强，但流动性不足
        3. **要看承接强度**：开盘后5分钟内不跌破开盘价，说明承接强
        4. **要看成交量放大**：5分钟内成交量放大8倍，说明主力进场
        5. **要看主线效应**：低空经济主线热度75，说明资金在主线内挖掘
        6. **要相信系统**：V9.0系统会捕捉这种弱转强机会
        """)
    
    # Tab 3: 触发条件
    with tab3:
        st.markdown("### 🎯 日内弱转强触发条件 (V9.0)")
        st.markdown("""
        **触发条件**：
        1. **前提条件**：竞价弱（成交少）
           - 竞价金额 < 500万
           - 竞价抢筹度 < 2%
        
        2. **条件1**：开盘5分钟内，股价不跌破开盘价（承接强）
           - 最低价 >= 开盘价 * 99.5%
           - 允许小幅波动（0.5%）
        
        3. **条件2**：5分钟内的成交量迅速放大，超过竞价成交量的5-10倍（主力进场换手）
           - 5分钟成交量 / 竞价量 >= 5倍
           - 5分钟成交量 / 竞价量 <= 10倍（避免过度放大诱多）
        
        4. **条件3**：必须有主线板块效应（ThemeDetector确认是今日主线）
           - 主线热度 > 60
           - 股票属于主线板块
        """)
        
        st.markdown("#### 📊 触发条件详细说明")
        
        conditions = pd.DataFrame({
            '条件': ['竞价弱', '承接强', '成交量放大', '主线效应'],
            '参数': [
                '竞价金额<500万 或 竞价抢筹度<2%',
                '最低价>=开盘价*99.5%',
                '5分钟成交量/竞价量>=5倍 且 <=10倍',
                '主线热度>60 且 股票属于主线板块'
            ],
            '神思电子': [
                '104万<500万 ✅',
                '23.31>=23.31*99.5% ✅',
                '4000/449=8.9倍 ✅',
                '热度75>60 ✅'
            ],
            '判定': ['✅ 满足', '✅ 满足', '✅ 满足', '✅ 满足'],
            '权重': ['前提条件', '30%', '30%', '40%']
        })
        
        st.dataframe(conditions, use_container_width=True)
        
        st.markdown("#### 🔍 触发条件检测逻辑")
        st.code("""
def detect_turnaround(symbol, auction_data, intraday_data, main_theme, theme_heat):
    \"\"\"
    检测日内弱转强
    
    Args:
        symbol: 股票代码
        auction_data: 竞价数据
            {
                'auction_amount': float,  # 竞价金额（万元）
                'auction_ratio': float,  # 竞价抢筹度
                'auction_volume': float,  # 竞价量（手）
                'open_price': float,  # 开盘价
            }
        intraday_data: 日内数据（开盘后5分钟的分时数据）
        main_theme: 主线板块名称
        theme_heat: 主线热度
    
    Returns:
        tuple: (是否弱转强, 原因, 修正评分)
    \"\"\"
    
    # 1. 检查前提条件：竞价弱
    if auction_data['auction_amount'] >= 500 and auction_data['auction_ratio'] >= 0.02:
        return False, "竞价不弱，不触发弱转强检测", 0.0
    
    # 2. 检查条件1：开盘5分钟内，股价不跌破开盘价（承接强）
    early_data = intraday_data.head(5)
    min_price = early_data['price'].min()
    if min_price < auction_data['open_price'] * 0.995:
        return False, "承接弱，跌破开盘价", 0.0
    
    # 3. 检查条件2：5分钟内的成交量迅速放大
    intraday_volume = early_data['volume'].sum()
    surge_ratio = intraday_volume / auction_data['auction_volume']
    if surge_ratio < 5 or surge_ratio > 10:
        return False, f"成交量放大不足或过度（{surge_ratio:.1f}倍）", 0.0
    
    # 4. 检查条件3：必须有主线板块效应
    if theme_heat < 60:
        return False, f"主线热度不足（{theme_heat:.0f}）", 0.0
    
    # 5. 所有条件满足，确认弱转强
    turnaround_score = calculate_turnaround_score(auction_data, intraday_data, theme_heat)
    reason = f"✅ 日内弱转强确认：竞价弱，承接强，成交量放大{surge_ratio:.1f}倍，主线效应强"
    
    return True, reason, turnaround_score
        """, language='python')
        
        st.markdown("#### 📈 触发条件可视化")
        
        # 模拟多只股票的触发条件数据
        np.random.seed(44)
        n_stocks = 20
        auction_amounts = np.random.uniform(100, 800, n_stocks)
        auction_ratios = np.random.uniform(0.5, 3.0, n_stocks)
        support_ratios = np.random.uniform(0.98, 1.02, n_stocks)
        surge_ratios = np.random.uniform(2, 12, n_stocks)
        theme_heats = np.random.uniform(40, 90, n_stocks)
        
        # 标记触发状态
        trigger_status = []
        for i in range(n_stocks):
            if auction_amounts[i] < 500 or auction_ratios[i] < 2:
                if support_ratios[i] >= 0.995 and 5 <= surge_ratios[i] <= 10 and theme_heats[i] > 60:
                    trigger_status.append('✅ 触发')
                else:
                    trigger_status.append('❌ 未触发')
            else:
                trigger_status.append('❌ 竞价不弱')
        
        df_trigger = pd.DataFrame({
            '股票': [f'股票{i+1}' for i in range(n_stocks)],
            '竞价金额': auction_amounts,
            '竞价抢筹度': auction_ratios,
            '承接强度': support_ratios,
            '成交量放大倍数': surge_ratios,
            '主线热度': theme_heats,
            '触发状态': trigger_status
        })
        
        st.dataframe(df_trigger, use_container_width=True)
        
        # 触发条件散点图
        st.markdown("#### 📊 承接强度vs成交量放大倍数散点图")
        
        df_scatter = pd.DataFrame({
            '承接强度': support_ratios,
            '成交量放大倍数': surge_ratios,
            '触发状态': trigger_status
        })
        
        fig = px.scatter(
            df_scatter,
            x='承接强度',
            y='成交量放大倍数',
            color='触发状态',
            title='承接强度vs成交量放大倍数（触发弱转强）',
            color_discrete_map={
                '✅ 触发': 'green',
                '❌ 未触发': 'red',
                '❌ 竞价不弱': 'gray'
            }
        )
        
        # 添加阈值线
        fig.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="5倍")
        fig.add_hline(y=10, line_dash="dash", line_color="orange", annotation_text="10倍")
        fig.add_vline(x=0.995, line_dash="dash", line_color="blue", annotation_text="99.5%")
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        **解读**：
        - **绿色区域**（承接强度>=99.5% 且 成交量放大5-10倍）：触发弱转强
        - **红色区域**：未触发（承接弱或成交量放大不足/过度）
        - **灰色区域**：竞价不弱，不触发检测
        """)
    
    # Tab 4: StrategyOrchestrator修正
    with tab4:
        st.markdown("### ⚖️ StrategyOrchestrator修正评分 (V9.0)")
        st.markdown("""
        **核心功能**：在StrategyOrchestrator中集成日内弱转强检测，修正竞价评分
        
        **修正逻辑**：
        1. 在一票否决权检查之后，加权打分之前，添加日内弱转强检测
        2. 如果检测到日内弱转强，修正评分：+20~+50分
        3. 修正后的评分用于最终决策
        
        **修正评分计算**：
        - 基础分：20分
        - 开盘涨幅加分：高开>10%加10分，>5%加5分
        - 主线热度加分：热度>80加10分，>60加5分
        - 承接强度加分：完全承接加10分，基本承接加5分
        - 成交量放大加分：放大>=8倍加10分，>=5倍加5分
        """)
        
        st.markdown("#### 🔄 StrategyOrchestrator决策流程（V9.0）")
        
        st.markdown("""
        ```
        开始
          ↓
        检查一票否决
          ↓
        ├─ ST股？ → 是 → 🚫 否决
        ├─ 退潮期？ → 是 → 反核模式？ → 否 → 🚫 否决
        ├─ 高潮期？ → 是 → 涨停板？ → 是 → 🚫 否决
        ├─ 流动性陷阱？ → 是 → 🚫 否决
        ├─ 杂毛股？ → 是 → 🚫 否决
        └─ 弱跟风？ → 是 → 🚫 否决
          ↓
        通过一票否决检查
          ↓
        🆕 V9.0: 检测日内弱转强
          ↓
        ├─ 竞价弱？ → 否 → 跳过
        ├─ 承接强？ → 否 → 跳过
        ├─ 成交量放大？ → 否 → 跳过
        └─ 主线效应？ → 否 → 跳过
          ↓
        🆕 V9.0: 应用修正评分（+20~+50分）
          ↓
        加权打分
          ↓
        输出决策（BUY/SELL/WAIT/REJECT）
        ```
        """)
        
        st.markdown("#### 📊 修正评分计算示例")
        
        score_examples = pd.DataFrame({
            '场景': ['神思电子', '案例1', '案例2', '案例3'],
            '基础分': [20, 20, 20, 20],
            '开盘涨幅加分': [10, 5, 10, 5],
            '主线热度加分': [5, 10, 10, 5],
            '承接强度加分': [10, 10, 5, 5],
            '成交量放大加分': [10, 10, 5, 5],
            '修正评分': [35, 35, 25, 15],
            '原始评分': [50, 45, 40, 35],
            '修正后评分': [85, 80, 65, 50],
            '决策': ['BUY', 'BUY', 'BUY', 'WAIT']
        })
        
        st.dataframe(score_examples, use_container_width=True)
        
        st.markdown("#### 💡 修正评分的影响")
        
        impact_analysis = pd.DataFrame({
            '原始评分': ['<40分', '40-60分', '60-80分', '>=80分'],
            '原始决策': ['REJECT', 'WAIT', 'BUY（轻仓）', 'BUY'],
            '修正+20分': ['WAIT', 'BUY（轻仓）', 'BUY', 'BUY'],
            '修正+35分': ['BUY（轻仓）', 'BUY', 'BUY', 'BUY'],
            '修正+50分': ['BUY', 'BUY', 'BUY', 'BUY'],
            '说明': [
                '修正后可能从REJECT变为WAIT或BUY',
                '修正后可能从WAIT变为BUY',
                '修正后可能从轻仓变为正常仓位',
                '修正后保持BUY，但信心更强'
            ]
        })
        
        st.dataframe(impact_analysis, use_container_width=True)
        
        st.markdown("#### 🎯 修正评分的边界情况")
        
        edge_cases = pd.DataFrame({
            '情况': ['竞价不弱', '承接弱', '成交量放大不足', '成交量过度放大', '主线热度不足'],
            '描述': [
                '竞价金额>=500万 且 竞价抢筹度>=2%',
                '最低价<开盘价*99.5%',
                '5分钟成交量/竞价量<5倍',
                '5分钟成交量/竞价量>10倍',
                '主线热度<=60'
            ],
            '是否检测': ['❌ 否', '✅ 是', '✅ 是', '✅ 是', '✅ 是'],
            '是否触发': ['❌ 否', '❌ 否', '❌ 否', '❌ 否', '❌ 否'],
            '修正评分': ['0分', '0分', '0分', '0分', '0分'],
            '原因': [
                '竞价不弱，不触发弱转强检测',
                '承接弱，不触发',
                '成交量放大不足，不触发',
                '成交量过度放大，可能是诱多',
                '主线热度不足，不触发'
            ]
        })
        
        st.dataframe(edge_cases, use_container_width=True)
        
        st.markdown("""
        **核心价值**：
        - **提高捕捉能力**：捕捉竞价弱但开盘后承接强的机会
        - **保持风控**：依然严格执行一票否决机制
        - **动态修正**：根据日内表现修正竞价评分
        - **模式内操作**：只捕捉符合模式内的机会
        - **避免踏空**：减少因竞价弱而错过真龙的机会
        
        **注意事项**：
        - 修正评分只在特定条件下触发（竞价弱、承接强、成交量放大、主线效应）
        - 修正评分的幅度有限（+20~+50分），不会过度提高风险
        - 修正评分不会影响一票否决机制
        - 修正评分只在主升期或高潮期生效
        """)
    
    # 总结
    st.markdown("---")
    st.markdown("### 📝 V9.0 总结")
    st.markdown("""
    **核心改进**：
    
    1. **IntradayTurnaroundDetector（日内弱转强探测器）**
       - 检测竞价弱但开盘后承接强的股票
       - 捕捉"日内弱转强"机会（如神思电子案例）
       - 修正评分：+20~+50分
    
    2. **StrategyOrchestrator集成**
       - 在一票否决权检查之后，加权打分之前，添加日内弱转强检测
       - 应用修正评分
    
    3. **algo.py优化**
       - 添加日内弱转强相关字段
       - 支持StrategyOrchestrator的弱转强检测
    
    4. **UI集成（V9.0特征页）**
       - Tab 1：核心逻辑
       - Tab 2：神思电子案例
       - Tab 3：触发条件
       - Tab 4：StrategyOrchestrator修正
    
    **核心价值**：
    - 提高捕捉能力：捕捉竞价弱但开盘后承接强的机会
    - 保持风控：依然严格执行一票否决机制
    - 动态修正：根据日内表现修正竞价评分
    - 模式内操作：只捕捉符合模式内的机会
    - 避免踏空：减少因竞价弱而错过真龙的机会
    
    **哲学思考**：
    - 系统是为了抓大概率的确定性，而不是抓小概率的幸存者
    - 神思电子涨停是市场的胜利，没买到是纪律的胜利
    - 宁可错过，绝不做错
    - 但系统可以变得更聪明，去捕捉这种"日内弱转强"的机会
    """)