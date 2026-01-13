"""
龙头识别与跟踪系统
实现龙头特征提取、评分模型和生命周期管理
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3
from collections import deque
import json


class DragonFeatureExtractor:
    """龙头特征提取器"""
    
    def __init__(self):
        """初始化特征提取器"""
        self.features = [
            '连续涨停天数',
            '换手率',
            '成交金额',
            '板块涨幅',
            '市场地位',
            '资金流入',
            '新闻热度',
            '社交讨论度'
        ]
    
    def extract(self, stock_data: pd.DataFrame, stock_info: Dict, 
                sector_data: Dict, news_data: List[Dict]) -> Dict:
        """
        提取龙头特征
        
        Args:
            stock_data: 股票历史数据
            stock_info: 股票基本信息
            sector_data: 板块数据
            news_data: 新闻数据
            
        Returns:
            特征字典
        """
        latest = stock_data.iloc[-1] if len(stock_data) > 0 else None
        
        if latest is None:
            return {}
        
        # 1. 连续涨停天数
        limit_up_days = self._count_limit_ups(stock_data)
        
        # 2. 换手率
        turnover_rate = self._calc_turnover(stock_data)
        
        # 3. 成交金额
        volume_amount = self._calc_volume_amount(stock_data)
        
        # 4. 板块涨幅
        sector_change = sector_data.get('change_pct', 0)
        
        # 5. 市场地位
        market_rank = self._get_market_rank(stock_info)
        
        # 6. 资金流入
        fund_inflow = self._calc_fund_inflow(stock_data)
        
        # 7. 新闻热度
        news_heat = self._calc_news_heat(news_data)
        
        # 8. 社交讨论度
        social_discussion = self._get_social_discussion(stock_info)
        
        return {
            '连续涨停天数': limit_up_days,
            '换手率': turnover_rate,
            '成交金额': volume_amount,
            '板块涨幅': sector_change,
            '市场地位': market_rank,
            '资金流入': fund_inflow,
            '新闻热度': news_heat,
            '社交讨论度': social_discussion,
            '最新价格': latest['close'],
            '最新涨幅': latest.get('pct_chg', 0),
            '最新成交量': latest['volume']
        }
    
    def _count_limit_ups(self, df: pd.DataFrame) -> int:
        """计算连续涨停天数"""
        if 'pct_chg' not in df.columns:
            return 0
        
        limit_up_threshold = 9.9  # 涨停阈值
        count = 0
        
        for i in range(len(df)-1, -1, -1):
            if df.iloc[i]['pct_chg'] >= limit_up_threshold:
                count += 1
            else:
                break
        
        return count
    
    def _calc_turnover(self, df: pd.DataFrame) -> float:
        """计算换手率"""
        if len(df) < 5:
            return 0
        
        recent = df.tail(5)
        avg_turnover = recent['volume'].mean()
        
        # 归一化到 0-1
        return min(1.0, avg_turnover / 100000000)  # 假设1亿为基准
    
    def _calc_volume_amount(self, df: pd.DataFrame) -> float:
        """计算成交金额"""
        if len(df) < 1:
            return 0
        
        latest = df.iloc[-1]
        volume = latest['volume']
        price = latest['close']
        
        amount = volume * price
        
        # 归一化到 0-1
        return min(1.0, amount / 1000000000)  # 假设10亿为基准
    
    def _get_market_rank(self, stock_info: Dict) -> float:
        """获取市场地位"""
        # 这里可以根据市值、行业地位等计算
        market_cap = stock_info.get('market_cap', 0)
        
        # 归一化到 0-1
        return min(1.0, market_cap / 100000000000)  # 假设100亿为基准
    
    def _calc_fund_inflow(self, df: pd.DataFrame) -> float:
        """计算资金流入"""
        if len(df) < 5:
            return 0
        
        recent = df.tail(5)
        
        # 简单计算：最近5天上涨天数占比
        up_days = sum(1 for i in range(len(recent)) if recent.iloc[i]['close'] > recent.iloc[i]['open'])
        return up_days / len(recent)
    
    def _calc_news_heat(self, news_data: List[Dict]) -> float:
        """计算新闻热度"""
        if not news_data:
            return 0
        
        # 最近24小时新闻数量
        now = datetime.now()
        recent_news = [
            n for n in news_data
            if (now - n.get('publish_time', now)).total_seconds() < 86400
        ]
        
        # 归一化到 0-1
        return min(1.0, len(recent_news) / 10)  # 假设10条为基准
    
    def _get_social_discussion(self, stock_info: Dict) -> float:
        """获取社交讨论度"""
        # 这里可以从社交媒体API获取
        # 暂时返回模拟值
        return stock_info.get('social_heat', 0.5)


class DragonScoringModel:
    """龙头评分模型"""
    
    def __init__(self):
        """初始化评分模型"""
        # 特征权重（可根据市场环境调整）
        self.base_weights = {
            '连续涨停天数': 0.25,
            '换手率': 0.15,
            '成交金额': 0.10,
            '板块涨幅': 0.15,
            '市场地位': 0.10,
            '资金流入': 0.10,
            '新闻热度': 0.08,
            '社交讨论度': 0.07
        }
        
        self.weights = self.base_weights.copy()
        self.market_environment = 'neutral'
    
    def score(self, features: Dict) -> Dict:
        """
        计算龙头评分
        
        Args:
            features: 特征字典
            
        Returns:
            评分结果
        """
        if not features:
            return {
                'score': 0,
                'confidence': 0,
                'potential': 'low'
            }
        
        # 计算加权得分
        weighted_score = 0
        total_weight = 0
        
        for feature_name, weight in self.weights.items():
            if feature_name in features:
                feature_value = features[feature_name]
                weighted_score += feature_value * weight
                total_weight += weight
        
        # 归一化
        if total_weight > 0:
            score = weighted_score / total_weight
        else:
            score = 0
        
        # 根据市场环境调整
        score = self._adjust_by_market_environment(score, features)
        
        # 计算置信度
        confidence = self._calculate_confidence(features)
        
        # 预测潜力
        potential = self._predict_potential(score, confidence)
        
        return {
            'score': score,
            'confidence': confidence,
            'potential': potential,
            'features': features
        }
    
    def _adjust_by_market_environment(self, score: float, features: Dict) -> float:
        """根据市场环境调整评分"""
        if self.market_environment == 'bull':
            # 牛市：涨停天数权重提高
            if features.get('连续涨停天数', 0) >= 2:
                score *= 1.2
        elif self.market_environment == 'bear':
            # 熊市：换手率权重提高，涨停天数权重降低
            if features.get('换手率', 0) > 0.5:
                score *= 1.1
            if features.get('连续涨停天数', 0) >= 3:
                score *= 0.9
        
        return min(1.0, max(0, score))
    
    def _calculate_confidence(self, features: Dict) -> float:
        """计算置信度"""
        # 基于特征完整性计算
        feature_count = len([v for v in features.values() if v > 0])
        total_features = len(features)
        
        if total_features == 0:
            return 0
        
        base_confidence = feature_count / total_features
        
        # 如果有连续涨停，提高置信度
        if features.get('连续涨停天数', 0) >= 2:
            base_confidence *= 1.2
        
        # 如果成交金额大，提高置信度
        if features.get('成交金额', 0) > 0.5:
            base_confidence *= 1.1
        
        return min(1.0, base_confidence)
    
    def _predict_potential(self, score: float, confidence: float) -> str:
        """预测潜力"""
        combined_score = score * confidence
        
        if combined_score >= 0.8:
            return 'very_high'
        elif combined_score >= 0.6:
            return 'high'
        elif combined_score >= 0.4:
            return 'medium'
        elif combined_score >= 0.2:
            return 'low'
        else:
            return 'very_low'
    
    def set_market_environment(self, environment: str):
        """
        设置市场环境
        
        Args:
            environment: 市场环境 ('bull', 'bear', 'neutral')
        """
        self.market_environment = environment
    
    def adjust_weights(self, weights: Dict[str, float]):
        """
        调整特征权重
        
        Args:
            weights: 新权重字典
        """
        # 验证权重总和
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'权重总和必须为1，当前为{total}')
        
        self.weights.update(weights)


class DragonLifecycleManager:
    """龙头生命周期管理器"""
    
    STAGES = ['启动', '加速', '分歧', '衰竭', '退潮']
    
    def __init__(self, db_path: str = 'data/dragon_cache.db'):
        """
        初始化生命周期管理器
        
        Args:
            db_path: 数据库路径
        """
        self.dragons = {}  # {stock_code: DragonState}
        self.db_path = db_path
        self._init_db()
        self._load_dragons_from_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dragon_states (
                stock_code TEXT PRIMARY KEY,
                current_stage TEXT,
                stage_start_time DATETIME,
                limit_up_days INTEGER,
                total_days INTEGER,
                peak_price REAL,
                current_price REAL,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_dragons_from_db(self):
        """从数据库加载龙头状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM dragon_states')
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            stock_code = row[0]
            self.dragons[stock_code] = {
                'current_stage': row[1],
                'stage_start_time': row[2],
                'limit_up_days': row[3],
                'total_days': row[4],
                'peak_price': row[5],
                'current_price': row[6],
                'update_time': row[7]
            }
    
    def track_dragon(self, stock_code: str, stock_data: pd.DataFrame) -> Dict:
        """
        跟踪龙头生命周期
        
        Args:
            stock_code: 股票代码
            stock_data: 股票数据
            
        Returns:
            跟踪结果
        """
        latest = stock_data.iloc[-1] if len(stock_data) > 0 else None
        if latest is None:
            return {}
        
        # 提取特征
        limit_up_days = self._count_limit_ups(stock_data)
        current_price = latest['close']
        
        # 如果是新龙头，初始化
        if stock_code not in self.dragons:
            self.dragons[stock_code] = {
                'current_stage': '启动',
                'stage_start_time': datetime.now(),
                'limit_up_days': limit_up_days,
                'total_days': 0,
                'peak_price': current_price,
                'current_price': current_price,
                'update_time': datetime.now()
            }
        else:
            # 更新现有龙头
            dragon = self.dragons[stock_code]
            dragon['limit_up_days'] = limit_up_days
            dragon['current_price'] = current_price
            dragon['total_days'] += 1
            dragon['update_time'] = datetime.now()
            
            # 更新最高价
            if current_price > dragon['peak_price']:
                dragon['peak_price'] = current_price
        
        # 预测阶段
        stage = self._predict_stage(stock_code, stock_data)
        old_stage = self.dragons[stock_code]['current_stage']
        
        # 如果阶段变化，更新
        if stage != old_stage:
            self.dragons[stock_code]['current_stage'] = stage
            self.dragons[stock_code]['stage_start_time'] = datetime.now()
        
        # 预测下一阶段
        next_stage = self._predict_next_stage(stage)
        
        # 预测阶段持续时间
        stage_duration = self._predict_duration(stage)
        
        # 获取阶段操作建议
        action = self._get_stage_action(stage)
        
        # 保存到数据库
        self._save_to_db(stock_code)
        
        return {
            'stock_code': stock_code,
            'current_stage': stage,
            'next_stage': next_stage,
            'stage_duration': stage_duration,
            'action': action,
            'limit_up_days': limit_up_days,
            'peak_price': self.dragons[stock_code]['peak_price'],
            'current_price': current_price,
            'total_days': self.dragons[stock_code]['total_days'],
            'stage_changed': stage != old_stage
        }
    
    def _count_limit_ups(self, df: pd.DataFrame) -> int:
        """计算连续涨停天数"""
        if 'pct_chg' not in df.columns:
            return 0
        
        count = 0
        for i in range(len(df)-1, -1, -1):
            if df.iloc[i]['pct_chg'] >= 9.9:
                count += 1
            else:
                break
        
        return count
    
    def _predict_stage(self, stock_code: str, stock_data: pd.DataFrame) -> str:
        """预测当前阶段"""
        dragon = self.dragons[stock_code]
        limit_up_days = dragon['limit_up_days']
        total_days = dragon['total_days']
        
        latest = stock_data.iloc[-1]
        current_price = latest['close']
        peak_price = dragon['peak_price']
        
        # 阶段判断逻辑
        if limit_up_days == 1 and total_days <= 2:
            return '启动'
        elif limit_up_days >= 2 and total_days <= 5:
            return '加速'
        elif limit_up_days >= 1 and total_days <= 8:
            # 检查是否出现分歧
            if latest['pct_chg'] < 5 and latest['volume'] > stock_data['volume'].mean():
                return '分歧'
            else:
                return '加速'
        elif total_days > 8:
            # 检查是否衰竭
            if current_price < peak_price * 0.95:
                return '衰竭'
            else:
                return '分歧'
        else:
            return '退潮'
    
    def _predict_next_stage(self, current_stage: str) -> str:
        """预测下一阶段"""
        stage_order = self.STAGES
        current_index = stage_order.index(current_stage)
        
        if current_index < len(stage_order) - 1:
            return stage_order[current_index + 1]
        else:
            return current_stage
    
    def _predict_duration(self, stage: str) -> int:
        """预测阶段持续时间（天）"""
        duration_map = {
            '启动': 2,
            '加速': 4,
            '分歧': 3,
            '衰竭': 2,
            '退潮': 5
        }
        return duration_map.get(stage, 3)
    
    def _get_stage_action(self, stage: str) -> str:
        """获取阶段操作建议"""
        action_map = {
            '启动': '关注，等待确认',
            '加速': '积极参与，控制仓位',
            '分歧': '谨慎，考虑减仓',
            '衰竭': '清仓，锁定利润',
            '退潮': '观望，寻找新机会'
        }
        return action_map.get(stage, '观望')
    
    def _save_to_db(self, stock_code: str):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        dragon = self.dragons[stock_code]
        
        cursor.execute('''
            INSERT OR REPLACE INTO dragon_states
            (stock_code, current_stage, stage_start_time, limit_up_days,
             total_days, peak_price, current_price, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stock_code,
            dragon['current_stage'],
            dragon['stage_start_time'],
            dragon['limit_up_days'],
            dragon['total_days'],
            dragon['peak_price'],
            dragon['current_price'],
            dragon['update_time']
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_dragons(self) -> List[Dict]:
        """获取所有龙头"""
        return [
            {
                'stock_code': code,
                **state
            }
            for code, state in self.dragons.items()
        ]
    
    def get_dragon(self, stock_code: str) -> Optional[Dict]:
        """获取指定龙头"""
        return self.dragons.get(stock_code)


class DragonTrackingSystem:
    """龙头跟踪系统（整合类）"""
    
    def __init__(self):
        """初始化系统"""
        self.feature_extractor = DragonFeatureExtractor()
        self.scoring_model = DragonScoringModel()
        self.lifecycle_manager = DragonLifecycleManager()
    
    def analyze_stock(self, 
                     stock_code: str,
                     stock_data: pd.DataFrame,
                     stock_info: Dict,
                     sector_data: Dict,
                     news_data: List[Dict]) -> Dict:
        """
        分析股票是否为龙头
        
        Args:
            stock_code: 股票代码
            stock_data: 股票数据
            stock_info: 股票信息
            sector_data: 板块数据
            news_data: 新闻数据
            
        Returns:
            分析结果
        """
        # 提取特征
        features = self.feature_extractor.extract(
            stock_data, stock_info, sector_data, news_data
        )
        
        # 计算评分
        score_result = self.scoring_model.score(features)
        
        # 跟踪生命周期
        lifecycle_result = self.lifecycle_manager.track_dragon(
            stock_code, stock_data
        )
        
        # 综合判断
        is_dragon = score_result['score'] >= 0.6 and score_result['confidence'] >= 0.5
        
        return {
            'stock_code': stock_code,
            'is_dragon': is_dragon,
            'score': score_result['score'],
            'confidence': score_result['confidence'],
            'potential': score_result['potential'],
            'features': features,
            'lifecycle': lifecycle_result,
            'timestamp': datetime.now()
        }
    
    def batch_analyze(self, stocks: List[Dict]) -> List[Dict]:
        """
        批量分析股票
        
        Args:
            stocks: 股票列表，每个元素包含 stock_code, stock_data, stock_info, sector_data, news_data
            
        Returns:
            分析结果列表
        """
        results = []
        
        for stock in stocks:
            result = self.analyze_stock(
                stock['stock_code'],
                stock['stock_data'],
                stock['stock_info'],
                stock['sector_data'],
                stock['news_data']
            )
            results.append(result)
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def set_market_environment(self, environment: str):
        """
        设置市场环境
        
        Args:
            environment: 市场环境
        """
        self.scoring_model.set_market_environment(environment)
    
    def get_top_dragons(self, limit: int = 10) -> List[Dict]:
        """
       获取顶级龙头
        
        Args:
            limit: 返回数量
            
        Returns:
            龙头列表
        """
        dragons = self.lifecycle_manager.get_all_dragons()
        
        # 按涨停天数排序
        dragons.sort(key=lambda x: x['limit_up_days'], reverse=True)
        
        return dragons[:limit]


# 使用示例
if __name__ == '__main__':
    # 创建系统
    system = DragonTrackingSystem()
    
    # 模拟股票数据
    dates = pd.date_range(start='2024-01-01', periods=10)
    stock_data = pd.DataFrame({
        'date': dates,
        'open': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
        'close': [10.5, 11.0, 11.5, 12.0, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5],
        'high': [10.6, 11.1, 11.6, 12.1, 12.6, 13.6, 14.6, 15.6, 16.6, 17.6],
        'low': [10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
        'volume': [1000000, 1200000, 1500000, 1800000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000],
        'pct_chg': [5.0, 4.8, 4.5, 4.3, 4.2, 8.3, 7.4, 6.9, 6.5, 6.1]
    })
    
    # 模拟其他数据
    stock_info = {
        'market_cap': 50000000000,
        'social_heat': 0.8
    }
    
    sector_data = {
        'change_pct': 5.0
    }
    
    news_data = [
        {'publish_time': datetime.now() - timedelta(hours=2), 'title': '公司发布重大利好'},
        {'publish_time': datetime.now() - timedelta(hours=5), 'title': '行业前景看好'}
    ]
    
    # 分析股票
    result = system.analyze_stock(
        stock_code='600000',
        stock_data=stock_data,
        stock_info=stock_info,
        sector_data=sector_data,
        news_data=news_data
    )
    
    print("龙头分析结果:")
    print(f"股票代码: {result['stock_code']}")
    print(f"是否为龙头: {'是' if result['is_dragon'] else '否'}")
    print(f"评分: {result['score']:.2f}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"潜力: {result['potential']}")
    print(f"生命周期: {result['lifecycle']['current_stage']}")
    print(f"操作建议: {result['lifecycle']['action']}")