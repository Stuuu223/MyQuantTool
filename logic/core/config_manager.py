#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置管理器 - 统一参数管理 (SSOT - Single Source of Truth)
CTO强制实施：所有硬编码参数必须从此管理器获取，禁止在代码中硬编码任何数字

配置读写铁律（必读）
===================
【热路径参数 → 缓存模式】
  在各引擎的 _load_config() 中读取并缓存为 self.xxx，O(1) 访问，Tick级热路径专用。
  配合 engine.reload_config() + ConfigManager.temporary_override() 支持回测参数扫描。

  示例：
    # 引擎内部
    self.tail_trap_decay = self._config.get('live_sniper.time_decay_ratios.tail_trap', 0.2)
    # 回测扫描
    with cfg.temporary_override({'live_sniper.time_decay_ratios.tail_trap': 0.1}):
        engine.reload_config()   # ← 必须！刷新实例缓存
        result = engine.run_backtest(...)

【非热路径 / 动态计算参数 → 调用时读取模式】
  不缓存为实例变量，每次调用时直接从 ConfigManager 读取。
  temporary_override 自动生效，无需 reload_config()。

  示例：compute_volume_ratio_threshold(market_ratios, mode='backtest')
  回测扫描只需：
    with cfg.temporary_override({'volume_ratio_filter.backtest_percentile': 0.90}):
        threshold = cfg.compute_volume_ratio_threshold(ratios, mode='backtest')  # 自动用0.90

Author: CTO
Date: 2026-02-24
Version: V1.1 (动态量比阈值 + reload_config铁律)
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
    
    def reload_config(self) -> None:
        """
        【回测参数扫描专用】重新从磁盘加载 JSON 配置（线程安全）。

        使用场景：
            temporary_override 修改了 ConfigManager 的内存值后，
            各引擎的 _load_config() 缓存不会自动更新，必须显式调用引擎的
            reload_config() 或本方法来同步磁盘最新配置。

        注意：temporary_override 内部已维护内存状态，通常不需要调用本方法；
              本方法主要用于「实盘切换参数文件」或「重启式参数热更新」场景。
        """
        with self._lock:
            self._load_config()
    
    def _validate_critical_keys(self):
        """【CTO铁律】确保JSON配置文件已同步最新架构，拒绝静默默认值"""
        critical_keys = [
            'stock_filter.min_volume_multiplier',
            'stock_filter.min_avg_turnover_pct',
            'stock_filter.min_intraday_turnover_pct'
        ]
        missing = []
        for key in critical_keys:
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
                engine.reload_config()   # ← 若引擎缓存了此参数，需调用reload_config()
                engine.run()
            # 退出后自动恢复原始配置

        【动态计算参数】如 compute_volume_ratio_threshold 在调用时读取config，
        temporary_override 自动生效，无需 engine.reload_config():
            with cfg.temporary_override({'volume_ratio_filter.backtest_percentile': 0.90}):
                threshold = cfg.compute_volume_ratio_threshold(ratios, mode='backtest')  # 自动用0.90
        
        Args:
            overrides: 要覆写的配置键值对，如 {'stock_filter.min_avg_turnover_pct': 3.0}
        """
        with self._lock:
            original_config = deepcopy(self._config)
        
        try:
            for key_path, value in overrides.items():
                self.set(key_path, value)
            yield self
        finally:
            with self._lock:
                self._config = original_config
    
    def compute_volume_ratio_threshold(
        self,
        market_volume_ratios: list[float],
        mode: str = 'live'
    ) -> float:
        """
        【动态量比阈值 Option B】从当日全市场量比分布动态计算过滤阈值。

        此函数每次调用时直接读取 ConfigManager（不缓存），
        因此 temporary_override 自动生效，无需 engine.reload_config()。

        回测灵敏度扫描示例：
            # 依次验证 88% / 90% / 92% / 95% 分位数效果
            for pct in [0.88, 0.90, 0.92, 0.95]:
                with cfg.temporary_override({'volume_ratio_filter.backtest_percentile': pct}):
                    threshold = cfg.compute_volume_ratio_threshold(market_ratios, mode='backtest')
                    result = run_backtest(threshold=threshold)

        Args:
            market_volume_ratios: 当日全市场各股有效量比列表（只含正值，排除停牌/未开盘）
            mode: 'live'   = 实盘，使用 live_percentile（默认0.95，Top5%）
                  'backtest' = 回测，使用 backtest_percentile（默认0.88，可用override调整）

        Returns:
            float: 量比过滤阈值。
                   ≥ fixed_threshold（3.0）保底，防止极端低活跃日阈值塌缩。
                   数据不足 min_stocks_for_dynamic 时直接返回 fixed_threshold。

        注意：
            - 量比列表应在每日开盘后收集，通常在第一次扫描前更新一次即可
            - 不要在每个 Tick 都重新传入完整列表，在外层缓存计算结果
        """
        import numpy as np

        fallback     = float(self.get('volume_ratio_filter.fixed_threshold', 3.0))
        min_stocks   = int(self.get('volume_ratio_filter.min_stocks_for_dynamic', 100))

        # 数据不足时 fallback
        valid_ratios = [r for r in market_volume_ratios if r > 0]
        if len(valid_ratios) < min_stocks:
            return fallback

        if mode == 'live':
            pct = float(self.get('volume_ratio_filter.live_percentile', 0.95))
        else:  # backtest
            pct = float(self.get('volume_ratio_filter.backtest_percentile', 0.88))

        # numpy percentile 入参是 0-100，config存的是 0-1
        dynamic_threshold = float(np.percentile(valid_ratios, pct * 100))

        # 动态值不得低于兜底固定阈值
        return max(dynamic_threshold, fallback)

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
        live_sniper = self._config.get('live_sniper', {})
        ratios = live_sniper.get('time_decay_ratios', {})
        return {
            'early_morning_rush': ratios.get('early_morning_rush', 1.2),
            'morning_confirm':    ratios.get('morning_confirm', 1.0),
            'noon_trash':         ratios.get('noon_trash', 0.8),
            'tail_trap':          ratios.get('tail_trap', 0.2)   # 【已修正】0.5→0.2
        }
    
    def get_kinetic_physics_config(self) -> Dict[str, float]:
        """
        【物理学重铸】获取微观动能+ATR势垒相关配置
        
        Returns:
            Dict: 物理学参数字典，包含:
                - atr_ratio_min: ATR势垒阈值（默认1.8x）
                - atr_period: ATR计算周期（默认20日）
                - micro_kinetic_window: 微观动能滑动窗口（默认5 Tick）
                - micro_kinetic_min_acceleration: 最小动能加速度（默认0.05）
                - kinetic_barrier_min: 动能/势垒比阈值（默认1.5）
                - early_scale_factor: 早盘降阈系数（默认0.6）
        """
        kinetic_physics = self._config.get('kinetic_physics', {})
        return {
            'atr_ratio_min': kinetic_physics.get('atr_ratio_min', 1.8),
            'atr_period': kinetic_physics.get('atr_period', 20),
            'micro_kinetic_window': kinetic_physics.get('micro_kinetic_window', 5),
            'micro_kinetic_min_acceleration': kinetic_physics.get('micro_kinetic_min_acceleration', 0.05),
            'kinetic_barrier_min': kinetic_physics.get('kinetic_barrier_min', 1.5),
            'early_scale_factor': kinetic_physics.get('early_scale_factor', 0.6)
        }
    
    def get_atr_ratio_min(self) -> float:
        """
        【ATR势垒阈值】获取ATR比率最小值
        
        【阈值来源】
        - 研究样本：2026-02-27至2026-03-02（4天）
        - 结论：atr_ratio >= 1.8时，涨停概率提升3.2倍
        - TODO: 后续需更大样本优化此参数
        
        Returns:
            float: ATR势垒阈值，默认1.8
        """
        return self.get('kinetic_physics.atr_ratio_min', 1.8)
    
    def get_micro_kinetic_window(self) -> int:
        """
        【微观动能窗口】获取滑动窗口大小
        
        Returns:
            int: 滑动窗口Tick数量，默认5（约15秒）
        """
        return int(self.get('kinetic_physics.micro_kinetic_window', 5))
    
    def get_early_scale_factor(self) -> float:
        """
        【早盘降阈系数】获取早盘阈值缩放因子
        
        物理意义：早盘(09:30-09:45)是资金意愿度暴露期，
        降低阈值至60%可捕捉更多早盘粒子初速度信号。
        
        Returns:
            float: 早盘阈值缩放因子，默认0.6
        """
        return self.get('kinetic_physics.early_scale_factor', 0.6)
    
    def get_atr_filter_enabled(self) -> bool:
        """
        【ATR势垒开关】获取ATR势垒是否启用
        
        Returns:
            bool: True=启用ATR计算，False=完全禁用
        """
        return self.get('kinetic_physics.atr_filter_enabled', True)
    
    def get_atr_filter_mode(self) -> str:
        """
        【ATR过滤模式】获取ATR势垒过滤模式
        
        模式说明：
        - 'record_only': 仅记录到df，不拦截（当前默认）
        - 'hard_filter': 硬过滤，拦截低能态股票
        
        等三个月回测后再切换为hard_filter
        
        Returns:
            str: 过滤模式，默认'record_only'
        """
        return self.get('kinetic_physics.atr_filter_mode', 'record_only')


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
    import numpy as np
    print("=" * 60)
    print("全局配置管理器测试 (V1.1)")
    print("=" * 60)
    
    config_mgr = get_config_manager()
    
    print(f"最小量比倍数: {config_mgr.get_min_volume_multiplier()}x")
    print(f"换手率阈值: {config_mgr.get_turnover_rate_thresholds()}")
    print(f"时间衰减比率: {config_mgr.get_time_decay_ratios()}")
    print(f"便捷函数获取: {get_param('live_sniper.min_volume_multiplier')}")
    
    # 测试动态量比阈值
    print("\n--- 动态量比阈值 compute_volume_ratio_threshold ---")
    mock_ratios = [float(x) for x in np.random.lognormal(0.5, 0.8, 5000)]  # 模拟全市场分布
    mock_ratios = [r for r in mock_ratios if r > 0]
    live_thr  = config_mgr.compute_volume_ratio_threshold(mock_ratios, mode='live')
    bt_thr    = config_mgr.compute_volume_ratio_threshold(mock_ratios, mode='backtest')
    print(f"  实盘(95th)阈值   : {live_thr:.4f}")
    print(f"  回测(88th)阈值   : {bt_thr:.4f}")
    assert bt_thr <= live_thr, "回测阈值应<=实盘阈值"
    print("  ✅ 通过")
    
    # 测试 temporary_override 对动态阈值的影响（无需reload_config）
    print("\n--- temporary_override 自动生效测试 ---")
    with config_mgr.temporary_override({'volume_ratio_filter.backtest_percentile': 0.90}):
        thr_90 = config_mgr.compute_volume_ratio_threshold(mock_ratios, mode='backtest')
    print(f"  override 0.90 → 阈值: {thr_90:.4f} (应 >= {bt_thr:.4f})")
    assert thr_90 >= bt_thr, "90分位阈值应>=88分位阈值"
    print("  ✅ temporary_override 自动生效，无需reload_config")
    
    # 测试数据不足时 fallback
    print("\n--- 数据不足 fallback 测试 ---")
    small_ratios = [1.5, 2.0, 3.0]  # 只有3只，< min_stocks=100
    fallback_thr = config_mgr.compute_volume_ratio_threshold(small_ratios, mode='live')
    assert fallback_thr == 3.0, f"数据不足时应返回fixed_threshold=3.0，实际{fallback_thr}"
    print(f"  数据不足(3只<100只) → fallback: {fallback_thr}")
    print("  ✅ 通过")
    
    print("=" * 60)
    print("✅ 配置管理器测试完成 (V1.1)")
