"""
联邦学习系统
支持隐私保护和聚合策略
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
import json
import os
import hashlib


class Client:
    """联邦学习客户端"""
    
    def __init__(self, client_id: str, data: pd.DataFrame, 
                 privacy_budget: float = 1.0):
        """
        初始化客户端
        
        Args:
            client_id: 客户端ID
            data: 本地数据
            privacy_budget: 隐私预算
        """
        self.client_id = client_id
        self.data = data
        self.local_model = None
        self.privacy_budget = privacy_budget
        self.privacy_used = 0.0
        self.training_history = []
    
    def set_model(self, model: Any):
        """设置本地模型"""
        self.local_model = model
    
    def train_local(self, epochs: int = 1, learning_rate: float = 0.01) -> Dict[str, Any]:
        """
        本地训练
        
        Args:
            epochs: 训练轮数
            learning_rate: 学习率
            
        Returns:
            训练结果
        """
        if self.local_model is None:
            raise ValueError("模型未设置")
        
        # 简化的本地训练
        n_samples = len(self.data)
        
        # 模拟训练过程
        for epoch in range(epochs):
            # 这里应该是实际的训练过程
            # 简化版：随机更新参数
            for i in range(len(self.local_model.weights)):
                noise = np.random.randn(*self.local_model.weights[i].shape) * 0.01
                self.local_model.weights[i] -= learning_rate * noise
        
        # 计算隐私消耗
        privacy_cost = epochs * 0.01  # 简化的隐私成本计算
        self.privacy_used += privacy_cost
        
        result = {
            'client_id': self.client_id,
            'n_samples': n_samples,
            'epochs': epochs,
            'privacy_used': self.privacy_used,
            'privacy_remaining': self.privacy_budget - self.privacy_used
        }
        
        self.training_history.append(result)
        return result
    
    def get_model_parameters(self) -> List[np.ndarray]:
        """获取模型参数"""
        if self.local_model is None:
            raise ValueError("模型未设置")
        return self.local_model.weights
    
    def add_differential_privacy(self, parameters: List[np.ndarray], 
                                 epsilon: float = 1.0, delta: float = 1e-5) -> List[np.ndarray]:
        """
        添加差分隐私噪声
        
        Args:
            parameters: 模型参数
            epsilon: 隐私参数
            delta: 隐私参数
            
        Returns:
            添加噪声后的参数
        """
        noisy_parameters = []
        
        for param in parameters:
            # 计算敏感度
            sensitivity = np.linalg.norm(param, ord=2)
            
            # 计算噪声标准差
            sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
            
            # 添加高斯噪声
            noise = np.random.normal(0, sigma, param.shape)
            noisy_param = param + noise
            
            noisy_parameters.append(noisy_param)
        
        return noisy_parameters
    
    def compute_model_update(self, global_parameters: List[np.ndarray]) -> List[np.ndarray]:
        """
        计算模型更新
        
        Args:
            global_parameters: 全局模型参数
            
        Returns:
            模型更新（参数差值）
        """
        local_parameters = self.get_model_parameters()
        
        updates = []
        for local_param, global_param in zip(local_parameters, global_parameters):
            update = local_param - global_param
            updates.append(update)
        
        return updates


class FederatedServer:
    """联邦学习服务器"""
    
    def __init__(self, global_model: Any, aggregation_strategy: str = 'fedavg'):
        """
        初始化联邦服务器
        
        Args:
            global_model: 全局模型
            aggregation_strategy: 聚合策略 ('fedavg', 'fedprox', 'fednova')
        """
        self.global_model = global_model
        self.aggregation_strategy = aggregation_strategy
        self.clients = {}
        self.round_history = []
        self.n_rounds = 0
    
    def register_client(self, client: Client):
        """注册客户端"""
        self.clients[client.client_id] = client
    
    def select_clients(self, fraction: float = 1.0) -> List[Client]:
        """
        选择参与训练的客户端
        
        Args:
            fraction: 选择比例
            
        Returns:
            选中的客户端列表
        """
        n_clients = int(len(self.clients) * fraction)
        client_ids = np.random.choice(list(self.clients.keys()), n_clients, replace=False)
        return [self.clients[cid] for cid in client_ids]
    
    def aggregate_updates(self, client_updates: Dict[str, Tuple[List[np.ndarray], int]],
                         method: str = 'fedavg') -> List[np.ndarray]:
        """
        聚合客户端更新
        
        Args:
            client_updates: 客户端更新 {client_id: (updates, n_samples)}
            method: 聚合方法
            
        Returns:
            聚合后的更新
        """
        if not client_updates:
            raise ValueError("没有可用的客户端更新")
        
        if method == 'fedavg':
            # FedAvg: 加权平均
            total_samples = sum(n_samples for _, n_samples in client_updates.values())
            
            aggregated_updates = []
            for i in range(len(list(client_updates.values())[0][0])):
                weighted_sum = np.zeros_like(list(client_updates.values())[0][0][i])
                
                for updates, n_samples in client_updates.values():
                    weighted_sum += updates[i] * n_samples
                
                aggregated_updates.append(weighted_sum / total_samples)
        
        elif method == 'fedprox':
            # FedProx: 近似聚合（简化版）
            total_samples = sum(n_samples for _, n_samples in client_updates.values())
            
            aggregated_updates = []
            for i in range(len(list(client_updates.values())[0][0])):
                weighted_sum = np.zeros_like(list(client_updates.values())[0][0][i])
                
                for updates, n_samples in client_updates.values():
                    # 添加正则化项
                    proximal_term = 0.01 * updates[i]
                    weighted_sum += (updates[i] + proximal_term) * n_samples
                
                aggregated_updates.append(weighted_sum / total_samples)
        
        elif method == 'fednova':
            # FedNova: 归一化聚合（简化版）
            aggregated_updates = []
            for i in range(len(list(client_updates.values())[0][0])):
                updates_list = [updates[i] for updates, _ in client_updates.values()]
                aggregated_updates.append(np.mean(updates_list, axis=0))
        
        else:
            raise ValueError(f"未知的聚合方法: {method}")
        
        return aggregated_updates
    
    def federated_round(self, selected_clients: List[Client], 
                       epochs: int = 1, learning_rate: float = 0.01,
                       use_dp: bool = False, dp_epsilon: float = 1.0) -> Dict[str, Any]:
        """
        执行一轮联邦训练
        
        Args:
            selected_clients: 选中的客户端
            epochs: 本地训练轮数
            learning_rate: 学习率
            use_dp: 是否使用差分隐私
            dp_epsilon: 差分隐私参数
            
        Returns:
            联邦训练结果
        """
        round_start = datetime.now()
        
        # 分发全局模型
        global_parameters = self.global_model.get_parameters()
        
        # 客户端本地训练
        client_updates = {}
        client_results = []
        
        for client in selected_clients:
            # 设置全局模型
            client.set_model(self.global_model)
            
            # 本地训练
            result = client.train_local(epochs, learning_rate)
            client_results.append(result)
            
            # 获取模型更新
            updates = client.compute_model_update(global_parameters)
            
            # 添加差分隐私
            if use_dp:
                updates = client.add_differential_privacy(updates, dp_epsilon)
            
            client_updates[client.client_id] = (updates, result['n_samples'])
        
        # 聚合更新
        aggregated_updates = self.aggregate_updates(client_updates, self.aggregation_strategy)
        
        # 更新全局模型
        for i in range(len(self.global_model.weights)):
            self.global_model.weights[i] += aggregated_updates[i]
        
        # 计算统计信息
        round_time = (datetime.now() - round_start).total_seconds()
        avg_privacy_used = np.mean([r['privacy_used'] for r in client_results])
        total_samples = sum(r['n_samples'] for r in client_results)
        
        # 记录历史
        self.n_rounds += 1
        round_info = {
            'round': self.n_rounds,
            'n_clients': len(selected_clients),
            'total_samples': total_samples,
            'round_time': round_time,
            'avg_privacy_used': avg_privacy_used,
            'use_dp': use_dp,
            'timestamp': datetime.now().isoformat()
        }
        self.round_history.append(round_info)
        
        return round_info
    
    def get_global_model(self) -> Any:
        """获取全局模型"""
        return self.global_model
    
    def get_round_history(self, limit: int = 100) -> List[Dict]:
        """获取训练历史"""
        return self.round_history[-limit:]
    
    def save_global_model(self, filepath: str):
        """保存全局模型"""
        model_data = {
            'n_rounds': self.n_rounds,
            'aggregation_strategy': self.aggregation_strategy,
            'parameters': [w.tolist() for w in self.global_model.weights],
            'round_history': self.round_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f)


class FederatedLearningSystem:
    """联邦学习系统"""
    
    def __init__(self, global_model: Any, aggregation_strategy: str = 'fedavg'):
        """
        初始化联邦学习系统
        
        Args:
            global_model: 全局模型
            aggregation_strategy: 聚合策略
        """
        self.server = FederatedServer(global_model, aggregation_strategy)
        self.clients = {}
        self.system_history = []
    
    def add_client(self, client_id: str, data: pd.DataFrame, 
                  privacy_budget: float = 1.0) -> Client:
        """
        添加客户端
        
        Args:
            client_id: 客户端ID
            data: 客户端数据
            privacy_budget: 隐私预算
            
        Returns:
            客户端对象
        """
        client = Client(client_id, data, privacy_budget)
        self.clients[client_id] = client
        self.server.register_client(client)
        return client
    
    def train(self, n_rounds: int, epochs_per_round: int = 1,
             client_fraction: float = 1.0, learning_rate: float = 0.01,
             use_dp: bool = False, dp_epsilon: float = 1.0) -> Dict[str, Any]:
        """
        执行联邦训练
        
        Args:
            n_rounds: 训练轮数
            epochs_per_round: 每轮本地训练轮数
            client_fraction: 客户端选择比例
            learning_rate: 学习率
            use_dp: 是否使用差分隐私
            dp_epsilon: 差分隐私参数
            
        Returns:
            训练结果
        """
        start_time = datetime.now()
        round_results = []
        
        for round_idx in range(n_rounds):
            # 选择客户端
            selected_clients = self.server.select_clients(client_fraction)
            
            # 执行联邦训练
            round_result = self.server.federated_round(
                selected_clients, epochs_per_round, learning_rate, use_dp, dp_epsilon
            )
            
            round_results.append(round_result)
            print(f"Round {round_idx + 1}/{n_rounds}, "
                  f"Clients: {round_result['n_clients']}, "
                  f"Time: {round_result['round_time']:.2f}s")
        
        total_time = (datetime.now() - start_time).total_seconds()
        avg_round_time = np.mean([r['round_time'] for r in round_results])
        total_privacy_used = np.mean([c.privacy_used for c in self.clients.values()])
        
        result = {
            'n_rounds': n_rounds,
            'total_time': total_time,
            'avg_round_time': avg_round_time,
            'total_privacy_used': total_privacy_used,
            'round_results': round_results
        }
        
        self.system_history.append(result)
        return result
    
    def get_global_model(self) -> Any:
        """获取全局模型"""
        return self.server.get_global_model()
    
    def get_client_info(self) -> List[Dict]:
        """获取客户端信息"""
        return [
            {
                'client_id': client.client_id,
                'n_samples': len(client.data),
                'privacy_budget': client.privacy_budget,
                'privacy_used': client.privacy_used,
                'privacy_remaining': client.privacy_budget - client.privacy_used
            }
            for client in self.clients.values()
        ]
    
    def save_system(self, filepath: str):
        """保存系统状态"""
        system_data = {
            'aggregation_strategy': self.server.aggregation_strategy,
            'n_clients': len(self.clients),
            'n_rounds': self.server.n_rounds,
            'global_model': {
                'parameters': [w.tolist() for w in self.server.global_model.weights]
            },
            'client_info': self.get_client_info(),
            'round_history': self.server.get_round_history()
        }
        
        with open(filepath, 'w') as f:
            json.dump(system_data, f)
    
    def load_system(self, filepath: str):
        """加载系统状态"""
        with open(filepath, 'r') as f:
            system_data = json.load(f)
        
        # 恢复全局模型
        parameters = [np.array(w) for w in system_data['global_model']['parameters']]
        self.server.global_model.set_parameters(parameters)
        
        # 恢复训练历史
        self.server.round_history = system_data['round_history']
        self.server.n_rounds = system_data['n_rounds']
        
        return self