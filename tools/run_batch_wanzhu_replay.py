#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主杯150票池批量特征提取脚本
CTO指令：批量提取顽主票历史起爆特征，为参数优化提供依据

系统哲学：资金为王 顺势而为 追随市场短线大哥
研究模型：A股 T+1 规则下的右侧起爆模型体系
回测系统：Tick/分K 回放 + 参数优化
"""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.data_providers.dongcai_provider import DongCaiT1Provider
from logic.services.event_lifecycle_service import EventLifecycleService
from logic.services.data_service import data_service

# QMT连接检查
def check_qmt_connection():
    """检查QMT连接状态"""
    try:
        from xtquant import xtdata
        # 尝试获取市场数据，验证连接
        test_data = xtdata.get_stock_list('沪深A股')
        if test_data and len(test_data) > 0:
            print("✅ QMT连接正常")
            return True
        else:
            print("❌ QMT未连接或数据异常")
            return False
    except Exception as e:
        print(f"❌ QMT连接检查失败: {e}")
        return False


def infer_flow_from_historical_tick(tick_data, base_signal, last_tick_data=None):
    """
    专门为历史Tick数据设计的资金流推断函数
    """
    # 提取历史tick数据字段
    last_price = tick_data.get('lastPrice', 0)
    volume = tick_data.get('volume', 0)
    amount = tick_data.get('amount', 0)
    bid_vol = tick_data.get('bidVol', [0]*5)
    ask_vol = tick_data.get('askVol', [0]*5)
    
    # 从上一个tick计算成交量增量
    volume_delta = volume
    if last_tick_data and 'volume' in last_tick_data:
        volume_delta = volume - last_tick_data['volume']
    
    # 计算买卖盘总和
    total_bid_vol = sum(bid_vol)
    total_ask_vol = sum(ask_vol)
    
    # 使用价格强度和挂单压力来推断资金流向
    if last_tick_data and 'lastPrice' in last_tick_data:
        price_change = last_price - last_tick_data['lastPrice']
        price_change_ratio = price_change / last_tick_data['lastPrice'] if last_tick_data['lastPrice'] > 0 else 0
    else:
        price_change_ratio = 0
        price_change = 0
    
    # 根据价格变化方向和买卖盘情况推断资金流向
    if volume_delta > 0:
        # 如果价格上涨，倾向于认为是主买
        if price_change > 0:
            main_flow = volume_delta * last_price * 100 * (1 + abs(price_change_ratio))
        # 如果价格下跌，倾向于认为是主卖
        elif price_change < 0:
            main_flow = volume_delta * last_price * 100 * (-1 - abs(price_change_ratio))
        # 如果价格不变，根据买卖盘压力判断
        else:
            if total_bid_vol > total_ask_vol:
                main_flow = volume_delta * last_price * 100 * 0.1  # 轻微买入倾向
            else:
                main_flow = volume_delta * last_price * 100 * -0.1  # 轻微卖出倾向
    else:
        main_flow = 0  # 无成交量变化时，资金流为0
    
    # 基于买卖盘比例计算压力
    total_vol = total_bid_vol + total_ask_vol
    if total_vol > 0:
        bid_pressure = total_bid_vol / total_vol
    else:
        bid_pressure = 0.5  # 无挂单时中性
    
    # 计算置信度
    base_confidence = base_signal.confidence if base_signal else 0.5
    volume_factor = max(0.5, min(1.0, volume_delta / 100000 if volume_delta > 0 else 0.1))
    price_factor = min(1.0, abs(price_change_ratio) * 10)
    pressure_factor = abs(bid_pressure - 0.5) * 2
    
    confidence = base_confidence * 0.4 + volume_factor * 0.2 + price_factor * 0.2 + pressure_factor * 0.2
    confidence = max(0.3, min(0.7, confidence))  # 限制在合理范围
    
    return {
        'main_net_inflow': main_flow,
        'super_large_net': main_flow * 0.4,
        'large_net': main_flow * 0.6,
        'confidence': confidence,
        'flow_direction': 'INFLOW' if main_flow > 0 else 'OUTFLOW'
    }


def extract_wanzhu_features():
    """
    批量提取顽主票特征（Phase 0.6: 集成EventLifecycleService过滤器）
    """
    print("="*80)
    print("顽主杯150票池批量特征提取 - Phase 0.6")
    print("新增：EventLifecycleService过滤器（sustain≥0.5, env≥0.6）")
    print("="*80)
    
    # 检查QMT连接
    if not check_qmt_connection():
        print("⚠️  QMT未连接，尝试继续运行（可能使用离线数据）")
    
    # 加载顽主票池
    wanzhu_file = Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "processed" / "wanzhu_selected_150.csv"
    if not wanzhu_file.exists():
        print(f"❌ 顽主票池文件不存在: {wanzhu_file}")
        return
    
    df = pd.read_csv(wanzhu_file)
    print(f"📊 加载顽主票池: {len(df)} 只股票")
    
    # 初始化EventLifecycleService
    lifecycle_service = EventLifecycleService()
    print("✅ EventLifecycleService过滤器已启用")
    print("   过滤阈值: sustain≥0.5, env≥0.6")
    print()
    
    # 处理150只全量
    sample_stocks = df.head(150)
    
    # 存储特征结果
    all_features = []
    filtered_count = 0
    passed_count = 0
    
    for idx, row in sample_stocks.iterrows():
        code = str(row['code']).zfill(6)  # 补齐6位
        name = row['name']
        print(f"\n🔍 处理第 {idx+1} 只: {code} - {name}")
        
        # 使用CSV中的真实起爆日（CTO建议：唯一event_date保证样本纯度）
        import datetime
        date_str = str(row.get('event_date', '2026-01-20'))  # 优先使用event_date列
        formatted_date = date_str.replace('-', '')
        
        try:
            # 格式化股票代码
            formatted_code = f"{code}.SH" if code.startswith(('60', '68')) else f"{code}.SZ"
            
            # 获取pre_close（CTO建议：从xtdata.get_local_data(period='1d')获取前日收盘）
            try:
                from xtquant import xtdata
                pre_close_data = xtdata.get_local_data(
                    field_list=['close'],
                    stock_list=[formatted_code],
                    period='1d',
                    start_time=formatted_date,
                    end_time=formatted_date,
                    count=2  # 获取2天数据，取前一天的close
                )
                if pre_close_data and 'close' in pre_close_data and formatted_code in pre_close_data['close'].index:
                    close_series = pre_close_data['close'].loc[formatted_code]
                    if len(close_series) >= 2:
                        pre_close = float(close_series.iloc[-2])  # 前一日收盘价
                    else:
                        pre_close = float(close_series.iloc[-1])  # 只有一天数据则用当日
                    print(f"   📊 昨收价: {pre_close} (from xtdata 1d)")
                else:
                    # fallback到DataService
                    pre_close = data_service.get_pre_close(code, date_str)
                    if pre_close <= 0:
                        pre_close = 10.0
                        print(f"   ⚠️  无法获取昨收，使用默认值10.0")
                    else:
                        print(f"   📊 昨收价: {pre_close} (from DataService)")
            except Exception as e:
                pre_close = 10.0
                print(f"   ⚠️  获取昨收失败: {e}，使用默认值10.0")
            
            # 创建历史数据提供者
            start_time = f"{formatted_date}093000"
            end_time = f"{formatted_date}150000"
            
            print(f"   📊 加载 {date_str} 历史Tick数据...")
            provider = QMTHistoricalProvider(
                stock_code=formatted_code,
                start_time=start_time,
                end_time=end_time,
                period='tick'
            )
            
            # 创建统一战法核心（CTO建议：顽主杯核心战法是Leader+TrueAttack，不用Halfway/Opening）
            print(f"   ⚔️ 初始化UnifiedWarfareCore...")
            warfare_core = UnifiedWarfareCore()
            
            # 禁用非顽主杯策略（Halfway和Opening），使用正确API
            warfare_core.disable_warfare('halfway_breakout')
            warfare_core.disable_warfare('opening_weak_to_strong')
            print(f"   🎯 启用策略: Leader + TrueAttack (顽主杯核心，已禁用Halfway/Opening)")
            print(f"   📋 当前激活检测器: {warfare_core.get_active_detectors()}")
            
            # 适度放宽参数，确保能检测到事件但不要过于宽松
            for detector_name in warfare_core.get_active_detectors():
                detector = warfare_core.event_manager.detectors.get(detector_name)
                if detector:
                    if hasattr(detector, 'breakout_strength'):
                        detector.breakout_strength = 0.005  # 0.5%推升
                    if hasattr(detector, 'volume_surge'):
                        detector.volume_surge = 1.2         # 20%放量
                    if hasattr(detector, 'confidence_threshold'):
                        detector.confidence_threshold = 0.3  # 30%置信度
            
            # 创建基础资金流提供者
            dongcai_provider = DongCaiT1Provider()
            
            # 初始化累计资金流
            total_net_inflow = 0
            prev_close = 0  # 用作计算涨幅的基准
            daily_high = 0  # 记录当日最高价
            event_count = 0
            key_moments = []  # 记录关键时刻
            
            last_tick = None
            tick_count = 0
            
            for tick in provider.iter_ticks():
                tick_count += 1
                
                # 获取时间
                time_str = tick['time']
                readable_time = datetime.datetime.fromtimestamp(int(time_str) / 1000).strftime('%H:%M:%S')
                
                # 获取基础资金流信号
                try:
                    base_signal = dongcai_provider.get_realtime_flow(code)
                except:
                    from logic.data_providers.base import CapitalFlowSignal
                    base_signal = CapitalFlowSignal(
                        code=code,
                        main_net_inflow=0,
                        super_large_inflow=0,
                        large_inflow=0,
                        timestamp=datetime.datetime.now().timestamp(),
                        confidence=0.5,
                        source='Default'
                    )
                
                # 使用历史数据推断算法
                inferred_flow = infer_flow_from_historical_tick(tick, base_signal, last_tick)
                
                # 累加资金流
                total_net_inflow += inferred_flow['main_net_inflow']
                
                # 使用前面获取的pre_close计算涨幅
                if prev_close == 0:
                    prev_close = pre_close  # 使用从DataService获取的昨收价
                
                # 计算当日涨幅
                current_price = tick['lastPrice']
                price_change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                
                # 更新当日最高价
                if current_price > daily_high:
                    daily_high = current_price
                
                # 组装 Context
                context = {
                    'stock_code': formatted_code,
                    'date': date_str,
                    'main_net_inflow': inferred_flow['main_net_inflow'],
                    'super_large_net_inflow': inferred_flow['super_large_net'],
                    'large_net_inflow': inferred_flow['large_net'],
                    'flow_confidence': inferred_flow['confidence'],
                    'total_net_inflow': total_net_inflow,  # 累计资金流
                    'price_change_pct': price_change_pct,  # 当日涨幅
                    'daily_high': daily_high,  # 当日最高价
                }

                # 送入实盘战法核心引擎
                events = warfare_core.process_tick(tick, context)

                if events:
                    for event in events:
                        event_count += 1
                        print(f"   🎯 [{readable_time}] 事件: {event['event_type']}, 涨幅: {price_change_pct:.2f}%, 单时净流: {inferred_flow['main_net_inflow']:.0f}, 累计净流: {total_net_inflow:.0f}")
                        
                        # 记录事件特征
                        key_moments.append({
                            'time': readable_time,
                            'event_type': event['event_type'],
                            'price': current_price,
                            'price_change_pct': price_change_pct,
                            'instant_flow': inferred_flow['main_net_inflow'],
                            'total_flow': total_net_inflow,
                            'volume': tick['volume'],
                            'confidence': event['confidence'],
                            'description': event.get('description', 'N/A')
                        })
                
                # 检查关键涨幅关口
                if abs(price_change_pct - 5.0) < 0.5 or abs(price_change_pct - 8.0) < 0.5 or \
                   abs(price_change_pct - 10.0) < 0.5 or abs(price_change_pct - 15.0) < 0.5:
                    # 单笔资金净流入超过3000万
                    if abs(inferred_flow['main_net_inflow']) > 30000000:
                        print(f"   💰 [{readable_time}] 关键涨幅{price_change_pct:.2f}% + 大额资金流入: {inferred_flow['main_net_inflow']:.0f}")
                        key_moments.append({
                            'time': readable_time,
                            'event_type': 'KEY_LEVEL_BULK_FLOW',
                            'price': current_price,
                            'price_change_pct': price_change_pct,
                            'instant_flow': inferred_flow['main_net_inflow'],
                            'total_flow': total_net_inflow,
                            'volume': tick['volume'],
                            'confidence': inferred_flow['confidence'],
                            'description': f'涨幅{price_change_pct:.2f}%关键点资金异动'
                        })
                
                last_tick = tick
            
            print(f"   ✅ 处理完成: {tick_count} 个tick, {event_count} 个事件")
            
            # ========== 新增：EventLifecycleService过滤器 ==========
            if event_count > 0:
                print(f"   🔍 运行EventLifecycleService分析...")
                lifecycle = lifecycle_service.analyze(code, date_str)
                
                sustain_score = lifecycle.get('sustain_score', 0)
                env_score = lifecycle.get('env_score', 0)
                is_true_breakout = lifecycle.get('is_true_breakout', False)
                
                print(f"   📊 维持分: {sustain_score:.2f}, 环境分: {env_score:.2f}, 预测: {is_true_breakout}")
                
                # 过滤器检查
                if sustain_score < 0.5 or env_score < 0.6:
                    print(f"   ⚠️  过滤器：跳过（维持分={sustain_score:.2f}<0.5 或 环境分={env_score:.2f}<0.6）")
                    filtered_count += 1
                    continue
                
                print(f"   ✅ 过滤器通过")
                passed_count += 1
            else:
                sustain_score = 0
                env_score = 0
                is_true_breakout = False
            # ========== 过滤器结束 ==========
            
            # 记录这只股票的特征（包含过滤器结果）
            stock_features = {
                'code': code,
                'name': name,
                'date': date_str,
                'total_ticks': tick_count,
                'total_events': event_count,
                'total_net_inflow': total_net_inflow,
                'final_price': current_price if 'current_price' in locals() else 0,
                'final_change_pct': price_change_pct if 'price_change_pct' in locals() else 0,
                'sustain_score': sustain_score,      # 新增
                'env_score': env_score,              # 新增
                'is_true_breakout': is_true_breakout, # 新增
                'key_moments': key_moments
            }
            
            all_features.append(stock_features)
            
            if event_count > 0:
                print(f"   📊 关键特征: 累计净流入 {total_net_inflow:.0f}, 最终涨幅 {price_change_pct:.2f}%")
        
        except Exception as e:
            print(f"   ❌ 处理失败: {e}")
            continue
    
    # 保存特征结果
    if all_features:
        output_file = Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "wanzhu_features_analysis_phase06.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_features, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n" + "="*80)
        print("Phase 0.6 顽主杯回测完成")
        print("="*80)
        print(f"📊 处理股票: {len(all_features)} 只")
        print(f"📊 过滤前信号: {filtered_count + passed_count} 个")
        print(f"📊 过滤后信号: {passed_count} 个")
        print(f"📊 过滤率: {filtered_count/(filtered_count + passed_count)*100:.1f}%" if (filtered_count + passed_count) > 0 else "📊 过滤率: N/A")
        print(f"📁 结果保存: {output_file}")
        
        # 汇总报告
        total_events = sum([stock['total_events'] for stock in all_features])
        avg_sustain = sum([stock.get('sustain_score', 0) for stock in all_features]) / len(all_features) if all_features else 0
        avg_env = sum([stock.get('env_score', 0) for stock in all_features]) / len(all_features) if all_features else 0
        
        print(f"\n【特征统计】")
        print(f"📈 总事件数: {total_events}")
        print(f"📈 平均维持分: {avg_sustain:.2f}")
        print(f"📈 平均环境分: {avg_env:.2f}")
        
        # 分层统计
        true_breakouts = [s for s in all_features if s.get('is_true_breakout', False)]
        print(f"📈 真起爆预测: {len(true_breakouts)} 只 ({len(true_breakouts)/len(all_features)*100:.1f}%)")
    else:
        print(f"\n⚠️ 无通过过滤器的样本")
    
    print("="*80)


def main():
    extract_wanzhu_features()


if __name__ == "__main__":
    main()
