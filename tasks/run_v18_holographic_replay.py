#!/usr/bin/env python3
"""
V18全息回演 - 兼容性转发模块

⚠️ 弃用警告: 此模块已迁移至 tasks.backtest.behavior_replay
请使用新路径:
    python tasks/backtest/behavior_replay.py
"""

import warnings
import sys

warnings.warn(
    "run_v18_holographic_replay 已弃用，"
    "请使用 tasks.backtest.behavior_replay",
    DeprecationWarning,
    stacklevel=2
)

# 转发执行
if __name__ == '__main__':
    print("="*70)
    print("⚠️  模块迁移提示")
    print("="*70)
    print("此脚本已迁移至: tasks/backtest/behavior_replay.py")
    print("请使用新命令运行:")
    print("  python tasks/backtest/behavior_replay.py")
    print("="*70)
    print()
    
    # 转发到新模块
    import sys
    sys.path.insert(0, 'E:\\MyQuantTool')
    from tasks.backtest.behavior_replay import run_holographic_replay
    run_holographic_replay()