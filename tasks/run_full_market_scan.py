#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场三漏斗扫描启动脚本

Usage:
    python tasks/run_full_market_scan.py --mode premarket
    python tasks/run_full_market_scan.py --mode intraday
    python tasks/run_full_market_scan.py --mode postmarket
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.full_market_scanner import FullMarketScanner
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='全市场三漏斗扫描系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  盘前扫描（9:00前）:
    python tasks/run_full_market_scan.py --mode premarket
  
  盘中扫描（交易时间）:
    python tasks/run_full_market_scan.py --mode intraday
  
  盘后复盘（15:00后）:
    python tasks/run_full_market_scan.py --mode postmarket

输出文件：
  data/scan_results/YYYY-MM-DD_{mode}.json
        """
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='premarket',
        choices=['premarket', 'intraday', 'postmarket'],
        help='扫描模式（默认: premarket）'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/market_scan_config.json',
        help='配置文件路径'
    )
    
    args = parser.parse_args()
    
    # 打印启动信息
    print("\n" + "=" * 80)
    print("🚀 全市场三漏斗扫描系统启动")
    print("=" * 80)
    print(f"📅 扫描模式: {args.mode}")
    print(f"⚙️  配置文件: {args.config}")
    print("=" * 80 + "\n")
    
    try:
        # 初始化扫描器
        scanner = FullMarketScanner(config_path=args.config)
        
        # 执行扫描（带风险管理）
        results = scanner.scan_with_risk_management(mode=args.mode)
        
        # 打印详细摘要
        print("\n" + "=" * 80)
        print("📊 扫描结果详情")
        print("=" * 80)
        
        # 打印风险信息
        print(f"\n📈 系统置信度: {results['confidence']*100:.1f}%")
        print(f"💰 今日建议最大总仓位: {results['position_limit']*100:.1f}%")
        print(f"🎯 风控原因: {results['risk_reason']}")
        
        if results['risk_warnings']:
            print("\n⚠️  风控警告:")
            for warning in results['risk_warnings']:
                print(f"   {warning}")
        
        print("\n" + "-" * 80)
        
        # 处理不同模式
        if results['mode'] == 'DEGRADED_LEVEL1_ONLY':
            print("⚠️  当前为降级模式：仅 Level 1 技术面筛选可用")
            print("   原因：资金流数据不可用")
            print("\n📋 技术面候选池（TOP50）:")
            print("-" * 80)
            
            if results.get('level1_candidates'):
                from logic.code_converter import CodeConverter
                # 需要获取股票详情来展示
                batch_size = 1000
                level1_data = {}
                
                try:
                    from xtquant import xtdata
                    tick_data = xtdata.get_full_tick(results['level1_candidates'])
                    level1_data = tick_data if tick_data else {}
                except Exception as e:
                    logger.warning(f"⚠️  获取 Level 1 详细信息失败: {e}")
                
                for idx, code in enumerate(results['level1_candidates'], 1):
                    tick = level1_data.get(code, {})
                    if tick:
                        last_price = tick.get('lastPrice', 0)
                        last_close = tick.get('lastClose', 0)
                        amount = tick.get('amount', 0)
                        if last_close > 0:
                            pct_chg = (last_price - last_close) / last_close * 100
                        else:
                            pct_chg = 0
                        
                        print(f"{idx:2d}. {CodeConverter.to_akshare(code)} - "
                              f"涨跌幅: {pct_chg:+.2f}% - "
                              f"成交额: {amount/1e8:.2f}亿")
                    else:
                        print(f"{idx:2d}. {CodeConverter.to_akshare(code)} - "
                              f"数据缺失")
            else:
                print("   (无)")
        else:
            # 正常模式：显示完整结果
            
            # 机会池
            print(f"\n✅ 机会池 ({len(results['opportunities'])} 只):")
            print("-" * 80)
            if results['opportunities']:
                for idx, item in enumerate(results['opportunities'][:10], 1):
                    print(f"{idx:2d}. {item['code_6digit']} - "
                          f"风险评分: {item['risk_score']:.2f} - "
                          f"类型: {item['capital_type']} - "
                          f"主力流入: {item['flow_data'].get('main_net_inflow', 0)/1e6:.1f}百万")
            else:
                print("   (无)")
            
            # 观察池
            print(f"\n⚠️  观察池 ({len(results['watchlist'])} 只):")
            print("-" * 80)
            if results['watchlist']:
                for idx, item in enumerate(results['watchlist'][:5], 1):
                    print(f"{idx:2d}. {item['code_6digit']} - "
                          f"风险评分: {item['risk_score']:.2f} - "
                          f"类型: {item['capital_type']} - "
                          f"诱多信号: {len(item['trap_signals'])}个")
            else:
                print("   (无)")
            
            # 黑名单
            print(f"\n❌ 黑名单 ({len(results['blacklist'])} 只):")
            print("-" * 80)
            if results['blacklist']:
                for idx, item in enumerate(results['blacklist'][:5], 1):
                    print(f"{idx:2d}. {item['code_6digit']} - "
                          f"风险评分: {item['risk_score']:.2f} - "
                          f"诱多信号: {', '.join(item['trap_signals'][:2])}")
            else:
                print("   (无)")
        
        print("\n" + "=" * 80)
        print("✅ 扫描完成！结果已保存到 data/scan_results/ 目录")
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断扫描")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 扫描失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
