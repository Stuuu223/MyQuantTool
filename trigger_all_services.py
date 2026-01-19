#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 一键激活脚本
用于强制点火所有服务，确保物理目录、数据缓存全部初始化
"""

import os
import sys
from datetime import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def init_directories():
    """
    初始化物理目录结构
    
    Returns:
        bool: 是否成功
    """
    logger.info("📁 正在初始化物理目录结构...")
    
    dirs = [
        "data/review_cases/golden_cases",
        "logs",
        "config",
        "data/kline_cache",
        "data/history"
    ]
    
    success = True
    for d in dirs:
        if not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
                logger.info(f"✅ 已创建目录: {d}")
            except Exception as e:
                logger.error(f"❌ 创建目录失败 {d}: {e}")
                success = False
        else:
            logger.info(f"✅ 目录已存在: {d}")
    
    return success


def ignite_review_engine(date_str=None):
    """
    点火复盘引擎，捕获今日/昨日案例
    
    Args:
        date_str: 日期字符串，格式 YYYYMMDD，默认为今天
    
    Returns:
        dict: 捕获的案例数据
    """
    logger.info("🔥 正在点火复盘引擎...")
    
    try:
        from logic.review_manager import ReviewManager
        rm = ReviewManager()
        
        # 如果没有指定日期，使用今天
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        # 运行每日复盘
        logger.info(f"📊 正在执行 {date_str} 的每日复盘...")
        rm.run_daily_review(date=date_str)
        
        # 捕获高价值案例
        logger.info(f"🎯 正在捕获高价值案例...")
        cases = rm.capture_golden_cases(date_str)
        
        if cases:
            logger.info(f"✅ 成功捕获 {cases['date']} 的高价值案例！")
            logger.info(f"   - 真龙: {len(cases['dragons'])} 只")
            logger.info(f"   - 大坑: {len(cases['traps'])} 只")
            logger.info(f"   - 市场情绪评分: {cases['market_score']}")
            return cases
        else:
            logger.warning("⚠️ 未捕获到高价值案例")
            return None
            
    except Exception as e:
        logger.error(f"❌ 点火复盘引擎失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def ignite_data_adapter():
    """
    点火数据适配器，预热 DDE 缓存
    
    Returns:
        bool: 是否成功
    """
    logger.info("📡 正在预热全市场资金流数据，请稍候...")
    
    try:
        from logic.data_adapter_akshare import MoneyFlowAdapter
        
        # 模拟调用一次触发全榜抓取
        # 使用一个常见的股票代码来测试
        test_codes = ['000001', '600519']
        result = MoneyFlowAdapter.batch_get_dde(test_codes)
        
        if result:
            logger.info(f"✅ 数据源点火成功！预热了 {len(result)} 只股票的 DDE 数据")
            return True
        else:
            logger.warning("⚠️ 数据源点火失败，未获取到 DDE 数据")
            return False
            
    except Exception as e:
        logger.error(f"❌ 点火数据适配器失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def ignite_database():
    """
    点火数据库，确保数据库连接正常
    
    Returns:
        bool: 是否成功
    """
    logger.info("🗄️ 正在检查数据库连接...")
    
    try:
        from logic.database_manager import get_db_manager
        
        db = get_db_manager()
        
        # 测试数据库查询
        sql = "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
        result = db.sqlite_query(sql)
        
        if result:
            logger.info(f"✅ 数据库连接正常，发现 {len(result)} 个表")
            return True
        else:
            logger.warning("⚠️ 数据库连接正常，但没有发现表")
            return False
            
    except Exception as e:
        logger.error(f"❌ 点火数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_system_health():
    """
    检查系统健康状态
    
    Returns:
        dict: 系统健康状态
    """
    logger.info("🏥 正在检查系统健康状态...")
    
    health = {
        "directories": False,
        "review_engine": False,
        "data_adapter": False,
        "database": False,
        "overall": False
    }
    
    # 检查目录
    if os.path.exists("data/review_cases/golden_cases"):
        health["directories"] = True
        logger.info("✅ 目录结构正常")
    else:
        logger.warning("⚠️ 目录结构异常")
    
    # 检查数据库
    if os.path.exists("data/stock_data.db"):
        health["database"] = True
        logger.info("✅ 数据库文件存在")
    else:
        logger.warning("⚠️ 数据库文件不存在")
    
    # 检查配置文件
    if os.path.exists("config.json"):
        logger.info("✅ 配置文件存在")
    else:
        logger.warning("⚠️ 配置文件不存在")
    
    # 计算整体健康状态
    all_checks = [health["directories"], health["database"]]
    health["overall"] = all(all_checks)
    
    return health


def main():
    """
    主函数：一键激活所有服务
    """
    print("=" * 60)
    print("🦁 MyQuantTool V18.7 服务激活中...")
    print("=" * 60)
    
    # 1. 物理目录初始化
    print("\n📁 步骤 1/5: 初始化物理目录结构")
    dir_success = init_directories()
    
    # 2. 点火数据库
    print("\n🗄️ 步骤 2/5: 点火数据库")
    db_success = ignite_database()
    
    # 3. 点火数据适配器
    print("\n📡 步骤 3/5: 预热数据适配器")
    adapter_success = ignite_data_adapter()
    
    # 4. 捕获今日/昨日案例 (点火复盘引擎)
    print("\n🔥 步骤 4/5: 点火复盘引擎")
    cases = ignite_review_engine()
    
    # 5. 检查系统健康状态
    print("\n🏥 步骤 5/5: 检查系统健康状态")
    health = check_system_health()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 服务激活总结")
    print("=" * 60)
    print(f"✅ 目录结构: {'正常' if dir_success else '异常'}")
    print(f"✅ 数据库: {'正常' if db_success else '异常'}")
    print(f"✅ 数据适配器: {'正常' if adapter_success else '异常'}")
    print(f"✅ 复盘引擎: {'正常' if cases else '异常'}")
    print(f"✅ 系统整体: {'正常' if health['overall'] else '异常'}")
    
    if health['overall']:
        print("\n🚀 所有服务准备就绪。指挥官，请运行 Streamlit 界面启动战斗！")
        print("   启动命令: streamlit run ui/v18_full_spectrum.py")
        return 0
    else:
        print("\n⚠️ 部分服务未就绪，请检查日志并修复问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())