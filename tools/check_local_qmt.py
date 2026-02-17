#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小验证脚本：测试本地QMT连接和交易日历
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 切换到项目根目录，确保配置能加载
os.chdir(PROJECT_ROOT)

try:
    from xtquant import xtdata
    XT_AVAILABLE = True
    print("✅ xtquant 模块可用")
except ImportError:
    XT_AVAILABLE = False
    print("❌ xtquant 未安装")
    sys.exit(1)


def test_local_connection():
    """
    测试本地QMT连接和交易日历
    """
    print("=" * 60)
    print("🧪 本地QMT连接测试")
    print("=" * 60)
    
    try:
        # 从配置获取端口
        import config.config_system as config
        config_instance = config.Config()
        port = config_instance.get('qmt_xtdata_port', 58610)
        
        print(f"📋 步骤1: 连接本地QMT xtdata服务 (端口: {port})")
        xtdata.connect(port=port)
        print("✅ 本地QMT连接成功")
        
        print(f"\n📋 步骤2: 获取上交所交易日历 (2025-01-01 ~ 2025-01-31)")
        dates = xtdata.get_trading_dates("SH", start_time="20250101", end_time="20250131")
        print(f"📊 交易日数量: {len(dates)}")
        print(f"📅 前5个交易日: {dates[:5] if dates else '无交易日'}")
        
        print(f"\n📋 步骤3: 获取指定股票历史数据 (300997.SZ, 2025-11-14)")
        # 先确保数据存在（如果不存在会自动下载）
        xtdata.download_history_data(
            stock_code="300997.SZ",
            period="tick",
            start_time="20251114",
            end_time="20251114"
        )
        print("✅ 历史数据下载完成")
        
        print("=" * 60)
        print("✅ 最小验证成功！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_local_connection()
    if not success:
        print("\n⚠️  请确认：")
        print("   1. QMT投研版或MiniQMT已启动")
        print("   2. xtdata端口配置正确")
        import config.config_system as config
        config_instance = config.Config()
        port = config_instance.get('qmt_xtdata_port', 58610)
        print(f"   3. 端口({port})无冲突")
        sys.exit(1)
    else:
        print("\n✅ 本地QMT连接测试通过！")
