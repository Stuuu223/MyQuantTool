"""
测试 xtdata 是否能获取数据
"""
import os
import sys

# 添加项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("="*80)
print("测试 xtdata 数据获取")
print("="*80)

try:
    from xtquant import xtdata
    from logic.code_converter import CodeConverter
    
    converter = CodeConverter()
    stock_code = "300997"
    qmt_code = converter.to_qmt(stock_code)
    
    print(f"\n股票代码: {stock_code} -> QMT代码: {qmt_code}")
    
    # 测试获取历史数据
    from datetime import datetime, timedelta
    start_time = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d 09:30:00')
    end_time = datetime.now().strftime('%Y%m%d 15:00:00')
    
    print(f"\n尝试获取历史数据...")
    print(f"   开始时间: {start_time}")
    print(f"   结束时间: {end_time}")
    
    df = xtdata.get_market_data(
        stock_list=[qmt_code],
        period='1d',
        start_time=start_time,
        end_time=end_time,
        dividend_type='front'
    )
    
    if df is None:
        print(f"   ❌ 返回 None")
    elif qmt_code not in df:
        print(f"   ❌ 代码 {qmt_code} 不在返回数据中")
        print(f"   返回的代码列表: {list(df.keys())}")
    else:
        print(f"   ✅ 成功获取数据")
        print(f"   数据形状: {df[qmt_code].shape}")
        print(f"   最新数据:\n{df[qmt_code].tail(3)}")
        
except Exception as e:
    print(f"\n❌ 发生错误:")
    print(f"   错误类型: {type(e).__name__}")
    print(f"   错误详情: {repr(e)}")
    
    import traceback
    print("\n完整堆栈:")
    traceback.print_exc()

print("\n" + "="*80)