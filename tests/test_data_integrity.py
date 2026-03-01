#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【CTO级数据完整性验证工具】

功能：
1. 验证日K/分钟K/Tick三周期数据完整性
2. 输出详细诊断报告（条数、缺失项、阈值达标情况）
3. 支持单股验证和批量验证
4. 可独立运行，也可被其他模块调用

使用方法：
  单只验证：python tests/test_data_integrity.py --stock 000001.SZ --date 20260228
  批量验证：python tests/test_data_integrity.py --list 000001.SZ,600519.SH --date 20260228
  全息池验证：python tests/test_data_integrity.py --holographic --date 20260228

Author: CTO
Date: 2026-03-01
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from xtquant import xtdata
    XT_AVAILABLE = True
except ImportError:
    XT_AVAILABLE = False
    print("❌ 错误：xtquant模块不可用，请检查QMT安装")
    sys.exit(1)

# ============================================================
# 数据完整性阈值（CTO钦定标准）
# ============================================================
class DataThreshold:
    """数据完整性阈值标准"""
    DAILY_MIN = 1      # 日K至少1条
    MINUTE_MIN = 240   # 分钟K至少240条（4小时交易）
    TICK_MIN = 1       # Tick至少1条（统一为 > 0 标准）

@dataclass
class PeriodReport:
    """单周期数据报告"""
    period: str
    exists: bool
    count: int
    threshold: int
    passed: bool
    
    def __str__(self):
        status = "✅" if self.passed else "❌"
        return f"{status} {self.period:6s} | {self.count:6d}条 (阈值≥{self.threshold})"

@dataclass
class StockReport:
    """单只股票完整性报告"""
    stock_code: str
    trade_date: str
    daily: PeriodReport
    minute: PeriodReport
    tick: PeriodReport
    
    @property
    def is_complete(self) -> bool:
        """是否完全达标"""
        return self.daily.passed and self.minute.passed and self.tick.passed
    
    @property
    def completeness_ratio(self) -> float:
        """完整度比率 (0.0-1.0)"""
        passed = sum([self.daily.passed, self.minute.passed, self.tick.passed])
        return passed / 3.0
    
    def print_report(self):
        """打印报告"""
        print(f"\n{'='*60}")
        print(f"股票代码: {self.stock_code} | 日期: {self.trade_date}")
        print(f"{'='*60}")
        print(self.daily)
        print(self.minute)
        print(self.tick)
        print(f"{'='*60}")
        if self.is_complete:
            print(f"✅ 完整性: 100% (全部达标)")
        else:
            print(f"⚠️ 完整性: {self.completeness_ratio*100:.0f}% (部分缺失)")
        print(f"{'='*60}")

class DataIntegrityChecker:
    """数据完整性检查器"""
    
    def __init__(self):
        if not XT_AVAILABLE:
            raise RuntimeError("xtquant不可用")
    
    def check_period(
        self, 
        stock_code: str, 
        trade_date: str, 
        period: str,
        threshold: int
    ) -> PeriodReport:
        """
        检查单个周期的数据
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            period: 周期 ('1d', '1m', 'tick')
            threshold: 最小条数阈值
        
        Returns:
            PeriodReport
        """
        try:
            data = xtdata.get_local_data(
                field_list=['time'],
                stock_list=[stock_code],
                period=period,
                start_time=trade_date,
                end_time=trade_date
            )
            
            if data and stock_code in data and not data[stock_code].empty:
                count = len(data[stock_code])
                passed = count >= threshold
                return PeriodReport(
                    period=period,
                    exists=True,
                    count=count,
                    threshold=threshold,
                    passed=passed
                )
            else:
                return PeriodReport(
                    period=period,
                    exists=False,
                    count=0,
                    threshold=threshold,
                    passed=False
                )
        except Exception as e:
            print(f"⚠️ 检查{stock_code} {period}数据时出错: {e}")
            return PeriodReport(
                period=period,
                exists=False,
                count=0,
                threshold=threshold,
                passed=False
            )
    
    def check_stock(self, stock_code: str, trade_date: str) -> StockReport:
        """
        检查单只股票的全周期数据
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
        
        Returns:
            StockReport
        """
        daily = self.check_period(stock_code, trade_date, '1d', DataThreshold.DAILY_MIN)
        minute = self.check_period(stock_code, trade_date, '1m', DataThreshold.MINUTE_MIN)
        tick = self.check_period(stock_code, trade_date, 'tick', DataThreshold.TICK_MIN)
        
        return StockReport(
            stock_code=stock_code,
            trade_date=trade_date,
            daily=daily,
            minute=minute,
            tick=tick
        )
    
    def check_batch(
        self, 
        stock_list: List[str], 
        trade_date: str,
        verbose: bool = True
    ) -> Dict[str, StockReport]:
        """
        批量检查多只股票
        
        Args:
            stock_list: 股票代码列表
            trade_date: 交易日期
            verbose: 是否打印详细报告
        
        Returns:
            {stock_code: StockReport}
        """
        reports = {}
        
        print(f"\n{'='*60}")
        print(f"批量数据完整性验证")
        print(f"日期: {trade_date} | 股票数: {len(stock_list)}")
        print(f"{'='*60}")
        
        for i, stock in enumerate(stock_list, 1):
            print(f"\n[{i}/{len(stock_list)}] 检查 {stock}...", end='')
            report = self.check_stock(stock, trade_date)
            reports[stock] = report
            
            if verbose:
                status = "✅" if report.is_complete else f"⚠️ {report.completeness_ratio*100:.0f}%"
                print(f" {status}")
            else:
                print()
        
        # 汇总统计
        complete_count = sum(1 for r in reports.values() if r.is_complete)
        avg_completeness = sum(r.completeness_ratio for r in reports.values()) / len(reports)
        
        print(f"\n{'='*60}")
        print(f"汇总统计")
        print(f"{'='*60}")
        print(f"完全达标: {complete_count}/{len(stock_list)} ({complete_count/len(stock_list)*100:.1f}%)")
        print(f"平均完整度: {avg_completeness*100:.1f}%")
        print(f"{'='*60}")
        
        return reports


def main():
    """主函数：命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据完整性验证工具')
    parser.add_argument('--stock', type=str, help='单只股票代码')
    parser.add_argument('--list', type=str, help='股票列表（逗号分隔）')
    parser.add_argument('--holographic', action='store_true', help='验证全息股票池')
    parser.add_argument('--date', type=str, required=True, help='交易日期 YYYYMMDD')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    checker = DataIntegrityChecker()
    
    # 单只验证
    if args.stock:
        report = checker.check_stock(args.stock, args.date)
        report.print_report()
        sys.exit(0 if report.is_complete else 1)
    
    # 批量验证
    if args.list:
        stock_list = [s.strip() for s in args.list.split(',')]
        reports = checker.check_batch(stock_list, args.date, args.verbose)
        
        # 打印失败项
        failed = [code for code, r in reports.items() if not r.is_complete]
        if failed:
            print(f"\n未完全达标的股票: {', '.join(failed)}")
        
        sys.exit(0 if all(r.is_complete for r in reports.values()) else 1)
    
    # 全息池验证
    if args.holographic:
        import json
        universe_file = project_root / 'data' / f'holographic_universe_{args.date}.json'
        
        if not universe_file.exists():
            print(f"❌ 全息股票池文件不存在: {universe_file}")
            sys.exit(1)
        
        with open(universe_file, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
        
        stock_list = universe_data.get('stocks', [])
        if not stock_list:
            print(f"❌ 全息股票池为空")
            sys.exit(1)
        
        print(f"📊 全息股票池: {len(stock_list)}只股票")
        reports = checker.check_batch(stock_list, args.date, args.verbose)
        
        sys.exit(0 if all(r.is_complete for r in reports.values()) else 1)
    
    parser.print_help()

if __name__ == '__main__':
    main()
