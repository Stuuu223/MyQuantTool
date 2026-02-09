"""测试QMT状态自检"""
import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from logic.qmt_health_check import check_qmt_health

result = check_qmt_health()

print("\n" + "="*80)
print("最终状态:", result['status'])
print("="*80)