#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局热力状态机 (Global Heat State Machine)

CTO Phase 6.2 核心架构 - 实盘毫秒级响应

功能:
1. 在实盘后台开异步线程，每3秒使用xtdata.get_full_tick全推接口
2. 实时计算73个关注名单的成交额增量绝对值
3. 数据存储在共享内存，供验钞机0.1毫秒读取

架构:
- 独立线程更新，避免阻塞主线程
- 共享内存存储current_market_heat_rank
- 错误处理和自动恢复机制

Author: AI System Architect
Date: 2026-02-23
"""

import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.utils.code_converter import CodeConverter

logger = logging.getLogger(__name__)


class GlobalHeatStateMachine:
    """
    全局热力状态机
    
    负责:
    1. 实时监控关注列表的热度变化
    2. 计算成交额增量绝对值
    3. 维护热度排名（共享内存）
    4. 提供毫秒级查询接口
    """
    
    # 类级别的共享内存（所有实例共享）
    _shared_memory = {
        'heat_data': {},
        'last_update': None,
        'is_running': False
    }
    _memory_lock = threading.RLock()
    
    def __init__(self, watch_list: List[str], update_interval: int = 3):
        """
        初始化全局热力状态机
        
        Args:
            watch_list: 关注股票代码列表（6位数字格式）
            update_interval: 更新间隔（秒），默认3秒
        """
        if not QMT_AVAILABLE:
            raise ImportError("xtquant未安装，无法使用GlobalHeatStateMachine")
        
        if not watch_list:
            raise ValueError("关注列表不能为空")
        
        self.watch_list = self._normalize_codes(watch_list)
        self.update_interval = update_interval
        
        # 线程控制
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # 历史数据缓存（用于计算增量）
        self._amount_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._history_lock = threading.RLock()
        
        # 统计数据
        self._update_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None
        self._start_time: Optional[datetime] = None
        
        logger.info(f"🔥 GlobalHeatStateMachine初始化完成 | 关注数量: {len(self.watch_list)} | 更新间隔: {update_interval}s")
    
    def _normalize_codes(self, codes: List[str]) -> List[str]:
        """
        标准化股票代码
        
        Args:
            codes: 原始代码列表
            
        Returns:
            QMT格式的代码列表（如000001.SZ）
        """
        normalized = []
        for code in codes:
            try:
                qmt_code = CodeConverter.to_qmt(code)
                normalized.append(qmt_code)
            except Exception as e:
                logger.warning(f"⚠️ 代码转换失败: {code}, 跳过. 错误: {e}")
                continue
        return normalized
    
    def start(self) -> bool:
        """
        启动异步更新线程
        
        Returns:
            bool: 是否成功启动
        """
        if self._is_running:
            logger.warning("⚠️ GlobalHeatStateMachine已在运行")
            return False
        
        try:
            # 测试QMT连接
            if not self._check_qmt_connection():
                logger.error("❌ QMT连接失败，无法启动GlobalHeatStateMachine")
                return False
            
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._update_loop,
                name="GlobalHeatStateMachine",
                daemon=True
            )
            self._thread.start()
            self._is_running = True
            self._start_time = datetime.now()
            
            # 更新共享内存状态
            with self._memory_lock:
                self._shared_memory['is_running'] = True
            
            logger.info("🔥 GlobalHeatStateMachine已启动")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动GlobalHeatStateMachine失败: {e}")
            self._last_error = str(e)
            return False
    
    def stop(self) -> bool:
        """
        停止异步更新线程
        
        Returns:
            bool: 是否成功停止
        """
        if not self._is_running:
            logger.warning("⚠️ GlobalHeatStateMachine未在运行")
            return False
        
        try:
            self._stop_event.set()
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5.0)
            
            self._is_running = False
            
            # 更新共享内存状态
            with self._memory_lock:
                self._shared_memory['is_running'] = False
            
            # 统计信息
            runtime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            logger.info(f"🛑 GlobalHeatStateMachine已停止 | 运行时间: {runtime:.1f}s | 更新次数: {self._update_count} | 错误次数: {self._error_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 停止GlobalHeatStateMachine失败: {e}")
            return False
    
    def _check_qmt_connection(self) -> bool:
        """
        检查QMT连接状态
        
        Returns:
            bool: 连接是否正常
        """
        try:
            test_code = self.watch_list[0] if self.watch_list else '000001.SZ'
            tick_data = xtdata.get_full_tick([test_code])
            return tick_data is not None and len(tick_data) > 0
        except Exception as e:
            logger.error(f"❌ QMT连接检查失败: {e}")
            return False
    
    def _update_loop(self):
        """
        每3秒执行的更新循环（后台线程）
        """
        logger.info("🔥 热力更新循环已启动")
        
        while not self._stop_event.is_set():
            try:
                cycle_start = time.time()
                
                # 计算热力
                heat_data = self._calculate_heat()
                
                # 更新共享内存
                self._update_shared_memory(heat_data)
                
                self._update_count += 1
                
                # 计算下次更新时间
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.update_interval - elapsed)
                
                if sleep_time > 0:
                    # 使用stop_event.wait以便响应停止信号
                    if self._stop_event.wait(timeout=sleep_time):
                        break
                
            except Exception as e:
                self._error_count += 1
                self._last_error = str(e)
                logger.error(f"❌ 热力更新循环异常: {e}")
                
                # 错误后等待一段时间再重试
                if self._stop_event.wait(timeout=1.0):
                    break
        
        logger.info("🛑 热力更新循环已退出")
    
    def _calculate_heat(self) -> Dict[str, Any]:
        """
        计算成交额增量和热力排名
        
        核心算法:
        1. 获取所有关注股票的实时tick数据
        2. 计算每只股票的成交额增量（当前 - 上次）
        3. 按成交额增量排序，生成热力排名
        
        Returns:
            Dict: 热力数据
        """
        timestamp = datetime.now()
        stock_heats = {}
        total_amount_delta = 0.0
        
        try:
            # 1. 批量获取全推tick数据
            tick_data = xtdata.get_full_tick(self.watch_list)
            
            if not tick_data:
                logger.warning("⚠️ get_full_tick返回空数据")
                return self._create_empty_heat_data(timestamp)
            
            # 2. 计算每只股票的成交额增量
            for qmt_code in self.watch_list:
                try:
                    if qmt_code not in tick_data:
                        continue
                    
                    tick = tick_data[qmt_code]
                    current_amount = tick.get('amount', 0)
                    
                    # 获取上次的成交额
                    last_amount = self._get_last_amount(qmt_code)
                    
                    # 计算增量（绝对值）
                    amount_delta = current_amount - last_amount if last_amount > 0 else 0
                    
                    # 存储历史数据
                    self._store_amount_history(qmt_code, current_amount, timestamp)
                    
                    # 计算热力分数（基于成交额增量的对数归一化）
                    heat_score = self._calculate_heat_score(amount_delta)
                    
                    stock_heats[qmt_code] = {
                        'amount_delta': amount_delta,
                        'current_amount': current_amount,
                        'heat_score': heat_score,
                        'rank': 0,  # 稍后计算
                        'last_price': tick.get('lastPrice', 0),
                        'pct_change': self._calculate_pct_change(tick)
                    }
                    
                    total_amount_delta += amount_delta
                    
                except Exception as e:
                    logger.warning(f"⚠️ 计算股票热力失败 {qmt_code}: {e}")
                    continue
            
            # 3. 按成交额增量排序，生成排名
            sorted_stocks = sorted(
                stock_heats.items(),
                key=lambda x: x[1]['amount_delta'],
                reverse=True
            )
            
            for rank, (code, data) in enumerate(sorted_stocks, 1):
                stock_heats[code]['rank'] = rank
            
            return {
                'timestamp': timestamp,
                'stock_heats': stock_heats,
                'total_amount_delta': total_amount_delta,
                'stock_count': len(stock_heats)
            }
            
        except Exception as e:
            logger.error(f"❌ 计算热力失败: {e}")
            return self._create_empty_heat_data(timestamp)
    
    def _get_last_amount(self, code: str) -> float:
        """
        获取上次的成交额
        
        Args:
            code: 股票代码
            
        Returns:
            float: 上次成交额，如果没有则返回0
        """
        with self._history_lock:
            history = self._amount_history.get(code, [])
            if history:
                return history[-1]['amount']
            return 0.0
    
    def _store_amount_history(self, code: str, amount: float, timestamp: datetime):
        """
        存储成交额历史数据
        
        Args:
            code: 股票代码
            amount: 当前成交额
            timestamp: 时间戳
        """
        with self._history_lock:
            self._amount_history[code].append({
                'amount': amount,
                'timestamp': timestamp
            })
            
            # 只保留最近100条记录（约5分钟）
            if len(self._amount_history[code]) > 100:
                self._amount_history[code] = self._amount_history[code][-100:]
    
    def _calculate_heat_score(self, amount_delta: float) -> float:
        """
        计算热力分数
        
        算法: 基于成交额增量的对数归一化
        - amount_delta <= 0: score = 0
        - amount_delta > 0: score = min(100, log10(amount_delta / 10000) * 10)
        
        Args:
            amount_delta: 成交额增量（元）
            
        Returns:
            float: 热力分数 (0-100)
        """
        if amount_delta <= 0:
            return 0.0
        
        # 转换为万元
        amount_wan = amount_delta / 10000
        
        # 对数归一化
        import math
        score = min(100.0, math.log10(max(1, amount_wan)) * 10)
        
        return round(score, 2)
    
    def _calculate_pct_change(self, tick: Dict) -> float:
        """
        计算涨跌幅
        
        Args:
            tick: tick数据
            
        Returns:
            float: 涨跌幅（%）
        """
        last_price = tick.get('lastPrice', 0)
        last_close = tick.get('lastClose', 0)
        
        if last_close > 0:
            return round((last_price - last_close) / last_close * 100, 2)
        return 0.0
    
    def _create_empty_heat_data(self, timestamp: datetime) -> Dict[str, Any]:
        """
        创建空的热力数据
        
        Args:
            timestamp: 时间戳
            
        Returns:
            Dict: 空热力数据结构
        """
        return {
            'timestamp': timestamp,
            'stock_heats': {},
            'total_amount_delta': 0.0,
            'stock_count': 0,
            'error': True
        }
    
    def _update_shared_memory(self, heat_data: Dict[str, Any]):
        """
        更新共享内存数据
        
        Args:
            heat_data: 热力数据
        """
        with self._memory_lock:
            self._shared_memory['heat_data'] = heat_data
            self._shared_memory['last_update'] = datetime.now()
    
    def get_heat_rank(self, stock_code: str) -> Dict[str, Any]:
        """
        获取某票当前热度排名（毫秒级响应）
        
        Args:
            stock_code: 股票代码（6位或QMT格式）
            
        Returns:
            Dict: 热度排名信息
        """
        try:
            # 标准化代码
            qmt_code = CodeConverter.to_qmt(stock_code)
            
            with self._memory_lock:
                heat_data = self._shared_memory.get('heat_data', {})
                stock_heats = heat_data.get('stock_heats', {})
                
                if qmt_code in stock_heats:
                    data = stock_heats[qmt_code].copy()
                    data['code'] = stock_code
                    data['qmt_code'] = qmt_code
                    data['timestamp'] = heat_data.get('timestamp')
                    data['is_valid'] = True
                    return data
                else:
                    return {
                        'code': stock_code,
                        'qmt_code': qmt_code,
                        'rank': -1,
                        'amount_delta': 0,
                        'heat_score': 0,
                        'is_valid': False,
                        'message': '股票不在关注列表或无数据'
                    }
                    
        except Exception as e:
            logger.error(f"❌ 获取热度排名失败 {stock_code}: {e}")
            return {
                'code': stock_code,
                'rank': -1,
                'amount_delta': 0,
                'heat_score': 0,
                'is_valid': False,
                'message': f'查询失败: {str(e)}'
            }
    
    def get_all_ranks(self) -> List[Dict[str, Any]]:
        """
        获取全池排名（毫秒级响应）
        
        Returns:
            List[Dict]: 按排名排序的股票列表
        """
        try:
            with self._memory_lock:
                heat_data = self._shared_memory.get('heat_data', {})
                stock_heats = heat_data.get('stock_heats', {})
                
                # 转换为列表并排序
                ranks = []
                for qmt_code, data in stock_heats.items():
                    item = data.copy()
                    item['qmt_code'] = qmt_code
                    item['code'] = CodeConverter.to_6digit(qmt_code)
                    ranks.append(item)
                
                # 按排名排序
                ranks.sort(key=lambda x: x.get('rank', 999))
                
                return ranks
                
        except Exception as e:
            logger.error(f"❌ 获取全池排名失败: {e}")
            return []
    
    def get_market_heat_summary(self) -> Dict[str, Any]:
        """
        获取市场整体热度摘要
        
        Returns:
            Dict: 市场热度摘要
        """
        try:
            with self._memory_lock:
                heat_data = self._shared_memory.get('heat_data', {})
                
                # 计算热度分布
                stock_heats = heat_data.get('stock_heats', {})
                heat_scores = [s['heat_score'] for s in stock_heats.values()]
                
                high_heat = len([s for s in heat_scores if s >= 50])
                medium_heat = len([s for s in heat_scores if 20 <= s < 50])
                low_heat = len([s for s in heat_scores if s < 20])
                
                return {
                    'timestamp': heat_data.get('timestamp'),
                    'last_update': self._shared_memory.get('last_update'),
                    'is_running': self._is_running,
                    'total_amount_delta': heat_data.get('total_amount_delta', 0),
                    'stock_count': heat_data.get('stock_count', 0),
                    'heat_distribution': {
                        'high': high_heat,
                        'medium': medium_heat,
                        'low': low_heat
                    },
                    'avg_heat_score': sum(heat_scores) / len(heat_scores) if heat_scores else 0,
                    'update_count': self._update_count,
                    'error_count': self._error_count,
                    'last_error': self._last_error
                }
                
        except Exception as e:
            logger.error(f"❌ 获取市场热度摘要失败: {e}")
            return {
                'is_running': self._is_running,
                'error': str(e)
            }
    
    def is_running(self) -> bool:
        """
        检查是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self._is_running
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取状态信息
        
        Returns:
            Dict: 状态信息
        """
        runtime = 0
        if self._start_time and self._is_running:
            runtime = (datetime.now() - self._start_time).total_seconds()
        
        return {
            'is_running': self._is_running,
            'watch_list_count': len(self.watch_list),
            'update_interval': self.update_interval,
            'update_count': self._update_count,
            'error_count': self._error_count,
            'runtime_seconds': runtime,
            'last_error': self._last_error,
            'start_time': self._start_time.isoformat() if self._start_time else None
        }


# 便捷函数：快速创建和启动
def create_and_start_heat_state_machine(
    watch_list: List[str],
    update_interval: int = 3
) -> GlobalHeatStateMachine:
    """
    创建并启动全局热力状态机
    
    Args:
        watch_list: 关注股票代码列表
        update_interval: 更新间隔（秒）
        
    Returns:
        GlobalHeatStateMachine: 已启动的状态机实例
    """
    gsm = GlobalHeatStateMachine(watch_list, update_interval)
    gsm.start()
    return gsm


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 模拟关注列表
    test_watch_list = [
        '000001',  # 平安银行
        '000002',  # 万科A
        '600519',  # 贵州茅台
        '300750',  # 宁德时代
        '000858',  # 五粮液
    ]
    
    # 创建并启动
    gsm = GlobalHeatStateMachine(test_watch_list, update_interval=3)
    
    if gsm.start():
        print("✅ 全局热力状态机已启动")
        
        try:
            # 运行测试
            for i in range(10):
                time.sleep(3)
                
                # 查询单只股票
                rank = gsm.get_heat_rank('000001')
                print(f"\n📊 000001 热度排名: {rank}")
                
                # 查询全池排名（前3）
                all_ranks = gsm.get_all_ranks()[:3]
                print(f"\n🏆 TOP3热度:")
                for r in all_ranks:
                    print(f"  {r['code']}: 排名={r['rank']}, 热力={r['heat_score']}, 增量={r['amount_delta']/10000:.2f}万")
                
                # 市场摘要
                summary = gsm.get_market_heat_summary()
                print(f"\n📈 市场热度: 高={summary['heat_distribution']['high']}, 中={summary['heat_distribution']['medium']}, 低={summary['heat_distribution']['low']}")
        
        except KeyboardInterrupt:
            print("\n🛑 用户中断")
        
        finally:
            gsm.stop()
            print("✅ 全局热力状态机已停止")
    else:
        print("❌ 启动失败")