"""
Tushare Structure Test Script
Test targets: Examine pro object structure
"""

import tushare as ts

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def examine_pro_structure():
    """Examine pro object structure"""
    print("=" * 60)
    print("Tushare Pro Object Structure")
    print("=" * 60)
    
    # Get all attributes
    all_attrs = dir(pro)
    
    print(f"\nAll attributes ({len(all_attrs)}):")
    for attr in sorted(all_attrs):
        try:
            value = getattr(pro, attr)
            attr_type = type(value).__name__
            print(f"  {attr:30s} : {attr_type}")
        except Exception as e:
            print(f"  {attr:30s} : Error - {e}")
    
    print("\n" + "=" * 60)
    print("Testing direct API calls")
    print("=" * 60)
    
    # Test known APIs
    test_apis = [
        ('daily', {'ts_code': '603607.SH', 'start_date': '20260201', 'end_date': '20260206'}),
        ('moneyflow', {'ts_code': '603607.SH', 'start_date': '20260201', 'end_date': '20260206'}),
        ('ths_moneyflow', {'ts_code': '603607.SH', 'start_date': '20260201', 'end_date': '20260206'}),
    ]
    
    for api_name, params in test_apis:
        try:
            result = pro.query(api_name, **params)
            print(f"✅ {api_name}: Success ({len(result)} records)")
        except Exception as e:
            print(f"❌ {api_name}: Failed - {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    examine_pro_structure()