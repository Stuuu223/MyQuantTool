#!/usr/bin/env python3
"""
顽主杯小程序数据采集脚本
功能：每日自动采集顽主杯榜单数据，生成标准CSV格式
作者：AI Assistant
日期：2026-02-18
"""

import json
import time
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
    import requests
except ImportError as e:
    print(f"[ERROR] 缺少依赖: {e}")
    print("请运行: pip install requests pandas")
    sys.exit(1)


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "wanzhu_miniprogram_config.json"
LOG_PATH = BASE_DIR / "crawl.log"


def log_message(msg: str, level: str = "INFO"):
    """输出并记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] [{level}] {msg}"
    print(full_msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")


def load_config() -> dict:
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_wanzhu_for_date(trade_date: str, config: dict) -> Optional[pd.DataFrame]:
    """
    获取指定日期的顽主杯榜单数据
    
    Args:
        trade_date: 交易日期，格式 'YYYYMMDD'
        config: 配置字典
        
    Returns:
        DataFrame或None（如果失败）
    """
    url = config["base_url"]
    headers = config.get("headers", {})
    params = config.get("default_params", {}).copy()
    
    # 动态添加日期参数
    params["date"] = trade_date
    
    # 随机延时，避免被风控
    delay = random.uniform(1.0, 3.0)
    log_message(f"等待 {delay:.1f} 秒后发送请求...")
    time.sleep(delay)
    
    try:
        resp = requests.get(
            url, 
            headers=headers, 
            params=params, 
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 解析响应数据（根据实际抓包结构调整）
        items = None
        
        # 尝试多种可能的字段名
        for key in ["list", "stocks", "data", "rankings", "result", "items"]:
            if key in data:
                items = data[key]
                break
        
        # 如果直接是数组
        if items is None and isinstance(data, list):
            items = data
            
        if not items:
            log_message(f"{trade_date} 没有返回榜单数据", "WARN")
            return None
        
        df = pd.DataFrame(items)
        
        # 标准化字段名（映射到MyQuantTool标准格式）
        field_mappings = {
            # 原始字段名 -> 标准字段名
            "stockCode": "code",
            "stock_code": "code", 
            "symbol": "code",
            "股票代码": "code",
            
            "stockName": "name",
            "stock_name": "name",
            "stock": "name",
            "股票名称": "name",
            
            "rank": "rank",
            "ranking": "rank",
            "排名": "rank",
            
            "industryName": "sector",
            "industry": "sector",
            "industry_name": "sector",
            "板块": "sector",
            "行业": "sector",
            
            "holderCount": "holder_count",
            "holder_count": "holder_count",
            "holderNum": "holder_count",
            "持股人数": "holder_count",
            
            "holdingAmount": "holding_amount",
            "holding_amount": "holding_amount",
            "amount": "holding_amount",
            "持仓金额": "holding_amount",
            
            "change": "change_pct",
            "changePct": "change_pct",
            "涨跌幅": "change_pct",
            
            "score": "score",
            "得分": "score",
        }
        
        # 执行字段映射
        rename_dict = {}
        for old_col in df.columns:
            if old_col in field_mappings:
                rename_dict[old_col] = field_mappings[old_col]
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # 添加日期列
        df["date"] = trade_date
        
        # 确保code字段格式统一（6位数字，不足补零）
        if "code" in df.columns:
            df["code"] = df["code"].astype(str).str.zfill(6)
        
        # 调整列顺序
        standard_cols = ["date", "code", "name", "rank", "sector", 
                        "holder_count", "holding_amount", "change_pct", "score"]
        
        # 先放标准列（如果存在），再放其他列
        ordered_cols = [c for c in standard_cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in standard_cols]
        df = df[ordered_cols + other_cols]
        
        log_message(f"{trade_date} 成功获取 {len(df)} 条数据")
        return df
        
    except requests.exceptions.RequestException as e:
        log_message(f"{trade_date} 请求失败: {e}", "ERROR")
        return None
    except Exception as e:
        log_message(f"{trade_date} 处理失败: {e}", "ERROR")
        return None


def save_daily_and_merge(df: pd.DataFrame, trade_date: str) -> None:
    """
    保存日数据并合并历史
    
    Args:
        df: 当日数据DataFrame
        trade_date: 交易日期
    """
    # 保存日文件
    daily_file = BASE_DIR / f"wanzhu_miniprogram_{trade_date}.csv"
    df.to_csv(daily_file, index=False, encoding="utf-8-sig")
    log_message(f"{trade_date} 日文件已保存: {daily_file}")
    
    # 合并所有历史数据
    all_files = sorted(BASE_DIR.glob("wanzhu_miniprogram_2*.csv"))
    all_dfs = []
    
    for f in all_files:
        try:
            tdf = pd.read_csv(f)
            all_dfs.append(tdf)
        except Exception as e:
            log_message(f"读取历史文件失败 {f}: {e}", "WARN")
    
    if not all_dfs:
        log_message("没有历史数据可合并", "WARN")
        return
    
    # 合并并去重
    hist = pd.concat(all_dfs, ignore_index=True)
    
    # 去重逻辑
    if "code" in hist.columns:
        hist = hist.drop_duplicates(subset=["date", "code"], keep="last")
    elif "name" in hist.columns:
        hist = hist.drop_duplicates(subset=["date", "name"], keep="last")
    else:
        hist = hist.drop_duplicates(subset=["date"], keep="last")
    
    # 按日期排序
    hist = hist.sort_values("date").reset_index(drop=True)
    
    # 保存历史总表
    hist_file = BASE_DIR / "wanzhu_miniprogram_history.csv"
    hist.to_csv(hist_file, index=False, encoding="utf-8-sig")
    log_message(f"历史合并完成: {hist_file} 共 {len(hist)} 行")
    
    # 同时生成MyQuantTool兼容格式
    export_for_myquanttool(hist)


def export_for_myquanttool(df: pd.DataFrame) -> None:
    """
    导出MyQuantTool兼容格式
    """
    # 复制数据
    export_df = df.copy()
    
    # 确保必要字段存在
    required_cols = ["date", "code", "name"]
    for col in required_cols:
        if col not in export_df.columns:
            log_message(f"缺少必要字段: {col}", "WARN")
    
    # 保存为MyQuantTool标准格式
    export_file = BASE_DIR / "wanzhu_history_from_miniprogram.csv"
    export_df.to_csv(export_file, index=False, encoding="utf-8-sig")
    log_message(f"MyQuantTool格式已导出: {export_file}")


def get_last_n_trade_dates(n: int = 5) -> list:
    """
    获取最近N个交易日日期（简化版，实际应该排除节假日）
    """
    dates = []
    current = datetime.now()
    
    while len(dates) < n:
        # 跳过周末
        if current.weekday() < 5:  # 0-4 是周一到周五
            dates.append(current.strftime("%Y%m%d"))
        current -= timedelta(days=1)
    
    return dates


def main():
    """主函数"""
    log_message("=" * 50)
    log_message("顽主杯小程序数据采集开始")
    log_message("=" * 50)
    
    # 加载配置
    try:
        config = load_config()
        log_message("配置文件加载成功")
    except Exception as e:
        log_message(f"加载配置失败: {e}", "ERROR")
        sys.exit(1)
    
    # 确定采集日期
    if len(sys.argv) > 1:
        # 命令行指定日期
        target_date = sys.argv[1]
        log_message(f"采集指定日期: {target_date}")
    else:
        # 默认采集今天
        target_date = datetime.now().strftime("%Y%m%d")
        log_message(f"采集今日数据: {target_date}")
    
    # 执行采集
    try:
        df = fetch_wanzhu_for_date(target_date, config)
        
        if df is None or df.empty:
            log_message(f"{target_date} 无数据，跳过保存", "WARN")
            sys.exit(0)
        
        # 保存和合并
        save_daily_and_merge(df, target_date)
        log_message("采集完成")
        
    except Exception as e:
        log_message(f"采集过程出错: {e}", "ERROR")
        import traceback
        log_message(traceback.format_exc(), "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()