#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温柔探针 - 单进程验证，禁止多线程

【用途】
  验证 QMT 数据连接是否正常，数据是否完好

【严禁】
  严禁在多进程框架下调用！xtdata 不是线程安全的！
"""

import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

def gentle_probe():
    from xtquant import xtdata
    
    logging.info("Step 1: 获取股票列表...")
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    logging.info(f"列表获取成功: {len(stocks)} 只")
    
    # 用最简单的两只股票验证
    for code in ['000001.SZ', '605090.SH']:
        logging.info(f"正在读取 {code}...")
        try:
            data = xtdata.get_local_data(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='20260201',
                end_time='20260226'
            )
            if data and code in data and len(data[code]) > 0:
                logging.info(f"✅ {code} 正常，{len(data[code])} 条")
            else:
                logging.warning(f"⚠️ {code} 返回空，可能需要补充下载")
        except Exception as e:
            logging.error(f"❌ {code} 异常: {e}")
        
        time.sleep(1)  # 每次读取间隔1秒，避免触发内部速率限制

if __name__ == '__main__':
    gentle_probe()
