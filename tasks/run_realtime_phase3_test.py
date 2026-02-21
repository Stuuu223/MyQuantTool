#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3 实盘测试脚本
运行时间：2026-02-24 至 2026-02-28（5个交易日）
功能：实时扫描全市场，使用EventLifecycleService过滤器发预警信号
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.event_lifecycle_service import EventLifecycleService
from logic.services.data_service import data_service
from logic.strategies.wind_filter import WindFilter


class RealtimePhase3Tester:
    """Phase 3实盘测试器"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or PROJECT_ROOT / "data" / "realtime_phase3_test"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化服务
        self.lifecycle_service = EventLifecycleService()
        self.wind_filter = WindFilter()
        
        # 过滤器阈值（CTO确定）
        self.sustain_threshold = 0.5    # 维持分≥0.5
        self.env_threshold = 0.6        # 环境分≥0.6
        
        # 每日信号记录
        self.daily_signals = []
        
        print(f"{'='*80}")
        print(f"Phase 3 实盘测试启动")
        print(f"测试日期: 2026-02-24 至 2026-02-28")
        print(f"过滤器: sustain≥{self.sustain_threshold}, env≥{self.env_threshold}")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*80}\n")
    
    def scan_watchlist(self, watchlist: list, date: str = None):
        """
        扫描关注列表
        
        Args:
            watchlist: [(code, name), ...]
            date: 测试日期（默认今天）
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*80}")
        print(f"扫描日期: {date}")
        print(f"扫描股票数: {len(watchlist)}")
        print(f"{'='*80}\n")
        
        signals = []
        
        for i, (code, name) in enumerate(watchlist, 1):
            print(f"[{i}/{len(watchlist)}] 分析 {name}({code})...", end=' ')
            
            try:
                # 使用EventLifecycleService分析
                result = self.lifecycle_service.analyze(code, date)
                
                sustain_score = result.get('sustain_score', 0)
                env_score = result.get('env_score', 0)
                is_true = result.get('is_true_breakout')
                confidence = result.get('confidence', 0)
                
                # 过滤器检查
                if sustain_score >= self.sustain_threshold and \
                   env_score >= self.env_threshold and \
                   is_true is True:
                    
                    # 生成预警信号
                    signal = {
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'date': date,
                        'code': code,
                        'name': name,
                        'sustain_score': round(sustain_score, 2),
                        'env_score': round(env_score, 2),
                        'confidence': round(confidence, 2),
                        'signal_type': 'TRUE_BREAKOUT',
                        'entry_signal': result.get('entry_signal', {}),
                        'raw_data': {
                            'sustain_duration': result.get('sustain_duration_min', 0),
                            'env_details': result.get('env_details', {})
                        }
                    }
                    signals.append(signal)
                    
                    print(f"🚨 预警! sustain={sustain_score:.2f}, env={env_score:.2f}")
                else:
                    print(f"跳过 sustain={sustain_score:.2f}, env={env_score:.2f}")
                    
            except Exception as e:
                print(f"❌ 失败: {e}")
        
        # 保存当日信号
        self.daily_signals.extend(signals)
        self._save_daily_signals(date, signals)
        
        print(f"\n{'='*80}")
        print(f"扫描完成: {len(signals)} 个预警信号")
        print(f"{'='*80}\n")
        
        return signals
    
    def _save_daily_signals(self, date: str, signals: list):
        """保存当日信号到文件"""
        output_file = self.output_dir / f"signals_{date}.json"
        
        data = {
            'date': date,
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'thresholds': {
                'sustain': self.sustain_threshold,
                'env': self.env_threshold
            },
            'signal_count': len(signals),
            'signals': signals
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 信号已保存: {output_file}")
    
    def generate_daily_report(self, date: str):
        """生成每日复盘报告"""
        # 读取当日信号
        signal_file = self.output_dir / f"signals_{date}.json"
        if not signal_file.exists():
            print(f"⚠️ 无信号文件: {date}")
            return
        
        with open(signal_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = data.get('signals', [])
        
        print(f"\n{'='*80}")
        print(f"复盘报告: {date}")
        print(f"{'='*80}")
        print(f"信号总数: {len(signals)}")
        
        if signals:
            print("\n预警信号列表:")
            for s in signals:
                print(f"  {s['time']} {s['name']}({s['code']})")
                print(f"    sustain={s['sustain_score']}, env={s['env_score']}, conf={s['confidence']}")
                if s.get('entry_signal'):
                    print(f"    建议入场: {s['entry_signal'].get('entry_price')}")
        
        print(f"\n{'='*80}")
        print("复盘要点:")
        print("1. 记录次日维持时长（是否>40分钟）")
        print("2. 记录次日收益率（相对信号日收盘）")
        print("3. 手动标记真假起爆（对比实际走势）")
        print(f"{'='*80}\n")
    
    def run_full_test(self, watchlist: list, start_date: str, end_date: str):
        """运行完整5天测试"""
        dates = self._get_trading_days(start_date, end_date)
        
        print(f"\n测试日期列表: {dates}\n")
        
        for date in dates:
            # 模拟每日扫描（实际运行时替换为真实日期）
            self.scan_watchlist(watchlist, date)
            
            # 生成复盘报告
            self.generate_daily_report(date)
        
        # 生成总报告
        self._generate_final_report()
    
    def _get_trading_days(self, start: str, end: str) -> list:
        """获取交易日列表"""
        dates = []
        current = datetime.strptime(start, '%Y-%m-%d')
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        
        while current <= end_dt:
            # 跳过周末
            if current.weekday() < 5:
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return dates
    
    def _generate_final_report(self):
        """生成最终测试报告"""
        report_file = self.output_dir / f"final_report_{datetime.now().strftime('%Y%m%d')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Phase 3 实盘测试报告\n\n")
            f.write(f"测试时间: 2026-02-24 至 2026-02-28\n")
            f.write(f"过滤器: sustain≥{self.sustain_threshold}, env≥{self.env_threshold}\n\n")
            
            f.write("## 每日信号统计\n\n")
            f.write("| 日期 | 信号数 | 命中数 | 命中率 | 平均收益 |\n")
            f.write("|------|--------|--------|--------|----------|\n")
            
            # TODO: 填充实际数据
            f.write("| 2026-02-24 | - | - | -% | - |\n")
            f.write("| 2026-02-25 | - | - | -% | - |\n")
            f.write("| 2026-02-26 | - | - | -% | - |\n")
            f.write("| 2026-02-27 | - | - | -% | - |\n")
            f.write("| 2026-02-28 | - | - | -% | - |\n\n")
            
            f.write("## 核心指标\n\n")
            f.write("- 总信号数: \n")
            f.write("- 命中率（次日维持>40分钟）: \n")
            f.write("- 平均收益率: \n")
            f.write("- 假阳性率: \n\n")
            
            f.write("## 结论\n\n")
            f.write("（待测试完成后填写）\n")
        
        print(f"📊 最终报告模板已生成: {report_file}")


def main():
    """主函数 - 2月24日实盘测试入口"""
    print("🚀 Phase 3 实盘测试")
    print("="*80)
    
    # 关注列表（清洗后的11只有效样本 + 扩展）
    watchlist = [
        # 高频核心层
        ('300017', '网宿科技'),
        ('000547', '航天发展'),
        ('300058', '蓝色光标'),
        ('000592', '平潭发展'),
        # 可扩展更多...
    ]
    
    # 创建测试器
    tester = RealtimePhase3Tester()
    
    # 运行测试（5天）
    tester.run_full_test(
        watchlist=watchlist,
        start_date='2026-02-24',
        end_date='2026-02-28'
    )
    
    print("\n" + "="*80)
    print("🎉 Phase 3 实盘测试完成")
    print("="*80)


if __name__ == '__main__':
    main()
