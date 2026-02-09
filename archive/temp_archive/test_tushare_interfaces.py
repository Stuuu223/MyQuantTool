"""
Tushare 接口测试脚本
测试目标：验证 Tushare 能否承担历史快照重建的数据源
测试股票：603607.SH（京华激光）
测试日期：2026-02-01 到 2026-02-06
"""

import pandas as pd
import tushare as ts
from datetime import datetime

# 设置 token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_daily_bars():
    """测试日线行情接口"""
    print("=" * 60)
    print("测试 1: 日线行情接口 (pro_bar)")
    print("=" * 60)
    
    try:
        # 获取日线数据（前复权）
        df = ts.pro_bar(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206',
            adj='qfq',  # 前复权
            freq='D'
        )
        
        print(f"✅ 获取成功：{len(df)} 条记录")
        print(f"字段：{list(df.columns)}")
        print(f"\n前5条数据：")
        print(df.head())
        print(f"\n数据类型：")
        print(df.dtypes)
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        return None

def test_tech_factors():
    """测试技术因子接口"""
    print("\n" + "=" * 60)
    print("测试 2: 技术因子接口")
    print("=" * 60)
    
    try:
        # 获取技术因子（需要专业版积分）
        df = ts.pro_bar(
            ts_code='603607.SH',
            start_date='20260201',
            end_date='20260206',
            adj='qfq',
            freq='D'
        )
        
        # 计算简单技术因子
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['pct_chg_3d'] = df['close'].pct_change(3)
        
        print(f"✅ 计算成功：{len(df)} 条记录")
        print(f"\n技术因子数据：")
        print(df[['trade_date', 'close', 'ma5', 'ma10', 'pct_chg_3d']].head())
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        return None

def test_intraday_bars():
    """测试分钟线数据（可选）"""
    print("\n" + "=" * 60)
    print("测试 3: 分钟线数据（5分钟）")
    print("=" * 60)
    
    try:
        # 获取 5 分钟线数据
        df = ts.pro_bar(
            ts_code='603607.SH',
            start_date='20260206',
            end_date='20260206',
            freq='5min'
        )
        
        print(f"✅ 获取成功：{len(df)} 条记录")
        print(f"字段：{list(df.columns)}")
        print(f"\n前10条数据：")
        print(df.head(10))
        
        return df
        
    except Exception as e:
        print(f"❌ 失败：{e}")
        print("（注：分钟线数据可能需要更高积分等级）")
        return None

def test_multi_stocks():
    """测试多只股票"""
    print("\n" + "=" * 60)
    print("测试 4: 多只股票（测试速率和稳定性）")
    print("=" * 60)
    
    test_stocks = ['603607.SH', '601869.SH', '300666.SZ']
    
    try:
        for ts_code in test_stocks:
            df = ts.pro_bar(
                ts_code=ts_code,
                start_date='20260201',
                end_date='20260206',
                adj='qfq',
                freq='D'
            )
            print(f"✅ {ts_code}: {len(df)} 条记录")
        
        print("\n✅ 多股票测试通过")
        
    except Exception as e:
        print(f"❌ 失败：{e}")

def main():
    print("Tushare 接口测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试股票: 603607.SH（京华激光）")
    print(f"测试日期: 2026-02-01 到 2026-02-06")
    print()
    
    # 运行测试
    test_daily_bars()
    test_tech_factors()
    test_intraday_bars()
    test_multi_stocks()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n结论：")
    print("1. 如果日线和技术因子测试通过 → Tushare 可以作为历史快照重建的数据源")
    print("2. 如果分钟线测试失败 → 不影响，先用日线重建")
    print("3. 如果多股票测试通过 → 速率和稳定性满足需求")

if __name__ == "__main__":
    main()