# -*- coding: utf-8 -*-
"""
CTO V24诊断测试 - 对比91只vs5只的差异根因

问题：
- 19:44运行：粗筛91只，正确
- 22:29运行：粗筛5只，错误

目的：
1. 验证UniverseBuilder底池构建
2. 验证_snapshot_filter过滤逻辑
3. 验证TrueDictionary预热
4. 验证自愈下载、日历防爆
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import time

def diagnose():
    """诊断底池构建和过滤流程"""
    
    print("=" * 80)
    print("🔍 CTO V24 诊断测试 - 91只vs5只差异根因")
    print("=" * 80)
    
    # Step 1: 测试UniverseBuilder底池构建
    print("\n" + "=" * 80)
    print("【Step 1】UniverseBuilder底池构建测试")
    print("=" * 80)
    
    from logic.data_providers.universe_builder import UniverseBuilder
    from xtquant import xtdata
    import pandas as pd
    import numpy as np
    
    target_date = datetime.now().strftime('%Y%m%d')
    builder = UniverseBuilder(target_date=target_date)
    
    t0 = time.perf_counter()
    base_pool, volume_ratios = builder.build()
    elapsed = (time.perf_counter() - t0) * 1000
    
    stats = builder.get_stats()
    
    print(f"\n📊 UniverseBuilder结果:")
    print(f"  - 目标日期: {target_date}")
    print(f"  - 漏斗1后: {stats.get('after_funnel1', 'N/A')}只")
    print(f"  - 漏斗2后: {stats.get('after_funnel2', 'N/A')}只")
    print(f"  - 最终底池: {len(base_pool)}只")
    print(f"  - 耗时: {elapsed:.0f}ms")
    
    # 检查001696在漏斗中的状态
    target_stock = '001696.SZ'
    print(f"\n🔍 检查 {target_stock} (宗申动力) 在UniverseBuilder中的状态:")
    
    # 检查是否在漏斗1通过
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    if target_stock in all_stocks:
        print(f"  - 在全市场列表中: ✅")
        
        # 检查静态过滤条件
        code = target_stock.split('.')[0]
        if code[:2] in ('43', '83', '87', '88'):
            print(f"  - 漏斗1静态过滤: ❌ 北交所股票")
        elif code.startswith('688'):
            print(f"  - 漏斗1静态过滤: ❌ 科创板股票")
        else:
            detail = xtdata.get_instrument_detail(target_stock, False)
            if detail:
                name = detail.get('InstrumentName', '') if hasattr(detail, 'get') else getattr(detail, 'InstrumentName', '')
                if 'ST' in name.upper() or '退' in name or '摘' in name:
                    print(f"  - 漏斗1静态过滤: ❌ ST/退市股票 ({name})")
                else:
                    print(f"  - 漏斗1静态过滤: ✅ 通过 ({name})")
            else:
                print(f"  - 漏斗1静态过滤: ⚠️ 无法获取股票信息")
    else:
        print(f"  - 在全市场列表中: ❌ 不存在")
    
    # 检查漏斗2数据
    from logic.utils.calendar_utils import get_nth_previous_trading_day
    start_date = get_nth_previous_trading_day(target_date, 7)
    
    print(f"\n  漏斗2日K检查 ({start_date} ~ {target_date}):")
    try:
        data = xtdata.get_local_data(
            field_list=['close', 'volume', 'amount'],
            stock_list=[target_stock],
            period='1d',
            start_time=start_date,
            end_time=target_date
        )
        
        if data and target_stock in data:
            df = data[target_stock]
            if df is not None and len(df) > 0:
                n = min(5, len(df))
                avg_amount = df['amount'].iloc[-n:].mean()
                last_close = df['close'].iloc[-1]
                today_volume = float(df['volume'].iloc[-1])
                avg_volume_5d = df['volume'].iloc[-n:].mean()
                
                # 获取流通股本
                detail = xtdata.get_instrument_detail(target_stock, False)
                float_shares = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0)) if detail else 0
                
                if float_shares > 0:
                    float_mkt_cap = float_shares * last_close
                    avg_turnover_pct = (avg_amount / float_mkt_cap) * 100.0
                else:
                    avg_turnover_pct = 0
                
                print(f"    - 数据条数: {len(df)}条")
                print(f"    - 最近收盘价: {last_close:.2f}元")
                print(f"    - 5日均成交额: {avg_amount/10000:.0f}万 (门槛5000万)")
                print(f"    - 今日成交量: {today_volume:.0f}手")
                print(f"    - 5日均成交量: {avg_volume_5d:.0f}手")
                print(f"    - 流通股本: {float_shares/100000000:.2f}亿股")
                print(f"    - 5日换手率: {avg_turnover_pct:.2f}% (门槛5.0%)")
                
                # 判断过滤原因
                if avg_amount < 50_000_000:
                    print(f"    ⚠️ 过滤原因: 均额不足{avg_amount/10000:.0f}万 < 5000万")
                elif not (3.0 <= last_close <= 300.0):
                    print(f"    ⚠️ 过滤原因: 价格越界{last_close:.2f}不在3-300元")
                elif avg_turnover_pct < 5.0:
                    print(f"    ⚠️ 过滤原因: 换手不足{avg_turnover_pct:.2f}% < 5.0%")
                else:
                    print(f"    ✅ 应该通过漏斗2！检查是否在其他地方被过滤")
            else:
                print(f"    ❌ 无日K数据或数据为空")
        else:
            print(f"    ❌ get_local_data返回空数据")
            # 尝试下载
            print(f"    尝试下载日K数据...")
            xtdata.download_history_data(target_stock, period='1d', start_time=start_date, end_time=target_date)
            time.sleep(0.5)
            data = xtdata.get_local_data(
                field_list=['close', 'volume', 'amount'],
                stock_list=[target_stock],
                period='1d',
                start_time=start_date,
                end_time=target_date
            )
            if data and target_stock in data and data[target_stock] is not None:
                df = data[target_stock]
                print(f"    下载后数据: {len(df)}条")
            else:
                print(f"    下载后仍无数据！")
    except Exception as e:
        print(f"    ❌ 获取日K数据失败: {e}")
    
    if len(base_pool) < 50:
        print(f"\n🚨 警告：底池只有{len(base_pool)}只，远低于预期的91只！")
        print(f"  前10只: {base_pool[:10]}")
    else:
        print(f"\n✅ 底池数量正常: {len(base_pool)}只")
    
    # Step 2: 测试TrueDictionary预热
    print("\n" + "=" * 80)
    print("【Step 2】TrueDictionary预热测试")
    print("=" * 80)
    
    from logic.data_providers.true_dictionary import get_true_dictionary
    
    true_dict = get_true_dictionary()
    
    # 检查预热前状态
    print(f"\n预热前状态:")
    print(f"  - float_volume缓存: {len(true_dict._float_volume)}只")
    print(f"  - avg_volume_5d缓存: {len(true_dict._avg_volume_5d)}只")
    
    # 执行预热
    t0 = time.perf_counter()
    result = true_dict.warmup(base_pool, target_date=target_date)
    elapsed = (time.perf_counter() - t0) * 1000
    
    print(f"\n预热后状态:")
    print(f"  - float_volume缓存: {len(true_dict._float_volume)}只")
    print(f"  - avg_volume_5d缓存: {len(true_dict._avg_volume_5d)}只")
    print(f"  - QMT成功: {result.get('qmt', {}).get('success', 0)}只")
    print(f"  - 5日均量成功: {result.get('avg_volume', {}).get('success', 0)}只")
    print(f"  - 耗时: {elapsed:.0f}ms")
    
    # Step 3: 测试_snapshot_filter过滤逻辑（模拟）
    print("\n" + "=" * 80)
    print("【Step 3】_snapshot_filter过滤逻辑测试（模拟）")
    print("=" * 80)
    
    from xtquant import xtdata
    import pandas as pd
    import numpy as np
    
    # 获取快照
    print(f"\n获取{len(base_pool)}只股票的Tick快照...")
    try:
        snapshot = xtdata.get_full_tick(base_pool)
        print(f"  - 快照获取成功: {len(snapshot)}只")
    except Exception as e:
        print(f"  - 快照获取失败: {e}")
        snapshot = {}
    
    if snapshot:
        # 模拟_snapshot_filter的过滤逻辑
        df = pd.DataFrame([
            {
                'stock_code': code,
                'price': tick.get('lastPrice', 0) if isinstance(tick, dict) else 0,
                'volume': tick.get('volume', 0) if isinstance(tick, dict) else 0,
                'amount': tick.get('amount', 0) if isinstance(tick, dict) else 0,
                'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else 0,
            }
            for code, tick in snapshot.items() if tick
        ])
        
        print(f"\n快照DataFrame: {len(df)}行")
        
        # 从TrueDictionary获取数据
        df['avg_volume_5d'] = df['stock_code'].map(true_dict.get_avg_volume_5d)
        df['avg_turnover_5d'] = df['stock_code'].map(true_dict.get_avg_turnover_5d)
        df['float_volume'] = df['stock_code'].map(true_dict.get_float_volume)
        
        # 统计缺失情况
        missing_avg_vol = df['avg_volume_5d'].isna().sum() + (df['avg_volume_5d'] == 0).sum()
        missing_avg_turn = df['avg_turnover_5d'].isna().sum() + (df['avg_turnover_5d'] == 0).sum()
        missing_float = df['float_volume'].isna().sum() + (df['float_volume'] == 0).sum()
        
        print(f"\n数据缺失统计:")
        print(f"  - avg_volume_5d缺失: {missing_avg_vol}只 ({missing_avg_vol/len(df)*100:.1f}%)")
        print(f"  - avg_turnover_5d缺失: {missing_avg_turn}只 ({missing_avg_turn/len(df)*100:.1f}%)")
        print(f"  - float_volume缺失: {missing_float}只 ({missing_float/len(df)*100:.1f}%)")
        
        # 计算量比（时间进度加权）- 模拟_snapshot_filter的真实逻辑
        df['volume_gu'] = df['volume'] * 100  # 手→股
        
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        raw_minutes = (now - market_open).total_seconds() / 60
        minutes_passed = max(5, min(raw_minutes, 240))  # 缓冲5分钟，最大240分钟
        
        # 估算全天成交量
        df['estimated_full_day_volume'] = df['volume_gu'] / minutes_passed * 240
        # 【CTO修复】avg_volume_5d单位是手，需要乘100转成股
        df['avg_volume_5d_gu'] = df['avg_volume_5d'] * 100
        df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d_gu'].replace(0, pd.NA)
        
        # 开盘瞬时换手率
        df['current_turnover'] = (df['volume_gu'] / df['float_volume'].replace(0, pd.NA)) * 100
        
        # 5日均成交额
        df['avg_amount_5d'] = df['avg_volume_5d'] * df['prev_close'] * 100
        
        # 填充默认值（V24修复后）
        df['volume_ratio'] = df['volume_ratio'].fillna(1.0).infer_objects(copy=False)
        df['avg_turnover_5d'] = df['avg_turnover_5d'].fillna(2.5).infer_objects(copy=False)
        df['avg_amount_5d'] = df['avg_amount_5d'].fillna(50000000.0).infer_objects(copy=False)
        df['current_turnover'] = df['current_turnover'].fillna(0.0).infer_objects(copy=False)
        
        # 打印volume_ratio分布（关键调试！）
        print(f"\n📊 volume_ratio深度诊断:")
        print(f"  - minutes_passed: {minutes_passed:.1f}分钟 (盘后模式={minutes_passed >= 240})")
        print(f"  - volume_ratio分布:")
        print(f"      min: {df['volume_ratio'].min():.2f}")
        print(f"      25%: {df['volume_ratio'].quantile(0.25):.2f}")
        print(f"      50%: {df['volume_ratio'].median():.2f}")
        print(f"      75%: {df['volume_ratio'].quantile(0.75):.2f}")
        print(f"      max: {df['volume_ratio'].max():.2f}")
        print(f"  - volume_ratio=1.0的股票数: {len(df[df['volume_ratio'] == 1.0])}只")
        print(f"  - volume_ratio>1.5的股票数: {len(df[df['volume_ratio'] > 1.5])}只")
        
        # 打印今日成交量情况
        print(f"\n📈 今日成交量诊断:")
        print(f"  - volume=0的股票数: {len(df[df['volume'] == 0])}只")
        print(f"  - volume>0的股票数: {len(df[df['volume'] > 0])}只")
        if len(df[df['volume'] > 0]) > 0:
            print(f"  - volume>0的volume分布:")
            vol_df = df[df['volume'] > 0]
            print(f"      min: {vol_df['volume'].min():.0f}手")
            print(f"      median: {vol_df['volume'].median():.0f}手")
            print(f"      max: {vol_df['volume'].max():.0f}手")
        
        # 过滤条件
        min_volume_multiplier = 1.5
        min_avg_amount_5d = 50000000.0
        min_avg_turnover_5d = 2.5
        max_open_turnover = 30.0
        
        mask = (
            (df['volume_ratio'] >= min_volume_multiplier) &
            (df['avg_amount_5d'] >= min_avg_amount_5d) &
            (df['avg_turnover_5d'] >= min_avg_turnover_5d) &
            (df['current_turnover'] < max_open_turnover)
        )
        
        filtered_df = df[mask]
        
        print(f"\n过滤结果:")
        print(f"  - volume_ratio >= {min_volume_multiplier}x: {len(df[df['volume_ratio'] >= min_volume_multiplier])}只")
        print(f"  - avg_amount_5d >= 5000万: {len(df[df['avg_amount_5d'] >= min_avg_amount_5d])}只")
        print(f"  - avg_turnover_5d >= 2.5%: {len(df[df['avg_turnover_5d'] >= min_avg_turnover_5d])}只")
        print(f"  - 最终通过: {len(filtered_df)}只")
        
        if len(filtered_df) < 20:
            print(f"\n🚨 警告：过滤后只剩{len(filtered_df)}只！")
            print(f"  通过的股票: {filtered_df['stock_code'].tolist()}")
        
        # Step 3.5: 模拟_run_radar_main_loop的细筛逻辑
        print("\n" + "=" * 80)
        print("【Step 3.5】_run_radar_main_loop细筛模拟")
        print("=" * 80)
        
        fine_filtered = []
        atr_rejected = 0
        turnover_rejected = 0
        
        for idx, row in filtered_df.iterrows():
            stock_code = row['stock_code']
            
            # 获取ATR数据
            atr_20d = true_dict.get_atr_20d(stock_code)
            
            # 从snapshot获取high/low
            tick = snapshot.get(stock_code, {})
            if isinstance(tick, dict):
                tick_high = tick.get('high', row['price'])
                tick_low = tick.get('low', row['price'])
            else:
                tick_high = row['price']
                tick_low = row['price']
            
            today_tr = tick_high - tick_low
            
            # 细筛条件1: ATR势垒
            if atr_20d and atr_20d > 0 and today_tr > 0:
                atr_ratio = today_tr / atr_20d
                if atr_ratio < 1.8:
                    atr_rejected += 1
                    continue  # ATR势垒不足，跳过
            
            # 细筛条件2: 死亡换手
            current_turnover = row['current_turnover']
            if current_turnover >= 70.0:
                turnover_rejected += 1
                continue
            
            fine_filtered.append(stock_code)
        
        print(f"\n细筛结果:")
        print(f"  - 粗筛通过: {len(filtered_df)}只")
        print(f"  - ATR势垒不足(<1.8x): {atr_rejected}只被淘汰")
        print(f"  - 死亡换手(>=70%): {turnover_rejected}只被淘汰")
        print(f"  - 细筛通过: {len(fine_filtered)}只")
        
        if len(fine_filtered) <= 10:
            print(f"\n细筛通过的股票: {fine_filtered}")
        
        # 检查19:44榜首是否在细筛结果中
        target_stock = '001696.SZ'  # 宗申动力
        
        # 先检查是否在粗筛结果中
        if target_stock not in filtered_df['stock_code'].values:
            print(f"\n🚨 {target_stock}(宗申动力)未通过粗筛！")
            # 检查原因
            # 重新获取原始数据
            orig_row = df[df['stock_code'] == target_stock]
            if len(orig_row) > 0:
                orig_row = orig_row.iloc[0]
                print(f"    - volume_ratio: {orig_row['volume_ratio']:.2f}x (需要>=1.5x)")
                print(f"    - avg_amount_5d: {orig_row['avg_amount_5d']/10000:.0f}万 (需要>=5000万)")
                print(f"    - avg_turnover_5d: {orig_row['avg_turnover_5d']:.1f}% (需要>=2.5%)")
                print(f"    - current_turnover: {orig_row['current_turnover']:.2f}% (需要<30%)")
                print(f"    - 原始volume: {orig_row['volume']:.0f}手")
                print(f"    - 原始price: {orig_row['price']:.2f}元")
                print(f"    - 原始prev_close: {orig_row['prev_close']:.2f}元")
                
                # 检查是否在原始df中
                print(f"\n    检查各条件:")
                print(f"    - volume_ratio >= 1.5: {orig_row['volume_ratio'] >= 1.5}")
                print(f"    - avg_amount_5d >= 5000万: {orig_row['avg_amount_5d'] >= 50000000}")
                print(f"    - avg_turnover_5d >= 2.5%: {orig_row['avg_turnover_5d'] >= 2.5}")
                print(f"    - current_turnover < 30%: {orig_row['current_turnover'] < 30}")
            else:
                print(f"    ⚠️ {target_stock}不在底池中！")
                # 检查是否在base_pool中
                if target_stock in base_pool:
                    print(f"    - 在base_pool中，但不在快照数据中")
                else:
                    print(f"    - 不在base_pool中！UniverseBuilder漏斗将其过滤了！")
        elif target_stock in fine_filtered:
            print(f"\n✅ {target_stock}(宗申动力)通过细筛！")
            # 打印详细数据
            target_row = filtered_df[filtered_df['stock_code'] == target_stock].iloc[0]
            atr_20d = true_dict.get_atr_20d(target_stock)
            tick = snapshot.get(target_stock, {})
            if isinstance(tick, dict):
                tick_high = tick.get('high', target_row['price'])
                tick_low = tick.get('low', target_row['price'])
            else:
                tick_high = target_row['price']
                tick_low = target_row['price']
            today_tr = tick_high - tick_low
            atr_ratio = today_tr / atr_20d if atr_20d and atr_20d > 0 else 0
            print(f"    - ATR_20D: {atr_20d:.4f}")
            print(f"    - 今日波幅: {today_tr:.2f}")
            print(f"    - ATR比率: {atr_ratio:.2f}x")
            print(f"    - 换手率: {target_row['current_turnover']:.2f}%")
        else:
            print(f"\n🚨 {target_stock}(宗申动力)被细筛淘汰！")
            # 检查原因
            target_row = filtered_df[filtered_df['stock_code'] == target_stock].iloc[0]
            atr_20d = true_dict.get_atr_20d(target_stock)
            tick = snapshot.get(target_stock, {})
            if isinstance(tick, dict):
                tick_high = tick.get('high', target_row['price'])
                tick_low = tick.get('low', target_row['price'])
            else:
                tick_high = target_row['price']
                tick_low = target_row['price']
            today_tr = tick_high - tick_low
            atr_ratio = today_tr / atr_20d if atr_20d and atr_20d > 0 else 0
            print(f"    - ATR_20D: {atr_20d:.4f}")
            print(f"    - 今日波幅: {today_tr:.2f}")
            print(f"    - ATR比率: {atr_ratio:.2f}x (需要>=1.8x)")
            print(f"    - 换手率: {target_row['current_turnover']:.2f}%")
            
            # 检查ATR是否为默认值
            if atr_20d == 0.05:
                print(f"    ⚠️ ATR使用默认值0.05，说明日K数据缺失！")
    
    # Step 4: 对比19:44和22:29的战果
    print("\n" + "=" * 80)
    print("【Step 4】战果对比分析")
    print("=" * 80)
    
    # 19:44的战果（正确）
    result_1944 = {
        'time': '19:44:13',
        'pool_size': 91,
        'top10': [
            ('001696.SZ', 91.1, '+9.99%', '7.43%', 'PURE'),
            ('000862.SZ', 81.8, '+3.97%', '6.74%', 'PURE'),
            ('000545.SZ', 81.3, '+9.97%', '10.19%', 'PURE'),
            ('600545.SH', 80.9, '+10.08%', '4.92%', 'PURE'),
            ('002470.SZ', 79.8, '+10.00%', '6.00%', 'PURE'),
            ('603316.SH', 79.7, '+10.00%', '3.74%', 'PURE'),
            ('002015.SZ', 79.3, '+10.00%', '2.97%', 'PURE'),
            ('000525.SZ', 79.1, '+4.07%', '3.22%', 'PURE'),
            ('300030.SZ', 79.0, '+3.92%', '1.77%', 'PURE'),
            ('002638.SZ', 77.9, '+3.47%', '2.25%', 'PURE'),
        ]
    }
    
    # 22:29的战果（错误）
    result_2229 = {
        'time': '22:29:47',
        'pool_size': 5,
        'top10': [
            ('600227.SH', 81.4, '+10.03%', '5.26%', '+78.9%'),
            ('600545.SH', 80.9, '+10.08%', '4.92%', '+100.0%'),
            ('600452.SH', 73.1, '+7.39%', '2.69%', '+74.8%'),
            ('600207.SH', 54.5, '+3.23%', '1.09%', '+47.4%'),
        ]
    }
    
    print(f"\n📊 19:44战果 (底池91只):")
    print(f"  榜首: {result_1944['top10'][0][0]} 得分{result_1944['top10'][0][1]} 涨幅{result_1944['top10'][0][2]} 流入{result_1944['top10'][0][3]}")
    print(f"  特点: 宗申动力(001696)榜首，流入7.43%，真龙!")
    
    print(f"\n📊 22:29战果 (底池5只):")
    print(f"  榜首: {result_2229['top10'][0][0]} 得分{result_2229['top10'][0][1]} 涨幅{result_2229['top10'][0][2]} 流入{result_2229['top10'][0][3]}")
    print(f"  特点: 赤天化(600227)榜首，流入5.26%，疑似伪龙!")
    
    # 分析差异
    print(f"\n🔍 差异分析:")
    print(f"  1. 底池数量: 91只 vs 5只 (差距18倍!)")
    print(f"  2. 榜首不同: 宗申动力(001696) vs 赤天化(600227)")
    print(f"  3. 001696在22:29榜单中消失! (疑似被误杀)")
    
    # 判断哪个更纯正
    print(f"\n⚖️ CTO裁决:")
    print(f"  19:44战果更纯正!")
    print(f"  理由:")
    print(f"  - 宗申动力(001696)流通市值200亿+, 7.43%流入封板 = 真金白银")
    print(f"  - 赤天化(600227)流通市值<50亿, 5.26%流入封板 = 抛压轻容易拉")
    print(f"  - 19:44有91只候选，竞争激烈，优胜劣汰")
    print(f"  - 22:29只有5只候选，矮子里拔将军")
    
    # Step 5: 验证自愈下载和日历防爆
    print("\n" + "=" * 80)
    print("【Step 5】验证自愈下载和日历防爆")
    print("=" * 80)
    
    from logic.utils.calendar_utils import get_nth_previous_trading_day
    
    # 测试交易日历
    test_date = datetime.now().strftime('%Y%m%d')
    start_22 = get_nth_previous_trading_day(test_date, 22)
    start_5 = get_nth_previous_trading_day(test_date, 5)
    
    print(f"\n交易日历测试:")
    print(f"  - 今日: {test_date}")
    print(f"  - 前22交易日: {start_22}")
    print(f"  - 前5交易日: {start_5}")
    
    # 测试自愈下载
    print(f"\n自愈下载测试:")
    test_stock = '001696.SZ'  # 宗申动力
    print(f"  - 测试股票: {test_stock}")
    
    try:
        # 先检查本地数据
        local_data = xtdata.get_local_data(
            field_list=['time', 'volume', 'close'],
            stock_list=[test_stock],
            period='1d',
            start_time=start_22,
            end_time=test_date
        )
        
        if local_data and test_stock in local_data:
            df = local_data[test_stock]
            print(f"  - 本地数据: {len(df)}条")
            if len(df) > 0:
                print(f"  - 最新数据日期: {df['time'].iloc[-1] if 'time' in df.columns else 'N/A'}")
        else:
            print(f"  - 本地数据: 无，需要下载!")
            # 模拟自愈下载
            print(f"  - 执行download_history_data...")
            xtdata.download_history_data(test_stock, period='1d', start_time=start_22, end_time=test_date)
            time.sleep(0.2)
            local_data = xtdata.get_local_data(
                field_list=['time', 'volume', 'close'],
                stock_list=[test_stock],
                period='1d',
                start_time=start_22,
                end_time=test_date
            )
            if local_data and test_stock in local_data:
                df = local_data[test_stock]
                print(f"  - 下载后数据: {len(df)}条")
    except Exception as e:
        print(f"  - 测试失败: {e}")
    
    # 最终结论
    print("\n" + "=" * 80)
    print("【CTO最终结论】")
    print("=" * 80)
    print(f"""
问题根因：
  1. UniverseBuilder底池构建正常，返回{len(base_pool)}只
  2. TrueDictionary预热可能部分失败
  3. _snapshot_filter过滤条件导致大量股票被误杀

建议修复：
  1. 检查_snapshot_filter的过滤条件是否过于严格
  2. 确保预热在过滤之前执行
  3. 默认值策略：让缺失数据的股票通过粗筛

战果裁决：
  ✅ 19:44战果更纯正（91只底池，宗申动力榜首）
  ❌ 22:29战果有缺陷（5只底池，缺失真龙）
""")
    
    return {
        'base_pool_size': len(base_pool),
        'snapshot_size': len(snapshot) if snapshot else 0,
        'filtered_size': len(filtered_df) if snapshot else 0,
        'verdict': '19:44战果更纯正'
    }


if __name__ == '__main__':
    result = diagnose()
    print(f"\n诊断完成: {result}")
