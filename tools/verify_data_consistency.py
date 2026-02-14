"""
数据一致性验证工具
对比 QMT 实时数据 vs 历史 CSV 数据
确认数据存储/读取是否损坏或格式错误
"""
import sys
from pathlib import Path
import pandas as pd
from xtquant import xtdata
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 配置
HISTORICAL_DATA_DIR = PROJECT_ROOT / "data/minute_data_real"
REPORT_FILE = PROJECT_ROOT / "data_consistency_report.json"

def verify_consistency(stock_code: str, date: str = "2026-02-13") -> dict:
    """
    验证单个股票的数据一致性
    
    Args:
        stock_code: 股票代码（如 '600519.SH'）
        date: 对比日期（格式：YYYY-MM-DD）
    
    Returns:
        {
            'stock_code': str,
            'date': str,
            'qmt_data': dict,
            'historical_data': dict,
            'diff': dict,
            'is_consistent': bool,
            'errors': list
        }
    """
    print(f"\n{'='*80}")
    print(f"验证股票: {stock_code} | 日期: {date}")
    print(f"{'='*80}")
    
    errors = []
    
    # 1. 获取 QMT 实时数据
    print("  [1/3] 获取 QMT 实时数据...")
    try:
        start_time = date.replace('-', '') + '093000'
        end_time = date.replace('-', '') + '150000'
        
        df_qmt = xtdata.get_market_data_ex(
            field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1m',
            start_time=start_time,
            end_time=end_time
        )
        
        if stock_code not in df_qmt or df_qmt[stock_code].empty:
            error_msg = f"QMT数据为空"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
            return {
                'stock_code': stock_code,
                'date': date,
                'qmt_data': None,
                'historical_data': None,
                'diff': None,
                'is_consistent': False,
                'errors': errors
            }
        
        qmt_df = df_qmt[stock_code].copy()
        qmt_df['datetime'] = pd.to_datetime(qmt_df['time'], format='%Y%m%d%H%M%S')
        qmt_df['date'] = qmt_df['datetime'].dt.strftime('%Y-%m-%d')
        
        print(f"    ✅ QMT数据加载成功: {len(qmt_df)} 行")
        
    except Exception as e:
        error_msg = f"获取QMT数据失败: {e}"
        print(f"    ❌ {error_msg}")
        errors.append(error_msg)
        return {
            'stock_code': stock_code,
            'date': date,
            'qmt_data': None,
            'historical_data': None,
            'diff': None,
            'is_consistent': False,
            'errors': errors
        }
    
    # 2. 获取历史 CSV 数据
    print("  [2/3] 获取历史 CSV 数据...")
    try:
        # 查找历史数据文件
        csv_files = list(HISTORICAL_DATA_DIR.rglob(f"{stock_code}_1m.csv"))
        
        if not csv_files:
            error_msg = f"未找到历史CSV文件"
            print(f"    ❌ {error_msg}")
            errors.append(error_msg)
            return {
                'stock_code': stock_code,
                'date': date,
                'qmt_data': None,
                'historical_data': None,
                'diff': None,
                'is_consistent': False,
                'errors': errors
            }
        
        csv_file = csv_files[0]
        hist_df = pd.read_csv(csv_file)
        hist_df['datetime'] = pd.to_datetime(hist_df['time_str'])
        hist_df['date'] = hist_df['datetime'].dt.strftime('%Y-%m-%d')
        
        print(f"    ✅ 历史CSV数据加载成功: {len(hist_df)} 行")
        
    except Exception as e:
        error_msg = f"获取历史CSV数据失败: {e}"
        print(f"    ❌ {error_msg}")
        errors.append(error_msg)
        return {
            'stock_code': stock_code,
            'date': date,
            'qmt_data': None,
            'historical_data': None,
            'diff': None,
            'is_consistent': False,
            'errors': errors
        }
    
    # 3. 对比数据
    print("  [3/3] 对比数据一致性...")
    
    # 筛选指定日期的数据
    qmt_daily = qmt_df[qmt_df['date'] == date]
    hist_daily = hist_df[hist_df['date'] == date]
    
    if len(qmt_daily) != len(hist_daily):
        error_msg = f"数据行数不一致: QMT={len(qmt_daily)}, CSV={len(hist_daily)}"
        print(f"    ❌ {error_msg}")
        errors.append(error_msg)
    
    # 提取关键指标
    qmt_first = qmt_daily.iloc[0] if len(qmt_daily) > 0 else None
    qmt_last = qmt_daily.iloc[-1] if len(qmt_daily) > 0 else None
    
    hist_first = hist_daily.iloc[0] if len(hist_daily) > 0 else None
    hist_last = hist_daily.iloc[-1] if len(hist_daily) > 0 else None
    
    qmt_metrics = {
        'open': qmt_first['open'] if qmt_first is not None else None,
        'close': qmt_last['close'] if qmt_last is not None else None,
        'high': qmt_daily['high'].max() if len(qmt_daily) > 0 else None,
        'low': qmt_daily['low'].min() if len(qmt_daily) > 0 else None,
        'volume': qmt_daily['volume'].sum() if len(qmt_daily) > 0 else None,
        'amount': qmt_daily['amount'].sum() if len(qmt_daily) > 0 else None
    } if qmt_first is not None else None
    
    hist_metrics = {
        'open': hist_first['open'] if hist_first is not None else None,
        'close': hist_last['close'] if hist_last is not None else None,
        'high': hist_daily['high'].max() if len(hist_daily) > 0 else None,
        'low': hist_daily['low'].min() if len(hist_daily) > 0 else None,
        'volume': hist_daily['volume'].sum() if len(hist_daily) > 0 else None,
        'amount': hist_daily['amount'].sum() if len(hist_daily) > 0 else None
    } if hist_first is not None else None
    
    print(f"    QMT数据: 开盘={qmt_metrics['open']:.2f}, 收盘={qmt_metrics['close']:.2f}, 最高={qmt_metrics['high']:.2f}, 最低={qmt_metrics['low']:.2f}")
    print(f"    CSV数据: 开盘={hist_metrics['open']:.2f}, 收盘={hist_metrics['close']:.2f}, 最高={hist_metrics['high']:.2f}, 最低={hist_metrics['low']:.2f}")
    
    # 计算差异
    diff = {}
    is_consistent = True
    
    if qmt_metrics is not None and hist_metrics is not None:
        for key in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            qmt_val = qmt_metrics[key]
            hist_val = hist_metrics[key]
            
            if qmt_val is not None and hist_val is not None:
                if qmt_val == 0:
                    diff_pct = 0
                else:
                    diff_pct = abs((qmt_val - hist_val) / qmt_val) * 100
                
                diff[key] = {
                    'qmt': qmt_val,
                    'historical': hist_val,
                    'diff_pct': diff_pct
                }
                
                # 检查是否超过阈值（0.1%）
                if diff_pct > 0.1:
                    is_consistent = False
                    error_msg = f"{key}差异过大: {diff_pct:.4f}% (阈值: 0.1%)"
                    print(f"    ⚠️  {error_msg}")
                    errors.append(error_msg)
    
    if is_consistent and len(errors) == 0:
        print(f"    ✅ 数据一致性验证通过")
    else:
        print(f"    ❌ 数据一致性验证失败，发现 {len(errors)} 个问题")
    
    return {
        'stock_code': stock_code,
        'date': date,
        'qmt_data': qmt_metrics,
        'historical_data': hist_metrics,
        'diff': diff,
        'is_consistent': is_consistent,
        'errors': errors
    }

def main():
    """主函数"""
    print("=" * 80)
    print("数据一致性验证工具")
    print("=" * 80)
    
    # 测试股票列表（从不同子目录选择）
    test_stocks = [
        '600519.SH',  # 贵州茅台（large_cap）
        '300182.SZ',  # 东方财富（mid_cap）
        '000001.SZ',  # 平安银行（small_cap）
        '002842.SZ',  # 中科通达
        '000858.SZ',  # 五粮液
        '600036.SH',  # 招商银行
        '300750.SZ',  # 宁波银行
        '601888.SH',  # 中国平安
        '002271.SZ',  # 东方雨虹
        '603697.SH',  # 中国人保
    ]
    
    test_date = '2026-02-13'
    
    results = []
    consistent_count = 0
    inconsistent_count = 0
    
    for stock_code in test_stocks:
        result = verify_consistency(stock_code, test_date)
        results.append(result)
        
        if result['is_consistent']:
            consistent_count += 1
        else:
            inconsistent_count += 1
    
    # 生成报告
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)
    print(f"测试股票数: {len(test_stocks)}")
    print(f"数据一致: {consistent_count} 只")
    print(f"数据不一致: {inconsistent_count} 只")
    print(f"一致性率: {consistent_count / len(test_stocks) * 100:.1f}%")
    
    # 保存报告
    report = {
        'test_date': test_date,
        'test_stocks': test_stocks,
        'results': results,
        'summary': {
            'total': len(test_stocks),
            'consistent': consistent_count,
            'inconsistent': inconsistent_count,
            'consistency_rate': consistent_count / len(test_stocks) * 100
        }
    }
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存: {REPORT_FILE}")
    
    # CTO 决策依据
    print("\n" + "=" * 80)
    print("CTO 决策依据")
    print("=" * 80)
    
    if consistent_count == len(test_stocks):
        print("✅ 数据完全一致，说明数据存储/读取没有问题")
        print("⚠️  问题可能出在：回测逻辑或策略本身")
        print("   - 检查回测代码是否有Bug")
        print("   - 检查是否存在未来函数泄漏")
        print("   - 分析77%止损的具体原因")
    elif inconsistent_count > len(test_stocks) * 0.5:
        print("❌ 数据严重不一致，说明数据存储/读取有问题")
        print("⚠️  必须先修复数据问题，再进行回测")
        print("   - 检查历史CSV文件的存储格式")
        print("   - 重新下载历史数据")
    else:
        print("⚠️  部分数据不一致，需要进一步调查")
        print("   - 检查不一致的股票是否有共同特征")
        print("   - 检查是否是特定时间或特定类型股票的问题")

if __name__ == "__main__":
    main()