"""
集合竞价预测系统
实现集合竞价特征提取、开盘走势预测和弱转强识别
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3
from collections import deque


class AuctionFeatureExtractor:
    """集合竞价特征提取器"""
    
    def __init__(self):
        """初始化特征提取器"""
        self.features = [
            '匹配价格',
            '匹配成交量',
            '买卖盘不平衡度',
            '价格波动率',
            '成交量激增',
            '订单簿深度'
        ]
    
    def extract(self, auction_data: Dict, prev_data: Optional[Dict] = None) -> Dict:
        """
        提取集合竞价特征
        
        Args:
            auction_data: 竞价数据
            prev_data: 前一日数据
            
        Returns:
            特征字典
        """
        # 1. 匹配价格
        match_price = auction_data.get('price', 0)
        
        # 2. 匹配成交量
        match_volume = auction_data.get('volume', 0)
        
        # 3. 买卖盘不平衡度
        order_imbalance = self._calc_imbalance(auction_data)
        
        # 4. 价格波动率
        price_volatility = self._calc_volatility(auction_data)
        
        # 5. 成交量激增
        volume_surge = self._calc_volume_surge(match_volume, prev_data)
        
        # 6. 订单簿深度
        order_book_depth = self._calc_depth(auction_data)
        
        return {
            '匹配价格': match_price,
            '匹配成交量': match_volume,
            '买卖盘不平衡度': order_imbalance,
            '价格波动率': price_volatility,
            '成交量激增': volume_surge,
            '订单簿深度': order_book_depth
        }
    
    def _calc_imbalance(self, auction_data: Dict) -> float:
        """计算买卖盘不平衡度"""
        buy_volume = auction_data.get('buy_volume', 0)
        sell_volume = auction_data.get('sell_volume', 0)
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0
        
        # 不平衡度：-1（卖方主导）到 1（买方主导）
        imbalance = (buy_volume - sell_volume) / total_volume
        return imbalance
    
    def _calc_volatility(self, auction_data: Dict) -> float:
        """计算价格波动率"""
        high = auction_data.get('high', 0)
        low = auction_data.get('low', 0)
        price = auction_data.get('price', 0)
        
        if price == 0:
            return 0
        
        # 波动率
        volatility = (high - low) / price
        return volatility
    
    def _calc_volume_surge(self, current_volume: float, prev_data: Optional[Dict]) -> float:
        """计算成交量激增"""
        if prev_data is None:
            return 0
        
        prev_volume = prev_data.get('volume', 0)
        if prev_volume == 0:
            return 0
        
        surge = current_volume / prev_volume
        return min(5.0, surge)  # 限制最大为5倍
    
    def _calc_depth(self, auction_data: Dict) -> float:
        """计算订单簿深度"""
        buy_orders = auction_data.get('buy_orders', [])
        sell_orders = auction_data.get('sell_orders', [])
        
        total_buy = sum(order.get('volume', 0) for order in buy_orders)
        total_sell = sum(order.get('volume', 0) for order in sell_orders)
        
        total_depth = total_buy + total_sell
        
        # 归一化到 0-1
        return min(1.0, total_depth / 10000000)  # 假设1000万为基准


class OpeningPredictor:
    """开盘走势预测器"""
    
    def __init__(self):
        """初始化预测器"""
        self.feature_extractor = AuctionFeatureExtractor()
        self.model = self._load_model()
    
    def _load_model(self):
        """加载模型（简化版）"""
        # 这里可以加载预训练的机器学习模型
        # 暂时使用规则模型
        return None
    
    def predict_opening(self, 
                       auction_data: Dict,
                       prev_data: Optional[Dict] = None,
                       market_data: Optional[Dict] = None) -> Dict:
        """
        预测开盘走势
        
        Args:
            auction_data: 竞价数据
            prev_data: 前一日数据
            market_data: 市场数据
            
        Returns:
            预测结果
        """
        # 提取特征
        features = self.feature_extractor.extract(auction_data, prev_data)
        
        # 预测开盘价
        opening_price = self._predict_price(features, prev_data)
        
        # 预测开盘成交量
        opening_volume = self._predict_volume(features, prev_data)
        
        # 预测弱转强
        weak_to_strong = self._predict_weak_to_strong(features, prev_data)
        
        # 计算强度
        strength = self._calculate_strength(features)
        
        # 计算置信度
        confidence = self._calculate_confidence(features)
        
        return {
            'opening_price': opening_price,
            'opening_volume': opening_volume,
            'weak_to_strong': weak_to_strong,
            'strength': strength,
            'confidence': confidence,
            'features': features
        }
    
    def _predict_price(self, features: Dict, prev_data: Optional[Dict]) -> Dict:
        """预测开盘价"""
        match_price = features['匹配价格']
        
        if prev_data is None:
            return {
                'price': match_price,
                'change_pct': 0,
                'prediction': '平开'
            }
        
        prev_close = prev_data.get('close', match_price)
        change_pct = (match_price - prev_close) / prev_close * 100
        
        # 预测开盘价走势
        if change_pct > 5:
            prediction = '高开'
        elif change_pct > 2:
            prediction = '小幅高开'
        elif change_pct > -2:
            prediction = '平开'
        elif change_pct > -5:
            prediction = '小幅低开'
        else:
            prediction = '低开'
        
        return {
            'price': match_price,
            'change_pct': change_pct,
            'prediction': prediction
        }
    
    def _predict_volume(self, features: Dict, prev_data: Optional[Dict]) -> Dict:
        """预测开盘成交量"""
        match_volume = features['匹配成交量']
        volume_surge = features['成交量激增']
        
        if prev_data is None:
            return {
                'volume': match_volume,
                'surge': 1.0,
                'prediction': '正常'
            }
        
        prev_volume = prev_data.get('volume', match_volume)
        surge = match_volume / prev_volume if prev_volume > 0 else 1.0
        
        # 预测成交量走势
        if surge > 2.0:
            prediction = '放量'
        elif surge > 1.5:
            prediction = '小幅放量'
        elif surge > 0.8:
            prediction = '正常'
        else:
            prediction = '缩量'
        
        return {
            'volume': match_volume,
            'surge': surge,
            'prediction': prediction
        }
    
    def _predict_weak_to_strong(self, features: Dict, prev_data: Optional[Dict]) -> Dict:
        """预测弱转强"""
        if prev_data is None:
            return {
                'is_wts': False,
                'strength': 0,
                'reason': '缺少前一日数据'
            }
        
        # 弱转强特征
        price_gap = features['匹配价格'] - prev_data.get('close', features['匹配价格'])
        volume_ratio = features['成交量激增']
        order_imbalance = features['买卖盘不平衡度']
        
        # 判断弱转强
        is_wts = False
        strength = 0
        reasons = []
        
        # 价格跳空
        if price_gap > 0:
            is_wts = True
            strength += 0.3
            reasons.append('价格跳空')
        
        # 成交量放大
        if volume_ratio > 1.5:
            is_wts = True
            strength += 0.3
            reasons.append('成交量放大')
        
        # 买盘主导
        if order_imbalance > 0.3:
            is_wts = True
            strength += 0.4
            reasons.append('买盘主导')
        
        return {
            'is_wts': is_wts,
            'strength': min(1.0, strength),
            'reason': ', '.join(reasons) if reasons else '无明显弱转强信号'
        }
    
    def _calculate_strength(self, features: Dict) -> float:
        """计算开盘强度"""
        # 综合多个特征计算强度
        imbalance = features['买卖盘不平衡度']
        volume_surge = features['成交量激增']
        depth = features['订单簿深度']
        
        # 归一化到 0-1
        strength = (imbalance + 1) / 2 * 0.4 + \
                   min(1.0, volume_surge / 2) * 0.3 + \
                   depth * 0.3
        
        return min(1.0, max(0, strength))
    
    def _calculate_confidence(self, features: Dict) -> float:
        """计算预测置信度"""
        # 基于特征完整性计算
        valid_features = sum(1 for v in features.values() if v > 0)
        total_features = len(features)
        
        base_confidence = valid_features / total_features
        
        # 如果成交量激增，提高置信度
        if features['成交量激增'] > 1.5:
            base_confidence *= 1.2
        
        # 如果买卖盘不平衡度高，提高置信度
        if abs(features['买卖盘不平衡度']) > 0.5:
            base_confidence *= 1.1
        
        return min(1.0, base_confidence)


class WeakToStrongDetector:
    """弱转强识别器"""
    
    def __init__(self):
        """初始化识别器"""
        self.model = self._load_model()
    
    def _load_model(self):
        """加载模型（简化版）"""
        return None
    
    def detect(self, 
               auction_data: Dict,
               prev_data: Optional[Dict] = None,
               market_sentiment: float = 0) -> Dict:
        """
        检测弱转强
        
        Args:
            auction_data: 竞价数据
            prev_data: 前一日数据
            market_sentiment: 市场情绪 (-1 到 1)
            
        Returns:
            检测结果
        """
        if prev_data is None:
            return {
                'is_wts': False,
                'strength': 0,
                'reason': '缺少前一日数据'
            }
        
        # 提取特征
        features = self._extract_features(auction_data, prev_data, market_sentiment)
        
        # 预测
        prediction = self._predict(features)
        
        return {
            'is_wts': prediction['is_wts'],
            'strength': prediction['strength'],
            'reason': prediction['reason'],
            'features': features
        }
    
    def _extract_features(self, 
                         auction_data: Dict,
                         prev_data: Dict,
                         market_sentiment: float) -> Dict:
        """提取特征"""
        price_gap = auction_data.get('price', 0) - prev_data.get('close', 0)
        volume_ratio = auction_data.get('volume', 0) / prev_data.get('volume', 1)
        order_imbalance = self._calc_imbalance(auction_data)
        
        return {
            'price_gap': price_gap,
            'volume_ratio': volume_ratio,
            'order_imbalance': order_imbalance,
            'market_sentiment': market_sentiment
        }
    
    def _calc_imbalance(self, auction_data: Dict) -> float:
        """计算买卖盘不平衡度"""
        buy_volume = auction_data.get('buy_volume', 0)
        sell_volume = auction_data.get('sell_volume', 0)
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0
        
        return (buy_volume - sell_volume) / total_volume
    
    def _predict(self, features: Dict) -> Dict:
        """预测弱转强"""
        is_wts = False
        strength = 0
        reasons = []
        
        # 价格跳空
        if features['price_gap'] > 0:
            is_wts = True
            strength += 0.3
            reasons.append('价格跳空')
        
        # 成交量放大
        if features['volume_ratio'] > 1.5:
            is_wts = True
            strength += 0.3
            reasons.append('成交量放大')
        
        # 买盘主导
        if features['order_imbalance'] > 0.3:
            is_wts = True
            strength += 0.3
            reasons.append('买盘主导')
        
        # 市场情绪好
        if features['market_sentiment'] > 0.3:
            is_wts = True
            strength += 0.1
            reasons.append('市场情绪好')
        
        return {
            'is_wts': is_wts,
            'strength': min(1.0, strength),
            'reason': ', '.join(reasons) if reasons else '无明显弱转强信号'
        }


class AuctionMonitor:
    """集合竞价实时监控"""

    def __init__(self, db_path: str = 'data/auction/auction_snapshots.db'):
        """
        初始化监控器

        Args:
            db_path: 数据库路径
        """
        self.alerts = deque(maxlen=100)
        self.thresholds = {
            'volume_surge': 2.0,
            'price_gap': 0.05,
            'order_imbalance': 0.5
        }
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT,
                alert_type TEXT,
                alert_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def monitor(self, 
                stock_code: str,
                auction_data: Dict,
                prev_data: Optional[Dict] = None) -> Dict:
        """
        监控集合竞价
        
        Args:
            stock_code: 股票代码
            auction_data: 竞价数据
            prev_data: 前一日数据
            
        Returns:
            监控结果
        """
        # 检测异常
        anomalies = self._detect_anomalies(auction_data, prev_data)
        
        # 预测开盘
        opening_prediction = self._predict_opening(auction_data, prev_data)
        
        # 触发预警
        alerts = self._trigger_alerts(stock_code, anomalies, opening_prediction)
        
        return {
            'stock_code': stock_code,
            'anomalies': anomalies,
            'opening_prediction': opening_prediction,
            'alerts': alerts,
            'timestamp': datetime.now()
        }
    
    def _detect_anomalies(self, 
                         auction_data: Dict,
                         prev_data: Optional[Dict]) -> List[Dict]:
        """检测异常"""
        anomalies = []
        
        if prev_data is None:
            return anomalies
        
        # 成交量异常
        volume_surge = auction_data.get('volume', 0) / prev_data.get('volume', 1)
        if volume_surge > self.thresholds['volume_surge']:
            anomalies.append({
                'type': 'volume_surge',
                'value': volume_surge,
                'threshold': self.thresholds['volume_surge'],
                'message': f'成交量激增 {volume_surge:.2f} 倍'
            })
        
        # 价格异常
        price_gap = (auction_data.get('price', 0) - prev_data.get('close', 0)) / prev_data.get('close', 1)
        if abs(price_gap) > self.thresholds['price_gap']:
            anomalies.append({
                'type': 'price_gap',
                'value': price_gap,
                'threshold': self.thresholds['price_gap'],
                'message': f'价格跳空 {price_gap*100:.2f}%'
            })
        
        # 买卖盘不平衡异常
        buy_volume = auction_data.get('buy_volume', 0)
        sell_volume = auction_data.get('sell_volume', 0)
        total_volume = buy_volume + sell_volume
        if total_volume > 0:
            imbalance = (buy_volume - sell_volume) / total_volume
            if abs(imbalance) > self.thresholds['order_imbalance']:
                anomalies.append({
                    'type': 'order_imbalance',
                    'value': imbalance,
                    'threshold': self.thresholds['order_imbalance'],
                    'message': f'买卖盘不平衡 {imbalance:.2f}'
                })
        
        return anomalies
    
    def _predict_opening(self, 
                        auction_data: Dict,
                        prev_data: Optional[Dict]) -> Dict:
        """预测开盘"""
        predictor = OpeningPredictor()
        return predictor.predict_opening(auction_data, prev_data)
    
    def _trigger_alerts(self, 
                       stock_code: str,
                       anomalies: List[Dict],
                       opening_prediction: Dict) -> List[Dict]:
        """触发预警"""
        alerts = []
        
        # 异常预警
        for anomaly in anomalies:
            alert = {
                'stock_code': stock_code,
                'type': anomaly['type'],
                'message': anomaly['message'],
                'timestamp': datetime.now()
            }
            alerts.append(alert)
            self.alerts.append(alert)
            self._save_alert(stock_code, anomaly['type'], anomaly['message'])
        
        # 弱转强预警
        if opening_prediction['weak_to_strong']['is_wts']:
            alert = {
                'stock_code': stock_code,
                'type': 'weak_to_strong',
                'message': f'弱转强信号: {opening_prediction["weak_to_strong"]["reason"]}',
                'timestamp': datetime.now()
            }
            alerts.append(alert)
            self.alerts.append(alert)
            self._save_alert(stock_code, 'weak_to_strong', alert['message'])
        
        return alerts
    
    def _save_alert(self, stock_code: str, alert_type: str, message: str):
        """保存预警到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auction_alerts (stock_code, alert_type, details)
            VALUES (?, ?, ?)
        ''', (stock_code, alert_type, message))
        
        conn.commit()
        conn.close()
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """获取最近预警"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT stock_code, alert_type, alert_time, details
            FROM auction_alerts
            ORDER BY alert_time DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'stock_code': row[0],
                'alert_type': row[1],
                'alert_time': row[2],
                'details': row[3]
            }
            for row in rows
        ]
    
    def set_threshold(self, key: str, value: float):
        """
        设置阈值
        
        Args:
            key: 阈值键
            value: 阈值
        """
        if key in self.thresholds:
            self.thresholds[key] = value


class AuctionPredictionSystem:
    """集合竞价预测系统（整合类）"""
    
    def __init__(self):
        """初始化系统"""
        self.feature_extractor = AuctionFeatureExtractor()
        self.opening_predictor = OpeningPredictor()
        self.wts_detector = WeakToStrongDetector()
        self.monitor = AuctionMonitor()
    
    def analyze(self, 
                stock_code: str,
                auction_data: Dict,
                prev_data: Optional[Dict] = None,
                market_sentiment: float = 0) -> Dict:
        """
        分析集合竞价
        
        Args:
            stock_code: 股票代码
            auction_data: 竞价数据
            prev_data: 前一日数据
            market_sentiment: 市场情绪
            
        Returns:
            分析结果
        """
        # 提取特征
        features = self.feature_extractor.extract(auction_data, prev_data)
        
        # 预测开盘
        opening_prediction = self.opening_predictor.predict_opening(
            auction_data, prev_data
        )
        
        # 检测弱转强
        wts_result = self.wts_detector.detect(
            auction_data, prev_data, market_sentiment
        )
        
        # 监控异常
        monitor_result = self.monitor.monitor(
            stock_code, auction_data, prev_data
        )
        
        return {
            'stock_code': stock_code,
            'features': features,
            'opening_prediction': opening_prediction,
            'weak_to_strong': wts_result,
            'monitor': monitor_result,
            'timestamp': datetime.now()
        }
    
    def batch_analyze(self, stocks: List[Dict]) -> List[Dict]:
        """
        批量分析
        
        Args:
            stocks: 股票列表
            
        Returns:
            分析结果列表
        """
        results = []
        
        for stock in stocks:
            result = self.analyze(
                stock['stock_code'],
                stock['auction_data'],
                stock.get('prev_data'),
                stock.get('market_sentiment', 0)
            )
            results.append(result)
        
        # 按弱转强强度排序
        results.sort(
            key=lambda x: x['weak_to_strong']['strength'],
            reverse=True
        )
        
        return results
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """获取预警"""
        return self.monitor.get_recent_alerts(limit)


# 使用示例
if __name__ == '__main__':
    # 创建系统
    system = AuctionPredictionSystem()
    
    # 模拟竞价数据
    auction_data = {
        'price': 11.0,
        'volume': 2000000,
        'buy_volume': 1500000,
        'sell_volume': 500000,
        'high': 11.2,
        'low': 10.8,
        'buy_orders': [
            {'price': 10.9, 'volume': 500000},
            {'price': 10.8, 'volume': 1000000}
        ],
        'sell_orders': [
            {'price': 11.1, 'volume': 300000},
            {'price': 11.2, 'volume': 200000}
        ]
    }
    
    # 模拟前一日数据
    prev_data = {
        'open': 10.0,
        'close': 10.5,
        'high': 10.6,
        'low': 9.9,
        'volume': 1000000
    }
    
    # 分析竞价
    result = system.analyze(
        stock_code='600000',
        auction_data=auction_data,
        prev_data=prev_data,
        market_sentiment=0.5
    )
    
    print("集合竞价分析结果:")
    print(f"股票代码: {result['stock_code']}")
    print(f"开盘价预测: {result['opening_prediction']['opening_price']['price']:.2f}")
    print(f"开盘价走势: {result['opening_prediction']['opening_price']['prediction']}")
    print(f"开盘成交量: {result['opening_prediction']['opening_volume']['volume']:,}")
    print(f"成交量走势: {result['opening_prediction']['opening_volume']['prediction']}")
    print(f"弱转强: {'是' if result['weak_to_strong']['is_wts'] else '否'}")
    print(f"弱转强强度: {result['weak_to_strong']['strength']:.2f}")
    print(f"弱转强原因: {result['weak_to_strong']['reason']}")
    print(f"开盘强度: {result['opening_prediction']['strength']:.2f}")
    print(f"预测置信度: {result['opening_prediction']['confidence']:.2f}")
    
    if result['monitor']['alerts']:
        print("\n预警信息:")
        for alert in result['monitor']['alerts']:
            print(f"  - {alert['type']}: {alert['message']}")
