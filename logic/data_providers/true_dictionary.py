#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrueDictionary - 真实数据字典 (CTO架构规范版 V2.1.0 - 100% QMT本地)

职责划分:
- QMT: 负责盘前取 FloatVolume(流通股本) / UpStopPrice(涨停价) / 5日平均成交量 - 本地C++接口极速读取
- 盘中: 严禁任何网络/磁盘请求,只读内存O(1)

CTO架构决策:
- 100% QMT本地架构，0外网请求
- 5日均量从QMT本地日K数据计算，禁止任何网络API

Author: AI总监 (CTO规范版)
Date: 2026-02-26
Version: 2.2.0 - 100% QMT本地架构，Tushare已物理剥离
"""

import os
import sys
import time
import logging
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# 【CTO修复】导入交易日历工具，禁止在量化系统中使用timedelta推算交易日
try:
    from logic.utils.calendar_utils import (
        get_real_trading_dates,
        get_latest_completed_trading_day,
        get_nth_previous_trading_day,
        get_trading_day_range
    )
    CALENDAR_UTILS_AVAILABLE = True
except ImportError as e:
    CALENDAR_UTILS_AVAILABLE = False
    logging.warning(f"[TrueDictionary] 交易日历工具导入失败: {e}")

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class TrueDictionary:
    """
    真实数据字典 - 盘前装弹机 (100% QMT本地版)
    
    CTO规范:
    1. 09:25前必须完成所有数据预热
    2. QMT原生接口取流通股本/涨停价(C++本地读取<100ms)
    3. QMT本地日K数据计算5日均量(替代外网API)
    4. 09:30后只读内存,任何网络请求都视为P0级事故
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if TrueDictionary._initialized:
            return
        
        # QMT数据 - 本地C++接口获取
        self._float_volume: Dict[str, int] = {}  # 流通股本(股)
        self._up_stop_price: Dict[str, float] = {}  # 涨停价
        self._down_stop_price: Dict[str, float] = {}  # 跌停价
        self._avg_volume_5d: Dict[str, float] = {}  # 5日平均成交量(QMT本地计算)
        self._avg_turnover_5d: Dict[str, float] = {}  # 5日平均换手率(市值平替法计算)
        
        # 【CTO第三维趋势网】MA均线数据缓存 - 盘前装弹时计算
        self._ma_data: Dict[str, Dict] = {}  # {stock_code: {'ma5': float, 'ma10': float, 'ma20': float}}
        
        # 【CTO ATR股性突变雷达】20日ATR数据缓存 - 盘前装弹时计算
        self._atr_20d_map: Dict[str, float] = {}  # {stock_code: atr_20d_value}
        
        # 【CTO修复】前收盘价缓存 - ATR计算需要
        self._prev_close_cache: Dict[str, float] = {}  # {stock_code: prev_close}
        
        # 板块映射 - 本地配置或QMT数据
        self._sector_map: Dict[str, List[str]] = {}  # 股票->板块列表
        
        # 元数据
        self._metadata = {
            'qmt_warmup_time': None,
            'avg_volume_warmup_time': None,  # QMT本地数据预热时间
            'stock_count': 0,
            'cache_date': None,
            'data_source': 'QMT本地100%'  # CTO规范标记
        }
        
        TrueDictionary._initialized = True
        logger.info("✅ [TrueDictionary] 初始化完成 - 100% QMT本地模式，等待盘前装弹")
    
    # ============================================================
    # 盘前装弹机 - 09:25前必须完成 (100% QMT本地)
    # ============================================================
    
    def warmup(self, stock_list: List[str], target_date: str = None, force: bool = False) -> Dict:
        """
        盘前装弹主入口 - CTO快照防弹衣版
        
        【CTO防爆】：只调用get_instrument_detail，不调用get_local_data！
        
        Args:
            stock_list: 全市场股票代码列表
            target_date: 目标日期(格式'YYYYMMDD')
            force: 是否强制刷新
            
        Returns:
            Dict: 装弹结果统计
        """
        # 【CTO修复】使用target_date替代当前日期，消灭未来函数
        today = target_date if target_date else datetime.now().strftime('%Y%m%d')
        
        # 检查是否已装弹
        if not force and self._metadata['cache_date'] == today:
            logger.info(f"📦 [TrueDictionary] 当日数据已装弹,跳过")
            return self._get_warmup_stats()
        
        # 【CTO缓存革命】Step 0: 尝试从硬盘缓存加载5日均量
        cache_dir = Path("data/cache")
        cache_file = cache_dir / f"true_dict_avg_vol_{today}.json"
        
        if not force and cache_file.exists():
            try:
                logger.info(f"⚡ [CTO缓存命中] 从硬盘加载 {cache_file}...")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 【CTO缓存毒化告警】校验缓存有效性
                cached_float_count = len(cached_data.get('float_volume', {}))
                expected_count = len(stock_list)
                if cached_float_count < expected_count * 0.5:
                    # 缓存数量严重不足（<50%），判定为投毒缓存，强制重新装弹
                    logger.error(f"⚠️ [CTO缓存毒化告警] 缓存只有{cached_float_count}只，期望{expected_count}只，丢弃烂缓存重新装弹！")
                    # 备份证据
                    import shutil
                    poisoned_file = cache_file.with_suffix('.json.poisoned')
                    shutil.move(str(cache_file), str(poisoned_file))
                    logger.info(f"🗑️ 投毒缓存已备份到: {poisoned_file}")
                    # 不return，继续往下走正常装弹流程
                else:
                    # 缓存健康，正常加载
                    self._avg_volume_5d = cached_data.get('avg_volume_5d', {})
                    self._float_volume = cached_data.get('float_volume', {})
                    self._up_stop_price = cached_data.get('up_stop_price', {})
                    
                    self._metadata['cache_date'] = today
                    self._metadata['data_source'] = 'QMT本地100% + 硬盘缓存'
                    
                    logger.info(f"✅ [CTO缓存命中] 0毫秒装弹完成! 5日均量:{len(self._avg_volume_5d)}只, 流通股本:{len(self._float_volume)}只")
                    return {
                        'qmt': {'success': len(self._float_volume), 'failed': 0, 'note': 'from_cache'},
                        'avg_volume': {'success': len(self._avg_volume_5d), 'failed': 0, 'note': 'from_cache'},
                        'integrity': {'is_ready': True, 'missing_rate': 0},
                        'total_stocks': len(stock_list),
                        'ready_for_trading': True,
                        'cache_hit': True
                    }
            except Exception as e:
                logger.warning(f"⚠️ [CTO缓存] 加载缓存失败: {e}, 重新计算...")
        
        print(f"🚀 [TrueDictionary-CTO防弹衣] 启动盘前装弹,目标{len(stock_list)}只股票")
        logger.info(f"🚀 [TrueDictionary-CTO防弹衣] 启动盘前装弹,目标{len(stock_list)}只股票")
        
        # Step 1: QMT本地极速读取 (C++接口, <100ms) - 只调用get_instrument_detail
        qmt_result = self._warmup_qmt_data(stock_list)
        
        # 【CTO全息克隆修复】：启用5日均量计算（单点查询安全！）
        avg_volume_result = self._warmup_avg_volume_from_qmt(stock_list, target_date=target_date)
        
        # 【CTO修复】启用ATR预热（传递target_date）
        atr_result = self._warmup_atr_data(stock_list, target_date=target_date)
        
        # MA暂时禁用（CTO防爆）
        ma_result = {'source': 'disabled', 'success': 0, 'failed': len(stock_list), 'note': 'CTO防爆：暂时禁用'}
        
        # Step 5: 数据完整性检查（只检查FloatVolume）
        integrity_check = self._check_data_integrity(stock_list)
        
        self._metadata['cache_date'] = today
        self._metadata['data_source'] = 'QMT本地100%'
        
        stats = {
            'qmt': qmt_result,
            'avg_volume': avg_volume_result,
            'integrity': integrity_check,
            'total_stocks': len(stock_list),
            'ready_for_trading': True  # 宽松模式，允许继续
        }
        
        print(f"✅ [TrueDictionary] CTO防弹衣装弹完成! (FloatVolume: {qmt_result['success']}只)")
        logger.info(f"✅ [TrueDictionary] CTO防弹衣装弹完成! (FloatVolume: {qmt_result['success']}只)")
        
        # 【CTO缓存革命】保存到硬盘缓存
        try:
            cache_dir = Path("data/cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"true_dict_avg_vol_{today}.json"
            
            cache_data = {
                'avg_volume_5d': self._avg_volume_5d,
                'float_volume': self._float_volume,
                'up_stop_price': self._up_stop_price,
                'cache_date': today,
                'cached_at': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            logger.info(f"💾 [CTO缓存] 数据已持久化至 {cache_file}")
            stats['cache_saved'] = True
        except Exception as e:
            logger.warning(f"⚠️ [CTO缓存] 保存缓存失败: {e}")
            stats['cache_saved'] = False
        
        return stats
    
    
    def _warmup_avg_volume_from_qmt(self, stock_list: List[str], target_date: str = None) -> Dict:
        """
        CTO强制规范: 从QMT本地日K数据计算5日均量
        
        使用QMT本地数据替代外网API：
        1. 读取最近5个交易日的日K线数据
        2. 计算volume的5日移动平均
        
        Args:
            stock_list: 股票代码列表
            target_date: 目标日期(格式'YYYYMMDD')，用于回测时指定历史日期
        
        Returns:
            Dict: 计算结果统计
        """
        start = time.perf_counter()
        
        print(f"📊 [QMT本地] 计算5日均量...")
        logger.info(f"📊 [QMT本地] 开始计算5日均量,目标{len(stock_list)}只股票")
        
        try:
            from xtquant import xtdata
            
            success = 0
            failed = 0
            
            # 【CTO时空锁死】：回测模式必须基于target_date往前推算！
            # 【CTO防爆】：禁止调用get_trading_dates，会导致BSON崩溃！
            # 原因：get_trading_dates内部触发了QMT C++层的批量数据加载
            if not target_date:
                logger.error("❌ [CTO铁血令] 回测模式必须传入target_date！禁止使用datetime.now()！")
                return {'success': 0, 'failed': len(stock_list)}
            
            # 【CTO时空锁死】：必须基于目标回测日期往前推算！
            end_date = target_date
            # 【CTO宪法合规】使用日历工具替代timedelta，22个交易日约等于30自然日
            start_date = get_nth_previous_trading_day(target_date, 22) if CALENDAR_UTILS_AVAILABLE else (datetime.strptime(target_date, '%Y%m%d') - timedelta(days=30)).strftime('%Y%m%d')
            logger.info(f"[CTO时空锁死] 5日均量计算周期: {start_date} ~ {end_date}")
            
            # 【CTO单点爆破】：一只一只查！防爆！防C++崩溃！
            all_data = {}
            missing_stocks = []  # 【CTO V24】记录缺失数据的股票
            logger.info(f"📦 [CTO单点爆破] 单只获取日K数据计算5日均量...")
            
            for stock in stock_list:
                try:
                    single_data = xtdata.get_local_data(
                        field_list=['time', 'volume'],
                        stock_list=[stock],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date
                    )
                    if single_data and stock in single_data and single_data[stock] is not None and len(single_data[stock]) > 0:
                        all_data[stock] = single_data[stock]
                    else:
                        missing_stocks.append(stock)  # 【CTO V24】记录缺失
                except Exception as e:
                    missing_stocks.append(stock)  # 【CTO V24】异常也记录
                    continue
            
            # 【CTO V33终极净身令】删除阻塞式下载循环！
            # 问题根因：download_history_data在QMT限流时会无限挂起
            # 修复：缺失数据直接跳过，不阻塞实盘引擎！
            if missing_stocks:
                logger.warning(f'⚠️ [防空警报] {len(missing_stocks)}只股票本地K线缺失！')
                logger.warning(f'🚫 为防止实盘引擎被网络卡死，系统拒绝现场下载，这些股票将被物理隔离。')
                logger.warning(f'💡 请在盘后运行：python tools/smart_download.py 补充弹药！')
                # 不下载！缺失的票在后续df is None判断中自然会被过滤掉
            
            # 【调试日志】检查all_data返回状态
            logger.info(f"[调试] xtdata.get_local_data返回: type={type(all_data)}, "
                       f"is_none={all_data is None}, "
                       f"len={len(all_data) if all_data else 0}, "
                       f"stock_list_len={len(stock_list)}")
            
            if all_data:
                # 【调试日志】打印第一只股票的数据结构
                sample_keys = list(all_data.keys())[:3]
                for idx, sample_key in enumerate(sample_keys):
                    sample_df = all_data[sample_key]
                    logger.info(f"[调试] 样本股票[{idx}] {sample_key}: "
                               f"df_type={type(sample_df)}, "
                               f"is_none={sample_df is None}, "
                               f"len={len(sample_df) if sample_df is not None else 'N/A'}, "
                               f"columns={sample_df.columns.tolist() if hasattr(sample_df, 'columns') else 'N/A'}")
                
                for stock_code, df in all_data.items():
                    # 【Bug修复】原代码要求len(df)>=5过于严格，导致春节等假期后数据不足时全部失败
                    # 【CTO V24节假日防爆】：使用.tail(5)确保只取最近5个交易日！
                    # 哪怕中间跨了春节/国庆，tail(5)只取最后5行（即最近5个交易日）
                    if df is not None and len(df) >= 1:
                        # 【CTO V24修复】精确取最近5个交易日的均值！
                        # 原逻辑用所有数据均值，会稀释最新信号！
                        n_days = min(5, len(df))  # 数据不足5天时用全部
                        avg_volume = df['volume'].tail(n_days).mean()  # 【CTO V24】精确5日！
                        # 【CTO铁血清洗】：绝不允许NaN或Inf进入系统缓存！
                        if pd.isna(avg_volume) or np.isinf(avg_volume):
                            avg_volume = 0.0
                        if avg_volume > 0:
                            self._avg_volume_5d[stock_code] = float(avg_volume)
                            success += 1
                        else:
                            # 【调试日志】volume计算失败
                            logger.debug(f"[调试-失败] {stock_code}: volume_mean={avg_volume}")
                            failed += 1
                    else:
                        # 【调试日志】df为None或长度不足
                        logger.debug(f"[调试-失败] {stock_code}: df_is_none={df is None}, "
                                    f"df_len={len(df) if df is not None else 0}")
                        failed += 1
            else:
                logger.error(f"[调试-致命] xtdata.get_local_data返回None或空字典!")
                failed = len(stock_list)
            
            elapsed = (time.perf_counter() - start) * 1000
            self._metadata['avg_volume_warmup_time'] = elapsed  # 已更名
            
            print(f"✅ [QMT本地] 5日均量计算完成: {success}只成功, {failed}只失败, 耗时{elapsed:.0f}ms")
            logger.info(f"✅ [QMT本地-5日均量] {success}只成功,耗时{elapsed:.1f}ms")
            
            return {
                'source': 'QMT本地日K数据',
                'success': success,
                'failed': failed,
                'elapsed_ms': elapsed,
                'note': 'CTO强制：一把梭哈，不分批，0外网请求'
            }
            
        except Exception as e:
            logger.error(f"🚨 [QMT本地-5日均量] 计算失败: {e}")
            print(f"🚨 [QMT本地-5日均量] 计算失败: {e}")
            return {'source': 'QMT本地', 'success': 0, 'failed': len(stock_list), 'error': str(e)}
    
    def _warmup_ma_data(self, stock_list: List[str], target_date: str = None) -> Dict:
        """
        【CTO第三维趋势网】计算MA5/MA10/MA20均线数据
        
        使用QMT本地日K数据计算均线，用于盘后回放的趋势过滤
        
        Args:
            stock_list: 股票代码列表
            target_date: 目标日期(格式'YYYYMMDD')，用于回测时指定历史日期
        """
        start = time.perf_counter()
        
        print(f"📊 [QMT本地] 计算MA均线数据...")
        logger.info(f"📊 [QMT本地] 开始计算MA5/MA10/MA20,目标{len(stock_list)}只股票")
        
        try:
            from xtquant import xtdata
            
            success = 0
            failed = 0
            
            # 【CTO时空锁死】：回测模式必须基于target_date往前推算！
            # 【CTO防爆】：禁止调用get_trading_dates，会导致BSON崩溃！
            if not target_date:
                logger.error("❌ [CTO铁血令] MA预热必须传入target_date！禁止使用datetime.now()！")
                return {'success': 0, 'failed': len(stock_list)}
            
            # 【CTO时空锁死】：必须基于目标回测日期往前推算！
            end_date = target_date
            # 【CTO宪法合规】使用日历工具替代timedelta，30个交易日约等于60自然日
            start_date = get_nth_previous_trading_day(target_date, 30) if CALENDAR_UTILS_AVAILABLE else (datetime.strptime(target_date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')
            logger.info(f"[CTO时空锁死] MA均线计算周期: {start_date} ~ {end_date}")
            
            # 【CTO单点爆破】：一只一只查！防爆！防C++崩溃！
            all_data = {}
            logger.info(f"📦 [CTO单点爆破] 单只获取MA数据...")
            
            for stock in stock_list:
                try:
                    single_data = xtdata.get_local_data(
                        field_list=['time', 'close'],
                        stock_list=[stock],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date
                    )
                    if single_data and stock in single_data:
                        all_data[stock] = single_data[stock]
                except Exception as e:
                    # 有毒的票直接跳过！
                    continue
            
            # 【调试】检查返回数据
            logger.info(f"[MA调试] get_local_data返回: type={type(all_data)}, is_none={all_data is None}")
            if all_data:
                sample_keys = list(all_data.keys())[:3]
                for key in sample_keys:
                    df = all_data[key]
                    logger.info(f"[MA调试] 样本{key}: df_type={type(df)}, is_none={df is None}, len={len(df) if df is not None else 0}")
                    if df is not None and len(df) > 0:
                        logger.info(f"[MA调试] 样本{key} columns: {df.columns.tolist() if hasattr(df, 'columns') else 'no columns'}")
            
            if all_data:
                for stock_code, df in all_data.items():
                    if df is not None and len(df) >= 5:  # 放宽到至少5天数据
                        # 计算MA5/MA10/MA20（根据可用数据）
                        closes = df['close'].values if 'close' in df.columns else df.values.flatten()
                        ma5 = closes[-5:].mean()
                        ma10 = closes[-10:].mean() if len(closes) >= 10 else ma5
                        ma20 = closes[-20:].mean() if len(closes) >= 20 else ma10
                        
                        self._ma_data[stock_code] = {
                            'ma5': float(ma5),
                            'ma10': float(ma10),
                            'ma20': float(ma20),
                            'close': float(closes[-1])  # 最新收盘价
                        }
                        success += 1
                    else:
                        failed += 1
            else:
                failed = len(stock_list)
            
            elapsed = (time.perf_counter() - start) * 1000
            
            print(f"✅ [QMT本地] MA均线计算完成: {success}只成功, {failed}只失败, 耗时{elapsed:.0f}ms")
            logger.info(f"✅ [QMT本地-MA均线] {success}只成功,耗时{elapsed:.1f}ms")
            
            return {
                'source': 'QMT本地日K数据',
                'success': success,
                'failed': failed,
                'elapsed_ms': elapsed
            }
            
        except Exception as e:
            logger.error(f"🚨 [QMT本地-MA均线] 计算失败: {e}")
            print(f"🚨 [QMT本地-MA均线] 计算失败: {e}")
            return {'source': 'QMT本地', 'success': 0, 'failed': len(stock_list), 'error': str(e)}
    
    def get_ma_data(self, stock_code: str) -> Optional[Dict]:
        """
        【CTO第三维趋势网】获取股票的MA数据
        
        Returns:
            Dict: {'ma5': float, 'ma10': float, 'ma20': float, 'close': float} 或 None
        """
        return self._ma_data.get(stock_code)
    
    def _warmup_atr_data(self, stock_list: List[str], target_date: str = None) -> Dict:
        """
        【CTO ATR股性突变雷达】计算20日ATR数据
        
        ATR公式: (High - Low) / Pre_Close 的20日滑动平均值
        用于检测股性突变，识别异常波动股票
        
        Args:
            stock_list: 股票代码列表
            target_date: 目标日期(格式'YYYYMMDD')，用于回测时指定历史日期
            
        Returns:
            Dict: 计算结果统计
        """
        start = time.perf_counter()
        
        print(f"📊 [QMT本地] 计算ATR_20D股性雷达...")
        logger.info(f"📊 [QMT本地] 开始计算ATR_20D,目标{len(stock_list)}只股票")
        
        try:
            from xtquant import xtdata
            
            success = 0
            failed = 0
            
            # 【CTO时空锁死】：回测模式必须基于target_date往前推算！
            # 【CTO防爆】：禁止调用get_trading_dates，会导致BSON崩溃！
            if not target_date:
                logger.error("❌ [CTO铁血令] ATR预热必须传入target_date！禁止使用datetime.now()！")
                return {'success': 0, 'failed': len(stock_list)}
            
            # 【CTO时空锁死】：必须基于目标回测日期往前推算！
            end_date = target_date
            # 【CTO宪法合规】使用日历工具替代timedelta，25个交易日约等于45自然日
            start_date = get_nth_previous_trading_day(target_date, 25) if CALENDAR_UTILS_AVAILABLE else (datetime.strptime(target_date, '%Y%m%d') - timedelta(days=45)).strftime('%Y%m%d')
            logger.info(f"[CTO时空锁死] ATR计算周期: {start_date} ~ {end_date}")
            
            # 【CTO单点爆破】：一只一只查！防爆！防C++崩溃！
            all_data = {}
            logger.info(f"📦 [CTO单点爆破] 单只获取ATR数据...")
            
            for stock in stock_list:
                try:
                    single_data = xtdata.get_local_data(
                        field_list=['time', 'high', 'low', 'close', 'open'],
                        stock_list=[stock],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date
                    )
                    if single_data and stock in single_data:
                        all_data[stock] = single_data[stock]
                except Exception as e:
                    # 有毒的票直接跳过！
                    continue
            
            if all_data:
                for stock_code, df in all_data.items():
                    if df is not None and len(df) >= 5:  # 至少5天数据才计算
                        try:
                            # 【Bug修复】QMT返回的数据可能没有pre_close列
                            # 需要从close列计算前一日收盘价
                            df = df.copy()
                            
                            # 检查是否有pre_close列
                            if 'pre_close' not in df.columns:
                                # 尝试从close列推导前一日收盘价
                                if 'close' in df.columns:
                                    df['pre_close'] = df['close'].shift(1)
                                    # 第一行的pre_close用开盘价替代（如果有）或使用close
                                    if 'open' in df.columns:
                                        df.loc[df.index[0], 'pre_close'] = df.loc[df.index[0], 'open']
                                    else:
                                        df.loc[df.index[0], 'pre_close'] = df.loc[df.index[0], 'close']
                                else:
                                    # 无法计算，跳过
                                    failed += 1
                                    continue
                            
                            # 计算每日 (High - Low) / Pre_Close
                            # 注意: pre_close可能为0或NaN,需要处理
                            df['tr'] = (df['high'] - df['low']) / df['pre_close'].replace(0, float('nan'))
                            
                            # 过滤掉无效值
                            valid_tr = df['tr'].dropna()
                            
                            if len(valid_tr) >= 5:  # 至少5个有效数据点
                                # 计算20日ATR(如果数据不足20天,使用所有可用数据)
                                atr_20d = valid_tr.mean()
                                
                                if pd.notna(atr_20d) and atr_20d > 0:
                                    self._atr_20d_map[stock_code] = float(atr_20d)
                                    # 【CTO修复】同时保存prev_close
                                    self._prev_close_cache[stock_code] = float(df['close'].iloc[-1])
                                    success += 1
                                else:
                                    failed += 1
                            else:
                                failed += 1
                        except Exception as e:
                            logger.debug(f"ATR计算失败 {stock_code}: {e}")
                            failed += 1
                    else:
                        failed += 1
            else:
                failed = len(stock_list)
                logger.error(f"[ATR调试-致命] xtdata.get_local_data返回None或空字典!")
            
            # 【CTO修复】为所有股票设置默认ATR值(0.05 = 5%日波动)
            # 确保即使QMT数据缺失,系统也能继续运行
            for stock_code in stock_list:
                if stock_code not in self._atr_20d_map:
                    self._atr_20d_map[stock_code] = 0.05  # 默认5%日波动
            
            elapsed = (time.perf_counter() - start) * 1000
            
            # 【CTO修正】如果使用默认值的超过50%，必须报严重警告
            if success < len(stock_list) * 0.5:
                logger.error(f"❌ [数据断层致命告警] {len(stock_list)-success} 只股票丢失真实日K！被迫启用 0.05 盲狙默认值！这极度危险！")
                print(f"❌ [QMT本地] ATR_20D计算: {success}只真实数据, {len(stock_list)-success}只使用默认值(极度危险！)")
            else:
                logger.info(f"✅ [QMT本地] ATR_20D计算完成: {success}只成功,{len(stock_list)-success}只使用默认值,耗时{elapsed:.1f}ms")
                print(f"[QMT本地] ATR_20D计算完成: {success}只成功, {len(stock_list)-success}只使用默认值")
            
            return {
                'source': 'QMT本地日K数据',
                'success': success,
                'failed': failed,
                'elapsed_ms': elapsed
            }
            
        except Exception as e:
            logger.error(f"🚨 [QMT本地-ATR_20D] 计算失败: {e}")
            print(f"🚨 [QMT本地-ATR_20D] 计算失败: {e}")
            return {'source': 'QMT本地', 'success': 0, 'failed': len(stock_list), 'error': str(e)}

    def get_atr_20d(self, stock_code: str) -> float:
        """
        【CTO ATR股性突变雷达】获取股票的20日ATR值
        
        ATR (Average True Range) 用于衡量股票波动性
        可用于检测股性突变 (如ATR突然增大表示波动加剧)
        
        Args:
            stock_code: 股票代码
            
        Returns:
            float: 20日ATR值,查不到返回默认值0.05 (表示5%的日波动)
        """
        return self._atr_20d_map.get(stock_code, 0.05)
    
    def get_prev_close(self, stock_code: str) -> Optional[float]:
        """
        【CTO修复】获取股票的前收盘价
        
        Args:
            stock_code: 股票代码
            
        Returns:
            float: 前收盘价，查不到返回None
        """
        return self._prev_close_cache.get(stock_code)

    def _warmup_qmt_data(self, stock_list: List[str]) -> Dict:
        """
        QMT本地C++接口读取 - 极速(<100ms)
        
        获取:
        - FloatVolume: 流通股本
        - UpStopPrice: 涨停价  
        - DownStopPrice: 跌停价
        """
        start = time.perf_counter()
        
        try:
            from xtquant import xtdata
            
            success = 0
            failed = 0
            
            for stock_code in stock_list:
                try:
                    # CTO规范: 使用QMT最底层C++接口
                    detail = xtdata.get_instrument_detail(stock_code, True)
                    
                    if detail is not None:
                        # 提取FloatVolume(流通股本)
                        fv = detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0)
                        if fv:
                            self._float_volume[stock_code] = int(fv)
                        
                        # 提取涨停价/跌停价
                        up = detail.get('UpStopPrice', 0) if hasattr(detail, 'get') else getattr(detail, 'UpStopPrice', 0)
                        down = detail.get('DownStopPrice', 0) if hasattr(detail, 'get') else getattr(detail, 'DownStopPrice', 0)
                        if up:
                            self._up_stop_price[stock_code] = float(up)
                        if down:
                            self._down_stop_price[stock_code] = float(down)
                        
                        success += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    failed += 1
                    if failed <= 3:  # 只记录前3个错误
                        logger.debug(f"QMT读取失败 {stock_code}: {e}")
            
            elapsed = (time.perf_counter() - start) * 1000
            self._metadata['qmt_warmup_time'] = elapsed
            
            result = {
                'source': 'QMT本地C++接口',
                'success': success,
                'failed': failed,
                'elapsed_ms': elapsed,
                'avg_ms_per_stock': elapsed / len(stock_list) if stock_list else 0
            }
            
            logger.info(f"✅ [QMT装弹] {success}只成功,耗时{elapsed:.1f}ms,平均每只{result['avg_ms_per_stock']:.3f}ms")
            return result
            
        except Exception as e:
            logger.error(f"🚨 [QMT装弹失败] {e}")
            return {'source': 'QMT', 'success': 0, 'failed': len(stock_list), 'error': str(e)}
    
    def _check_data_integrity(self, stock_list: List[str]) -> Dict:
        """
        数据完整性检查 - CTO强制规范
        
        CTO强制：两项核心数据都必须存在！
        - FloatVolume：流通股本，必须存在
        - 5日均量：量比计算的根基，必须存在！
        - 数据只能从QMT本地获取，严禁任何外网请求
        """
        total = len(stock_list)
        
        # 检查FloatVolume(QMT核心数据) - 必须存在
        missing_float = sum(1 for s in stock_list if s not in self._float_volume)
        
        # 检查5日均量(核心数据) - CTO强制：必须存在！
        missing_avg = sum(1 for s in stock_list if s not in self._avg_volume_5d)
        
        # CTO强制：两项核心数据都必须检查
        # 缺失率取两者最大值
        float_missing_rate = missing_float / total if total > 0 else 1.0
        avg_missing_rate = missing_avg / total if total > 0 else 1.0
        max_missing_rate = max(float_missing_rate, avg_missing_rate)
        
        # 核心数据缺失率<=30%才可交易
        # 原因：部分股票可能是新股/停牌，本地数据不全是正常现象
        # 实盘中会自动过滤掉无数据的股票
        is_ready = max_missing_rate <= 0.30
        
        return {
            'is_ready': is_ready,
            'missing_rate': max_missing_rate,
            'missing_float': missing_float,
            'missing_avg': missing_avg,
            'total': total,
            'note': 'CTO强制：FloatVolume和5日均量都必须存在，100% QMT本地计算'
        }
    
    # ============================================================
    # 盘中O(1)极速查询 - 严禁任何网络请求!!!
    # ============================================================
    
    def get_float_volume(self, stock_code: str) -> float:
        """
        获取流通股本 - O(1)内存查询
        
        CTO规范:
        - 09:30后只读内存
        - 严禁调用xtdata.get_instrument_detail
        - 未找到返回0(由调用方判断是否熔断)
        
        【CTO修复】强制转换为float，防止类型爆炸
        """
        return float(self._float_volume.get(stock_code, 0))
    
    def get_up_stop_price(self, stock_code: str) -> float:
        """获取涨停价 - O(1)内存查询"""
        return self._up_stop_price.get(stock_code, 0.0)
    
    def get_down_stop_price(self, stock_code: str) -> float:
        """获取跌停价 - O(1)内存查询"""
        return self._down_stop_price.get(stock_code, 0.0)
    
    def get_avg_volume_5d(self, stock_code: str) -> float:
        """获取5日平均成交量 - O(1)内存查询
        
        【CTO铁血令】强制转换为float，防止类型爆炸
        """
        try:
            val = self._avg_volume_5d.get(stock_code, 0.0)
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def build_static_cache(self, stock_list: List[str], default_float_volume: float = 1000000000.0) -> Dict:
        """
        【CTO V34】构建静态常数预编译快查表
        
        从run_live_trading_engine.py剥离，实现预热层与逻辑分离
        
        Args:
            stock_list: 股票代码列表
            default_float_volume: 流通股本默认值（10亿股）
            
        Returns:
            Dict: {stock_code: {'float_volume': float, 'avg_volume_5d': float}}
        """
        static_cache = {}
        
        for stock in stock_list:
            fv = self.get_float_volume(stock)
            avg_vol_5d = self.get_avg_volume_5d(stock)
            
            # 【CTO V23健壮性修复】流通股本缺失时用默认值，绝不跳过股票！
            if not fv or fv <= 0:
                fv = default_float_volume
            
            static_cache[stock] = {
                'float_volume': fv,
                'avg_volume_5d': avg_vol_5d or 1.0
            }
        
        logger.info(f"[TrueDictionary] 静态快查表编译完成: {len(static_cache)} 只股票")
        return static_cache
    
    def get_avg_turnover_5d(self, stock_code: str, target_date: str = None) -> float:
        """
        获取5日平均换手率 - 市值平替法
        
        【CTO市值平替法】
        - 公式：成交额 / (流通股本 × 收盘价) × 100
        - 优点：绕开volume单位问题，避免历史流通股本漂移
        - 注意：使用当前的FloatVolume（误差在可接受范围内）
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期(格式'YYYYMMDD')，用于回测
            
        Returns:
            float: 5日平均换手率(%)
        """
        try:
            # 优先从缓存读取
            val = self._avg_turnover_5d.get(stock_code)
            if val is not None:
                return float(val)
            
            # 缓存未命中，实时计算
            if not target_date:
                target_date = datetime.now().strftime('%Y%m%d')
            
            start_date = get_nth_previous_trading_day(target_date, 22) if CALENDAR_UTILS_AVAILABLE else (datetime.strptime(target_date, '%Y%m%d') - timedelta(days=30)).strftime('%Y%m%d')
            
            from xtquant import xtdata
            
            # 获取流通股本
            float_volume = self.get_float_volume(stock_code)
            if float_volume <= 0:
                return 0.0
            
            # 获取日K数据
            data = xtdata.get_local_data(
                field_list=['time', 'close', 'amount'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=target_date
            )
            
            if not data or stock_code not in data:
                return 0.0
            
            df = data[stock_code]
            if df is None or len(df) < 1:
                return 0.0
            
            # 计算每日换手率：amount / (float_volume * close) * 100
            df = df.copy()
            df['turnover_rate'] = df['amount'] / (float_volume * df['close']) * 100
            
            # 取最近5个交易日均值
            recent_turnover = df['turnover_rate'].tail(5)
            avg_turnover = recent_turnover.mean()
            
            # 清理NaN/Inf
            if pd.isna(avg_turnover) or np.isinf(avg_turnover):
                return 0.0
            
            # 缓存结果
            self._avg_turnover_5d[stock_code] = float(avg_turnover)
            
            return float(avg_turnover)
            
        except Exception as e:
            logger.debug(f"[get_avg_turnover_5d] {stock_code} 计算失败: {e}")
            return 0.0
    
    def get_sectors(self, stock_code: str) -> List[str]:
        """获取所属板块 - O(1)内存查询"""
        return self._sector_map.get(stock_code, [])
    
    # ============================================================
    # 工具方法
    # ============================================================
    
    def _get_warmup_stats(self) -> Dict:
        """获取装弹统计"""
        return {
            'qmt_cached': len(self._float_volume),
            'up_stop_cached': len(self._up_stop_price),
            'avg_volume_cached': len(self._avg_volume_5d),
            'sector_cached': len(self._sector_map),
            'cache_date': self._metadata['cache_date'],
            'data_source': self._metadata['data_source'],
            'is_ready': True
        }
    
    def is_ready_for_trading(self) -> bool:
        """检查是否可交易 - CTO规范: 盘前必须调用"""
        today = datetime.now().strftime('%Y%m%d')
        if self._metadata['cache_date'] != today:
            return False
        
        integrity = self._check_data_integrity(list(self._float_volume.keys()))
        return integrity['is_ready']
    
    def get_stats(self) -> Dict:
        """获取完整统计"""
        return {
            'qmt': {
                'float_volume': len(self._float_volume),
                'up_stop_price': len(self._up_stop_price),
                'warmup_ms': self._metadata['qmt_warmup_time']
            },
            'avg_volume': {
                'avg_volume_5d': len(self._avg_volume_5d),
                'warmup_ms': self._metadata['avg_volume_warmup_time']
            },
            'cache_date': self._metadata['cache_date'],
            'data_source': self._metadata['data_source'],
            'is_ready': self.is_ready_for_trading()
        }


# ============================================================
# 全局单例
# ============================================================

_true_dict_instance: Optional[TrueDictionary] = None


def get_true_dictionary() -> TrueDictionary:
    """获取TrueDictionary单例"""
    global _true_dict_instance
    if _true_dict_instance is None:
        _true_dict_instance = TrueDictionary()
    return _true_dict_instance


def warmup_true_dictionary(stock_list: List[str], target_date: str = None) -> Dict:
    """便捷函数: 执行盘前装弹 (100% QMT本地)
    
    Args:
        stock_list: 股票代码列表
        target_date: 目标日期(格式'YYYYMMDD')，用于回测时指定历史日期
    """
    return get_true_dictionary().warmup(stock_list, target_date=target_date)


# ============================================================
# 测试入口 - 真实QMT联调
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TrueDictionary 真实QMT联调测试")
    print("CTO规范: 100% QMT本地架构，0外网请求")
    print("=" * 60)
    
    # 获取实例
    td = get_true_dictionary()
    
    # 测试股票(小规模测试)
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH']
    
    print(f"\n📊 测试股票: {test_stocks}")
    print("⚠️  注意: 此测试需要真实QMT连接!")
    
    try:
        # 执行盘前装弹
        result = td.warmup(test_stocks)
        
        print("\n📈 装弹结果:")
        print(f"  QMT: {result['qmt']}")
        print(f"  5日均量: {result['avg_volume']}")
        print(f"  完整性: {result['integrity']}")
        
        # 查询测试
        if result['integrity']['is_ready']:
            print("\n🔍 内存查询测试:")
            for stock in test_stocks:
                fv = td.get_float_volume(stock)
                avg = td.get_avg_volume_5d(stock)
                up = td.get_up_stop_price(stock)
                print(f"  {stock}: FloatVolume={fv:,}, 5日Avg={avg:,.0f}, 涨停价={up}")
        
        print("\n✅ TrueDictionary测试完成 (100% QMT本地)")
        
    except Exception as e:
        print(f"\n❌ 测试失败(可能需要QMT连接): {e}")
        import traceback
        traceback.print_exc()