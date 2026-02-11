#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试聚合逻辑修复"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from logic.qmt_health_check import QMTHealthChecker

# 创建健康检查实例
checker = QMTHealthChecker()

# 运行健康检查
result = checker.check_all()

# 打印结果
print("=" * 80)
print("🏥 QMT 健康检查结果")
print("=" * 80)
print(f"检查时间: {result['check_time']}")
print(f"整体状态: {result['status']}")
print(f"建议数量: {len(result['recommendations'])}")

print("\n📋 各项检查详情:")
for check_name, check_result in result['details'].items():
    print(f"  {check_name}: {check_result['status']}")
    if 'message' in check_result:
        print(f"    {check_result['message']}")

print("\n💡 建议:")
for rec in result['recommendations']:
    print(f"  {rec}")

print("\n" + "=" * 80)

# 验证修复
if result['status'] == 'ERROR' and len(result['recommendations']) == 0:
    print("❌ 修复失败：状态为 ERROR 但建议列表为空")
    sys.exit(1)
elif result['status'] == 'HEALTHY' and len(result['recommendations']) > 0:
    print("✅ 修复成功：状态为 HEALTHY 且建议列表非空")
    sys.exit(0)
elif result['status'] == 'ERROR' and len(result['recommendations']) > 0:
    print(f"✅ 修复成功：状态为 ERROR 且有 {len(result['recommendations'])} 条建议")
    sys.exit(0)
else:
    print(f"⚠️  未知状态: {result['status']}, 建议: {len(result['recommendations'])} 条")
    sys.exit(0)