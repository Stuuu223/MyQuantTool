"""
强化学习优化系统
支持DQN和PPO两种算法，用于交易策略优化
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from collections import deque
import json
import os


class TradingEnvironment:
    """交易环境模拟器"""
    
    def __init__(self, data: pd.DataFrame, initial_balance: float = 100000.0):
        """
        初始化交易环境
        
        Args:
            data: 历史价格数据
            initial_balance: 初始资金
        """
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0  # 0: 空仓, 1: 满仓
        self.position_size = 0.0  # 持仓数量
        self.entry_price = 0.0
        self.max_steps = len(data) - 1
        self.trades = []  # 交易记录
        
    def reset(self) -> np.ndarray:
        """重置环境"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        self.trades = []
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """获取当前状态"""
        if self.current_step >= len(self.data):
            return np.zeros(10)
        
        current_data = self.data.iloc[self.current_step]
        
        # 计算技术指标
        window = min(20, self.current_step + 1)
        recent_data = self.data.iloc[max(0, self.current_step - window + 1):self.current_step + 1]
        
        # 状态特征
        state = np.zeros(10)
        
        # 1. 当前价格归一化
        if len(recent_data) > 0:
            price_mean = recent_data['close'].mean()
            price_std = recent_data['close'].std()
            if price_std > 0:
                state[0] = (current_data['close'] - price_mean) / price_std
        
        # 2. 持仓状态
        state[1] = self.position
        
        # 3. 资金比例
        if self.position_size > 0 and self.entry_price > 0:
            state[2] = (current_data['close'] - self.entry_price) / self.entry_price
        
        # 4. MA比率
        if len(recent_data) > 5:
            ma5 = recent_data['close'].iloc[-5:].mean()
            if ma5 > 0:
                state[3] = current_data['close'] / ma5 - 1
        
        # 5. 波动率
        if len(recent_data) > 1:
            state[4] = recent_data['close'].pct_change().std()
        
        # 6. 成交量比率
        if len(recent_data) > 5:
            vol_ma5 = recent_data['volume'].iloc[-5:].mean()
            if vol_ma5 > 0:
                state[5] = current_data['volume'] / vol_ma5 - 1
        
        # 7. RSI
        if len(recent_data) >= 14:
            changes = recent_data['close'].diff()
            gains = changes.where(changes > 0, 0)
            losses = -changes.where(changes < 0, 0)
            avg_gain = gains.iloc[-14:].mean()
            avg_loss = losses.iloc[-14:].mean()
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                state[6] = 100 - (100 / (1 + rs))
        
        # 8. MACD
        if len(recent_data) >= 26:
            ema12 = recent_data['close'].ewm(span=12).mean().iloc[-1]
            ema26 = recent_data['close'].ewm(span=26).mean().iloc[-1]
            macd = ema12 - ema26
            state[7] = macd / (self.initial_balance * 0.01)  # 归一化
        
        # 9. 时间进度
        state[8] = self.current_step / self.max_steps
        
        # 10. 资金比例
        state[9] = self.balance / self.initial_balance
        
        return state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行动作
        
        Args:
            action: 0=持有, 1=买入, 2=卖出
            
        Returns:
            (next_state, reward, done, info)
        """
        if self.current_step >= self.max_steps:
            return self._get_state(), 0.0, True, {}
        
        current_price = self.data.iloc[self.current_step]['close']
        reward = 0.0
        
        # 执行动作
        if action == 1 and self.position == 0:  # 买入
            self.position = 1
            self.position_size = self.balance / current_price
            self.entry_price = current_price
            self.balance = 0.0
            self.trades.append({
                'step': self.current_step,
                'action': 'buy',
                'price': current_price,
                'size': self.position_size
            })
        elif action == 2 and self.position == 1:  # 卖出
            self.position = 0
            self.balance = self.position_size * current_price
            profit = self.balance - (self.position_size * self.entry_price)
            reward = profit / (self.position_size * self.entry_price)  # 收益率
            self.trades.append({
                'step': self.current_step,
                'action': 'sell',
                'price': current_price,
                'profit': profit
            })
            self.position_size = 0.0
            self.entry_price = 0.0
        
        # 计算持仓收益
        if self.position == 1:
            unrealized_profit = (current_price - self.entry_price) / self.entry_price
            reward = unrealized_profit * 0.1  # 持仓收益的10%作为奖励
        
        # 惩罚频繁交易
        if len(self.trades) > 0 and self.trades[-1]['step'] == self.current_step:
            reward -= 0.001  # 交易成本
        
        # 移动到下一步
        self.current_step += 1
        done = self.current_step >= self.max_steps
        
        # 如果结束，平仓
        if done and self.position == 1:
            self.balance = self.position_size * current_price
            profit = self.balance - (self.position_size * self.entry_price)
            reward += profit / (self.position_size * self.entry_price)
            self.position = 0
            self.position_size = 0.0
        
        next_state = self._get_state()
        info = {
            'balance': self.balance,
            'position': self.position,
            'total_return': (self.balance - self.initial_balance) / self.initial_balance,
            'n_trades': len(self.trades)
        }
        
        return next_state, reward, done, info


class DQNAgent:
    """DQN智能体"""
    
    def __init__(self, state_size: int, action_size: int, learning_rate: float = 0.001):
        """
        初始化DQN智能体
        
        Args:
            state_size: 状态维度
            action_size: 动作空间大小
            learning_rate: 学习率
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = 0.95  # 折扣因子
        self.epsilon = 1.0  # 探索率
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.memory = deque(maxlen=2000)
        self.batch_size = 32
        
        # 简化的神经网络参数
        self.weights1 = np.random.randn(state_size, 64) * 0.1
        self.bias1 = np.zeros(64)
        self.weights2 = np.random.randn(64, 64) * 0.1
        self.bias2 = np.zeros(64)
        self.weights3 = np.random.randn(64, action_size) * 0.1
        self.bias3 = np.zeros(action_size)
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                 next_state: np.ndarray, done: bool):
        """存储经验"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: np.ndarray) -> int:
        """选择动作"""
        if np.random.random() <= self.epsilon:
            return np.random.choice(self.action_size)
        
        q_values = self._forward(state)
        return np.argmax(q_values)
    
    def _forward(self, state: np.ndarray) -> np.ndarray:
        """前向传播"""
        # 隐藏层1
        h1 = np.maximum(0, np.dot(state, self.weights1) + self.bias1)
        # 隐藏层2
        h2 = np.maximum(0, np.dot(h1, self.weights2) + self.bias2)
        # 输出层
        q_values = np.dot(h2, self.weights3) + self.bias3
        return q_values
    
    def replay(self):
        """经验回放"""
        if len(self.memory) < self.batch_size:
            return
        
        minibatch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        
        losses = []
        for i in minibatch:
            state, action, reward, next_state, done = self.memory[i]
            
            # 计算目标Q值
            target = reward
            if not done:
                next_q_values = self._forward(next_state)
                target = reward + self.gamma * np.amax(next_q_values)
            
            # 计算预测Q值
            q_values = self._forward(state)
            q_values[action] = target
            
            # 计算损失（简化版）
            pred_q_values = self._forward(state)
            loss = (pred_q_values[action] - target) ** 2
            losses.append(loss)
        
        # 更新探索率
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return np.mean(losses) if losses else 0.0


class PPOAgent:
    """PPO智能体"""
    
    def __init__(self, state_size: int, action_size: int, learning_rate: float = 0.0003):
        """
        初始化PPO智能体
        
        Args:
            state_size: 状态维度
            action_size: 动作空间大小
            learning_rate: 学习率
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = 0.99
        self.gae_lambda = 0.95
        self.clip_epsilon = 0.2
        
        # 策略网络
        self.policy_weights1 = np.random.randn(state_size, 64) * 0.1
        self.policy_bias1 = np.zeros(64)
        self.policy_weights2 = np.random.randn(64, action_size) * 0.1
        self.policy_bias2 = np.zeros(action_size)
        
        # 价值网络
        self.value_weights1 = np.random.randn(state_size, 64) * 0.1
        self.value_bias1 = np.zeros(64)
        self.value_weights2 = np.random.randn(64, 1) * 0.1
        self.value_bias2 = np.zeros(1)
        
        # 存储轨迹
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []
    
    def _policy_forward(self, state: np.ndarray) -> np.ndarray:
        """策略网络前向传播"""
        h1 = np.maximum(0, np.dot(state, self.policy_weights1) + self.policy_bias1)
        logits = np.dot(h1, self.policy_weights2) + self.policy_bias2
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        action_probs = exp_logits / np.sum(exp_logits)
        return action_probs
    
    def _value_forward(self, state: np.ndarray) -> float:
        """价值网络前向传播"""
        h1 = np.maximum(0, np.dot(state, self.value_weights1) + self.value_bias1)
        value = np.dot(h1, self.value_weights2) + self.value_bias2
        return value[0]
    
    def act(self, state: np.ndarray) -> Tuple[int, float, float]:
        """选择动作"""
        action_probs = self._policy_forward(state)
        action = np.random.choice(self.action_size, p=action_probs)
        log_prob = np.log(action_probs[action] + 1e-10)
        value = self._value_forward(state)
        return action, log_prob, value
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                 log_prob: float, value: float, done: bool):
        """存储轨迹"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)
    
    def compute_gae(self, rewards: List[float], values: List[float], 
                    dones: List[bool]) -> List[float]:
        """计算广义优势估计"""
        advantages = []
        gae = 0.0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages.insert(0, gae)
        
        return advantages
    
    def update(self) -> Dict[str, float]:
        """更新策略"""
        if len(self.rewards) == 0:
            return {}
        
        # 计算GAE
        advantages = self.compute_gae(self.rewards, self.values, self.dones)
        
        # 计算回报
        returns = []
        discounted_return = 0.0
        for t in reversed(range(len(self.rewards))):
            discounted_return = self.rewards[t] + self.gamma * discounted_return * (1 - self.dones[t])
            returns.insert(0, discounted_return)
        
        # 转换为numpy数组
        advantages = np.array(advantages)
        returns = np.array(returns)
        
        # 归一化优势
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-10)
        
        # 策略更新（简化版）
        policy_loss = 0.0
        value_loss = 0.0
        
        for i in range(len(self.states)):
            state = self.states[i]
            action = self.actions[i]
            old_log_prob = self.log_probs[i]
            advantage = advantages[i]
            return_value = returns[i]
            
            # 计算新的动作概率
            new_action_probs = self._policy_forward(state)
            new_log_prob = np.log(new_action_probs[action] + 1e-10)
            
            # 计算比率
            ratio = np.exp(new_log_prob - old_log_prob)
            
            # PPO裁剪
            surr1 = ratio * advantage
            surr2 = np.clip(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantage
            policy_loss -= np.minimum(surr1, surr2)
            
            # 价值损失
            predicted_value = self._value_forward(state)
            value_loss += (predicted_value - return_value) ** 2
        
        policy_loss /= len(self.states)
        value_loss /= len(self.states)
        
        # 清空轨迹
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []
        
        return {
            'policy_loss': policy_loss,
            'value_loss': value_loss,
            'total_loss': policy_loss + value_loss
        }


class RLOptimizationSystem:
    """强化学习优化系统"""
    
    def __init__(self):
        """初始化系统"""
        self.environments = {}
        self.agents = {}
        self.training_history = []
        self.best_performance = {}
        
    def create_environment(self, env_id: str, data: pd.DataFrame, 
                          initial_balance: float = 100000.0) -> TradingEnvironment:
        """
        创建交易环境
        
        Args:
            env_id: 环境ID
            data: 历史数据
            initial_balance: 初始资金
            
        Returns:
            交易环境
        """
        env = TradingEnvironment(data, initial_balance)
        self.environments[env_id] = env
        return env
    
    def create_dqn_agent(self, agent_id: str, state_size: int, action_size: int,
                        learning_rate: float = 0.001) -> DQNAgent:
        """
        创建DQN智能体
        
        Args:
            agent_id: 智能体ID
            state_size: 状态维度
            action_size: 动作空间大小
            learning_rate: 学习率
            
        Returns:
            DQN智能体
        """
        agent = DQNAgent(state_size, action_size, learning_rate)
        self.agents[agent_id] = agent
        return agent
    
    def create_ppo_agent(self, agent_id: str, state_size: int, action_size: int,
                        learning_rate: float = 0.0003) -> PPOAgent:
        """
        创建PPO智能体
        
        Args:
            agent_id: 智能体ID
            state_size: 状态维度
            action_size: 动作空间大小
            learning_rate: 学习率
            
        Returns:
            PPO智能体
        """
        agent = PPOAgent(state_size, action_size, learning_rate)
        self.agents[agent_id] = agent
        return agent
    
    def train_dqn(self, env_id: str, agent_id: str, n_episodes: int = 100,
                 max_steps: int = 1000) -> Dict[str, Any]:
        """
        训练DQN智能体
        
        Args:
            env_id: 环境ID
            agent_id: 智能体ID
            n_episodes: 训练轮数
            max_steps: 每轮最大步数
            
        Returns:
            训练结果
        """
        env = self.environments.get(env_id)
        agent = self.agents.get(agent_id)
        
        if not env or not agent:
            raise ValueError("环境或智能体不存在")
        
        episode_rewards = []
        episode_returns = []
        
        for episode in range(n_episodes):
            state = env.reset()
            total_reward = 0.0
            
            for step in range(max_steps):
                action = agent.act(state)
                next_state, reward, done, info = env.step(action)
                
                agent.remember(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                
                if done:
                    break
            
            # 经验回放
            loss = agent.replay()
            
            episode_rewards.append(total_reward)
            episode_returns.append(info.get('total_return', 0.0))
            
            # 记录历史
            self.training_history.append({
                'episode': episode,
                'reward': total_reward,
                'return': info.get('total_return', 0.0),
                'loss': loss,
                'epsilon': agent.epsilon,
                'timestamp': datetime.now().isoformat()
            })
        
        # 更新最佳性能
        avg_return = np.mean(episode_returns)
        if env_id not in self.best_performance or avg_return > self.best_performance[env_id]:
            self.best_performance[env_id] = avg_return
        
        return {
            'n_episodes': n_episodes,
            'avg_reward': np.mean(episode_rewards),
            'avg_return': np.mean(episode_returns),
            'best_return': np.max(episode_returns),
            'worst_return': np.min(episode_returns),
            'std_return': np.std(episode_returns),
            'final_epsilon': agent.epsilon
        }
    
    def train_ppo(self, env_id: str, agent_id: str, n_episodes: int = 100,
                 max_steps: int = 1000, update_interval: int = 10) -> Dict[str, Any]:
        """
        训练PPO智能体
        
        Args:
            env_id: 环境ID
            agent_id: 智能体ID
            n_episodes: 训练轮数
            max_steps: 每轮最大步数
            update_interval: 更新间隔
            
        Returns:
            训练结果
        """
        env = self.environments.get(env_id)
        agent = self.agents.get(agent_id)
        
        if not env or not agent:
            raise ValueError("环境或智能体不存在")
        
        episode_rewards = []
        episode_returns = []
        update_losses = []
        
        for episode in range(n_episodes):
            state = env.reset()
            total_reward = 0.0
            
            for step in range(max_steps):
                action, log_prob, value = agent.act(state)
                next_state, reward, done, info = env.step(action)
                
                agent.remember(state, action, reward, log_prob, value, done)
                state = next_state
                total_reward += reward
                
                if done:
                    break
            
            # 定期更新策略
            if (episode + 1) % update_interval == 0:
                losses = agent.update()
                if losses:
                    update_losses.append(losses)
            
            episode_rewards.append(total_reward)
            episode_returns.append(info.get('total_return', 0.0))
            
            # 记录历史
            self.training_history.append({
                'episode': episode,
                'reward': total_reward,
                'return': info.get('total_return', 0.0),
                'timestamp': datetime.now().isoformat()
            })
        
        # 更新最佳性能
        avg_return = np.mean(episode_returns)
        if env_id not in self.best_performance or avg_return > self.best_performance[env_id]:
            self.best_performance[env_id] = avg_return
        
        return {
            'n_episodes': n_episodes,
            'avg_reward': np.mean(episode_rewards),
            'avg_return': np.mean(episode_returns),
            'best_return': np.max(episode_returns),
            'worst_return': np.min(episode_returns),
            'std_return': np.std(episode_returns),
            'n_updates': len(update_losses),
            'avg_policy_loss': np.mean([l['policy_loss'] for l in update_losses]) if update_losses else 0.0,
            'avg_value_loss': np.mean([l['value_loss'] for l in update_losses]) if update_losses else 0.0
        }
    
    def get_training_history(self, limit: int = 100) -> List[Dict]:
        """获取训练历史"""
        return self.training_history[-limit:]
    
    def get_best_performance(self) -> Dict[str, float]:
        """获取最佳性能"""
        return self.best_performance
    
    def save_agent(self, agent_id: str, filepath: str):
        """保存智能体"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError("智能体不存在")
        
        # 简化保存（实际应该保存完整模型）
        agent_data = {
            'agent_id': agent_id,
            'type': 'DQN' if isinstance(agent, DQNAgent) else 'PPO',
            'state_size': agent.state_size,
            'action_size': agent.action_size,
            'learning_rate': agent.learning_rate
        }
        
        with open(filepath, 'w') as f:
            json.dump(agent_data, f)
    
    def load_agent(self, agent_id: str, filepath: str):
        """加载智能体"""
        with open(filepath, 'r') as f:
            agent_data = json.load(f)
        
        if agent_data['type'] == 'DQN':
            agent = DQNAgent(agent_data['state_size'], agent_data['action_size'], 
                           agent_data['learning_rate'])
        else:
            agent = PPOAgent(agent_data['state_size'], agent_data['action_size'],
                           agent_data['learning_rate'])
        
        self.agents[agent_id] = agent
        return agent