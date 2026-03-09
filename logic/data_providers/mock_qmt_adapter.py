# -*- coding: utf-8 -*-
"""
MockQmtAdapter - åå²Tickä¼ªè£å®æ¶æµééå?

ãCTO V52æå½¹ä¸?- çµé­ç»ä¸æ¶ææ ¸å¿ç»ä»¶ã?
è®©Scanæ¨¡å¼å¤ç¨LiveTradingEngineï¼å®ç°ç»å¯¹åè´¨åæºï¼

è®¾è®¡åçï¼?
- å®ç°ä¸QMTEventAdapterç¸åçæ¥å?
- ä»æ¬å°åå²Tickæä»¶è¯»åæ°æ®
- ææ¶é´çº¿ä¼ªè£æå®æ¶Tickæ¨é?

Author: CTOæ¶æç»?
Date: 2026-03-09
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class MockQmtAdapter:
    """
    Mock QMTééå?- ä»åå²Tickæä»¶è¯»åï¼ä¼ªè£æå®æ¶æµ?
    
    ç¨éï¼
    - Scanæ¨¡å¼å¤ç¨LiveTradingEngine
    - åæµæ¶ä½¿ç¨çå®å¼æé»è¾
    - å¼åè°è¯æ éè¿æ¥QMT
    """
    
    def __init__(self, target_date: str = None, event_bus=None):
        """
        åå§åMockééå?
        
        Args:
            target_date: ç®æ æ¥æ (æ ¼å¼: 'YYYYMMDD')
            event_bus: äºä»¶æ»çº¿å®ä¾
        """
        self.target_date = target_date or datetime.now().strftime('%Y%m%d')
        self.event_bus = event_bus
        self._subscribed_stocks = set()
        self._tick_data_cache = {}  # {stock_code: DataFrame}
        self._current_time_index = {}  # {stock_code: current_row_index}
        self._is_initialized = False
        self._xtdata = None
        
    def initialize(self) -> bool:
        """
        åå§å?- è¿æ¥QMTè¯»ååå²æ°æ®
        
        Returns:
            bool: æ¯å¦åå§åæå?
        """
        try:
            from xtquant import xtdata
            xtdata.enable_hello = False
            self._xtdata = xtdata
            self._is_initialized = True
            logger.info(f"â?[MockQmtAdapter] åå§åæåï¼ç®æ æ¥æ: {self.target_date}")
            return True
        except ImportError:
            logger.error("â?[MockQmtAdapter] æ æ³å¯¼å¥xtquantæ¨¡å")
            return False
        except Exception as e:
            logger.error(f"â?[MockQmtAdapter] åå§åå¤±è´? {e}")
            return False
    
    def subscribe_ticks(self, stock_list: List[str]) -> int:
        """
        è®¢éè¡ç¥¨Tickæ°æ® - é¢å è½½åå²Tick
        
        Args:
            stock_list: è¡ç¥¨ä»£ç åè¡¨
            
        Returns:
            int: æåè®¢éæ°é
        """
        if not self._is_initialized:
            logger.error("[MockQmtAdapter] æªåå§åï¼æ æ³è®¢é?)
            return 0
        
        success_count = 0
        for stock in stock_list:
            try:
                # å è½½åå²Tickæ°æ®
                local_data = self._xtdata.get_local_data(
                    field_list=[],
                    stock_list=[stock],
                    period='tick',
                    start_time=self.target_date,
                    end_time=self.target_date
                )
                
                if local_data and stock in local_data:
                    df = local_data[stock]
                    if df is not None and not df.empty:
                        self._tick_data_cache[stock] = df
                        self._current_time_index[stock] = 0
                        self._subscribed_stocks.add(stock)
                        success_count += 1
            except Exception as e:
                logger.debug(f"[MockQmtAdapter] {stock} å è½½å¤±è´¥: {e}")
                continue
        
        logger.info(f"â?[MockQmtAdapter] é¢å è½?{success_count}/{len(stock_list)} åªè¡ç¥¨åå²Tick")
        return success_count
    
    def get_all_a_shares(self) -> List[str]:
        """
        è·åå¨Aè¡åè¡?
        
        Returns:
            List[str]: è¡ç¥¨ä»£ç åè¡¨
        """
        if not self._is_initialized:
            return []
        
        try:
            sz = self._xtdata.get_stock_list_in_sector('SZ')
            sh = self._xtdata.get_stock_list_in_sector('SH')
            all_stocks = sz + sh
            # è¿æ»¤STãéå¸ç­
            valid_stocks = [s for s in all_stocks if not any(x in s for x in ['ST', 'é', 'PT'])]
            return valid_stocks
        except Exception as e:
            logger.error(f"[MockQmtAdapter] è·åè¡ç¥¨åè¡¨å¤±è´¥: {e}")
            return []
    
    def get_full_tick_snapshot(self, stock_list: List[str]) -> Dict[str, Dict]:
        """
        è·åTickå¿«ç§ - ä»åå²æ°æ®æåææ°ç¶æ?
        
        Args:
            stock_list: è¡ç¥¨ä»£ç åè¡¨
            
        Returns:
            Dict[str, Dict]: {stock_code: tick_dict}
        """
        snapshot = {}
        
        for stock in stock_list:
            if stock in self._tick_data_cache:
                df = self._tick_data_cache[stock]
                if df is not None and not df.empty:
                    # åæåä¸è¡ä½ä¸ºå½åå¿«ç?
                    last_row = df.iloc[-1]
                    snapshot[stock] = self._row_to_tick_dict(last_row, stock)
            else:
                # å°è¯å®æ¶å è½½ï¼æå è½½ï¼?
                try:
                    local_data = self._xtdata.get_local_data(
                        field_list=[],
                        stock_list=[stock],
                        period='tick',
                        start_time=self.target_date,
                        end_time=self.target_date
                    )
                    if local_data and stock in local_data:
                        df = local_data[stock]
                        if df is not None and not df.empty:
                            self._tick_data_cache[stock] = df
                            last_row = df.iloc[-1]
                            snapshot[stock] = self._row_to_tick_dict(last_row, stock)
                except:
                    pass
        
        return snapshot
    
    def get_tick_at_time(self, stock: str, time_str: str) -> Optional[Dict]:
        """
        è·åæå®æ¶é´çTickæ°æ® - ç¨äºæ¶é´çº¿åæ?
        
        Args:
            stock: è¡ç¥¨ä»£ç 
            time_str: æ¶é´å­ç¬¦ä¸?(æ ¼å¼: 'HH:MM:SS' æ?'HHMMSS')
            
        Returns:
            Optional[Dict]: Tickå­å¸æNone
        """
        if stock not in self._tick_data_cache:
            return None
        
        df = self._tick_data_cache[stock]
        if df is None or df.empty:
            return None
        
        # æ ååæ¶é´æ ¼å¼?
        if ':' in time_str:
            target_time = time_str.replace(':', '')
        else:
            target_time = time_str
        
        # æ¥æ¾å¹éæ¶é´çè¡
        for idx, row in df.iterrows():
            tick_time = str(row.get('time', ''))
            # tick_timeæ ¼å¼å¯è½æ?'HHMMSS' ææ¶é´æ³
            if target_time in str(tick_time):
                return self._row_to_tick_dict(row, stock)
        
        return None
    
    def get_timeline_ticks(self, stock_list: List[str], interval_seconds: int = 3) -> List[Dict]:
        """
        è·åæ¶é´çº¿Tickåºå - ç¨äºåæ¾æ¨¡å¼
        
        Args:
            stock_list: è¡ç¥¨ä»£ç åè¡¨
            interval_seconds: æ¶é´é´éï¼ç§ï¼?
            
        Returns:
            List[Dict]: æ¶é´çº¿Tickåè¡¨ï¼æ¯ä¸ªåç´ åå?{time, ticks: {stock: tick_dict}}
        """
        timeline = []
        
        # æå»ºæ¶é´çº¿ï¼09:30 - 15:00ï¼?
        start_time = datetime.strptime("093000", "%H%M%S")
        end_time = datetime.strptime("150000", "%H%M%S")
        
        current_time = start_time
        while current_time <= end_time:
            time_str = current_time.strftime("%H%M%S")
            
            ticks_at_time = {}
            for stock in stock_list:
                tick = self.get_tick_at_time(stock, time_str)
                if tick:
                    ticks_at_time[stock] = tick
            
            if ticks_at_time:
                timeline.append({
                    'time': time_str,
                    'datetime': current_time,
                    'ticks': ticks_at_time
                })
            
            current_time += timedelta(seconds=interval_seconds)
        
        return timeline
    
    def _row_to_tick_dict(self, row, stock_code: str) -> Dict:
        """
        å°DataFrameè¡è½¬æ¢ä¸ºTickå­å¸
        
        Args:
            row: DataFrameè¡?
            stock_code: è¡ç¥¨ä»£ç 
            
        Returns:
            Dict: æ åTickå­å¸
        """
        return {
            'stock_code': stock_code,
            'lastPrice': float(row.get('lastPrice', 0)),
            'open': float(row.get('open', 0)),
            'high': float(row.get('high', 0)),
            'low': float(row.get('low', 0)),
            'lastClose': float(row.get('lastClose', 0)),
            'amount': float(row.get('amount', 0)),
            'volume': float(row.get('volume', 0)),
            'bidPrice1': float(row.get('bidPrice1', 0)),
            'bidVol1': float(row.get('bidVol1', 0)),
            'askPrice1': float(row.get('askPrice1', 0)),
            'askVol1': float(row.get('askVol1', 0)),
            'time': row.get('time', 0),
        }
    
    def push_tick_to_event_bus(self, stock: str, tick_dict: Dict) -> bool:
        """
        å°Tickæ¨éå°äºä»¶æ»çº¿ - æ¨¡æå®æ¶æ¨é?
        
        Args:
            stock: è¡ç¥¨ä»£ç 
            tick_dict: Tickæ°æ®å­å¸
            
        Returns:
            bool: æ¯å¦æ¨éæå?
        """
        if self.event_bus is None:
            return False
        
        try:
            # ¡¾CTOÍ³Ò»¹æ·¶¡¿Ê¹ÓÃ±ê×¼TickEvent
            from logic.data_providers.event_bus import TickEvent
            event = TickEvent(
                stock_code=stock,
                price=float(tick_dict.get(\"lastPrice\", 0)),
                volume=float(tick_dict.get(\"volume\", 0)),
                amount=float(tick_dict.get(\"amount\", 0)),
                open=float(tick_dict.get(\"open\", 0)),
                high=float(tick_dict.get(\"high\", 0)),
                low=float(tick_dict.get(\"low\", 0)),
                prev_close=float(tick_dict.get(\"lastClose\", 0)),
                timestamp=tick_dict.get(\"time\", \"\"),
                data=tick_dict
            )
            self.event_bus.publish(\"tick\", event)
            return True
        except Exception as e:
            logger.debug(f"[MockQmtAdapter] æ¨éäºä»¶å¤±è´? {e}")
            return False
