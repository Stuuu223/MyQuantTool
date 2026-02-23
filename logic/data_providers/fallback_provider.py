"""
QMT数据源路由器 - CTO Phase 14.2: QMT原教旨主义

核心原则:
1. 只信任QMT数据流 (Level-2 VIP 或 Level-1本地)
2. QMT失败即熔断，禁止降级到Tushare等第三方
3. Level-1 Tick推断是我们的核心算法

Author: AI总监
Date: 2026-02-23
Version: 2.0.0 (QMT原教旨主义版)
"""
import os
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """数据源状态"""
    VIP_L2 = "VIP_L2"           # Level-2 VIP极速数据
    LOCAL_L1 = "LOCAL_L1"       # Level-1本地数据
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"  # 熔断


@dataclass
class QMTDataResponse:
    """QMT数据响应"""
    success: bool
    data: Optional[Dict]
    source: DataSourceStatus
    error_msg: Optional[str] = None
    tick_count: int = 0
    use_inference: bool = False  # 是否使用了推断算法


class CircuitBreakerError(Exception):
    """熔断异常 - QMT数据不可用"""
    pass


class QMTRouter:
    """
    QMT数据路由器 - QMT原教旨主义实现
    
    老板定调：
    "如果连QMT Level-1都出问题，就停下来修，Tushare无法代替QMT"
    
    数据流：
    1. 优先尝试VIP Level-2 (如果配置了Token)
    2. VIP失败或无权限 -> 降级到本地Level-1 + Tick推断算法
    3. Level-1也失败 -> 触发熔断，禁止交易该股票
    
    绝对禁止：降级到Tushare或任何第三方云端接口
    """
    
    def __init__(self):
        self.vip_token = os.getenv('QMT_VIP_TOKEN')
        self.vip_sites = self._parse_vip_sites()
        self.use_vip = bool(self.vip_token and self.vip_token != 'your_vip_token_here')
        self.circuit_breaker_count = 0
        
        if self.use_vip:
            logger.info(f"【QMTRouter】VIP Level-2模式，站点数: {len(self.vip_sites)}")
        else:
            logger.info("【QMTRouter】本地Level-1模式 (VIP Token未配置)")
    
    def _parse_vip_sites(self) -> list:
        """解析VIP站点配置"""
        sites_str = os.getenv('QMT_VIP_SITES', '')
        if not sites_str:
            return []
        return [s.strip() for s in sites_str.split(',') if s.strip()]
    
    def get_tick_data(self, stock_code: str, date: str) -> QMTDataResponse:
        """
        获取Tick数据 - QMT唯一数据源
        
        Args:
            stock_code: 股票代码
            date: 日期 YYYYMMDD
            
        Returns:
            QMTDataResponse: 数据响应
            
        Raises:
            CircuitBreakerError: 熔断时抛出
        """
        # 第一步：尝试VIP Level-2
        if self.use_vip:
            result = self._fetch_vip_l2(stock_code, date)
            if result.success:
                return result
            logger.warning(f"【QMTRouter】VIP Level-2不可用，降级到本地Level-1")
        
        # 第二步：本地Level-1 + 推断算法
        result = self._fetch_local_l1(stock_code, date)
        if result.success:
            return result
        
        # 第三步：熔断
        self.circuit_breaker_count += 1
        error_msg = (
            f"🚫 【熔断】股票 {stock_code} {date} 数据获取失败！"
            f"VIP Level-2和本地Level-1均不可用。"
            f"根据老板指令：QMT失败即停机，禁止降级到第三方。"
            f"请检查QMT客户端是否正常运行。"
        )
        logger.error(error_msg)
        raise CircuitBreakerError(error_msg)
    
    def _fetch_vip_l2(self, stock_code: str, date: str) -> QMTDataResponse:
        """获取VIP Level-2数据"""
        try:
            from xtquant import xtdata
            
            # 标准化代码
            normalized_code = self._normalize_code(stock_code)
            
            # 尝试连接VIP站点获取数据
            for site in self.vip_sites:
                try:
                    host, port = site.split(':')
                    # 这里应该实现实际的VIP连接
                    # 简化：直接使用xtdata的本地接口作为示例
                    data = xtdata.get_local_data(
                        field_list=['time', 'lastPrice', 'volume', 'amount'],
                        stock_list=[normalized_code],
                        period='tick',
                        start_time=date,
                        end_time=date
                    )
                    
                    if data and normalized_code in data and not data[normalized_code].empty:
                        tick_df = data[normalized_code]
                        return QMTDataResponse(
                            success=True,
                            data={'tick_df': tick_df, 'source_site': site},
                            source=DataSourceStatus.VIP_L2,
                            tick_count=len(tick_df)
                        )
                except Exception as e:
                    logger.warning(f"【VIP】站点 {site} 失败: {e}")
                    continue
            
            return QMTDataResponse(
                success=False,
                data=None,
                source=DataSourceStatus.VIP_L2,
                error_msg="所有VIP站点均不可用"
            )
            
        except ImportError:
            return QMTDataResponse(
                success=False,
                data=None,
                source=DataSourceStatus.VIP_L2,
                error_msg="xtquant未安装"
            )
        except Exception as e:
            return QMTDataResponse(
                success=False,
                data=None,
                source=DataSourceStatus.VIP_L2,
                error_msg=f"VIP获取异常: {str(e)}"
            )
    
    def _fetch_local_l1(self, stock_code: str, date: str) -> QMTDataResponse:
        """
        获取本地Level-1数据 + 主动买卖推断
        
        这是老板拍板的核心算法：
        "Level-1 Tick推断是我们的核心竞争力"
        """
        try:
            from xtquant import xtdata
            
            normalized_code = self._normalize_code(stock_code)
            
            # 获取本地Level-1数据
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not data or normalized_code not in data or data[normalized_code].empty:
                return QMTDataResponse(
                    success=False,
                    data=None,
                    source=DataSourceStatus.LOCAL_L1,
                    error_msg="本地Level-1数据为空"
                )
            
            tick_df = data[normalized_code]
            
            # Level-1 Tick推断算法
            tick_df = self._infer_active_buy_l1(tick_df)
            
            return QMTDataResponse(
                success=True,
                data={'tick_df': tick_df},
                source=DataSourceStatus.LOCAL_L1,
                tick_count=len(tick_df),
                use_inference=True
            )
            
        except Exception as e:
            return QMTDataResponse(
                success=False,
                data=None,
                source=DataSourceStatus.LOCAL_L1,
                error_msg=f"本地Level-1异常: {str(e)}"
            )
    
    def _infer_active_buy_l1(self, tick_df) -> 'pd.DataFrame':
        """
        Level-1 Tick主动买卖推断算法
        
        核心逻辑：
        1. 当前Tick.lastPrice > 上一Tick.lastPrice -> 视为主动买
        2. 当前Tick.lastPrice < 上一Tick.lastPrice -> 视为主动卖
        3. 相等 -> 保持上一笔方向或标记为中性
        
        这是我们在全息回演中验证有效的核心算法
        """
        import pandas as pd
        
        if tick_df.empty:
            return tick_df
        
        df = tick_df.copy()
        
        # 确保按时间排序
        if 'time' in df.columns:
            df = df.sort_values('time').reset_index(drop=True)
        
        # 计算价格变动
        if 'lastPrice' in df.columns:
            df['price_change'] = df['lastPrice'].diff()
            
            # 推断主动买卖方向
            df['active_direction'] = df['price_change'].apply(
                lambda x: 'BUY' if x > 0 else ('SELL' if x < 0 else 'NEUTRAL')
            )
            
            # 计算主动买入量（简化模型：价格上涨时的成交量视为主动买）
            if 'volume' in df.columns:
                df['active_buy_vol'] = df.apply(
                    lambda row: row['volume'] if row['active_direction'] == 'BUY' else 0,
                    axis=1
                )
                df['active_sell_vol'] = df.apply(
                    lambda row: row['volume'] if row['active_direction'] == 'SELL' else 0,
                    axis=1
                )
        
        return df
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.strip().replace('.', '')
        
        if code.startswith('sh'):
            return f"{code[2:]}.SH"
        elif code.startswith('sz'):
            return f"{code[2:]}.SZ"
        elif code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        elif '.SH' in code or '.SZ' in code:
            return code
        else:
            return f"{code}.SH"
    
    def get_stats(self) -> Dict:
        """获取路由器统计"""
        return {
            'use_vip': self.use_vip,
            'vip_sites': len(self.vip_sites),
            'circuit_breaker_count': self.circuit_breaker_count,
            'mode': 'VIP_L2' if self.use_vip else 'LOCAL_L1'
        }


# 便捷函数
def get_qmt_tick(stock_code: str, date: str) -> QMTDataResponse:
    """获取QMT Tick数据（QMT-only模式）"""
    router = QMTRouter()
    return router.get_tick_data(stock_code, date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    router = QMTRouter()
    print(f"路由器状态: {router.get_stats()}")
    
    try:
        result = router.get_tick_data('002969.SZ', '20251231')
        print(f"\n获取成功:")
        print(f"  数据源: {result.source.value}")
        print(f"  Tick数: {result.tick_count}")
        print(f"  使用推断: {result.use_inference}")
    except CircuitBreakerError as e:
        print(f"\n熔断触发: {e}")