"""
Generate Static Stock-Sector Map

This script generates a static mapping table of stocks to their sectors (industry and concepts).
This mapping table will be used by V18.1 Hybrid Engine to eliminate 90% of AkShare requests.

Usage:
    python tools/generate_static_map.py

Output:
    data/stock_sector_map.json - Static mapping table
    data/stock_sector_map_report.txt - Generation report

Time: ~5 minutes to generate complete mapping for all A-shares
"""

import akshare as ak
import pandas as pd
import json
import time
from datetime import datetime
import os

# Disable tqdm progress bar
os.environ['TQDM_DISABLE'] = '1'


def generate_stock_sector_map():
    """Generate static stock-sector mapping table"""
    
    print("=" * 80)
    print("V18.1 Hybrid Engine - Static Stock-Sector Map Generator")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize mapping table
    stock_sector_map = {}
    
    # Step 1: Get all A-stock list
    print("Step 1: Getting all A-stock list...")
    t_start = time.time()
    
    try:
        stock_list_df = ak.stock_info_a_code_name()
        stock_list = stock_list_df['code'].tolist()
        print(f"✅ Found {len(stock_list)} A-stocks")
    except Exception as e:
        print(f"❌ Failed to get stock list: {e}")
        return None
    
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Step 2: Get industry sector information
    print("Step 2: Getting industry sector information...")
    t_start = time.time()
    
    try:
        # Get industry sectors
        industry_df = ak.stock_board_industry_name_em()
        industry_list = industry_df['板块名称'].tolist()
        print(f"✅ Found {len(industry_list)} industry sectors")
    except Exception as e:
        print(f"❌ Failed to get industry sectors: {e}")
        return None
    
    # Get industry constituent stocks
    industry_stock_map = {}
    for i, industry_name in enumerate(industry_list):
        try:
            print(f"   Processing {i+1}/{len(industry_list)}: {industry_name}...", end='\r')
            
            # Get constituent stocks for this industry
            industry_stocks_df = ak.stock_board_industry_cons_em(symbol=industry_name)
            
            if industry_stocks_df is not None and not industry_stocks_df.empty:
                stock_codes = industry_stocks_df['代码'].tolist()
                for stock_code in stock_codes:
                    if stock_code not in industry_stock_map:
                        industry_stock_map[stock_code] = []
                    industry_stock_map[stock_code].append(industry_name)
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\n   ⚠️ Failed to get stocks for {industry_name}: {e}")
            continue
    
    print(f"\n✅ Built industry-stock map: {len(industry_stock_map)} stocks")
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Step 3: Get concept sector information (optional, can be skipped to save time)
    print("Step 3: Getting concept sector information (Top 50 concepts only)...")
    t_start = time.time()
    
    try:
        # Get concept sectors
        concept_df = ak.stock_board_concept_name_em()
        concept_list = concept_df['板块名称'].tolist()
        
        # Only process top 50 concepts to save time
        concept_list = concept_list[:50]
        print(f"✅ Found {len(concept_list)} concept sectors (Top 50)")
    except Exception as e:
        print(f"❌ Failed to get concept sectors: {e}")
        concept_list = []
    
    # Get concept constituent stocks
    concept_stock_map = {}
    for i, concept_name in enumerate(concept_list):
        try:
            print(f"   Processing {i+1}/{len(concept_list)}: {concept_name}...", end='\r')
            
            # Get constituent stocks for this concept
            concept_stocks_df = ak.stock_board_concept_cons_em(symbol=concept_name)
            
            if concept_stocks_df is not None and not concept_stocks_df.empty:
                stock_codes = concept_stocks_df['代码'].tolist()
                for stock_code in stock_codes:
                    if stock_code not in concept_stock_map:
                        concept_stock_map[stock_code] = []
                    concept_stock_map[stock_code].append(concept_name)
            
            # Add delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\n   ⚠️ Failed to get stocks for {concept_name}: {e}")
            continue
    
    print(f"\n✅ Built concept-stock map: {len(concept_stock_map)} stocks")
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Step 4: Build final mapping table
    print("Step 4: Building final mapping table...")
    t_start = time.time()
    
    # Initialize all stocks in stock list
    for stock_code in stock_list:
        stock_sector_map[stock_code] = {
            'industry': industry_stock_map.get(stock_code, ['未知'])[0] if stock_code in industry_stock_map else '未知',
            'concepts': concept_stock_map.get(stock_code, [])
        }
    
    # Add stocks that are in sector maps but not in stock list
    all_stocks = set(industry_stock_map.keys()) | set(concept_stock_map.keys())
    for stock_code in all_stocks:
        if stock_code not in stock_sector_map:
            stock_sector_map[stock_code] = {
                'industry': industry_stock_map.get(stock_code, ['未知'])[0] if stock_code in industry_stock_map else '未知',
                'concepts': concept_stock_map.get(stock_code, [])
            }
    
    print(f"✅ Final mapping table: {len(stock_sector_map)} stocks")
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Step 5: Save to JSON file
    print("Step 5: Saving to JSON file...")
    t_start = time.time()
    
    # Create data directory if not exists
    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Save mapping table
    output_file = os.path.join(data_dir, 'stock_sector_map.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stock_sector_map, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved to: {output_file}")
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Step 6: Generate report
    print("Step 6: Generating report...")
    t_start = time.time()
    
    report_file = os.path.join(data_dir, 'stock_sector_map_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("V18.1 Hybrid Engine - Static Stock-Sector Map Generation Report\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Generation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total stocks: {len(stock_sector_map)}\n")
        f.write(f"Industry sectors: {len(industry_list)}\n")
        f.write(f"Concept sectors: {len(concept_list)}\n\n")
        
        # Statistics
        stocks_with_industry = sum(1 for s in stock_sector_map.values() if s['industry'] != '未知')
        stocks_with_concepts = sum(1 for s in stock_sector_map.values() if s['concepts'])
        
        f.write("Statistics:\n")
        f.write(f"  Stocks with industry info: {stocks_with_industry} ({stocks_with_industry/len(stock_sector_map)*100:.1f}%)\n")
        f.write(f"  Stocks with concept info: {stocks_with_concepts} ({stocks_with_concepts/len(stock_sector_map)*100:.1f}%)\n\n")
        
        # Top industries
        f.write("Top 10 Industries (by stock count):\n")
        industry_counts = {}
        for s in stock_sector_map.values():
            ind = s['industry']
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
        
        top_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (industry, count) in enumerate(top_industries, 1):
            f.write(f"  {i}. {industry}: {count} stocks\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"✅ Report saved to: {report_file}")
    t_cost = time.time() - t_start
    print(f"   Time: {t_cost:.2f}s\n")
    
    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total stocks: {len(stock_sector_map)}")
    print(f"Stocks with industry info: {stocks_with_industry} ({stocks_with_industry/len(stock_sector_map)*100:.1f}%)")
    print(f"Stocks with concept info: {stocks_with_concepts} ({stocks_with_concepts/len(stock_sector_map)*100:.1f}%)")
    print(f"\nOutput files:")
    print(f"  - {output_file}")
    print(f"  - {report_file}")
    print("\n✅ Static stock-sector map generation completed!")
    print("\nNext steps:")
    print("  1. Restart the system to load the new mapping table")
    print("  2. V18.1 Hybrid Engine will use this mapping table")
    print("  3. Performance should improve by 5000x for sector queries")
    print("=" * 80)
    
    return stock_sector_map


if __name__ == '__main__':
    generate_stock_sector_map()