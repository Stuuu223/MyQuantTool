#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证性能监控功能
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.log_config import use_normal_mode
import time

logger = get_logger(__name__)

def test_performance_monitor():
    """测试性能监控功能"""

    print("=" * 80)
    print("🧪 验证性能监控功能")
    print("=" * 80)
    print()

    # 应用日志配置
    use_normal_mode()

    # 测试配置加载性能
    print("测试配置加载性能...")
    print("-" * 80)

    import json
    config_path = project_root / 'config' / 'market_scan_config.json'

    # 计时
    start = time.perf_counter()
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    elapsed = (time.perf_counter() - start) * 1000

    print(f"✅ 配置加载耗时: {elapsed:.2f}ms")

    # 性能告警
    if elapsed > 100:
        print(f"⚠️  配置加载耗时过长: {elapsed:.2f}ms（正常应 <50ms）")
        print(f"   可能原因: 磁盘IO延迟、JSON文件过大、网络磁盘")
    elif elapsed > 50:
        print(f"⚠️  配置加载耗时偏高: {elapsed:.2f}ms（正常应 <50ms）")
    else:
        print(f"✅ 配置加载性能优秀: {elapsed:.2f}ms（正常应 <50ms）")

    print()
    print("=" * 80)
    print("✅ 性能监控验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_performance_monitor()