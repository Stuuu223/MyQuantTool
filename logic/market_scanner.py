#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场扫描引擎

三阶段渐进式筛选：
1. 预筛选：硬性条件快速过滤
2. 四维初筛：简化QPST识别异常
3. 精准QPST：完整分析输出榜单

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
    全市场扫描器
    
    三阶段渐进式筛选，输出TOP 20-50诱多榜单
    """
    
    def __init__(self, use_cache: bool = True, cache_dir: str = 'data/kline_cache'):
        """
        初始化扫描器
        
        Args:
            use_cache: 是否使用本地CSV缓存作为备份
            cache_dir: 缓存目录路径
        """
        if not QMT_AVAILABLE:
            raise RuntimeError("⚠️ xtquant 未安装，MarketScanner 不可用")
        
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化批量分析器
        self.analyzer = BatchQPSTAnalyzer()
        
        # 失败记录
        self.failed_codes = []
        
        logger.info("✅ MarketScanner 初始化完成")
        logger.info(f"   - 缓存目录: {self.cache_dir}")
        logger.info(f"   - 缓存备份: {' 启用' if use_cache else '禁用'}")
    
    def scan(self, stock_list: List[str], scan_time: str = None) -> List[Dict]:
        """
        执行全市场扫描
        
        Args:
            stock_list: 股票代码列表
            scan_time: 扫描时间节点（'09:35' | '10:00' | '14:00'）
        
        Returns:
            TOP 20-50 诱多榜单
        """
        if scan_time is None:
            scan_time = datetime.now().strftime('%H:%M')
        
        logger.info("="*80)
        logger.info(f"🚀 开始全市场扫描 - {scan_time}")
        logger.info("="*80)
        logger.info(f"待扫描股票数量: {len(stock_list)}")
        
        start_time = time.time()
        
        # 重置失败记录
        self.failed_codes = []
        
        # ===== 阶段1: 预筛选 =====
        candidates = self._phase1_pre_filter(stock_list)
        logger.info(f"\n✅ 阶段1完成: {len(stock_list)} → {len(candidates)} 只股票")
        
        if not candidates:
            logger.warning("⚠️ 预筛选后无候选股票，扫描结束")
            return []
        
        # ===== 阶段2: 四维初筛 =====
        potentials = self._phase2_qpst_lite(candidates)
        logger.info(f"✅ 阶段2完成: {len(candidates)} → {len(potentials)} 只股票")
        
        if not potentials:
            logger.warning("⚠️ 四维初筛后无候选股票，扫描结束")
            return []
        
        # ===== 阶段3: 精准QPST =====
        trap_list = self._phase3_qpst_full(potentials)
        logger.info(f"✅ 阶段3完成: {len(potentials)} → {len(trap_list)} 只股票")
        
        # 按置信度排序
        trap_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 统计信息
        elapsed = time.time() - start_time
        logger.info("="*80)
        logger.info(f"📊 扫描完成 - 耗时 {elapsed:.1f}秒")
        logger.info(f"   - 总扫描: {len(stock_list)} 只")
        logger.info(f"   - 预筛选: {len(candidates)} 只")
        logger.info(f"   - 初筛选: {len(potentials)} 只")
        logger.info(f"   - 最终榜单: {len(trap_list)} 只")
        logger.info(f"   - 失败股票: {len(self.failed_codes)} 只")
        logger.info("="*80)
        
        return trap_list[:50]  # TOP 50
    
    def _phase1_pre_filter(self, stock_list: List[str]) -> List[str]:
        """
        阶段1: 预筛选（硬性条件）
        
        目标: 5000股 → 200-400股（1分钟内完成）
        
        筛选条件:
        1. 涨幅 > 2%
        2. 换手率 > 3%（10分钟）
        3. 放量 > 1.3倍
        """
        logger.info("\n🔍 阶段1: 预筛选（硬性条件）")
        logger.info("-" * 80)
        
        candidates = []
        
        # 批量获取分钟K数据（QMT接口）
        logger.info("正在批量获取分钟K数据...")
        kline_data = self._get_kline_batch(stock_list, count=10)
        
        logger.info(f"成功获取 {len(kline_data)} 只股票的K线数据")
        
        for code in stock_list:
            try:
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
                float_shares = self.analyzer.equity_info.get(code, {}).get('float_shares', 0)
                if float_shares > 0:
                    turnover = df['volume'].sum() / float_shares
                else:
                    turnover = 0
                
                # 硬性筛选条件
                if price_change > 0.02 and turnover > 0.03 and volume_ratio > 1.3:
                    candidates.append(code)
                    logger.debug(f"  ✓ {code}: 涨幅={price_change:.2%}, 换手={turnover:.2%}, 量比={volume_ratio:.2f}")
            
            except Exception as e:
                logger.debug(f"  ✗ {code}: 预筛选失败 - {e}")
                self.failed_codes.append(code)
        
        return candidates
    
    def _phase2_qpst_lite(self, candidates: List[str]) -> List[str]:
        """
        阶段2: 四维初筛（简化QPST）
        
        目标: 200-400股 → 50-100股（3分钟内完成）
        """
        logger.info("\n🔍 阶段2: 四维初筛（简化QPST）")
        logger.info("-" * 80)
        
        potentials = []
        
        # 批量获取分钟K数据
        logger.info("正在批量获取分钟K数据...")
        kline_data = self._get_kline_batch(candidates, count=10)
        
        for code in candidates:
            try:
                if code not in kline_data:
                    continue
                
                df = kline_data[code]
                
                if len(df) < 10:
                    continue
                
                # 快速四维判断
                signals = self.analyzer.analyze_lite(df, code)
                
                # 统计异常维度数量
                abnormal_count = sum(1 for sig in signals.values() if sig == 'ABNORMAL')
                
                # 至少2个维度异常才进入下一阶段
                if abnormal_count >= 2:
                    potentials.append(code)
                    logger.debug(f"  ✓ {code}: {abnormal_count}/4 维度异常 - {signals}")
            
            except Exception as e:
                logger.debug(f"  ✗ {code}: 初筛失败 - {e}")
                self.failed_codes.append(code)
        
        return potentials
    
    def _phase3_qpst_full(self, potentials: List[str]) -> List[Dict]:
        """
        阶段3: 精准QPST（完整分析）
        
        目标: 50-100股 → 20-50股（5分钟内完成）
        """
        logger.info("\n🔍 阶段3: 精准QPST（完整分析）")
        logger.info("-" * 80)
        
        # 智能选择单进程 vs 多进程
        if len(potentials) < 100:
            logger.info(f"使用单进程模式（{len(potentials)} 只股票）")
            results = [self._analyze_single_stock(code) for code in potentials]
        else:
            logger.info(f"使用多进程模式（{len(potentials)} 只股票，{cpu_count()} 核心）")
            with Pool(processes=min(8, cpu_count())) as pool:
                results = pool.map(self._analyze_single_stock, potentials)
        
        # 过滤出诱多预警
        trap_list = []
        for result in results:
            if result and result['final_signal'] == 'TRAP_WARNING':
                trap_list.append(result)
                logger.info(f"  ⚠️  {result['code']}: {result['reason']} (置信度: {result['confidence']:.0%})")
        
        return trap_list
    
    def _analyze_single_stock(self, code: str) -> Optional[Dict]:
        """
        单股票完整QPST分析
        
        Args:
            code: 股票代码
        
        Returns:
            分析结果字典 或 None（失败）
        """
        try:
            # 获取更长时间的分钟K（30根）
            df = self._get_kline_single(code, count=30)
            
            if df is None or len(df) < 20:
                return None
            
            # 执行完整四维分析
            result = self.analyzer.analyze_full(df, code)
            
            # 添加股票代码和时间戳
            result['code'] = code
            result['timestamp'] = datetime.now().strftime('%H:%M:%S')
            
            return result
        
        except Exception as e:
            logger.debug(f"  ✗ {code}: 完整分析失败 - {e}")
            self.failed_codes.append(code)
            return None
    
    # ========== 数据获取层（QMT主力 + CSV备份） ==========
    
    def _get_kline_batch(self, stock_list: List[str], count: int = 10) -> Dict[str, pd.DataFrame]:
        """
        批量获取分钟K数据（QMT接口）
        
        Args:
            stock_list: 股票代码列表
            count: K线根数
        
        Returns:
            {code: DataFrame, ...}
        """
        try:
            # 使用QMT批量获取
            kline_data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_list,
                period='1m',
                count=count,
                dividend_type='none'
            )
            
            # 添加时间列（方便尾盘判断）
            for code, df in kline_data.items():
                if not df.empty and df.index.name == 'time':
                    df['time'] = df.index.strftime('%H:%M')
            
            return kline_data
        
        except Exception as e:
            logger.error(f"❌ QMT批量获取失败: {e}")
            
            # 降级到CSV缓存
            if self.use_cache:
                logger.warning("⚠️ 降级使用CSV缓存")
                return self._load_from_cache_batch(stock_list, count)
            
            return {}
    
    def _get_kline_single(self, code: str, count: int = 30) -> Optional[pd.DataFrame]:
        """
        获取单个股票的分钟K数据
        
        Args:
            code: 股票代码
            count: K线根数
        
        Returns:
            DataFrame 或 None
        """
        try:
            # 使用QMT获取
            kline_data = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[code],
                period='1m',
                count=count,
                dividend_type='none'
            )
            
            if code in kline_data:
                df = kline_data[code]
                if not df.empty and df.index.name == 'time':
                    df['time'] = df.index.strftime('%H:%M')
                return df
            
            return None
        
        except Exception as e:
            logger.debug(f"QMT获取{code}失败: {e}")
            
            # 降级到CSV缓存
            if self.use_cache:
                return self._load_from_cache_single(code, count)
            
            return None
    
    def _load_from_cache_batch(self, stock_list: List[str], count: int) -> Dict[str, pd.DataFrame]:
        """
        从CSV缓存批量加载（备份方案）
        
        Args:
            stock_list: 股票代码列表
            count: K线根数
        
        Returns:
            {code: DataFrame, ...}
        """
        result = {}
        for code in stock_list:
            df = self._load_from_cache_single(code, count)
            if df is not None:
                result[code] = df
        return result
    
    def _load_from_cache_single(self, code: str, count: int) -> Optional[pd.DataFrame]:
        """
        从CSV缓存加载单个股票数据
        
        Args:
            code: 股票代码
            count: K线根数
        
        Returns:
            DataFrame 或 None
        """
        try:
            # 构建缓存文件路径
            today = datetime.now().strftime('%Y%m%d')
            cache_file = self.cache_dir / today / f"{code.replace('.', '_')}_1min.csv"
            
            if not cache_file.exists():
                return None
            
            # 读取CSV
            df = pd.read_csv(cache_file, parse_dates=['time'])
            
            # 取最近count根K线
            if len(df) > count:
                df = df.tail(count)
            
            # 添加时间列
            df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M')
            
            return df
        
        except Exception as e:
            logger.debug(f"CSV加载{code}失败: {e}")
            return None
    
    def get_failed_codes(self) -> List[str]:
        """
        获取失败的股票代码列表
        
        Returns:
            失败股票代码列表
        """
        return list(set(self.failed_codes))  # 去重
