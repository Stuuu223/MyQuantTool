"""详细检查AkShare数据日期范围"""
import akshare as ak
from datetime import datetime

code = "000050"
market = "sz"

print("="*60)
print("详细检查AkShare数据日期范围")
print("="*60)

try:
    df = ak.stock_individual_fund_flow(stock=code, market=market)

    if df.empty:
        print("❌ 未获取到数据")
    else:
        print(f"✅ 获取到 {len(df)} 条数据")
        print(f"\n当前日期: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"\n数据日期范围:")
        print(f"  最新: {df.iloc[0]['日期']}")
        print(f"  最旧: {df.iloc[-1]['日期']}")

        # 检查数据日期是否连续
        print(f"\n数据时间跨度:")
        latest_date = df.iloc[0]['日期']
        oldest_date = df.iloc[-1]['日期']

        try:
            latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
            oldest_dt = datetime.strptime(oldest_date, '%Y-%m-%d')
            current_dt = datetime.now()

            days_span = (latest_dt - oldest_dt).days
            days_to_now = (current_dt - latest_dt).days

            print(f"  数据时间跨度: {days_span} 天")
            print(f"  距今天数: {days_to_now} 天")

            if days_to_now > 30:
                print(f"  ⚠️  数据滞后严重！距今已超过30天")
        except:
            pass

        # 打印前10条和后10条
        print(f"\n前10条数据:")
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            print(f"  {row['日期']}: 主力={row['主力净流入-净额']/1e4:.1f}万, 涨跌={row['涨跌幅']:.2f}%")

        print(f"\n后10条数据:")
        for i in range(max(0, len(df)-10), len(df)):
            row = df.iloc[i]
            print(f"  {row['日期']}: 主力={row['主力净流入-净额']/1e4:.1f}万, 涨跌={row['涨跌幅']:.2f}%")

except Exception as e:
    print(f"❌ 获取数据失败: {e}")
    import traceback
    traceback.print_exc()

print("="*60)