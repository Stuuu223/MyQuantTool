"""
真实数据驱动的智能交易系统（简化版）
不依赖PyTorch，使用scikit-learn实现深度学习功能
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from logic.akshare_data_loader import AKShareDataLoader
from logic.llm_interface import LLMManager, LLMMessage
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)


class RealMarketDataPipeline:
    """真实市场数据管道"""
    
    def __init__(self):
        """初始化数据管道"""
        self.data_loader = AKShareDataLoader()
        self.cache = {}
        self.cache_expiry = 300  # 5分钟缓存
    
    def get_stock_data(self, stock_code: str, period: str = 'daily', 
                      start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票真实数据
        
        Args:
            stock_code: 股票代码
            period: 周期 (daily, weekly, monthly)
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            股票数据
        """
        cache_key = f"{stock_code}_{period}_{start_date}_{end_date}"
        
        # 检查缓存
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_expiry:
                return cached_data
        
        try:
            # 获取真实数据
            if period == 'daily':
                df = self.data_loader.get_stock_daily(stock_code, start_date, end_date)
            elif period == 'weekly':
                df = self.data_loader.get_stock_weekly(stock_code, start_date, end_date)
            else:
                df = self.data_loader.get_stock_monthly(stock_code, start_date, end_date)
            
            # 缓存数据
            self.cache[cache_key] = (df, datetime.now())
            
            logger.info(f"成功获取 {stock_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取 {stock_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_lhb_data(self, date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜真实数据
        
        Args:
            date: 日期
            
        Returns:
            龙虎榜数据
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y%m%d")
            
            df = self.data_loader.get_lhb_daily(date)
            logger.info(f"成功获取龙虎榜数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    def get_sector_data(self, sector_name: str = None) -> pd.DataFrame:
        """
        获取板块真实数据
        
        Args:
            sector_name: 板块名称
            
        Returns:
            板块数据
        """
        try:
            if sector_name is None:
                df = self.data_loader.get_sector_list()
            else:
                df = self.data_loader.get_sector_stocks(sector_name)
            
            logger.info(f"成功获取板块数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return pd.DataFrame()


class FeatureEngineer:
    """特征工程"""
    
    def __init__(self):
        """初始化特征工程"""
        self.scaler = StandardScaler()
    
    def create_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建技术指标特征
        
        Args:
            data: 原始数据
            
        Returns:
            特征数据
        """
        df = data.copy()
        
        # 移动平均
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # 成交量指标
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma10'] = df['volume'].rolling(window=10).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        # 价格变化
        df['pct_change'] = df['close'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        
        # 波动率
        df['volatility'] = df['pct_change'].rolling(window=20).std()
        
        return df
    
    def create_sequence_features(self, data: pd.DataFrame, sequence_length: int = 20) -> np.ndarray:
        """
        创建序列特征
        
        Args:
            data: 数据
            sequence_length: 序列长度
            
        Returns:
            序列特征
        """
        features = []
        
        for i in range(sequence_length, len(data)):
            window = data.iloc[i-sequence_length:i]
            features.append(window.values.flatten())
        
        return np.array(features)


class MLModel:
    """机器学习模型"""
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        初始化模型
        
        Args:
            model_type: 模型类型
        """
        self.model_type = model_type
        
        if model_type == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        elif model_type == 'gradient_boosting':
            self.model = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        else:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        训练模型
        
        Args:
            X: 特征
            y: 目标
            
        Returns:
            训练结果
        """
        # 归一化
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        
        # 评估
        y_pred = self.model.predict(X_scaled)
        mae = np.mean(np.abs(y - y_pred))
        mse = np.mean((y - y_pred) ** 2)
        
        return {
            'mae': mae,
            'mse': mse,
            'rmse': np.sqrt(mse)
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测
        
        Args:
            X: 特征
            
        Returns:
            预测结果
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self, feature_names: List[str]) -> Dict[str, float]:
        """
        获取特征重要性
        
        Args:
            feature_names: 特征名称
            
        Returns:
            特征重要性
        """
        if not self.is_fitted:
            raise ValueError("模型未训练")
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return dict(zip(feature_names, importances))
        else:
            return {}


class CausalInferenceEngine:
    """因果推断引擎"""
    
    def __init__(self):
        """初始化因果推断引擎"""
        self.causal_graph = {}
    
    def discover_causal_relations(self, data: pd.DataFrame, threshold: float = 0.5) -> Dict[str, Dict[str, float]]:
        """
        发现因果关系
        
        Args:
            data: 数据
            threshold: 相关性阈值
            
        Returns:
            因果关系图
        """
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        causal_relations = {}
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                # 计算相关性
                corr = data[col1].corr(data[col2])
                
                if abs(corr) > threshold:
                    # 基于时间顺序推断因果方向（简化版）
                    # 实际应该使用更复杂的因果发现算法
                    if corr > 0:
                        causal_relations[col1] = {col2: abs(corr)}
                    else:
                        causal_relations[col2] = {col1: abs(corr)}
        
        self.causal_graph = causal_relations
        return causal_relations
    
    def estimate_causal_effect(self, treatment: str, outcome: str,
                             data: pd.DataFrame, confounders: List[str] = None) -> float:
        """
        估计因果效应
        
        Args:
            treatment: 处理变量
            outcome: 结果变量
            data: 数据
            confounders: 混淆变量
            
        Returns:
            因果效应
        """
        if confounders is None:
            confounders = []
        
        try:
            from sklearn.linear_model import LinearRegression
            
            X = data[[treatment] + confounders].values
            y = data[outcome].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            # 处理变量的系数就是因果效应
            causal_effect = model.coef_[0]
            
            return causal_effect
            
        except Exception as e:
            logger.error(f"估计因果效应失败: {e}")
            return 0.0


class IntelligentTradingSystem:
    """智能交易系统"""
    
    def __init__(self, llm_api_key: str = None):
        """
        初始化智能交易系统
        
        Args:
            llm_api_key: LLM API密钥
        """
        # 数据管道
        self.data_pipeline = RealMarketDataPipeline()
        
        # 特征工程
        self.feature_engineer = FeatureEngineer()
        
        # LLM接口
        self.llm = None
        if llm_api_key:
            self.llm = LLMManager(api_key=llm_api_key)
        
        # 因果推断引擎
        self.causal_engine = CausalInferenceEngine()
        
        # 模型
        self.model = None
        self.feature_names = []
        
        # 系统状态
        self.market_state = {}
        self.decision_history = []
    
    def initialize_model(self, stock_code: str, model_type: str = 'random_forest'):
        """
        初始化模型
        
        Args:
            stock_code: 股票代码
            model_type: 模型类型
        """
        # 获取历史数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = self.data_pipeline.get_stock_data(stock_code, 'daily', start_date, end_date)
        
        if data.empty:
            raise ValueError(f"无法获取 {stock_code} 的数据")
        
        # 创建技术指标
        data_with_features = self.feature_engineer.create_technical_features(data)
        
        # 准备训练数据
        data_with_features = data_with_features.dropna()
        
        # 选择特征列
        feature_cols = [col for col in data_with_features.columns 
                       if col not in ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
        
        # 创建序列特征
        sequence_length = 20
        X = self.feature_engineer.create_sequence_features(
            data_with_features[feature_cols + ['close']], 
            sequence_length
        )
        
        # 目标是预测下一个收盘价
        y = data_with_features['close'].values[sequence_length:]
        
        # 初始化模型
        self.model = MLModel(model_type)
        self.feature_names = feature_cols
        
        # 训练模型
        result = self.model.train(X, y)
        
        logger.info(f"模型初始化完成，MAE: {result['mae']:.4f}")
        
        return result
    
    def analyze_market_with_llm(self, stock_code: str, context: Dict[str, Any] = None) -> str:
        """
        使用LLM分析市场
        
        Args:
            stock_code: 股票代码
            context: 上下文信息
            
        Returns:
            LLM分析结果
        """
        if self.llm is None:
            return "LLM未配置"
        
        # 获取市场数据
        data = self.data_pipeline.get_stock_data(stock_code, 'daily')
        lhb_data = self.data_pipeline.get_lhb_data()
        
        # 构建提示词
        prompt = f"""作为专业的股票分析师，请分析股票 {stock_code} 的市场情况：

股票数据：
{data.tail(10).to_string()}

龙虎榜数据：
{lhb_data.head(5).to_string() if not lhb_data.empty else "无龙虎榜数据"}

请从以下角度进行分析：
1. 技术面：价格走势、成交量、技术指标
2. 基本面：公司基本面（如果有）
3. 资金面：龙虎榜、资金流向
4. 情绪面：市场情绪、热点题材
5. 因果关系：分析影响股价的关键因素

请给出：
- 当前市场状态
- 关键驱动因素
- 风险提示
- 操作建议
- 预测理由"""
        
        messages = [
            LLMMessage(role="system", content="你是一个专业的股票分析师，擅长技术分析和市场研判。"),
            LLMMessage(role="user", content=prompt)
        ]
        
        try:
            response = self.llm.chat(messages, model="gpt-4")
            return response.content
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return f"LLM分析失败: {str(e)}"
    
    def discover_causal_mechanism(self, stock_code: str) -> Dict[str, Dict[str, float]]:
        """
        发现市场因果机制
        
        Args:
            stock_code: 股票代码
            
        Returns:
            因果关系图
        """
        # 获取数据
        data = self.data_pipeline.get_stock_data(stock_code, 'daily')
        
        if data.empty:
            return {}
        
        # 创建技术指标
        data_with_features = self.feature_engineer.create_technical_features(data)
        
        # 发现因果关系
        causal_graph = self.causal_engine.discover_causal_relations(data_with_features)
        
        self.market_state['causal_graph'] = causal_graph
        
        return causal_graph
    
    def make_decision(self, stock_code: str, current_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        做出交易决策
        
        Args:
            stock_code: 股票代码
            current_data: 当前数据
            
        Returns:
            决策结果
        """
        if self.model is None:
            try:
                self.initialize_model(stock_code)
            except Exception as e:
                logger.error(f"模型初始化失败: {e}")
                return {
                    'stock_code': stock_code,
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': f"模型初始化失败: {str(e)}"
                }
        
        # 获取最新数据
        data = self.data_pipeline.get_stock_data(stock_code, 'daily')
        
        if data.empty:
            return {
                'stock_code': stock_code,
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': "无法获取数据"
            }
        
        # 创建技术指标
        data_with_features = self.feature_engineer.create_technical_features(data)
        
        # 预测下一个价格
        try:
            feature_cols = [col for col in data_with_features.columns 
                           if col not in ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
            
            sequence_length = 20
            X = self.feature_engineer.create_sequence_features(
                data_with_features[feature_cols + ['close']], 
                sequence_length
            )
            
            if len(X) == 0:
                return {
                    'stock_code': stock_code,
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': "数据不足"
                }
            
            # 预测
            prediction = self.model.predict(X[-1:])
            current_price = data_with_features['close'].iloc[-1]
            predicted_price = prediction[0]
            
            # 计算收益率
            return_rate = (predicted_price - current_price) / current_price
            
            # 决策逻辑
            if return_rate > 0.02:
                action = 'buy'
                confidence = min(0.9, return_rate * 10)
            elif return_rate < -0.02:
                action = 'sell'
                confidence = min(0.9, abs(return_rate) * 10)
            else:
                action = 'hold'
                confidence = 0.5
            
            # 因果分析
            causal_graph = self.discover_causal_mechanism(stock_code)
            
            # LLM分析（如果配置）
            llm_analysis = ""
            if self.llm:
                llm_analysis = self.analyze_market_with_llm(stock_code)
            
            decision = {
                'stock_code': stock_code,
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'confidence': confidence,
                'current_price': current_price,
                'predicted_price': predicted_price,
                'expected_return': return_rate,
                'causal_factors': list(causal_graph.keys()),
                'llm_analysis': llm_analysis,
                'reasoning': f"基于机器学习预测，预期收益率: {return_rate:.2%}"
            }
            
            self.decision_history.append(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"决策失败: {e}")
            return {
                'stock_code': stock_code,
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f"决策失败: {str(e)}"
            }


# 使用示例
if __name__ == "__main__":
    # 创建系统
    system = IntelligentTradingSystem(llm_api_key=None)
    
    # 分析股票
    stock_code = "600000"
    
    print("初始化模型...")
    result = system.initialize_model(stock_code)
    print(f"训练结果: {result}")
    
    print("\n发现因果关系...")
    causal_graph = system.discover_causal_mechanism(stock_code)
    print(f"因果关系: {causal_graph}")
    
    print("\n做出决策...")
    decision = system.make_decision(stock_code)
    print(f"决策结果:")
    for key, value in decision.items():
        print(f"  {key}: {value}")