#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间机器Mock脚本 - 历史Tick伪装实时流喂给LiveTradingEngine
================================================================

【CTO V71物理级架构修复】Step 2
目标：用历史Tick测试LiveTradingEngine，确保Scan/Live物理逻辑100%同源

使用方法：
    python tools/mock_live_runner.py --date 20260310 --stocks 000001.SZ,600519.SH

架构说明：
    - 读取本地Tick数据
    - 按时间顺序推送Tick
    - 调用LiveTradingEngine核心打分逻辑
    - 输出实时榜单和交易信号

物理定律：
    - 时间锁定：模拟指定交易日的完整时间流
    - 量纲统一：amount单位为元，volume单位为股
    - 引擎同源：100%复用calculate_true_dragon_score
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
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

logger = logging.getLogger(__name__)


class MockLiveRunner:
    """时间机器Mock运行器"""
    
    def __init__(self, target_date: str, stock_list: List[str] = None):
        """
        初始化Mock运行器
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            stock_list: 股票列表，为空则使用粗筛结果
        """
        self.target_date = target_date
        self.stock_list = stock_list or []
        self.config_mgr = get_config_manager()
        self.true_dict = get_true_dictionary()
        
        # Tick队列缓存 {stock_code: List[Dict]}
        self.tick_queues: Dict[str, List[Dict]] = {}
        
        # 当前模拟时间
        self.current_time: Optional[datetime] = None
        
        # 榜单缓存
        self.leaderboard: Dict[str, Dict] = {}
        
        logger.info(f"[MockLiveRunner] 初始化完成，目标日期={target_date}")
    
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
        运行Mock交易时段
        
        模拟完整的交易时段：
        - 09:25 竞价结束
        - 09:30-11:30 早盘
        - 11:30-13:00 午休
        - 13:00-15:00 午盘
        """
        print(f"\n{'='*60}")
        print(f"[MockLiveRunner] 时间机器启动 - {self.target_date}")
        print(f"{'='*60}\n")
        
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
        # 时间锚点
        time_anchors = [
            ('09:25:00', '竞价结束'),
            ('09:30:00', '开盘'),
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
        
        # 遍历时间锚点
        for time_str, event_name in time_anchors:
            current_time = datetime.strptime(f"{self.target_date}{time_str}", "%Y%m%d%H:%M:%S")
            
            print(f"\n⏰ [{time_str}] {event_name}")
            print("-" * 40)
            
            # 在每个时间点计算当前榜单
            self._calculate_leaderboard_at_time(current_time)
            
            # 打印当前榜单
            self._print_leaderboard()
        
        print(f"\n{'='*60}")
        print(f"[MockLiveRunner] 时间机器结束")
        print(f"{'='*60}\n")
    
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
            
            # 【CTO V78】价格纯度 = (现价 - 昨收) / (最高 - 最低)
            # 反映价格在日内振幅中的位置，正值=强势区，负值=弱势区
            price_range = high - low
            if price_range > 0:
                raw_purity = (price - prev_close) / price_range
            else:
                # 一字板情况：价格无波动，纯度取决于涨跌方向
                raw_purity = 1.0 if price > prev_close else (-1.0 if price < prev_close else 0)
            purity = max(min(raw_purity * 100, 100.0), -100.0)  # 限制在[-100, 100]
            
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='时间机器Mock脚本')
    parser.add_argument('--date', type=str, required=True, help='目标日期 (YYYYMMDD)')
    parser.add_argument('--stocks', type=str, default='', help='股票列表，逗号分隔')
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
    runner = MockLiveRunner(args.date, stock_list)
    
    # 运行Mock
    runner.run_mock_session()


if __name__ == '__main__':
    main()
