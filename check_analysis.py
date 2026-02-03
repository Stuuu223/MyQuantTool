import json
import glob
import os

files = glob.glob('data/stock_analysis/300997/*_analysis.json')
files.sort(reverse=True)

print("最近的5个分析文件:")
for f in files[:5]:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        price = data.get('layer1_realtime', {}).get('price', 0)
        data_source = data.get('layer1_realtime', {}).get('data_source', 'N/A')
        
        print(f"{os.path.basename(f)}: 价格={price}, 数据源={data_source}")
    except Exception as e:
        print(f"{os.path.basename(f)}: 错误={e}")