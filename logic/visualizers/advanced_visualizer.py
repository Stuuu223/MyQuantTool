"""
可视化增强模块

功能：
- 3D图表展示多维数据关系
- 交互式策略分析界面
- 实时资金流向可视化
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

try:
    import plotly
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("警告: 未安装plotly，部分高级可视化功能将受限")

try:
    import dash
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    print("警告: 未安装dash，交互式界面功能将受限")


class AdvancedVisualizer:
    """高级可视化器"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')  # 使用seaborn样式
    
    def plot_3d_parameter_space(self, 
                               optimization_results: List[Dict], 
                               metric_name: str = 'sharpe_ratio',
                               figsize: tuple = (12, 9)) -> None:
        """
        3D参数空间可视化
        
        Args:
            optimization_results: 优化结果列表，每个元素包含参数和指标值
            metric_name: 用于可视化的指标名称
            figsize: 图表大小
        """
        if not optimization_results:
            print("没有优化结果可显示")
            return
        
        # 提取参数和指标值
        params = []
        values = []
        
        for result in optimization_results:
            if isinstance(result, tuple) and len(result) == 2:
                param_dict, metric_value = result
            else:
                param_dict = result.get('params', {})
                metric_value = result.get(metric_name, 0)
            
            params.append(param_dict)
            values.append(metric_value)
        
        if len(params) < 1:
            print("参数数据不足，无法生成3D图")
            return
        
        # 尝试找到三个不同的参数用于3D可视化
        param_names = list(params[0].keys())
        if len(param_names) < 2:
            print("参数数量不足，无法生成3D图")
            return
        
        # 选择前三个参数（如果有）用于3D图
        if len(param_names) >= 3:
            x_param = param_names[0]
            y_param = param_names[1]
            z_param = param_names[2]
            
            x_vals = [p.get(x_param, 0) for p in params]
            y_vals = [p.get(y_param, 0) for p in params]
            z_vals = [p.get(z_param, 0) for p in params]
            
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111, projection='3d')
            
            scatter = ax.scatter(x_vals, y_vals, z_vals, c=values, cmap='viridis', s=60)
            
            ax.set_xlabel(x_param)
            ax.set_ylabel(y_param)
            ax.set_zlabel(z_param)
            ax.set_title(f'3D参数空间 - {metric_name} 分布')
            
            plt.colorbar(scatter, ax=ax, label=metric_name)
            plt.tight_layout()
            plt.show()
        else:
            # 如果只有两个参数，创建2D散点图用颜色表示指标值
            x_param = param_names[0]
            y_param = param_names[1] if len(param_names) > 1 else 'index'
            
            if y_param == 'index':
                x_vals = [p.get(x_param, 0) for p in params]
                y_vals = list(range(len(params)))
            else:
                x_vals = [p.get(x_param, 0) for p in params]
                y_vals = [p.get(y_param, 0) for p in params]
            
            plt.figure(figsize=figsize[:2])
            scatter = plt.scatter(x_vals, y_vals, c=values, cmap='viridis', s=60)
            
            plt.xlabel(x_param)
            plt.ylabel(y_param)
            plt.title(f'2D参数空间 - {metric_name} 分布')
            
            plt.colorbar(scatter, label=metric_name)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
    
    def plot_3d_strategy_performance(self, 
                                    comparison_df: pd.DataFrame,
                                    x_metric: str = 'sharpe_ratio',
                                    y_metric: str = 'total_return',
                                    z_metric: str = 'max_drawdown',
                                    figsize: tuple = (12, 9)) -> None:
        """
        3D策略性能对比
        
        Args:
            comparison_df: 策略对比结果DataFrame
            x_metric: X轴指标
            y_metric: Y轴指标
            z_metric: Z轴指标
            figsize: 图表大小
        """
        if comparison_df.empty:
            print("没有对比数据可显示")
            return
        
        # 检查指标列是否存在
        available_metrics = [col for col in [x_metric, y_metric, z_metric] if col in comparison_df.columns]
        if len(available_metrics) < 3:
            print(f"指定的指标列不全存在，可用: {list(comparison_df.columns)}")
            # 使用默认指标
            x_metric, y_metric, z_metric = 'sharpe_ratio', 'total_return', 'max_drawdown'
        
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        x_vals = comparison_df[x_metric]
        y_vals = comparison_df[y_metric]
        z_vals = comparison_df[z_metric]
        labels = comparison_df['strategy_name']
        
        scatter = ax.scatter(x_vals, y_vals, z_vals, c=range(len(labels)), cmap='tab10', s=100)
        
        ax.set_xlabel(x_metric)
        ax.set_ylabel(y_metric)
        ax.set_zlabel(z_metric)
        ax.set_title('3D策略性能对比')
        
        # 添加标签
        for i, label in enumerate(labels):
            ax.text(x_vals.iloc[i], y_vals.iloc[i], z_vals.iloc[i], label, size=8)
        
        plt.tight_layout()
        plt.show()
    
    def plot_3d_market_sentiment(self,
                                sentiment_data: pd.DataFrame,
                                figsize: tuple = (12, 9)) -> None:
        """
        3D市场情绪分析
        
        Args:
            sentiment_data: 情绪数据DataFrame，应包含时间序列和多种情绪指标
            figsize: 图表大小
        """
        if sentiment_data.empty:
            print("没有情绪数据可显示")
            return
        
        required_cols = ['news_sentiment', 'social_sentiment', 'market_sentiment']
        available_cols = [col for col in required_cols if col in sentiment_data.columns]
        
        if len(available_cols) < 2:
            print("情绪数据列不足")
            return
        
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # 如果有时间列，将其作为Z轴
        if 'timestamp' in sentiment_data.columns or 'date' in sentiment_data.columns:
            time_col = 'timestamp' if 'timestamp' in sentiment_data.columns else 'date'
            x_vals = sentiment_data[available_cols[0]] if len(available_cols) > 0 else [0] * len(sentiment_data)
            y_vals = sentiment_data[available_cols[1]] if len(available_cols) > 1 else [0] * len(sentiment_data)
            z_vals = pd.to_datetime(sentiment_data[time_col]).map(datetime.timestamp)
        else:
            # 否则使用索引作为Z轴
            x_vals = sentiment_data[available_cols[0]] if len(available_cols) > 0 else [0] * len(sentiment_data)
            y_vals = sentiment_data[available_cols[1]] if len(available_cols) > 1 else [0] * len(sentiment_data)
            z_vals = list(range(len(sentiment_data)))
        
        scatter = ax.scatter(x_vals, y_vals, z_vals, c=sentiment_data[available_cols[0]] if available_cols else [0], 
                           cmap='RdYlGn', s=30, alpha=0.7)
        
        ax.set_xlabel(available_cols[0] if len(available_cols) > 0 else 'X')
        ax.set_ylabel(available_cols[1] if len(available_cols) > 1 else 'Y')
        ax.set_zlabel('Time' if 'timestamp' in sentiment_data.columns or 'date' in sentiment_data.columns else 'Index')
        ax.set_title('3D市场情绪分析')
        
        plt.colorbar(scatter, ax=ax, label=available_cols[0] if available_cols else 'Value')
        plt.tight_layout()
        plt.show()
    
    def plot_correlation_3d(self, data: pd.DataFrame, figsize: tuple = (12, 9)) -> None:
        """
        3D相关性分析
        
        Args:
            data: 数据DataFrame
            figsize: 图表大小
        """
        if data.empty or len(data.columns) < 3:
            print("数据列数不足，无法进行3D相关性分析")
            return
        
        # 计算相关性矩阵
        corr_matrix = data.select_dtypes(include=[np.number]).corr()
        
        if corr_matrix.shape[0] < 3:
            print("数值列数不足，无法进行3D相关性分析")
            return
        
        # 选择相关性最高的三个变量
        corr_values = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                for k in range(j+1, len(corr_matrix.columns)):
                    col1, col2, col3 = corr_matrix.columns[i], corr_matrix.columns[j], corr_matrix.columns[k]
                    r12 = corr_matrix.iloc[i, j]
                    r13 = corr_matrix.iloc[i, k]
                    r23 = corr_matrix.iloc[j, k]
                    # 使用平均相关性作为Z值
                    avg_corr = (abs(r12) + abs(r13) + abs(r23)) / 3
                    corr_values.append([r12, r13, r23, avg_corr, col1, col2, col3])
        
        if not corr_values:
            print("无法计算变量间相关性")
            return
        
        # 转换为DataFrame并选择相关性最高的组合
        corr_df = pd.DataFrame(corr_values, columns=['r12', 'r13', 'r23', 'avg_corr', 'col1', 'col2', 'col3'])
        top_combination = corr_df.loc[corr_df['avg_corr'].idxmax()]
        
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # 使用实际数据值进行3D散点图
        x_data = data[top_combination['col1']].dropna()
        y_data = data[top_combination['col2']].dropna()
        z_data = data[top_combination['col3']].dropna()
        
        # 确保三个系列长度一致
        min_len = min(len(x_data), len(y_data), len(z_data))
        x_data = x_data[:min_len]
        y_data = y_data[:min_len]
        z_data = z_data[:min_len]
        
        scatter = ax.scatter(x_data, y_data, z_data, c=range(min_len), cmap='viridis', s=30)
        
        ax.set_xlabel(top_combination['col1'])
        ax.set_ylabel(top_combination['col2'])
        ax.set_zlabel(top_combination['col3'])
        ax.set_title(f'3D相关性分析: {top_combination["col1"]} vs {top_combination["col2"]} vs {top_combination["col3"]}')
        
        plt.colorbar(scatter, ax=ax, label='Index')
        plt.tight_layout()
        plt.show()
    
    def plot_interactive_3d_scatter(self, 
                                   x_data: List[float], 
                                   y_data: List[float], 
                                   z_data: List[float], 
                                   colors: Optional[List[float]] = None,
                                   labels: Optional[List[str]] = None,
                                   title: str = "3D Scatter Plot") -> None:
        """
        绘制交互式3D散点图（使用Plotly）
        
        Args:
            x_data: X轴数据
            y_data: Y轴数据
            z_data: Z轴数据
            colors: 颜色数据
            labels: 标签数据
            title: 图表标题
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用交互式图表")
            return
        
        fig = go.Figure(data=[go.Scatter3d(
            x=x_data,
            y=y_data,
            z=z_data,
            mode='markers',
            marker=dict(
                size=5,
                color=colors if colors is not None else z_data,
                colorscale='Viridis',
                opacity=0.8
            ),
            text=labels if labels is not None else None,
            hovertemplate='<b>%{text}</b><br>X: %{x}<br>Y: %{y}<br>Z: %{z}<extra></extra>' if labels is not None else None
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            width=800,
            height=600
        )
        
        fig.show()
    
    def plot_interactive_surface(self, 
                                x_range: Tuple[float, float, int], 
                                y_range: Tuple[float, float, int], 
                                z_function: callable,
                                title: str = "3D Surface Plot") -> None:
        """
        绘制交互式3D表面图
        
        Args:
            x_range: (min, max, num_points) for X axis
            y_range: (min, max, num_points) for Y axis
            z_function: 接受(x,y)返回z值的函数
            title: 图表标题
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用交互式图表")
            return
        
        x = np.linspace(x_range[0], x_range[1], x_range[2])
        y = np.linspace(y_range[0], y_range[1], y_range[2])
        X, Y = np.meshgrid(x, y)
        
        # 计算Z值
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                Z[i, j] = z_function(X[i, j], Y[i, j])
        
        fig = go.Figure(data=[go.Surface(x=X, y=Y, z=Z)])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            width=800,
            height=600
        )
        
        fig.show()


class InteractiveAnalyzer:
    """交互式分析器"""
    
    def __init__(self):
        if not DASH_AVAILABLE:
            print("警告: Dash不可用，交互式分析界面功能受限")
    
    def create_strategy_analysis_dashboard(self, 
                                         comparison_data: pd.DataFrame, 
                                         strategy_results: Dict[str, Any],
                                         title: str = "策略分析仪表板") -> Optional[Any]:
        """
        创建策略分析仪表板
        
        Args:
            comparison_data: 策略对比数据
            strategy_results: 策略结果字典
            title: 仪表板标题
            
        Returns:
            Dash app对象
        """
        if not DASH_AVAILABLE:
            print("Dash不可用，无法创建交互式仪表板")
            return None
        
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.H1(title, style={'text-align': 'center'}),
            
            html.Div([
                html.H2("策略性能对比"),
                dcc.Graph(
                    id='performance-comparison',
                    figure={
                        'data': [
                            {'x': comparison_data['strategy_name'], 'y': comparison_data['sharpe_ratio'], 
                             'type': 'bar', 'name': '夏普比率'},
                            {'x': comparison_data['strategy_name'], 'y': comparison_data['total_return'], 
                             'type': 'bar', 'name': '总收益率'}
                        ],
                        'layout': {
                            'title': '策略性能对比',
                            'xaxis': {'title': '策略'},
                            'yaxis': {'title': '指标值'}
                        }
                    }
                )
            ]),
            
            html.Div([
                html.H2("风险指标"),
                dcc.Graph(
                    id='risk-metrics',
                    figure={
                        'data': [
                            {'x': comparison_data['strategy_name'], 'y': comparison_data['max_drawdown'], 
                             'type': 'bar', 'name': '最大回撤', 'marker': {'color': 'red'}}
                        ],
                        'layout': {
                            'title': '最大回撤对比',
                            'xaxis': {'title': '策略'},
                            'yaxis': {'title': '回撤'}
                        }
                    }
                )
            ]),
            
            html.Div([
                html.H2("参数影响分析"),
                dcc.Dropdown(
                    id='metric-dropdown',
                    options=[
                        {'label': '夏普比率', 'value': 'sharpe_ratio'},
                        {'label': '总收益率', 'value': 'total_return'},
                        {'label': '最大回撤', 'value': 'max_drawdown'},
                        {'label': '胜率', 'value': 'win_rate'}
                    ],
                    value='sharpe_ratio'
                ),
                dcc.Graph(id='parameter-impact')
            ])
        ])
        
        @app.callback(
            Output('parameter-impact', 'figure'),
            [Input('metric-dropdown', 'value')]
        )
        def update_parameter_impact(selected_metric):
            fig = {
                'data': [{
                    'x': comparison_data['strategy_name'],
                    'y': comparison_data[selected_metric],
                    'type': 'bar',
                    'name': selected_metric
                }],
                'layout': {
                    'title': f'{selected_metric} 对比',
                    'xaxis': {'title': '策略'},
                    'yaxis': {'title': selected_metric}
                }
            }
            return fig
        
        return app
    
    def create_market_sentiment_dashboard(self, 
                                        sentiment_data: pd.DataFrame,
                                        title: str = "市场情绪分析仪表板") -> Optional[Any]:
        """
        创建市场情绪分析仪表板
        
        Args:
            sentiment_data: 情绪数据
            title: 仪表板标题
            
        Returns:
            Dash app对象
        """
        if not DASH_AVAILABLE:
            print("Dash不可用，无法创建交互式仪表板")
            return None
        
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.H1(title, style={'text-align': 'center'}),
            
            html.Div([
                html.H2("情绪指标趋势"),
                dcc.Graph(
                    id='sentiment-trend',
                    figure={
                        'data': [
                            go.Scatter(
                                x=sentiment_data.index,
                                y=sentiment_data[col],
                                mode='lines+markers',
                                name=col
                            ) for col in sentiment_data.columns 
                            if col not in ['timestamp', 'date']
                        ],
                        'layout': go.Layout(
                            title='情绪指标趋势',
                            xaxis={'title': '时间'},
                            yaxis={'title': '情绪分数'}
                        )
                    }
                )
            ])
        ])
        
        return app


class RealTimeFundFlowVisualizer:
    """实时资金流向可视化器"""
    
    def __init__(self):
        self.flow_history = []
    
    def plot_fund_flow_3d(self, 
                         flow_data: pd.DataFrame,
                         figsize: tuple = (12, 9)) -> None:
        """
        3D资金流向可视化
        
        Args:
            flow_data: 资金流向数据，应包含时间、大单流向、中单流向、小单流向等
            figsize: 图表大小
        """
        if flow_data.empty:
            print("没有资金流向数据可显示")
            return
        
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # 检查必需的列
        required_cols = ['timestamp', 'large_net_flow', 'medium_net_flow', 'small_net_flow']
        available_cols = [col for col in required_cols if col in flow_data.columns]
        
        if len(available_cols) < 4:
            print(f"缺少必要的资金流向数据列，需要: {required_cols}")
            return
        
        # 将时间转换为数值
        time_numeric = pd.to_datetime(flow_data['timestamp']).map(datetime.timestamp)
        large_flow = flow_data['large_net_flow']
        medium_flow = flow_data['medium_net_flow']
        small_flow = flow_data['small_net_flow']
        
        # 创建3D散点图
        scatter = ax.scatter(
            large_flow, 
            medium_flow, 
            small_flow, 
            c=time_numeric, 
            cmap='plasma', 
            s=50, 
            alpha=0.7
        )
        
        ax.set_xlabel('大单净流入')
        ax.set_ylabel('中单净流入')
        ax.set_zlabel('小单净流入')
        ax.set_title('3D资金流向分析')
        
        plt.colorbar(scatter, ax=ax, label='时间')
        plt.tight_layout()
        plt.show()
    
    def plot_interactive_fund_flow_heatmap(self, flow_data: pd.DataFrame) -> None:
        """
        绘制交互式资金流向热力图
        
        Args:
            flow_data: 资金流向数据
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用交互式图表")
            return
        
        if flow_data.empty:
            print("没有资金流向数据可显示")
            return
        
        # 选择数值列
        numeric_cols = flow_data.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            print("需要至少2个数值列才能生成热力图")
            return
        
        # 计算相关性矩阵
        corr_matrix = flow_data[numeric_cols].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0
        ))
        
        fig.update_layout(
            title='资金流向相关性热力图',
            xaxis_title='指标',
            yaxis_title='指标',
            width=800,
            height=600
        )
        
        fig.show()
    
    def animate_fund_flow(self, flow_data: pd.DataFrame, window_size: int = 20) -> None:
        """
        动态展示资金流向变化
        
        Args:
            flow_data: 资金流向数据
            window_size: 动画窗口大小
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用动画图表")
            return
        
        if flow_data.empty or len(flow_data) < window_size:
            print("数据不足，无法生成动画")
            return
        
        # 准备动画数据
        frames = []
        for i in range(window_size, len(flow_data)):
            window_data = flow_data.iloc[i-window_size:i]
            
            frame_data = go.Scatter3d(
                x=window_data.get('large_net_flow', [0] * len(window_data)),
                y=window_data.get('medium_net_flow', [0] * len(window_data)),
                z=window_data.get('small_net_flow', [0] * len(window_data)),
                mode='lines+markers',
                name=f'Window {i}'
            )
            
            frames.append(go.Frame(data=[frame_data], name=f'Frame{i}'))
        
        # 创建基础图表
        fig = go.Figure(
            data=[go.Scatter3d(
                x=flow_data.get('large_net_flow', [0] * len(flow_data))[:window_size],
                y=flow_data.get('medium_net_flow', [0] * len(flow_data))[:window_size],
                z=flow_data.get('small_net_flow', [0] * len(flow_data))[:window_size],
                mode='lines+markers'
            )],
            layout=go.Layout(
                title='资金流向动态变化',
                scene=dict(
                    xaxis_title='大单净流入',
                    yaxis_title='中单净流入',
                    zaxis_title='小单净流入'
                ),
                updatemenus=[dict(
                    type='buttons',
                    showactive=False,
                    buttons=[dict(label='Play',
                                  method='animate',
                                  args=[None, dict(frame=dict(duration=500, redraw=True), 
                                                  fromcurrent=True, mode='immediate')])
                    ]
                )],
                sliders=[dict(
                    steps=[],
                    currentvalue={'prefix': 'Frame:'}
                )]
            ),
            frames=frames
        )
        
        fig.show()


# 使用示例
def demo_advanced_visualization():
    """演示高级可视化功能"""
    print("=== 高级可视化演示 ===")
    
    visualizer = AdvancedVisualizer()
    
    # 生成示例数据
    np.random.seed(42)
    n_points = 100
    
    # 示例1: 3D参数空间可视化
    print("\n1. 3D参数空间可视化")
    optimization_results = []
    for i in range(n_points):
        params = {
            'param1': np.random.uniform(0, 10),
            'param2': np.random.uniform(0, 5),
            'param3': np.random.uniform(1, 3)
        }
        # 模拟指标值，与参数有一定关系
        metric_value = params['param1'] * 0.3 + params['param2'] * 0.5 - params['param3'] * 0.2 + np.random.normal(0, 0.5)
        optimization_results.append((params, metric_value))
    
    visualizer.plot_3d_parameter_space(optimization_results, 'sharpe_ratio')
    
    # 示例2: 3D策略性能对比 (使用模拟数据)
    print("\n2. 3D策略性能对比")
    comparison_data = pd.DataFrame({
        'strategy_name': [f'Strategy_{i}' for i in range(8)],
        'sharpe_ratio': np.random.uniform(0.5, 2.5, 8),
        'total_return': np.random.uniform(0.1, 0.5, 8),
        'max_drawdown': np.random.uniform(-0.1, -0.3, 8),
        'win_rate': np.random.uniform(0.4, 0.7, 8)
    })
    
    visualizer.plot_3d_strategy_performance(comparison_data)
    
    # 示例3: 3D相关性分析
    print("\n3. 3D相关性分析")
    sample_data = pd.DataFrame({
        'price': 100 + np.cumsum(np.random.normal(0, 1, 50)),
        'volume': np.random.exponential(1000000, 50),
        'rsi': np.random.uniform(20, 80, 50),
        'macd': np.random.normal(0, 0.1, 50)
    })
    
    visualizer.plot_correlation_3d(sample_data)
    
    # 如果Plotly可用，演示交互式图表
    if PLOTLY_AVAILABLE:
        print("\n4. 交互式3D散点图")
        x_data = np.random.randn(100)
        y_data = np.random.randn(100)
        z_data = np.random.randn(100)
        colors = np.random.rand(100)
        
        visualizer.plot_interactive_3d_scatter(
            x_data, y_data, z_data, colors, 
            labels=[f'Point_{i}' for i in range(100)],
            title="交互式3D散点图示例"
        )
    
    # 演示实时资金流向可视化
    print("\n5. 3D资金流向可视化")
    fund_flow_data = pd.DataFrame({
        'timestamp': pd.date_range(end=datetime.now(), periods=50, freq='D'),
        'large_net_flow': np.random.normal(1000000, 500000, 50),
        'medium_net_flow': np.random.normal(500000, 200000, 50),
        'small_net_flow': np.random.normal(200000, 100000, 50),
        'total_flow': np.random.normal(1700000, 600000, 50)
    })
    
    fund_visualizer = RealTimeFundFlowVisualizer()
    fund_visualizer.plot_fund_flow_3d(fund_flow_data)


if __name__ == "__main__":
    demo_advanced_visualization()
