"""
资金流向数据收集器
每天自动获取并保存资金流向数据，积累历史数据
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class FundFlowCollector:
    """资金流向数据收集器"""

    def __init__(self, cache_dir="data/fund_flow_cache"):
        """初始化收集器"""
        self.base_url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def parse_stock_code(self, stock_code: str) -> str:
        """解析股票代码为东方财富格式"""
        code = stock_code.replace('.SZ', '').replace('.SH', '').replace('.sz', '').replace('.sh', '')
        if code.startswith('6') or code.startswith('5'):
            return f"1.{code}"
        else:
            return f"0.{code}"

    def get_cache_file(self, stock_code: str) -> str:
        """获取缓存文件路径"""
        code = stock_code.replace('.', '_')
        return os.path.join(self.cache_dir, f"{code}_fund_flow.json")

    def load_cache(self, stock_code: str) -> List[Dict]:
        """加载缓存数据"""
        cache_file = self.get_cache_file(stock_code)

        if not os.path.exists(cache_file):
            return []

        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 过滤掉 90 天前的数据
        cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        data = [d for d in data if d['date'] >= cutoff_date]

        return data

    def save_cache(self, stock_code: str, data: List[Dict]):
        """保存缓存数据"""
        cache_file = self.get_cache_file(stock_code)

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_today_fund_flow(self, stock_code: str) -> Optional[Dict]:
        """获取今日资金流向"""
        try:
            secid = self.parse_stock_code(stock_code)

            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f7",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
                "klt": "101",
                "lmt": 1
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'data' not in data or 'klines' not in data['data']:
                return None

            klines = data['data']['klines']
            if not klines:
                return None

            parts = klines[0].split(',')

            return {
                "date": parts[0],
                "main_net_inflow": float(parts[1]),
                "super_large_net": float(parts[2]),
                "large_net": float(parts[3]),
                "medium_net": float(parts[4]),
                "small_net": float(parts[5]),
                "institution_net": float(parts[2]) + float(parts[3]),
                "retail_net": float(parts[4]) + float(parts[5]),
            }

        except Exception as e:
            print(f"获取资金流向失败: {e}")
            return None

    def collect(self, stock_code: str) -> Dict:
        """收集今日资金流向并保存"""
        # 加载现有缓存
        cache = self.load_cache(stock_code)

        # 获取今日数据
        today_data = self.get_today_fund_flow(stock_code)

        if today_data is None:
            return {
                "stock_code": stock_code,
                "success": False,
                "message": "获取数据失败"
            }

        # 检查今日数据是否已存在
        today_date = datetime.now().strftime("%Y-%m-%d")

        # 移除今日旧数据（如果有）
        cache = [d for d in cache if d['date'] != today_date]

        # 添加今日数据
        cache.append(today_data)

        # 保存缓存
        self.save_cache(stock_code, cache)

        return {
            "stock_code": stock_code,
            "success": True,
            "message": f"成功收集 {len(cache)} 天数据",
            "total_days": len(cache),
            "latest_data": today_data
        }

    def get_history(self, stock_code: str, days: int = 30) -> List[Dict]:
        """获取历史资金流向数据"""
        cache = self.load_cache(stock_code)
        return cache[-days:] if cache else []

    def analyze_history(self, stock_code: str, days: int = 10) -> Dict:
        """分析历史资金流向趋势"""
        history = self.get_history(stock_code, days)

        if not history:
            return {
                "stock_code": stock_code,
                "error": "没有历史数据"
            }

        # 计算每日信号
        daily_signals = []

        for day in history:
            inst_net = day['institution_net']
            retail_net = day['retail_net']

            if inst_net < 0 and retail_net > 0:
                signal = "BEARISH"
                pattern = "机构减仓，散户接盘"
            elif inst_net > 0 and retail_net < 0:
                signal = "BULLISH"
                pattern = "机构吸筹，散户恐慌"
            elif inst_net > 0 and retail_net > 0:
                signal = "BULLISH"
                pattern = "共同看好"
            else:
                signal = "BEARISH"
                pattern = "共同看淡"

            daily_signals.append({
                "date": day['date'],
                "institution_net": inst_net,
                "retail_net": retail_net,
                "signal": signal,
                "pattern": pattern
            })

        # 统计
        bullish_days = sum(1 for d in daily_signals if d['signal'] == 'BULLISH')
        bearish_days = len(daily_signals) - bullish_days

        # 判断趋势
        if bullish_days > bearish_days:
            trend = "BULLISH"
            trend_desc = "吸筹趋势"
        elif bearish_days > bullish_days:
            trend = "BEARISH"
            trend_desc = "减仓趋势"
        else:
            trend = "NEUTRAL"
            trend_desc = "震荡趋势"

        return {
            "stock_code": stock_code,
            "history": history,
            "daily_signals": daily_signals,
            "statistics": {
                "total_days": len(daily_signals),
                "bullish_days": bullish_days,
                "bearish_days": bearish_days,
            },
            "trend": trend,
            "trend_desc": trend_desc
        }


# 全局实例
_collector = None


def get_fund_flow_collector() -> FundFlowCollector:
    """获取全局收集器"""
    global _collector
    if _collector is None:
        _collector = FundFlowCollector()
    return _collector


if __name__ == "__main__":
    # 测试：收集欢乐家资金流向
    collector = get_fund_flow_collector()

    print("开始收集资金流向数据...")
    result = collector.collect("300997")
    print(f"\n结果: {result}")

    # 显示历史数据
    print("\n历史资金流向:")
    history = collector.get_history("300997", days=30)
    print(f"共有 {len(history)} 天数据")

    for day in history:
        inst_net = day['institution_net'] / 10000
        retail_net = day['retail_net'] / 10000
        print(f"{day['date']}: 机构 {inst_net:>8.2f}万, 散户 {retail_net:>8.2f}万")