#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 增强版三漏斗扫描器

核心功能：
- 集成三大过滤器：板块共振、动态阈值、竞价校验
- 在 Level 2 之后增加过滤层（Level 2.5）
- 保留原有三漏斗扫描功能，只是增强过滤能力

集成架构：
```
Level 1: 技术面粗筛（QMT）
  ↓
Level 2: 资金流向分析（AkShare）
  ↓
【新增】Level 2.5: 三大过滤器检查
  ├─ 风口过滤器（板块共振）
  ├─ 动态阈值（市值+时间+情绪）
  └─ 竞价校验（仅开盘阶段）
  ↓
Level 3: 坑vs机会分类（TrapDetector）
```

核心逻辑：
1. 过滤器应用顺序：板块共振 → 动态阈值 → 竞价校验
2. 过滤结果处理：通过所有过滤器 → 进入Level 3；未通过 → 记录到观察池
3. 可配置开关：支持单独启用/禁用每个过滤器

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-14
"""

import json
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.data_providers.data_source_manager import get_smart_data_manager

# 导入三大过滤器
from logic.strategies.wind_filter import get_wind_filter, WindFilter
from logic.strategies.dynamic_threshold import get_dynamic_threshold, DynamicThreshold
from logic.strategies.auction_strength_validator import get_auction_strength_validator, AuctionStrengthValidator

# 导入原有扫描器
from logic.strategies.triple_funnel_scanner import (
    TripleFunnelScanner,
    StockBasicInfo,
    Level1Result,
    Level2Result,
    Level3Result,
    WatchlistItem,
    TradingSignal,
    RiskLevel
)

logger = get_logger(__name__)


# ==================== 数据结构定义 ====================

@dataclass
class Filter25Result:
    """
    Level 2.5 三大过滤器结果
    
    Attributes:
        code: 股票代码
        passed: 是否通过所有过滤器
        wind_result: 板块共振过滤器结果
        threshold_result: 动态阈值过滤器结果
        auction_result: 竞价校验器结果
        reasons: 未通过的原因列表
        details: 详细信息
    """
    code: str
    passed: bool
    wind_result: Optional[Dict] = None
    threshold_result: Optional[Dict] = None
    auction_result: Optional[Dict] = None
    reasons: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


# ==================== V12.1.0 增强版扫描器 ====================

class TripleFunnelScannerV121(TripleFunnelScanner):
    """
    V12.1.0 增强版三漏斗扫描器
    
    集成三大过滤器：
    1. 板块共振过滤器（wind_filter）- 拒绝"孤军深入"
    2. 动态阈值管理器（dynamic_threshold）- 废弃硬编码阈值
    3. 竞价强弱校验器（auction_strength_validator）- 避免竞价陷阱
    
    核心改进：
    - 在 Level 2 之后增加 Level 2.5 过滤层
    - 支持独立启用/禁用每个过滤器
    - 提供详细的过滤结果日志
    - 保留原有三漏斗扫描功能
    """

    def __init__(
        self,
        config_path: str = "config/watchlist_pool.json",
        enable_wind_filter: bool = True,
        enable_dynamic_threshold: bool = True,
        enable_auction_validator: bool = True,
        sentiment_stage: str = 'divergence'
    ):
        """
        初始化 V12.1.0 增强版扫描器
        
        Args:
            config_path: 观察池配置文件路径
            enable_wind_filter: 是否启用板块共振过滤器
            enable_dynamic_threshold: 是否启用动态阈值管理器
            enable_auction_validator: 是否启用竞价校验器
            sentiment_stage: 情绪周期阶段（'start', 'main', 'climax', 'divergence', 'recession', 'freeze'）
        """
        # 调用父类初始化
        super().__init__(config_path)
        
        # 初始化三大过滤器
        try:
            self.wind_filter = get_wind_filter()
            logger.info("✅ [V12.1.0] 板块共振过滤器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 板块共振过滤器加载失败: {e}")
            self.wind_filter = None
        
        try:
            self.dynamic_threshold = get_dynamic_threshold()
            logger.info("✅ [V12.1.0] 动态阈值管理器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 动态阈值管理器加载失败: {e}")
            self.dynamic_threshold = None
        
        try:
            self.auction_validator = get_auction_strength_validator()
            logger.info("✅ [V12.1.0] 竞价强弱校验器加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [V12.1.0] 竞价强弱校验器加载失败: {e}")
            self.auction_validator = None
        
        # 过滤器配置
        self.enable_wind_filter = enable_wind_filter
        self.enable_dynamic_threshold = enable_dynamic_threshold
        self.enable_auction_validator = enable_auction_validator
        self.sentiment_stage = sentiment_stage
        
        # 性能统计
        self._filter_stats = {
            'total_checks': 0,
            'wind_passed': 0,
            'threshold_passed': 0,
            'auction_passed': 0,
            'all_passed': 0,
            'total_time_ms': 0.0
        }
        
        logger.info("=" * 80)
        logger.info("🚀 [V12.1.0] 增强版三漏斗扫描器初始化完成")
        logger.info(f"   - 板块共振过滤器: {'✅ 启用' if enable_wind_filter else '❌ 禁用'}")
        logger.info(f"   - 动态阈值管理器: {'✅ 启用' if enable_dynamic_threshold else '❌ 禁用'}")
        logger.info(f"   - 竞价强弱校验器: {'✅ 启用' if enable_auction_validator else '❌ 禁用'}")
        logger.info(f"   - 情绪周期阶段: {sentiment_stage}")
        logger.info("=" * 80)
    
    def _apply_filters(
        self,
        stock_code: str,
        tick_data: Optional[Dict] = None,
        flow_data: Optional[Dict] = None,
        auction_data: Optional[Dict] = None
    ) -> Filter25Result:
        """
        应用三大过滤器
        
        过滤顺序：
        1. 板块共振过滤器（最严格）
        2. 动态阈值过滤器（调整参数）
        3. 竞价校验器（仅开盘阶段）
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据（用于动态阈值）
            flow_data: 资金流数据（用于动态阈值）
            auction_data: 竞价数据（用于竞价校验）
        
        Returns:
            Filter25Result: 过滤结果
        """
        start_time = time.time()
        
        result = Filter25Result(
            code=stock_code,
            passed=False,
            reasons=[],
            details={}
        )
        
        try:
            # 1. 板块共振过滤器
            if self.enable_wind_filter and self.wind_filter:
                wind_result = self.wind_filter.check_sector_resonance(stock_code)
                result.wind_result = wind_result
                
                if wind_result.get('is_resonance', False):
                    self._filter_stats['wind_passed'] += 1
                    logger.debug(f"✅ [板块共振] {stock_code} 通过")
                else:
                    reason = f"板块未共振（涨停={wind_result.get('limit_up_count', 0)} 上涨={wind_result.get('breadth', 0)*100:.1f}%）"
                    result.reasons.append(reason)
                    logger.debug(f"❌ [板块共振] {stock_code} 未通过: {reason}")
            
            # 2. 动态阈值过滤器
            if self.enable_dynamic_threshold and self.dynamic_threshold:
                current_time = datetime.now()
                current_price = tick_data.get('price', 0) if tick_data else 0
                
                threshold_result = self.dynamic_threshold.calculate_thresholds(
                    stock_code,
                    current_time,
                    self.sentiment_stage,
                    current_price
                )
                result.threshold_result = threshold_result
                
                # 检查资金流是否满足动态阈值
                if flow_data:
                    main_inflow = flow_data.get('主力净流入', 0)
                    min_inflow = threshold_result.get('main_inflow_min', 0)
                    
                    if main_inflow >= min_inflow:
                        self._filter_stats['threshold_passed'] += 1
                        logger.debug(f"✅ [动态阈值] {stock_code} 通过 (主力流入={main_inflow/1e4:.0f}万 ≥ {min_inflow/1e4:.0f}万)")
                    else:
                        reason = f"主力流入不足（{main_inflow/1e4:.0f}万 < {min_inflow/1e4:.0f}万）"
                        result.reasons.append(reason)
                        logger.debug(f"❌ [动态阈值] {stock_code} 未通过: {reason}")
                else:
                    # 没有资金流数据，跳过检查
                    logger.debug(f"⚠️ [动态阈值] {stock_code} 无资金流数据，跳过检查")
            
            # 3. 竞价校验器（仅开盘阶段）
            if self.enable_auction_validator and self.auction_validator:
                current_time = datetime.now()
                time_segment = self.dynamic_threshold._get_time_segment(current_time) if self.dynamic_threshold else 'mid'
                
                # 仅在开盘阶段检查竞价
                if time_segment == 'open' and auction_data:
                    auction_result = self.auction_validator.validate_auction(stock_code, auction_data)
                    result.auction_result = auction_result
                    
                    if auction_result.get('is_valid', False):
                        self._filter_stats['auction_passed'] += 1
                        logger.debug(f"✅ [竞价校验] {stock_code} 通过 ({auction_result.get('action', 'UNKNOWN')})")
                    else:
                        reason = f"竞价校验未通过（{auction_result.get('reason', '未知原因')}）"
                        result.reasons.append(reason)
                        logger.debug(f"❌ [竞价校验] {stock_code} 未通过: {reason}")
                else:
                    # 非开盘阶段，跳过竞价检查
                    logger.debug(f"⚠️ [竞价校验] {stock_code} 非开盘阶段，跳过检查")
            
            # 4. 判断是否通过所有过滤器
            result.passed = len(result.reasons) == 0
            
            if result.passed:
                self._filter_stats['all_passed'] += 1
                logger.info(f"✅ [Level 2.5] {stock_code} 通过所有过滤器")
            else:
                logger.info(f"❌ [Level 2.5] {stock_code} 未通过: {', '.join(result.reasons)}")
            
            # 5. 记录耗时
            elapsed_time = (time.time() - start_time) * 1000  # 毫秒
            self._filter_stats['total_time_ms'] += elapsed_time
            self._filter_stats['total_checks'] += 1
            
            result.details['elapsed_time_ms'] = elapsed_time
            result.details['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [Level 2.5] 过滤器应用失败: {stock_code}, {e}")
            result.reasons.append(f"过滤器应用失败: {e}")
            return result
    
    def run_post_market_scan_v121(self, max_stocks: int = 100) -> List[Dict]:
        """
        运行盘后扫描（V12.1.0 增强版）
        
        流程：
        Level 1 → Level 2 → Level 2.5（三大过滤器）→ Level 3
        
        Args:
            max_stocks: 最大扫描股票数
        
        Returns:
            通过筛选的股票信息列表（包含完整的筛选结果）
        """
        logger.info("=" * 80)
        logger.info(f"🚀 [V12.1.0] 开始盘后扫描（增强版）")
        logger.info("=" * 80)
        
        passed_stocks = []
        
        # 获取观察池股票
        watchlist = self.watchlist_manager.get_all()
        stock_codes = [item.code for item in watchlist]
        
        if not stock_codes:
            logger.warning("⚠️ 观察池为空，请先添加股票")
            return passed_stocks
        
        # 限制扫描数量
        stock_codes = stock_codes[:max_stocks]
        logger.info(f"📋 扫描 {len(stock_codes)} 只股票")
        
        # 重置统计
        self._filter_stats = {
            'total_checks': 0,
            'wind_passed': 0,
            'threshold_passed': 0,
            'auction_passed': 0,
            'all_passed': 0,
            'total_time_ms': 0.0
        }
        
        # 获取实时行情
        try:
            df_quotes = self.data_manager.get_realtime_quotes(stock_codes)
            
            if df_quotes.empty:
                logger.error("❌ 获取实时行情失败")
                return passed_stocks
            
            # 逐只股票筛选
            for _, row in df_quotes.iterrows():
                code = row['代码']
                name = row['名称']
                
                # Level 1: 基础过滤
                stock_info = StockBasicInfo(
                    code=code,
                    name=name,
                    price=float(row['最新价']),
                    pct_change=float(row['涨跌幅']),
                    volume=int(row['成交量']),
                    amount=float(row['成交额']),
                    turnover_rate=float(row.get('换手率', 0)),
                    high=float(row['最高']),
                    low=float(row['最低']),
                    open=float(row['今开'])
                )
                
                level1_result = self.level1_filter.filter(stock_info)
                self.watchlist_manager.update_result(code, 1, level1_result)
                
                if not level1_result.passed:
                    logger.debug(f"❌ [Level1] {code} {name}: {', '.join(level1_result.reasons)}")
                    continue
                
                logger.info(f"✅ [Level1] {code} {name} 通过")
                
                # Level 2: 资金流向分析
                level2_result = self.level2_analyzer.analyze(code)
                self.watchlist_manager.update_result(code, 2, level2_result)
                
                if not level2_result.passed:
                    logger.debug(f"❌ [Level2] {code} {name}: {', '.join(level2_result.reasons)}")
                    continue
                
                logger.info(f"✅ [Level2] {code} {name} 通过 (资金流得分: {level2_result.fund_flow_score:.0f})")
                
                # Level 2.5: 三大过滤器（V12.1.0 新增）
                tick_data = {
                    'price': float(row['最新价']),
                    'volume': int(row['成交量']),
                    'amount': float(row['成交额'])
                }
                
                # 获取资金流数据
                flow_data = None
                try:
                    market = self.converter.get_market(code).lower()
                    standard_code = self.converter.to_standard(code)
                    flow_data = self.data_manager.get_money_flow(standard_code, market)
                except Exception as e:
                    logger.debug(f"⚠️ 获取资金流数据失败: {code}, {e}")
                
                # 竞价数据（仅开盘阶段）
                auction_data = None
                current_time = datetime.now()
                time_segment = self.dynamic_threshold._get_time_segment(current_time) if self.dynamic_threshold else 'mid'
                
                if time_segment == 'open':
                    try:
                        auction_data = {
                            'open_price': float(row['今开']),
                            'prev_close': float(row['昨收']) if '昨收' in row else float(row['最新价']) / (1 + float(row['涨跌幅']) / 100),
                            'volume_ratio': float(row.get('量比', 1.0)) if '量比' in row else 1.0,
                            'amount': float(row['成交额']),
                            'high_price': float(row['最高']),
                            'low_price': float(row['最低']),
                            'is_limit_up': float(row['涨跌幅']) >= 9.8
                        }
                    except Exception as e:
                        logger.debug(f"⚠️ 获取竞价数据失败: {code}, {e}")
                
                filter25_result = self._apply_filters(code, tick_data, flow_data, auction_data)
                
                if not filter25_result.passed:
                    logger.debug(f"❌ [Level 2.5] {code} {name}: {', '.join(filter25_result.reasons)}")
                    continue
                
                logger.info(f"✅ [Level 2.5] {code} {name} 通过所有过滤器")
                
                # Level 3: 风险评估
                level3_result = self.level3_assessor.assess(code)
                self.watchlist_manager.update_result(code, 3, level3_result)
                
                if not level3_result.passed:
                    logger.debug(f"❌ [Level3] {code} {name}: {', '.join(level3_result.reasons)}")
                    continue
                
                logger.info(f"✅ [Level3] {code} {name} 通过 (综合得分: {level3_result.comprehensive_score:.0f})")
                
                # 通过所有筛选
                passed_stocks.append({
                    'code': code,
                    'name': name,
                    'level1_result': level1_result,
                    'level2_result': level2_result,
                    'filter25_result': filter25_result,
                    'level3_result': level3_result
                })
        
        except Exception as e:
            logger.error(f"❌ 盘后扫描失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # 打印统计信息
        logger.info("=" * 80)
        logger.info(f"✅ [V12.1.0] 盘后扫描完成")
        logger.info(f"   - 扫描股票: {len(stock_codes)} 只")
        logger.info(f"   - 通过筛选: {len(passed_stocks)} 只")
        logger.info(f"   - 过滤器统计:")
        logger.info(f"     * 总检查: {self._filter_stats['total_checks']}")
        logger.info(f"     * 板块共振通过: {self._filter_stats['wind_passed']}")
        logger.info(f"     * 动态阈值通过: {self._filter_stats['threshold_passed']}")
        logger.info(f"     * 竞价校验通过: {self._filter_stats['auction_passed']}")
        logger.info(f"     * 全部通过: {self._filter_stats['all_passed']}")
        if self._filter_stats['total_checks'] > 0:
            avg_time = self._filter_stats['total_time_ms'] / self._filter_stats['total_checks']
            logger.info(f"   - 平均过滤耗时: {avg_time:.2f}ms/股")
        logger.info("=" * 80)
        
        return passed_stocks
    
    def get_filter_stats(self) -> Dict:
        """
        获取过滤器统计信息
        
        Returns:
            dict: 统计信息
        """
        return self._filter_stats.copy()
    
    def update_sentiment_stage(self, sentiment_stage: str):
        """
        更新情绪周期阶段
        
        Args:
            sentiment_stage: 情绪周期阶段（'start', 'main', 'climax', 'divergence', 'recession', 'freeze'）
        """
        self.sentiment_stage = sentiment_stage
        logger.info(f"🔄 [V12.1.0] 情绪周期阶段更新: {sentiment_stage}")
    
    def toggle_filter(self, filter_name: str, enabled: bool):
        """
        切换过滤器开关
        
        Args:
            filter_name: 过滤器名称（'wind', 'threshold', 'auction'）
            enabled: 是否启用
        """
        if filter_name == 'wind':
            self.enable_wind_filter = enabled
            logger.info(f"🔄 [V12.1.0] 板块共振过滤器: {'✅ 启用' if enabled else '❌ 禁用'}")
        elif filter_name == 'threshold':
            self.enable_dynamic_threshold = enabled
            logger.info(f"🔄 [V12.1.0] 动态阈值管理器: {'✅ 启用' if enabled else '❌ 禁用'}")
        elif filter_name == 'auction':
            self.enable_auction_validator = enabled
            logger.info(f"🔄 [V12.1.0] 竞价强弱校验器: {'✅ 启用' if enabled else '❌ 禁用'}")
        else:
            logger.warning(f"⚠️ [V12.1.0] 未知过滤器: {filter_name}")


# ==================== 全局实例 ====================

_scanner_v121: Optional[TripleFunnelScannerV121] = None


def get_scanner_v121(
    config_path: str = "config/watchlist_pool.json",
    enable_wind_filter: bool = True,
    enable_dynamic_threshold: bool = True,
    enable_auction_validator: bool = True,
    sentiment_stage: str = 'divergence'
) -> TripleFunnelScannerV121:
    """
    获取 V12.1.0 增强版扫描器单例
    
    Args:
        config_path: 观察池配置文件路径
        enable_wind_filter: 是否启用板块共振过滤器
        enable_dynamic_threshold: 是否启用动态阈值管理器
        enable_auction_validator: 是否启用竞价校验器
        sentiment_stage: 情绪周期阶段
    
    Returns:
        TripleFunnelScannerV121: 扫描器实例
    """
    global _scanner_v121
    if _scanner_v121 is None:
        _scanner_v121 = TripleFunnelScannerV121(
            config_path=config_path,
            enable_wind_filter=enable_wind_filter,
            enable_dynamic_threshold=enable_dynamic_threshold,
            enable_auction_validator=enable_auction_validator,
            sentiment_stage=sentiment_stage
        )
    return _scanner_v121


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 V12.1.0 增强版三漏斗扫描器 - 演示")
    print("=" * 80)
    
    # 创建扫描器
    scanner = get_scanner_v121(
        enable_wind_filter=True,
        enable_dynamic_threshold=True,
        enable_auction_validator=True,
        sentiment_stage='divergence'
    )
    
    # 1. 添加测试股票到观察池
    print("\n📝 添加测试股票到观察池...")
    scanner.watchlist_manager.add("000001", "平安银行", "测试用")
    scanner.watchlist_manager.add("600519", "贵州茅台", "测试用")
    
    # 2. 运行盘后扫描（V12.1.0 增强版）
    print("\n🔍 运行盘后扫描（V12.1.0 增强版）...")
    passed = scanner.run_post_market_scan_v121(max_stocks=10)
    
    print(f"\n✅ 通过筛选: {len(passed)} 只股票")
    for stock in passed:
        print(f"\n  {stock['code']} {stock['name']}")
        print(f"    Level 1: {'✅' if stock['level1_result'].passed else '❌'}")
        print(f"    Level 2: {'✅' if stock['level2_result'].passed else '❌'} (得分: {stock['level2_result'].fund_flow_score:.0f})")
        print(f"    Level 2.5: {'✅' if stock['filter25_result'].passed else '❌'}")
        if stock['filter25_result'].wind_result:
            print(f"      - 板块共振: {'✅' if stock['filter25_result'].wind_result.get('is_resonance') else '❌'}")
        if stock['filter25_result'].threshold_result:
            print(f"      - 动态阈值: {'✅' if stock['filter25_result'].threshold_result.get('passed', True) else '❌'}")
        if stock['filter25_result'].auction_result:
            print(f"      - 竞价校验: {'✅' if stock['filter25_result'].auction_result.get('is_valid') else '❌'}")
        print(f"    Level 3: {'✅' if stock['level3_result'].passed else '❌'} (得分: {stock['level3_result'].comprehensive_score:.0f})")
    
    # 3. 获取过滤器统计
    print("\n📊 过滤器统计:")
    stats = scanner.get_filter_stats()
    print(f"  总检查: {stats['total_checks']}")
    print(f"  板块共振通过: {stats['wind_passed']}")
    print(f"  动态阈值通过: {stats['threshold_passed']}")
    print(f"  竞价校验通过: {stats['auction_passed']}")
    print(f"  全部通过: {stats['all_passed']}")
    if stats['total_checks'] > 0:
        print(f"  平均耗时: {stats['total_time_ms']/stats['total_checks']:.2f}ms/股")
    
    # 4. 切换过滤器演示
    print("\n🔄 切换过滤器演示:")
    scanner.toggle_filter('wind', False)
    scanner.toggle_filter('threshold', True)
    scanner.toggle_filter('auction', False)
    
    # 5. 更新情绪周期
    print("\n🔄 更新情绪周期:")
    scanner.update_sentiment_stage('start')
    
    print("\n" + "=" * 80)
    print("✅ 演示完成")
    print("=" * 80)