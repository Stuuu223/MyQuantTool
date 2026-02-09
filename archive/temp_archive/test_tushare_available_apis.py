"""
Tushare 可用接口查询脚本
测试目标：查看 Tushare 支持哪些接口
"""

import tushare as ts

# 设置 token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"
ts.set_token(TOKEN)
pro = ts.pro_api()

def test_apis():
    """测试不同的接口名称"""
    print("=" * 60)
    print("Tushare 可用接口测试")
    print("=" * 60)
    
    # 尝试的接口名称列表
    api_names = [
        'ths_moneyflow',
        'ths_moneyflow_hk',
        'ths_daily',
        'stk_chip_cost',
        'stk_chip_distribution',
        'stk_chip_concentration',
        'moneyflow',
        'moneyflow_hsgt',
        'moneyflow_fund',
    ]
    
    for api_name in api_names:
        try:
            # 尝试获取接口
            api_func = getattr(pro, api_name)
            print(f"✅ {api_name}: 接口存在")
            
            # 尝试调用（可能需要参数）
            try:
                df = api_func(limit=1)
                print(f"   数据预览: {len(df)} 条记录")
            except Exception as e:
                print(f"   调用失败: {e}")
            
        except AttributeError:
            print(f"❌ {api_name}: 接口不存在")
        except Exception as e:
            print(f"❌ {api_name}: 错误 - {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_apis()