"""
AI 便捷接口
让 AI 可以轻松调用个股分析工具
"""
from tools.comprehensive_stock_tool import comprehensive_stock_analysis, quick_analysis
from tools.enhanced_stock_analyzer import analyze_stock_enhanced, analyze_stock_json
import json
import os
from datetime import datetime


def get_analysis_file_path(stock_code, days, mode='analyze'):
    """
    生成分析文件路径（自动创建文件夹）

    Args:
        stock_code: 股票代码
        days: 分析天数
        mode: 分析模式（用于文件命名）

    Returns:
        str: 文件路径
    """
    # 基础目录（使用相对路径）
    base_dir = 'data/stock_analysis'

    # 按股票代码分类
    stock_dir = os.path.join(base_dir, stock_code)

    # 确保目录存在
    os.makedirs(stock_dir, exist_ok=True)

    # 生成文件名：股票代码_日期_天数days[_mode].json
    # 添加详细时间戳（包含时分秒）便于追踪
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    if mode == 'enhanced':
        filename = f"{stock_code}_{date_str}_{days}days_enhanced.json"
    elif mode == 'supplement':
        filename = f"{stock_code}_{date_str}_{days}days_supplement.json"
    else:
        filename = f"{stock_code}_{date_str}_{days}days.json"

    file_path = os.path.join(stock_dir, filename)

    return file_path


def save_analysis_result(result, stock_code, days, mode='analyze'):
    """
    保存分析结果到文件（自动归类）

    Args:
        result: 分析结果（dict）
        stock_code: 股票代码
        days: 分析天数
        mode: 分析模式（用于文件命名）

    Returns:
        str: 保存的文件路径
    """
    file_path = get_analysis_file_path(stock_code, days, mode)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return file_path


def analyze_stock(stock_code, days=10, mode='analyze', use_qmt=None, output_all_data=False, pure_data=False, auto_save=False):
    """
    分析个股（AI 便捷接口）

    Args:
        stock_code: 股票代码（如 '300997'）
        days: 分析最近几天（默认10天）
        mode: 分析模式
            - 'analyze' 或 'full': 完整分析（AkShare资金流向 + QMT技术指标，默认）
            - 'quick': 快速分析（仅核心指标）
            - 'akshare': 仅AkShare分析（资金流向）
            - 'qmt': 仅QMT分析（技术指标，不含资金流向）
            - 'json': 返回JSON格式的结构化数据（AkShare+QMT，便于AI处理）
            - 'enhanced': 增强分析模式（包含滚动指标、诱多检测、资金性质分类、风险评分）
            - 'supplement': QMT补充数据（换手率、Tick验证、分时均线、盘口数据）
        use_qmt: 是否使用 QMT 数据（None=根据模式自动判断，True=强制使用，False=强制不使用）
        output_all_data: 是否输出所有数据（仅在非json模式有效）
        pure_data: 是否只输出纯数据（不包含主观判断和建议，仅在json模式有效）
        auto_save: 是否自动保存到文件（仅在json模式有效，默认False）

    Returns:
        str: 分析报告（非json模式）或dict（json模式）
        如果auto_save=True，还会返回文件路径

    Examples:
        # 默认分析（AkShare+QMT）
        result = analyze_stock('300997', days=60)
        print(result)

        # 快速分析
        result = analyze_stock('301171', days=5, mode='quick')
        print(result)

        # 仅AkShare分析
        result = analyze_stock('300997', days=60, mode='akshare')
        print(result)

        # 仅QMT分析
        result = analyze_stock('300997', days=60, mode='qmt')
        print(result)

        # JSON格式分析（包含主观判断）
        result = analyze_stock('300997', days=60, mode='json')
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # JSON格式分析（纯数据，不包含主观判断）
        result = analyze_stock('300997', days=60, mode='json', pure_data=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # JSON格式分析（自动保存）
        result, file_path = analyze_stock('300997', days=60, mode='json', auto_save=True)
        print(f"数据已保存到: {file_path}")
    """
    # 根据模式自动决定是否使用QMT
    if use_qmt is None:
        if mode in ['analyze', 'full', 'json']:
            use_qmt = True
        elif mode == 'akshare':
            use_qmt = False
        elif mode == 'qmt':
            use_qmt = True
        else:
            use_qmt = False

    if mode == 'quick':
        result = quick_analysis(stock_code, days)
        if auto_save:
            return result, None
        return result
    elif mode in ['analyze', 'full']:
        result = analyze_stock_enhanced(stock_code, days=days, use_qmt=use_qmt, output_all_data=output_all_data, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    elif mode == 'akshare':
        result = analyze_stock_enhanced(stock_code, days=days, use_qmt=False, output_all_data=output_all_data, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    elif mode == 'qmt':
        result = analyze_stock_enhanced(stock_code, days=days, use_qmt=True, output_all_data=output_all_data, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    elif mode == 'json':
        result = analyze_stock_json(stock_code, days=days, use_qmt=use_qmt, auto_download=True, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    elif mode == 'enhanced':
        result = analyze_stock_json(stock_code, days=days, use_qmt=use_qmt, auto_download=True, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    elif mode == 'supplement':
        # QMT 补充数据模式（换手率、Tick验证、分时均线、盘口数据）
        from logic.qmt_supplement import get_qmt_supplement
        result = get_qmt_supplement(stock_code, days=days)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result
    else:
        # 默认为分析模式
        result = analyze_stock_enhanced(stock_code, days=days, use_qmt=True, output_all_data=output_all_data, pure_data=pure_data)
        if auto_save:
            file_path = save_analysis_result(result, stock_code, days, mode)
            return result, file_path
        return result


def analyze_stock_structured(stock_code, days=60, use_qmt=True, auto_download=True):
    """
    分析个股（返回结构化JSON数据 - 便于AI调用）

    这个函数返回一个包含所有分析数据的字典，便于AI程序化处理。

    Args:
        stock_code: 股票代码（如 '300997'）
        days: 分析天数（默认60天）
        use_qmt: 是否使用 QMT 数据（默认True）
        auto_download: 是否自动下载QMT数据（如果未找到，默认True）

    Returns:
        dict: 包含以下结构的数据：
            {
                'stock_code': '300997',
                'analyze_time': '2026-02-02 18:00:00',
                'analyze_days': 60,
                'fund_flow': {
                    'data_range': '2025-08-06 至 2026-02-02',
                    'total_days': 60,
                    'bullish_days': 21,
                    'bearish_days': 39,
                    'total_institution': -15258.43,
                    'total_retail': 15258.43,
                    'trend': 'strong_bearish',
                    'daily_data': [
                        {
                            'date': '2025-11-10',
                            'super_large': 20089.25,
                            'large': -2980.01,
                            'medium': -9557.33,
                            'small': -7551.90,
                            'institution': 17109.24,
                            'retail': -17109.24,
                            'signal': '吸筹',
                            'signal_type': 'BULLISH',
                            'description': '机构吸筹，散户恐慌'
                        },
                        ...
                    ]
                },
                'qmt': {
                    'data_range': '2025-08-06 至 2026-02-02',
                    'total_days': 60,
                    'latest': {
                        'close': 25.50,
                        'pct_chg': 2.35,
                        'volume': 15000000,
                        'MA5': 25.20,
                        'MA10': 25.00,
                        'MA20': 24.80,
                        'BIAS_5': 1.19,
                        'BIAS_10': 2.00,
                        'RSI': 58.5,
                        'MACD': 0.15,
                        'MACD_SIGNAL': 0.10,
                        'MACD_HIST': 0.05
                    },
                    'daily_data': [
                        {
                            'date': '2025-11-10',
                            'close': 25.50,
                            'open': 25.00,
                            'high': 25.80,
                            'low': 24.90,
                            'volume': 15000000,
                            'pct_chg': 2.35,
                            'MA5': 25.20,
                            'MA10': 25.00,
                            'MA20': 24.80,
                            'BIAS_5': 1.19,
                            'BIAS_10': 2.00,
                            'RSI': 58.5,
                            'MACD': 0.15
                        },
                        ...
                    ]
                },
                'summary': {
                    'fund_strength': '弱势',
                    'tech_strength': '强势',
                    'recommendation': '谨慎观望'
                }
            }

    Examples:
        # 获取结构化数据（默认AkShare+QMT）
        result = analyze_stock_structured('300997', days=60)

        # 仅使用AkShare数据
        result = analyze_stock_structured('300997', days=60, use_qmt=False)

        # 输出JSON格式
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 访问特定数据
        print(f"趋势: {result['fund_flow']['trend']}")
        print(f"建议: {result['summary']['recommendation']}")
        print(f"最近一天: {result['fund_flow']['daily_data'][-1]}")

        # 遍历每日数据
        for day in result['fund_flow']['daily_data']:
            print(f"{day['date']}: {day['signal']} - {day['description']}")
    """
    result = analyze_stock_json(stock_code, days=days, use_qmt=use_qmt, auto_download=auto_download, pure_data=True)

    if auto_save:
        file_path = save_analysis_result(result, stock_code, days, mode)
        return result, file_path

    return result


def ask_more_days(days=10):
    """
    询问用户是否需要更久的数据

    Args:
        days: 当前分析的天数

    Returns:
        str: 提示信息

    Examples:
        ask_more_days(10)
        # 输出：是否需要查看更长时间的数据？可选项：30天、60天、90天
    """
    options = [30, 60, 90]
    return f"\n💡 是否需要查看更长时间的数据？可选项：{options} 天\n   使用命令：analyze_stock('股票代码', days={options[0]})"


# 便捷别名
analyze = analyze_stock
quick = quick_analysis


def batch_analyze_stocks(stock_codes, days=60, mode='json', auto_save=True, pure_data=True):
    """
    批量分析多只股票

    Args:
        stock_codes: 股票代码列表
        days: 分析天数
        mode: 分析模式
        auto_save: 是否自动保存到文件
        pure_data: 是否使用纯数据模式

    Returns:
        list: [(stock_code, result, file_path), ...]
    """
    results = []
    
    for stock_code in stock_codes:
        try:
            result = analyze_stock(stock_code, days=days, mode=mode, pure_data=pure_data, auto_save=auto_save)
            if auto_save:
                result, file_path = result
                results.append((stock_code, result, file_path))
            else:
                results.append((stock_code, result, None))
        except Exception as e:
            print(f"分析 {stock_code} 失败: {e}")
            results.append((stock_code, None, None))
    
    return results


def get_qmt_supplement(stock_code: str, days: int = 1, auto_save: bool = False):
    """
    获取 QMT 补充数据（便捷函数）

    Args:
        stock_code: 股票代码
        days: 换手率数据天数（默认1天）
        auto_save: 是否自动保存到文件

    Returns:
        dict: 补充数据，包含：
            - turnover_rate: 换手率数据
            - tick_validation: Tick成交验证
            - intraday_ma_1m: 1分钟分时均线
            - intraday_ma_5m: 5分钟分时均线
            - order_book: 盘口数据

    Examples:
        # 获取补充数据
        data = get_qmt_supplement('300997', days=5)
        print(data['tick_validation'])
        print(data['intraday_ma_1m']['pattern'])

        # 自动保存
        data, file_path = get_qmt_supplement('300997', days=5, auto_save=True)
        print(f"数据已保存到: {file_path}")
    """
    return analyze_stock(stock_code, days=days, mode='supplement', auto_save=auto_save)


if __name__ == "__main__":
    import sys

    # 测试
    print("=" * 80)
    print("AI 便捷接口测试")
    print("=" * 80)

    stock_code = "300997"

    # 快速分析
    print("\n1. 快速分析（5天）:")
    print(quick(stock_code, 5))

    # 完整分析
    print("\n2. 完整分析（10天）:")
    result = analyze(stock_code, 10, mode='full')
    print(result)

    # 询问是否需要更久的数据
    print("\n3. 提示信息:")
    print(ask_more_days(10))