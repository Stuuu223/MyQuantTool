"""
实时情绪感知系统
实现毫秒级情绪变化感知和状态机自动策略切换
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sqlite3
from collections import deque
import math


class EmotionState:
    """情绪状态机 - 7个状态"""
    
    STATES = [
        '极度恐慌',  # 0
        '恐慌',      # 1
        '谨慎',      # 2
        '中性',      # 3
        '乐观',      # 4
        '贪婪',      # 5
        '极度贪婪'   # 6
    ]
    
    def __init__(self, history_size: int = 100):
        """
        初始化情绪状态机
        
        Args:
            history_size: 历史记录数量
        """
        self.current_state = '中性'
        self.current_index = 3
        self.history = deque(maxlen=history_size)
        self.transitions = self._load_transition_rules()
        self.state_scores = {
            '极度恐慌': -1.0,
            '恐慌': -0.6,
            '谨慎': -0.2,
            '中性': 0.0,
            '乐观': 0.2,
            '贪婪': 0.6,
            '极度贪婪': 1.0
        }
        self.last_transition_time = datetime.now()
    
    def _load_transition_rules(self) -> Dict:
        """加载状态转换规则"""
        return {
            # 从极度恐慌可以转换到
            '极度恐慌': {
                '极度恐慌': 0.7,  # 70%概率保持
                '恐慌': 0.25,     # 25%概率改善
                '谨慎': 0.05      # 5%概率大幅改善
            },
            '恐慌': {
                '极度恐慌': 0.15,
                '恐慌': 0.6,
                '谨慎': 0.2,
                '中性': 0.05
            },
            '谨慎': {
                '恐慌': 0.1,
                '谨慎': 0.6,
                '中性': 0.25,
                '乐观': 0.05
            },
            '中性': {
                '谨慎': 0.2,
                '中性': 0.6,
                '乐观': 0.2
            },
            '乐观': {
                '中性': 0.2,
                '乐观': 0.6,
                '贪婪': 0.15,
                '极度贪婪': 0.05
            },
            '贪婪': {
                '乐观': 0.2,
                '贪婪': 0.6,
                '极度贪婪': 0.2
            },
            '极度贪婪': {
                '乐观': 0.15,
                '贪婪': 0.25,
                '极度贪婪': 0.6
            }
        }
    
    def update(self, sentiment_score: float, timestamp: Optional[datetime] = None) -> Dict:
        """
        更新情绪状态
        
        Args:
            sentiment_score: 情绪得分 (-1 到 1)
            timestamp: 时间戳
            
        Returns:
            状态更新信息
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 记录历史
        self.history.append({
            'score': sentiment_score,
            'timestamp': timestamp,
            'state': self.current_state
        })
        
        # 判断是否需要状态转换
        if self._should_transition(sentiment_score):
            new_state = self._predict_next_state(sentiment_score)
            old_state = self.current_state
            
            # 更新状态
            self.current_state = new_state
            self.current_index = self.STATES.index(new_state)
            self.last_transition_time = timestamp
            
            return {
                'transition': True,
                'old_state': old_state,
                'new_state': new_state,
                'trigger_score': sentiment_score,
                'timestamp': timestamp
            }
        
        return {
            'transition': False,
            'current_state': self.current_state,
            'score': sentiment_score,
            'timestamp': timestamp
        }
    
    def _should_transition(self, sentiment_score: float) -> bool:
        """
        判断是否应该转换状态
        
        Args:
            sentiment_score: 情绪得分
            
        Returns:
            是否需要转换
        """
        # 如果历史记录不足，不转换
        if len(self.history) < 5:
            return False
        
        # 计算最近5次的平均得分
        recent_scores = [h['score'] for h in list(self.history)[-5:]]
        avg_score = np.mean(recent_scores)
        
        # 计算当前状态对应的得分范围
        current_score = self.state_scores[self.current_state]
        
        # 如果平均得分偏离当前状态得分超过阈值，则转换
        threshold = 0.3
        if abs(avg_score - current_score) > threshold:
            return True
        
        # 检查是否有连续3次同向变化
        if len(recent_scores) >= 3:
            if all(recent_scores[i] > recent_scores[i-1] for i in range(1, len(recent_scores))):
                return True  # 连续上升
            if all(recent_scores[i] < recent_scores[i-1] for i in range(1, len(recent_scores))):
                return True  # 连续下降
        
        return False
    
    def _predict_next_state(self, sentiment_score: float) -> str:
        """
        预测下一个状态
        
        Args:
            sentiment_score: 情绪得分
            
        Returns:
            下一个状态
        """
        # 根据得分直接映射到状态
        if sentiment_score <= -0.8:
            return '极度恐慌'
        elif sentiment_score <= -0.4:
            return '恐慌'
        elif sentiment_score <= -0.1:
            return '谨慎'
        elif sentiment_score <= 0.1:
            return '中性'
        elif sentiment_score <= 0.4:
            return '乐观'
        elif sentiment_score <= 0.8:
            return '贪婪'
        else:
            return '极度贪婪'
    
    def get_state_info(self) -> Dict:
        """获取当前状态信息"""
        return {
            'current_state': self.current_state,
            'state_index': self.current_index,
            'state_score': self.state_scores[self.current_state],
            'last_transition_time': self.last_transition_time,
            'history_size': len(self.history),
            'avg_score': np.mean([h['score'] for h in self.history]) if self.history else 0
        }
    
    def detect_anomaly(self, threshold: float = 0.8) -> Optional[Dict]:
        """
        检测情绪异常
        
        Args:
            threshold: 异常阈值
            
        Returns:
            异常信息，如果没有异常则返回None
        """
        if len(self.history) < 10:
            return None
        
        # 计算最近10次的得分标准差
        recent_scores = [h['score'] for h in list(self.history)[-10:]]
        std_score = np.std(recent_scores)
        
        # 如果标准差过大，说明情绪波动剧烈
        if std_score > threshold:
            return {
                'anomaly': True,
                'type': 'high_volatility',
                'std_score': std_score,
                'current_state': self.current_state,
                'message': f'情绪波动剧烈 (标准差: {std_score:.2f})'
            }
        
        # 检查是否有极端情绪
        if abs(self.state_scores[self.current_state]) > 0.8:
            return {
                'anomaly': True,
                'type': 'extreme_emotion',
                'state': self.current_state,
                'message': f'检测到极端情绪: {self.current_state}'
            }
        
        return None


class EmotionStrategyMapper:
    """情绪-策略映射器"""
    
    MAPPING = {
        '极度恐慌': {
            'strategy': '空仓',
            'position': 0.0,
            'risk_level': '极低',
            'action': '清仓观望',
            'description': '市场极度恐慌，建议空仓等待'
        },
        '恐慌': {
            'strategy': '试探',
            'position': 0.2,
            'risk_level': '低',
            'action': '小仓位试探',
            'description': '市场恐慌，可小仓位试探优质标的'
        },
        '谨慎': {
            'strategy': '观望',
            'position': 0.3,
            'risk_level': '中等偏低',
            'action': '谨慎参与',
            'description': '市场谨慎，控制仓位参与'
        },
        '中性': {
            'strategy': '正常',
            'position': 0.5,
            'risk_level': '中等',
            'action': '正常操作',
            'description': '市场中性，正常仓位操作'
        },
        '乐观': {
            'strategy': '积极',
            'position': 0.7,
            'risk_level': '中等偏高',
            'action': '积极布局',
            'description': '市场乐观，可积极布局'
        },
        '贪婪': {
            'strategy': '激进',
            'position': 0.8,
            'risk_level': '高',
            'action': '激进操作',
            'description': '市场贪婪，激进操作但需警惕'
        },
        '极度贪婪': {
            'strategy': '减仓',
            'position': 0.4,
            'risk_level': '极高',
            'action': '反向减仓',
            'description': '市场极度贪婪，建议减仓锁定利润'
        }
    }
    
    def __init__(self):
        """初始化策略映射器"""
        self.mapping = self.MAPPING.copy()
    
    def get_strategy(self, emotion_state: str) -> Dict:
        """
        获取对应策略
        
        Args:
            emotion_state: 情绪状态
            
        Returns:
            策略信息
        """
        return self.mapping.get(emotion_state, self.mapping['中性'])
    
    def get_position_suggestion(self, emotion_state: str, current_position: float) -> Dict:
        """
        获取仓位建议
        
        Args:
            emotion_state: 情绪状态
            current_position: 当前仓位
            
        Returns:
            仓位调整建议
        """
        strategy = self.get_strategy(emotion_state)
        target_position = strategy['position']
        
        if current_position < target_position:
            action = '加仓'
            delta = target_position - current_position
        elif current_position > target_position:
            action = '减仓'
            delta = current_position - target_position
        else:
            action = '保持'
            delta = 0
        
        return {
            'current_position': current_position,
            'target_position': target_position,
            'action': action,
            'delta': delta,
            'strategy': strategy['strategy'],
            'risk_level': strategy['risk_level']
        }


class RealtimeSentimentProcessor:
    """实时情绪处理器"""
    
    def __init__(self, db_path: str = 'data/sentiment_cache.db'):
        """
        初始化实时情绪处理器
        
        Args:
            db_path: 数据库路径
        """
        self.emotion_state = EmotionState()
        self.strategy_mapper = EmotionStrategyMapper()
        self.db_path = db_path
        self._init_db()
        
        # 情绪计算权重
        self.weights = {
            'news_sentiment': 0.35,
            'social_sentiment': 0.25,
            'price_sentiment': 0.25,
            'fund_flow_sentiment': 0.15
        }
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sentiment_score REAL,
                emotion_state TEXT,
                strategy TEXT,
                position REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_sentiment(self, 
                           news_score: float = 0,
                           social_score: float = 0,
                           price_score: float = 0,
                           fund_flow_score: float = 0) -> float:
        """
        计算综合情绪得分
        
        Args:
            news_score: 新闻情绪得分 (-1 到 1)
            social_score: 社交媒体情绪得分 (-1 到 1)
            price_score: 价格情绪得分 (-1 到 1)
            fund_flow_score: 资金流向情绪得分 (-1 到 1)
            
        Returns:
            综合情绪得分 (-1 到 1)
        """
        # 加权平均
        weighted_score = (
            news_score * self.weights['news_sentiment'] +
            social_score * self.weights['social_sentiment'] +
            price_score * self.weights['price_sentiment'] +
            fund_flow_score * self.weights['fund_flow_sentiment']
        )
        
        # 确保在 -1 到 1 范围内
        weighted_score = max(-1.0, min(1.0, weighted_score))
        
        return weighted_score
    
    def process_sentiment(self,
                          news_score: float = 0,
                          social_score: float = 0,
                          price_score: float = 0,
                          fund_flow_score: float = 0,
                          current_position: float = 0.5) -> Dict:
        """
        处理情绪更新
        
        Args:
            news_score: 新闻情绪得分
            social_score: 社交媒体情绪得分
            price_score: 价格情绪得分
            fund_flow_score: 资金流向情绪得分
            current_position: 当前仓位
            
        Returns:
            处理结果
        """
        # 计算综合情绪得分
        sentiment_score = self.calculate_sentiment(
            news_score, social_score, price_score, fund_flow_score
        )
        
        # 更新情绪状态
        state_update = self.emotion_state.update(sentiment_score)
        
        # 获取策略
        strategy = self.strategy_mapper.get_strategy(self.emotion_state.current_state)
        
        # 获取仓位建议
        position_suggestion = self.strategy_mapper.get_position_suggestion(
            self.emotion_state.current_state,
            current_position
        )
        
        # 检测异常
        anomaly = self.emotion_state.detect_anomaly()
        
        # 保存到数据库
        self._save_to_db(sentiment_score, strategy, position_suggestion)
        
        return {
            'sentiment_score': sentiment_score,
            'emotion_state': self.emotion_state.current_state,
            'state_info': self.emotion_state.get_state_info(),
            'strategy': strategy,
            'position_suggestion': position_suggestion,
            'state_update': state_update,
            'anomaly': anomaly,
            'timestamp': datetime.now()
        }
    
    def _save_to_db(self, sentiment_score: float, strategy: Dict, position_suggestion: Dict):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sentiment_history 
            (sentiment_score, emotion_state, strategy, position)
            VALUES (?, ?, ?, ?)
        ''', (
            sentiment_score,
            self.emotion_state.current_state,
            strategy['strategy'],
            position_suggestion['target_position']
        ))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """
        获取历史记录
        
        Args:
            limit: 返回记录数量
            
        Returns:
            历史记录列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, sentiment_score, emotion_state, strategy, position
            FROM sentiment_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'sentiment_score': row[1],
                'emotion_state': row[2],
                'strategy': row[3],
                'position': row[4]
            }
            for row in rows
        ]
    
    def set_weights(self, weights: Dict[str, float]):
        """
        设置情绪计算权重
        
        Args:
            weights: 权重字典
        """
        # 验证权重总和为1
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'权重总和必须为1，当前为{total}')
        
        self.weights.update(weights)


# 使用示例
if __name__ == '__main__':
    # 创建处理器
    processor = RealtimeSentimentProcessor()
    
    # 模拟情绪更新
    result = processor.process_sentiment(
        news_score=0.5,
        social_score=0.3,
        price_score=0.4,
        fund_flow_score=0.6,
        current_position=0.5
    )
    
    print("情绪处理结果:")
    print(f"情绪得分: {result['sentiment_score']:.2f}")
    print(f"情绪状态: {result['emotion_state']}")
    print(f"策略: {result['strategy']['strategy']}")
    print(f"目标仓位: {result['position_suggestion']['target_position']:.0%}")
    print(f"操作建议: {result['position_suggestion']['action']}")
    
    if result['anomaly']:
        print(f"⚠️ 异常检测: {result['anomaly']['message']}")