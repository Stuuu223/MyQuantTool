#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实分钟K线数据批量下载器 (QMT)

功能：
1. 批量下载指定类别的股票分钟数据
2. 支持 AkShare 动态筛选活跃股（剔除冷门股）
3. 自动管理分类目录
4. 支持增量更新

Author: MyQuantTool Team
Date: 2026-02-09
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
from xtquant import xtdata
import akshare as ak

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入速率限制器
try:
    from logic.rate_limiter import RateLimiter
    RATE_LIMITER = RateLimiter(
        max_requests_per_minute=10,  # 每分钟最多10次请求（更保守）
        max_requests_per_hour=100,   # 每小时最多100次请求
        min_request_interval=5,       # 最小请求间隔5秒
        enable_logging=True
    )
except ImportError:
    RATE_LIMITER = None

# 预定义静态股票池 (作为备选)
STATIC_POOLS = {
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


def get_active_stock_pool(top_n: int = 500) -> List[str]:
    """
    使用 AkShare 获取全市场活跃股名单
    筛选标准：
    1. 剔除 ST/ST*
    2. 剔除北交所 (8/4开头)
    3. 按成交额倒序排列，取前 top_n
    """
    print(f"\n🔍 正在通过 AkShare 筛选全市场活跃股 (Top {top_n})...")

    # 应用速率限制
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
        print("⏳ 速率限制器已就绪，避免被封IP")

    try:
        # 获取实时行情
        df = ak.stock_zh_a_spot_em()

        # 记录请求
        if RATE_LIMITER:
            RATE_LIMITER.record_request()

        # 1. 剔除 ST
        df = df[~df['名称'].str.contains('ST')]

        # 2. 剔除北交所 (代码 8xxxx, 4xxxx, 9xxxx)
        df = df[~df['代码'].str.match(r'^(8|4|9)')]

        # 3. 按成交额排序 (倒序)
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        df.sort_values('成交额', ascending=False, inplace=True)

        # 4. 取前 N 名
        top_df = df.head(top_n)

        # 转换为 QMT 代码格式 (600xxx -> 600xxx.SH, 00xxxx -> 00xxxx.SZ)
        qmt_codes = []
        for _, row in top_df.iterrows():
            code = str(row['代码'])
            if code.startswith('6'):
                qmt_codes.append(f"{code}.SH")
            else:
                qmt_codes.append(f"{code}.SZ")

        print(f"✅ 筛选完成！最小成交额: {top_df.iloc[-1]['成交额']/1e8:.2f} 亿")
        print(f"   示例: {qmt_codes[:5]}")
        return qmt_codes

    except Exception as e:
        print(f"❌ AkShare 获取失败: {e}")
        print("⚠️  将回退到静态股票池")
        return []


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
        # 进度条显示
        sys.stdout.write(f"\r   🚀 [{idx+1}/{len(codes)}] 下载 {code}...")
        sys.stdout.flush()

        try:
            # 1. 触发下载
            xtdata.download_history_data(
                stock_code=code,
                period='1m',
                start_time=start_time_str,
                end_time=end_time_str,
                incrementally=True
            )

            # 2. 读取数据
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
                success_count += 1

        except Exception as e:
            pass  # 忽略单个失败，保持批量进行

    print(f"\n🏁 分类 {category} 完成: {success_count}/{len(codes)} 成功")


def main():
    parser = argparse.ArgumentParser(description='QMT 分钟数据批量下载器')
    parser.add_argument('--mode', type=str, default='active', choices=['active', 'static'], help='下载模式: active(活跃股) | static(静态池)')
    parser.add_argument('--top', type=int, default=100, help='活跃股数量 (默认100)')
    parser.add_argument('--days', type=int, default=20, help='下载天数')
    args = parser.parse_args()

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

    target_pool = {}

    if args.mode == 'active':
        active_codes = get_active_stock_pool(top_n=args.top)
        if active_codes:
            target_pool['active_top_' + str(args.top)] = active_codes
        else:
            print("⚠️  AkShare 获取失败，自动回退到静态股票池")
            target_pool = STATIC_POOLS
    else:
        target_pool = STATIC_POOLS

    total_start = time.time()

    for category, codes in target_pool.items():
        download_category(category, codes, days=args.days)

    total_time = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"🎉 所有任务完成! 耗时: {total_time:.1f}s")
    print(f"💾 数据目录: data/minute_data_real/")
    print("=" * 60)


if __name__ == "__main__":
    main()