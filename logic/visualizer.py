"""
数据可视化增强模块
提供高级图表展示功能
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


class AdvancedVisualizer:
    """高级可视化器"""

    @staticmethod
    def create_radar_chart(categories, values, title="雷达图"):
        """
        创建雷达图
        
        Args:
            categories: 类别列表
            values: 数值列表
            title: 图表标题
        """
        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='数值',
            line_color='rgb(0, 100, 255)',
            fillcolor='rgba(0, 100, 255, 0.3)'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) * 1.2]
                )
            ),
            showlegend=True,
            title=title,
            height=500
        )

        return fig

    @staticmethod
    def create_heatmap(data, title="热力图"):
        """
        创建热力图
        
        Args:
            data: DataFrame数据
            title: 图表标题
        """
        fig = go.Figure(data=go.Heatmap(
            z=data.values,
            x=data.columns,
            y=data.index,
            colorscale='Viridis',
            showscale=True
        ))

        fig.update_layout(
            title=title,
            height=600
        )

        return fig

    @staticmethod
    def create_trend_chart(dates, values, title="趋势图", line_name="趋势"):
        """
        创建趋势图
        
        Args:
            dates: 日期列表
            values: 数值列表
            title: 图表标题
            line_name: 线条名称
        """
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name=line_name,
            line=dict(color='rgb(0, 100, 255)', width=2),
            marker=dict(size=6)
        ))

        # 添加平均线
        avg_value = sum(values) / len(values)
        fig.add_hline(y=avg_value, line_dash="dash", line_color="red",
                     annotation_text=f"平均值: {avg_value:.2f}")

        fig.update_layout(
            title=title,
            xaxis_title="日期",
            yaxis_title="数值",
            height=400
        )

        return fig

    @staticmethod
    def create_multi_line_chart(data_dict, title="多线图"):
        """
        创建多线图
        
        Args:
            data_dict: 字典格式，键为线条名称，值为(x, y)元组
            title: 图表标题
        """
        fig = go.Figure()

        colors = ['rgb(0, 100, 255)', 'rgb(255, 100, 0)', 'rgb(0, 200, 100)',
                 'rgb(200, 0, 100)', 'rgb(100, 100, 100)']

        for idx, (name, (x, y)) in enumerate(data_dict.items()):
            fig.add_trace(go.Scatter(
                x=x,
                y=y,
                mode='lines+markers',
                name=name,
                line=dict(color=colors[idx % len(colors)], width=2),
                marker=dict(size=6)
            ))

        fig.update_layout(
            title=title,
            xaxis_title="日期",
            yaxis_title="数值",
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    @staticmethod
    def create_sankey_diagram(labels, source, target, value, title="桑基图"):
        """
        创建桑基图
        
        Args:
            labels: 节点标签列表
            source: 源节点索引列表
            target: 目标节点索引列表
            value: 数值列表
            title: 图表标题
        """
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color="blue"
            ),
            link=dict(
                source=source,
                target=target,
                value=value
            )
        )])

        fig.update_layout(
            title_text=title,
            font_size=10,
            height=700
        )

        return fig

    @staticmethod
    def create_gauge_chart(value, title="仪表盘", min_val=0, max_val=100):
        """
        创建仪表盘图
        
        Args:
            value: 当前值
            title: 图表标题
            min_val: 最小值
            max_val: 最大值
        """
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': (max_val + min_val) / 2},
            gauge={
                'axis': {'range': [min_val, max_val]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [min_val, min_val + (max_val - min_val) * 0.3], 'color': "lightgray"},
                    {'range': [min_val + (max_val - min_val) * 0.3, min_val + (max_val - min_val) * 0.7], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': min_val + (max_val - min_val) * 0.9
                }
            }
        ))

        fig.update_layout(height=400)

        return fig

    @staticmethod
    def create_funnel_chart(labels, values, title="漏斗图"):
        """
        创建漏斗图
        
        Args:
            labels: 标签列表
            values: 数值列表
            title: 图表标题
        """
        fig = go.Figure(go.Funnel(
            y=labels,
            x=values,
            textinfo="value+percent initial",
            marker={"color": ["deepskyblue", "lightsalmon", "tan", "teal", "gold"],
                   "line": {"color": ["wheat", "wheat", "wheat", "wheat", "wheat"], "width": 3}}
        ))

        fig.update_layout(
            title=title,
            height=500
        )

        return fig

    @staticmethod
    def create_3d_scatter(x, y, z, labels, title="3D散点图"):
        """
        创建3D散点图
        
        Args:
            x: x坐标列表
            y: y坐标列表
            z: z坐标列表
            labels: 点标签列表
            title: 图表标题
        """
        fig = go.Figure(data=[go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(
                size=8,
                color=z,
                colorscale='Viridis',
                opacity=0.8
            ),
            text=labels,
            hovertemplate='<b>%{text}</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>'
        )])

        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='X轴',
                yaxis_title='Y轴',
                zaxis_title='Z轴'
            ),
            height=600
        )

        return fig

    @staticmethod
    def create_candlestick_with_volume(df, title="K线图"):
        """
        创建带成交量的K线图
        
        Args:
            df: 包含OHLCV数据的DataFrame
            title: 图表标题
        """
        fig = go.Figure()

        # K线图
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线'
        ))

        # 成交量
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['volume'],
            name='成交量',
            yaxis='y2',
            marker_color='rgba(0, 100, 255, 0.5)'
        ))

        fig.update_layout(
            title=title,
            xaxis_rangeslider_visible=False,
            yaxis=dict(
                title='价格',
                side='left'
            ),
            yaxis2=dict(
                title='成交量',
                side='right',
                overlaying='y',
                showgrid=False
            ),
            height=600
        )

        return fig

    @staticmethod
    def create_correlation_heatmap(df, title="相关性热力图"):
        """
        创建相关性热力图
        
        Args:
            df: DataFrame数据
            title: 图表标题
        """
        corr_matrix = df.corr()

        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu',
            zmid=0,
            showscale=True,
            text=corr_matrix.values.round(2),
            texttemplate='%{text}',
            textfont={"size": 10}
        ))

        fig.update_layout(
            title=title,
            height=600
        )

        return fig