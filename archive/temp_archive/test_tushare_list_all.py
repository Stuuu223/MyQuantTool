"""
Tushare List All APIs Script
Test targets: List all available APIs
"""

import tushare as ts

# Set token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def list_all_apis():
    """List all available APIs"""
    print("=" * 60)
    print("Tushare Available APIs List")
    print("=" * 60)
    
    # Get all attributes of pro object
    all_attrs = dir(pro)
    
    # Filter for methods (callable and not starting with _)
    api_methods = [attr for attr in all_attrs if callable(getattr(pro, attr)) and not attr.startswith('_')]
    
    print(f"Found {len(api_methods)} API methods:")
    for i, api in enumerate(api_methods, 1):
        print(f"{i:3d}. {api}")
    
    print("\n" + "=" * 60)
    print("Searching for moneyflow/chip/ths related APIs")
    print("=" * 60)
    
    # Search for specific APIs
    keywords = ['money', 'flow', 'chip', 'ths', 'stk']
    
    for keyword in keywords:
        found = [api for api in api_methods if keyword in api.lower()]
        print(f"\nAPIs containing '{keyword}':")
        for api in found:
            print(f"  - {api}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    list_all_apis()
