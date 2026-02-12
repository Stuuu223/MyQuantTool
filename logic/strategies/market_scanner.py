#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场批量扫描器（三阶段渐进式筛选）

核心设计：
- 阶段1: 预筛选（硬性条件） → 5000股筛到200-400股
- 阶段2: 四维初筛（简化QPST） → 200-400股筛到50-100股
- 阶段3: 精准QPST（完整分析） → 50-100股筛到20-50股

优势：
- 高效：总扫描时间控制在5-10分钟内
- 精准：逐层筛选，避免误报
- 可扩展：易于添加新的筛选维度

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import time
import pandas as pd
from typing import List, Dict, Optional
from multiprocessing import Pool, cpu_count
from functools import partial

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.batch_qpst_analyzer import BatchQPSTAnalyzer
from logic.trap_detector_batch import TrapDetectorBatch
from logic.logger import get_logger

logger = get_logger(__name__)


class MarketScanner:
    """
    全市场批量扫描器
    
    三阶段渐进式筛选：
    1. 预筛选：快速剔除90%不活跃股票
    2. 初筛：简化四维分析，识别明显异常
    3. 精筛：完整QPST分析+反诱多检测
    """
    
    def __init__(self, equity_info: dict, use_multiprocess: bool = True, batch_size: int = 500):
        """
        初始化扫描器
        
        Args:
            equity_info: 股本信息字典
            use_multiprocess: 是否使用多进程加速
            batch_size: 预筛选分批大小（默认500只/批）
        """
        if not QMT_AVAILABLE:
            raise RuntimeError("⚠️ xtquant 未安装，MarketScanner 不可用")
        
        self.equity_info = equity_info
        self.use_multiprocess = use_multiprocess
        self.batch_size = batch_size  # 🔥 [P1 FIX] 分批大小配置
        
        # 初始化分析器
        self.qpst_analyzer = BatchQPSTAnalyzer(equity_info, config_path="config/phase2_config.yaml")
        self.trap_detector = TrapDetectorBatch()
        
        logger.info("="*80)
        logger.info("✅ MarketScanner 初始化完成")
        logger.info(f"   - 股本信息: {len(equity_info)} 只股票")
        logger.info(f"   - 多进程: {'启用' if use_multiprocess else '禁用'}")
        logger.info(f"   - 分批大小: {batch_size} 只/批")  # 🔥 [P1 FIX]
        logger.info("="*80)
    
    def scan(self, stock_list: List[str], scan_time: str = '09:35') -> List[Dict]:
        """
        执行全市场扫描
        
        Args:
            stock_list: 股票代码列表
            scan_time: 扫描时间节点 ('09:35' | '10:00' | '14:00')
        
        Returns:
            TOP 20-50 诱多榜单
        """
        logger.info("\n" + "="*80)
        logger.info(f"🔍 开始全市场扫描 - {scan_time}")
        logger.info(f"   扫描股票数: {len(stock_list)}")
        logger.info("="*80)
        
        start_time = time.time()
        
        # ===== 阶段1: 预筛选 =====
        phase1_start = time.time()
        candidates = self._phase1_pre_filter(stock_list, scan_time)
        phase1_time = time.time() - phase1_start
        
        logger.info(f"\n✅ 阶段1完成: {len(stock_list)} → {len(candidates)} 只股票")
        logger.info(f"   耗时: {phase1_time:.1f}秒")
        
        if len(candidates) == 0:
            logger.warning("⚠️ 预筛选后无候选股票，扫描结束")
            return []
        
        # ===== 阶段2: 四维初筛 =====
        phase2_start = time.time()
        potentials = self._phase2_qpst_lite(candidates)
        phase2_time = time.time() - phase2_start
        
        logger.info(f"\n✅ 阶段2完成: {len(candidates)} → {len(potentials)} 只股票")
        logger.info(f"   耗时: {phase2_time:.1f}秒")
        
        if len(potentials) == 0:
            logger.warning("⚠️ 初筛后无候选股票，扫描结束")
            return []
        
        # ===== 阶段3: 精准QPST =====
        phase3_start = time.time()
        trap_list = self._phase3_qpst_full(potentials)
        phase3_time = time.time() - phase3_start
        
        logger.info(f"\n✅ 阶段3完成: {len(potentials)} → {len(trap_list)} 只股票")
        logger.info(f"   耗时: {phase3_time:.1f}秒")
        
        # 按置信度排序
        trap_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        total_time = time.time() - start_time
        logger.info("\n" + "="*80)
        logger.info(f"🎯 扫描完成！总耗时: {total_time:.1f}秒")
        logger.info(f"   输出榜单: TOP {len(trap_list[:50])}")
        logger.info("="*80 + "\n")
        
        return trap_list[:50]
    
    def _phase1_pre_filter(self, stock_list: List[str], scan_time: str) -> List[str]:
        """
        阶段1: 预筛选（硬性条件）
        
        目标: 5000股 → 200-400股（1分钟内完成）
        
        筛选条件:
        1. 涨幅 > 2%
        2. 换手率 > 3%（基于10分钟累计成交量）
        3. 放量 > 1.3倍
        
        🔥 [P1 FIX] 分批获取K线数据，避免内存溢出
        """
        logger.info("\n⏳ 阶段1: 预筛选（硬性条件）...")
        logger.info(f"   分批大小: {self.batch_size} 只/批")
        logger.info(f"   预计批次数: {(len(stock_list) + self.batch_size - 1) // self.batch_size}")
        
        candidates = []
        
        # 根据扫描时间确定K线数量
        kline_count = self._get_kline_count(scan_time)
        
        try:
            # 🔥 [P1 FIX] 分批获取K线数据
            for batch_idx in range(0, len(stock_list), self.batch_size):
                batch = stock_list[batch_idx:batch_idx + self.batch_size]
                
                logger.debug(f"   处理批次 {batch_idx // self.batch_size + 1}/{(len(stock_list) + self.batch_size - 1) // self.batch_size}: {len(batch)} 只股票")
                
                # 批量获取分钟K数据
                kline_data = xtdata.get_market_data_ex(
                    field_list=['close', 'volume'],
                    stock_list=batch,
                    period='1m',
                    count=kline_count
                )
                
                # 处理批次数据
                for code in batch:
                    if code not in kline_data:
                        continue
                    
                    df = kline_data[code]
                    
                    if len(df) < 10:
                        continue
                    
                    # 计算涨幅
                    price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
                    
                    # 计算量比
                    recent_vol = df['volume'].iloc[-3:].mean()
                    earlier_vol = df['volume'].iloc[:-3].mean()
                    volume_ratio = recent_vol / earlier_vol if earlier_vol > 0 else 0
                    
                    # 计算换手率
                    float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
                    if float_shares > 0:
                        turnover = df['volume'].sum() / float_shares
                    else:
                        turnover = 0
                    
                    # 硬性筛选条件
                    if price_change > 0.02 and turnover > 0.03 and volume_ratio > 1.3:
                        candidates.append(code)
        
        except Exception as e:
            logger.error(f"❌ 阶段1预筛选失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return candidates
    
    def _phase2_qpst_lite(self, candidates: List[str]) -> List[str]:
        """
        阶段2: 四维初筛（简化QPST）
        
        目标: 200-400股 → 50-100股（3分钟内完成）
        
        只计算关键指标，不做完整分析
        """
        logger.info("\n⏳ 阶段2: 四维初筛（简化QPST）...")
        
        potentials = []
        
        for code in candidates:
            try:
                # 获取分钟K数据
                df = self._get_kline(code, count=10)
                if df is None or len(df) < 10:
                    continue
                
                # 快速四维判断（简化版）
                abnormal_count = 0
                
                # 量能异常
                volumes = df['volume'].values
                volume_ratio = volumes[-3:].mean() / volumes[:-3].mean() if volumes[:-3].mean() > 0 else 0
                if volume_ratio > 2.0:
                    abnormal_count += 1
                
                # 价格异常
                price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
                amplitude = ((df['high'] - df['low']) / df['close']).mean()
                if price_change > 0.03 or amplitude > 0.03:
                    abnormal_count += 1
                
                # 换手率异常
                float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
                if float_shares > 0:
                    turnover = df['volume'].sum() / float_shares
                    if turnover > 0.02:
                        abnormal_count += 1
                
                # 至少2个维度异常才进入下一阶段
                if abnormal_count >= 2:
                    potentials.append(code)
            
            except Exception as e:
                logger.debug(f"阶段2分析 {code} 失败: {e}")
                continue
        
        return potentials
    
    def _phase3_qpst_full(self, potentials: List[str]) -> List[Dict]:
        """
        阶段3: 精准QPST（完整分析）
        
        目标: 50-100股 → 20-50股（5分钟内完成）
        
        执行完整的四维分析 + 反诱多检测
        """
        logger.info("\n⏳ 阶段3: 精准QPST（完整分析）...")
        
        trap_list = []
        
        # 智能选择单进程或多进程
        if self.use_multiprocess and len(potentials) > 100:
            # 多进程加速
            logger.info(f"   使用多进程加速（{cpu_count()} 核心）")
            with Pool(processes=min(cpu_count(), 8)) as pool:
                results = pool.map(self._analyze_single_stock, potentials)
            
            trap_list = [r for r in results if r is not None]
        else:
            # 单进程
            for code in potentials:
                result = self._analyze_single_stock(code)
                if result:
                    trap_list.append(result)
        
        return trap_list
    
    def _analyze_single_stock(self, code: str) -> Optional[Dict]:
        """
        单股票完整QPST分析
        """
        try:
            # 获取更长时间的分钟K（用于完整分析）
            df = self._get_kline(code, count=30)
            if df is None or len(df) < 20:
                return None
            
            # 执行完整四维分析
            qpst_result = self.qpst_analyzer.analyze(code, df)
            
            # 反诱多检测
            trap_signals = self.trap_detector.detect(code, df, qpst_result)
            
            # 判断是否为诱多
            vote_result = qpst_result['vote_result']
            
            # 如果有诱多信号，直接标记为诱多
            if trap_signals:
                final_signal = 'TRAP_WARNING'
                confidence = 0.9
                reason = f"诱多预警: {'; '.join(trap_signals)}"
            # 如果四维分析显示异常
            elif vote_result['level'] in ['STRONG', 'MODERATE']:
                final_signal = 'POTENTIAL_TRAP'
                confidence = vote_result['confidence']
                reason = f"四维异常: {'+'.join(vote_result['positive_dims'])}"
            else:
                return None
            
            # 获取当前价格信息
            current_price = df['close'].iloc[-1]
            price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
            
            return {
                'code': code,
                'final_signal': final_signal,
                'confidence': confidence,
                'reason': reason,
                'trap_signals': trap_signals,
                'current_price': round(current_price, 2),
                'price_change': round(price_change, 4),
                'qpst_result': qpst_result,
                'timestamp': time.strftime('%H:%M:%S')
            }
        
        except Exception as e:
            logger.debug(f"分析 {code} 失败: {e}")
            return None
    
    def _get_kline(self, code: str, count: int = 10) -> Optional[pd.DataFrame]:
        """
        获取分钟K数据
        """
        try:
            kline = xtdata.get_market_data_ex(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
                stock_list=[code],
                period='1m',
                count=count
            )
            
            if code in kline:
                return kline[code]
        
        except Exception as e:
            logger.debug(f"获取 {code} K线数据失败: {e}")
        
        return None
    
    def _get_kline_count(self, scan_time: str) -> int:
        """
        根据扫描时间确定需要的K线数量
        """
        time_mapping = {
            '09:35': 10,  # 开盘5分钟
            '10:00': 30,  # 开盘30分钟
            '14:00': 90,  # 午盘1小时
        }
        return time_mapping.get(scan_time, 10)
