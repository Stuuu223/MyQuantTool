#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票AI分析工具 - 兼容性包装器

此模块为向后兼容而保留，实际功能委托给 EnhancedStockAnalyzer。

推荐使用:
    from tools.enhanced_stock_analyzer import EnhancedStockAnalyzer
    analyzer = EnhancedStockAnalyzer()
    result = analyzer.comprehensive_analysis('300997', days=60)

兼容用法:
    from tools.stock_ai_tool import analyze_stock
    result = analyze_stock('300997', days=60)

Author: MyQuantTool Team
Date: 2026-02-19
Version: V1.0 (Wrapper)
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 委托给增强版分析器
from tools.enhanced_stock_analyzer import EnhancedStockAnalyzer


def analyze_stock(code: str, days: int = 60, output_all_data: bool = True) -> Dict[str, Any]:
    """
    分析股票数据（兼容接口）

    Args:
        code: 股票代码（6位数字，如 '300997'）
        days: 分析天数，默认60天
        output_all_data: 是否输出所有数据

    Returns:
        包含分析结果的字典

    Raises:
        ValueError: 当股票代码格式不正确时
        Exception: 分析过程中的其他错误

    Example:
        >>> result = analyze_stock('300997', days=60)
        >>> print(result.get('fund_flow', {}).get('trend', 'UNKNOWN'))
    """
    if not code or not isinstance(code, str):
        raise ValueError(f"股票代码必须是字符串，收到: {type(code)}")

    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"股票代码格式不正确，应为6位数字，收到: {code}")

    # 创建分析器实例
    analyzer = EnhancedStockAnalyzer(use_qmt=True)

    # 执行综合分析
    result = analyzer.comprehensive_analysis(
        stock_code=code,
        days=days,
        output_all_data=output_all_data,
        pure_data=False
    )

    # 如果返回的是字符串（报告格式），包装成字典
    if isinstance(result, str):
        return {
            'success': True,
            'stock_code': code,
            'report': result,
            'note': '返回格式为文本报告，如需结构化数据请直接使用 EnhancedStockAnalyzer'
        }

    return result


def quick_analyze(code: str) -> Dict[str, str]:
    """
    快速分析股票（简化接口）

    Args:
        code: 股票代码（6位数字）

    Returns:
        简化的分析结果字典
    """
    analyzer = EnhancedStockAnalyzer(use_qmt=True)

    # 执行纯数据分析（无主观判断）
    result = analyzer.comprehensive_analysis(
        stock_code=code,
        days=30,
        output_all_data=False,
        pure_data=True
    )

    if isinstance(result, str):
        return {'stock_code': code, 'status': 'report_generated', 'preview': result[:200]}

    # 提取关键信息
    fund_flow = result.get('fund_flow', {})
    trap = result.get('trap_detection', {})

    return {
        'stock_code': code,
        'trend': fund_flow.get('trend', 'UNKNOWN'),
        'risk_score': str(trap.get('comprehensive_risk_score', 'N/A')),
        'capital_type': result.get('capital_classification', {}).get('type', 'UNKNOWN'),
        'status': 'success'
    }


# 向后兼容：如果直接运行脚本
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='股票AI分析工具')
    parser.add_argument('code', help='股票代码（如 300997）')
    parser.add_argument('--days', type=int, default=60, help='分析天数（默认60）')
    parser.add_argument('--quick', action='store_true', help='快速模式（仅关键指标）')

    args = parser.parse_args()

    try:
        if args.quick:
            result = quick_analyze(args.code)
            print(f"\n股票代码: {result['stock_code']}")
            print(f"资金趋势: {result['trend']}")
            print(f"风险评分: {result['risk_score']}")
            print(f"资金类型: {result['capital_type']}")
        else:
            result = analyze_stock(args.code, days=args.days)
            if 'report' in result:
                print(result['report'])
            else:
                import json
                print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        sys.exit(1)
