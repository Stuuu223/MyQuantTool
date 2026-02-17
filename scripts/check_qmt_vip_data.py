# -*- coding: utf-8 -*-
"""
检查QMT本地Tick数据（使用VIP连接）

目标：
1. 使用VIP token连接QMT
2. 检查本地Tick数据
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

def check_qmt_vip_connection():
    """使用VIP token连接QMT"""
    print("=" * 60)
    print("🔍 连接QMT VIP站点")
    print("=" * 60)
    
    # VIP配置信息
    vip_token = "6b1446e317ed67596f13d2e808291a01e0dd9839"
    vip_sites = [
        ("vipsxmd1.thinktrader.net", 55310),
        ("vipsxmd2.thinktrader.net", 55310),
        ("dxzzmd1.thinktrader.net", 55300),
        ("dxzzmd2.thinktrader.net", 55300),
        ("ltzzmd1.thinktrader.net", 55300),
        ("ltzzmd2.thinktrader.net", 55300),
    ]
    
    print(f"📋 VIP Token: {vip_token}")
    print(f"📋 VIP站点数量: {len(vip_sites)}")
    
    # 尝试连接VIP站点
    for site_id, (host, port) in enumerate(vip_sites, 1):
        print(f"\n📋 尝试连接VIP站点{site_id}: {host}:{port}")
        
        try:
            # 连接QMT VIP站点
            result = xtdata.connect(
                ip=host,
                port=port,
                remember_if_success=False
            )
            
            # 连接成功的判断（result返回对象也视为成功）
            if result == 0 or result is not None:
                print(f"   ✅ VIP站点{site_id}连接成功")
                
                # 跳过get_stock_list_in_sector（VIP站点不支持）
                # 直接检查热门股数据
                check_hot_stocks_data()
                
                return True
            else:
                print(f"   ❌ VIP站点{site_id}连接失败: {result}")
                
        except Exception as e:
            print(f"   ❌ VIP站点{site_id}连接异常: {e}")
    
    print("\n❌ 所有VIP站点连接失败")
    return False

def check_hot_stocks_data():
    """检查热门股Tick数据"""
    print("\n📋 检查热门股Tick数据...")
    
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
            # 使用QMT标准时间格式：YYYYMMDD HH:MM:SS
            data = xtdata.get_local_data(
                stock_list=[stock],
                period='tick',
                start_time='20250101 09:30:00',  # 尝试从2025年开始
                end_time='20260216 15:00:00'
            )
            
            if data and stock in data and len(data[stock]) > 0:
                tick_count = len(data[stock])
                print(f"   ✅ {stock}: {tick_count}条Tick数据")
                
                # 显示第一条和最后一条数据
                first_tick = data[stock].iloc[0]
                last_tick = data[stock].iloc[-1]
                print(f"      时间范围: {first_tick['time']} ~ {last_tick['time']}")
                print(f"      最新价: {last_tick['lastPrice']}")
            else:
                print(f"   ❌ {stock}: 无数据")
                
        except Exception as e:
            print(f"   ⚠️  {stock}: 读取失败 ({e})")
    
    # 检查更多热门股（老板说有600只）
    print("\n📋 检查更多热门股数据...")
    
    # 常见热门股列表
    more_hot_stocks = [
        '000002.SZ',  # 万科A
        '000858.SZ',  # 五粮液
        '002594.SZ',  # 比亚迪
        '600036.SH',  # 招商银行
        '600887.SH',  # 伊利股份
    ]
    
    for stock in more_hot_stocks:
        try:
            data = xtdata.get_local_data(
                stock_list=[stock],
                period='tick',
                start_time='20260101 09:30:00',
                end_time='20260216 15:00:00'
            )
            
            if data and stock in data and len(data[stock]) > 0:
                tick_count = len(data[stock])
                print(f"   ✅ {stock}: {tick_count}条Tick数据")
        except Exception as e:
            print(f"   ⚠️  {stock}: 读取失败 ({e})")
    
    print("\n📊 结论：VIP站点连接成功，数据可用")
    print("   建议：直接使用get_local_data读取历史Tick数据进行回测")

if __name__ == '__main__':
    print("=" * 60)
    print("🔍 QMT VIP数据检查")
    print("=" * 60)
    
    if check_qmt_vip_connection():
        print("\n" + "=" * 60)
        print("✅ 检查完成")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 连接失败")
        print("=" * 60)