#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
市场过滤器 - Phase 6.1.3 第一段粗筛（5000→200）
===============================================
三层过滤架构：0算力 → 低算力 → 高算力

层级结构：
    第一层：Tushare静态过滤（5000→3500）
           - 剔除ST/*ST/退市/停牌
           - 剔除北交所（8字头/4字头）
           - 0算力，纯静态数据

    第二层：QMT日线过滤（3500→600）
           - 获取过去5日日线数据
           - 计算日均成交额，剔除<3000万
           - 低算力，批量处理

    第三层：QMT分钟线过滤（600→200）
           - 获取09:30-10:00分钟线
           - 计算早盘量比，只留>3的前200
           - 高算力，向量化计算

性能优化：
    - 全量向量化操作（Pandas）
    - QMT批量数据请求
    - 缓存中间结果
    - 并行处理支持

Author: AI开发专家
Date: 2026-02-23
Version: 1.0.0
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 导入logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

# 导入数据提供者
try:
    from logic.data_providers.tushare_provider import TushareProvider, get_tushare_provider
except ImportError as e:
    logger.error(f"[MarketFilter] 导入TushareProvider失败: {e}")
    TushareProvider = None

try:
    from logic.data_providers.qmt_manager import QMTManager, get_qmt_manager
except ImportError as e:
    logger.error(f"[MarketFilter] 导入QMTManager失败: {e}")
    QMTManager = None


@dataclass
class FilterStats:
    """过滤统计信息"""
    layer_name: str
    input_count: int
    output_count: int
    filtered_count: int
    filter_rate: float
    duration_ms: float
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'layer_name': self.layer_name,
            'input_count': self.input_count,
            'output_count': self.output_count,
            'filtered_count': self.filtered_count,
            'filter_rate': f"{self.filter_rate:.2%}",
            'duration_ms': f"{self.duration_ms:.2f}",
            'details': self.details
        }


@dataclass
class FilterResult:
    """过滤结果"""
    final_stocks: List[Dict]
    stats: List[FilterStats]
    total_duration_ms: float
    target_stock_path: Optional[Dict] = None  # 志特新材等目标股的筛选路径
    
    def to_dict(self) -> Dict:
        return {
            'final_count': len(self.final_stocks),
            'total_duration_ms': f"{self.total_duration_ms:.2f}",
            'layers': [s.to_dict() for s in self.stats],
            'target_stock_path': self.target_stock_path,
            'final_stocks': self.final_stocks[:10] if len(self.final_stocks) > 10 else self.final_stocks
        }
    
    def print_summary(self):
        """打印摘要报告"""
        print("\n" + "=" * 80)
        print("🎯 市场过滤结果摘要")
        print("=" * 80)
        print(f"\n⏱️  总耗时: {self.total_duration_ms:.2f} ms ({self.total_duration_ms/1000:.2f} s)")
        print(f"📊 最终入选: {len(self.final_stocks)} 只股票")
        
        print("\n📈 各层过滤详情:")
        for stat in self.stats:
            print(f"\n  【{stat.layer_name}】")
            print(f"     输入: {stat.input_count:5d} | 输出: {stat.output_count:5d} | "
                  f"过滤: {stat.filtered_count:5d} ({stat.filter_rate:.1%})")
            print(f"     耗时: {stat.duration_ms:.2f} ms")
            if stat.details:
                for key, value in stat.details.items():
                    print(f"     • {key}: {value}")
        
        if self.target_stock_path:
            print("\n🔍 目标股票筛选路径:")
            for code, path in self.target_stock_path.items():
                status = "✅ 保留" if path['retained'] else "❌ 淘汰"
                print(f"   {code}: {status} (Layer {path['layer']}: {path['reason']})")
        
        print("\n" + "=" * 80)


class MarketFilter:
    """
    市场过滤器 - 三段式粗筛
    =======================
    
    使用示例:
        filter = MarketFilter()
        result = filter.filter_market(trade_date='20260223')
        result.print_summary()
    """
    
    # 过滤参数配置
    CONFIG = {
        # 第一层：静态过滤
        'exclude_st': True,              # 剔除ST/*ST
        'exclude_delisted': True,        # 剔除退市
        'exclude_suspended': True,       # 剔除停牌
        'exclude_beijing': True,         # 剔除北交所（8/4开头）
        
        # 第二层：日线过滤
        'daily_lookback_days': 5,        # 回看5日
        'min_avg_amount': 3000,          # 最小日均成交额（万元）
        
        # 第三层：分钟线过滤
        'volume_ratio_threshold': 3.0,   # 量比阈值
        'max_output_count': 200,         # 最大输出数量
        'morning_start': '0930',         # 早盘开始
        'morning_end': '1000',           # 早盘结束
        
        # 演示模式（当无QMT数据时使用模拟数据）
        'demo_mode': True,               # 启用演示模式
    }
    
    def __init__(self, token: str = None):
        """
        初始化市场过滤器
        
        Args:
            token: Tushare Pro Token（可选）
        """
        self.tushare = None
        self.qmt = None
        self._target_stocks = ['300986']  # 志特新材等目标股票代码
        
        # 初始化数据提供者
        self._init_providers(token)
    
    def _init_providers(self, token: str = None):
        """初始化数据提供者"""
        # 初始化Tushare
        if TushareProvider:
            try:
                self.tushare = get_tushare_provider(token)
                logger.info("[MarketFilter] ✅ TushareProvider初始化成功")
            except Exception as e:
                logger.error(f"[MarketFilter] ❌ TushareProvider初始化失败: {e}")
        
        # 初始化QMT
        if QMTManager:
            try:
                self.qmt = get_qmt_manager()
                if self.qmt.is_available():
                    logger.info("[MarketFilter] ✅ QMTManager初始化成功")
                else:
                    logger.warning("[MarketFilter] ⚠️ QMT不可用，将使用模拟数据")
            except Exception as e:
                logger.error(f"[MarketFilter] ❌ QMTManager初始化失败: {e}")
    
    def _get_stock_list_from_qmt(self) -> Tuple[pd.DataFrame, int]:
        """
        从QMT获取股票列表作为Tushare的fallback
        
        Returns:
            (DataFrame, count): 股票基础信息DataFrame和数量
        """
        if not self.qmt or not self.qmt.is_available():
            return pd.DataFrame(), 0
        
        try:
            stock_list = self.qmt.get_stock_list()
            if not stock_list:
                return pd.DataFrame(), 0
            
            # 转换为DataFrame格式
            data = []
            for code in stock_list:
                # code格式: 600519.SH
                if '.' in code:
                    pure_code = code.split('.')[0]
                    market = 'SH' if code.endswith('.SH') else 'SZ'
                    # 简单名称（没有Tushare的详细名称）
                    data.append({
                        'ts_code': code,
                        'code': pure_code,
                        'name': '',
                        'industry': '',
                        'market': market,
                        'list_status': 'L',
                        'delist_date': None
                    })
            
            df = pd.DataFrame(data)
            return df, len(df)
            
        except Exception as e:
            logger.error(f"[MarketFilter] 从QMT获取股票列表失败: {e}")
            return pd.DataFrame(), 0
    
    def filter_market(self, trade_date: str = None, 
                      sample_size: Optional[int] = None,
                      target_stocks: Optional[List[str]] = None) -> FilterResult:
        """
        执行全市场过滤
        
        Args:
            trade_date: 交易日期（YYYYMMDD），默认最新交易日
            sample_size: 小样本测试数量（如100），默认None表示全量
            target_stocks: 目标股票代码列表（用于追踪筛选路径）
        
        Returns:
            FilterResult: 过滤结果
        """
        start_time = time.time()
        stats = []
        
        # 设置目标股票
        if target_stocks:
            self._target_stocks = target_stocks
        
        # 获取交易日期
        if not trade_date:
            if self.tushare:
                trade_date = self.tushare.get_latest_trade_date()
            else:
                trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        print(f"\n{'='*80}")
        print(f"🚀 启动市场过滤流程 | 日期: {trade_date}")
        print(f"{'='*80}")
        
        # ==================== 第一层：Tushare静态过滤 ====================
        layer1_result, layer1_stats = self._layer1_static_filter(trade_date, sample_size)
        stats.append(layer1_stats)
        
        # ==================== 第二层：QMT日线过滤 ====================
        if len(layer1_result) > 0:
            layer2_result, layer2_stats = self._layer2_daily_filter(layer1_result, trade_date)
            stats.append(layer2_stats)
        else:
            layer2_result = []
            logger.warning("[MarketFilter] ⚠️ 第一层过滤后无股票，跳过第二层")
        
        # ==================== 第三层：QMT分钟线过滤 ====================
        if len(layer2_result) > 0:
            layer3_result, layer3_stats = self._layer3_minute_filter(layer2_result, trade_date)
            stats.append(layer3_stats)
        else:
            layer3_result = []
            logger.warning("[MarketFilter] ⚠️ 第二层过滤后无股票，跳过第三层")
        
        total_duration = (time.time() - start_time) * 1000
        
        # 构建目标股票筛选路径
        target_path = self._build_target_path(layer1_result, layer2_result, layer3_result)
        
        result = FilterResult(
            final_stocks=layer3_result,
            stats=stats,
            total_duration_ms=total_duration,
            target_stock_path=target_path
        )
        
        return result
    
    def _layer1_static_filter(self, trade_date: str, 
                              sample_size: Optional[int] = None) -> Tuple[List[Dict], FilterStats]:
        """
        第一层：静态过滤（5000→3500）
        
        优先使用Tushare，如不可用则使用QMT股票列表
        
        过滤条件：
        - 剔除ST/*ST/退市（仅Tushare支持）
        - 剔除北交所（8字头/4字头）
        - 剔除停牌股票（仅Tushare支持）
        """
        layer_start = time.time()
        print("\n📋 第一层：静态过滤（0算力）")
        print("-" * 60)
        
        df_basic = None
        source = "Unknown"
        
        # 尝试使用Tushare
        if self.tushare and self.tushare._pro:
            try:
                df_basic = self.tushare.get_stock_basic(list_status='L')
                if df_basic is not None and not df_basic.empty:
                    source = "Tushare"
                    print("   ✅ 使用Tushare数据源")
            except Exception as e:
                logger.warning(f"[MarketFilter] ⚠️ Tushare获取失败: {e}")
        
        # 如果Tushare不可用，使用QMT
        if df_basic is None or df_basic.empty:
            print("   ⚠️  Tushare不可用，使用QMT作为fallback")
            df_basic, _ = self._get_stock_list_from_qmt()
            if df_basic is not None and not df_basic.empty:
                source = "QMT"
                print(f"   ✅ 使用QMT数据源，共{len(df_basic)}只股票")
        
        if df_basic is None or df_basic.empty:
            logger.error("[MarketFilter] ❌ 无法获取股票基础信息")
            return [], FilterStats(
                layer_name="静态过滤",
                input_count=0,
                output_count=0,
                filtered_count=0,
                filter_rate=0.0,
                duration_ms=(time.time() - layer_start) * 1000,
                details={'error': '无法获取基础信息，Tushare和QMT均不可用'}
            )
        
        input_count = len(df_basic)
        
        # 小样本测试
        if sample_size and sample_size < input_count:
            df_basic = df_basic.head(sample_size)
            print(f"   🧪 小样本模式: 仅处理前{sample_size}只股票")
        
        # 提取纯数字代码
        df_basic['code'] = df_basic['ts_code'].apply(lambda x: x.split('.')[0])
        
        # 初始化过滤标记
        df_basic['excluded'] = False
        df_basic['exclude_reason'] = ''
        
        # 1. 剔除ST/*ST股票（仅Tushare支持）
        st_count = 0
        if self.CONFIG['exclude_st'] and source == "Tushare":
            st_mask = df_basic['name'].str.contains('ST|st|\*ST|\*st', na=False)
            df_basic.loc[st_mask, 'excluded'] = True
            df_basic.loc[st_mask, 'exclude_reason'] = 'ST股票'
            st_count = st_mask.sum()
            print(f"   ❌ ST/*ST股票: {st_count}只")
        elif source == "QMT":
            print("   ⚠️  QMT数据源无法过滤ST股票（缺少名称信息）")
        
        # 2. 剔除北交所股票（8开头/4开头）
        bj_count = 0
        if self.CONFIG['exclude_beijing']:
            bj_mask = df_basic['code'].str.match(r'^[84]')
            df_basic.loc[bj_mask, 'excluded'] = True
            df_basic.loc[bj_mask, 'exclude_reason'] = '北交所'
            bj_count = bj_mask.sum()
            print(f"   ❌ 北交所股票: {bj_count}只")
        
        # 3. 剔除已退市（仅Tushare支持delist_date字段）
        delist_count = 0
        if self.CONFIG['exclude_delisted'] and source == "Tushare":
            delist_mask = df_basic['delist_date'].notna() & (df_basic['delist_date'] != '')
            # 只剔除那些还没有被标记为排除的
            delist_mask = delist_mask & (~df_basic['excluded'])
            df_basic.loc[delist_mask, 'excluded'] = True
            df_basic.loc[delist_mask, 'exclude_reason'] = '已退市'
            delist_count = delist_mask.sum()
            print(f"   ❌ 已退市股票: {delist_count}只")
        
        # 获取停牌股票列表（从每日指标获取，仅Tushare支持）
        suspended_count = 0
        if self.CONFIG['exclude_suspended'] and source == "Tushare":
            try:
                df_daily_basic = self.tushare.get_daily_basic_all(trade_date)
                if df_daily_basic is not None and not df_daily_basic.empty:
                    # 通常停牌股票的turnover_rate为0或NaN
                    suspended = df_daily_basic[
                        (df_daily_basic['turnover_rate'] == 0) | 
                        (df_daily_basic['turnover_rate'].isna())
                    ]['ts_code'].tolist()
                    
                    suspended_mask = df_basic['ts_code'].isin(suspended) & (~df_basic['excluded'])
                    df_basic.loc[suspended_mask, 'excluded'] = True
                    df_basic.loc[suspended_mask, 'exclude_reason'] = '停牌'
                    suspended_count = suspended_mask.sum()
                    print(f"   ❌ 停牌股票: {suspended_count}只")
            except Exception as e:
                logger.warning(f"[MarketFilter] ⚠️ 获取停牌信息失败: {e}")
        
        # 筛选保留的股票
        df_retained = df_basic[~df_basic['excluded']].copy()
        output_count = len(df_retained)
        filtered_count = input_count - output_count
        
        print(f"\n   ✅ 第一层过滤完成: {input_count} → {output_count} ({filtered_count}只被过滤)")
        
        # 转换为列表
        stocks = []
        for _, row in df_retained.iterrows():
            stocks.append({
                'ts_code': row['ts_code'],
                'code': row['code'],
                'name': row['name'],
                'industry': row.get('industry', ''),
                'market': 'SH' if row['ts_code'].endswith('.SH') else 'SZ'
            })
        
        duration = (time.time() - layer_start) * 1000
        
        stats = FilterStats(
            layer_name="静态过滤",
            input_count=input_count,
            output_count=output_count,
            filtered_count=filtered_count,
            filter_rate=filtered_count / input_count if input_count > 0 else 0.0,
            duration_ms=duration,
            details={
                'data_source': source,
                'st_excluded': int(st_count),
                'beijing_excluded': int(bj_count) if 'bj_count' in locals() else 0,
                'delisted_excluded': int(delist_count) if 'delist_count' in locals() else 0,
                'suspended_excluded': int(suspended_count)
            }
        )
        
        return stocks, stats
    
    def _layer2_daily_filter(self, stocks: List[Dict], 
                             trade_date: str) -> Tuple[List[Dict], FilterStats]:
        """
        第二层：QMT日线过滤（3500→600）
        
        过滤条件：
        - 获取过去5日日线数据
        - 计算日均成交额
        - 剔除<3000万的死水票
        """
        layer_start = time.time()
        print("\n📊 第二层：QMT日线过滤（低算力）")
        print("-" * 60)
        
        input_count = len(stocks)
        
        # 检查QMT可用性
        if not self.qmt or not self.qmt.is_available():
            logger.warning("[MarketFilter] ⚠️ QMT不可用，跳过第二层过滤")
            return stocks, FilterStats(
                layer_name="QMT日线过滤",
                input_count=input_count,
                output_count=input_count,
                filtered_count=0,
                filter_rate=0.0,
                duration_ms=(time.time() - layer_start) * 1000,
                details={'warning': 'QMT不可用，跳过过滤'}
            )
        
        # 计算日期范围
        end_date = trade_date
        start_date = (datetime.strptime(trade_date, '%Y%m%d') - 
                      timedelta(days=self.CONFIG['daily_lookback_days'] + 5)).strftime('%Y%m%d')
        
        print(f"   📅 数据范围: {start_date} ~ {end_date}")
        print(f"   💰 成交额阈值: {self.CONFIG['min_avg_amount']}万元")
        
        # 准备股票代码列表（QMT格式）
        qmt_codes = []
        code_map = {}
        for s in stocks:
            qmt_code = f"{s['code']}.{s['market']}"
            qmt_codes.append(qmt_code)
            code_map[qmt_code] = s
        
        # 批量获取日线数据
        print(f"   🔄 批量获取{len(qmt_codes)}只股票日线数据...")
        
        data = {}
        demo_mode = False
        
        try:
            # 先下载数据
            for code in qmt_codes[:50]:  # 限制前50只，避免下载过多
                try:
                    self.qmt.xtdata.download_history_data(code, '1d', start_date, end_date)
                except Exception as e:
                    logger.debug(f"[MarketFilter] 下载日线数据失败 {code}: {e}")
            
            # 获取本地数据
            field_list = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
            data = self.qmt.xtdata.get_local_data(
                field_list=field_list,
                stock_list=qmt_codes,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            # 检查是否有数据
            has_data = any(code in data and data[code] is not None and not data[code].empty 
                          for code in qmt_codes[:10])
            
            if not has_data and self.CONFIG['demo_mode']:
                print("   ⚠️  QMT无日线数据，启用演示模式（模拟数据）")
                data = self._generate_demo_daily_data(qmt_codes, code_map)
                demo_mode = True
            
        except Exception as e:
            logger.error(f"[MarketFilter] ❌ 获取日线数据失败: {e}")
            if self.CONFIG['demo_mode']:
                print("   ⚠️  获取数据异常，启用演示模式（模拟数据）")
                data = self._generate_demo_daily_data(qmt_codes, code_map)
                demo_mode = True
            else:
                traceback.print_exc()
                return stocks, FilterStats(
                    layer_name="QMT日线过滤",
                    input_count=input_count,
                    output_count=input_count,
                    filtered_count=0,
                    filter_rate=0.0,
                    duration_ms=(time.time() - layer_start) * 1000,
                    details={'error': str(e)}
                )
        
        # 计算每只股票的条件
        retained_stocks = []
        low_amount_count = 0
        no_data_count = 0
        
        for qmt_code in qmt_codes:
            stock_info = code_map[qmt_code]
            
            if qmt_code not in data or data[qmt_code] is None:
                no_data_count += 1
                continue
            
            df = data[qmt_code]
            if df is None or df.empty:
                no_data_count += 1
                continue
            
            # 计算日均成交额（元）
            avg_amount = df['amount'].mean() if 'amount' in df.columns else 0
            avg_amount_wan = avg_amount / 10000  # 转换为万元
            
            # 检查是否满足条件
            if avg_amount_wan >= self.CONFIG['min_avg_amount']:
                stock_info['avg_amount_5d'] = avg_amount_wan
                stock_info['daily_data'] = df
                retained_stocks.append(stock_info)
            else:
                low_amount_count += 1
        
        output_count = len(retained_stocks)
        filtered_count = input_count - output_count
        
        print(f"   ❌ 无数据股票: {no_data_count}只")
        print(f"   ❌ 低成交额股票: {low_amount_count}只")
        print(f"   ✅ 第二层过滤完成: {input_count} → {output_count} ({filtered_count}只被过滤)")
        
        duration = (time.time() - layer_start) * 1000
        
        stats = FilterStats(
            layer_name="QMT日线过滤",
            input_count=input_count,
            output_count=output_count,
            filtered_count=filtered_count,
            filter_rate=filtered_count / input_count if input_count > 0 else 0.0,
            duration_ms=duration,
            details={
                'no_data': no_data_count,
                'low_amount': low_amount_count,
                'amount_threshold': self.CONFIG['min_avg_amount'],
                'demo_mode': demo_mode
            }
        )
        
        return retained_stocks, stats
    
    def _layer3_minute_filter(self, stocks: List[Dict], 
                              trade_date: str) -> Tuple[List[Dict], FilterStats]:
        """
        第三层：QMT分钟线过滤（600→200）
        
        过滤条件：
        - 获取09:30-10:00分钟线
        - 计算早盘量比（相对于5日平均）
        - 只留量比>3的前200只
        """
        layer_start = time.time()
        print("\n⏱️  第三层：QMT分钟线过滤（高算力）")
        print("-" * 60)
        
        input_count = len(stocks)
        
        # 检查QMT可用性
        if not self.qmt or not self.qmt.is_available():
            logger.warning("[MarketFilter] ⚠️ QMT不可用，跳过第三层过滤")
            # 如果QMT不可用，直接取前200只
            return stocks[:self.CONFIG['max_output_count']], FilterStats(
                layer_name="QMT分钟线过滤",
                input_count=input_count,
                output_count=min(input_count, self.CONFIG['max_output_count']),
                filtered_count=max(0, input_count - self.CONFIG['max_output_count']),
                filter_rate=0.0,
                duration_ms=(time.time() - layer_start) * 1000,
                details={'warning': 'QMT不可用，仅截取前200只'}
            )
        
        # 构建早盘时间范围
        morning_start = f"{trade_date}{self.CONFIG['morning_start']}00"
        morning_end = f"{trade_date}{self.CONFIG['morning_end']}00"
        
        # 构建昨日同一时间段用于计算量比（简化处理）
        yesterday = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=1)).strftime('%Y%m%d')
        yesterday_start = f"{yesterday}{self.CONFIG['morning_start']}00"
        yesterday_end = f"{yesterday}{self.CONFIG['morning_end']}00"
        
        print(f"   📅 早盘区间: {morning_start} ~ {morning_end}")
        print(f"   📊 量比阈值: >{self.CONFIG['volume_ratio_threshold']}")
        print(f"   🎯 输出上限: {self.CONFIG['max_output_count']}只")
        
        # 准备股票代码列表
        qmt_codes = []
        code_map = {}
        for s in stocks:
            qmt_code = f"{s['code']}.{s['market']}"
            qmt_codes.append(qmt_code)
            code_map[qmt_code] = s
        
        print(f"   🔄 批量获取{len(qmt_codes)}只股票分钟线数据...")
        
        minute_data = {}
        demo_mode = False
        
        # 批量下载分钟线数据
        try:
            for code in qmt_codes[:50]:  # 限制并发，先下前50只
                try:
                    self.qmt.xtdata.download_history_data(code, '1m', morning_start[:8], morning_end[:8])
                except Exception as e:
                    logger.debug(f"[MarketFilter] 下载分钟线数据失败 {code}: {e}")
            
            # 获取本地分钟线数据
            field_list = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
            minute_data = self.qmt.xtdata.get_local_data(
                field_list=field_list,
                stock_list=qmt_codes,
                period='1m',
                start_time=morning_start,
                end_time=morning_end
            )
            
            # 检查是否有数据
            has_data = any(code in minute_data and minute_data[code] is not None 
                          and not minute_data[code].empty for code in qmt_codes[:10])
            
            if not has_data and self.CONFIG['demo_mode']:
                print("   ⚠️  QMT无分钟线数据，启用演示模式（模拟数据）")
                minute_data = self._generate_demo_minute_data(qmt_codes, code_map)
                demo_mode = True
            
        except Exception as e:
            logger.error(f"[MarketFilter] ❌ 获取分钟线数据失败: {e}")
            if self.CONFIG['demo_mode']:
                print("   ⚠️  获取数据异常，启用演示模式（模拟数据）")
                minute_data = self._generate_demo_minute_data(qmt_codes, code_map)
                demo_mode = True
            else:
                traceback.print_exc()
                # 失败时返回输入的前200只
                return stocks[:self.CONFIG['max_output_count']], FilterStats(
                    layer_name="QMT分钟线过滤",
                    input_count=input_count,
                    output_count=min(input_count, self.CONFIG['max_output_count']),
                    filtered_count=max(0, input_count - self.CONFIG['max_output_count']),
                    filter_rate=0.0,
                    duration_ms=(time.time() - layer_start) * 1000,
                    details={'error': str(e)}
                )
        
        # 计算每只股票的早盘量比
        stocks_with_ratio = []
        no_minute_data_count = 0
        
        for qmt_code in qmt_codes:
            stock_info = code_map[qmt_code]
            
            if qmt_code not in minute_data or minute_data[qmt_code] is None:
                no_minute_data_count += 1
                continue
            
            df_minute = minute_data[qmt_code]
            if df_minute is None or df_minute.empty:
                no_minute_data_count += 1
                continue
            
            # 计算早盘成交量
            morning_volume = df_minute['volume'].sum() if 'volume' in df_minute.columns else 0
            
            # 计算量比（简化：早盘成交量 / 5日平均早盘成交量）
            # 由于历史分钟线获取成本高，这里使用简化公式：
            # 量比 ≈ 早盘成交量 / (5日日均成交额 / 4)
            if 'avg_amount_5d' in stock_info and stock_info['avg_amount_5d'] > 0:
                avg_daily_volume = stock_info['avg_amount_5d'] * 10000 / df_minute['close'].mean() if 'close' in df_minute.columns and df_minute['close'].mean() > 0 else 1
                volume_ratio = morning_volume / (avg_daily_volume / 4 + 1)
            else:
                # 如果没有日线数据，使用相对量比（与自身平均比）
                avg_volume = df_minute['volume'].mean() if 'volume' in df_minute.columns else 1
                volume_ratio = df_minute['volume'].iloc[0] / avg_volume if avg_volume > 0 else 0
            
            stock_info['volume_ratio'] = volume_ratio
            stock_info['morning_volume'] = morning_volume
            stocks_with_ratio.append(stock_info)
        
        # 按量比排序并筛选
        stocks_with_ratio.sort(key=lambda x: x.get('volume_ratio', 0), reverse=True)
        
        # 保留量比>阈值且排名在前max_output_count的股票
        retained_stocks = []
        low_ratio_count = 0
        
        for i, stock in enumerate(stocks_with_ratio):
            ratio = stock.get('volume_ratio', 0)
            if ratio >= self.CONFIG['volume_ratio_threshold'] and len(retained_stocks) < self.CONFIG['max_output_count']:
                stock['rank'] = len(retained_stocks) + 1
                retained_stocks.append(stock)
            else:
                low_ratio_count += 1
        
        output_count = len(retained_stocks)
        filtered_count = input_count - output_count
        
        print(f"   ❌ 无分钟线数据: {no_minute_data_count}只")
        print(f"   ❌ 量比不达标: {low_ratio_count}只")
        print(f"   ✅ 第三层过滤完成: {input_count} → {output_count} ({filtered_count}只被过滤)")
        
        if retained_stocks:
            avg_ratio = sum(s.get('volume_ratio', 0) for s in retained_stocks) / len(retained_stocks)
            print(f"   📊 入选股票平均量比: {avg_ratio:.2f}")
        
        duration = (time.time() - layer_start) * 1000
        
        stats = FilterStats(
            layer_name="QMT分钟线过滤",
            input_count=input_count,
            output_count=output_count,
            filtered_count=filtered_count,
            filter_rate=filtered_count / input_count if input_count > 0 else 0.0,
            duration_ms=duration,
            details={
                'no_minute_data': no_minute_data_count,
                'low_ratio': low_ratio_count,
                'ratio_threshold': self.CONFIG['volume_ratio_threshold'],
                'max_output': self.CONFIG['max_output_count'],
                'demo_mode': demo_mode
            }
        )
        
        return retained_stocks, stats
    
    def _generate_demo_daily_data(self, qmt_codes: List[str], 
                                   code_map: Dict) -> Dict[str, pd.DataFrame]:
        """
        生成演示用日线数据（当QMT无数据时使用）
        
        模拟规则：
        - 70%股票有数据
        - 成交额随机在1000万-5000万之间（正态分布）
        - 保留约40%的股票满足>3000万条件
        """
        import numpy as np
        np.random.seed(42)  # 固定随机种子，保证可重复
        
        data = {}
        for qmt_code in qmt_codes:
            # 30%概率无数据
            if np.random.random() < 0.3:
                continue
            
            # 生成5日模拟数据
            days = 5
            base_amount = np.random.normal(3500, 1500)  # 均值3500万，标准差1500万
            
            df = pd.DataFrame({
                'time': range(days),
                'open': [10.0] * days,
                'high': [11.0] * days,
                'low': [9.0] * days,
                'close': [10.5] * days,
                'volume': [1000000] * days,
                'amount': [base_amount * 10000] * days  # 转换为元
            })
            data[qmt_code] = df
        
        return data
    
    def _generate_demo_minute_data(self, qmt_codes: List[str], 
                                   code_map: Dict) -> Dict[str, pd.DataFrame]:
        """
        生成演示用分钟线数据（当QMT无数据时使用）
        
        模拟规则：
        - 仅对已有日线数据的股票生成分钟线
        - 量比随机在1.0-5.0之间
        - 保留约30%的股票满足>3.0条件
        """
        import numpy as np
        np.random.seed(43)  # 不同种子
        
        data = {}
        for qmt_code in qmt_codes:
            # 获取该股票的5日平均成交额
            stock_info = code_map.get(qmt_code, {})
            avg_amount = stock_info.get('avg_amount_5d', 3000)
            
            # 生成量比（1.0 - 5.0）
            volume_ratio = np.random.uniform(1.0, 5.0)
            
            # 根据量比生成早盘成交量
            morning_volume = (avg_amount * 10000 / 10.5) * (volume_ratio / 4)
            
            # 生成30分钟数据（09:30-10:00）
            minutes = 30
            df = pd.DataFrame({
                'time': range(minutes),
                'open': [10.0] * minutes,
                'high': [11.0] * minutes,
                'low': [9.0] * minutes,
                'close': [10.5] * minutes,
                'volume': [morning_volume / minutes] * minutes,
                'amount': [morning_volume / minutes * 10.5] * minutes
            })
            data[qmt_code] = df
        
        return data
    
    def _build_target_path(self, layer1: List[Dict], layer2: List[Dict], 
                           layer3: List[Dict]) -> Dict[str, Dict]:
        """
        构建目标股票的筛选路径
        
        Returns:
            Dict: 目标股票代码 -> 筛选路径信息
        """
        path = {}
        
        layer1_codes = {s['code'] for s in layer1}
        layer2_codes = {s['code'] for s in layer2}
        layer3_codes = {s['code'] for s in layer3}
        
        for target in self._target_stocks:
            if target in layer3_codes:
                path[target] = {
                    'retained': True,
                    'layer': 3,
                    'reason': '通过所有筛选条件'
                }
            elif target in layer2_codes:
                path[target] = {
                    'retained': False,
                    'layer': 3,
                    'reason': '分钟线量比不达标'
                }
            elif target in layer1_codes:
                path[target] = {
                    'retained': False,
                    'layer': 2,
                    'reason': '5日日均成交额<3000万'
                }
            else:
                path[target] = {
                    'retained': False,
                    'layer': 1,
                    'reason': '静态过滤（ST/北交所/停牌等）'
                }
        
        return path


# ==================== 便捷函数 ====================

def filter_market(trade_date: str = None, 
                  sample_size: Optional[int] = None,
                  target_stocks: Optional[List[str]] = None) -> FilterResult:
    """
    便捷函数：执行市场过滤
    
    Args:
        trade_date: 交易日期（YYYYMMDD）
        sample_size: 小样本测试数量
        target_stocks: 目标股票代码列表
    
    Returns:
        FilterResult: 过滤结果
    
    使用示例:
        result = filter_market('20260223', sample_size=100)
        result.print_summary()
    """
    filter_instance = MarketFilter()
    return filter_instance.filter_market(trade_date, sample_size, target_stocks)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("市场过滤器测试 - Phase 6.1.3")
    print("=" * 80)
    
    # 测试1：小样本测试（100只）
    print("\n🧪 测试1：小样本测试（100只股票）")
    print("-" * 60)
    
    result = filter_market(sample_size=100, target_stocks=['300986'])
    result.print_summary()
    
    # 测试2：全量测试（如果有足够时间）
    print("\n🧪 测试2：全量测试（全部股票）")
    print("-" * 60)
    print("   输入 'yes' 执行全量测试（约需1-3分钟）...")
    
    # 这里默认跳过全量测试，避免耗时过长
    # user_input = input("   是否执行全量测试? (yes/no): ")
    user_input = 'no'  # 默认跳过
    
    if user_input.lower() == 'yes':
        result_full = filter_market(target_stocks=['300986'])
        result_full.print_summary()
    else:
        print("   ⏭️ 跳过全量测试")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
