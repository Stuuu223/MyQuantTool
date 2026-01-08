"""
板块强度排行模块 - UI渲染函数
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any

def render_sector_strength_tab(db, config):
    """渲染板块强度排行标签页"""
    st.subheader("📈 板块强度排行")
    
    st.info("💡 提示：当前使用演示数据，实际数据需要等待股市开盘，休市时间以收盘为准")
    
    # 生成模拟板块数据
    sectors = [
        "新能源车", "光伏", "芯片", "生物医药", "人工智能", 
        "消费电子", "券商", "银行", "房地产", "食品饮料", 
        "钢铁", "煤炭", "有色金属", "建材", "医药"
    ]
    
    # 生成模拟数据
    np.random.seed(42)
    data = []
    for sector in sectors:
        strength = np.random.uniform(-2.0, 5.0)  # 强度值
        avg_change = np.random.uniform(-1.5, 2.5)  # 平均涨跌幅
        top_stocks = np.random.choice([5, 10, 15, 20], 1)[0]  # 领涨股票数量
        volume_ratio = np.random.uniform(0.8, 2.0)  # 成交量比率
        
        data.append({
            "板块": sector,
            "强度": strength,
            "平均涨跌幅": avg_change,
            "领涨股票数": top_stocks,
            "成交量比率": volume_ratio
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values("强度", ascending=False)
    
    # 显示板块强度排行表格
    st.subheader("📊 板块强度排行")
    
    # 添加排名列
    df["排名"] = range(1, len(df) + 1)
    df = df[["排名", "板块", "强度", "平均涨跌幅", "领涨股票数", "成交量比率"]]
    
    # 根据强度设置颜色
    def color_row(row):
        if row["强度"] > 3:
            return ["color: green"] * len(row)
        elif row["强度"] > 0:
            return ["color: #0066cc"] * len(row)
        elif row["强度"] > -1.5:
            return ["color: orange"] * len(row)
        else:
            return ["color: red"] * len(row)
    
    styled_df = df.style.apply(color_row, axis=1).format({
        "强度": "{:.2f}",
        "平均涨跌幅": "{:.2f}%",
        "成交量比率": "{:.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True)
    
    # 绘制板块强度图表
    st.subheader("📈 板块强度分布")
    
    # 柱状图
    fig_bar = px.bar(
        df.head(10), 
        x="强度", 
        y="板块", 
        orientation='h',
        title="前10强板块强度",
        color="强度",
        color_continuous_scale="RdYlGn"
    )
    fig_bar.update_layout(height=500)
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # 绘制强度与涨跌幅的关系
    st.subheader("🔍 强度与平均涨跌幅关系")
    fig_scatter = px.scatter(
        df, 
        x="强度", 
        y="平均涨跌幅", 
        text="板块",
        title="板块强度与平均涨跌幅关系",
        color="强度",
        color_continuous_scale="RdYlGn",
        range_x=[df["强度"].min() - 0.5, df["强度"].max() + 0.5],
        range_y=[df["平均涨跌幅"].min() - 0.5, df["平均涨跌幅"].max() + 0.5]
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 显示强势板块详情
    strong_sectors = df[df["强度"] > 2]
    if not strong_sectors.empty:
        st.subheader("💪 强势板块详情")
        for _, row in strong_sectors.iterrows():
            with st.expander(f"📈 {row['板块']} (强度: {row['强度']:.2f})"):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("强度", f"{row['强度']:.2f}")
                col2.metric("平均涨跌幅", f"{row['平均涨跌幅']:.2f}%")
                col3.metric("领涨股票数", f"{row['领涨股票数']}")
                col4.metric("成交量比率", f"{row['成交量比率']:.2f}")
                
                # 板块内个股涨跌分布（模拟数据）
                stock_changes = np.random.normal(row['平均涨跌幅'], 1.0, 10)  # 模拟10只个股的涨跌幅
                stock_fig = go.Figure(data=go.Bar(x=[f'股票{i+1}' for i in range(10)], y=stock_changes))
                stock_fig.update_layout(
                    title=f"{row['板块']} 内个股涨跌幅分布",
                    xaxis_title="个股",
                    yaxis_title="涨跌幅(%)",
                    height=300
                )
                st.plotly_chart(stock_fig, use_container_width=True)


# 如果直接运行此模块
if __name__ == "__main__":
    # 仅为测试目的
    st.set_page_config(page_title="板块强度", layout="wide")
    render_sector_strength_tab(None, {})