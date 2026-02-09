"""
Tushare 5000 积分接口测试脚本
测试目标：验证行业资金流向和筹码成本接口是否可用
"""

import pandas as pd
import tushare as ts
from datetime import datetime

# 设置 token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_industry_moneyflow():
    """测试行业资金流向接口（doc_id=343）"""
    print("=" * 60)
    print("测试 1: 行业资金流向接口（THS）")
    print("=" * 60)
    
    try:
        # 获取行业资金流向数据
        df = pro.ths_moneyflow(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"✅ 获取成功：{len(df)} 条记录")
        print(f"字段：{list(df.columns)}")
        print(f"\n数据：")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        print("（可能原因：积分不足、参数错误、接口未开通）")
        return None

def test_chip_cost():
    """测试每日筹码成本和胜率接口（doc_id=293）"""
    print("\n" + "=" * 60)
    print("测试 2: 每日筹码成本和胜率接口")
    print("=" * 60)
    
    try:
        # 获取筹码成本和胜率数据
        df = pro.daily_chip(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"✅ 获取成功：{len(df)} 条记录")
        print(f"字段：{list(df.columns)}")
        print(f"\n数据：")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        print("（可能原因：积分不足、参数错误、接口未开通）")
        return None

def test_chip_distribution():
    """测试筹码分布接口"""
    print("\n" + "=" * 60)
    print("测试 3: 筹码分布接口")
    print("=" * 60)
    
    try:
        # 获取筹码分布数据
        df = pro.stk_chip_distribution(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206'
        )
        
        print(f"✅ 获取成功：{len(df)} 条记录")
        print(f"字段：{list(df.columns)}")
        print(f"\n数据：")
        print(df)
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        print("（可能原因：积分不足、参数错误、接口未开通）")
        return None

def main():
    print("Tushare 5000 积分接口测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试股票: 603607.SH（京华激光）")
    print(f"测试日期: 2026-02-01 到 2026-02-06")
    print()
    
    # 运行测试
    test_industry_moneyflow()
    test_chip_cost()
    test_chip_distribution()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n结论：")
    print("1. 如果行业资金流向测试通过 → 可以获取行业资金流向数据")
    print("2. 如果筹码成本测试通过 → 可以获取筹码成本和胜率数据")
    print("3. 如果筹码分布测试通过 → 可以获取筹码分布数据")
    print("\n这些数据可以作为历史快照的增强特征。")

if __name__ == "__main__":
    main()