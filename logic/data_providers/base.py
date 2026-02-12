from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class CapitalFlowSignal:
    code: str
    timestamp: float
    main_net_inflow: float
    super_large_inflow: float
    large_inflow: float
    confidence: float
    source: str

    @property
    def flow_direction(self) -> str:
        return "INFLOW" if self.main_net_inflow > 0 else "OUTFLOW"

class ICapitalFlowProvider(ABC):
    @abstractmethod
    def get_realtime_flow(self, code: str) -> Optional[CapitalFlowSignal]:
        """获取实时资金流"""
        pass

    @abstractmethod
    def get_data_freshness(self, code: str) -> int:
        """获取数据新鲜度"""
        pass

    @abstractmethod
    def get_full_tick(self, code_list: List[str]) -> Dict:
        """获取全推Tick数据 (Phase 2新增)"""
        pass

    @abstractmethod
    def get_kline_data(self, code_list: List[str], period: str = '1d',
                       start_time: str = '', end_time: str = '',
                       count: int = -1) -> Dict:
        """获取K线数据 (Phase 2新增)"""
        pass

    @abstractmethod
    def get_stock_list_in_sector(self, sector_name: str) -> List[str]:
        """获取板块成分股 (Phase 2新增)"""
        pass

    @abstractmethod
    def get_historical_flow(self, code: str, days: int = 30) -> Optional[Dict]:
        """获取历史资金流"""
        pass

    @abstractmethod
    def get_market_data(self, field_list: List[str], stock_list: List[str],
                       period: str = '1d', start_time: str = '', end_time: str = '',
                       dividend_type: str = 'none', fill_data: bool = False) -> Dict:
        """获取市场数据（财务数据等）"""
        pass

    @abstractmethod
    def get_instrument_detail(self, code: str) -> Dict:
        """获取合约详情"""
        pass

    @abstractmethod
    def download_history_data(self, code: str, period: str = '1m',
                              count: int = -1, incrementally: bool = False) -> Dict:
        """下载历史数据"""
        pass