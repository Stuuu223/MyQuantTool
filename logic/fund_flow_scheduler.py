"""
资金流向数据自动收集调度器
每天自动收集股票的资金流向数据，积累历史数据
"""

import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.fund_flow_collector import FundFlowCollector, get_fund_flow_collector


class FundFlowScheduler:
    """资金流向自动收集调度器"""

    def __init__(self):
        """初始化调度器"""
        self.collector = get_fund_flow_collector()
        self.last_run_time = None
        self.run_interval = 3600  # 默认每小时运行一次（单位：秒）

    def collect_single_stock(self, stock_code: str) -> dict:
        """
        收集单只股票的资金流向

        Args:
            stock_code: 股票代码

        Returns:
            收集结果
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始收集 {stock_code} 的资金流向数据...")
        result = self.collector.collect(stock_code)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {stock_code}: {result['message']}")
        return result

    def collect_multiple_stocks(self, stock_codes: List[str]) -> List[dict]:
        """
        收集多只股票的资金流向

        Args:
            stock_codes: 股票代码列表

        Returns:
            收集结果列表
        """
        results = []

        print(f"\n{'='*60}")
        print(f"开始批量收集 {len(stock_codes)} 只股票的资金流向数据")
        print(f"{'='*60}\n")

        for i, stock_code in enumerate(stock_codes, 1):
            print(f"[{i}/{len(stock_codes)}] ", end="")

            try:
                result = self.collect_single_stock(stock_code)
                results.append(result)

                # 间隔 0.5 秒，避免请求过快
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ {stock_code} 收集失败: {e}")
                results.append({
                    "stock_code": stock_code,
                    "success": False,
                    "message": f"收集失败: {e}"
                })

        print(f"\n{'='*60}")
        print(f"批量收集完成！")
        print(f"成功: {sum(1 for r in results if r.get('success'))} 只")
        print(f"失败: {sum(1 for r in results if not r.get('success'))} 只")
        print(f"{'='*60}\n")

        return results

    def run_once(self, stock_codes: Optional[List[str]] = None) -> dict:
        """
        运行一次收集任务

        Args:
            stock_codes: 要收集的股票代码列表，如果为 None 则使用默认列表

        Returns:
            运行结果
        """
        self.last_run_time = datetime.now()

        if stock_codes is None:
            # 默认股票列表
            stock_codes = [
                "300997",  # 欢乐家
                "301171",  # 易点天下
                "000001",  # 平安银行
                "600000",  # 浦发银行
                "600519",  # 贵州茅台
            ]

        results = self.collect_multiple_stocks(stock_codes)

        return {
            "run_time": self.last_run_time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stocks": len(stock_codes),
            "success_count": sum(1 for r in results if r.get('success')),
            "fail_count": sum(1 for r in results if not r.get('success')),
            "results": results,
        }

    def run_scheduled(self, stock_codes: Optional[List[str]] = None, max_runs: int = 0):
        """
        定时运行收集任务

        Args:
            stock_codes: 要收集的股票代码列表
            max_runs: 最大运行次数，0 表示无限循环
        """
        run_count = 0

        print(f"\n{'='*60}")
        print("资金流向自动收集调度器启动")
        print(f"运行间隔: {self.run_interval} 秒")
        print(f"最大运行次数: {'无限' if max_runs == 0 else max_runs}")
        print(f"{'='*60}\n")

        while True:
            if max_runs > 0 and run_count >= max_runs:
                print(f"\n已达到最大运行次数 {max_runs}，调度器停止")
                break

            run_count += 1

            print(f"\n第 {run_count} 次运行")
            print(f"{'='*60}")

            # 运行一次收集
            self.run_once(stock_codes)

            # 等待下次运行
            if max_runs == 0 or run_count < max_runs:
                next_run_time = datetime.now() + timedelta(seconds=self.run_interval)
                print(f"\n下次运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"等待 {self.run_interval} 秒...\n")

                time.sleep(self.run_interval)


# 便捷函数
def collect_fund_flow(stock_codes: Optional[List[str]] = None) -> dict:
    """
    便捷函数：运行一次资金流向收集

    Args:
        stock_codes: 股票代码列表

    Returns:
        收集结果
    """
    scheduler = FundFlowScheduler()
    return scheduler.run_once(stock_codes)


def analyze_stock(stock_code: str, days: int = 10) -> str:
    """
    便捷函数：分析个股（先收集数据，再分析）

    Args:
        stock_code: 股票代码
        days: 分析最近几天

    Returns:
        分析报告
    """
    # 先收集今日数据
    scheduler = FundFlowScheduler()
    scheduler.collect_single_stock(stock_code)

    # 再进行分析
    from logic.multi_day_analysis import analyze_multi_day
    return analyze_multi_day(stock_code, days)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 命令行参数：python fund_flow_scheduler.py <股票代码> [天数]
        stock_code = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 10

        print(f"分析 {stock_code} 最近 {days} 天的资金流向\n")
        report = analyze_stock(stock_code, days)
        print(report)

    else:
        # 默认：收集默认股票列表的资金流向
        print("运行一次资金流向收集\n")
        result = collect_fund_flow()
        print(f"\n运行结果: {result}")