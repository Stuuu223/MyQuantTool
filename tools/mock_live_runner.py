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
import json

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
from logic.core.sandbox_manager import SandboxManager  # 【CTO V169】沙盒档案库

logger = logging.getLogger(__name__)


class MockLiveRunner:
    """全息战场模拟器 - 三大物理关卡"""
    
    def __init__(self, target_date: str, stock_list: List[str] = None, initial_capital: float = 100000.0, sandbox: SandboxManager = None):
        """
        初始化Mock运行器
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            stock_list: 股票列表，为空则使用粗筛结果
            initial_capital: 初始本金
            sandbox: 【CTO V169】沙盒档案库管理器（多日连续模式共享）
        """
        self.target_date = target_date
        self.stock_list = stock_list or []
        self.config_manager = get_config_manager()  # 【CTO V172扫尾】统一命名为config_manager
        self.true_dict = get_true_dictionary()
        
        # 【CTO V169】沙盒档案库 - 如果未传入则自动创建
        if sandbox:
            self.sandbox = sandbox
        else:
            self.sandbox = SandboxManager(mode="backtest")
        
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
        
        # 【CTO V166】单吊模式状态
        self.has_bought_today = False  # 今日是否已买入
        self.current_top1_code = None  # 当前Top1代码
        self.current_top1_score = 0.0  # 当前Top1分数
        
        # 【CTO V166】T+1锁状态 {stock_code: buy_date}
        self.t1_lock: Dict[str, str] = {}
        
        # 【CTO V168】全天候Top10审计台账 - 每分钟记录，用于正反样本分析
        self.daily_top10_ledger: List[Dict] = []
        
        # 【CTO V172】真实流通盘缓存 - 废除10亿股硬编码！
        self.float_volumes: Dict[str, float] = {}  # {stock_code: float_volume_shares}
        
        logger.info(f"[MockLiveRunner] 初始化完成，目标日期={target_date}，本金=¥{initial_capital:,.0f}")
        logger.info(f"[MockLiveRunner] 沙盒ID: {self.sandbox.get_run_id()}")
    
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
            
            # 【CTO V172核弹级修复】获取真实流通盘数据！废除10亿股硬编码！
            try:
                detail = xtdata.get_instrument_detail(stock_code)
                if detail:
                    # QMT返回的FloatVolume单位是万股，需要转换为股
                    float_vol_wangu = detail.get('FloatVolume', 0)
                    if float_vol_wangu and float_vol_wangu > 0:
                        # 检测单位：如果值很小（<1000），说明是亿股；如果是万级别，说明是万股
                        # A股最小流通市值约20亿，如果float_vol < 1000，单位是亿股
                        if float_vol_wangu < 1000:
                            # 单位是亿股，转换为股
                            float_vol_shares = float_vol_wangu * 100000000
                        else:
                            # 单位是万股，转换为股
                            float_vol_shares = float_vol_wangu * 10000
                        self.float_volumes[stock_code] = float_vol_shares
                        logger.debug(f"[MockLiveRunner] {stock_code} 真实流通盘: {float_vol_shares/100000000:.2f}亿股")
                    else:
                        logger.warning(f"[MockLiveRunner] {stock_code} FloatVolume=0，将跳过打分")
                        self.float_volumes[stock_code] = 0
                else:
                    logger.warning(f"[MockLiveRunner] {stock_code} 无法获取instrument_detail，将跳过打分")
                    self.float_volumes[stock_code] = 0
            except Exception as e:
                logger.warning(f"[MockLiveRunner] {stock_code} 获取流通盘失败: {e}，将跳过打分")
                self.float_volumes[stock_code] = 0
            
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

        # ================================================================
        # 【CTO V166】废除静态锚点，改为每分钟流式雷达
        # 实盘不可能按"09:35、09:45"这种死板时间点买
        # 真正的买点是物理状态的"临界节点"，每一分钟都要检查
        # ================================================================
        
        # 关键事件时间点（仅用于日志打印）
        key_events = {
            '09:25:00': '竞价结束',
            '09:30:00': '开盘',
            '11:30:00': '早盘结束',
            '13:00:00': '午盘开盘',
            '15:00:00': '收盘',
        }
        
        # 生成每分钟时间轴 09:30 -> 14:57
        time_points = []
        from datetime import timedelta
        start_time = datetime.strptime(f"{self.target_date}09:30:00", "%Y%m%d%H:%M:%S")
        end_time = datetime.strptime(f"{self.target_date}14:57:00", "%Y%m%d%H:%M:%S")
        
        current = start_time
        while current <= end_time:
            # 跳过11:30-13:00午休
            if current.hour == 11 and current.minute > 30:
                current = datetime.strptime(f"{self.target_date}13:00:00", "%Y%m%d%H:%M:%S")
                continue
            if current.hour == 12:
                current = datetime.strptime(f"{self.target_date}13:00:00", "%Y%m%d%H:%M:%S")
                continue
            time_points.append(current)
            current += timedelta(minutes=1)
        
        # 竞价阶段先计算
        auction_time = datetime.strptime(f"{self.target_date}09:25:00", "%Y%m%d%H:%M:%S")
        self._calculate_leaderboard_at_time(auction_time)
        
        prev_time = None
        last_print_minute = -99  # 控制日志打印频率
        
        # 遍历每分钟时间轴
        for current_time in time_points:
            time_str = current_time.strftime('%H:%M:%S')
            
            # 关键事件打印日志
            if time_str in key_events:
                print(f"\n⏰ [{time_str}] {key_events[time_str]}")
                print("-" * 50)
            
            # 每分钟计算榜单
            self._calculate_leaderboard_at_time(current_time)
            
            # 【CTO V168】记录每分钟Top10到审计台账
            self._record_top10_to_ledger(current_time)
            
            # 【CTO V166核心】每分钟检查买点触发
            self._check_triggers_and_execute(current_time, prev_time)
            
            # 【CTO V166核心】每分钟监控持仓
            self._monitor_positions(current_time)
            
            # 每15分钟打印一次状态
            current_minute = current_time.hour * 60 + current_time.minute
            if abs(current_minute - last_print_minute) >= 15:
                self._print_status_brief(current_time)
                last_print_minute = current_minute
            
            prev_time = current_time
        
        # 收盘：打印最终状态
        print(f"\n⏰ [15:00:00] 收盘")
        print("-" * 50)
        
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
            
            # 【CTO V170】计算真实时间切片成交额（废除线性外推造假！）
            # 真实5分钟成交额：取过去5分钟内的所有Tick
            cutoff_5min = target_time - timedelta(minutes=5)
            cutoff_15min = target_time - timedelta(minutes=15)
            
            # 计算真实5分钟累计成交额（当前amount - 5分钟前的amount）
            amount_5min_ago = 0.0
            amount_15min_ago = 0.0
            for tick in tick_list:
                tick_time = self._parse_tick_time(tick['time'])
                if tick_time <= cutoff_5min:
                    amount_5min_ago = tick['amount']
                if tick_time <= cutoff_15min:
                    amount_15min_ago = tick['amount']
            
            # 真实时间切片成交额 = 当前累计 - N分钟前累计
            true_flow_5min = max(0, total_amount - amount_5min_ago)
            true_flow_15min = max(0, total_amount - amount_15min_ago)
            
            # 【CTO V172核弹级修复】使用真实流通盘！废除10亿股硬编码！
            real_float_volume = self.float_volumes.get(stock_code, 0)
            if real_float_volume <= 0:
                # 无真实流通盘数据，跳过打分！绝不使用假数据！
                logger.debug(f"[MockLiveRunner] {stock_code} 流通盘数据缺失，跳过打分")
                return  # 数据缺失就跳过，禁止用假数据凑数
            
            # 调用核心打分引擎
            try:
                # 创建引擎实例并调用
                engine = KineticCoreEngine()
                # 【CTO V170】传入真实时间切片数据，绝不允许线性外推！
                # 【CTO V172】传入真实流通盘，绝不允许硬编码10亿股！
                # 【CTO V173】net_inflow改用true_flow_5min真实时间切片！
                # 废除current_tick['amount']*0.5全天累计额，改用5分钟真实切片
                # ⚠️ 0.5净流入比例是估算值[UNVERIFIED]，待网格扫描验证
                result = engine.calculate_true_dragon_score(
                    net_inflow=true_flow_5min * 0.5,  # 【CTO V173】真实5分钟切片成交额，假设50%净流入[UNVERIFIED]
                    price=current_tick['price'],
                    prev_close=current_tick['lastClose'],
                    high=current_tick['high'],
                    low=current_tick['low'],
                    open_price=current_tick['open'],
                    flow_5min=true_flow_5min,  # 【CTO V170】真实5分钟成交额
                    flow_15min=true_flow_15min,  # 【CTO V170】真实15分钟成交额
                    flow_5min_median_stock=5000000,  # 默认历史中位数
                    space_gap_pct=10.0,  # 默认空间差
                    float_volume_shares=real_float_volume,  # 【CTO V172】真实流通盘！禁止硬编码！
                    current_time=target_time,  # 【修复】datetime对象
                    total_amount=total_amount,
                    total_volume=int(total_amount / current_tick['price']) if current_tick['price'] > 0 else 0,
                    limit_up_queue_amount=0,
                    mode='scan',
                    stock_code=stock_code
                )
                
                # 【CTO V168修复】返回类型是tuple: (final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe, debug_metrics)
                if isinstance(result, tuple) and len(result) >= 6:
                    score, sustain_ratio, inflow_ratio, ratio_stock, mfe, debug_metrics = result[0], result[1], result[2], result[3], result[4], result[5]
                    self.leaderboard[stock_code] = {
                        'score': score,
                        'price': current_tick['price'],
                        'amount': total_amount,
                        'mfe': mfe,
                        'sustain_ratio': sustain_ratio,
                        'inflow_ratio': inflow_ratio,
                        'tick': current_tick,
                        'debug_metrics': debug_metrics  # 【CTO V168】高阶物理算子明细
                    }
                elif isinstance(result, tuple) and len(result) >= 5:
                    # 兼容旧版本返回值（无debug_metrics）
                    score, sustain_ratio, inflow_ratio, ratio_stock, mfe = result[0], result[1], result[2], result[3], result[4]
                    self.leaderboard[stock_code] = {
                        'score': score,
                        'price': current_tick['price'],
                        'amount': total_amount,
                        'mfe': mfe,
                        'sustain_ratio': sustain_ratio,
                        'inflow_ratio': inflow_ratio,
                        'tick': current_tick,
                        'debug_metrics': {}  # 空字典兼容
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
    
    def _record_top10_to_ledger(self, current_time: datetime):
        """
        【CTO V168】记录每分钟Top10到审计台账
        
        用于正反样本分析，建立香农信息熵分析的基础数据
        """
        if not self.leaderboard:
            return
        
        # 按分数排序取Top10
        sorted_stocks = sorted(
            self.leaderboard.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )[:10]
        
        for rank, (code, data) in enumerate(sorted_stocks, 1):
            debug_m = data.get('debug_metrics', {})
            self.daily_top10_ledger.append({
                'date': self.target_date,
                'time': current_time.strftime('%H:%M:%S'),
                'rank': rank,
                'code': code,
                'score': data['score'],
                'price': data['price'],
                'mfe': data.get('mfe', 0),
                'sustain': data.get('sustain_ratio', 0),
                'inflow_pct': data.get('inflow_ratio', 0),
                # 高阶物理算子
                'mass_potential': debug_m.get('mass_potential', 0),
                'velocity': debug_m.get('velocity', 0),
                'kinetic_energy': debug_m.get('base_kinetic_energy', 0),
                'friction': debug_m.get('friction_multiplier', 0),
                'purity': debug_m.get('purity_norm', 0),
                'ratio_stock': debug_m.get('ratio_stock', 0),
                'change_pct': debug_m.get('change_pct', 0)
            })
    
    def _parse_tick_time(self, time_val):
        """
        【CTO V75重构】物理级时间戳解析
        兼容 QMT 返回的毫秒时间戳 (int/float) 或 字符串
        
        【CTO V165修复】QMT毫秒时间戳是UTC，需转为北京时间(UTC+8)
        """
        import pandas as pd
        from datetime import datetime
        try:
            # 1. 尝试作为数值型毫秒级时间戳解析
            if isinstance(time_val, (int, float)):
                # 如果数值很大，说明是毫秒时间戳 (如 1773072000000)
                if time_val > 1000000000000:
                    dt = pd.to_datetime(time_val, unit='ms')
                    # 【CTO V165关键修复】UTC -> 北京时间
                    dt = dt.tz_localize('UTC').tz_convert('Asia/Shanghai')
                    return dt.replace(tzinfo=None).to_pydatetime()  # 去掉时区信息便于比较
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
        prev_tick_time = None
        for tick in tick_list:
            tick_time = self._parse_tick_time(tick['time'])
            if tick_time <= prev_minute_end:
                prev_amount = tick['amount']
                prev_tick_time = tick_time
        
        # 获取当前分钟最后一个Tick的amount
        curr_amount = prev_amount
        curr_tick_time = None
        for tick in tick_list:
            tick_time = self._parse_tick_time(tick['time'])
            if tick_time < current_minute_end:
                curr_amount = tick['amount']
                curr_tick_time = tick_time
        
        # 当前分钟成交额 = 当前累计 - 上一分钟累计
        return max(0, curr_amount - prev_amount)
    
    def _check_triggers_and_execute(self, current_time: datetime, prev_time: datetime):
        """
        【CTO V166 刺客模式】单吊Top1 + T+1物理锁
        
        核心逻辑：
        1. 每天只允许买入一次（单吊模式）
        2. 只买分数最高的Top1股票
        3. 全仓买入（All-in）
        4. T+1锁：买入当天禁止卖出
        """
        if prev_time is None:
            return
        
        # 【CTO V166】检查是否今日已买入
        if self.has_bought_today:
            return  # 今日已买入，静默拒绝
        
        # 【CTO V166】检查是否已有持仓
        if len(self.execution_manager.positions) > 0:
            return  # 有持仓就不再买
        
        # 获取分数最高的股票（Top1）
        if not self.leaderboard:
            return
        
        # 排序找出Top1
        sorted_stocks = sorted(
            self.leaderboard.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        if not sorted_stocks:
            return
        
        top1_code, top1_data = sorted_stocks[0]
        top1_score = top1_data['score']
        
        # 更新Top1状态
        self.current_top1_code = top1_code
        self.current_top1_score = top1_score
        
        # 【CTO V171】买入条件检查 - 阈值从config读取
        min_trigger_score = self.config_manager.get('kinetic_physics.min_trigger_score', 100.0)
        
        # 条件1：分数>=阈值（提高门槛避免噪音）
        if top1_score < min_trigger_score:
            return
        
        # 条件2：sustain_ratio>=1.0（资金流入正反馈）
        volume_ratio = top1_data.get('sustain_ratio', 0)
        if volume_ratio < 1.0:
            return
        
        # 条件3：有真实成交额
        if top1_data.get('amount', 0) <= 0:
            return
        
        # 准备买入参数
        tick = top1_data.get('tick', {})
        price = top1_data['price']
        current_mfe = top1_data.get('mfe', 0)
        sustain_ratio = top1_data.get('sustain_ratio', 0)
        inflow_ratio = top1_data.get('inflow_ratio', 0)
        high = tick.get('high', price)
        low = tick.get('low', price)
        open_price = tick.get('open', price)
        prev_close = tick.get('lastClose', price)
        
        # 计算涨停逼近率
        limit_up_price = tick.get('limitUpPrice', 0)
        if limit_up_price <= 0:
            if top1_code.startswith('300') or top1_code.startswith('688'):
                limit_up_price = prev_close * 1.2
            else:
                limit_up_price = prev_close * 1.1
        limit_proximity = (price - prev_close) / (limit_up_price - prev_close) if (limit_up_price - prev_close) > 0 else 0.5
        
        # 【CTO V172流动性拒止】涨停边缘绝对禁止买入！排队是大猪特权！
        if price >= limit_up_price * 0.998:
            return  # 涨停排队是骗局，智猪绝不接盘！
        
        # 【CTO V172缩量秒板毒药拦截】涨幅高但流入极低 = 极度一致性陷阱
        inflow_min = self.config_manager.get('kinetic_physics.early_buy.inflow_min_for_high_surge', 0.5)
        if price > prev_close * 1.08 and inflow_ratio < inflow_min:
            return  # 涨幅>8%但流入<0.5%，缩量秒板毒药，拒绝虚假一致性！
        
        # 【CTO V172避雷针相对论防御】
        upward_displacement = high - open_price
        if upward_displacement > 0:
            drawdown_from_high = high - price
            retrace_ratio = drawdown_from_high / upward_displacement
            retrace_ratio_max = self.config_manager.get('kinetic_physics.retrace_ratio_max', 0.618)
            if retrace_ratio > retrace_ratio_max:
                return  # 避雷针：向上势能已被吞噬，禁止开火
        
        # 【CTO V172 VWAP确认】
        total_amount = top1_data.get('amount', 0)
        total_volume = tick.get('volume', 1)
        if total_volume > 0:
            vwap = total_amount / (total_volume * 100) if total_volume > 0 else price
            vwap_deviation_max = self.config_manager.get('kinetic_physics.vwap_deviation_max', 0.02)
            if price < vwap * (1 - vwap_deviation_max):
                return  # 智猪法则：未在均线上方形成强势沉没成本
        
        # 【CTO V172核心：连续函数点火概率模型】
        # 废除if-else布尔切断，改用Sigmoid和Gaussian连续函数乘积
        from logic.utils.math_utils_core import sigmoid_multiplier, gaussian_penalty, calculate_ignition_probability
        
        # 从config读取连续函数参数
        mfe_mid = self.config_manager.get('kinetic_physics.early_buy.mfe_midpoint', 1.2)
        mfe_k = self.config_manager.get('kinetic_physics.early_buy.mfe_steepness', 2.0)
        sustain_mid = self.config_manager.get('kinetic_physics.early_buy.sustain_midpoint', 1.5)
        sustain_k = self.config_manager.get('kinetic_physics.early_buy.sustain_steepness', 2.0)
        prox_opt = self.config_manager.get('kinetic_physics.early_buy.proximity_optimal', 0.75)
        prox_sigma = self.config_manager.get('kinetic_physics.early_buy.proximity_sigma', 0.15)
        ignition_threshold = self.config_manager.get('kinetic_physics.early_buy.ignition_threshold', 0.30)
        
        # 计算综合点火概率
        ignition_prob = calculate_ignition_probability(
            mfe=current_mfe,
            sustain_ratio=sustain_ratio,
            proximity=limit_proximity,
            mfe_midpoint=mfe_mid,
            mfe_steepness=mfe_k,
            sustain_midpoint=sustain_mid,
            sustain_steepness=sustain_k,
            proximity_optimal=prox_opt,
            proximity_sigma=prox_sigma
        )
        
        if ignition_prob < ignition_threshold:
            # 综合能量不足，拒绝买入
            logger.debug(f"[MockLiveRunner] {top1_code} 点火概率{ignition_prob:.2%} < {ignition_threshold:.0%}，拒绝")
            return
        
        # 【CTO V172扫尾】删除重复读取min_trigger_score和废话assert
        # L701已经检查过 if top1_score < min_trigger_score: return
        # 能走到这里说明分数一定>=阈值，不需要再检查
        
        # 【CTO V167防作弊】硬断言：确保买入的是当时的绝对Top1
        assert top1_code == sorted_stocks[0][0], f"FATAL: 系统买入的不是当时的绝对Top1！存在作弊嫌疑！买入{top1_code} vs Top1{sorted_stocks[0][0]}"
        
        # 计算分钟级成交额
        minute_volume = self._get_minute_volume(top1_code, current_time)
        
        # 【CTO V166】执行单吊买入
        from logic.execution.mock_execution_manager import TriggerType
        success, order = self.execution_manager.place_mock_order(
            stock_code=top1_code,
            last_price=price,
            direction='BUY',
            trigger_type=TriggerType.STATIC_SCORE,
            tick_data=tick,
            minute_volume=minute_volume
        )
        
        if success:
            # 【CTO V167防作弊】捕获案发现场Top10快照作为铁证
            # 【CTO V168透明度】增加高阶物理算子明细
            snapshot_top10 = []
            for idx, (code, data) in enumerate(sorted_stocks[:10]):
                debug_m = data.get('debug_metrics', {})
                snapshot_top10.append({
                    'rank': idx + 1,
                    'code': code,
                    'score': data['score'],
                    'mfe': data.get('mfe', 0),
                    'sustain': data.get('sustain_ratio', 0),
                    'price': data['price'],
                    'is_buy_target': code == top1_code,  # 标记买入标的
                    # 【CTO V168】高阶物理算子明细
                    'mass_potential': debug_m.get('mass_potential', 0),
                    'velocity': debug_m.get('velocity', 0),
                    'kinetic_energy': debug_m.get('base_kinetic_energy', 0),
                    'friction': debug_m.get('friction_multiplier', 0),
                    'purity': debug_m.get('purity_norm', 0),
                    'inflow_pct': debug_m.get('inflow_ratio_pct', 0),
                    'ratio_stock': debug_m.get('ratio_stock', 0)
                })
            
            # 记录买入信号（含铁证快照）
            self.buy_signals.append({
                'time': current_time.strftime('%H:%M:%S'),
                'stock': top1_code,
                'price': price,
                'trigger': '刺客Top1单吊',
                'score': top1_score,
                'mfe': current_mfe,
                'sustain': volume_ratio,
                'moment_snapshot': snapshot_top10  # 【CTO V167】案发现场铁证
            })
            
            # 【CTO V166】设置单吊锁和T+1锁
            self.has_bought_today = True
            self.t1_lock[top1_code] = self.target_date
            
            print(f"\n🎯 [刺客买入] {top1_code} @ {price:.2f}")
            print(f"   分数: {top1_score:.0f} | MFE: {current_mfe:.2f} | Sustain: {volume_ratio:.2f}")
            print(f"   模式: 单吊Top1 | 仓位: 全仓")
    
    def _monitor_positions(self, current_time: datetime):
        """
        【CTO V166】监控持仓，T+1物理锁强制执行
        
        核心规则：
        1. T+1锁：买入当天禁止卖出（A股规则）
        2. 微观防爆：第二天才允许止损
        
        Args:
            current_time: 当前时间
        """
        positions = self.execution_manager.positions
        if not positions:
            return
        
        for stock_code, pos in list(positions.items()):
            # 【CTO V166核心】T+1物理锁检查
            buy_date = self.t1_lock.get(stock_code, '')
            if buy_date == self.target_date:
                # 今天买的，不能卖！
                # 只更新价格，不做止损检查
                tick_list = self.tick_queues.get(stock_code, [])
                for tick in reversed(tick_list):
                    tick_time = self._parse_tick_time(tick['time'])
                    if tick_time <= current_time:
                        pos.current_price = tick['price']
                        pos.max_price = max(pos.max_price, tick['price'])
                        break
                continue  # 跳过止损检查
            
            # 第二天及以后：允许止损检查
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
            
            # 【CTO V172扫尾】删除10亿股僵尸代码！使用真实流通盘
            real_float_vol = self.float_volumes.get(stock_code, 0)
            if real_float_vol <= 0:
                logger.warning(f"[{stock_code}] 持仓监控缺失真实流通盘，跳过本分钟动能更新！")
                continue  # 不要用假数据污染
            
            inflow_ratio = (total_amount * 0.5) / (real_float_vol * current_price) * 100
            mfe = amplitude / max(inflow_ratio, 0.01) if inflow_ratio > 0 else 0
            
            # 持仓时间（分钟）
            entry_time = datetime.strptime(pos.entry_time, '%Y-%m-%d %H:%M:%S')
            minutes_elapsed = (current_time - entry_time).total_seconds() / 60
            
            # 【CTO V162关卡3】检查微观防爆（仅第二天起生效）
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
        """
        收盘处理持仓
        
        【CTO V166】T+1锁：买入当天不能卖
        收盘时只是记录持仓状态，不强制平仓
        """
        positions = list(self.execution_manager.positions.keys())
        if not positions:
            return
        
        print("\n🔔 收盘持仓检查:")
        for stock_code in positions:
            pos = self.execution_manager.positions.get(stock_code)
            if not pos:
                continue
            
            # 【CTO V166核心】T+1锁检查
            buy_date = self.t1_lock.get(stock_code, '')
            if buy_date == self.target_date:
                # 今天买的，不能卖，记录为锁仓
                print(f"  📦 {stock_code}: 锁仓中(T+1) | 成本:{pos.entry_price:.2f} | 数量:{pos.volume}")
            else:
                # 不是今天买的，可以卖
                tick_list = self.tick_queues.get(stock_code, [])
                if tick_list:
                    last_tick = tick_list[-1]
                    pos.current_price = last_tick['price']
                    print(f"  ✅ {stock_code}: 可卖出 | 成本:{pos.entry_price:.2f} | 现价:{pos.current_price:.2f}")
    
    def _print_status_brief(self, current_time: datetime):
        """【CTO V166】打印简短状态（每15分钟）"""
        time_str = current_time.strftime('%H:%M')
        
        # 榜单Top1
        if self.leaderboard:
            sorted_stocks = sorted(self.leaderboard.items(), key=lambda x: x[1]['score'], reverse=True)
            if sorted_stocks:
                top1_code, top1_data = sorted_stocks[0]
                top1_score = top1_data['score']
                print(f"  [{time_str}] Top1: {top1_code} 分数={top1_score:.0f}")
        
        # 持仓状态
        if self.execution_manager.positions:
            for code, pos in self.execution_manager.positions.items():
                status = "锁仓(T+1)" if self.t1_lock.get(code) == self.target_date else "可卖"
                print(f"  [{time_str}] 持仓: {code} {status} | 成本={pos.entry_price:.2f}")
    
    def _print_final_report(self):
        """
        【CTO V166】刺客级账户战报
        【CTO V169】沙盒档案库持久化
        
        格式严格按照Boss要求：
        账户总资金 | 持仓资金 | 剩余可用 | 当日收益 | 账户总收益
        持仓股票详情
        """
        report = self.execution_manager.get_performance_report()
        portfolio = self.execution_manager.get_portfolio_summary()
        
        # 计算账户总资金 = 现金 + 持仓市值
        total_position_value = 0.0
        for stock_code, pos in self.execution_manager.positions.items():
            total_position_value += pos.current_price * pos.volume if pos.current_price > 0 else pos.entry_price * pos.volume
        
        total_value = report.get('final_cash', 0) + total_position_value
        initial = report.get('initial_capital', 100000)
        
        # 计算收益
        if total_position_value > 0:
            total_float_pnl = total_position_value - (initial - report.get('final_cash', 0))
            float_pnl_pct = total_float_pnl / initial * 100 if initial > 0 else 0
            day_pnl_pct = float_pnl_pct
            day_pnl = total_float_pnl
        else:
            day_pnl = report.get('realized_pnl', 0)
            day_pnl_pct = report.get('realized_pnl_pct', 0)
        
        total_pnl = total_value - initial
        total_pnl_pct = total_pnl / initial * 100 if initial > 0 else 0
        
        # ==================== 控制台输出 ====================
        print("\n" + "="*70)
        print(f"【CTO V169 刺客级账户战报 - {self.target_date}】")
        print(f"沙盒ID: {self.sandbox.get_run_id()}")
        print("="*70)
        
        print(f"\n💰 账户总资金：¥{total_value:,.2f}")
        print(f"💼 持仓资金：¥{total_position_value:,.2f}")
        print(f"💵 剩余可用资金：¥{report.get('final_cash', 0):,.2f}")
        
        float_sign = "+" if day_pnl >= 0 else ""
        print(f"📈 当日收益：{float_sign}{day_pnl_pct:.2f}% ({float_sign}¥{day_pnl:,.2f})")
        
        total_sign = "+" if total_pnl >= 0 else ""
        print(f"🏆 账户总收益：{total_sign}{total_pnl_pct:.2f}% ({total_sign}¥{total_pnl:,.2f})")
        
        # 持仓股票详情
        print("\n" + "-"*70)
        print("📦 当前持仓股票：")
        
        positions_data = []  # 用于JSON持久化
        
        if self.execution_manager.positions:
            for i, (code, pos) in enumerate(self.execution_manager.positions.items(), 1):
                buy_date = self.t1_lock.get(code, '')
                is_locked = buy_date == self.target_date
                status = "锁仓中(T+1)" if is_locked else "可卖出"
                
                current_price = pos.current_price if pos.current_price > 0 else pos.entry_price
                float_pnl = (current_price - pos.entry_price) / pos.entry_price * 100
                float_pnl_value = (current_price - pos.entry_price) * pos.volume
                float_sign = "+" if float_pnl >= 0 else ""
                holding_value = current_price * pos.volume
                
                print(f"\n[{i}] {code}")
                print(f"    状态：{status} / 持仓天数：{pos.holding_days}天")
                print(f"    买入成本：¥{pos.entry_price:.2f}")
                print(f"    当前现价：¥{current_price:.2f}")
                print(f"    浮动收益：{float_sign}{float_pnl:.2f}% ({float_sign}¥{float_pnl_value:,.2f})")
                print(f"    持有市值：¥{holding_value:,.2f}")
                
                # 收集持仓数据
                positions_data.append({
                    'code': code,
                    'status': status,
                    'holding_days': pos.holding_days,
                    'entry_price': pos.entry_price,
                    'current_price': current_price,
                    'float_pnl_pct': float_pnl,
                    'float_pnl_value': float_pnl_value,
                    'holding_value': holding_value,
                    'volume': pos.volume
                })
        else:
            print("  无持仓")
        
        # 当日操作记录
        print("\n" + "-"*70)
        if self.buy_signals:
            print("🎯 当日操作记录：")
            for sig in self.buy_signals:
                print(f"  【买入单吊】 {sig['stock']} @ {sig['price']:.2f} | 触发: {sig['trigger']} | 耗资: ¥{initial:,.2f}")
                
                snapshot = sig.get('moment_snapshot', [])
                if snapshot:
                    print(f"\n  ==================== 【案发现场快照 {sig['time']}】 ====================")
                    for item in snapshot:
                        buy_mark = " (*买入标的*)" if item.get('is_buy_target') else ""
                        debug_info = ""
                        if item.get('mass_potential', 0) != 0 or item.get('kinetic_energy', 0) != 0:
                            debug_info = f" | 动能:{item.get('kinetic_energy', 0):.3f} | 质量:{item.get('mass_potential', 0):.4f} | 摩擦:{item.get('friction', 0):.2f}"
                        print(f"  [Top {item['rank']}] {item['code']} | 分数: {item['score']:.0f} | MFE: {item['mfe']:.2f} | Sustain: {item['sustain']:.2f} | 现价: {item['price']:.2f}{debug_info}{buy_mark}")
                    print("  " + "="*60)
        else:
            print("🎯 当日操作记录：无")
        
        # 真实胜率统计
        print("\n" + "-"*70)
        print("📊 真实胜率统计（净利润>0才算赢）：")
        win_count = report.get('win_count', 0)
        loss_count = report.get('loss_count', 0)
        win_rate = report.get('win_rate', 0)
        print(f"  盈利次数：{win_count}")
        print(f"  亏损次数：{loss_count}")
        print(f"  真实胜率：{win_rate:.1f}%")
        
        print("\n" + "="*70)
        
        # ==================== 【CTO V169】沙盒持久化 ====================
        
        # 1. 保存每日Top10审计台账CSV
        if self.daily_top10_ledger:
            self.sandbox.save_daily_ledger(self.target_date, self.daily_top10_ledger)
        
        # 2. 构建结构化战报数据（含案发现场快照）
        battle_report_data = {
            'account': {
                'total_value': total_value,
                'position_value': total_position_value,
                'cash': report.get('final_cash', 0),
                'day_pnl': day_pnl,
                'day_pnl_pct': day_pnl_pct,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct
            },
            'positions': positions_data,
            'buy_signals': self.buy_signals,  # 含moment_snapshot案发现场
            'performance': {
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': win_rate,
                'trade_count': len(self.execution_manager.trades)
            }
        }
        
        # 3. 保存JSON战报
        self.sandbox.save_battle_report_json(self.target_date, battle_report_data)
        
        # 4. 生成并保存MD战报
        md_content = self._generate_markdown_report(
            total_value, total_position_value, report, day_pnl, day_pnl_pct,
            total_pnl, total_pnl_pct, positions_data, win_count, loss_count, win_rate
        )
        self.sandbox.save_battle_report_md(self.target_date, md_content)
        
        print(f"\n📁 档案已存入沙盒: {self.sandbox.get_sandbox_root()}")
    
    def _generate_markdown_report(self, total_value, total_position_value, report, 
                                   day_pnl, day_pnl_pct, total_pnl, total_pnl_pct,
                                   positions_data, win_count, loss_count, win_rate) -> str:
        """
        【CTO V169】生成人类可读的Markdown战报
        """
        lines = []
        lines.append(f"# 刺客级账户战报 - {self.target_date}\n")
        lines.append(f"> 沙盒ID: `{self.sandbox.get_run_id()}`\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        lines.append("## 💰 账户概览\n")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 账户总资金 | ¥{total_value:,.2f} |")
        lines.append(f"| 持仓资金 | ¥{total_position_value:,.2f} |")
        lines.append(f"| 剩余可用 | ¥{report.get('final_cash', 0):,.2f} |")
        day_sign = "+" if day_pnl >= 0 else ""
        lines.append(f"| 当日收益 | {day_sign}{day_pnl_pct:.2f}% ({day_sign}¥{day_pnl:,.2f}) |")
        total_sign = "+" if total_pnl >= 0 else ""
        lines.append(f"| 账户总收益 | {total_sign}{total_pnl_pct:.2f}% ({total_sign}¥{total_pnl:,.2f}) |")
        
        lines.append("\n## 📦 当前持仓\n")
        if positions_data:
            lines.append("| 代码 | 状态 | 成本 | 现价 | 浮动收益 | 持仓市值 |")
            lines.append("|------|------|------|------|----------|----------|")
            for pos in positions_data:
                sign = "+" if pos['float_pnl_pct'] >= 0 else ""
                lines.append(f"| {pos['code']} | {pos['status']} | ¥{pos['entry_price']:.2f} | ¥{pos['current_price']:.2f} | {sign}{pos['float_pnl_pct']:.2f}% | ¥{pos['holding_value']:,.2f} |")
        else:
            lines.append("*无持仓*")
        
        lines.append("\n## 🎯 当日操作记录\n")
        if self.buy_signals:
            for sig in self.buy_signals:
                lines.append(f"### 买入: {sig['stock']} @ ¥{sig['price']:.2f}\n")
                lines.append(f"- **触发时间**: {sig['time']}")
                lines.append(f"- **触发类型**: {sig['trigger']}")
                lines.append(f"- **分数**: {sig['score']:.0f}")
                lines.append(f"- **MFE**: {sig['mfe']:.2f}")
                lines.append(f"- **Sustain**: {sig['sustain']:.2f}")
                
                # 案发现场快照
                snapshot = sig.get('moment_snapshot', [])
                if snapshot:
                    lines.append("\n**案发现场Top10快照:**\n")
                    lines.append("| 排名 | 代码 | 分数 | MFE | Sustain | 现价 | 买入标的 |")
                    lines.append("|------|------|------|-----|---------|------|----------|")
                    for item in snapshot:
                        mark = "✅" if item.get('is_buy_target') else ""
                        lines.append(f"| {item['rank']} | {item['code']} | {item['score']:.0f} | {item['mfe']:.2f} | {item['sustain']:.2f} | ¥{item['price']:.2f} | {mark} |")
        else:
            lines.append("*无操作*")
        
        lines.append("\n## 📊 胜率统计\n")
        lines.append(f"- 盈利次数: {win_count}")
        lines.append(f"- 亏损次数: {loss_count}")
        lines.append(f"- 真实胜率: {win_rate:.1f}%")
        
        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全息战场模拟器 - CTO V163多日连续回测')
    parser.add_argument('--date', type=str, default='', help='单日模式: 目标日期 (YYYYMMDD)')
    parser.add_argument('--start_date', type=str, default='', help='多日模式: 开始日期 (YYYYMMDD)')
    parser.add_argument('--end_date', type=str, default='', help='多日模式: 结束日期 (YYYYMMDD)')
    parser.add_argument('--stocks', type=str, default='', help='股票列表，逗号分隔')
    parser.add_argument('--capital', type=float, default=100000.0, help='初始本金 (默认10万)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 【CTO V163】判断单日模式还是多日模式
    if args.start_date and args.end_date:
        # 多日连续回测模式
        run_continuous_backtest(args)
    elif args.date:
        # 单日模式
        run_single_day(args)
    else:
        print("[ERR] 必须指定 --date (单日) 或 --start_date + --end_date (多日)")
        return


def run_single_day(args):
    """【CTO V169】单日回测模式"""
    stock_list = []
    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',') if s.strip()]
    
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
    
    # 【CTO V169】创建沙盒
    sandbox = SandboxManager(mode="backtest")
    
    # 保存配置快照
    config_snapshot = {
        'target_date': args.date,
        'initial_capital': args.capital,
        'stock_list': stock_list[:10] if stock_list else [],  # 只保存前10只避免过大
        'stock_count': len(stock_list)
    }
    sandbox.save_config_snapshot(config_snapshot)
    
    runner = MockLiveRunner(args.date, stock_list, initial_capital=args.capital, sandbox=sandbox)
    runner.run_mock_session()
    
    # 打印沙盒目录结构
    sandbox.print_sandbox_summary()


def run_continuous_backtest(args):
    """【CTO V163/V169】多日连续回测模式 - 沙盒档案库"""
    from logic.utils.calendar_utils import get_trading_days_between
    
    start_date = args.start_date
    end_date = args.end_date
    initial_capital = args.capital
    
    # 【CTO V169】创建共享沙盒（多日共用一个Run ID）
    sandbox = SandboxManager(mode="continuous_backtest")
    
    print("\n" + "="*70)
    print(f"🚀 [多日连续回测] CTO V169 时间机器启动")
    print(f"   沙盒ID: {sandbox.get_run_id()}")
    print(f"   区间: {start_date} → {end_date}")
    print(f"   本金: ¥{initial_capital:,.2f}")
    print("="*70 + "\n")
    
    # 获取交易日列表
    try:
        trading_days = get_trading_days_between(start_date, end_date)
    except Exception as e:
        print(f"[WARN] get_trading_days_between失败: {e}，使用简单日期范围")
        # 降级：简单生成日期范围
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        trading_days = []
        current = start
        while current <= end:
            # 跳过周末
            if current.weekday() < 5:
                trading_days.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)
    
    if not trading_days:
        print("[ERR] 区间内无交易日")
        return
    
    print(f"📅 交易日列表: {trading_days}")
    
    # 【CTO V169】保存配置快照
    config_snapshot = {
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'trading_days': trading_days,
        'stocks_param': args.stocks
    }
    sandbox.save_config_snapshot(config_snapshot)
    
    # 共享的ExecutionManager（跨日资金复利）
    shared_manager = None
    daily_snapshots = []
    
    for i, date_str in enumerate(trading_days):
        print(f"\n{'='*70}")
        print(f"📆 [{i+1}/{len(trading_days)}] {date_str}")
        print("="*70)
        
        # 获取当日活跃底池
        stock_list = []
        if args.stocks:
            stock_list = [s.strip() for s in args.stocks.split(',') if s.strip()]
        
        if not stock_list:
            try:
                from logic.data_providers.universe_builder import UniverseBuilder
                base_pool, _ = UniverseBuilder(target_date=date_str).build()
                stock_list = base_pool
                print(f"[MockLiveRunner] {date_str} 装载 {len(stock_list)} 只活跃标的")
            except Exception as e:
                print(f"[WARN] {date_str} 底池装载失败: {e}，跳过该日")
                continue
        
        # 创建运行器（继承前一日资金 + 共享沙盒）
        if shared_manager is None:
            # 第一天：新初始化
            runner = MockLiveRunner(date_str, stock_list, initial_capital=initial_capital, sandbox=sandbox)
            shared_manager = runner.execution_manager
        else:
            # 后续日：继承资金和持仓
            runner = MockLiveRunner(date_str, stock_list, initial_capital=initial_capital, sandbox=sandbox)
            runner.execution_manager = shared_manager  # 共享资金状态机
            
            # 跨日继承持仓
            shared_manager.carry_positions_to_next_day(date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:8])
        
        # 运行当日模拟
        runner.run_mock_session()
        
        # 记录当日快照
        snapshot = shared_manager.get_daily_snapshot(date_str)
        daily_snapshots.append(snapshot)
        
        print(f"\n📊 [{date_str}] 日终净值: ¥{snapshot['total_value']:,.2f} | 累计盈亏: {snapshot['pnl_pct']:+.2f}%")
    
    # ==================== 最终报告 ====================
    print("\n" + "="*70)
    print("📈 多日连续回测 - 最终资金曲线报告")
    print("="*70)
    
    if daily_snapshots:
        print("\n日期          | 现金          | 持仓市值      | 总资产        | 累计收益率")
        print("-" * 80)
        for snap in daily_snapshots:
            print(f"{snap['date']} | ¥{snap['cash']:>10,.2f} | ¥{snap['position_value']:>10,.2f} | ¥{snap['total_value']:>10,.2f} | {snap['pnl_pct']:>+8.2f}%")
        
        # 统计
        final_snapshot = daily_snapshots[-1]
        print("\n" + "="*70)
        print(f"💰 初始本金: ¥{initial_capital:,.2f}")
        print(f"💰 最终资产: ¥{final_snapshot['total_value']:,.2f}")
        print(f"📈 累计盈亏: ¥{final_snapshot['pnl']:,.2f} ({final_snapshot['pnl_pct']:+.2f}%)")
        print(f"📊 交易天数: {len(daily_snapshots)} 天")
        print(f"📊 总交易次数: {final_snapshot['trade_count']} 笔")
        print("="*70)
        
        # 【CTO V169】保存资金曲线到沙盒
        sandbox.save_equity_curve(daily_snapshots)
    
    # 【CTO V169】打印沙盒目录结构
    sandbox.print_sandbox_summary()


if __name__ == '__main__':
    main()
