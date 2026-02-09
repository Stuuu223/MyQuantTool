#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实分钟K线数据批量下载器 (QMT)

功能：
1. 批量下载指定类别的股票分钟数据
2. 支持 Tushare Pro 动态筛选活跃股（替代 AkShare）
3. 自动管理分类目录
4. 支持增量更新

Author: MyQuantTool Team
Date: 2026-02-09
Update: 2026-02-09 - 升级到 Tushare Pro，避免 AkShare IP 封禁
"""

import sys
import time
import argparse
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
from xtquant import xtdata

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入速率限制器
try:
    from logic.rate_limiter import RateLimiter
    RATE_LIMITER = RateLimiter(
        max_requests_per_minute=10,
        max_requests_per_hour=100,
        min_request_interval=5,
        enable_logging=True
    )
except ImportError:
    RATE_LIMITER = None

# Tushare Pro 配置
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')  # 从环境变量读取
if not TUSHARE_TOKEN:
    # 如果环境变量未设置，尝试从配置文件读取
    config_file = project_root / 'config' / 'tushare_token.txt'
    if config_file.exists():
        TUSHARE_TOKEN = config_file.read_text().strip()

# 预定义静态股票池 (作为备选)
STATIC_POOLS = {
    'static_pool_500': [
        # 大盘蓝筹（上证50成分股，共50只）
        '600000.SH', '600009.SH', '600010.SH', '600015.SH', '600016.SH',
        '600018.SH', '600019.SH', '600025.SH', '600028.SH', '600029.SH',
        '600030.SH', '600031.SH', '600036.SH', '600048.SH', '600050.SH',
        '600104.SH', '600276.SH', '600519.SH', '600547.SH', '600585.SH',
        '600690.SH', '600703.SH', '600887.SH', '600900.SH', '600905.SH',
        '600909.SH', '600926.SH', '600958.SH', '600999.SH', '601012.SH',
        '601066.SH', '601088.SH', '601111.SH', '601138.SH', '601166.SH',
        '601169.SH', '601211.SH', '601225.SH', '601229.SH', '601288.SH',
        '601318.SH', '601328.SH', '601336.SH', '601360.SH', '601398.SH',
        '601601.SH', '601628.SH', '601668.SH', '601688.SH', '601766.SH',
        # 中盘成长（150只）
        '000001.SZ', '000002.SZ', '000063.SZ', '000069.SZ', '000100.SZ',
        '000157.SZ', '000166.SZ', '000338.SZ', '000333.SZ', '000400.SZ',
        '000401.SZ', '000402.SZ', '000415.SZ', '000423.SZ', '000488.SZ',
        '000525.SZ', '000568.SZ', '000581.SZ', '000596.SZ', '000625.SZ',
        '000627.SZ', '000629.SZ', '000630.SZ', '000651.SZ', '000652.SZ',
        '000661.SZ', '000665.SZ', '000671.SZ', '000708.SZ', '000717.SZ',
        '000718.SZ', '000725.SZ', '000728.SZ', '000729.SZ', '000732.SZ',
        '000768.SZ', '000783.SZ', '000786.SZ', '000792.SZ', '000799.SZ',
        '000800.SZ', '000807.SZ', '000816.SZ', '000826.SZ', '000839.SZ',
        '000848.SZ', '000858.SZ', '000860.SZ', '000876.SZ', '000883.SZ',
        '000895.SZ', '000898.SZ', '000900.SZ', '000901.SZ', '000902.SZ',
        '000915.SZ', '000930.SZ', '000933.SZ', '000937.SZ', '000938.SZ',
        '000960.SZ', '000961.SZ', '000967.SZ', '000970.SZ', '000977.SZ',
        '000983.SZ', '000988.SZ', '000989.SZ', '001979.SZ', '002001.SZ',
        '002004.SZ', '002007.SZ', '002008.SZ', '002015.SZ', '002016.SZ',
        '002019.SZ', '002024.SZ', '002025.SZ', '002027.SZ', '002028.SZ',
        '002035.SZ', '002038.SZ', '002040.SZ', '002044.SZ', '002047.SZ',
        '002050.SZ', '002051.SZ', '002053.SZ', '002054.SZ', '002055.SZ',
        '002056.SZ', '002059.SZ', '002060.SZ', '002061.SZ', '002063.SZ',
        '002064.SZ', '002065.SZ', '002069.SZ', '002070.SZ', '002071.SZ',
        '002072.SZ', '002073.SZ', '002074.SZ', '002075.SZ', '002076.SZ',
        '002078.SZ', '002080.SZ', '002082.SZ', '002083.SZ', '002084.SZ',
        '002085.SZ', '002087.SZ', '002088.SZ', '002089.SZ', '002090.SZ',
        '002091.SZ', '002092.SZ', '002094.SZ', '002095.SZ', '002096.SZ',
        '002097.SZ', '002099.SZ', '002100.SZ', '002101.SZ', '002103.SZ',
        '002104.SZ', '002105.SZ', '002106.SZ', '002107.SZ', '002108.SZ',
        '002109.SZ', '002110.SZ', '002111.SZ', '002112.SZ', '002113.SZ',
        '002114.SZ', '002115.SZ', '002116.SZ', '002117.SZ', '002118.SZ',
        '002119.SZ', '002120.SZ', '002121.SZ', '002122.SZ', '002123.SZ',
        '002124.SZ', '002125.SZ', '002126.SZ', '002127.SZ', '002128.SZ',
        '002129.SZ', '002130.SZ', '002131.SZ', '002132.SZ', '002133.SZ',
        '002134.SZ', '002135.SZ', '002136.SZ', '002137.SZ', '002138.SZ',
        '002139.SZ', '002140.SZ', '002141.SZ', '002142.SZ', '002143.SZ',
        '002144.SZ', '002145.SZ', '002146.SZ', '002147.SZ', '002148.SZ',
        '002149.SZ', '002150.SZ', '002151.SZ', '002152.SZ', '002153.SZ',
        '002154.SZ', '002155.SZ', '002156.SZ', '002157.SZ', '002158.SZ',
        '002159.SZ', '002160.SZ', '002161.SZ', '002162.SZ', '002163.SZ',
        '002164.SZ', '002165.SZ', '002166.SZ', '002167.SZ', '002168.SZ',
        '002169.SZ', '002170.SZ', '002171.SZ', '002172.SZ', '002173.SZ',
        '002174.SZ', '002175.SZ', '002176.SZ', '002177.SZ', '002178.SZ',
        '002179.SZ', '002180.SZ', '002181.SZ', '002182.SZ', '002183.SZ',
        '002184.SZ', '002185.SZ', '002186.SZ', '002187.SZ', '002188.SZ',
        '002189.SZ', '002190.SZ', '002191.SZ', '002192.SZ', '002193.SZ',
        '002194.SZ', '002195.SZ', '002196.SZ', '002197.SZ', '002198.SZ',
        '002199.SZ', '002200.SZ', '002201.SZ', '002202.SZ', '002203.SZ',
        '002204.SZ', '002205.SZ', '002206.SZ', '002207.SZ', '002208.SZ',
        '002209.SZ', '002210.SZ', '002211.SZ', '002212.SZ', '002213.SZ',
        '002214.SZ', '002215.SZ', '002216.SZ', '002217.SZ', '002218.SZ',
        '002219.SZ', '002220.SZ', '002221.SZ', '002222.SZ', '002223.SZ',
        '002224.SZ', '002225.SZ', '002226.SZ', '002227.SZ', '002228.SZ',
        '002229.SZ', '002230.SZ', '002231.SZ', '002232.SZ', '002233.SZ',
        # 创业板（100只）
        '300001.SZ', '300002.SZ', '300003.SZ', '300004.SZ', '300005.SZ',
        '300006.SZ', '300007.SZ', '300008.SZ', '300009.SZ', '300010.SZ',
        '300011.SZ', '300012.SZ', '300013.SZ', '300014.SZ', '300015.SZ',
        '300016.SZ', '300017.SZ', '300018.SZ', '300019.SZ', '300020.SZ',
        '300021.SZ', '300022.SZ', '300023.SZ', '300024.SZ', '300025.SZ',
        '300026.SZ', '300027.SZ', '300028.SZ', '300029.SZ', '300030.SZ',
        '300031.SZ', '300032.SZ', '300033.SZ', '300034.SZ', '300035.SZ',
        '300036.SZ', '300037.SZ', '300038.SZ', '300039.SZ', '300040.SZ',
        '300041.SZ', '300042.SZ', '300043.SZ', '300044.SZ', '300045.SZ',
        '300046.SZ', '300047.SZ', '300048.SZ', '300049.SZ', '300050.SZ',
        '300051.SZ', '300052.SZ', '300053.SZ', '300054.SZ', '300055.SZ',
        '300056.SZ', '300057.SZ', '300058.SZ', '300059.SZ', '300060.SZ',
        '300061.SZ', '300062.SZ', '300063.SZ', '300064.SZ', '300065.SZ',
        '300066.SZ', '300067.SZ', '300068.SZ', '300069.SZ', '300070.SZ',
        '300071.SZ', '300072.SZ', '300073.SZ', '300074.SZ', '300075.SZ',
        '300076.SZ', '300077.SZ', '300078.SZ', '300079.SZ', '300080.SZ',
        '300081.SZ', '300082.SZ', '300083.SZ', '300084.SZ', '300085.SZ',
        '300086.SZ', '300087.SZ', '300088.SZ', '300089.SZ', '300090.SZ',
        '300091.SZ', '300092.SZ', '300093.SZ', '300094.SZ', '300095.SZ',
        '300096.SZ', '300097.SZ', '300098.SZ', '300099.SZ', '300100.SZ',
        # 热门股（100只）
        '300750.SZ', '300760.SZ', '603259.SH', '600309.SH', '601888.SH',
        '600887.SH', '600028.SH', '600048.SH', '601668.SH', '002594.SZ',
        '002714.SZ', '300059.SZ', '002475.SZ', '601166.SH', '603697.SH',
        '002415.SZ', '000725.SZ', '600010.SH', '600018.SH', '600019.SH',
        '600050.SH', '601601.SH', '601628.SH', '601318.SH', '601336.SH',
        '601688.SH', '002230.SZ', '002027.SZ', '600000.SH', '600016.SH',
        '601988.SH', '601328.SH', '600015.SH', '002352.SZ', '600570.SH',
        '600436.SH', '002304.SZ', '002271.SZ', '600809.SH', '002460.SZ',
        '002466.SZ', '002493.SZ', '601012.SH', '603288.SH', '000333.SZ',
        '300997.SZ', '301150.SZ', '301000.SZ', '301002.SZ', '301003.SZ',
        '301004.SZ', '301005.SZ', '301006.SZ', '301007.SZ', '301008.SZ',
        '301009.SZ', '301010.SZ', '301011.SZ', '301012.SZ', '301013.SZ',
        '301014.SZ', '301015.SZ', '301016.SZ', '301017.SZ', '301018.SZ',
        '301019.SZ', '301020.SZ', '301021.SZ', '301022.SZ', '301023.SZ',
        '002271.SZ', '002230.SZ', '002415.SZ', '002007.SZ', '000001.SZ',
        '601398.SH', '601288.SH', '601939.SH', '600036.SH', '601857.SH',
        '600900.SH', '601088.SH', '000858.SZ', '600276.SH', '600887.SH',
        '601318.SH', '601336.SH', '601688.SH', '002594.SZ', '601668.SH',
        '603259.SH', '601888.SH', '000333.SZ', '600887.SH', '601012.SH',
        '603288.SH', '002352.SZ', '600570.SH', '600436.SH', '002304.SZ',
        '600519.SH', '300750.SZ', '002594.SZ', '002475.SZ', '601888.SH'
    ]
}


def get_active_stock_pool_tushare(top_n: int = 500) -> List[str]:
    """
    使用 Tushare Pro 获取全市场活跃股名单
    筛选标准：
    1. 剔除 ST/ST*
    2. 剔除北交所 (8/4开头)
    3. 按成交额倒序排列，取前 top_n
    
    需要 Tushare Pro 权限：daily_basic 接口
    """
    print(f"\n🔍 正在通过 Tushare Pro 筛选全市场活跃股 (Top {top_n})...")
    
    if not TUSHARE_TOKEN:
        print("❌ Tushare Token 未配置！")
        print("   请设置环境变量: export TUSHARE_TOKEN='your_token'")
        print("   或创建文件: config/tushare_token.txt")
        return []
    
    # 应用速率限制
    if RATE_LIMITER:
        RATE_LIMITER.wait_if_needed()
        print("⏳ 速率限制器已就绪")
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 获取最近交易日
        today = datetime.now()
        trade_date = today.strftime('%Y%m%d')
        
        # 如果今天非交易日，往前推
        for i in range(5):
            try:
                # 获取基础行情数据（包含成交额）
                df = pro.daily_basic(
                    trade_date=trade_date,
                    fields='ts_code,turnover_rate,volume_ratio,pe,total_mv'
                )
                if len(df) > 0:
                    break
                trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
            except:
                trade_date = (today - timedelta(days=i+1)).strftime('%Y%m%d')
        
        # 获取日线行情（获取成交额）
        df_daily = pro.daily(
            trade_date=trade_date,
            fields='ts_code,amount'
        )
        
        if RATE_LIMITER:
            RATE_LIMITER.record_request()
        
        # 合并数据
        df = df.merge(df_daily, on='ts_code', how='left')
        
        # 1. 剔除缺失数据
        df = df.dropna(subset=['amount'])
        
        # 2. 获取股票名称（用于剔除ST）
        df_name = pro.stock_basic(fields='ts_code,name')
        df = df.merge(df_name, on='ts_code', how='left')
        
        # 3. 剔除 ST
        df = df[~df['name'].str.contains('ST', na=False)]
        
        # 4. 剔除北交所
        df = df[~df['ts_code'].str.match(r'^(8|4|9)')]
        
        # 5. 按成交额排序
        df.sort_values('amount', ascending=False, inplace=True)
        
        # 6. 取前 N 名
        top_df = df.head(top_n)
        
        # 7. 转换为 QMT 格式 (000001.SZ, 600000.SH)
        qmt_codes = []
        for code in top_df['ts_code'].tolist():
            # Tushare 格式: 000001.SZ, 600000.SH (已是QMT格式)
            qmt_codes.append(code)
        
        print(f"✅ 筛选完成！获取 {len(qmt_codes)} 只股票")
        print(f"   最小成交额: {top_df.iloc[-1]['amount']:.2f} 万元")
        print(f"   示例: {qmt_codes[:5]}")
        return qmt_codes
        
    except Exception as e:
        print(f"❌ Tushare Pro 获取失败: {e}")
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
            pass  # 忽略单个失败
            
    print(f"\n🏁 分类 {category} 完成: {success_count}/{len(codes)} 成功")


def main():
    parser = argparse.ArgumentParser(description='QMT 分钟数据批量下载器')
    parser.add_argument('--mode', type=str, default='tushare', 
                        choices=['tushare', 'static'], 
                        help='下载模式: tushare(Tushare Pro) | static(静态池)')
    parser.add_argument('--top', type=int, default=500, help='活跃股数量 (默认500)')
    parser.add_argument('--days', type=int, default=30, help='下载天数')
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 真实分钟数据批量下载器 (QMT + Tushare Pro)")
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
    
    if args.mode == 'tushare':
        tushare_codes = get_active_stock_pool_tushare(top_n=args.top)
        if tushare_codes:
            target_pool['tushare_top_' + str(args.top)] = tushare_codes
        else:
            print("⚠️  Tushare 获取失败，自动回退到静态股票池")
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