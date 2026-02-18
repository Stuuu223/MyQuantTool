"""
顽主杯股票名称到代码映射补全工具

使用akshare根据名称模糊匹配股票代码
"""
import pandas as pd
import akshare as ak
from pathlib import Path
import json
from typing import Dict, Optional

def load_unmapped_stocks(csv_path: Path) -> pd.DataFrame:
    """加载未映射的股票"""
    df = pd.read_csv(csv_path)
    # 找出code为空的记录
    unmapped = df[df['code'].isna() | (df['code'] == '')]['name'].unique()
    return pd.DataFrame({'name': unmapped})

def search_stock_code(name: str) -> Optional[str]:
    """使用akshare搜索股票代码"""
    try:
        # 尝试精确匹配
        stock_info = ak.stock_info_a_code_name()
        match = stock_info[stock_info['name'] == name]
        if not match.empty:
            return match.iloc[0]['code']
        
        # 尝试模糊匹配（名称包含）
        match = stock_info[stock_info['name'].str.contains(name, na=False)]
        if not match.empty:
            return match.iloc[0]['code']
        
        # 尝试反向模糊匹配（被包含）
        match = stock_info[stock_info['name'].apply(lambda x: name in x if pd.notna(x) else False)]
        if not match.empty:
            return match.iloc[0]['code']
        
        return None
    except Exception as e:
        print(f"搜索 {name} 失败: {e}")
        return None

def build_mapping(wanzhu_csv: Path, output_json: Path):
    """构建名称到代码的映射"""
    print("=" * 60)
    print("🔍 顽主杯股票代码映射补全")
    print("=" * 60)
    
    # 1. 加载未映射股票
    unmapped_df = load_unmapped_stocks(wanzhu_csv)
    print(f"\n发现 {len(unmapped_df)} 只未映射股票")
    
    # 2. 加载现有映射
    existing_mapping = {}
    if output_json.exists():
        with open(output_json, 'r', encoding='utf-8') as f:
            existing_mapping = json.load(f)
        print(f"已有映射: {len(existing_mapping)} 条")
    
    # 3. 逐个搜索
    new_mappings = {}
    failed_names = []
    
    print("\n🌐 开始搜索股票代码...")
    for idx, row in unmapped_df.iterrows():
        name = row['name']
        
        # 跳过已存在的
        if name in existing_mapping:
            continue
        
        code = search_stock_code(name)
        if code:
            new_mappings[name] = code
            print(f"  ✅ {name} -> {code}")
        else:
            failed_names.append(name)
            print(f"  ❌ {name} -> 未找到")
    
    # 4. 合并并保存
    all_mappings = {**existing_mapping, **new_mappings}
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 映射已保存: {output_json}")
    print(f"  新增映射: {len(new_mappings)} 条")
    print(f"  总计映射: {len(all_mappings)} 条")
    print(f"  映射失败: {len(failed_names)} 只")
    
    if failed_names:
        print(f"\n⚠️ 映射失败的股票（需人工处理）:")
        for name in failed_names[:10]:
            print(f"  - {name}")
        if len(failed_names) > 10:
            print(f"  ... 还有 {len(failed_names) - 10} 只")
    
    return all_mappings

if __name__ == '__main__':
    wanzhu_csv = Path('data/wanzhu_history_from_api.csv')
    output_json = Path('config/wanzhu_name_to_code_mapping.json')
    
    build_mapping(wanzhu_csv, output_json)
