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
import threading
from contextlib import contextmanager
from copy import deepcopy
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
        self._lock = threading.Lock()  # 【线程安全】配置读写锁
        self._load_config()
        self._validate_critical_keys()  # 【CTO铁律】启动时强制校验核心配置
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = PathResolver.get_config_dir() / 'strategy_params.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"❌ [ConfigManager] 加载配置文件失败: {e}")
    
    def _validate_critical_keys(self):
        """【CTO铁律】确保JSON配置文件已同步最新架构，拒绝静默默认值"""
        critical_keys = [
            'stock_filter.min_volume_multiplier',
            'stock_filter.min_avg_turnover_pct',
            'stock_filter.min_intraday_turnover_pct'
        ]
        missing = []
        for key in critical_keys:
            # 尝试深层读取
            keys = key.split('.')
            val = self._config
            try:
                for k in keys:
                    val = val[k]
            except KeyError:
                missing.append(key)
                
        if missing:
            error_msg = f"❌ [配置断言失败] strategy_params.json 缺少核心键值: {missing}。请立即更新配置文件！"
            print(error_msg)
            # 自动修复或硬报错，这里选择抛出异常逼迫修复
            raise RuntimeError(error_msg)
    
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
    
    def set(self, key_path: str, value: Any) -> None:
        """
        通过点分路径设置配置值
        
        Args:
            key_path: 键路径，如 'stock_filter.min_avg_turnover_pct'
            value: 要设置的值
        """
        keys = key_path.split('.')
        with self._lock:
            node = self._config
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = value
    
    @contextmanager
    def temporary_override(self, overrides: Dict[str, Any]):
        """
        线程安全的临时配置覆写上下文管理器
        
        用法:
            with cfg.temporary_override({'stock_filter.min_avg_turnover_pct': 3.0}):
                engine.run()
            # 退出后自动恢复原始配置
        
        Args:
            overrides: 要覆写的配置键值对，如 {'stock_filter.min_avg_turnover_pct': 3.0}
        """
        # 深拷贝当前配置，保留原始状态
        with self._lock:
            original_config = deepcopy(self._config)
        
        try:
            # 通过合法setter写入覆写值
            for key_path, value in overrides.items():
                self.set(key_path, value)
            yield self
        finally:
            # 无论是否异常，必定恢复
            with self._lock:
                self._config = original_config
    
    def get_min_volume_multiplier(self) -> float:
        """【V20.5唯一真理】获取最小量比倍数阈值 - 从 live_sniper.min_volume_multiplier 读取"""
        return self.get('live_sniper.min_volume_multiplier', 3.0)
    
    def get_turnover_rate_thresholds(self) -> Dict[str, float]:
        """【CTO规范化】获取换手率阈值，严禁缩进错乱"""
        return {
            'min_avg_turnover_pct': self.get('stock_filter.min_avg_turnover_pct', 3.0),
            'min_intraday_turnover_pct': self.get('stock_filter.min_intraday_turnover_pct', 5.0),
            'per_minute_min': self.get('live_sniper.turnover_rate_per_min_min', 0.2),
            'total_max': self.get('live_sniper.turnover_rate_max', 300.0),
            'death_turnover_rate': self.get('live_sniper.death_turnover_rate', 300.0),
            'min_active_turnover_rate': self.get('live_sniper.min_active_turnover_rate', 3.0)
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


def get_min_volume_multiplier() -> float:
    """【V20.5唯一真理】便捷获取最小量比倍数"""
    return get_config_manager().get_min_volume_multiplier()


if __name__ == "__main__":
    # 测试配置管理器
    print("=" * 60)
    print("全局配置管理器测试 (V20.5)")
    print("=" * 60)
    
    config_mgr = get_config_manager()
    
    print(f"最小量比倍数: {config_mgr.get_min_volume_multiplier()}x")
    print(f"换手率阈值: {config_mgr.get_turnover_rate_thresholds()}")
    print(f"时间衰减比率: {config_mgr.get_time_decay_ratios()}")
    
    # 测试便捷函数
    print(f"便捷函数获取: {get_param('live_sniper.min_volume_multiplier')}")
    
    print("=" * 60)
    print("✅ 配置管理器测试完成 (V20.5)")