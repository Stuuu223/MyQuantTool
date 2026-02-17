# -*- coding: utf-8 -*-
"""
检查QMT本地Tick数据

目标：
1. 检查本地有哪些股票的Tick数据
2. 检查数据的时间跨度
3. 选择有代表性的股票进行测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    print("❌ xtquant未安装，无法检查QMT数据")
    sys.exit(1)

def check_local_data():
    """检查本地Tick数据"""
    print("=" * 60)
    print("🔍 检查QMT本地Tick数据")
    print("=" * 60)
    
    # 1. 检查全市场股票列表
    print("\n📋 步骤1: 获取全市场股票列表...")
    try:
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
        print(f"✅ 全市场股票数量: {len(stock_list)}只")
        
        # 显示前10只股票
        print(f"   前10只股票: {stock_list[:10]}")
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return
    
    # 2. 检查每只股票是否有本地数据
    print("\n📋 步骤2: 检查本地数据覆盖...")
    
    # 检查前50只股票的数据
    checked_stocks = stock_list[:50]
    stocks_with_data = []
    
    for stock in checked_stocks:
        try:
            # 尝试获取最近1天的数据
            end_time = '20260216 15:00:00'
            start_time = '20260201 09:30:00'
            
            # 获取Tick数据
            data = xtdata.get_local_data(
                stock_list=[stock],
                period='tick',
                start_time=start_time,
                end_time=end_time
            )
            
            if data and stock in data and len(data[stock]) > 0:
                stocks_with_data.append(stock)
                print(f"   ✅ {stock}: 有数据 ({len(data[stock])}条)")
            else:
                print(f"   ❌ {stock}: 无数据")
        except Exception as e:
            print(f"   ⚠️  {stock}: 检查失败 ({e})")
    
    print(f"\n📊 数据覆盖情况: {len(stocks_with_data)}/{len(checked_stocks)}")
    
    # 3. 检查数据时间跨度
    if stocks_with_data:
        print("\n📋 步骤3: 检查数据时间跨度...")
        
        # 选择第一只有数据的股票
        sample_stock = stocks_with_data[0]
        
        # 尝试获取不同时间段的数据
        time_ranges = [
            ('2026-01-01', '2026-02-16'),
            ('2025-12-01', '2026-02-16'),
            ('2025-11-01', '2026-02-16'),
        ]
        
        for start_date, end_date in time_ranges:
            try:
                data = xtdata.get_local_data(
                    stock_list=[sample_stock],
                    period='tick',
                    start_time=f'{start_date} 09:30:00',
                    end_time=f'{end_date} 15:00:00'
                )
                
                if data and sample_stock in data and len(data[sample_stock]) > 0:
                    tick_count = len(data[sample_stock])
                    print(f"   ✅ {start_date} ~ {end_date}: {tick_count}条Tick数据")
                else:
                    print(f"   ❌ {start_date} ~ {end_date}: 无数据")
            except Exception as e:
                print(f"   ⚠️  {start_date} ~ {end_date}: 检查失败 ({e})")
    
    # 4. 检查热门股（300997欢乐家、603697有友食品等）
    print("\n📋 步骤4: 检查热门股数据...")
    
    hot_stocks = [
        '300997.SZ',  # 欢乐家
        '603697.SH',  # 有友食品
        '000001.SZ',  # 平安银行
        '600519.SH',  # 贵州茅台
        '300750.SZ',  # 宁德时代
    ]
    
    for stock in hot_stocks:
        try:
            # 获取最近30天的数据
            end_time = '20260216 15:00:00'
            start_time = '20260117 09:30:00'
            
            data = xtdata.get_local_data(
                stock_list=[stock],
                period='tick',
                start_time=start_time,
                end_time=end_time
            )
            
            if data and stock in data and len(data[stock]) > 0:
                tick_count = len(data[stock])
                print(f"   ✅ {stock}: {tick_count}条Tick数据")
                
                # 显示第一条和最后一条数据的时间
                first_tick = data[stock].iloc[0]
                last_tick = data[stock].iloc[-1]
                print(f"      时间范围: {first_tick['time']} ~ {last_tick['time']}")
            else:
                print(f"   ❌ {stock}: 无数据")
        except Exception as e:
            print(f"   ⚠️  {stock}: 检查失败 ({e})")
    
    print("\n" + "=" * 60)
    print("✅ 检查完成")
    print("=" * 60)

if __name__ == '__main__':
    check_local_data()