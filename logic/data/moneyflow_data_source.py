"""
Unified Moneyflow Data Source Abstraction
Supports multiple data sources: eastmoney, tushare, tushare_ths
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import pandas as pd
import tushare as ts
import json
import os

# Tushare token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"


@dataclass
class MoneyflowSnapshot:
    """Unified moneyflow snapshot structure"""
    ts_code: str
    trade_date: str
    main_net_inflow: float      # 主力净流入（万元）
    super_large_net: float      # 超大单净流入（万元）
    large_net: float            # 大单净流入（万元）
    medium_net: float           # 中单净流入（万元）
    small_net: float            # 小单净流入（万元）
    source: str                 # 'eastmoney' | 'tushare' | 'tushare_ths'
    raw_data: Optional[dict] = None  # 原始数据（用于调试）


class MoneyflowDataSource:
    """Abstract moneyflow data source"""
    
    def get_moneyflow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> List[MoneyflowSnapshot]:
        """Get moneyflow data"""
        raise NotImplementedError


class EastmoneyMoneyflowSource(MoneyflowDataSource):
    """Eastmoney moneyflow data source"""
    
    def __init__(self, data_dir: str = "E:/MyQuantTool/data/scan_results"):
        self.data_dir = data_dir
    
    def get_moneyflow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> List[MoneyflowSnapshot]:
        """Get moneyflow data from eastmoney JSON files"""
        # Find the latest snapshot file (exclude test files and 999999 files)
        snapshot_files = []
        for file in os.listdir(self.data_dir):
            if file.endswith("_intraday.json") and "test" not in file.lower() and "999999" not in file:
                snapshot_files.append(os.path.join(self.data_dir, file))
        
        if not snapshot_files:
            return []
        
        # Use the latest snapshot file (by modification time)
        latest_file = max(snapshot_files, key=os.path.getmtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract flow_data for the specified stock
        opportunities = data.get('results', {}).get('opportunities', [])
        
        snapshots = []
        for opp in opportunities:
            if opp.get('code') == ts_code:
                flow_data = opp.get('flow_data', {})
                records = flow_data.get('records', [])
                
                for record in records:
                    # Convert date format from YYYY-MM-DD to YYYYMMDD
                    record_date = record['date'].replace('-', '')
                    if start_date <= record_date <= end_date:
                        # Convert from Yuan (元) to Wan Yuan (万元)
                        snapshot = MoneyflowSnapshot(
                            ts_code=ts_code,
                            trade_date=record_date,
                            main_net_inflow=record.get('main_net_inflow', 0.0) / 10000,
                            super_large_net=record.get('super_large_net', 0.0) / 10000,
                            large_net=record.get('large_net', 0.0) / 10000,
                            medium_net=record.get('medium_net', 0.0) / 10000,
                            small_net=record.get('small_net', 0.0) / 10000,
                            source='eastmoney',
                            raw_data=record
                        )
                        snapshots.append(snapshot)
        
        return snapshots


class TushareMoneyflowSource(MoneyflowDataSource):
    """Tushare standard moneyflow data source"""
    
    def __init__(self, token: str = TOKEN):
        ts.set_token(token)
        self.pro = ts.pro_api()
    
    def get_moneyflow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> List[MoneyflowSnapshot]:
        """Get moneyflow data from Tushare moneyflow API"""
        try:
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            snapshots = []
            for _, row in df.iterrows():
                # Calculate net inflow for each category
                super_large_net = (row['buy_elg_amount'] - row['sell_elg_amount']) / 10000  # Convert to 万元
                large_net = (row['buy_lg_amount'] - row['sell_lg_amount']) / 10000
                medium_net = (row['buy_md_amount'] - row['sell_md_amount']) / 10000
                small_net = (row['buy_sm_amount'] - row['sell_sm_amount']) / 10000
                main_net_inflow = super_large_net + large_net
                
                snapshot = MoneyflowSnapshot(
                    ts_code=ts_code,
                    trade_date=row['trade_date'],
                    main_net_inflow=main_net_inflow,
                    super_large_net=super_large_net,
                    large_net=large_net,
                    medium_net=medium_net,
                    small_net=small_net,
                    source='tushare',
                    raw_data=row.to_dict()
                )
                snapshots.append(snapshot)
            
            return snapshots
            
        except Exception as e:
            print(f"Tushare moneyflow error: {e}")
            return []


class TushareTHSMoneyflowSource(MoneyflowDataSource):
    """Tushare THS moneyflow data source"""
    
    def __init__(self, token: str = TOKEN):
        ts.set_token(token)
        self.pro = ts.pro_api()
    
    def get_moneyflow(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> List[MoneyflowSnapshot]:
        """Get moneyflow data from Tushare moneyflow_ths API"""
        try:
            df = self.pro.moneyflow_ths(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            snapshots = []
            for _, row in df.iterrows():
                # THS only provides buy amounts, need to estimate sell amounts
                # Use net_amount to estimate main_net_inflow
                main_net_inflow = row['net_amount'] / 10000  # Convert to 万元
                
                # THS doesn't provide detailed breakdown, use estimation
                # Assume super_large_net = buy_lg_amount * 0.6, large_net = buy_lg_amount * 0.4
                large_buy = row['buy_lg_amount'] / 10000
                medium_buy = row['buy_md_amount'] / 10000
                small_buy = row['buy_sm_amount'] / 10000
                
                # Estimate based on typical ratios
                super_large_net = large_buy * 0.6
                large_net = large_buy * 0.4
                medium_net = medium_buy - main_net_inflow * 0.2  # Rough estimation
                small_net = small_buy - main_net_inflow * 0.1  # Rough estimation
                
                snapshot = MoneyflowSnapshot(
                    ts_code=ts_code,
                    trade_date=row['trade_date'],
                    main_net_inflow=main_net_inflow,
                    super_large_net=super_large_net,
                    large_net=large_net,
                    medium_net=medium_net,
                    small_net=small_net,
                    source='tushare_ths',
                    raw_data=row.to_dict()
                )
                snapshots.append(snapshot)
            
            return snapshots
            
        except Exception as e:
            print(f"Tushare THS moneyflow error: {e}")
            return []


def get_moneyflow(
    ts_code: str,
    start_date: str,
    end_date: str,
    source: str = "eastmoney",
    fallback_sources: Optional[List[str]] = None,
) -> List[MoneyflowSnapshot]:
    """
    Unified interface to get moneyflow data from different sources
    
    Args:
        ts_code: Stock code (e.g., '603607.SH')
        start_date: Start date (e.g., '20260201')
        end_date: End date (e.g., '20260206')
        source: Primary data source ('eastmoney' | 'tushare' | 'tushare_ths')
        fallback_sources: List of fallback sources if primary fails
    
    Returns:
        List of MoneyflowSnapshot objects
    """
    # Default fallback sources
    if fallback_sources is None:
        fallback_sources = []
        if source != "eastmoney":
            fallback_sources.append("eastmoney")
        if source != "tushare":
            fallback_sources.append("tushare")
        if source != "tushare_ths":
            fallback_sources.append("tushare_ths")
    
    # Map source names to data source classes
    source_map = {
        'eastmoney': EastmoneyMoneyflowSource,
        'tushare': TushareMoneyflowSource,
        'tushare_ths': TushareTHSMoneyflowSource,
    }
    
    # Try primary source first
    primary_class = source_map.get(source)
    if primary_class:
        primary_source = primary_class()
        snapshots = primary_source.get_moneyflow(ts_code, start_date, end_date)
        if snapshots:
            print(f"✅ Got {len(snapshots)} records from {source}")
            return snapshots
        else:
            print(f"❌ No data from {source}")
    
    # Try fallback sources
    for fallback_source in fallback_sources:
        fallback_class = source_map.get(fallback_source)
        if fallback_class:
            fallback_instance = fallback_class()
            snapshots = fallback_instance.get_moneyflow(ts_code, start_date, end_date)
            if snapshots:
                print(f"✅ Got {len(snapshots)} records from fallback: {fallback_source}")
                return snapshots
            else:
                print(f"❌ No data from fallback: {fallback_source}")
    
    print(f"❌ No moneyflow data available for {ts_code}")
    return []


def compare_moneyflow_sources(
    ts_code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Compare moneyflow data from different sources
    
    Args:
        ts_code: Stock code (e.g., '603607.SH')
        start_date: Start date (e.g., '20260201')
        end_date: End date (e.g., '20260206')
    
    Returns:
        DataFrame comparing main_net_inflow from different sources
    """
    sources = ['eastmoney', 'tushare', 'tushare_ths']
    
    comparison_data = {}
    for source in sources:
        snapshots = get_moneyflow(ts_code, start_date, end_date, source=source, fallback_sources=[])
        
        for snapshot in snapshots:
            trade_date = snapshot.trade_date
            if trade_date not in comparison_data:
                comparison_data[trade_date] = {}
            comparison_data[trade_date][f"{source}_main_net"] = snapshot.main_net_inflow
    
    # Convert to DataFrame
    df = pd.DataFrame.from_dict(comparison_data, orient='index')
    df.index.name = 'trade_date'
    
    return df


if __name__ == "__main__":
    # Test all three sources
    print("=" * 60)
    print("Test: Compare moneyflow data from three sources")
    print("=" * 60)
    
    ts_code = '603607.SH'
    start_date = '20250812'
    end_date = '20250822'
    
    df = compare_moneyflow_sources(ts_code, start_date, end_date)
    print("\nComparison:")
    print(df)
    
    print("\n" + "=" * 60)
    print("Test: Get moneyflow from eastmoney (with fallback)")
    print("=" * 60)
    
    snapshots = get_moneyflow(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        source='eastmoney',
        fallback_sources=['tushare', 'tushare_ths']
    )
    
    print(f"\nGot {len(snapshots)} snapshots:")
    for snapshot in snapshots:
        print(f"  {snapshot.trade_date}: {snapshot.source} - main_net_inflow={snapshot.main_net_inflow:.2f}")