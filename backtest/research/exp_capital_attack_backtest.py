#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金攻击策略实验脚本

实验目的：验证资金攻击检测在热门票上的效果
数据来源：config/exp_capital_attack_config.json（禁止硬编码）

Author: AI团队
Date: 2026-02-18
Status: EXPERIMENTAL
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)

# 加载实验配置（禁止在此文件硬编码阈值）
CONFIG_PATH = Path("config/exp_capital_attack_config.json")

def load_config() -> Dict:
    """加载实验配置"""
    if not CONFIG_PATH.exists():
        # 创建默认配置
        default_config = {
            "experiment": "capital_attack",
            "version": "0.1.0",
            "thresholds": {
                "main_inflow_min": 100000000,  # 1亿（默认，可调）
                "price_strength_min": 0.05,     # 5%（默认，可调）
                "score_threshold": 0.5          # 触发阈值（默认，可调）
            },
            "scoring": {
                "inflow_weight": 0.5,
                "strength_weight": 0.5
            },
            "note": "所有阈值可调，禁止硬编码在脚本中"
        }
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 创建默认配置: {CONFIG_PATH}")
        return default_config
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

class CapitalAttackExperiment:
    """资金攻击实验"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.thresholds = config['thresholds']
        self.scoring = config['scoring']
        
    def calculate_score(self, main_inflow: float, price_strength: float) -> float:
        """
        计算资金攻击评分
        
        Args:
            main_inflow: 主力净流入（元）
            price_strength: 价格强度（相对开盘涨幅）
        
        Returns:
            float: 0-1评分
        """
        score = 0.0
        
        # 资金维度
        if main_inflow >= self.thresholds['main_inflow_min']:
            score += self.scoring['inflow_weight']
        
        # 强度维度
        if price_strength >= self.thresholds['price_strength_min']:
            score += self.scoring['strength_weight']
        
        return score
    
    def analyze_stock_day(self, code: str, date: str) -> Dict:
        """
        分析单日资金攻击情况
        
        Returns:
            Dict: {
                'code': 股票代码,
                'date': 日期,
                'main_inflow': 主力净流入,
                'price_strength': 价格强度,
                'score': 资金攻击评分,
                'is_attack': 是否触发资金攻击,
                'data_quality': 数据质量
            }
        """
        try:
            # 获取Tick数据
            start_time = f"{date}093000"
            end_time = f"{date}150000"
            provider = QMTHistoricalProvider(code, start_time, end_time)
            
            # 推断资金流
            flow_data = provider.estimate_main_flow_from_ticks()
            
            main_inflow = flow_data.get('main_net_inflow', 0)
            price_strength = flow_data.get('price_strength', 0)
            
            # 计算评分
            score = self.calculate_score(main_inflow, price_strength)
            is_attack = score >= self.thresholds['score_threshold']
            
            return {
                'code': code,
                'date': date,
                'main_inflow': main_inflow,
                'price_strength': price_strength,
                'score': score,
                'is_attack': is_attack,
                'data_quality': 'ok'
            }
            
        except Exception as e:
            logger.error(f"❌ 分析失败 {code} {date}: {e}")
            return {
                'code': code,
                'date': date,
                'main_inflow': 0,
                'price_strength': 0,
                'score': 0,
                'is_attack': False,
                'data_quality': f'error: {e}'
            }
    
    def run_experiment(self, test_cases: List[Dict]) -> pd.DataFrame:
        """
        运行实验
        
        Args:
            test_cases: 测试用例列表 [{code, date, expected}]
        
        Returns:
            pd.DataFrame: 实验结果
        """
        results = []
        
        for case in test_cases:
            code = case['code']
            date = case['date']
            expected = case.get('expected', 'unknown')
            
            logger.info(f"🔍 分析: {code} {date}")
            result = self.analyze_stock_day(code, date)
            result['expected'] = expected
            results.append(result)
        
        df = pd.DataFrame(results)
        return df
    
    def generate_report(self, df: pd.DataFrame) -> str:
        """生成实验报告"""
        report = []
        report.append("="*70)
        report.append("📊 资金攻击实验报告")
        report.append("="*70)
        report.append(f"实验时间: {datetime.now()}")
        report.append(f"样本数: {len(df)}")
        report.append(f"配置: {CONFIG_PATH}")
        report.append("")
        
        # 触发率统计
        attack_count = df['is_attack'].sum()
        attack_rate = attack_count / len(df) * 100 if len(df) > 0 else 0
        report.append(f"📈 触发统计:")
        report.append(f"   触发资金攻击: {attack_count}/{len(df)} ({attack_rate:.1f}%)")
        report.append("")
        
        # 详细结果
        report.append("📋 详细结果:")
        for _, row in df.iterrows():
            status = "🔥" if row['is_attack'] else "❌"
            report.append(
                f"   {status} {row['code']} {row['date']} | "
                f"净流入={row['main_inflow']/1e4:.0f}万 | "
                f"强度={row['price_strength']:.3f} | "
                f"评分={row['score']:.2f} | "
                f"预期={row['expected']}"
            )
        
        report.append("")
        report.append("="*70)
        return "\n".join(report)


def run_wangsu_test():
    """网宿科技测试（1月26日涨停日）"""
    config = load_config()
    experiment = CapitalAttackExperiment(config)
    
    test_cases = [
        {
            'code': '300017.SZ',
            'date': '20260126',  # 涨停日
            'expected': '应该触发（巨量资金+大涨）'
        },
        {
            'code': '300017.SZ',
            'date': '20260127',  # 起爆次日
            'expected': '应该触发（资金持续）'
        },
        {
            'code': '300017.SZ',
            'date': '20260205',  # 节后
            'expected': '应该触发（延续强势）'
        }
    ]
    
    df = experiment.run_experiment(test_cases)
    report = experiment.generate_report(df)
    print(report)
    
    # 保存结果
    output_path = Path("backtest/results/exp_capital_attack_wangsu.csv")
    df.to_csv(output_path, index=False)
    print(f"\n💾 结果保存: {output_path}")
    
    return df


def run_wanzhu_test():
    """顽主杯131只票测试"""
    config = load_config()
    experiment = CapitalAttackExperiment(config)
    
    # 加载顽主票列表（统一使用wanzhu_selected_150.csv）
    wanzhu_csv = Path("data/wanzhu_data/processed/wanzhu_selected_150.csv")
    if not wanzhu_csv.exists():
        logger.error(f"❌ 找不到顽主票列表: {wanzhu_csv}")
        return pd.DataFrame()
    
    import pandas as pd
    wanzhu_df = pd.read_csv(wanzhu_csv)
    wanzhu_codes = wanzhu_df['code'].tolist()
    
    # 构建测试用例（2月4-13日真实数据区间）
    test_cases = []
    dates = ['20260204', '20260205', '20260206', '20260207', 
             '20260210', '20260211', '20260212', '20260213']
    
    for code in wanzhu_codes[:20]:  # 先测前20只
        for date in dates:
            test_cases.append({
                'code': code,
                'date': date,
                'expected': '看实际表现'
            })
    
    logger.info(f"🎯 顽主杯测试: {len(test_cases)} 个样本")
    df = experiment.run_experiment(test_cases)
    report = experiment.generate_report(df)
    print(report)
    
    # 保存结果
    output_path = Path("backtest/results/exp_capital_attack_wanzhu.csv")
    df.to_csv(output_path, index=False)
    print(f"\n💾 结果保存: {output_path}")
    
    return df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='资金攻击实验')
    parser.add_argument('--test', choices=['wangsu', 'wanzhu', 'all'], 
                       default='wangsu', help='测试类型')
    
    args = parser.parse_args()
    
    if args.test == 'wangsu':
        run_wangsu_test()
    elif args.test == 'wanzhu':
        run_wanzhu_test()
    elif args.test == 'all':
        run_wangsu_test()
        print("\n" + "="*70 + "\n")
        run_wanzhu_test()
