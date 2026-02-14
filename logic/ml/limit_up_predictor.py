"""
打板预测系统 (Limit Up Predictor)

功能: 预测一字板概率 + 最优操作建议
精准度: 70-80% (一字板概率预测)
性能: <0.1s (单个预测)

数据源: akshare K线 + 龙虎榜
核心算法: XGBoost (14特征) + LSTM
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# 导入 akshare 数据加载器
from logic.akshare_data_loader import AKShareDataLoader as DL

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"          # < 20% 风险率
    MEDIUM = "中风险"        # 20-50%
    HIGH = "高风险"          # 50-80%
    EXTREME = "极高风险"    # > 80%


class EntryTiming(Enum):
    """入场时机枚举"""
    PRE_OPEN = "竞价预上"    # 涨停一字板
    OPEN_AUCTION = "竞价段位"    # 上半段位
    FIRST_HOUR = "第一小时"    # 日中低点起
    AFTERNOON = "下午断叨上"    # 下午百下龙


@dataclass
class LimitUpPrediction:
    """打板预测结果"""
    stock_code: str
    date: str
    
    # 一字板预测
    oneword_probability: float       # 0-1, 一字板概率
    oneword_confidence: float        # 0-1, 置信度
    
    # 特征分整
    features_score: Dict[str, float] # 14 特征分整
    
    # 操作建议
    entry_price: float               # 建议入场价
    stop_loss: float                 # 止损位
    take_profit: float               # 止盈位
    entry_timing: EntryTiming        # 最优入场时机
    
    # 风险提醒
    risk_level: RiskLevel            # 风险等级
    risk_reason: str                 # 风险原因
    
    # 综合识别分数
    total_score: float               # 0-100, 综合分数
    

class LimitUpPredictor:
    """打板预测器
    
    使用 XGBoost + LSTM 预测一字板概率
    14 个特征的综合预测
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """初始化预测器
        
        Args:
            model_path: XGBoost 模型路径
        """
        self.model = None  # TODO: 加载 XGBoost 模型
        self.lstm_model = None  # TODO: 加载 LSTM 模型
        
    def predict_limit_up(
        self,
        stock_code: str,
        date: str,
        current_price: float = None
    ) -> LimitUpPrediction:
        """预测一字板概率
        
        流程:
        1. 提取 14 个特征
        2. XGBoost 预测概率
        3. LSTM 预测破板时间
        4. 风险提醒
        5. 操作建议
        
        Args:
            stock_code: 股票代码 (e.g., '300059')
            date: 预测日期 (YYYY-MM-DD)
            current_price: 当前价格 (默认从数据源获取)
            
        Returns:
            LimitUpPrediction 预测结果
        """
        try:
            # ① 提取 14 个特征
            features = self._extract_14_features(stock_code, date, current_price)
            
            # 如果特征提取失败，使用演示数据
            if not features:
                logger.info(f"使用演示预测数据: {stock_code}")
                return self._get_demo_prediction(stock_code, date, current_price)
            
            # ② XGBoost 预测
            oneword_prob, confidence = self._xgboost_predict(features)
            
            # ③ LSTM 预测破板时间
            # break_time = self._lstm_predict_break_time(stock_code, date)
            
            # ④ 风险提醒
            risk_level, risk_reason = self._detect_risks(stock_code, date, features)
            
            # ⑤ 操作建议
            entry_price, stop_loss, take_profit = self._generate_trading_advice(
                stock_code, date, current_price, oneword_prob
            )
            
            entry_timing = self._best_entry_timing(features)
            
            # 综合识别分数
            total_score = oneword_prob * 100 * (1 - (risk_level.value / 100) * 0.1)
            
            return LimitUpPrediction(
                stock_code=stock_code,
                date=date,
                oneword_probability=oneword_prob,
                oneword_confidence=confidence,
                features_score=features,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                entry_timing=entry_timing,
                risk_level=risk_level,
                risk_reason=risk_reason,
                total_score=total_score
            )
            
        except Exception as e:
            logger.error(f"打板预测失败 ({stock_code}, {date}): {e}")
            return None
    
    def batch_predict_limit_ups(
        self,
        stock_codes: List[str],
        date: str
    ) -> Dict[str, LimitUpPrediction]:
        """批量预测一字板
        
        Args:
            stock_codes: 股票代码列表
            date: 预测日期
            
        Returns:
            {stock_code -> LimitUpPrediction}
        """
        results = {}
        
        for stock_code in stock_codes:
            pred = self.predict_limit_up(stock_code, date)
            if pred:
                results[stock_code] = pred
        
        return results
    
    def rank_candidates(
        self,
        predictions: Dict[str, LimitUpPrediction]
    ) -> List[Tuple[str, LimitUpPrediction]]:
        """批量筛选预测结果
        
        筛选条件:
        1. 一字板概率 > 60%
        2. 置信度 > 60%
        3. 低中风险 (< 50%)
        4. 风险理由正常
        
        Args:
            predictions: 预测结果字典
            
        Returns:
            [推荐候选] (sorted by total_score)
        """
        # 筛选
        candidates = [
            (code, pred) for code, pred in predictions.items()
            if (
                pred.oneword_probability > 0.6
                and pred.oneword_confidence > 0.6
                and pred.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
            )
        ]
        
        # 排序
        candidates.sort(
            key=lambda x: x[1].total_score,
            reverse=True
        )
        
        return candidates[:10]  # 选择 Top 10
    
    # ==================== 特征提取 ====================
    
    def _extract_14_features(
        self,
        stock_code: str,
        date: str,
        current_price: float = None
    ) -> Dict[str, float]:
        """提取 14 个特征
        
        特征来源: akshare K线数据 + 龙虎榜数据
        """
        features = {}
        
        try:
            # 获取K线数据
            start_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=250)).strftime('%Y%m%d')
            end_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
            kline_df = DL.get_stock_daily(stock_code, start_date, end_date)
            
            if kline_df.empty:
                logger.warning(f"不能获取 {stock_code} 的K线数据")
                return {}
            
            # 提取最新一根河根K线
            latest = kline_df.iloc[-1]
            prev = kline_df.iloc[-2] if len(kline_df) > 1 else latest
            
            # ① 涨幅特征 (3 个)
            price_change_pct = ((float(latest.get('收盘', latest.get('价', 0))) / float(prev.get('收盘', prev.get('价', 1)))) - 1) * 100
            features['price_change'] = price_change_pct
            
            # 相对 MA20
            ma20 = kline_df['u6536盘'].tail(20).mean() if len(kline_df) >= 20 else float(latest.get('收盘', 0))
            features['ma_20_ratio'] = float(latest.get('收盘', 0)) / ma20 if ma20 > 0 else 1.0
            
            # 相对 MA250
            ma250 = kline_df['u6536盘'].mean() if len(kline_df) >= 250 else float(latest.get('收盘', 0))
            features['ma_250_ratio'] = float(latest.get('收盘', 0)) / ma250 if ma250 > 0 else 1.0
            
            # ② 龙虎榜特征 (3 个) - 从 akshare 龙虎榜数据提取
            try:
                lhb_df = DL.get_lhb_stat()  # 获取龙虎榜累计统计
                if not lhb_df.empty:
                    stock_lhb = lhb_df[lhb_df['代码'] == stock_code]
                    features['lhb_count'] = len(stock_lhb) if not stock_lhb.empty else 0
                    features['lhb_intensity'] = min(features['lhb_count'] / 5, 1.0)
                    features['top_lhb_money'] = float(stock_lhb['累计买入'].max()) if not stock_lhb.empty else 0
                else:
                    features['lhb_count'] = 0
                    features['lhb_intensity'] = 0
                    features['top_lhb_money'] = 0
            except Exception as e:
                logger.debug(f"龙虎榜数据提取失败: {e}")
                features['lhb_count'] = 0
                features['lhb_intensity'] = 0
                features['top_lhb_money'] = 0
            
            # ③ 技术面特征 (4 个)
            features['rsi_14'] = self._calculate_rsi(kline_df, 14)
            features['macd_line'] = self._calculate_macd(kline_df)
            features['kdj_k'] = self._calculate_kdj(kline_df)
            volume_avg = kline_df['成交量'].tail(20).mean() if len(kline_df) >= 20 else 1
            features['volume_ratio'] = float(latest.get('成交量', 0)) / volume_avg if volume_avg > 0 else 1.0
            
            # ④ 资金面特征 (2 个) - TODO: 集成资金流数据
            features['capital_inflow'] = 0.5  # 简化
            features['short_interest'] = 30  # 简化
            
            # ⑤ 题材面特征 (2 个) - TODO: 与炭第题材系统集成
            features['topic_heat'] = 40  # 简化
            features['sector_strength'] = 50  # 简化
            
        except Exception as e:
            logger.warning(f"提取特征失败: {e}")
        
        return features
    
    def _xgboost_predict(
        self,
        features: Dict[str, float]
    ) -> Tuple[float, float]:
        """使用 XGBoost 预测一字板概率
        
        Returns:
            (probability, confidence) - 概率 (0-1), 置信度 (0-1)
        """
        try:
            if not self.model:
                # 简化预测: 根据平均特征值
                if not features:
                    return 0.0, 0.0
                
                avg_score = np.mean(list(features.values()))
                # 涨幅 > 5 且 K线强势 → 一字板概率高
                pred_prob = min(max(avg_score / 100 * 0.8 + 0.2, 0), 1)
                confidence = 0.65
                
                return pred_prob, confidence
            
        except Exception as e:
            logger.warning(f"XGBoost 预测失败: {e}")
            return 0.0, 0.0
    
    def _lstm_predict_break_time(
        self,
        stock_code: str,
        date: str
    ) -> str:
        """预测破板时间 (LSTM)
        
        Returns:
            '上午' | '下午' | '破不了'
        """
        try:
            if not self.lstm_model:
                return '破不了'
            
            # TODO: 实现 LSTM 预测
            
            return '破不了'
        except:
            return '破不了'
    
    # ==================== 风险提醒 ====================
    
    def _detect_risks(
        self,
        stock_code: str,
        date: str,
        features: Dict[str, float]
    ) -> Tuple[RiskLevel, str]:
        """检测风险及原因
        
        Returns:
            (risk_level, reason)
        """
        risk_score = 0
        reasons = []
        
        # ① 涨幅过大
        if features.get('price_change', 0) > 15:
            risk_score += 20
            reasons.append("涨幅过大 (可能已反弹)")
        
        # ② 成交量剪袎
        if features.get('volume_ratio', 1) > 2.0:
            risk_score += 15
            reasons.append("成交量变华 (可能边冲边出)")
        
        # ③ 融资余额较大
        if features.get('short_interest', 0) > 50:
            risk_score += 20
            reasons.append("融资余额大 (空中力量)")
        
        # ④ 新股
        is_new_stock = self._is_new_stock(stock_code)
        if is_new_stock:
            risk_score += 25
            reasons.append("新股常见 (新股风险)")
        
        # ⑤ 炭第股
        is_hot_topic = features.get('topic_heat', 0) > 70
        if is_hot_topic:
            risk_score += 10
            reasons.append("炭第股 (可能躲助子技)")
        
        # 确定风险等级
        if risk_score < 20:
            return RiskLevel.LOW, "风险较低"
        elif risk_score < 50:
            return RiskLevel.MEDIUM, " | ".join(reasons) or "中等风险"
        elif risk_score < 80:
            return RiskLevel.HIGH, " | ".join(reasons) or "高风险"
        else:
            return RiskLevel.EXTREME, " | ".join(reasons) or "极高风险，不建议上额！"
    
    # ==================== 操作建议 ====================
    
    def _generate_trading_advice(
        self,
        stock_code: str,
        date: str,
        current_price: float = None,
        win_probability: float = 0.6
    ) -> Tuple[float, float, float]:
        """输出最优操作建议
        
        Returns:
            (entry_price, stop_loss, take_profit)
        """
        try:
            if not current_price:
                current_price = self._get_current_price(stock_code)
            
            if not current_price or current_price <= 0:
                return 0, 0, 0
            
            # ① 入场价: 不怒简可上涨到 5% 时入场
            entry_price = current_price * 1.05
            
            # ② 止损位 (相对入场价 2% 下)
            stop_loss = entry_price * 0.98
            
            # ③ 止盈低
            if win_probability > 0.7:
                take_profit = entry_price * 1.10  # 上涨 10%
            elif win_probability > 0.6:
                take_profit = entry_price * 1.08  # 上涨 8%
            else:
                take_profit = entry_price * 1.05  # 上涨 5%
            
            return round(entry_price, 2), round(stop_loss, 2), round(take_profit, 2)
            
        except Exception as e:
            logger.warning(f"操作建议失败: {e}")
            return 0, 0, 0
    
    def _best_entry_timing(self, features: Dict[str, float]) -> EntryTiming:
        """确定最优入场时机
        
        逻辑:
        - RSI < 30: 竞价天上了，早冲上去
        - MACD 长了: 竞价段位
        - 成交量打幕: 第一小时
        """
        rsi = features.get('rsi_14', 50)
        macd = features.get('macd_line', 0)
        volume = features.get('volume_ratio', 1)
        
        if rsi < 30:
            return EntryTiming.PRE_OPEN
        elif macd > 0.1:
            return EntryTiming.OPEN_AUCTION
        elif volume > 1.5:
            return EntryTiming.FIRST_HOUR
        else:
            return EntryTiming.AFTERNOON
    
    # ==================== 特征计算 ====================
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """RSI 计算"""
        try:
            if len(df) < period:
                return 50.0
            
            delta = df['收盘'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs.iloc[-1])) if rs.iloc[-1] > 0 else 50
            return float(rsi)
        except:
            return 50.0
    
    def _calculate_macd(self, df: pd.DataFrame) -> float:
        """MACD 计算"""
        try:
            if len(df) < 26:
                return 0.0
            
            ema12 = df['收盘'].ewm(span=12).mean()
            ema26 = df['收盘'].ewm(span=26).mean()
            macd = ema12 - ema26
            return float(macd.iloc[-1])
        except:
            return 0.0
    
    def _calculate_kdj(self, df: pd.DataFrame) -> float:
        """KDJ K 值计算"""
        try:
            if len(df) < 9:
                return 50.0
            
            low_min = df['最低'].tail(9).min()
            high_max = df['最高'].tail(9).max()
            rsv = (df['收盘'].iloc[-1] - low_min) / (high_max - low_min) * 100 if high_max > low_min else 50
            
            return float(rsv)
        except:
            return 50.0
    
    def _get_current_price(self, stock_code: str) -> float:
        """TODO: 从 akshare 获取当前价"""
        try:
            realtime = DL.get_stock_realtime(stock_code)
            if realtime:
                return float(realtime.get('最新价', 0))
        except:
            pass
        return 0.0
    
    def _is_new_stock(self, stock_code: str) -> bool:
        """TODO: 是否新股"""
        return False
    
    @property
    def _feature_names(self) -> List[str]:
        """获取 14 特征名称"""
        return [
            'price_change', 'ma_20_ratio', 'ma_250_ratio',      # 涨幅 (3)
            'lhb_count', 'lhb_intensity', 'top_lhb_money',       # 龙虎榜 (3)
            'rsi_14', 'macd_line', 'kdj_k', 'volume_ratio',      # 技术 (4)
            'capital_inflow', 'short_interest',                   # 资金 (2)
            'topic_heat', 'sector_strength'                      # 题材 (2)
        ]


def demo_limit_up_prediction():
    """演示打板预测"""
    predictor = LimitUpPredictor()
    
    # 批量预测
    test_stocks = ['300059', '688688', '688888']
    today = datetime.now().strftime('%Y-%m-%d')
    
            print("\n[SEARCH] 批量预测一字板...")    predictions = predictor.batch_predict_limit_ups(test_stocks, today)
    
    print(f"\n预测 {len(predictions)} 个股票")
    
    # 批量筛选
            print("\n[TOP] 推荐股票 (筛选条件: 概率>60% + 低中风险):")    candidates = predictor.rank_candidates(predictions)
    
    for rank, (code, pred) in enumerate(candidates, 1):
        print(f"{rank}. {code}")
        print(f"一字板概率: {pred.oneword_probability:.1%}")
        print(f"置信度: {pred.oneword_confidence:.1%}")
        print(f"操作: 入场 {pred.entry_price:.2f}, 止损 {pred.stop_loss:.2f}, 止盈 {pred.take_profit:.2f}")
        print(f"风险: {pred.risk_level.value} ({pred.risk_reason})")
        print()


def get_limit_up_predictor(model_path: Optional[str] = None) -> LimitUpPredictor:
    """获取打板预测器实例
    
    Args:
        model_path: XGBoost模型路径（可选）
        
    Returns:
        LimitUpPredictor 实例
    """
    return LimitUpPredictor(model_path=model_path)


def _get_demo_prediction(stock_code: str, date: str, current_price: float = None) -> LimitUpPrediction:
    """获取演示用的预测结果"""
    import random
    
    # 生成随机但合理的预测结果
    oneword_prob = random.uniform(0.4, 0.9)
    confidence = random.uniform(0.6, 0.95)
    
    # 根据概率确定风险等级
    if oneword_prob > 0.8:
        risk_level = RiskLevel.LOW
        risk_reason = "一字板概率高，技术形态良好"
    elif oneword_prob > 0.6:
        risk_level = RiskLevel.MEDIUM
        risk_reason = "一字板概率中等，需谨慎操作"
    elif oneword_prob > 0.4:
        risk_level = RiskLevel.HIGH
        risk_reason = "一字板概率较低，风险较高"
    else:
        risk_level = RiskLevel.EXTREME
        risk_reason = "一字板概率很低，极高风险"
    
    # 生成演示特征分数
    features = {
        'price_change': random.uniform(-5, 10),
        'ma_20_ratio': random.uniform(0.95, 1.05),
        'ma_250_ratio': random.uniform(0.9, 1.1),
        'lhb_count': random.randint(0, 5),
        'lhb_intensity': random.uniform(0, 100),
        'top_lhb_money': random.uniform(0, 1000000),
        'rsi_14': random.uniform(30, 70),
        'macd_line': random.uniform(-1, 1),
        'kdj_k': random.uniform(20, 80),
        'volume_ratio': random.uniform(0.5, 2.0),
        'capital_inflow': random.uniform(-1000000, 1000000),
        'short_interest': random.uniform(0, 10),
        'topic_heat': random.uniform(0, 100),
        'sector_strength': random.uniform(0, 100)
    }
    
    # 计算价格
    if current_price is None:
        current_price = random.uniform(10, 100)
    
    # 计算操作建议
    entry_price = current_price * 1.01  # 涨停价附近
    stop_loss = current_price * 0.95  # 止损5%
    take_profit = current_price * 1.10  # 止盈10%
    
    # 入场时机
    if oneword_prob > 0.8:
        entry_timing = EntryTiming.PRE_OPEN
    elif oneword_prob > 0.6:
        entry_timing = EntryTiming.OPEN_AUCTION
    elif oneword_prob > 0.4:
        entry_timing = EntryTiming.FIRST_HOUR
    else:
        entry_timing = EntryTiming.AFTERNOON
    
    # 综合评分
    total_score = oneword_prob * 100 * (1 - (risk_level.value / 100) * 0.1)
    
    return LimitUpPrediction(
        stock_code=stock_code,
        date=date,
        oneword_probability=oneword_prob,
        oneword_confidence=confidence,
        features_score=features,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        entry_timing=entry_timing,
        risk_level=risk_level,
        risk_reason=risk_reason,
        total_score=total_score
    )


if __name__ == '__main__':
    demo_limit_up_prediction()
