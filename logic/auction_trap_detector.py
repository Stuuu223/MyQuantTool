#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价诡多检测器 (Phase3 第1周)

功能：
1. 检测“竞价高开+开盘砸盘”诡多模式
2. 检测“纾价爆量+尾盘回落”诡多模式
3. 检测“竞价平开+开盘拉升”正常模式

检测规则：
- 竞价高开+开盘砸盘: 竞价涨幅>3% + 开盘5分钟内跌幅>2%
- 纾价爆量+尾盘回落: 纾价量比>2 + 尾盘回落>1%
- 纾价平开+开盘拉升: 纾价涨幅<1% + 开盘5分钟涨幅>3%

使用方法：
    from logic.auction_trap_detector import AuctionTrapDetector
    
    detector = AuctionTrapDetector()
    result = detector.detect(auction_data, open_data)
    
    if result['trap_type'] != 'NORMAL':
        print(f"发现诡多: {result['trap_type']}")
        print(f"风险级别: {result['risk_level']}")
        print(f"置信度: {result['confidence']*100:.0f}%")
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger

logger = get_logger(__name__)


class TrapType(Enum):
    """诡多类型枚举"""
    NORMAL = "NORMAL"  # 正常
    AUC_HIGH_OPEN_DUMP = "AUC_HIGH_OPEN_DUMP"  # 纾价高开+开盘砸盘
    AUC_BOOM_TAIL_DROP = "AUC_BOOM_TAIL_DROP"  # 纾价爆量+尾盘回落
    AUC_FLAT_OPEN_PUMP = "AUC_FLAT_OPEN_PUMP"  # 纾价平开+开盘拉升


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "🟢 低"  # 低风险
    MEDIUM = "🟡 中"  # 中风险
    HIGH = "🔴 高"  # 高风险


@dataclass
class AuctionData:
    """纾价数据类"""
    code: str
    name: str
    auction_price: float  # 纾价价格
    prev_close: float  # 昨收
    auction_change: float  # 纾价涨幅
    auction_volume: int  # 纾价量（手）
    auction_amount: float  # 纾价金额（元）
    volume_ratio: float  # 量比
    buy_orders: int  # 买单量
    sell_orders: int  # 卖单量
    timestamp: str  # 时间戳


@dataclass
class OpenData:
    """开盘数据类"""
    code: str
    open_price: float  # 开盘价
    high_5min: float  # 开盘5分钟最高价
    low_5min: float  # 开盘5分钟最低价
    close_5min: float  # 开盘5分钟收盘价
    volume_5min: int  # 开盘5分钟成交量
    tail_drop: float  # 尾盘回落幅度（最高-收盘）
    timestamp: str  # 时间戳


@dataclass
class DetectionResult:
    """检测结果类"""
    code: str
    name: str
    trap_type: TrapType  # 诡多类型
    risk_level: RiskLevel  # 风险级别
    confidence: float  # 置信度 (0-1)
    auction_change: float  # 纾价涨幅
    open_change: float  # 开盘涨幅
    volume_ratio: float  # 量比
    tail_drop: float  # 尾盘回落
    signals: List[str]  # 信号列表
    timestamp: str  # 检测时间


class AuctionTrapDetector:
    """
    纾价诡多检测器
    
    检测纾价阶段的异常模式，识别诡多陷阱
    """
    
    # 检测阈值配置
    THRESHOLDS = {
        # 纾价高开+开盘砸盘
        'auc_high_open': 0.03,  # 纾价涨幅 > 3%
        'open_dump': -0.02,  # 开盘5分钟跌幅 > 2%
        
        # 纾价爆量+尾盘回落
        'auc_volume_ratio': 2.0,  # 量比 > 2.0
        'tail_drop': 0.01,  # 尾盘回落 > 1%
        
        # 纾价平开+开盘拉升
        'auc_flat_open': 0.01,  # 纾价涨幅 < 1%
        'open_pump': 0.03,  # 开盘5分钟涨幅 > 3%
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化检测器
        
        Args:
            config: 自定义配置（可覆盖默认阈值）
        """
        if config:
            self.THRESHOLDS.update(config)
        
        logger.info("✅ 纾价诡多检测器初始化成功")
    
    def _detect_high_open_dump(self, auction_data: AuctionData, open_data: OpenData) -> Optional[DetectionResult]:
        """
        检测“纾价高开+开盘砸盘”模式
        
        特征：
        - 纾价高开 > 3%
        - 开盘5分钟内砸盘 > 2%
        - 纾价放量（量比 > 1.5）
        
        Returns:
            检测结果，未检测到返回None
        """
        # 计算开盘变化
        open_change = (open_data.close_5min - open_data.open_price) / open_data.open_price
        
        # 检测条件
        is_high_open = auction_data.auction_change > self.THRESHOLDS['auc_high_open']
        is_dump = open_change < self.THRESHOLDS['open_dump']
        has_volume = auction_data.volume_ratio > 1.5
        
        if is_high_open and is_dump:
            # 计算置信度（80-95%）
            confidence = 0.8
            if has_volume:
                confidence += 0.1  # 放量确认 +10%
            if open_change < -0.03:
                confidence += 0.05  # 大幅砸盘 +5%
            
            # 确定风险级别
            if auction_data.auction_change > 0.05 and open_change < -0.03:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.MEDIUM
            
            # 生成信号
            signals = []
            signals.append(f"纾价高开 {auction_data.auction_change*100:.2f}%")
            signals.append(f"开盘5分钟砸盘 {-open_change*100:.2f}%")
            if has_volume:
                signals.append(f"纾价放量 {auction_data.volume_ratio:.1f}倍")
            
            return DetectionResult(
                code=auction_data.code,
                name=auction_data.name,
                trap_type=TrapType.AUC_HIGH_OPEN_DUMP,
                risk_level=risk_level,
                confidence=min(confidence, 0.95),
                auction_change=auction_data.auction_change,
                open_change=open_change,
                volume_ratio=auction_data.volume_ratio,
                tail_drop=open_data.tail_drop,
                signals=signals,
                timestamp=open_data.timestamp
            )
        
        return None
    
    def _detect_boom_tail_drop(self, auction_data: AuctionData, open_data: OpenData) -> Optional[DetectionResult]:
        """
        检测“纾价爆量+尾盘回落”模式
        
        特征：
        - 纾价量比 > 2.0
        - 尾盘回落 > 1%
        - 纾价涨幅适中（1-5%）
        
        Returns:
            检测结果，未检测到返回None
        """
        # 检测条件
        is_boom = auction_data.volume_ratio > self.THRESHOLDS['auc_volume_ratio']
        is_drop = open_data.tail_drop > self.THRESHOLDS['tail_drop']
        is_moderate_change = 0.01 < auction_data.auction_change < 0.05
        
        if is_boom and is_drop:
            # 计算置信度（70-85%）
            confidence = 0.7
            if is_moderate_change:
                confidence += 0.05  # 适中涨幅 +5%
            if auction_data.volume_ratio > 3.0:
                confidence += 0.05  # 爆量确认 +5%
            if open_data.tail_drop > 0.02:
                confidence += 0.05  # 大幅回落 +5%
            
            # 确定风险级别
            if auction_data.volume_ratio > 3.0 and open_data.tail_drop > 0.02:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # 生成信号
            signals = []
            signals.append(f"纾价爆量 {auction_data.volume_ratio:.1f}倍")
            signals.append(f"尾盘回落 {open_data.tail_drop*100:.2f}%")
            if is_moderate_change:
                signals.append(f"纾价涨幅适中 {auction_data.auction_change*100:.2f}%")
            
            return DetectionResult(
                code=auction_data.code,
                name=auction_data.name,
                trap_type=TrapType.AUC_BOOM_TAIL_DROP,
                risk_level=risk_level,
                confidence=min(confidence, 0.85),
                auction_change=auction_data.auction_change,
                open_change=(open_data.close_5min - open_data.open_price) / open_data.open_price,
                volume_ratio=auction_data.volume_ratio,
                tail_drop=open_data.tail_drop,
                signals=signals,
                timestamp=open_data.timestamp
            )
        
        return None
    
    def _detect_flat_open_pump(self, auction_data: AuctionData, open_data: OpenData) -> Optional[DetectionResult]:
        """
        检测“纾价平开+开盘拉升”模式（正常模式）
        
        特征：
        - 纾价涨幅 < 1%
        - 开盘5分钟涨幅 > 3%
        - 纾价放量适中（1.5-2.5）
        
        Returns:
            检测结果，未检测到返回None
        """
        # 计算开盘变化
        open_change = (open_data.close_5min - open_data.open_price) / open_data.open_price
        
        # 检测条件
        is_flat_open = abs(auction_data.auction_change) < self.THRESHOLDS['auc_flat_open']
        is_pump = open_change > self.THRESHOLDS['open_pump']
        has_moderate_volume = 1.5 < auction_data.volume_ratio < 2.5
        
        if is_flat_open and is_pump:
            # 计算置信度（60-75%）
            confidence = 0.6
            if has_moderate_volume:
                confidence += 0.05  # 适中放量 +5%
            if open_change > 0.05:
                confidence += 0.05  # 大幅拉升 +5%
            if open_data.tail_drop < 0.005:
                confidence += 0.05  # 尾盘稳定 +5%
            
            # 确定风险级别（这是正常模式）
            risk_level = RiskLevel.LOW
            
            # 生成信号
            signals = []
            signals.append(f"纾价平开 {auction_data.auction_change*100:.2f}%")
            signals.append(f"开盘5分钟拉升 {open_change*100:.2f}%")
            if has_moderate_volume:
                signals.append(f"纾价放量适中 {auction_data.volume_ratio:.1f}倍")
            
            return DetectionResult(
                code=auction_data.code,
                name=auction_data.name,
                trap_type=TrapType.AUC_FLAT_OPEN_PUMP,
                risk_level=risk_level,
                confidence=min(confidence, 0.75),
                auction_change=auction_data.auction_change,
                open_change=open_change,
                volume_ratio=auction_data.volume_ratio,
                tail_drop=open_data.tail_drop,
                signals=signals,
                timestamp=open_data.timestamp
            )
        
        return None
    
    def detect(self, auction_data: Dict[str, Any], open_data: Dict[str, Any]) -> DetectionResult:
        """
        检测纾价诡多模式
        
        Args:
            auction_data: 纾价数据字典
            open_data: 开盘数据字典
        
        Returns:
            检测结果
        """
        # 转换为数据类
        auction = AuctionData(
            code=auction_data.get('code', ''),
            name=auction_data.get('name', ''),
            auction_price=auction_data.get('auction_price', 0),
            prev_close=auction_data.get('prev_close', 0),
            auction_change=auction_data.get('auction_change', 0),
            auction_volume=auction_data.get('auction_volume', 0),
            auction_amount=auction_data.get('auction_amount', 0),
            volume_ratio=auction_data.get('volume_ratio', 0),
            buy_orders=auction_data.get('buy_orders', 0),
            sell_orders=auction_data.get('sell_orders', 0),
            timestamp=auction_data.get('timestamp', '')
        )
        
        open_d = OpenData(
            code=open_data.get('code', ''),
            open_price=open_data.get('open_price', 0),
            high_5min=open_data.get('high_5min', 0),
            low_5min=open_data.get('low_5min', 0),
            close_5min=open_data.get('close_5min', 0),
            volume_5min=open_data.get('volume_5min', 0),
            tail_drop=open_data.get('tail_drop', 0),
            timestamp=open_data.get('timestamp', '')
        )
        
        # 按优先级顺序检测
        # 1. 纾价高开+开盘砸盘（最高优先级）
        result = self._detect_high_open_dump(auction, open_d)
        if result:
            logger.info(f"⚠️ [诡多检测] {result.name}({result.code}) - {result.trap_type.value} - {result.risk_level.value}")
            return result
        
        # 2. 纾价爆量+尾盘回落
        result = self._detect_boom_tail_drop(auction, open_d)
        if result:
            logger.info(f"⚠️ [诡多检测] {result.name}({result.code}) - {result.trap_type.value} - {result.risk_level.value}")
            return result
        
        # 3. 纾价平开+开盘拉升（正常模式）
        result = self._detect_flat_open_pump(auction, open_d)
        if result:
            logger.debug(f"✅ [正常模式] {result.name}({result.code}) - {result.trap_type.value}")
            return result
        
        # 没有检测到任何模式
        open_change = (open_d.close_5min - open_d.open_price) / open_d.open_price
        
        return DetectionResult(
            code=auction.code,
            name=auction.name,
            trap_type=TrapType.NORMAL,
            risk_level=RiskLevel.LOW,
            confidence=0.0,
            auction_change=auction.auction_change,
            open_change=open_change,
            volume_ratio=auction.volume_ratio,
            tail_drop=open_d.tail_drop,
            signals=[],
            timestamp=open_d.timestamp
        )
    
    def batch_detect(self, auction_data_list: List[Dict[str, Any]], 
                     open_data_list: List[Dict[str, Any]]) -> List[DetectionResult]:
        """
        批量检测纾价诡多模式
        
        Args:
            auction_data_list: 纾价数据列表
            open_data_list: 开盘数据列表
        
        Returns:
            检测结果列表
        """
        results = []
        
        # 构建 code 到 open_data 的映射
        open_data_map = {data['code']: data for data in open_data_list}
        
        for auction_data in auction_data_list:
            code = auction_data.get('code')
            
            if code in open_data_map:
                result = self.detect(auction_data, open_data_map[code])
                results.append(result)
            else:
                logger.warning(f"⚠️ {code} 未找到开盘数据，跳过检测")
        
        return results
    
    def get_trap_summary(self, results: List[DetectionResult]) -> Dict[str, Any]:
        """
        生成诡多检测汇总报告
        
        Args:
            results: 检测结果列表
        
        Returns:
            汇总报告字典
        """
        total = len(results)
        trap_counts = {}
        risk_counts = {}
        
        for result in results:
            # 统计诡多类型
            trap_type = result.trap_type.value
            trap_counts[trap_type] = trap_counts.get(trap_type, 0) + 1
            
            # 统计风险级别
            if result.trap_type != TrapType.NORMAL:
                risk_level = result.risk_level.value
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        return {
            'total': total,
            'trap_counts': trap_counts,
            'risk_counts': risk_counts,
            'trap_rate': (total - trap_counts.get('NORMAL', 0)) / total if total > 0 else 0
        }


if __name__ == "__main__":
    # 测试代码
    detector = AuctionTrapDetector()
    
    # 测试案例1: 纾价高开+开盘砸盘
    auction_data_1 = {
        'code': '300997.SZ',
        'name': '欢乐家',
        'auction_price': 15.50,
        'prev_close': 15.00,
        'auction_change': 0.0333,  # 3.33%
        'auction_volume': 500000,
        'auction_amount': 7750000,
        'volume_ratio': 2.5,
        'buy_orders': 50,
        'sell_orders': 30,
        'timestamp': '2026-02-11 09:25:00'
    }
    
    open_data_1 = {
        'code': '300997.SZ',
        'open_price': 15.50,
        'high_5min': 15.60,
        'low_5min': 15.10,
        'close_5min': 15.15,
        'volume_5min': 100000,
        'tail_drop': 0.029,  # 2.9%
        'timestamp': '2026-02-11 09:35:00'
    }
    
    result_1 = detector.detect(auction_data_1, open_data_1)
    print(f"\n测试案例1: {result_1.name}({result_1.code})")
    print(f"诡多类型: {result_1.trap_type.value}")
    print(f"风险级别: {result_1.risk_level.value}")
    print(f"置信度: {result_1.confidence*100:.0f}%")
    print(f"信号: {', '.join(result_1.signals)}")