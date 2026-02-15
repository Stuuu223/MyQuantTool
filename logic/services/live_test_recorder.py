"""实盘验证结果记录与统计脚本

- 记录每日模型预测与实际结果
- 统计准确率、召回率、F1 等核心指标
"""
from dataclasses import dataclass, asdict
from typing import List, Optional
import pandas as pd
from pathlib import Path
from datetime import datetime


RESULT_COLUMNS = [
    "date",          # 日期 YYYY-MM-DD
    "stock_code",    # 股票代码
    "stock_name",    # 股票名称
    "strategy",      # 使用的策略/模型名称
    "signal",        # 预测信号: buy/sell/hold/limit_up...
    "prob",          # 预测概率 (0-1)
    "entry_price",   # 入场价
    "exit_price",    # 离场价
    "pnl_pct",       # 收益率 (%)
    "label",         # 实际结果: 1=成功, 0=失败
    "notes",         # 备注
]


@dataclass
class TradeRecord:
    date: str
    stock_code: str
    stock_name: str
    strategy: str
    signal: str
    prob: float
    entry_price: float
    exit_price: float
    pnl_pct: float
    label: int
    notes: str = ""

    def to_dict(self):
        return asdict(self)


class LiveTestRecorder:
    """实盘验证结果记录工具"""

    def __init__(self, csv_path: str = "data/live_test_results.csv"):
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.csv_path.exists():
            # 初始化空表
            pd.DataFrame(columns=RESULT_COLUMNS).to_csv(self.csv_path, index=False)

    def append_record(self, record: TradeRecord) -> None:
        """追加一条记录"""
        df = pd.DataFrame([record.to_dict()])[RESULT_COLUMNS]
        df.to_csv(self.csv_path, mode="a", header=not self.csv_path.exists(), index=False)

    def load_all(self) -> pd.DataFrame:
        if self.csv_path.exists():
            return pd.read_csv(self.csv_path)
        return pd.DataFrame(columns=RESULT_COLUMNS)


class LiveTestAnalyzer:
    """实盘结果统计分析工具"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def basic_metrics(self):
        """整体指标: 命中率、平均收益等"""
        if self.df.empty:
            return {}

        total = len(self.df)
        success = int((self.df["label"] == 1).sum())
        hit_rate = success / total if total > 0 else 0

        avg_pnl = self.df["pnl_pct"].mean()
        win_pnl = self.df.loc[self.df["label"] == 1, "pnl_pct"].mean()
        lose_pnl = self.df.loc[self.df["label"] == 0, "pnl_pct"].mean()

        return {
            "total_trades": total,
            "success_trades": success,
            "hit_rate": hit_rate,
            "avg_pnl": avg_pnl,
            "avg_win_pnl": win_pnl,
            "avg_lose_pnl": lose_pnl,
        }

    def by_strategy(self) -> pd.DataFrame:
        """按策略维度统计指标"""
        if self.df.empty:
            return pd.DataFrame()

        grouped = self.df.groupby("strategy").agg(
            total_trades=("label", "count"),
            success_trades=("label", lambda x: int((x == 1).sum())),
            hit_rate=("label", lambda x: (x == 1).mean()),
            avg_pnl=("pnl_pct", "mean"),
        )
        return grouped.sort_values("hit_rate", ascending=False)

    def by_stock(self, min_trades: int = 3) -> pd.DataFrame:
        """按个股维度统计 (过滤掉样本太少的)"""
        if self.df.empty:
            return pd.DataFrame()

        grouped = self.df.groupby("stock_code").agg(
            stock_name=("stock_name", "first"),
            total_trades=("label", "count"),
            hit_rate=("label", lambda x: (x == 1).mean()),
            avg_pnl=("pnl_pct", "mean"),
        )
        grouped = grouped[grouped["total_trades"] >= min_trades]
        return grouped.sort_values("hit_rate", ascending=False)


if __name__ == "__main__":
    # 简单示例
    recorder = LiveTestRecorder()
    today = datetime.now().strftime("%Y-%m-%d")

    # 假设记录一笔打板预测
    rec = TradeRecord(
        date=today,
        stock_code="300059",
        stock_name="东方财富",
        strategy="limit_up_predict_v4",
        signal="limit_up",
        prob=0.78,
        entry_price=14.65,
        exit_price=15.10,
        pnl_pct=(15.10 / 14.65 - 1) * 100,
        label=1,
        notes="一字板成功",
    )
    recorder.append_record(rec)

    df_all = recorder.load_all()
    analyzer = LiveTestAnalyzer(df_all)
    print("整体指标:", analyzer.basic_metrics())
    print("\n按策略:")
    print(analyzer.by_strategy())
