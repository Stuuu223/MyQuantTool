#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置管理器 - 统一参数管理 (SSOT - Single Source of Truth)
CTO强制实施：所有硬编码参数必须从此管理器获取，禁止在代码中硬编码任何数字

Author: CTO
Date: 2026-02-24
Version: V1.0 (工业级标准化版)
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from logic.core.path_resolver import PathResolver


class ConfigManager:
    """
    全局配置管理器 - SSOT (Single Source of Truth)
    
    CTO强制规范：
    1. 所有参数必须从strategy_params.json获取
    2. 禁止代码中出现任何硬编码数字
    3. 实盘与回演使用同一套参数配置
    """
    
    def __init__(self):
        """初始化配置管理器"""
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = PathResolver.get_config_dir() / 'strategy_params.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"❌ [ConfigManager] 加载配置文件失败: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置参数
        
        Args:
            key_path: 键路径，如 'halfway.volume_surge_percentile'
            default: 默认值
            
        Returns:
            配置参数值
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_volume_ratio_percentile(self, strategy: str = 'halfway') -> float:
        """获取量比分位数阈值"""
        if strategy == 'halfway':
            return self.get('halfway.volume_surge_percentile', 0.88)
        elif strategy == 'leader':
            return self.get('leader.volume_ratio_percentile', 0.90)
        elif strategy == 'true_attack':
            return self.get('true_attack.inflow_ratio_percentile', 0.99)
        elif strategy == 'trap':
            return self.get('trap.volume_spike_percentile', 0.95)
        else:
            return self.get('halfway.volume_surge_percentile', 0.88)
    
    def get_price_momentum_percentile(self, strategy: str = 'halfway') -> float:
        """获取价格动量分位数阈值"""
        if strategy == 'halfway':
            return self.get('halfway.price_momentum_percentile', 0.85)
        else:
            return self.get('halfway.price_momentum_percentile', 0.85)
    
    def get_turnover_rate_thresholds(self) -> Dict[str, float]:
        """获取换手率阈值 (从配置文件获取，支持实盘和回演统一)"""
        # 优先从配置文件获取，否则使用默认值
        live_sniper = self._config.get('live_sniper', {})
        return {
            'per_minute_min': live_sniper.get('turnover_rate_per_min_min', 0.2),      # 每分钟最小换手率
            'total_max': live_sniper.get('turnover_rate_max', 70.0),                  # 总换手率最大值 (CTO铁血令: 70%死亡线)
            'death_turnover_rate': live_sniper.get('death_turnover_rate', 70.0),      # 死亡换手率阈值 (CTO铁血令: 70%死亡线)
            'min_active_turnover_rate': live_sniper.get('min_active_turnover_rate', 3.0)  # 最低活跃换手率
        }
    
    def get_time_decay_ratios(self) -> Dict[str, float]:
        """获取时间衰减系数 (从配置文件获取，支持实盘和回演统一)"""
        # 优先从配置文件获取，否则使用默认值
        live_sniper = self._config.get('live_sniper', {})
        ratios = live_sniper.get('time_decay_ratios', {})
        return {
            'early_morning_rush': ratios.get('early_morning_rush', 1.2),    # 09:30-10:00 早盘冲刺
            'morning_confirm': ratios.get('morning_confirm', 1.0),          # 10:00-10:30 上午确认
            'noon_trash': ratios.get('noon_trash', 0.8),                    # 10:30-14:00 午间垃圾时间
            'tail_trap': ratios.get('tail_trap', 0.5)                       # 14:00-14:55 尾盘陷阱
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便捷函数
def get_param(key_path: str, default: Any = None) -> Any:
    """便捷获取参数函数"""
    return get_config_manager().get(key_path, default)


def get_volume_ratio_percentile(strategy: str = 'halfway') -> float:
    """便捷获取量比分位数函数"""
    return get_config_manager().get_volume_ratio_percentile(strategy)


def get_price_momentum_percentile(strategy: str = 'halfway') -> float:
    """便捷获取价格动量分位数函数"""
    return get_config_manager().get_price_momentum_percentile(strategy)


if __name__ == "__main__":
    # 测试配置管理器
    print("=" * 60)
    print("全局配置管理器测试")
    print("=" * 60)
    
    config_mgr = get_config_manager()
    
    print(f"半路策略量比分位数: {config_mgr.get_volume_ratio_percentile('halfway')}")
    print(f"龙头策略量比分位数: {config_mgr.get_volume_ratio_percentile('leader')}")
    print(f"价格动量分位数: {config_mgr.get_price_momentum_percentile()}")
    print(f"换手率阈值: {config_mgr.get_turnover_rate_thresholds()}")
    print(f"时间衰减比率: {config_mgr.get_time_decay_ratios()}")
    
    # 测试便捷函数
    print(f"便捷函数获取: {get_param('halfway.volume_surge_percentile')}")
    
    print("=" * 60)
    print("✅ 配置管理器测试完成")