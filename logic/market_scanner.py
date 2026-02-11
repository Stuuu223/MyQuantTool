#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场批量扫描器（三阶段渐进式筛选）

目标：
- 扫描全A股5000+股票
- 识别疑似诱多股票（TOP 20-50）
- 执行时间：<10分钟

三阶段筛选：
1. 预筛选（1分钟）：5000股 → 200-400股（硬性条件）
2. 四维初筛（3分钟）：200-400股 → 50-100股（简化QPST）
3. 精准QPST（5分钟）：50-100股 → 20-50股（完整分析）

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
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
    全市场批量扫描器
    
    特性：
    - 三阶段渐进式筛选（粗筛→初筛→精筛）
    - 智能并行（<100股单进程，>100股多进程）
    - QMT实时数据 + CSV备份机制
    - 内存优化（只保留必要数据）
    """
    
    def __init__(self, equity_info_path: str = 'data/equity_info.json'):
        """
        初始化市场扫描器
        
        Args:
            equity_info_path: 股本信息文件路径
        """
        if not QMT_AVAILABLE:
            raise RuntimeError("⚠️ xtquant 未安装，MarketScanner 不可用")
        
        # 加载股本信息
        self.equity_info = self._load_equity_info(equity_info_path)
        
        # 初始化批量分析器
        self.analyzer = BatchQPSTAnalyzer(self.equity_info)
        
        # CSV缓存目录
        self.cache_dir = Path('data/kline_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ MarketScanner 初始化完成")
        logger.info(f"   - 股本信息: {len(self.equity_info)} 只股票")
        logger.info(f"   - 缓存目录: {self.cache_dir}")
    
    def _load_equity_info(self, path: str) -> dict:
        """加载股本信息"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                equity_info = json.load(f)
            logger.debug(f"✅ 加载股本信息: {len(equity_info)} 只股票")
            return equity_info
        except Exception as e:
            logger.warning(f"⚠️ 加载股本信息失败: {e}，将使用空字典")
            return {}
    
    def scan(self, stock_list: List[str], scan_time: str = 'auto') -> List[dict]:
        """
        扫描全市场
        
        Args:
            stock_list: 股票代码列表（如 ['300997.SZ', '603697.SH', ...]）
            scan_time: 扫描时间节点（'09:35' | '10:00' | '14:00' | 'auto'）
        
        Returns:
            TOP 20-50 诱多榜单
        """
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("🚀 全市场扫描启动")
        logger.info("="*80)
        logger.info(f"扫描范围: {len(stock_list)} 只股票")
        logger.info(f"扫描时间: {scan_time}")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        # ===== 阶段1: 预筛选（硬性条件） =====
        logger.info("\n📊 阶段1: 预筛选（硬性条件）")
        phase1_start = time.time()
        candidates = self._phase1_pre_filter(stock_list)
        phase1_time = time.time() - phase1_start
        logger.info(f"✅ 阶段1完成: {len(stock_list)} → {len(candidates)} 只股票 (耗时 {phase1_time:.1f}秒)")
        
        if not candidates:
            logger.warning("⚠️ 预筛选后无候选股票，终止扫描")
            return []
        
        # ===== 阶段2: 四维初筛（简化QPST） =====
        logger.info("\n📊 阶段2: 四维初筛（简化QPST）")
        phase2_start = time.time()
        potentials = self._phase2_qpst_lite(candidates)
        phase2_time = time.time() - phase2_start
        logger.info(f"✅ 阶段2完成: {len(candidates)} → {len(potentials)} 只股票 (耗时 {phase2_time:.1f}秒)")
        
        if not potentials:
            logger.warning("⚠️ 四维初筛后无候选股票，终止扫描")
            return []
        
        # ===== 阶段3: 精准QPST（完整分析） =====
        logger.info("\n📊 阶段3: 精准QPST（完整分析）")
        phase3_start = time.time()
        trap_list = self._phase3_qpst_full(potentials)
        phase3_time = time.time() - phase3_start
        logger.info(f"✅ 阶段3完成: {len(potentials)} → {len(trap_list)} 只股票 (耗时 {phase3_time:.1f}秒)")
        
        # 按置信度排序
        trap_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        total_time = time.time() - start_time
        logger.info("\n" + "="*80)
        logger.info(f"🎯 扫描完成，共耗时 {total_time:.1f}秒")
        logger.info(f"📋 输出榜单: TOP {len(trap_list[:50])} 疑似诱多股票")
        logger.info("="*80)
        
        return trap_list[:50]  # TOP 50
    
    def _phase1_pre_filter(self, stock_list: List[str]) -> List[str]:
        """
        阶段1: 预筛选（硬性条件）
        
        目标: 5000股 → 200-400股（1分钟内完成）
        
        条件:
        1. 涨幅 > 2%
        2. 换手率 > 3%（10分钟）
        3. 放量 > 1.3倍
        """
        candidates = []
        
        try:
            # 批量获取最新10根分钟K（一次性获取所有股票）
            logger.info("   正在批量获取分钟K数据...")
            kline_data = xtdata.get_market_data_ex(
                field_list=['close', 'volume'],
                stock_list=stock_list,
                period='1m',
                count=10
            )
            
            for code in stock_list:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                if len(df) < 10:
                    continue
                
                # 计算涨幅
                price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
                
                # 计算量比
                volumes = df['volume'].values
                recent_vol = volumes[-3:].mean()
                earlier_vol = volumes[:-3].mean()
                volume_ratio = recent_vol / earlier_vol if earlier_vol > 0 else 0
                
                # 计算换手率（需要股本信息）
                float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
                if float_shares > 0:
                    turnover = df['volume'].sum() / float_shares
                else:
                    turnover = 0
                
                # 硬性筛选条件
                if price_change > 0.02 and turnover > 0.03 and volume_ratio > 1.3:
                    candidates.append(code)
                    logger.debug(f"   ✓ {code}: 涨幅{price_change:.2%}, 换手{turnover:.2%}, 量比{volume_ratio:.2f}")
        
        except Exception as e:
            logger.error(f"❌ 阶段1筛选失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return candidates
    
    def _phase2_qpst_lite(self, candidates: List[str]) -> List[str]:
        """
        阶段2: 四维初筛（简化QPST）
        
        目标: 200-400股 → 50-100股（3分钟内完成）
        
        只计算关键指标，不做完整分析
        """
        potentials = []
        
        try:
            # 批量获取分钟K数据
            logger.info("   正在批量获取分钟K数据...")
            kline_data = xtdata.get_market_data_ex(
                field_list=['close', 'high', 'low', 'volume'],
                stock_list=candidates,
                period='1m',
                count=10
            )
            
            for code in candidates:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                if len(df) < 10:
                    continue
                
                # 快速四维判断（简化版）
                abnormal_count = 0
                
                # 量能异常
                volumes = df['volume'].values
                recent_vol = volumes[-3:].mean()
                earlier_vol = volumes[:-3].mean()
                if earlier_vol > 0 and recent_vol / earlier_vol > 2.5:
                    abnormal_count += 1
                
                # 价格异常（振幅过大）
                amplitudes = (df['high'] - df['low']) / df['close']
                if amplitudes.mean() > 0.025:
                    abnormal_count += 1
                
                # 换手率异常
                float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
                if float_shares > 0:
                    turnover = df['volume'].sum() / float_shares
                    if turnover > 0.02:  # 10分钟换手>2%
                        abnormal_count += 1
                
                # 至少2个维度异常才进入下一阶段
                if abnormal_count >= 2:
                    potentials.append(code)
                    logger.debug(f"   ✓ {code}: {abnormal_count}个维度异常")
        
        except Exception as e:
            logger.error(f"❌ 阶段2筛选失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return potentials
    
    def _phase3_qpst_full(self, potentials: List[str]) -> List[dict]:
        """
        阶段3: 精准QPST（完整分析）
        
        目标: 50-100股 → 20-50股（5分钟内完成）
        
        执行完整的四维分析 + 反诱多检测
        """
        trap_list = []
        
        try:
            # 批量获取更长时间的分钟K（用于完整分析）
            logger.info("   正在批量获取分钟K数据...")
            kline_data = xtdata.get_market_data_ex(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=potentials,
                period='1m',
                count=30  # 最近30根K线
            )
            
            # 智能选择单进程或多进程
            if len(potentials) < 100:
                # 单进程处理（<100股）
                logger.info("   使用单进程模式...")
                for code in potentials:
                    if code not in kline_data:
                        continue
                    
                    result = self._analyze_single_stock(code, kline_data[code])
                    if result and result['final_signal'] == 'TRAP_WARNING':
                        trap_list.append(result)
            
            else:
                # 多进程处理（>100股）
                logger.info(f"   使用多进程模式（{cpu_count()}核心）...")
                tasks = [(code, kline_data[code]) for code in potentials if code in kline_data]
                
                with Pool(processes=min(cpu_count(), 8)) as pool:
                    results = pool.starmap(self._analyze_single_stock, tasks)
                
                for result in results:
                    if result and result['final_signal'] == 'TRAP_WARNING':
                        trap_list.append(result)
        
        except Exception as e:
            logger.error(f"❌ 阶段3筛选失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return trap_list
    
    def _analyze_single_stock(self, code: str, kline_df: pd.DataFrame) -> Optional[dict]:
        """
        单股票完整QPST分析
        
        Args:
            code: 股票代码
            kline_df: 分钟K数据
        
        Returns:
            分析结果（如果无效则返回None）
        """
        if len(kline_df) < 20:
            return None
        
        try:
            # 执行完整四维分析
            result = self.analyzer.analyze(code, kline_df)
            return result
        
        except Exception as e:
            logger.debug(f"⚠️ 分析{code}失败: {e}")
            return None
    
    def _save_to_cache(self, code: str, kline_df: pd.DataFrame):
        """
        保存K线数据到CSV缓存
        
        Args:
            code: 股票代码
            kline_df: 分钟K数据
        """
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            cache_file = self.cache_dir / date_str / f"{code.replace('.', '_')}_1min.csv"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            kline_df.to_csv(cache_file, index=False, encoding='utf-8')
            logger.debug(f"✅ 缓存数据: {cache_file}")
        
        except Exception as e:
            logger.debug(f"⚠️ 缓存数据失败 {code}: {e}")
    
    def _load_from_cache(self, code: str) -> Optional[pd.DataFrame]:
        """
        从CSV缓存加载K线数据
        
        Args:
            code: 股票代码
        
        Returns:
            分钟K数据（如果缓存不存在则返回None）
        """
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            cache_file = self.cache_dir / date_str / f"{code.replace('.', '_')}_1min.csv"
            
            if cache_file.exists():
                df = pd.read_csv(cache_file, encoding='utf-8')
                logger.debug(f"✅ 加载缓存: {cache_file}")
                return df
        
        except Exception as e:
            logger.debug(f"⚠️ 加载缓存失败 {code}: {e}")
        
        return None
