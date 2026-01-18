#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V15.1 动态离场系统 (Dynamic Exit System) UI 模块
展示三级火箭防守逻辑，保护浮盈，锁定利润，炸板逃逸
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from logic.position_manager import PositionManager
from logic.logger import get_logger

logger = get_logger(__name__)


def render_dynamic_exit(data_manager=None):
    """
    渲染动态离场系统展示面板

    Args:
        data_manager: 数据管理器实例（可选）
    """
    st.subheader("🛡️ V15.1 动态离场系统 (The Reaper)")

    st.markdown("""
    **V15.1 核心变革**：
    - ❌ V15.0: 固定止损线（-8%）
    - ✅ V15.1: 动态止损，三级火箭防守
    
    **三级防守**：
    - 🛡️ 一级防守：浮盈 > 3% → 止损线 = 成本价 + 0.5%（保本单）
    - 🔒 二级防守：最高浮盈 > 7% → 止损线 = 最高价 * 0.97（回撤锁定）
    - 🚨 三级防守：炸板 2% → 强制卖出（炸板逃逸）
    """)

    # 侧边栏配置
    with st.sidebar:
        st.markdown("### ⚙️ 测试配置")
        
        stock_code = st.text_input("股票代码", value="603056", help="例如：603056", key="dynamic_exit_stock_code")
        
        # 模拟数据输入
        st.markdown("#### 📊 持仓数据")
        
        cost_price = st.number_input(
            "成本价",
            min_value=0.0,
            max_value=1000.0,
            value=10.00,
            step=0.01,
            help="买入成本价"
        )
        
        current_price = st.number_input(
            "当前价格",
            min_value=0.0,
            max_value=1000.0,
            value=10.20,
            step=0.01,
            help="当前市场价格"
        )
        
        highest_price = st.number_input(
            "持仓期间最高价",
            min_value=0.0,
            max_value=1000.0,
            value=10.80,
            step=0.01,
            help="持仓期间达到的最高价"
        )
        
        st.markdown("#### 🎯 涨停信息")
        
        is_limit_up = st.checkbox(
            "是否曾封涨停",
            value=False,
            help="如果曾封涨停，将启用三级防守"
        )
        
        limit_up_price = st.number_input(
            "涨停价",
            min_value=0.0,
            max_value=1000.0,
            value=11.00,
            step=0.01,
            help="涨停价格，用于判断炸板"
        )
        
        st.markdown("---")
        st.markdown("### 💡 三级防守说明")
        st.info("""
        **V15.1 三级火箭防守**：
        
        **一级防守：成本保护**
        - 条件：浮盈 > 3%
        - 止损线：成本价 + 0.5%
        - 口诀：赚了钱的单子，绝不允许变成亏损走
        
        **二级防守：回撤锁定**
        - 条件：最高浮盈 > 7%（但未涨停）
        - 止损线：最高价 * 0.97
        - 口诀：吃不到鱼头，但要保住鱼身
        
        **三级防守：炸板逃逸**
        - 条件：曾涨停 + 炸板 2%
        - 动作：强制市价卖出
        - 口诀：涨停板是用来封的，不是用来给你画饼的
        """)

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔍 开始动态止损分析")

        if st.button("🚀 运行 V15.1 分析", type="primary"):
            with st.spinner("正在运行动态止损分析..."):
                try:
                    # 创建仓位管理器
                    pm = PositionManager(account_value=100000)
                    
                    # 计算动态止损
                    result = pm.calculate_dynamic_stop_loss(
                        current_price=current_price,
                        cost_price=cost_price,
                        highest_price=highest_price,
                        is_limit_up=is_limit_up,
                        limit_up_price=limit_up_price
                    )
                    
                    # 检查是否触发止损
                    exit_signal = pm.check_position_exit_signal(
                        stock_code=stock_code,
                        current_price=current_price,
                        cost_price=cost_price,
                        highest_price=highest_price,
                        is_limit_up=is_limit_up,
                        limit_up_price=limit_up_price
                    )
                    
                    # 保存到 session state
                    st.session_state['v15_1_result'] = result
                    st.session_state['v15_1_exit_signal'] = exit_signal
                    st.session_state['input_params'] = {
                        'stock_code': stock_code,
                        'cost_price': cost_price,
                        'current_price': current_price,
                        'highest_price': highest_price,
                        'is_limit_up': is_limit_up,
                        'limit_up_price': limit_up_price
                    }
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    logger.error(f"V15.1 分析失败: {e}")
                    st.error(f"V15.1 分析失败: {e}")

    with col2:
        st.markdown("### 📊 快速统计")

        # 显示分析结果摘要
        if 'v15_1_result' in st.session_state:
            result = st.session_state['v15_1_result']
            exit_signal = st.session_state['v15_1_exit_signal']
            
            # 当前盈亏
            current_profit = result['current_profit'] * 100
            
            if current_profit >= 0:
                st.metric(
                    "当前浮盈",
                    f"+{current_profit:.2f}%",
                    delta=f"止损价: {result['stop_loss_price']:.2f}",
                    delta_color="normal"
                )
            else:
                st.metric(
                    "当前浮亏",
                    f"{current_profit:.2f}%",
                    delta=f"止损价: {result['stop_loss_price']:.2f}",
                    delta_color="inverse"
                )
            
            # 防守等级
            defense_level = result['defense_level']
            if defense_level == 0:
                st.metric("防守等级", "无", delta="初始止损")
            elif defense_level == 1:
                st.metric("防守等级", "一级", delta="成本保护")
            elif defense_level == 2:
                st.metric("防守等级", "二级", delta="回撤锁定")
            elif defense_level == 3:
                st.metric("防守等级", "三级", delta="炸板逃逸")
            
            # 触发状态
            if exit_signal['triggered'] or exit_signal['should_sell']:
                st.error(f"🚨 {exit_signal['action']}")
            else:
                st.success(f"✅ {exit_signal['action']}")
        else:
            st.info("👈 点击左侧按钮开始分析")

    st.markdown("---")

    # 显示详细分析结果
    if 'v15_1_result' in st.session_state:
        result = st.session_state['v15_1_result']
        exit_signal = st.session_state['v15_1_exit_signal']
        params = st.session_state['input_params']
        
        # 1. 防守状态展示
        st.markdown("### 🛡️ 防守状态展示")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            # 一级防守
            if result['tier_1_active']:
                st.success("✅ **一级防守：成本保护**")
                st.write(f"止损价：{result['stop_loss_price']:.2f}")
                st.write(f"止损比例：+{result['stop_loss_ratio']*100:.2f}%")
            else:
                st.info("❌ **一级防守：未激活**")
                st.write(f"当前浮盈：{result['current_profit']*100:.2f}%")
                st.write(f"触发条件：> 3%")
        
        with col_b:
            # 二级防守
            if result['tier_2_active']:
                st.success("✅ **二级防守：回撤锁定**")
                st.write(f"止损价：{result['stop_loss_price']:.2f}")
                st.write(f"最高价：{params['highest_price']:.2f}")
                st.write(f"回撤比例：3%")
            else:
                st.info("❌ **二级防守：未激活**")
                highest_profit = (params['highest_price'] - params['cost_price']) / params['cost_price'] * 100
                st.write(f"最高浮盈：{highest_profit:.2f}%")
                st.write(f"触发条件：> 7%")
        
        with col_c:
            # 三级防守
            if result['tier_3_active']:
                st.error("🚨 **三级防守：炸板逃逸**")
                st.write(f"涨停价：{params['limit_up_price']:.2f}")
                st.write(f"当前价：{params['current_price']:.2f}")
                st.write(f"炸板比例：{(1 - params['current_price']/params['limit_up_price'])*100:.2f}%")
            else:
                st.info("❌ **三级防守：未激活**")
                if params['is_limit_up']:
                    break_ratio = (1 - params['current_price']/params['limit_up_price']) * 100
                    st.write(f"当前炸板：{break_ratio:.2f}%")
                    st.write(f"触发条件：> 2%")
                else:
                    st.write("未涨停")
        
        st.markdown("---")
        
        # 2. V15.1 决策详情
        st.markdown("### 🎯 V15.1 决策详情")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📊 输入参数")
            st.write(f"- **股票代码**: {params['stock_code']}")
            st.write(f"- **成本价**: {params['cost_price']:.2f}")
            st.write(f"- **当前价格**: {params['current_price']:.2f}")
            st.write(f"- **最高价格**: {params['highest_price']:.2f}")
            st.write(f"- **是否涨停**: {'是' if params['is_limit_up'] else '否'}")
            if params['is_limit_up']:
                st.write(f"- **涨停价**: {params['limit_up_price']:.2f}")
            
            st.markdown("#### 🚦 信号")
            if exit_signal['triggered'] or exit_signal['should_sell']:
                st.error(f"**动作**: {exit_signal['action']}")
            else:
                st.success(f"**动作**: {exit_signal['action']}")
            
            st.markdown(f"**止损原因**: {result['stop_loss_reason']}")
            
            # 当前盈亏
            current_profit = result['current_profit'] * 100
            if current_profit >= 0:
                st.success(f"**当前浮盈**: +{current_profit:.2f}%")
            else:
                st.error(f"**当前浮亏**: {current_profit:.2f}%")
            
            # 止损价
            stop_loss_ratio = result['stop_loss_ratio'] * 100
            if stop_loss_ratio >= 0:
                st.success(f"**止损价**: {result['stop_loss_price']:.2f}（+{stop_loss_ratio:.2f}%）")
            else:
                st.error(f"**止损价**: {result['stop_loss_price']:.2f}（{stop_loss_ratio:.2f}%）")
        
        with col_b:
            st.markdown("#### 📊 防守分析")
            
            # 计算各个防守等级的止损价
            tier_1_stop_loss = params['cost_price'] * 1.005
            tier_2_stop_loss = params['highest_price'] * 0.97
            initial_stop_loss = params['cost_price'] * 0.92
            
            st.write(f"- **初始止损**: {initial_stop_loss:.2f}（-8%）")
            st.write(f"- **一级防守**: {tier_1_stop_loss:.2f}（+0.5%）")
            st.write(f"- **二级防守**: {tier_2_stop_loss:.2f}（最高价 * 0.97）")
            
            st.markdown("---")
            st.markdown("#### 💡 V15.1 核心优势")
            st.info("""
            **1. 成本保护**
            - 浮盈 > 3% → 止损线上移
            - 绝不允许盈利单变成亏损
            
            **2. 回撤锁定**
            - 最高浮盈 > 7% → 锁定利润
            - 从最高点回撤 3% 止盈
            
            **3. 炸板逃逸**
            - 炸板 2% → 强制卖出
            - 不留恋涨停画饼
            """)
        
        st.markdown("---")
        
        # 3. 三级防守对比图
        st.markdown("### 📊 三级防守对比")
        
        # 创建对比表
        defense_data = {
            '防守等级': ['无', '一级防守', '二级防守', '三级防守'],
            '触发条件': ['初始状态', '浮盈 > 3%', '最高浮盈 > 7%', '炸板 2%'],
            '止损价': [f"{initial_stop_loss:.2f}", f"{tier_1_stop_loss:.2f}", f"{tier_2_stop_loss:.2f}", "强制卖出"],
            '止损比例': ['-8%', '+0.5%', '最高价*0.97', '市价'],
            '口诀': ['初始止损', '保本单', '保住鱼身', '炸板即走']
        }
        
        df_defense = pd.DataFrame(defense_data)
        st.dataframe(df_defense, use_container_width=True)
        
        # 创建对比图
        fig = go.Figure()
        
        # 不同防守等级的止损价
        fig.add_trace(go.Bar(
            name='初始止损',
            x=['止损价'],
            y=[initial_stop_loss],
            marker_color='#ff7f0e'
        ))
        
        fig.add_trace(go.Bar(
            name='一级防守',
            x=['止损价'],
            y=[tier_1_stop_loss],
            marker_color='#1f77b4'
        ))
        
        fig.add_trace(go.Bar(
            name='二级防守',
            x=['止损价'],
            y=[tier_2_stop_loss],
            marker_color='#2ca02c'
        ))
        
        fig.add_trace(go.Bar(
            name='当前价格',
            x=['止损价'],
            y=[params['current_price']],
            marker_color='#d62728'
        ))
        
        fig.update_layout(
            title="V15.1 三级防守止损价对比",
            xaxis_title="防守等级",
            yaxis_title="价格",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 4. 导出功能
        st.markdown("### 📥 导出分析结果")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # 导出 JSON
            import json
            export_data = {
                'stock_code': params['stock_code'],
                'v15_1_result': result,
                'v15_1_exit_signal': exit_signal,
                'input_params': params,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📄 下载 JSON 报告",
                data=json_str,
                file_name=f"v15_1_dynamic_exit_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col_b:
            # 导出 Markdown 报告
            current_profit = result['current_profit'] * 100
            stop_loss_ratio = result['stop_loss_ratio'] * 100
            
            md_report = f"""# V15.1 动态离场系统分析报告

**股票代码**: {params['stock_code']}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 V15.1 决策结果

- **当前浮盈**: {current_profit:+.2f}%
- **止损价**: {result['stop_loss_price']:.2f}
- **止损比例**: {stop_loss_ratio:+.2f}%
- **防守等级**: {result['defense_level']}
- **止损原因**: {result['stop_loss_reason']}
- **动作**: {exit_signal['action']}

---

## 🛡️ 防守状态

**一级防守（成本保护）**: {'✅ 激活' if result['tier_1_active'] else '❌ 未激活'}
**二级防守（回撤锁定）**: {'✅ 激活' if result['tier_2_active'] else '❌ 未激活'}
**三级防守（炸板逃逸）**: {'✅ 激活' if result['tier_3_active'] else '❌ 未激活'}

---

## 📊 输入参数

- 成本价: {params['cost_price']:.2f}
- 当前价格: {params['current_price']:.2f}
- 最高价格: {params['highest_price']:.2f}
- 是否涨停: {'是' if params['is_limit_up'] else '否'}
- 涨停价: {params['limit_up_price']:.2f}

---

## 💡 V15.1 三级防守

**一级防守：成本保护**
- 条件：浮盈 > 3%
- 止损线：成本价 + 0.5%
- 口诀：赚了钱的单子，绝不允许变成亏损走

**二级防守：回撤锁定**
- 条件：最高浮盈 > 7%（但未涨停）
- 止损线：最高价 * 0.97
- 口诀：吃不到鱼头，但要保住鱼身

**三级防守：炸板逃逸**
- 条件：曾涨停 + 炸板 2%
- 动作：强制市价卖出
- 口诀：涨停板是用来封的，不是用来给你画饼的

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*V15.1 Dynamic Exit System v1.0*
"""
            
            st.download_button(
                label="📝 下载 Markdown 报告",
                data=md_report,
                file_name=f"v15_1_dynamic_exit_{params['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
    
    else:
        st.info("👈 点击左侧按钮开始分析")


if __name__ == '__main__':
    # 测试运行
    render_dynamic_exit()