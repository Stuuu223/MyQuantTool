#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输出格式化器 - 统一管理状态显示格式

功能：
- 从配置文件读取格式模板
- 提供统一的格式化接口
- 支持动态配置，避免硬编码

Author: iFlow CLI
Version: V1.0
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from functools import lru_cache  # 🔥 修复：添加缺失的导入

logger = logging.getLogger(__name__)

OUTPUT_FORMAT_PATH = Path(__file__).resolve().parents[1] / "config" / "output_format.json"


@lru_cache(maxsize=1)
def _load_output_format() -> Dict[str, str]:
    """加载输出格式配置（带缓存）"""
    if not OUTPUT_FORMAT_PATH.exists():
        logger.warning(f"⚠️  输出格式配置文件不存在: {OUTPUT_FORMAT_PATH}")
        # 返回默认格式
        return {
            "status_line": "✅ 机会池: {opp:2d} | 观察池: {watch:2d} | 黑名单: {black:2d}",
            "metrics_line": "📈 系统置信度: {conf:.1%} | 💰 今日建议最大总仓位: {pos:.1%}",
            "timing_line": "⏰ 扫描耗时: {time:.1f}s"
        }
    
    with OUTPUT_FORMAT_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)


def format_scan_result(result: Dict[str, Any], scan_time: float = 0.0) -> str:
    """
    格式化扫描结果输出
    
    Args:
        result: 扫描结果字典
        scan_time: 扫描耗时（秒）
    
    Returns:
        格式化后的字符串
    """
    formats = _load_output_format()
    
    # 状态行
    status = formats['status_line'].format(
        opp=len(result.get('opportunities', [])),
        watch=len(result.get('watchlist', [])),
        black=len(result.get('blacklist', []))
    )
    
    # 指标行
    metrics = formats['metrics_line'].format(
        conf=result.get('confidence', 0.0),
        pos=result.get('position_limit', 0.0)
    )
    
    # 时机行（如果有）
    timing = ""
    if 'timing_line' in formats and scan_time > 0:
        timing = formats['timing_line'].format(time=scan_time)
        timing = f"\n{timing}"
    
    return f"{status}\n{metrics}{timing}"


def format_level_stats(level_name: str, count_in: int, count_out: int, elapsed: float) -> str:
    """
    格式化级别统计输出
    
    Args:
        level_name: 级别名称（如 "Level 1", "Level 2"）
        count_in: 输入数量
        count_out: 输出数量
        elapsed: 耗时（秒）
    
    Returns:
        格式化后的字符串
    """
    return f"✅ {level_name} 完成: {count_in} → {count_out} 只 (耗时: {elapsed:.1f}秒)"


def format_summary_header() -> str:
    """
    格式化摘要表头
    
    Returns:
        格式化后的表头字符串
    """
    return "================================================================================\n📊 扫描结果统计\n================================================================================"