#!/usr/bin/env python3
"""
多数据源股票数据采集
整合东方财富、同花顺等公开数据源
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "crawl_all.log"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class StockDataCollector:
    """股票数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
    
    def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        """随机延时，防止被封"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def get_eastmoney_zt(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        东方财富涨停股
        """
        log("获取东方财富涨停股...")
        
        url = "http://push2ex.eastmoney.com/getTopicZTPool"
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": "0",
            "pagesize": "500",
            "sort": "fbt:asc",
            "date": trade_date
        }
        
        try:
            self._random_delay()
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get("data") and data["data"].get("pool"):
                df = pd.DataFrame(data["data"]["pool"])
                
                # 标准化字段名
                df = df.rename(columns={
                    "c": "code",
                    "n": "name",
                    "p": "price",
                    "zdp": "change_pct",
                    "amount": "amount",
                    "ltsj": "limit_up_time",
                    "hybk": "sector",
                    "zttj": "zt_info"
                })
                
                # 解析连板信息
                if "zt_info" in df.columns:
                    df["limit_up_days"] = df["zt_info"].apply(lambda x: x.get("days", 0) if isinstance(x, dict) else 0)
                    df["limit_up_count"] = df["zt_info"].apply(lambda x: x.get("ct", 0) if isinstance(x, dict) else 0)
                    df = df.drop("zt_info", axis=1)
                
                df["date"] = trade_date
                df["source"] = "eastmoney_zt"
                
                log(f"东方财富涨停股: {len(df)} 条")
                return df
            
            return None
            
        except Exception as e:
            log(f"东方财富涨停股失败: {e}", "ERROR")
            return None
    
    def get_eastmoney_longhu(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        东方财富龙虎榜
        """
        log("获取东方财富龙虎榜...")
        
        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "SECURITY_CODE",
            "sortTypes": "1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DMSK_TS",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB"
        }
        
        try:
            self._random_delay(3, 6)
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get("result") and data["result"].get("data"):
                df = pd.DataFrame(data["result"]["data"])
                df["date"] = trade_date
                df["source"] = "eastmoney_longhu"
                
                log(f"东方财富龙虎榜: {len(df)} 条")
                return df
            
            return None
            
        except Exception as e:
            log(f"东方财富龙虎榜失败: {e}", "ERROR")
            return None
    
    def get_all_data(self, trade_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取所有数据源
        """
        results = {}
        
        # 涨停股
        zt_df = self.get_eastmoney_zt(trade_date)
        if zt_df is not None:
            results["zt"] = zt_df
        
        # 龙虎榜
        longhu_df = self.get_eastmoney_longhu(trade_date)
        if longhu_df is not None:
            results["longhu"] = longhu_df
        
        return results


def save_data(data_dict: Dict[str, pd.DataFrame], trade_date: str):
    """保存数据"""
    for name, df in data_dict.items():
        if df is None or df.empty:
            continue
        
        # 保存日文件
        daily_file = BASE_DIR / f"stock_{name}_{trade_date}.csv"
        df.to_csv(daily_file, index=False, encoding="utf-8-sig")
        log(f"保存日文件: {daily_file} ({len(df)} 条)")
        
        # 合并历史
        all_files = sorted(BASE_DIR.glob(f"stock_{name}_2*.csv"))
        if len(all_files) > 1:
            all_dfs = []
            for f in all_files:
                try:
                    tdf = pd.read_csv(f)
                    all_dfs.append(tdf)
                except Exception as e:
                    log(f"读取历史文件失败 {f}: {e}", "WARN")
            
            if all_dfs:
                hist = pd.concat(all_dfs, ignore_index=True)
                
                # 去重
                if "code" in hist.columns:
                    hist = hist.drop_duplicates(subset=["date", "code"], keep="last")
                
                # 按日期排序
                hist = hist.sort_values("date").reset_index(drop=True)
                
                # 保存历史总表
                hist_file = BASE_DIR / f"stock_{name}_history.csv"
                hist.to_csv(hist_file, index=False, encoding="utf-8-sig")
                log(f"历史合并: {hist_file} ({len(hist)} 条)")


def main():
    log("=" * 60)
    log("多数据源股票数据采集")
    log("=" * 60)
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 支持命令行指定日期
    import sys
    if len(sys.argv) > 1:
        today = sys.argv[1]
        log(f"采集指定日期: {today}")
    else:
        log(f"采集今日数据: {today}")
    
    collector = StockDataCollector()
    data = collector.get_all_data(today)
    
    if data:
        save_data(data, today)
        total = sum(len(df) for df in data.values())
        log(f"采集完成，共 {len(data)} 个数据源，{total} 条数据")
    else:
        log("未获取到任何数据", "WARN")
    
    log("=" * 60)


if __name__ == "__main__":
    main()
