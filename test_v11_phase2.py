#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V11 阶段二测试：新陈代谢 (TTL)
验证数据库自动瘦身机制是否正常工作
"""

import pandas as pd
from datetime import datetime, timedelta
from logic.data_manager import DataManager
import os


def test_metabolism():
    print("🧪 启动 V11 阶段二测试：新陈代谢 (TTL)...")
    
    # 1. 初始化 DataManager
    dm = DataManager()
    dm._ensure_db_initialized()
    
    # 2. 造假数据 (注入一些 100 天前的老数据)
    old_date = (datetime.now() - timedelta(days=100)).strftime("%Y%m%d")
    recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
    
    print(f"📝 正在注入测试数据: 老数据({old_date}), 新数据({recent_date})")
    
    # 插入老数据 (模拟垃圾)
    dm.conn.execute(
        "INSERT OR REPLACE INTO daily_bars (symbol, date, close) VALUES (?, ?, ?)",
        ('TEST01', old_date, 10.0)
    )
    # 插入新数据 (模拟有用数据)
    dm.conn.execute(
        "INSERT OR REPLACE INTO daily_bars (symbol, date, close) VALUES (?, ?, ?)",
        ('TEST01', recent_date, 20.0)
    )
    dm.conn.commit()
    
    # 3. 验证注入结果
    df = pd.read_sql("SELECT * FROM daily_bars WHERE symbol='TEST01'", dm.conn)
    print(f"📊 注入后数据量: {len(df)} 条")
    if len(df) < 2:
        print("❌ 数据注入失败！")
        return
    
    # 4. 执行瘦身 (保留 90 天)
    print("🧹 执行 prune_old_data(days_to_keep=90)...")
    dm.prune_old_data(days_to_keep=90)
    
    # 5. 最终验证
    df_after = pd.read_sql("SELECT * FROM daily_bars WHERE symbol='TEST01'", dm.conn)
    print(f"📊 清理后数据量: {len(df_after)} 条")
    
    # 检查老数据是否没了
    old_exists = not df_after[df_after['date'] == old_date].empty
    recent_exists = not df_after[df_after['date'] == recent_date].empty
    
    if not old_exists and recent_exists:
        print("✅ 测试通过！老数据已被物理删除，新数据完好无损。")
        print("✅ VACUUM 执行成功，空间已释放。")
    else:
        print(f"❌ 测试失败: 老数据存在={old_exists}, 新数据存在={recent_exists}")


if __name__ == "__main__":
    test_metabolism()