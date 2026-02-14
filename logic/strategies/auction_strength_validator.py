#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 竞价强弱校验器 (Auction Strength Validator)

核心功能：
- 引入"预期差"概念，避免竞价陷阱
- 区分明牌焦点股和非明牌股的判断逻辑
- 根据历史表现计算竞价预期溢价
- 提供降级策略（数据缺失时返回中性判断）

核心逻辑：
1. 明牌焦点股判断：
   - 如果是昨日涨停股：今日竞价量比 < 1.0 或 低开 → 不及预期 → 放弃
   - 昨日越强，今日预期越高

2. 首板挖掘判断：
   - 竞价量比 > 3.0 且 高开 1-3% → 超预期 → 加分
   - 竞价爆量跳空高开 → 强烈关注

3. 基础判定：
   - 量比排序 + 涨幅排序配合
   - 量比 > 1.5 且 高开 > 2% → 基础通过

设计原则：
1. 区分明牌焦点股和非明牌股的判断逻辑
2. 提供降级策略（数据缺失时返回中性判断）
3. 添加详细的日志记录
4. 考虑数据缓存优化

验收标准：
- 能够正确判断明牌焦点股
- 能够正确判断首板挖掘股
- 能够计算竞价预期溢价
- 竞价信号准确率>75%
- 单次验证耗时<30ms
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-14
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.cache_manager import CacheManager

logger = get_logger(__name__)


class AuctionStrengthValidator:
    """
    竞价强弱校验器
    
    功能：
    1. 验证竞价强弱（明牌焦点股 vs 首板挖掘股）
    2. 计算竞价预期溢价率
    3. 判断是否超预期或不及预期
    4. 提供降级策略和缓存优化
    
    数据格式：
    {
        "open_price": float,      # 竞价开盘价
        "prev_close": float,      # 昨日收盘价
        "volume_ratio": float,    # 竞价量比
        "amount": float,          # 竞价成交额
        "high_price": float,      # 竞价最高价
        "low_price": float,       # 竞价最低价
        "is_limit_up": bool       # 是否竞价涨停
    }
    """

    # 明牌焦点股阈值
    FOCUS_STOCK_MIN_VOLUME_RATIO = 1.0  # 焦点股最小量比
    FOCUS_STOCK_MIN_OPEN_GAP = 0.0     # 焦点股最小高开（不能低开）
    
    # 首板挖掘股阈值
    FIRST_BOARD_MIN_VOLUME_RATIO = 3.0  # 首板最小量比
    FIRST_BOARD_MIN_OPEN_GAP = 0.01    # 首板最小高开 1%
    FIRST_BOARD_MAX_OPEN_GAP = 0.03    # 首板最大高开 3%
    
    # 基础判定阈值
    BASE_MIN_VOLUME_RATIO = 1.5       # 基础最小量比
    BASE_MIN_OPEN_GAP = 0.02          # 基础最小高开 2%
    
    # 预期溢价计算参数
    EXPECTATION_BASE = 0.01            # 基础预期 1%
    EXPECTATION_MULTIPLIER = 2.0       # 涨停股预期倍数
    
    # 缓存时间（秒）
    CACHE_TTL_HISTORY = 3600  # 历史数据缓存1小时
    CACHE_TTL_EXPECTATION = 300  # 预期缓存5分钟

    def __init__(self):
        """初始化竞价强弱校验器"""
        self.converter = CodeConverter()
        self.cache = CacheManager()

        # 加载历史数据（用于判断是否是明牌焦点股）
        self.history_data = self._load_history_data()

        # 性能统计
        self._validate_count = 0
        self._total_time = 0.0

        logger.info("✅ [竞价强弱校验器] 初始化完成")
        logger.info(f"   - 历史数据: {len(self.history_data)} 只股票")
        logger.info(f"   - 焦点股量比阈值: ≥ {self.FOCUS_STOCK_MIN_VOLUME_RATIO}")
        logger.info(f"   - 首板量比阈值: ≥ {self.FIRST_BOARD_MIN_VOLUME_RATIO}")
        logger.info(f"   - 基础量比阈值: ≥ {self.BASE_MIN_VOLUME_RATIO}")
    
    def _load_history_data(self) -> Dict:
        """
        加载历史数据（用于判断是否是明牌焦点股）
        
        Returns:
            dict: 历史数据字典，结构: {code: {prev_close, is_limit_up, pct_chg, ...}}
        """
        try:
            # 尝试从多个数据源加载
            history_data = {}

            # 1. 尝试加载昨日涨停股数据
            limit_up_path = Path("data/hot_stocks.json")
            if limit_up_path.exists():
                with open(limit_up_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for stock in data:
                            code = stock.get('code', '')
                            if code:
                                history_data[code] = {
                                    'is_limit_up': True,
                                    'prev_close': stock.get('close', 0),
                                    'pct_chg': stock.get('pct_chg', 0)
                                }

            # 2. 尝试加载股票基本信息
            stock_names_path = Path("data/stock_names.json")
            if stock_names_path.exists():
                with open(stock_names_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for code, info in data.items():
                        if code not in history_data:
                            history_data[code] = {
                                'is_limit_up': False,
                                'prev_close': 0,
                                'pct_chg': 0
                            }

            logger.info(f"✅ [竞价强弱] 加载历史数据: {len(history_data)} 只股票")
            return history_data

        except Exception as e:
            logger.error(f"❌ [竞价强弱] 加载历史数据失败: {e}")
            return {}
    
    def _is_focus_stock(self, stock_code: str) -> bool:
        """
        判断是否是明牌焦点股
        
        焦点股特征：
        - 昨日涨停
        - 连续多日涨停
        - 热门题材龙头
        
        Args:
            stock_code: 股票代码
        
        Returns:
            bool: 是否是焦点股
        """
        try:
            # 转换为标准代码
            standard_code = self.converter.to_standard(stock_code)
            
            # 检查历史数据
            if standard_code in self.history_data:
                stock_info = self.history_data[standard_code]
                
                # 昨日涨停的股票是焦点股
                if stock_info.get('is_limit_up', False):
                    return True
                
                # 昨日涨幅 > 9% 的股票也是焦点股
                if stock_info.get('pct_chg', 0) > 9.0:
                    return True
            
            return False

        except Exception as e:
            logger.debug(f"⚠️ [竞价强弱] 判断焦点股失败: {stock_code}, {e}")
            return False
    
    def calculate_expectation(self, stock_code: str) -> float:
        """
        计算竞价预期溢价率
        
        逻辑：
        - 基础预期：1%
        - 焦点股：2-3%（昨日越强，预期越高）
        - 非焦点股：0.5-1%
        
        Args:
            stock_code: 股票代码
        
        Returns:
            float: 预期的高开幅度（0-1）
        """
        try:
            # 尝试从缓存获取
            cache_key = f"expectation_{stock_code}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 转换为标准代码
            standard_code = self.converter.to_standard(stock_code)
            
            # 判断是否是焦点股
            is_focus = self._is_focus_stock(stock_code)
            
            if is_focus:
                # 焦点股：预期更高
                if standard_code in self.history_data:
                    pct_chg = self.history_data[standard_code].get('pct_chg', 0)
                    # 昨日越强，今日预期越高
                    expectation = min(0.03, self.EXPECTATION_BASE * self.EXPECTATION_MULTIPLIER * (pct_chg / 9.0))
                else:
                    expectation = self.EXPECTATION_BASE * self.EXPECTATION_MULTIPLIER
            else:
                # 非焦点股：预期较低
                expectation = self.EXPECTATION_BASE * 0.5
            
            # 确保预期在合理范围内
            expectation = max(0.005, min(0.05, expectation))
            
            # 缓存结果
            self.cache.set(cache_key, expectation, ttl=self.CACHE_TTL_EXPECTATION)
            
            return expectation

        except Exception as e:
            logger.error(f"❌ [竞价强弱] 计算预期失败: {stock_code}, {e}")
            return self.EXPECTATION_BASE
    
    def validate_auction(
        self,
        stock_code: str,
        auction_data: dict,
        is_focus_stock: bool = None
    ) -> dict:
        """
        验证竞价强弱
        
        Args:
            stock_code: 股票代码
            auction_data: 竞价数据（包含open_price, prev_close, volume_ratio等）
            is_focus_stock: 是否是明牌焦点股（如果为None则自动判断）
        
        Returns:
            {
                "is_valid": bool,
                "reason": str,
                "action": str,  # STRONG_BUY/BUY/WATCH/REJECT
                "confidence": float,  # 0-1
                "details": dict
            }
        """
        start_time = time.time()
        
        try:
            # 1. 数据校验
            if not auction_data:
                return self._build_neutral_result(
                    is_valid=False,
                    reason="竞价数据缺失",
                    action="WATCH",
                    confidence=0.0,
                    details={'error': '竞价数据缺失'}
                )
            
            # 提取关键字段
            open_price = auction_data.get('open_price', 0)
            prev_close = auction_data.get('prev_close', 0)
            volume_ratio = auction_data.get('volume_ratio', 0)
            amount = auction_data.get('amount', 0)
            high_price = auction_data.get('high_price', 0)
            low_price = auction_data.get('low_price', 0)
            is_limit_up = auction_data.get('is_limit_up', False)
            
            # 数据有效性检查
            if prev_close <= 0:
                return self._build_neutral_result(
                    is_valid=False,
                    reason="昨日收盘价无效",
                    action="WATCH",
                    confidence=0.0,
                    details={'error': '昨日收盘价无效'}
                )
            
            # 2. 计算高开幅度
            open_gap_pct = (open_price - prev_close) / prev_close
            
            # 3. 判断是否是焦点股
            if is_focus_stock is None:
                is_focus_stock = self._is_focus_stock(stock_code)
            
            # 4. 计算预期
            expectation = self.calculate_expectation(stock_code)
            
            # 5. 根据焦点股类型应用不同的验证逻辑
            if is_focus_stock:
                result = self._validate_focus_stock(
                    stock_code,
                    open_gap_pct,
                    volume_ratio,
                    expectation,
                    auction_data
                )
            else:
                result = self._validate_first_board(
                    stock_code,
                    open_gap_pct,
                    volume_ratio,
                    expectation,
                    auction_data
                )
            
            # 6. 额外加分项
            bonus_points = 0
            bonus_reasons = []
            
            # 竞价涨停 → 强烈加分
            if is_limit_up:
                bonus_points += 0.2
                bonus_reasons.append("竞价涨停")
            
            # 爆量高开 → 加分
            if volume_ratio > 5.0 and open_gap_pct > 0.05:
                bonus_points += 0.1
                bonus_reasons.append("爆量高开")
            
            # 调整置信度
            result['confidence'] = min(1.0, result['confidence'] + bonus_points)
            
            # 添加详细信息
            result['details'].update({
                'open_gap_pct': open_gap_pct,
                'volume_ratio': volume_ratio,
                'expectation': expectation,
                'is_focus_stock': is_focus_stock,
                'is_limit_up': is_limit_up,
                'bonus_points': bonus_points,
                'bonus_reasons': bonus_reasons,
                'calculation_time_ms': (time.time() - start_time) * 1000
            })
            
            # 7. 更新性能统计
            self._validate_count += 1
            self._total_time += (time.time() - start_time) * 1000
            
            # 8. 日志记录
            self._log_validation_result(stock_code, result)
            
            return result

        except Exception as e:
            logger.error(f"❌ [竞价强弱] 验证失败: {stock_code}, {e}")
            return self._build_neutral_result(
                is_valid=False,
                reason=f"验证失败: {e}",
                action="WATCH",
                confidence=0.0,
                details={'error': str(e)}
            )
    
    def _validate_focus_stock(
        self,
        stock_code: str,
        open_gap_pct: float,
        volume_ratio: float,
        expectation: float,
        auction_data: dict
    ) -> dict:
        """
        验证明牌焦点股
        
        逻辑：
        - 昨日涨停股：今日竞价量比 < 1.0 或 低开 → 不及预期 → 放弃
        - 昨日越强，今日预期越高
        
        Args:
            stock_code: 股票代码
            open_gap_pct: 高开幅度
            volume_ratio: 竞价量比
            expectation: 预期溢价
            auction_data: 竞价数据
        
        Returns:
            dict: 验证结果
        """
        # 1. 判断是否不及预期
        is_weak = False
        weak_reasons = []
        
        # 低开 → 不及预期
        if open_gap_pct < self.FOCUS_STOCK_MIN_OPEN_GAP:
            is_weak = True
            weak_reasons.append(f"低开 {open_gap_pct*100:.2f}%")
        
        # 量比不足 → 不及预期
        if volume_ratio < self.FOCUS_STOCK_MIN_VOLUME_RATIO:
            is_weak = True
            weak_reasons.append(f"量比不足 {volume_ratio:.2f}")
        
        # 2. 如果不及预期，返回拒绝
        if is_weak:
            return self._build_reject_result(
                reason="不及预期：昨日强势股今日表现疲软",
                details={
                    'weak_reasons': weak_reasons,
                    'is_focus_stock': True
                }
            )
        
        # 3. 判断是否超预期
        is_strong = False
        strong_reasons = []
        confidence = 0.5
        
        # 高开 ≥ 预期 → 超预期
        if open_gap_pct >= expectation:
            is_strong = True
            strong_reasons.append(f"超预期高开 {open_gap_pct*100:.2f}% (预期 {expectation*100:.2f}%)")
            confidence += 0.2
        
        # 量比 ≥ 2.0 → 强势
        if volume_ratio >= 2.0:
            is_strong = True
            strong_reasons.append(f"量比充足 {volume_ratio:.2f}")
            confidence += 0.1
        
        # 4. 返回结果
        if is_strong:
            if confidence >= 0.8:
                return self._build_strong_buy_result(
                    reason="焦点股强势超预期",
                    details={
                        'strong_reasons': strong_reasons,
                        'is_focus_stock': True
                    }
                )
            else:
                return self._build_buy_result(
                    reason="焦点股符合预期",
                    details={
                        'strong_reasons': strong_reasons,
                        'is_focus_stock': True
                    }
                )
        else:
            return self._build_watch_result(
                reason="焦点股中性表现",
                details={
                    'is_focus_stock': True
                }
            )
    
    def _validate_first_board(
        self,
        stock_code: str,
        open_gap_pct: float,
        volume_ratio: float,
        expectation: float,
        auction_data: dict
    ) -> dict:
        """
        验证首板挖掘股
        
        逻辑：
        - 竞价量比 > 3.0 且 高开 1-3% → 超预期 → 加分
        - 竞价爆量跳空高开 → 强烈关注
        - 量比 > 1.5 且 高开 > 2% → 基础通过
        
        Args:
            stock_code: 股票代码
            open_gap_pct: 高开幅度
            volume_ratio: 竞价量比
            expectation: 预期溢价
            auction_data: 竞价数据
        
        Returns:
            dict: 验证结果
        """
        # 1. 基础判定
        base_passed = False
        
        # 量比 > 1.5 且 高开 > 2% → 基础通过
        if volume_ratio >= self.BASE_MIN_VOLUME_RATIO and open_gap_pct >= self.BASE_MIN_OPEN_GAP:
            base_passed = True
        
        # 2. 首板挖掘判定
        is_first_board = False
        first_board_reasons = []
        confidence = 0.4
        
        # 竞价量比 > 3.0 且 高开 1-3% → 超预期
        if (volume_ratio >= self.FIRST_BOARD_MIN_VOLUME_RATIO and
            self.FIRST_BOARD_MIN_OPEN_GAP <= open_gap_pct <= self.FIRST_BOARD_MAX_OPEN_GAP):
            is_first_board = True
            first_board_reasons.append(f"首板超预期：量比{volume_ratio:.2f} 高开{open_gap_pct*100:.2f}%")
            confidence += 0.3
        
        # 竞价爆量跳空高开 → 强烈关注
        if volume_ratio > 5.0 and open_gap_pct > 0.05:
            is_first_board = True
            first_board_reasons.append(f"爆量跳空：量比{volume_ratio:.2f} 高开{open_gap_pct*100:.2f}%")
            confidence += 0.2
        
        # 3. 返回结果
        if is_first_board:
            if confidence >= 0.8:
                return self._build_strong_buy_result(
                    reason="首板挖掘超预期",
                    details={
                        'first_board_reasons': first_board_reasons,
                        'is_first_board': True
                    }
                )
            else:
                return self._build_buy_result(
                    reason="首板挖掘符合预期",
                    details={
                        'first_board_reasons': first_board_reasons,
                        'is_first_board': True
                    }
                )
        elif base_passed:
            return self._build_watch_result(
                reason="基础通过",
                details={
                    'is_first_board': False
                }
            )
        else:
            return self._build_reject_result(
                reason="未达到基础阈值",
                details={
                    'threshold': f'量比≥{self.BASE_MIN_VOLUME_RATIO} 高开≥{self.BASE_MIN_OPEN_GAP*100:.0f}%',
                    'is_first_board': False
                }
            )
    
    def _build_strong_buy_result(self, reason: str, details: dict = None) -> dict:
        """构建强烈买入结果"""
        return {
            'is_valid': True,
            'reason': reason,
            'action': 'STRONG_BUY',
            'confidence': 0.8,
            'details': details or {}
        }
    
    def _build_buy_result(self, reason: str, details: dict = None) -> dict:
        """构建买入结果"""
        return {
            'is_valid': True,
            'reason': reason,
            'action': 'BUY',
            'confidence': 0.6,
            'details': details or {}
        }
    
    def _build_watch_result(self, reason: str, details: dict = None) -> dict:
        """构建观察结果"""
        return {
            'is_valid': False,
            'reason': reason,
            'action': 'WATCH',
            'confidence': 0.4,
            'details': details or {}
        }
    
    def _build_reject_result(self, reason: str, details: dict = None) -> dict:
        """构建拒绝结果"""
        return {
            'is_valid': False,
            'reason': reason,
            'action': 'REJECT',
            'confidence': 0.2,
            'details': details or {}
        }
    
    def _build_neutral_result(
        self,
        is_valid: bool,
        reason: str,
        action: str,
        confidence: float,
        details: dict = None
    ) -> dict:
        """构建中性结果（降级策略）"""
        return {
            'is_valid': is_valid,
            'reason': reason,
            'action': action,
            'confidence': confidence,
            'details': details or {}
        }
    
    def _log_validation_result(self, stock_code: str, result: dict) -> None:
        """
        记录验证结果
        
        Args:
            stock_code: 股票代码
            result: 验证结果
        """
        try:
            action = result.get('action', 'UNKNOWN')
            reason = result.get('reason', '')
            confidence = result.get('confidence', 0)
            details = result.get('details', {})
            
            open_gap_pct = details.get('open_gap_pct', 0)
            volume_ratio = details.get('volume_ratio', 0)
            elapsed_time = details.get('calculation_time_ms', 0)
            
            if action in ['STRONG_BUY', 'BUY']:
                logger.info(
                    f"✅ [竞价强弱] {stock_code} {action} "
                    f"高开={open_gap_pct*100:.2f}% 量比={volume_ratio:.2f} "
                    f"置信度={confidence:.2f} "
                    f"原因={reason} "
                    f"耗时={elapsed_time:.1f}ms"
                )
            elif action == 'REJECT':
                logger.debug(
                    f"❌ [竞价强弱] {stock_code} REJECT "
                    f"高开={open_gap_pct*100:.2f}% 量比={volume_ratio:.2f} "
                    f"原因={reason}"
                )
            else:  # WATCH
                logger.debug(
                    f"⚠️ [竞价强弱] {stock_code} WATCH "
                    f"高开={open_gap_pct*100:.2f}% 量比={volume_ratio:.2f} "
                    f"原因={reason}"
                )
        
        except Exception as e:
            logger.debug(f"⚠️ [竞价强弱] 记录日志失败: {e}")
    
    def batch_validate(
        self,
        stock_auction_data: Dict[str, dict]
    ) -> Dict[str, dict]:
        """
        批量验证竞价强弱
        
        Args:
            stock_auction_data: {stock_code: auction_data}
        
        Returns:
            dict: {stock_code: validation_result}
        """
        results = {}
        
        for stock_code, auction_data in stock_auction_data.items():
            results[stock_code] = self.validate_auction(stock_code, auction_data)
        
        return results
    
    def get_performance_stats(self) -> Dict:
        """
        获取性能统计
        
        Returns:
            dict: 性能统计信息
        """
        if self._validate_count > 0:
            avg_time = self._total_time / self._validate_count
        else:
            avg_time = 0.0
        
        return {
            'total_validations': self._validate_count,
            'total_time_ms': self._total_time,
            'avg_time_ms': avg_time,
            'performance_target': '<30ms',
            'is_target_met': avg_time < 30.0
        }
    
    def get_cache_info(self) -> Dict:
        """
        获取缓存信息
        
        Returns:
            dict: 缓存统计
        """
        cache_info = self.cache.get_cache_info()
        
        # 统计预期相关的缓存
        expectation_cache_keys = [
            k for k in cache_info.get('缓存键列表', [])
            if k.startswith('expectation_')
        ]
        
        return {
            '总缓存数': cache_info.get('缓存数量', 0),
            '预期相关缓存数': len(expectation_cache_keys),
            '预期缓存键列表': expectation_cache_keys
        }


# ==================== 全局实例 ====================

_auction_strength_validator: Optional[AuctionStrengthValidator] = None


def get_auction_strength_validator() -> AuctionStrengthValidator:
    """获取竞价强弱校验器单例"""
    global _auction_strength_validator
    if _auction_strength_validator is None:
        _auction_strength_validator = AuctionStrengthValidator()
    return _auction_strength_validator


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试竞价强弱校验器
    print("=" * 80)
    print("竞价强弱校验器测试")
    print("=" * 80)
    
    validator = get_auction_strength_validator()
    
    # 测试数据
    test_cases = [
        {
            'name': '焦点股超预期',
            'stock_code': '600519',
            'is_focus_stock': True,
            'auction_data': {
                'open_price': 1850.0,
                'prev_close': 1800.0,
                'volume_ratio': 2.5,
                'amount': 500000000,
                'high_price': 1860.0,
                'low_price': 1840.0,
                'is_limit_up': False
            }
        },
        {
            'name': '焦点股不及预期',
            'stock_code': '000001',
            'is_focus_stock': True,
            'auction_data': {
                'open_price': 15.0,
                'prev_close': 16.0,
                'volume_ratio': 0.8,
                'amount': 100000000,
                'high_price': 15.5,
                'low_price': 14.5,
                'is_limit_up': False
            }
        },
        {
            'name': '首板超预期',
            'stock_code': '300750',
            'is_focus_stock': False,
            'auction_data': {
                'open_price': 205.0,
                'prev_close': 200.0,
                'volume_ratio': 4.0,
                'amount': 300000000,
                'high_price': 208.0,
                'low_price': 202.0,
                'is_limit_up': False
            }
        },
        {
            'name': '首板爆量跳空',
            'stock_code': '600036',
            'is_focus_stock': False,
            'auction_data': {
                'open_price': 45.0,
                'prev_close': 42.0,
                'volume_ratio': 6.0,
                'amount': 400000000,
                'high_price': 46.0,
                'low_price': 44.0,
                'is_limit_up': False
            }
        },
        {
            'name': '基础通过',
            'stock_code': '601318',
            'is_focus_stock': False,
            'auction_data': {
                'open_price': 55.0,
                'prev_close': 53.0,
                'volume_ratio': 1.8,
                'amount': 200000000,
                'high_price': 56.0,
                'low_price': 54.0,
                'is_limit_up': False
            }
        },
        {
            'name': '未达阈值',
            'stock_code': '000858',
            'is_focus_stock': False,
            'auction_data': {
                'open_price': 18.0,
                'prev_close': 17.8,
                'volume_ratio': 1.2,
                'amount': 50000000,
                'high_price': 18.5,
                'low_price': 17.5,
                'is_limit_up': False
            }
        },
        {
            'name': '竞价涨停',
            'stock_code': '002475',
            'is_focus_stock': False,
            'auction_data': {
                'open_price': 35.0,
                'prev_close': 32.0,
                'volume_ratio': 3.5,
                'amount': 600000000,
                'high_price': 35.0,
                'low_price': 35.0,
                'is_limit_up': True
            }
        }
    ]
    
    print(f"\n测试用例数: {len(test_cases)}")
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        
        result = validator.validate_auction(
            test_case['stock_code'],
            test_case['auction_data'],
            test_case['is_focus_stock']
        )
        
        print(f"\n股票代码: {test_case['stock_code']}")
        print(f"是否焦点股: {'是' if test_case['is_focus_stock'] else '否'}")
        print(f"竞价数据:")
        print(f"  - 开盘价: {test_case['auction_data']['open_price']:.2f}")
        print(f"  - 昨收价: {test_case['auction_data']['prev_close']:.2f}")
        print(f"  - 量比: {test_case['auction_data']['volume_ratio']:.2f}")
        print(f"  - 成交额: {test_case['auction_data']['amount']/1e8:.2f}亿")
        print(f"  - 是否涨停: {'是' if test_case['auction_data']['is_limit_up'] else '否'}")
        
        print(f"\n验证结果:")
        print(f"  - 是否有效: {'✅ 是' if result['is_valid'] else '❌ 否'}")
        print(f"  - 操作建议: {result['action']}")
        print(f"  - 原因: {result['reason']}")
        print(f"  - 置信度: {result['confidence']:.2f}")
        
        details = result.get('details', {})
        print(f"\n详细信息:")
        print(f"  - 高开幅度: {details.get('open_gap_pct', 0)*100:.2f}%")
        print(f"  - 量比: {details.get('volume_ratio', 0):.2f}")
        print(f"  - 预期溢价: {details.get('expectation', 0)*100:.2f}%")
        print(f"  - 加分项: {details.get('bonus_points', 0):.2f}")
        if details.get('bonus_reasons'):
            print(f"  - 加分原因: {', '.join(details['bonus_reasons'])}")
        print(f"  - 计算耗时: {details.get('calculation_time_ms', 0):.2f}ms")
    
    print("\n" + "=" * 80)
    print("性能验证:")
    print("=" * 80)
    
    # 性能测试：批量验证
    batch_data = {
        test_case['stock_code']: test_case['auction_data']
        for test_case in test_cases
    }
    
    start_time = time.time()
    batch_results = validator.batch_validate(batch_data)
    elapsed_time = (time.time() - start_time) * 1000
    
    print(f"批量验证 {len(batch_data)} 只股票:")
    print(f"  总耗时: {elapsed_time:.2f}ms")
    print(f"  平均耗时: {elapsed_time/len(batch_data):.2f}ms/股")
    
    # 验证性能要求
    avg_time = elapsed_time / len(batch_data)
    if avg_time < 30:
        print(f"  ✅ 性能达标（<30ms）")
    else:
        print(f"  ❌ 性能不达标（>{30}ms）")
    
    # 获取性能统计
    stats = validator.get_performance_stats()
    print(f"\n性能统计:")
    print(f"  总验证次数: {stats['total_validations']}")
    print(f"  总耗时: {stats['total_time_ms']:.2f}ms")
    print(f"  平均耗时: {stats['avg_time_ms']:.2f}ms")
    print(f"  性能目标: {stats['performance_target']}")
    print(f"  目标达成: {'✅ 是' if stats['is_target_met'] else '❌ 否'}")
    
    print("\n" + "=" * 80)
    print("缓存信息:")
    print("=" * 80)
    cache_info = validator.get_cache_info()
    print(f"总缓存数: {cache_info['总缓存数']}")
    print(f"预期相关缓存数: {cache_info['预期相关缓存数']}")
    
    print("\n✅ 测试完成")
    print("=" * 80)
