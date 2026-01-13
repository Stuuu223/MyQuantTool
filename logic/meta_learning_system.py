"""
元学习系统
实现MAML算法和快速适应能力
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
import sqlite3
from collections import deque


class Task:
    """任务类"""
    
    def __init__(self, 
                 task_id: str,
                 train_data: pd.DataFrame,
                 test_data: pd.DataFrame):
        """
        初始化任务
        
        Args:
            task_id: 任务ID
            train_data: 训练数据
            test_data: 测试数据
        """
        self.task_id = task_id
        self.train_data = train_data
        self.test_data = test_data
    
    def get_support_set(self, n_samples: int = 5) -> pd.DataFrame:
        """获取支持集"""
        return self.train_data.head(n_samples)
    
    def get_query_set(self, n_samples: int = 5) -> pd.DataFrame:
        """获取查询集"""
        return self.test_data.head(n_samples)


class MAMLModel:
    """MAML模型"""
    
    def __init__(self, 
                 input_dim: int,
                 hidden_dim: int = 64,
                 output_dim: int = 1):
        """
        初始化MAML模型
        
        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            output_dim: 输出维度
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # 初始化参数
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.001  # 更小的初始化
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, output_dim) * 0.001  # 更小的初始化
        self.b2 = np.zeros(output_dim)
        
        # 元学习参数
        self.meta_lr = 0.0001  # 进一步降低学习率
        self.inner_lr = 0.001  # 进一步降低内部学习率
        self.inner_steps = 3  # 减少内部步数
        self.grad_clip = 0.1  # 更严格的梯度裁剪
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        前向传播
        
        Args:
            X: 输入数据
            
        Returns:
            输出
        """
        # 隐藏层
        h = np.dot(X, self.W1) + self.b1
        h = np.maximum(0, h)  # ReLU
        
        # 输出层
        y = np.dot(h, self.W2) + self.b2
        
        return y
    
    def compute_loss(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """
        计算损失
        
        Args:
            y_pred: 预测值
            y_true: 真实值
            
        Returns:
            损失值
        """
        return np.mean((y_pred - y_true) ** 2)
    
    def inner_update(self, 
                    X_support: np.ndarray,
                    y_support: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        内部更新
        
        Args:
            X_support: 支持集输入
            y_support: 支持集标签
            
        Returns:
            更新后的参数
        """
        # 复制参数
        W1 = self.W1.copy()
        b1 = self.b1.copy()
        W2 = self.W2.copy()
        b2 = self.b2.copy()
        
        # 多步梯度下降
        for _ in range(self.inner_steps):
            # 前向传播
            h = np.dot(X_support, W1) + b1
            h = np.maximum(0, h)
            y_pred = np.dot(h, W2) + b2
            
            # 计算损失
            loss = np.mean((y_pred - y_support) ** 2)
            
            # 反向传播
            d_y_pred = 2 * (y_pred - y_support) / len(y_support)
            
            # 确保维度正确
            if d_y_pred.ndim == 1:
                d_y_pred = d_y_pred.reshape(-1, 1)
            
            # 梯度裁剪
            d_y_pred = np.clip(d_y_pred, -self.grad_clip, self.grad_clip)
            
            d_W2 = np.dot(h.T, d_y_pred)
            d_b2 = np.sum(d_y_pred, axis=0)
            
            d_h = np.dot(d_y_pred, W2.T)
            d_h[h <= 0] = 0  # ReLU梯度
            
            # 梯度裁剪
            d_h = np.clip(d_h, -self.grad_clip, self.grad_clip)
            
            d_W1 = np.dot(X_support.T, d_h)
            d_b1 = np.sum(d_h, axis=0)
            
            # 梯度裁剪
            d_W1 = np.clip(d_W1, -self.grad_clip, self.grad_clip)
            d_W2 = np.clip(d_W2, -self.grad_clip, self.grad_clip)
            
            # 更新参数
            W1 -= self.inner_lr * d_W1
            b1 -= self.inner_lr * d_b1
            W2 -= self.inner_lr * d_W2
            b2 -= self.inner_lr * d_b2
        
        return W1, b1, W2, b2
    
    def meta_update(self, tasks: List[Task]):
        """
        元更新
        
        Args:
            tasks: 任务列表
        """
        # 计算每个任务的梯度
        gradients = []
        
        for task in tasks:
            # 获取支持集和查询集
            X_support = self._prepare_data(task.get_support_set())
            y_support = self._prepare_labels(task.get_support_set())
            X_query = self._prepare_data(task.get_query_set())
            y_query = self._prepare_labels(task.get_query_set())
            
            # 内部更新
            W1, b1, W2, b2 = self.inner_update(X_support, y_support)
            
            # 计算查询集损失和梯度
            h = np.dot(X_query, W1) + b1
            h = np.maximum(0, h)
            y_pred = np.dot(h, W2) + b2
            
            loss = np.mean((y_pred - y_query) ** 2)
            
            # 计算梯度（简化版）
            d_y_pred = 2 * (y_pred - y_query) / len(y_query)
            
            # 确保维度正确
            if d_y_pred.ndim == 1:
                d_y_pred = d_y_pred.reshape(-1, 1)
            
            d_W2 = np.dot(h.T, d_y_pred)
            d_b2 = np.sum(d_y_pred, axis=0)
            
            d_h = np.dot(d_y_pred, W2.T)
            d_h[h <= 0] = 0
            
            d_W1 = np.dot(X_query.T, d_h)
            d_b1 = np.sum(d_h, axis=0)
            
            gradients.append({
                'W1': d_W1,
                'b1': d_b1,
                'W2': d_W2,
                'b2': d_b2
            })
        
        # 平均梯度
        avg_grad = {
            'W1': np.mean([g['W1'] for g in gradients], axis=0),
            'b1': np.mean([g['b1'] for g in gradients], axis=0),
            'W2': np.mean([g['W2'] for g in gradients], axis=0),
            'b2': np.mean([g['b2'] for g in gradients], axis=0)
        }
        
        # 元更新
        self.W1 -= self.meta_lr * avg_grad['W1']
        self.b1 -= self.meta_lr * avg_grad['b1']
        self.W2 -= self.meta_lr * avg_grad['W2']
        self.b2 -= self.meta_lr * avg_grad['b2']
    
    def adapt(self, 
             X_support: np.ndarray,
             y_support: np.ndarray,
             n_steps: int = 5) -> Dict:
        """
        适应新任务
        
        Args:
            X_support: 支持集输入
            y_support: 支持集标签
            n_steps: 适应步数
            
        Returns:
            适应结果
        """
        # 复制参数
        W1 = self.W1.copy()
        b1 = self.b1.copy()
        W2 = self.W2.copy()
        b2 = self.b2.copy()
        
        # 适应
        for _ in range(n_steps):
            h = np.dot(X_support, W1) + b1
            h = np.maximum(0, h)
            y_pred = np.dot(h, W2) + b2
            
            d_y_pred = 2 * (y_pred - y_support) / len(y_support)
            
            # 确保维度正确
            if d_y_pred.ndim == 1:
                d_y_pred = d_y_pred.reshape(-1, 1)
            
            d_W2 = np.dot(h.T, d_y_pred)
            d_b2 = np.sum(d_y_pred, axis=0)
            
            d_h = np.dot(d_y_pred, W2.T)
            d_h[h <= 0] = 0
            
            d_W1 = np.dot(X_support.T, d_h)
            d_b1 = np.sum(d_h, axis=0)
            
            W1 -= self.inner_lr * d_W1
            b1 -= self.inner_lr * d_b1
            W2 -= self.inner_lr * d_W2
            b2 -= self.inner_lr * d_b2
        
        # 计算适应后的损失
        h = np.dot(X_support, W1) + b1
        h = np.maximum(0, h)
        y_pred = np.dot(h, W2) + b2
        loss = np.mean((y_pred - y_support) ** 2)
        
        return {
            'W1': W1,
            'b1': b1,
            'W2': W2,
            'b2': b2,
            'loss': loss
        }
    
    def predict(self, 
               X: np.ndarray,
               adapted_params: Optional[Dict] = None) -> np.ndarray:
        """
        预测
        
        Args:
            X: 输入数据
            adapted_params: 适应后的参数
            
        Returns:
            预测结果
        """
        if adapted_params is None:
            W1, b1, W2, b2 = self.W1, self.b1, self.W2, self.b2
        else:
            W1, b1, W2, b2 = adapted_params['W1'], adapted_params['b1'], adapted_params['W2'], adapted_params['b2']
        
        h = np.dot(X, W1) + b1
        h = np.maximum(0, h)
        y_pred = np.dot(h, W2) + b2
        
        return y_pred
    
    def _prepare_data(self, data: pd.DataFrame) -> np.ndarray:
        """准备数据"""
        # 提取特征
        features = ['close', 'volume', 'pct_chg']
        available_features = [f for f in features if f in data.columns]
        
        if not available_features:
            return np.zeros((len(data), 3))
        
        # 获取数据并归一化
        X = data[available_features].values
        
        # 标准化（Z-score normalization）
        for i in range(X.shape[1]):
            col = X[:, i]
            mean = np.mean(col)
            std = np.std(col)
            if std > 0:
                X[:, i] = (col - mean) / std
        
        return X
    
    def _prepare_labels(self, data: pd.DataFrame) -> np.ndarray:
        """准备标签"""
        # 使用下一个收盘价作为标签
        if 'close' not in data.columns:
            return np.zeros((len(data), 1))
        
        labels = data['close'].values
        
        # 归一化
        mean = np.mean(labels)
        std = np.std(labels)
        if std > 0:
            labels = (labels - mean) / std
        
        # 确保返回二维形状
        if labels.ndim == 1:
            labels = labels.reshape(-1, 1)
        return labels


class MetaLearningSystem:
    """元学习系统（整合类）"""
    
    def __init__(self, 
                 input_dim: int = 3,
                 hidden_dim: int = 64,
                 output_dim: int = 1,
                 db_path: str = 'data/meta_learning_cache.db'):
        """
        初始化系统
        
        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            output_dim: 输出维度
            db_path: 数据库路径
        """
        self.model = MAMLModel(input_dim, hidden_dim, output_dim)
        self.db_path = db_path
        self._init_db()
        self.tasks = []
        self.adaptation_history = deque(maxlen=100)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta_training_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                n_tasks INTEGER,
                meta_loss REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                task_id TEXT,
                n_samples INTEGER,
                adaptation_loss REAL,
                test_loss REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_task(self, 
                   task_id: str,
                   train_data: pd.DataFrame,
                   test_data: pd.DataFrame):
        """
        创建任务
        
        Args:
            task_id: 任务ID
            train_data: 训练数据
            test_data: 测试数据
        """
        task = Task(task_id, train_data, test_data)
        self.tasks.append(task)
    
    def meta_train(self, 
                   tasks: List[Dict] = None,
                   n_epochs: int = 100,
                   tasks_per_epoch: int = 5,
                   n_support: int = 5,
                   n_query: int = 5) -> Dict:
        """
        元训练
        
        Args:
            tasks: 任务列表（可选，如果不提供则使用self.tasks）
            n_epochs: 训练轮数
            tasks_per_epoch: 每轮任务数
            n_support: 支持集大小
            n_query: 查询集大小
            
        Returns:
            训练结果
        """
        if tasks is None:
            tasks = self.tasks
        
        if len(tasks) == 0:
            return {
                'success': False,
                'message': '没有可用的任务'
            }
        
        training_history = []
        
        for epoch in range(n_epochs):
            # 随机采样任务
            sampled_tasks = np.random.choice(self.tasks, 
                                          min(tasks_per_epoch, len(self.tasks)),
                                          replace=False)
            
            # 元更新
            self.model.meta_update(sampled_tasks)
            
            # 计算元损失
            meta_loss = 0
            for task in sampled_tasks:
                X_query = self.model._prepare_data(task.get_query_set())
                y_query = self.model._prepare_labels(task.get_query_set())
                
                y_pred = self.model.predict(X_query)
                loss = self.model.compute_loss(y_pred, y_query)
                meta_loss += loss
            
            meta_loss /= len(sampled_tasks)
            
            training_history.append({
                'epoch': epoch,
                'meta_loss': meta_loss
            })
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}/{n_epochs}, Meta Loss: {meta_loss:.4f}")
        
        # 保存训练历史
        self._save_meta_training(n_epochs, meta_loss)
        
        return {
            'success': True,
            'n_epochs': n_epochs,
            'final_meta_loss': meta_loss,
            'training_history': training_history
        }
    
    def adapt_to_new_task(self,
                         task_id: str,
                         support_data: pd.DataFrame,
                         query_data: pd.DataFrame,
                         n_steps: int = 5) -> Dict:
        """
        适应新任务
        
        Args:
            task_id: 任务ID
            support_data: 支持数据
            query_data: 查询数据
            n_steps: 适应步数
            
        Returns:
            适应结果
        """
        # 准备数据
        X_support = self.model._prepare_data(support_data)
        y_support = self.model._prepare_labels(support_data)
        X_query = self.model._prepare_data(query_data)
        y_query = self.model._prepare_labels(query_data)
        
        # 适应
        adapted_params = self.model.adapt(X_support, y_support, n_steps)
        
        # 在查询集上测试
        y_pred = self.model.predict(X_query, adapted_params)
        test_loss = self.model.compute_loss(y_pred, y_query)
        
        # 记录适应历史
        adaptation_record = {
            'timestamp': datetime.now(),
            'task_id': task_id,
            'n_samples': len(support_data),
            'adaptation_loss': adapted_params['loss'],
            'test_loss': test_loss
        }
        
        self.adaptation_history.append(adaptation_record)
        self._save_adaptation(adaptation_record)
        
        return {
            'task_id': task_id,
            'adaptation_loss': adapted_params['loss'],
            'test_loss': test_loss,
            'adapted_params': adapted_params,
            'predictions': y_pred
        }
    
    def predict(self, 
               X: np.ndarray,
               adapted_params: Optional[Dict] = None) -> np.ndarray:
        """
        预测
        
        Args:
            X: 输入数据
            adapted_params: 适应后的参数
            
        Returns:
            预测结果
        """
        return self.model.predict(X, adapted_params)
    
    def _save_meta_training(self, n_tasks: int, meta_loss: float):
        """保存元训练记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO meta_training_history (n_tasks, meta_loss)
            VALUES (?, ?)
        ''', (n_tasks, meta_loss))
        
        conn.commit()
        conn.close()
    
    def _save_adaptation(self, record: Dict):
        """保存适应记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO adaptation_history (task_id, n_samples, adaptation_loss, test_loss)
            VALUES (?, ?, ?, ?)
        ''', (record['task_id'], record['n_samples'], record['adaptation_loss'], record['test_loss']))
        
        conn.commit()
        conn.close()
    
    def get_adaptation_history(self, limit: int = 50) -> List[Dict]:
        """获取适应历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, task_id, n_samples, adaptation_loss, test_loss
            FROM adaptation_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'task_id': row[1],
                'n_samples': row[2],
                'adaptation_loss': row[3],
                'test_loss': row[4]
            }
            for row in rows
        ]


# 使用示例
if __name__ == '__main__':
    # 创建系统
    system = MetaLearningSystem()
    
    # 创建训练任务
    print("创建训练任务...")
    for i in range(10):
        # 生成模拟数据
        dates = pd.date_range(start=datetime.now() - timedelta(days=20), periods=20)
        train_data = pd.DataFrame({
            'date': dates[:15],
            'close': np.linspace(10, 15, 15) + np.random.randn(15) * 0.5,
            'volume': np.linspace(1000000, 2000000, 15),
            'pct_chg': np.random.randn(15) * 0.02
        })
        
        test_data = pd.DataFrame({
            'date': dates[15:],
            'close': np.linspace(15, 18, 5) + np.random.randn(5) * 0.5,
            'volume': np.linspace(2000000, 2500000, 5),
            'pct_chg': np.random.randn(5) * 0.02
        })
        
        system.create_task(f'task_{i}', train_data, test_data)
    
    # 元训练
    print("\n开始元训练...")
    training_result = system.meta_train(n_epochs=50, tasks_per_epoch=5)
    
    if training_result['success']:
        print(f"\n训练完成!")
        print(f"最终元损失: {training_result['final_meta_loss']:.4f}")
    else:
        print(f"训练失败: {training_result['message']}")
    
    # 适应新任务
    print("\n适应新任务...")
    new_dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=10)
    support_data = pd.DataFrame({
        'date': new_dates[:5],
        'close': np.linspace(20, 22, 5) + np.random.randn(5) * 0.5,
        'volume': np.linspace(3000000, 3500000, 5),
        'pct_chg': np.random.randn(5) * 0.02
    })
    
    query_data = pd.DataFrame({
        'date': new_dates[5:],
        'close': np.linspace(22, 24, 5) + np.random.randn(5) * 0.5,
        'volume': np.linspace(3500000, 4000000, 5),
        'pct_chg': np.random.randn(5) * 0.02
    })
    
    adaptation_result = system.adapt_to_new_task(
        'new_task',
        support_data,
        query_data,
        n_steps=5
    )
    
    print(f"\n适应结果:")
    print(f"任务ID: {adaptation_result['task_id']}")
    print(f"适应损失: {adaptation_result['adaptation_loss']:.4f}")
    print(f"测试损失: {adaptation_result['test_loss']:.4f}")
    print(f"预测值: {adaptation_result['predictions']}")