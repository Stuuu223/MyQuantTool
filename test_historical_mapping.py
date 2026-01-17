#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史数据映射验证测试
验证 HistoricalReplayProvider 的数据映射是否正确
"""

import sys
from logic.data_provider_factory import DataProviderFactory
from logic.logger import get_logger

logger = get_logger(__name__)


def test_data_mapping():
    """测试数据映射"""
    print("=" * 60)
    print("🔍 历史数据映射验证测试")
    print("=" * 60)
    
    try:
        # 创建历史回放数据提供者
        provider = DataProviderFactory.get_provider(
            mode='replay',
            date='20260116',
            stock_list=['600058', '000858']
        )
        
        # 获取数据
        print("\n📥 正在获取历史数据...")
        stocks_data = provider.get_realtime_data(['600058', '000858'])
        
        if not stocks_data:
            print("❌ 未获取到数据，请检查网络连接")
            return False
        
        print(f"✅ 成功获取 {len(stocks_data)} 只股票的数据\n")
        
        # 检查数据格式
        print("📊 数据格式检查：")
        required_fields = [
            'code', 'name', 'price', 'change_pct', 'volume', 'amount',
            'open', 'high', 'low', 'pre_close'
        ]
        
        for stock in stocks_data:
            print(f"\n股票: {stock['code']} - {stock['name']}")
            print("-" * 40)
            
            missing_fields = []
            for field in required_fields:
                if field not in stock:
                    missing_fields.append(field)
                else:
                    value = stock[field]
                    if field in ['change_pct']:
                        print(f"  {field}: {value*100:.2f}%")
                    elif field in ['amount', 'volume']:
                        print(f"  {field}: {value:,.0f}")
                    else:
                        print(f"  {field}: {value}")
            
            if missing_fields:
                print(f"  ⚠️ 缺少字段: {', '.join(missing_fields)}")
            else:
                print(f"  ✅ 所有必需字段都存在")
            
            # 检查特殊字段
            if 'replay_date' in stock:
                print(f"  📅 回放日期: {stock['replay_date']}")
            if 'replay_mode' in stock:
                print(f"  🎮 回放模式: {stock['replay_mode']}")
        
        # 检查数据合理性
        print("\n" + "=" * 60)
        print("🔍 数据合理性检查：")
        print("=" * 60)
        
        for stock in stocks_data:
            code = stock['code']
            price = stock['price']
            open_price = stock['open']
            high = stock['high']
            low = stock['low']
            change_pct = stock['change_pct']
            
            print(f"\n股票: {code}")
            
            # 检查价格关系
            if low <= price <= high:
                print(f"  ✅ 价格在高低范围内: {low} <= {price} <= {high}")
            else:
                print(f"  ❌ 价格异常: {low} <= {price} <= {high}")
            
            # 检查涨跌幅计算
            if stock['pre_close'] > 0:
                calculated_change = (price - stock['pre_close']) / stock['pre_close']
                if abs(calculated_change - change_pct) < 0.01:
                    print(f"  ✅ 涨跌幅计算正确: {change_pct*100:.2f}%")
                else:
                    print(f"  ⚠️ 涨跌幅可能不一致: {change_pct*100:.2f}% vs {calculated_change*100:.2f}%")
            
            # 检查成交额和成交量
            if stock['volume'] > 0 and stock['amount'] > 0:
                avg_price = stock['amount'] / stock['volume']
                if abs(avg_price - price) / price < 0.1:  # 允许10%误差
                    print(f"  ✅ 成交额和成交量匹配")
                else:
                    print(f"  ⚠️ 成交额和成交量可能不匹配: 均价={avg_price:.2f}, 收盘={price:.2f}")
        
        print("\n" + "=" * 60)
        print("✅ 数据映射验证测试完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_data_mapping()
    sys.exit(0 if success else 1)
