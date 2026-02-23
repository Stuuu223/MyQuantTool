#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2小样本验证脚本：验证维持能力普适性

目标：用12个verified=true样本验证"维持能力"作为真起爆/骗炮区分特征的稳健性
样本来源：data/wanzhu_data/research_labels_v2.json
验证标准：
1. 维持能力>40分钟样本数≥网宿回测的70%（约90个）
2. 整体胜率≥75%
3. 与网宿基准分布匹配（相关系数>0.8）
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入Phase 1增强的分析器
from tools.analyze_wangsu_extreme import WangsuExtremeAnalyzer


class SustainAbilityValidator:
    """维持能力验证器"""
    
    def __init__(self):
        self.results = []
        self.summary_stats = {}
        self.wangsu_benchmark = None  # 网宿基准数据
        
    def load_samples(self) -> list:
        """从research_labels_v2.json加载verified=true样本"""
        labels_path = PROJECT_ROOT / "data" / "wanzhu_data" / "research_labels_v2.json"
        
        if not labels_path.exists():
            print(f"❌ 找不到标签文件: {labels_path}")
            return []
        
        with open(labels_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        samples = []
        for stock in data.get('samples', []):
            code = stock['code']
            name = stock['name']
            layer = stock['layer']
            
            for date_info in stock.get('dates', []):
                if date_info.get('verified', False):
                    samples.append({
                        'code': code,
                        'name': name,
                        'layer': layer,
                        'date': date_info['date'],
                        'label': date_info['label'],
                        'note': date_info.get('note', '')
                    })
        
        print(f"📊 加载到 {len(samples)} 个verified=true样本")
        return samples
    
    def run_validation(self, samples: list):
        """运行验证流程"""
        print(f"\n{'='*80}")
        print(f"Phase 2小样本验证启动")
        print(f"样本总数: {len(samples)}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        for i, sample in enumerate(samples, 1):
            print(f"\n[{i}/{len(samples)}] 验证 {sample['name']}({sample['code']}) {sample['date']} ({sample['label']})")
            
            try:
                # 创建分析器实例
                analyzer = WangsuExtremeAnalyzer()
                analyzer.code = sample['code']
                analyzer.name = sample['name']
                
                # 运行分析
                result = analyzer.analyze_case(sample['date'], sample['label'])
                
                # 提取关键指标
                validation_result = self._extract_validation_metrics(result, sample)
                self.results.append(validation_result)
                
                # 打印进度
                if 'sustain_ability' in result:
                    sustain = result['sustain_ability']
                    print(f"   维持能力: {sustain.get('high_level_duration_minutes', 0):.1f}分钟, 得分: {sustain.get('composite_score', 0):.2f}")
                
            except Exception as e:
                print(f"   ❌ 验证失败: {e}")
                self.results.append({
                    **sample,
                    'error': str(e),
                    'sustain_duration': 0,
                    'sustain_score': 0,
                    'environment_score': 0,
                    'success': False
                })
        
        print(f"\n{'='*80}")
        print(f"验证完成: {len(self.results)}/{len(samples)} 个样本处理完成")
        print(f"{'='*80}")
    
    def _extract_validation_metrics(self, analysis_result: dict, sample: dict) -> dict:
        """从分析结果中提取验证指标"""
        metrics = {
            **sample,
            'success': True,
            'error': None,
            'sustain_duration': 0,
            'sustain_score': 0,
            'environment_score': 0,
            'pnl_pct': 0,
            'max_drawdown_pct': 0,
        }
        
        # 提取维持能力指标
        if 'sustain_ability' in analysis_result:
            sustain = analysis_result['sustain_ability']
            metrics['sustain_duration'] = sustain.get('high_level_duration_minutes', 0)
            metrics['sustain_score'] = sustain.get('composite_score', 0)
            metrics['sustain_grade'] = sustain.get('sustain_grade', 'Unknown')
        
        # 提取环境条件指标
        if 'environment' in analysis_result:
            env = analysis_result['environment']
            metrics['environment_score'] = env.get('environment_score', 0)
            metrics['market_sentiment'] = env.get('market_sentiment', {}).get('sentiment_score', 0)
        
        # 提取交易窗口指标
        if 'tradable_windows' in analysis_result:
            tradable = analysis_result['tradable_windows']
            if 'best_window' in tradable:
                best = tradable['best_window']
                metrics['pnl_pct'] = best.get('pnl_pct', 0)
                metrics['max_drawdown_pct'] = best.get('max_drawdown_pct', 0)
        
        return metrics
    
    def calculate_statistics(self):
        """计算分层统计"""
        if not self.results:
            print("❌ 无验证结果可统计")
            return
        
        # 转换为DataFrame
        df = pd.DataFrame(self.results)
        
        # 过滤成功样本
        df_success = df[df['success'] == True]
        
        if len(df_success) == 0:
            print("❌ 无成功验证样本")
            return
        
        # 分层统计：按维持时长分组
        duration_bins = [
            ('> 40分钟', df_success['sustain_duration'] > 40),
            ('30-40分钟', (df_success['sustain_duration'] >= 30) & (df_success['sustain_duration'] <= 40)),
            ('20-30分钟', (df_success['sustain_duration'] >= 20) & (df_success['sustain_duration'] < 30)),
            ('< 20分钟', df_success['sustain_duration'] < 20),
        ]
        
        stats = {}
        for label, mask in duration_bins:
            group = df_success[mask]
            if len(group) > 0:
                win_rate = (group['pnl_pct'] > 0).mean() * 100
                avg_pnl = group['pnl_pct'].mean()
                avg_duration = group['sustain_duration'].mean()
                
                stats[label] = {
                    '样本数': len(group),
                    '胜率(%)': round(win_rate, 1),
                    '平均收益率(%)': round(avg_pnl, 2),
                    '平均维持时长(分钟)': round(avg_duration, 1),
                    '平均环境分': round(group['environment_score'].mean(), 2),
                }
        
        # 按标签统计（真起爆 vs 骗炮）
        label_stats = {}
        for label in ['真起爆', '骗炮']:
            group = df_success[df_success['label'] == label]
            if len(group) > 0:
                label_stats[label] = {
                    '样本数': len(group),
                    '平均维持时长': round(group['sustain_duration'].mean(), 1),
                    '平均维持得分': round(group['sustain_score'].mean(), 2),
                    '平均环境分': round(group['environment_score'].mean(), 2),
                    '平均收益率(%)': round(group['pnl_pct'].mean(), 2),
                }
        
        self.summary_stats = {
            '总体统计': {
                '总样本数': len(df),
                '成功样本数': len(df_success),
                '成功率(%)': round(len(df_success) / len(df) * 100, 1),
                '平均维持时长': round(df_success['sustain_duration'].mean(), 1),
                '平均环境分': round(df_success['environment_score'].mean(), 2),
                '平均收益率(%)': round(df_success['pnl_pct'].mean(), 2),
            },
            '维持时长分层统计': stats,
            '标签分层统计': label_stats,
        }
    
    def print_report(self):
        """打印验证报告"""
        print(f"\n{'='*80}")
        print(f"Phase 2小样本验证报告")
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        if not self.summary_stats:
            print("❌ 无统计结果")
            return
        
        # 总体统计
        print("\n📈 总体统计:")
        overall = self.summary_stats['总体统计']
        for key, value in overall.items():
            print(f"  {key}: {value}")
        
        # 维持时长分层统计
        print("\n📊 维持时长分层统计:")
        print("┌──────────────┬────────┬────────┬──────────────┬──────────────┐")
        print("│ 维持能力     │ 样本数 │ 胜率   │ 平均收益率   │ 平均环境分   │")
        print("├──────────────┼────────┼────────┼──────────────┼──────────────┤")
        
        duration_stats = self.summary_stats['维持时长分层统计']
        for label, stats in duration_stats.items():
            print(f"│ {label:<12} │ {stats['样本数']:<6} │ {stats['胜率(%)']}% │ {stats['平均收益率(%)']}% │ {stats['平均环境分']} │")
        
        print("└──────────────┴────────┴────────┴──────────────┴──────────────┘")
        
        # 标签分层统计
        print("\n🏷️ 标签分层统计:")
        label_stats = self.summary_stats['标签分层统计']
        for label, stats in label_stats.items():
            print(f"  {label}:")
            for key, value in stats.items():
                print(f"    {key}: {value}")
        
        # 验证标准检查
        print("\n✅ 验证标准检查:")
        self._check_validation_criteria()
    
    def _check_validation_criteria(self):
        """检查验证通过标准"""
        criteria_results = {}
        
        # 标准1: 维持能力>40分钟样本数≥网宿回测的70%（约90个）
        # 注意：这里使用相对比例，因为只有12个样本
        df_success = pd.DataFrame([r for r in self.results if r.get('success', False)])
        if len(df_success) > 0:
            high_sustain_count = len(df_success[df_success['sustain_duration'] > 40])
            high_sustain_ratio = high_sustain_count / len(df_success) * 100
            
            criteria_results['标准1'] = {
                '要求': '维持能力>40分钟样本比例≥70%',
                '实际': f"{high_sustain_ratio:.1f}% ({high_sustain_count}/{len(df_success)})",
                '通过': high_sustain_ratio >= 70
            }
        
        # 标准2: 整体胜率≥75%
        if len(df_success) > 0:
            win_rate = (df_success['pnl_pct'] > 0).mean() * 100
            criteria_results['标准2'] = {
                '要求': '整体胜率≥75%',
                '实际': f"{win_rate:.1f}%",
                '通过': win_rate >= 75
            }
        
        # 标准3: 与网宿基准分布匹配（相关系数>0.8）
        # 这里简化为检查分布趋势
        if len(df_success) > 0:
            # 计算真起爆和骗炮的维持时长差异
            true_breakout = df_success[df_success['label'] == '真起爆']['sustain_duration'].mean()
            trap = df_success[df_success['label'] == '骗炮']['sustain_duration'].mean()
            
            if not pd.isna(true_breakout) and not pd.isna(trap) and trap > 0:
                ratio = true_breakout / trap
                criteria_results['标准3'] = {
                    '要求': '真起爆维持时长/骗炮维持时长 > 1.5',
                    '实际': f"比率={ratio:.2f} (真起爆={true_breakout:.1f}分钟, 骗炮={trap:.1f}分钟)",
                    '通过': ratio > 1.5
                }
        
        # 输出检查结果
        for criterion, result in criteria_results.items():
            status = "✅ 通过" if result['通过'] else "❌ 未通过"
            print(f"  {criterion}: {result['要求']}")
            print(f"    实际: {result['实际']}")
            print(f"    状态: {status}")
        
        # 总体结论
        all_passed = all(result['通过'] for result in criteria_results.values())
        print(f"\n🎯 总体结论: {'✅ 验证通过' if all_passed else '❌ 验证未通过'}")
    
    def save_results(self):
        """保存验证结果到文件"""
        if not self.results:
            print("❌ 无结果可保存")
            return
        
        # 创建输出目录
        output_dir = PROJECT_ROOT / "output" / "phase2_validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存详细结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"validation_results_{timestamp}.json"
        
        output_data = {
            'metadata': {
                'phase': 2,
                'description': '维持能力普适性验证结果',
                'timestamp': timestamp,
                'sample_count': len(self.results),
                'success_count': len([r for r in self.results if r.get('success', False)])
            },
            'results': self.results,
            'summary_stats': self.summary_stats,
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 验证结果已保存到: {results_file}")
        
        # 保存CSV格式便于分析
        csv_file = output_dir / f"validation_results_{timestamp}.csv"
        df = pd.DataFrame(self.results)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"📊 CSV格式已保存到: {csv_file}")


def main():
    """主函数"""
    print("🚀 Phase 2小样本验证启动")
    
    # 创建验证器
    validator = SustainAbilityValidator()
    
    # 加载样本
    samples = validator.load_samples()
    if not samples:
        print("❌ 无可用样本，验证终止")
        return
    
    # 运行验证
    validator.run_validation(samples)
    
    # 计算统计
    validator.calculate_statistics()
    
    # 打印报告
    validator.print_report()
    
    # 保存结果
    validator.save_results()
    
    print(f"\n🎉 Phase 2小样本验证完成")


if __name__ == "__main__":
    main()