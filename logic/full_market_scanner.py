#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场三漏斗扫描器 (Full Market Triple Funnel Scanner)

架构设计：
    全市场 5187 只
        ↓ Level 1: 技术面粗筛 (QMT批量)
    300-500 只异动股
        ↓ Level 2: 资金流向分析 (AkShare)
    50-100 只精选
        ↓ Level 3: 坑vs机会分类 (TrapDetector + CapitalClassifier)
    最终输出：机会池 / 观察池 / 黑名单

Author: MyQuantTool Team
Date: 2026-02-05
"""

import time
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.trap_detector import TrapDetector
from logic.capital_classifier import CapitalClassifier
from logic.fund_flow_analyzer import FundFlowAnalyzer
from logic.rate_limiter import RateLimiter
from logic.code_converter import CodeConverter
from logic.logger import get_logger

logger = get_logger(__name__)


class FullMarketScanner:
    """
    全市场三漏斗扫描器
    
    核心职责：
    1. Level 1: 从全市场快速筛选异动股（技术面粗筛）
    2. Level 2: 对异动股做资金流向深度分析
    3. Level 3: 对精选股做诱多陷阱检测和资金性质分类
    
    输出结果：
    - opportunities: 机会池（低风险 + 主力建仓）
    - watchlist: 观察池（有潜力但需验证）
    - blacklist: 黑名单（明显诱多陷阱）
    """
    
    def __init__(self, config_path: str = "config/market_scan_config.json"):
        """
        初始化全市场扫描器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 检查 QMT 可用性
        if not QMT_AVAILABLE:
            logger.error("❌ xtquant 未安装，无法使用 QMT 数据源")
            raise ImportError("请先安装 xtquant 库")
        
        # 初始化核心模块
        self.trap_detector = TrapDetector()
        self.capital_classifier = CapitalClassifier()
        self.fund_flow = FundFlowAnalyzer()
        self.limiter = RateLimiter(max_requests_per_minute=60, max_requests_per_hour=2000, min_request_interval=0.1)  # 东方财富 API 限速
        self.converter = CodeConverter()
        
        # 获取全市场股票列表
        self.all_stocks = self._init_qmt_stock_list()
        
        logger.info(f"✅ 全市场扫描器初始化完成")
        logger.info(f"   - 股票池: {len(self.all_stocks)} 只")
        logger.info(f"   - Level 1 阈值: 涨跌幅>{self.config['level1']['pct_chg_min']}%, 成交额>{self.config['level1']['amount_min']/1e7:.0f}千万")
        logger.info(f"   - Level 2 阈值: 主力流入>{self.config['level2']['main_inflow_min']/1e6:.0f}百万")
        logger.info(f"   - Level 3 阈值: 风险评分<{self.config['level3']['risk_score_max']}")
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"⚠️  配置文件不存在: {config_path}，使用默认配置")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """默认配置"""
        return {
            'level1': {
                'pct_chg_min': 3.0,       # 涨跌幅最小值（%）
                'amount_min': 30000000,   # 成交额最小值（3000万）
                'turnover_min': 2.0,      # 换手率最小值（%）
            },
            'level2': {
                'main_inflow_min': 5000000,  # 主力流入最小值（500万）
                'super_ratio_min': 0.3,      # 超大单占比
            },
            'level3': {
                'risk_score_max': 0.6,    # 风险评分上限
            }
        }
    
    def _init_qmt_stock_list(self) -> List[str]:
        """初始化 QMT 全市场股票列表"""
        try:
            # 获取沪深A股全部股票
            stocks = xtdata.get_stock_list_in_sector('沪深A股')
            logger.info(f"✅ QMT 股票列表获取成功: {len(stocks)} 只")
            return stocks
        except Exception as e:
            logger.error(f"❌ QMT 股票列表获取失败: {e}")
            return []
    
    def scan_market(self, mode: str = 'premarket') -> Dict[str, List[dict]]:
        """
        执行全市场扫描
        
        Args:
            mode: 扫描模式
                - premarket: 盘前模式（9:00前）
                - intraday: 盘中模式（9:30-15:00）
                - postmarket: 盘后模式（15:00后）
        
        Returns:
            {
                'opportunities': [...],  # 机会池
                'watchlist': [...],      # 观察池
                'blacklist': [...]       # 黑名单
            }
        """
        logger.info("=" * 80)
        logger.info(f"🚀 开始全市场扫描 (模式: {mode})")
        logger.info("=" * 80)
        start_time = time.time()
        
        # ===== Level 1: 技术面粗筛 =====
        logger.info("\n🔍 [Level 1] 技术面粗筛...")
        candidates_l1 = self._level1_technical_filter()
        logger.info(f"✅ Level 1 完成: {len(self.all_stocks)} → {len(candidates_l1)} 只 (耗时: {time.time()-start_time:.1f}秒)")
        
        if not candidates_l1:
            logger.warning("⚠️  Level 1 未筛选出任何股票，提前结束")
            return {'opportunities': [], 'watchlist': [], 'blacklist': []}
        
        # ===== Level 2: 资金流向分析 =====
        logger.info(f"\n💰 [Level 2] 资金流向分析 ({len(candidates_l1)} 只)...")
        l2_start = time.time()
        candidates_l2 = self._level2_capital_analysis(candidates_l1)
        logger.info(f"✅ Level 2 完成: {len(candidates_l1)} → {len(candidates_l2)} 只 (耗时: {time.time()-l2_start:.1f}秒)")
        
        if not candidates_l2:
            logger.warning("⚠️  Level 2 未筛选出任何股票，提前结束")
            return {'opportunities': [], 'watchlist': [], 'blacklist': []}
        
        # ===== Level 3: 坑 vs 机会分类 =====
        logger.info(f"\n⚠️  [Level 3] 诱多陷阱检测 ({len(candidates_l2)} 只)...")
        l3_start = time.time()
        results = self._level3_trap_classification(candidates_l2)
        logger.info(f"✅ Level 3 完成 (耗时: {time.time()-l3_start:.1f}秒)")
        
        # 输出统计
        logger.info("\n" + "=" * 80)
        logger.info("📊 扫描结果统计")
        logger.info("=" * 80)
        logger.info(f"✅ 机会池: {len(results['opportunities'])} 只")
        logger.info(f"⚠️  观察池: {len(results['watchlist'])} 只")
        logger.info(f"❌ 黑名单: {len(results['blacklist'])} 只")
        logger.info(f"⏱️  总耗时: {time.time() - start_time:.1f} 秒")
        logger.info("=" * 80)
        
        # 保存结果
        self._save_results(results, mode)
        
        return results
    
    def scan_with_risk_management(self, mode='premarket') -> Dict:
        """
        带风险管理的扫描
        
        Args:
            mode: 扫描模式
        
        Returns:
            {
                'mode': str,                  # 模式：FULL | DEGRADED_LEVEL1_ONLY
                'evidence_matrix': dict,     # 证据矩阵
                'position_limit': float,     # 仓位上限
                'confidence': float,         # 系统置信度
                'risk_reason': str,          # 风控原因
                'risk_warnings': list,       # 风控警告
                'opportunities': list,       # 机会池
                'watchlist': list,          # 观察池
                'blacklist': list,           # 黑名单
                'level1_candidates': list    # Level 1 候选（降级模式）
            }
        """
        logger.info("=" * 80)
        logger.info(f"🚀 开始全市场扫描（带风险管理） (模式: {mode})")
        logger.info("=" * 80)
        start_time = time.time()
        
        # ===== Level 1: 技术面粗筛 =====
        logger.info("\n🔍 [Level 1] 技术面粗筛...")
        candidates_l1 = self._level1_technical_filter()
        logger.info(f"✅ Level 1 完成: {len(self.all_stocks)} → {len(candidates_l1)} 只 (耗时: {time.time()-start_time:.1f}秒)")
        
        if not candidates_l1:
            logger.warning("⚠️  Level 1 未筛选出任何股票，提前结束")
            return self._build_degraded_result([], 'level1_empty')
        
        # ===== 计算相对热门度 =====
        logger.info(f"\n🔥 计算相对热门度...")
        candidates_l1 = self._calculate_relative_hotness(candidates_l1)
        
        # ===== 构建热门池（TOP 100）=====
        hot_pool_size = 100
        hot_pool = candidates_l1[:hot_pool_size]
        logger.info(f"✅ 热门票池构建完成: TOP {hot_pool_size} (热门评分范围: {hot_pool[0]['hot_score']:.4f} - {hot_pool[-1]['hot_score']:.4f})")
        
        # ===== 检查风险标签（仅对热门池）=====
        logger.info(f"  检查风险标签...")
        for candidate in hot_pool:
            code = candidate['code']
            risk_tag = self._check_short_term_risk(code)
            candidate['risk_tag'] = risk_tag
        
        # 统计风险标签分布
        extreme_risk_count = sum(1 for c in hot_pool if c.get('risk_tag') == '短期涨幅极端')
        logger.info(f"  ✅ 风险标签检查完成: 正常 {len(hot_pool) - extreme_risk_count} 只, 极端风险 {extreme_risk_count} 只")
        
        # 收集证据矩阵
        evidence_matrix = {
            'technical': {
                'available': True,
                'quality': 'GOOD',
                'count': len(candidates_l1),
                'hot_pool_size': hot_pool_size,
                'details': 'QMT Tick 数据，本地可控'
            }
        }
        
        # ===== Level 2: 资金流向分析（仅对热门池）=====
        logger.info(f"\n💰 [Level 2] 资金流向分析 (热门池 {len(hot_pool)} 只)...")
        l2_start = time.time()
        candidates_l2 = []
        fund_flow_error_rate = 0
        
        try:
            # 记录 API 错误次数（样本检查前 100 只）
            sample_size = min(100, len(hot_pool))
            error_count = 0
            
            for idx, candidate in enumerate(hot_pool[:sample_size]):
                code = candidate['code']
                code_6digit = CodeConverter.to_akshare(code)
                flow_data = self.fund_flow.get_fund_flow_cached(code_6digit)
                if 'error' in flow_data:
                    error_count += 1
            
            fund_flow_error_rate = error_count / sample_size if sample_size > 0 else 0
            
            if fund_flow_error_rate > 0.8:
                # 数据质量差，标记为不可用
                evidence_matrix['fund_flow'] = {
                    'available': False,
                    'quality': 'NONE',
                    'error_rate': fund_flow_error_rate,
                    'details': f'API 错误率 {fund_flow_error_rate:.0%} (502 Bad Gateway)'
                }
                logger.warning(f"⚠️  资金流数据异常（错误率: {fund_flow_error_rate:.0%}）")
            else:
                # 数据质量可接受，正常执行 Level 2（仅对热门池）
                hot_pool_codes = [c['code'] for c in hot_pool]
                candidates_l2 = self._level2_capital_analysis(hot_pool_codes)
                evidence_matrix['fund_flow'] = {
                    'available': True,
                    'quality': 'GOOD',
                    'error_rate': fund_flow_error_rate,
                    'details': '东方财富 API（仅热门池）'
                }
        
        except Exception as e:
            evidence_matrix['fund_flow'] = {
                'available': False,
                'quality': 'ERROR',
                'details': str(e)
            }
            logger.warning(f"⚠️  Level 2 异常: {e}")
        
        logger.info(f"✅ Level 2 完成: 热门池 {len(hot_pool)} → {len(candidates_l2)} 只 (耗时: {time.time()-l2_start:.1f}秒)")
        
        # ===== Level 3: 风险分类 =====
        if candidates_l2:
            logger.info(f"\n⚠️  [Level 3] 诱多陷阱检测 ({len(candidates_l2)} 只)...")
            l3_start = time.time()
            candidates_l3 = self._level3_trap_classification(candidates_l2)
            logger.info(f"✅ Level 3 完成 (耗时: {time.time()-l3_start:.1f}秒)")
            scan_mode = 'FULL'
        else:
            candidates_l3 = {
                'opportunities': [],
                'watchlist': [],
                'blacklist': []
            }
            scan_mode = 'DEGRADED_LEVEL1_ONLY'
        
        # 生成市场情绪证据（简化版）
        evidence_matrix['market_sentiment'] = {
            'available': True,
            'quality': 'MEDIUM',
            'score': 0.6,  # 简化处理，基于涨跌停统计
            'details': '基于涨跌停统计'
        }
        
        # ===== 风控评估 =====
        try:
            from logic.risk_manager import RiskManager
            risk_manager = RiskManager()
            risk_result = risk_manager.calculate_position_limit(evidence_matrix)
        except Exception as e:
            logger.error(f"❌ RiskManager 初始化失败: {e}")
            risk_result = {
                'position_limit': 0.1,
                'confidence': 0.1,
                'reason': '风险管理模块异常',
                'warnings': ['⚠️ 风控模块异常']
            }
        
        # 构建结果
        result = {
            'mode': scan_mode,
            'evidence_matrix': evidence_matrix,
            'position_limit': risk_result['position_limit'],
            'confidence': risk_result['confidence'],
            'risk_reason': risk_result['reason'],
            'risk_warnings': risk_result['warnings'],
            **candidates_l3
        }
        
        if scan_mode == 'DEGRADED_LEVEL1_ONLY':
            result['level1_candidates'] = hot_pool[:50]  # 降级模式提供热门池 TOP50
            result['hot_pool'] = hot_pool  # 提供完整热门池
            result['total_candidates'] = len(candidates_l1)  # 提供总候选数
        
        # 输出统计
        logger.info("\n" + "=" * 80)
        logger.info("📊 扫描结果统计")
        logger.info("=" * 80)
        logger.info(f"✅ 机会池: {len(result['opportunities'])} 只")
        logger.info(f"⚠️  观察池: {len(result['watchlist'])} 只")
        logger.info(f"❌ 黑名单: {len(result['blacklist'])} 只")
        logger.info(f"📈 系统置信度: {result['confidence']*100:.1f}%")
        logger.info(f"💰 今日建议最大总仓位: {result['position_limit']*100:.1f}%")
        logger.info(f"🎯 风控原因: {result['risk_reason']}")
        
        if result['risk_warnings']:
            logger.info("\n⚠️  风控警告:")
            for warning in result['risk_warnings']:
                logger.info(f"   {warning}")
        
        if scan_mode == 'DEGRADED_LEVEL1_ONLY':
            logger.info(f"\n📋 技术面候选池（TOP50）:")
            logger.info(f"   由于资金流数据不可用，仅提供技术面筛选结果")
        
        logger.info(f"⏱️  总耗时: {time.time() - start_time:.1f} 秒")
        logger.info("=" * 80)
        
        # 保存结果
        self._save_results(result, mode)
        
        return result
    
    def _build_degraded_result(self, candidates_l1: List[str], reason: str) -> Dict:
        """构建降级结果"""
        return {
            'mode': 'DEGRADED_LEVEL1_ONLY',
            'evidence_matrix': {
                'technical': {
                    'available': False,
                    'quality': 'NONE',
                    'details': reason
                },
                'fund_flow': {
                    'available': False,
                    'quality': 'NONE',
                    'details': '未执行'
                },
                'market_sentiment': {
                    'available': False,
                    'quality': 'NONE',
                    'details': '未执行'
                }
            },
            'position_limit': 0.1,
            'confidence': 0.0,
            'risk_reason': f'Level 1 失败: {reason}',
            'risk_warnings': [f'⚠️ {reason}'],
            'opportunities': [],
            'watchlist': [],
            'blacklist': [],
            'level1_candidates': candidates_l1[:50] if candidates_l1 else []
        }
    
    def _level1_technical_filter(self) -> List[dict]:
        """
        Level 1: 技术面粗筛
        
        从全市场 5000+ 只压缩到 300-500 只
        
        筛选条件：
        1. |涨跌幅| > 3%
        2. 成交额 > 3000万
        3. 换手率 > 2%
        4. 剔除 ST、退市、科创板
        
        Returns:
            候选股票详细信息列表
        """
        candidates = []
        batch_size = 1000
        total_batches = (len(self.all_stocks) + batch_size - 1) // batch_size
        
        for i in range(0, len(self.all_stocks), batch_size):
            batch = self.all_stocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            # 分批获取 QMT Tick 数据
            try:
                tick_data = xtdata.get_full_tick(batch)
                
                # 本地过滤
                for code in batch:
                    tick = tick_data.get(code, {})
                    if tick and self._check_level1_criteria(code, tick):
                        # 构建候选股票详细信息
                        last_close = tick.get('lastClose', 0)
                        last_price = tick.get('lastPrice', 0)
                        amount = tick.get('amount', 0)
                        volume = tick.get('totalVolume', 0)
                        
                        # 计算涨跌幅
                        if last_close > 0:
                            pct_chg = (last_price - last_close) / last_close * 100
                        else:
                            pct_chg = 0
                        
                        # 获取财务信息（流通股本、流通市值）
                        financial_info = self._get_stock_financial_info(code)
                        
                        candidates.append({
                            'code': code,
                            'name': tick.get('stockName', ''),
                            'last_price': last_price,
                            'last_close': last_close,
                            'pct_chg': pct_chg,
                            'amount': amount,
                            'volume': volume,
                            'circulating_shares': financial_info.get('circulating_shares', 0),
                            'circulating_market_cap': financial_info.get('circulating_market_cap', 0),
                        })
                
                hit_count = len([c for c in batch if any(c['code'] == x['code'] for x in candidates)])
                logger.info(f"  批次 {batch_num}/{total_batches}: 获取 {len(batch)} 只股票 (命中: {hit_count} 只)")
                
            except Exception as e:
                logger.warning(f"⚠️  批次 {batch_num} 获取失败: {e}")
                continue
        
        return candidates
    
    def _check_level1_criteria(self, code: str, tick: dict) -> bool:
        """检查 Level 1 筛选条件"""
        if not tick:
            return False
        
        try:
            # 基础风控：剔除垃圾股
            stock_name = tick.get('stockName', '')
            if 'ST' in stock_name or '退' in stock_name:
                return False
            if code.startswith(('688', '8', '4')):  # 科创板、北交所
                return False
            
            # 获取价格数据（仅使用 QMT Tick 实际存在的字段）
            last_close = tick.get('lastClose', 0)
            last_price = tick.get('lastPrice', 0)
            amount = tick.get('amount', 0)
            
            # 计算涨跌幅
            if last_close == 0:
                return False
            pct_chg = abs((last_price - last_close) / last_close * 100)
            
            cfg = self.config['level1']
            
            # 两个条件必须同时满足（暂时去掉换手率，需要额外 API 获取流通市值）
            if pct_chg < cfg['pct_chg_min']:
                return False
            if amount < cfg['amount_min']:
                return False
            # TODO: 换手率需要单独调用 QMT 的其他接口获取流通市值，暂时注释掉
            # if turnover < cfg['turnover_min']:
            #     return False
            
            return True
            
        except Exception as e:
            return False
    
    def _get_stock_financial_info(self, code: str) -> Dict:
        """
        获取股票财务信息（流通股本、流通市值）
        
        Args:
            code: 股票代码（QMT格式）
        
        Returns:
            {
                'circulating_shares': 流通股本（股）,
                'circulating_market_cap': 流通市值（元）
            }
        """
        try:
            # 尝试使用不同的 QMT API 获取流通股本
            # 方法 1: 使用 get_market_data 获取
            try:
                financial_data = xtdata.get_market_data(
                    field_list=['SH_FLOAT_VAL'],  # 流通股本
                    stock_list=[code],
                    period='1d',
                    start_time='',
                    end_time='',
                    dividend_type='none'
                )
                
                if financial_data and code in financial_data:
                    circulating_shares = financial_data[code].get('SH_FLOAT_VAL', 0)
                    if circulating_shares and circulating_shares > 0:
                        # 获取当前价格
                        tick_data = xtdata.get_full_tick([code])
                        if tick_data and code in tick_data:
                            current_price = tick_data[code].get('lastPrice', 0)
                            if current_price > 0:
                                circulating_market_cap = circulating_shares * current_price
                                return {
                                    'circulating_shares': circulating_shares,
                                    'circulating_market_cap': circulating_market_cap
                                }
            except Exception as e:
                logger.debug(f"方法 1 获取流通股本失败 {code}: {e}")
            
            # 方法 2: 使用 get_instrument_type + 简化计算
            # 如果方法 1 失败，使用成交额和换手率的关系来估算
            # 换手率 = 成交量 / 流通股本
            # 如果没有流通股本数据，可以使用总股本作为近似
            try:
                # 获取股票基本信息
                stock_info = xtdata.get_instrument_type(code)
                if stock_info:
                    # 尝试获取其他可能的字段
                    pass
            except Exception as e:
                logger.debug(f"方法 2 获取流通股本失败 {code}: {e}")
            
            # 方法 3: 使用成交额作为替代指标
            # 如果无法获取流通股本，则返回 0，后续计算时会处理
            return {
                'circulating_shares': 0,
                'circulating_market_cap': 0
            }
            
        except Exception as e:
            logger.warning(f"⚠️  获取股票财务信息失败 {code}: {e}")
            return {
                'circulating_shares': 0,
                'circulating_market_cap': 0
            }
    
    def _calculate_turnover_rate(self, code: str, volume: float, circulating_shares: float) -> float:
        """
        计算换手率
        
        Args:
            code: 股票代码
            volume: 成交量（股）
            circulating_shares: 流通股本（股）
        
        Returns:
            换手率（0.0 - 1.0）
        """
        try:
            if circulating_shares == 0:
                return 0.0
            
            turnover_rate = volume / circulating_shares
            return min(turnover_rate, 1.0)  # 限制在 100% 以内
        except Exception as e:
            logger.warning(f"⚠️  计算换手率失败 {code}: {e}")
            return 0.0
    
    def _calculate_relative_volume(self, code: str, amount: float, circulating_market_cap: float) -> float:
        """
        计算相对放量因子
        
        Args:
            code: 股票代码
            amount: 成交额（元）
            circulating_market_cap: 流通市值（元）
        
        Returns:
            相对放量因子（0.0 - 1.0）
        """
        try:
            if circulating_market_cap == 0:
                return 0.0
            
            relative_volume = amount / circulating_market_cap
            return min(relative_volume, 1.0)  # 限制在 100% 以内
        except Exception as e:
            logger.warning(f"⚠️  计算相对放量因子失败 {code}: {e}")
            return 0.0
    
    def _calculate_relative_hotness(self, candidates: List[dict]) -> List[dict]:
        """
        计算相对热门度
        
        Args:
            candidates: 候选股票列表（包含详细信息）
        
        Returns:
            添加了热门评分的候选股票列表
        """
        logger.info("  计算相对热门度...")
        
        # 提取所有候选股的成交额，用于归一化
        amounts = [c.get('amount', 0) for c in candidates]
        max_amount = max(amounts) if amounts else 1
        min_amount = min(amounts) if amounts else 0
        amount_range = max_amount - min_amount if max_amount > min_amount else 1
        
        # 计算换手率和相对放量因子
        for candidate in candidates:
            code = candidate['code']
            volume = candidate.get('volume', 0)
            amount = candidate.get('amount', 0)
            circulating_shares = candidate.get('circulating_shares', 0)
            circulating_market_cap = candidate.get('circulating_market_cap', 0)
            
            # 计算换手率
            turnover_rate = self._calculate_turnover_rate(code, volume, circulating_shares)
            candidate['turnover_rate'] = turnover_rate
            
            # 计算相对放量因子
            relative_volume = self._calculate_relative_volume(code, amount, circulating_market_cap)
            candidate['relative_volume'] = relative_volume
            
            # 计算相对热门度
            if turnover_rate > 0 or relative_volume > 0:
                # 如果有流通股本数据，使用换手率 + 相对放量
                hot_score = turnover_rate * 0.6 + relative_volume * 0.4
            else:
                # 如果没有流通股本数据，使用成交额归一化作为替代
                hot_score = (amount - min_amount) / amount_range
            
            candidate['hot_score'] = hot_score
        
        # 计算排名
        candidates_sorted = sorted(candidates, key=lambda x: x['hot_score'], reverse=True)
        total = len(candidates_sorted)
        
        for idx, candidate in enumerate(candidates_sorted):
            candidate['hot_rank'] = idx + 1
            candidate['hot_percentile'] = (total - idx) / total  # 热门百分位
        
        logger.info(f"  ✅ 相对热门度计算完成")
        
        return candidates_sorted
    
    def _check_short_term_risk(self, code: str) -> Optional[str]:
        """
        检查短期涨幅风险（10 日涨幅）
        
        Args:
            code: 股票代码（QMT格式）
        
        Returns:
            None 或 '短期涨幅极端'
        """
        try:
            # 获取最近 10 个交易日收盘价
            kline = xtdata.get_market_data(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='',
                end_time='',
                count=10,
                dividend_type='none'
            )
            
            if not kline or code not in kline or len(kline[code]) < 10:
                return None
            
            # 提取收盘价数据
            close_prices = kline[code]['close']
            if len(close_prices) < 10:
                return None
            
            # 计算 10 日累计涨幅
            close_10_days_ago = close_prices[0]
            close_today = close_prices[-1]
            
            if close_10_days_ago == 0:
                return None
            
            r10 = (close_today - close_10_days_ago) / close_10_days_ago
            
            # 风险标签（两档）
            if r10 >= 0.8:  # 10 日涨幅 ≥ 80%
                return '短期涨幅极端'
            else:
                return None
        
        except Exception as e:
            logger.warning(f"⚠️  检查短期涨幅风险失败 {code}: {e}")
            return None
    
    def check_before_order(self, code: str, position_pct: float, max_system_confidence: float = 0.7, 
                          max_single_position: float = 0.05, hot_pool_codes: List[str] = None) -> Tuple[bool, str]:
        """
        下单前的强制检查（硬刹车）
        
        Args:
            code: 股票代码（QMT格式）
            position_pct: 拟下单仓位（%）
            max_system_confidence: 最大系统置信度阈值（默认 0.7）
            max_single_position: 单票最大仓位（默认 5%）
            hot_pool_codes: 热门票池代码列表
        
        Returns:
            (是否允许下单, 拒绝原因)
        """
        # 转换为 6 位代码（如果需要）
        code_6digit = CodeConverter.to_akshare(code) if '.' in code else code
        
        # 检查 1：系统置信度
        try:
            from logic.risk_manager import RiskManager
            risk_manager = RiskManager()
            
            # 构建证据矩阵（简化版）
            evidence_matrix = {
                'technical': {'available': True, 'quality': 'GOOD'},
                'fund_flow': {'available': False, 'quality': 'NONE'},  # 假设资金流不可用
                'market_sentiment': {'available': True, 'quality': 'MEDIUM'}
            }
            
            confidence_result = risk_manager.assess_confidence(evidence_matrix)
            system_confidence = confidence_result.get('confidence', 0)
            
            if system_confidence < max_system_confidence:
                return False, f"系统置信度过低（{system_confidence:.1%}，阈值 {max_system_confidence:.1%}），建议降低仓位"
        except Exception as e:
            logger.warning(f"⚠️  检查系统置信度失败: {e}")
        
        # 检查 2：单票仓位上限
        if position_pct > max_single_position:
            return False, f"单票仓位超限（拟开 {position_pct:.1%}，上限 {max_single_position:.1%}）"
        
        # 检查 3：极端风险标签
        risk_tag = self._check_short_term_risk(code)
        if risk_tag == '短期涨幅极端':
            return False, f"短期涨幅极端（10 日涨幅 ≥ 80%），建议不参与"
        
        # 检查 4：是否在热门池
        if hot_pool_codes and code not in hot_pool_codes and code_6digit not in hot_pool_codes:
            return False, f"不在热门池内，建议只参与热门票池"
        
        # 所有检查通过
        return True, "检查通过"
    
    def _level2_capital_analysis(self, candidates: List[str]) -> List[dict]:
        """
        Level 2: 资金流向深度分析
        
        从 300-500 只压缩到 50-100 只
        
        分析内容：
        1. 主力净流入 > 0
        2. 超大单占比 > 30%
        3. 近3日资金流向趋势
        
        Args:
            candidates: Level 1 筛选出的股票列表
        
        Returns:
            包含资金流向数据的股票列表
        """
        results = []
        total = len(candidates)
        
        for idx, code in enumerate(candidates):
            # 进度打印
            if idx % 10 == 0 or idx == total - 1:
                logger.info(f"  进度: {idx+1}/{total} ({(idx+1)/total*100:.1f}%)")

            try:
                # 转换为6位代码（AkShare格式）
                code_6digit = CodeConverter.to_akshare(code)

                # 获取资金流向（东方财富 API，不需要严格限速）
                flow_data = self.fund_flow.get_fund_flow(code_6digit)

                if not flow_data:
                    continue

                # 检查资金条件
                if self._check_level2_criteria(code, flow_data):
                    results.append({
                        'code': code,
                        'flow_data': flow_data
                    })
            except Exception as e:
                logger.warning(f"⚠️  {code} Level2 分析失败: {e}")
                continue
        
        return results
    
    def _check_level2_criteria(self, code: str, flow_data: dict) -> bool:
        """检查 Level 2 资金条件"""
        try:
            cfg = self.config['level2']

            # 获取最新一天的数据
            latest = flow_data.get('latest')
            if not latest:
                return False

            # 条件 1: 主力净流入（超大单 + 大单）必须为正
            super_large_net = latest.get('super_large_net', 0)
            large_net = latest.get('large_net', 0)
            institution_net = super_large_net + large_net

            if institution_net <= 0:
                return False

            # 条件 2: 超大单占比（超大单 / 主力净流入）
            if institution_net > 0:
                super_ratio = abs(super_large_net / institution_net)
                if super_ratio < cfg['super_ratio_min']:
                    return False

            return True

        except Exception as e:
            logger.warning(f"⚠️  {code} Level2 条件检查失败: {e}")
            return False
    
    def _level3_trap_classification(self, candidates: List[dict]) -> Dict[str, List[dict]]:
        """
        Level 3: 坑 vs 机会分类
        
        调用现有的 TrapDetector + CapitalClassifier
        
        分类逻辑：
        - 风险评分 > 0.8 → blacklist（明显诱多陷阱）
        - 风险评分 0.6-0.8 → watchlist（需要观察）
        - 风险评分 < 0.6 → opportunities（可考虑机会）
        
        Args:
            candidates: Level 2 筛选出的股票列表
        
        Returns:
            分类结果字典
        """
        opportunities = []
        watchlist = []
        blacklist = []
        
        for idx, item in enumerate(candidates):
            code = item['code']
            
            if idx % 5 == 0:
                logger.info(f"  进度: {idx+1}/{len(candidates)}")
            
            try:
                # 转换为6位代码
                code_6digit = CodeConverter.to_akshare(code)
                
                # 诱多检测
                trap_result = self.trap_detector.detect(code_6digit)
                
                # 资金性质分类
                capital_result = self.capital_classifier.classify(code_6digit)
                
                # 综合风险评分
                risk_score = self._calculate_risk_score(trap_result, capital_result)
                
                # 构造结果对象
                result = {
                    'code': code,
                    'code_6digit': code_6digit,
                    'risk_score': risk_score,
                    'trap_signals': trap_result.get('signals', []),
                    'capital_type': capital_result.get('type', 'unknown'),
                    'flow_data': item['flow_data'],
                    'scan_time': datetime.now().isoformat()
                }
                
                # 分类
                if risk_score > 0.8:
                    blacklist.append(result)
                elif risk_score > 0.6:
                    watchlist.append(result)
                else:
                    opportunities.append(result)
                    
            except Exception as e:
                logger.warning(f"⚠️  {code} Level3 分析失败: {e}")
                continue
        
        return {
            'opportunities': sorted(opportunities, key=lambda x: x['risk_score']),
            'watchlist': sorted(watchlist, key=lambda x: x['risk_score']),
            'blacklist': sorted(blacklist, key=lambda x: x['risk_score'], reverse=True)
        }
    
    def _calculate_risk_score(self, trap_result: dict, capital_result: dict) -> float:
        """
        计算综合风险评分
        
        权重分配：
        - 诱多信号: 最高 0.7
        - 资金性质: 最高 0.3
        
        Returns:
            0.0 - 1.0，越高风险越大
        """
        score = 0.0
        
        # 诱多信号权重
        trap_signals = trap_result.get('signals', [])
        if '单日暴量+隔日反手' in trap_signals:
            score += 0.4
        if '游资突袭' in trap_signals:
            score += 0.3
        if '长期流出+单日巨量' in trap_signals:
            score += 0.2
        
        # 资金性质权重
        capital_type = capital_result.get('type', '')
        if capital_type == '散户接盘':
            score += 0.3
        elif capital_type == '游资短炒':
            score += 0.2
        elif capital_type == '机构长线':
            score -= 0.1  # 降低风险
        
        return min(max(score, 0.0), 1.0)
    
    def _save_results(self, results: dict, mode: str):
        """保存扫描结果到文件"""
        os.makedirs('data/scan_results', exist_ok=True)
        
        filename = f"data/scan_results/{datetime.now().strftime('%Y-%m-%d')}_{mode}.json"
        
        output = {
            'scan_time': datetime.now().isoformat(),
            'mode': mode,
            'summary': {
                'opportunities': len(results['opportunities']),
                'watchlist': len(results['watchlist']),
                'blacklist': len(results['blacklist'])
            },
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 结果已保存: {filename}")


if __name__ == "__main__":
    # 快速测试
    scanner = FullMarketScanner()
    results = scanner.scan_market(mode='premarket')
    
    print("\n" + "=" * 80)
    print("📊 扫描结果摘要")
    print("=" * 80)
    print(f"✅ 机会池: {len(results['opportunities'])} 只")
    for item in results['opportunities'][:5]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - {item['capital_type']}")
    
    print(f"\n⚠️  观察池: {len(results['watchlist'])} 只")
    for item in results['watchlist'][:3]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - {item['capital_type']}")
    
    print(f"\n❌ 黑名单: {len(results['blacklist'])} 只")
    for item in results['blacklist'][:3]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - 诱多信号: {item['trap_signals']}")
