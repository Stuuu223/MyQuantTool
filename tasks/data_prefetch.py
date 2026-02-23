#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据蓄水脚本 - 下载472只短线活跃股 Tick 数据

使用方式：
python tasks/data_prefetch.py
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("data_prefetch")

# ================= 配置区 =================
# VIP Token
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'

# 从竞价数据生成的短线活跃股名单（472只）
ACTIVE_STOCKS_FILE = PROJECT_ROOT / 'config' / 'active_stocks.json'
if ACTIVE_STOCKS_FILE.exists():
    with open(ACTIVE_STOCKS_FILE, 'r', encoding='utf-8') as f:
        ELITE_POOL = json.load(f)
    logger.info(f"📋 从 {ACTIVE_STOCKS_FILE} 加载了 {len(ELITE_POOL)} 只短线活跃股")
else:
    logger.warning(f"⚠️  {ACTIVE_STOCKS_FILE} 不存在，使用默认名单")
    ELITE_POOL = [
        '600589.SH', '002475.SZ', '600519.SH', '301018.SZ', '300582.SZ',
        '002194.SZ', '603629.SH', '601112.SH', '301200.SZ', '688627.SH'
    ]
# ========================================


def start_token_service():
    """
    启动 xtdatacenter 行情服务 (Token 模式)
    """
    from xtquant import xtdatacenter as xtdc
    from xtquant import xtdata
    
    # 1. 设置数据目录为QMT客户端目录（不得下载到项目内）
    from pathlib import Path
    data_dir = Path('E:/qmt/userdata_mini/datadir')
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    logger.info(f"📂 QMT数据目录: {data_dir}")
    
    # 2. 设置 Token
    xtdc.set_token(VIP_TOKEN)
    logger.info(f"🔑 Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")
    
    # 3. 初始化并监听端口
    xtdc.init()
    listen_port = xtdc.listen(port=(58620, 58630))
    logger.info(f"🚀 行情服务已启动，监听端口: {listen_port}")
    
    return listen_port


def download_tasks(listen_port):
    """
    执行数据下载任务
    """
    from xtquant import xtdata
    
    # 1. 连接到行情服务
    _, port = listen_port
    xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)
    
    # 等待连接成功
    for i in range(10):
        if xtdata.get_market_data(['close'], ['600519.SH'], count=1):
            logger.info("✅ 成功连接到行情服务！")
            break
        time.sleep(1)
        logger.info(f"⏳ 等待连接... {i+1}/10")
    else:
        logger.error("❌ 连接失败，请检查 Token 是否有效或网络问题")
        return
    
    # ------------------------------------------------------------------
    # 任务 A：全市场 1分钟 K线 (已完成，跳过)
    # ------------------------------------------------------------------
    logger.info("=" * 80)
    logger.info("📋 [方案A] 全市场 1分钟 K线 (近1年)")
    logger.info("=" * 80)
    logger.info("   ✅ 已完成，跳过下载（5190只股票，19.28 GB）")
    
    # ------------------------------------------------------------------
    # 任务 B：下载472只短线活跃股 Tick 数据 (近6个月)
    # ------------------------------------------------------------------
    logger.info("=" * 80)
    logger.info(f"💎 [方案B] 短线活跃股 Tick 数据 ({len(ELITE_POOL)}只)")
    logger.info("=" * 80)
    
    start_time_tick = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d%H%M%S')
    
    logger.info(f"   时间范围: 近6个月")
    logger.info(f"   预估数据量: ~{len(ELITE_POOL) * 180 * 3 / 1024:.1f} GB")
    
    success_count = 0
    fail_count = 0
    
    for idx, code in enumerate(ELITE_POOL):
        logger.info(f"   [{idx+1}/{len(ELITE_POOL)}] 下载 Tick: {code} ...")
        
        try:
            xtdata.download_history_data(code, period='tick', start_time=start_time_tick)
            success_count += 1
            time.sleep(0.2)
        except Exception as e:
            fail_count += 1
            logger.error(f"   ❌ {code} 下载失败: {e}")
    
    logger.info("=" * 80)
    logger.info(f"✅ Tick 数据下载完毕！")
    logger.info(f"   成功: {success_count} 只")
    logger.info(f"   失败: {fail_count} 只")
    logger.info("=" * 80)


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 数据蓄水启动 - 下载472只短线活跃股 Tick 数据")
    logger.info("=" * 80)
    
    try:
        # 1. 启动 Token 服务
        port = start_token_service()
        
        # 2. 执行下载任务
        download_tasks(port)
        
        # 3. 保持运行 (不要退出，否则服务会断)
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎉 所有任务完成！按 Ctrl+C 退出...")
        logger.info("=" * 80)
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("👋 停止运行")
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()