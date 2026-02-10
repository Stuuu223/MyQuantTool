#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接诊断Redis中存储的数据格式

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.database_manager import DatabaseManager
from datetime import datetime

db_manager = DatabaseManager()
db_manager._init_redis()

# 测试股票代码
test_code = '000001.SZ'
today = datetime.now().strftime("%Y%m%d")
key = f"auction:{today}:{test_code}"

print("=" * 80)
print("🔍 直接诊断Redis数据格式")
print("=" * 80)
print(f"📌 测试Key: {key}")

# 直接从Redis获取原始数据
raw_data = db_manager._redis_client.get(key)

print(f"\n📊 原始数据类型: {type(raw_data)}")

if raw_data:
    print(f"📊 原始数据长度: {len(raw_data)}")
    print(f"📊 原始数据前100字符: {raw_data[:100]}")
    
    # 尝试解析
    try:
        if isinstance(raw_data, str):
            print(f"📊 数据是字符串，尝试json.loads...")
            parsed_data = json.loads(raw_data)
            print(f"✅ 解析成功，类型: {type(parsed_data)}")
            print(f"📊 解析后数据: {parsed_data}")
        elif isinstance(raw_data, dict):
            print(f"📊 数据是dict，直接使用: {raw_data}")
        else:
            print(f"📊 数据类型未知: {type(raw_data)}")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
else:
    print("❌ Redis中没有找到数据")

print("=" * 80)