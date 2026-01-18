#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.3 生态看门人 - UI 组件
识别"德不配位"的流动性异常，拒绝参与"游资对价值股的强暴"
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from logic.iron_rule_monitor import IronRuleMonitor
from logic.logger import get_logger

logger = get_logger(__name__)


def render_ecological_watchdog_tab(db_instance, config):
    """
    渲染生态看门人标签页
    
    Args:
        db_instance: 数据库实例
        config: 配置对象
    """
    st.markdown("---")
    st.markdown("### 🌍 V16.3 生态看门人")
    st.caption("识别\"德不配位\"的流动性异常，拒绝参与\"游资对价值股的强暴\"")
    
    # 初始化监控器
    iron_monitor = IronRuleMonitor()
    
    # 创建布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📊 单股生态异常查询")
        
        # 股票代码输入
        stock_code = st.text_input(
            "股票代码",
            value="600519",
            help="输入 6 位股票代码，如 600519"
        )
        
        # 查询按钮
        if st.button("🔍 查询生态异常", use_container_width=True):
            with st.spinner("正在分析生态异常..."):
                # 获取生态风险分析
                eco_risk = iron_monitor.check_value_distortion(stock_code)
                
                # 显示结果
                _display_eco_risk_result(eco_risk, stock_code)
    
    with col2:
        st.markdown("#### 📋 风险统计")
        
        # 显示风险统计信息
        _display_eco_risk_statistics(iron_monitor)
    
    st.markdown("---")
    st.markdown("#### 📈 批量检查")
    
    # 批量检查区域
    _display_batch_check(iron_monitor)
    
    st.markdown("---")
    st.markdown("#### 📖 风险说明")
    
    # 显示风险说明
    _display_eco_risk_explanation()


def _display_eco_risk_result(eco_risk: Dict, stock_code: str):
    """
    显示生态风险结果
    
    Args:
        eco_risk: 生态风险数据
        stock_code: 股票代码
    """
    # 风险等级颜色映射
    risk_colors = {
        'DANGER': '🔴',
        'WARNING': '🟡',
        'LOW': '🟢'
    }
    
    # 显示风险等级
    risk_emoji = risk_colors.get(eco_risk['risk_level'], '⚪')
    st.markdown(f"### {risk_emoji} 风险等级: {eco_risk['risk_level']}")
    
    # 显示风险原因
    if eco_risk['has_risk']:
        st.error(eco_risk['reason'])
    else:
        st.success(eco_risk['reason'])
    
    # 显示详细数据
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("换手率倍数", f"{eco_risk['turnover_ratio']:.1f}x")
    with col2:
        st.metric("板块占比", f"{eco_risk['sector_ratio']:.1%}")
    with col3:
        st.metric("换手率异常", "是" if eco_risk['turnover_anomaly'] else "否")
    
    # 显示流动性黑洞
    if eco_risk['liquidity_blackhole']:
        st.warning("🌪️ 检测到流动性黑洞：该股票正在吸干板块流动性")


def _display_eco_risk_statistics(iron_monitor: IronRuleMonitor):
    """
    显示生态风险统计
    
    Args:
        iron_monitor: 铁律监控器
    """
    # 获取自选股列表（这里使用示例数据）
    stock_codes = ["600519", "000001", "000002", "601318", "600036"]
    
    # 获取生态风险摘要
    summary = iron_monitor.get_ecological_risk_summary(stock_codes)
    
    # 显示统计信息
    st.metric("总股票数", summary['total_stocks'])
    st.metric("危险股票", len(summary['danger_stocks']), delta_color="inverse")
    st.metric("警告股票", len(summary['warning_stocks']))
    st.metric("正常股票", len(summary['normal_stocks']))
    
    # 显示危险股票列表
    if summary['danger_stocks']:
        st.markdown("##### 🔴 危险股票")
        for stock_code in summary['danger_stocks']:
            eco_risk = summary['risk_details'][stock_code]
            st.warning(f"{stock_code}: {eco_risk['reason']}")
    
    # 显示警告股票列表
    if summary['warning_stocks']:
        st.markdown("##### 🟡 警告股票")
        for stock_code in summary['warning_stocks']:
            eco_risk = summary['risk_details'][stock_code]
            st.info(f"{stock_code}: {eco_risk['reason']}")


def _display_batch_check(iron_monitor: IronRuleMonitor):
    """
    显示批量检查
    
    Args:
        iron_monitor: 铁律监控器
    """
    # 股票代码输入
    stock_codes_input = st.text_area(
        "批量检查股票代码（每行一个）",
        value="600519\n000001\n000002",
        help="每行输入一个 6 位股票代码"
    )
    
    # 批量检查按钮
    if st.button("🔍 批量检查", use_container_width=True):
        # 解析股票代码
        stock_codes = [code.strip() for code in stock_codes_input.split('\n') if code.strip()]
        
        if not stock_codes:
            st.warning("请输入股票代码")
            return
        
        with st.spinner("正在批量分析生态异常..."):
            # 获取生态风险摘要
            summary = iron_monitor.get_ecological_risk_summary(stock_codes)
            
            # 显示结果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总股票数", summary['total_stocks'])
            with col2:
                st.metric("危险股票", len(summary['danger_stocks']), delta_color="inverse")
            with col3:
                st.metric("警告股票", len(summary['warning_stocks']))
            
            # 显示详细结果
            st.markdown("##### 📊 详细结果")
            
            # 创建结果表格
            results = []
            for stock_code in stock_codes:
                eco_risk = summary['risk_details'][stock_code]
                results.append({
                    '股票代码': stock_code,
                    '风险等级': eco_risk['risk_level'],
                    '换手率倍数': f"{eco_risk['turnover_ratio']:.1f}x",
                    '板块占比': f"{eco_risk['sector_ratio']:.1%}",
                    '换手率异常': '是' if eco_risk['turnover_anomaly'] else '否',
                    '流动性黑洞': '是' if eco_risk['liquidity_blackhole'] else '否',
                    '风险原因': eco_risk['reason']
                })
            
            df = pd.DataFrame(results)
            
            # 根据风险等级着色
            def highlight_risk(row):
                if row['风险等级'] == 'DANGER':
                    return ['background-color: #ffcccc'] * len(row)
                elif row['风险等级'] == 'WARNING':
                    return ['background-color: #ffffcc'] * len(row)
                else:
                    return ['background-color: #ccffcc'] * len(row)
            
            styled_df = df.style.apply(highlight_risk, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)


def _display_eco_risk_explanation():
    """
    显示生态风险说明
    """
    st.markdown("""
    ### 🎯 风险判定标准
    
    | 风险等级 | 判定条件 | 说明 |
    |---------|---------|------|
    | 🔴 危险 | 换手率 > 5倍均值 且 涨幅 > 5% | 价值票游资化，换手率爆炸，谨防接盘 |
    | 🟡 警告 | 板块占比 > 30% | 个股吸干板块流动性，独木难支 |
    | 🟢 正常 | 无异常 | 生态正常，可以参与 |
    
    ### ⚠️ 重要提示
    
    1. **换手率背离**：价值投资讲究细水长流，突然的暴量通常是主力在"大干快上"准备出货
    2. **流动性黑洞**：一将功成万骨枯。当一只票吸走了板块 30% 的血，板块崩塌时它也独活不了
    3. **操作建议**：遇到危险股票，建议坚决回避，不要抱有侥幸心理
    4. **降权处理**：警告股票的 AI 评分会自动降级 50%，降低参与概率
    
    ### 📚 相关概念
    
    - **换手率背离**：当前换手率远高于历史均值，说明有异常资金介入
    - **流动性黑洞**：个股成交额占板块总成交额的比例过高，吸干板块流动性
    - **生态异常**：价值股被游资化，出现不符合其基本面的异常波动
    
    ### 🛡️ 防御策略
    
    1. **一票否决**：只要检测到生态异常，系统自动拒绝买入
    2. **降权处理**：警告股票的 AI 评分自动降级 50%
    3. **黑名单机制**：将危险股票加入黑名单，系统自动屏蔽
    4. **定期检查**：定期检查持仓股票的生态状态，及时调整仓位
    
    ### 🎭 金融政治经济学视角
    
    在 A 股，最大的空头永远不是外资，而是不仅不看好自家公司、甚至急于把公司当提款机的大股东。
    
    我们要做的，是识别"德不配位"的流动性异常，拒绝参与"游资对价值股的强暴"。
    
    波动可以制造，但不能由游资来制造破坏性的波动。
    """)


if __name__ == "__main__":
    # 测试
    print("V16.3 生态看门人 UI 组件")
    print("请通过 Streamlit 运行此组件")
