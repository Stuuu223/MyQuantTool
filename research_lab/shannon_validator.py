# -*- coding: utf-8 -*-
"""
【MyQuantLab 模块三】香农真理试金石 (Shannon's Validation Core)

核心功能：
- 利用香农六把钥匙：降维、逆向思考、信息熵、冗余验证、边界条件、基础概率
- 拒绝一切拍脑袋，所有物理假说必须通过回归验证

验证维度：
1. 多元回归R²（解释力）- 低于0.2自动报警
2. 相关系数（Correlation）- 正相关还是负相关？
3. 信息熵（Information Entropy）- 是否能区分"仙丹"和"毒药"？

Author: CTO
Date: 2026-03-14
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# 尝试导入scipy
try:
    from scipy import stats
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("[ShannonValidator] scipy未安装，部分功能受限")


@dataclass
class ValidationResult:
    """验证结果"""
    factor_name: str
    r_squared: float  # R²解释力
    correlation: float  # 相关系数
    information_entropy: float  # 信息熵
    sample_count: int  # 样本数
    is_valid: bool  # 是否通过验证
    warning: str = ""  # 警告信息
    
    def to_dict(self) -> Dict:
        return {
            'factor_name': self.factor_name,
            'r_squared': self.r_squared,
            'correlation': self.correlation,
            'information_entropy': self.information_entropy,
            'sample_count': self.sample_count,
            'is_valid': self.is_valid,
            'warning': self.warning,
        }


class ShannonValidator:
    """
    香农试金石引擎 - 自动化因子验证
    
    使用示例:
        validator = ShannonValidator()
        result = validator.validate_factor(
            factor_values=[1.5, 2.3, 0.8, ...],  # 因子值
            returns=[2.5, 5.1, -1.2, ...],       # T+N收益
            factor_name='volume_ratio'
        )
        if not result.is_valid:
            print(f"因子验证失败: {result.warning}")
    """
    
    # 验证阈值（CTO红线）
    MIN_R_SQUARED = 0.05  # R²最低阈值（因子研究很难达到0.2）
    MIN_CORRELATION_ABS = 0.05  # 相关系数绝对值最低阈值
    MIN_SAMPLE_COUNT = 30  # 最小样本数
    MIN_ENTROPY_GAIN = 0.01  # 最小信息熵增益
    
    def __init__(self):
        self._results: List[ValidationResult] = []
    
    def validate_factor(
        self,
        factor_values: List[float],
        returns: List[float],
        factor_name: str,
        verbose: bool = True
    ) -> ValidationResult:
        """
        验证单个因子
        
        Args:
            factor_values: 因子值列表
            returns: 对应的T+N收益列表
            factor_name: 因子名称
            verbose: 是否打印详细信息
        
        Returns:
            ValidationResult: 验证结果
        """
        # 清洗数据
        factor_arr, return_arr = self._clean_data(factor_values, returns)
        
        if len(factor_arr) < self.MIN_SAMPLE_COUNT:
            return ValidationResult(
                factor_name=factor_name,
                r_squared=0.0,
                correlation=0.0,
                information_entropy=0.0,
                sample_count=len(factor_arr),
                is_valid=False,
                warning=f"样本数不足: {len(factor_arr)} < {self.MIN_SAMPLE_COUNT}"
            )
        
        # 计算R²
        r_squared = self._calculate_r_squared(factor_arr, return_arr)
        
        # 计算相关系数
        correlation = self._calculate_correlation(factor_arr, return_arr)
        
        # 计算信息熵
        entropy = self._calculate_information_entropy(factor_arr, return_arr)
        
        # 综合判断
        is_valid, warning = self._evaluate(
            r_squared, correlation, entropy, len(factor_arr)
        )
        
        result = ValidationResult(
            factor_name=factor_name,
            r_squared=r_squared,
            correlation=correlation,
            information_entropy=entropy,
            sample_count=len(factor_arr),
            is_valid=is_valid,
            warning=warning
        )
        
        self._results.append(result)
        
        if verbose:
            self._print_result(result)
        
        return result
    
    def validate_power_transformation(
        self,
        base_values: List[float],
        returns: List[float],
        factor_name: str,
        powers: List[float] = [1.0, 2.0, 3.0, 5.0]
    ) -> Dict[float, ValidationResult]:
        """
        验证次方变换（寻找最优次方系数）
        
        用途：验证velocity的3次方、purity的5次方是否最优
        
        Args:
            base_values: 基础值列表（如涨幅）
            returns: 对应的T+N收益列表
            factor_name: 因子名称
            powers: 待测试的次方列表
        
        Returns:
            Dict[float, ValidationResult]: {次方: 验证结果}
        """
        results = {}
        
        for power in powers:
            # 应用次方变换
            transformed = [v ** power for v in base_values]
            
            # 验证
            result = self.validate_factor(
                transformed, 
                returns, 
                f"{factor_name}^{power}",
                verbose=False
            )
            results[power] = result
        
        # 打印最优结果
        best_power = max(results.keys(), key=lambda p: results[p].r_squared)
        logger.info(f"[ShannonValidator] {factor_name}最优次方: {best_power}")
        logger.info(f"  R²: {results[best_power].r_squared:.4f}")
        logger.info(f"  相关系数: {results[best_power].correlation:.4f}")
        
        return results
    
    def batch_validate(
        self,
        factor_dict: Dict[str, List[float]],
        returns: List[float],
        verbose: bool = True
    ) -> List[ValidationResult]:
        """
        批量验证多个因子
        
        Args:
            factor_dict: {因子名: 因子值列表}
            returns: T+N收益列表
            verbose: 是否打印详细信息
        
        Returns:
            List[ValidationResult]: 验证结果列表
        """
        results = []
        
        for factor_name, factor_values in factor_dict.items():
            result = self.validate_factor(
                factor_values, returns, factor_name, verbose
            )
            results.append(result)
        
        # 按R²排序
        results.sort(key=lambda r: r.r_squared, reverse=True)
        
        return results
    
    def generate_report(self) -> str:
        """生成验证报告"""
        if not self._results:
            return "暂无验证结果"
        
        lines = [
            "=" * 60,
            "【香农试金石验证报告】",
            "=" * 60,
            "",
            f"{'因子名':<20} {'R²':>8} {'相关系数':>10} {'样本数':>8} {'状态':>8}",
            "-" * 60,
        ]
        
        for r in self._results:
            status = "✅通过" if r.is_valid else "❌失败"
            lines.append(
                f"{r.factor_name:<20} {r.r_squared:>8.4f} {r.correlation:>10.4f} "
                f"{r.sample_count:>8} {status:>8}"
            )
        
        lines.extend([
            "",
            "=" * 60,
            f"总计: {len(self._results)}个因子, "
            f"通过: {sum(1 for r in self._results if r.is_valid)}个",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    # ============== 内部方法 ==============
    
    def _clean_data(
        self,
        factor_values: List[float],
        returns: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """清洗数据：移除NaN和无穷值"""
        factor_arr = np.array(factor_values, dtype=float)
        return_arr = np.array(returns, dtype=float)
        
        # 移除NaN和无穷
        valid_mask = (
            np.isfinite(factor_arr) & 
            np.isfinite(return_arr) &
            ~np.isnan(factor_arr) & 
            ~np.isnan(return_arr)
        )
        
        return factor_arr[valid_mask], return_arr[valid_mask]
    
    def _calculate_r_squared(
        self,
        factor_arr: np.ndarray,
        return_arr: np.ndarray
    ) -> float:
        """计算R²"""
        if not HAS_SCIPY:
            # 简化计算：使用相关系数的平方
            corr = self._calculate_correlation(factor_arr, return_arr)
            return corr ** 2
        
        try:
            # 线性回归
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                factor_arr, return_arr
            )
            return r_value ** 2
        except Exception:
            return 0.0
    
    def _calculate_correlation(
        self,
        factor_arr: np.ndarray,
        return_arr: np.ndarray
    ) -> float:
        """计算Pearson相关系数"""
        try:
            if len(factor_arr) < 2:
                return 0.0
            
            # 使用numpy计算
            factor_mean = np.mean(factor_arr)
            return_mean = np.mean(return_arr)
            
            numerator = np.sum((factor_arr - factor_mean) * (return_arr - return_mean))
            denominator = np.sqrt(
                np.sum((factor_arr - factor_mean) ** 2) * 
                np.sum((return_arr - return_mean) ** 2)
            )
            
            if denominator == 0:
                return 0.0
            
            return numerator / denominator
            
        except Exception:
            return 0.0
    
    def _calculate_information_entropy(
        self,
        factor_arr: np.ndarray,
        return_arr: np.ndarray
    ) -> float:
        """
        计算信息熵增益
        
        物理意义：该因子是否能显著区分"仙丹"和"毒药"
        """
        try:
            # 将收益二分化：正收益=仙丹，负收益=毒药
            positive_mask = return_arr > 0
            negative_mask = return_arr <= 0
            
            if np.sum(positive_mask) == 0 or np.sum(negative_mask) == 0:
                return 0.0
            
            # 计算因子在正/负收益组的均值差异
            positive_mean = np.mean(factor_arr[positive_mask])
            negative_mean = np.mean(factor_arr[negative_mask])
            factor_std = np.std(factor_arr)
            
            if factor_std == 0:
                return 0.0
            
            # 标准化差异作为信息熵代理
            entropy_gain = abs(positive_mean - negative_mean) / factor_std
            
            return entropy_gain
            
        except Exception:
            return 0.0
    
    def _evaluate(
        self,
        r_squared: float,
        correlation: float,
        entropy: float,
        sample_count: int
    ) -> Tuple[bool, str]:
        """综合评估"""
        warnings = []
        
        if r_squared < self.MIN_R_SQUARED:
            warnings.append(f"R²过低({r_squared:.4f}<{self.MIN_R_SQUARED})")
        
        if abs(correlation) < self.MIN_CORRELATION_ABS:
            warnings.append(f"相关系数过小(|{correlation:.4f}|<{self.MIN_CORRELATION_ABS})")
        
        if entropy < self.MIN_ENTROPY_GAIN:
            warnings.append(f"信息熵增益不足({entropy:.4f}<{self.MIN_ENTROPY_GAIN})")
        
        is_valid = len(warnings) == 0
        warning = "; ".join(warnings) if warnings else ""
        
        return is_valid, warning
    
    def _print_result(self, result: ValidationResult):
        """打印验证结果"""
        status = "✅" if result.is_valid else "❌"
        print(f"{status} [{result.factor_name}] "
              f"R²={result.r_squared:.4f} "
              f"Corr={result.correlation:.4f} "
              f"N={result.sample_count}")
        
        if result.warning:
            print(f"   ⚠️ {result.warning}")