"""
游资流向可视化模块
提供 Sankey 图和时间轴可视化功能
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any
from logic.logger import get_logger

logger = get_logger(__name__)


def plot_capital_sankey(df_operations: pd.DataFrame, capital_name: str = None) -> go.Figure:
    """
    游资操作链路可视化 - Sankey 流向图

    Args:
        df_operations: 游资操作数据 DataFrame
        capital_name: 游资名称 (可选)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_operations.empty:
            logger.warning("操作数据为空，无法生成 Sankey 图")
            return None

        # 数据准备
        # 节点: 游资 -> 股票 -> 行业 -> 操作类型
        nodes = []
        links = {'source': [], 'target': [], 'value': []}

        # 添加游资节点
        if capital_name:
            nodes.append({'name': capital_name, 'color': '#667eea'})
            capital_idx = 0
        else:
            # 如果没有指定游资，使用所有游资
            unique_capitals = df_operations['游资名称'].unique() if '游资名称' in df_operations.columns else []
            for cap in unique_capitals:
                nodes.append({'name': cap, 'color': '#667eea'})
            capital_idx = 0

        # 添加股票节点
        unique_stocks = df_operations['股票名称'].unique() if '股票名称' in df_operations.columns else []
        stock_start_idx = len(nodes)
        for stock in unique_stocks:
            nodes.append({'name': stock, 'color': '#764ba2'})

        # 添加操作类型节点
        operation_types = ['买入', '卖出', '净买入', '净卖出']
        operation_start_idx = len(nodes)
        for op_type in operation_types:
            nodes.append({'name': op_type, 'color': '#f093fb'})

        # 构建链接
        node_labels = [node['name'] for node in nodes]
        node_colors = [node['color'] for node in nodes]

        # 游资 -> 股票
        for _, row in df_operations.iterrows():
            stock_name = row.get('股票名称', '')
            buy_amount = float(row.get('买入金额', 0) or 0)
            sell_amount = float(row.get('卖出金额', 0) or 0)

            if stock_name and stock_name in node_labels:
                stock_idx = node_labels.index(stock_name)

                # 买入链接
                if buy_amount > 0:
                    links['source'].append(capital_idx)
                    links['target'].append(stock_idx)
                    links['value'].append(buy_amount / 100000000)  # 转换为亿元

                # 卖出链接
                if sell_amount > 0:
                    links['source'].append(stock_idx)
                    links['target'].append(operation_start_idx + 1)  # 卖出
                    links['value'].append(sell_amount / 100000000)

        # 创建 Sankey 图
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=node_labels,
                color=node_colors
            ),
            link=dict(
                source=links['source'],
                target=links['target'],
                value=links['value'],
                color='rgba(102, 126, 234, 0.3)'
            )
        )])

        fig.update_layout(
            title_text=f"游资操作链路流向分析 - {capital_name or '全部游资'}",
            font=dict(size=12, color='#333'),
            height=600,
            margin=dict(l=20, r=20, t=60, b=20)
        )

        logger.info(f"成功生成 Sankey 图，包含 {len(nodes)} 个节点")
        return fig

    except Exception as e:
        logger.error(f"生成 Sankey 图失败: {e}")
        return None


def plot_capital_timeline(df_operations: pd.DataFrame, capital_name: str = None) -> go.Figure:
    """
    游资操作时间轴可视化

    Args:
        df_operations: 游资操作数据 DataFrame
        capital_name: 游资名称 (可选)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_operations.empty:
            logger.warning("操作数据为空，无法生成时间轴图")
            return None

        # 按日期排序
        df = df_operations.copy()
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
        elif '上榜日' in df.columns:
            df['日期'] = pd.to_datetime(df['上榜日'])
            df = df.sort_values('日期')

        # 创建时间轴图
        fig = go.Figure()

        # 按操作类型分组
        buy_data = df[df['买入金额'] > 0] if '买入金额' in df.columns else pd.DataFrame()
        sell_data = df[df['卖出金额'] > 0] if '卖出金额' in df.columns else pd.DataFrame()

        # 买入点
        if not buy_data.empty:
            fig.add_trace(go.Scatter(
                x=buy_data['日期'],
                y=buy_data['买入金额'] / 100000000,  # 转换为亿元
                mode='markers+lines',
                name='买入',
                marker=dict(
                    size=10,
                    color='rgba(76, 175, 80, 0.8)',
                    line=dict(width=2, color='rgb(76, 175, 80)')
                ),
                hovertemplate='<b>%{text}</b><br>日期: %{x|%Y-%m-%d}<br>金额: ¥%{y:.2f}亿<extra></extra>',
                text=buy_data['股票名称'] + ' (' + buy_data['股票代码'] + ')'
            ))

        # 卖出点
        if not sell_data.empty:
            fig.add_trace(go.Scatter(
                x=sell_data['日期'],
                y=sell_data['卖出金额'] / 100000000,  # 转换为亿元
                mode='markers+lines',
                name='卖出',
                marker=dict(
                    size=10,
                    color='rgba(244, 67, 54, 0.8)',
                    line=dict(width=2, color='rgb(244, 67, 54)')
                ),
                hovertemplate='<b>%{text}</b><br>日期: %{x|%Y-%m-%d}<br>金额: ¥%{y:.2f}亿<extra></extra>',
                text=sell_data['股票名称'] + ' (' + sell_data['股票代码'] + ')'
            ))

        fig.update_layout(
            title_text=f"游资操作时间轴 - {capital_name or '全部游资'}",
            xaxis_title="日期",
            yaxis_title="金额 (亿元)",
            hovermode='closest',
            height=500,
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=True
        )

        logger.info(f"成功生成时间轴图，包含 {len(df)} 条操作记录")
        return fig

    except Exception as e:
        logger.error(f"生成时间轴图失败: {e}")
        return None