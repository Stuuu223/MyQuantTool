#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常识护栏与熔断器 - 防止明显错误的数据污染系统

老板指出的"一眼假"数据，在这里被自动拦截
"""
from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SanityGuards:
    """
    常识护栏 - 数据的最后防线
    
    所有计算结果必须通过这里的检查，否则系统拒绝继续运行
    """
    
    # 涨停限制定义
    GEM_LIMIT_UP = 20.0      # 创业板
    MAIN_LIMIT_UP = 10.0     # 主板
    STAR_LIMIT_UP = 20.0     # 科创板/北交所
    
    # 异常阈值
    MAX_REASONABLE_CHANGE = 100.0  # 最大合理涨幅100%（ST股可能超过20%）
    MIN_VOLUME = 0              # 最小成交量
    MAX_SCORE = 200.0           # 最大合理得分
    
    @classmethod
    def check_price_change(cls, change_pct: float, stock_code: str = '') -> Tuple[bool, str]:
        """
        检查涨幅是否合理
        
        Args:
            change_pct: 涨跌幅百分比
            stock_code: 股票代码（用于判断板块）
        
        Returns:
            (通过检查, 信息/错误信息)
        """
        if abs(change_pct) > cls.MAX_REASONABLE_CHANGE:
            error_msg = f"涨幅异常：{change_pct:.2f}%，超过合理范围（±{cls.MAX_REASONABLE_CHANGE}%）"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        # 根据股票代码判断板块涨停限制
        if stock_code:
            if stock_code.startswith('3'):  # 创业板
                limit = cls.GEM_LIMIT_UP
            elif stock_code.startswith('68') or stock_code.startswith('8') or stock_code.startswith('4'):
                limit = cls.STAR_LIMIT_UP
            else:
                limit = cls.MAIN_LIMIT_UP
            
            if abs(change_pct) > limit + 1.0:  # 允许1%误差
                if abs(change_pct) > limit * 2:
                    error_msg = f"涨幅严重异常：{change_pct:.2f}%，超过{limit}%涨停限制的2倍"
                    logger.error(f"[SanityGuards] {error_msg}")
                    return False, error_msg
                else:
                    warning_msg = f"注意：涨幅{change_pct:.2f}%超过正常涨停限制{limit}%"
                    logger.warning(f"[SanityGuards] {warning_msg}")
                    return True, warning_msg
        
        return True, "通过"
    
    @classmethod
    def check_score_consistency(cls, base_score: float, final_score: float, 
                                stock_code: str = '') -> Tuple[bool, str]:
        """
        检查得分一致性
        
        核心检查：如果final_score为0但base_score>0，说明惩罚机制出错
        
        Args:
            base_score: 基础分
            final_score: 最终得分
            stock_code: 股票代码
        """
        if final_score == 0.0 and base_score > 0:
            error_msg = f"{stock_code} 得分逻辑错误：基础分{basis_score:.2f}>0但最终得分=0，检查惩罚机制"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        if final_score < 0:
            error_msg = f"最终得分异常：{final_score}，不能为负数"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        if final_score > cls.MAX_SCORE:
            error_msg = f"最终得分异常：{final_score}，超出合理范围[0, {cls.MAX_SCORE}]"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        if base_score < 0 or base_score > 100:
            warning_msg = f"基础分异常：{base_score}，正常范围[0, 100]"
            logger.warning(f"[SanityGuards] {warning_msg}")
            return True, warning_msg
        
        return True, "通过"
    
    @classmethod
    def check_volume_reasonable(cls, volume: float, avg_volume_5d: float = 0) -> Tuple[bool, str]:
        """
        检查成交量是否合理
        """
        if volume < 0:
            error_msg = f"成交量不能为负数：{volume}"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        if volume == 0:
            error_msg = "成交量为0"
            logger.warning(f"[SanityGuards] {error_msg}")
            return True, error_msg  # 警告但允许通过
        
        if avg_volume_5d > 0:
            ratio = volume / avg_volume_5d
            if ratio > 50:
                error_msg = f"成交量异常：当日{volume}是5日均量{avg_volume_5d}的{ratio:.1f}倍"
                logger.error(f"[SanityGuards] {error_msg}")
                return False, error_msg
            elif ratio > 20:
                warning_msg = f"成交量显著放大：是5日均量的{ratio:.1f}倍"
                logger.warning(f"[SanityGuards] {warning_msg}")
                return True, warning_msg
        
        return True, "通过"
    
    @classmethod
    def check_pre_close_valid(cls, pre_close: float, stock_code: str = '') -> Tuple[bool, str]:
        """
        检查昨收价是否有效
        """
        if pre_close <= 0:
            error_msg = f"{stock_code} 昨收价无效：{pre_close}，必须大于0"
            logger.error(f"[SanityGuards] {error_msg}")
            return False, error_msg
        
        if pre_close > 10000:
            warning_msg = f"{stock_code} 昨收价{pre_close}异常高，请检查"
            logger.warning(f"[SanityGuards] {warning_msg}")
            return True, warning_msg
        
        return True, "通过"
    
    @classmethod
    def full_sanity_check(cls, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        完整 Sanity Check
        
        Args:
            data: 包含以下键的字典
                - stock_code: 股票代码
                - change_pct: 涨跌幅
                - base_score: 基础分
                - final_score: 最终得分
                - volume: 成交量
                - avg_volume_5d: 5日均量（可选）
                - pre_close: 昨收价（可选）
        
        Returns:
            (全部通过, 错误/警告列表)
        """
        errors = []
        stock_code = data.get('stock_code', 'Unknown')
        
        # 检查1：昨收价
        if 'pre_close' in data:
            passed, msg = cls.check_pre_close_valid(data['pre_close'], stock_code)
            if not passed:
                errors.append(msg)
        
        # 检查2：涨幅
        if 'change_pct' in data:
            passed, msg = cls.check_price_change(data['change_pct'], stock_code)
            if not passed:
                errors.append(msg)
        
        # 检查3：得分一致性
        if 'base_score' in data and 'final_score' in data:
            passed, msg = cls.check_score_consistency(
                data['base_score'],
                data['final_score'],
                stock_code
            )
            if not passed:
                errors.append(msg)
        
        # 检查4：成交量
        if 'volume' in data:
            avg_vol = data.get('avg_volume_5d', 0)
            passed, msg = cls.check_volume_reasonable(data['volume'], avg_vol)
            if not passed:
                errors.append(msg)
        
        all_passed = len([e for e in errors if "错误" in e or "异常" in e]) == 0
        
        if all_passed:
            logger.info(f"[SanityGuards] {stock_code} 通过全部检查")
        else:
            logger.error(f"[SanityGuards] {stock_code} 未通过检查：{errors}")
        
        return all_passed, errors


# 便捷函数
def sanity_check(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """便捷函数：执行完整检查"""
    return SanityGuards.full_sanity_check(data)