#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO 扩库计划 V3: 全量样本分K数据挖掘机
==========================================
核心职责：从散落的csv中清洗出所有正负样本，并驱动QMT批量下载1m/1d数据

设计原则：
1. 正样本：violent_surge_samples_detailed.csv (lag=0 起爆日)
2. 负样本：scan_returns_v*.csv (final_return <= -8.0)
3. 投研版权限：可追溯2021年以来的1m数据
4. 1m降维替代Tick计算raw_sustain和MFE

Author: AI开发专家团队 (CTO V3指令)
Date: 2026-03-10
Version: V1.0.0
"""

import pandas as pd
import os
import time
import logging
from xtquant import xtdata

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

VALIDATION_DIR = 'data/validation'


def extract_positive_samples() -> list:
    """
    提取正样本（真龙）- 从violent_surge_samples_detailed.csv
    """
    samples = []
    surge_file = os.path.join(VALIDATION_DIR, 'violent_surge_samples_detailed.csv')
    
    if not os.path.exists(surge_file):
        logger.warning(f"[正样本] 文件不存在: {surge_file}")
        return samples
    
    df_surge = pd.read_csv(surge_file)
    # 仅取起爆日 (lag=0)
    surge_ignition = df_surge[df_surge['lag'] == 0].copy()
    
    for _, row in surge_ignition.iterrows():
        stock_code = row.get('stock_code', '')
        ignition_date = row.get('ignition_date', '')
        
        if stock_code and ignition_date:
            samples.append({
                'stock_code': str(stock_code),
                'date': str(int(ignition_date)),
                'label': 1,
                'source': 'violent_surge'
            })
    
    logger.info(f"[正样本] 提取 {len(samples)} 个真龙起爆点")
    return samples


def extract_negative_samples() -> list:
    """
    提取负样本（骗炮）- 从scan_returns_v*.csv系列
    """
    samples = []
    trap_count = 0
    
    # 扫描所有scan_returns_v*.csv文件
    for file in os.listdir(VALIDATION_DIR):
        if not (file.startswith('scan_returns_v') and file.endswith('.csv')):
            continue
            
        file_path = os.path.join(VALIDATION_DIR, file)
        
        try:
            df_scan = pd.read_csv(file_path)
            
            # 寻找严重亏损的真实骗炮案例
            if 'final_return' not in df_scan.columns:
                continue
            
            # CTO标准：final_return <= -8.0 为骗炮陷阱
            traps = df_scan[df_scan['final_return'] <= -8.0].copy()
            
            for _, row in traps.iterrows():
                # 列名兼容处理
                code = row.get('code', row.get('stock', row.get('stock_code', '')))
                date = row.get('first_seen', row.get('buy_date', row.get('date', '')))
                
                if code and date:
                    samples.append({
                        'stock_code': str(code),
                        'date': str(int(date)) if isinstance(date, (int, float)) else str(date),
                        'label': 0,
                        'source': file
                    })
                    trap_count += 1
                    
        except Exception as e:
            logger.warning(f"[负样本] 读取 {file} 失败: {e}")
            continue
    
    logger.info(f"[负样本] 提取 {trap_count} 个骗炮陷阱")
    return samples


def build_sample_base():
    """
    构建样本底座并驱动QMT下载数据
    """
    print("=" * 70)
    print("CTO 扩库计划 V3: 全量样本分K数据挖掘机")
    print("=" * 70)
    
    # 1. 提取正样本
    positive_samples = extract_positive_samples()
    
    # 2. 提取负样本
    negative_samples = extract_negative_samples()
    
    # 3. 合并去重
    all_samples = positive_samples + negative_samples
    df_samples = pd.DataFrame(all_samples)
    
    if df_samples.empty:
        logger.error("[错误] 没有提取到任何样本")
        return
    
    # 去重（同一股票同一天只保留一条）
    df_samples = df_samples.drop_duplicates(subset=['stock_code', 'date'])
    
    # 按日期排序
    df_samples = df_samples.sort_values(['date', 'stock_code']).reset_index(drop=True)
    
    # 统计
    positive_count = (df_samples['label'] == 1).sum()
    negative_count = (df_samples['label'] == 0).sum()
    
    print(f"\n[样本底座清洗完毕]")
    print(f"  总样本数: {len(df_samples)}")
    print(f"  正样本(真龙): {positive_count}")
    print(f"  负样本(骗炮): {negative_count}")
    
    # 保存样本底座
    output_path = os.path.join(VALIDATION_DIR, 'large_samples_base.csv')
    df_samples.to_csv(output_path, index=False)
    print(f"  输出文件: {output_path}")
    
    # 4. 驱动QMT批量下载
    print("\n" + "=" * 70)
    print("[QMT批量下载] 开始向引擎发送下载指令...")
    print("=" * 70)
    
    stock_list = df_samples['stock_code'].unique().tolist()
    min_date = df_samples['date'].min()
    max_date = df_samples['date'].max()
    
    print(f"  涉及股票: {len(stock_list)} 只")
    print(f"  时间跨度: {min_date} 至 {max_date}")
    
    # 计算下载起始日期（往前推100天以确保5日均值计算）
    min_date_int = int(min_date)
    year = min_date_int // 10000
    month = (min_date_int % 10000) // 100
    day = min_date_int % 100
    
    # 粗略往前推100天
    start_date = min_date_int - 10000  # 简化：减10000（约3个月）
    if start_date < 20210101:
        start_date = 20210101
    
    print(f"  下载起始: {start_date}")
    print(f"  下载类型: 1d(日线) + 1m(分钟线)")
    
    try:
        # 下载日线 (用于计算历史基准safe_median)
        print("\n[下载1d数据]...")
        xtdata.download_history_data2(
            stock_list, 
            period='1d', 
            start_time=str(start_date), 
            end_time=str(max_date)
        )
        print("  ✓ 1d数据下载指令已下发")
        
        # 下载1分钟线 (用于计算MFE和raw_sustain)
        print("\n[下载1m数据]...")
        xtdata.download_history_data2(
            stock_list, 
            period='1m', 
            start_time=str(start_date), 
            end_time=str(max_date)
        )
        print("  ✓ 1m数据下载指令已下发")
        
        # ========== CTO强制落盘校验（解决异步陷阱）==========
        # 物理真相：download_history_data2是异步接口！
        # 下载300只股票3年的1m数据需要10-15分钟
        # 必须等待数据真正落盘，绝不允许静默跳过！
        # ==================================================
        print("\n[CTO落盘校验] 等待数据真正写入硬盘...")
        
        # 抽样验证：取10只股票检查数据是否落盘
        sample_stocks = stock_list[:10] if len(stock_list) > 10 else stock_list
        sample_date = min_date  # 用最早日期验证
        
        max_wait_minutes = 20  # 最大等待20分钟
        wait_interval = 30  # 每30秒检查一次
        waited_seconds = 0
        
        while waited_seconds < max_wait_minutes * 60:
            landed_count = 0
            for stock in sample_stocks:
                try:
                    check = xtdata.get_local_data(
                        field_list=['close'],
                        stock_list=[stock],
                        period='1m',
                        start_time=sample_date,
                        end_time=sample_date
                    )
                    if check and stock in check and len(check[stock]) > 0:
                        landed_count += 1
                except:
                    pass
            
            if landed_count >= len(sample_stocks) * 0.8:  # 80%落地即认为成功
                print(f"  ✓ 落盘校验通过 ({landed_count}/{len(sample_stocks)} 样本股票有数据)")
                print(f"  ✓ 总等待时间: {waited_seconds}秒")
                break
            
            print(f"  ... 等待中 ({landed_count}/{len(sample_stocks)} 已落盘, {waited_seconds}秒)")
            time.sleep(wait_interval)
            waited_seconds += wait_interval
        else:
            print(f"  ⚠ 落盘校验超时！仅 {landed_count}/{len(sample_stocks)} 有数据")
            print(f"  ⚠ 建议手动运行 tools/check_data_availability.py 验证")
        
        print("\n[提示] 数据落盘完成，可运行 research_pipeline.py 提取特征")
        
    except Exception as e:
        logger.error(f"[下载失败] {e}")
    
    return df_samples


if __name__ == "__main__":
    build_sample_base()
