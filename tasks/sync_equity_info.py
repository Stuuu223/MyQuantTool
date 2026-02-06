#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘前同步全A股股本信息
功能：
1. 从AkShare获取全A股基础信息
2. 提取总股本、流通股本、昨收价
3. 计算流通市值、总市值
4. 保存到本地JSON供Level1使用
"""

import json
import sys
import os
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    
    # 禁用代理（强制直连）
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    # 配置 requests session 禁用代理
    import requests
    requests.Session.proxies = {
        'http': None,
        'https': None,
    }
    
    print("✅ 已禁用代理，使用直连")
    
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ 警告: AkShare未安装，请运行: pip install akshare")


def sync_equity_info():
    """
    同步全A股股本信息到本地JSON
    
    Returns:
        dict: 股本信息字典 {code: {name, total_shares, float_shares, ...}}
    """
    if not AKSHARE_AVAILABLE:
        print("❌ AkShare不可用，无法同步股本信息")
        return {}
    
    print("=" * 80)
    print("📊 盘前同步全A股股本信息")
    print("=" * 80)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 获取A股实时行情（包含股本信息）
        print("📥 正在获取全A股基础信息...")
        print("⏱️  已启用速率限制，避免被封禁...")
        print()
        
        stock_info = ak.stock_zh_a_spot_em()
        
        print(f"✅ 获取成功！共 {len(stock_info)} 只股票")
        print()
        
        # 速率限制：处理完成后等待2秒
        time.sleep(2)
        
        # 提取需要的字段
        print("🔄 正在处理数据...")
        equity_data = {}
        
        for idx, row in stock_info.iterrows():
            code = row['代码']
            
            # 转换为股和元（原始数据单位：股本为"亿股"，市值为"亿元"）
            total_shares = float(row['总股本']) * 100000000 if row['总股本'] else 0
            float_shares = float(row['流通股']) * 100000000 if row['流通股'] else 0
            last_close = float(row['最新价']) if row['最新价'] else 0
            
            # 计算市值（元）
            total_market_cap = total_shares * last_close
            float_market_cap = float_shares * last_close
            
            equity_data[code] = {
                'name': row['名称'],
                'total_shares': total_shares,  # 总股本（股）
                'float_shares': float_shares,  # 流通股本（股）
                'last_close': last_close,  # 昨收价（元）
                'total_market_cap': total_market_cap,  # 总市值（元）
                'float_market_cap': float_market_cap,  # 流通市值（元）
                'total_market_cap_yi': total_market_cap / 1_000_000_000,  # 总市值（亿元）
                'float_market_cap_yi': float_market_cap / 1_000_000_000,  # 流通市值（亿元）
                'sync_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 每1000只打印一次进度
            if (idx + 1) % 1000 == 0:
                print(f"   已处理: {idx + 1}/{len(stock_info)}")
        
        print(f"✅ 处理完成！共 {len(equity_data)} 只股票")
        print()
        
        # 保存到JSON
        output_file = 'data/equity_info.json'
        print(f"💾 正在保存到: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(equity_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 保存成功！")
        print()
        
        # 打印统计信息
        print("📊 统计信息:")
        print(f"   总股票数: {len(equity_data)}")
        
        # 按市值统计
        small_cap = [c for c in equity_data.values() if c['float_market_cap_yi'] < 80]
        mid_cap = [c for c in equity_data.values() if 80 <= c['float_market_cap_yi'] < 200]
        large_cap = [c for c in equity_data.values() if c['float_market_cap_yi'] >= 200]
        
        print(f"   小盘股 (<80亿): {len(small_cap)} 只")
        print(f"   中盘股 (80-200亿): {len(mid_cap)} 只")
        print(f"   大盘股 (≥200亿): {len(large_cap)} 只")
        print()
        
        print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return equity_data
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        import traceback
        print(traceback.format_exc())
        return {}


def load_equity_info():
    """
    加载本地股本信息
    
    Returns:
        dict: 股本信息字典
    """
    try:
        with open('data/equity_info.json', 'r', encoding='utf-8') as f:
            equity_info = json.load(f)
        print(f"✅ 加载股本信息: {len(equity_info)} 只股票")
        return equity_info
    except Exception as e:
        print(f"⚠️ 加载股本信息失败: {e}")
        return {}


if __name__ == '__main__':
    print()
    sync_equity_info()
    print()