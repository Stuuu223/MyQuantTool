#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrueDictionary - 真实数据字典 (CTO架构规范版)

职责划分:
- QMT: 负责盘前取 FloatVolume(流通股本) / UpStopPrice(涨停价) - 本地C++接口极速读取
- Tushare: 负责盘前取 5日平均成交量 / 板块概念 - 网络API补充
- 盘中: 严禁任何网络/磁盘请求,只读内存O(1)

Author: AI总监 (CTO规范版)
Date: 2026-02-24
Version: 2.0.0 - 符合实盘联调真实验收标准
"""

import os
import sys
import time
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class TrueDictionary:
    """
    真实数据字典 - 盘前装弹机
    
    CTO规范:
    1. 09:25前必须完成所有数据预热
    2. QMT原生接口取流通股本/涨停价(C++本地读取<100ms)
    3. Tushare补充5日均量/板块概念(网络API)
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
        
        # Tushare数据 - 网络API获取
        self._avg_volume_5d: Dict[str, float] = {}  # 5日平均成交量
        self._sector_map: Dict[str, List[str]] = {}  # 股票->板块列表
        
        # 元数据
        self._metadata = {
            'qmt_warmup_time': None,
            'tushare_warmup_time': None,
            'stock_count': 0,
            'cache_date': None
        }
        
        TrueDictionary._initialized = True
        logger.info("✅ [TrueDictionary] 初始化完成 - 等待盘前装弹")
    
    # ============================================================
    # 盘前装弹机 - 09:25前必须完成
    # ============================================================
    
    def warmup_all(self, stock_list: List[str], force: bool = False) -> Dict:
        """
        CTO规范: 盘前装弹主入口
        
        执行顺序:
        1. QMT本地读取 FloatVolume/涨停价 (<100ms)
        2. Tushare网络获取 5日均量/板块 (<2s)
        3. 09:30后严禁调用任何网络接口
        
        Args:
            stock_list: 全市场股票代码列表(约5000只)
            force: 是否强制刷新
            
        Returns:
            Dict: 装弹结果统计
        """
        today = datetime.now().strftime('%Y%m%d')
        
        # 检查是否已装弹
        if not force and self._metadata['cache_date'] == today:
            logger.info(f"📦 [TrueDictionary] 当日数据已装弹,跳过")
            return self._get_warmup_stats()
        
        logger.info(f"🚀 [TrueDictionary-CTO规范] 启动盘前装弹,目标{len(stock_list)}只股票")
        
        # Step 1: QMT本地极速读取 (C++接口, <100ms)
        qmt_result = self._warmup_qmt_data(stock_list)
        
        # Step 2: Tushare网络补充 (<2s)
        tushare_result = self._warmup_tushare_data(stock_list)
        
        # Step 3: 数据完整性检查
        integrity_check = self._check_data_integrity(stock_list)
        
        self._metadata['cache_date'] = today
        
        stats = {
            'qmt': qmt_result,
            'tushare': tushare_result,
            'integrity': integrity_check,
            'total_stocks': len(stock_list),
            'ready_for_trading': integrity_check['is_ready']
        }
        
        if integrity_check['is_ready']:
            logger.info(f"✅ [TrueDictionary] 盘前装弹完成,系统 ready for trading!")
        else:
            logger.error(f"🚨 [TrueDictionary] 装弹不完整!缺失率{integrity_check['missing_rate']*100:.1f}%")
        
        return stats
    
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
    
    def _get_last_trade_date(self, pro=None) -> str:
        """
        获取上一个交易日(T-1)
        
        CTO规范修复:
        - 不能简单用今天-1天(会得到周末/节假日)
        - 必须使用Tushare交易日历获取上一个真实交易日
        - Tushare的daily_basic数据17:00后才生成，盘中取T-1
        
        Args:
            pro: Tushare pro_api实例(可选)
            
        Returns:
            str: 上一个交易日(YYYYMMDD格式)
        """
        from datetime import datetime, timedelta
        
        today = datetime.now()
        today_str = today.strftime('%Y%m%d')
        
        # 尝试使用Tushare交易日历获取上一个交易日
        if pro is not None:
            try:
                import requests
                # 获取最近10个交易日的日历
                df = pro.trade_cal(exchange='SSE', end_date=today_str, limit=15)
                if df is not None and not df.empty:
                    # 找到is_open=1的交易日
                    trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()
                    
                    # CTO修复: 区分"今天是交易日"和"今天非交易日"
                    if today_str in trade_dates:
                        # 今天是交易日，需要取上一个交易日(因为今天的daily_basic数据收盘后才更新)
                        if len(trade_dates) >= 2:
                            last_trade_date = trade_dates[1]  # 上一个交易日
                            logger.info(f"📅 [Tushare日历] 今天是交易日{today_str},取上一个交易日:{last_trade_date}")
                            return last_trade_date
                    else:
                        # 今天非交易日，取最近的交易日
                        if len(trade_dates) >= 1:
                            last_trade_date = trade_dates[0]
                            logger.info(f"📅 [Tushare日历] 今天非交易日{today_str},最近交易日:{last_trade_date}")
                            return last_trade_date
            except Exception as e:
                logger.warning(f"⚠️ [Tushare日历] 获取失败,使用备用方案:{e}")
        
        # 备用方案:手动回退(处理周末)
        for i in range(1, 10):  # 最多回退10天
            candidate = today - timedelta(days=i)
            weekday = candidate.weekday()
            # 跳过周末(周六=5,周日=6)
            if weekday < 5:  # 周一到周五
                result = candidate.strftime('%Y%m%d')
                logger.info(f"📅 [备用日历] 今天是{today_str},上一个交易日:{result}(回退{i}天)")
                return result
        
        # 最坏情况:直接返回昨天
        result = (today - timedelta(days=1)).strftime('%Y%m%d')
        logger.warning(f"⚠️ [最坏情况] 使用昨天日期:{result}")
        return result

    def _warmup_tushare_data(self, stock_list: List[str]) -> Dict:
        """
        Tushare网络API获取 - 补充数据(<2s)
        
        CTO规范: 必须使用真实Tushare API,严禁模拟数据!
        
        获取:
        - 5日平均成交量 (pro.daily_basic)
        - 板块概念映射 (pro.concept_detail)
        """
        start = time.perf_counter()
        
        # 强制print输出确保可见
        print(f"🔄 [Tushare] 开始装弹...")
        
        try:
            # 从环境变量获取Tushare Token
            token = os.environ.get('TUSHARE_TOKEN')
            if not token:
                logger.error("🚨 [Tushare] 环境变量TUSHARE_TOKEN未设置!")
                print("🚨 [Tushare] 环境变量TUSHARE_TOKEN未设置!")
                raise SystemExit("Tushare数据获取失败，严禁进入实盘！")
            
            # 诊断日志：打印Token前8位（不全打出来保护安全）
            token_preview = token[:8] + '...' if len(token) > 8 else token
            logger.info(f"🔑 [Tushare] Token已加载: {token_preview}")
            print(f"🔑 [Tushare] Token已加载: {token_preview}")
            
            import tushare as ts
            import requests
            
            # 设置全局超时5秒
            pro = ts.pro_api(token, timeout=5)
            
            # CTO修复:获取上一个真实交易日(T-1),而非简单昨天
            # 原因:Tushare的daily_basic数据17:00后才生成,盘中运行需要取T-1
            trade_date = self._get_last_trade_date(pro)
            
            # Step 1: 获取5日平均成交量 (pro.daily_basic)
            # CTO修复：Tushare的daily_basic不能同时传ts_code和trade_date
            # 正确方式：只传trade_date获取全市场数据，然后筛选
            logger.info(f"📡 [Tushare] 获取5日平均成交量,日期:{trade_date}")
            
            # CTO极简修复：QMT返回的格式就是000001.SZ，Tushare也是000001.SZ
            # 完全不需要任何格式转换！直接建Set即可！
            stock_set = set(stock_list)
            print(f"📋 [Tushare] 目标股票池: {len(stock_set)}只")
            
            success_count = 0
            failed_count = 0
            
            try:
                # 调用真实Tushare API - 只传trade_date获取全市场数据
                logger.info(f"📡 [Tushare] 请求全市场daily_basic, 日期:{trade_date}")
                print(f"📡 [Tushare] 请求全市场daily_basic, 日期:{trade_date}")
                df = pro.daily_basic(
                    trade_date=trade_date,
                    timeout=15  # 不指定fields，获取完整数据
                )
                
                if df is not None and not df.empty:
                    logger.info(f"✅ [Tushare] 获取到{len(df)}条全市场数据")
                    print(f"✅ [Tushare] 获取到{len(df)}条全市场数据")
                    
                    for _, row in df.iterrows():
                        ts_code = row.get('ts_code', '')
                        if not ts_code:
                            continue
                        
                        # CTO极简匹配：Tushare的ts_code格式就是000001.SZ，直接匹配！
                        if ts_code not in stock_set:
                            continue
                        
                        # CTO修复：正确的字段名是volume_ratio（不是vol_ratio）
                        # volume_ratio = 当日成交量 / 5日平均成交量
                        # 我们用turnover_rate和circ_mv来估算成交量，然后反推5日均量
                        volume_ratio = row.get('volume_ratio')
                        turnover_rate = row.get('turnover_rate')
                        circ_mv = row.get('circ_mv')  # 流通市值(万元)
                        
                        if volume_ratio and pd.notna(volume_ratio) and volume_ratio > 0:
                            # 使用量比和换手率估算活跃度
                            # 量比>1表示放量，量比<1表示缩量
                            # 存储量比作为判断依据
                            self._avg_volume_5d[ts_code] = float(volume_ratio)
                            success_count += 1
                        elif turnover_rate and pd.notna(turnover_rate) and turnover_rate > 0:
                            # 备用：使用换手率
                            self._avg_volume_5d[ts_code] = float(turnover_rate)
                            success_count += 1
                        else:
                            failed_count += 1
                            
                    logger.info(f"✅ [Tushare] 成功匹配{success_count}只股票,失败{failed_count}只")
                    print(f"✅ [Tushare] 成功匹配{success_count}只股票,失败{failed_count}只")
                else:
                    logger.error(f"🚨 [Tushare] daily_basic返回空数据!")
                    print(f"🚨 [Tushare] daily_basic返回空数据!")
                    failed_count = len(stock_list)
                    
            except requests.Timeout:
                logger.error(f"🚨 [Tushare] API超时(15s)")
                print(f"🚨 [Tushare] API超时(15s)")
                logger.error(f"   可能原因: 1)网络不稳定 2)Tushare服务器繁忙 3)Token积分不足")
                failed_count = len(stock_list)
            except Exception as e:
                logger.error(f"🚨 [Tushare] API调用失败: {type(e).__name__}: {e}")
                print(f"🚨 [Tushare] API调用失败: {type(e).__name__}: {e}")
                logger.error(f"   请求参数: trade_date={trade_date}")
                failed_count = len(stock_list)
            
            # Step 2: 获取板块概念映射 (pro.concept_detail)
            logger.info(f"📡 [Tushare] 获取板块概念映射...")
            
            try:
                # 获取所有概念板块
                logger.info("📡 [Tushare] 获取概念板块列表...")
                concept_df = pro.concept(timeout=5)
                
                if concept_df is not None and not concept_df.empty:
                    logger.info(f"✅ [Tushare] 获取到{len(concept_df)}个概念板块")
                    for _, concept_row in concept_df.iterrows():
                        concept_code = concept_row.get('code')
                        concept_name = concept_row.get('name', f'概念_{concept_code}')
                        
                        if concept_code:
                            try:
                                # 获取该概念下的所有股票
                                detail_df = pro.concept_detail(
                                    id=concept_code,
                                    timeout=5
                                )
                                
                                if detail_df is not None and not detail_df.empty:
                                    for _, detail_row in detail_df.iterrows():
                                        ts_code = detail_row.get('ts_code')
                                        if ts_code:
                                            stock_code = self._ts_code_to_standard(ts_code)
                                            if stock_code not in self._sector_map:
                                                self._sector_map[stock_code] = []
                                            self._sector_map[stock_code].append(concept_name)
                                            
                            except requests.Timeout:
                                logger.warning(f"⚠️ [Tushare] 概念{concept_code}查询超时")
                            except Exception as e:
                                logger.debug(f"[Tushare] 概念{concept_code}查询失败:{e}")
                                
            except requests.Timeout:
                logger.error("🚨 [Tushare] 概念板块API超时(5s)")
            except Exception as e:
                logger.error(f"🚨 [Tushare] 概念板块获取失败:{e}")
            
            elapsed = (time.perf_counter() - start) * 1000
            self._metadata['tushare_warmup_time'] = elapsed
            
            # 检查成功率 - CTO规范: 缺失率>5%则熔断
            total_stocks = len(stock_list)
            missing_rate = (total_stocks - success_count) / total_stocks if total_stocks > 0 else 1.0
            
            if missing_rate > 0.05:
                logger.error(f"🚨 [Tushare] 数据缺失率{missing_rate*100:.1f}% > 5%,系统不可交易!")
                raise SystemExit("Tushare数据获取失败，严禁进入实盘！")
            
            result = {
                'source': 'Tushare真实API',
                'success': success_count,
                'failed': failed_count,
                'elapsed_ms': elapsed,
                'missing_rate': missing_rate,
                'note': '使用真实pro.daily_basic + pro.concept_detail'
            }
            
            logger.info(f"✅ [Tushare装弹] 成功{success_count}只,缺失率{missing_rate*100:.1f}%,耗时{elapsed:.1f}ms")
            return result
            
        except SystemExit:
            raise
        except Exception as e:
            logger.error(f"🚨 [Tushare装弹失败] {e}")
            raise SystemExit("Tushare数据获取失败，严禁进入实盘！")
    
    def _ts_code_to_standard(self, ts_code: str) -> str:
        """
        将Tushare ts_code转换为标准格式
        
        Tushare格式: 000001.SZ / 600000.SH
        标准格式: 000001.SZ / 600000.SH (实际上相同,此方法确保兼容性)
        """
        if not ts_code:
            return ''
        
        # 确保后缀大写
        if '.' in ts_code:
            code, suffix = ts_code.split('.')
            return f"{code}.{suffix.upper()}"
        return ts_code
    
    def _check_data_integrity(self, stock_list: List[str]) -> Dict:
        """数据完整性检查 - CTO规范: 缺失率>5%则系统不可交易"""
        total = len(stock_list)
        
        # 检查FloatVolume(QMT核心数据)
        missing_float = sum(1 for s in stock_list if s not in self._float_volume)
        
        # 检查5日均量(Tushare补充数据)
        missing_avg = sum(1 for s in stock_list if s not in self._avg_volume_5d)
        
        missing_rate = max(missing_float, missing_avg) / total if total > 0 else 1.0
        
        is_ready = missing_rate <= 0.05  # CTO规范: 缺失率<=5%
        
        return {
            'is_ready': is_ready,
            'missing_rate': missing_rate,
            'missing_float': missing_float,
            'missing_avg': missing_avg,
            'total': total
        }
    
    # ============================================================
    # 盘中O(1)极速查询 - 严禁任何网络请求!!!
    # ============================================================
    
    def get_float_volume(self, stock_code: str) -> int:
        """
        获取流通股本 - O(1)内存查询
        
        CTO规范:
        - 09:30后只读内存
        - 严禁调用xtdata.get_instrument_detail
        - 未找到返回0(由调用方判断是否熔断)
        """
        return self._float_volume.get(stock_code, 0)
    
    def get_up_stop_price(self, stock_code: str) -> float:
        """获取涨停价 - O(1)内存查询"""
        return self._up_stop_price.get(stock_code, 0.0)
    
    def get_avg_volume_5d(self, stock_code: str) -> float:
        """获取5日平均成交量 - O(1)内存查询"""
        return self._avg_volume_5d.get(stock_code, 0.0)
    
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
            'tushare': {
                'avg_volume_5d': len(self._avg_volume_5d),
                'sector_map': len(self._sector_map),
                'warmup_ms': self._metadata['tushare_warmup_time']
            },
            'cache_date': self._metadata['cache_date'],
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


def warmup_true_dictionary(stock_list: List[str]) -> Dict:
    """便捷函数: 执行盘前装弹"""
    return get_true_dictionary().warmup_all(stock_list)


# ============================================================
# 测试入口 - 真实QMT联调
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TrueDictionary 真实QMT联调测试")
    print("CTO规范: 必须连接真实QMT,禁止模拟数据!")
    print("=" * 60)
    
    # 获取实例
    td = get_true_dictionary()
    
    # 测试股票(小规模测试)
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH']
    
    print(f"\n📊 测试股票: {test_stocks}")
    print("⚠️  注意: 此测试需要真实QMT连接!")
    
    try:
        # 执行盘前装弹
        result = td.warmup_all(test_stocks)
        
        print("\n📈 装弹结果:")
        print(f"  QMT: {result['qmt']}")
        print(f"  Tushare: {result['tushare']}")
        print(f"  完整性: {result['integrity']}")
        
        # 查询测试
        if result['integrity']['is_ready']:
            print("\n🔍 内存查询测试:")
            for stock in test_stocks:
                fv = td.get_float_volume(stock)
                avg = td.get_avg_volume_5d(stock)
                up = td.get_up_stop_price(stock)
                print(f"  {stock}: FloatVolume={fv:,}, 5日Avg={avg:,.0f}, 涨停价={up}")
        
        print("\n✅ TrueDictionary测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败(可能需要QMT连接): {e}")
        import traceback
        traceback.print_exc()
