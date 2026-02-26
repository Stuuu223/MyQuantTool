#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法扫描器适配器 (Unified Warfare Scanner Adapter)

功能：
1. 将统一战法核心（UnifiedWarfareCore）接入FullMarketScanner三漏斗体系
2. 作为Level 2/3的补充检测器，提供更细粒度的战法事件
3. 保持与现有EventDriven系统的兼容性

架构位置：
FullMarketScanner (Level 1-3漏斗)
    ↓
UnifiedWarfareScannerAdapter (战法事件层)
    ↓
UnifiedWarfareCore (多战法检测)
    ↓
HalfwayBreakoutDetector / LeaderCandidateDetector / ...

Author: AI Project Director
Version: V1.0
Date: 2026-02-17
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from logic.strategies.unified_warfare_core import get_unified_warfare_core
# 【CTO P0抢修】移除不存在的event_detector依赖
# EventType未实际使用，直接删除导入
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WarfareScanResult:
    """战法扫描结果"""
    stock_code: str
    timestamp: datetime
    events: List[Dict[str, Any]]
    primary_warfare: Optional[str] = None  # 主要战法类型
    confidence: float = 0.0
    

def scan_stock_for_warfare(
    stock_code: str,
    price_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> WarfareScanResult:
    """
    扫描单只股票的战法事件
    
    Args:
        stock_code: 股票代码
        price_data: 价格数据（包含当前价、历史价等）
        context: 上下文信息
        
    Returns:
        战法扫描结果
    """
    # 获取统一战法核心
    warfare_core = get_unified_warfare_core()
    
    # 构建tick_data格式
    tick_data = {
        'stock_code': stock_code,
        'datetime': datetime.now(),
        'price': price_data.get('current_price', 0),
        'volume': price_data.get('volume', 0),
        'amount': price_data.get('amount', 0),
        'open': price_data.get('open', 0),
        'high': price_data.get('high', 0),
        'low': price_data.get('low', 0),
        'prev_close': price_data.get('prev_close', 0),
    }
    
    # 构建上下文
    if context is None:
        context = {}
    
    # 添加价格历史
    if 'price_history' not in context and 'kline_data' in price_data:
        # 从K线数据提取价格历史
        kline = price_data['kline_data']
        context['price_history'] = [k.get('close', 0) for k in kline]
        context['volume_history'] = [k.get('volume', 0) for k in kline]
    
    # 使用统一战法核心检测事件
    events = warfare_core.process_tick(tick_data, context)
    
    # 确定主要战法（置信度最高的）
    primary_warfare = None
    max_confidence = 0.0
    
    for event in events:
        if event['confidence'] > max_confidence:
            max_confidence = event['confidence']
            primary_warfare = event['event_type']
    
    result = WarfareScanResult(
        stock_code=stock_code,
        timestamp=datetime.now(),
        events=events,
        primary_warfare=primary_warfare,
        confidence=max_confidence
    )
    
    return result


def filter_warfare_signals(
    results: List[WarfareScanResult],
    min_confidence: float = 0.3,
    warfare_types: Optional[List[str]] = None
) -> List[WarfareScanResult]:
    """
    过滤战法信号
    
    Args:
        results: 扫描结果列表
        min_confidence: 最小置信度
        warfare_types: 指定的战法类型列表（如['halfway_breakout', 'leader_candidate']）
        
    Returns:
        过滤后的结果
    """
    filtered = []
    
    for result in results:
        # 检查置信度
        if result.confidence < min_confidence:
            continue
        
        # 检查战法类型
        if warfare_types and result.primary_warfare not in warfare_types:
            continue
        
        filtered.append(result)
    
    # 按置信度排序
    filtered.sort(key=lambda x: x.confidence, reverse=True)
    
    return filtered


def format_warfare_report(result: WarfareScanResult) -> str:
    """
    格式化战法扫描报告
    
    Args:
        result: 扫描结果
        
    Returns:
        格式化的报告字符串
    """
    lines = []
    lines.append(f"🎯 {result.stock_code} 战法扫描结果")
    lines.append(f"   主要战法: {result.primary_warfare or '无'}")
    lines.append(f"   置信度: {result.confidence:.2f}")
    lines.append(f"   检测到 {len(result.events)} 个事件:")
    
    for event in result.events:
        lines.append(f"   - {event['event_type']}: {event['description']} (置信度:{event['confidence']:.2f})")
    
    return "\n".join(lines)


# ==================== 与FullMarketScanner集成的示例函数 ====================

def integrate_with_fullmarket_scanner(
    scanner_results: List[Dict[str, Any]],
    enable_warfare_detection: bool = True
) -> List[Dict[str, Any]]:
    """
    将战法检测集成到FullMarketScanner的结果中
    
    Args:
        scanner_results: FullMarketScanner的扫描结果
        enable_warfare_detection: 是否启用战法检测
        
    Returns:
        增强后的扫描结果（添加战法事件字段）
    """
    if not enable_warfare_detection:
        return scanner_results
    
    enhanced_results = []
    
    for result in scanner_results:
        stock_code = result.get('code', '')
        
        # 构建价格数据
        price_data = {
            'current_price': result.get('price', 0),
            'volume': result.get('volume', 0),
            'amount': result.get('amount', 0),
            'open': result.get('open', 0),
            'high': result.get('high', 0),
            'low': result.get('low', 0),
            'prev_close': result.get('prev_close', 0),
        }
        
        # 扫描战法事件
        warfare_result = scan_stock_for_warfare(stock_code, price_data)
        
        # 将战法结果合并到原始结果中
        enhanced_result = result.copy()
        enhanced_result['warfare_events'] = warfare_result.events
        enhanced_result['primary_warfare'] = warfare_result.primary_warfare
        enhanced_result['warfare_confidence'] = warfare_result.confidence
        
        enhanced_results.append(enhanced_result)
        
        # 如果有高置信度战法事件，记录日志
        if warfare_result.confidence >= 0.5:
            logger.info(f"🎯 [战法检测] {stock_code} 发现高置信度信号: {warfare_result.primary_warfare} ({warfare_result.confidence:.2f})")
    
    return enhanced_results


# ==================== 与EventDriven集成的示例函数 ====================

def on_tick_event(
    stock_code: str,
    tick_data: Dict[str, Any],
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Tick事件处理器（供EventDriven系统调用）
    
    Args:
        stock_code: 股票代码
        tick_data: Tick数据
        context: 上下文
        
    Returns:
        如果检测到战法事件，返回事件详情；否则返回None
    """
    # 获取统一战法核心
    warfare_core = get_unified_warfare_core()
    
    # 处理tick
    events = warfare_core.process_tick(tick_data, context)
    
    if not events:
        return None
    
    # 选择置信度最高的事件
    best_event = max(events, key=lambda x: x['confidence'])
    
    if best_event['confidence'] < 0.3:  # 阈值过滤
        return None
    
    return {
        'stock_code': stock_code,
        'event_type': best_event['event_type'],
        'confidence': best_event['confidence'],
        'description': best_event['description'],
        'data': best_event['data'],
        'timestamp': best_event['timestamp'],
    }


if __name__ == "__main__":
    # 测试适配器
    print("🧪 统一战法扫描器适配器测试")
    print("="*80)
    
    # 模拟FullMarketScanner输出
    mock_scanner_results = [
        {
            'code': '300750',
            'price': 205.0,
            'volume': 1200000,
            'open': 200.0,
            'high': 208.0,
            'low': 199.0,
            'prev_close': 200.0,
        },
        {
            'code': '000001',
            'price': 15.2,
            'volume': 500000,
            'open': 15.0,
            'high': 15.3,
            'low': 14.9,
            'prev_close': 15.0,
        }
    ]
    
    # 测试集成
    enhanced = integrate_with_fullmarket_scanner(mock_scanner_results)
    
    for result in enhanced:
        print(f"\n{result['code']}:")
        print(f"   价格: {result['price']}")
        print(f"   战法事件: {result.get('warfare_events', [])}")
        print(f"   主要战法: {result.get('primary_warfare', '无')}")
        print(f"   置信度: {result.get('warfare_confidence', 0):.2f}")
    
    print("\n✅ 测试完成")
