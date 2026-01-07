"""
热力图可视化模块
提供游资活跃度和板块热力图功能
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any
from logic.logger import get_logger

logger = get_logger(__name__)


def plot_activity_heatmap(df_operations: pd.DataFrame, by: str = 'day') -> go.Figure:
    """
    游资活跃度热力图

    Args:
        df_operations: 游资操作数据 DataFrame
        by: 聚合维度 ('day' 按天, 'hour' 按小时, 'week' 按周)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_operations.empty:
            logger.warning("操作数据为空，无法生成活跃度热力图")
            return None

        df = df_operations.copy()

        # 确保有日期列
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
        elif '上榜日' in df.columns:
            df['日期'] = pd.to_datetime(df['上榜日'])
        else:
            logger.error("数据中缺少日期列")
            return None

        # 按维度聚合
        if by == 'day':
            df['day'] = df['日期'].dt.day
            df['month'] = df['日期'].dt.month
            pivot_data = df.groupby(['month', 'day']).size().reset_index(name='count')
            pivot_table = pivot_data.pivot(index='month', columns='day', values='count').fillna(0)

            x_labels = list(range(1, 32))
            y_labels = list(range(1, 13))
            title = "游资活跃度热力图 (按日)"

        elif by == 'hour':
            df['hour'] = df['日期'].dt.hour
            df['day_of_week'] = df['日期'].dt.dayofweek
            pivot_data = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
            pivot_table = pivot_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)

            x_labels = list(range(24))
            y_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            title = "游资活跃度热力图 (按小时)"

        elif by == 'week':
            df['week'] = df['日期'].dt.isocalendar().week
            df['year'] = df['日期'].dt.year
            pivot_data = df.groupby(['year', 'week']).size().reset_index(name='count')
            pivot_table = pivot_data.pivot(index='year', columns='week', values='count').fillna(0)

            x_labels = list(range(1, 53))
            y_labels = sorted(df['year'].unique())
            title = "游资活跃度热力图 (按周)"

        else:
            logger.error(f"不支持的聚合维度: {by}")
            return None

        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=x_labels,
            y=y_labels,
            colorscale='Viridis',
            colorbar=dict(title="操作次数"),
            hoverongaps=False
        ))

        fig.update_layout(
            title_text=title,
            xaxis_title="日期" if by == 'day' else "小时" if by == 'hour' else "周数",
            yaxis_title="月份" if by == 'day' else "星期" if by == 'hour' else "年份",
            height=500,
            margin=dict(l=20, r=20, t=60, b=20)
        )

        logger.info(f"成功生成活跃度热力图，维度: {by}")
        return fig

    except Exception as e:
        logger.error(f"生成活跃度热力图失败: {e}")
        return None


def plot_sector_heatmap(df_operations: pd.DataFrame, capital_name: str = None) -> go.Figure:
    """
    板块热力图 - 展示游资在不同板块的操作分布

    Args:
        df_operations: 游资操作数据 DataFrame
        capital_name: 游资名称 (可选)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_operations.empty:
            logger.warning("操作数据为空，无法生成板块热力图")
            return None

        df = df_operations.copy()

        # 检查是否有板块信息
        if '板块' not in df.columns and '行业' not in df.columns:
            logger.warning("数据中缺少板块信息，尝试从股票代码获取")
            # 这里可以添加从股票代码获取板块的逻辑
            # 暂时使用股票名称作为板块
            df['板块'] = df['股票名称'] if '股票名称' in df.columns else '未知'
        else:
            df['板块'] = df['板块'] if '板块' in df.columns else df['行业']

        # 按游资和板块聚合
        if '游资名称' in df.columns:
            pivot_data = df.groupby(['游资名称', '板块']).agg({
                '买入金额': 'sum',
                '卖出金额': 'sum',
                '净买入': lambda x: x.sum()
            }).reset_index()

            # 计算总操作金额
            pivot_data['总金额'] = pivot_data['买入金额'] + pivot_data['卖出金额']

            # 如果指定了游资，只显示该游资
            if capital_name:
                pivot_data = pivot_data[pivot_data['游资名称'] == capital_name]

            # 创建透视表
            pivot_table = pivot_data.pivot(
                index='游资名称' if not capital_name else '板块',
                columns='板块' if not capital_name else '游资名称',
                values='总金额'
            ).fillna(0)

            # 转换为亿元
            pivot_table = pivot_table / 100000000

            x_labels = pivot_table.columns.tolist()
            y_labels = pivot_table.index.tolist()
            z_values = pivot_table.values

        else:
            # 如果没有游资名称，只按板块统计
            pivot_data = df.groupby('板块').agg({
                '买入金额': 'sum',
                '卖出金额': 'sum'
            }).reset_index()

            pivot_data['总金额'] = pivot_data['买入金额'] + pivot_data['卖出金额']
            pivot_data = pivot_data.sort_values('总金额', ascending=False).head(20)

            # 创建单行热力图
            pivot_table = pivot_data.set_index('板块')[['总金额']].T
            pivot_table = pivot_table / 100000000

            x_labels = pivot_table.columns.tolist()
            y_labels = ['总金额']
            z_values = pivot_table.values

        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale='RdYlGn',
            colorbar=dict(title="金额 (亿元)"),
            hoverongaps=False,
            text=z_values,
            texttemplate="%{z:.2f}",
            textfont={"size": 10}
        ))

        fig.update_layout(
            title_text=f"游资板块操作分布 - {capital_name or '全部游资'}",
            xaxis_title="板块",
            yaxis_title="游资" if '游资名称' in df.columns else "",
            height=500,
            margin=dict(l=20, r=20, t=60, b=20)
        )

        logger.info(f"成功生成板块热力图")
        return fig

    except Exception as e:
        logger.error(f"生成板块热力图失败: {e}")
        return None