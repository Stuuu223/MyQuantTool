#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分钟K线数据拉取工具 - 解决样本丢失问题

功能：
1. 从QMT服务器下载1分钟K线数据到本地缓存
2. 读取本地缓存数据进行策略回测
3. 数据完整性验证

优势：
- 无需L2权限（所有QMT用户免费）
- 数据可补全（不会永久丢失）
- 数据量小（5000只股票/天约20MB）
- 适合诱多检测和趋势分析

Author: iFlow CLI
Date: 2026-02-09
"""

import time
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    print("❌ xtquant 未安装，无法使用 QMT 数据源")
    print("   请安装：pip install xtquant")
    QMT_AVAILABLE = False
    sys.exit(1)


def fetch_minute_data(
    code_list: List[str],
    start_date: str = None,
    end_date: str = None,
    verbose: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    拉取1分钟K线数据
    
    Args:
        code_list: 股票代码列表，如 ['600519.SH', '000001.SZ']
        start_date: 开始日期，格式 'YYYYMMDD'，默认为7天前
        end_date: 结束日期，格式 'YYYYMMDD'，默认为今天
        verbose: 是否打印详细信息
    
    Returns:
        字典，key为股票代码，value为DataFrame
    """
    if not QMT_AVAILABLE:
        return {}
    
    # 默认日期范围：过去7天
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if verbose:
        print("=" * 80)
        print("🚀 开始拉取1分钟K线数据")
        print("=" * 80)
        print(f"📅 时间范围: {start_date} ~ {end_date}")
        print(f"📊 股票数量: {len(code_list)}")
        print()
    
    # 第1步：强制下载数据到本地缓存
    if verbose:
        print("📥 第1步：从QMT服务器下载数据到本地缓存...")
    
    try:
        xtdata.download_history_data(
            stock_list=code_list,
            period='1m',
            start_time=start_date,
            end_time=end_date
        )
        if verbose:
            print("✅ 下载完成")
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return {}
    
    # 第2步：从本地缓存读取数据
    if verbose:
        print()
        print("📖 第2步：从本地缓存读取数据...")
    
    try:
        data = xtdata.get_market_data(
            field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=code_list,
            period='1m',
            start_time=start_date,
            end_time=end_date,
            count=-1,  # -1 表示取时间段内所有数据
            dividend_type='none',  # 不复权（回测通常用前复权 'front'）
            fill_data=True  # 填充停牌数据
        )
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return {}
    
    # 第3步：转换和验证数据
    result = {}
    
    for code in code_list:
        if code in data and data[code] is not None:
            df = data[code]
            
            if not df.empty:
                # 转换时间戳为可读时间
                df['time_str'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                result[code] = df
                
                if verbose:
                    print(f"✅ {code}: 获取到 {len(df)} 根分钟K线")
            else:
                if verbose:
                    print(f"⚠️  {code}: 数据为空")
        else:
            if verbose:
                print(f"❌ {code}: 数据获取失败")
    
    if verbose:
        print()
        print("=" * 80)
        print("📊 数据拉取完成")
        print(f"成功: {len(result)}/{len(code_list)} 只股票")
        print("=" * 80)
    
    return result


def verify_data_integrity(
    data_dict: Dict[str, pd.DataFrame],
    expected_days: int = 7
) -> Dict[str, any]:
    """
    验证数据完整性
    
    Args:
        data_dict: 股票数据字典
        expected_days: 预期天数（用于计算预期的K线数量）
    
    Returns:
        验证结果字典
    """
    print()
    print("=" * 80)
    print("🔍 数据完整性验证")
    print("=" * 80)
    
    # 交易日约5天/周，每天约240根K线（4小时交易）
    expected_bars = expected_days * 240
    
    results = {
        'total_stocks': len(data_dict),
        'valid_stocks': 0,
        'incomplete_stocks': 0,
        'missing_stocks': 0,
        'details': []
    }
    
    for code, df in data_dict.items():
        actual_bars = len(df)
        completeness = actual_bars / expected_bars * 100
        
        status = '✅ 完整' if completeness >= 80 else '⚠️ 不完整'
        
        result_detail = {
            'code': code,
            'actual_bars': actual_bars,
            'expected_bars': expected_bars,
            'completeness': completeness,
            'status': status
        }
        
        results['details'].append(result_detail)
        
        if completeness >= 80:
            results['valid_stocks'] += 1
        elif completeness > 0:
            results['incomplete_stocks'] += 1
        else:
            results['missing_stocks'] += 1
        
        print(f"{code}: {actual_bars:4d} 根K线 ({completeness:5.1f}%) {status}")
    
    print()
    print(f"✅ 完整: {results['valid_stocks']}/{results['total_stocks']}")
    print(f"⚠️  不完整: {results['incomplete_stocks']}/{results['total_stocks']}")
    print(f"❌ 缺失: {results['missing_stocks']}/{results['total_stocks']}")
    print("=" * 80)
    
    return results


def save_data_to_csv(
    data_dict: Dict[str, pd.DataFrame],
    output_dir: str = 'data/minute_data'
):
    """
    保存数据到CSV文件
    
    Args:
        data_dict: 股票数据字典
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print()
    print("=" * 80)
    print("💾 保存数据到CSV")
    print("=" * 80)
    
    for code, df in data_dict.items():
        file_path = output_path / f"{code}_1m.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"✅ {code} → {file_path}")
    
    print("=" * 80)


def load_data_from_csv(
    input_dir: str = 'data/minute_data'
) -> Dict[str, pd.DataFrame]:
    """
    从CSV文件加载数据
    
    Args:
        input_dir: 输入目录
    
    Returns:
        字典，key为股票代码，value为DataFrame
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ 目录不存在: {input_path}")
        return {}
    
    print()
    print("=" * 80)
    print("📂 从CSV加载数据")
    print("=" * 80)
    
    result = {}
    
    for file_path in input_path.glob('*_1m.csv'):
        code = file_path.stem.replace('_1m', '')
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            result[code] = df
            print(f"✅ {code}: {len(df)} 根K线")
        except Exception as e:
            print(f"❌ {code}: 加载失败 - {e}")
    
    print("=" * 80)
    return result


def analyze_first_stock(data_dict: Dict[str, pd.DataFrame]):
    """
    分析第一只股票的数据
    
    Args:
        data_dict: 股票数据字典
    """
    if not data_dict:
        print("❌ 没有数据可分析")
        return
    
    first_code = list(data_dict.keys())[0]
    df = data_dict[first_code]
    
    print()
    print("=" * 80)
    print(f"📊 {first_code} 数据分析")
    print("=" * 80)
    print()
    
    # 基本统计
    print("📌 基本信息:")
    print(f"   股票代码: {first_code}")
    print(f"   K线数量: {len(df)}")
    print(f"   时间范围: {df['time_str'].min()} ~ {df['time_str'].max()}")
    print()
    
    # 前5根和后5根
    print("📈 前5根K线:")
    print(df[['time_str', 'open', 'high', 'low', 'close', 'volume']].head())
    print()
    
    print("📉 后5根K线:")
    print(df[['time_str', 'open', 'high', 'low', 'close', 'volume']].tail())
    print()
    
    # 统计信息
    print("📊 统计信息:")
    print(f"   平均成交量: {df['volume'].mean():.0f}")
    print(f"   最大成交量: {df['volume'].max():.0f}")
    print(f"   平均振幅: {((df['high'] - df['low']) / df['close'] * 100).mean():.2f}%")
    print("=" * 80)


def main():
    """主函数"""
    print()
    print("=" * 80)
    print("🔧 MyQuantTool - 分钟K线数据拉取工具")
    print("=" * 80)
    print()
    print("✅ 无需L2权限（所有QMT用户免费）")
    print("✅ 数据可补全（解决样本丢失问题）")
    print("✅ 数据量小（5000只股票/天约20MB）")
    print()
    
    # 测试股票列表（可替换为你的股票池）
    test_stocks = [
        '600519.SH',  # 贵州茅台
        '000001.SZ',  # 平安银行
        '300997.SZ',  # 欢乐家
        '002099.SZ',  # 海翔药业
        '301150.SZ',  # 中船汉光
    ]
    
    # 拉取数据
    data = fetch_minute_data(
        code_list=test_stocks,
        start_date='20260201',  # 2月1日
        end_date='20260209',    # 2月9日
        verbose=True
    )
    
    if not data:
        print("❌ 没有获取到数据，请检查QMT连接")
        return
    
    # 验证数据完整性
    verify_data_integrity(data, expected_days=7)
    
    # 分析第一只股票
    analyze_first_stock(data)
    
    # 保存到CSV
    save_data_to_csv(data, 'data/minute_data')
    
    print()
    print("✅ 数据拉取完成！")
    print()
    print("📝 下一步:")
    print("   1. 使用这些数据进行策略回测")
    print("   2. 对比Tick数据，验证数据完整性")
    print("   3. 集成到你的扫描器中")


if __name__ == "__main__":
    main()