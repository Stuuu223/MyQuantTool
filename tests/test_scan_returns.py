"""
CTO V48 榜单收益回撤测试

扫描20260225-20260305各榜单，追踪所有标的到0306的：
1. 期间最大收益
2. 期间最大回撤
3. 截至0306的收益
4. 截至0306的回撤

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


def get_top_stocks(date: str, top_n: int = 10) -> List[Dict]:
    """
    获取指定日期的Top N股票榜单
    
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
                # 【CTO V50】冻结时间改为09:45，消除尾盘腰斩
                frozen_time = dt_class.combine(dt_class.today(), time_type(9, 45, 0))
                
                result = core_engine.calculate_true_dragon_score(
                    net_inflow=current_amount * raw_purity * 0.5,  # V49: 对齐实盘引擎
                    price=current_price,
                    prev_close=pre_close,
                    high=tick_high,
                    low=tick_low,
                    open_price=open_price,
                    flow_5min=flow_5min,
                    flow_15min=flow_15min,
                    flow_5min_median_stock=1.0,
                    space_gap_pct=0.5,
                    float_volume_shares=fv,
                    current_time=frozen_time
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
                        'purity': quant_purity
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
    print("📊 CTO V48 榜单收益回撤测试")
    print(f"   测试范围: {START_DATE} ~ {END_DATE}")
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
            print(f"   ✅ {date}: Top1 {top_stocks[0]['code']} {top_stocks[0]['score']:.1f}分")
            
            # 记录股票首次出现
            for stock_info in top_stocks:
                code = stock_info['code']
                if code not in all_stocks_data:
                    all_stocks_data[code] = {
                        'first_seen': date,
                        'entry_price': stock_info['price'],
                        'entry_score': stock_info['score']
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
                **returns
            })
    
    # 按最大收益排序
    results.sort(key=lambda x: x['max_return'] or 0, reverse=True)
    
    # 输出结果
    print("\n" + "=" * 120)
    print("📈 收益回撤分析结果 (按最大收益排序)")
    print("=" * 120)
    print(f"{'股票':<12} {'首次出现':<12} {'入场价':<10} {'入场分':<8} {'最大收益%':<12} {'最大回撤%':<12} {'最终收益%':<12} {'最终回撤%':<12}")
    print("-" * 120)
    
    for r in results[:30]:  # 显示Top 30
        print(f"{r['code']:<12} {r['first_seen']:<12} {r['entry_price']:<10.2f} {r['entry_score']:<8.1f} "
              f"{r['max_return']:>+11.2f}% {r['max_drawdown']:>11.2f}% "
              f"{r['final_return']:>+11.2f}% {r['final_drawdown']:>11.2f}%")
    
    # 统计汇总
    print("\n" + "=" * 80)
    print("📊 汇总统计")
    print("=" * 80)
    
    if results:
        max_returns = [r['max_return'] for r in results if r['max_return'] is not None]
        final_returns = [r['final_return'] for r in results if r['final_return'] is not None]
        max_drawdowns = [r['max_drawdown'] for r in results if r['max_drawdown'] is not None]
        
        print(f"平均最大收益: {sum(max_returns)/len(max_returns):.2f}%")
        print(f"平均最终收益: {sum(final_returns)/len(final_returns):.2f}%")
        print(f"平均最大回撤: {sum(max_drawdowns)/len(max_drawdowns):.2f}%")
        print(f"正收益比例: {sum(1 for r in final_returns if r > 0)/len(final_returns)*100:.1f}%")
        print(f"涨幅>10%比例: {sum(1 for r in max_returns if r > 10)/len(max_returns)*100:.1f}%")
    
    # 保存结果
    output_path = 'data/validation/scan_returns_analysis.csv'
    import os
    os.makedirs('data/validation', exist_ok=True)
    
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存到: {output_path}")


if __name__ == '__main__':
    main()
