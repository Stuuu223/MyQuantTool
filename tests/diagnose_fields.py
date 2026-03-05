"""
字段完整性诊断脚本 - 独立测试，不污染生产代码

【诊断目的】
验证 avg_turnover_5d 和 avg_amount_5d 在当前环境下的实际值

【运行方式】
cd E:\MyQuantTool
E:\MyQuantTool\venv_qmt\Scripts\python.exe tests/diagnose_fields.py
"""

import sys
sys.path.insert(0, 'E:/MyQuantTool')
sys.path.insert(0, 'E:/MyQuantTool/xtquant')

from datetime import datetime
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.data_providers.universe_builder import UniverseBuilder

def main():
    print("=" * 60)
    print("🔬 字段完整性诊断")
    print("=" * 60)
    
    # 1. 获取股票池
    print("\n【Step 1】获取股票池...")
    builder = UniverseBuilder()
    today = datetime.now().strftime('%Y%m%d')
    
    # 使用粗筛获取基础池
    stock_pool = builder.get_daily_universe(date=today, enable_ma_filter=False)
    print(f"粗筛池: {len(stock_pool)} 只")
    
    if not stock_pool:
        print("❌ 粗筛池为空，无法继续诊断")
        return
    
    # 2. 预热TrueDictionary
    print("\n【Step 2】预热TrueDictionary...")
    true_dict = get_true_dictionary(stock_pool, target_date=today, force=True)
    print(f"预热完成: {true_dict.is_ready()}")
    
    # 3. 字段完整性检查
    print("\n【Step 3】字段完整性检查...")
    
    # 取前20只做样本
    sample = stock_pool[:20]
    
    results = {
        'avg_volume_5d': [],
        'avg_turnover_5d': [],
        'float_volume': [],
        'prev_close': [],
    }
    
    for code in sample:
        results['avg_volume_5d'].append(true_dict.get_avg_volume_5d(code))
        results['avg_turnover_5d'].append(true_dict.get_avg_turnover_5d(code))
        results['float_volume'].append(true_dict.get_float_volume(code))
        results['prev_close'].append(true_dict.get_prev_close(code))
    
    print("\n📊 诊断结果（前20只样本）:")
    print("-" * 40)
    
    for field, values in results.items():
        valid = sum(1 for v in values if v and v > 0)
        zero = sum(1 for v in values if v == 0)
        none_nan = sum(1 for v in values if v is None or (isinstance(v, float) and str(v) == 'nan'))
        print(f"  {field}:")
        print(f"    有效: {valid}/20")
        print(f"    零值: {zero}/20")
        print(f"    None/NaN: {none_nan}/20")
    
    # 4. 详细查看一只股票
    print("\n【Step 4】详细诊断（第一只股票）...")
    first_code = sample[0]
    print(f"股票代码: {first_code}")
    print(f"  avg_volume_5d: {true_dict.get_avg_volume_5d(first_code)}")
    print(f"  avg_turnover_5d: {true_dict.get_avg_turnover_5d(first_code)}")
    print(f"  float_volume: {true_dict.get_float_volume(first_code)}")
    print(f"  prev_close: {true_dict.get_prev_close(first_code)}")
    
    # 5. 全池统计
    print("\n【Step 5】全池统计（可能需要较长时间）...")
    full_stats = {
        'avg_volume_5d_valid': 0,
        'avg_turnover_5d_valid': 0,
        'float_volume_valid': 0,
    }
    
    for code in stock_pool:
        if true_dict.get_avg_volume_5d(code) > 0:
            full_stats['avg_volume_5d_valid'] += 1
        if true_dict.get_avg_turnover_5d(code) > 0:
            full_stats['avg_turnover_5d_valid'] += 1
        if true_dict.get_float_volume(code) > 0:
            full_stats['float_volume_valid'] += 1
    
    print(f"\n📊 全池统计:")
    print(f"  avg_volume_5d 有效: {full_stats['avg_volume_5d_valid']}/{len(stock_pool)}")
    print(f"  avg_turnover_5d 有效: {full_stats['avg_turnover_5d_valid']}/{len(stock_pool)}")
    print(f"  float_volume 有效: {full_stats['float_volume_valid']}/{len(stock_pool)}")
    
    print("\n" + "=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)

if __name__ == '__main__':
    main()