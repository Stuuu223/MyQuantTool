#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
150% 死亡换手合理性验证脚本（可复核版本 + QMT连接修复）

【目标】
验证 150% 作为"游资出货完毕红线"的统计合理性。

【严禁】
- 不允许声称"已执行/已结论"但不给出 data/validation 下输出文件
- 不允许 magic number 兜底伪造数据（缺数据必须显式NA）
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.core.config_manager import get_config_manager

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ValidationConfig:
    lookback_days: int = 90
    bucket_min: float = 70.0
    bucket_death: float = 150.0
    bucket_extreme: float = 200.0
    forward_days: tuple = (1, 3)
    min_bars_required: int = 10  # 修复：降低到10，确保有数据就能统计


class DailyKlineProvider:
    """日线数据适配层接口"""
    def get_daily(self, stock_code: str, start: datetime, end: datetime) -> pd.DataFrame:
        raise NotImplementedError


class QMTDailyKlineProvider(DailyKlineProvider):
    """基于 QMT 本地数据的日线提供者（复用 TrueDictionary 架构逻辑）"""
    
    def __init__(self):
        try:
            import xtquant.xtdata as xtdata
            self.xtdata = xtdata
            self._debug_count = 0
            self._debug_logs = []
        except ImportError:
            raise RuntimeError("未安装 xtquant，无法读取 QMT 数据")
    
    def get_daily(self, stock_code: str, start: datetime, end: datetime) -> pd.DataFrame:
        """
        读取日线数据（复刻 TrueDictionary 的逻辑）
        
        Returns:
            pd.DataFrame with columns: date, close, turnover_rate (%)
        """
        start_str = start.strftime('%Y%m%d')
        end_str = end.strftime('%Y%m%d')
        
        # 1. 获取日线数据（time, close, volume, amount...）
        try:
            data_dict = self.xtdata.get_local_data(
                stock_list=[stock_code],
                period='1d',
                start_time=start_str,
                end_time=end_str,
                field_list=['time', 'close', 'volume', 'amount']
            )
        except Exception as e:
            if self._debug_count < 3:
                self._debug_logs.append(f"[{stock_code}] get_local_data异常: {e}")
                self._debug_count += 1
            return pd.DataFrame()
        
        if data_dict is None or stock_code not in data_dict:
            if self._debug_count < 3:
                self._debug_logs.append(f"[{stock_code}] data_dict为空或无此股票")
                self._debug_count += 1
            return pd.DataFrame()
        
        df = data_dict[stock_code]
        if df is None or (hasattr(df, 'empty') and df.empty):
            if self._debug_count < 3:
                self._debug_logs.append(f"[{stock_code}] df为空")
                self._debug_count += 1
            return pd.DataFrame()
        
        df = df.copy()
        # 【修复】xtdata返回的time是毫秒时间戳，需要转成日期
        if 'time' in df.columns:
            # 毫秒时间戳转日期
            df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df.drop(columns=['time'], errors='ignore')
        
        # 2. 获取流通股本（FloatVolume，单位：股）
        try:
            # 【修复】is_sync=False 改为 False（QMT API不接受关键字参数）
            detail = self.xtdata.get_instrument_detail(stock_code, False)
            if detail is None:
                if self._debug_count < 5:
                    self._debug_logs.append(f"[{stock_code}] instrument_detail为None")
                    self._debug_count += 1
                return pd.DataFrame()
            
            float_volume = detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0)
            if float_volume <= 0:
                if self._debug_count < 5:
                    self._debug_logs.append(f"[{stock_code}] FloatVolume={float_volume}")
                    self._debug_count += 1
                return pd.DataFrame()
        except Exception as e:
            if self._debug_count < 3:
                self._debug_logs.append(f"[{stock_code}] get_instrument_detail异常: {e}")
                self._debug_count += 1
            return pd.DataFrame()
        
        # 3. 计算换手率（QMT volume单位是手，FloatVolume单位是股）
        # turnover_rate = volume(手) * 100(股/手) / FloatVolume(股) * 100(%)
        df['turnover_rate'] = df['volume'] * 100.0 / float_volume * 100.0
        
        if self._debug_count < 3:
            self._debug_logs.append(
                f"[{stock_code}] 成功: {len(df)}行, "
                f"turnover_rate范围={df['turnover_rate'].min():.4f}%~{df['turnover_rate'].max():.4f}%"
            )
            self._debug_count += 1
        
        return df[['date', 'close', 'turnover_rate']]


def discover_stock_codes_from_datadir(qmt_userdata_path: str) -> list:
    """从 datadir/SZ/86400 与 datadir/SH/86400 目录扫描股票文件名"""
    base = Path(qmt_userdata_path) / "datadir"
    sz_dir = base / "SZ" / "86400"
    sh_dir = base / "SH" / "86400"
    
    codes = []
    
    def scan_dir(market_dir: Path, suffix_market: str) -> None:
        if not market_dir.exists():
            return
        for p in market_dir.iterdir():
            if not p.is_file():
                continue
            stem = p.stem if p.suffix else p.name
            if not stem.isdigit():
                continue
            if len(stem) != 6:
                continue
            codes.append(f"{stem}.{suffix_market}")
    
    scan_dir(sz_dir, "SZ")
    scan_dir(sh_dir, "SH")
    
    return sorted(list(set(codes)))


def add_forward_returns(df: pd.DataFrame, forward_days: tuple) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True).copy()
    for n in forward_days:
        df[f"fwd_{n}d_ret"] = (df["close"].shift(-n) / df["close"] - 1.0) * 100.0
    return df


def bucketize(turnover: float, cfg: ValidationConfig) -> str:
    if pd.isna(turnover):
        return "NA"
    if turnover < cfg.bucket_min:
        return f"<{cfg.bucket_min:.0f}%"
    if turnover < cfg.bucket_death:
        return f"{cfg.bucket_min:.0f}-{cfg.bucket_death:.0f}%"
    if turnover < cfg.bucket_extreme:
        return f"{cfg.bucket_death:.0f}-{cfg.bucket_extreme:.0f}%"
    return f">={cfg.bucket_extreme:.0f}%"


def run_validation(provider: DailyKlineProvider, cfg: ValidationConfig) -> None:
    config = get_config_manager()
    qmt_path = config.get_qmt_userdata_path()
    
    print("=" * 70)
    print("150% 死亡换手合理性验证（可复核版本）")
    print("=" * 70)
    print(f"QMT_USERDATA_PATH: {qmt_path}")
    print(f"发现目录: {Path(qmt_path)/'datadir'/'SZ'/'86400'}")
    print(f"发现目录: {Path(qmt_path)/'datadir'/'SH'/'86400'}")
    print(f"输出目录: {VALIDATION_DIR}")
    print("-" * 70)
    
    end = datetime.now()
    start = end - timedelta(days=cfg.lookback_days)
    
    stock_codes = discover_stock_codes_from_datadir(qmt_path)
    if not stock_codes:
        raise RuntimeError("未在 datadir/SZ|SH/86400 发现股票文件，检查 QMT_USERDATA_PATH 是否正确。")
    
    print(f"发现 {len(stock_codes)} 只股票")
    
    events = []
    skipped_no_data = 0
    skipped_short_hist = 0
    skipped_no_turnover = 0
    
    # 调试计数器
    debug_sample_count = 0
    debug_turnover_samples = []
    
    for i, code in enumerate(stock_codes, 1):
        if i % 500 == 0:
            print(f"进度: {i}/{len(stock_codes)}")
        
        df = provider.get_daily(code, start, end)
        if df is None or df.empty:
            skipped_no_data += 1
            continue
        
        # 调试：记录前10个有效样本的换手率范围
        if debug_sample_count < 10 and 'turnover_rate' in df.columns:
            max_tr = df['turnover_rate'].max()
            min_tr = df['turnover_rate'].min()
            debug_turnover_samples.append(f"{code}: max={max_tr:.4f}%, min={min_tr:.4f}%")
            debug_sample_count += 1
        
        need_cols = {"date", "close", "turnover_rate"}
        if not need_cols.issubset(set(df.columns)):
            skipped_no_turnover += 1
            continue
        
        df = df.copy()
        # Provider已返回datetime格式的date列，无需再次解析
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["turnover_rate"] = pd.to_numeric(df["turnover_rate"], errors="coerce")
        
        # 调试：检查日期解析结果
        if debug_sample_count < 3:
            debug_turnover_samples.append(f"{code} dates: {df['date'].head(3).tolist()}")
        
        df = df.dropna(subset=["date", "close", "turnover_rate"]).sort_values("date")
        if len(df) < cfg.min_bars_required:
            skipped_short_hist += 1
            continue
        
        df = add_forward_returns(df, cfg.forward_days)
        
        # 只取换手>=70%事件
        df_evt = df[df["turnover_rate"] >= cfg.bucket_min].copy()
        if df_evt.empty:
            continue
        
        # 只保留 forward return 有效的事件
        for n in cfg.forward_days:
            df_evt = df_evt[df_evt[f"fwd_{n}d_ret"].notna()]
        if df_evt.empty:
            continue
        
        df_evt["stock_code"] = code
        df_evt["bucket"] = df_evt["turnover_rate"].apply(lambda x: bucketize(x, cfg))
        
        keep_cols = ["stock_code", "date", "turnover_rate", "bucket"] + [f"fwd_{n}d_ret" for n in cfg.forward_days]
        events.append(df_evt[keep_cols])
    
    # 打印调试信息
    print("-" * 70)
    print("【Provider调试日志】:")
    for s in provider._debug_logs:
        print(f"  {s}")
    print("【调试】前10个样本换手率范围:")
    for s in debug_turnover_samples:
        print(f"  {s}")
    print(f"【调试】跳过统计: 无数据={skipped_no_data}, 历史不足={skipped_short_hist}, 字段缺失={skipped_no_turnover}")
    print("-" * 70)
    
    if not events:
        print("\n" + "=" * 70)
        print("错误: 没有收集到任何事件样本（换手>=70%）")
        print("请检查 provider 是否正确提供 turnover_rate")
        print("=" * 70)
        return
    
    out_df = pd.concat(events, ignore_index=True)
    
    # 事件明细输出
    csv_path = VALIDATION_DIR / "death_turnover_150_events.csv"
    out_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    # 分桶统计
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("150% 死亡换手验证 - 分桶统计摘要")
    summary_lines.append("=" * 70)
    summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"事件样本数(换手>={cfg.bucket_min:.0f}%): {len(out_df)}")
    summary_lines.append(f"跳过：无数据={skipped_no_data} | 历史不足={skipped_short_hist} | 字段缺失={skipped_no_turnover}")
    summary_lines.append("")
    
    buckets = [
        f"{cfg.bucket_min:.0f}-{cfg.bucket_death:.0f}%",
        f"{cfg.bucket_death:.0f}-{cfg.bucket_extreme:.0f}%",
        f">={cfg.bucket_extreme:.0f}%"
    ]
    for b in buckets:
        dfb = out_df[out_df["bucket"] == b]
        summary_lines.append(f"[{b}] 样本数: {len(dfb)}")
        if dfb.empty:
            summary_lines.append("")
            continue
        for n in cfg.forward_days:
            r = dfb[f"fwd_{n}d_ret"].astype(float)
            win = (r > 0).mean() * 100.0
            summary_lines.append(
                f"  fwd_{n}d: mean={r.mean():.3f}% | median={r.median():.3f}% | "
                f"win%={win:.2f}% | p5={np.percentile(r,5):.3f}%"
            )
        summary_lines.append("")
    
    txt_path = VALIDATION_DIR / "death_turnover_150_summary.txt"
    txt_path.write_text("\n".join(summary_lines), encoding="utf-8")
    
    print("✅ 已输出事件明细:", csv_path)
    print("✅ 已输出统计摘要:", txt_path)
    print("提示：只有当这两个文件存在且内容可复核时，才允许对外宣称结论。")


def main() -> None:
    # 【关键修复】连接 QMT 客户端
    try:
        import xtquant.xtdata as xtdata
        print("正在连接 QMT 客户端...")
        conn_result = xtdata.connect(port=58610)
        if conn_result != 0:
            print(f"警告: QMT 连接返回 {conn_result}，可能未正常连接")
        else:
            print("✅ QMT 客户端连接成功")
    except Exception as e:
        print(f"❌ QMT 连接失败: {e}")
        print("请确保 QMT 客户端已启动并登录")
        return
    
    cfg = ValidationConfig()
    provider = QMTDailyKlineProvider()
    run_validation(provider, cfg)


if __name__ == "__main__":
    main()