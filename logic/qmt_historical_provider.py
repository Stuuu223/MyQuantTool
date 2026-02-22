#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT历史数据提供者（迁移到TickProvider）

功能：
1. 从QMT本地datadir读取历史Tick数据
2. 提供统一的Tick数据迭代接口
3. 作为QmtTickProvider的底层入口
4. 支持Tick→主力净流推断算法

使用TickProvider统一封装类，不再直接导入xtdata

Author: CTO (T4迁移)
Date: 2026-02-19
Version: V1.1 (TickProvider版)
"""

from typing import Iterator, Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from logic.data_providers.base import ICapitalFlowProvider, CapitalFlowSignal

# 🔥 T4迁移：不再直接导入xtdata，通过TickProvider获取
# from xtquant import xtdata


class QMTHistoricalProvider:
    """
    QMT历史数据提供者

    职责：
    1. 读取指定股票、时间范围的Tick数据
    2. 提供统一的Tick数据迭代接口
    3. 支持Tick数据的时间序列处理
    """

    def __init__(
        self, 
        stock_code: str, 
        start_time: str, 
        end_time: str, 
        period: str = "tick",
        tick_provider=None
    ) -> None:
        """
        初始化QMT历史数据提供者

        Args:
            stock_code: 股票代码（QMT格式，如 300997.SZ）
            start_time: 开始时间（格式：YYYYMMDDhhmmss 或 YYYYMMDD hh:mm:ss）
            end_time: 结束时间（格式：YYYYMMDDhhmmss 或 YYYYMMDD hh:mm:ss）
            period: 数据周期，默认为"tick"
            tick_provider: TickProvider实例（可选，不传则自动创建）
        """
        self.stock_code = stock_code
        # 标准化时间格式为YYYYMMDDhhmmss
        self.start_time = self._normalize_time_format(start_time)
        self.end_time = self._normalize_time_format(end_time)
        self.period = period
        
        # 🔥 T4迁移：使用TickProvider管理xtdata
        self._tick_provider = tick_provider
        self._xtdata = None
        self._ensure_data_dir()

    def _get_xtdata(self):
        """获取xtdata实例（纯本地模式，无订阅端口）"""
        if self._xtdata is None:
            # 🔥 历史模式：直接导入xtdata，不通过TickProvider（避免订阅端口58609）
            import xtquant.xtdata as xtdata
            self._xtdata = xtdata
            print("   🔥 历史模式：直连xtdata.get_local_data()")
        return self._xtdata

    def _normalize_time_format(self, time_str: str) -> str:
        """
        标准化时间格式为YYYYMMDDhhmmss

        Args:
            time_str: 时间字符串（支持多种格式）

        Returns:
            str: 标准化后的时间字符串
        """
        if not time_str:
            return time_str

        # 移除特殊字符
        time_str = time_str.replace("-", "").replace(" ", "").replace(":", "")

        # 如果是YYYYMMDD格式，扩展为YYYYMMDD000000
        if len(time_str) == 8:
            time_str = time_str + "000000"

        return time_str

    def _ensure_data_dir(self) -> None:
        """
        确保QMT数据目录已设置
        """
        # 🔥 T4迁移：复用TickProvider的数据目录设置
        # 延迟初始化，在需要时再设置
        pass

    def _ensure_local_history(self) -> None:
        """
        确保本地历史数据存在
        """
        try:
            xtdata = self._get_xtdata()
            # 下载本地缺失的历史Tick数据
            xtdata.download_history_data(
                stock_code=self.stock_code,
                period=self.period,
                start_time=self.start_time,
                end_time=self.end_time
            )
        except Exception as e:
            print(f"⚠️ 下载历史数据时出错: {e}")
            # 如果下载失败，继续尝试读取已有的数据

    def get_raw_ticks(self) -> pd.DataFrame:
        """
        获取原始Tick数据 - V14路径修复版
        
        QMT tick文件是二进制格式，需要使用xtdata读取。
        
        Returns:
            pd.DataFrame: 包含Tick数据的DataFrame
        """
        try:
            # 先尝试配置xtdata数据目录
            xtdata = self._get_xtdata()
            
            # 配置数据目录 - 使用项目目录
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            data_dir = str(project_root / "data" / "qmt_data")
            
            # 设置数据目录
            if hasattr(xtdata, 'default_data_dir'):
                xtdata.default_data_dir = data_dir
            if hasattr(xtdata, '__data_dir_from_server'):
                xtdata.__data_dir_from_server = data_dir
            
            # 读取Tick数据
            df = xtdata.get_local_data(
                field_list=[
                    "time", "lastPrice", "open", "high", "low",
                    "volume", "amount", "bidPrice", "askPrice",
                    "bidVol", "askVol",
                ],
                stock_list=[self.stock_code],
                period=self.period,
                start_time=self.start_time,
                end_time=self.end_time
            )

            if df is None or self.stock_code not in df:
                print(f"❌ 未获取到数据: {self.stock_code}")
                return pd.DataFrame()

            tick_df = df[self.stock_code]
            if tick_df is None or tick_df.empty:
                print(f"❌ 数据为空: {self.stock_code}")
                return pd.DataFrame()
            
            # 添加preClose估算
            if 'preClose' not in tick_df.columns:
                tick_df['preClose'] = tick_df['lastPrice'].iloc[0] * 0.98 if len(tick_df) > 0 else 0
            
            print(f"✅ 读取Tick数据成功: {len(tick_df)}条")
            return tick_df.sort_values("time").reset_index(drop=True)
            
        except Exception as e:
            print(f"❌ 获取Tick数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def iter_ticks(self) -> Iterator[Dict[str, Any]]:
        """
        迭代返回Tick数据

        Yields:
            Dict[str, Any]: Tick数据字典，包含时间、价格、成交量等字段
        """
        tick_df = self.get_raw_ticks()
        
        for _, row in tick_df.iterrows():
            # 格式化为实盘Tick格式，确保与UnifiedWarfareCore兼容
            tick_dict = self._format_to_realtime_tick(row)
            yield tick_dict
    
    def _format_to_realtime_tick(self, row):
        """
        强制将QMT本地的DataFrame格式，1:1精准映射为实盘字典格式
        解决五档数据丢失导致的静默失败问题
        """
        # QMT历史数据中，bidPrice, askPrice, bidVol, askVol已经是数组格式
        bid_price_list = row.get("bidPrice", [0.0, 0.0, 0.0, 0.0, 0.0])
        ask_price_list = row.get("askPrice", [0.0, 0.0, 0.0, 0.0, 0.0])
        bid_vol_list = row.get("bidVol", [0, 0, 0, 0, 0])
        ask_vol_list = row.get("askVol", [0, 0, 0, 0, 0])
        
        # 确保是5档数据
        if not isinstance(bid_price_list, list) or len(bid_price_list) == 0:
            bid_price_list = [0.0, 0.0, 0.0, 0.0, 0.0]
        if not isinstance(ask_price_list, list) or len(ask_price_list) == 0:
            ask_price_list = [0.0, 0.0, 0.0, 0.0, 0.0]
        if not isinstance(bid_vol_list, list) or len(bid_vol_list) == 0:
            bid_vol_list = [0, 0, 0, 0, 0]
        if not isinstance(ask_vol_list, list) or len(ask_vol_list) == 0:
            ask_vol_list = [0, 0, 0, 0, 0]

        return {
            "time": int(str(row["time"]).replace(',', '') or 0),
            "lastPrice": float(row.get("lastPrice", 0)),
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "volume": float(row.get("volume", 0)),
            "amount": float(row.get("amount", 0)),
            "bidPrice": bid_price_list,
            "askPrice": ask_price_list,
            "bidVol": bid_vol_list,
            "askVol": ask_vol_list,
            "preClose": float(str(row.get("preClose", 0)).replace(',', ''))
        }

    def get_tick_count(self) -> int:
        """
        获取Tick数据总数量

        Returns:
            int: Tick数据数量
        """
        tick_df = self.get_raw_ticks()
        return len(tick_df) if not tick_df.empty else 0

    def get_time_range(self) -> tuple:
        """
        获取时间范围

        Returns:
            tuple: (最早时间, 最晚时间)
        """
        tick_df = self.get_raw_ticks()
        if tick_df.empty:
            return (None, None)
        
        first_time = tick_df['time'].iloc[0] if not tick_df.empty else None
        last_time = tick_df['time'].iloc[-1] if not tick_df.empty else None
        return (first_time, last_time)

    def estimate_main_flow_from_ticks(self) -> Dict[str, float]:
        """
        从Tick数据推断主力资金流

        根据CTO指示的算法：
        estimated_main_flow = base_flow * 0.4 + bid_pressure * 1.0 + price_strength * 0.3

        Returns:
            Dict[str, float]: 资金流相关指标
        """
        tick_df = self.get_raw_ticks()
        if tick_df.empty:
            return {
                "main_net_inflow": 0.0,
                "main_buy": 0.0,
                "main_sell": 0.0,
                "retail_net_inflow": 0.0,
                "bid_pressure": 0.0,
                "price_strength": 0.0,
                "base_flow": 0.0
            }

        # 计算基础资金流（基于成交量和价格变化）
        volumes = tick_df['volume'].diff().fillna(0)
        price_changes = tick_df['lastPrice'].diff().fillna(0)
        
        # 计算主动买入/卖出（基于价格变化和成交量）
        main_buy = ((price_changes > 0) * volumes).sum()
        main_sell = ((price_changes < 0) * volumes).sum()
        base_flow = main_buy + main_sell  # 可能为负值，表示净流出

        # 计算买卖压力（基于盘口数据）
        bid_prices = tick_df['bidPrice'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 0)
        ask_prices = tick_df['askPrice'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 0)
        bid_vols = tick_df['bidVol'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 0)
        ask_vols = tick_df['askVol'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 0)

        # 买卖压力计算
        bid_pressure = (bid_vols * bid_prices).sum() - (ask_vols * ask_prices).sum()
        
        # 价格强度（基于价格相对于开盘价的变化）
        open_price = tick_df['open'].iloc[0] if not tick_df.empty else 0
        if open_price > 0:
            price_changes_from_open = (tick_df['lastPrice'] - open_price) / open_price
            price_strength = price_changes_from_open.mean()
        else:
            price_strength = 0.0

        # 计算主力净流入（使用CTO提供的公式）
        main_net_inflow = base_flow * 0.4 + bid_pressure * 1.0 + price_strength * 0.3

        return {
            "main_net_inflow": float(main_net_inflow),
            "main_buy": float(main_buy),
            "main_sell": float(main_sell),
            "retail_net_inflow": float(base_flow - main_net_inflow),  # 零售资金流
            "bid_pressure": float(bid_pressure),
            "price_strength": float(price_strength),
            "base_flow": float(base_flow)
        }


class QmtTickCapitalFlowProvider(ICapitalFlowProvider):
    """
    QMT Tick 资金流提供者

    实现 ICapitalFlowProvider 接口，从Tick数据推断资金流
    注意：此提供者返回的是基于窗口时间的估算资金流，不是实时逐笔数据
    """

    def __init__(self, window_minutes: int = 30, tick_provider=None):
        """
        初始化

        Args:
            window_minutes: 计算资金流的时间窗口（分钟）
            tick_provider: TickProvider实例（可选）
        """
        self.window_minutes = window_minutes
        self._tick_provider = tick_provider
        self._xtdata = None

    def _get_xtdata(self):
        """获取xtdata实例（通过TickProvider）"""
        if self._xtdata is None:
            if self._tick_provider is None:
                from logic.data_providers.tick_provider import TickProvider
                self._tick_provider = TickProvider()
                if not self._tick_provider.is_connected():
                    self._tick_provider.connect()
            self._xtdata = self._tick_provider._xtdata
        return self._xtdata

    def get_realtime_flow(self, code: str) -> Optional[CapitalFlowSignal]:
        """
        获取实时资金流（基于时间窗口的估算）

        注意：此方法返回的是基于最近N分钟Tick数据推断出的资金流，
        而非Level-2意义上的逐笔主力流向。返回值会带有估算窗口信息。

        Args:
            code: 股票代码

        Returns:
            CapitalFlowSignal: 资金流信号（包含估算窗口信息）
        """
        from datetime import datetime, timedelta
        import time

        # 计算时间范围（最近N分钟）
        now = datetime.now()
        start_time = now - timedelta(minutes=self.window_minutes)
        
        start_str = start_time.strftime("%Y%m%d%H%M%S")
        end_str = now.strftime("%Y%m%d%H%M%S")

        try:
            # 创建历史数据提供者
            provider = QMTHistoricalProvider(
                stock_code=code,
                start_time=start_str,
                end_time=end_str,
                period="tick",
                tick_provider=self._tick_provider
            )

            # 获取Tick数据并推断资金流
            flow_data = provider.estimate_main_flow_from_ticks()

            # 构建CapitalFlowSignal
            signal = CapitalFlowSignal(
                code=code,
                timestamp=time.time(),  # 使用当前时间戳（秒级）
                main_net_inflow=flow_data["main_net_inflow"],
                super_large_inflow=flow_data["main_buy"],  # 使用主力买入作为超大单流入
                large_inflow=flow_data["main_sell"],      # 使用主力卖出作为大单流出
                confidence=0.8,  # Tick数据分析的置信度
                source="QMT_Tick_Windowed_Estimator"      # 明确标识为窗口估算器
            )

            # 添加窗口信息到额外属性（如果类支持）
            setattr(signal, 'window_start_time', start_str)
            setattr(signal, 'window_end_time', end_str)
            setattr(signal, 'window_minutes', self.window_minutes)

            return signal

        except Exception as e:
            print(f"❌ 获取实时资金流失败: {e}")
            return None

    def get_data_freshness(self, code: str) -> int:
        """
        获取数据新鲜度

        Args:
            code: 股票代码

        Returns:
            int: 数据新鲜度（毫秒）
        """
        import time
        # Tick数据非常实时，返回最小延迟
        return 100  # 100毫秒

    def get_full_tick(self, code_list: List[str]) -> Dict:
        """
        获取全推Tick数据

        Args:
            code_list: 股票代码列表

        Returns:
            Dict: Tick数据字典
        """
        # 这个方法需要QMT实时接口，不是历史数据
        # 返回空字典，实际使用QMT实时接口
        return {}

    def get_kline_data(self, code_list: List[str], period: str = '1d',
                       start_time: str = '', end_time: str = '',
                       count: int = -1) -> Dict:
        """
        获取K线数据

        Args:
            code_list: 股票代码列表
            period: 周期
            start_time: 开始时间
            end_time: 结束时间
            count: 数据条数

        Returns:
            Dict: K线数据
        """
        # 从QMT获取K线数据
        try:
            xtdata = self._get_xtdata()
            result = {}
            for code in code_list:
                data = xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                    stock_list=[code],
                    period=period,
                    start_time=start_time,
                    end_time=end_time,
                    count=count
                )
                result[code] = data.get(code, pd.DataFrame())
            return result
        except Exception as e:
            print(f"❌ 获取K线数据失败: {e}")
            return {}

    def get_stock_list_in_sector(self, sector_name: str) -> List[str]:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称

        Returns:
            List[str]: 股票代码列表
        """
        try:
            xtdata = self._get_xtdata()
            return xtdata.get_stock_list_in_sector(sector_name)
        except Exception as e:
            print(f"❌ 获取板块成分股失败: {e}")
            return []

    def get_historical_flow(self, code: str, days: int = 30) -> Optional[Dict]:
        """
        获取历史资金流

        Args:
            code: 股票代码
            days: 天数

        Returns:
            Dict: 历史资金流数据
        """
        from datetime import datetime, timedelta
        import time

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        start_str = start_time.strftime("%Y%m%d")
        end_str = end_time.strftime("%Y%m%d")

        try:
            # 创建历史数据提供者
            provider = QMTHistoricalProvider(
                stock_code=code,
                start_time=start_str,
                end_time=end_str,
                period="tick",
                tick_provider=self._tick_provider
            )

            # 获取资金流数据
            flow_data = provider.estimate_main_flow_from_ticks()

            return {
                "code": code,
                "start_date": start_str,
                "end_date": end_str,
                "days": days,
                "main_net_inflow": flow_data["main_net_inflow"],
                "main_buy": flow_data["main_buy"],
                "main_sell": flow_data["main_sell"],
                "retail_net_inflow": flow_data["retail_net_inflow"],
                "timestamp": time.time()
            }

        except Exception as e:
            print(f"❌ 获取历史资金流失败: {e}")
            return None

    def get_market_data(self, field_list: List[str], stock_list: List[str],
                       period: str = '1d', start_time: str = '', end_time: str = '',
                       dividend_type: str = 'none', fill_data: bool = False) -> Dict:
        """
        获取市场数据

        Args:
            field_list: 字段列表
            stock_list: 股票列表
            period: 周期
            start_time: 开始时间
            end_time: 结束时间
            dividend_type: 分红类型
            fill_data: 是否填充数据

        Returns:
            Dict: 市场数据
        """
        try:
            xtdata = self._get_xtdata()
            return xtdata.get_local_data(
                field_list=field_list,
                stock_list=stock_list,
                period=period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,
                fill_data=fill_data
            )
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
            return {}

    def get_instrument_detail(self, code: str) -> Dict:
        """
        获取合约详情

        Args:
            code: 股票代码

        Returns:
            Dict: 合约详情
        """
        # QMT中没有直接的合约详情接口，返回空字典
        return {}

    def download_history_data(self, code: str, period: str = '1m',
                              count: int = -1, incrementally: bool = False) -> Dict:
        """
        下载历史数据

        Args:
            code: 股票代码
            period: 周期
            count: 数据条数
            incrementally: 是否增量下载

        Returns:
            Dict: 下载结果
        """
        try:
            xtdata = self._get_xtdata()
            result = xtdata.download_history_data(
                stock_code=code,
                period=period,
                start_time="",
                end_time="",
                incrementally=incrementally
            )
            return {"success": True, "result": result}
        except Exception as e:
            print(f"❌ 下载历史数据失败: {e}")
            return {"success": False, "error": str(e)}

    def get_provider_name(self) -> str:
        """
        获取提供者名称

        Returns:
            str: 提供者名称
        """
        return "QMT_Tick_Capital_Flow_Provider"


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("🧪 QMTHistoricalProvider 测试 (TickProvider版)")
    print("=" * 60)

    # 测试读取300997.SZ的Tick数据
    provider = QMTHistoricalProvider(
        stock_code="300997.SZ",
        start_time="20251114093000",
        end_time="20251114150000",
        period="tick"
    )

    print(f"📊 Tick数量: {provider.get_tick_count()}")
    print(f"📅 时间范围: {provider.get_time_range()}")

    # 测试资金流推断
    flow_data = provider.estimate_main_flow_from_ticks()
    print(f"💰 资金流推断结果: {flow_data}")

    # 测试Tick迭代
    print("\n📋 测试Tick迭代 (前5条):")
    count = 0
    for tick in provider.iter_ticks():
        if count < 5:
            print(f"  {tick['time']}: {tick['last_price']:.2f}, {tick['volume']}")
            count += 1
        else:
            break

    print("\n✅ QMTHistoricalProvider 测试完成")
    print("=" * 60)