"""
CTO V35 照妖镜修复版 - 榜单收益回撤测试

扫描20260225-20260305各榜单，追踪所有标的到0306的：
1. 期间最大收益
2. 期间最大回撤
3. 截至0306的收益
4. 截至0306的回撤

V35修复清单：
- 动态danger_pct：主板8.5%/创业板17%/北交所25%（解决用主板标尺惩罚创业板）

V34修复清单：
- 毒瘤一修复：废除时间冻结(09:45)，改用mode="scan"跳过尾盘衰减
- 毒瘤二修复：涨停检测改用绝对价格推导(limit_up_price=pre_close*1.10/1.20)

⚠️ 【CTO阴阳测试免责声明】⚠️
本脚本仅为Scan榜单静态探测，代表"如果按榜单买入并持有到截止日"的理论收益。
不包含以下实盘防守逻辑：
1. EV盈亏比拦截闸（涨幅>8.5%未封板不执行）
2. 黄金3分钟生死观察队列（3分钟抗重力测试）
3. 流动性防骗炮护城河（卖盘真空区过滤）

因此，本测试结果≠真实实盘胜率，仅供榜单质量评估使用。
真实实盘胜率需要通过Live模式Tick级回演验证。

用法:
    python tests/test_scan_returns.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from xtquant import xtdata
import pandas as pd
from typing import Dict, List, Tuple

# 测试日期范围
START_DATE = '20260225'
END_DATE = '20260306'

# 交易日列表（需要根据实际情况调整）
TRADING_DAYS = [
    '20260225',
    '20260226', 
    '20260227',
    '20260228',
    '20260302',  # 周一
    '20260303',
    '20260304',
    '20260305',
    '20260306',
]


def get_top_stocks(date: str, top_n: int = 20) -> List[Dict]:
    """
    获取指定日期的Top N股票榜单（V33照妖镜版本）
    
    返回: [{'code': '600354.SH', 'score': 90.0, 'price': 7.63, ...}, ...]
    """
    from logic.data_providers.universe_builder import UniverseBuilder
    from logic.data_providers.true_dictionary import get_true_dictionary
    from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine
    from datetime import time as time_type
    
    print(f"  扫描 {date}...")
    
    try:
        # 1. 获取粗筛底池
        builder = UniverseBuilder(target_date=date)
        base_pool, volume_ratios = builder.build()
        
        if not base_pool:
            print(f"  ⚠️ {date} 粗筛底池为空")
            return []
        
        # 2. 预热TrueDictionary
        true_dict = get_true_dictionary()
        true_dict.warmup(base_pool, target_date=date)
        
        # 3. 逐只读取Tick打分
        core_engine = 动能打分引擎CoreEngine()
        results = []
        
        for stock in base_pool:
            try:
                local_data = xtdata.get_local_data(
                    field_list=[],
                    stock_list=[stock],
                    period='tick',
                    start_time=date,
                    end_time=date
                )
                
                if not local_data or stock not in local_data:
                    continue
                    
                df = pd.DataFrame(local_data[stock])
                if df.empty:
                    continue
                
                tick = df.iloc[-1]
                current_price = float(tick.get('lastPrice', 0))
                current_amount = float(tick.get('amount', 0))
                pre_close = float(tick.get('lastClose', 0))
                
                if pre_close <= 0 or current_price <= 0:
                    continue
                
                tick_high = float(tick.get('high', current_price))
                tick_low = float(tick.get('low', current_price))
                open_price = float(tick.get('open', current_price))
                
                # 【CTO V34照妖镜修复】用绝对价格推导判断涨停（解决盘后askPrice1被清空的问题）
                # 涨停价计算：主板10%，创业板/科创板20%，北交所30%
                if stock.startswith(('30', '68')):  # 创业板、科创板 20%
                    limit_up_price = round(pre_close * 1.20, 2)
                elif stock.startswith(('8', '4')):  # 北交所 30%
                    limit_up_price = round(pre_close * 1.30, 2)
                else:  # 主板 10%
                    limit_up_price = round(pre_close * 1.10, 2)
                # 现价距离涨停价<1分钱即判定为物理封板
                is_limit_up = (current_price >= limit_up_price - 0.011)
                
                # 封单金额：尝试从盘口获取，若无法获取则给默认值
                ask_price1 = float(tick.get('askPrice1', 0.0) or 0.0)
                bid_price1 = float(tick.get('bidPrice1', 0.0) or 0.0)
                bid_vol1 = int(tick.get('bidVol1', 0) or 0) * 100  # 手转股
                if is_limit_up:
                    if bid_price1 > 0 and bid_vol1 > 0:
                        limit_up_queue_amount = bid_price1 * bid_vol1
                    else:
                        # 盘口数据缺失时，给一个默认封单（防止真龙被误判）
                        limit_up_queue_amount = 50000000.0  # 默认5000万封单
                else:
                    limit_up_queue_amount = 0.0
                
                # 计算参数
                price_position = (current_price - tick_low) / (tick_high - tick_low) if tick_high > tick_low else 0.5
                change_pct = (current_price - pre_close) / pre_close
                acceleration_factor = 1.0 + (price_position - 0.5) * 1.0 + change_pct * 3.0
                acceleration_factor = max(0.3, min(acceleration_factor, 3.0))
                
                flow_5min = current_amount / 240.0 * 5
                flow_15min = current_amount / 240.0 * 15 * acceleration_factor
                
                fv = true_dict.get_float_volume(stock)
                if not fv or fv <= 0:
                    fv = 1_000_000_000.0
                elif fv < 10_000_000:
                    fv *= 10000
                
                price_range = tick_high - tick_low
                raw_purity = (current_price - pre_close) / price_range if price_range > 0 else (1.0 if current_price > pre_close else -1.0)
                
                from datetime import datetime as dt_class
                # 【CTO V34修复】废除时间冻结毒瘤！使用实际时间+mode=scan跳过衰减
                actual_time = dt_class.combine(dt_class.today(), time_type(15, 0, 0))  # 使用实际收盘时间
                
                # 【CTO V37】动态势能基准估算（废除1.0硬编码造假！）
                # 物理假设：A股正常标的，平均每日换手率约2%。全天240分钟，5分钟占1/48。
                # 正常的5分钟成交额（中位数）大约是：流通市值 * 2% / 48 ≈ 流通市值 * 0.0004
                dynamic_median_flow = fv * 0.0004 if fv > 0 else 1.0
                
                # 【CTO V33】调用引擎，传入涨停状态和封单金额
                result = core_engine.calculate_true_dragon_score(
                    net_inflow=current_amount * raw_purity * 0.5,  # V49: 对齐实盘引擎
                    price=current_price,
                    prev_close=pre_close,
                    high=tick_high,
                    low=tick_low,
                    open_price=open_price,
                    flow_5min=flow_5min,
                    flow_15min=flow_15min,
                    flow_5min_median_stock=dynamic_median_flow,  # 【CTO V37】动态估算基准！
                    space_gap_pct=0.5,
                    float_volume_shares=fv,
                    current_time=actual_time,
                    is_limit_up=is_limit_up,  # 【CTO V33】涨停状态
                    limit_up_queue_amount=limit_up_queue_amount,  # 【CTO V33】封单金额
                    mode="scan",  # 【CTO V34】scan模式跳过时间衰减
                    stock_code=stock  # 【CTO V35】股票代码用于动态danger_pct
                )
                
                if isinstance(result, tuple) and len(result) >= 5:
                    score, sustain_ratio, inflow_ratio, ratio_stock, mfe = result[:5]
                else:
                    continue
                
                quant_purity = min(max(raw_purity * 100, -100), 100)
                
                if score >= 50.0 and quant_purity > -50.0:
                    results.append({
                        'code': stock,
                        'score': score,
                        'price': current_price,
                        'change': change_pct * 100,
                        'inflow_ratio': min(max(inflow_ratio, -50.0), 50.0),
                        'sustain_ratio': sustain_ratio,
                        'mfe': mfe,
                        'purity': quant_purity,
                        'is_limit_up': is_limit_up,  # 【CTO V33】新增
                        'limit_up_queue_amount': limit_up_queue_amount  # 【CTO V33】新增
                    })
                    
            except Exception as e:
                continue
        
        # 排序取Top N
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]
        
    except Exception as e:
        print(f"  ❌ {date} 扫描失败: {e}")
        return []


def calculate_returns(stock: str, entry_date: str, end_date: str) -> Dict:
    """
    计算股票从entry_date到end_date的收益回撤
    
    返回: {
        'max_return': 最大收益率,
        'max_drawdown': 最大回撤率,
        'final_return': 截至end_date收益率,
        'final_drawdown': 截至end_date回撤率
    }
    """
    try:
        # 获取日K数据
        start_date = (datetime.strptime(entry_date, '%Y%m%d') - timedelta(days=5)).strftime('%Y%m%d')
        
        data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close'],
            stock_list=[stock],
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        
        if not data or stock not in data:
            return {'max_return': None, 'max_drawdown': None, 'final_return': None, 'final_drawdown': None}
        
        df = pd.DataFrame(data[stock])
        if df.empty or len(df) == 0:
            return {'max_return': None, 'max_drawdown': None, 'final_return': None, 'final_drawdown': None}
        
        # 找到entry_date的收盘价作为基准
        entry_close = None
        for idx in df.index:
            if str(idx) == entry_date:
                entry_close = float(df.loc[idx, 'close'])
                break
        
        if entry_close is None or entry_close <= 0:
            # 取entry_date之后的第一个有效价格
            for idx in df.index:
                if str(idx) >= entry_date:
                    entry_close = float(df.loc[idx, 'close'])
                    break
        
        if entry_close is None or entry_close <= 0:
            return {'max_return': None, 'max_drawdown': None, 'final_return': None, 'final_drawdown': None}
        
        # 计算期间收益和回撤
        max_price = entry_close
        min_price = entry_close
        final_close = entry_close
        
        for idx in df.index:
            if str(idx) >= entry_date:
                high = float(df.loc[idx, 'high'])
                low = float(df.loc[idx, 'low'])
                close = float(df.loc[idx, 'close'])
                
                max_price = max(max_price, high)
                min_price = min(min_price, low)
                final_close = close
        
        max_return = (max_price - entry_close) / entry_close * 100
        max_drawdown = (entry_close - min_price) / entry_close * 100
        final_return = (final_close - entry_close) / entry_close * 100
        
        # 计算最终回撤（从最高点到最终价格）
        final_drawdown = (max_price - final_close) / max_price * 100 if max_price > entry_close else 0
        
        return {
            'max_return': round(max_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'final_return': round(final_return, 2),
            'final_drawdown': round(final_drawdown, 2)
        }
        
    except Exception as e:
        return {'max_return': None, 'max_drawdown': None, 'final_return': None, 'final_drawdown': None}


def main():
    print("=" * 80)
    print("📊 CTO V35 照妖镜修复版 - 榜单收益回撤测试")
    print(f"   测试范围: {START_DATE} ~ {END_DATE}")
    print("   核心修复: 动态danger_pct + 封板绝对价格推导 + 废除时间冻结")
    print("=" * 80)
    
    # 检查日K数据
    print("\n📦 检查日K数据范围...")
    sample = xtdata.get_local_data(
        field_list=['close'],
        stock_list=['600354.SH'],
        period='1d',
        start_time='20260220',
        end_time='20260310'
    )
    df = pd.DataFrame(sample['600354.SH']) if '600354.SH' in sample else None
    if df is not None and not df.empty:
        print(f"   日K数据范围: {df.index[0]} ~ {df.index[-1]}")
    else:
        print("   ⚠️ 无法获取日K数据范围")
    
    # 存储所有股票的累计数据
    all_stocks_data = {}  # {stock: {'first_seen': date, 'entry_price': price, 'returns': {...}}}
    daily_results = {}  # {date: [top_stocks]}
    
    # 扫描每天的榜单
    print("\n📦 扫描各日榜单...")
    for date in TRADING_DAYS[:-1]:  # 不包括最后一天
        if date >= END_DATE:
            continue
            
        top_stocks = get_top_stocks(date, top_n=20)
        
        if top_stocks:
            daily_results[date] = top_stocks
            # 统计封板数量
            limit_up_count = sum(1 for s in top_stocks if s.get('is_limit_up', False))
            print(f"   ✅ {date}: Top1 {top_stocks[0]['code']} {top_stocks[0]['score']:.1f}分 (封板{limit_up_count}/{len(top_stocks)}只)")
            
            # 记录股票首次出现
            for stock_info in top_stocks:
                code = stock_info['code']
                if code not in all_stocks_data:
                    all_stocks_data[code] = {
                        'first_seen': date,
                        'entry_price': stock_info['price'],
                        'entry_score': stock_info['score'],
                        'is_limit_up': stock_info.get('is_limit_up', False),
                        'limit_up_queue': stock_info.get('limit_up_queue_amount', 0)
                    }
        else:
            print(f"   ⚠️ {date}: 无结果")
    
    print(f"\n📦 累计出现股票数: {len(all_stocks_data)}")
    
    # 计算每只股票的收益回撤
    print("\n📦 计算收益回撤...")
    results = []
    
    for stock, info in all_stocks_data.items():
        returns = calculate_returns(stock, info['first_seen'], END_DATE)
        
        if returns['max_return'] is not None:
            results.append({
                'code': stock,
                'first_seen': info['first_seen'],
                'entry_price': info['entry_price'],
                'entry_score': info['entry_score'],
                'is_limit_up': info['is_limit_up'],
                'limit_up_queue': info['limit_up_queue'],
                **returns
            })
    
    # 按最大收益排序
    results.sort(key=lambda x: x['max_return'] or 0, reverse=True)
    
    # 输出结果
    print("\n" + "=" * 140)
    print("📈 收益回撤分析结果 (按最大收益排序)")
    print("=" * 140)
    print(f"{'股票':<12} {'首次出现':<12} {'入场价':<10} {'入场分':<10} {'封板':<6} {'最大收益%':<12} {'最大回撤%':<12} {'最终收益%':<12} {'最终回撤%':<12}")
    print("-" * 140)
    
    for r in results[:30]:  # 显示Top 30
        limit_tag = "✅" if r['is_limit_up'] else "❌"
        print(f"{r['code']:<12} {r['first_seen']:<12} {r['entry_price']:<10.2f} {r['entry_score']:<10.1f} {limit_tag:<6} "
              f"{r['max_return']:>+11.2f}% {r['max_drawdown']:>11.2f}% "
              f"{r['final_return']:>+11.2f}% {r['final_drawdown']:>11.2f}%")
    
    # 统计汇总
    print("\n" + "=" * 80)
    print("📊 V35 照妖镜修复版 汇总统计")
    print("=" * 80)
    
    # 【CTO阴阳测试免责声明】
    print("\n⚠️  【免责声明】本测试仅为Scan榜单静态探测，不代表真实实盘胜率！")
    print("   未包含：EV盈亏比拦截、黄金3分钟观察、流动性防骗炮护城河")
    print("   真实胜率需通过Live模式Tick级回演验证。\n")
    
    if results:
        max_returns = [r['max_return'] for r in results if r['max_return'] is not None]
        final_returns = [r['final_return'] for r in results if r['final_return'] is not None]
        max_drawdowns = [r['max_drawdown'] for r in results if r['max_drawdown'] is not None]
        entry_scores = [r['entry_score'] for r in results]
        
        # 封板股统计
        limit_up_stocks = [r for r in results if r['is_limit_up']]
        non_limit_up_stocks = [r for r in results if not r['is_limit_up']]
        
        print(f"\n【整体统计】")
        print(f"样本数量: {len(results)}")
        print(f"分数范围: {min(entry_scores):.1f} ~ {max(entry_scores):.1f}")
        print(f"平均最大收益: {sum(max_returns)/len(max_returns):.2f}%")
        print(f"平均最终收益: {sum(final_returns)/len(final_returns):.2f}%")
        print(f"平均最大回撤: {sum(max_drawdowns)/len(max_drawdowns):.2f}%")
        print(f"正收益比例: {sum(1 for r in final_returns if r > 0)/len(final_returns)*100:.1f}%")
        print(f"涨幅>10%比例: {sum(1 for r in max_returns if r > 10)/len(max_returns)*100:.1f}%")
        
        print(f"\n【封板照妖镜效果】")
        if limit_up_stocks:
            limit_returns = [r['max_return'] for r in limit_up_stocks]
            limit_final = [r['final_return'] for r in limit_up_stocks]
            print(f"封板股数量: {len(limit_up_stocks)} ({len(limit_up_stocks)/len(results)*100:.1f}%)")
            print(f"封板股平均最大收益: {sum(limit_returns)/len(limit_returns):.2f}%")
            print(f"封板股平均最终收益: {sum(limit_final)/len(limit_final):.2f}%")
        
        if non_limit_up_stocks:
            non_limit_returns = [r['max_return'] for r in non_limit_up_stocks]
            non_limit_final = [r['final_return'] for r in non_limit_up_stocks]
            print(f"非封板股数量: {len(non_limit_up_stocks)} ({len(non_limit_up_stocks)/len(results)*100:.1f}%)")
            print(f"非封板股平均最大收益: {sum(non_limit_returns)/len(non_limit_returns):.2f}%")
            print(f"非封板股平均最终收益: {sum(non_limit_final)/len(non_limit_final):.2f}%")
        
        # 分数分布
        print(f"\n【分数分布】")
        score_bins = [(0, 100), (100, 300), (300, 500), (500, 1000), (1000, float('inf'))]
        for low, high in score_bins:
            count = sum(1 for s in entry_scores if low <= s < high)
            if count > 0:
                high_str = str(int(high)) if high < float('inf') else "∞"
                print(f"  {low}-{high_str}分: {count}只 ({count/len(results)*100:.1f}%)")
    
    # 保存结果
    output_path = 'data/validation/scan_returns_v34.csv'
    import os
    os.makedirs('data/validation', exist_ok=True)
    
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存到: {output_path}")


if __name__ == '__main__':
    main()
