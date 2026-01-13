"""
分布式训练系统
支持多GPU训练和数据并行
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import Manager, Queue
import json
import os
import time


class DataPartition:
    """数据分区"""
    
    def __init__(self, data: pd.DataFrame, n_partitions: int):
        """
        初始化数据分区
        
        Args:
            data: 原始数据
            n_partitions: 分区数量
        """
        self.data = data
        self.n_partitions = n_partitions
        self.partitions = self._partition_data()
    
    def _partition_data(self) -> List[pd.DataFrame]:
        """分区数据"""
        partitions = []
        chunk_size = len(self.data) // self.n_partitions
        
        for i in range(self.n_partitions):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < self.n_partitions - 1 else len(self.data)
            partitions.append(self.data.iloc[start_idx:end_idx].copy())
        
        return partitions
    
    def get_partition(self, partition_id: int) -> pd.DataFrame:
        """获取指定分区"""
        if partition_id < 0 or partition_id >= self.n_partitions:
            raise ValueError(f"无效的分区ID: {partition_id}")
        return self.partitions[partition_id]
    
    def get_all_partitions(self) -> List[pd.DataFrame]:
        """获取所有分区"""
        return self.partitions


class Worker:
    """工作节点"""
    
    def __init__(self, worker_id: int, data: pd.DataFrame):
        """
        初始化工作节点
        
        Args:
            worker_id: 工作节点ID
            data: 分配的数据
        """
        self.worker_id = worker_id
        self.data = data
        self.model = None
        self.gradients = None
    
    def train(self, model: Any, train_func: Callable, epochs: int = 1) -> Dict[str, Any]:
        """
        在本地数据上训练模型
        
        Args:
            model: 模型
            train_func: 训练函数
            epochs: 训练轮数
            
        Returns:
            训练结果
        """
        start_time = time.time()
        
        # 执行训练
        result = train_func(model, self.data, epochs)
        
        elapsed_time = time.time() - start_time
        
        return {
            'worker_id': self.worker_id,
            'n_samples': len(self.data),
            'epochs': epochs,
            'training_time': elapsed_time,
            'result': result
        }
    
    def compute_gradients(self, model: Any, loss_func: Callable) -> np.ndarray:
        """
        计算梯度
        
        Args:
            model: 模型
            loss_func: 损失函数
            
        Returns:
            梯度
        """
        # 简化版：使用数值梯度
        gradients = []
        eps = 1e-5
        
        for i in range(len(model.weights)):
            original_value = model.weights[i]
            
            # 计算正向扰动
            model.weights[i] = original_value + eps
            loss_plus = loss_func(model, self.data)
            
            # 计算负向扰动
            model.weights[i] = original_value - eps
            loss_minus = loss_func(model, self.data)
            
            # 计算梯度
            gradient = (loss_plus - loss_minus) / (2 * eps)
            gradients.append(gradient)
            
            # 恢复原始值
            model.weights[i] = original_value
        
        self.gradients = np.array(gradients)
        return self.gradients


class ParameterServer:
    """参数服务器"""
    
    def __init__(self, model: Any):
        """
        初始化参数服务器
        
        Args:
            model: 全局模型
        """
        self.global_model = model
        self.worker_gradients = {}
        self.aggregation_history = []
        self.n_workers = 0
    
    def register_worker(self, worker_id: int):
        """注册工作节点"""
        self.worker_gradients[worker_id] = None
        self.n_workers += 1
    
    def receive_gradients(self, worker_id: int, gradients: np.ndarray):
        """接收梯度"""
        if worker_id not in self.worker_gradients:
            raise ValueError(f"未注册的工作节点: {worker_id}")
        self.worker_gradients[worker_id] = gradients
    
    def aggregate_gradients(self, method: str = 'average') -> np.ndarray:
        """
        聚合梯度
        
        Args:
            method: 聚合方法 ('average', 'weighted', 'median')
            
        Returns:
            聚合后的梯度
        """
        gradients_list = [g for g in self.worker_gradients.values() if g is not None]
        
        if len(gradients_list) == 0:
            raise ValueError("没有可用的梯度")
        
        if method == 'average':
            # 平均聚合
            aggregated = np.mean(gradients_list, axis=0)
        elif method == 'weighted':
            # 加权聚合（简化版，使用样本数作为权重）
            aggregated = np.mean(gradients_list, axis=0)
        elif method == 'median':
            # 中位数聚合
            aggregated = np.median(gradients_list, axis=0)
        else:
            raise ValueError(f"未知的聚合方法: {method}")
        
        # 记录历史
        self.aggregation_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'n_workers': len(gradients_list),
            'gradient_norm': np.linalg.norm(aggregated)
        })
        
        # 清空梯度
        for worker_id in self.worker_gradients:
            self.worker_gradients[worker_id] = None
        
        return aggregated
    
    def update_model(self, learning_rate: float = 0.01):
        """
        更新全局模型
        
        Args:
            learning_rate: 学习率
        """
        # 聚合梯度
        aggregated_gradients = self.aggregate_gradients()
        
        # 更新模型参数
        for i in range(len(self.global_model.weights)):
            self.global_model.weights[i] -= learning_rate * aggregated_gradients[i]
    
    def get_global_model(self) -> Any:
        """获取全局模型"""
        return self.global_model
    
    def get_aggregation_history(self, limit: int = 100) -> List[Dict]:
        """获取聚合历史"""
        return self.aggregation_history[-limit:]


class SimpleModel:
    """简单模型（用于演示）"""
    
    def __init__(self, input_size: int, hidden_size: int = 64, output_size: int = 1):
        """
        初始化模型
        
        Args:
            input_size: 输入维度
            hidden_size: 隐藏层维度
            output_size: 输出维度
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # 模型参数
        self.weights = [
            np.random.randn(input_size, hidden_size) * 0.1,
            np.random.randn(hidden_size, output_size) * 0.1
        ]
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """前向传播"""
        h = np.maximum(0, np.dot(X, self.weights[0]))
        output = np.dot(h, self.weights[1])
        return output
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        return self.forward(X)
    
    def get_parameters(self) -> List[np.ndarray]:
        """获取参数"""
        return self.weights
    
    def set_parameters(self, parameters: List[np.ndarray]):
        """设置参数"""
        self.weights = parameters


class DistributedTrainingSystem:
    """分布式训练系统"""
    
    def __init__(self, n_workers: int = 4):
        """
        初始化分布式训练系统
        
        Args:
            n_workers: 工作节点数量
        """
        self.n_workers = n_workers
        self.workers = {}
        self.parameter_server = None
        self.data_partition = None
        self.training_history = []
        self.best_model = None
        self.best_loss = float('inf')
    
    def setup(self, data: pd.DataFrame, model: SimpleModel):
        """
        设置分布式训练
        
        Args:
            data: 训练数据
            model: 模型
        """
        # 数据分区
        self.data_partition = DataPartition(data, self.n_workers)
        
        # 创建工作节点
        for i in range(self.n_workers):
            partition_data = self.data_partition.get_partition(i)
            self.workers[i] = Worker(i, partition_data)
        
        # 创建参数服务器
        self.parameter_server = ParameterServer(model)
        
        # 注册工作节点
        for i in range(self.n_workers):
            self.parameter_server.register_worker(i)
    
    def train_synchronous(self, train_func: Callable, loss_func: Callable,
                         n_epochs: int = 10, learning_rate: float = 0.01) -> Dict[str, Any]:
        """
        同步训练
        
        Args:
            train_func: 训练函数
            loss_func: 损失函数
            n_epochs: 训练轮数
            learning_rate: 学习率
            
        Returns:
            训练结果
        """
        start_time = time.time()
        epoch_losses = []
        
        for epoch in range(n_epochs):
            epoch_start = time.time()
            
            # 每个工作节点训练
            worker_results = []
            for worker_id, worker in self.workers.items():
                global_model = self.parameter_server.get_global_model()
                result = worker.train(global_model, train_func, epochs=1)
                worker_results.append(result)
            
            # 计算梯度
            for worker_id, worker in self.workers.items():
                global_model = self.parameter_server.get_global_model()
                gradients = worker.compute_gradients(global_model, loss_func)
                self.parameter_server.receive_gradients(worker_id, gradients)
            
            # 聚合梯度并更新模型
            self.parameter_server.update_model(learning_rate)
            
            # 评估模型
            global_model = self.parameter_server.get_global_model()
            total_loss = 0.0
            for worker in self.workers.values():
                loss = loss_func(global_model, worker.data)
                total_loss += loss
            avg_loss = total_loss / len(self.workers)
            
            epoch_losses.append(avg_loss)
            epoch_time = time.time() - epoch_start
            
            # 记录历史
            self.training_history.append({
                'epoch': epoch,
                'loss': avg_loss,
                'epoch_time': epoch_time,
                'timestamp': datetime.now().isoformat()
            })
            
            # 保存最佳模型
            if avg_loss < self.best_loss:
                self.best_loss = avg_loss
                self.best_model = global_model.get_parameters()
            
            print(f"Epoch {epoch + 1}/{n_epochs}, Loss: {avg_loss:.4f}, Time: {epoch_time:.2f}s")
        
        total_time = time.time() - start_time
        
        return {
            'n_epochs': n_epochs,
            'total_time': total_time,
            'avg_epoch_time': np.mean([h['epoch_time'] for h in self.training_history]),
            'final_loss': epoch_losses[-1],
            'best_loss': self.best_loss,
            'epoch_losses': epoch_losses
        }
    
    def train_asynchronous(self, train_func: Callable, loss_func: Callable,
                          n_epochs: int = 10, learning_rate: float = 0.01,
                          staleness: int = 3) -> Dict[str, Any]:
        """
        异步训练
        
        Args:
            train_func: 训练函数
            loss_func: 损失函数
            n_epochs: 训练轮数
            learning_rate: 学习率
            staleness: 延迟容忍度
            
        Returns:
            训练结果
        """
        start_time = time.time()
        epoch_losses = []
        
        # 使用线程池实现异步训练
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            for epoch in range(n_epochs):
                epoch_start = time.time()
                
                # 提交训练任务
                futures = []
                for worker_id, worker in self.workers.items():
                    global_model = self.parameter_server.get_global_model()
                    future = executor.submit(worker.train, global_model, train_func, 1)
                    futures.append((worker_id, future))
                
                # 等待完成并计算梯度
                for worker_id, future in futures:
                    result = future.result()
                    global_model = self.parameter_server.get_global_model()
                    gradients = self.workers[worker_id].compute_gradients(global_model, loss_func)
                    self.parameter_server.receive_gradients(worker_id, gradients)
                
                # 聚合梯度并更新模型
                self.parameter_server.update_model(learning_rate)
                
                # 评估模型
                global_model = self.parameter_server.get_global_model()
                total_loss = 0.0
                for worker in self.workers.values():
                    loss = loss_func(global_model, worker.data)
                    total_loss += loss
                avg_loss = total_loss / len(self.workers)
                
                epoch_losses.append(avg_loss)
                epoch_time = time.time() - epoch_start
                
                # 记录历史
                self.training_history.append({
                    'epoch': epoch,
                    'loss': avg_loss,
                    'epoch_time': epoch_time,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 保存最佳模型
                if avg_loss < self.best_loss:
                    self.best_loss = avg_loss
                    self.best_model = global_model.get_parameters()
                
                print(f"Epoch {epoch + 1}/{n_epochs}, Loss: {avg_loss:.4f}, Time: {epoch_time:.2f}s")
        
        total_time = time.time() - start_time
        
        return {
            'n_epochs': n_epochs,
            'total_time': total_time,
            'avg_epoch_time': np.mean([h['epoch_time'] for h in self.training_history]),
            'final_loss': epoch_losses[-1],
            'best_loss': self.best_loss,
            'epoch_losses': epoch_losses
        }
    
    def get_training_history(self, limit: int = 100) -> List[Dict]:
        """获取训练历史"""
        return self.training_history[-limit:]
    
    def get_best_model(self) -> Optional[List[np.ndarray]]:
        """获取最佳模型"""
        return self.best_model
    
    def save_model(self, filepath: str):
        """保存模型"""
        if self.best_model is None:
            raise ValueError("没有可保存的模型")
        
        model_data = {
            'best_loss': self.best_loss,
            'parameters': [w.tolist() for w in self.best_model],
            'training_history': self.training_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f)
    
    def load_model(self, filepath: str, model: SimpleModel):
        """加载模型"""
        with open(filepath, 'r') as f:
            model_data = json.load(f)
        
        parameters = [np.array(w) for w in model_data['parameters']]
        model.set_parameters(parameters)
        self.best_model = parameters
        self.best_loss = model_data['best_loss']
        self.training_history = model_data['training_history']
        
        return model