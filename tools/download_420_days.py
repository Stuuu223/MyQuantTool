# -*- coding: utf-8 -*-
"""
下载今天往前420个交易日的Tick数据
全息回演数据准备
"""
import sys
from pathlib import Path

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta
from xtquant import xtdata

def get_last_n_trading_days(n=420):
    """获取最近N个交易日（跳过周末）"""
    dates = []
    current = datetime.now()
    
    while len(dates) < n:
        current -= timedelta(days=1)
        # 跳过周末 (0=周一, 6=周日)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y%m%d"))
    
    return list(reversed(dates))  # 从早到晚

def main():
    print("=" * 80)
    print("【全息回演数据下载器】420个交易日Tick数据")
    print("=" * 80)
    
    # 连接QMT
    xtdata.connect()
    print("\n✅ QMT连接成功")
    
    # 获取日期范围
    trading_days = get_last_n_trading_days(420)
    start_date = trading_days[0]
    end_date = trading_days[-1]
    
    print(f"\n📅 下载日期范围: {start_date} ~ {end_date}")
    print(f"📊 共 {len(trading_days)} 个交易日")
    
    # 获取全市场股票
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"📈 股票数量: {len(all_stocks)} 只")
    print(f"💾 预计总数据量: {len(all_stocks) * len(trading_days)} 股票-日")
    
    print("\n" + "=" * 80)
    print("开始下载...")
    print("=" * 80)
    
    # 下载tick数据
    total_tasks = len(all_stocks) * len(trading_days)
    completed = 0
    failed = []
    
    for date in trading_days:
        print(f"\n📅 下载日期: {date}")
        
        for i, stock in enumerate(all_stocks):
            try:
                # 先检查是否已有数据
                existing = xtdata.get_local_data(
                    field_list=["time"],
                    stock_list=[stock],
                    period="tick",
                    start_time=date,
                    end_time=date
                )
                
                if existing and stock in existing and len(existing[stock]) > 100:
                    print(f"  [{i+1}/{len(all_stocks)}] {stock} ✅ 已存在")
                    completed += 1
                    continue
                
                # 下载数据
                xtdata.download_history_data(
                    stock_code=stock,
                    period="tick",
                    start_time=date,
                    end_time=date
                )
                
                print(f"  [{i+1}/{len(all_stocks)}] {stock} ⬇️  下载完成")
                completed += 1
                
            except Exception as e:
                print(f"  [{i+1}/{len(all_stocks)}] {stock} ❌ 失败: {e}")
                failed.append((stock, date))
            
            # 每100只显示进度
            if (i + 1) % 100 == 0:
                print(f"\n📊 进度: {completed}/{total_tasks} ({completed/total_tasks*100:.2f}%)")
    
    print("\n" + "=" * 80)
    print("下载完成!")
    print(f"✅ 成功: {completed}")
    print(f"❌ 失败: {len(failed)}")
    
    if failed:
        print(f"\n失败列表 (前10条):")
        for stock, date in failed[:10]:
            print(f"  - {stock} @ {date}")

if __name__ == "__main__":
    main()
