#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Tushare 实时价格兜底
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    import tushare as ts

    logger = logging.getLogger(__name__)

    # 测试股票
    codes = ['300912.SZ', '603618.SH', '605088.SH']

    logger.info("=" * 80)
    logger.info("🔍 测试 Tushare 实时价格获取")
    logger.info("=" * 80)

    for code in codes:
        logger.info(f"\n📊 {code}:")

        try:
            # 转换代码格式（Tushare使用小写）
            code_ak = code.replace('.SZ', '.sz').replace('.SH', '.sh')

            # 方法1：实时报价
            try:
                pro = ts.pro_api()
                quote = pro.quote(code_ak=code_ak)

                if not quote.empty and len(quote) > 0:
                    price = float(quote['price'].iloc[0])
                    logger.info(f"  ✅ 实时报价: {price}")
                else:
                    logger.warning(f"  ⚠️ 实时报价为空")
            except Exception as e:
                logger.warning(f"  ⚠️ 实时报价失败: {e}")

            # 方法2：日线最新价
            try:
                pro = ts.pro_api()
                today = __import__('datetime').datetime.now().strftime('%Y%m%d')
                df = pro.daily(ts_code=code_ak, trade_date=today)

                if not df.empty and len(df) > 0:
                    close_price = float(df['close'].iloc[0])
                    logger.info(f"  ✅ 日线最新收盘: {close_price}")
                else:
                    logger.warning(f"  ⚠️ 日线数据为空（可能是非交易日）")
            except Exception as e:
                logger.warning(f"  ⚠️ 日线数据失败: {e}")

            # 方法3：分钟线最新价
            try:
                pro = ts.pro_api()
                df = pro.min(ts_code=code_ak, start_time='09:00:00', end_time='15:00:00')

                if not df.empty and len(df) > 0:
                    min_price = float(df['close'].iloc[-1])
                    logger.info(f"  ✅ 分钟线最新: {min_price}")
                else:
                    logger.warning(f"  ⚠️ 分钟线数据为空")
            except Exception as e:
                logger.warning(f"  ⚠️ 分钟线数据失败: {e}")

        except Exception as e:
            logger.error(f"❌ {code} 测试失败: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ Tushare 测试完成")
    logger.info("=" * 80)

except ImportError as e:
    print(f"❌ Tushare 未安装: {e}")
    print("请运行: pip install tushare")