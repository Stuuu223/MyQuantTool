#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网宿科技（300017）A/B对比测试脚本
CTO指令：1月26日（真起爆）vs 2月13日（骗炮回落）资金特征对比

核心任务：
1. 删除np.std(returns)愚蠢波动率判断
2. 引入RollingFlow多周期资金统计（1min/5min/15min）
3. 打印资金对比表格，验证真突破vs骗炮的资金差异
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from collections import deque
import pandas as pd

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider


def get_pre_close_price(stock_code, date_str):
    """
    获取昨收价
    由于QMT Tick数据不包含preClose字段，需要从日线数据获取
    临时方案：使用已知的历史数据或从open推算
    """
    # 网宿科技（300017）的历史数据（根据老板提供的信息）
    known_prices = {
        '2026-01-26': 11.48,  # 1月23日收盘价
        '2026-02-13': 22.52,  # 2月12日收盘价（近似）
    }
    
    if date_str in known_prices:
        return known_prices[date_str]
    
    # 如果未知，返回None，后续使用open作为fallback（虽然不精确）
    return None


class RollingFlowCalculator:
    """
    多周期滚动资金流计算器
    CTO指令：替代愚蠢的单笔Tick计算，实现1min/5min/15min多周期切片
    """
    
    def __init__(self, windows=[1, 5, 15]):
        """
        初始化
        Args:
            windows: 时间窗口列表（分钟）
        """
        self.windows = windows
        # 存储tick数据：(timestamp, price, volume_delta, estimated_flow)
        self.tick_buffer = deque(maxlen=5000)
        
    def add_tick(self, tick_data, last_tick_data=None):
        """
        添加tick数据并计算资金流
        
        Returns:
            dict: 各周期资金统计
        """
        timestamp = int(tick_data['time'])
        price = tick_data['lastPrice']
        volume = tick_data['volume']
        
        # 计算成交量增量
        if last_tick_data:
            volume_delta = volume - last_tick_data['volume']
            price_change = price - last_tick_data['lastPrice']
        else:
            volume_delta = 0
            price_change = 0
        
        # 估算单笔tick资金流（简化版：价格上涨=流入，下跌=流出）
        if volume_delta > 0:
            if price_change > 0:
                estimated_flow = volume_delta * price * 100  # 主买流入
            elif price_change < 0:
                estimated_flow = -volume_delta * price * 100  # 主卖流出
            else:
                estimated_flow = 0
        else:
            estimated_flow = 0
        
        # 存储到buffer
        self.tick_buffer.append({
            'timestamp': timestamp,
            'price': price,
            'volume_delta': volume_delta,
            'estimated_flow': estimated_flow
        })
        
        # 计算各周期资金流
        return self._calculate_window_flows(timestamp)
    
    def _calculate_window_flows(self, current_timestamp):
        """计算各时间窗口的资金流"""
        results = {}
        
        for window_minutes in self.windows:
            window_ms = window_minutes * 60 * 1000
            cutoff_time = current_timestamp - window_ms
            
            # 取窗口内tick
            window_ticks = [t for t in self.tick_buffer if t['timestamp'] >= cutoff_time]
            
            if window_ticks:
                # 计算该窗口总净流入
                total_flow = sum([t['estimated_flow'] for t in window_ticks])
                total_volume = sum([t['volume_delta'] for t in window_ticks])
                avg_price = sum([t['price'] for t in window_ticks]) / len(window_ticks)
                
                # 计算价格变化
                price_change = window_ticks[-1]['price'] - window_ticks[0]['price']
                price_change_pct = (price_change / window_ticks[0]['price'] * 100) if window_ticks[0]['price'] > 0 else 0
            else:
                total_flow = 0
                total_volume = 0
                avg_price = 0
                price_change_pct = 0
            
            results[f'flow_{window_minutes}min'] = total_flow
            results[f'volume_{window_minutes}min'] = total_volume
            results[f'price_change_{window_minutes}min'] = price_change_pct
        
        return results


def analyze_single_day(stock_code, date, focus_periods):
    """
    分析单日数据
    
    Args:
        stock_code: 股票代码
        date: 日期字符串 '2026-01-26'
        focus_periods: 关注时段列表 ['09:30-10:30', '14:15-14:25']
    
    Returns:
        dict: 分析结果
    """
    print(f"\n{'='*80}")
    print(f"分析 {stock_code} @ {date}")
    print(f"{'='*80}")
    
    # 创建历史数据提供者
    start_time = f"{date.replace('-', '')}093000"
    end_time = f"{date.replace('-', '')}150000"
    
    provider = QMTHistoricalProvider(
        stock_code=stock_code,
        start_time=start_time,
        end_time=end_time,
        period='tick'
    )
    
    # 初始化滚动资金流计算器
    flow_calc = RollingFlowCalculator(windows=[1, 5, 15])
    
    # 🔥 修正：在遍历前获取昨收价
    pre_close = get_pre_close_price(stock_code, date)
    
    # 存储结果
    last_tick = None
    focus_data = []  # 关注时段的数据
    daily_stats = {
        'max_price': 0,
        'min_price': float('inf'),
        'open_price': 0,
        'pre_close': pre_close if pre_close else 0,  # 🔥 修正：使用获取到的昨收价
        'close_price': 0,
        'total_volume': 0,
        'key_moments': []
    }
    
    # 遍历tick
    tick_count = 0
    for tick in provider.iter_ticks():
        tick_count += 1
        
        time_str = tick['time']
        readable_time = datetime.fromtimestamp(int(time_str) / 1000).strftime('%H:%M:%S')
        
        # 记录开盘价
        if daily_stats['open_price'] == 0:
            daily_stats['open_price'] = tick['lastPrice']
            # 🔥 如果无法获取昨收价，使用第一笔tick的open字段作为近似（QMT的open字段可能是昨收）
            if daily_stats['pre_close'] == 0:
                daily_stats['pre_close'] = tick.get('open', tick['lastPrice'])
        
        # 更新最高最低价
        daily_stats['max_price'] = max(daily_stats['max_price'], tick['lastPrice'])
        daily_stats['min_price'] = min(daily_stats['min_price'], tick['lastPrice'])
        daily_stats['close_price'] = tick['lastPrice']
        daily_stats['total_volume'] = tick['volume']
        
        # 计算滚动资金流
        flow_results = flow_calc.add_tick(tick, last_tick)
        
        # 检查是否在关注时段
        for period in focus_periods:
            start, end = period.split('-')
            if start <= readable_time <= end:
                # 计算从日内低点起的涨幅（波段涨幅）
                band_gain = (tick['lastPrice'] - daily_stats['min_price']) / daily_stats['min_price'] * 100 if daily_stats['min_price'] > 0 else 0
                
                # 🔥 修正：计算真实涨幅（相对昨收价）
                pre_close = daily_stats['pre_close'] if daily_stats['pre_close'] > 0 else tick.get('open', tick['lastPrice'])
                true_gain = (tick['lastPrice'] - pre_close) / pre_close * 100 if pre_close > 0 else 0
                
                record = {
                    'time': readable_time,
                    'price': tick['lastPrice'],
                    'band_gain_pct': band_gain,  # 从日内低点起的涨幅（辅助指标）
                    'true_gain_pct': true_gain,  # 🔥 真实涨幅（相对昨收价，核心指标）
                    **flow_results
                }
                focus_data.append(record)
                
                # 🔥 修正：关键时刻判断使用真实涨幅（相对昨收）
                if abs(true_gain - 5.0) < 0.5 or abs(true_gain - 8.0) < 0.5 or abs(true_gain - 11.0) < 0.5 or abs(true_gain - 20.0) < 0.5:
                    daily_stats['key_moments'].append({
                        'time': readable_time,
                        'band_gain_pct': band_gain,
                        'true_gain_pct': true_gain,  # 🔥 记录真实涨幅
                        **flow_results
                    })
        
        last_tick = tick
    
    # 🔥 修正：使用昨收价计算真实涨幅
    true_change_pct = (daily_stats['close_price'] - daily_stats['pre_close']) / daily_stats['pre_close'] * 100 if daily_stats['pre_close'] > 0 else 0
    
    print(f"✅ 共处理 {tick_count} 个tick")
    print(f"📊 昨收价: {daily_stats['pre_close']:.2f}, 开盘价: {daily_stats['open_price']:.2f}")
    print(f"📊 日内低点: {daily_stats['min_price']:.2f}, 高点: {daily_stats['max_price']:.2f}")
    print(f"📊 真实涨幅(相对昨收): {true_change_pct:.2f}%")
    
    return {
        'date': date,
        'focus_data': focus_data,
        'daily_stats': daily_stats,
        'tick_count': tick_count
    }


def print_comparison_table(results_126, results_213):
    """
    打印A/B对比表格
    """
    print(f"\n{'='*100}")
    print("网宿科技 A/B对比测试结果")
    print(f"{'='*100}")
    print(f"对比组: 1月26日（真起爆） vs 2月13日（骗炮回落）")
    print(f"{'='*100}\n")
    
    # 1. 全天统计对比
    print("【一、全天统计对比】")
    print(f"{'指标':<30} {'1月26日（真起爆）':<25} {'2月13日（骗炮）':<25} {'差异':<20}")
    print("-" * 100)
    
    stats_126 = results_126['daily_stats']
    stats_213 = results_213['daily_stats']
    
    # 🔥 修正：使用昨收价计算真实涨幅
    pre_126, close_126 = stats_126['pre_close'], stats_126['close_price']
    pre_213, close_213 = stats_213['pre_close'], stats_213['close_price']
    open_126, open_213 = stats_126['open_price'], stats_213['open_price']
    
    change_126 = (close_126 - pre_126) / pre_126 * 100 if pre_126 > 0 else 0
    change_213 = (close_213 - pre_213) / pre_213 * 100 if pre_213 > 0 else 0
    
    print(f"{'昨收价':<30} {pre_126:<25.2f} {pre_213:<25.2f} {pre_126 - pre_213:<20.2f}")
    print(f"{'开盘价':<30} {open_126:<25.2f} {open_213:<25.2f} {open_126 - open_213:<20.2f}")
    print(f"{'收盘价':<30} {close_126:<25.2f} {close_213:<25.2f} {close_126 - close_213:<20.2f}")
    print(f"{'真实涨幅(相对昨收)':<30} {change_126:<25.2f}% {change_213:<25.2f}% {change_126 - change_213:<20.2f}%")
    print(f"{'日内最高':<30} {stats_126['max_price']:<25.2f} {stats_213['max_price']:<25.2f}")
    print(f"{'日内最低':<30} {stats_126['min_price']:<25.2f} {stats_213['min_price']:<25.2f}")
    print()
    
    # 2. 早盘拉升期对比（09:30-10:30）
    print("【二、早盘拉升期对比（09:30-10:30）】")
    print(f"{'时间':<10} {'真实涨幅':<12} {'1分钟资金流':<18} {'5分钟资金流':<18} {'15分钟资金流':<18} {'日期':<15}")
    print("-" * 100)
    
    # 提取早盘数据
    morning_126 = [d for d in results_126['focus_data'] if '09:30' <= d['time'] <= '10:30']
    morning_213 = [d for d in results_213['focus_data'] if '09:30' <= d['time'] <= '10:30']
    
    # 取关键时间点（每10分钟一个样本）
    key_times = ['09:35', '09:45', '09:55', '10:05', '10:15', '10:25']
    
    for t in key_times:
        # 找最接近的时间点
        data_126 = next((d for d in morning_126 if abs(int(d['time'].replace(':', '')) - int(t.replace(':', ''))) < 5), None)
        data_213 = next((d for d in morning_213 if abs(int(d['time'].replace(':', '')) - int(t.replace(':', ''))) < 5), None)
        
        if data_126:
            true_gain = data_126.get('true_gain_pct', data_126['band_gain_pct'])
            print(f"{data_126['time']:<10} {true_gain:<12.2f}% {data_126['flow_1min']/1e6:<18.2f}M {data_126['flow_5min']/1e6:<18.2f}M {data_126['flow_15min']/1e6:<18.2f}M {'1月26日':<15}")
        if data_213:
            true_gain = data_213.get('true_gain_pct', data_213['band_gain_pct'])
            print(f"{data_213['time']:<10} {true_gain:<12.2f}% {data_213['flow_1min']/1e6:<18.2f}M {data_213['flow_5min']/1e6:<18.2f}M {data_213['flow_15min']/1e6:<18.2f}M {'2月13日':<15}")
    
    print()
    
    # 3. 关键时刻对比（涨幅突破5%/8%/11%/20%时）
    print("【三、关键时刻资金特征对比（突破关键涨幅时）】")
    print(f"{'日期':<15} {'时间':<10} {'真实涨幅':<12} {'1分钟流':<15} {'5分钟流':<15} {'15分钟流':<15} {'信号判断':<15}")
    print("-" * 100)
    
    for km in results_126['daily_stats']['key_moments'][:5]:
        signal = "🟢 真突破" if km['flow_5min'] > 0 else "🔴 异常"
        true_gain = km.get('true_gain_pct', km['band_gain_pct'])  # 兼容旧数据
        print(f"{'1月26日':<15} {km['time']:<10} {true_gain:<12.2f}% {km['flow_1min']/1e6:<15.2f}M {km['flow_5min']/1e6:<15.2f}M {km['flow_15min']/1e6:<15.2f}M {signal:<15}")
    
    for km in results_213['daily_stats']['key_moments'][:5]:
        signal = "🟢 真突破" if km['flow_5min'] > 0 else "🔴 骗炮"
        true_gain = km.get('true_gain_pct', km['band_gain_pct'])  # 兼容旧数据
        print(f"{'2月13日':<15} {km['time']:<10} {true_gain:<12.2f}% {km['flow_1min']/1e6:<15.2f}M {km['flow_5min']/1e6:<15.2f}M {km['flow_15min']/1e6:<15.2f}M {signal:<15}")
    
    print()
    
    # 4. 下午点火期对比（14:15-14:25）
    print("【四、下午点火期对比（14:15-14:25）】")
    print(f"{'时间':<10} {'真实涨幅':<12} {'1分钟资金流':<18} {'5分钟资金流':<18} {'15分钟资金流':<18} {'日期':<15}")
    print("-" * 100)
    
    afternoon_126 = [d for d in results_126['focus_data'] if '14:15' <= d['time'] <= '14:25']
    afternoon_213 = [d for d in results_213['focus_data'] if '14:15' <= d['time'] <= '14:25']
    
    # 取下午关键时间点
    pm_times = ['14:15', '14:17', '14:19', '14:21', '14:23', '14:25']
    
    for t in pm_times:
        data_126 = next((d for d in afternoon_126 if abs(int(d['time'].replace(':', '')) - int(t.replace(':', ''))) < 3), None)
        data_213 = next((d for d in afternoon_213 if abs(int(d['time'].replace(':', '')) - int(t.replace(':', ''))) < 3), None)
        
        if data_126:
            true_gain = data_126.get('true_gain_pct', data_126['band_gain_pct'])
            print(f"{data_126['time']:<10} {true_gain:<12.2f}% {data_126['flow_1min']/1e6:<18.2f}M {data_126['flow_5min']/1e6:<18.2f}M {data_126['flow_15min']/1e6:<18.2f}M {'1月26日':<15}")
        if data_213:
            true_gain = data_213.get('true_gain_pct', data_213['band_gain_pct'])
            print(f"{data_213['time']:<10} {true_gain:<12.2f}% {data_213['flow_1min']/1e6:<18.2f}M {data_213['flow_5min']/1e6:<18.2f}M {data_213['flow_15min']/1e6:<18.2f}M {'2月13日':<15}")
    
    print()
    
    # 5. 关键发现总结
    print("【五、关键发现总结】")
    print("-" * 100)
    
    # 计算平均资金流
    if morning_126:
        avg_1min_126 = sum([d['flow_1min'] for d in morning_126]) / len(morning_126) / 1e6
        avg_5min_126 = sum([d['flow_5min'] for d in morning_126]) / len(morning_126) / 1e6
        avg_15min_126 = sum([d['flow_15min'] for d in morning_126]) / len(morning_126) / 1e6
    else:
        avg_1min_126 = avg_5min_126 = avg_15min_126 = 0
    
    if morning_213:
        avg_1min_213 = sum([d['flow_1min'] for d in morning_213]) / len(morning_213) / 1e6
        avg_5min_213 = sum([d['flow_5min'] for d in morning_213]) / len(morning_213) / 1e6
        avg_15min_213 = sum([d['flow_15min'] for d in morning_213]) / len(morning_213) / 1e6
    else:
        avg_1min_213 = avg_5min_213 = avg_15min_213 = 0
    
    print(f"✅ 早盘平均1分钟资金流: 1月26日 {avg_1min_126:.2f}M vs 2月13日 {avg_1min_213:.2f}M (差异: {avg_1min_126 - avg_1min_213:.2f}M)")
    print(f"✅ 早盘平均5分钟资金流: 1月26日 {avg_5min_126:.2f}M vs 2月13日 {avg_5min_213:.2f}M (差异: {avg_5min_126 - avg_5min_213:.2f}M)")
    print(f"✅ 早盘平均15分钟资金流: 1月26日 {avg_15min_126:.2f}M vs 2月13日 {avg_15min_213:.2f}M (差异: {avg_15min_126 - avg_15min_213:.2f}M)")
    print()
    print(f"🎯 结论:")
    if avg_5min_126 > avg_5min_213:
        print(f"   - 真起爆日（1.26）的5分钟滚动资金流入显著高于骗炮日（2.13），差值 {avg_5min_126 - avg_5min_213:.2f}M")
        print(f"   - 建议策略: 当5分钟滚动资金流 > {avg_5min_126 * 0.5:.2f}M 且波段涨幅在5%-11%区间时，触发真突破信号")
    else:
        print(f"   - 数据异常，需要进一步分析")
    
    print(f"{'='*100}\n")


def main():
    """主函数"""
    print("="*100)
    print("网宿科技（300017）A/B对比测试")
    print("CTO指令：1月26日（真起爆）vs 2月13日（骗炮回落）资金特征对比")
    print("="*100)
    
    stock_code = "300017.SZ"
    focus_periods = ['09:30-10:30', '14:15-14:25']  # 关注早盘和下午点火期
    
    # A组：1月26日（真起爆日）
    print("\n🟢 开始分析 A组：2026-01-26（真起爆日，最终20CM涨停）")
    results_126 = analyze_single_day(stock_code, '2026-01-26', focus_periods)
    
    # B组：2月13日（骗炮回落日）
    print("\n🔴 开始分析 B组：2026-02-13（骗炮回落日，早盘+8%后回落到+1.81%）")
    results_213 = analyze_single_day(stock_code, '2026-02-13', focus_periods)
    
    # 打印对比表格
    print_comparison_table(results_126, results_213)
    
    # 保存详细数据到CSV供进一步分析
    output_dir = Path(PROJECT_ROOT) / "data" / "wanzhu_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if results_126['focus_data']:
        df_126 = pd.DataFrame(results_126['focus_data'])
        df_126.to_csv(output_dir / "wangsu_0126_flow_analysis.csv", index=False)
        print(f"💾 1月26日详细数据已保存: {output_dir / 'wangsu_0126_flow_analysis.csv'}")
    
    if results_213['focus_data']:
        df_213 = pd.DataFrame(results_213['focus_data'])
        df_213.to_csv(output_dir / "wangsu_0213_flow_analysis.csv", index=False)
        print(f"💾 2月13日详细数据已保存: {output_dir / 'wangsu_0213_flow_analysis.csv'}")
    
    print("\n" + "="*100)
    print("✅ A/B对比测试完成")
    print("="*100)


if __name__ == "__main__":
    main()
