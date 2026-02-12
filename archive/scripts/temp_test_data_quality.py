#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据质量硬校验
"""
import sys
import pandas as pd
from logic.data_quality_validator import validate_kline, validate_tick, DataQualityError

def test_validate_kline_success():
    """测试正常K线数据"""
    print("\n测试1: 正常K线数据")
    data = {
        'open': [10.0, 10.5, 11.0],
        'high': [10.2, 10.8, 11.2],
        'low': [9.8, 10.2, 10.8],
        'close': [10.1, 10.7, 11.1],
        'volume': [1000000, 1200000, 1500000]
    }
    df = pd.DataFrame(data)
    
    try:
        result = validate_kline(df, code="600000", period="1d")
        print(f"✅ 通过: 数据长度={len(result)}")
    except DataQualityError as e:
        print(f"❌ 失败: {e}")

def test_validate_kline_empty():
    """测试空DataFrame"""
    print("\n测试2: 空DataFrame")
    df = pd.DataFrame()
    
    try:
        validate_kline(df, code="600000", period="1d")
        print(f"❌ 应该抛出异常但没有")
    except DataQualityError as e:
        print(f"✅ 正确抛出异常: {e}")

def test_validate_kline_missing_fields():
    """测试缺少字段"""
    print("\n测试3: 缺少字段")
    data = {
        'open': [10.0, 10.5],
        'close': [10.1, 10.7]
        # 缺少 high, low, volume
    }
    df = pd.DataFrame(data)
    
    try:
        validate_kline(df, code="600000", period="1d")
        print(f"❌ 应该抛出异常但没有")
    except DataQualityError as e:
        print(f"✅ 正确抛出异常: {e}")

def test_validate_kline_invalid_price():
    """测试非法价格（价格<=0）"""
    print("\n测试4: 非法价格")
    data = {
        'open': [10.0, 0.0, 11.0],  # 第二个价格为0
        'high': [10.2, 10.8, 11.2],
        'low': [9.8, 10.2, 10.8],
        'close': [10.1, 10.7, 11.1],
        'volume': [1000000, 1200000, 1500000]
    }
    df = pd.DataFrame(data)
    
    try:
        validate_kline(df, code="600000", period="1d")
        print(f"❌ 应该抛出异常但没有")
    except DataQualityError as e:
        print(f"✅ 正确抛出异常: {e}")

def test_validate_kline_negative_volume():
    """测试负成交量"""
    print("\n测试5: 负成交量")
    data = {
        'open': [10.0, 10.5, 11.0],
        'high': [10.2, 10.8, 11.2],
        'low': [9.8, 10.2, 10.8],
        'close': [10.1, 10.7, 11.1],
        'volume': [1000000, -100, 1500000]  # 第二个成交量为负
    }
    df = pd.DataFrame(data)
    
    try:
        validate_kline(df, code="600000", period="1d")
        print(f"❌ 应该抛出异常但没有")
    except DataQualityError as e:
        print(f"✅ 正确抛出异常: {e}")

def test_validate_kline_none():
    """测试None输入"""
    print("\n测试6: None输入")
    try:
        validate_kline(None, code="600000", period="1d")
        print(f"❌ 应该抛出异常但没有")
    except DataQualityError as e:
        print(f"✅ 正确抛出异常: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试数据质量硬校验")
    print("=" * 60)
    
    test_validate_kline_success()
    test_validate_kline_empty()
    test_validate_kline_missing_fields()
    test_validate_kline_invalid_price()
    test_validate_kline_negative_volume()
    test_validate_kline_none()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
