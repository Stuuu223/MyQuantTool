import time
from typing import Optional, List, Dict
from xtquant import xtdata
from logic.logger import logger
from logic.code_converter import CodeConverter
from .base import ICapitalFlowProvider, CapitalFlowSignal

class Level1InferenceProvider(ICapitalFlowProvider):
    def __init__(self):
        self.converter = CodeConverter()

    def get_realtime_flow(self, code: str) -> Optional[CapitalFlowSignal]:
        try:
            qmt_code = self.converter.convert_to_qmt_format(code)
            tick = xtdata.get_full_tick([qmt_code])
            if not tick or qmt_code not in tick:
                return None
            data = tick[qmt_code]
            # 这里简化逻辑，实际应复用原 fund_flow_analyzer 的推算
            return CapitalFlowSignal(
                code=code,
                timestamp=time.time(),
                main_net_inflow=0.0,
                super_large_inflow=0.0,
                large_inflow=0.0,
                confidence=0.5,
                source='level1'
            )
        except Exception as e:
            logger.error(f"[Level1] Fetch error for {code}: {str(e)}")
            return None

    def get_data_freshness(self, code: str) -> int:
        return 1

    def get_full_tick(self, code_list: List[str]) -> Dict:
        try:
            qmt_codes = [self.converter.convert_to_qmt_format(c) for c in code_list]
            return xtdata.get_full_tick(qmt_codes)
        except Exception as e:
            logger.error(f"[Level1] get_full_tick error: {e}")
            return {}

    def get_kline_data(self, code_list: List[str], period: str = '1d',
                       start_time: str = '', end_time: str = '',
                       count: int = -1) -> Dict:
        try:
            qmt_codes = [self.converter.convert_to_qmt_format(c) for c in code_list]
            return xtdata.get_market_data_ex(
                field_list=[],
                stock_list=qmt_codes,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count
            )
        except Exception as e:
            logger.error(f"[Level1] get_kline_data error: {e}")
            return {}

    def get_stock_list_in_sector(self, sector_name: str) -> List[str]:
        try:
            return xtdata.get_stock_list_in_sector(sector_name)
        except Exception as e:
            logger.error(f"[Level1] get_stock_list_in_sector error: {e}")
            return []

    def get_historical_flow(self, code: str, days: int = 30) -> Optional[Dict]:
        return {}

    def get_market_data(self, field_list: List[str], stock_list: List[str],
                       period: str = '1d', start_time: str = '', end_time: str = '',
                       dividend_type: str = 'none', fill_data: bool = False) -> Dict:
        try:
            qmt_codes = [self.converter.convert_to_qmt_format(c) for c in stock_list]
            return xtdata.get_market_data(
                field_list=field_list,
                stock_list=qmt_codes,
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,
                fill_data=fill_data
            )
        except Exception as e:
            logger.error(f"[Level1] get_market_data error: {e}")
            return {}

    def get_instrument_detail(self, code: str) -> Dict:
        try:
            qmt_code = self.converter.convert_to_qmt_format(code)
            return xtdata.get_instrument_detail(qmt_code)
        except Exception as e:
            logger.error(f"[Level1] get_instrument_detail error: {e}")
            return {}

    def download_history_data(self, code: str, period: str = '1m',
                              count: int = -1, incrementally: bool = False) -> Dict:
        try:
            qmt_code = self.converter.convert_to_qmt_format(code)
            return xtdata.download_history_data(qmt_code, period=period, count=count, incrementally=incrementally)
        except Exception as e:
            logger.error(f"[Level1] download_history_data error: {e}")
            return {}