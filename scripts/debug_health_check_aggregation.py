#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速诊断脚本：检查 QMT 健康检查的聚合逻辑"""

import json

# 测试聚合逻辑
result = {
    'status': 'UNKNOWN',
    'details': {
        'qmt_client': {'status': 'OK', 'message': 'QMT 客户端已启动'},
        'server_login': {'status': 'OK', 'message': '行情主站已连接', 'logged_in': True},
        'market_status': {'status': 'OK', 'is_trading_time': True},
        'trading_status': {'status': 'OK', 'is_trading_time': True},
        'data_mode': {'status': 'OK', 'data_mode': 'REALTIME_SUBSCRIPTION'}
    },
    'recommendations': []
}

print("=" * 80)
print("当前聚合逻辑测试")
print("=" * 80)
print(f"初始状态: {result['status']}")
print(f"子检查状态:")
for name, check in result['details'].items():
    print(f"  - {name}: {check.get('status')}")
print()

# 模拟旧逻辑
print("旧逻辑测试:")
if result['status'] != 'ERROR' and result['status'] != 'WARNING':
    result['status'] = 'HEALTHY'
    result['recommendations'].append('✅ QMT 状态正常，可以进行实时决策')
print(f"  结果状态: {result['status']}")
print(f"  建议: {result['recommendations']}")
print()

# 重置状态
result['status'] = 'UNKNOWN'
result['recommendations'] = []

# 模拟新逻辑
print("新逻辑测试:")
errors = []
warnings = []
for check_name, check_result in result['details'].items():
    if check_result.get('status') == 'ERROR':
        errors.append(f'{check_name}: {check_result.get("message", "未知错误")}')
    elif check_result.get('status') == 'WARNING':
        warnings.append(f'{check_name}: {check_result.get("message", "未知警告")}')

if errors:
    result['status'] = 'ERROR'
    result['recommendations'] = [f'❌ {err}' for err in errors]
elif warnings:
    result['status'] = 'WARNING'
    result['recommendations'] = [f'⚠️  {warn}' for warn in warnings]
else:
    result['status'] = 'HEALTHY'
    result['recommendations'].append('✅ QMT 状态正常，可以进行实时决策')

print(f"  结果状态: {result['status']}")
print(f"  建议: {result['recommendations']}")

print()
print("=" * 80)
print("结论:")
print("旧逻辑: ✅ 正常（因为 status='UNKNOWN' 不等于 ERROR/WARNING，所以改为 HEALTHY）")
print("新逻辑: ✅ 正常（因为 errors/warnings 都为空，所以改为 HEALTHY）")
print()
print("🔥 问题诊断：")
print("你的日志显示 '整体状态: ❌ ERROR'，说明某个子检查返回了 ERROR 或 WARNING")
print("但所有子检查都显示 OK，这说明可能存在以下问题之一：")
print("1. 某个子检查返回了 ERROR/WARNING，但在日志中没有显示")
print("2. result['status'] 在聚合逻辑执行前被设置为 ERROR")
print("3. 聚合逻辑的 if 条件判断有 bug")
print()
print("建议：在 check_all() 返回前添加调试输出：")
print("print(f'DEBUG: result[\"status\"]={result[\"status\"]}')")
print("print(f'DEBUG: result[\"details\"]={json.dumps(result[\"details\"], ensure_ascii=False, indent=2)}')")