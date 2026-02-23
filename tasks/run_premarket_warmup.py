#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘前户口本模块 (Phase 6.1.2 - Tushare Pro)
=============================================
每日08:30自动拉取全市场基础数据，构建"股票户口本"

功能：
1. 全市场股票基础信息（stock_basic）
2. 昨日收盘价（pre_close）
3. 流通股本（float_share）
4. 板块/概念分类（industry）
5. 停牌/ST标记（list_status, name标记）
6. 数据存储到 data/reference/daily_stock_profile_YYYYMMDD.json
7. 数据更新机制（避免重复拉取）

Usage:
    python tasks/run_premarket_warmup.py
    python tasks/run_premarket_warmup.py --date 20260221
    python tasks/run_premarket_warmup.py --force  # 强制刷新

Schedule:
    每天早上08:30自动运行（通过Windows任务计划程序或crontab）

Author: AI开发专家
Date: 2026-02-23
Version: 6.1.2
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from logic.data_providers.tushare_provider import TushareProvider, get_tushare_provider

# 导入logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)


class PremarketWarmupManager:
    """
    盘前户口本管理器
    =================
    负责每日盘前数据拉取和存储
    """
    
    # 数据存储路径
    REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
    
    def __init__(self, provider: Optional[TushareProvider] = None):
        """
        初始化管理器
        
        Args:
            provider: TushareProvider实例，如未提供则自动创建
        """
        self.provider = provider or get_tushare_provider()
        self.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_stocks': 0,
            'success_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'start_time': None,
            'end_time': None
        }
    
    def get_profile_path(self, date: str) -> Path:
        """
        获取指定日期的户口本文件路径
        
        Args:
            date: 日期（YYYYMMDD）
        
        Returns:
            Path: 文件路径
        """
        return self.REFERENCE_DIR / f"daily_stock_profile_{date}.json"
    
    def check_exists(self, date: str) -> bool:
        """
        检查指定日期的户口本是否已存在
        
        Args:
            date: 日期（YYYYMMDD）
        
        Returns:
            bool: 是否存在
        """
        profile_path = self.get_profile_path(date)
        if not profile_path.exists():
            return False
        
        try:
            # 检查文件内容是否完整
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查必要字段
            if 'stocks' not in data or 'metadata' not in data:
                return False
            
            stock_count = len(data['stocks'])
            if stock_count < 1000:  # A股至少有1000+只股票
                logger.warning(f"[Warmup] ⚠️ 已有数据但股票数量异常: {stock_count}")
                return False
            
            logger.info(f"[Warmup] ✅ 发现已有户口本: {date}，共{stock_count}只股票")
            return True
            
        except Exception as e:
            logger.warning(f"[Warmup] ⚠️ 读取已有户口本失败: {e}")
            return False
    
    def fetch_stock_basic(self) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息
        
        Returns:
            Dict: 以ts_code为key的基础信息字典
        """
        logger.info("[Warmup] 📊 开始获取股票基础信息...")
        
        try:
            df_basic = self.provider.get_stock_basic(list_status='L')
            if df_basic is None or df_basic.empty:
                logger.error("[Warmup] ❌ 获取股票基础信息失败")
                return None
            
            # 转换为字典，以ts_code为key
            stocks = {}
            for _, row in df_basic.iterrows():
                ts_code = row['ts_code']
                stocks[ts_code] = {
                    'ts_code': ts_code,
                    'symbol': row.get('symbol', ''),
                    'name': row.get('name', ''),
                    'area': row.get('area', ''),
                    'industry': row.get('industry', ''),
                    'fullname': row.get('fullname', ''),
                    'enname': row.get('enname', ''),
                    'cnspell': row.get('cnspell', ''),
                    'market': row.get('market', ''),
                    'exchange': row.get('exchange', ''),
                    'curr_type': row.get('curr_type', ''),
                    'list_status': row.get('list_status', 'L'),
                    'list_date': row.get('list_date', ''),
                    'delist_date': row.get('delist_date', ''),
                    'is_hs': row.get('is_hs', ''),
                    # ST标记检测
                    'is_st': 'ST' in str(row.get('name', '')) or '*ST' in str(row.get('name', '')),
                }
            
            logger.info(f"[Warmup] ✅ 获取基础信息成功，共{len(stocks)}只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"[Warmup] ❌ 获取基础信息异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_daily_data(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """
        获取日线数据（昨收价等）
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
        
        Returns:
            Dict: 以ts_code为key的日线数据字典
        """
        logger.info(f"[Warmup] 📈 开始获取日线数据: {trade_date}...")
        
        try:
            df_daily = self.provider.get_daily_all(trade_date)
            if df_daily is None or df_daily.empty:
                logger.error(f"[Warmup] ❌ 获取日线数据失败: {trade_date}")
                return None
            
            daily_data = {}
            for _, row in df_daily.iterrows():
                ts_code = row['ts_code']
                daily_data[ts_code] = {
                    'pre_close': float(row.get('pre_close', 0)),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'change': float(row.get('change', 0)),
                    'pct_chg': float(row.get('pct_chg', 0)),
                    'vol': float(row.get('vol', 0)),
                    'amount': float(row.get('amount', 0)),
                }
            
            logger.info(f"[Warmup] ✅ 获取日线数据成功，共{len(daily_data)}条")
            return daily_data
            
        except Exception as e:
            logger.error(f"[Warmup] ❌ 获取日线数据异常: {e}")
            return None
    
    def fetch_daily_basic(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """
        获取每日指标（流通股本等）
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
        
        Returns:
            Dict: 以ts_code为key的每日指标字典
        """
        logger.info(f"[Warmup] 📊 开始获取每日指标: {trade_date}...")
        
        try:
            df_basic = self.provider.get_daily_basic_all(trade_date)
            if df_basic is None or df_basic.empty:
                logger.error(f"[Warmup] ❌ 获取每日指标失败: {trade_date}")
                return None
            
            basic_data = {}
            for _, row in df_basic.iterrows():
                ts_code = row['ts_code']
                basic_data[ts_code] = {
                    'float_share': float(row.get('float_share', 0)),  # 流通股本（万股）
                    'total_share': float(row.get('total_share', 0)),  # 总股本（万股）
                    'free_share': float(row.get('free_share', 0)),    # 自由流通股本（万股）
                    'circ_mv': float(row.get('circ_mv', 0)),          # 流通市值（万元）
                    'total_mv': float(row.get('total_mv', 0)),        # 总市值（万元）
                    'turnover_rate': float(row.get('turnover_rate', 0)),
                    'turnover_rate_f': float(row.get('turnover_rate_f', 0)),
                    'volume_ratio': float(row.get('volume_ratio', 0)),
                    'pe': float(row.get('pe', 0)) if pd.notna(row.get('pe')) else None,
                    'pe_ttm': float(row.get('pe_ttm', 0)) if pd.notna(row.get('pe_ttm')) else None,
                    'pb': float(row.get('pb', 0)) if pd.notna(row.get('pb')) else None,
                    'ps': float(row.get('ps', 0)) if pd.notna(row.get('ps')) else None,
                }
            
            logger.info(f"[Warmup] ✅ 获取每日指标成功，共{len(basic_data)}条")
            return basic_data
            
        except Exception as e:
            logger.error(f"[Warmup] ❌ 获取每日指标异常: {e}")
            return None
    
    def merge_stock_data(
        self,
        stocks: Dict[str, Any],
        daily_data: Dict[str, Any],
        basic_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并各类数据
        
        Args:
            stocks: 基础信息字典
            daily_data: 日线数据字典
            basic_data: 每日指标字典
        
        Returns:
            Dict: 合并后的完整数据
        """
        merged = {}
        
        for ts_code, stock_info in stocks.items():
            merged[ts_code] = stock_info.copy()
            
            # 合并日线数据
            if ts_code in daily_data:
                merged[ts_code].update(daily_data[ts_code])
            else:
                merged[ts_code].update({
                    'pre_close': None,
                    'open': None,
                    'high': None,
                    'low': None,
                    'close': None,
                    'change': None,
                    'pct_chg': None,
                    'vol': None,
                    'amount': None,
                })
                self.stats['failed_count'] += 1
            
            # 合并每日指标
            if ts_code in basic_data:
                merged[ts_code].update(basic_data[ts_code])
            else:
                merged[ts_code].update({
                    'float_share': None,
                    'total_share': None,
                    'free_share': None,
                    'circ_mv': None,
                    'total_mv': None,
                    'turnover_rate': None,
                    'turnover_rate_f': None,
                    'volume_ratio': None,
                    'pe': None,
                    'pe_ttm': None,
                    'pb': None,
                    'ps': None,
                })
                self.stats['failed_count'] += 1
            
            self.stats['success_count'] += 1
        
        return merged
    
    def save_profile(self, date: str, data: Dict[str, Any]) -> bool:
        """
        保存户口本到文件
        
        Args:
            date: 日期（YYYYMMDD）
            data: 股票数据字典
        
        Returns:
            bool: 是否保存成功
        """
        profile_path = self.get_profile_path(date)
        
        try:
            # 构建输出结构
            output = {
                'metadata': {
                    'date': date,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'version': '6.1.2',
                    'source': 'Tushare Pro',
                    'total_stocks': len(data),
                    'data_types': [
                        'stock_basic',
                        'daily',
                        'daily_basic'
                    ]
                },
                'stocks': data
            }
            
            # 保存为JSON
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            # 计算文件大小
            file_size = profile_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"[Warmup] ✅ 户口本保存成功: {profile_path}")
            logger.info(f"[Warmup]    文件大小: {file_size_mb:.2f} MB")
            logger.info(f"[Warmup]    股票数量: {len(data)}")
            
            return True
            
        except Exception as e:
            logger.error(f"[Warmup] ❌ 保存户口本失败: {e}")
            return False
    
    def run_warmup(self, date: Optional[str] = None, force: bool = False) -> bool:
        """
        执行盘前预热
        
        Args:
            date: 指定日期，默认最近交易日
            force: 是否强制刷新（即使已存在）
        
        Returns:
            bool: 是否成功
        """
        self.stats['start_time'] = datetime.now()
        
        print("=" * 80)
        print("盘前户口本模块 (Phase 6.1.2 - Tushare Pro)")
        print("=" * 80)
        
        # 1. 确定日期
        if date is None:
            date = self.provider.get_latest_trade_date()
        
        print(f"\n📅 目标日期: {date}")
        print(f"🔄 强制刷新: {'是' if force else '否'}")
        
        # 2. 检查是否已存在
        if not force and self.check_exists(date):
            print(f"\n⏭️  户口本已存在，跳过拉取")
            print(f"   文件路径: {self.get_profile_path(date)}")
            self.stats['skipped_count'] = 1
            self.stats['end_time'] = datetime.now()
            return True
        
        print("\n📋 数据清单:")
        print("  1. 全市场股票基础信息（stock_basic）")
        print("  2. 昨日收盘价（pre_close）")
        print("  3. 流通股本（float_share）")
        print("  4. 板块/概念分类（industry）")
        print("  5. 停牌/ST标记（is_st）")
        
        print("\n🚀 开始拉取数据...")
        
        # 3. 获取各类数据
        # 3.1 基础信息
        stocks = self.fetch_stock_basic()
        if stocks is None:
            logger.error("[Warmup] ❌ 获取基础信息失败，终止")
            return False
        
        self.stats['total_stocks'] = len(stocks)
        
        # 3.2 日线数据
        daily_data = self.fetch_daily_data(date)
        if daily_data is None:
            logger.warning("[Warmup] ⚠️ 日线数据获取失败，使用空数据")
            daily_data = {}
        
        # 3.3 每日指标
        basic_data = self.fetch_daily_basic(date)
        if basic_data is None:
            logger.warning("[Warmup] ⚠️ 每日指标获取失败，使用空数据")
            basic_data = {}
        
        # 4. 合并数据
        print("\n🔄 合并数据...")
        merged_data = self.merge_stock_data(stocks, daily_data, basic_data)
        
        # 5. 保存数据
        print("\n💾 保存户口本...")
        success = self.save_profile(date, merged_data)
        
        self.stats['end_time'] = datetime.now()
        
        # 6. 打印统计
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 80)
        print("📊 执行统计")
        print("=" * 80)
        print(f"  总股票数: {self.stats['total_stocks']}")
        print(f"  成功合并: {self.stats['success_count']}")
        print(f"  数据缺失: {self.stats['failed_count']}")
        print(f"  执行时间: {duration:.2f}秒")
        print(f"  文件路径: {self.get_profile_path(date)}")
        
        if success:
            print("\n✅ 盘前户口本生成成功")
        else:
            print("\n❌ 盘前户口本生成失败")
        
        print("=" * 80)
        
        return success
    
    def get_profile(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的户口本数据
        
        Args:
            date: 日期，默认最近交易日
        
        Returns:
            Dict: 户口本数据，如果不存在则返回None
        """
        if date is None:
            date = self.provider.get_latest_trade_date()
        
        profile_path = self.get_profile_path(date)
        
        if not profile_path.exists():
            logger.warning(f"[Warmup] ⚠️ 户口本不存在: {date}")
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"[Warmup] ❌ 读取户口本失败: {e}")
            return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='盘前户口本模块 (Phase 6.1.2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tasks/run_premarket_warmup.py              # 拉取最近交易日数据
  python tasks/run_premarket_warmup.py --date 20260221  # 拉取指定日期
  python tasks/run_premarket_warmup.py --force      # 强制刷新（覆盖已有数据）
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='指定日期（YYYYMMDD格式），默认最近交易日'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制刷新，即使数据已存在也重新拉取'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='检查指定日期的户口本是否存在'
    )
    
    args = parser.parse_args()
    
    try:
        # 创建管理器
        manager = PremarketWarmupManager()
        
        # 检查模式
        if args.check:
            date = args.date or manager.provider.get_latest_trade_date()
            exists = manager.check_exists(date)
            print(f"\n📋 检查户口本: {date}")
            print(f"   状态: {'✅ 存在' if exists else '❌ 不存在'}")
            print(f"   路径: {manager.get_profile_path(date)}")
            return 0 if exists else 1
        
        # 执行预热
        success = manager.run_warmup(date=args.date, force=args.force)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
        return 130
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import pandas as pd  # 用于类型检查
    sys.exit(main())