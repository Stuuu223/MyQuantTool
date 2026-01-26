#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.7 全战法测试脚本
测试所有战法的性能和扫描结果
"""

import sys
import time
from datetime import datetime
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.dragon_tactics import DragonTactics
from logic.low_suction_engine import LowSuctionEngine
from logic.active_stock_filter import ActiveStockFilter

logger = get_logger(__name__)


def test_dragon_tactics():
    """测试龙头战法"""
    logger.info("=" * 80)
    logger.info("🐉 开始测试龙头战法")
    logger.info("=" * 80)
    
    try:
        db = DataManager()
        dragon_tactics = DragonTactics(db)
        
        # 获取活跃股票
        logger.info("正在获取活跃股票...")
        stock_filter = ActiveStockFilter()
        active_stocks = stock_filter.get_active_stocks(
            limit=50,
            sort_by='amount',
            min_amplitude=3.0,
            min_turnover=1.0
        )
        
        if not active_stocks:
            logger.warning("❌ 未获取到活跃股票")
            return
        
        logger.info(f"✅ 获取到 {len(active_stocks)} 只活跃股票")
        
        # 测试龙头战法
        dragon_count = 0
        for stock in active_stocks[:20]:  # 测试前20只股票
            stock_code = stock['code']
            stock_name = stock.get('name', '')
            
            try:
                # 获取实时数据
                realtime_data = db.get_realtime_data(stock_code)
                if not realtime_data:
                    continue
                
                # 构建股票信息
                stock_info = {
                    'code': stock_code,
                    'name': stock_name,
                    'price': realtime_data.get('current', 0),
                    'open': realtime_data.get('open', 0),
                    'pre_close': realtime_data.get('pre_close', 0),
                    'high': realtime_data.get('high', 0),
                    'low': realtime_data.get('low', 0),
                    'bid_volume': realtime_data.get('bid1_volume', 0),
                    'ask_volume': realtime_data.get('ask1_volume', 0),
                    'volume': realtime_data.get('volume', 0),
                    'turnover': realtime_data.get('turnover_rate', 0),
                    'volume_ratio': realtime_data.get('volume_ratio', 1.0),
                    'prev_pct_change': realtime_data.get('prev_pct_change', 0),
                    'is_20cm': stock_code.startswith('688') or stock_code.startswith('300')
                }
                
                # 获取均线数据
                kline_data = db.get_kline(stock_code, period='daily', count=20)
                if kline_data and len(kline_data) >= 20:
                    stock_info['ma5'] = kline_data['close'].rolling(window=5).mean().iloc[-1]
                    stock_info['ma10'] = kline_data['close'].rolling(window=10).mean().iloc[-1]
                    stock_info['ma20'] = kline_data['close'].rolling(window=20).mean().iloc[-1]
                
                # 分析龙头战法
                result = dragon_tactics.check_dragon_criteria(stock_info)
                
                if result.get('total_score', 0) > 60:
                    dragon_count += 1
                    logger.info(f"✅ [龙头] {stock_code} {stock_name} 评分: {result['total_score']:.1f}, 角色: {result.get('role', '未知')}, 信号: {result.get('signal', '未知')}")
                    if result.get('sector_resonance_score'):
                        logger.info(f"   板块共振评分: {result['sector_resonance_score']:+.1f}, 详情: {result.get('sector_resonance_details', [])}")
                
            except Exception as e:
                logger.warning(f"⚠️ 测试 {stock_code} 失败: {e}")
        
        logger.info(f"📊 龙头战法测试完成，发现 {dragon_count} 只龙头股")
        
    except Exception as e:
        logger.error(f"❌ 龙头战法测试失败: {e}")


def test_low_suction():
    """测试低吸战法"""
    logger.info("=" * 80)
    logger.info("📉 开始测试低吸战法")
    logger.info("=" * 80)
    
    try:
        db = DataManager()
        low_suction = LowSuctionEngine()
        
        # 获取活跃股票
        logger.info("正在获取活跃股票...")
        stock_filter = ActiveStockFilter()
        active_stocks = stock_filter.get_active_stocks(
            limit=50,
            sort_by='amount',
            min_amplitude=3.0,
            min_turnover=0.5
        )
        
        if not active_stocks:
            logger.warning("❌ 未获取到活跃股票")
            return
        
        logger.info(f"✅ 获取到 {len(active_stocks)} 只活跃股票")
        
        # 测试低吸战法
        suction_count = 0
        for stock in active_stocks[:20]:  # 测试前20只股票
            stock_code = stock['code']
            stock_name = stock.get('name', '')
            
            try:
                # 获取实时数据
                realtime_data = db.get_realtime_data(stock_code)
                if not realtime_data:
                    continue
                
                current_price = realtime_data.get('current', 0)
                prev_close = realtime_data.get('pre_close', 0)
                
                if current_price == 0 or prev_close == 0:
                    continue
                
                # 检查5日均线低吸
                result = low_suction.check_ma5_suction(stock_code, current_price, prev_close)
                
                if result.get('has_suction'):
                    suction_count += 1
                    logger.info(f"✅ [低吸] {stock_code} {stock_name} 置信度: {result['confidence']:.2f}, 类型: {result.get('suction_type', '未知')}")
                    logger.info(f"   原因: {result.get('reason', '')}")
                    if result.get('sector_resonance_score'):
                        logger.info(f"   板块共振评分: {result['sector_resonance_score']:+.1f}")
                
            except Exception as e:
                logger.warning(f"⚠️ 测试 {stock_code} 失败: {e}")
        
        logger.info(f"📊 低吸战法测试完成，发现 {suction_count} 只低吸股")
        
    except Exception as e:
        logger.error(f"❌ 低吸战法测试失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 V19.7 全战法测试开始")
    logger.info("=" * 80)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # 测试龙头战法
    test_dragon_tactics()
    
    # 测试低吸战法
    test_low_suction()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logger.info("=" * 80)
    logger.info(f"✅ V19.7 全战法测试完成，耗时: {elapsed_time:.2f}秒")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()