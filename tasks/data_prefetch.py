#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据蓄水脚本 - 为 Level 0 情绪风控模型训练准备数据

策略：宽窄结合
- 方案 A：全市场 1分钟 K线（普查，必须做）
- 方案 B：核心龙头池 Tick 数据（精查，强烈建议）

Token: 6b1446e317ed67596f13d2e808291a01e0dd9839

使用方式：
python tasks/data_prefetch.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger("data_prefetch")


def init_qmt_with_token():
    """初始化 QMT Token 模式"""
    try:
        from xtquant import xtdata
        
        # CTO 提供的 Token
        token = '6b1446e317ed67596f13d2e808291a01e0dd9839'
        
        # 连接 Token 模式
        result = xtdata.connect(token=token)
        
        if result == 0:
            logger.info("✅ QMT Token 连接成功")
            return True
        else:
            logger.error(f"❌ QMT Token 连接失败，错误码: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ QMT Token 初始化异常: {e}")
        return False


def prefetch_full_market_1m():
    """
    方案 A：下载全市场 1分钟 K线（近30天）
    
    目标：构建大盘情绪指数（涨停家数、跌停家数、连板晋级率）
    """
    try:
        from xtquant import xtdata
        
        logger.info("=" * 80)
        logger.info("📋 [方案A] 开始下载全市场 1分钟 K线")
        logger.info("=" * 80)
        
        # 1. 获取全市场股票列表
        logger.info("📋 获取全市场股票列表...")
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
        logger.info(f"   共 {len(stock_list)} 只股票")
        
        # 2. 计算时间范围（近30天）
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d%H%M%S')
        end_time = datetime.now().strftime('%Y%m%d%H%M%S')
        
        logger.info(f"   时间范围: {start_time} ~ {end_time}")
        logger.info(f"   数据周期: 1分钟")
        
        # 3. 批量下载（每次 500 只，避免超时）
        batch_size = 500
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        success_count = 0
        fail_count = 0
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i : i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"   进度: {i}/{len(stock_list)} (批次 {batch_num}/{total_batches})...")
            
            try:
                # 使用 download_history_data2 批量下载
                xtdata.download_history_data2(
                    stock_list=batch,
                    period='1m',
                    start_time=start_time,
                    end_time=end_time
                )
                success_count += len(batch)
                logger.info(f"   ✅ 批次 {batch_num} 下载成功 ({len(batch)} 只)")
                
                # 避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                fail_count += len(batch)
                logger.error(f"   ❌ 批次 {batch_num} 下载失败: {e}")
        
        # 4. 总结
        logger.info("=" * 80)
        logger.info("✅ 全市场 1分钟 K线下载完毕！")
        logger.info(f"   成功: {success_count} 只")
        logger.info(f"   失败: {fail_count} 只")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 方案 A 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def prefetch_core_leaders_tick():
    """
    方案 B：精选龙头 Tick 数据（精查）
    
    目标：训练"龙头首阴"、"竞价抓龙"等高精度模型
    策略：只下载过去 30 天内出现过涨停板的股票的 Tick 数据
    """
    try:
        from xtquant import xtdata
        
        logger.info("=" * 80)
        logger.info("💎 [方案B] 开始下载核心龙头 Tick 数据")
        logger.info("=" * 80)
        
        # 1. 计算时间范围（近30天）
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d%H%M%S')
        end_time = datetime.now().strftime('%Y%m%d%H%M%S')
        
        logger.info(f"   时间范围: {start_time} ~ {end_time}")
        logger.info(f"   数据周期: Tick")
        
        # 2. 示例：下载 10huang 提到的几只经典案例股
        # 实际应该通过日线筛选找出近期涨停股（约 300-500 只）
        core_stocks = [
            '600519.SH',  # 贵州茅台 - 龙头代表
            '300997.SZ',  # 欢乐家 - 经典案例
            '600606.SH',  # 绿地控股
            '600482.SH',  # 中国软件
            '600036.SH',  # 招商银行
            '000001.SZ',  # 平安银行
            '300059.SZ',  # 东方财富
            '002475.SZ',  # 立讯精密
            '603986.SH',  # 兆易创新
            '600276.SH',  # 恒瑞医药
        ]
        
        logger.info(f"   核心股票池: {len(core_stocks)} 只")
        
        success_count = 0
        fail_count = 0
        
        for code in core_stocks:
            logger.info(f"   下载 Tick: {code}...")
            
            try:
                xtdata.download_history_data(
                    stock_code=code,
                    period='tick',
                    start_time=start_time,
                    end_time=end_time
                )
                success_count += 1
                logger.info(f"   ✅ {code} 下载成功")
                
                # 避免请求过快
                time.sleep(0.3)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"   ❌ {code} 下载失败: {e}")
        
        # 4. 总结
        logger.info("=" * 80)
        logger.info("✅ 核心龙头 Tick 数据下载完毕！")
        logger.info(f"   成功: {success_count} 只")
        logger.info(f"   失败: {fail_count} 只")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 方案 B 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 数据蓄水启动 - Level 0 情绪风控模型训练准备")
    logger.info("=" * 80)
    
    # 1. 初始化 QMT Token
    if not init_qmt_with_token():
        logger.error("❌ QMT Token 初始化失败，无法继续")
        return 1
    
    logger.info("")
    
    # 2. 方案 A：全市场 1分钟 K线（普查，必须做）
    logger.info("开始执行方案 A：全市场 1分钟 K线下载...")
    success_a = prefetch_full_market_1m()
    
    logger.info("")
    
    # 3. 方案 B：核心龙头 Tick 数据（精查，强烈建议）
    logger.info("开始执行方案 B：核心龙头 Tick 数据下载...")
    success_b = prefetch_core_leaders_tick()
    
    logger.info("")
    
    # 4. 总结
    logger.info("=" * 80)
    logger.info("📊 数据蓄水完成总结")
    logger.info("=" * 80)
    logger.info(f"   方案 A (全市场 1分钟 K线): {'✅ 成功' if success_a else '❌ 失败'}")
    logger.info(f"   方案 B (核心龙头 Tick): {'✅ 成功' if success_b else '❌ 失败'}")
    logger.info("=" * 80)
    
    if success_a and success_b:
        logger.info("🎉 所有数据蓄水任务完成！")
        return 0
    else:
        logger.warning("⚠️ 部分数据蓄水任务失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())