"""
个股分析工具（整合版）
整合 QMT 历史数据、QMT Tick 数据和资金流向分析
提供完整的个股技术面和资金面分析
支持单日和多日分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data.fund_flow_analyzer import analyze_fund_flow, FundFlowAnalyzer
from logic.multi_day_analysis import analyze_multi_day


def analyze_stock_single(stock_code: str, use_qmt: bool = True) -> str:
    """
    单日个股分析

    Args:
        stock_code: 股票代码
        use_qmt: 是否使用 QMT 数据

    Returns:
        格式化的分析报告
    """
    # from logic.stock_analyzer_original import StockAnalyzer

    analyzer = StockAnalyzer()
    result = analyzer.analyze_stock(stock_code, use_qmt)
    return analyzer.format_analysis(result)


def analyze_stock_multi_day(stock_code: str, days: int = 10) -> str:
    """
    多日资金流向分析

    Args:
        stock_code: 股票代码
        days: 分析最近几天

    Returns:
        格式化的分析报告
    """
    return analyze_multi_day(stock_code, days)


def analyze_stock_comprehensive(stock_code: str, days: int = 10, use_qmt: bool = True) -> str:
    """
    综合分析（单日技术面 + 多日资金面）

    Args:
        stock_code: 股票代码
        days: 资金流向分析天数
        use_qmt: 是否使用 QMT 技术面数据

    Returns:
        完整的综合分析报告
    """
    report = f"""
{'='*80}
## 综合个股分析报告

**股票代码**: {stock_code}
**分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{'='*80}

"""

    # 单日技术面分析
    if use_qmt:
        try:
            report += "### 📊 单日技术面分析\n\n"
            report += analyze_stock_single(stock_code, use_qmt=True)
            report += "\n"
        except Exception as e:
            report += "### 📊 单日技术面分析\n\n"
            report += f"⚠️ 获取 QMT 技术面数据失败: {e}\n\n"
    else:
        # 使用资金流向分析代替
        report += "### 📊 单日资金流向分析\n\n"
        from logic.data.fund_flow_analyzer import FundFlowAnalyzer
        analyzer = FundFlowAnalyzer()
        result = analyzer.analyze_fund_flow(stock_code)
        report += analyzer.format_analysis(result)
        report += "\n"

    # 多日资金流向分析
    report += f"{'='*80}\n\n"
    report += f"### 📈 多日资金流向趋势分析\n\n"
    report += analyze_multi_day(stock_code, days)

    return report


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) > 2 else "multi"

        if mode == "single":
            print(analyze_stock_single(stock_code))
        elif mode == "multi":
            print(analyze_stock_multi_day(stock_code))
        elif mode == "comprehensive":
            print(analyze_stock_comprehensive(stock_code))
        else:
            print(f"未知模式: {mode}")
            print("可用模式: single, multi, comprehensive")
    else:
        stock_code = "300997"
        print(analyze_stock_multi_day(stock_code))
