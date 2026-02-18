#!/usr/bin/env python3
"""
安全批量采集历史数据 - 防封策略
东方财富限制：每分钟不超过700次，建议每秒不超过5次
策略：每次请求间隔 5-8 秒，每天只请求1-2次
"""

import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "crawl_history.log"


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class SafeStockCollector:
    """安全股票数据采集器 - 防封版"""
    
    # 安全策略参数
    MIN_DELAY = 5.0  # 最小延迟5秒
    MAX_DELAY = 8.0  # 最大延迟8秒
    MAX_RETRY = 3    # 最大重试次数
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "http://quote.eastmoney.com/",
            "Connection": "keep-alive"
        })
        self.request_count = 0
        self.start_time = datetime.now()
    
    def _safe_delay(self):
        """安全延时 - 随机5-8秒"""
        delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
        log(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def _check_rate(self):
        """检查请求速率"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            rate = self.request_count / elapsed
            if rate > 0.2:  # 每秒超过0.2次（即5秒1次）就减速
                extra_delay = random.uniform(3, 5)
                log(f"速率过高 ({rate:.2f}/s)，额外等待 {extra_delay:.1f} 秒")
                time.sleep(extra_delay)
    
    def _make_request(self, url: str, params: dict, headers: dict = None) -> Optional[dict]:
        """安全请求 - 带重试机制"""
        for attempt in range(self.MAX_RETRY):
            try:
                # 检查速率
                self._check_rate()
                
                # 延时
                if self.request_count > 0:
                    self._safe_delay()
                
                # 发送请求
                log(f"请求: {url[:60]}... (尝试 {attempt + 1}/{self.MAX_RETRY})")
                resp = self.session.get(url, params=params, headers=headers, timeout=20)
                self.request_count += 1
                
                # 检查状态
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except:
                        log(f"JSON解析失败: {resp.text[:100]}", "WARN")
                        return None
                elif resp.status_code == 403:
                    log(f"IP可能被禁 (403)，等待60秒", "ERROR")
                    time.sleep(60)
                elif resp.status_code == 429:
                    log(f"请求过于频繁 (429)，等待120秒", "ERROR")
                    time.sleep(120)
                else:
                    log(f"HTTP错误: {resp.status_code}", "WARN")
                    
            except requests.exceptions.Timeout:
                log(f"请求超时，等待10秒后重试", "WARN")
                time.sleep(10)
            except Exception as e:
                log(f"请求异常: {e}", "ERROR")
                time.sleep(5)
        
        return None
    
    def get_eastmoney_zt(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        获取东方财富涨停股 - 指定日期
        """
        log(f"获取 {trade_date} 涨停数据...")
        
        url = "http://push2ex.eastmoney.com/getTopicZTPool"
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": "0",
            "pagesize": "500",
            "sort": "fbt:asc",
            "date": trade_date
        }
        
        data = self._make_request(url, params)
        
        if data and data.get("data") and data["data"].get("pool"):
            df = pd.DataFrame(data["data"]["pool"])
            
            # 标准化字段
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
                df["limit_up_days"] = df["zt_info"].apply(
                    lambda x: x.get("days", 0) if isinstance(x, dict) else 0
                )
                df["limit_up_count"] = df["zt_info"].apply(
                    lambda x: x.get("ct", 0) if isinstance(x, dict) else 0
                )
                df = df.drop("zt_info", axis=1)
            
            df["date"] = trade_date
            df["source"] = "eastmoney_zt"
            
            log(f"✓ {trade_date} 涨停股: {len(df)} 条")
            return df
        
        log(f"✗ {trade_date} 无数据", "WARN")
        return None
    
    def crawl_date_range(self, start_date: str, end_date: str):
        """
        批量采集日期范围的数据
        """
        log("=" * 60)
        log(f"开始批量采集: {start_date} 至 {end_date}")
        log("=" * 60)
        
        # 生成交易日列表（排除周末）
        dates = []
        current = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        while current <= end:
            # 只采集周一到周五
            if current.weekday() < 5:
                dates.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)
        
        log(f"共 {len(dates)} 个交易日需要采集")
        
        all_data = []
        success_count = 0
        fail_count = 0
        
        for i, date_str in enumerate(dates, 1):
            log(f"\n[{i}/{len(dates)}] 采集 {date_str}")
            
            df = self.get_eastmoney_zt(date_str)
            
            if df is not None and not df.empty:
                all_data.append(df)
                success_count += 1
                
                # 每10天保存一次中间结果
                if i % 10 == 0 and all_data:
                    self._save_intermediate(all_data, i)
            else:
                fail_count += 1
            
            # 每30天暂停一下，防止长时间运行被封
            if i % 30 == 0:
                pause_time = random.uniform(30, 60)
                log(f"\n已采集30天，暂停 {pause_time:.0f} 秒...")
                time.sleep(pause_time)
        
        # 保存最终结果
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            self._save_final(final_df, start_date, end_date)
            
            log("\n" + "=" * 60)
            log(f"采集完成: 成功 {success_count} 天, 失败 {fail_count} 天")
            log(f"总数据: {len(final_df)} 条")
            log(f"请求次数: {self.request_count}")
            log(f"总耗时: {(datetime.now() - self.start_time).total_seconds() / 60:.1f} 分钟")
            log("=" * 60)
            
            return final_df
        else:
            log("未获取到任何数据", "ERROR")
            return None
    
    def _save_intermediate(self, data_list: list, batch_num: int):
        """保存中间结果"""
        df = pd.concat(data_list, ignore_index=True)
        file_path = BASE_DIR / f"zt_history_batch_{batch_num}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        log(f"保存中间结果: {file_path} ({len(df)} 条)")
    
    def _save_final(self, df: pd.DataFrame, start_date: str, end_date: str):
        """保存最终结果"""
        # 去重
        if "code" in df.columns:
            df = df.drop_duplicates(subset=["date", "code"], keep="last")
        
        # 排序
        df = df.sort_values(["date", "code"]).reset_index(drop=True)
        
        # 保存
        file_path = BASE_DIR / f"zt_history_{start_date}_{end_date}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        log(f"\n✓ 保存最终结果: {file_path}")
        log(f"  总记录: {len(df)} 条")
        log(f"  日期范围: {df['date'].min()} 至 {df['date'].max()}")
        log(f"  股票数: {df['code'].nunique()} 只")


def main():
    """
    主函数 - 采集近三个月数据
    """
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    log("\n" + "=" * 60)
    log("东方财富涨停股历史数据采集")
    log("=" * 60)
    log(f"采集范围: {start_str} 至 {end_str}")
    log(f"安全策略: 每次请求间隔 {SafeStockCollector.MIN_DELAY}-{SafeStockCollector.MAX_DELAY} 秒")
    log(f"预计耗时: 约 {(90 * 6 / 60):.0f} 分钟")
    log("=" * 60 + "\n")
    
    # 开始采集
    collector = SafeStockCollector()
    df = collector.crawl_date_range(start_str, end_str)
    
    if df is not None:
        log("\n✓ 采集成功！")
        log(f"数据文件: zt_history_{start_str}_{end_str}.csv")
    else:
        log("\n✗ 采集失败", "ERROR")


if __name__ == "__main__":
    main()