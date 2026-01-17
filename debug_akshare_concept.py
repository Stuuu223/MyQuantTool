"""
调试 AkShare 个股信息 API

检查 ak.stock_individual_info_em() 返回的数据格式

Author: iFlow CLI
Date: 2026-01-16
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import akshare as ak


def debug_stock_info():
    """调试个股信息 API"""
    code = '600519'  # 贵州茅台
    
    print(f"正在获取股票 {code} 的详细信息...")
    stock_info = ak.stock_individual_info_em(symbol=code)
    
    print(f"\n数据类型: {type(stock_info)}")
    print(f"数据形状: {stock_info.shape}")
    print(f"数据列: {stock_info.columns.tolist()}")
    
    print(f"\n前10行数据:")
    print(stock_info.head(10))
    
    print(f"\n所有数据:")
    print(stock_info)
    
    # 转换为字典
    info_dict = dict(zip(stock_info['item'], stock_info['value']))
    
    print(f"\n转换为字典:")
    for key, value in info_dict.items():
        print(f"  {key}: {value}")
    
    # 检查关键字段
    print(f"\n关键字段检查:")
    print(f"  所属行业: {info_dict.get('所属行业', 'N/A')}")
    print(f"  所属行业代码: {info_dict.get('所属行业代码', 'N/A')}")
    print(f"  概念: {info_dict.get('概念', 'N/A')}")
    print(f"  行业: {info_dict.get('行业', 'N/A')}")
    print(f"  行业分类: {info_dict.get('行业分类', 'N/A')}")


if __name__ == "__main__":
    debug_stock_info()