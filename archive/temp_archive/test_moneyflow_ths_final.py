"""
Final Test for Tushare moneyflow_ths API
Test targets:
1. Verify if the API is still accessible
2. Get actual data
3. Compare with eastmoney and standard moneyflow
"""

import sys
sys.path.append('E:/MyQuantTool')

import tushare as ts
import pandas as pd
from datetime import datetime
from logic.moneyflow_data_source import (
    EastmoneyMoneyflowSource,
    TushareMoneyflowSource,
    TushareTHSMoneyflowSource
)

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_direct_api_call():
    """Test direct API call to moneyflow_ths"""
    print("=" * 60)
    print("Test 1: Direct API Call to moneyflow_ths")
    print("=" * 60)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test stock: 603607.SH")
    print(f"Test date: 2025-08-12 to 2025-08-22")
    print()
    
    try:
        # Direct API call
        df = pro.moneyflow_ths(
            ts_code='603607.SH',
            start_date='20250812',
            end_date='20250822'
        )
        
        print(f"✅ SUCCESS: {len(df)} records")
        print(f"\nFields: {list(df.columns)}")
        print(f"\nData Preview:")
        print(df)
        
        print("\n" + "=" * 60)
        print("Conclusion: API is ACCESSIBLE")
        print("=" * 60)
        
        return df
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ FAILED: {e}")
        
        print("\n" + "=" * 60)
        print("Conclusion: API is NOT ACCESSIBLE")
        print("=" * 60)
        
        if "每小时" in error_msg or "hour" in error_msg.lower():
            print("Reason: Rate limited (frequency control)")
        elif "权限" in error_msg or "permission" in error_msg.lower():
            print("Reason: No permission (insufficient points)")
        else:
            print(f"Reason: Unknown error - {error_msg}")
        
        return None

def test_all_three_sources():
    """Test all three moneyflow sources"""
    print("\n" + "=" * 60)
    print("Test 2: Compare All Three Moneyflow Sources")
    print("=" * 60)
    
    ts_code = '603607.SH'
    start_date = '20250812'
    end_date = '20250822'
    
    # Test eastmoney
    print("\n[1/3] Testing eastmoney source...")
    eastmoney_source = EastmoneyMoneyflowSource()
    eastmoney_snapshots = eastmoney_source.get_moneyflow(ts_code, start_date, end_date)
    
    if eastmoney_snapshots:
        print(f"✅ Eastmoney: {len(eastmoney_snapshots)} records")
        eastmoney_df = pd.DataFrame([{
            'trade_date': s.trade_date,
            'main_net_inflow': s.main_net_inflow,
            'source': s.source
        } for s in eastmoney_snapshots])
    else:
        print("❌ Eastmoney: No data")
        eastmoney_df = pd.DataFrame()
    
    # Test tushare standard
    print("\n[2/3] Testing tushare standard source...")
    tushare_source = TushareMoneyflowSource()
    tushare_snapshots = tushare_source.get_moneyflow(ts_code, start_date, end_date)
    
    if tushare_snapshots:
        print(f"✅ Tushare Standard: {len(tushare_snapshots)} records")
        tushare_df = pd.DataFrame([{
            'trade_date': s.trade_date,
            'main_net_inflow': s.main_net_inflow,
            'source': s.source
        } for s in tushare_snapshots])
    else:
        print("❌ Tushare Standard: No data")
        tushare_df = pd.DataFrame()
    
    # Test tushare_ths
    print("\n[3/3] Testing tushare_ths source...")
    ths_source = TushareTHSMoneyflowSource()
    ths_snapshots = ths_source.get_moneyflow(ts_code, start_date, end_date)
    
    if ths_snapshots:
        print(f"✅ Tushare THS: {len(ths_snapshots)} records")
        ths_df = pd.DataFrame([{
            'trade_date': s.trade_date,
            'main_net_inflow': s.main_net_inflow,
            'source': s.source
        } for s in ths_snapshots])
    else:
        print("❌ Tushare THS: No data (likely rate limited)")
        ths_df = pd.DataFrame()
    
    # Merge and compare
    print("\n" + "=" * 60)
    print("Comparison: main_net_inflow (万元)")
    print("=" * 60)
    
    if not eastmoney_df.empty and not tushare_df.empty:
        comparison_df = eastmoney_df.merge(
            tushare_df,
            on='trade_date',
            how='outer',
            suffixes=('_eastmoney', '_tushare')
        )
        
        if not ths_df.empty:
            comparison_df = comparison_df.merge(
                ths_df,
                on='trade_date',
                how='outer'
            )
            comparison_df.rename(columns={'main_net_inflow': 'main_net_inflow_ths'}, inplace=True)
        
        comparison_df = comparison_df.sort_values('trade_date')
        print(comparison_df.to_string(index=False))
        
        # Calculate consistency
        print("\n" + "=" * 60)
        print("Consistency Analysis")
        print("=" * 60)
        
        if not ths_df.empty:
            # Check direction consistency
            eastmoney_direction = comparison_df['main_net_inflow_eastmoney'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
            tushare_direction = comparison_df['main_net_inflow_tushare'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
            ths_direction = comparison_df['main_net_inflow_ths'].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
            
            eastmoney_tushare_match = (eastmoney_direction == tushare_direction).sum()
            eastmoney_tushare_total = len(comparison_df)
            
            eastmoney_ths_match = (eastmoney_direction == ths_direction).sum()
            eastmoney_ths_total = len(comparison_df)
            
            tushare_ths_match = (tushare_direction == ths_direction).sum()
            tushare_ths_total = len(comparison_df)
            
            print(f"Eastmoney vs Tushare: {eastmoney_tushare_match}/{eastmoney_tushare_total} days match direction ({eastmoney_tushare_match/eastmoney_tushare_total*100:.1f}%)")
            print(f"Eastmoney vs THS: {eastmoney_ths_match}/{eastmoney_ths_total} days match direction ({eastmoney_ths_match/eastmoney_ths_total*100:.1f}%)")
            print(f"Tushare vs THS: {tushare_ths_match}/{tushare_ths_total} days match direction ({tushare_ths_match/tushare_ths_total*100:.1f}%)")
    else:
        print("Insufficient data for comparison")

def main():
    print("=" * 60)
    print("Tushare moneyflow_ths Final Test")
    print("=" * 60)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Direct API call
    df = test_direct_api_call()
    
    # Test 2: Compare all three sources
    test_all_three_sources()
    
    print("\n" + "=" * 60)
    print("Final Conclusion")
    print("=" * 60)
    
    if df is not None:
        print("✅ moneyflow_ths API is ACCESSIBLE")
        print("✅ Your token has 5000+ points")
        print("✅ The API can be used for offline research")
        print("⚠️  But frequency is limited (rate control)")
        print("⚠️  Not suitable for high-frequency usage")
    else:
        print("❌ moneyflow_ths API is NOT ACCESSIBLE")
        print("❌ Either rate limited or permission denied")
        print("✅ Continue using eastmoney + standard moneyflow")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()