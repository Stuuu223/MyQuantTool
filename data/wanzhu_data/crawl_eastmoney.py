#!/usr/bin/env python3
"""
东方财富数据采集 - 带频率控制
获取龙虎榜、涨停数据
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_eastmoney_longhu():
    """
    东方财富龙虎榜
    接口: http://data.eastmoney.com/stock/lhb.html
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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://data.eastmoney.com/"
    }
    
    try:
        time.sleep(random.uniform(2, 5))  # 控制频率
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        
        if data.get("result") and data["result"].get("data"):
            df = pd.DataFrame(data["result"]["data"])
            log(f"龙虎榜: {len(df)} 条")
            return df
        
        return None
        
    except Exception as e:
        log(f"龙虎榜失败: {e}")
        return None


def get_eastmoney_zt():
    """
    东方财富涨停股
    """
    log("获取涨停股...")
    
    url = "http://push2ex.eastmoney.com/getTopicZTPool"
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "200",
        "sort": "fbt:asc",
        "date": datetime.now().strftime("%Y%m%d")
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        time.sleep(random.uniform(2, 5))
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        
        if data.get("data") and data["data"].get("pool"):
            df = pd.DataFrame(data["data"]["pool"])
            log(f"涨停股: {len(df)} 条")
            return df
        
        return None
        
    except Exception as e:
        log(f"涨停股失败: {e}")
        return None


def main():
    log("=" * 60)
    log("东方财富数据采集")
    log("=" * 60)
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 获取涨停股
    zt_df = get_eastmoney_zt()
    if zt_df is not None:
        zt_df["date"] = today
        file_path = BASE_DIR / f"em_zt_{today}.csv"
        zt_df.to_csv(file_path, index=False, encoding="utf-8-sig")
        log(f"保存: {file_path}")
        print("\n涨停股预览:")
        print(zt_df.head(10))
    
    log("=" * 60)


if __name__ == "__main__":
    main()
