#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全息战场模拟器 - 历史Tick真实交易回演
================================================================

【CTO V162收官战版】三大物理关卡全息沙盘

使用方法：
    python tools/mock_live_runner.py --date 20260310 --stocks 000001.SZ,600519.SH

三大物理关卡：
    关卡1：动态滑点惩罚 - 引力弹弓/阶梯突破场景滑点×2（千2）
    关卡2：流动性拒绝 - 成交量不足时部分成交或废单
    关卡3：微观防爆确认 - 买入后价格跌破触发价时止损

物理定律：
    - 时间锁定：模拟指定交易日的完整时间流
    - 量纲统一：amount单位为元，volume单位为股
    - 真实摩擦：滑点/佣金/印花税/流动性一个不能少
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import logging

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 设置QMT虚拟环境路径
VENV_PYTHON = PROJECT_ROOT / "venv_qmt" / "Scripts" / "python.exe"

# 导入项目模块
from logic.core.config_manager import get_config_manager
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.strategies.kinetic_core_engine import KineticCoreEngine
from logic.execution.mock_execution_manager import MockExecutionManager, TriggerType, OrderStatus
from research_lab.trigger_validator import TriggerValidator

logger = logging.getLogger(__name__)


class MockLiveRunner:
    """全息战场模拟器 - 三大物理关卡"""
    
    def __init__(self, target_date: str, stock_list: List[str] = None, initial_capital: float = 100000.0):
        """
        初始化Mock运行器
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            stock_list: 股票列表，为空则使用粗筛结果
            initial_capital: 初始本金
        """
        self.target_date = target_date
        self.stock_list = stock_list or []
        self.config_mgr = get_config_manager()
        self.true_dict = get_true_dictionary()
        
        # 【CTO V162】核心组件
        self.execution_manager = MockExecutionManager(initial_capital=initial_capital, max_position_ratio=1.0)
        self.trigger_validator = TriggerValidator()
        
        # Tick队列缓存 {stock_code: List[Dict]}
        self.tick_queues: Dict[str, List[Dict]] = {}
        
        # 当前模拟时间
        self.current_time: Optional[datetime] = None
        
        # 榜单缓存
        self.leaderboard: Dict[str, Dict] = {}
        
        # 【CTO V162】分钟级成交额缓存（用于流动性检查）
        self.minute_volumes: Dict[str, Dict[str, float]] = {}  # {stock_code: {HH:MM: amount}}
        
        # 【CTO V162】买入信号记录
        self.buy_signals: List[Dict] = []
        
        logger.info(f"[MockLiveRunner] 初始化完成，目标日期={target_date}，本金=¥{initial_capital:,.0f}")
    
    def load_tick_data(self, stock_code: str) -> bool:
        """
        加载单只股票的Tick数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否成功加载
        """
        try:
            import xtquant.xtdata as xtdata
            
            # 构造Tick数据路径
            # QMT Tick路径: datadir/{SZ,SH}/0/{股票代码}/{日期}.dat
            exchange = 'SZ' if stock_code.endswith('.SZ') else 'SH'
            code_only = stock_code.split('.')[0]
            
            # 使用xtdata读取本地Tick
            tick_df = xtdata.get_local_data(
                field_list=[],  # 空列表返回所有字段
                stock_list=[stock_code], 
                period='tick', 
                start_time=f'{self.target_date}092500',
                end_time=f'{self.target_date}150000'
            )
            
            if tick_df is None or stock_code not in tick_df or tick_df[stock_code].empty:
                logger.warning(f"[MockLiveRunner] {stock_code} 无Tick数据")
                return False
            
            # 获取该股票的DataFrame
            df = tick_df[stock_code]
            
            # 转换为Tick队列
            tick_list = []
            for idx, row in df.iterrows():
                try:
                    # 【CTO V75防御性编程】提前验证时间戳有效性
                    raw_time = row.get('time', 0)
                    # 触发时间戳解析验证（不使用返回值，只验证是否有效）
                    _ = self._parse_tick_time(raw_time)
                    
                    tick = {
                        'time': raw_time,
                        'price': float(row.get('lastPrice', row.get('price', 0))),
                        'volume': int(row.get('volume', 0)),
                        'amount': float(row.get('amount', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'open': float(row.get('open', 0)),
                        'lastClose': float(row.get('lastClose', row.get('preClose', 0))),
                        'limitUpPrice': float(row.get('limitUpPrice', 0)),
                        'limitDownPrice': float(row.get('limitDownPrice', 0)),
                        'askPrice1': float(row.get('askPrice1', 0)),
                        'bidPrice1': float(row.get('bidPrice1', 0)),
                    }
                    # 只有有效Tick才加入
                    if tick['amount'] > 0 and tick['price'] > 0:
                        tick_list.append(tick)
                except Exception as e:
                    # 【CTO防线】遇到脏数据Tick物理跳过，不阻塞系统
                    continue
            
            self.tick_queues[stock_code] = tick_list
            logger.info(f"[MockLiveRunner] {stock_code} 加载{len(tick_list)}个Tick")
            return True
            
        except Exception as e:
            logger.error(f"[MockLiveRunner] {stock_code} 加载Tick失败: {e}")
            return False
    
    def run_mock_session(self):
        """
        运行Mock交易时段 - 【CTO V162】三大物理关卡全息沙盘
        
        模拟完整的交易时段：
        - 09:25 竞价结束
        - 09:30-11:30 早盘
        - 11:30-13:00 午休
        - 13:00-15:00 午盘
        """
        print(f"\n{'='*70}")
        print(f"[全息战场模拟器] CTO V162 三大物理关卡 - {self.target_date}")
        print(f"{'='*70}")
        print(f"[关卡1] 动态滑点: 基准千1 → 活跃场景千2")
        print(f"[关卡2] 流动性拒绝: 买入金额 > 33%该分钟成交额时拒绝")
        print(f"[关卡3] 微观防爆: 3分钟内破位+MFE<0.5触发止损")
        print(f"{'='*70}\n")
        
        # 加载所有股票的Tick数据
        loaded_count = 0
        for stock_code in self.stock_list:
            if self.load_tick_data(stock_code):
                loaded_count += 1
        
        if loaded_count == 0:
            print("[MockLiveRunner] 错误：没有成功加载任何Tick数据")
            return
        
        print(f"[MockLiveRunner] 成功加载 {loaded_count}/{len(self.stock_list)} 只股票\n")
        
        # 模拟时间轴
        # 时间锚点 - 更密集的交易检查
        time_anchors = [
            ('09:25:00', '竞价结束'),
            ('09:30:00', '开盘'),
            ('09:35:00', '开盘5分钟'),
            ('09:45:00', '开盘15分钟'),
            ('10:00:00', '早盘第一小时'),
            ('10:30:00', '早盘中期'),
            ('11:00:00', '早盘后期'),
            ('11:30:00', '早盘结束'),
            ('13:00:00', '午盘开盘'),
            ('13:30:00', '午盘中期'),
            ('14:00:00', '午盘后期'),
            ('14:30:00', '尾盘前期'),
            ('14:45:00', '尾盘'),
            ('15:00:00', '收盘'),
        ]
        
        prev_time = None
        
        # 遍历时间锚点
        for time_str, event_name in time_anchors:
            current_time = datetime.strptime(f"{self.target_date}{time_str}", "%Y%m%d%H:%M:%S")
            
            print(f"\n⏰ [{time_str}] {event_name}")
            print("-" * 50)
            
            # 在每个时间点计算当前榜单
            self._calculate_leaderboard_at_time(current_time)
            
            # 【CTO V162】核心：检查买点触发
            self._check_triggers_and_execute(current_time, prev_time)
            
            # 【CTO V162】持仓监控：检查微观防爆
            self._monitor_positions(current_time)
            
            # 打印当前榜单
            self._print_leaderboard()
            
            # 打印当前持仓
            self._print_positions()
            
            prev_time = current_time
        
        # 收盘：强制平仓所有持仓
        self._close_all_positions()
        
        # 【CTO V162】输出最终绩效报告
        self._print_final_report()
        
        print(f"\n{'='*70}")
        print(f"[全息战场模拟器] 回演结束")
        print(f"{'='*70}\n")
    
    def _calculate_leaderboard_at_time(self, target_time: datetime):
        """
        在指定时间点计算榜单
        
        Args:
            target_time: 目标时间
        """
        self.leaderboard.clear()
        
        minutes_passed = self._get_minutes_passed(target_time)
        
        for stock_code, tick_list in self.tick_queues.items():
            # 找到目标时间点之前最后一个Tick
            current_tick = None
            for tick in tick_list:
                tick_time = self._parse_tick_time(tick['time'])
                if tick_time <= target_time:
                    current_tick = tick
                else:
                    break
            
            if current_tick is None:
                continue
            
            # 计算累计成交额
            total_amount = 0.0
            for tick in tick_list:
                tick_time = self._parse_tick_time(tick['time'])
                if tick_time <= target_time:
                    # 注意：amount可能是累计值也可能是单笔值
                    # QMT Tick的amount通常是累计值
                    total_amount = tick['amount']
            
            # 调用核心打分引擎
            try:
                # 创建引擎实例并调用
                engine = KineticCoreEngine()
                # 【CTO V76修复】引擎返回tuple(final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe)
                # 参数需要current_time(datetime)而非target_date(str)
                result = engine.calculate_true_dragon_score(
                    net_inflow=current_tick['amount'] * 0.5,  # 简化：假设50%是净流入
                    price=current_tick['price'],
                    prev_close=current_tick['lastClose'],
                    high=current_tick['high'],
                    low=current_tick['low'],
                    open_price=current_tick['open'],
                    flow_5min=total_amount / max(minutes_passed, 1) * 5,  # 估算5分钟流入
                    flow_15min=total_amount / max(minutes_passed, 1) * 15,  # 估算15分钟流入
                    flow_5min_median_stock=5000000,  # 默认历史中位数
                    space_gap_pct=10.0,  # 默认空间差
                    float_volume_shares=1000000000,  # 默认流通盘10亿股
                    current_time=target_time,  # 【修复】datetime对象
                    total_amount=total_amount,
                    total_volume=int(total_amount / current_tick['price']) if current_tick['price'] > 0 else 0,
                    limit_up_queue_amount=0,
                    mode='scan',
                    stock_code=stock_code
                )
                
                # 【修复】返回类型是tuple: (final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe)
                if isinstance(result, tuple) and len(result) >= 5:
                    score, sustain_ratio, inflow_ratio, ratio_stock, mfe = result[0], result[1], result[2], result[3], result[4]
                    self.leaderboard[stock_code] = {
                        'score': score,
                        'price': current_tick['price'],
                        'amount': total_amount,
                        'mfe': mfe,
                        'sustain_ratio': sustain_ratio,
                        'inflow_ratio': inflow_ratio,
                        'tick': current_tick
                    }
                    
            except Exception as e:
                logger.warning(f"[MockLiveRunner] {stock_code} 打分失败: {e}")
    
    def _get_minutes_passed(self, current_time: datetime) -> int:
        """计算开盘后经过的分钟数"""
        open_time = datetime.strptime(f"{self.target_date}09:30:00", "%Y%m%d%H:%M:%S")
        if current_time <= open_time:
            return 0
        
        # 午休时间扣除
        morning_end = datetime.strptime(f"{self.target_date}11:30:00", "%Y%m%d%H:%M:%S")
        afternoon_start = datetime.strptime(f"{self.target_date}13:00:00", "%Y%m%d%H:%M:%S")
        
        if current_time <= morning_end:
            # 早盘时段
            delta = current_time - open_time
            return int(delta.total_seconds() / 60)
        elif current_time <= afternoon_start:
            # 午休时段，使用早盘结束时的分钟数
            delta = morning_end - open_time
            return int(delta.total_seconds() / 60)
        else:
            # 午盘时段
            morning_delta = morning_end - open_time
            afternoon_delta = current_time - afternoon_start
            total_minutes = int(morning_delta.total_seconds() / 60) + int(afternoon_delta.total_seconds() / 60)
            return total_minutes
    
    def _parse_tick_time(self, time_val):
        """
        【CTO V75重构】物理级时间戳解析
        兼容 QMT 返回的毫秒时间戳 (int/float) 或 字符串
        """
        import pandas as pd
        from datetime import datetime
        try:
            # 1. 尝试作为数值型毫秒级时间戳解析
            if isinstance(time_val, (int, float)):
                # 如果数值很大，说明是毫秒时间戳 (如 1773072000000)
                if time_val > 1000000000000:
                    dt = pd.to_datetime(time_val, unit='ms')
                    return dt.to_pydatetime()
                # 如果是 YYYYMMDDHHMMSS 格式的整数 (如 20260311093000)
                elif time_val > 20000000000000:
                    return datetime.strptime(str(int(time_val)), "%Y%m%d%H%M%S")
                # 其他情况假设为秒级时间戳
                else:
                    dt = pd.to_datetime(time_val, unit='s')
                    return dt.to_pydatetime()
                    
            # 2. 作为字符串解析
            time_str = str(time_val).strip()
            # 如果字符串是纯数字且很长，尝试转为数值型毫秒处理
            if time_str.isdigit() and len(time_str) >= 13:
                 dt = pd.to_datetime(int(time_str), unit='ms')
                 return dt.to_pydatetime()
                 
            # 如果只包含时分秒 HHMMSS (长度为6)
            if len(time_str) == 6:
                return datetime.strptime(f"{self.target_date}{time_str}", "%Y%m%d%H%M%S")
            # 如果包含完整的 YYYYMMDDHHMMSS
            elif len(time_str) == 14:
                return datetime.strptime(time_str, "%Y%m%d%H%M%S")
            # 带有分隔符的常规格式
            else:
                return pd.to_datetime(time_str).to_pydatetime()
                
        except Exception as e:
            # 解析失败时的兜底：抛出异常让上层接管，禁止伪造时间
            raise ValueError(f"无法解析的时间戳格式: {time_val}, 错误: {e}")
    
    def _print_leaderboard(self):
        """
        【CTO V77】调用主引擎的render_live_dashboard - SSOT原则
        【CTO V78】补齐change/purity字段，添加pool_stats完整统计
        """
        from logic.utils.metrics_utils import render_live_dashboard
        
        # 构建符合render_live_dashboard格式的top_targets列表
        top_targets = []
        sorted_stocks = sorted(
            self.leaderboard.items(), 
            key=lambda x: x[1]['score'], 
            reverse=True
        )[:10]
        
        up_count = 0
        down_count = 0
        
        for code, data in sorted_stocks:
            tick = data.get('tick', {})
            prev_close = tick.get('lastClose', tick.get('prev_close', data['price']))
            price = data['price']
            high = tick.get('high', price)
            low = tick.get('low', price)
            
            # 【CTO V78】涨跌幅百分比
            change = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 【CTO V80】价格纯度 = (当前价 - 日内最低) / (日内最高 - 日内最低)
            # 反映价格在日内振幅中的位置：100%=最高点收盘，0%=最低点收盘
            price_range = high - low
            if price_range > 0:
                raw_purity = (price - low) / price_range  # 【V80修复】正确公式
            else:
                # 一字板情况：价格无波动，涨停给100%，跌停给0%
                raw_purity = 1.0 if price >= prev_close else 0.0
            purity = min(max(raw_purity * 100, 0.0), 100.0)  # 【V80修复】范围0-100%
            
            # 统计涨跌数量
            if change >= 0:
                up_count += 1
            else:
                down_count += 1
            
            top_targets.append({
                'code': code,
                'score': data['score'],
                'price': price,
                'change': change,  # 【CTO V78】字段名修正
                'inflow_ratio': data.get('inflow_ratio', 0),
                'sustain_ratio': data.get('sustain_ratio', 0),
                'mfe': data.get('mfe', 0),
                'purity': purity  # 【CTO V78】真实计算，不再硬编码0
            })
        
        # 【CTO V78】完整pool_stats统计
        pool_stats = {
            'total': len(self.tick_queues),
            'active': len(self.leaderboard),
            'passed_fine_filter': len(self.leaderboard),
            'up': up_count,
            'down': down_count
        }
        render_live_dashboard(top_targets, pool_stats=pool_stats, is_rest=True)

    # ==================== 【CTO V162】三大物理关卡核心方法 ====================
    
    def _get_minute_volume(self, stock_code: str, current_time: datetime) -> float:
        """
        获取当前分钟的成交额（用于流动性检查）
        
        Args:
            stock_code: 股票代码
            current_time: 当前时间
            
        Returns:
            该分钟成交额
        """
        tick_list = self.tick_queues.get(stock_code, [])
        if not tick_list:
            return 0.0
        
        # 找到当前分钟内的所有Tick
        current_minute_start = current_time.replace(second=0, microsecond=0)
        current_minute_end = current_minute_start + timedelta(minutes=1)
        
        # 获取前一分钟的最后一个Tick的amount作为基准
        prev_minute_end = current_minute_start
        prev_amount = 0.0
        for tick in tick_list:
            tick_time = self._parse_tick_time(tick['time'])
            if tick_time <= prev_minute_end:
                prev_amount = tick['amount']
        
        # 获取当前分钟最后一个Tick的amount
        curr_amount = prev_amount
        for tick in tick_list:
            tick_time = self._parse_tick_time(tick['time'])
            if tick_time < current_minute_end:
                curr_amount = tick['amount']
        
        # 当前分钟成交额 = 当前累计 - 上一分钟累计
        return max(0, curr_amount - prev_amount)
    
    def _check_triggers_and_execute(self, current_time: datetime, prev_time: datetime):
        """
        【CTO V162关卡核心】检查物理买点触发并执行交易
        
        Args:
            current_time: 当前时间
            prev_time: 上一个时间点
        """
        if prev_time is None:
            return
        
        # 获取榜单中分数>=50的标的
        candidates = [
            (code, data) for code, data in self.leaderboard.items()
            if data['score'] >= 50.0
        ]
        
        for stock_code, data in candidates:
            tick = data.get('tick', {})
            price = data['price']
            prev_close = tick.get('lastClose', price)
            high = tick.get('high', price)
            low = tick.get('low', price)
            open_price = tick.get('open', price)
            total_amount = data['amount']
            
            # 计算分钟级成交额
            minute_volume = self._get_minute_volume(stock_code, current_time)
            
            # 构造TriggerValidator需要的参数
            vwap = total_amount / (total_amount / price) if price > 0 and total_amount > 0 else price
            amplitude = (high - low) / prev_close * 100 if prev_close > 0 else 0
            volume_ratio = data.get('sustain_ratio', 1.0)
            mfe = data.get('mfe', 0)
            
            # 【CTO V162】调用TriggerValidator检测物理买点
            trigger_signal = self.trigger_validator.check_all_triggers(
                stock_code=stock_code,
                current_price=price,
                vwap=vwap,
                high=high,
                low=low,
                prev_close=prev_close,
                open_price=open_price,
                amplitude_pct=amplitude,
                volume_ratio=volume_ratio,
                mfe=mfe,
                minutes_passed=self._get_minutes_passed(current_time),
                tick_data=None  # 暂不传详细Tick
            )
            
            if trigger_signal is None:
                continue  # 没有触发任何买点
            
            # 【CTO V162关卡2】获取流动性数据
            minute_volume = self._get_minute_volume(stock_code, current_time)
            
            # 【CTO V162关卡1+2+3】执行买入
            success, order = self.execution_manager.place_mock_order(
                stock_code=stock_code,
                last_price=price,
                direction='BUY',
                trigger_type=trigger_signal.trigger_type,
                tick_data=tick,
                minute_volume=minute_volume
            )
            
            if success:
                self.buy_signals.append({
                    'time': current_time.strftime('%H:%M:%S'),
                    'stock': stock_code,
                    'price': price,
                    'trigger': trigger_signal.trigger_type.value,
                    'score': data['score'],
                    'mfe': mfe,
                    'sustain': volume_ratio
                })
    
    def _monitor_positions(self, current_time: datetime):
        """
        【CTO V162关卡3】监控持仓，检查微观防爆
        
        Args:
            current_time: 当前时间
        """
        positions = self.execution_manager.positions
        if not positions:
            return
        
        for stock_code, pos in list(positions.items()):
            # 获取当前价格和MFE
            tick_list = self.tick_queues.get(stock_code, [])
            current_tick = None
            for tick in tick_list:
                tick_time = self._parse_tick_time(tick['time'])
                if tick_time <= current_time:
                    current_tick = tick
                else:
                    break
            
            if current_tick is None:
                continue
            
            current_price = current_tick['price']
            high = current_tick.get('high', current_price)
            low = current_tick.get('low', current_price)
            prev_close = current_tick.get('lastClose', current_price)
            
            # 计算当前MFE
            amplitude = (high - low) / prev_close if prev_close > 0 else 0
            total_amount = current_tick['amount']
            float_volume = 1000000000  # 默认10亿股
            inflow_ratio = (total_amount * 0.5) / (float_volume * current_price) * 100
            mfe = amplitude / max(inflow_ratio, 0.01) if inflow_ratio > 0 else 0
            
            # 持仓时间（分钟）
            entry_time = datetime.strptime(pos.entry_time, '%Y-%m-%d %H:%M:%S')
            minutes_elapsed = (current_time - entry_time).total_seconds() / 60
            
            # 【CTO V162关卡3】检查微观防爆
            stopped, reason = self.execution_manager.check_micro_guard(
                stock_code, current_price, mfe, int(minutes_elapsed)
            )
            
            if stopped:
                # 执行止损卖出
                success, order = self.execution_manager.place_mock_order(
                    stock_code=stock_code,
                    last_price=current_price,
                    direction='SELL'
                )
                if success:
                    logger.warning(f"⚠️ [微观防爆止损] {stock_code}: {reason}")
    
    def _print_positions(self):
        """打印当前持仓"""
        positions = self.execution_manager.positions
        if not positions:
            return
        
        print("\n📊 当前持仓:")
        print("-" * 50)
        for code, pos in positions.items():
            pnl_pct = (pos.current_price - pos.entry_price) / pos.entry_price * 100 if pos.entry_price > 0 else 0
            print(f"  {code}: {pos.volume}股 @ {pos.entry_price:.2f} | 当前:{pos.current_price:.2f} | PnL:{pnl_pct:+.2f}%")
        print("-" * 50)
    
    def _close_all_positions(self):
        """收盘强制平仓"""
        positions = list(self.execution_manager.positions.keys())
        if not positions:
            return
        
        print("\n🔔 收盘强制平仓:")
        for stock_code in positions:
            # 用最后一个Tick的价格平仓
            tick_list = self.tick_queues.get(stock_code, [])
            if tick_list:
                last_tick = tick_list[-1]
                success, order = self.execution_manager.place_mock_order(
                    stock_code=stock_code,
                    last_price=last_tick['price'],
                    direction='SELL'
                )
    
    def _print_final_report(self):
        """【CTO V162】输出最终绩效报告"""
        report = self.execution_manager.get_performance_report()
        portfolio = self.execution_manager.get_portfolio_summary()
        
        print("\n" + "="*70)
        print("📈 全息战场模拟器 - 最终绩效报告")
        print("="*70)
        
        if 'error' in report:
            print(f"  {report['error']}")
            return
        
        print(f"\n💰 资金状况:")
        print(f"  初始本金: ¥{report['initial_capital']:,.2f}")
        print(f"  最终现金: ¥{report['final_cash']:,.2f}")
        print(f"  总买入额: ¥{report['total_buy']:,.2f}")
        print(f"  总卖出额: ¥{report['total_sell']:,.2f}")
        print(f"  总手续费: ¥{report['total_fees']:,.2f}")
        
        print(f"\n📊 绩效指标:")
        pnl = report['realized_pnl']
        pnl_pct = report['realized_pnl_pct']
        pnl_sign = "+" if pnl >= 0 else ""
        print(f"  实现盈亏: {pnl_sign}¥{pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)")
        print(f"  交易次数: {report['trade_count']}")
        print(f"  盈利次数: {report['win_count']}")
        print(f"  亏损次数: {report['loss_count']}")
        
        if report['trade_count'] > 0:
            win_rate = report['win_count'] / (report['win_count'] + report['loss_count']) * 100 if (report['win_count'] + report['loss_count']) > 0 else 0
            print(f"  胜率: {win_rate:.1f}%")
        
        print(f"\n📋 关卡统计:")
        print(f"  拒绝订单: {portfolio.get('rejected_count', 0)} 笔")
        print(f"  部分成交: {portfolio.get('partial_count', 0)} 笔")
        
        if self.buy_signals:
            print(f"\n🎯 买入信号记录 ({len(self.buy_signals)}笔):")
            for sig in self.buy_signals[:10]:  # 只显示前10笔
                print(f"  [{sig['time']}] {sig['stock']} @ {sig['price']:.2f} | {sig['trigger']} | 分数:{sig['score']:.0f}")
        
        print("\n" + "="*70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全息战场模拟器 - CTO V162三大物理关卡')
    parser.add_argument('--date', type=str, required=True, help='目标日期 (YYYYMMDD)')
    parser.add_argument('--stocks', type=str, default='', help='股票列表，逗号分隔')
    parser.add_argument('--capital', type=float, default=100000.0, help='初始本金 (默认10万)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 解析股票列表
    stock_list = []
    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',') if s.strip()]
    
    # 【CTO V74修复】如果没有指定股票，动态获取今日真实活跃底池
    # 不再硬编码死票！要读取smart_download刚下载的那批活跃票
    if not stock_list:
        print("[MockLiveRunner] 未指定股票，正在通过 UniverseBuilder 获取今日真实活跃物理底池...")
        try:
            from logic.data_providers.universe_builder import UniverseBuilder
            base_pool, _ = UniverseBuilder(target_date=args.date).build()
            stock_list = base_pool
            print(f"[MockLiveRunner] 成功装载 {len(stock_list)} 只活跃标的。")
        except Exception as e:
            print(f"[ERR] 底池装载失败: {e}")
            return
    
    # 创建运行器
    runner = MockLiveRunner(args.date, stock_list, initial_capital=args.capital)
    
    # 运行Mock
    runner.run_mock_session()


if __name__ == '__main__':
    main()
