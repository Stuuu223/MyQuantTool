#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从AkShare获取全市场股本数据

严格按照速率要求：
- 使用ak.stock_zh_a_spot_em()一次性获取全市场数据
- 应用RateLimiter控制速率
- 保存到data/equity_info_akshare.json

使用方法：
    python tools/fetch_equity_from_akshare.py

作者：量化CTO
日期：2026-02-13
版本：V1.0
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import akshare as ak
    from logic.core.rate_limiter import RateLimiter
    from logic.utils.logger import get_logger
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保使用虚拟环境运行: venv_qmt\\Scripts\\python.exe")
    sys.exit(1)

logger = get_logger(__name__)

# 禁用代理（防止ProxyError）
import os
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# Monkey patch requests以禁用代理
import requests
original_request = requests.Session.request

def no_proxy_request(self, method, url, *args, **kwargs):
    # 移除任何代理设置
    kwargs.pop('proxies', None)
    kwargs['proxies'] = {'http': None, 'https': None}
    return original_request(self, method, url, *args, **kwargs)

requests.Session.request = no_proxy_request


def fetch_equity_from_akshare():
    """
    从AkShare获取全市场股本数据
    
    AkShare API: ak.stock_zh_a_spot_em()
    - 一次性获取全市场数据
    - 包含：总市值、流通市值、市盈率、市净率、换手率
    
    速率限制：
    - AkShare推荐间隔：1-2秒（实时行情）
    - 项目配置：60次/分钟，最小间隔1秒
    
    耗时：< 3秒（单次调用）
    """
    
    # 初始化速率限制器（严格遵守文档要求）
    limiter = RateLimiter(
        max_requests_per_minute=60,   # AkShare: 60次/分钟
        max_requests_per_hour=2000,   # AkShare: 2000次/小时
        min_request_interval=1.0,     # 最小间隔1秒
        enable_logging=True
    )
    
    print("=" * 80)
    print("🚀 开始从AkShare获取全市场股本数据")
    print("=" * 80)
    
    # 应用速率限制
    limiter.wait_if_needed()
    
    start_time = time.time()
    
    try:
        print("\n📡 调用AkShare API: ak.stock_zh_a_spot_em()...")
        
        # 一次性获取全市场数据（无需循环）
        df = ak.stock_zh_a_spot_em()
        
        elapsed = time.time() - start_time
        print(f"✅ API调用成功！耗时: {elapsed:.2f}秒")
        print(f"📊 获取到 {len(df)} 只股票的数据")
        
        # 记录请求
        limiter.record_request()
        
        # 检查必要字段
        required_fields = ['代码', '总市值', '流通市值', '市盈率-动态', '市净率', '换手率']
        missing_fields = [f for f in required_fields if f not in df.columns]
        
        if missing_fields:
            print(f"⚠️ 警告：缺少字段: {missing_fields}")
        else:
            print(f"✅ 所有必要字段都存在")
        
        # 构造股本数据结构
        equity_data = {
            'latest_update': datetime.now().strftime('%Y%m%d'),
            'retention_days': 30,
            'data': {
                datetime.now().strftime('%Y%m%d'): {}
            }
        }
        
        # 填充数据
        for _, row in df.iterrows():
            code = row['代码']
            equity_data['data'][datetime.now().strftime('%Y%m%d')][code] = {
                'float_mv': row['流通市值'],  # 万元
                'total_mv': row['总市值'],      # 万元
                'close': row['最新价'],
                'turnover_rate': row['换手率'],
                'pe': row['市盈率-动态'],
                'pb': row['市净率']
            }
        
        # 保存到文件
        output_path = project_root / 'data' / 'equity_info_akshare.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(equity_data, f, indent=2, ensure_ascii=False)
        
        file_size = output_path.stat().st_size / 1024  # KB
        print(f"\n💾 数据已保存到: {output_path}")
        print(f"📁 文件大小: {file_size:.1f} KB")
        
        # 数据质量检查
        print("\n📋 数据质量检查:")
        print(f"  ✅ 股票数量: {len(df)}")
        print(f"  ✅ 日期: {datetime.now().strftime('%Y-%m-%d')}")
        
        # 检查NaN数量
        pe_nan = df['市盈率-动态'].isna().sum()
        pb_nan = df['市净率'].isna().sum()
        
        print(f"  📊 PE NaN数量: {pe_nan} ({pe_nan/len(df)*100:.1f}%)")
        print(f"  📊 PB NaN数量: {pb_nan} ({pb_nan/len(df)*100:.1f}%)")
        
        if pe_nan / len(df) < 0.1 and pb_nan / len(df) < 0.1:
            print("  ✅ 数据质量良好（NaN < 10%）")
        else:
            print("  ⚠️ 数据质量一般（NaN ≥ 10%）")
        
        # 显示前5只股票
        print("\n📝 前5只股票示例:")
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            print(f"  {row['代码']} {row['名称']}: 市值={row['总市值']/10000:.1f}亿, PE={row['市盈率-动态']}")
        
        print("\n" + "=" * 80)
        print("✅ 股本数据获取完成！")
        print("=" * 80)
        
        return equity_data
        
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        logger.error(f"获取股本数据失败: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    result = fetch_equity_from_akshare()
    
    if result:
        print("\n🎉 成功！股本数据已更新。")
        print("现在可以使用 data/equity_info_akshare.json 进行筛选。")
    else:
        print("\n❌ 失败！请检查网络连接和AkShare API可用性。")


if __name__ == "__main__":
    main()