#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试市场数据获取
验证涨停跌停数据是否正常
"""

import sys
from logic.data_manager import DataManager
from logic.sentiment_analyzer import SentimentAnalyzer
from logic.logger import get_logger

logger = get_logger(__name__)


def test_market_snapshot():
    """测试市场快照获取"""
    print("\n" + "="*60)
    print("测试1: 市场快照获取")
    print("="*60)
    
    try:
        import easyquotation as eq
        
        # 初始化行情接口
        quotation = eq.use('sina')
        
        print(f"✅ Easyquotation 已初始化: {type(quotation)}")
        
        # 获取市场快照
        snapshot = quotation.market_snapshot(prefix=False)
        
        if snapshot is None or len(snapshot) == 0:
            print("❌ 市场快照为空")
            return False
        
        print(f"✅ 获取市场快照成功: {len(snapshot)} 只股票")
        
        # 显示前5只股票的数据
        print("\n前5只股票数据:")
        for i, (code, data) in enumerate(list(snapshot.items())[:5]):
            print(f"  {code}: {data.get('name', 'N/A')} - 价格: {data.get('now', 0)} - 涨跌幅: {data.get('percent', 0)}%")
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_analyzer():
    """测试情绪分析器"""
    print("\n" + "="*60)
    print("测试2: 情绪分析器")
    print("="*60)
    
    try:
        dm = DataManager()
        analyzer = SentimentAnalyzer(dm)
        
        # 分析市场情绪
        metrics = analyzer.analyze_market_mood(force_refresh=True)
        
        if metrics is None:
            print("❌ 情绪分析返回 None")
            return False
        
        print(f"✅ 情绪分析成功")
        print(f"  - 涨停家数: {metrics.get('limit_up', 0)}")
        print(f"  - 跌停家数: {metrics.get('limit_down', 0)}")
        print(f"  - 上涨家数: {metrics.get('up', 0)}")
        print(f"  - 下跌家数: {metrics.get('down', 0)}")
        print(f"  - 市场温度: {metrics.get('score', 0)}")
        print(f"  - 炸板率: {metrics.get('zhaban_rate', 0):.1f}%")
        
        # 检查数据是否合理
        if metrics.get('limit_up', 0) == 0 and metrics.get('limit_down', 0) == 0:
            print("⚠️ 警告: 涨停和跌停家数都为0，数据可能有问题")
            return False
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_limit_up_pool():
    """测试涨停池数据获取"""
    print("\n" + "="*60)
    print("测试3: 涨停池数据获取")
    print("="*60)
    
    try:
        import akshare as ak
        from datetime import datetime
        
        # 获取今日涨停池
        today = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=today)
        
        if df is None or df.empty:
            print(f"⚠️ {today} 没有获取到涨停数据 (可能是休市或数据未更新)")
            return True
        
        print(f"✅ 获取涨停池成功: {len(df)} 只股票")
        
        # 显示前5只涨停股
        print("\n前5只涨停股:")
        for i, row in df.head(5).iterrows():
            print(f"  {row['代码']} {row['名称']} - 连板: {row['连板数']} - 封单: {row['封板资金']}")
        
        return True
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("市场数据获取测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("市场快照获取", test_market_snapshot()))
    results.append(("情绪分析器", test_sentiment_analyzer()))
    results.append(("涨停池数据获取", test_limit_up_pool()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查数据获取逻辑")
        return 1


if __name__ == "__main__":
    sys.exit(main())
