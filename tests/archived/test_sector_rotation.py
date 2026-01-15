from logic.sector_rotation_analyzer import get_sector_rotation_analyzer
from datetime import datetime

analyzer = get_sector_rotation_analyzer()
date = datetime.now().strftime('%Y-%m-%d')
result = analyzer.calculate_sector_strength(date)

print(f'成功计算{len(result)}个板块的强度')
print('强度变化示例:')
for sector, strength in list(result.items())[:3]:
    print(f'{sector}: {strength.delta:.1f}')