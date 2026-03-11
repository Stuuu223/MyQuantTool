#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全息实盘雷达引擎 - CTO架构重构阶段一
=====================================
职责：纯净的事件监听，只锁定并打标签，不产生交易废单

设计标准：
1. 事件驱动：通过VIP Token接入xtdata.subscribe_whole_quote()
2. 环形缓冲区：内存中维持高频数据，只计算Price_Momentum和MFE
3. 纯净输出：符合条件的标的+时间戳存入Candidate_Pool
4. 极速稳定：先确保数据流订阅稳定，不做复杂计算

Author: AI开发团队 (CTO架构重构)
Date: 2026-03-11
Version: V1.0.0 (阶段一)
"""

import os
import sys
import time
import logging
from datetime import datetime, time as dt_time
from collections import deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from xtquant import xtdata

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RadarSignal:
    """雷达信号数据结构"""
    stock_code: str
    timestamp: datetime
    price: float
    high: float
    low: float
    price_momentum: float
    # 预留字段，阶段二填充
    volume_ratio: float = 0.0
    mfe: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'price': self.price,
            'high': self.high,
            'low': self.low,
            'price_momentum': round(self.price_momentum, 4)
        }


class LiveRadarEngine:
    """
    实盘雷达引擎 - 只做纯净的事件监听
    
    CTO设计标准：
    - 订阅全市场活跃标的
    - 计算Price_Momentum = (当前价 - 日内最低) / (日内最高 - 日内最低)
    - 当Price_Momentum > 0.9时，打印并缓存
    """
    
    # 交易时间常量
    MARKET_OPEN = dt_time(9, 30)
    MARKET_CLOSE = dt_time(15, 0)
    
    def __init__(self):
        """初始化雷达引擎"""
        self.candidate_pool: Dict[str, RadarSignal] = {}
        self.tick_buffer: Dict[str, deque] = {}  # 环形缓冲区
        self.running = False
        self._buffer_maxlen = 60  # 约3分钟微观轨迹
        
        logger.info("=" * 60)
        logger.info("全息实盘雷达引擎 - 阶段一启动")
        logger.info("=" * 60)
    
    def calculate_price_momentum(self, price: float, high: float, low: float) -> float:
        """
        计算价格动能净值 (Price Momentum)
        
        Formula: (当前价 - 日内最低) / (日内最高 - 日内最低)
        
        Args:
            price: 当前价格
            high: 日内最高价
            low: 日内最低价
            
        Returns:
            float: 0.0-1.0之间的动能净值
        """
        if high <= low:
            return 1.0 if price >= high else 0.0
        
        momentum = (price - low) / (high - low)
        return max(0.0, min(1.0, momentum))
    
    def on_tick_callback(self, data: Dict):
        """
        Tick数据回调函数 - 核心处理逻辑
        
        Args:
            data: QMT推送的Tick数据字典
        """
        try:
            # 解析Tick数据
            stock_code = data.get('stock_code', '')
            if not stock_code:
                return
            
            # 获取关键字段
            price = data.get('lastPrice', 0.0)
            high = data.get('high', 0.0)
            low = data.get('low', 0.0)
            
            if price <= 0 or high <= 0 or low <= 0:
                return
            
            # 计算Price Momentum
            momentum = self.calculate_price_momentum(price, high, low)
            
            # CTO标准：当且仅当Price Momentum > 0.9时触发
            if momentum > 0.9:
                timestamp = datetime.now()
                signal = RadarSignal(
                    stock_code=stock_code,
                    timestamp=timestamp,
                    price=price,
                    high=high,
                    low=low,
                    price_momentum=momentum
                )
                
                # 存入Candidate Pool
                self.candidate_pool[stock_code] = signal
                
                # 打印到控制台
                logger.info(
                    f"🎯 [雷达锁定] {stock_code} | "
                    f"时间:{timestamp.strftime('%H:%M:%S')} | "
                    f"价格:{price:.2f} | "
                    f"动能:{momentum:.2%}"
                )
            
        except Exception as e:
            logger.error(f"[Tick处理异常] {e}")
    
    def start(self, stock_list: Optional[List[str]] = None):
        """
        启动雷达引擎
        
        Args:
            stock_list: 订阅股票列表，None则订阅全市场
        """
        if self.running:
            logger.warning("雷达引擎已在运行")
            return
        
        logger.info("[启动] 正在连接QMT数据流...")
        
        try:
            # 订阅行情
            if stock_list:
                # 订阅指定列表
                for stock in stock_list:
                    xtdata.subscribe_quote(stock, period='tick', callback=self.on_tick_callback)
                logger.info(f"[订阅] 已订阅 {len(stock_list)} 只股票")
            else:
                # 全市场订阅（通过subscribe_whole_quote）
                xtdata.subscribe_whole_quote(callback=self.on_tick_callback)
                logger.info("[订阅] 已订阅全市场")
            
            self.running = True
            logger.info("[运行中] 雷达引擎已启动，等待数据流...")
            logger.info("[监控] 当Price Momentum > 0.9时将输出锁定信号")
            
            # 保持运行
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("[停止] 用户中断")
            self.stop()
        except Exception as e:
            logger.error(f"[运行异常] {e}")
            self.stop()
    
    def stop(self):
        """停止雷达引擎"""
        self.running = False
        logger.info("[停止] 雷达引擎已关闭")
        logger.info(f"[统计] 本次运行共锁定 {len(self.candidate_pool)} 只标的")
        
        # 输出最终候选池
        if self.candidate_pool:
            logger.info("=" * 60)
            logger.info("本次候选池汇总:")
            for code, signal in sorted(self.candidate_pool.items()):
                logger.info(f"  {code}: 动能{signal.price_momentum:.2%} @ {signal.timestamp.strftime('%H:%M:%S')}")
    
    def get_candidate_pool(self) -> Dict[str, RadarSignal]:
        """获取当前候选池"""
        return self.candidate_pool.copy()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='全息实盘雷达引擎 - CTO架构重构阶段一')
    parser.add_argument('--stocks', nargs='+', help='指定订阅股票列表（默认全市场）')
    parser.add_argument('--test', action='store_true', help='测试模式（模拟数据）')
    args = parser.parse_args()
    
    # 创建引擎
    radar = LiveRadarEngine()
    
    if args.test:
        # 测试模式：模拟数据
        logger.info("[测试模式] 使用模拟数据")
        test_data = {
            'stock_code': '000001.SZ',
            'lastPrice': 11.5,
            'high': 11.8,
            'low': 10.0
        }
        radar.on_tick_callback(test_data)
        
        # 验证计算
        momentum = radar.calculate_price_momentum(11.5, 11.8, 10.0)
        logger.info(f"测试计算: Price Momentum = {momentum:.2%}")
        
        # 测试未触发情况
        test_data2 = {
            'stock_code': '000002.SZ',
            'lastPrice': 10.5,
            'high': 11.8,
            'low': 10.0
        }
        radar.on_tick_callback(test_data2)
        momentum2 = radar.calculate_price_momentum(10.5, 11.8, 10.0)
        logger.info(f"测试计算(未触发): Price Momentum = {momentum2:.2%}")
        
    else:
        # 实盘模式
        try:
            stock_list = args.stocks if args.stocks else None
            radar.start(stock_list)
        except Exception as e:
            logger.error(f"[启动失败] {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
