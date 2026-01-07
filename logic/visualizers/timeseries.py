"""
时间序列可视化模块
提供排名变化和业绩表现的时间序列图表
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any
from logic.logger import get_logger

logger = get_logger(__name__)


def plot_ranking_timeseries(df_rank: pd.DataFrame, stock_name: str = None) -> go.Figure:
    """
    龙虎榜排名变化时间序列图

    Args:
        df_rank: 排名数据 DataFrame
        stock_name: 股票名称 (可选)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_rank.empty:
            logger.warning("排名数据为空，无法生成排名时间序列图")
            return None

        df = df_rank.copy()

        # 确保有日期列
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
        elif '上榜日' in df.columns:
            df['日期'] = pd.to_datetime(df['上榜日'])
        else:
            logger.error("数据中缺少日期列")
            return None

        # 按日期排序
        df = df.sort_values('日期')

        # 创建图表
        fig = go.Figure()

        # 如果有排名列，绘制排名变化
        if '排名' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['日期'],
                y=df['排名'],
                mode='lines+markers',
                name='排名',
                line=dict(color='#667eea', width=2),
                marker=dict(size=8),
                hovertemplate='<b>%{text}</b><br>日期: %{x|%Y-%m-%d}<br>排名: %{y}<extra></extra>',
                text=df['股票名称'] if '股票名称' in df.columns else ''
            ))

            # 反转 Y 轴，因为排名越小越好
            fig.update_yaxis(autorange="reversed")

        # 如果有净买入额，绘制净买入变化
        if '净买入' in df.columns or '龙虎榜净买入' in df.columns:
            net_buy_col = '净买入' if '净买入' in df.columns else '龙虎榜净买入'
            fig.add_trace(go.Scatter(
                x=df['日期'],
                y=df[net_buy_col] / 100000000,  # 转换为亿元
                mode='lines+markers',
                name='净买入 (亿元)',
                line=dict(color='#764ba2', width=2),
                marker=dict(size=8),
                yaxis='y2',
                hovertemplate='<b>%{text}</b><br>日期: %{x|%Y-%m-%d}<br>净买入: ¥%{y:.2f}亿<extra></extra>',
                text=df['股票名称'] if '股票名称' in df.columns else ''
            ))

            # 添加第二个 Y 轴
            fig.update_layout(
                yaxis2=dict(
                    title="净买入 (亿元)",
                    overlaying='y',
                    side='right'
                )
            )

        fig.update_layout(
            title_text=f"龙虎榜排名变化 - {stock_name or '全部股票'}",
            xaxis_title="日期",
            yaxis_title="排名",
            hovermode='closest',
            height=500,
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        logger.info(f"成功生成排名时间序列图")
        return fig

    except Exception as e:
        logger.error(f"生成排名时间序列图失败: {e}")
        return None


def plot_performance_timeseries(df_operations: pd.DataFrame, capital_name: str = None) -> go.Figure:
    """
    游资业绩表现时间序列图

    Args:
        df_operations: 游资操作数据 DataFrame
        capital_name: 游资名称 (可选)

    Returns:
        Plotly Figure 对象
    """
    try:
        if df_operations.empty:
            logger.warning("操作数据为空，无法生成业绩时间序列图")
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

        # 按日期排序
        df = df.sort_values('日期')

        # 按日期聚合数据
        df_daily = df.groupby('日期').agg({
            '买入金额': 'sum',
            '卖出金额': 'sum',
            '净买入': lambda x: x.sum()
        }).reset_index()

        # 计算累计净买入
        df_daily['累计净买入'] = df_daily['净买入'].cumsum() / 100000000  # 转换为亿元
        df_daily['当日净买入'] = df_daily['净买入'] / 100000000

        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('累计净买入趋势', '每日净买入'),
            vertical_spacing=0.1
        )

        # 累计净买入
        fig.add_trace(
            go.Scatter(
                x=df_daily['日期'],
                y=df_daily['累计净买入'],
                mode='lines+markers',
                name='累计净买入',
                line=dict(color='#667eea', width=2),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.2)'
            ),
            row=1, col=1
        )

        # 每日净买入
        colors = ['rgba(76, 175, 80, 0.8)' if x > 0 else 'rgba(244, 67, 54, 0.8)'
                  for x in df_daily['当日净买入']]

        fig.add_trace(
            go.Bar(
                x=df_daily['日期'],
                y=df_daily['当日净买入'],
                name='每日净买入',
                marker_color=colors
            ),
            row=2, col=1
        )

        fig.update_layout(
            title_text=f"游资业绩表现 - {capital_name or '全部游资'}",
            height=700,
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="累计净买入 (亿元)", row=1, col=1)
        fig.update_yaxes(title_text="每日净买入 (亿元)", row=2, col=1)

        logger.info(f"成功生成业绩时间序列图")
        return fig

    except Exception as e:
        logger.error(f"生成业绩时间序列图失败: {e}")
        return None