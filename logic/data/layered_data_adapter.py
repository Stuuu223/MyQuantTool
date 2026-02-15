"""
分层数据适配器
实现 QMT + AkShare 混合数据架构
- 第一层：QMT 快速过滤（5000 → 50）
- 第二层：AkShare 精准分析（50 → 10）
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from functools import lru_cache

from logic.data.fund_flow_analyzer import FundFlowAnalyzer


class LayeredDataAdapter:
    """
    分层数据适配器

    实现 QMT + AkShare 混合数据架构：
    - 第一层：QMT 快速过滤（海选）
    - 第二层：AkShare 精准分析（精选）
    """

    def __init__(self, qmt_instance=None):
        """
        初始化分层数据适配器

        Args:
            qmt_instance: QMT 实例（可选）
        """
        self.qmt = qmt_instance
        self.fund_flow_analyzer = FundFlowAnalyzer()
        self.layer1_results = []
        self.layer2_results = []

    def scan_stocks(self, stock_list: List[str], max_candidates: int = 50) -> Dict:
        """
        两层扫描股票

        Args:
            stock_list: 待扫描的股票列表
            max_candidates: 第一层最多保留的候选股票数量

        Returns:
            扫描结果
        """
        print(f"🚀 开始分层扫描，总股票数: {len(stock_list)}")

        # 第一层：QMT 快速过滤
        print(f"\n📊 [第一层] QMT 快速过滤（{len(stock_list)} → {max_candidates}）")
        layer1_start = time.time()

        candidates = self._layer1_filter(stock_list, max_candidates)

        layer1_time = time.time() - layer1_start
        print(f"✅ [第一层] 完成！耗时: {layer1_time:.2f}秒")
        print(f"   筛选出: {len(candidates)} 只候选股票")

        # 第二层：AkShare 精准分析
        print(f"\n🎯 [第二层] AkShare 精准分析（{len(candidates)} → 最终）")
        layer2_start = time.time()

        final_picks = self._layer2_filter(candidates)

        layer2_time = time.time() - layer2_start
        print(f"✅ [第二层] 完成！耗时: {layer2_time:.2f}秒")
        print(f"   最终精选: {len(final_picks)} 只股票")

        # 返回结果
        return {
            "total_stocks": len(stock_list),
            "candidates": candidates,
            "final_picks": final_picks,
            "layer1_time": layer1_time,
            "layer2_time": layer2_time,
            "total_time": layer1_time + layer2_time,
        }

    def _layer1_filter(self, stock_list: List[str], max_candidates: int) -> List[Dict]:
        """
        第一层：QMT 快速过滤

        过滤条件（不依赖资金流向）：
        - 涨停或接近涨停
        - 价格合理（10-50 元）
        - 放量（量比 > 1.5）
        - MA60 向上
        - 换手率适中（3%-15%）

        Args:
            stock_list: 待过滤的股票列表
            max_candidates: 最多保留的候选股票数量

        Returns:
            候选股票列表
        """
        candidates = []

        for stock in stock_list:
            try:
                # 获取 QMT Tick 数据
                tick = self.qmt.xtdata.get_full_tick([stock])

                # 获取历史数据（60 日）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)

                start_date_str = start_date.strftime("%Y%m%d")
                end_date_str = end_date.strftime("%Y%m%d")

                history = self.qmt.xtdata.get_market_data(
                    stock_list=[stock],
                    period='1d',
                    start_time=start_date_str,
                    end_time=end_date_str,
                    dividend_type='front'
                )

                # 基础过滤
                if self._passes_basic_filter(tick, history):
                    candidates.append({
                        "stock": stock,
                        "tick": tick,
                        "history": history,
                        "filter_score": self._calc_filter_score(tick, history)
                    })

            except Exception as e:
                # 忽略错误，继续处理下一只股票
                continue

        # 按评分排序，保留前 max_candidates 只
        candidates.sort(key=lambda x: x["filter_score"], reverse=True)
        self.layer1_results = candidates[:max_candidates]

        return self.layer1_results

    def _passes_basic_filter(self, tick: Dict, history: Dict) -> bool:
        """
        基础过滤条件

        Args:
            tick: QMT Tick 数据
            history: QMT 历史数据

        Returns:
            是否通过过滤
        """
        try:
            # 1. 涨停或接近涨停
            up_limit_price = tick.get('upLimitPrice', 0)
            last_price = tick.get('lastPrice', 0)

            if up_limit_price > 0 and last_price < up_limit_price * 0.985:
                return False

            # 2. 价格范围 10-50 元
            if not (10 <= last_price <= 50):
                return False

            # 3. 放量（量比 > 1.5）
            volume_ratio = self._calc_volume_ratio(history)
            if volume_ratio < 1.5:
                return False

            # 4. MA60 向上
            if not self._is_ma60_up(history):
                return False

            # 5. 换手率适中（3%-15%）
            turnover = self._calc_turnover(tick, history)
            if not (3 <= turnover <= 15):
                return False

            return True

        except Exception as e:
            return False

    def _calc_filter_score(self, tick: Dict, history: Dict) -> float:
        """
        计算过滤评分

        Args:
            tick: QMT Tick 数据
            history: QMT 历史数据

        Returns:
            评分（0-100）
        """
        try:
            score = 0

            # 1. 涨停溢价（20分）
            up_limit_price = tick.get('upLimitPrice', 0)
            last_price = tick.get('lastPrice', 0)
            if up_limit_price > 0:
                premium = (last_price / up_limit_price - 1) * 100
                score += max(0, 20 - premium)  # 越接近涨停，分数越高

            # 2. 量比（20分）
            volume_ratio = self._calc_volume_ratio(history)
            score += min(20, volume_ratio * 10)

            # 3. 趋势（30分）
            trend_score = self._calc_trend_score(history)
            score += trend_score

            # 4. 换手率（30分）
            turnover = self._calc_turnover(tick, history)
            if 3 <= turnover <= 8:
                score += 30  # 最佳换手率区间
            elif 8 < turnover <= 15:
                score += 20
            else:
                score += 10

            return min(100, score)

        except Exception as e:
            return 0

    def _calc_volume_ratio(self, history: Dict) -> float:
        """计算量比"""
        try:
            if isinstance(history, dict) and 'volume' in history:
                if isinstance(history['volume'], pd.DataFrame):
                    df = history['volume'].T
                else:
                    df = pd.DataFrame(history['volume']).T

                df = df.sort_index()

                # 当前成交量
                current_volume = df.iloc[-1]['volume']

                # 5 日平均成交量
                avg_volume_5 = df['volume'].rolling(5).mean().iloc[-2]

                if avg_volume_5 > 0:
                    return current_volume / avg_volume_5

            return 1.0

        except Exception as e:
            return 1.0

    def _calc_turnover(self, tick: Dict, history: Dict) -> float:
        """计算换手率"""
        try:
            # 简化计算，假设流通股本
            current_volume = tick.get('volume', 0)
            total_shares = 1000000000  # 假设 10 亿流通股本

            turnover = (current_volume / total_shares) * 100
            return turnover

        except Exception as e:
            return 0

    def _is_ma60_up(self, history: Dict) -> bool:
        """判断 MA60 是否向上"""
        try:
            if isinstance(history, dict) and 'close' in history:
                if isinstance(history['close'], pd.DataFrame):
                    df = history['close'].T
                else:
                    df = pd.DataFrame(history['close']).T

                df = df.sort_index()

                # 计算 MA60
                df['MA60'] = df['close'].rolling(60).mean()

                # 比较 MA60 斜率
                ma60_now = df['MA60'].iloc[-1]
                ma60_5_ago = df['MA60'].iloc[-5] if len(df) >= 5 else df['MA60'].iloc[0]

                return ma60_now > ma60_5_ago

            return False

        except Exception as e:
            return False

    def _calc_trend_score(self, history: Dict) -> float:
        """计算趋势评分"""
        try:
            if isinstance(history, dict) and 'close' in history:
                if isinstance(history['close'], pd.DataFrame):
                    df = history['close'].T
                else:
                    df = pd.DataFrame(history['close']).T

                df = df.sort_index()

                # 计算 20 日涨跌幅
                latest = df.iloc[-1]['close']
                df_20_ago = df.iloc[-20] if len(df) >= 20 else df.iloc[0]

                change_pct = (latest - df_20_ago) / df_20_ago * 100

                # 转换为评分
                if change_pct > 20:
                    return 30
                elif change_pct > 10:
                    return 25
                elif change_pct > 0:
                    return 20
                elif change_pct > -10:
                    return 10
                else:
                    return 0

            return 0

        except Exception as e:
            return 0

    def _layer2_filter(self, candidates: List[Dict]) -> List[Dict]:
        """
        第二层：AkShare 精准分析

        精准判断条件：
        - 机构资金净流入（超大单 + 大单）
        - 散户资金净流出（中单 + 小单）→ 底部机会
- 或者机构和散户都净流入 → 追高风险

        Args:
            candidates: 候选股票列表

        Returns:
            最终精选股票列表
        """
        final_picks = []
        akshare_success = 0
        qmt_fallback = 0

        for candidate in candidates:
            stock = candidate["stock"]

            try:
                # 获取资金流向分析
                fund_flow_result = self.fund_flow_analyzer.analyze_fund_flow(stock)

                if "error" in fund_flow_result:
                    continue

                # 根据资金流向决策
                decision = fund_flow_result["decision"]
                risk_level = fund_flow_result["risk_level"]
                fund_flow = fund_flow_result.get("fund_flow", {})

                # 统计成功率
                if fund_flow_result.get("data_source") == "EASTMONEY_REALTIME":
                    akshare_success += 1
                else:
                    qmt_fallback += 1

                # 筛选条件
                if decision == "BUY":
                    # 底部机会：机构买，散户卖
                    final_picks.append({
                        **candidate,
                        "fund_flow": fund_flow_result,
                        "layer2_score": 100,
                    })
                elif decision == "OBSERVE" and risk_level == "MEDIUM":
                    # 需要观望
                    final_picks.append({
                        **candidate,
                        "fund_flow": fund_flow_result,
                        "layer2_score": 50,
                    })
                elif fund_flow.get("institution_net", 0) > 5000000:
                    # 机构净流入 > 500万
                    final_picks.append({
                        **candidate,
                        "fund_flow": fund_flow_result,
                        "layer2_score": 70,
                    })

                # 控制请求速度
                time.sleep(0.5)

            except Exception as e:
                # 忽略错误，继续处理下一只股票
                continue

        # 按第二层评分排序
        final_picks.sort(key=lambda x: x["layer2_score"], reverse=True)
        self.layer2_results = final_picks

        print(f"  - AkShare 成功: {akshare_success} 只")
        print(f"  - QMT 降级: {qmt_fallback} 只")

        return self.layer2_results

    def get_filter_report(self) -> str:
        """
        获取过滤报告

        Returns:
            格式化的过滤报告
        """
        report = f"""
## 分层过滤报告

### 第一层：QMT 快速过滤
候选股票数: {len(self.layer1_results)}

Top 10:
"""
        for i, candidate in enumerate(self.layer1_results[:10], 1):
            report += f"{i}. {candidate['stock']} (评分: {candidate['filter_score']:.1f})\n"

        report += f"""
### 第二层：AkShare 精准分析
最终精选数: {len(self.layer2_results)}

精选股票:
"""
        for i, pick in enumerate(self.layer2_results, 1):
            stock = pick['stock']
            score = pick.get('layer2_score', 0)
            decision = pick.get('fund_flow', {}).get('decision', 'UNKNOWN')
            report += f"{i}. {stock} (评分: {score}, 决策: {decision})\n"

        return report


# 全局实例
_layered_data_adapter = None


def init_layered_adapter(qmt_instance=None):
    """
    初始化全局分层适配器

    Args:
        qmt_instance: QMT 实例
    """
    global _layered_data_adapter
    _layered_data_adapter = LayeredDataAdapter(qmt_instance)


def scan_stocks_layered(stock_list: List[str], max_candidates: int = 50) -> Dict:
    """
    便捷函数：两层扫描股票

    Args:
        stock_list: 待扫描的股票列表
        max_candidates: 第一层最多保留的候选股票数量

    Returns:
        扫描结果
    """
    global _layered_data_adapter

    if _layered_data_adapter is None:
        _layered_data_adapter = LayeredDataAdapter()

    return _layered_data_adapter.scan_stocks(stock_list, max_candidates)


if __name__ == "__main__":
    # 测试
    test_stocks = ["300997", "000001", "600000", "600519"]
    result = scan_stocks_layered(test_stocks, max_candidates=10)
    print(result)
    print(get_filter_report())