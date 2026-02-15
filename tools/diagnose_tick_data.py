"""
Tick 数据诊断脚本 - 检查时间戳和数据完整性
"""
import pandas as pd
from pathlib import Path
from xtquant import xtdata, xtdatacenter as xtdc
import logging
import sys

PROJECT_ROOT = Path("E:/MyQuantTool")
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'

def init_qmt_once():
    """初始化QMT连接"""
    DATA_DIR = PROJECT_ROOT / 'data' / 'qmt_data'
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(DATA_DIR))
    xtdc.set_token(VIP_TOKEN)
    xtdc.init()
    print("✅ QMT 初始化完成")

def diagnose_single_stock(stock_code, test_date):
    """诊断单只股票的tick数据"""
    print(f"\n{'='*60}")
    print(f"诊断 {stock_code} - {test_date}")
    print('='*60)
    
    # 扩大时间范围（确保覆盖所有数据）
    start_time = test_date.replace('-', '') + '080000'  # 08:00开始
    end_time = test_date.replace('-', '') + '170000'    # 17:00结束
    
    print(f"请求时间范围: {start_time} ~ {end_time}")
    
    # 获取完整字段
    tick_df = xtdata.get_market_data_ex(
        field_list=['time', 'lastPrice', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[stock_code],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )
    
    if stock_code not in tick_df or tick_df[stock_code].empty:
        print(f"❌ 无数据")
        return
    
    df = tick_df[stock_code].copy()
    
    # 转换时间戳（注意：QMT返回的时间戳是北京时间，需要正确处理）
    print(f"\n原始时间戳（前5个）:")
    print(df['time'].head())
    print(f"原始时间戳（后5个）:")
    print(df['time'].tail())
    
    # 方法1：直接转换为UTC时间，然后+8小时
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
    # 或者方法2：转换为datetime后+8小时
    # df['timestamp'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
    
    print(f"\n转换后的时间戳（前5个）:")
    print(df['timestamp'].head())
    print(f"转换后的时间戳（后5个）:")
    print(df['timestamp'].tail())
    
    print(f"\n📊 数据概览:")
    print(f"  总记录数: {len(df):,}")
    print(f"  时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"  lastPrice 非空: {df['lastPrice'].notna().sum()}/{len(df)}")
    
    if df['lastPrice'].notna().sum() > 0:
        valid_df = df[df['lastPrice'].notna()]
        print(f"  价格范围: {valid_df['lastPrice'].min():.2f} ~ {valid_df['lastPrice'].max():.2f}")
    
    # 检查交易时间段（9:00-15:00）
    trading_df = df[(df['timestamp'].dt.hour >= 9) & (df['timestamp'].dt.hour <= 15)]
    print(f"  交易时间段(9-15点): {len(trading_df):,} 条 ({len(trading_df)/len(df)*100:.1f}%)")
    
    # 按小时统计
    print(f"\n📊 按小时分布:")
    hour_dist = df.groupby(df['timestamp'].dt.hour).size()
    for hour, count in hour_dist.items():
        print(f"  {hour:02d}:00: {count:6,} 条 ({count/len(df)*100:5.2f}%)")
    
    # 检查关键时间点（需要转换为时区感知的时间）
    buy_time = pd.to_datetime(f"{test_date} 09:35:00").tz_localize('Asia/Shanghai')
    sell_time = pd.to_datetime(f"{test_date} 14:55:00").tz_localize('Asia/Shanghai')
    
    buy_data = df[df['timestamp'] <= buy_time]
    sell_data = df[df['timestamp'] >= sell_time]
    
    print(f"\n⏰ 关键时间点:")
    print(f"  09:35 之前: {len(buy_data)} 条")
    if not buy_data.empty:
        print(f"    最后一笔时间: {buy_data['timestamp'].max()}")
        print(f"    最后一笔价格: {buy_data['lastPrice'].iloc[-1] if buy_data['lastPrice'].iloc[-1] > 0 else 'N/A'}")
    else:
        print(f"    无数据")
    
    print(f"  14:55 之后: {len(sell_data)} 条")
    if not sell_data.empty:
        print(f"    第一笔时间: {sell_data['timestamp'].min()}")
        print(f"    第一笔价格: {sell_data['lastPrice'].iloc[0] if sell_data['lastPrice'].iloc[0] > 0 else 'N/A'}")
    else:
        print(f"    无数据")
    
    # 检查是否有09:30附近的数据
    open_time = pd.to_datetime(f"{test_date} 09:30:00").tz_localize('Asia/Shanghai')
    close_time = pd.to_datetime(f"{test_date} 15:00:00").tz_localize('Asia/Shanghai')
    
    morning_data = df[(df['timestamp'] >= open_time) & (df['timestamp'] <= open_time.replace(minute=40))]
    afternoon_data = df[(df['timestamp'] >= close_time.replace(minute=50)) & (df['timestamp'] <= close_time.replace(minute=59))]
    
    print(f"\n📅 交易时段:")
    print(f"  09:30-09:40: {len(morning_data)} 条")
    print(f"  14:50-14:59: {len(afternoon_data)} 条")
    
    # 前5条和后5条数据
    print(f"\n📈 前 5 条数据:")
    print(df[['timestamp', 'lastPrice', 'volume', 'amount']].head())
    print(f"\n📉 后 5 条数据:")
    print(df[['timestamp', 'lastPrice', 'volume', 'amount']].tail())

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 Tick 数据诊断工具")
    print("=" * 60)
    
    init_qmt_once()
    
    test_cases = [
        ('600007.SH', '2026-02-13'),
        ('000001.SZ', '2026-02-13'),
        ('300182.SZ', '2026-02-13')
    ]
    
    for stock, date in test_cases:
        try:
            diagnose_single_stock(stock, date)
        except Exception as e:
            print(f"\n❌ 处理 {stock} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == '__main__':
    main()