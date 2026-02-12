#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 multi_source_adapter 的硬校验
"""
import sys
import logging
from logic.multi_source_adapter import get_adapter, DataQualityError

logging.basicConfig(level=logging.INFO)

def test_get_market_overview():
    """测试获取市场概览"""
    print("\n测试1: 获取市场概览")
    try:
        adapter = get_adapter()
        market = adapter.get_market_overview()
        print(f"✅ 成功: {market}")
    except DataQualityError as e:
        print(f"❌ 数据质量不合格: {e}")
    except Exception as e:
        print(f"⚠️ 其他异常: {e}")

def test_get_stock_quote():
    """测试获取股票报价"""
    print("\n测试2: 获取股票报价")
    try:
        adapter = get_adapter()
        quote = adapter.get_stock_quote("600519")
        print(f"✅ 成功: {quote}")
    except DataQualityError as e:
        print(f"❌ 数据质量不合格: {e}")
    except Exception as e:
        print(f"⚠️ 其他异常: {e}")

def test_get_limit_up_stocks():
    """测试获取涨停股票"""
    print("\n测试3: 获取涨停股票")
    try:
        adapter = get_adapter()
        limit_ups = adapter.get_limit_up_stocks(10)
        print(f"✅ 成功: {len(limit_ups) if limit_ups is not None else 0} 只股票")
    except DataQualityError as e:
        print(f"❌ 数据质量不合格: {e}")
    except Exception as e:
        print(f"⚠️ 其他异常: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试 multi_source_adapter 硬校验")
    print("=" * 60)
    
    test_get_market_overview()
    test_get_stock_quote()
    test_get_limit_up_stocks()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)