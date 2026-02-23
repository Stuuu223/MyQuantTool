#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究流水线总驱动
CTO指令：给定labels + 日期范围，一键重跑：Tick回放→ratio计算→summary输出
目标：幂等+可重放，重复运行N次结果完全一致
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.services.data_service import data_service
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.rolling_metrics import RollingFlowCalculator


def load_labels(config_path: Path) -> list:
    """
    加载标签配置（唯一正确来源）
    格式: [{"code": "300017", "name": "网宿科技", "dates": [...]}, ...]
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config.get('samples', [])


def analyze_single_case(code: str, name: str, date: str, label: str, 
                        output_dir: Path, log_file) -> dict:
    """
    分析单个案例，返回结果字典
    """
    log_msg = f"\n[{code} {name}] {date} ({label})"
    print(log_msg)
    log_file.write(log_msg + "\n")
    
    try:
        # 1. 环境检查
        passed, env_info = data_service.env_check()
        if not passed:
            raise Exception(f"环境检查失败: {env_info}")
        
        # 2. 验证数据存在
        exists, estimated = data_service.verify_tick_exists(code)
        if not exists:
            raise Exception(f"Tick数据不存在")
        
        # 3. 获取昨收价（唯一正确来源）
        pre_close = data_service.get_pre_close(code, date)
        if pre_close <= 0:
            raise Exception(f"无法获取昨收价")
        
        log_msg = f"  昨收价: {pre_close}"
        print(log_msg)
        log_file.write(log_msg + "\n")
        
        # 4. Tick回放
        formatted_code = data_service._format_code(code)
        start_time = date.replace('-', '') + '093000'
        end_time = date.replace('-', '') + '150000'
        
        provider = QMTHistoricalProvider(
            stock_code=formatted_code,
            start_time=start_time,
            end_time=end_time,
            period='tick'
        )
        
        # 5. 计算资金流
        calc = RollingFlowCalculator(windows=[1, 5, 15])
        results = []
        last_tick = None
        
        for tick in provider.iter_ticks():
            metrics = calc.add_tick(tick, last_tick)
            
            true_change = (tick['lastPrice'] - pre_close) / pre_close * 100
            
            results.append({
                'time': datetime.fromtimestamp(int(tick['time']) / 1000).strftime('%H:%M:%S'),
                'price': tick['lastPrice'],
                'true_change_pct': true_change,
                'flow_1min': metrics.flow_1min.total_flow,
                'flow_5min': metrics.flow_5min.total_flow,
                'flow_15min': metrics.flow_15min.total_flow,
            })
            last_tick = tick
        
        if not results:
            raise Exception("无Tick数据")
        
        df = pd.DataFrame(results)
        
        # 6. 保存原始数据
        label_str = 'true' if label == '真起爆' else 'trap'
        output_file = output_dir / f"{code}_{date}_{label_str}.csv"
        df.to_csv(output_file, index=False)
        
        # 7. 计算关键指标
        max_flow = df['flow_5min'].max()
        final_change = df['true_change_pct'].iloc[-1]
        max_change = df['true_change_pct'].max()
        
        log_msg = f"  ✅ 完成: 涨幅{final_change:.2f}%, 最大涨幅{max_change:.2f}%, 5min流{max_flow/1e6:.1f}M"
        print(log_msg)
        log_file.write(log_msg + "\n")
        
        return {
            'code': code,
            'name': name,
            'date': date,
            'label': label,
            'pre_close': pre_close,
            'final_change': final_change,
            'max_change': max_change,
            'max_flow_5min': max_flow,
            'tick_count': len(df),
            'status': 'success',
            'env_info': {
                'data_dir': env_info.get('data_dir'),
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        error_msg = f"  ❌ 失败: {str(e)}"
        print(error_msg)
        log_file.write(error_msg + "\n")
        return {
            'code': code,
            'name': name,
            'date': date,
            'label': label,
            'status': 'failed',
            'error': str(e)
        }


def run_pipeline(config_path: Path, output_dir: Path, log_dir: Path):
    """
    执行完整研究流水线
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 打开日志文件
    log_file_path = log_dir / f"pipeline_{timestamp}.log"
    
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        # 写入头信息
        header = f"""
{'='*80}
研究流水线执行日志
开始时间: {datetime.now().isoformat()}
配置文件: {config_path}
输出目录: {output_dir}
{'='*80}
"""
        print(header)
        log_file.write(header + "\n")
        
        # 1. 环境检查
        print("\n【1. 环境自检】")
        log_file.write("\n【1. 环境自检】\n")
        passed, env_info = data_service.env_check()
        
        if not passed:
            print("❌ 环境检查失败，终止执行")
            log_file.write("❌ 环境检查失败，终止执行\n")
            return
        
        print(f"✅ 环境检查通过")
        print(f"  数据目录: {env_info.get('data_dir')}")
        print(f"  深圳股票: {env_info.get('sz_stock_count')}只")
        print(f"  上海股票: {env_info.get('sh_stock_count')}只")
        
        log_file.write(f"✅ 环境检查通过\n")
        log_file.write(f"  数据目录: {env_info.get('data_dir')}\n")
        log_file.write(f"  深圳股票: {env_info.get('sz_stock_count')}只\n")
        log_file.write(f"  上海股票: {env_info.get('sh_stock_count')}只\n")
        
        # 2. 加载标签
        print("\n【2. 加载标签配置】")
        log_file.write("\n【2. 加载标签配置】\n")
        
        samples = load_labels(config_path)
        total_cases = sum(len(s.get('dates', [])) for s in samples)
        
        print(f"样本数: {len(samples)}只, 案例数: {total_cases}个")
        log_file.write(f"样本数: {len(samples)}只, 案例数: {total_cases}个\n")
        
        # 3. 执行分析
        print("\n【3. 执行Tick回放分析】")
        log_file.write("\n【3. 执行Tick回放分析】\n")
        
        results = []
        success_count = 0
        failed_count = 0
        
        for sample in samples:
            code = sample['code']
            name = sample['name']
            
            for date_info in sample.get('dates', []):
                if isinstance(date_info, dict):
                    date = date_info['date']
                    label = date_info['label']
                else:
                    # 跳过未标注的
                    continue
                
                result = analyze_single_case(code, name, date, label, output_dir, log_file)
                results.append(result)
                
                if result['status'] == 'success':
                    success_count += 1
                else:
                    failed_count += 1
        
        # 4. 保存汇总
        print("\n【4. 生成汇总报告】")
        log_file.write("\n【4. 生成汇总报告】\n")
        
        summary_df = pd.DataFrame([r for r in results if r['status'] == 'success'])
        if not summary_df.empty:
            summary_file = output_dir / f"analysis_summary_{timestamp}.csv"
            summary_df.to_csv(summary_file, index=False)
            print(f"✅ 汇总已保存: {summary_file}")
            log_file.write(f"✅ 汇总已保存: {summary_file}\n")
        
        # 5. 统计信息
        print("\n【5. 执行统计】")
        log_file.write("\n【5. 执行统计】\n")
        
        if not summary_df.empty and 'label' in summary_df.columns:
            for label in summary_df['label'].unique():
                subset = summary_df[summary_df['label'] == label]
                print(f"\n【{label}】样本数: {len(subset)}")
                print(f"  平均涨幅: {subset['final_change'].mean():.2f}%")
                print(f"  平均5分钟流: {subset['max_flow_5min'].mean()/1e6:.1f}M")
                
                log_file.write(f"\n【{label}】样本数: {len(subset)}\n")
                log_file.write(f"  平均涨幅: {subset['final_change'].mean():.2f}%\n")
                log_file.write(f"  平均5分钟流: {subset['max_flow_5min'].mean()/1e6:.1f}M\n")
        
        # 结尾
        footer = f"""
{'='*80}
执行完成
成功: {success_count}个, 失败: {failed_count}个
结束时间: {datetime.now().isoformat()}
{'='*80}
"""
        print(footer)
        log_file.write(footer + "\n")
    
    print(f"\n📄 完整日志: {log_file_path}")


def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='研究流水线总驱动')
    parser.add_argument('--config', type=str, 
                        default='data/wanzhu_data/research_sample_config.json',
                        help='标签配置文件路径')
    parser.add_argument('--output', type=str,
                        default='data/wanzhu_data/samples',
                        help='输出目录')
    parser.add_argument('--log', type=str,
                        default='logs/research_pipeline',
                        help='日志目录')
    
    args = parser.parse_args()
    
    config_path = PROJECT_ROOT / args.config
    output_dir = PROJECT_ROOT / args.output
    log_dir = PROJECT_ROOT / args.log
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    run_pipeline(config_path, output_dir, log_dir)


if __name__ == "__main__":
    main()
