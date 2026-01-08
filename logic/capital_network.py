# Workaround for NetworkX + Pydantic v1 + Python 3.14 compatibility issue
# The error occurs when Python 3.14's dataclass processing tries to access 
# __annotate__ on wrapper_descriptor objects, which don't have this attribute

import sys
import dataclasses
import types

# Store the original _add_slots function BEFORE we modify it
_original_add_slots = dataclasses._add_slots

def _patched_add_slots(cls, frozen, weakref_slot, fields):
    """Patched version to handle the __annotate__ attribute issue with wrapper_descriptor"""
    # The issue occurs when trying to access __init__.__annotate__ on a wrapper_descriptor
    # We need to replace wrapper_descriptor __init__ methods before processing
    
    init_method = cls.__init__
    
    if isinstance(init_method, types.WrapperDescriptorType):
        # This is a wrapper_descriptor like object.__init__ which doesn't have __annotate__
        # Create a new method with proper attributes
        original_init = init_method
        
        # Create a new function that calls the original method
        def new_init(self, *_, **__):
            # For classes without custom __init__, the object.__init__ just does nothing
            return original_init(self, *_, **__)
        
        # Copy any annotations
        if hasattr(original_init, '__annotations__'):
            new_init.__annotations__ = original_init.__annotations__.copy()
        else:
            new_init.__annotations__ = {}
        
        # The new function needs to be assigned to the class
        cls.__init__ = new_init
    
    # Call the ORIGINAL function which should now work
    try:
        result = _original_add_slots(cls, frozen, weakref_slot, fields)
        return result
    except AttributeError as e:
        if "__annotate__" in str(e) and "wrapper_descriptor" in str(e):
            # If we still get the error, handle it by ensuring the class has proper attributes
            # This is a fallback approach
            if isinstance(init_method, types.WrapperDescriptorType):
                original_init = init_method
                def safe_init(self, *args, **kwargs):
                    return original_init(self, *args, **kwargs)
                
                # Copy annotations
                if hasattr(original_init, '__annotations__'):
                    safe_init.__annotations__ = original_init.__annotations__.copy()
                
                # Set __annotate__ to the annotations as well
                safe_init.__annotate__ = getattr(safe_init, '__annotations__', {})
                
                # Replace the __init__ in the class
                cls.__init__ = safe_init
            
            # Retry using the ORIGINAL function  
            return _original_add_slots(cls, frozen, weakref_slot, fields)
        else:
            # If it's a different error, re-raise it
            raise

# Apply the patch to the dataclasses module - make sure this is applied globally
dataclasses._add_slots = _patched_add_slots

# Now import NetworkX - this should work without the __annotate__ error
import networkx as nx

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("没有matplotlib，无法本地擏描图谱")

logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    """
    节点量化指标
    """
    node_id: str  # 游资/股票代码
    node_type: str  # 'capital' 或 'stock'
    degree: int  # 连接数
    weighted_degree: float  # 加权连接
    betweenness_centrality: float  # 中介中心度
    closeness_centrality: float  # 事不律中心度
    clustering_coefficient: float  # 聚类一致性系数
    is_hub: bool  # 是否为中心节点
    strength: float  # 挺上量 (需来总额/操作数)


@dataclass
class EdgeMetrics:
    """
    边的量化指标
    """
    source: str  # 游资/股票A
    target: str  # 股票B/游资B
    edge_type: str  # 'capital_stock' 或 'capital_capital'
    weight: float  # 权重 (成交额/操作数/对斗月数)
    frequency: int  # 共现频次
    intensity: float  # 强度 (0-1)
    is_competitive: bool  # 是否为对斗关系


class CapitalNetworkBuilder:
    """
    游资关系图谱构建器
    """
    
    def __init__(self, lookback_days: int = 30):
        """
        Args:
            lookback_days: 回须窗口 (天数)
        """
        self.lookback_days = lookback_days
        self.graph = nx.Graph()
        self.stock_graph = None  # 股票子图
        self.capital_graph = None  # 游资子图
        self.node_metrics = {}
        self.edge_metrics = {}
    
    def build_graph_from_lhb(
        self,
        df_lhb: pd.DataFrame,
        include_competitive: bool = True
    ) -> nx.Graph:
        """
        从龙虎榜数据构建二部图
        
        Args:
            df_lhb: 龙虎榜整体数据
            include_competitive: 是否包含对斗关系
        
        Returns:
            nx.Graph 游资-股票二部图
        """
        self.graph = nx.Graph()
        
        # 提取包含的游资和股票
        capitals = df_lhb['游资名称'].unique()
        stocks = df_lhb['股票代码'].unique()
        
        # 添加节点
        for capital in capitals:
            self.graph.add_node(capital, node_type='capital')
        
        for stock in stocks:
            self.graph.add_node(stock, node_type='stock')
        
        # 添加游资-股票需来 (成交额为权重)
        for _, row in df_lhb.iterrows():
            capital = row['游资名称']
            stock = row['股票代码']
            amount = row.get('成交额', 0)
            
            # 如果已存在需来，倒成交额
            if self.graph.has_edge(capital, stock):
                self.graph[capital][stock]['weight'] += amount
                self.graph[capital][stock]['frequency'] += 1
            else:
                self.graph.add_edge(
                    capital, stock,
                    weight=amount,
                    frequency=1,
                    type='capital_stock'
                )
        
        # 添加游资-游资对斗关系 (可选)
        if include_competitive:
            self._add_capital_competitive_edges(df_lhb)
        
        return self.graph
    
    def _add_capital_competitive_edges(self, df_lhb: pd.DataFrame) -> None:
        """
        添加游资-游资对斗需来 (同一日互买卖同一票票)
        """
        # 提取股票级别的游资操作
        stock_capitals = df_lhb.groupby('股票代码')['游资名称'].apply(list)
        
        # 如果前两个游资在同一票票上操作，且一个买入一个卖出，则是对斗
        for stock, capitals in stock_capitals.items():
            if len(capitals) >= 2:
                stock_data = df_lhb[df_lhb['股票代码'] == stock]
                
                # 提取买入游资
                buyers = stock_data[stock_data['操作方向'] == '买']['游资名称'].unique()
                # 提取卖出游资
                sellers = stock_data[stock_data['操作方向'] == '卖']['游资名称'].unique()
                
                # 列举所有对斗对斗
                for buyer in buyers:
                    for seller in sellers:
                        if buyer != seller:
                            # 添加或更新游资需来
                            if self.graph.has_edge(buyer, seller):
                                self.graph[buyer][seller]['competitive_count'] += 1
                                self.graph[buyer][seller]['weight'] += 1
                            else:
                                self.graph.add_edge(
                                    buyer, seller,
                                    weight=1,
                                    frequency=1,
                                    competitive_count=1,
                                    type='capital_capital'
                                )
    
    def calculate_node_metrics(self) -> Dict[str, NodeMetrics]:
        """
        计算节点指标
        """
        self.node_metrics = {}
        
        # 中心度指标
        betweenness = nx.betweenness_centrality(self.graph, weight='weight')
        closeness = nx.closeness_centrality(self.graph, distance='weight')
        clustering = nx.clustering(self.graph)
        
        # 提取节点强度 (需来总额/操作数)
        for node in self.graph.nodes():
            edges = self.graph.edges(node, data=True)
            weight_sum = sum(data['weight'] for _, _, data in edges)
            frequency_sum = sum(data.get('frequency', 1) for _, _, data in edges)
            strength = weight_sum / max(frequency_sum, 1)
            
            # 判断是否为中心节点 (度数或中心度扇一)
            is_hub = (
                self.graph.degree(node) >= 10 or
                betweenness.get(node, 0) > 0.1
            )
            
            metrics = NodeMetrics(
                node_id=node,
                node_type=self.graph.nodes[node].get('node_type', 'unknown'),
                degree=self.graph.degree(node),
                weighted_degree=sum(data['weight'] for _, _, data in edges),
                betweenness_centrality=betweenness.get(node, 0),
                closeness_centrality=closeness.get(node, 0),
                clustering_coefficient=clustering.get(node, 0),
                is_hub=is_hub,
                strength=strength
            )
            
            self.node_metrics[node] = metrics
        
        return self.node_metrics
    
    def get_capital_clusters(self, k: int = 3) -> Dict[int, List[str]]:
        """
        使用【简敦线算法】分散游资群组
        
        Args:
            k: 群组数
        
        Returns:
            {group_id: [capitals, ...]}
        """
        # 提取游资子图
        capital_nodes = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get('node_type') == 'capital'
        ]
        
        if not capital_nodes:
            return {}
        
        # 构建游资子图
        capital_subgraph = self.graph.subgraph(capital_nodes).copy()
        
        # 添加处理 (如果是单一节点，处理为一个群组)
        if len(capital_nodes) == 0:
            return {}
        elif len(capital_nodes) == 1:
            return {0: capital_nodes}
        
        # 使用示那屍会突什算法承饢
        try:
            from sklearn.cluster import SpectralClustering
            
            # 计算距离矩阵 (1 - 正规化的成交额)
            n = len(capital_nodes)
            distances = np.ones((n, n))
            
            for i, cap1 in enumerate(capital_nodes):
                for j, cap2 in enumerate(capital_nodes):
                    if i != j and capital_subgraph.has_edge(cap1, cap2):
                        weight = capital_subgraph[cap1][cap2]['weight']
                        distances[i][j] = 1 / (1 + weight)
            
            # 粗粟含族群组
            clustering = SpectralClustering(
                n_clusters=min(k, len(capital_nodes)),
                affinity='precomputed',
                assign_labels='kmeans',
                random_state=42
            )
            
            # 计算伺出今强度矩阵 (1 - 距离)
            affinity = 1 - distances / distances.max()
            labels = clustering.fit_predict(affinity)
            
            # 组合群组ᴗ时
            clusters = defaultdict(list)
            for capital, label in zip(capital_nodes, labels):
                clusters[int(label)].append(capital)
            
            return dict(clusters)
        
        except ImportError:
            logger.warning("scikit-learn未可用，使用简敦分组")
            # 简敦操作: 优先提取度數最高的k个游资
            capital_degrees = [
                (cap, self.graph.degree(cap, weight='weight'))
                for cap in capital_nodes
            ]
            capital_degrees.sort(key=lambda x: x[1], reverse=True)
            
            clusters = {}
            for idx, (capital, _) in enumerate(capital_degrees[:k]):
                clusters[idx] = [capital]
            
            return clusters
    
    def analyze_competitive_landscape(
        self,
        df_lhb: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        分析对斗景象
        
        Returns:
            {capital: {
                'main_opponents': [...],
                'battle_count': int,
                'battle_success_rate': float,
                'dominated_fields': [...]
            }}
        """
        analysis = {}
        
        capitals = df_lhb['游资名称'].unique()
        
        for capital in capitals:
            capital_data = df_lhb[df_lhb['游资名称'] == capital]
            
            # 提取该游资的操作股票
            operated_stocks = set(capital_data['股票代码'].unique())
            
            # 找出其他游资在相同股票上的操作
            opponents = Counter()
            success_battles = 0
            total_battles = 0
            
            for stock in operated_stocks:
                stock_data = df_lhb[df_lhb['股票代码'] == stock]
                other_capitals = stock_data[
                    stock_data['游资名称'] != capital
                ]['游资名称'].unique()
                
                for opponent in other_capitals:
                    opponents[opponent] += 1
                    
                    # 判断是否是常流 (同一股票上一个买一个卖)
                    capital_op = stock_data[
                        (stock_data['游资名称'] == capital) &
                        (stock_data['操作方向'] == '买')
                    ]
                    opponent_op = stock_data[
                        (stock_data['游资名称'] == opponent) &
                        (stock_data['操作方向'] == '卖')
                    ]
                    
                    if not capital_op.empty and not opponent_op.empty:
                        total_battles += 1
                        # 帔正行为：是否在对斗后走优
                        if capital_op.iloc[0]['成交额'] > opponent_op.iloc[0]['成交额']:
                            success_battles += 1
            
            analysis[capital] = {
                'main_opponents': opponents.most_common(3),
                'battle_count': total_battles,
                'battle_success_rate': success_battles / max(total_battles, 1),
                'dominated_stocks': list(operated_stocks)
            }
        
        return analysis
    
    def visualize_network(
        self,
        output_path: str = None,
        show_labels: bool = True,
        figsize: Tuple = (15, 12)
    ) -> None:
        """
        可載化网络 (Matplotlib)
        
        Args:
            output_path: 保存路径
            show_labels: 是否显示节点标签
            figsize: 图表大小
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("没有matplotlib，无法绘制图谱")
            return
        
        # 使用Spring布局
        pos = nx.spring_layout(
            self.graph,
            k=2,
            iterations=50,
            seed=42
        )
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 提取节点类型
        capital_nodes = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get('node_type') == 'capital'
        ]
        stock_nodes = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get('node_type') == 'stock'
        ]
        
        # 绘制节点
        nx.draw_networkx_nodes(
            self.graph, pos,
            nodelist=capital_nodes,
            node_color='#FF6B6B',
            node_size=800,
            label='Capitals',
            ax=ax
        )
        
        nx.draw_networkx_nodes(
            self.graph, pos,
            nodelist=stock_nodes,
            node_color='#4ECDC4',
            node_size=300,
            label='Stocks',
            ax=ax
        )
        
        # 绘制需来
        nx.draw_networkx_edges(
            self.graph, pos,
            alpha=0.3,
            ax=ax
        )
        
        # 绘制标签
        if show_labels:
            nx.draw_networkx_labels(
                self.graph, pos,
                font_size=8,
                font_color='#333',
                ax=ax
            )
        
        ax.set_title('Capital Network Graph', fontsize=16, fontweight='bold')
        ax.legend(scatterpoints=1)
        ax.axis('off')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"图谱已保存到: {output_path}")
        else:
            plt.show()
    
    def get_network_summary(self) -> Dict:
        """
        获取网络报告
        """
        if not self.node_metrics:
            self.calculate_node_metrics()
        
        capitals = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get('node_type') == 'capital'
        ]
        stocks = [
            node for node in self.graph.nodes()
            if self.graph.nodes[node].get('node_type') == 'stock'
        ]
        
        # 找出中心游资
        hub_capitals = [
            cap for cap in capitals
            if self.node_metrics[cap].is_hub
        ]
        
        return {
            'total_capitals': len(capitals),
            'total_stocks': len(stocks),
            'total_edges': self.graph.number_of_edges(),
            'hub_capitals': hub_capitals,
            'network_density': nx.density(self.graph),
            'average_clustering': nx.average_clustering(self.graph),
            'connected_components': nx.number_connected_components(self.graph)
        }
