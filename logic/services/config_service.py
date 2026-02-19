# -*- coding: utf-8 -*-
"""
配置服务 - 统一配置管理 (Config Service)

所有配置必须通过此服务读取，禁止直接访问config/目录文件。
整合31个散落配置文件为统一接口。
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / 'config'


@dataclass
class StrategyConfig:
    """策略配置"""
    halfway_params: Dict[str, Any]
    leader_thresholds: Dict[str, Any]
    true_attack_thresholds: Dict[str, Any]


@dataclass
class DataConfig:
    """数据配置"""
    qmt_token: str
    vip_servers: list
    data_home: str


class ConfigService:
    """
    配置服务 - 统一入口
    
    取代直接访问的31个配置文件：
    - wanzhu_*.json (6个) → get_wanzhu_config()
    - *_config.json (15个) → get_module_config(module)
    - *.py paths → get_paths()
    """
    
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_json(self, filename: str) -> Dict:
        """加载JSON配置文件（带缓存）"""
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = CONFIG_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"配置文件不存在: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self._cache[filename] = data
            return data
    
    def get_strategy_config(self) -> StrategyConfig:
        """获取策略配置（整合halfway/leader/true_attack）"""
        halfway = self._load_json('exp_capital_attack_config.json')
        true_attack = self._load_json('true_attack_config.json')
        
        return StrategyConfig(
            halfway_params=halfway.get('thresholds', {}),
            leader_thresholds={'min_change': 7.0, 'min_volume_ratio': 2.0},
            true_attack_thresholds=true_attack.get('ratio_thresholds', {})
        )
    
    def get_data_config(self) -> DataConfig:
        """获取数据配置（整合QMT/数据路径）"""
        qmt_config = self._load_json('qmt_config.json')
        
        return DataConfig(
            qmt_token=qmt_config.get('vip_token', ''),
            vip_servers=qmt_config.get('vip_servers', []),
            data_home=str(PROJECT_ROOT / 'data' / 'qmt_data')
        )
    
    def get_stock_universe(self, name: str = 'wanzhu_selected') -> list:
        """获取股票池（整合所有wanzhu_*.json）"""
        mapping = {
            'wanzhu_top150': 'wanzhu_top150_tick_download.json',
            'wanzhu_selected': 'wanzhu_selected_150.csv',  # 特殊处理CSV
            'wanzhu_top50': 'wanzhu_top50_usable.json',
            'wanzhu_big_movers': 'wanzhu_big_movers.json'
        }
        
        filename = mapping.get(name, f'{name}.json')
        
        if filename.endswith('.csv'):
            import pandas as pd
            df = pd.read_csv(CONFIG_DIR.parent / 'data' / 'wanzhu_data' / 'processed' / filename)
            return df['code'].tolist()
        else:
            data = self._load_json(filename)
            return data.get('stocks', [])
    
    def get_module_config(self, module: str) -> Dict:
        """获取模块配置（通用接口）"""
        config_files = {
            'market_scan': 'market_scan_config.json',
            'signal': 'signal_config.json',
            'portfolio': 'portfolio_config.json',
            'scanner': 'scanner_v121_config.json'
        }
        
        filename = config_files.get(module, f'{module}_config.json')
        return self._load_json(filename)
    
    def clear_cache(self):
        """清除配置缓存（配置热更新时用）"""
        self._cache.clear()


# 全局配置服务实例
config_service = ConfigService()
