#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实分钟K线数据批量下载器 (QMT)

功能：
1. 批量下载指定类别的股票分钟数据
2. 自动管理分类目录
3. 支持增量更新

Author: MyQuantTool Team
Date: 2026-02-09
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
from xtquant import xtdata

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 股票池定义
STOCK_POOLS = {
    'large_cap': [
        '600519.SH', '601398.SH', '601288.SH', '601939.SH', '600036.SH',
        '601857.SH', '600900.SH', '601088.SH', '000858.SZ', '000333.SZ',
        '300750.SZ', '300760.SZ', '603259.SH', '600276.SH', '600309.SH',
        '601888.SH', '600887.SH', '600028.SH', '600048.SH', '601668.SH',
        '002594.SZ', '002714.SZ', '300059.SZ', '002475.SZ', '601166.SH'
    ],
    'mid_cap': [
        '002027.SZ', '002230.SZ', '002415.SZ', '002007.SZ', '000001.SZ',
        '600000.SH', '600016.SH', '601988.SH', '601328.SH', '600015.SH',
        '000725.SZ', '600010.SH', '600018.SH', '600019.SH', '600050.SH',
        '601601.SH', '601628.SH', '601318.SH', '601336.SH', '601688.SH',
        '000651.SZ', '000002.SZ', '000063.SZ', '000069.SZ', '000166.SZ'
    ],
    'small_cap': [
        '300997.SZ', '300001.SZ', '300002.SZ', '300003.SZ', '300004.SZ',
        '300005.SZ', '300006.SZ', '300007.SZ', '300008.SZ', '300009.SZ',
        '300010.SZ', '300011.SZ', '300012.SZ', '300013.SZ', '300014.SZ',
        '002001.SZ', '002002.SZ', '002003.SZ', '002004.SZ', '002005.SZ',
        '002006.SZ', '002008.SZ', '002009.SZ', '002010.SZ', '002011.SZ'
    ],
    'hot_stocks': [
        '300997.SZ', '603697.SH', '600519.SH', '300750.SZ', '002594.SZ',
        '002475.SZ', '601888.SH', '000858.SZ', '603259.SH', '300059.SZ',
        '600276.SH', '600036.SH', '000333.SZ', '600887.SH', '601012.SH',
        '603288.SH', '002352.SZ', '600570.SH', '600436.SH', '002304.SZ',
        '002271.SZ', '600809.SH', '002460.SZ', '002466.SZ', '002493.SZ'
    ]
}

def download_category(
    category: str, 
    codes: List[str], 
    days: int = 10,
    output_base_dir: str = 'data/minute_data_real'
):
    """下载特定分类的股票数据"""
    
    # 准备目录
    category_dir = Path(output_base_dir) / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 开始处理分类: {category} ({len(codes)} 只)")
    
    # 计算时间范围
    # 注意：download_history_data 需要时间范围字符串 'YYYYMMDD'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_time_str = start_date.strftime('%Y%m%d') + "000000"
    end_time_str = end_date.strftime('%Y%m%d') + "235959"
    
    success_count = 0
    
    for idx, code in enumerate(codes):
        print(f"   [{idx+1}/{len(codes)}] 下载 {code}...", end=" ")
        
        try:
            # 1. 触发下载 (修正：使用start_time/end_time替代count)
            xtdata.download_history_data(
                stock_code=code,
                period='1m',
                start_time=start_time_str,
                end_time=end_time_str,
                incrementally=True
            )
            
            # 2. 读取数据 (get_market_data_ex 支持 count，获取最近的N根)
            # 每天240根，days天大约 days * 240
            count_bars = days * 240
            
            data = xtdata.get_market_data_ex(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[code],
                period='1m',
                count=count_bars,
                fill_data=False
            )
            
            if code in data and len(data[code]) > 0:
                df = data[code]
                
                # 转换时间
                if 'time' in df.columns:
                    df['time_str'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                else:
                    df['time_str'] = df.index
                    df['time_str'] = pd.to_datetime(df['time_str'], unit='ms') + pd.Timedelta(hours=8)

                # 保存
                file_path = category_dir / f"{code}_1m.csv"
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                print(f"✅ 成功 ({len(df)} bars)")
                success_count += 1
            else:
                print("⚠️  无数据")
                
        except Exception as e:
            print(f"❌ 失败: {e}")
            
    print(f"🏁 分类 {category} 完成: {success_count}/{len(codes)} 成功")

def main():
    print("=" * 60)
    print("🚀 真实分钟数据批量下载器 (QMT)")
    print("=" * 60)
    
    # 检查 QMT 连接
    try:
        xtdata.get_market_data(field_list=['close'], stock_list=['600000.SH'], period='1d', count=1)
        print("✅ QMT 连接正常")
    except Exception as e:
        print(f"❌ QMT 连接失败: {e}")
        print("请确保 QMT 客户端已启动并登录")
        return

    # 默认下载最近 20 天数据 (约一个月)
    DAYS_TO_DOWNLOAD = 20
    
    total_start = time.time()
    
    for category, codes in STOCK_POOLS.items():
        download_category(category, codes, days=DAYS_TO_DOWNLOAD)
        
    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"🎉 所有任务完成! 耗时: {total_time:.1f}s")
    print(f"💾 数据目录: data/minute_data_real/")
    print("=" * 60)

if __name__ == "__main__":
    main()
