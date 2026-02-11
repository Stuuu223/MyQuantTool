#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试主线起爆候选白名单修复

验证：
1. 主线起爆候选能从黑名单拯救到机会池
2. 风险评分较低的主线起爆候选不会被误判为TRAP_PUMP_DUMP
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json


def test_mainline_whitelist():
    """测试主线起爆候选白名单逻辑"""

    # 模拟Level 3分类结果
    level3_result = {
        'opportunities': [],
        'watchlist': [],
        'blacklist': [
            {
                'code': '605088.SH',
                'name': '凯盛新材',
                'risk_score': 0.00,
                'scenario_reasons': ['多日资金流健康', '主线起爆候选'],
                'is_potential_mainline': True,
                'scenario_type': 'MAINLINE_RALLY',
                'scenario_confidence': 0.90
            },
            {
                'code': '000719.SZ',
                'name': '中核钛白',
                'risk_score': 0.00,
                'scenario_reasons': ['多日资金流健康', '主线起爆候选'],
                'is_potential_mainline': True,
                'scenario_type': 'MAINLINE_RALLY',
                'scenario_confidence': 0.90
            },
            {
                'code': '300364.SZ',
                'name': '中文在线',
                'risk_score': 0.90,
                'scenario_reasons': ['检测到拉高出货模式'],
                'is_potential_mainline': False,
                'scenario_type': 'TRAP_PUMP_DUMP',
                'scenario_confidence': 0.80
            }
        ]
    }

    # 导入FullMarketScanner
    from logic.full_market_scanner import FullMarketScanner

    # 创建扫描器实例（使用默认配置）
    scanner = FullMarketScanner()

    # 应用最终过滤
    final_result = scanner.apply_final_filters(level3_result)

    # 验证结果
    print("=" * 80)
    print("主线起爆候选白名单测试")
    print("=" * 80)
    print()

    print("输入：")
    print(f"  机会池: {len(level3_result['opportunities'])} 只")
    print(f"  观察池: {len(level3_result['watchlist'])} 只")
    print(f"  黑名单: {len(level3_result['blacklist'])} 只")
    print(f"    - 605088.SH (主线起爆候选, risk=0.00)")
    print(f"    - 000719.SZ (主线起爆候选, risk=0.00)")
    print(f"    - 300364.SZ (拉高出货, risk=0.90)")
    print()

    print("输出：")
    print(f"  机会池: {len(final_result['opportunities'])} 只")
    for stock in final_result['opportunities']:
        print(f"    - {stock['code']} ({stock['name']}) risk={stock['risk_score']:.2f}")
    print(f"  观察池: {len(final_result['watchlist'])} 只")
    for stock in final_result['watchlist']:
        print(f"    - {stock['code']} ({stock['name']}) risk={stock['risk_score']:.2f}")
    print(f"  黑名单: {len(final_result['blacklist'])} 只")
    for stock in final_result['blacklist']:
        print(f"    - {stock['code']} ({stock['name']}) risk={stock['risk_score']:.2f}")
    print()

    # 验证断言
    assert len(final_result['opportunities']) == 2, f"期望2只机会池，实际{len(final_result['opportunities'])}只"
    assert final_result['opportunities'][0]['code'] == '605088.SH', f"期望605088.SH，实际{final_result['opportunities'][0]['code']}"
    assert final_result['opportunities'][1]['code'] == '000719.SZ', f"期望000719.SZ，实际{final_result['opportunities'][1]['code']}"
    assert len(final_result['blacklist']) == 1, f"期望1只黑名单，实际{len(final_result['blacklist'])}只"
    assert final_result['blacklist'][0]['code'] == '300364.SZ', f"期望300364.SZ，实际{final_result['blacklist'][0]['code']}"

    print("✅ 测试通过！")
    print("=" * 80)


if __name__ == "__main__":
    test_mainline_whitelist()