#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键式股票分析工具

使用方法:
    python quick_analyze.py 300997                                    # 基本分析
    python quick_analyze.py 300997 --position 0.3                     # 带持仓分析
    python quick_analyze.py 300997 --position 0.3 --entry-price 24.5  # 完整参数
    python quick_analyze.py 300997 --mode realtime                    # 指定模式
    python quick_analyze.py 000001                                    # 主板股票（6位代码）
    python quick_analyze.py 000001.SZ                                 # 深市股票（带后缀）
"""

import argparse
import sys
from pathlib import Path
from tools.stock_analyzer import UnifiedStockAnalyzer


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='一键式股票分析工具 - 三层数据融合',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 300997                                    # 基本分析
  %(prog)s 300997 --position 0.3                     # 带持仓分析
  %(prog)s 300997 --position 0.3 --entry-price 24.5  # 完整参数
  %(prog)s 000001 --mode realtime                    # 指定模式
        """
    )
    
    parser.add_argument(
        'stock_code',
        help='股票代码（如：300997, 000001, 600000）'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['auto', 'realtime', 'historical'],
        default='auto',
        help='分析模式（默认：auto自动判断）'
    )
    
    parser.add_argument(
        '--position', '-p',
        type=float,
        default=0.0,
        help='当前持仓比例 0-1（如：0.3表示30%%）'
    )
    
    parser.add_argument(
        '--entry-price', '-e',
        type=float,
        help='建仓价格（配合--position使用）'
    )
    
    parser.add_argument(
        '--output', '-o',
        choices=['json', 'txt', 'both'],
        default='both',
        help='输出格式（默认：both）'
    )
    
    parser.add_argument(
        '--no-output',
        action='store_true',
        help='只显示分析结果，不保存文件'
    )
    
    return parser.parse_args()


def validate_args(args):
    """验证参数"""
    # 股票代码格式验证
    code = args.stock_code.strip()
    
    # 允许的格式：300997, 000001.SZ, 600000.SH
    if '.' in code:
        parts = code.split('.')
        if len(parts) != 2:
            print(f"❌ 错误：股票代码格式错误 '{code}'")
            print("   正确格式：300997 或 000001.SZ")
            return False
    else:
        # 纯数字，6位
        if not code.isdigit() or len(code) != 6:
            print(f"❌ 错误：股票代码必须是6位数字 '{code}'")
            return False
    
    # 持仓比例验证
    if not 0 <= args.position <= 1:
        print(f"❌ 错误：持仓比例必须在0-1之间（当前：{args.position}）")
        return False
    
    # 建仓价格验证
    if args.entry_price is not None and args.entry_price <= 0:
        print(f"❌ 错误：建仓价格必须大于0（当前：{args.entry_price}）")
        return False
    
    # 关联验证
    if args.position > 0 and args.entry_price is None:
        print("⚠️  警告：有持仓但未提供建仓价格，止盈止损功能将无法使用")
    
    return True


def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 验证参数
    if not validate_args(args):
        sys.exit(1)
    
    # 显示参数摘要
    print("="*80)
    print(f"🚀 一键式股票分析工具")
    print("="*80)
    print(f"股票代码: {args.stock_code}")
    print(f"分析模式: {args.mode}")
    print(f"当前持仓: {args.position:.0%}")
    if args.entry_price:
        print(f"建仓价格: {args.entry_price:.2f}元")
    print(f"输出格式: {args.output}")
    print("="*80)
    print()
    
    try:
        # 创建分析器
        analyzer = UnifiedStockAnalyzer()
        
        # 执行分析
        if args.no_output:
            output_format = 'none'
        else:
            output_format = args.output
        
        result = analyzer.analyze(
            stock_code=args.stock_code,
            mode=args.mode,
            position=args.position,
            entry_price=args.entry_price,
            output_format=output_format
        )
        
        # 显示结果摘要
        print()
        print("="*80)
        if result['success']:
            print("✅ 分析完成！")
            
            # 提取关键信息
            if 'layer1_realtime' in result:
                # 三层数据融合模式
                realtime = result['layer1_realtime']
                intraday = result['layer2_intraday']
                historical = result['layer3_historical']
                decision = result['integrated_decision']
                
                print(f"\n📊 实时快照:")
                print(f"  价格: {realtime.get('price', 0):.2f}元")
                print(f"  涨跌: {realtime.get('pct_change', 0):+.2f}%")
                print(f"  买卖压力: {realtime.get('bid_ask_pressure', 0):.2f}")
                
                if historical:
                    print(f"\n📈 历史数据:")
                    trap_risk = historical.get('trap_detection', {}).get('comprehensive_risk_score', 0)
                    print(f"  诱多风险: {trap_risk:.2f}")
                
                if decision:
                    print(f"\n🎯 智能决策:")
                    print(f"  决策: {decision['decision']}")
                    print(f"  置信度: {decision['confidence']:.0%}")
                    print(f"  理由: {decision['reason']}")
                    
            elif 'decision' in result:
                # 兼容旧版格式
                decision = result['decision']
                print(f"\n🎯 交易决策:")
                print(f"  动作: {decision.get('action', 'N/A')}")
                print(f"  置信度: {decision.get('confidence', 0):.0%}")
                print(f"  理由: {decision.get('reason', 'N/A')}")
            
            # 显示文件保存位置
            if not args.no_output and 'output_file' in result:
                output_file = result['output_file']
                if output_file:
                    print(f"\n📁 结果已保存:")
                    print(f"  {output_file}")
            
        else:
            print(f"❌ 分析失败: {result.get('error', '未知错误')}")
            sys.exit(1)
        
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()