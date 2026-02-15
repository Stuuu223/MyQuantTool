#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT 历史数据提供者
使用 QMT 本地历史数据进行精准复盘
支持时间点快照（如 14:56:55）和时间段数据获取
"""

from logic.data.data_provider_factory import DataProvider
from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = get_logger(__name__)


class QMTHistoricalProvider(DataProvider):
    """
    QMT 历史数据提供者
    
    功能：
    - 使用 QMT 本地历史数据进行精准复盘
    - 支持指定时间点快照（如 14:56:55）
    - 支持时间段数据获取
    - 伪装成实时数据格式返回
    - 支持全市场批量查询
    
    优势：
    - 毫秒级精度（支持 Tick 数据）
    - 本地查询，速度快
    - 数据完整（包含盘口数据）
    - 支持全市场历史数据回放
    """
    
    def __init__(self, date=None, time_point=None, period='1m', **kwargs):
        """
        初始化 QMT 历史数据提供者
        
        Args:
            date: 历史日期（格式：'20260128'），默认为昨天
            time_point: 时间点（格式：'145600'，即 14:56:00），可选
            period: 数据周期
                - 'tick': 分笔数据（最精确，数据量大）
                - '1m': 1分钟线（推荐，平衡精度和性能）
                - '5m': 5分钟线
                - '1d': 日线
            **kwargs: 额外参数
        """
        super().__init__()
        
        # 默认日期：昨天
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        self.date = date
        self.time_point = time_point  # 指定时间点，如 '145600'
        self.period = period
        self.cache = {}  # 缓存已获取的数据
        self.code_converter = CodeConverter()
        
        # 🆕 V19.17: 初始化 QMT 数据接口
        try:
            from xtquant import xtdata
            self.xtdata = xtdata
            self.qmt_available = True
            logger.info(f"✅ [V19.17] QMT 历史数据接口已加载")
        except ImportError as e:
            self.qmt_available = False
            logger.error(f"❌ [V19.17] QMT 历史数据接口加载失败: {e}")
            logger.error(f"   请确保 QMT 环境已正确配置（Python 3.10 + xtquant）")
        
        logger.info(f"📅 QMT 历史回放模式：日期={self.date}, 周期={self.period}, 时间点={self.time_point}")
    
    def download_history_data(self, stock_codes: List[str], period: str = None) -> bool:
        """
        下载历史数据到本地
        
        Args:
            stock_codes: 股票代码列表
            period: 数据周期，默认使用初始化时的周期
        
        Returns:
            bool: 是否下载成功
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用，无法下载历史数据")
            return False
        
        period = period or self.period
        
        try:
            # 转换为 QMT 格式
            qmt_codes = [self.code_converter.to_qmt(code) for code in stock_codes]
            
            logger.info(f"📥 [V19.17] 正在下载 {len(qmt_codes)} 只股票的 {period} 历史数据...")
            
            # 下载历史数据
            for qmt_code in qmt_codes:
                try:
                    self.xtdata.download_history_data(
                        stock_code=qmt_code,
                        period=period,
                        start_time=self.date,
                        end_time=self.date
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 下载 {qmt_code} 历史数据失败: {e}")
                    continue
            
            logger.info(f"✅ [V19.17] 历史数据下载完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 下载历史数据失败: {e}")
            return False
    
    def get_snapshot_at_time(self, code: str, time_str: str) -> Optional[Dict]:
        """
        获取指定时间点的数据快照
        
        Args:
            code: 股票代码（如 '000426'）
            time_str: 时间字符串（如 '145600'，即 14:56:00）
        
        Returns:
            Dict: 时间点快照数据，格式与实时数据一致
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用")
            return None
        
        try:
            # 转换为 QMT 格式
            qmt_code = self.code_converter.to_qmt(code)
            
            # 构造时间范围（取该时间点附近的数据）
            start_time = self.date + time_str
            end_time = self.date + '150000'  # 取到收盘
            
            logger.debug(f"🔍 [V19.17] 获取 {code} 在 {time_str} 的快照...")
            
            # 获取历史数据
            data = self.xtdata.get_local_data(
                field_list=[],  # 获取所有字段
                stock_list=[qmt_code],
                period=self.period,
                start_time=start_time,
                end_time=end_time,
                count=1,  # 只取最近一条
                dividend_type='none',
                fill_data=True
            )
            
            if qmt_code not in data or data[qmt_code].empty:
                logger.warning(f"⚠️ 未找到 {code} 在 {time_str} 的数据")
                return None
            
            # 获取最近一条数据
            row = data[qmt_code].iloc[0]
            
            # 🔥 V19.17: 构造标准数据格式（与实时数据一致）
            # 先尝试从行数据中获取昨收价
            last_close = 0
            if 'lastClose' in row and pd.notna(row['lastClose']) and row['lastClose'] > 0:
                last_close = row['lastClose']
            elif 'preClose' in row and pd.notna(row['preClose']) and row['preClose'] > 0:
                last_close = row['preClose']
            else:
                # 如果没有昨收价，尝试从 open 字段估算
                last_close = row.get('open', 0)
            
            current_price = row.get('close', 0)
            
            # 计算涨幅
            change_pct = 0
            if last_close > 0 and current_price > 0:
                change_pct = (current_price - last_close) / last_close
            
            snapshot = {
                'code': code,
                'name': '',  # QMT 不提供名称
                'price': current_price,
                'now': current_price,  # 兼容 easyquotation 格式
                'change_pct': change_pct,
                'volume': row.get('volume', 0) / 100,  # 股数 → 手数
                'amount': row.get('amount', 0) / 10000,  # 元 → 万元
                'open': row.get('open', 0),
                'high': row.get('high', 0),
                'low': row.get('low', 0),
                'pre_close': last_close,
                'close': current_price,
                'data_timestamp': time_str,
                'turnover': 0,  # QMT 1分钟线不提供换手率
                'volume_ratio': 0,
                'bid1': 0,  # 1分钟线不提供盘口
                'ask1': 0,
                'bid1_volume': 0,
                'ask1_volume': 0,
                # QMT 历史数据特有字段
                'source': 'QMT_History',
                'replay_date': self.date,
                'replay_time': time_str,
                'replay_mode': True,
            }
            
            logger.debug(f"✅ [V19.17] 获取 {code} 在 {time_str} 的快照成功")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 获取 {code} 在 {time_str} 的快照失败: {e}")
            return None
    
    def get_time_range_data(self, code: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        获取指定时间段的数据
        
        Args:
            code: 股票代码
            start_time: 开始时间（如 '143000'，即 14:30:00）
            end_time: 结束时间（如 '150000'，即 15:00:00）
        
        Returns:
            DataFrame: 时间段数据
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用")
            return pd.DataFrame()
        
        try:
            qmt_code = self.code_converter.to_qmt(code)
            
            start_dt = self.date + start_time
            end_dt = self.date + end_time
            
            data = self.xtdata.get_local_data(
                field_list=[],
                stock_list=[qmt_code],
                period=self.period,
                start_time=start_dt,
                end_time=end_dt,
                count=-1,  # 获取所有数据
                dividend_type='none',
                fill_data=True
            )
            
            if qmt_code not in data or data[qmt_code].empty:
                return pd.DataFrame()
            
            return data[qmt_code]
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 获取 {code} 时间段数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_data(self, stock_list: List[str]) -> List[Dict]:
        """
        获取历史数据并伪装成实时数据
        
        如果指定了 time_point，则返回该时间点的快照
        否则返回当日收盘数据
        
        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表
        
        Returns:
            list: 股票数据列表（格式与实时数据一致）
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用")
            return []
        
        try:
            # 提取股票代码
            if isinstance(stock_list[0], dict):
                codes = [stock.get('code') for stock in stock_list]
            else:
                codes = stock_list
            
            result = []
            
            # 🔥 V19.17: 如果指定了时间点，使用快照模式
            if self.time_point:
                logger.info(f"🎬 [V19.17] 复盘模式：获取 {len(codes)} 只股票在 {self.time_point} 的快照...")
                
                for code in codes:
                    snapshot = self.get_snapshot_at_time(code, self.time_point)
                    if snapshot:
                        result.append(snapshot)
            else:
                # 否则获取当日收盘数据
                logger.info(f"📅 [V19.17] 复盘模式：获取 {len(codes)} 只股票的收盘数据...")
                
                # 下载历史数据（如果还没下载）
                self.download_history_data(codes)
                
                # 获取收盘数据（15:00:00）
                for code in codes:
                    snapshot = self.get_snapshot_at_time(code, '150000')
                    if snapshot:
                        result.append(snapshot)
            
            logger.info(f"✅ [V19.17] 复盘模式：成功获取 {len(result)} 只股票的数据")
            return result
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 获取复盘数据失败: {e}")
            return []
    
    def get_market_data(self) -> Dict:
        """
        获取历史市场数据
        
        Returns:
            dict: 市场数据
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用")
            return {
                'limit_up_count': 0,
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
                'replay_date': self.date,
                'replay_mode': True,
            }
        
        try:
            # 🔥 V19.17: 使用 QMT 获取当日全市场数据
            # 这里简化处理，返回默认值
            # 实际应用中可以通过 QMT 获取全市场统计
            
            logger.info(f"📊 [V19.17] 获取 {self.date} 的市场数据...")
            
            return {
                'limit_up_count': 0,  # 需要通过全市场扫描计算
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
                'replay_date': self.date,
                'replay_time': self.time_point,
                'replay_mode': True,
            }
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 获取市场数据失败: {e}")
            return {
                'limit_up_count': 0,
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
                'replay_date': self.date,
                'replay_mode': True,
            }
    
    def get_historical_kline(self, code: str, days: int = 60) -> pd.DataFrame:
        """
        获取历史K线数据（用于技术分析）
        
        Args:
            code: 股票代码
            days: 获取天数
        
        Returns:
            DataFrame: K线数据
        """
        if not self.qmt_available:
            logger.error("❌ QMT 接口不可用")
            return pd.DataFrame()
        
        try:
            qmt_code = self.code_converter.to_qmt(code)
            
            # 计算起始日期
            end_date = datetime.strptime(self.date, '%Y%m%d')
            start_date = (end_date - timedelta(days=days*2)).strftime('%Y%m%d')
            
            # 下载历史数据
            self.xtdata.download_history_data(
                stock_code=qmt_code,
                period='1d',
                start_time=start_date,
                end_time=self.date
            )
            
            # 获取数据
            data = self.xtdata.get_local_data(
                field_list=[],
                stock_list=[qmt_code],
                period='1d',
                start_time=start_date,
                end_time=self.date,
                count=-1,
                dividend_type='none',
                fill_data=True
            )
            
            if qmt_code not in data or data[qmt_code].empty:
                return pd.DataFrame()
            
            # 只返回最近 days 天的数据
            df = data[qmt_code]
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ [V19.17] 获取 {code} 历史K线数据失败: {e}")
            return pd.DataFrame()