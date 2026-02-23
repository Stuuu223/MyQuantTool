#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用VIP服务下载Tick数据（正确方法）
参考：tasks/data_prefetch.py 的成功实现
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path('E:/MyQuantTool')
sys.path.insert(0, str(PROJECT_ROOT))

# VIP Token
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'

import pandas as pd
from datetime import datetime
from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
import time


def start_vip_service():
    """启动VIP行情服务"""
    print("="*80)
    print("【启动QMT VIP行情服务】")
    print("="*80)
    
    # 1. 设置数据目录为QMT客户端目录（不得下载到项目内）
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    print(f"📂 QMT数据目录: {data_dir}")
    
    # 2. 设置VIP Token
    xtdc.set_token(VIP_TOKEN)
    print(f"🔑 VIP Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")
    
    # 3. 初始化并监听端口
    xtdc.init()
    listen_port = xtdc.listen(port=(58620, 58630))
    print(f"🚀 VIP行情服务已启动，监听端口: {listen_port}")
    print("="*80)
    
    return listen_port


def download_tick_with_vip(stock_list, trade_date, listen_port):
    """使用VIP服务下载Tick数据"""
    print(f"\n{'='*80}")
    print(f"【VIP Tick数据下载】")
    print(f"{'='*80}")
    print(f"日期: {trade_date}")
    print(f"股票数: {len(stock_list)}只")
    print(f"{'='*80}")
    
    # 连接到VIP行情服务
    _, port = listen_port
    xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)
    print("✅ 已连接到VIP行情服务\n")
    
    success_count = 0
    failed_list = []
    
    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"[{i}/{len(stock_list)}] {stock_code}", end=" ")
            
            # 检查是否已有数据
            existing = xtdata.get_local_data(
                field_list=['time'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if existing and stock_code in existing and len(existing[stock_code]) > 100:
                print(f"✅ 已存在 ({len(existing[stock_code])}条)")
                success_count += 1
                continue
            
            # 使用VIP服务下载
            xtdata.download_history_data(
                stock_code=stock_code,
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            # 验证下载
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if data and stock_code in data and len(data[stock_code]) > 100:
                tick_count = len(data[stock_code])
                print(f"✅ 成功 ({tick_count}条)")
                success_count += 1
            else:
                print(f"⚠️ 数据不足")
                failed_list.append(stock_code)
                
        except Exception as e:
            print(f"❌ 失败: {e}")
            failed_list.append(stock_code)
        
        time.sleep(0.2)
    
    return success_count, failed_list


def main():
    """主函数"""
    # 加载候选名单
    candidates_file = PROJECT_ROOT / 'data' / 'scan_results' / '20251231_candidates_73.csv'
    if not candidates_file.exists():
        print(f"❌ 候选名单不存在: {candidates_file}")
        return
    
    df = pd.read_csv(candidates_file)
    # 只下载缺失Tick数据的股票（排除已有数据的11只）
    stock_list = df['ts_code'].tolist()[11:]  # 从第12只开始
    
    print(f"📋 需要下载Tick数据: {len(stock_list)}只")
    
    # 启动VIP服务
    listen_port = start_vip_service()
    
    # 下载Tick数据
    success_count, failed_list = download_tick_with_vip(
        stock_list, '20251231', listen_port
    )
    
    # 输出汇总
    print(f"\n{'='*80}")
    print("【VIP下载结果】")
    print(f"{'='*80}")
    print(f"总计: {len(stock_list)}只")
    print(f"成功: {success_count}只")
    print(f"失败: {len(failed_list)}只")
    
    if failed_list:
        print(f"\n失败列表 ({len(failed_list)}只):")
        for code in failed_list[:10]:
            print(f"   - {code}")
        if len(failed_list) > 10:
            print(f"   ... 及其他 {len(failed_list)-10} 只")
    
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
