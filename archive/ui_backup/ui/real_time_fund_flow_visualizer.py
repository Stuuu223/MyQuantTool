"""
实时资金流向可视化模块

功能：
- 实时资金流向图表
- 多维度资金流向分析
- 大单、中单、小单流向可视化
- 资金流向热力图
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import warnings
warnings.filterwarnings('ignore')

try:
    import plotly
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("警告: 未安装plotly，部分高级可视化功能将受限")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: 未安装akshare，部分实时数据获取功能将受限")


class RealTimeFundFlowVisualizer:
    """实时资金流向可视化器"""
    
    def __init__(self):
        self.flow_history = []
        self.current_data = None
    
    def generate_mock_fund_flow_data(self, periods: int = 100) -> pd.DataFrame:
        """
        生成模拟资金流向数据
        
        Args:
            periods: 数据点数量
            
        Returns:
            资金流向DataFrame
        """
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='30min')  # 30分钟频率
        
        # 生成模拟资金流向数据
        np.random.seed(42)
        
        # 大单、中单、小单净流入（可以为正也可以为负）
        large_net_flow = np.random.normal(500000, 300000, periods)
        medium_net_flow = np.random.normal(200000, 150000, periods)
        small_net_flow = np.random.normal(100000, 80000, periods)
        
        # 累计资金流向
        cumulative_large = np.cumsum(large_net_flow)
        cumulative_medium = np.cumsum(medium_net_flow)
        cumulative_small = np.cumsum(small_net_flow)
        
        # 计算主力资金（大单+中单）
        main_net_flow = large_net_flow + medium_net_flow
        cumulative_main = cumulative_large + cumulative_medium
        
        # 计算总资金流
        total_net_flow = large_net_flow + medium_net_flow + small_net_flow
        cumulative_total = np.cumsum(total_net_flow)
        
        data = pd.DataFrame({
            'datetime': dates,
            'large_net_flow': large_net_flow,
            'medium_net_flow': medium_net_flow,
            'small_net_flow': small_net_flow,
            'main_net_flow': main_net_flow,  # 主力资金
            'total_net_flow': total_net_flow,
            'cumulative_large': cumulative_large,
            'cumulative_medium': cumulative_medium,
            'cumulative_small': cumulative_small,
            'cumulative_main': cumulative_main,
            'cumulative_total': cumulative_total,
            'flow_balance': large_net_flow - small_net_flow,  # 大单vs小单平衡
        })
        
        return data
    
    def plot_fund_flow_time_series(self, 
                                  data: pd.DataFrame, 
                                  chart_type: str = 'net_flow',
                                  figsize: tuple = (15, 10)) -> None:
        """
        绘制资金流向时间序列图
        
        Args:
            data: 资金流向数据
            chart_type: 图表类型 ('net_flow', 'cumulative', 'balance')
            figsize: 图表大小
        """
        fig, axes = plt.subplots(2, 1, figsize=figsize)
        
        if chart_type == 'net_flow':
            # 净流入时间序列
            axes[0].plot(data['datetime'], data['large_net_flow'], label='大单净流入', alpha=0.7)
            axes[0].plot(data['datetime'], data['medium_net_flow'], label='中单净流入', alpha=0.7)
            axes[0].plot(data['datetime'], data['small_net_flow'], label='小单净流入', alpha=0.7)
            axes[0].plot(data['datetime'], data['total_net_flow'], label='总净流入', linewidth=2)
            
            axes[0].set_title('资金净流入时间序列')
            axes[0].set_ylabel('净流入金额')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # 成交量对比
            axes[1].bar(data['datetime'], data['total_net_flow'], alpha=0.6, 
                       color=['green' if x > 0 else 'red' for x in data['total_net_flow']])
            axes[1].set_title('净流入柱状图（绿色流入，红色流出）')
            axes[1].set_ylabel('净流入金额')
            axes[1].grid(True, alpha=0.3)
        
        elif chart_type == 'cumulative':
            # 累计资金流向
            axes[0].plot(data['datetime'], data['cumulative_large'], label='大单累计', alpha=0.7)
            axes[0].plot(data['datetime'], data['cumulative_medium'], label='中单累计', alpha=0.7)
            axes[0].plot(data['datetime'], data['cumulative_small'], label='小单累计', alpha=0.7)
            axes[0].plot(data['datetime'], data['cumulative_main'], label='主力累计', linewidth=2)
            
            axes[0].set_title('累计资金流向')
            axes[0].set_ylabel('累计金额')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # 总累计
            axes[1].plot(data['datetime'], data['cumulative_total'], label='总累计资金', linewidth=2, color='purple')
            axes[1].set_title('总累计资金流向')
            axes[1].set_ylabel('累计金额')
            axes[1].set_xlabel('时间')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        
        elif chart_type == 'balance':
            # 资金平衡（大单vs小单）
            axes[0].plot(data['datetime'], data['flow_balance'], label='大单-小单净额', linewidth=2)
            axes[0].axhline(y=0, color='black', linestyle='--', alpha=0.5)
            
            axes[0].set_title('大单与小单资金平衡')
            axes[0].set_ylabel('资金差额')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # 主力资金占比
            total_flow_abs = np.abs(data['large_net_flow']) + np.abs(data['medium_net_flow']) + np.abs(data['small_net_flow'])
            large_ratio = np.abs(data['large_net_flow']) / (total_flow_abs + 1e-10)  # 避免除零
            medium_ratio = np.abs(data['medium_net_flow']) / (total_flow_abs + 1e-10)
            small_ratio = np.abs(data['small_net_flow']) / (total_flow_abs + 1e-10)
            
            axes[1].plot(data['datetime'], large_ratio, label='大单占比', alpha=0.7)
            axes[1].plot(data['datetime'], medium_ratio, label='中单占比', alpha=0.7)
            axes[1].plot(data['datetime'], small_ratio, label='小单占比', alpha=0.7)
            
            axes[1].set_title('各类型资金占比')
            axes[1].set_ylabel('占比')
            axes[1].set_xlabel('时间')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_interactive_fund_flow(self, data: pd.DataFrame):
        """
        绘制交互式资金流向图
        
        Args:
            data: 资金流向数据
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用交互式图表")
            return
        
        # 创建子图
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('资金净流入', '累计资金流向', '资金平衡分析')
        )
        
        # 净流入
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['large_net_flow'], 
                      mode='lines', name='大单净流入', line=dict(color='red')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['medium_net_flow'], 
                      mode='lines', name='中单净流入', line=dict(color='orange')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['small_net_flow'], 
                      mode='lines', name='小单净流入', line=dict(color='blue')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['total_net_flow'], 
                      mode='lines', name='总净流入', line=dict(color='black', width=2)),
            row=1, col=1
        )
        
        # 累计资金
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_large'], 
                      mode='lines', name='大单累计', line=dict(color='red'), showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_medium'], 
                      mode='lines', name='中单累计', line=dict(color='orange'), showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_small'], 
                      mode='lines', name='小单累计', line=dict(color='blue'), showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_total'], 
                      mode='lines', name='总累计', line=dict(color='purple', width=2), showlegend=False),
            row=2, col=1
        )
        
        # 资金平衡
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['flow_balance'], 
                      mode='lines', name='大单-小单净额', line=dict(color='green', width=2)),
            row=3, col=1
        )
        fig.add_hline(y=0, line_dash="dash", line_color="black", row=3, col=1)
        
        fig.update_layout(
            height=900,
            title_text="实时资金流向分析",
            xaxis_title="时间",
            showlegend=True
        )
        
        fig.show()
    
    def plot_fund_flow_heatmap(self, data: pd.DataFrame, agg_period: str = 'D'):
        """
        绘制资金流向热力图
        
        Args:
            data: 资金流向数据
            agg_period: 聚合周期 ('D' for day, 'H' for hour, 'W' for week)
        """
        # 按指定周期聚合数据
        data['period'] = data['datetime'].dt.to_period(agg_period)
        agg_data = data.groupby('period').agg({
            'large_net_flow': 'sum',
            'medium_net_flow': 'sum',
            'small_net_flow': 'sum',
            'total_net_flow': 'sum'
        }).reset_index()
        
        # 转换为热力图数据
        heatmap_data = agg_data[['large_net_flow', 'medium_net_flow', 'small_net_flow', 'total_net_flow']].values
        period_labels = agg_data['period'].astype(str)
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            heatmap_data.T,
            xticklabels=period_labels,
            yticklabels=['大单', '中单', '小单', '总计'],
            cmap='RdBu_r',
            center=0,
            cbar_kws={'label': '资金流向金额'}
        )
        plt.title(f'{agg_period}度资金流向热力图')
        plt.xlabel('时间周期')
        plt.ylabel('资金类型')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    def plot_fund_flow_3d(self, data: pd.DataFrame):
        """
        绘制3D资金流向图
        
        Args:
            data: 资金流向数据
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用3D图表")
            return
        
        fig = go.Figure(data=go.Scatter3d(
            x=data['large_net_flow'],
            y=data['medium_net_flow'],
            z=data['small_net_flow'],
            mode='markers',
            marker=dict(
                size=5,
                color=data.index,  # 使用索引作为颜色
                colorscale='Viridis',
                opacity=0.8
            ),
            text=data['datetime'].dt.strftime('%Y-%m-%d %H:%M'),
            hovertemplate='<b>%{text}</b><br>大单: %{x:,.0f}<br>中单: %{y:,.0f}<br>小单: %{z:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='3D资金流向分析',
            scene=dict(
                xaxis_title='大单净流入',
                yaxis_title='中单净流入',
                zaxis_title='小单净流入'
            ),
            width=800,
            height=600
        )
        
        fig.show()
    
    def animate_fund_flow(self, data: pd.DataFrame, update_interval: int = 10):
        """
        创建资金流向动画
        
        Args:
            data: 资金流向数据
            update_interval: 更新间隔（数据点数）
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用动画功能")
            return
        
        frames = []
        for i in range(update_interval, len(data), update_interval):
            frame_data = data.iloc[:i]
            
            frames.append(go.Frame(
                data=[
                    go.Scatter(
                        x=frame_data['datetime'],
                        y=frame_data['large_net_flow'],
                        mode='lines',
                        name='大单净流入',
                        line=dict(color='red')
                    ),
                    go.Scatter(
                        x=frame_data['datetime'],
                        y=frame_data['medium_net_flow'],
                        mode='lines',
                        name='中单净流入',
                        line=dict(color='orange')
                    ),
                    go.Scatter(
                        x=frame_data['datetime'],
                        y=frame_data['small_net_flow'],
                        mode='lines',
                        name='小单净流入',
                        line=dict(color='blue')
                    )
                ],
                name=f'frame{i}'
            ))
        
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=data['datetime'][:update_interval],
                    y=data['large_net_flow'][:update_interval],
                    mode='lines',
                    name='大单净流入',
                    line=dict(color='red')
                ),
                go.Scatter(
                    x=data['datetime'][:update_interval],
                    y=data['medium_net_flow'][:update_interval],
                    mode='lines',
                    name='中单净流入',
                    line=dict(color='orange')
                ),
                go.Scatter(
                    x=data['datetime'][:update_interval],
                    y=data['small_net_flow'][:update_interval],
                    mode='lines',
                    name='小单净流入',
                    line=dict(color='blue')
                )
            ],
            layout=go.Layout(
                title='资金流向动画',
                xaxis=dict(title='时间'),
                yaxis=dict(title='净流入金额'),
                updatemenus=[dict(
                    type='buttons',
                    showactive=False,
                    buttons=[dict(
                        label='Play',
                        method='animate',
                        args=[None, dict(frame=dict(duration=500, redraw=True), 
                                        fromcurrent=True, mode='immediate')]
                    )]
                )],
                sliders=[dict(
                    steps=[],
                    currentvalue={'prefix': 'Frame:'}
                )]
            ),
            frames=frames
        )
        
        fig.show()
    
    def plot_fund_flow_dashboard(self, data: pd.DataFrame):
        """
        绘制资金流向仪表板
        
        Args:
            data: 资金流向数据
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly不可用，请安装plotly以使用仪表板")
            return
        
        # 创建包含多个子图的仪表板
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('净流入趋势', '主力资金占比', '资金流向分布', '累计资金对比'),
            specs=[[{"secondary_y": False}, {"type": "pie"}],
                   [{"type": "histogram"}, {"secondary_y": False}]]
        )
        
        # 净流入趋势
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['total_net_flow'], 
                      mode='lines', name='总净流入', line=dict(color='blue')),
            row=1, col=1
        )
        
        # 主力资金占比饼图
        recent_data = data.tail(10)  # 最近10期数据
        avg_large = recent_data['large_net_flow'].mean()
        avg_medium = recent_data['medium_net_flow'].mean()
        avg_small = recent_data['small_net_flow'].mean()
        
        fig.add_trace(
            go.Pie(labels=['大单', '中单', '小单'], 
                   values=[abs(avg_large), abs(avg_medium), abs(avg_small)],
                   name="资金占比"),
            row=1, col=2
        )
        
        # 资金流向分布直方图
        fig.add_trace(
            go.Histogram(x=data['total_net_flow'], name='资金分布', nbinsx=30),
            row=2, col=1
        )
        
        # 累计资金对比
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_total'], 
                      mode='lines', name='总累计', line=dict(color='purple')),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=data['datetime'], y=data['cumulative_main'], 
                      mode='lines', name='主力累计', line=dict(color='red')),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=True, 
                         title_text="资金流向综合仪表板")
        fig.show()
    
    def get_real_fund_flow_data(self, symbol: str = "000001") -> Optional[pd.DataFrame]:
        """
        获取真实资金流向数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            资金流向DataFrame或None
        """
        if not AKSHARE_AVAILABLE:
            print("akshare不可用，返回模拟数据")
            return self.generate_mock_fund_flow_data(50)
        
        try:
            # 这里使用akshare获取真实的资金流向数据
            # 注意：实际的akshare接口可能会变化
            print(f"尝试获取{symbol}的资金流向数据...")
            # 模拟调用真实数据接口（因为akshare的接口可能需要实际测试）
            # df = ak.stock_individual_fund_flow(stock=symbol)
            # 为演示目的，暂时返回模拟数据
            return self.generate_mock_fund_flow_data(50)
        except Exception as e:
            print(f"获取真实数据失败: {e}，返回模拟数据")
            return self.generate_mock_fund_flow_data(50)


class StreamlitFundFlowApp:
    """Streamlit资金流向应用"""
    
    def __init__(self):
        self.visualizer = RealTimeFundFlowVisualizer()
        st.set_page_config(
            page_title="实时资金流向分析",
            page_icon="💰",
            layout="wide"
        )
    
    def run(self):
        """运行Streamlit应用"""
        st.title("💰 实时资金流向分析平台")
        
        # 侧边栏
        st.sidebar.header("数据设置")
        symbol = st.sidebar.text_input("股票代码", "000001")
        days = st.sidebar.slider("获取天数", 1, 30, 7)
        update_freq = st.sidebar.slider("更新频率(分钟)", 5, 60, 30)
        
        # 选择数据
        st.sidebar.subheader("数据源")
        data_source = st.sidebar.radio("数据源", ["模拟数据", "真实数据（需要akshare）"])
        
        # 获取数据
        if st.sidebar.button("获取数据") or 'data' not in st.session_state:
            with st.spinner(f"获取{symbol}资金流向数据..."):
                if data_source == "真实数据（需要akshare）":
                    data = self.visualizer.get_real_fund_flow_data(symbol)
                else:
                    # 生成更多数据用于演示
                    data = self.visualizer.generate_mock_fund_flow_data(days * 24 * 2)  # 每天48个数据点（30分钟间隔）
                
                st.session_state['data'] = data
                st.session_state['last_update'] = datetime.now()
        
        if 'data' not in st.session_state:
            st.info("点击侧边栏的'获取数据'按钮开始分析")
            return
        
        data = st.session_state['data']
        st.sidebar.write(f"数据更新时间: {st.session_state['last_update']}")
        st.sidebar.write(f"数据点数: {len(data)}")
        
        # 主要内容区域
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("大单净流入", f"¥{data['large_net_flow'].sum():,.0f}", 
                     f"¥{data['large_net_flow'].tail(5).mean():,.0f}/期")
        with col2:
            st.metric("中单净流入", f"¥{data['medium_net_flow'].sum():,.0f}",
                     f"¥{data['medium_net_flow'].tail(5).mean():,.0f}/期")
        with col3:
            st.metric("小单净流入", f"¥{data['small_net_flow'].sum():,.0f}",
                     f"¥{data['small_net_flow'].tail(5).mean():,.0f}/期")
        with col4:
            st.metric("总净流入", f"¥{data['total_net_flow'].sum():,.0f}",
                     f"¥{data['total_net_flow'].tail(5).mean():,.0f}/期")
        
        # 选项卡
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["净流入趋势", "累计资金", "资金平衡", "3D分析", "仪表板"])
        
        with tab1:
            st.subheader("资金净流入趋势")
            
            # 选择要显示的资金类型
            fund_types = st.multiselect(
                "选择资金类型",
                ["large_net_flow", "medium_net_flow", "small_net_flow", "total_net_flow"],
                default=["large_net_flow", "medium_net_flow", "small_net_flow"]
            )
            
            if fund_types:
                fig = go.Figure()
                colors = {'large_net_flow': 'red', 'medium_net_flow': 'orange', 
                         'small_net_flow': 'blue', 'total_net_flow': 'black'}
                
                for fund_type in fund_types:
                    fig.add_trace(go.Scatter(
                        x=data['datetime'],
                        y=data[fund_type],
                        mode='lines',
                        name=fund_type.replace('_net_flow', '').replace('_', ' ').title(),
                        line=dict(color=colors.get(fund_type, 'gray'))
                    ))
                
                fig.update_layout(
                    title="资金净流入趋势",
                    xaxis_title="时间",
                    yaxis_title="净流入金额",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("累计资金流向")
            cumulative_types = st.multiselect(
                "选择累计类型",
                ["cumulative_large", "cumulative_medium", "cumulative_small", "cumulative_total"],
                default=["cumulative_large", "cumulative_medium", "cumulative_total"]
            )
            
            if cumulative_types:
                fig = go.Figure()
                colors = {'cumulative_large': 'red', 'cumulative_medium': 'orange', 
                         'cumulative_small': 'blue', 'cumulative_total': 'purple'}
                
                for cum_type in cumulative_types:
                    fig.add_trace(go.Scatter(
                        x=data['datetime'],
                        y=data[cum_type],
                        mode='lines',
                        name=cum_type.replace('cumulative_', '').replace('_', ' ').title(),
                        line=dict(color=colors.get(cum_type, 'gray'))
                    ))
                
                fig.update_layout(
                    title="累计资金流向",
                    xaxis_title="时间",
                    yaxis_title="累计金额",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("资金平衡分析")
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("大单-小单净额", "资金类型占比变化")
            )
            
            fig.add_trace(
                go.Scatter(x=data['datetime'], y=data['flow_balance'], 
                          mode='lines', name='大单-小单净额', line=dict(color='green')),
                row=1, col=1
            )
            fig.add_hline(y=0, line_dash="dash", line_color="black", row=1, col=1)
            
            # 资金类型占比
            total_flow_abs = np.abs(data['large_net_flow']) + np.abs(data['medium_net_flow']) + np.abs(data['small_net_flow'])
            large_ratio = np.abs(data['large_net_flow']) / (total_flow_abs + 1e-10)
            medium_ratio = np.abs(data['medium_net_flow']) / (total_flow_abs + 1e-10)
            small_ratio = np.abs(data['small_net_flow']) / (total_flow_abs + 1e-10)
            
            fig.add_trace(
                go.Scatter(x=data['datetime'], y=large_ratio, 
                          mode='lines', name='大单占比', line=dict(color='red')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=data['datetime'], y=medium_ratio, 
                          mode='lines', name='中单占比', line=dict(color='orange')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=data['datetime'], y=small_ratio, 
                          mode='lines', name='小单占比', line=dict(color='blue')),
                row=2, col=1
            )
            
            fig.update_layout(height=600, title_text="资金平衡分析")
            st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            st.subheader("3D资金流向分析")
            if st.button("生成3D图"):
                with st.spinner("生成3D图表..."):
                    self.visualizer.plot_fund_flow_3d(data.head(50))  # 使用前50个数据点
                    st.success("3D图表已生成！")
        
        with tab5:
            st.subheader("资金流向仪表板")
            if st.button("生成仪表板"):
                with st.spinner("生成仪表板..."):
                    self.visualizer.plot_fund_flow_dashboard(data)
                    st.success("仪表板已生成！")


def run_fund_flow_app():
    """运行资金流向应用"""
    app = StreamlitFundFlowApp()
    app.run()


def demo_fund_flow_visualization():
    """演示资金流向可视化"""
    print("=== 实时资金流向可视化演示 ===")
    
    # 创建可视化器
    visualizer = RealTimeFundFlowVisualizer()
    
    # 生成示例数据
    data = visualizer.generate_mock_fund_flow_data(100)
    print(f"生成了 {len(data)} 条资金流向数据")
    print(f"数据时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
    
    # 演示不同的可视化方法
    print("\n1. 绘制资金净流入时间序列...")
    visualizer.plot_fund_flow_time_series(data, chart_type='net_flow')
    
    print("\n2. 绘制累计资金流向...")
    visualizer.plot_fund_flow_time_series(data, chart_type='cumulative')
    
    print("\n3. 绘制资金平衡分析...")
    visualizer.plot_fund_flow_time_series(data, chart_type='balance')
    
    print("\n4. 绘制资金流向热力图...")
    visualizer.plot_fund_flow_heatmap(data, agg_period='D')
    
    # 如果Plotly可用，演示交互式图表
    if PLOTLY_AVAILABLE:
        print("\n5. 绘制交互式资金流向图...")
        visualizer.plot_interactive_fund_flow(data)
        
        print("\n6. 绘制3D资金流向图...")
        visualizer.plot_fund_flow_3d(data)
        
        print("\n7. 绘制资金流向仪表板...")
        visualizer.plot_fund_flow_dashboard(data)
    
    # 显示数据统计
    print("\n=== 数据统计 ===")
    print(data[['large_net_flow', 'medium_net_flow', 'small_net_flow', 'total_net_flow']].describe())


if __name__ == "__main__":
    demo_fund_flow_visualization()
