#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场扫描引擎（三阶段渐进式筛选）

核心架构：
  阶段1：预筛选（硬性条件，1分钟） → 5000股 → 200-400股
  阶段2：四维初筛（简化QPST，3分钟） → 200-400股 → 50-100股
  阶段3：精准QPST（完整分析，5分钟） → 50-100股 → 20-50股

使用场景：
  - 每天2-3次扫描（09:35, 10:00, 14:00）
  - 输出TOP 20-50诱多榜单
  - 日报/周报生成

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import time
import json
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.batch_qpst_analyzer import BatchQPSTAnalyzer
from logic.logger import get_logger

logger = get_logger(__name__)


class MarketScanner:
    """
    全市场扫描器（三阶段渐进式筛选）
    
    功能：
    1. 阶段1：预筛选（硬性条件）
    2. 阶段2：四维初筛（简化QPST）
    3. 阶段3：精准QPST（完整分析）
    4. 智能并行（自动选择单/多进程）
    5. 数据缓存（本地CSV备份）
    """
    
    def __init__(self, 
                 equity_info: dict,
                 cache_dir: str = 'data/kline_cache',
                 enable_cache: bool = True,
                 parallel_threshold: int = 100):
        """
        初始化市场扫描器
        
        Args:
            equity_info: 股本信息字典 {code: {float_shares, total_shares}}
            cache_dir: 本地缓存目录
            enable_cache: 是否启用缓存
            parallel_threshold: 并行阈值（候选股票数>此值时使用多进程）
        """
        if not QMT_AVAILABLE:
            raise RuntimeError("⚠️ xtquant 未安装，MarketScanner 不可用")
        
        self.equity_info = equity_info
        self.cache_dir = Path(cache_dir)
        self.enable_cache = enable_cache
        self.parallel_threshold = parallel_threshold
        
        # 初始化分析器
        self.analyzer = BatchQPSTAnalyzer(equity_info)
        
        # 创建缓存目录
        if enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ MarketScanner 初始化完成")
        logger.info(f"   - 股本信息: {len(equity_info)} 只股票")
        logger.info(f"   - 缓存目录: {cache_dir}")
        logger.info(f"   - 并行阈值: {parallel_threshold}")
    
    
    def scan(self, stock_list: List[str], scan_time: str = None) -> List[dict]:
        """
        执行全市场扫描
        
        Args:
            stock_list: 股票代码列表（如 ['300997.SZ', '603697.SH', ...]）
            scan_time: 扫描时间节点（'09:35' | '10:00' | '14:00'，默认当前时间）
        
        Returns:
            TOP 50 诱多榜单
        """
        scan_time = scan_time or datetime.now().strftime('%H:%M')
        logger.info("="*80)
        logger.info(f"🚀 启动全市场扫描 - {scan_time}")
        logger.info(f"📊 扫描范围: {len(stock_list)} 只股票")
        logger.info("="*80)
        
        start_time = time.time()
        
        # ===== 阶段1：预筛选（硬性条件） =====
        logger.info("\n🔍 阶段1：预筛选（硬性条件）...")
        phase1_start = time.time()
        candidates = self._phase1_pre_filter(stock_list)
        phase1_time = time.time() - phase1_start
        logger.info(f"✅ 阶段1完成: {len(stock_list)} → {len(candidates)} 只股票 (耗时: {phase1_time:.1f}秒)")
        
        if not candidates:
            logger.warning("⚠️ 阶段1未发现候选股票，扫描结束")
            return []
        
        # ===== 阶段2：四维初筛（简化QPST） =====
        logger.info("\n🔍 阶段2：四维初筛（简化QPST）...")
        phase2_start = time.time()
        potentials = self._phase2_qpst_lite(candidates)
        phase2_time = time.time() - phase2_start
        logger.info(f"✅ 阶段2完成: {len(candidates)} → {len(potentials)} 只股票 (耗时: {phase2_time:.1f}秒)")
        
        if not potentials:
            logger.warning("⚠️ 阶段2未发现潜在股票，扫描结束")
            return []
        
        # ===== 阶段3：精准QPST（完整分析） =====
        logger.info("\n🔍 阶段3：精准QPST（完整分析）...")
        phase3_start = time.time()
        trap_list = self._phase3_qpst_full(potentials)
        phase3_time = time.time() - phase3_start
        logger.info(f"✅ 阶段3完成: {len(potentials)} → {len(trap_list)} 只股票 (耗时: {phase3_time:.1f}秒)")
        
        # 按置信度排序
        trap_list.sort(key=lambda x: x['confidence'], reverse=True)
        top_50 = trap_list[:50]
        
        total_time = time.time() - start_time
        logger.info("\n" + "="*80)
        logger.info(f"🎉 扫描完成！共发现 {len(top_50)} 只疑似诱多股票")
        logger.info(f"⏱️  总耗时: {total_time:.1f}秒")
        logger.info("="*80)
        
        return top_50
    
    
    def _phase1_pre_filter(self, stock_list: List[str]) -> List[str]:
        """
        阶段1：预筛选（硬性条件）
        
        目标: 5000股 → 200-400股（1分钟内完成）
        
        条件:
        1. 涨幅 > 2%
        2. 换手率 > 3%（10分钟）
        3. 放量 > 1.3倍
        """
        candidates = []
        
        try:
            # 批量获取最新数据（一次性获取所有股票）
            logger.debug("  正在批量获取分钟K数据...")
            kline_data = xtdata.get_market_data_ex(
                field_list=['close', 'volume'],
                stock_list=stock_list,
                period='1m',
                count=10,  # 最近10根分钟K
                dividend_type='none',
                fill_data=False
            )
            
            logger.debug(f"  成功获取 {len(kline_data)} 只股票数据")
            
            for code in stock_list:
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
            logger.debug(traceback.format_exc())
        
        return candidates
    
    
    def _phase2_qpst_lite(self, candidates: List[str]) -> List[str]:
        """
        阶段2：四维初筛（简化QPST）
        
        目标: 200-400股 → 50-100股（3分钟内完成）
        
        只计算关键指标，不做完整分析
        """
        potentials = []
        
        try:
            # 批量获取分钟K数据
            logger.debug("  正在批量获取分钟K数据...")
            kline_data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=candidates,
                period='1m',
                count=10,
                dividend_type='none',
                fill_data=False
            )
            
            for code in candidates:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                if len(df) < 10:
                    continue
                
                # 添加time列（用于时间判断）
                if 'time' not in df.columns:
                    df['time'] = pd.date_range(end=datetime.now(), periods=len(df), freq='1min').time
                
                # 快速四维判断
                dims = self.analyzer.analyze_lite(df, code)
                
                # 至少2个维度异常才进入下一阶段
                abnormal_count = sum(1 for v in dims.values() if v == 'ABNORMAL')
                
                if abnormal_count >= 2:
                    potentials.append(code)
            
        except Exception as e:
            logger.error(f"❌ 阶段2初筛失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return potentials
    
    
    def _phase3_qpst_full(self, potentials: List[str]) -> List[dict]:
        """
        阶段3：精准QPST（完整分析）
        
        目标: 50-100股 → 20-50股（5分钟内完成）
        
        执行完整的四维分析 + 反诱多检测
        """
        trap_list = []
        
        # 智能选择单进程或多进程
        use_parallel = len(potentials) > self.parallel_threshold
        
        if use_parallel:
            logger.info(f"  使用多进程并行（{len(potentials)}只股票 > {self.parallel_threshold}）")
            trap_list = self._analyze_parallel(potentials)
        else:
            logger.info(f"  使用单进程串行（{len(potentials)}只股票 ≤ {self.parallel_threshold}）")
            trap_list = self._analyze_serial(potentials)
        
        # 过滤出诱多预警
        trap_list = [r for r in trap_list if r and r['final_signal'] == 'TRAP_WARNING']
        
        return trap_list
    
    
    def _analyze_serial(self, stock_list: List[str]) -> List[dict]:
        """
        单进程串行分析
        """
        results = []
        
        try:
            # 批量获取分钟K数据
            kline_data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_list,
                period='1m',
                count=30,  # 完整分析需要更多数据
                dividend_type='none',
                fill_data=False
            )
            
            for code in stock_list:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                if len(df) < 20:
                    continue
                
                # 添加time列
                if 'time' not in df.columns:
                    df['time'] = pd.date_range(end=datetime.now(), periods=len(df), freq='1min').time
                
                # 执行完整QPST分析
                result = self.analyzer.analyze_full(df, code)
                if result:
                    results.append(result)
        
        except Exception as e:
            logger.error(f"❌ 串行分析失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return results
    
    
    def _analyze_parallel(self, stock_list: List[str]) -> List[dict]:
        """
        多进程并行分析
        """
        results = []
        
        try:
            # 批量获取分钟K数据（主进程）
            kline_data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_list,
                period='1m',
                count=30,
                dividend_type='none',
                fill_data=False
            )
            
            # 准备分析任务
            tasks = []
            for code in stock_list:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                if len(df) < 20:
                    continue
                
                # 添加time列
                if 'time' not in df.columns:
                    df['time'] = pd.date_range(end=datetime.now(), periods=len(df), freq='1min').time
                
                tasks.append((df, code, self.equity_info))
            
            # 多进程执行
            num_processes = min(cpu_count(), 8)  # 最多8个进程
            logger.debug(f"  启动 {num_processes} 个进程...")
            
            with Pool(processes=num_processes) as pool:
                results = pool.starmap(self._analyze_single_stock_worker, tasks)
            
            # 过滤空结果
            results = [r for r in results if r is not None]
        
        except Exception as e:
            logger.error(f"❌ 并行分析失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return results
    
    
    @staticmethod
    def _analyze_single_stock_worker(df: pd.DataFrame, code: str, equity_info: dict) -> Optional[dict]:
        """
        单股票分析工作函数（供多进程调用）
        
        注意：此函数在子进程中执行，需要重新初始化analyzer
        """
        try:
            # 在子进程中创建analyzer
            analyzer = BatchQPSTAnalyzer(equity_info)
            result = analyzer.analyze_full(df, code)
            return result
        except Exception as e:
            # 子进程中的异常不会传递到主进程，需要记录
            return None
    
    
    def save_results(self, results: List[dict], output_dir: str = 'data/scan_results'):
        """
        保存扫描结果
        
        Args:
            results: 扫描结果列表
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # 保存JSON
        json_file = output_path / f'scan_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 扫描结果已保存: {json_file}")
        
        return str(json_file)
