#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顽主杯150票池批量特征提取脚本
CTO指令：批量提取顽主票历史起爆特征，为参数优化提供依据

系统哲学：资金为王 顺势而为 追随市场短线大哥
研究模型：A股 T+1 规则下的右侧起爆模型体系
回测系统：Tick/分K 回放 + 参数优化

修改记录：使用老板指定CSV路径读取tick数据，删除QMT依赖
data/wanzhu_data/samples/{code}_{date}_{label}.csv
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

from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.data_providers.dongcai_provider import DongCaiT1Provider
from logic.services.event_lifecycle_service import EventLifecycleService


def load_tick_from_csv(code, date, sample_dir="data/wanzhu_data/samples"):
    """
    从CSV加载tick数据（老板指定路径）
    路径格式：data/wanzhu_data/samples/{code}_{date}_{label}.csv
    
    Args:
        code: 股票代码，如 '000592'
        date: 日期，如 '2026-01-20'
        sample_dir: CSV文件目录
    
    Returns:
        (ticks列表, 数据行数)
    """
    # 尝试匹配文件
    pattern = f"{code}_{date}_*.csv"
    sample_path = Path(PROJECT_ROOT) / sample_dir
    
    matching_files = list(sample_path.glob(pattern))
    if not matching_files:
        return None, 0
    
    # 读取第一个匹配的文件
    csv_file = matching_files[0]
    
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"   ❌ 读取CSV失败: {csv_file}, 错误: {e}")
        return None, 0
    
    # 转换为tick字典列表
    ticks = []
    for _, row in df.iterrows():
        tick = {
            'time': row['time'],
            'lastPrice': row['price'],
            'price': row['price'],
            'true_change_pct': row.get('true_change_pct', 0),
            'volume': 0,  # CSV中无volume，设为0
            'amount': 0,
            'flow_5min': row.get('flow_5min', 0),  # 🔥 关键：CSV自带资金流
            'flow_15min': row.get('flow_15min', 0),
            'flow_sustainability': row.get('flow_sustainability', 1.0),
            'bidPrice': [0.0]*5,
            'askPrice': [0.0]*5,
            'bidVol': [0]*5,
            'askVol': [0]*5,
        }
        ticks.append(tick)
    
    return ticks, len(ticks)


def get_tick_from_csv(code: str, date: str) -> list:
    """
    从CSV文件读取Tick数据（老板指定路径）
    路径: data/wanzhu_data/samples/{code}_{date}_{label}.csv
    
    Args:
        code: 股票代码，如 '000592'
        date: 日期，如 '2026-01-20'
    
    Returns:
        tick列表，每个tick是dict
    """
    from pathlib import Path
    
    # 尝试多个路径（samples, samples_v2等）
    base_paths = [
        Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "samples",
        Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "samples_v2",
    ]
    
    date_str = date.replace('-', '')
    
    for base_path in base_paths:
        if not base_path.exists():
            continue
        
        # 查找匹配的文件（忽略label后缀）
        pattern = f"{code}_{date}_*.csv"
        import glob
        files = glob.glob(str(base_path / pattern))
        
        if files:
            csv_file = files[0]  # 取第一个匹配的文件
            try:
                df = pd.read_csv(csv_file)
                print(f"✅ 读取CSV: {len(df)} 行 - {Path(csv_file).name}")
                
                # 转换为tick字典列表
                ticks = []
                for _, row in df.iterrows():
                    tick = {
                        'time': row['time'],
                        'lastPrice': float(row['price']),
                        'volume': float(row.get('volume', 0)),
                        'amount': float(row.get('amount', 0)),
                        'flow_5min': row.get('flow_5min', 0),  # 🔥 关键：CSV自带资金流
                        'flow_15min': row.get('flow_15min', 0),
                        'flow_sustainability': row.get('flow_sustainability', 1.0),
                        'bidPrice': [float(row['price'])] * 5,
                        'askPrice': [float(row['price']) * 1.001] * 5,
                        'bidVol': [100] * 5,
                        'askVol': [100] * 5,
                    }
                    ticks.append(tick)
                return ticks
            except Exception as e:
                print(f"❌ 读取CSV失败: {e}")
                continue
    
    print(f"⚠️  未找到CSV: {code} {date}")
    return []


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


def get_available_dates_from_qmt(code):
    """从QMT数据目录读取实际可用的日期文件"""
    import os
    
    # 尝试SZ和SH目录
    for exchange in ['SZ', 'SH']:
        data_dir = Path(f"E:/MyQuantTool/data/qmt_data/datadir/{exchange}/0/{code}")
        if data_dir.exists():
            # 获取所有日期文件（YYYYMMDD格式）
            date_files = sorted([f.name for f in data_dir.iterdir() if f.is_file() and len(f.name) == 8])
            # 转换为YYYY-MM-DD格式
            dates = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in date_files]
            return dates
    
    return []

def get_recent_trading_days(end_date='2026-02-21', days=5):
    """
    获取最近N个交易日列表（从QMT数据目录读取实际可用日期）
    
    Args:
        end_date: 结束日期（未使用，保留参数兼容性）
        days: 交易日数量
    
    Returns:
        交易日列表 ['2026-02-17', '2026-02-18', ...]
    """
    # 使用网宿科技300017作为参考，获取所有可用日期
    all_dates = get_available_dates_from_qmt('300017')
    
    if not all_dates:
        # 备用：硬编码正确的交易日（移除春节后日期）
        all_dates = [
            '2026-01-20', '2026-01-21', '2026-01-22', '2026-01-23', 
            '2026-01-26', '2026-01-27', '2026-01-28',
            '2026-02-02', '2026-02-03', '2026-02-04', '2026-02-05',
            '2026-02-06', '2026-02-09', '2026-02-10', '2026-02-11',
            '2026-02-12', '2026-02-13'  # 春节后无数据
        ]
    
    # 取最近days天
    if len(all_dates) >= days:
        return all_dates[-days:]
    return all_dates


def extract_wanzhu_features():
    """
    批量提取顽主票特征（多日滚动回测）
    
    回测设计：
    - 时间范围：每个票最近30个交易日
    - 样本：150只票
    - 统计：日信号数（过滤前/后）、过滤率、高维持占比
    
    数据来源：老板指定CSV路径 data/wanzhu_data/samples/{code}_{date}_{label}.csv
    """
    print("="*80)
    print("顽主杯票池多日滚动回测（CSV数据源）")
    print("📁 数据源: data/wanzhu_data/samples/{code}_{date}_{label}.csv")
    print("="*80)
    
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
    
    # 🔥 测试网宿真起爆日
    trading_days = ['2026-01-26']  # 网宿真起爆日
    print(f"📅 测试日期: {trading_days[0]} (网宿科技真起爆日)")
    print()
    
    # 🔥 4只高频层泡泡票（Phase 0.6验证集）
    bubble_stocks = [
        ('300017', '网宿科技'),   # 真起爆日测试
        ('000547', '航天发展'),   # 高频层
        ('300058', '蓝色光标'),   # 高频层
        ('000592', '平潭发展'),   # 高频层
    ]
    
    # 自动扫描samples目录获取所有可用样本
    samples_dir = Path(PROJECT_ROOT) / "data/wanzhu_data/samples"
    all_csv_files = list(samples_dir.glob("*.csv"))
    
    # 提取所有样本日期（去重）
    trading_days = sorted(set([f.stem.split('_')[1] for f in all_csv_files]))
    print(f"📅 扫描到 {len(trading_days)} 个样本日期: {', '.join(trading_days[:5])}...")
    
    # 股票代码到名称的映射
    stock_name_map = {
        '300017': '网宿科技',
        '000547': '航天发展',
        '300058': '蓝色光标',
        '000592': '平潭发展',
        '002792': '通宇通讯',
        '301005': '超捷股份',
        '603516': '淳中科技',
        '603778': '国晟科技',
    }
    
    # 🔥 修复：为每只股票设置正确的pre_close（从features分析文件获取）
    stock_pre_close = {
        '300017': 10.0,   # 网宿科技
        '000547': 28.9,   # 航天发展
        '300058': 8.5,    # 蓝色光标
        '000592': 4.2,    # 平潭发展
        '002792': 15.3,   # 通宇通讯
        '301005': 12.8,   # 超捷股份
        '603516': 22.5,   # 淳中科技
        '603778': 18.2,   # 国晟科技
    }
    
    # 多日滚动统计
    total_stock_days = 0
    total_signals_before = 0
    total_signals_after = 0
    high_sustain_days = 0
    filtered_count = 0
    passed_count = 0
    
    # 存储每日详细结果
    daily_results = []
    all_features = []
    
    # 🔥 改为直接遍历所有CSV样本文件
    csv_samples = []
    for csv_file in all_csv_files:
        # 解析文件名: {code}_{date}_{label}.csv
        parts = csv_file.stem.split('_')
        if len(parts) >= 3:
            code = parts[0]
            date = parts[1]
            label = '_'.join(parts[2:])  # true 或 trap
            name = stock_name_map.get(code, '未知')
            csv_samples.append({
                'code': code,
                'name': name,
                'date': date,
                'label': label,
                'path': csv_file
            })
    
    print(f"🫧 扫描到 {len(csv_samples)} 个CSV样本")
    
    # 遍历所有CSV样本
    for idx, sample in enumerate(csv_samples):
        code = sample['code']
        name = sample['name']
        date_str = sample['date']
        label = sample['label']
        
        print(f"\n🔍 处理第 {idx+1}/{len(csv_samples)} 个: {code} - {name} ({date_str} {label})")
        
        try:
                # 格式化股票代码
                formatted_code = f"{code}.SH" if code.startswith(('60', '68')) else f"{code}.SZ"
                
                # 直接从CSV加载tick数据（老板指定路径）
                print(f"   📊 加载 {date_str} CSV数据...")
                ticks, tick_count = load_tick_from_csv(code, date_str)
                
                if tick_count < 100:
                    print(f"   ⚠️  {date_str} 无CSV数据或数据太少，跳过")
                    continue
                
                # 🔥 使用对应股票的pre_close
                pre_close = stock_pre_close.get(code, 10.0)
                
                print(f"   ✅ CSV Tick数据: {tick_count} 行, pre_close={pre_close:.2f} ({name})")
                
                # 创建统一战法核心
                print(f"   ⚔️ 初始化UnifiedWarfareCore...")
                warfare_core = UnifiedWarfareCore()
                
                # 🔥 回灌ratio化策略：启用所有检测器（实盘配置）
                # warfare_core.disable_warfare('halfway_breakout')  # 不禁用
                # warfare_core.disable_warfare('opening_weak_to_strong')  # 不禁用
                print(f"   🎯 启用策略: 全部战法（Halfway+Leader+DipBuy+Opening）")
                print(f"   📋 当前激活检测器: {warfare_core.get_active_detectors()}")
                
                # 🔥 回灌实盘ratio参数（file:2 三漏斗标准）
                for detector_name in warfare_core.get_active_detectors():
                    detector = warfare_core.event_manager.detectors.get(detector_name)
                    if detector:
                        if hasattr(detector, 'breakout_strength'):
                            detector.breakout_strength = 0.01  # Level 1: ratio >1%
                        if hasattr(detector, 'volume_surge'):
                            detector.volume_surge = 1.5        # 50%放量
                        if hasattr(detector, 'confidence_threshold'):
                            detector.confidence_threshold = 0.3  # 30%置信度
                        print(f"   ⚙️  {detector_name}: breakout_strength=0.01 (ratio化回灌)")
                
                # 创建基础资金流提供者
                dongcai_provider = DongCaiT1Provider()
                
                # 初始化累计变量
                total_net_inflow = 0
                prev_close = pre_close  # 用作计算涨幅的基准
                daily_high = 0          # 记录当日最高价
                event_count = 0
                key_moments = []        # 记录关键时刻
                
                last_tick = None
                processed_count = 0     # 处理计数器
                current_price = 0
                price_change_pct = 0
                
                # 处理tick数据（直接迭代CSV加载的ticks）
                for tick in ticks:
                    processed_count += 1
                    
                    # 获取时间（CSV中已是字符串格式 HH:MM:SS）
                    time_str = tick['time']
                    readable_time = time_str
                    
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
                            timestamp=datetime.now().timestamp(),
                            confidence=0.5,
                            source='Default'
                        )
                    
                    # 🔥 使用CSV自带的flow_5min作为资金流（CSV有flow_5min列）
                    flow_5min = tick.get('flow_5min', 0)
                    inferred_flow = {
                        'main_net_inflow': flow_5min,
                        'super_large_net': flow_5min * 0.4,
                        'large_net': flow_5min * 0.6,
                        'confidence': 0.8,
                    }
                    
                    # 累加资金流
                    total_net_inflow += flow_5min
                    
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
                        'pre_close': prev_close,  # 🔥 关键：传入昨收价
                        'main_net_inflow': inferred_flow['main_net_inflow'],
                        'super_large_net_inflow': inferred_flow['super_large_net'],
                        'large_net_inflow': inferred_flow['large_net'],
                        'flow_confidence': inferred_flow['confidence'],
                        'total_net_inflow': total_net_inflow,
                        'price_change_pct': price_change_pct,
                        'daily_high': daily_high,
                    }
                    
                    # 送入实盘战法核心引擎
                    events = warfare_core.process_tick(tick, context)
                    
                    if events:
                        for event in events:
                            event_count += 1
                            print(f"   🎯 [{readable_time}] 事件: {event['event_type']}, "
                                  f"涨幅: {price_change_pct:.2f}%, 单时净流: {inferred_flow['main_net_inflow']:.0f}, "
                                  f"累计净流: {total_net_inflow:.0f}")
                            
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
                            print(f"   💰 [{readable_time}] 关键涨幅{price_change_pct:.2f}% + "
                                  f"大额资金流入: {inferred_flow['main_net_inflow']:.0f}")
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
                
                print(f"   ✅ Tick处理完成: {processed_count} 个tick, {event_count} 个事件")
                
                # 统计信号数（过滤前）
                total_signals_before += event_count
                
                # ========== EventLifecycleService过滤器 ==========
                sustain_score = 0
                env_score = 0
                is_true_breakout = False
                
                if event_count > 0:
                    print(f"   🔍 运行EventLifecycleService分析...")
                    lifecycle = lifecycle_service.analyze(code, date_str)
                    
                    sustain_score = lifecycle.get('sustain_score', 0)
                    env_score = lifecycle.get('env_score', 0)
                    is_true_breakout = lifecycle.get('is_true_breakout', False)
                    
                    print(f"   📊 维持分: {sustain_score:.2f}, 环境分: {env_score:.2f}, 预测: {is_true_breakout}")
                    
                    # 统计高维持
                    if sustain_score >= 0.5:
                        high_sustain_days += 1
                    
                    # 过滤器检查
                    if sustain_score < 0.5 or env_score < 0.6:
                        print(f"   ⚠️  过滤器：跳过（维持分={sustain_score:.2f}<0.5 或 环境分={env_score:.2f}<0.6）")
                        filtered_count += 1
                    else:
                        print(f"   ✅ 过滤器通过")
                        passed_count += 1
                        total_signals_after += event_count
                else:
                    # 无信号，视为被过滤
                    filtered_count += 1
                # ========== 过滤器结束 ==========
                
                # 记录每日结果
                daily_results.append({
                    'code': code,
                    'name': name,
                    'date': date_str,
                    'signals_before': event_count,
                    'signals_after': event_count if (sustain_score >= 0.5 and env_score >= 0.6) else 0,
                    'sustain_score': sustain_score,
                    'env_score': env_score,
                    'is_true_breakout': is_true_breakout,
                    'tick_count': tick_count
                })
                
                # 记录这只股票的特征
                stock_features = {
                    'code': code,
                    'name': name,
                    'date': date_str,
                    'total_ticks': tick_count,
                    'total_events': event_count,
                    'total_net_inflow': total_net_inflow,
                    'final_price': current_price,
                    'final_change_pct': price_change_pct,
                    'sustain_score': sustain_score,
                    'env_score': env_score,
                    'is_true_breakout': is_true_breakout,
                    'key_moments': key_moments
                }
                
                all_features.append(stock_features)
                
                if event_count > 0:
                    print(f"   📊 关键特征: 累计净流入 {total_net_inflow:.0f}, 最终涨幅 {price_change_pct:.2f}%")
                
        except Exception as e:
            print(f"   ❌ 处理 {date_str} 失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 🔥 即使失败也要记录到报告（标记为失败）
            failed_features = {
                'code': code,
                'name': name,
                'date': date_str,
                'total_ticks': 0,
                'total_events': 0,
                'total_net_inflow': 0,
                'final_price': 0,
                'final_change_pct': 0,
                'sustain_score': 0,
                'env_score': 0,
                'is_true_breakout': False,
                'key_moments': [],
                'error': str(e)
            }
            all_features.append(failed_features)
            continue
    
    # 保存特征结果
    if all_features:
        output_file = Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "wanzhu_features_analysis_csv_v2.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_features, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n" + "="*80)
        print("多日滚动回测完成")
        print("="*80)
        print(f"📊 总票日数: {total_stock_days} (3票 × {len(trading_days)}天)")
        print(f"📊 过滤前信号: {total_signals_before} 个")
        print(f"📊 过滤后信号: {total_signals_after} 个")
        if total_signals_before > 0:
            print(f"📊 过滤率: {(1-total_signals_after/total_signals_before)*100:.1f}%")
        if total_stock_days > 0:
            print(f"📊 高维持占比: {high_sustain_days/total_stock_days*100:.1f}%")
        print(f"📁 结果保存: {output_file}")
        
        # 多日滚动统计报告
        print(f"\n【多日滚动统计】")
        print(f"📅 回测时间范围: {trading_days[0]} 至 {trading_days[-1]}")
        if len(trading_days) > 0:
            print(f"📈 日均信号数(过滤前): {total_signals_before/len(trading_days):.1f} 个/天")
            print(f"📈 日均信号数(过滤后): {total_signals_after/len(trading_days):.1f} 个/天")
        
        # 按日期分组统计
        df_results = pd.DataFrame(daily_results)
        if not df_results.empty:
            print(f"\n【按日期统计】")
            for date in trading_days:
                day_data = df_results[df_results['date'] == date]
                if not day_data.empty:
                    signals_before = day_data['signals_before'].sum()
                    signals_after = day_data['signals_after'].sum()
                    print(f"  {date}: 过滤前{signals_before}个, 过滤后{signals_after}个")
        
        # 分层统计
        sustain_high = [s for s in all_features if s.get('sustain_score', 0) >= 0.5]
        env_high = [s for s in all_features if s.get('env_score', 0) >= 0.6]
        both_high = [s for s in all_features if s.get('sustain_score', 0) >= 0.5 and s.get('env_score', 0) >= 0.6]
        
        print(f"\n【分层统计】")
        if len(all_features) > 0:
            print(f"📊 sustain≥0.5: {len(sustain_high)} 票日 ({len(sustain_high)/len(all_features)*100:.1f}%)")
            print(f"📊 env≥0.6: {len(env_high)} 票日 ({len(env_high)/len(all_features)*100:.1f}%)")
            print(f"📊 双高(真起爆): {len(both_high)} 票日 ({len(both_high)/len(all_features)*100:.1f}%)")
        
        # 保存CSV报告
        csv_file = Path(PROJECT_ROOT) / "data" / "wanzhu_data" / "wanzhu_rolling_backtest_report.csv"
        df_report = pd.DataFrame(all_features)
        df_report.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"\n📁 CSV报告: {csv_file}")
    else:
        print(f"\n⚠️ 无有效数据")
    
    print("="*80)


def main():
    extract_wanzhu_features()


if __name__ == "__main__":
    main()