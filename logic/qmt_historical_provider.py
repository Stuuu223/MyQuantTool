#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT历史数据提供者 - V14路径修复版
统一从QMT标准路径读取历史Tick数据

CTO指令：所有数据访问必须通过DataService，禁止硬编码路径
"""
import pandas as pd
from typing import Iterator, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

# 从DataService导入配置
from logic.services.data_service import data_service

class QMTHistoricalProvider:
    """
    QMT历史数据提供者
    统一从QMT标准路径读取历史Tick数据
    """
    
    def __init__(self, stock_code: str, start_time: str, end_time: str, period: str = 'tick'):
        """
        初始化历史数据提供者
        
        Args:
            stock_code: 股票代码 (e.g. '000547.SZ')
            start_time: 开始时间 (e.g. '20260101' or '20260101000000')
            end_time: 结束时间 (e.g. '20260101' or '20260101150000')
            period: 数据周期 ('tick', '1m', '5m', '1d')
        """
        self.stock_code = stock_code
        self.start_time = start_time
        self.end_time = end_time
        self.period = period
        
        # 验证环境
        passed, info = data_service.env_check()
        if not passed:
            print(f"⚠️ 环境检查失败: {info}")
        else:
            print(f"✅ 环境检查通过: {info.get('sz_stock_count', 0)} SZ, {info.get('sh_stock_count', 0)} SH")
    
    def _get_xtdata(self):
        """获取xtdata模块（延迟导入避免启动时连接）"""
        try:
            from xtquant import xtdata
            return xtdata
        except ImportError:
            raise ImportError("xtquant module not found. Please install xtquant.")
    
    def get_raw_ticks(self) -> pd.DataFrame:
        """
        获取原始Tick数据 - V14路径修复版
        现在直接使用xtdata的默认配置（QMT客户端路径）
        
        Returns:
            pd.DataFrame: 包含Tick数据的DataFrame
        """
        try:
            xtdata = self._get_xtdata()
            
            # 🔥 V14修复：不再手动设置数据目录，使用xtdata默认配置
            # xtdata会自动使用QMT客户端配置的数据目录 (E:\qmt\userdata_mini\datadir)
            
            # 验证股票数据是否存在
            exists, tick_count = data_service.verify_tick_exists(self.stock_code)
            if not exists:
                print(f"❌ Tick数据不存在: {self.stock_code}")
                return pd.DataFrame()
            else:
                print(f"📊 Tick数据存在: {self.stock_code}, 预估条数: {tick_count}")
            
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
                # 🔥 V14修复：使用DataService获取准确的昨收价
                date_part = self.start_time[:8]  # 提取日期部分
                if len(date_part) == 8:
                    # 转换为'YYYY-MM-DD'格式
                    date_formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                    pre_close = data_service.get_pre_close(self.stock_code, date_formatted)
                    if pre_close > 0:
                        tick_df['preClose'] = pre_close
                    else:
                        tick_df['preClose'] = tick_df['lastPrice'].iloc[0] * 0.98 if len(tick_df) > 0 else 0
                else:
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
        迭代返回Tick数据（用于逐笔处理）
        """
        df = self.get_raw_ticks()
        for _, row in df.iterrows():
            tick_dict = row.to_dict()
            # 添加股票代码信息
            tick_dict['stock_code'] = self.stock_code
            yield tick_dict

    def get_tick_count(self) -> int:
        """
        获取Tick数据条数
        """
        df = self.get_raw_ticks()
        return len(df) if df is not None else 0

    def get_time_range(self) -> tuple:
        """
        获取时间范围
        """
        df = self.get_raw_ticks()
        if df.empty:
            return None, None
        return df['time'].min(), df['time'].max()

    def get_price_range(self) -> tuple:
        """
        获取价格范围
        """
        df = self.get_raw_ticks()
        if df.empty:
            return 0, 0
        return df['lastPrice'].min(), df['lastPrice'].max()

    def get_volume_range(self) -> tuple:
        """
        获取成交量范围
        """
        df = self.get_raw_ticks()
        if df.empty:
            return 0, 0
        return df['volume'].min(), df['volume'].max()

    def get_amount_range(self) -> tuple:
        """
        获取成交额范围
        """
        df = self.get_raw_ticks()
        if df.empty:
            return 0, 0
        return df['amount'].min(), df['amount'].max()

    def get_summary(self) -> Dict[str, Any]:
        """
        获取数据摘要
        """
        df = self.get_raw_ticks()
        if df.empty:
            return {
                'count': 0,
                'time_range': (None, None),
                'price_range': (0, 0),
                'volume_range': (0, 0),
                'amount_range': (0, 0)
            }
        
        time_range = self.get_time_range()
        price_range = self.get_price_range()
        volume_range = self.get_volume_range()
        amount_range = self.get_amount_range()
        
        return {
            'count': len(df),
            'time_range': time_range,
            'price_range': price_range,
            'volume_range': volume_range,
            'amount_range': amount_range,
            'avg_volume_per_tick': df['volume'].mean() if 'volume' in df.columns else 0,
            'avg_amount_per_tick': df['amount'].mean() if 'amount' in df.columns else 0
        }


def format_time_for_display(time_value) -> str:
    """
    格式化时间戳用于显示
    """
    try:
        # 如果是时间戳（整数或浮点数）
        if isinstance(time_value, (int, float)):
            if time_value > 1e10:  # 毫秒级时间戳
                dt = datetime.fromtimestamp(time_value / 1000)
            else:  # 秒级时间戳
                dt = datetime.fromtimestamp(time_value)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(time_value, str):
            # 如果是字符串格式的时间
            return time_value
        else:
            return str(time_value)
    except Exception:
        return str(time_value)


# 测试和验证代码
if __name__ == "__main__":
    print("="*60)
    print("QMT历史数据提供者 - V14路径修复版测试")
    print("="*60)
    
    # 环境检查
    print("\n1. 环境检查...")
    passed, info = data_service.env_check()
    print(f"   检查结果: {passed}")
    print(f"   深圳股票: {info.get('sz_stock_count', 0)}只")
    print(f"   上海股票: {info.get('sh_stock_count', 0)}只")
    
    print("\n2. Tick数据验证...")
    test_codes = ['000547.SZ', '300017.SZ']
    for code in test_codes:
        exists, count = data_service.verify_tick_exists(code)
        print(f"   {code}: 存在={exists}, 预估={count}条")
    
    print("\n3. 数据读取测试...")
    # 创建提供者实例
    provider = QMTHistoricalProvider(
        stock_code='000547.SZ',
        start_time='20260204000000',  # YYYYMMDDHHMMSS
        end_time='20260204150000',
        period='tick'
    )
    
    print(f"\n📊 开始获取 {provider.stock_code} 的Tick数据...")
    tick_df = provider.get_raw_ticks()
    
    if len(tick_df) > 0:
        print(f"✅ 成功获取 {len(tick_df)} 条Tick数据")
        print(f"📊 列名: {list(tick_df.columns)}")
        print(f"📊 时间范围: {format_time_for_display(tick_df['time'].iloc[0])} -> {format_time_for_display(tick_df['time'].iloc[-1])}")
        print(f"📊 价格范围: {tick_df['lastPrice'].min():.2f} - {tick_df['lastPrice'].max():.2f}")
        print(f"📊 成交量范围: {tick_df['volume'].min():.0f} - {tick_df['volume'].max():.0f}")
        
        # 显示前几行数据
        print(f"\n📋 前5行数据:")
        print(tick_df.head())
        
        # 数据摘要
        summary = provider.get_summary()
        print(f"\n📈 数据摘要:")
        for key, value in summary.items():
            print(f"   {key}: {value}")
    else:
        print("❌ 未获取到数据")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)