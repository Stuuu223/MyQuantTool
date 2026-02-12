#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快照回测引擎 - 验证历史信号的T+1/T+5收益

核心功能：
1. 读取历史扫描快照（data/scan_results/*.json）
2. 对每个机会信号计算T+1/T+5/T+10实际收益
3. 统计胜率、盈亏比、最大回撤等指标
4. 生成回测报告（JSON + 控制台输出）

与传统回测的区别：
- 传统回测：模拟交易过程，计算持仓期间的收益
- 快照回测：验证历史信号质量，计算固定持有期的收益

Author: MyQuantTool Team
Date: 2026-02-10
Version: V1.0
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import Dict, List
from datetime import datetime

from data_sources.price_history_fetcher import PriceHistoryFetcher
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class SnapshotBacktestEngine:
    """快照回测引擎 - 计算T+1/T+5收益"""

    def __init__(self):
        """初始化回测引擎"""
        try:
            self.price_fetcher = PriceHistoryFetcher()
            self.backtest_results = []
            logger.info("✅ 快照回测引擎初始化完成")
        except ImportError as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise

    def backtest_snapshot(self, snapshot_file: Path) -> Dict:
        """
        对单个快照进行回测

        Args:
            snapshot_file: 快照文件路径

        Returns:
            dict: 回测结果
        """
        logger.info(f"\n📊 回测快照: {snapshot_file.name}")
        logger.info("-" * 80)

        try:
            # 加载快照
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)

            # 提取扫描日期
            scan_time = snapshot.get('scan_time', '')
            if not scan_time:
                logger.error("❌ 快照缺少scan_time字段")
                return {}

            scan_date = scan_time[:10]
            logger.info(f"   扫描日期: {scan_date}")

            # 提取机会池
            opportunities = snapshot.get('results', {}).get('opportunities', [])

            if not opportunities:
                logger.warning(f"   ⚠️ 机会池为空，跳过回测")
                return {
                    'scan_date': scan_date,
                    'scan_file': str(snapshot_file),
                    'results': []
                }

            logger.info(f"   机会池信号数量: {len(opportunities)}")

            # 对每只股票计算T+1/T+5收益
            results = []
            success_count = 0

            for i, item in enumerate(opportunities, 1):
                code = item['code']
                buy_price = item['last_price']

                logger.info(f"   [{i}/{len(opportunities)}] {code} (买入价: ¥{buy_price:.2f})")

                # 获取未来价格
                future_prices = self.price_fetcher.get_future_prices(code, scan_date, [1, 5, 10])

                if not future_prices:
                    logger.warning(f"      ⚠️ 未来价格数据缺失，跳过")
                    continue

                # 计算收益
                t1_price = future_prices.get(1)
                t5_price = future_prices.get(5)
                t10_price = future_prices.get(10)

                t1_return = self.price_fetcher.calculate_return(buy_price, t1_price) if t1_price else None
                t5_return = self.price_fetcher.calculate_return(buy_price, t5_price) if t5_price else None
                t10_return = self.price_fetcher.calculate_return(buy_price, t10_price) if t10_price else None

                # 构建结果
                result = {
                    'code': code,
                    'buy_price': buy_price,
                    't1_price': t1_price,
                    't5_price': t5_price,
                    't10_price': t10_price,
                    't1_return': t1_return,
                    't5_return': t5_return,
                    't10_return': t10_return,
                    'risk_score': item.get('risk_score', 0),
                    'scenario_type': item.get('scenario_type', 'UNKNOWN'),
                    'decision_tag': item.get('decision_tag', 'UNKNOWN')
                }

                results.append(result)
                success_count += 1

                # 打印结果
                if t1_return is not None:
                    t1_emoji = "✅" if t1_return > 0 else "❌"
                    logger.info(f"      T+1: {t1_emoji} {t1_return:+.2f}% (¥{t1_price:.2f})")
                if t5_return is not None:
                    t5_emoji = "✅" if t5_return > 0 else "❌"
                    logger.info(f"      T+5: {t5_emoji} {t5_return:+.2f}% (¥{t5_price:.2f})")

            logger.info(f"\n   ✅ 回测完成: {success_count}/{len(opportunities)} 个有效样本")

            return {
                'scan_date': scan_date,
                'scan_file': str(snapshot_file),
                'confidence': snapshot.get('results', {}).get('confidence', 0),
                'results': results
            }

        except Exception as e:
            logger.error(f"❌ 回测失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def calculate_metrics(self, backtest_results: List[Dict]) -> Dict:
        """
        计算回测指标

        Args:
            backtest_results: 回测结果列表

        Returns:
            dict: 指标字典
        """
        logger.info("\n📊 计算回测指标...")
        logger.info("=" * 80)

        # 收集所有有效的收益数据
        all_t1_returns = []
        all_t5_returns = []
        all_t10_returns = []

        for backtest in backtest_results:
            for item in backtest.get('results', []):
                if item['t1_return'] is not None:
                    all_t1_returns.append(item['t1_return'])
                if item['t5_return'] is not None:
                    all_t5_returns.append(item['t5_return'])
                if item['t10_return'] is not None:
                    all_t10_returns.append(item['t10_return'])

        if not all_t1_returns:
            logger.warning("⚠️ 没有有效的T+1数据")
            return {}

        logger.info(f"有效样本: T+1={len(all_t1_returns)}, T+5={len(all_t5_returns)}, T+10={len(all_t10_returns)}")

        # 计算T+1指标
        t1_win_count = sum(1 for r in all_t1_returns if r > 0)
        t1_loss_count = sum(1 for r in all_t1_returns if r < 0)
        t1_win_rate = t1_win_count / len(all_t1_returns) * 100
        t1_avg_return = sum(all_t1_returns) / len(all_t1_returns)
        t1_max_return = max(all_t1_returns)
        t1_max_loss = min(all_t1_returns)

        t1_wins = [r for r in all_t1_returns if r > 0]
        t1_losses = [r for r in all_t1_returns if r < 0]
        t1_avg_win = sum(t1_wins) / len(t1_wins) if t1_wins else 0
        t1_avg_loss = sum(t1_losses) / len(t1_losses) if t1_losses else 0
        t1_profit_loss_ratio = abs(t1_avg_win / t1_avg_loss) if t1_avg_loss != 0 else float('inf')

        # 计算T+5指标
        if all_t5_returns:
            t5_win_count = sum(1 for r in all_t5_returns if r > 0)
            t5_loss_count = sum(1 for r in all_t5_returns if r < 0)
            t5_win_rate = t5_win_count / len(all_t5_returns) * 100
            t5_avg_return = sum(all_t5_returns) / len(all_t5_returns)
            t5_max_return = max(all_t5_returns)
            t5_max_loss = min(all_t5_returns)

            t5_wins = [r for r in all_t5_returns if r > 0]
            t5_losses = [r for r in all_t5_returns if r < 0]
            t5_avg_win = sum(t5_wins) / len(t5_wins) if t5_wins else 0
            t5_avg_loss = sum(t5_losses) / len(t5_losses) if t5_losses else 0
            t5_profit_loss_ratio = abs(t5_avg_win / t5_avg_loss) if t5_avg_loss != 0 else float('inf')
        else:
            t5_win_rate = t5_avg_return = t5_max_return = t5_max_loss = t5_profit_loss_ratio = 0
            t5_win_count = t5_loss_count = 0

        # 计算T+10指标
        if all_t10_returns:
            t10_win_count = sum(1 for r in all_t10_returns if r > 0)
            t10_loss_count = sum(1 for r in all_t10_returns if r < 0)
            t10_win_rate = t10_win_count / len(all_t10_returns) * 100
            t10_avg_return = sum(all_t10_returns) / len(all_t10_returns)
            t10_max_return = max(all_t10_returns)
            t10_max_loss = min(all_t10_returns)
        else:
            t10_win_rate = t10_avg_return = t10_max_return = t10_max_loss = 0
            t10_win_count = t10_loss_count = 0

        return {
            't1_metrics': {
                'total_signals': len(all_t1_returns),
                'win_count': t1_win_count,
                'loss_count': t1_loss_count,
                'win_rate': t1_win_rate,
                'avg_return': t1_avg_return,
                'max_return': t1_max_return,
                'max_loss': t1_max_loss,
                'avg_win': t1_avg_win,
                'avg_loss': t1_avg_loss,
                'profit_loss_ratio': t1_profit_loss_ratio
            },
            't5_metrics': {
                'total_signals': len(all_t5_returns),
                'win_count': t5_win_count,
                'loss_count': t5_loss_count,
                'win_rate': t5_win_rate,
                'avg_return': t5_avg_return,
                'max_return': t5_max_return,
                'max_loss': t5_max_loss,
                'avg_win': t5_avg_win,
                'avg_loss': t5_avg_loss,
                'profit_loss_ratio': t5_profit_loss_ratio
            },
            't10_metrics': {
                'total_signals': len(all_t10_returns),
                'win_count': t10_win_count,
                'loss_count': t10_loss_count,
                'win_rate': t10_win_rate,
                'avg_return': t10_avg_return,
                'max_return': t10_max_return,
                'max_loss': t10_max_loss
            }
        }

    def generate_backtest_report(self, metrics: Dict, output_file: str):
        """生成回测报告"""
        print()
        logger.info("=" * 80)
        logger.info("📊 真正的回测报告（T+1/T+5/T+10收益验证）")
        logger.info("=" * 80)
        print()

        t1 = metrics['t1_metrics']
        t5 = metrics['t5_metrics']
        t10 = metrics['t10_metrics']

        # T+1指标
        logger.info("📈 T+1 指标（次日收益）:")
        logger.info(f"   总信号数: {t1['total_signals']}")
        logger.info(f"   盈利次数: {t1['win_count']} | 亏损次数: {t1['loss_count']}")
        logger.info(f"   胜率: {t1['win_rate']:.2f}%")
        logger.info(f"   平均收益: {t1['avg_return']:+.2f}%")
        logger.info(f"   平均盈利: {t1['avg_win']:+.2f}% | 平均亏损: {t1['avg_loss']:+.2f}%")
        logger.info(f"   盈亏比: {t1['profit_loss_ratio']:.2f}")
        logger.info(f"   最大收益: {t1['max_return']:+.2f}%")
        logger.info(f"   最大亏损: {t1['max_loss']:+.2f}%")
        print()

        # T+5指标
        logger.info("📈 T+5 指标（5日收益）:")
        logger.info(f"   总信号数: {t5['total_signals']}")
        logger.info(f"   盈利次数: {t5['win_count']} | 亏损次数: {t5['loss_count']}")
        logger.info(f"   胜率: {t5['win_rate']:.2f}%")
        logger.info(f"   平均收益: {t5['avg_return']:+.2f}%")
        logger.info(f"   平均盈利: {t5['avg_win']:+.2f}% | 平均亏损: {t5['avg_loss']:+.2f}%")
        logger.info(f"   盈亏比: {t5['profit_loss_ratio']:.2f}")
        logger.info(f"   最大收益: {t5['max_return']:+.2f}%")
        logger.info(f"   最大亏损: {t5['max_loss']:+.2f}%")
        print()

        # T+10指标
        logger.info("📈 T+10 指标（10日收益）:")
        logger.info(f"   总信号数: {t10['total_signals']}")
        logger.info(f"   盈利次数: {t10['win_count']} | 亏损次数: {t10['loss_count']}")
        logger.info(f"   胜率: {t10['win_rate']:.2f}%")
        logger.info(f"   平均收益: {t10['avg_return']:+.2f}%")
        logger.info(f"   最大收益: {t10['max_return']:+.2f}%")
        logger.info(f"   最大亏损: {t10['max_loss']:+.2f}%")
        print()

        # 策略评估
        logger.info("🎯 策略评估:")
        if t1['win_rate'] >= 60 and t1['profit_loss_ratio'] >= 2.0:
            logger.info("   ✅ 策略有效性: 优秀")
            logger.info("   💡 建议: 可以小仓位实盘验证")
        elif t1['win_rate'] >= 50 and t1['profit_loss_ratio'] >= 1.5:
            logger.info("   ✅ 策略有效性: 良好")
            logger.info("   💡 建议: 可以谨慎尝试，控制仓位")
        elif t1['win_rate'] >= 40:
            logger.info("   ⚠️ 策略有效性: 一般")
            logger.info("   💡 建议: 需要优化筛选条件")
        else:
            logger.info("   ❌ 策略有效性: 较差")
            logger.info("   💡 建议: 重新设计策略逻辑")
        print()

        logger.info("=" * 80)

        # 保存报告
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 报告已保存: {output_file}")
        logger.info("=" * 80)


if __name__ == "__main__":
    # 单元测试
    print()
    print("=" * 80)
    print("🧪 快照回测引擎 - 单元测试")
    print("=" * 80)

    engine = SnapshotBacktestEngine()

    # 测试：回测单个快照
    test_snapshot = Path("data/scan_results/2026-02-10_intraday.json")

    if test_snapshot.exists():
        logger.info(f"\n✅ 找到测试快照: {test_snapshot}")
        result = engine.backtest_snapshot(test_snapshot)

        if result and result.get('results'):
            logger.info("\n✅ 回测成功，计算指标...")
            metrics = engine.calculate_metrics([result])

            output_file = "data/backtest/reports/test_backtest_report.json"
            engine.generate_backtest_report(metrics, output_file)
        else:
            logger.error("❌ 回测结果为空")
    else:
        logger.error(f"❌ 测试快照不存在: {test_snapshot}")
        logger.info("💡 提示：请先运行全市场扫描生成快照")