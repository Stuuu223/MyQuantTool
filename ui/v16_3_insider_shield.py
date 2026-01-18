#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.3 内部人防御盾 (Insider Shield) - UI 组件
监控大股东减持和高管套现风险，防止被内部人收割
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime, timedelta
from logic.iron_rule_monitor import IronRuleMonitor
from logic.logger import get_logger

logger = get_logger(__name__)


def render_insider_shield_tab(db_instance, config):
    """
    渲染内部人防御盾标签页
    
    Args:
        db_instance: 数据库实例
        config: 配置对象
    """
    st.markdown("---")
    st.markdown("### 🛡️ V16.3 内部人防御盾 (The Insider Shield)")
    st.caption("监控大股东减持和高管套现风险，防止被内部人收割")
    
    # 初始化监控器
    iron_monitor = IronRuleMonitor()
    
    # 创建布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📊 单股减持风险查询")
        
        # 股票代码输入
        stock_code = st.text_input(
            "股票代码",
            value="600519",
            help="输入 6 位股票代码，如 600519"
        )
        
        # 查询天数选择
        days = st.slider(
            "查询天数",
            min_value=30,
            max_value=365,
            value=90,
            help="查询最近多少天的减持公告"
        )
        
        # 查询按钮
        if st.button("🔍 查询减持风险", use_container_width=True):
            with st.spinner("正在查询减持公告..."):
                # 获取减持风险分析
                risk_data = iron_monitor.check_insider_selling(stock_code, days)
                
                # 显示结果
                _display_risk_result(risk_data, stock_code, days)
    
    with col2:
        st.markdown("#### 📋 风险统计")
        
        # 显示风险统计信息
        _display_risk_statistics(iron_monitor)
    
    st.markdown("---")
    st.markdown("#### 📈 批量检查")
    
    # 批量检查区域
    _display_batch_check(iron_monitor)
    
    st.markdown("---")
    st.markdown("#### 📖 风险说明")
    
    # 显示风险说明
    _display_risk_explanation()


def _display_risk_result(risk_data: Dict, stock_code: str, days: int):
    """
    显示风险结果
    
    Args:
        risk_data: 风险数据
        stock_code: 股票代码
        days: 查询天数
    """
    # 风险等级颜色映射
    risk_colors = {
        'HIGH': '🔴',
        'MEDIUM': '🟡',
        'LOW': '🟢'
    }
    
    # 显示风险等级
    risk_emoji = risk_colors.get(risk_data['risk_level'], '⚪')
    st.markdown(f"### {risk_emoji} 风险等级: {risk_data['risk_level']}")
    
    # 显示风险原因
    if risk_data['has_risk']:
        st.error(risk_data['reason'])
    else:
        st.success(risk_data['reason'])
    
    # 显示详细数据
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总减持比例", f"{risk_data['total_decrease_ratio']:.2f}%")
    with col2:
        st.metric("总减持金额", f"{risk_data['total_decrease_value']:.0f} 万元")
    with col3:
        st.metric("减持记录数", len(risk_data['decrease_records']))
    
    # 显示减持记录
    if risk_data['decrease_records']:
        st.markdown("##### 📝 减持记录详情")
        
        # 转换为 DataFrame
        df = pd.DataFrame(risk_data['decrease_records'])
        
        # 格式化显示
        df['减持比例'] = df['减持比例'].apply(lambda x: f"{x:.2f}%")
        df['减持金额'] = df['减持金额'].apply(lambda x: f"{x:.0f} 万元")
        df['减持价格'] = df['减持价格'].apply(lambda x: f"{x:.2f}" if x > 0 else "-")
        
        # 显示表格
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("未发现减持记录")


def _display_risk_statistics(iron_monitor: IronRuleMonitor):
    """
    显示风险统计
    
    Args:
        iron_monitor: 铁律监控器
    """
    # 获取自选股列表（这里使用示例数据）
    stock_codes = ["600519", "000001", "000002", "601318", "600036"]
    
    # 获取风险摘要
    summary = iron_monitor.get_insider_risk_summary(stock_codes, days=90)
    
    # 显示统计信息
    st.metric("总股票数", summary['total_stocks'])
    st.metric("高风险股票", len(summary['high_risk_stocks']), delta_color="inverse")
    st.metric("中风险股票", len(summary['medium_risk_stocks']))
    st.metric("低风险股票", len(summary['low_risk_stocks']))
    
    # 显示高风险股票列表
    if summary['high_risk_stocks']:
        st.markdown("##### 🔴 高风险股票")
        for stock_code in summary['high_risk_stocks']:
            risk_data = summary['risk_details'][stock_code]
            st.warning(f"{stock_code}: {risk_data['reason']}")
    
    # 显示中风险股票列表
    if summary['medium_risk_stocks']:
        st.markdown("##### 🟡 中风险股票")
        for stock_code in summary['medium_risk_stocks']:
            risk_data = summary['risk_details'][stock_code]
            st.info(f"{stock_code}: {risk_data['reason']}")


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
    
    # 查询天数选择
    days = st.slider(
        "查询天数",
        min_value=30,
        max_value=365,
        value=90,
        key="batch_days"
    )
    
    # 批量检查按钮
    if st.button("🔍 批量检查", use_container_width=True):
        # 解析股票代码
        stock_codes = [code.strip() for code in stock_codes_input.split('\n') if code.strip()]
        
        if not stock_codes:
            st.warning("请输入股票代码")
            return
        
        with st.spinner("正在批量查询减持风险..."):
            # 获取风险摘要
            summary = iron_monitor.get_insider_risk_summary(stock_codes, days)
            
            # 显示结果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总股票数", summary['total_stocks'])
            with col2:
                st.metric("高风险股票", len(summary['high_risk_stocks']), delta_color="inverse")
            with col3:
                st.metric("中风险股票", len(summary['medium_risk_stocks']))
            
            # 显示详细结果
            st.markdown("##### 📊 详细结果")
            
            # 创建结果表格
            results = []
            for stock_code in stock_codes:
                risk_data = summary['risk_details'][stock_code]
                results.append({
                    '股票代码': stock_code,
                    '风险等级': risk_data['risk_level'],
                    '总减持比例(%)': f"{risk_data['total_decrease_ratio']:.2f}",
                    '总减持金额(万元)': f"{risk_data['total_decrease_value']:.0f}",
                    '风险原因': risk_data['reason']
                })
            
            df = pd.DataFrame(results)
            
            # 根据风险等级着色
            def highlight_risk(row):
                if row['风险等级'] == 'HIGH':
                    return ['background-color: #ffcccc'] * len(row)
                elif row['风险等级'] == 'MEDIUM':
                    return ['background-color: #ffffcc'] * len(row)
                else:
                    return ['background-color: #ccffcc'] * len(row)
            
            styled_df = df.style.apply(highlight_risk, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)


def _display_risk_explanation():
    """
    显示风险说明
    """
    st.markdown("""
    ### 🎯 风险判定标准
    
    | 风险等级 | 判定条件 | 说明 |
    |---------|---------|------|
    | 🔴 高危 (HIGH) | 总减持比例 > 2% 或 总减持金额 > 1亿 | 大股东正在大规模套现，坚决回避 |
    | 🟡 中危 (MEDIUM) | 总减持比例 > 1% 或 总减持金额 > 5000万 | 股东有减持计划，需要谨慎 |
    | 🟢 低危 (LOW) | 有减持记录但规模较小 | 有减持公告，但影响有限 |
    
    ### ⚠️ 重要提示
    
    1. **数据来源**：减持公告来自东方财富网，可能存在延迟
    2. **查询范围**：默认查询最近 90 天的减持公告
    3. **风险提示**：即使没有减持公告，也要关注其他风险因素
    4. **操作建议**：遇到高风险股票，建议坚决回避，不要抱有侥幸心理
    
    ### 📚 相关概念
    
    - **减持**：股东卖出持有的股票，通常意味着股东不看好公司前景
    - **套现**：股东通过减持股票获得现金，可能是为了个人资金需求
    - **内部人风险**：公司内部人员（大股东、高管）减持带来的股价下跌风险
    
    ### 🛡️ 防御策略
    
    1. **黑名单机制**：将高风险股票加入黑名单，系统自动屏蔽
    2. **一票否决**：只要检测到减持风险，系统自动拒绝买入
    3. **定期检查**：定期检查持仓股票的减持公告，及时调整仓位
    """)


if __name__ == "__main__":
    # 测试
    print("V16.3 内部人防御盾 UI 组件")
    print("请通过 Streamlit 运行此组件")