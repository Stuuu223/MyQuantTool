#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【Phase 6.1.5】时间机器回演脚本
==============================
对指定历史日期执行完整两段式筛选，验证Top 10名单。

功能：
1. 输入参数：日期（YYYYMMDD格式）
2. 自动执行两段式筛选：
   - 第一段：market_filter（5000→200）
   - 第二段：tick_refiner（200→Top 10）
3. 输出完整回演日志
4. 特别验证志特新材(300986)是否在Top 10

使用示例:
    python tasks/run_time_machine_backtest.py --date 20251231
    python tasks/run_time_machine_backtest.py --date 20260223 --output-json

Author: AI开发专家
Date: 2026-02-23
Version: 1.0.0
"""

import os
import sys
import json
import time
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# 导入logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

# 导入筛选模块
try:
    from logic.analyzers.market_filter import MarketFilter, FilterResult
    MARKET_FILTER_AVAILABLE = True
except ImportError as e:
    MARKET_FILTER_AVAILABLE = False
    logger.error(f"[TimeMachine] 导入MarketFilter失败: {e}")

try:
    from logic.analyzers.tick_refiner import TickRefiner, RefinerResult
    TICK_REFINER_AVAILABLE = True
except ImportError as e:
    TICK_REFINER_AVAILABLE = False
    logger.error(f"[TimeMachine] 导入TickRefiner失败: {e}")


@dataclass
class TimeMachineResult:
    """时间机器回演结果"""
    trade_date: str
    phase_6_1_3_result: Optional[FilterResult] = None
    phase_6_1_4_result: Optional[RefinerResult] = None
    total_duration_ms: float = 0.0
    success: bool = False
    error_message: str = ""
    
    # 志特新材验证结果
    target_stock_in_top10: bool = False
    target_stock_rank: Optional[int] = None
    target_stock_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            'trade_date': self.trade_date,
            'total_duration_ms': f"{self.total_duration_ms:.2f}",
            'total_duration_sec': f"{self.total_duration_ms/1000:.2f}",
            'success': self.success,
            'error_message': self.error_message,
            'phase_6_1_3': self.phase_6_1_3_result.to_dict() if self.phase_6_1_3_result else None,
            'phase_6_1_4': self.phase_6_1_4_result.to_dict() if self.phase_6_1_4_result else None,
            'target_stock_validation': {
                'code': '300986',
                'name': '志特新材',
                'in_top10': self.target_stock_in_top10,
                'rank': self.target_stock_rank,
                'data': self.target_stock_data
            }
        }


class TimeMachineBacktest:
    """
    时间机器回演器
    ==============
    对历史日期执行完整两段式筛选
    """
    
    # 目标股票配置
    TARGET_STOCK = '300986'  # 志特新材
    
    def __init__(self, token: str = None):
        """
        初始化时间机器
        
        Args:
            token: Tushare Pro Token（可选）
        """
        self.market_filter = None
        self.tick_refiner = None
        self.token = token
        
        self._init_components()
    
    def _init_components(self):
        """初始化各阶段组件"""
        # 初始化第一段：市场过滤器
        if MARKET_FILTER_AVAILABLE:
            try:
                self.market_filter = MarketFilter(token=self.token)
                logger.info("[TimeMachine] ✅ MarketFilter初始化成功")
            except Exception as e:
                logger.error(f"[TimeMachine] ❌ MarketFilter初始化失败: {e}")
        
        # 初始化第二段：Tick炼蛊器
        if TICK_REFINER_AVAILABLE:
            try:
                self.tick_refiner = TickRefiner(token=self.token)
                logger.info("[TimeMachine] ✅ TickRefiner初始化成功")
            except Exception as e:
                logger.error(f"[TimeMachine] ❌ TickRefiner初始化失败: {e}")
    
    def run_backtest(self, trade_date: str) -> TimeMachineResult:
        """
        执行完整回演
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
        
        Returns:
            TimeMachineResult: 回演结果
        """
        start_time = time.time()
        result = TimeMachineResult(trade_date=trade_date)
        
        print("\n" + "=" * 100)
        print("🕐 【Phase 6.1.5】时间机器回演启动")
        print("=" * 100)
        print(f"\n📅 回演日期: {trade_date}")
        print(f"🎯 目标股票: {self.TARGET_STOCK} (志特新材)")
        print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # ==================== 第一段：粗筛（5000→200）====================
            print("\n" + "-" * 100)
            print("📊 Phase 6.1.3: 市场粗筛（5000→200）")
            print("-" * 100)
            
            if not self.market_filter:
                raise RuntimeError("MarketFilter不可用，无法执行第一段筛选")
            
            phase_6_1_3_result = self.market_filter.filter_market(
                trade_date=trade_date,
                target_stocks=[self.TARGET_STOCK]
            )
            result.phase_6_1_3_result = phase_6_1_3_result
            
            # 打印第一段结果
            phase_6_1_3_result.print_summary()
            
            # 检查是否有足够股票进入第二阶段
            if len(phase_6_1_3_result.final_stocks) == 0:
                raise RuntimeError("第一段筛选后无股票，无法进入第二阶段")
            
            # ==================== 第二段：精筛（200→Top 10）====================
            print("\n" + "-" * 100)
            print("📊 Phase 6.1.4: Tick炼蛊（200→Top 10）")
            print("-" * 100)
            
            if not self.tick_refiner:
                raise RuntimeError("TickRefiner不可用，无法执行第二段筛选")
            
            # 转换股票格式
            stock_list_for_refiner = []
            for stock in phase_6_1_3_result.final_stocks:
                stock_list_for_refiner.append({
                    'code': stock.get('code', ''),
                    'name': stock.get('name', '')
                })
            
            phase_6_1_4_result = self.tick_refiner.refine(
                stock_list=stock_list_for_refiner,
                trade_date=trade_date,
                target_stock=self.TARGET_STOCK
            )
            result.phase_6_1_4_result = phase_6_1_4_result
            
            # 打印第二段结果
            phase_6_1_4_result.print_summary()
            
            # ==================== 验证志特新材 ====================
            print("\n" + "-" * 100)
            print("🔍 志特新材(300986)验证结果")
            print("-" * 100)
            
            target_detail = phase_6_1_4_result.target_stock_detail
            target_rank = phase_6_1_4_result.stats.target_stock_rank
            
            result.target_stock_rank = target_rank
            
            if target_detail:
                result.target_stock_in_top10 = target_rank <= 10 if target_rank else False
                result.target_stock_data = target_detail.to_dict()
                
                print(f"  ✅ 志特新材在结果列表中")
                print(f"  📊 最终排名: 第 {target_rank} 名")
                
                if result.target_stock_in_top10:
                    print(f"  🏆 志特新材成功进入Top 10！")
                else:
                    print(f"  ⚠️ 志特新材未进入Top 10（排名: {target_rank}）")
                
                print(f"  📈 V18得分: {target_detail.v18_score:.2f}")
                print(f"  📈 真实振幅: {target_detail.true_amplitude*100:.2f}%")
                print(f"  📈 ATR比率: {target_detail.true_atr_ratio:.2f}")
                print(f"  📈 早盘量比: {target_detail.volume_ratio:.2f}")
            else:
                result.target_stock_in_top10 = False
                print(f"  ❌ 志特新材不在结果中（可能在第一段被过滤）")
                
                # 检查第一段的目标股票路径
                if phase_6_1_3_result.target_stock_path:
                    for code, path in phase_6_1_3_result.target_stock_path.items():
                        if self.TARGET_STOCK in code:
                            print(f"  📋 第一阶段筛选路径:")
                            print(f"     状态: {'✅ 保留' if path['retained'] else '❌ 淘汰'}")
                            print(f"     层级: {path['layer']}")
                            print(f"     原因: {path['reason']}")
            
            result.success = True
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"[TimeMachine] 回演失败: {e}")
            traceback.print_exc()
        
        # 计算总耗时
        result.total_duration_ms = (time.time() - start_time) * 1000
        
        # 打印总结
        self._print_summary(result)
        
        return result
    
    def _print_summary(self, result: TimeMachineResult):
        """打印回演总结"""
        print("\n" + "=" * 100)
        print("🎯 时间机器回演总结")
        print("=" * 100)
        print(f"\n📅 回演日期: {result.trade_date}")
        print(f"⏱️  总耗时: {result.total_duration_ms:.2f} ms ({result.total_duration_ms/1000:.2f} s)")
        print(f"✅ 执行状态: {'成功' if result.success else '失败'}")
        
        if not result.success:
            print(f"❌ 错误信息: {result.error_message}")
            return
        
        # 第一段统计
        if result.phase_6_1_3_result:
            print(f"\n📊 第一段粗筛（5000→200）:")
            print(f"   输入: ~5000只")
            print(f"   输出: {len(result.phase_6_1_3_result.final_stocks)}只")
            print(f"   耗时: {result.phase_6_1_3_result.total_duration_ms:.2f} ms")
        
        # 第二段统计
        if result.phase_6_1_4_result:
            print(f"\n📊 第二段精筛（200→Top 10）:")
            print(f"   输入: {result.phase_6_1_4_result.stats.input_count}只")
            print(f"   成功处理: {result.phase_6_1_4_result.stats.processed_count}只")
            print(f"   输出Top 10")
            print(f"   耗时: {result.phase_6_1_4_result.stats.duration_ms:.2f} ms")
            
            print(f"\n🏆 Top 10 名单:")
            for i, stock in enumerate(result.phase_6_1_4_result.top10_stocks, 1):
                marker = "🎯" if self.TARGET_STOCK in stock.code else "  "
                print(f"   {marker} {i}. {stock.code} {stock.name} (V18: {stock.v18_score:.1f})")
        
        # 志特新材验证
        print(f"\n🔍 志特新材(300986)验证:")
        if result.target_stock_in_top10:
            print(f"   ✅ 成功进入Top 10！")
            print(f"   📊 排名: 第 {result.target_stock_rank} 名")
        elif result.target_stock_rank:
            print(f"   ⚠️ 未进入Top 10")
            print(f"   📊 排名: 第 {result.target_stock_rank} 名")
        else:
            print(f"   ❌ 不在结果中")
        
        print("\n" + "=" * 100)


def save_results(result: TimeMachineResult, output_dir: Path = None):
    """
    保存回演结果到文件
    
    Args:
        result: 回演结果
        output_dir: 输出目录
    """
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "time_machine"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = output_dir / f"time_machine_{result.trade_date}_{timestamp}.json"
    txt_file = output_dir / f"time_machine_{result.trade_date}_{timestamp}.txt"
    
    # 保存JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2, default=str)
    
    # 保存文本报告
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"时间机器回演报告\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"回演日期: {result.trade_date}\n")
        f.write(f"执行时间: {timestamp}\n")
        f.write(f"总耗时: {result.total_duration_ms:.2f} ms\n")
        f.write(f"执行状态: {'成功' if result.success else '失败'}\n\n")
        
        if result.success:
            f.write(f"志特新材排名: 第 {result.target_stock_rank} 名\n")
            f.write(f"进入Top 10: {'是' if result.target_stock_in_top10 else '否'}\n\n")
            
            if result.phase_6_1_4_result:
                f.write("Top 10 名单:\n")
                for i, stock in enumerate(result.phase_6_1_4_result.top10_stocks, 1):
                    f.write(f"  {i}. {stock.code} {stock.name} (V18: {stock.v18_score:.1f})\n")
    
    print(f"\n💾 结果已保存:")
    print(f"   JSON: {json_file}")
    print(f"   TXT:  {txt_file}")
    
    return json_file, txt_file


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='时间机器回演脚本 - Phase 6.1.5',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
    python tasks/run_time_machine_backtest.py --date 20251231
    python tasks/run_time_machine_backtest.py --date 20260223 --save
    python tasks/run_time_machine_backtest.py --date 20260223 --token YOUR_TOKEN
        """
    )
    
    parser.add_argument(
        '--date', '-d',
        type=str,
        required=True,
        help='回演日期 (YYYYMMDD格式, 如 20251231)'
    )
    
    parser.add_argument(
        '--token', '-t',
        type=str,
        default=None,
        help='Tushare Pro Token（可选）'
    )
    
    parser.add_argument(
        '--save', '-s',
        action='store_true',
        help='保存结果到文件'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出目录（可选）'
    )
    
    args = parser.parse_args()
    
    # 验证日期格式
    try:
        datetime.strptime(args.date, '%Y%m%d')
    except ValueError:
        print("❌ 错误: 日期格式不正确，请使用YYYYMMDD格式（如20251231）")
        sys.exit(1)
    
    print("=" * 100)
    print("🕐 时间机器回演系统")
    print("=" * 100)
    print(f"\n📅 目标日期: {args.date}")
    print(f"🎯 目标股票: 300986 (志特新材)")
    
    # 创建时间机器实例
    time_machine = TimeMachineBacktest(token=args.token)
    
    # 执行回演
    result = time_machine.run_backtest(trade_date=args.date)
    
    # 保存结果
    if args.save:
        output_dir = Path(args.output_dir) if args.output_dir else None
        save_results(result, output_dir)
    
    # 返回退出码
    sys.exit(0 if result.success else 1)


if __name__ == '__main__':
    main()