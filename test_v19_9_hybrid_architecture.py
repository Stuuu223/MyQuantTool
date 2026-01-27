#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.9 混合动力架构测试脚本

测试三级火箭架构的有效性：
1. 极速层（easyquotation）- 半路战法
2. 基础层（efinance）- 低吸战法
3. 增强层（akshare）- 龙头战法

Author: iFlow CLI
Version: V19.9
"""

import sys
import time
from datetime import datetime
from logic.logger import get_logger
from logic.data_source_manager import get_smart_data_manager

logger = get_logger(__name__)


def test_fast_layer():
    """测试极速层（easyquotation）"""
    logger.info("=" * 80)
    logger.info("🚀 测试极速层（easyquotation）- 半路战法")
    logger.info("=" * 80)
    
    try:
        manager = get_smart_data_manager()
        
        # 测试股票列表
        test_stocks = ['sh600519', 'sz000001', 'sz300750']
        
        logger.info(f"🔄 测试获取实时数据，股票数量: {len(test_stocks)}")
        
        start_time = time.time()
        data = manager.get_realtime_price_fast(test_stocks)
        elapsed_time = time.time() - start_time
        
        if data:
            logger.info(f"✅ 极速层测试成功！")
            logger.info(f"   - 获取股票数: {len(data)}")
            logger.info(f"   - 响应时间: {elapsed_time:.3f}秒")
            
            for code, info in data.items():
                logger.info(f"   - {code} {info.get('name', '')}: ¥{info.get('price', 0):.2f}")
        else:
            logger.warning("⚠️ 极速层测试失败，未获取到数据")
    
    except Exception as e:
        logger.error(f"❌ 极速层测试失败: {e}")


def test_basic_layer():
    """测试基础层（efinance）"""
    logger.info("=" * 80)
    logger.info("📊 测试基础层（efinance）- 低吸战法")
    logger.info("=" * 80)
    
    try:
        manager = get_smart_data_manager()
        
        # 测试股票代码
        test_stock = '600519'
        
        logger.info(f"🔄 测试获取历史K线数据，股票: {test_stock}")
        
        start_time = time.time()
        df = manager.get_history_kline(test_stock)
        elapsed_time = time.time() - start_time
        
        if not df.empty:
            logger.info(f"✅ 基础层测试成功！")
            logger.info(f"   - K线数量: {len(df)}")
            logger.info(f"   - 响应时间: {elapsed_time:.3f}秒")
            logger.info(f"   - 最新收盘价: ¥{df.iloc[-1]['收盘']:.2f}")
        else:
            logger.warning("⚠️ 基础层测试失败，未获取到数据")
    
    except Exception as e:
        logger.error(f"❌ 基础层测试失败: {e}")


def test_enhanced_layer():
    """测试增强层（akshare）"""
    logger.info("=" * 80)
    logger.info("🔥 测试增强层（akshare）- 龙头战法")
    logger.info("=" * 80)
    
    try:
        manager = get_smart_data_manager()
        
        # 测试股票代码
        test_stock = '600519'
        
        logger.info(f"🔄 测试获取资金流数据，股票: {test_stock}")
        
        start_time = time.time()
        data = manager.get_money_flow(test_stock)
        elapsed_time = time.time() - start_time
        
        if data:
            logger.info(f"✅ 增强层测试成功！")
            logger.info(f"   - 响应时间: {elapsed_time:.3f}秒")
            logger.info(f"   - 主力净流入: {data.get('今日主力净流入-净额', 0)/10000:.1f}万")
        else:
            logger.warning("⚠️ 增强层测试失败，未获取到数据")
    
    except Exception as e:
        logger.error(f"❌ 增强层测试失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 V19.9 混合动力架构测试开始")
    logger.info("=" * 80)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # 测试极速层
    test_fast_layer()
    
    # 测试基础层
    test_basic_layer()
    
    # 测试增强层
    test_enhanced_layer()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logger.info("=" * 80)
    logger.info(f"✅ V19.9 混合动力架构测试完成，耗时: {elapsed_time:.2f}秒")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()