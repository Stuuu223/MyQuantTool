#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究完整性校验器 V1.0
任何研究 CSV 在生成正式报告前，必须通过此校验

用法：
    python tasks/validate_research_integrity.py data/validation/violent_surge_v3_detailed.csv
"""

import sys
from pathlib import Path
import pandas as pd


INTEGRITY_RULES = {
    # 规则: (检查函数, 阈值, 比较方式, 失败说明)
    "T-1涨停率": (
        lambda df: df[df['lag']==-1]['is_limit_up'].mean() * 100,
        5.0,
        "<",
        "样本存在连板中间截片污染（T-1涨停率应<5%）"
    ),
    "T0涨停率": (
        lambda df: df[df['lag']==0]['is_limit_up'].mean() * 100,
        90.0,
        ">",
        "起爆日定义偏移（T0涨停率应>90%）"
    ),
    "T0下跌率": (
        lambda df: (df[df['lag']==0]['daily_return'] < -1).mean() * 100,
        5.0,
        "<",
        "起爆日存在下跌样本（T0下跌率应<5%）"
    ),
    "最小样本量": (
        lambda df: len(df[df['lag']==0]),
        50,
        ">",
        "样本量不足，结论统计意义低（应>=50）"
    ),
}


def validate(detail_csv_path: str) -> bool:
    """校验研究完整性"""
    df = pd.read_csv(detail_csv_path)
    
    print("=" * 60)
    print("研究完整性校验")
    print("=" * 60)
    print(f"文件: {detail_csv_path}")
    print(f"总记录: {len(df)}")
    
    samples = df[['stock_code', 'ignition_date']].drop_duplicates()
    print(f"独立样本: {len(samples)}")
    print()
    
    passed = True
    for rule_name, (check_fn, threshold, compare, msg) in INTEGRITY_RULES.items():
        try:
            value = check_fn(df)
        except Exception as e:
            print(f"❌ {rule_name}: 计算失败 ({e})")
            passed = False
            continue
        
        if compare == "<":
            ok = value < threshold
            comp_str = f"<{threshold}"
        else:
            ok = value >= threshold
            comp_str = f">={threshold}"
        
        status = "✅" if ok else "❌"
        print(f"{status} {rule_name}: {value:.1f}% (阈值{comp_str})")
        
        if not ok:
            print(f"   → {msg}")
            passed = False
    
    print("=" * 60)
    if passed:
        print("✅ 校验通过，可生成正式报告")
    else:
        print("❌ 校验失败，需修复样本或算法")
    
    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tasks/validate_research_integrity.py <detail_csv_path>")
        sys.exit(1)
    
    result = validate(sys.argv[1])
    sys.exit(0 if result else 1)
