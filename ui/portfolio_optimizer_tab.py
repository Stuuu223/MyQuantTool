"""
组合优化模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any

from logic.portfolio_optimizer import PortfolioOptimizer


def render_portfolio_optimizer_tab(db, config):
    """渲染组合优化标签页"""
    st.subheader("⚖️ 投资组合优化")
    
    # 初始化模块
    portfolio_optimizer = PortfolioOptimizer()
    
    st.subheader("投资组合优化器")
    
    # 生成模拟收益率数据
    dates = pd.date_range(end=datetime.now(), periods=100)
    assets = ['股票A', '股票B', '股票C', '债券D', '商品E']
    
    # 创建模拟收益率数据
    np.random.seed(42)
    returns_data = {}
    for asset in assets:
        # 生成具有不同特征的收益率数据
        daily_returns = np.random.normal(0.0005, 0.02, 100)  # 均值0.05%，标准差2%
        returns_data[asset] = daily_returns
    
    returns_df = pd.DataFrame(returns_data, index=dates)
    
    st.write("模拟资产收益率数据 (最近10天):")
    st.dataframe(returns_df.tail(10).style.format("{:.4f}"))
    
    # 选择优化方法
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox("优化方法", ["马科维茨均值方差", "风险平价", "Black-Litterman"])
    
    with col2:
        if method == "马科维茨均值方差":
            target_return = st.number_input("目标收益率", value=0.0008, step=0.0001, format="%.4f")
        else:
            target_return = None
    
    if st.button("执行优化"):
        with st.spinner("正在优化投资组合..."):
            method_map = {
                "马科维茨均值方差": "markowitz",
                "风险平价": "risk_parity", 
                "Black-Litterman": "black_litterman"
            }
            
            result = portfolio_optimizer.optimize_portfolio(
                returns_df, 
                method=method_map[method],
                target_return=target_return
            )
        
        # 显示优化结果
        col1, col2, col3 = st.columns(3)
        col1.metric("预期收益率", f"{result.expected_return:.2%}")
        col2.metric("波动率", f"{result.volatility:.2%}")
        col3.metric("夏普比率", f"{result.sharpe_ratio:.3f}")
        
        st.subheader("资产权重分配")
        weights_df = pd.DataFrame(list(result.weights.items()), columns=['资产', '权重'])
        weights_df['权重百分比'] = weights_df['权重'].apply(lambda x: f"{x:.2%}")
        
        # 显示权重图表
        fig = px.pie(weights_df, values='权重', names='资产', title='资产权重分布')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(weights_df)
        
        # 显示风险贡献
        st.subheader("风险贡献分析")
        risk_df = pd.DataFrame(list(result.risk_contribution.items()), columns=['资产', '风险贡献'])
        risk_df['风险贡献百分比'] = risk_df['风险贡献'].apply(lambda x: f"{x:.2%}")
        st.dataframe(risk_df)


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="组合优化", layout="wide")
    render_portfolio_optimizer_tab(None, {})