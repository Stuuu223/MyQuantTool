#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QMT 实时价格兜底
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from xtquant import xtdata

    logger = logging.getLogger(__name__)

    # 测试股票
    codes = ['300912.SZ', '603618.SH', '605088.SH']

    logger.info("=" * 80)
    logger.info("🔍 测试 QMT 实时价格获取")
    logger.info("=" * 80)

    try:
        # 获取全市场 tick 数据
        logger.info("\n📡 获取全市场 tick 数据...")
        tick_data = xtdata.get_full_tick(codes)

        if tick_data:
            logger.info(f"✅ 成功获取 {len(tick_data)} 只股票数据")

            for code in codes:
                logger.info(f"\n📊 {code}:")

                if code in tick_data:
                    stock_tick = tick_data[code]

                    # 获取最新价
                    last_price = stock_tick.get('lastPrice') or stock_tick.get('last_price', 0)
                    logger.info(f"  ✅ 最新价: {last_price}")

                    # 获取其他字段
                    logger.info(f"  - 昨收: {stock_tick.get('lastClose', 0)}")
                    logger.info(f"  - 成交量: {stock_tick.get('volume', 0)}")
                    logger.info(f"  - 成交额: {stock_tick.get('amount', 0)}")
                else:
                    logger.warning(f"  ⚠️ 未找到 {code} 数据")
        else:
            logger.warning("⚠️ get_full_tick 返回空数据")

    except Exception as e:
        logger.error(f"❌ QMT 获取失败: {e}")
        logger.info("\n💡 可能原因：")
        logger.info("  1. QMT 客户端未启动")
        logger.info("  2. QMT 未登录")
        logger.info("  3. xtquant DLL 加载失败")

    logger.info("\n" + "=" * 80)
    logger.info("✅ QMT 测试完成")
    logger.info("=" * 80)

except ImportError as e:
    print(f"❌ xtquant 未安装: {e}")
    print("请使用虚拟环境: venv_qmt\\Scripts\\python.exe")
except Exception as e:
    print(f"❌ 测试失败: {e}")