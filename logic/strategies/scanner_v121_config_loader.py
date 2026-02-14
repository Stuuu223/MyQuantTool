#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 扫描器配置加载器

支持从配置文件加载扫描器配置，提供预设配置快速切换

Author: iFlow CLI
Date: 2026-02-14
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import Dict, Optional

from logic.utils.logger import get_logger
from logic.strategies.triple_funnel_scanner_v121 import get_scanner_v121, TripleFunnelScannerV121

logger = get_logger(__name__)


class ScannerV121ConfigLoader:
    """
    V12.1.0 扫描器配置加载器
    
    功能：
    1. 从配置文件加载扫描器配置
    2. 提供预设配置快速切换
    3. 支持动态更新配置
    """
    
    DEFAULT_CONFIG_PATH = "config/scanner_v121_config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path) if config_path else Path(self.DEFAULT_CONFIG_PATH)
        self.config = self._load_config()
        self._scanner: Optional[TripleFunnelScannerV121] = None
        
        logger.info(f"✅ [配置加载器] 初始化完成: {self.config_path}")
    
    def _load_config(self) -> Dict:
        """
        加载配置文件
        
        Returns:
            dict: 配置字典
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"✅ [配置加载器] 配置文件加载成功")
                return config
            else:
                logger.warning(f"⚠️ [配置加载器] 配置文件不存在: {self.config_path}，使用默认配置")
                return self._default_config()
        except Exception as e:
            logger.error(f"❌ [配置加载器] 配置文件加载失败: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """
        默认配置
        
        Returns:
            dict: 默认配置
        """
        return {
            "scanner_v121": {
                "filters": {
                    "wind_filter": {"enabled": True},
                    "dynamic_threshold": {"enabled": True, "config": {"sentiment_stage": "divergence"}},
                    "auction_validator": {"enabled": True}
                },
                "scan_config": {
                    "post_market_scan": {"max_stocks": 100}
                },
                "presets": {
                    "conservative": {
                        "filters": {"wind_filter": True, "dynamic_threshold": True, "auction_validator": True},
                        "sentiment_stage": "recession"
                    },
                    "aggressive": {
                        "filters": {"wind_filter": False, "dynamic_threshold": True, "auction_validator": False},
                        "sentiment_stage": "start"
                    },
                    "balanced": {
                        "filters": {"wind_filter": True, "dynamic_threshold": True, "auction_validator": True},
                        "sentiment_stage": "divergence"
                    }
                }
            }
        }
    
    def get_scanner(self, preset: str = "balanced", reload: bool = False) -> TripleFunnelScannerV121:
        """
        获取扫描器实例
        
        Args:
            preset: 预设配置名称（conservative/aggressive/balanced/ab_test_no_filters）
            reload: 是否重新加载扫描器
        
        Returns:
            TripleFunnelScannerV121: 扫描器实例
        """
        if self._scanner is None or reload:
            self._scanner = self._create_scanner(preset)
        
        return self._scanner
    
    def _create_scanner(self, preset: str) -> TripleFunnelScannerV121:
        """
        创建扫描器实例
        
        Args:
            preset: 预设配置名称
        
        Returns:
            TripleFunnelScannerV121: 扫描器实例
        """
        # 获取预设配置
        presets = self.config.get("scanner_v121", {}).get("presets", {})
        preset_config = presets.get(preset, presets.get("balanced", {}))
        
        # 提取过滤器配置
        filters_config = preset_config.get("filters", {})
        enable_wind_filter = filters_config.get("wind_filter", True)
        enable_dynamic_threshold = filters_config.get("dynamic_threshold", True)
        enable_auction_validator = filters_config.get("auction_validator", True)
        
        # 提取情绪周期
        sentiment_stage = preset_config.get("sentiment_stage", "divergence")
        
        logger.info(f"🔄 [配置加载器] 创建扫描器: {preset}")
        logger.info(f"   - 板块共振: {'✅' if enable_wind_filter else '❌'}")
        logger.info(f"   - 动态阈值: {'✅' if enable_dynamic_threshold else '❌'}")
        logger.info(f"   - 竞价校验: {'✅' if enable_auction_validator else '❌'}")
        logger.info(f"   - 情绪周期: {sentiment_stage}")
        
        # 创建扫描器
        scanner = get_scanner_v121(
            enable_wind_filter=enable_wind_filter,
            enable_dynamic_threshold=enable_dynamic_threshold,
            enable_auction_validator=enable_auction_validator,
            sentiment_stage=sentiment_stage
        )
        
        return scanner
    
    def switch_preset(self, preset: str) -> TripleFunnelScannerV121:
        """
        切换预设配置
        
        Args:
            preset: 预设配置名称
        
        Returns:
            TripleFunnelScannerV121: 新的扫描器实例
        """
        logger.info(f"🔄 [配置加载器] 切换预设配置: {preset}")
        return self.get_scanner(preset=preset, reload=True)
    
    def get_available_presets(self) -> list:
        """
        获取可用的预设配置列表
        
        Returns:
            list: 预设配置名称列表
        """
        presets = self.config.get("scanner_v121", {}).get("presets", {})
        return list(presets.keys())
    
    def get_preset_info(self, preset: str) -> Optional[Dict]:
        """
        获取预设配置信息
        
        Args:
            preset: 预设配置名称
        
        Returns:
            dict: 预设配置信息
        """
        presets = self.config.get("scanner_v121", {}).get("presets", {})
        return presets.get(preset)


# ==================== 全局实例 ====================

_config_loader: Optional[ScannerV121ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ScannerV121ConfigLoader:
    """
    获取配置加载器单例
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        ScannerV121ConfigLoader: 配置加载器实例
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ScannerV121ConfigLoader(config_path)
    return _config_loader


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 V12.1.0 扫描器配置加载器 - 演示")
    print("=" * 80)
    
    # 1. 获取配置加载器
    print("\n📝 步骤1: 获取配置加载器...")
    loader = get_config_loader()
    print("✅ 配置加载器加载成功")
    
    # 2. 查看可用预设
    print("\n📝 步骤2: 查看可用预设...")
    presets = loader.get_available_presets()
    print(f"✅ 可用预设: {', '.join(presets)}")
    
    # 3. 查看预设信息
    print("\n📝 步骤3: 查看预设信息...")
    for preset in presets:
        info = loader.get_preset_info(preset)
        if info and isinstance(info, dict):
            comment = info.get('comment', '无描述')
            print(f"\n  {preset}: {comment}")
            print(f"    过滤器: {info.get('filters', {})}")
            print(f"    情绪周期: {info.get('sentiment_stage', '未知')}")
        else:
            print(f"\n  {preset}: 配置无效")
    
    # 4. 创建扫描器（使用平衡模式）
    print("\n📝 步骤4: 创建扫描器（平衡模式）...")
    scanner_balanced = loader.get_scanner(preset="balanced")
    print(f"✅ 扫描器创建成功")
    
    # 5. 切换到保守模式
    print("\n📝 步骤5: 切换到保守模式...")
    scanner_conservative = loader.switch_preset("conservative")
    print(f"✅ 扫描器切换成功")
    
    # 6. 切换到激进模式
    print("\n📝 步骤6: 切换到激进模式...")
    scanner_aggressive = loader.switch_preset("aggressive")
    print(f"✅ 扫描器切换成功")
    
    # 7. 切换到 A/B 测试模式
    print("\n📝 步骤7: 切换到 A/B 测试模式...")
    scanner_ab_test = loader.switch_preset("ab_test_no_filters")
    print(f"✅ 扫描器切换成功")
    
    print("\n" + "=" * 80)
    print("✅ 演示完成")
    print("=" * 80)
