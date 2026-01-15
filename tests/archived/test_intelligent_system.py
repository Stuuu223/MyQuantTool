"""
测试真实数据驱动的智能交易系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from logic.intelligent_trading_system_simple import IntelligentTradingSystem, RealMarketDataPipeline
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_real_data_pipeline():
    """测试真实数据管道"""
    print("=" * 60)
    print("测试1: 真实数据管道")
    print("=" * 60)
    
    pipeline = RealMarketDataPipeline()
    
    # 测试获取股票数据
    print("\n1.1 获取股票数据...")
    stock_code = "600000"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    data = pipeline.get_stock_data(stock_code, 'daily', start_date, end_date)
    
    if not data.empty:
        print(f"✅ 成功获取 {stock_code} 数据")
        print(f"   数据量: {len(data)} 条")
        print(f"   时间范围: {data.index[0]} 到 {data.index[-1]}")
        print(f"   列名: {list(data.columns)}")
        print(f"\n   最新5条数据:")
        print(data.tail())
    else:
        print(f"❌ 获取 {stock_code} 数据失败")
    
    # 测试获取龙虎榜数据
    print("\n1.2 获取龙虎榜数据...")
    lhb_data = pipeline.get_lhb_data()
    
    if not lhb_data.empty:
        print(f"✅ 成功获取龙虎榜数据")
        print(f"   数据量: {len(lhb_data)} 条")
        print(f"   列名: {list(lhb_data.columns)}")
        print(f"\n   最新5条数据:")
        print(lhb_data.head())
    else:
        print(f"⚠️  龙虎榜数据为空（可能不是交易日）")
    
    # 测试获取板块数据
    print("\n1.3 获取板块数据...")
    sector_data = pipeline.get_sector_data()
    
    if not sector_data.empty:
        print(f"✅ 成功获取板块数据")
        print(f"   数据量: {len(sector_data)} 条")
        print(f"   列名: {list(sector_data.columns)}")
        print(f"\n   最新5条数据:")
        print(sector_data.head())
    else:
        print(f"❌ 获取板块数据失败")


def test_deep_learning_model():
    """测试深度学习模型"""
    print("\n" + "=" * 60)
    print("测试2: 深度学习模型")
    print("=" * 60)
    
    try:
        import torch
        from logic.intelligent_trading_system import DeepLearningModel, MarketDataset
        
        print("\n2.1 创建模拟数据...")
        # 创建模拟数据
        dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
        data = pd.DataFrame({
            'date': dates,
            'open': np.linspace(10, 20, 100) + np.random.randn(100) * 0.5,
            'high': np.linspace(10.5, 20.5, 100) + np.random.randn(100) * 0.5,
            'low': np.linspace(9.5, 19.5, 100) + np.random.randn(100) * 0.5,
            'close': np.linspace(10, 20, 100) + np.random.randn(100) * 0.5,
            'volume': np.linspace(1000000, 5000000, 100),
            'amount': np.linspace(10000000, 50000000, 100)
        })
        
        print(f"✅ 模拟数据创建成功，共 {len(data)} 条")
        
        print("\n2.2 创建数据集...")
        dataset = MarketDataset(data, sequence_length=20)
        print(f"✅ 数据集创建成功，样本数: {len(dataset)}")
        
        print("\n2.3 创建深度学习模型...")
        input_size = len(dataset.feature_columns)
        model = DeepLearningModel(input_size, hidden_size=64, num_layers=2)
        print(f"✅ 模型创建成功")
        print(f"   输入维度: {input_size}")
        print(f"   隐藏层维度: 64")
        print(f"   LSTM层数: 2")
        
        print("\n2.4 测试前向传播...")
        X, y = dataset[0]
        X_batch = X.unsqueeze(0)  # 添加batch维度
        output = model(X_batch)
        print(f"✅ 前向传播成功")
        print(f"   输入形状: {X_batch.shape}")
        print(f"   输出形状: {output.shape}")
        print(f"   输出值: {output.item():.4f}")
        print(f"   目标值: {y.item():.4f}")
        
        print("\n2.5 测试训练...")
        from logic.intelligent_trading_system import OnlineLearningEngine
        
        engine = OnlineLearningEngine(model, learning_rate=0.001)
        
        # 批量训练
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=16, shuffle=True)
        
        for epoch in range(5):
            total_loss = 0.0
            for X_batch, y_batch in dataloader:
                result = engine.online_update(X_batch, y_batch)
                total_loss += result['loss']
            
            avg_loss = total_loss / len(dataloader)
            print(f"   Epoch {epoch+1}/5, Loss: {avg_loss:.4f}")
        
        print("✅ 训练完成")
        
        print("\n2.6 测试评估...")
        X_test, y_test = dataset[0]
        X_test_batch = X_test.unsqueeze(0)
        y_test_batch = y_test.unsqueeze(0)
        
        eval_result = engine.evaluate(X_test_batch, y_test_batch)
        print(f"✅ 评估完成")
        print(f"   Loss: {eval_result['loss']:.4f}")
        print(f"   MAE: {eval_result['mae']:.4f}")
        print(f"   MAPE: {eval_result['mape']:.2f}%")
        
    except Exception as e:
        print(f"❌ 深度学习模型测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_causal_inference():
    """测试因果推断"""
    print("\n" + "=" * 60)
    print("测试3: 因果推断")
    print("=" * 60)
    
    try:
        from logic.intelligent_trading_system import CausalInferenceEngine
        
        print("\n3.1 创建模拟数据...")
        # 创建有因果关系的数据
        np.random.seed(42)
        n = 1000
        
        # X -> Y -> Z
        X = np.random.randn(n)
        Y = 2 * X + np.random.randn(n) * 0.5
        Z = 3 * Y + np.random.randn(n) * 0.5
        
        data = pd.DataFrame({
            'X': X,
            'Y': Y,
            'Z': Z,
            'W': np.random.randn(n)  # 独立变量
        })
        
        print(f"✅ 模拟数据创建成功，共 {len(data)} 条")
        print(f"   列名: {list(data.columns)}")
        
        print("\n3.2 发现因果关系...")
        engine = CausalInferenceEngine()
        causal_graph = engine.discover_causal_relations(data)
        
        print(f"✅ 因果关系发现完成")
        print(f"   发现的因果关系:")
        for cause, effects in causal_graph.items():
            for effect, strength in effects.items():
                print(f"     {cause} -> {effect} (强度: {strength:.4f})")
        
        print("\n3.3 估计因果效应...")
        causal_effect = engine.estimate_causal_effect('X', 'Y', data)
        print(f"✅ 因果效应估计完成")
        print(f"   X -> Y 的因果效应: {causal_effect:.4f}")
        print(f"   真实因果效应: 2.0")
        print(f"   误差: {abs(causal_effect - 2.0):.4f}")
        
    except Exception as e:
        print(f"❌ 因果推断测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_intelligent_system():
    """测试智能交易系统"""
    print("\n" + "=" * 60)
    print("测试4: 智能交易系统集成")
    print("=" * 60)
    
    try:
        print("\n4.1 创建智能交易系统...")
        system = IntelligentTradingSystem(llm_api_key=None)  # 不使用LLM
        print("✅ 系统创建成功")
        
        print("\n4.2 初始化模型...")
        stock_code = "600000"
        system.initialize_model(stock_code)
        print(f"✅ 模型初始化成功")
        
        print("\n4.3 发现因果机制...")
        causal_graph = system.discover_causal_mechanism(stock_code)
        print(f"✅ 因果机制发现完成")
        print(f"   发现的因果因素: {list(causal_graph.keys())}")
        
        print("\n4.4 做出决策...")
        current_data = {
            'timestamp': datetime.now().isoformat(),
            'price': 10.5,
            'volume': 1000000
        }
        decision = system.make_decision(stock_code, current_data)
        print(f"✅ 决策完成")
        print(f"   动作: {decision['action']}")
        print(f"   置信度: {decision['confidence']:.2f}")
        print(f"   推理: {decision['reasoning']}")
        
        print("\n4.5 持续学习...")
        # 创建模拟新数据
        dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=10)
        new_data = pd.DataFrame({
            'date': dates,
            'open': np.linspace(10, 11, 10) + np.random.randn(10) * 0.2,
            'high': np.linspace(10.2, 11.2, 10) + np.random.randn(10) * 0.2,
            'low': np.linspace(9.8, 10.8, 10) + np.random.randn(10) * 0.2,
            'close': np.linspace(10, 11, 10) + np.random.randn(10) * 0.2,
            'volume': np.linspace(1000000, 2000000, 10),
            'amount': np.linspace(10000000, 20000000, 10)
        })
        
        avg_loss = system.continuous_learning(stock_code, new_data)
        print(f"✅ 持续学习完成")
        print(f"   平均损失: {avg_loss:.4f}")
        
    except Exception as e:
        print(f"❌ 智能系统测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("开始测试真实数据驱动的智能交易系统")
    print("=" * 60)
    
    # 测试1: 真实数据管道
    test_real_data_pipeline()
    
    # 测试2: 深度学习模型
    test_deep_learning_model()
    
    # 测试3: 因果推断
    test_causal_inference()
    
    # 测试4: 智能系统集成
    test_intelligent_system()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()