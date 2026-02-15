"""
强化学习交易代理
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class TradingEnvironment:
    """
    交易环境
    
    用于强化学习的环境模拟
    """
    
    def __init__(self, df: pd.DataFrame, initial_capital: float = 100000):
        """
        初始化交易环境
        
        Args:
            df: K线数据
            initial_capital: 初始资金
        """
        self.df = df
        self.initial_capital = initial_capital
        
        # 状态空间
        self.current_step = 0
        self.capital = initial_capital
        self.position = 0  # 0: 空仓, 1: 满仓
        self.position_size = 0
        self.entry_price = 0
        
        # 动作空间
        self.action_space = 3  # 0: 持有, 1: 买入, 2: 卖出
    
    def reset(self) -> np.ndarray:
        """
        重置环境
        
        Returns:
            初始状态
        """
        self.current_step = 0
        self.capital = self.initial_capital
        self.position = 0
        self.position_size = 0
        self.entry_price = 0
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """
        获取当前状态
        
        Returns:
            状态向量
        """
        if self.current_step >= len(self.df):
            return np.zeros(10)
        
        row = self.df.iloc[self.current_step]
        
        # 技术指标
        state = [
            row['close'] / row['open'] - 1,  # 日收益率
            row['high'] / row['close'] - 1,   # 最高涨幅
            row['low'] / row['close'] - 1,    # 最低跌幅
            row['volume'] / row['volume'].rolling(20).mean().iloc[-1] if self.current_step >= 20 else 1,  # 成交量比率
            self.position,  # 持仓状态
            self.capital / self.initial_capital,  # 资金比例
        ]
        
        # 添加历史价格特征 (最近5天)
        for i in range(1, 6):
            if self.current_step - i >= 0:
                state.append(self.df.iloc[self.current_step - i]['close'] / row['close'] - 1)
            else:
                state.append(0)
        
        return np.array(state)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行动作
        
        Args:
            action: 动作 (0: 持有, 1: 买入, 2: 卖出)
        
        Returns:
            (状态, 奖励, 是否结束, 信息)
        """
        if self.current_step >= len(self.df) - 1:
            return self._get_state(), 0, True, {}
        
        # 获取当前价格
        current_price = self.df.iloc[self.current_step]['close']
        
        # 执行动作
        reward = 0
        
        if action == 1 and self.position == 0:  # 买入
            self.position = 1
            self.position_size = int(self.capital * 0.95 / current_price / 100) * 100
            self.entry_price = current_price
            self.capital -= self.position_size * current_price
            reward = 0  # 买入不奖励
        
        elif action == 2 and self.position == 1:  # 卖出
            self.position = 0
            profit = (current_price - self.entry_price) * self.position_size
            self.capital += self.position_size * current_price
            reward = profit / self.initial_capital  # 奖励 = 收益率
            self.position_size = 0
            self.entry_price = 0
        
        elif action == 0:  # 持有
            if self.position == 1:
                # 计算浮动盈亏
                unrealized_pnl = (current_price - self.entry_price) * self.position_size
                reward = unrealized_pnl / self.initial_capital * 0.1  # 浮动盈亏的10%作为奖励
        
        # 移动到下一步
        self.current_step += 1
        
        # 检查是否结束
        done = self.current_step >= len(self.df) - 1
        
        # 信息
        info = {
            'capital': self.capital,
            'position': self.position,
            'price': current_price
        }
        
        return self._get_state(), reward, done, info


class RLAgentBase(ABC):
    """
    强化学习代理基类
    """
    
    def __init__(self, name: str, state_size: int, action_size: int):
        """
        初始化代理
        
        Args:
            name: 代理名称
            state_size: 状态空间大小
            action_size: 动作空间大小
        """
        self.name = name
        self.state_size = state_size
        self.action_size = action_size
        self.model = None
        self.is_trained = False
    
    @abstractmethod
    def train(self, env: TradingEnvironment, episodes: int = 100):
        """
        训练代理
        
        Args:
            env: 交易环境
            episodes: 训练回合数
        """
        pass
    
    @abstractmethod
    def act(self, state: np.ndarray) -> int:
        """
        选择动作
        
        Args:
            state: 当前状态
        
        Returns:
            动作
        """
        pass


class DQNAgent(RLAgentBase):
    """
    DQN (Deep Q-Network) 代理
    """
    
    def __init__(self, state_size: int = 10, action_size: int = 3):
        super().__init__("DQN代理", state_size, action_size)
        self.memory = []
        self.gamma = 0.95  # 折扣因子
        self.epsilon = 1.0  # 探索率
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.batch_size = 32
    
    def _build_model(self):
        """构建DQN模型"""
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Dense, Dropout
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return None
        
        model = Sequential([
            Dense(64, input_dim=self.state_size, activation='relu'),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        
        model.compile(loss='mse', optimizer='adam')
        return model
    
    def remember(self, state, action, reward, next_state, done):
        """存储经验"""
        self.memory.append((state, action, reward, next_state, done))
        
        # 限制记忆大小
        if len(self.memory) > 2000:
            self.memory.pop(0)
    
    def act(self, state: np.ndarray) -> int:
        """
        选择动作 (epsilon-greedy策略)
        
        Args:
            state: 当前状态
        
        Returns:
            动作
        """
        if np.random.rand() <= self.epsilon:
            return np.random.randint(self.action_size)
        
        if self.model is None:
            self.model = self._build_model()
        
        act_values = self.model.predict(state.reshape(1, -1), verbose=0)
        return np.argmax(act_values[0])
    
    def replay(self, batch_size: int = 32):
        """经验回放"""
        if len(self.memory) < batch_size:
            return
        
        minibatch = np.random.choice(self.memory, batch_size, replace=False)
        
        for state, action, reward, next_state, done in minibatch:
            target = reward
            
            if not done:
                if self.model is None:
                    self.model = self._build_model()
                target = reward + self.gamma * np.amax(
                    self.model.predict(next_state.reshape(1, -1), verbose=0)[0]
                )
            
            target_f = self.model.predict(state.reshape(1, -1), verbose=0)
            target_f[0][action] = target
            
            self.model.fit(state.reshape(1, -1), target_f, epochs=1, verbose=0)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def train(self, env: TradingEnvironment, episodes: int = 100):
        """
        训练DQN代理
        
        Args:
            env: 交易环境
            episodes: 训练回合数
        """
        if self.model is None:
            self.model = self._build_model()
        
        for e in range(episodes):
            state = env.reset()
            total_reward = 0
            
            for time in range(len(env.df) - 1):
                action = self.act(state)
                next_state, reward, done, _ = env.step(action)
                
                self.remember(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                
                if done:
                    break
                
                # 经验回放
                if len(self.memory) > self.batch_size:
                    self.replay(self.batch_size)
            
            logger.info(f"回合 {e+1}/{episodes}, 总奖励: {total_reward:.4f}, 探索率: {self.epsilon:.2f}")
        
        self.is_trained = True
        logger.info("DQN训练完成")


class PPOAgent(RLAgentBase):
    """
    PPO (Proximal Policy Optimization) 代理
    """
    
    def __init__(self, state_size: int = 10, action_size: int = 3):
        super().__init__("PPO代理", state_size, action_size)
        self.gamma = 0.99
        self.clip_ratio = 0.2
    
    def _build_model(self):
        """构建PPO模型"""
        try:
            from tensorflow.keras.models import Model
            from tensorflow.keras.layers import Input, Dense
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return None, None
        
        # Actor网络
        actor_input = Input(shape=(self.state_size,))
        x = Dense(64, activation='relu')(actor_input)
        x = Dense(32, activation='relu')(x)
        actor_output = Dense(self.action_size, activation='softmax')(x)
        actor = Model(actor_input, actor_output)
        
        # Critic网络
        critic_input = Input(shape=(self.state_size,))
        y = Dense(64, activation='relu')(critic_input)
        y = Dense(32, activation='relu')(y)
        critic_output = Dense(1)(y)
        critic = Model(critic_input, critic_output)
        
        actor.compile(optimizer='adam', loss='categorical_crossentropy')
        critic.compile(optimizer='adam', loss='mse')
        
        return actor, critic
    
    def act(self, state: np.ndarray) -> int:
        """
        选择动作 (基于策略)
        
        Args:
            state: 当前状态
        
        Returns:
            动作
        """
        if self.model is None:
            self.model = self._build_model()
        
        actor, _ = self.model
        
        probs = actor.predict(state.reshape(1, -1), verbose=0)[0]
        return np.random.choice(self.action_size, p=probs)
    
    def train(self, env: TradingEnvironment, episodes: int = 100):
        """
        训练PPO代理
        
        Args:
            env: 交易环境
            episodes: 训练回合数
        """
        if self.model is None:
            self.model = self._build_model()
        
        actor, critic = self.model
        
        for e in range(episodes):
            state = env.reset()
            episode_memory = []
            total_reward = 0
            
            for time in range(len(env.df) - 1):
                # 选择动作
                probs = actor.predict(state.reshape(1, -1), verbose=0)[0]
                action = np.random.choice(self.action_size, p=probs)
                
                # 执行动作
                next_state, reward, done, _ = env.step(action)
                
                # 存储经验
                episode_memory.append({
                    'state': state,
                    'action': action,
                    'reward': reward,
                    'next_state': next_state,
                    'done': done,
                    'prob': probs[action]
                })
                
                state = next_state
                total_reward += reward
                
                if done:
                    break
            
            # 计算优势函数
            returns = []
            G = 0
            for step in reversed(episode_memory):
                G = step['reward'] + self.gamma * G
                returns.insert(0, G)
            
            returns = np.array(returns)
            returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)
            
            # 更新策略
            for step in episode_memory:
                state = step['state']
                action = step['action']
                old_prob = step['prob']
                G = returns[episode_memory.index(step)]
                
                # 计算新概率
                probs = actor.predict(state.reshape(1, -1), verbose=0)[0]
                new_prob = probs[action]
                
                # 计算比率
                ratio = new_prob / (old_prob + 1e-8)
                
                # PPO裁剪
                surr1 = ratio * G
                surr2 = np.clip(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio) * G
                
                # 更新Actor
                with actor.graph.as_default():
                    actor.train_on_batch(
                        state.reshape(1, -1),
                        np.eye(self.action_size)[action:action+1]
                    )
                
                # 更新Critic
                state_value = critic.predict(state.reshape(1, -1), verbose=0)[0][0]
                critic.train_on_batch(state.reshape(1, -1), np.array([[G]]))
            
            logger.info(f"回合 {e+1}/{episodes}, 总奖励: {total_reward:.4f}")
        
        self.is_trained = True
        logger.info("PPO训练完成")