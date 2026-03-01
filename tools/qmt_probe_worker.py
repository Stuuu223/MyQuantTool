# -*- coding: utf-8 -*-
"""
QMT探雷兵 - 独立子进程版

【CTO扫雷令】：
每个探雷兵只负责查1只股票的数据。
查到就活（exit 0），崩了就死（exit -1073740791等负数）。
主进程通过子进程的返回码判断是否踩雷！

Author: CTO扫雷部队
Date: 2026-03-01
"""
import sys
import argparse


def probe_stock(stock_code: str, date: str, period: str) -> int:
    """
    探测单只股票是否有毒
    
    Args:
        stock_code: 股票代码
        date: 测试日期 YYYYMMDD
        period: 数据周期 (tick/1d)
        
    Returns:
        0: 安全，数据正常
        2: 安全，但无数据
        3: Python层异常
        负数: C++层崩溃（BSON等）
    """
    try:
        from xtquant import xtdata
        
        # 极简触碰，只要能活着把DataFrame返回，就说明底层没毒
        if period == 'tick':
            # Tick数据测试
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice'],  # 用最少的数据量试探
                stock_list=[stock_code],
                period='tick',
                start_time=date,
                end_time=date
            )
        else:
            # 日K数据测试
            data = xtdata.get_local_data(
                field_list=['close'],
                stock_list=[stock_code],
                period='1d',
                start_time=date,
                end_time=date
            )
        
        if data and stock_code in data and not data[stock_code].empty:
            return 0  # 活着回来，状态码0代表安全
        else:
            return 2  # 活着回来，但没数据
            
    except Exception as e:
        print(f"Python异常: {stock_code} - {e}", file=sys.stderr)
        return 3  # 捕获到了代码层异常


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QMT探雷兵 - 探测单只股票")
    parser.add_argument("--stock", required=True, help="股票代码")
    parser.add_argument("--date", required=True, help="测试日期 YYYYMMDD")
    parser.add_argument("--period", default="tick", choices=['tick', '1d'], help="数据周期")
    args = parser.parse_args()
    
    exit_code = probe_stock(args.stock, args.date, args.period)
    sys.exit(exit_code)
