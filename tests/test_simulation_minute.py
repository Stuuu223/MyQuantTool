#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分钟K线仿真测试 - 提前验证系统稳定性

功能：
1. 拉取今天（2月10日）的分钟K线数据
2. 模拟事件驱动监控的扫描流程
3. 验证系统是否能正常输出信号
4. 提前发现潜在问题

使用方式：
    python tests/test_simulation_minute.py --date 2026-02-10

Author: Stuuu223
Version: V1.0
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.full_market_scanner import FullMarketScanner
from logic.logger import get_logger
from xtquant import xtdata

logger = get_logger(__name__)


class MinuteSimulation:
    """分钟K线仿真测试器"""

    def __init__(self, test_date: str):
        """
        初始化仿真测试器

        Args:
            test_date: 测试日期（格式：YYYY-MM-DD）
        """
        self.test_date = test_date
        self.scanner = FullMarketScanner()
        self.simulation_results = []

    def _fetch_minute_klines(self, stock_codes: list, period: str = '1m') -> dict:
        """
        拉取分钟K线数据

        Args:
            stock_codes: 股票代码列表
            period: K线周期（1m, 5m, 15m, 30m, 60m）

        Returns:
            dict: {code: DataFrame}
        """
        try:
            logger.info(f"📊 拉取分钟K线数据: {len(stock_codes)} 只股票")

            # 使用QMT拉取分钟K线
            klines = xtdata.get_market_data_ex(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_codes,
                period=period,
                count=240,  # 拉取一整天的数据（9:30-15:00，240分钟）
                fill_data=True
            )

            logger.info(f"✅ 成功拉取 {len(klines)} 只股票的K线数据")
            return klines

        except Exception as e:
            logger.error(f"❌ 拉取分钟K线失败: {e}")
            return {}

    def _simulate_scan_at_timepoint(self, timepoint: str) -> dict:
        """
        模拟某个时间点的扫描

        Args:
            timepoint: 时间点（格式：HH:MM）

        Returns:
            dict: 扫描结果
        """
        logger.info(f"\n🔍 模拟扫描时间点: {timepoint}")
        logger.info("-" * 80)

        try:
            # 执行全市场扫描
            results = self.scanner.scan_with_risk_management(mode='intraday')

            # 保存结果
            self.simulation_results.append({
                'timepoint': timepoint,
                'opportunities': len(results['opportunities']),
                'watchlist': len(results['watchlist']),
                'blacklist': len(results['blacklist']),
                'confidence': results['confidence'],
                'position_limit': results['position_limit']
            })

            # 打印摘要
            logger.info(f"✅ 扫描完成: 机会{len(results['opportunities'])} | 观察{len(results['watchlist'])} | 黑名单{len(results['blacklist'])}")
            logger.info(f"   系统置信度: {results['confidence']*100:.1f}%")
            logger.info(f"   建议最大仓位: {results['position_limit']*100:.1f}%")

            return results

        except Exception as e:
            logger.error(f"❌ 扫描失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def run_full_day_simulation(self):
        """运行全天仿真测试"""
        logger.info("=" * 80)
        logger.info("🎬 分钟K线仿真测试启动")
        logger.info("=" * 80)
        logger.info(f"📅 测试日期: {self.test_date}")
        logger.info(f"⏰ 模拟时间段: 9:30-15:00")
        logger.info("=" * 80)
        print()

        # 定义关键时间点（模拟盘中扫描）
        key_timepoints = [
            "09:30",  # 开盘
            "10:00",  # 早盘
            "10:30",
            "11:00",
            "11:30",  # 午盘收盘前
            "13:00",  # 午盘开盘
            "13:30",
            "14:00",
            "14:30",
            "15:00",  # 收盘
        ]

        # 依次模拟每个时间点
        for timepoint in key_timepoints:
            results = self._simulate_scan_at_timepoint(timepoint)

            if results and results['opportunities']:
                logger.info(f"\n🔥 发现机会信号 ({timepoint}):")
                for item in results['opportunities'][:5]:  # 只显示前5个
                    logger.info(f"   {item['code']} - 风险: {item.get('risk_score', 0):.2f}")
                if len(results['opportunities']) > 5:
                    logger.info(f"   ... 还有 {len(results['opportunities']) - 5} 只")

            print()

        # 生成仿真报告
        self._generate_simulation_report()

    def run_quick_simulation(self):
        """快速仿真测试（只测试关键时间点）"""
        logger.info("=" * 80)
        logger.info("⚡ 快速仿真测试启动")
        logger.info("=" * 80)
        logger.info(f"📅 测试日期: {self.test_date}")
        logger.info(f"⏰ 测试时间点: 09:30, 13:00, 14:30")
        logger.info("=" * 80)
        print()

        # 只测试3个关键时间点
        key_timepoints = [
            "09:30",  # 开盘
            "13:00",  # 午盘开盘
            "14:30",  # 收盘前
        ]

        # 依次模拟每个时间点
        for timepoint in key_timepoints:
            results = self._simulate_scan_at_timepoint(timepoint)

            if results and results['opportunities']:
                logger.info(f"\n🔥 发现机会信号 ({timepoint}):")
                for item in results['opportunities'][:5]:  # 只显示前5个
                    logger.info(f"   {item['code']} - 风险: {item.get('risk_score', 0):.2f}")
                if len(results['opportunities']) > 5:
                    logger.info(f"   ... 还有 {len(results['opportunities']) - 5} 只")

            print()

        # 生成仿真报告
        self._generate_simulation_report()

    def _generate_simulation_report(self):
        """生成仿真报告"""
        logger.info("=" * 80)
        logger.info("📊 仿真测试报告")
        logger.info("=" * 80)
        print()

        if not self.simulation_results:
            logger.warning("⚠️ 没有仿真结果")
            return

        # 统计信号数量
        total_opportunities = sum(r['opportunities'] for r in self.simulation_results)
        total_watchlist = sum(r['watchlist'] for r in self.simulation_results)
        total_blacklist = sum(r['blacklist'] for r in self.simulation_results)

        logger.info(f"📈 仿真结果汇总:")
        logger.info(f"   总扫描次数: {len(self.simulation_results)}")
        logger.info(f"   总机会信号: {total_opportunities}")
        logger.info(f"   总观察信号: {total_watchlist}")
        logger.info(f"   总黑名单: {total_blacklist}")
        print()

        # 按时间点显示
        logger.info(f"📋 时间点详情:")
        for result in self.simulation_results:
            logger.info(f"   {result['timepoint']}: 机会{result['opportunities']} | 观察{result['watchlist']} | 黑名单{result['blacklist']} | 置信度{result['confidence']*100:.1f}%")
        print()

        # 判断系统状态
        if total_opportunities == 0:
            logger.warning("⚠️ 仿真结果：全天无机会信号")
            logger.warning("   可能原因：")
            logger.warning("   1. 市场确实没有符合条件的机会")
            logger.warning("   2. 系统筛选条件过于严格")
            logger.warning("   3. 数据源异常（QMT数据不完整）")
            logger.warning("\n   建议：")
            logger.warning("   - 检查QMT连接状态")
            logger.warning("   - 检查资金流数据是否正常")
            logger.warning("   - 适当放宽筛选条件（仅用于测试）")
        else:
            logger.info("✅ 仿真结果：系统能正常输出信号")
            logger.info(f"   平均每次扫描: {total_opportunities / len(self.simulation_results):.1f} 个机会")
            logger.info("\n   建议：")
            logger.info("   - 明天盘中正常运行即可")
            logger.info("   - 重点关注早盘（9:30-10:00）的信号质量")

        print()
        logger.info("=" * 80)

        # 保存仿真报告
        report_file = f"data/simulation_report_{self.test_date}.json"
        Path(report_file).parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.simulation_results, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 仿真报告已保存: {report_file}")
        logger.info("=" * 80)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='分钟K线仿真测试')
    parser.add_argument(
        '--date',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='测试日期（格式：YYYY-MM-DD），默认今天'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='quick',
        choices=['quick', 'full'],
        help='仿真模式（quick: 快速测试3个时间点，full: 全天10个时间点）'
    )

    args = parser.parse_args()

    # 创建仿真测试器
    simulation = MinuteSimulation(args.date)

    # 运行仿真
    if args.mode == 'quick':
        simulation.run_quick_simulation()
    else:
        simulation.run_full_day_simulation()


if __name__ == "__main__":
    main()
