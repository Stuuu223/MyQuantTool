#!/usr/bin/env python3
"""
同花顺热门股票数据采集
无需登录，直接获取公开数据
"""

import json
import time
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
    import pandas as pd
except ImportError:
    print("请先安装依赖: pip install requests pandas")
    import sys
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "ths_crawl.log"

# 同花顺API配置
THS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "http://stockpage.10jqka.com.cn/",
}


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class THSDataCollector:
    """同花顺数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(THS_HEADERS)
    
    def get_hot_stock_rank(self) -> Optional[pd.DataFrame]:
        """
        获取同花顺热股榜
        来源: http://stockpage.10jqka.com.cn/hotstock/
        """
        log("获取同花顺热股榜...")
        
        # 同花顺热股榜API
        url = "http://stockpage.10jqka.com.cn/hotstock/"
        
        try:
            time.sleep(random.uniform(1, 3))
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            # 解析HTML中的数据
            html = resp.text
            
            # 尝试提取JSON数据
            # 同花顺数据通常在script标签中
            json_match = re.search(r'var\s+hotStock\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                df = pd.DataFrame(data)
                log(f"热股榜获取成功: {len(df)} 条")
                return df
            
            # 备用：尝试其他格式
            json_match2 = re.search(r'"data":\s*(\[.*?\])', html, re.DOTALL)
            if json_match2:
                data = json.loads(json_match2.group(1))
                df = pd.DataFrame(data)
                return df
            
            log("未找到热股榜数据", "WARN")
            return None
            
        except Exception as e:
            log(f"热股榜获取失败: {e}", "ERROR")
            return None
    
    def get_limit_up_stocks(self) -> Optional[pd.DataFrame]:
        """
        获取涨停股票列表
        来源: 同花顺涨停榜
        """
        log("获取涨停股票...")
        
        # 涨停榜API
        url = "http://stockpage.10jqka.com.cn/zrztb/"
        
        try:
            time.sleep(random.uniform(1, 3))
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            html = resp.text
            
            # 提取涨停数据
            json_match = re.search(r'var\s+zrztb\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                df = pd.DataFrame(data)
                log(f"涨停榜获取成功: {len(df)} 条")
                return df
            
            log("未找到涨停数据", "WARN")
            return None
            
        except Exception as e:
            log(f"涨停榜获取失败: {e}", "ERROR")
            return None
    
    def get_longhu_bang(self) -> Optional[pd.DataFrame]:
        """
        获取龙虎榜数据
        来源: 同花顺数据中心
        """
        log("获取龙虎榜数据...")
        
        # 龙虎榜API
        url = "http://data.10jqka.com.cn/ifmarket/lhbggxq/quote/"
        
        try:
            time.sleep(random.uniform(2, 4))
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            # 龙虎榜数据通常是JSONP格式
            text = resp.text
            
            # 提取JSON数据
            json_match = re.search(r'\((.*)\)', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                if "data" in data:
                    df = pd.DataFrame(data["data"])
                    log(f"龙虎榜获取成功: {len(df)} 条")
                    return df
            
            log("未找到龙虎榜数据", "WARN")
            return None
            
        except Exception as e:
            log(f"龙虎榜获取失败: {e}", "ERROR")
            return None
    
    def get_all_data(self, trade_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取所有数据
        """
        results = {}
        
        # 热股榜
        hot_df = self.get_hot_stock_rank()
        if hot_df is not None:
            hot_df["date"] = trade_date
            hot_df["source"] = "ths_hot"
            results["hot"] = hot_df
        
        # 涨停榜
        limit_df = self.get_limit_up_stocks()
        if limit_df is not None:
            limit_df["date"] = trade_date
            limit_df["source"] = "ths_limit_up"
            results["limit_up"] = limit_df
        
        # 龙虎榜
        longhu_df = self.get_longhu_bang()
        if longhu_df is not None:
            longhu_df["date"] = trade_date
            longhu_df["source"] = "ths_longhu"
            results["longhu"] = longhu_df
        
        return results


def save_data(data_dict: Dict[str, pd.DataFrame], trade_date: str):
    """保存数据"""
    for name, df in data_dict.items():
        if df is None or df.empty:
            continue
        
        # 保存日文件
        daily_file = BASE_DIR / f"ths_{name}_{trade_date}.csv"
        df.to_csv(daily_file, index=False, encoding="utf-8-sig")
        log(f"保存: {daily_file} ({len(df)} 条)")
        
        # 合并历史
        all_files = sorted(BASE_DIR.glob(f"ths_{name}_2*.csv"))
        if len(all_files) > 1:
            all_dfs = [pd.read_csv(f) for f in all_files]
            hist = pd.concat(all_dfs, ignore_index=True)
            
            # 去重
            if "code" in hist.columns:
                hist = hist.drop_duplicates(subset=["date", "code"], keep="last")
            
            hist_file = BASE_DIR / f"ths_{name}_history.csv"
            hist.to_csv(hist_file, index=False, encoding="utf-8-sig")
            log(f"历史合并: {hist_file} ({len(hist)} 条)")


def main():
    log("=" * 60)
    log("同花顺数据采集开始")
    log("=" * 60)
    
    today = datetime.now().strftime("%Y%m%d")
    
    collector = THSDataCollector()
    data = collector.get_all_data(today)
    
    if data:
        save_data(data, today)
        log(f"采集完成，共 {len(data)} 个数据源")
    else:
        log("未获取到任何数据", "WARN")
    
    log("=" * 60)


if __name__ == "__main__":
    main()
