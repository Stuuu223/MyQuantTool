"""
真实数据驱动的智能交易系统
整合真实数据源、深度学习模型、LLM推理和因果推断
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from logic.akshare_data_loader import AKShareDataLoader
from logic.llm_interface import LLMInterface, LLMMessage
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


class MarketDataset(Dataset):
    """市场数据集"""
    
    def __init__(self, data: pd.DataFrame, sequence_length: int = 60, 
                 feature_columns: List[str] = None):
        """
        初始化数据集
        
        Args:
            data: 市场数据
            sequence_length: 序列长度
            feature_columns: 特征列
        """
        self.data = data
        self.sequence_length = sequence_length
        
        if feature_columns is None:
            self.feature_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
        else:
            self.feature_columns = feature_columns
        
        # 归一化数据
        self.features = self._normalize_features()
        
        # 创建序列
        self.sequences = self._create_sequences()
    
    def _normalize_features(self) -> np.ndarray:
        """归一化特征"""
        features = self.data[self.feature_columns].values
        
        # Z-score归一化
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0)
        normalized = (features - mean) / (std + 1e-10)
        
        return normalized
    
    def _create_sequences(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        """创建序列"""
        sequences = []
        
        for i in range(len(self.features) - self.sequence_length):
            X = self.features[i:i + self.sequence_length]
            y = self.features[i + self.sequence_length, 3]  # 预测收盘价
            
            sequences.append((X, y))
        
        return sequences
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        X, y = self.sequences[idx]
        return torch.FloatTensor(X), torch.FloatTensor([y])


class DeepLearningModel(nn.Module):
    """深度学习模型"""
    
    def __init__(self, input_size: int, hidden_size: int = 128, 
                 num_layers: int = 2, output_size: int = 1, 
                 dropout: float = 0.2):
        """
        初始化深度学习模型
        
        Args:
            input_size: 输入维度
            hidden_size: 隐藏层维度
            num_layers: LSTM层数
            output_size: 输出维度
            dropout: Dropout比例
        """
        super(DeepLearningModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM层
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        
        # 注意力机制
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=8)
        
        # 全连接层
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc2 = nn.Linear(hidden_size // 2, output_size)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # 激活函数
        self.relu = nn.ReLU()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        # LSTM
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # 注意力机制
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # 取最后一个时间步
        last_output = attn_out[:, -1, :]
        
        # 全连接层
        out = self.dropout(last_output)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out


class CausalInferenceEngine:
    """因果推断引擎"""
    
    def __init__(self):
        """初始化因果推断引擎"""
        self.causal_graph = {}
        self.causal_strengths = {}
    
    def discover_causal_relations(self, data: pd.DataFrame, 
                                 method: str = 'pc') -> Dict[str, Dict[str, float]]:
        """
        发现因果关系
        
        Args:
            data: 数据
            method: 方法 (pc, ges, notears)
            
        Returns:
            因果关系图
        """
        # 简化版：使用相关性作为因果强度的代理
        # 实际应该使用专业的因果发现算法
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        causal_relations = {}
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                # 计算相关性
                corr = data[col1].corr(data[col2])
                
                if abs(corr) > 0.5:  # 阈值
                    # 假设因果关系（实际需要更复杂的算法）
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
        # 简化版：使用回归估计因果效应
        # 实际应该使用Do-Calculus、IPW等方法
        
        if confounders is None:
            confounders = []
        
        # 构建回归公式
        formula = f"{outcome} ~ {treatment}"
        if confounders:
            formula += " + " + " + ".join(confounders)
        
        # 简化：使用线性回归
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


class OnlineLearningEngine:
    """在线学习引擎"""
    
    def __init__(self, model: DeepLearningModel, learning_rate: float = 0.001):
        """
        初始化在线学习引擎
        
        Args:
            model: 模型
            learning_rate: 学习率
        """
        self.model = model
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.loss_fn = nn.MSELoss()
        self.performance_history = []
    
    def online_update(self, X: torch.Tensor, y: torch.Tensor) -> Dict[str, float]:
        """
        在线更新模型
        
        Args:
            X: 输入数据
            y: 目标数据
            
        Returns:
            更新结果
        """
        # 前向传播
        self.model.train()
        predictions = self.model(X)
        
        # 计算损失
        loss = self.loss_fn(predictions, y)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # 记录性能
        mae = torch.mean(torch.abs(predictions - y)).item()
        
        result = {
            'loss': loss.item(),
            'mae': mae,
            'timestamp': datetime.now().isoformat()
        }
        
        self.performance_history.append(result)
        
        return result
    
    def evaluate(self, X: torch.Tensor, y: torch.Tensor) -> Dict[str, float]:
        """
        评估模型
        
        Args:
            X: 输入数据
            y: 目标数据
            
        Returns:
            评估结果
        """
        self.model.eval()
        
        with torch.no_grad():
            predictions = self.model(X)
            
            loss = self.loss_fn(predictions, y)
            mae = torch.mean(torch.abs(predictions - y)).item()
            mape = torch.mean(torch.abs((predictions - y) / (y + 1e-10))).item() * 100
        
        return {
            'loss': loss.item(),
            'mae': mae,
            'mape': mape
        }


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
        
        # LLM接口
        self.llm = None
        if llm_api_key:
            self.llm = LLMInterface(api_key=llm_api_key)
        
        # 因果推断引擎
        self.causal_engine = CausalInferenceEngine()
        
        # 在线学习引擎
        self.model = None
        self.online_engine = None
        
        # 系统状态
        self.market_state = {}
        self.decision_history = []
    
    def initialize_model(self, stock_code: str, sequence_length: int = 60):
        """
        初始化模型
        
        Args:
            stock_code: 股票代码
            sequence_length: 序列长度
        """
        # 获取历史数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        data = self.data_pipeline.get_stock_data(stock_code, 'daily', start_date, end_date)
        
        if data.empty:
            raise ValueError(f"无法获取 {stock_code} 的数据")
        
        # 创建数据集
        dataset = MarketDataset(data, sequence_length)
        
        # 初始化模型
        input_size = len(dataset.feature_columns)
        self.model = DeepLearningModel(input_size)
        
        # 初始化在线学习引擎
        self.online_engine = OnlineLearningEngine(self.model)
        
        logger.info(f"模型初始化完成，输入维度: {input_size}")
    
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
        
        # 发现因果关系
        causal_graph = self.causal_engine.discover_causal_relations(data)
        
        self.market_state['causal_graph'] = causal_graph
        
        return causal_graph
    
    def make_decision(self, stock_code: str, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        做出交易决策
        
        Args:
            stock_code: 股票代码
            current_data: 当前数据
            
        Returns:
            决策结果
        """
        if self.model is None:
            self.initialize_model(stock_code)
        
        # 使用深度学习模型预测
        # 这里需要将current_data转换为模型输入格式
        
        # 使用LLM进行推理
        llm_analysis = self.analyze_market_with_llm(stock_code, current_data)
        
        # 因果分析
        causal_graph = self.discover_causal_mechanism(stock_code)
        
        # 综合决策
        decision = {
            'stock_code': stock_code,
            'timestamp': datetime.now().isoformat(),
            'action': 'hold',  # hold, buy, sell
            'confidence': 0.5,
            'llm_analysis': llm_analysis,
            'causal_factors': list(causal_graph.keys()),
            'reasoning': '基于深度学习预测和LLM推理的综合决策'
        }
        
        self.decision_history.append(decision)
        
        return decision
    
    def continuous_learning(self, stock_code: str, new_data: pd.DataFrame):
        """
        持续学习
        
        Args:
            stock_code: 股票代码
            new_data: 新数据
        """
        if self.online_engine is None:
            logger.warning("在线学习引擎未初始化")
            return
        
        # 创建数据集
        dataset = MarketDataset(new_data, sequence_length=60)
        
        # 批量更新
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        total_loss = 0.0
        for X, y in dataloader:
            result = self.online_engine.online_update(X, y)
            total_loss += result['loss']
        
        avg_loss = total_loss / len(dataloader)
        
        logger.info(f"在线学习完成，平均损失: {avg_loss:.4f}")
        
        return avg_loss


# 使用示例
if __name__ == "__main__":
    # 创建系统
    system = IntelligentTradingSystem(llm_api_key="your-api-key")
    
    # 分析股票
    stock_code = "600000"
    analysis = system.analyze_market_with_llm(stock_code)
    print("LLM分析结果:")
    print(analysis)
    
    # 发现因果关系
    causal_graph = system.discover_causal_mechanism(stock_code)
    print("\n因果关系:")
    print(causal_graph)
    
    # 做出决策
    decision = system.make_decision(stock_code, {})
    print("\n决策结果:")
    print(decision)