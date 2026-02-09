#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 QMT 数据权限"""

import sys
sys.path.append('E:/MyQuantTool')

from xtquant import xtdata

print("=" * 60)
print("检查 QMT 数据权限")
print("=" * 60)

# 检查行情服务信息
try:
    data_dir = xtdata.get_data_dir()
    print(f"📁 数据目录: {data_dir}")
    
    # 检查订阅信息
    print("\n📊 尝试获取订阅信息...")
    
    # 测试订阅接口（如果有的话）
    try:
        subscribe_info = xtdata.get_subscribe_list()
        print(f"✅ 订阅列表: {subscribe_info}")
    except Exception as e:
        print(f"ℹ️ 无法获取订阅列表: {e}")
    
    # 测试行情等级
    try:
        level_info = xtdata.get_full_tick(['600519.SH'])
        if level_info:
            print(f"✅ Level2 行情可用")
        else:
            print(f"ℹ️ 只有 Level1 行情")
    except Exception as e:
        print(f"ℹ️ 行情等级检查失败: {e}")
    
    # 检查分钟线数据是否支持
    print("\n📈 测试分钟线下载...")
    try:
        xtdata.download_history_data(
            stock_code='600519.SH',
            period='1m',
            start_time='20240101',
            end_time='20240105'
        )
        print("✅ 分钟线下载成功")
        
        # 验证
        data = xtdata.get_local_data(
            field_list=['time', 'close'],
            stock_list=['600519.SH'],
            period='1m',
            count=-1
        )
        if data and '600519.SH' in data:
            print(f"✅ 读取到 {len(data['600519.SH'])} 条分钟数据")
        else:
            print("❌ 读取分钟数据失败")
    except Exception as e:
        print(f"❌ 分钟线下载失败: {e}")
        
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)