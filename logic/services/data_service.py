#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据服务统一入口
CTO指令：所有数据访问必须通过此Service，禁止脚本直接拼路径
"""

import json
from pathlib import Path
from typing import Optional, Tuple, Dict
import pandas as pd
from datetime import datetime

# 加载数据路径配置
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "data_paths.json"
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    DATA_CONFIG = json.load(f)


class DataService:
    """
    统一数据服务
    负责：QMT数据访问、价格数据获取、环境自检
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._data_root = DATA_CONFIG['qmt_data_root']
        self._env_check_passed = False
        self._env_info = {}
        
        # 🔥 Phase 1: 加载股票流通市值缓存
        self.equity_cache = {}
        self._equity_cache_loaded = False
        self.load_equity_cache()
    
    def env_check(self) -> Tuple[bool, Dict]:
        """
        环境自检（每次研究脚本入口必须调用）
        
        Returns:
            (是否通过, 环境信息字典)
        """
        try:
            from xtquant import xtdata
            xtdata.connect()
            
            info = {
                'xtdata_connected': True,
                'data_dir': xtdata.data_dir,
                'config_data_root': self._data_root,
                'timestamp': datetime.now().isoformat()
            }
            
            # 检查关键目录
            sz_path = Path(self._data_root) / 'sz' / '0'
            sh_path = Path(self._data_root) / 'sh' / '0'
            
            info['sz_exists'] = sz_path.exists()
            info['sh_exists'] = sh_path.exists()
            info['sz_stock_count'] = len(list(sz_path.iterdir())) if sz_path.exists() else 0
            info['sh_stock_count'] = len(list(sh_path.iterdir())) if sh_path.exists() else 0
            
            self._env_check_passed = True
            self._env_info = info
            
            return True, info
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def get_tick_file_path(self, stock_code: str) -> Tuple[str, str]:
        """
        获取tick文件完整路径（唯一正确路径）
        
        Args:
            stock_code: 原始代码如"002792"或完整代码"002792.SZ"
            
        Returns:
            (完整文件路径, 市场标识'sz'/'sh')
        """
        pure_code = stock_code.split('.')[0]
        
        # 判断市场
        sz_prefixes = DATA_CONFIG['market_structure']['sz']['code_prefix']
        sh_prefixes = DATA_CONFIG['market_structure']['sh']['code_prefix']
        
        market = None
        for prefix in sz_prefixes:
            if pure_code.startswith(prefix):
                market = 'sz'
                break
        
        if not market:
            for prefix in sh_prefixes:
                if pure_code.startswith(prefix):
                    market = 'sh'
                    break
        
        if not market:
            market = 'sz'  # 默认深圳
        
        # 构建路径：datadir/sz/0/002792（无扩展名）
        full_path = Path(self._data_root) / market / '0' / pure_code
        
        return str(full_path), market
    
    def verify_tick_exists(self, stock_code: str) -> Tuple[bool, int]:
        """
        验证tick数据是否存在并返回大致条数
        
        Returns:
            (是否存在, 预估条数)
        """
        file_path, _ = self.get_tick_file_path(stock_code)
        exists = Path(file_path).exists()
        
        # 粗略估计条数（通过文件大小）
        estimated_ticks = 0
        if exists:
            file_size = Path(file_path).stat().st_size
            estimated_ticks = file_size // 100  # 粗略估计每条100字节
        
        return exists, estimated_ticks
    
    def get_daily_data(self, stock_code: str, date_str: str) -> Optional[pd.DataFrame]:
        """
        获取日线数据（用于昨收、开高低收）
        
        Args:
            stock_code: 股票代码
            date_str: 日期'2026-01-26'
            
        Returns:
            DataFrame或None
        """
        try:
            from xtquant import xtdata
            
            formatted_code = self._format_code(stock_code)
            
            # 下载历史数据
            xtdata.download_history_data(
                stock_code=formatted_code,
                period='1d',
                start_time=date_str.replace('-', ''),
                end_time=date_str.replace('-', '')
            )
            
            # 获取数据
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'preClose'],
                stock_list=[formatted_code],
                period='1d',
                start_time=date_str.replace('-', ''),
                end_time=date_str.replace('-', '')
            )
            
            if formatted_code in data and data[formatted_code] is not None:
                return data[formatted_code]
            return None
            
        except Exception as e:
            print(f"获取日线数据失败 {stock_code} {date_str}: {e}")
            return None
    
    def get_pre_close(self, stock_code: str, date_str: str) -> float:
        """
        获取昨收价（唯一正确来源）
        
        Returns:
            昨收价，失败返回0
        """
        df = self.get_daily_data(stock_code, date_str)
        if df is not None and not df.empty:
            if 'preClose' in df.columns:
                return float(df['preClose'].iloc[0])
            elif 'close' in df.columns:
                # 如果是第一天，用当日开盘价作为近似
                return float(df['open'].iloc[0])
        return 0.0
    
    def _format_code(self, raw_code: str) -> str:
        """格式化为完整代码"""
        if '.' in raw_code:
            return raw_code
        
        sz_prefixes = DATA_CONFIG['market_structure']['sz']['code_prefix']
        for prefix in sz_prefixes:
            if raw_code.startswith(prefix):
                return f"{raw_code}.SZ"
        return f"{raw_code}.SH"
    
    def get_env_info(self) -> Dict:
        """获取环境信息（用于日志记录）"""
        return self._env_info.copy()
    
    def load_equity_cache(self) -> bool:
        """
        加载股票流通市值缓存（equity_info_tushare.json）
        
        Returns:
            是否加载成功
        """
        try:
            equity_path = Path(__file__).resolve().parent.parent.parent / "data" / "equity_info" / "equity_info_tushare.json"
            
            if not equity_path.exists():
                print(f"⚠️ 未找到流通市值文件: {equity_path}")
                return False
            
            with open(equity_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析嵌套结构: {date: {code: {float_mv, total_mv, ...}}}
            for date_str, stocks in data.get('data', {}).items():
                self.equity_cache[date_str] = {}
                for code, info in stocks.items():
                    # float_mv单位是万元，转换为亿元
                    float_mv = info.get('float_mv', 0)
                    self.equity_cache[date_str][code] = float_mv / 1e4  # 转为亿元
            
            self._equity_cache_loaded = True
            print(f"✅ 流通市值缓存加载完成: {len(self.equity_cache)} 个交易日")
            return True
            
        except Exception as e:
            print(f"❌ 加载流通市值缓存失败: {e}")
            return False
    
    def get_circ_mv(self, stock_code: str, trade_date: str = None) -> float:
        """
        获取股票流通市值（亿元）
        
        Args:
            stock_code: 股票代码（如'300017.SZ'或'300017'）
            trade_date: 交易日期（如'2026-01-26'），None则使用最新
            
        Returns:
            流通市值（亿元），未找到返回50.0（默认值）
        """
        if not self._equity_cache_loaded or not self.equity_cache:
            return 50.0  # 默认50亿
        
        # 格式化代码
        pure_code = stock_code.split('.')[0]
        
        # 确定市场后缀
        if stock_code.endswith('.SH') or stock_code.endswith('.SZ') or stock_code.endswith('.BJ'):
            formatted_code = stock_code
        else:
            # 根据代码前缀判断
            if pure_code.startswith(('60', '68', '69')):
                formatted_code = f"{pure_code}.SH"
            elif pure_code.startswith('8'):
                formatted_code = f"{pure_code}.BJ"
            else:
                formatted_code = f"{pure_code}.SZ"
        
        # 🔥 修复：如果没有精确日期匹配，使用最近的有效日期
        if trade_date:
            date_key = trade_date.replace('-', '')
            if date_key not in self.equity_cache:
                # 查找最近的日期（模糊匹配）
                sorted_dates = sorted(self.equity_cache.keys())
                date_key = sorted_dates[-1]  # 使用最新日期
        else:
            # 使用最新日期
            date_key = max(self.equity_cache.keys()) if self.equity_cache else None
        
        if not date_key:
            return 50.0
        
        circ_mv = self.equity_cache[date_key].get(formatted_code, 0)
        
        # 如果当前日期没有，尝试所有日期
        if circ_mv <= 0:
            for d in sorted(self.equity_cache.keys(), reverse=True):
                circ_mv = self.equity_cache[d].get(formatted_code, 0)
                if circ_mv > 0:
                    break
        
        return circ_mv if circ_mv > 0 else 50.0


# 全局单例
data_service = DataService()


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("数据服务测试")
    print("="*60)
    
    # 环境自检
    print("\n1. 环境自检")
    passed, info = data_service.env_check()
    print(f"  检查通过: {passed}")
    print(f"  数据目录: {info.get('data_dir', 'N/A')}")
    print(f"  深圳股票数: {info.get('sz_stock_count', 0)}")
    print(f"  上海股票数: {info.get('sh_stock_count', 0)}")
    
    # 路径测试
    print("\n2. 路径测试")
    test_codes = ['002792', '603778', '300017']
    for code in test_codes:
        path, market = data_service.get_tick_file_path(code)
        exists, estimated = data_service.verify_tick_exists(code)
        print(f"  {code} ({market}): 存在={exists}, 预估条数={estimated}")
    
    # 昨收价测试
    print("\n3. 昨收价测试")
    pre_close = data_service.get_pre_close('300017', '2026-01-26')
    print(f"  网宿科技 2026-01-26 昨收: {pre_close}")
    
    print("\n" + "="*60)
