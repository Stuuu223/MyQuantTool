"""
应用顽主杯股票代码映射到数据文件
"""
import pandas as pd
import json
from pathlib import Path

def apply_mapping(wanzhu_csv: Path, mapping_json: Path, output_csv: Path):
    """应用代码映射"""
    print("=" * 60)
    print("🔗 应用顽主杯代码映射")
    print("=" * 60)
    
    # 1. 加载数据
    df = pd.read_csv(wanzhu_csv)
    print(f"\n原始数据: {len(df)} 条记录")
    
    # 2. 加载映射
    with open(mapping_json, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    print(f"映射表: {len(mapping)} 条")
    
    # 3. 应用映射（只填充空的code）
    def get_code(row):
        if pd.notna(row['code']) and row['code'] != '':
            return row['code']
        name = row['name']
        code = mapping.get(name, '')
        if code and not code.endswith('.SH') and not code.endswith('.SZ'):
            # 添加市场后缀
            if code.startswith('6'):
                code = code + '.SH'
            else:
                code = code + '.SZ'
        return code
    
    df['code'] = df.apply(get_code, axis=1)
    
    # 4. 统计
    mapped_count = df[df['code'].notna() & (df['code'] != '')].shape[0]
    print(f"\n映射后:")
    print(f"  有代码: {mapped_count} 条 ({mapped_count/len(df)*100:.1f}%)")
    print(f"  无代码: {len(df) - mapped_count} 条 ({(len(df)-mapped_count)/len(df)*100:.1f}%)")
    
    # 5. 保存
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n💾 已保存: {output_csv}")
    
    return df

if __name__ == '__main__':
    wanzhu_csv = Path('data/wanzhu_history_from_api.csv')
    mapping_json = Path('config/wanzhu_name_to_code_mapping.json')
    output_csv = Path('data/wanzhu_history_mapped.csv')
    
    apply_mapping(wanzhu_csv, mapping_json, output_csv)
