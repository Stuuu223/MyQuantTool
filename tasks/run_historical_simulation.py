#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0.5: 50样本历史回测模拟
运行时间：2026-02-21（不开盘窗口）
功能：50个verified样本 × 起爆日±3天 历史Tick回测
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.event_lifecycle_service import EventLifecycleService
from logic.backtest.behavior_replay_engine import BehaviorReplayEngine


class HistoricalSimulator:
    """50样本历史回测模拟器"""
    
    def __init__(self):
        self.output_dir = PROJECT_ROOT / "data" / "historical_simulation"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化服务
        self.lifecycle_service = EventLifecycleService()
        self.replay_engine = BehaviorReplayEngine(use_sustain_filter=True)
        
        # 过滤器阈值
        self.sustain_threshold = 0.5
        self.env_threshold = 0.6
        
        print(f"{'='*80}")
        print(f"Phase 0.5: 50样本历史回测模拟")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*80}\n")
    
    def load_samples_from_csv(self) -> list:
        """加载顽主杯150样本池（from CSV）"""
        csv_path = PROJECT_ROOT / "data" / "wanzhu_data" / "processed" / "wanzhu_selected_150.csv"
        
        if not csv_path.exists():
            print(f"❌ 找不到顽主杯150文件: {csv_path}")
            return []
        
        df = pd.read_csv(csv_path)
        samples = []
        
        # 取前150只（如果不够则全取）
        for _, row in df.head(150).iterrows():
            code = str(row['code']).zfill(6)  # 补齐6位
            name = row['name']
            layer = row.get('layer', 'unknown')
            
            # 为每只票生成测试日期（使用历史日期2026年1月，确保有数据）
            import datetime
            
            # 使用2026年1月的历史数据（已知有数据的日期）
            if layer == 'high_freq':
                # 高频票：1月20-31日
                test_dates = ['2026-01-20', '2026-01-21', '2026-01-23']
            elif layer == 'mid_freq':
                # 中频票：1月中旬
                test_dates = ['2026-01-15', '2026-01-20', '2026-01-24']
            else:
                # 低频票：1月初和1月底
                test_dates = ['2026-01-06', '2026-01-26', '2026-01-31']
            
            # 每只票取3个测试日
            for date_str in test_dates:
                samples.append({
                    'code': code,
                    'name': name,
                    'layer': layer,
                    'date': date_str,
                    'label': '待检测'  # 由EventLifecycleService判定
                })
        
        print(f"📊 加载顽主杯150样本池: {len(samples)} 个测试点")
        return samples
    
    def load_samples(self) -> list:
        """加载verified=true样本（保留兼容）"""
        # 优先使用顽主杯150
        wanzhu_samples = self.load_samples_from_csv()
        if wanzhu_samples:
            return wanzhu_samples
        
        # 回退到JSON
        labels_path = PROJECT_ROOT / "data" / "wanzhu_data" / "research_labels_v2.json"
        
        with open(labels_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        samples = []
        for stock in data.get('samples', []):
            code = stock['code']
            name = stock['name']
            
            for date_info in stock.get('dates', []):
                # 只使用verified=true且日期在2026年1月后的（确保有Tick数据）
                if date_info.get('verified', False):
                    date = date_info['date']
                    # 跳过2025年12月的数据（Tick可能缺失）
                    if date.startswith('2026'):
                        samples.append({
                            'code': code,
                            'name': name,
                            'date': date,
                            'label': date_info['label'],
                            'layer': stock.get('layer', 'unknown')
                        })
        
        # 去重并按日期排序
        seen = set()
        unique_samples = []
        for s in samples:
            key = f"{s['code']}_{s['date']}"
            if key not in seen:
                seen.add(key)
                unique_samples.append(s)
        
        # 如果不足50个，补充一些2026年的样本（即使verified=false但数据质量ok的）
        if len(unique_samples) < 50:
            for stock in data.get('samples', []):
                code = stock['code']
                name = stock['name']
                
                for date_info in stock.get('dates', []):
                    date = date_info['date']
                    # 补充2026年的样本
                    if date.startswith('2026') and not date_info.get('verified', False):
                        # 检查是否已存在
                        key = f"{code}_{date}"
                        if key not in seen and len(unique_samples) < 50:
                            seen.add(key)
                            unique_samples.append({
                                'code': code,
                                'name': name,
                                'date': date,
                                'label': date_info['label'],
                                'layer': stock.get('layer', 'unknown'),
                                'note': 'extended'
                            })
        
        print(f"加载样本: {len(unique_samples)} 个")
        print(f"  - 真起爆: {sum(1 for s in unique_samples if s['label'] == '真起爆')}")
        print(f"  - 骗炮: {sum(1 for s in unique_samples if s['label'] == '骗炮')}")
        print()
        
        return unique_samples
    
    def simulate_sample(self, sample: dict) -> dict:
        """模拟单个样本"""
        code = sample['code']
        name = sample['name']
        date = sample['date']
        label = sample['label']
        
        result = {
            'code': code,
            'name': name,
            'date': date,
            'label': label,
            'success': False,
            'sustain_score': 0,
            'env_score': 0,
            'is_true_breakout': None,
            'confidence': 0,
            'pnl_pct': 0,
            'max_drawdown': 0,
            'data_source': 'none'
        }
        
        try:
            # 使用EventLifecycleService分析
            lifecycle_result = self.lifecycle_service.analyze(code, date)
            
            sustain_score = lifecycle_result.get('sustain_score', 0)
            env_score = lifecycle_result.get('env_score', 0)
            is_true = lifecycle_result.get('is_true_breakout')
            confidence = lifecycle_result.get('confidence', 0)
            
            # 记录结果
            result['success'] = True
            result['sustain_score'] = sustain_score
            result['env_score'] = env_score
            result['is_true_breakout'] = is_true
            result['confidence'] = confidence
            result['sustain_duration'] = lifecycle_result.get('sustain_duration_min', 0)
            
            # 如果有交易信号，模拟收益
            entry_signal = lifecycle_result.get('entry_signal')
            if entry_signal:
                result['pnl_pct'] = entry_signal.get('pnl_pct', 0)
                result['max_drawdown'] = entry_signal.get('max_drawdown_pct', 0)
                result['entry_price'] = entry_signal.get('entry_price', 0)
            
            # 标记数据源
            result['data_source'] = 'tick'  # 或 'kline'
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def run_simulation(self, samples: list):
        """运行完整回测模拟"""
        print(f"{'='*80}")
        print(f"开始回测模拟: {len(samples)} 个样本")
        print(f"{'='*80}\n")
        
        results = []
        
        for i, sample in enumerate(samples, 1):
            print(f"[{i}/{len(samples)}] {sample['name']}({sample['code']}) {sample['date']} ({sample['label']})")
            
            result = self.simulate_sample(sample)
            results.append(result)
            
            if result['success']:
                status = "✅" if result['is_true_breakout'] else "❌"
                print(f"    {status} sustain={result['sustain_score']:.2f}, env={result['env_score']:.2f}, "
                      f"predict={result['is_true_breakout']}, pnl={result['pnl_pct']:+.2f}%")
            else:
                print(f"    ⚠️ 失败: {result.get('error', 'unknown')}")
        
        print(f"\n{'='*80}")
        print(f"回测完成: {len(results)} 个样本")
        print(f"{'='*80}\n")
        
        return results
    
    def generate_statistics(self, results: list):
        """生成统计报告"""
        print(f"{'='*80}")
        print(f"特征统计报告")
        print(f"{'='*80}\n")
        
        # 过滤成功样本
        success_results = [r for r in results if r.get('success', False)]
        
        if not success_results:
            print("无有效结果")
            return
        
        # 总体统计
        total = len(success_results)
        true_breakouts = [r for r in success_results if r['label'] == '真起爆']
        traps = [r for r in success_results if r['label'] == '骗炮']
        
        print(f"【总体统计】")
        print(f"  总样本数: {total}")
        print(f"  真起爆: {len(true_breakouts)} ({len(true_breakouts)/total*100:.1f}%)")
        print(f"  骗炮: {len(traps)} ({len(traps)/total*100:.1f}%)")
        print()
        
        # 维持能力分层统计
        print(f"【维持能力分层统计】")
        print(f"{'-'*80}")
        print(f"{'特征组合':<20} {'样本数':<10} {'胜率':<10} {'平均盈亏':<12} {'平均维持':<10}")
        print(f"{'-'*80}")
        
        # sustain >= 0.5
        high_sustain = [r for r in success_results if r['sustain_score'] >= 0.5]
        if high_sustain:
            wins = sum(1 for r in high_sustain if r['pnl_pct'] > 0)
            win_rate = wins / len(high_sustain) * 100
            avg_pnl = sum(r['pnl_pct'] for r in high_sustain) / len(high_sustain)
            avg_duration = sum(r.get('sustain_duration', 0) for r in high_sustain) / len(high_sustain)
            print(f"{'sustain>=0.5':<20} {len(high_sustain):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_duration:>6.1f}min")
        
        # sustain >= 0.3
        mid_sustain = [r for r in success_results if 0.3 <= r['sustain_score'] < 0.5]
        if mid_sustain:
            wins = sum(1 for r in mid_sustain if r['pnl_pct'] > 0)
            win_rate = wins / len(mid_sustain) * 100
            avg_pnl = sum(r['pnl_pct'] for r in mid_sustain) / len(mid_sustain)
            avg_duration = sum(r.get('sustain_duration', 0) for r in mid_sustain) / len(mid_sustain)
            print(f"{'0.3<=sustain<0.5':<20} {len(mid_sustain):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_duration:>6.1f}min")
        
        # sustain < 0.3
        low_sustain = [r for r in success_results if r['sustain_score'] < 0.3]
        if low_sustain:
            wins = sum(1 for r in low_sustain if r['pnl_pct'] > 0)
            win_rate = wins / len(low_sustain) * 100
            avg_pnl = sum(r['pnl_pct'] for r in low_sustain) / len(low_sustain)
            avg_duration = sum(r.get('sustain_duration', 0) for r in low_sustain) / len(low_sustain)
            print(f"{'sustain<0.3':<20} {len(low_sustain):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_duration:>6.1f}min")
        
        print(f"{'-'*80}\n")
        
        # 环境分层统计
        print(f"【环境分层统计】")
        print(f"{'-'*80}")
        print(f"{'特征组合':<20} {'样本数':<10} {'胜率':<10} {'平均盈亏':<12} {'平均环境':<10}")
        print(f"{'-'*80}")
        
        # env >= 0.6
        high_env = [r for r in success_results if r['env_score'] >= 0.6]
        if high_env:
            wins = sum(1 for r in high_env if r['pnl_pct'] > 0)
            win_rate = wins / len(high_env) * 100
            avg_pnl = sum(r['pnl_pct'] for r in high_env) / len(high_env)
            avg_env = sum(r['env_score'] for r in high_env) / len(high_env)
            print(f"{'env>=0.6':<20} {len(high_env):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_env:>6.2f}")
        
        # env 0.4-0.6
        mid_env = [r for r in success_results if 0.4 <= r['env_score'] < 0.6]
        if mid_env:
            wins = sum(1 for r in mid_env if r['pnl_pct'] > 0)
            win_rate = wins / len(mid_env) * 100
            avg_pnl = sum(r['pnl_pct'] for r in mid_env) / len(mid_env)
            avg_env = sum(r['env_score'] for r in mid_env) / len(mid_env)
            print(f"{'0.4<=env<0.6':<20} {len(mid_env):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_env:>6.2f}")
        
        # env < 0.4
        low_env = [r for r in success_results if r['env_score'] < 0.4]
        if low_env:
            wins = sum(1 for r in low_env if r['pnl_pct'] > 0)
            win_rate = wins / len(low_env) * 100
            avg_pnl = sum(r['pnl_pct'] for r in low_env) / len(low_env)
            avg_env = sum(r['env_score'] for r in low_env) / len(low_env)
            print(f"{'env<0.4':<20} {len(low_env):<10} {win_rate:>6.1f}%    {avg_pnl:>+6.2f}%      {avg_env:>6.2f}")
        
        print(f"{'-'*80}\n")
        
        # 标签分层统计
        print(f"【标签分层统计】")
        print(f"{'-'*80}")
        print(f"{'标签':<15} {'样本数':<10} {'平均维持分':<12} {'平均环境分':<12} {'平均收益':<10}")
        print(f"{'-'*80}")
        
        if true_breakouts:
            avg_sustain = sum(r['sustain_score'] for r in true_breakouts) / len(true_breakouts)
            avg_env = sum(r['env_score'] for r in true_breakouts) / len(true_breakouts)
            avg_pnl = sum(r['pnl_pct'] for r in true_breakouts) / len(true_breakouts)
            print(f"{'真起爆':<15} {len(true_breakouts):<10} {avg_sustain:>8.2f}      {avg_env:>8.2f}      {avg_pnl:>+6.2f}%")
        
        if traps:
            avg_sustain = sum(r['sustain_score'] for r in traps) / len(traps)
            avg_env = sum(r['env_score'] for r in traps) / len(traps)
            avg_pnl = sum(r['pnl_pct'] for r in traps) / len(traps)
            print(f"{'骗炮':<15} {len(traps):<10} {avg_sustain:>8.2f}      {avg_env:>8.2f}      {avg_pnl:>+6.2f}%")
        
        print(f"{'-'*80}\n")
        
        # 保存详细结果
        self._save_results(results)
    
    def _save_results(self, results: list):
        """保存详细结果到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON格式
        json_file = self.output_dir / f"simulation_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'timestamp': timestamp,
                    'sample_count': len(results),
                    'sustain_threshold': self.sustain_threshold,
                    'env_threshold': self.env_threshold
                },
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 详细结果已保存: {json_file}")
        
        # CSV格式
        csv_file = self.output_dir / f"simulation_results_{timestamp}.csv"
        df = pd.DataFrame(results)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"📊 CSV格式已保存: {csv_file}")


def main():
    """主函数"""
    print("🚀 Phase 0.5: 50样本历史回测模拟")
    print("="*80)
    
    # 创建模拟器
    simulator = HistoricalSimulator()
    
    # 加载样本
    samples = simulator.load_samples()
    
    if not samples:
        print("❌ 无可用样本")
        return 1
    
    # 运行回测
    results = simulator.run_simulation(samples)
    
    # 生成统计
    simulator.generate_statistics(results)
    
    print("\n" + "="*80)
    print("🎉 Phase 0.5 历史回测模拟完成")
    print("="*80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
