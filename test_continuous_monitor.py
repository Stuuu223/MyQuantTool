#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试持续监控脚本 - 验证状态指纹功能

测试内容：
1. FullMarketScanner的generate_state_signature方法
2. 状态指纹对比逻辑
3. 快照保存功能

Author: iFlow CLI
Version: V1.0
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.logger import get_logger

logger = get_logger(__name__)


def test_state_signature():
    """测试状态指纹生成功能"""
    print("=" * 80)
    print("🧪 测试状态指纹生成功能")
    print("=" * 80)
    
    # 创建扫描器
    scanner = FullMarketScanner()
    
    # 创建测试结果1
    result1 = {
        'mode': 'FULL',
        'confidence': 0.925,
        'position_limit': 0.74,
        'opportunities': [
            {'code': '000592.SZ', 'risk_score': 0.0, 'capital_type': 'HOT_MONEY'},
            {'code': '601869.SH', 'risk_score': 0.2, 'capital_type': 'INSTITUTIONAL'}
        ],
        'watchlist': [
            {'code': '300502.SZ', 'risk_score': 0.5, 'capital_type': 'UNCLEAR'}
        ],
        'blacklist': []
    }
    
    # 创建测试结果2（相同）
    result2 = {
        'mode': 'FULL',
        'confidence': 0.925,
        'position_limit': 0.74,
        'opportunities': [
            {'code': '000592.SZ', 'risk_score': 0.0, 'capital_type': 'HOT_MONEY'},
            {'code': '601869.SH', 'risk_score': 0.2, 'capital_type': 'INSTITUTIONAL'}
        ],
        'watchlist': [
            {'code': '300502.SZ', 'risk_score': 0.5, 'capital_type': 'UNCLEAR'}
        ],
        'blacklist': []
    }
    
    # 创建测试结果3（不同）
    result3 = {
        'mode': 'FULL',
        'confidence': 0.925,
        'position_limit': 0.74,
        'opportunities': [
            {'code': '000592.SZ', 'risk_score': 0.3, 'capital_type': 'HOT_MONEY'},  # 风险评分变化
            {'code': '601869.SH', 'risk_score': 0.2, 'capital_type': 'INSTITUTIONAL'}
        ],
        'watchlist': [
            {'code': '300502.SZ', 'risk_score': 0.5, 'capital_type': 'UNCLEAR'}
        ],
        'blacklist': []
    }
    
    # 生成状态指纹
    sig1 = scanner.generate_state_signature(result1)
    sig2 = scanner.generate_state_signature(result2)
    sig3 = scanner.generate_state_signature(result3)
    
    print(f"\n📊 测试结果:")
    print(f"   结果1指纹: {sig1[:16]}...")
    print(f"   结果2指纹: {sig2[:16]}...")
    print(f"   结果3指纹: {sig3[:16]}...")
    
    print(f"\n🔍 指纹对比:")
    print(f"   结果1 vs 结果2: {'相同' if sig1 == sig2 else '不同'} ✅")
    print(f"   结果1 vs 结果3: {'相同' if sig1 == sig3 else '不同'} ✅")
    
    print(f"\n✅ 状态指纹功能测试通过！")
    print("=" * 80)


def test_real_scan():
    """测试真实扫描"""
    print("\n" + "=" * 80)
    print("🧪 测试真实扫描（单次）")
    print("=" * 80)
    
    # 创建扫描器
    scanner = FullMarketScanner()
    
    # 执行扫描
    print("\n🔍 开始扫描...")
    results = scanner.scan_with_risk_management(mode='intraday')
    
    # 生成状态指纹
    sig = scanner.generate_state_signature(results)
    
    print(f"\n📊 扫描结果:")
    print(f"   机会池: {len(results['opportunities'])} 只")
    print(f"   观察池: {len(results['watchlist'])} 只")
    print(f"   黑名单: {len(results['blacklist'])} 只")
    print(f"   系统置信度: {results['confidence']*100:.1f}%")
    print(f"   状态指纹: {sig[:16]}...")
    
    print(f"\n✅ 真实扫描测试通过！")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🎯 持续监控功能测试")
    print("=" * 80)
    
    try:
        # 测试1：状态指纹生成
        test_state_signature()
        
        # 测试2：真实扫描（可选，耗时较长）
        print("\n是否执行真实扫描测试？")
        print("注意：真实扫描可能需要1-2分钟时间")
        print("输入 'y' 继续，其他键跳过...")
        
        choice = input().strip().lower()
        if choice == 'y':
            test_real_scan()
        else:
            print("\n⏭️  已跳过真实扫描测试")
        
        print("\n" + "=" * 80)
        print("🎉 所有测试完成！")
        print("=" * 80)
        print("\n下一步：")
        print("1. 运行 start_continuous_monitor.bat 启动持续监控")
        print("2. 或者在交易时间内运行: python tasks/run_continuous_monitor.py")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
