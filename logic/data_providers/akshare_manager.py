#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare数据管理器 (V16.2 - 缓存+预热架构)

核心功能：
1. 强制缓存：所有接口调用前先查磁盘缓存
2. 双模式控制：warmup模式（允许联网）/readonly模式（只读缓存）
3. 限速保护：严格遵守200次/小时限制
4. TTL管理：不同数据类型有不同的有效期

数据类型：
1. 个股资金流 - stock_individual_fund_flow（近100日主力/超大单）
2. 龙虎榜 - stock_lhb_detail_em（每日详情）
3. 基本面指标 - stock_financial_analysis_indicator（财务指标）
4. 昨日涨停池 - stock_zt_pool_previous_em（昨日涨停）

V16.3变更：
- ❌ 已移除：个股新闻（stock_news_em）- 根据"资金为王，拒绝噪音"原则

Usage:
    # 盘前预热模式
    manager = AkShareDataManager(mode='warmup')
    manager.warmup_all()
    
    # 盘中只读模式
    manager = AkShareDataManager(mode='readonly')
    data = manager.get_fund_flow('600519')

Architecture:
    盘前预热（08:30-09:25）: 允许联网拉数据 → 写入缓存
    盘中扫描（09:30-15:00）: 只读缓存，绝不联网
    盘后复盘（17:00-20:00）: 允许联网拉数据 → 更新缓存

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.2
"""

import sys
import os
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime as dt_datetime, date as dt_date, timedelta as dt_timedelta
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[AkShareDataManager] ⚠️ akshare 未安装，缓存模式将无法使用")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[AkShareDataManager] ⚠️ pandas 未安装，缓存模式将无法使用")

from logic.utils.logger import get_logger
from logic.core.rate_limiter import get_rate_limiter
import random

logger = get_logger(__name__)


class PandasJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理pandas DataFrame和date对象"""

    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            # pandas DataFrame或Series
            return obj.to_dict()
        elif hasattr(pd, 'NaT') and obj is pd.NaT:
            # pandas NaT
            return None
        elif hasattr(pd, 'Timestamp') and isinstance(obj, pd.Timestamp):
            # pandas Timestamp
            if pd.isna(obj):
                return None
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, (dt_date, dt_datetime)):
            # Python date或datetime对象
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            # 可迭代对象（非字符串/字节）
            try:
                return list(obj)
            except TypeError:
                return str(obj)
        else:
            # 其他类型使用默认处理
            return super().default(obj)


class AkShareDataManager:
    """
    AkShare数据管理器（缓存+预热架构）
    
    核心原则：
    1. 盘中只读缓存，绝不联网
    2. 盘前预热模式，允许联网
    3. 限速保护，防止封IP
    4. TTL管理，数据有效性控制
    
    模式：
    - warmup: 预热模式，允许联网拉数据
    - readonly: 只读模式，只读缓存
    """
    
    def __init__(self, mode: str = 'readonly', cache_dir: str = 'data/ak_cache'):
        """
        初始化AkShare数据管理器

        Args:
            mode: 运行模式（'warmup'或'readonly'）
            cache_dir: 缓存目录
        """
        self.mode = mode
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # V16.4.0: 使用全局限流器（替代土制限速）
        self.limiter = get_rate_limiter()
        # 更新限速参数（针对AkShare优化）
        self.limiter.update_limits(
            max_requests_per_minute=60,
            max_requests_per_hour=2000,
            min_request_interval=0.1
        )

        # TTL配置（秒）
        self.ttl_config = {
            'fund_flow': 8 * 3600,  # 8小时（当日收盘前）
            'lhb_detail': 24 * 3600,  # 24小时（次日收盘前）
            'financial_indicator': 7 * 24 * 3600,  # 7天
            'limit_up_pool': 8 * 3600,  # 8小时（当日收盘前）
        }

        print(f"[AkShareDataManager] ✅ 初始化完成，模式: {self.mode}, 缓存目录: {self.cache_dir}")
    
    def _check_rate_limit(self) -> None:
        """
        检查并执行限速保护（V16.4.0: 使用RateLimiter）

        功能：
        1. 随机延迟（防WAF指纹识别）
        2. 限流器检查（自动等待）
        3. 记录请求
        """
        if self.mode == 'readonly':
            return  # 只读模式不限速

        # V16.4.0: 1. 强制随机延迟（防WAF指纹识别）
        time.sleep(random.uniform(0.1, 0.3))

        # V16.4.0: 2. 限流器检查（自动等待）
        self.limiter.wait_if_needed(url="akshare")
        self.limiter.record_request(url="akshare")
    
    def _get_cache_key(self, data_type: str, code: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            data_type: 数据类型
            code: 股票代码
            **kwargs: 其他参数
        
        Returns:
            str: 缓存键
        """
        # 组合所有参数
        params = f"{data_type}_{code}"
        for k, v in sorted(kwargs.items()):
            params += f"_{k}_{v}"
        
        # 生成哈希
        return hashlib.md5(params.encode('utf-8')).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            cache_key: 缓存键
        
        Returns:
            Path: 缓存文件路径
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def _read_cache(self, cache_key: str) -> Optional[Dict]:
        """
        读取缓存
        
        Args:
            cache_key: 缓存键
        
        Returns:
            Optional[Dict]: 缓存数据，如果不存在或过期返回None
        """
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查TTL
            fetch_time = cache_data.get('fetch_time', 0)
            data_type = cache_data.get('data_type', '')
            ttl = self.ttl_config.get(data_type, 3600)
            
            if time.time() - fetch_time > ttl:
                logger.debug(f"[AkShareDataManager] 缓存过期: {cache_key}")
                return None
            
            return cache_data
        except Exception as e:
            logger.warning(f"[AkShareDataManager] 读取缓存失败: {e}")
            return None
    
    def _write_cache(self, cache_key: str, data_type: str, data: Any) -> None:
        """
        写入缓存

        Args:
            cache_key: 缓存键
            data_type: 数据类型
            data: 数据
        """
        cache_file = self._get_cache_file(cache_key)

        try:
            cache_data = {
                'data_type': data_type,
                'fetch_time': time.time(),
                'data': data,
                'cache_key': cache_key
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2, cls=PandasJSONEncoder)

            logger.debug(f"[AkShareDataManager] 缓存写入成功: {cache_key}")
        except Exception as e:
            logger.error(f"[AkShareDataManager] 写入缓存失败: {e} (file: {cache_file})")
    
    def get_fund_flow(self, code: str, days: int = 100) -> Optional[Dict]:
        """
        获取个股资金流（带缓存）

        Args:
            code: 股票代码
            days: 天数

        Returns:
            Optional[Dict]: 资金流数据，如果缓存不存在返回None
        """
        cache_key = self._get_cache_key('fund_flow', code, days=days)

        # 尝试读取缓存
        cached_data = self._read_cache(cache_key)
        if cached_data is not None:
            return cached_data['data']

        # 只读模式：缓存不存在返回None
        if self.mode == 'readonly':
            logger.debug(f"[AkShareDataManager] 只读模式：资金流缓存不存在 {code}")
            return None

        # 预热模式：联网拉取
        if not AKSHARE_AVAILABLE:
            logger.warning("[AkShareDataManager] akshare 未安装")
            return None

        try:
            self._check_rate_limit()

            # 解析股票代码和市场
            # code格式: "600000.SH" 或 "000001.SZ"
            if '.' in code:
                stock_code, market = code.split('.')
                market = market.lower()  # sh, sz
            else:
                # 如果没有后缀，默认为sh
                stock_code = code
                market = 'sh'

            # 拉取数据（正确的API签名）
            df = ak.stock_individual_fund_flow(stock=stock_code, market=market)

            # 检查数据是否为空
            if df is None or df.empty:
                logger.warning(f"[AkShareDataManager] 资金流数据为空: {code}")
                return None

            # 写入缓存
            self._write_cache(cache_key, 'fund_flow', df)

            return df.to_dict()
        except Exception as e:
            logger.warning(f"[AkShareDataManager] 获取资金流失败 {code}: {e}")
            return None
    
    def get_lhb_detail(self, date: str = None) -> Optional[List[Dict]]:
        """
        获取龙虎榜详情（带缓存和数据清洗）

        数据清洗：提取核心字段，过滤无关信息

        Args:
            date: 日期（YYYYMMDD），默认为最近一个交易日

        Returns:
            Optional[List[Dict]]: 清洗后的龙虎榜数据，如果缓存不存在返回None
        """
        if date is None:
            date = (dt_datetime.now() - dt_timedelta(days=1)).strftime('%Y%m%d')

        cache_key = self._get_cache_key('lhb_detail', date)

        # 尝试读取缓存
        cached_data = self._read_cache(cache_key)
        if cached_data is not None:
            return cached_data['data']

        # 只读模式：缓存不存在返回None
        if self.mode == 'readonly':
            logger.debug(f"[AkShareDataManager] 只读模式：龙虎榜缓存不存在 {date}")
            return None

        # 预热模式：联网拉取
        if not AKSHARE_AVAILABLE:
            logger.warning("[AkShareDataManager] akshare 未安装")
            return None

        try:
            self._check_rate_limit()

            # 拉取数据（正确的API签名：使用start_date和end_date）
            df = ak.stock_lhb_detail_em(start_date=date, end_date=date)

            # 检查数据是否为空
            if df is None or df.empty:
                logger.warning(f"[AkShareDataManager] 龙虎榜数据为空: {date}")
                return None

            # ========== 数据清洗：提取核心字段 ==========
            # 核心字段列表（根据CTO要求）
            core_columns = [
                '代码',           # 股票代码
                '名称',           # 股票名称
                '上榜日',         # 上榜日期
                '解读',           # 解读分析
                '龙虎榜净买额',   # 净买入额
                '龙虎榜买入额',   # 买入额
                '龙虎榜卖出额',   # 卖出额
                '龙虎榜成交额',   # 成交额
                '上榜原因',       # 上榜原因
                '上榜后1日',      # 后1日表现
                '上榜后2日',      # 后2日表现
                '上榜后5日',      # 后5日表现
                '上榜后10日'      # 后10日表现
            ]

            # 检查核心字段是否存在
            available_columns = [col for col in core_columns if col in df.columns]
            if len(available_columns) < len(core_columns):
                missing = set(core_columns) - set(available_columns)
                logger.warning(f"[AkShareDataManager] 龙虎榜数据字段缺失: {missing}")

            # 只保留核心字段
            df_cleaned = df[available_columns].copy()

            # 写入缓存
            self._write_cache(cache_key, 'lhb_detail', df_cleaned)

            logger.info(f"[AkShareDataManager] ✅ 龙虎榜数据获取成功: {date}, {len(df_cleaned)}只股票, {len(available_columns)}个核心字段")

            return df_cleaned.to_dict()
        except Exception as e:
            logger.warning(f"[AkShareDataManager] 获取龙虎榜失败 {date}: {e}")
            return None
    
    def get_financial_indicator(self, code: str) -> Optional[Dict]:
        """
        获取基本面指标（带缓存和降级策略）

        降级策略：
        1. 优先使用 stock_financial_analysis_indicator（详细指标）
        2. 失败时降级到 stock_financial_abstract（简略指标）
        3. 两者都失败时返回 None，并标记数据缺失

        Args:
            code: 股票代码

        Returns:
            Optional[Dict]: 基本面数据，包含 data_source 标识来源
        """
        cache_key = self._get_cache_key('financial_indicator', code)

        # 尝试读取缓存
        cached_data = self._read_cache(cache_key)
        if cached_data is not None:
            return cached_data['data']

        # 只读模式：缓存不存在返回None
        if self.mode == 'readonly':
            logger.debug(f"[AkShareDataManager] 只读模式：基本面缓存不存在 {code}")
            return None

        # 预热模式：联网拉取
        if not AKSHARE_AVAILABLE:
            logger.warning("[AkShareDataManager] akshare 未安装")
            return None

        # 提取纯数字代码（移除市场后缀）
        symbol = code.split('.')[0] if '.' in code else code

        # ========== 策略1：尝试获取详细指标 ==========
        try:
            self._check_rate_limit()
            df = ak.stock_financial_analysis_indicator(symbol=symbol)

            if df is not None and not df.empty:
                # 添加数据来源标识
                result = df.to_dict()
                result['_metadata'] = {
                    'data_source': 'stock_financial_analysis_indicator',
                    'symbol': symbol,
                    'timestamp': dt_datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self._write_cache(cache_key, 'financial_indicator', df)
                logger.info(f"[AkShareDataManager] ✅ 基本面指标获取成功（详细模式）: {code}")
                return result
        except Exception as e:
            logger.warning(f"[AkShareDataManager] ⚠️ 详细指标获取失败，启用降级策略: {code} - {e}")

        # ========== 策略2：降级到简略指标 ==========
        try:
            self._check_rate_limit()
            df = ak.stock_financial_abstract(symbol=symbol)

            if df is not None and not df.empty:
                # 添加数据来源标识
                result = df.to_dict()
                result['_metadata'] = {
                    'data_source': 'stock_financial_abstract (降级模式)',
                    'symbol': symbol,
                    'timestamp': dt_datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'warning': '使用降级数据源，指标可能不完整'
                }
                self._write_cache(cache_key, 'financial_indicator', df)
                logger.info(f"[AkShareDataManager] ✅ 基本面指标获取成功（降级模式）: {code}")
                return result
            else:
                logger.warning(f"[AkShareDataManager] ⚠️ 降级数据源返回空: {code}")
        except Exception as e:
            logger.error(f"[AkShareDataManager] ❌ 降级数据源也失败: {code} - {e}")

        # ========== 策略3：数据缺失警告 ==========
        logger.error(f"[AkShareDataManager] ⛔ FUNDAMENTAL DATA MISSING: {code} - 所有数据源均失败")
        return None
    
    def get_limit_up_pool(self, date: str = None) -> Optional[List[str]]:
        """
        获取昨日涨停池（带缓存）

        Args:
            date: 日期（YYYYMMDD），默认为昨日

        Returns:
            Optional[List[str]]: 涨停股票代码列表，如果缓存不存在返回None
        """
        if date is None:
            date = (dt_datetime.now() - dt_timedelta(days=1)).strftime('%Y%m%d')

        cache_key = self._get_cache_key('limit_up_pool', date)
        
        # 尝试读取缓存
        cached_data = self._read_cache(cache_key)
        if cached_data is not None:
            return cached_data['data']
        
        # 只读模式：缓存不存在返回None
        if self.mode == 'readonly':
            logger.debug(f"[AkShareDataManager] 只读模式：涨停池缓存不存在 {date}")
            return None
        
        # 预热模式：联网拉取
        if not AKSHARE_AVAILABLE:
            logger.warning("[AkShareDataManager] akshare 未安装")
            return None
        
        try:
            self._check_rate_limit()
            
            # 拉取数据
            df = ak.stock_zt_pool_previous_em(date=date)
            
            if not df.empty:
                codes = df['代码'].tolist()
                self._write_cache(cache_key, 'limit_up_pool', codes)
                return codes
            
            return None
        except Exception as e:
            logger.warning(f"[AkShareDataManager] 获取涨停池失败 {date}: {e}")
            return None
    
    def warmup_all(self, stock_list: List[str] = None) -> Dict[str, Any]:
        """
        预热所有数据（盘前调用）
        
        Args:
            stock_list: 股票代码列表（用于预热个股数据）
        
        Returns:
            Dict: 预热报告
        """
        print("[AkShareDataManager] 🚀 开始预热所有数据...")
        
        report = {
            'fund_flow': {'success': 0, 'failed': 0},
            'lhb_detail': {'success': 0, 'failed': 0},
            'financial_indicator': {'success': 0, 'failed': 0},
            'limit_up_pool': {'success': 0, 'failed': 0},
        }
        
        # 预热涨停池
        print("[AkShareDataManager] 1️⃣ 预热涨停池...")
        if self.get_limit_up_pool() is not None:
            report['limit_up_pool']['success'] = 1
        else:
            report['limit_up_pool']['failed'] = 1
        
        # 预热龙虎榜
        print("[AkShareDataManager] 2️⃣ 预热龙虎榜...")
        if self.get_lhb_detail() is not None:
            report['lhb_detail']['success'] = 1
        else:
            report['lhb_detail']['failed'] = 1
        
        # 预热个股数据（如果有股票列表）
        if stock_list:
            print(f"[AkShareDataManager] 3️⃣ 预热个股数据（{len(stock_list)}只股票）...")
            
            # 🔥 [V16.2.1 修复] 删除硬编码限制，预热所有股票
            # 增加进度显示
            total = len(stock_list)
            for i, code in enumerate(stock_list, 1):
                # 每处理10只股票打印一次进度
                if i % 10 == 0:
                    print(f"[AkShareDataManager] 进度: {i}/{total} ({i/total*100:.0f}%)")
                
                # 预热资金流
                if self.get_fund_flow(code) is not None:
                    report['fund_flow']['success'] += 1
                else:
                    report['fund_flow']['failed'] += 1
                
                # 预热基本面
                if self.get_financial_indicator(code) is not None:
                    report['financial_indicator']['success'] += 1
                else:
                    report['financial_indicator']['failed'] += 1
            
            print(f"[AkShareDataManager] ✅ 个股数据预热完成: {total}只股票")
        
        # 保存预热报告
        report_file = self.cache_dir / 'warmup_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[AkShareDataManager] ✅ 预热完成，报告已保存: {report_file}")
        
        return report


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("AkShareDataManager 测试")
    print("=" * 80)
    
    # 1. 预热模式测试
    print("\n🚀 预热模式测试:")
    manager = AkShareDataManager(mode='warmup')
    
    # 预热涨停池
    limit_up_pool = manager.get_limit_up_pool()
    if limit_up_pool:
        print(f"  ✅ 涨停池: {len(limit_up_pool)}只股票")
    else:
        print(f"  ❌ 涨停池: 获取失败")
    
    # 2. 只读模式测试
    print("\n🔒 只读模式测试:")
    manager = AkShareDataManager(mode='readonly')
    
    # 读取涨停池（从缓存）
    limit_up_pool = manager.get_limit_up_pool()
    if limit_up_pool:
        print(f"  ✅ 涨停池（缓存）: {len(limit_up_pool)}只股票")
    else:
        print(f"  ❌ 涨停池（缓存）: 缓存不存在")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
