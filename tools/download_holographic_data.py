# -*- coding: utf-8 -*-
"""
全息时间机器数据下载器
批量下载12.24-01.05区间所有粗筛股票的Tick数据

Author: 项目总监
Date: 2026-02-23
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'download_holographic.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_universe_for_dates(dates: List[str]) -> List[str]:
    """
    获取多个日期的粗筛股票池并合并去重

    CTO规范: 第一层粗筛已改用QMT的snapshot进行实时快照过滤
    但为了数据下载器的兼容性，保持使用Tushare daily_basic作为主要粗筛方法
    因为下载器需要在非交易时间也能获取历史股票池，QMT历史数据可能不可用

    Args:
        dates: 日期列表 ['YYYYMMDD', ...]

    Returns:
        去重后的股票代码列表
    """
    from logic.data_providers.universe_builder import UniverseBuilder
    import random

    builder = UniverseBuilder()
    all_stocks = set()

    for date in dates:
        try:
            logger.info(f"【粗筛-兼容模式】{date} 开始...")
            
            # 使用Tushare作为主要方法，因为它可以在非交易时间获取历史数据
            stocks = builder.get_daily_universe(date)
            
            # 如果Tushare方法失败或返回空列表，作为备选从QMT获取全市场股票的子集
            if not stocks:
                logger.warning(f"【粗筛-兼容模式】{date} Tushare方法返回空列表，使用QMT备选方案")
                from xtquant import xtdata
                
                all_stocks_list = xtdata.get_stock_list_in_sector('沪深A股')
                if all_stocks_list:
                    # 随机选择一部分股票作为备选，确保有数据可下载
                    sample_size = min(100, len(all_stocks_list))
                    stocks = random.sample(all_stocks_list, sample_size)
                    logger.info(f"【粗筛-兼容模式】{date} QMT备选方案获取到 {len(stocks)} 只股票")
                else:
                    logger.error(f"【粗筛-兼容模式】{date} QMT也无法获取股票列表")
                    continue
            
            all_stocks.update(stocks)
            logger.info(f"【粗筛-兼容模式】{date} 获取到 {len(stocks)} 只，累计 {len(all_stocks)} 只")
            
        except Exception as e:
            logger.error(f"【粗筛-兼容模式】{date} 失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    return list(all_stocks)


def download_tick_batch(stock_list: List[str], dates: List[str]) -> Dict:
    """
    批量下载Tick数据
    
    Args:
        stock_list: 股票代码列表
        dates: 日期列表
    
    Returns:
        下载结果统计
    """
    try:
        from xtquant import xtdata
    except ImportError:
        logger.error("xtquant未安装")
        return {'error': 'xtquant未安装'}
    
    results = {
        'total': len(stock_list) * len(dates),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    # 启动VIP服务
    try:
        from xtquant import xtdatacenter as xtdc
        from logic.core.path_resolver import PathResolver
        
        vip_token = os.getenv('QMT_VIP_TOKEN', '')
        # 从环境变量获取QMT路径
        data_dir = os.getenv('QMT_PATH', '')
        
        if not data_dir:
            # 如果环境变量未设置，使用PathResolver获取路径
            data_dir = str(PathResolver.get_qmt_data_dir())
        
        if vip_token:
            xtdc.set_data_home_dir(data_dir)
            xtdc.set_token(vip_token)
            xtdc.init()
            port = xtdc.listen(port=(58620, 58630))
            logger.info(f"【VIP服务】已启动，端口: {port}")
    except Exception as e:
        logger.warning(f"【VIP服务】启动失败: {e}，使用普通模式")
    
    logger.info(f"【下载任务】股票: {len(stock_list)} 只，日期: {len(dates)} 天，总计: {results['total']} 个任务")
    
    start_date = dates[0]
    end_date = dates[-1]
    
    for i, stock in enumerate(stock_list, 1):
        try:
            # 标准化代码
            if '.' not in stock:
                if stock.startswith('6'):
                    stock = f"{stock}.SH"
                else:
                    stock = f"{stock}.SZ"
            
            # 检查是否已有数据
            try:
                existing = xtdata.get_local_data(
                    field_list=['time'],
                    stock_list=[stock],
                    period='tick',
                    start_time=start_date,
                    end_time=end_date
                )
                
                if existing and stock in existing and len(existing[stock]) > 1000:
                    results['skipped'] += len(dates)
                    logger.debug(f"[{i}/{len(stock_list)}] {stock} 已有数据，跳过")
                    continue
            except:
                pass
            
            # 下载
            xtdata.download_history_data(
                stock_code=stock,
                period='tick',
                start_time=start_date,
                end_time=end_date
            )
            
            # 验证
            data = xtdata.get_local_data(
                field_list=['time'],
                stock_list=[stock],
                period='tick',
                start_time=start_date,
                end_time=end_date
            )
            
            if data and stock in data and len(data[stock]) > 100:
                results['success'] += len(dates)
                logger.info(f"[{i}/{len(stock_list)}] {stock} ✅ ({len(data[stock])} ticks)")
            else:
                results['failed'] += len(dates)
                logger.warning(f"[{i}/{len(stock_list)}] {stock} ❌ 数据不足")
                
        except Exception as e:
            results['failed'] += len(dates)
            error_msg = f"{stock}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"[{i}/{len(stock_list)}] {stock} ❌ {e}")
        
        # 间隔避免限流
        time.sleep(0.1)
    
    return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='全息时间机器数据下载器')
    parser.add_argument('--start-date', type=str, default='20251220', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, default='20260110', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--output', type=str, default='data/holographic_universe.json', help='输出文件路径')
    parser.add_argument('--workers', type=int, default=4, help='并发数')
    parser.add_argument('--type', type=str, choices=['tick', 'kline', 'all'], default='tick', help='数据类型')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("【全息时间机器数据下载器】")
    print("=" * 60)
    
    # 解析日期区间
    start_date = datetime.strptime(args.start_date, '%Y%m%d')
    end_date = datetime.strptime(args.end_date, '%Y%m%d')
    
    # 生成日期列表（只保留工作日）
    dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 工作日
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    logger.info(f"【日期区间】{dates[0]} ~ {dates[-1]} ({len(dates)} 天)")
    print(f"📅 日期区间: {dates[0]} ~ {dates[-1]} ({len(dates)} 天)")
    
    # Step 1: 获取粗筛股票池
    print("\n📊 Step 1: 获取粗筛股票池...")
    stock_list = get_universe_for_dates(dates[:5])  # 取前5个日期的粗筛结果
    
    if not stock_list:
        logger.error("【粗筛】未能获取任何股票")
        print("❌ 粗筛失败，无法获取股票池")
        return
    
    print(f"✅ 粗筛完成: {len(stock_list)} 只股票")
    logger.info(f"【粗筛完成】共 {len(stock_list)} 只股票")
    
    # 保存股票池
    import json
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'dates': dates,
            'stocks': stock_list,
            'count': len(stock_list),
            'created_at': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 股票池已保存: {output_path}")
    
    # Step 2: 下载Tick数据
    print(f"\n📥 Step 2: 下载Tick数据 ({len(stock_list)} 只 × {len(dates)} 天)...")
    results = download_tick_batch(stock_list, dates)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("【下载完成】")
    print(f"  总任务: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  跳过: {results['skipped']}")
    
    if results['errors']:
        print(f"\n错误列表 (前10条):")
        for err in results['errors'][:10]:
            print(f"  - {err}")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
