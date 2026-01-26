#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.7 全战法测试脚本（使用模拟数据）
测试所有战法的性能和扫描结果
"""

import sys
import time
from datetime import datetime
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.dragon_tactics import DragonTactics
from logic.low_suction_engine import LowSuctionEngine

logger = get_logger(__name__)


def create_mock_stocks():
    """创建模拟股票数据"""
    mock_stocks = [
        {
            'code': '000001',
            'name': '平安银行',
            'price': 12.50,
            'open': 12.30,
            'pre_close': 12.00,
            'high': 12.80,
            'low': 12.20,
            'bid_volume': 1000,
            'ask_volume': 500,
            'volume': 50000,
            'turnover': 5.2,
            'volume_ratio': 1.5,
            'prev_pct_change': 3.5,
            'ma5': 12.10,
            'ma10': 11.90,
            'ma20': 11.50,
            'is_20cm': False
        },
        {
            'code': '000002',
            'name': '万科A',
            'price': 18.30,
            'open': 18.00,
            'pre_close': 17.50,
            'high': 18.50,
            'low': 17.80,
            'bid_volume': 2000,
            'ask_volume': 800,
            'volume': 80000,
            'turnover': 4.5,
            'volume_ratio': 2.0,
            'prev_pct_change': 4.6,
            'ma5': 17.80,
            'ma10': 17.40,
            'ma20': 16.90,
            'is_20cm': False
        },
        {
            'code': '300001',
            'name': '特锐德',
            'price': 25.80,
            'open': 24.50,
            'pre_close': 23.00,
            'high': 26.50,
            'low': 24.00,
            'bid_volume': 500,
            'ask_volume': 300,
            'volume': 30000,
            'turnover': 12.2,
            'volume_ratio': 3.5,
            'prev_pct_change': 12.2,
            'ma5': 23.50,
            'ma10': 22.00,
            'ma20': 20.50,
            'is_20cm': True
        },
        {
            'code': '688001',
            'name': '中微公司',
            'price': 180.50,
            'open': 175.00,
            'pre_close': 170.00,
            'high': 185.00,
            'low': 173.00,
            'bid_volume': 200,
            'ask_volume': 100,
            'volume': 5000,
            'turnover': 8.5,
            'volume_ratio': 2.5,
            'prev_pct_change': 6.2,
            'ma5': 172.00,
            'ma10': 168.00,
            'ma20': 160.00,
            'is_20cm': True
        },
        {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1680.00,
            'open': 1665.00,
            'pre_close': 1650.00,
            'high': 1690.00,
            'low': 1660.00,
            'bid_volume': 50,
            'ask_volume': 30,
            'volume': 1000,
            'turnover': 0.8,
            'volume_ratio': 0.8,
            'prev_pct_change': 1.8,
            'ma5': 1655.00,
            'ma10': 1645.00,
            'ma20': 1630.00,
            'is_20cm': False
        },
        {
            'code': '000858',
            'name': '五粮液',
            'price': 145.20,
            'open': 142.00,
            'pre_close': 140.00,
            'high': 147.00,
            'low': 141.50,
            'bid_volume': 800,
            'ask_volume': 400,
            'volume': 25000,
            'turnover': 3.8,
            'volume_ratio': 1.8,
            'prev_pct_change': 3.7,
            'ma5': 141.50,
            'ma10': 139.00,
            'ma20': 136.00,
            'is_20cm': False
        },
        {
            'code': '002594',
            'name': '比亚迪',
            'price': 210.50,
            'open': 205.00,
            'pre_close': 200.00,
            'high': 215.00,
            'low': 204.00,
            'bid_volume': 300,
            'ask_volume': 200,
            'volume': 15000,
            'turnover': 6.5,
            'volume_ratio': 2.2,
            'prev_pct_change': 5.3,
            'ma5': 202.00,
            'ma10': 198.00,
            'ma20': 192.00,
            'is_20cm': False
        },
        {
            'code': '300750',
            'name': '宁德时代',
            'price': 185.30,
            'open': 180.00,
            'pre_close': 175.00,
            'high': 190.00,
            'low': 178.00,
            'bid_volume': 400,
            'ask_volume': 250,
            'volume': 20000,
            'turnover': 7.8,
            'volume_ratio': 2.8,
            'prev_pct_change': 5.9,
            'ma5': 178.00,
            'ma10': 173.00,
            'ma20': 168.00,
            'is_20cm': True
        },
        {
            'code': '600036',
            'name': '招商银行',
            'price': 35.80,
            'open': 35.20,
            'pre_close': 34.80,
            'high': 36.20,
            'low': 35.00,
            'bid_volume': 1500,
            'ask_volume': 700,
            'volume': 60000,
            'turnover': 2.8,
            'volume_ratio': 1.3,
            'prev_pct_change': 2.9,
            'ma5': 35.00,
            'ma10': 34.50,
            'ma20': 34.00,
            'is_20cm': False
        },
        {
            'code': '000725',
            'name': '京东方A',
            'price': 4.25,
            'open': 4.15,
            'pre_close': 4.00,
            'high': 4.35,
            'low': 4.10,
            'bid_volume': 5000,
            'ask_volume': 3000,
            'volume': 200000,
            'turnover': 6.2,
            'volume_ratio': 2.5,
            'prev_pct_change': 6.3,
            'ma5': 4.10,
            'ma10': 3.95,
            'ma20': 3.80,
            'is_20cm': False
        }
    ]
    return mock_stocks


def test_dragon_tactics():
    """测试龙头战法"""
    logger.info("=" * 80)
    logger.info("🐉 开始测试龙头战法（使用模拟数据）")
    logger.info("=" * 80)
    
    try:
        db = DataManager()
        dragon_tactics = DragonTactics(db)
        
        # 获取模拟股票
        mock_stocks = create_mock_stocks()
        logger.info(f"✅ 获取到 {len(mock_stocks)} 只模拟股票")
        
        # 测试龙头战法
        dragon_count = 0
        for stock_info in mock_stocks:
            stock_code = stock_info['code']
            stock_name = stock_info.get('name', '')
            
            try:
                # 分析龙头战法
                result = dragon_tactics.check_dragon_criteria(stock_info)
                
                logger.info(f"📊 [龙头] {stock_code} {stock_name}")
                logger.info(f"   评分: {result['total_score']:.1f}, 角色: {result.get('role', '未知')}, 信号: {result.get('signal', '未知')}")
                logger.info(f"   涨幅: {((stock_info['price'] - stock_info['pre_close']) / stock_info['pre_close'] * 100):.2f}%, 换手率: {stock_info['turnover']:.2f}%")
                
                if result.get('sector_resonance_score'):
                    logger.info(f"   板块共振评分: {result['sector_resonance_score']:+.1f}")
                
                if result.get('total_score', 0) > 60:
                    dragon_count += 1
                    logger.info(f"   ✅ 符合龙头标准！")
                
                logger.info("-" * 60)
                
            except Exception as e:
                logger.warning(f"⚠️ 测试 {stock_code} 失败: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        
        logger.info(f"📊 龙头战法测试完成，发现 {dragon_count} 只龙头股")
        
    except Exception as e:
        logger.error(f"❌ 龙头战法测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def test_low_suction():
    """测试低吸战法"""
    logger.info("=" * 80)
    logger.info("📉 开始测试低吸战法（使用模拟数据）")
    logger.info("=" * 80)
    
    try:
        db = DataManager()
        low_suction = LowSuctionEngine()
        
        # 获取模拟股票
        mock_stocks = create_mock_stocks()
        logger.info(f"✅ 获取到 {len(mock_stocks)} 只模拟股票")
        
        # 创建一些低吸场景的模拟数据
        low_suction_scenarios = [
            {
                'code': '000010',
                'name': '低吸测试股1',
                'current': 10.50,
                'pre_close': 11.00,
                'ma5': 10.80
            },
            {
                'code': '000020',
                'name': '低吸测试股2',
                'current': 8.20,
                'pre_close': 8.50,
                'ma5': 8.40
            },
            {
                'code': '000030',
                'name': '低吸测试股3',
                'current': 15.30,
                'pre_close': 16.00,
                'ma5': 15.80
            }
        ]
        
        # 测试低吸战法
        suction_count = 0
        for scenario in low_suction_scenarios:
            stock_code = scenario['code']
            stock_name = scenario.get('name', '')
            
            try:
                # 检查5日均线低吸
                result = low_suction.check_ma5_suction(
                    stock_code,
                    scenario['current'],
                    scenario['pre_close']
                )
                
                logger.info(f"📊 [低吸] {stock_code} {stock_name}")
                logger.info(f"   当前价: {scenario['current']:.2f}, 昨收: {scenario['pre_close']:.2f}, MA5: {scenario['ma5']:.2f}")
                logger.info(f"   有低吸信号: {result.get('has_suction', False)}")
                
                if result.get('has_suction'):
                    suction_count += 1
                    logger.info(f"   置信度: {result['confidence']:.2f}, 类型: {result.get('suction_type', '未知')}")
                    logger.info(f"   原因: {result.get('reason', '')}")
                    if result.get('sector_resonance_score'):
                        logger.info(f"   板块共振评分: {result['sector_resonance_score']:+.1f}")
                    logger.info(f"   ✅ 发现低吸机会！")
                
                logger.info("-" * 60)
                
            except Exception as e:
                logger.warning(f"⚠️ 测试 {stock_code} 失败: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        
        logger.info(f"📊 低吸战法测试完成，发现 {suction_count} 只低吸股")
        
    except Exception as e:
        logger.error(f"❌ 低吸战法测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 V19.7 全战法测试开始（使用模拟数据）")
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