#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试：获取涨幅3-5%的股票，打印详细数据
"""

import sys
import os
import logging

# 先设置日志级别为DEBUG，再导入模块
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xtquant import xtdata
from logic.full_market_scanner import FullMarketScanner
import json

def main():
    print("=" * 80)
    print("测试：获取涨幅3-5%的股票（详细DEBUG版本）")
    print("=" * 80)
    
    # 初始化扫描器
    scanner = FullMarketScanner()
    
    # 获取全市场股票
    all_stocks = scanner.all_stocks
    print(f"\n全市场股票总数: {len(all_stocks)} 只")
    
    # 分批获取tick数据
    batch_size = 1000
    candidates_3_5 = []  # 涨幅3-5%的股票
    debug_count = 0  # 只对前5只打印DEBUG
    max_debug = 5
    
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"\n批次 {batch_num}: 获取 {len(batch)} 只股票...")
        
        try:
            tick_data = xtdata.get_full_tick(batch)
            
            for code in batch:
                tick = tick_data.get(code, {})
                if not tick or not isinstance(tick, dict):
                    continue
                
                # 获取价格数据
                last_close = tick.get('lastClose', 0)
                last_price = tick.get('lastPrice', 0)
                amount = tick.get('amount', 0)
                
                # 计算涨跌幅
                if last_close > 0:
                    pct_chg = (last_price - last_close) / last_close * 100
                else:
                    pct_chg = 0
                
                # 筛选：涨幅3-5%
                if 3.0 <= pct_chg <= 5.0:
                    # 获取成交量
                    volume = (
                        tick.get('totalVolume') or 
                        tick.get('volume') or 
                        tick.get('total_volume') or 
                        tick.get('turnoverVolume') or 
                        tick.get('turnover_volume') or 
                        0
                    )
                    if volume == 0 and amount > 0 and last_price > 0:
                        volume = amount / last_price
                    
                    # 只对前5只打印DEBUG日志
                    if debug_count < max_debug:
                        print(f"\n{'='*80}")
                        print(f"DEBUG #{debug_count+1}: {code}")
                        print(f"{'='*80}")
                    
                    # 计算量比
                    volume_ratio = scanner._check_volume_ratio(code, volume, tick)
                    volume_ratio_str = f"{volume_ratio:.2f}" if volume_ratio is not None else "数据缺失"
                    
                    # 获取市值
                    market_cap = scanner._get_market_cap(code, tick)
                    market_cap_str = f"{market_cap/1e8:.2f}亿" if market_cap > 0 else "0"
                    
                    # 获取量比阈值
                    if market_cap == 0:
                        volume_ratio_threshold = 1.5
                    else:
                        volume_ratio_threshold = scanner.get_volume_ratio_threshold(market_cap)
                    
                    # 判断是否通过Level1
                    level1_passed = scanner._check_level1_criteria(code, tick)
                    
                    # 只对前5只打印详细结果
                    if debug_count < max_debug:
                        print(f"\n结果汇总:")
                        print(f"  涨跌幅={pct_chg:.2f}%")
                        print(f"  成交额={amount/1e8:.2f}亿")
                        print(f"  量比={volume_ratio_str}")
                        print(f"  市值={market_cap_str}")
                        print(f"  量比阈值={volume_ratio_threshold:.2f}")
                        print(f"  Level1通过={'✅' if level1_passed else '❌'}")
                        debug_count += 1
                    
                    candidates_3_5.append({
                        'code': code,
                        'name': tick.get('stockName', ''),
                        'pct_chg': pct_chg,
                        'amount': amount,
                        'volume_ratio': volume_ratio,
                        'volume_ratio_str': volume_ratio_str,
                        'market_cap': market_cap,
                        'market_cap_str': market_cap_str,
                        'volume_ratio_threshold': volume_ratio_threshold,
                        'level1_passed': level1_passed
                    })
                    
        except Exception as e:
            print(f"  ❌ 批次 {batch_num} 获取失败: {e}")
            continue
        
        # 只对前5只进行DEBUG，找到问题即可
        if debug_count >= max_debug:
            print(f"\n已收集{max_debug}只样本的DEBUG信息，停止扫描")
            break
    
    # 打印结果
    print("\n" + "=" * 80)
    print(f"✅ 找到涨幅3-5%的股票（部分）: {len(candidates_3_5)} 只")
    print("=" * 80)
    
    # 统计
    passed_count = sum(1 for c in candidates_3_5 if c['level1_passed'])
    failed_count = len(candidates_3_5) - passed_count
    
    print(f"\n统计:")
    print(f"  通过Level1: {passed_count} 只")
    print(f"  未通过Level1: {failed_count} 只")
    
    # 保存到文件
    output_file = "data/level1_debug_3_5_pct_debug.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(candidates_3_5, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 详细数据已保存到: {output_file}")

if __name__ == "__main__":
    main()