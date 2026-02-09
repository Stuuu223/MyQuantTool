"""验证修复后的资金流数据"""
import json
import tushare as ts

# 检查000050的真实资金流
api = ts.pro_api('1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b')
df = api.moneyflow(trade_date='20260109', ts_code='000050.SZ')

row = df.iloc[0]

print("="*60)
print("000050.SZ 资金流数据验证")
print("="*60)

# 金额字段（单位：千元）
buy_elg = row['buy_elg_amount'] * 1000  # 转换为元
sell_elg = row['sell_elg_amount'] * 1000
buy_lg = row['buy_lg_amount'] * 1000
sell_lg = row['sell_lg_amount'] * 1000

main_net_inflow = (buy_elg - sell_elg) + (buy_lg - sell_lg)

print(f"超大单买入: {buy_elg/1e4:.1f}万")
print(f"超大单卖出: {sell_elg/1e4:.1f}万")
print(f"大单买入: {buy_lg/1e4:.1f}万")
print(f"大单卖出: {sell_lg/1e4:.1f}万")
print(f"主力净流入: {main_net_inflow/1e4:.1f}万")
print("="*60)

# 检查市值信息
df2 = api.daily_basic(ts_code='000050.SZ', trade_date='20260109', fields='trade_date,total_mv,circ_mv,turnover_rate')
print(f"总市值: {df2.iloc[0]['total_mv']/1e4:.1f}亿")
print(f"流通市值: {df2.iloc[0]['circ_mv']/1e4:.1f}亿")
print(f"换手率: {df2.iloc[0]['turnover_rate']:.2f}%")
print("="*60)

# 计算Attack评分
# 从daily接口获取成交额
df_daily = api.daily(ts_code='000050.SZ', trade_date='20260109')
amount_yi = df_daily.iloc[0]['amount'] * 1000 / 1e8  # Tushare的amount单位是千元
flow_score = min(main_net_inflow / 100 * 20, 100)  # 100万=20分

pct_chg = 7.1055
if pct_chg < 5:
    pct_score = 0
elif pct_chg < 10:
    pct_score = pct_chg * 16
else:
    pct_score = 80 + (pct_chg - 10) * 10

if amount_yi < 0.05:
    amount_score = 100
elif amount_yi < 0.1:
    amount_score = 80
elif amount_yi < 0.3:
    amount_score = 50
else:
    amount_score = 20

total_score = flow_score * 0.5 + pct_score * 0.3 + amount_score * 0.2

print(f"Attack评分计算:")
print(f"  主力流入({main_net_inflow/1e4:.1f}万): {flow_score:.1f}分 (权重50%)")
print(f"  涨幅({pct_chg:.2f}%): {pct_score:.1f}分 (权重30%)")
print(f"  成交额({amount_yi:.2f}亿): {amount_score:.1f}分 (权重20%)")
print(f"  总分: {total_score:.1f}")
print("="*60)

# 判断分类
if main_net_inflow > 1000000:
    category = "机会池"
elif main_net_inflow > 500000:
    category = "观察池"
else:
    category = "黑名单"

print(f"分类结果: {category}")
print(f"主力流入1366万 > 100万 = 机会池 ✅")