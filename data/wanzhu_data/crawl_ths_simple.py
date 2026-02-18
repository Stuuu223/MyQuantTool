#!/usr/bin/env python3
"""
同花顺数据采集 - 简化版
使用同花顺公开API接口
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "ths_crawl.log"


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_ths_zt_ban():
    """
    获取同花顺涨停榜数据
    接口: http://data.10jqka.com.cn/rank/ztrank/
    """
    log("获取涨停榜数据...")
    
    url = "http://data.10jqka.com.cn/rank/ztrank/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "http://data.10jqka.com.cn/"
    }
    
    try:
        time.sleep(random.uniform(1, 3))
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        
        # 解析HTML中的数据
        html = resp.text
        
        # 查找数据
        import re
        match = re.search(r'var\s+data\s*=\s*(\[.*?\]);', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            df = pd.DataFrame(data)
            log(f"涨停榜: {len(df)} 条")
            return df
        
        log("未找到涨停数据", "WARN")
        return None
        
    except Exception as e:
        log(f"涨停榜失败: {e}", "ERROR")
        return None


def get_ths_hot():
    """
    获取同花顺热股榜
    """
    log("获取热股榜...")
    
    # 尝试多个可能的接口
    urls = [
        "http://stockpage.10jqka.com.cn/hotstock/",
        "http://data.10jqka.com.cn/rank/hotstock/",
    ]
    
    for url in urls:
        try:
            time.sleep(random.uniform(1, 2))
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://stockpage.10jqka.com.cn/"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            
            # 尝试解析
            html = resp.text
            
            # 方法1: 查找JSON变量
            import re
            patterns = [
                r'var\s+hotStock\s*=\s*(\[.*?\]);',
                r'var\s+data\s*=\s*(\[.*?\]);',
                r'"data":\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if isinstance(data, list) and len(data) > 0:
                            df = pd.DataFrame(data)
                            log(f"热股榜: {len(df)} 条")
                            return df
                    except:
                        continue
            
        except Exception as e:
            log(f"{url} 失败: {e}", "WARN")
            continue
    
    log("热股榜未找到", "WARN")
    return None


def main():
    log("=" * 60)
    log("同花顺数据采集")
    log("=" * 60)
    
    today = datetime.now().strftime("%Y%m%d")
    
    # 采集热股榜
    hot_df = get_ths_hot()
    if hot_df is not None:
        hot_df["date"] = today
        hot_df["source"] = "ths_hot"
        
        # 保存
        file_path = BASE_DIR / f"ths_hot_{today}.csv"
        hot_df.to_csv(file_path, index=False, encoding="utf-8-sig")
        log(f"保存: {file_path}")
        
        # 显示前几行
        print("\n热股榜预览:")
        print(hot_df.head())
    
    # 采集涨停榜
    zt_df = get_ths_zt_ban()
    if zt_df is not None:
        zt_df["date"] = today
        zt_df["source"] = "ths_zt"
        
        file_path = BASE_DIR / f"ths_zt_{today}.csv"
        zt_df.to_csv(file_path, index=False, encoding="utf-8-sig")
        log(f"保存: {file_path}")
        
        print("\n涨停榜预览:")
        print(zt_df.head())
    
    log("=" * 60)


if __name__ == "__main__":
    main()
