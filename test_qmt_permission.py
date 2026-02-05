#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QMT 资金流向数据权限

用途：
- 测试 QMT 账号是否有资金流向数据权限
- 测试 get_market_data_ex 接口返回的数据格式
- 验证 download_history_data 是否必要
"""

from xtquant import xtdata
import time

def test_single_stock_fund_flow():
    """测试单只股票的资金流数据"""
    
    print("=" * 80)
    print("🧪 QMT 资金流向数据权限测试")
    print("=" * 80)
    
    # 测试股票代码
    code = "000001.SZ"
    
    print(f"\n📌 测试股票: {code}")
    print("=" * 80)
    
    # Step 1: 尝试下载历史数据
    print(f"\n📥 Step 1: 尝试下载历史数据 (period='transactioncount1d')...")
    try:
        result = xtdata.download_history_data(code, period="transactioncount1d")
        print(f"   ✅ 下载完成，返回: {result}")
    except Exception as e:
        print(f"   ❌ 下载失败: {e}")
        print(f"   💡 可能原因：没有 VIP 权限")
        return False
    
    # Step 2: 获取资金流数据（尝试多种方式）
    print(f"\n📊 Step 2: 获取资金流数据...")
    
    # 尝试不同的参数组合
    test_configs = [
        {
            "name": "方案1: get_market_data_ex with transactioncount1d",
            "func": lambda: xtdata.get_market_data_ex([], [code], period="transactioncount1d", count=5)
        },
        {
            "name": "方案2: get_market_data_ex with 1d",
            "func": lambda: xtdata.get_market_data_ex([], [code], period="1d", count=5)
        },
        {
            "name": "方案3: get_market_data (标准方法)",
            "func": lambda: xtdata.get_market_data(
                field_list=['amount', 'volume', 'close'],
                stock_list=[code],
                period='1d',
                start_time='',
                end_time='',
                count=5
            )
        }
    ]
    
    for idx, config in enumerate(test_configs, 1):
        print(f"\n   🧪 尝试 {config['name']}...")
        try:
            result = config['func']()
            
            print(f"      返回类型: {type(result)}")
            
            if result is None:
                print(f"      ❌ 返回 None")
                continue
            
            if isinstance(result, dict):
                print(f"      ✅ 返回字典")
                print(f"      键: {list(result.keys())}")
                
                if code in result:
                    print(f"      ✅ 包含该股票数据")
                    data = result[code]
                    print(f"      数据类型: {type(data)}")
                    print(f"      数据内容: {data}")
                else:
                    print(f"      ❌ 不包含该股票数据")
                    print(f"      可用键: {list(result.keys())}")
            else:
                print(f"      ❌ 返回格式异常: {type(result)}")
                print(f"      值: {result}")
        
        except Exception as e:
            print(f"      ❌ 异常: {e}")
    
    # 最后尝试标准的 get_market_data 获取 Tick 数据
    print(f"\n   🧪 尝试标准方法: get_full_tick...")
    try:
        tick_data = xtdata.get_full_tick([code])
        print(f"      返回类型: {type(tick_data)}")
        
        if isinstance(tick_data, dict):
            print(f"      ✅ 返回字典")
            print(f"      键: {list(tick_data.keys())}")
            
            if code in tick_data:
                tick = tick_data[code]
                print(f"      ✅ 包含该股票数据")
                print(f"      Tick 数据: {tick}")
            else:
                print(f"      ❌ 不包含该股票数据")
                print(f"      可用键: {list(tick_data.keys())}")
        else:
            print(f"      ❌ 返回格式异常: {type(tick_data)}")
            print(f"      值: {tick_data}")
    
    except Exception as e:
        print(f"      ❌ 异常: {e}")
        
    except Exception as e:
        print(f"   ❌ 获取失败: {e}")
        print(f"   💡 可能原因：没有 VIP 权限或接口调用错误")
        return False

if __name__ == "__main__":
    test_single_stock_fund_flow()