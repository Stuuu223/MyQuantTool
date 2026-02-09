import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime

# Configuration
CSV_PATH = Path("data/tracking/scan_performance.csv")
RED_FLAG_DROP_THRESHOLD = -0.04  # -4%

def get_realtime_price(code_with_suffix):
    """
    Fetch real-time/closing data using AkShare
    code_with_suffix: e.g., '002514.SZ' -> '002514' for akshare
    """
    symbol = code_with_suffix.split('.')[0]
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == symbol]
        if not row.empty:
            return {
                "open": float(row.iloc[0]['今开']),
                "high": float(row.iloc[0]['最高']),
                "low": float(row.iloc[0]['最低']),
                "close": float(row.iloc[0]['最新价']),
                "pct": float(row.iloc[0]['涨跌幅']) / 100.0
            }
    except Exception as e:
        print(f"Error fetching {code_with_suffix}: {e}")
    return None

def verify_performance():
    print("Starting T+1 Performance Verification...")
    
    if not CSV_PATH.exists():
        print(f"File not found: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    success_count = 0
    fail_count = 0
    core_failure = False
    
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("-" * 60)
    print(f"{'Code':<10} {'Name':<10} {'Init':<8} {'Close':<8} {'Chg%':<8} {'Result'}")
    print("-" * 60)

    for index, row in df.iterrows():
        code = row['code']
        if code == "000000.SZ":
            continue  # Skip placeholder
        
        # 1. Fetch data
        market_data = get_realtime_price(code)
        if not market_data:
            print(f"{code:<10} Data Unavailable")
            continue

        # 2. Update data
        t1_close = market_data['close']
        initial = row['initial_price']
        
        # Calculate change percentage
        if initial > 0:
            pct_change = (t1_close - initial) / initial
        else:
            pct_change = market_data['pct']  # Fallback to daily pct
        
        # 3. Determine result
        result = "WIN" if pct_change > 0 else "LOSS"
        if pct_change == 0:
            result = "DRAW"
        
        # Update DataFrame
        df.at[index, 't1_open'] = market_data['open']
        df.at[index, 't1_high'] = market_data['high']
        df.at[index, 't1_low'] = market_data['low']
        df.at[index, 't1_close'] = t1_close
        df.at[index, 'pct_change'] = round(pct_change * 100, 2)
        df.at[index, 'result'] = result

        # 4. Print row
        print(f"{code:<10} {row['name']:<10} {initial:<8.2f} {t1_close:<8.2f} {pct_change*100:>6.2f}% {result}")

        # 5. Statistics and red flag check
        if result == "WIN":
            success_count += 1
        elif result == "LOSS":
            fail_count += 1
        
        # Red flag check: 002514 crashes
        if code == "002514.SZ" and pct_change < RED_FLAG_DROP_THRESHOLD:
            core_failure = True
            print(f"   CRITICAL ALERT: Core Stock {code} dropped < -4%!")

    # Save updates
    df.to_csv(CSV_PATH, index=False)
    print("-" * 60)
    print(f"Updated data saved to {CSV_PATH}")

    # --- Decision Logic ---
    print("\nFINAL DECISION MATRIX")
    print("=" * 30)
    
    total_valid = success_count + fail_count
    if total_valid == 0:
        print("Waiting for data...")
        return

    win_rate = success_count / total_valid

    # Decision output
    if core_failure:
        print("Result: CRITICAL FAILURE (Core Crash)")
        print("Action: Immediate rollback to v9.4.5 (git checkout v9.4.5)")
    elif fail_count >= 3:
        print("Result: GROUP FAILURE (System Failure)")
        print("Action: System cannot beat random chance, need emergency parameter adjustment")
    elif win_rate >= 0.75:
        print("Result: EXCELLENT")
        print("Action: Keep current version, continue monitoring for 1 week")
    elif win_rate >= 0.5:
        print("Result: GOOD")
        print("Action: Prepare for Phase 3 optimization")
    else:
        print("Result: MARGINAL")
        print("Action: Win rate < 50%, need parameter tuning")

if __name__ == "__main__":
    verify_performance()
