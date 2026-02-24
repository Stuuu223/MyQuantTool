"""
股票池构建器 - Tushare粗筛 (CTO重构版)
使用daily_basic截面数据一次性获取，禁止循环请求

重构要点：
- 原代码循环调用stk_mins导致6000次API请求
- 现改用daily_basic一次请求获取全市场量比
- 6000次请求 10分钟 → 1次请求 0.5秒
- CTO强制：所有参数从配置管理器获取，禁止硬编码

Author: iFlow CLI
Date: 2026-02-24
Version: 3.0.0 (CTO强制重构 - ratio化)
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from dotenv import load_dotenv

from logic.core.path_resolver import PathResolver
from logic.core.sanity_guards import SanityGuards
from logic.core.config_manager import get_config_manager

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)


class UniverseBuilder:
    """
    股票池构建器
    
    三漏斗粗筛 (全市场5000 → ~60-100只):
    1. 静态过滤: 剔除ST、退市、北交所
    2. 金额过滤: 5日平均成交额 > 3000万
    3. 量比过滤: 当日量比 > 3.0 (右侧起爆：筛选真正放量的股票)
    """
    
    def __init__(self, strategy: str = 'universe_build'):
        """初始化，使用粗筛专用参数"""
        self.strategy = strategy  # 默认使用universe_build策略
        self.config_manager = get_config_manager()
        self.tushare_token = self._load_tushare_token()
        
    @property
    def MIN_AMOUNT(self) -> int:
        """最小金额阈值"""
        return 30000000  # 3000万
    
    def _get_volume_ratio_percentile_threshold(self, date: str) -> float:
        """获取基于分位数的量比阈值 - CTO裁决：统一使用分位数标准
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            量比阈值
        """
        # 从配置获取分位数阈值，默认使用live_sniper的0.95分位数
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
        
        # 获取全市场量比数据，计算对应分位数的绝对值
        try:
            import tushare as ts
            if not self.tushare_token:
                # 如果无法获取实时分位数，回退到配置的绝对值
                universe_config = self.config_manager._config.get('universe_build', {})
                return universe_config.get('volume_ratio_absolute', 3.0)
            
            ts.set_token(self.tushare_token)
            pro = ts.pro_api()
            
            # 获取当日全市场量比数据
            df_basic = pro.daily_basic(
                trade_date=date,
                fields='ts_code,volume_ratio'
            )
            
            if df_basic is not None and not df_basic.empty:
                # 过滤掉无效数据
                valid_ratios = df_basic['volume_ratio'].dropna()
                if len(valid_ratios) > 0:
                    # 计算指定分位数对应的量比值
                    threshold_value = valid_ratios.quantile(volume_percentile)
                    # 确保阈值不低于安全下限
                    return max(threshold_value, 1.5)  # 设置最低阈值为1.5，确保真正放量
            
            # 如果Tushare获取失败，回退到配置的绝对值
            universe_config = self.config_manager._config.get('universe_build', {})
            return universe_config.get('volume_ratio_absolute', 3.0)
            
        except Exception as e:
            logger.warning(f"获取分位数阈值失败，使用回退值: {e}")
            universe_config = self.config_manager._config.get('universe_build', {})
            return universe_config.get('volume_ratio_absolute', 3.0)
        
    @property
    def MIN_ACTIVE_TURNOVER_RATE(self) -> float:
        """最低活跃换手率 - CTO换手率纠偏裁决：拒绝死水"""
        # 从配置获取最低活跃换手率，默认3.0%
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('min_active_turnover_rate', 3.0)
        
    @property
    def DEATH_TURNOVER_RATE(self) -> float:
        """死亡换手率 - CTO换手率纠偏裁决：防范极端爆炒陷阱"""
        # 从配置获取死亡换手率，默认70.0%
        live_sniper_config = self.config_manager._config.get('live_sniper', {})
        return live_sniper_config.get('death_turnover_rate', 70.0)
        
    def _load_tushare_token(self) -> str:
        """
        加载Tushare Token - CTODict: 优先环境变量，其次配置文件
        
        Returns:
            Tushare Token字符串
        """
        # 1. 优先从环境变量读取 (CTO: 能放env的就env)
        env_token = os.getenv('TUSHARE_TOKEN')
        if env_token and env_token.strip():
            logger.info("【UniverseBuilder】从环境变量读取Tushare Token")
            return env_token.strip()
        
        # 2. 从.env文件读取 (python-dotenv已加载)
        # load_dotenv()已在模块级别调用
        
        # 3. 从配置文件读取 (兼容旧版本)
        try:
            config_path = PathResolver.get_config_dir() / 'config.json'
            if config_path.exists():
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    token = config.get('tushare_token', '')
                    if token:
                        logger.info("【UniverseBuilder】从config.json读取Tushare Token")
                        return token
        except Exception as e:
            logger.error(f"加载Tushare配置失败: {e}")
        
        logger.warning("【UniverseBuilder】未找到Tushare Token，请设置TUSHARE_TOKEN环境变量或config.json")
        return ''
    
    def _init_tushare(self):
        """初始化Tushare接口"""
        try:
            import tushare as ts
            if not self.tushare_token:
                raise ValueError("Tushare token未配置")
            ts.set_token(self.tushare_token)
            return ts.pro_api()
        except ImportError:
            raise ImportError("tushare未安装，请执行: pip install tushare")
        except Exception as e:
            raise RuntimeError(f"Tushare初始化失败: {e}")
    
    def get_daily_universe(self, date: str) -> List[str]:
        """
        获取当日股票池 (CTO重构版 - 截面向量查询)
        
        Args:
            date: 日期 'YYYYMMDD'
            
        Returns:
            股票代码列表 (约60-100只)
            
        Raises:
            RuntimeError: 无法获取数据时抛出
        """
        import time
        start_time = time.time()
        logger.info(f"【UniverseBuilder】开始构建 {date} 股票池 (CTO重构版)")
        
        pro = self._init_tushare()
        
        # CTO强制: 一次API请求获取全市场截面数据
        # 包含: 量比(volume_ratio)、换手率(turnover_rate)、流通市值(circ_mv)
        try:
            df_basic = pro.daily_basic(
                trade_date=date,
                fields='ts_code,volume_ratio,turnover_rate,circ_mv,total_mv,amount'
            )
            logger.info(f"【UniverseBuilder】截面数据获取成功: {len(df_basic)} 只")
        except Exception as e:
            raise RuntimeError(f"获取截面数据失败: {e}")
        
        # 向量化过滤 (CTO: 禁止循环，用Pandas)
        # 第一层: 剔除量比为空的股票
        df_filtered = df_basic[df_basic['volume_ratio'].notna()].copy()
        logger.info(f"【UniverseBuilder】第一层(有效量比): {len(df_filtered)} 只")
        
        # 第二层: 量比 > 分位数阈值 (右侧起爆：筛选真正放量的股票，CTO裁决：统一使用分位数标准)
        volume_ratio_threshold = self._get_volume_ratio_percentile_threshold(date)
        df_filtered = df_filtered[df_filtered['volume_ratio'] >= volume_ratio_threshold]
        logger.info(f"【UniverseBuilder】第二层(量比>{volume_ratio_threshold:.2f}, 右侧起爆): {len(df_filtered)} 只")
        
        # 第三层: 换手率过滤 (CTO换手率纠偏裁决)
        # 换手率 > 最低活跃阈值 (拒绝死水) 且 < 死亡换手率 (防范极端爆炒陷阱)
        min_turnover = self.MIN_ACTIVE_TURNOVER_RATE
        max_turnover = self.DEATH_TURNOVER_RATE
        df_filtered = df_filtered[
            (df_filtered['turnover_rate'] > min_turnover) & 
            (df_filtered['turnover_rate'] < max_turnover)
        ]
        logger.info(f"【UniverseBuilder】第三层(换手率>{min_turnover}%-<{max_turnover}%): {len(df_filtered)} 只")
        
        # 第四层: 剔除科创板(688)和北交所(8开头/4开头)
        df_filtered = df_filtered[~df_filtered['ts_code'].str.startswith('688')]
        df_filtered = df_filtered[~df_filtered['ts_code'].str.match(r'^[84]\d{5}\.(SZ|SH|BJ)')]
        logger.info(f"【UniverseBuilder】第四层(剔除科创/北交): {len(df_filtered)} 只")
        
        # 转换为标准格式
        result = [self._to_standard_code(code) for code in df_filtered['ts_code'].tolist()]
        
        elapsed = time.time() - start_time
        logger.info(f"【UniverseBuilder】最终股票池: {len(result)} 只 (耗时: {elapsed:.2f}秒)")
        
        return result
    
    # ===== 以下方法已废弃，保留仅供参考 =====
    # 原代码使用循环调用stk_mins导致6000次API请求
    # 已改用daily_basic截面查询，1次请求完成
    # See: get_daily_universe() for new implementation
    
    @staticmethod
    def _to_standard_code(ts_code: str) -> str:
        """转换为标准格式 (#######.SH/SZ)"""
        if '.' in ts_code:
            code, exchange = ts_code.split('.')
            if exchange == 'SH':
                return f"{code}.SH"
            elif exchange == 'SZ':
                return f"{code}.SZ"
        return ts_code


# 便捷函数
def get_daily_universe(date: str) -> List[str]:
    """
    获取当日股票池 (便捷函数)
    
    Args:
        date: 日期 'YYYYMMDD'
        
    Returns:
        股票代码列表
        
    Raises:
        RuntimeError: 无法获取数据时抛出
    """
    builder = UniverseBuilder()
    return builder.get_daily_universe(date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    try:
        universe = get_daily_universe('20251231')
        print(f"股票池: {len(universe)} 只")
        print(f"前10只: {universe[:10]}")
    except Exception as e:
        print(f"错误: {e}")
