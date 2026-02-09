#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分钟K线回测测试工具

功能：
1. 验证数据完整性
2. 执行简单回测策略
3. 生成回测报告

Author: iFlow CLI
Date: 2026-02-09
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_minute_data(data_dir: str = 'data/minute_data') -> Dict[str, pd.DataFrame]:
    """加载分钟K线数据"""
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {data_path}")
        return {}
    
    print()
    print("=" * 80)
    print(f"📂 加载分钟K线数据: {data_path}")
    print("=" * 80)
    
    result = {}
    
    for file_path in data_path.glob('*_1m.csv'):
        code = file_path.stem.replace('_1m', '')
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            result[code] = df
            print(f"✅ {code}: {len(df)} 根K线")
        except Exception as e:
            print(f"❌ {code}: 加载失败 - {e}")
    
    print()
    print(f"📊 加载完成: {len(result)} 只股票")
    print("=" * 80)
    
    return result


def verify_data_integrity(data_dict: Dict[str, pd.DataFrame]):
    """验证数据完整性"""
    print()
    print("=" * 80)
    print("🔍 数据完整性验证")
    print("=" * 80)
    
    # 期望数量根据数据长度而定，不再硬编码 5082
    # expected_bars = 5082  
    
    for code, df in data_dict.items():
        # 检查数据量
        actual_bars = len(df)
        # completeness = actual_bars / expected_bars * 100
        
        # 检查缺失值
        missing_values = df.isnull().sum().sum()
        
        # 检查价格合理性
        # 兼容不同列名
        cols = ['open', 'high', 'low', 'close']
        existing_cols = [c for c in cols if c in df.columns]
        
        negative_prices = 0
        zero_prices = 0
        
        if existing_cols:
            negative_prices = (df[existing_cols] < 0).sum().sum()
            zero_prices = (df[existing_cols] == 0).sum().sum()
        
        print(f"\n📌 {code}:")
        print(f"   K线数量: {actual_bars}")
        print(f"   缺失值: {missing_values}")
        print(f"   负价格: {negative_prices}")
        print(f"   零价格: {zero_prices}")
        
        # 时间范围
        if 'time_str' in df.columns:
            try:
                df['time_str'] = pd.to_datetime(df['time_str'])
                time_range = f"{df['time_str'].min()} ~ {df['time_str'].max()}"
                print(f"   时间范围: {time_range}")
            except:
                pass
    
    print()
    print("=" * 80)


def analyze_data_statistics(data_dict: Dict[str, pd.DataFrame]):
    """数据分析"""
    print()
    print("=" * 80)
    print("📊 数据统计分析")
    print("=" * 80)
    
    for code, df in data_dict.items():
        print(f"\n📌 {code}:")
        
        # 基本统计
        avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
        max_volume = df['volume'].max() if 'volume' in df.columns else 0
        avg_amount = df['amount'].mean() if 'amount' in df.columns else 0
        
        # 振幅统计
        if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100
            avg_amplitude = df['amplitude'].mean()
            max_amplitude = df['amplitude'].max()
            
            print(f"   平均成交量: {avg_volume:,.0f}")
            print(f"   最大成交量: {max_volume:,.0f}")
            print(f"   平均成交额: {avg_amount:,.0f}")
            print(f"   平均振幅: {avg_amplitude:.2f}%")
            print(f"   最大振幅: {max_amplitude:.2f}%")
    
    print()
    print("=" * 80)


def run_simple_backtest(data_dict: Dict[str, pd.DataFrame]):
    """运行简单回测策略"""
    print()
    print("=" * 80)
    print("🧪 回测策略测试")
    print("=" * 80)
    print()
    print("策略描述:")
    print("   - 当收盘价 > 5日均线 * 1.01 时买入")
    print("   - 当收盘价 < 5日均线 * 0.99 时卖出")
    print()
    
    results = {}
    
    for code, df in data_dict.items():
        print(f"\n📌 {code}:")
        
        if 'close' not in df.columns:
            print("   ❌ 缺少收盘价数据")
            continue

        # 计算5日均线 (240分钟 * 5 = 1200分钟)
        # 这里为了演示，使用 240 分钟 (约1天) 作为周期
        df['ma5'] = df['close'].rolling(window=240*5).mean()
        
        # 初始化状态
        position = False  # 是否持仓
        buy_price = 0.0
        trades = []
        total_return = 0.0
        
        # 逐分钟回测
        # 确保数据足够计算MA
        start_idx = 240*5
        if len(df) <= start_idx:
            print("   ⚠️ 数据量不足以计算5日均线")
            continue

        for i in range(start_idx, len(df)): 
            current_price = df.iloc[i]['close']
            ma5 = df.iloc[i]['ma5']
            
            if pd.isna(ma5):
                continue

            if not position:
                # 没有持仓，检查买入条件
                if current_price > ma5 * 1.01:  # 收盘价高于5日均线的1%
                    position = True
                    buy_price = current_price
                    time_str = df.iloc[i]['time_str'] if 'time_str' in df.columns else str(i)
                    trades.append({
                        'type': 'BUY',
                        'price': current_price,
                        'time': time_str
                    })
                    # print(f"   买入: {current_price:.2f} @ {time_str}")
            else:
                # 持仓中，检查卖出条件
                if current_price < ma5 * 0.99:  # 收盘价低于5日均线的0.99
                    position = False
                    profit_pct = (current_price - buy_price) / buy_price * 100
                    total_return += profit_pct
                    time_str = df.iloc[i]['time_str'] if 'time_str' in df.columns else str(i)
                    trades.append({
                        'type': 'SELL',
                        'price': current_price,
                        'time': time_str,
                        'profit_pct': profit_pct
                    })
                    # print(f"   卖出: {current_price:.2f} @ {time_str} (收益: {profit_pct:.2f}%)")
        
        # 统计结果
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        win_trades = [t for t in sell_trades if t['profit_pct'] > 0]
        
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        results[code] = {
            'trades': len(trades) // 2,
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_return': total_return / len(sell_trades) if sell_trades else 0
        }
        
        print(f"   交易次数: {results[code]['trades']}")
        print(f"   胜率: {results[code]['win_rate']:.1f}%")
        print(f"   总收益率: {results[code]['total_return']:.2f}%")
        print(f"   平均收益率: {results[code]['avg_return']:.2f}%")
    
    print()
    print("=" * 80)
    
    return results


def generate_backtest_report(data_dict: Dict[str, pd.DataFrame], backtest_results: Dict):
    """生成回测报告"""
    report = []
    
    report.append("# 分钟K线回测报告")
    report.append("")
    report.append(f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**数据来源**: 模拟/QMT数据")
    report.append("")
    
    report.append("## 3. 回测策略结果")
    report.append("")
    report.append("### 策略说明")
    report.append("- 买入条件：收盘价 > 5日均线 * 1.01")
    report.append("- 卖出条件：收盘价 < 5日均线 * 0.99")
    report.append("")
    
    for code, result in backtest_results.items():
        report.append(f"### {code}")
        report.append(f"- 交易次数: {result['trades']}")
        report.append(f"- 胜率: {result['win_rate']:.1f}%")
        report.append(f"- 总收益率: {result['total_return']:.2f}%")
        report.append(f"- 平均收益率: {result['avg_return']:.2f}%")
        report.append("")
    
    # 保存报告
    report_path = Path('data/backtest_1m_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print()
    print("=" * 80)
    print("📝 回测报告已生成")
    print(f"📄 报告路径: {report_path}")
    print("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='分钟K线回测工具')
    parser.add_argument('--data-dir', type=str, default='data/minute_data_mock', help='数据目录路径')
    args = parser.parse_args()

    print()
    print("=" * 80)
    print("🧪 MyQuantTool - 分钟K线回测测试")
    print("=" * 80)
    print()
    
    # 加载数据
    data = load_minute_data(args.data_dir)
    
    if not data:
        print("❌ 没有数据可回测")
        return
    
    # 验证数据完整性
    verify_data_integrity(data)
    
    # 数据统计分析
    analyze_data_statistics(data)
    
    # 运行回测
    backtest_results = run_simple_backtest(data)
    
    # 生成报告
    generate_backtest_report(data, backtest_results)
    
    print()
    print("✅ 回测测试完成！")


if __name__ == "__main__":
    main()
