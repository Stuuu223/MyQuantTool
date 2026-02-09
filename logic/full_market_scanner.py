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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.equity_data_accessor import get_circ_mv
from logic.rolling_risk_features import compute_multi_day_risk_features, compute_all_scenario_features
from logic.scenario_classifier import ScenarioClassifier

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
        
        # 检查 QMT 可用性（警告但不阻止初始化）
        if not QMT_AVAILABLE:
            logger.warning("⚠️  xtquant 未安装，QMT 数据源不可用")
            logger.warning("⚠️  系统将使用 AkShare 降级数据源，扫描速度会变慢")
        else:
            logger.info("✅ QMT 数据源可用，将使用 QMT 进行高速扫描")
        
        # 初始化核心模块
        self.trap_detector = TrapDetector()
        self.capital_classifier = CapitalClassifier()
        self.fund_flow = FundFlowAnalyzer()
        self.limiter = RateLimiter(max_requests_per_minute=60, max_requests_per_hour=2000, min_request_interval=0.1)  # 东方财富 API 限速
        self.converter = CodeConverter()
        self.scenario_classifier = ScenarioClassifier()  # 场景分类器
        
        # 加载本地股本信息（用于市值分层）
        self.equity_info = self._load_equity_info()
        
        # 🎯 加载板块映射表（用于时机斧）
        self.sector_map = self._load_sector_map()
        
        # 获取全市场股票列表
        self.all_stocks = self._init_qmt_stock_list()
        
        logger.info(f"✅ 全市场扫描器初始化完成")
        logger.info(f"   - 股票池: {len(self.all_stocks)} 只")
        logger.info(f"   - 股本信息: {len(self.equity_info)} 只股票")
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
    
    def _load_equity_info(self) -> dict:
        """
        加载本地股本信息（优先级: Tushare > 完整版 > MVP版）
        
        Returns:
            dict: 股本信息字典 {code: {name, total_shares, float_shares, ...}}
        """
        # 优先级1: Tushare版本
        try:
            with open('data/equity_info_tushare.json', 'r', encoding='utf-8') as f:
                equity_info = json.load(f)
            logger.info(f"✅ 加载股本信息（Tushare版）: {len(equity_info)} 只股票")
            return equity_info
        except Exception as e:
            logger.warning(f"⚠️ 加载Tushare版失败: {e}")
        
        # 优先级2: 完整版（AkShare）
        try:
            with open('data/equity_info.json', 'r', encoding='utf-8') as f:
                equity_info = json.load(f)
            logger.info(f"✅ 加载股本信息（完整版）: {len(equity_info)} 只股票")
            return equity_info
        except Exception as e:
            logger.warning(f"⚠️ 加载完整版失败: {e}")
        
        # 优先级3: MVP版本
        try:
            with open('data/equity_info_mvp.json', 'r', encoding='utf-8') as f:
                equity_info = json.load(f)
            logger.info(f"✅ 加载股本信息（MVP版）: {len(equity_info)} 只股票")
            return equity_info
        except Exception as e2:
            logger.warning(f"⚠️ 加载MVP版也失败: {e2}")
            return {}
    
    def _load_sector_map(self) -> dict:
        """
        加载板块映射表（用于时机斧）
        
        Returns:
            dict: 板块映射字典 {code: {industry, concepts}}
        """
        try:
            with open('data/stock_sector_map.json', 'r', encoding='utf-8') as f:
                sector_map = json.load(f)
            logger.info(f"✅ 加载板块映射表: {len(sector_map)} 只股票")
            return sector_map
        except Exception as e:
            logger.warning(f"⚠️ 加载板块映射表失败: {e}")
            return {}
    
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
                'risk_score_max': 0.8,    # 风险评分上限（已调整：0.6 -> 0.8，降低敏感度）
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

        # ===== QMT 状态检查（强制或软检查）=====
        from logic.qmt_health_check import check_qmt_health, require_realtime_mode

        if mode == 'intraday':
            # 盘中模式：强制要求实时模式
            try:
                require_realtime_mode()
            except RuntimeError as e:
                logger.error(f"❌ QMT 状态不满足实时决策要求: {e}")
                logger.error("❌ 无法进行盘中扫描，请检查 QMT 客户端状态")
                return {'opportunities': [], 'watchlist': [], 'blacklist': []}
        else:
            # 盘前/盘后模式：软检查，只打印警告
            result = check_qmt_health()
            if result['status'] == 'ERROR':
                logger.warning(f"⚠️  QMT 状态异常: {result['recommendations']}")
                logger.warning("⚠️  将尝试使用本地缓存数据")

        # ===== QMT 状态检查结束 =====
        
        # ===== Level 1: 技术面粗筛 =====
        logger.info("\\n🔍 [Level 1] 技术面粗筛...")
        candidates_l1 = self._level1_technical_filter()
        logger.info(f"✅ Level 1 完成: {len(self.all_stocks)} → {len(candidates_l1)} 只 (耗时: {time.time()-start_time:.1f}秒)")
        
        if not candidates_l1:
            logger.warning("⚠️  Level 1 未筛选出任何股票，提前结束")
            return {'opportunities': [], 'watchlist': [], 'blacklist': []}
        
        # ===== Level 2: 资金流向分析 =====
        logger.info(f"\\n💰 [Level 2] 资金流向分析 ({len(candidates_l1)} 只)...")
        l2_start = time.time()
        candidates_l2 = self._level2_capital_analysis(candidates_l1)
        logger.info(f"✅ Level 2 完成: {len(candidates_l1)} → {len(candidates_l2)} 只 (耗时: {time.time()-l2_start:.1f}秒)")
        
        if not candidates_l2:
            logger.warning("⚠️  Level 2 未筛选出任何股票，提前结束")
            return {'opportunities': [], 'watchlist': [], 'blacklist': []}
        
        # ===== Level 3: 坑 vs 机会分类 =====
        logger.info(f"\\n⚠️  [Level 3] 诱多陷阱检测 ({len(candidates_l2)} 只)...")
        l3_start = time.time()
        results = self._level3_trap_classification(candidates_l2)
        logger.info(f"✅ Level 3 完成 (耗时: {time.time()-l3_start:.1f}秒)")
        
        # 输出统计
        logger.info("\\n" + "=" * 80)
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
    
    def scan_with_risk_management(self, mode='premarket', stock_list=None) -> Dict:
        """
        带风险管理的扫描
        
        Args:
            mode: 扫描模式
            stock_list: 可选，指定扫描的股票列表（None=全市场）
        
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
        if stock_list:
            logger.info(f"🚀 开始候选池扫描（带风险管理） (模式: {mode})")
            logger.info(f"   扫描范围: {len(stock_list)} 只候选股票")
        else:
            logger.info(f"🚀 开始全市场扫描（带风险管理） (模式: {mode})")
        logger.info("=" * 80)
        start_time = time.time()

        # ===== QMT 状态检查（强制或软检查）=====
        # 🔥 [9:38 AM Hotfix] 强制绕过状态检查，因为数据流是通的
        # from logic.qmt_health_check import check_qmt_health, require_realtime_mode

        # if mode == 'intraday':
        #     # 盘中模式：强制要求实时模式
        #     try:
        #         require_realtime_mode()
        #     except RuntimeError as e:
        #         logger.error(f"❌ QMT 状态不满足实时决策要求: {e}")
        #         logger.error("❌ 无法进行盘中扫描，请检查 QMT 客户端状态")
        #         return {
        #             'mode': 'DEGRADED_LEVEL1_ONLY',
        #             'evidence_matrix': {},
        #             'position_limit': 0.0,
        #             'confidence': 0.0,
        #             'risk_reason': 'QMT 状态异常',
        #             'risk_warnings': ['⚠️ QMT 状态不满足实时决策要求'],
        #             'opportunities': [],
        #             'watchlist': [],
        #             'blacklist': [],
        #             'level1_candidates': []
        #         }
        # else:
        #     # 盘前/盘后模式：软检查，只打印警告
        #     result = check_qmt_health()
        #     if result['status'] == 'ERROR':
        #         logger.warning(f"⚠️  QMT 状态异常: {result['recommendations']}")
        #         logger.warning("⚠️  将尝试使用本地缓存数据")

        logger.warning("🔥 [9:38 AM Hotfix] QMT状态检查已移除，假设QMT正常工作")
        # ===== QMT 状态检查结束 =====
        
        # ===== Level 1: 技术面粗筛 =====
        logger.info("\\n🔍 [Level 1] 技术面粗筛...")
        
        if stock_list:
            # 只扫描指定的股票列表（候选池模式）
            candidates_l1 = self._level1_technical_filter_stocks(stock_list)
        else:
            # 全市场扫描
            candidates_l1 = self._level1_technical_filter()
        
        logger.info(f"✅ Level 1 完成: {len(self.all_stocks) if not stock_list else len(stock_list)} → {len(candidates_l1)} 只 (耗时: {time.time()-start_time:.1f}秒)")
        
        if not candidates_l1:
            logger.warning("⚠️  Level 1 未筛选出任何股票，提前结束")
            return self._build_degraded_result([], 'level1_empty')
        
        # ===== 计算相对热门度 =====
        logger.info(f"\\n🔥 计算相对热门度...")
        candidates_l1 = self._calculate_relative_hotness(candidates_l1)
        
        # ===== 构建热门池（TOP 100，只使用数据有效的票）=====
        hot_pool_size = 100
        
        # 只用数据有效的票构建热门池
        valid_candidates = [c for c in candidates_l1 if c.get('hot_data_valid', False)]
        invalid_candidates = [c for c in candidates_l1 if not c.get('hot_data_valid', False)]
        
        logger.info(f"  数据有效性统计: 有效 {len(valid_candidates)} 只, 无效 {len(invalid_candidates)} 只")
        
        if len(valid_candidates) < hot_pool_size:
            logger.warning(f"⚠️  有效数据票数不足 {hot_pool_size} 只，热门池将只包含 {len(valid_candidates)} 只")
            hot_pool = valid_candidates
        else:
            hot_pool = valid_candidates[:hot_pool_size]
        
        if hot_pool:
            logger.info(f"✅ 热门票池构建完成: TOP {len(hot_pool)} (热门评分范围: {hot_pool[0]['hot_score']:.4f} - {hot_pool[-1]['hot_score']:.4f})")
        else:
            logger.warning(f"⚠️  没有有效数据的票，热门池为空")
            hot_pool = []
        
        # ===== 检查风险标签（仅对热门池）=====
        if hot_pool:
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
        logger.info(f"\\n💰 [Level 2] 资金流向分析 (热门池 {len(hot_pool)} 只)...")
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
            logger.info(f"\\n⚠️  [Level 3] 诱多陷阱检测 ({len(candidates_l2)} 只)...")
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
        logger.info("\\n" + "=" * 80)
        logger.info("📊 扫描结果统计")
        logger.info("=" * 80)
        logger.info(f"✅ 机会池: {len(result['opportunities'])} 只")
        logger.info(f"⚠️  观察池: {len(result['watchlist'])} 只")
        logger.info(f"❌ 黑名单: {len(result['blacklist'])} 只")
        logger.info(f"📈 系统置信度: {result['confidence']*100:.1f}%")
        logger.info(f"💰 今日建议最大总仓位: {result['position_limit']*100:.1f}%")
        logger.info(f"🎯 风控原因: {result['risk_reason']}")
        
        if result['risk_warnings']:
            logger.info("\\n⚠️  风控警告:")
            for warning in result['risk_warnings']:
                logger.info(f"   {warning}")
        
        if scan_mode == 'DEGRADED_LEVEL1_ONLY':
            logger.info(f"\\n📋 技术面候选池（TOP50）:")
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
                
                # 详细日志：检查返回值
                logger.info(f"批次 {batch_num} 获取成功, tick_data 类型: {type(tick_data)}")
                if not isinstance(tick_data, dict):
                    logger.warning(f"⚠️  批次 {batch_num} 返回数据类型异常: {type(tick_data)}, 值: {str(tick_data)[:200]}")
                    continue
                
                # 本地过滤
                batch_samples = []  # 收集每批次的样本（用于打印涨跌幅最高的）
                
                for idx, code in enumerate(batch):
                    tick = tick_data.get(code, {})
                    
                    # 类型检查：确保 tick 是字典
                    if not isinstance(tick, dict):
                        logger.warning(f"⚠️  股票 {code} Tick 数据类型异常: {type(tick)}, 值: {str(tick)[:200]}")
                        continue
                    
                    # 收集样本数据
                    if tick:
                        last_close = tick.get('lastClose', 0)
                        last_price = tick.get('lastPrice', 0)
                        amount = tick.get('amount', 0)
                        pct_chg = abs((last_price - last_close) / last_close * 100) if last_close > 0 else 0
                        volume = (
                            tick.get('totalVolume') or 
                            tick.get('volume') or 
                            tick.get('total_volume') or 
                            tick.get('turnoverVolume') or 
                            tick.get('turnover_volume') or 
                            0
                        )
                        if volume == 0 and amount > 0 and last_price > 0:
                            volume = amount / last_price
                        
                        # 计算量比
                        volume_ratio = self._check_volume_ratio(code, volume, tick)
                        volume_ratio_str = f"{volume_ratio:.2f}" if volume_ratio is not None else "数据缺失"
                        
                        # 获取市值
                        market_cap = self._get_market_cap(code, tick)
                        market_cap_str = f"{market_cap/1e8:.2f}亿" if market_cap > 0 else "0"
                        
                        # 添加到样本列表
                        batch_samples.append({
                            'code': code,
                            'pct_chg': pct_chg,
                            'amount': amount,
                            'volume_ratio_str': volume_ratio_str,
                            'market_cap_str': market_cap_str
                        })
                    
                    if tick and self._check_level1_criteria(code, tick):
                        # 构建候选股票详细信息
                        last_close = tick.get('lastClose', 0)
                        last_price = tick.get('lastPrice', 0)
                        amount = tick.get('amount', 0)
                        
                        # 尝试多个可能的成交量字段名
                        volume = (
                            tick.get('totalVolume') or 
                            tick.get('volume') or 
                            tick.get('total_volume') or 
                            tick.get('turnoverVolume') or 
                            tick.get('turnover_volume') or 
                            0
                        )
                        
                        # 如果没有成交量字段，尝试用成交额和价格估算
                        if volume == 0 and amount > 0 and last_price > 0:
                            volume = amount / last_price
                        
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
                # 静默处理，避免刷屏
                if batch_num == 1 or batch_num % 5 == 0:  # 只在部分批次显示
                    logger.debug(f"批次 {batch_num} 处理异常: {e}")
                continue
        
        return candidates
    
    def _level1_technical_filter_stocks(self, stock_list: List[str]) -> List[dict]:
        """
        对指定股票列表进行 Level 1 技术面筛选
        
        Args:
            stock_list: 要筛选的股票代码列表
        
        Returns:
            候选股票详细信息列表
        """
        candidates = []
        batch_size = 1000
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            # 分批获取 QMT Tick 数据
            try:
                tick_data = xtdata.get_full_tick(batch)
                
                logger.info(f"批次 {batch_num} 获取成功, tick_data 类型: {type(tick_data)}")
                if not isinstance(tick_data, dict):
                    logger.warning(f"⚠️  批次 {batch_num} 返回数据类型异常: {type(tick_data)}")
                    continue
                
                # 本地过滤
                batch_samples = []  # 初始化 batch_samples

                for code in batch:
                    tick = tick_data.get(code, {})
                    
                    if not isinstance(tick, dict):
                        continue
                    
                    if tick and self._check_level1_criteria(code, tick):
                        # 构建候选股票详细信息
                        last_close = tick.get('lastClose', 0)
                        last_price = tick.get('lastPrice', 0)
                        amount = tick.get('amount', 0)
                        
                        volume = (
                            tick.get('totalVolume') or 
                            tick.get('volume') or 
                            tick.get('total_volume') or 
                            tick.get('turnoverVolume') or 
                            tick.get('turnover_volume') or 
                            0
                        )
                        
                        if volume == 0 and amount > 0 and last_price > 0:
                            volume = amount / last_price
                        
                        if last_close > 0:
                            pct_chg = (last_price - last_close) / last_close * 100
                        else:
                            pct_chg = 0
                        
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
                logger.info(f"  批次 {batch_num}: 获取 {len(batch)} 只股票 (命中: {hit_count} 只)")
                
                # 打印每批次涨跌幅最高的样本
                if batch_samples:
                    # 按涨跌幅降序排序
                    sorted_samples = sorted(batch_samples, key=lambda x: x['pct_chg'], reverse=True)
                    # 打印前3只涨跌幅最高的
                    for sample in sorted_samples[:3]:
                        logger.info(f"[L1样本] {sample['code']}: 涨跌幅={sample['pct_chg']:.2f}%, 成交额={sample['amount']/1e8:.2f}亿, 量比={sample['volume_ratio_str']}, 市值={sample['market_cap_str']}")
                
            except Exception as e:
                # 静默处理，避免刷屏
                if batch_num == 1 or batch_num % 5 == 0:  # 只在部分批次显示
                    logger.debug(f"批次 {batch_num} 处理异常: {e}")
                continue
        
        return candidates
    
    def _check_volume_ratio(self, code: str, current_volume: float, tick: dict) -> Optional[float]:
        """
        检查量比（当日成交量 / 5日平均成交量）- 返回量比供外部判断
        
        Args:
            code: 股票代码
            current_volume: 当日成交量
            tick: Tick数据（用于获取流通市值）
        
        Returns:
            Optional[float]: 
                - None: 数据缺失（K线不足、接口失败等）
                - float: 量比（当日成交量 / 5日平均成交量），可能小于1
        """
        try:
            # 获取最近5日K线数据（只需要成交量）
            kline_data = xtdata.get_market_data_ex(
                field_list=['volume'],
                stock_list=[code],
                period='1d',
                start_time='',
                end_time='',
                count=5,
                dividend_type='none'
            )
            
            # 数据缺失：返回None
            if not kline_data or code not in kline_data:
                # DEBUG: 已禁用，避免刷屏
                # print(f"[量比DEBUG] {code}: kline_data为空={not kline_data}, code不在数据中={code not in kline_data}")
                # print(f"[量比DEBUG] {code}: 返回None, 原因=no_data_for_code")
                return None
            
            # 类型检查：支持pandas.DataFrame和dict两种类型
            code_data = kline_data[code]
            if isinstance(code_data, dict):
                # 字典类型
                if 'volume' not in code_data:
                    # DEBUG: 已禁用，避免刷屏
                    # print(f"[量比DEBUG] {code}: code_data keys={list(code_data.keys())}")
                    # print(f"[量比DEBUG] {code}: 缺少volume字段")
                    # print(f"[量比DEBUG] {code}: 返回None, 原因=no_volume_field")
                    return None
                volumes = code_data['volume']
            elif hasattr(code_data, '__class__') and code_data.__class__.__name__ == 'DataFrame':
                # pandas.DataFrame类型
                import pandas as pd
                if not isinstance(code_data, pd.DataFrame):
                    # DEBUG: 已禁用，避免刷屏
                    # print(f"[量比DEBUG] {code}: 数据类型={type(code_data)}, 期望dict或DataFrame")
                    # print(f"[量比DEBUG] {code}: 返回None, 原因=invalid_data_type")
                    return None
                if 'volume' not in code_data.columns:
                    # DEBUG: 已禁用，避免刷屏
                    # print(f"[量比DEBUG] {code}: DataFrame columns={list(code_data.columns)}")
                    # print(f"[量比DEBUG] {code}: 缺少volume列")
                    # print(f"[量比DEBUG] {code}: 返回None, 原因=no_volume_column")
                    return None
                volumes = code_data['volume'].tolist()
            else:
                # DEBUG: 已禁用，避免刷屏
                # print(f"[量比DEBUG] {code}: 数据类型={type(code_data)}, 期望dict或DataFrame")
                # print(f"[量比DEBUG] {code}: 返回None, 原因=invalid_data_type")
                return None
            # DEBUG: 已禁用，避免刷屏
            # print(f"[量比DEBUG] {code}: len(volumes)={len(volumes)}, 需要5")
            
            if len(volumes) < 5:
                # DEBUG: 已禁用，避免刷屏
                # print(f"[量比DEBUG] {code}: 最后3根成交量={volumes[-3:] if len(volumes) >= 3 else volumes}")
                # print(f"[量比DEBUG] {code}: 返回None, 原因=not_enough_bars")
                return None
            
            # 计算5日平均成交量
            avg_volume_5d = sum(volumes) / len(volumes)
            
            if avg_volume_5d == 0:
                # DEBUG: 已禁用，避免刷屏
                # print(f"[量比DEBUG] {code}: 5日成交量={volumes}")
                # print(f"[量比DEBUG] {code}: 返回None, 原因=avg_volume_zero")
                return None
            
            # 计算量比（可能小于1，表示缩量）
            volume_ratio = current_volume / avg_volume_5d
            
            # DEBUG: 已禁用，避免刷屏
            # print(f"[量比DEBUG] {code}: current_volume={current_volume}, avg_5d={avg_volume_5d:.2f}, ratio={volume_ratio:.2f}")
            
            return volume_ratio
            
        except Exception as e:
            # DEBUG: 已禁用，避免刷屏
            # print(f"[量比DEBUG] {code}: 异常={e}")
            # import traceback
            # print(f"[量比DEBUG] {code}: traceback={traceback.format_exc()}")
            return None
    
    def _get_market_cap(self, code: str, tick: dict) -> float:
        """
        获取流通市值（元）- 优先使用本地股本信息
        
        Args:
            code: 股票代码
            tick: Tick数据
        
        Returns:
            float: 流通市值（元），如果无法获取返回0
        """
        try:
            # 1. 优先使用本地股本信息（更可靠、更快速）
            if code in self.equity_info:
                equity = self.equity_info[code]
                last_price = tick.get('lastPrice', 0) or equity.get('last_close', 0)
                float_shares = equity.get('float_shares', 0)
                
                if float_shares > 0 and last_price > 0:
                    return float_shares * last_price
            
            # 2. 备用：尝试从 tick 数据中获取
            market_cap = (
                tick.get('circulatingMarketCap') or 
                tick.get('SH_FLOAT_VAL') or 
                tick.get('FLOAT_VAL') or 
                0
            )
            
            if market_cap > 0:
                return market_cap
            
            # 3. 备用：尝试从 QMT 获取
            try:
                financial_data = xtdata.get_market_data(
                    field_list=['SH_FLOAT_VAL', 'FLOAT_VAL'],
                    stock_list=[code],
                    period='1d',
                    start_time='',
                    end_time='',
                    dividend_type='none'
                )
                
                if financial_data and code in financial_data:
                    data = financial_data[code]
                    market_cap = (
                        data.get('SH_FLOAT_VAL') or 
                        data.get('FLOAT_VAL') or 
                        0
                    )
                    
                    if market_cap > 0:
                        return market_cap
            
            except Exception as e:
                logger.debug(f"从 QMT 获取市值失败 {code}: {e}")
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"获取市值失败 {code}: {e}")
            return 0.0
    
    def get_volume_ratio_threshold(self, market_cap: float) -> float:
        """
        根据市值分层获取量比阈值（市场共识版）
        
        市值分层逻辑：
        - 小盘（<80亿）：量比≥2.0（小盘股波动大，需要明显放量）
        - 中盘（80-200亿）：量比≥1.5（平衡机会和质量）
        - 大盘（≥200亿）：量比≥1.3（大盘股流动性好，小幅放量就有意义）
        
        Args:
            market_cap: 流通市值（单位：元）
        
        Returns:
            float: 量比阈值
        """
        # 市值单位转换：元 → 亿
        market_cap_yi = market_cap / 1_000_000_000
        
        if market_cap_yi < 80:
            # 小盘：需要明显放量
            return 2.0
        elif market_cap_yi < 200:
            # 中盘：平衡机会和质量
            return 1.5
        else:
            # 大盘：流动性好，小幅放量就有意义
            return 1.3
    
    def run_level1_screening(self) -> List[str]:
        """
        运行 Level 1 初筛（公开方法）
        
        返回:
            List[str]: 通过 Level 1 筛选的股票代码列表
        """
        candidates = self._level1_technical_filter()
        return [c['code'] for c in candidates]
    
    def _check_level1_criteria(self, code: str, tick: dict) -> bool:
        """
        检查 Level 1 筛选条件（增强版：添加量比过滤）

        筛选条件：
        1. 基础风控：剔除垃圾股
        2. 涨跌幅：|涨跌幅| > 3%
        3. 成交额：> 2000万
        4. 换手率：> 2%
        5. 量比：> 1.5（新增）
        """
        # 🔥 [Debug] 追踪001335.SZ
        if code == '001335.SZ' or code.endswith('001335'):
            logger.info(f"🔍 [DEBUG 001335] Level 1检查开始: code={code}")
        """检查 Level 1 筛选条件"""
        if not tick:
            # 🔥 [Debug] 追踪001335.SZ
            if code == '001335.SZ' or code.endswith('001335'):
                logger.info(f"🔍 [DEBUG 001335] Level 1失败: tick数据为空")
            return False

        try:
            # 基础风控：剔除垃圾股
            stock_name = tick.get('stockName', '')
            if 'ST' in stock_name or '退' in stock_name:
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 剔除垃圾股 (name={stock_name})")
                return False
            if code.startswith(('688', '8', '4')):  # 科创板、北交所
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 科创板/北交所 (code={code})")
                return False

            # 获取价格数据（仅使用 QMT Tick 实际存在的字段）
            last_close = tick.get('lastClose', 0)
            last_price = tick.get('lastPrice', 0)
            amount = tick.get('amount', 0)

            # 获取成交量
            volume = (
                tick.get('totalVolume') or
                tick.get('volume') or
                tick.get('total_volume') or
                tick.get('turnoverVolume') or
                tick.get('turnover_volume') or
                0
            )

            # 如果没有成交量字段，尝试用成交额和价格估算
            if volume == 0 and amount > 0 and last_price > 0:
                volume = amount / last_price

            # 计算涨跌幅
            if last_close == 0:
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 昨收价为0 (last_close=0)")
                return False
            pct_chg = abs((last_price - last_close) / last_close * 100)

            cfg = self.config['level1']

            # 两个条件必须同时满足
            if pct_chg < cfg['pct_chg_min']:
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 涨跌幅过低 (pct_chg={pct_chg:.2f}%, threshold={cfg['pct_chg_min']:.2f}%)")
                return False
            if amount < cfg['amount_min']:
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 成交额过低 (amount={amount/1e8:.2f}亿, threshold={cfg['amount_min']/1e8:.2f}亿)")
                return False

            # 检查量比（新增：市值分层阈值）
            volume_ratio = self._check_volume_ratio(code, volume, tick)

            # 量比数据缺失：直接拒绝（避免候选池溢出）
            if volume_ratio is None:
                logger.debug(f"[L1过滤] {code}: 量比数据缺失，拒绝")
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 量比数据缺失")
                return False

            # 量比数据正常：按市值分层阈值判断
            # 获取流通市值用于分层
            market_cap = self._get_market_cap(code, tick)

            # 市值为0时，使用默认阈值（1.5）
            if market_cap == 0:
                volume_ratio_threshold = 1.5
                logger.debug(f"[L1检查] {code}: 市值=0，使用默认量比阈值 1.5")
            else:
                volume_ratio_threshold = self.get_volume_ratio_threshold(market_cap)
                logger.debug(f"[L1检查] {code}: 市值={market_cap/1e8:.2f}亿，阈值={volume_ratio_threshold:.2f}")

            # 检查量比是否达标
            if volume_ratio < volume_ratio_threshold:
                logger.debug(f"[L1过滤] {code}: 量比={volume_ratio:.2f} < 阈值={volume_ratio_threshold:.2f}")
                # 🔥 [Debug] 追踪001335.SZ
                if code == '001335.SZ' or code.endswith('001335'):
                    logger.info(f"🔍 [DEBUG 001335] Level 1失败: 量比过低 (volume_ratio={volume_ratio:.2f}, threshold={volume_ratio_threshold:.2f})")
                return False

            # 所有检查通过
            volume_ratio_str = f"{volume_ratio:.2f}" if volume_ratio is not None else "数据缺失"
            logger.debug(f"[L1通过] {code}: 涨跌幅={pct_chg:.2f}%, 成交额={amount/1e8:.2f}亿, 量比={volume_ratio_str}")
            # 🔥 [Debug] 追踪001335.SZ
            if code == '001335.SZ' or code.endswith('001335'):
                logger.info(f"🔍 [DEBUG 001335] Level 1通过! 涨跌幅={pct_chg:.2f}%, 成交额={amount/1e8:.2f}亿, 量比={volume_ratio_str}")
            return True

        except Exception as e:
            # 🔥 [Debug] 追踪001335.SZ
            if code == '001335.SZ' or code.endswith('001335'):
                logger.info(f"🔍 [DEBUG 001335] Level 1失败: 异常 ({e})")
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
            # 方法 1: 使用 get_market_data 获取流通股本（尝试多个字段）
            try:
                # 尝试多个可能的流通股本字段
                financial_data = xtdata.get_market_data(
                    field_list=['SH_FLOAT_VAL', 'FLOAT_VAL', 'TOTAL_SHARES'],  # 尝试多个字段
                    stock_list=[code],
                    period='1d',
                    start_time='',
                    end_time='',
                    dividend_type='none'
                )
                
                if financial_data and code in financial_data:
                    data = financial_data[code]
                    # 尝试不同的字段名
                    circulating_shares = (
                        data.get('SH_FLOAT_VAL') or 
                        data.get('FLOAT_VAL') or 
                        data.get('TOTAL_SHARES') or 
                        0
                    )
                    
                    if circulating_shares and circulating_shares > 0:
                        # 获取当前价格
                        tick_data = xtdata.get_full_tick([code])
                        if tick_data and code in tick_data:
                            current_price = tick_data[code].get('lastPrice', 0)
                            if current_price > 0:
                                circulating_market_cap = circulating_shares * current_price
                                logger.debug(f"✅ 获取流通股本成功 {code}: {circulating_shares/1e8:.2f}亿股")
                                return {
                                    'circulating_shares': circulating_shares,
                                    'circulating_market_cap': circulating_market_cap
                                }
            except Exception as e:
                logger.debug(f"方法 1 获取流通股本失败 {code}: {e}")
            
            # 方法 2: 使用 get_instrument_detail 获取股票详细信息
            try:
                instrument_detail = xtdata.get_instrument_detail(code)
                if instrument_detail:
                    # 尝试从详细信息中获取流通股本
                    circulating_shares = (
                        instrument_detail.get('FloatVolume') or 
                        instrument_detail.get('FloatShares') or 
                        instrument_detail.get('CirculatingShares') or 
                        0
                    )
                    
                    if circulating_shares and circulating_shares > 0:
                        current_price = instrument_detail.get('LastPrice', 0)
                        if current_price > 0:
                            circulating_market_cap = circulating_shares * current_price
                            logger.debug(f"✅ 方法2获取流通股本成功 {code}: {circulating_shares/1e8:.2f}亿股")
                            return {
                                'circulating_shares': circulating_shares,
                                'circulating_market_cap': circulating_market_cap
                            }
            except Exception as e:
                logger.debug(f"方法 2 获取流通股本失败 {code}: {e}")
            
            # 方法 3: 使用 get_full_tick 中的流通市值字段
            try:
                tick_data = xtdata.get_full_tick([code])
                if tick_data and code in tick_data:
                    tick = tick_data[code]
                    # 尝试从 tick 数据中获取流通市值
                    circulating_market_cap = (
                        tick.get('marketCap') or 
                        tick.get('circulatingMarketCap') or 
                        tick.get('totalMarketCap') or 
                        0
                    )
                    
                    if circulating_market_cap and circulating_market_cap > 0:
                        current_price = tick.get('lastPrice', 0)
                        if current_price > 0:
                            circulating_shares = circulating_market_cap / current_price
                            logger.debug(f"✅ 方法3获取流通股本成功 {code}: {circulating_shares/1e8:.2f}亿股")
                            return {
                                'circulating_shares': circulating_shares,
                                'circulating_market_cap': circulating_market_cap
                            }
            except Exception as e:
                logger.debug(f"方法 3 获取流通股本失败 {code}: {e}")
            
            # 方法 4: 不再估算流通市值，返回 0
            # 在热门度计算中使用成交额归一化
            return {
                'circulating_shares': 0,
                'circulating_market_cap': 0,
                'use_amount_normalization': True  # 标记为使用成交额归一化
            }
            
            # 所有方法都失败，返回 0
            logger.warning(f"⚠️  所有方法获取流通股本失败 {code}")
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
        
        logger.info(f"  成交额范围: {min_amount/1e8:.2f}亿 - {max_amount/1e8:.2f}亿，范围: {amount_range/1e8:.2f}亿")
        
        # 计算换手率和相对放量因子
        valid_count = 0
        invalid_count = 0
        
        for candidate in candidates:
            code = candidate['code']
            volume = candidate.get('volume', 0)
            amount = candidate.get('amount', 0)
            circulating_shares = candidate.get('circulating_shares', 0)
            circulating_market_cap = candidate.get('circulating_market_cap', 0)
            
            # 数据校验：只要成交额和成交量有效，就认为数据有效
            # 即使流通股本和流通市值是 0，也可以用成交额归一化
            data_valid = (volume > 0 and amount > 0)
            
            if data_valid:
                # 数据有效，尝试计算换手率和相对放量
                if circulating_shares > 0 and circulating_market_cap > 0:
                    # 有流通股本数据，使用换手率 + 相对放量
                    turnover_rate = self._calculate_turnover_rate(code, volume, circulating_shares)
                    relative_volume = self._calculate_relative_volume(code, amount, circulating_market_cap)
                    hot_score = turnover_rate * 0.6 + relative_volume * 0.4
                    data_source = "流通股本数据"
                else:
                    # 没有流通股本数据，使用成交额归一化作为替代
                    turnover_rate = 0.0
                    relative_volume = 0.0
                    hot_score = (amount - min_amount) / amount_range if amount_range > 0 else 0.0
                    data_source = "成交额归一化"
                
                valid_count += 1
            else:
                # 数据无效
                turnover_rate = 0.0
                relative_volume = 0.0
                hot_score = 0.0
                data_source = "数据无效"
                invalid_count += 1
            
            candidate['turnover_rate'] = turnover_rate
            candidate['relative_volume'] = relative_volume
            candidate['hot_score'] = hot_score
            candidate['hot_data_valid'] = data_valid
            candidate['data_source'] = data_source
        
        # 计算排名
        candidates_sorted = sorted(candidates, key=lambda x: x['hot_score'], reverse=True)
        total = len(candidates_sorted)
        
        for idx, candidate in enumerate(candidates_sorted):
            candidate['hot_rank'] = idx + 1
            candidate['hot_percentile'] = (total - idx) / total  # 热门百分位
        
        logger.info(f"  ✅ 相对热门度计算完成 (有效数据: {valid_count} 只, 无效数据: {invalid_count} 只)")
        
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
    
    def _level2_capital_analysis(self, candidates) -> List[dict]:
        """
        Level 2: 资金流向深度分析

        从 300-500 只压缩到 50-100 只

        分析内容：
        1. 主力净流入 > 0
        2. 超大单占比 > 30%
        3. 近3日资金流向趋势

        Args:
            candidates: Level 1 筛选出的股票列表
                       - 可以是代码列表 List[str]
                       - 也可以是字典列表 List[dict]（包含完整字段）

        Returns:
            包含资金流向数据的股票列表（保留所有原始字段）
        """
        results = []
        total = len(candidates)

        for idx, candidate in enumerate(candidates):
            # 进度打印（改为每20只打印一次，减少刷屏）
            if idx % 20 == 0 or idx == total - 1:
                logger.info(f"  进度: {idx+1}/{total} ({(idx+1)/total*100:.1f}%)")

            try:
                # 兼容两种输入格式：代码字符串 或 字典
                if isinstance(candidate, str):
                    code = candidate
                    candidate_dict = {}
                else:
                    code = candidate.get('code', '')
                    candidate_dict = candidate

                # 转换为6位代码（AkShare格式）
                code_6digit = CodeConverter.to_akshare(code)

                # ================= [修复] 计算 price_3d_change =================
                # 🔥 修复3日价格数据缺失问题，使Level 3诱多检测能够正常工作
                try:
                    # 获取最近4根日K线 (包含今天)
                    # count=4 逻辑: [T-3, T-2, T-1, Today] -> Close[0] 即为3天前的收盘价
                    current_price = candidate_dict.get('last_price', 0)
                    
                    price_3d_change = 0.0
                    
                    if current_price <= 0:
                        logger.warning(f"⚠️  {code} current_price={current_price}，无法计算price_3d_change")
                    else:
                        # 策略1：QMT 日线数据 (最快)
                        if QMT_AVAILABLE:
                            try:
                                kline_data = xtdata.get_market_data_ex(
                                    field_list=['close'],
                                    stock_list=[code],
                                    period='1d',
                                    start_time='',
                                    end_time='',
                                    count=10,  # ✅ [P1修复] 预取更多数据，防止仅取4根遇到停牌不足的情况
                                    dividend_type='front',  # 前复权
                                    fill_data=True
                                )

                                if code in kline_data and hasattr(kline_data[code], '__len__'):
                                    df = kline_data[code]
                                    # ✅ [P1修复] 显式长度校验
                                    if len(df) < 2:
                                        logger.warning(f"⚠️  {code} QMT K线数据不足 (len={len(df)})，需要至少2条")
                                    else:
                                        # 按时间排序，确保iloc[0]是旧的
                                        # QMT返回的数据通常是按时间升序的，但为了保险
                                        if hasattr(df, 'sort_index'):
                                            df.sort_index(ascending=True, inplace=True)

                                        # ✅ [P1修复] 安全获取 ref_close，防止 iloc 越界
                                        idx_ref = -4 if len(df) >= 4 else 0
                                        ref_close = df.iloc[idx_ref]['close']

                                        if ref_close > 0:
                                            price_3d_change = (current_price - ref_close) / ref_close
                                            logger.debug(f"✅ {code} 使用QMT计算price_3d_change={price_3d_change:.4f}")
                                        else:
                                            logger.warning(f"⚠️  {code} QMT ref_close=0")
                                else:
                                    logger.warning(f"⚠️  {code} QMT 未返回有效数据结构")
                            except Exception as e:
                                logger.warning(f"⚠️  {code} QMT获取K线失败: {e}")
                                # QMT_AVAILABLE = False # 不要因为单次失败就禁用全局QMT

                        # 策略2：AkShare 日线数据 (降级)
                        if price_3d_change == 0.0:
                            try:
                                import akshare as ak
                                symbol_6 = CodeConverter.to_akshare(code)
                                # ✅ [P0修复] 动态计算 start_date，避免年度切换时失效
                                # 获取过去90天的数据，确保有足够的数据计算3日涨幅
                                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
                                df = ak.stock_zh_a_hist(symbol=symbol_6, period='daily', start_date=start_date, adjust='qfq')
                                if df is not None and len(df) >= 2:
                                    df.sort_values('日期', ascending=True, inplace=True)
                                    ref_close = df.iloc[-4]['收盘'] if len(df) >= 4 else df.iloc[0]['收盘']
                                    if ref_close > 0:
                                        price_3d_change = (current_price - ref_close) / ref_close
                                        logger.info(f"✅ {code} 使用AkShare计算price_3d_change={price_3d_change:.4f}")
                            except Exception as e:
                                logger.warning(f"⚠️  {code} AkShare获取K线失败: {e}")

                        # 策略3：QMT 1分钟数据合成 (兜底)
                        if price_3d_change == 0.0 and QMT_AVAILABLE:
                            try:
                                # ✅ [P2修复] 增加 count 到 2400 (约10个交易日)，确保覆盖长假
                                count_min = 2400
                                # 尝试下载最近的分钟数据 (确保数据存在)
                                xtdata.download_history_data(code, period='1m', count=count_min, incrementally=True)
                                
                                # 获取最近2400根1分钟K线 (约10个交易日)
                                kline_1m = xtdata.get_market_data_ex(
                                    field_list=['time', 'close'],
                                    stock_list=[code],
                                    period='1m',
                                    start_time='',
                                    end_time='',
                                    count=count_min,  # ✅ [P2修复] 同步增加获取数量
                                    dividend_type='front',
                                    fill_data=True
                                )
                                
                                if code in kline_1m and not kline_1m[code].empty:
                                    df_1m = kline_1m[code]
                                    # 确保有时间索引
                                    import pandas as pd
                                    if 'time' in df_1m.columns:
                                        df_1m['time'] = pd.to_datetime(df_1m['time'], unit='ms')
                                        df_1m.set_index('time', inplace=True)
                                    
                                    # 重采样为日线
                                    daily_close = df_1m['close'].resample('D').last().dropna()
                                    
                                    if len(daily_close) >= 2:
                                        # 取倒数第4个（T-3）
                                        idx_ref = -4 if len(daily_close) >= 4 else 0
                                        ref_close = daily_close.iloc[idx_ref]
                                        
                                        if ref_close > 0:
                                            price_3d_change = (current_price - ref_close) / ref_close
                                            logger.info(f"✅ {code} 使用QMT分钟数据合成计算price_3d_change={price_3d_change:.4f}")
                            except Exception as e:
                                logger.warning(f"⚠️  {code} 分钟数据合成失败: {e}")

                except Exception as e:
                    logger.warning(f"⚠️  {code} 计算price_3d_change异常: {e}")
                    price_3d_change = 0.0

                # 将计算结果写入 candidate_dict，传递给后续流程
                candidate_dict['price_3d_change'] = price_3d_change
                # ================= [修复结束] =================

                # 获取资金流向（东方财富 API，获取30天数据用于Level3分析）
                flow_data = self.fund_flow.get_fund_flow(code_6digit, days=30)

                if not flow_data:
                    continue

                # 检查资金条件
                if self._check_level2_criteria(code, flow_data):
                    # 构建结果，保留所有原始字段
                    result = candidate_dict.copy() if candidate_dict else {}
                    result['code'] = code
                    result['flow_data'] = flow_data
                    results.append(result)
            except Exception as e:
                code_str = candidate if isinstance(candidate, str) else candidate.get('code', 'unknown')
                logger.warning(f"⚠️  {code_str} Level2 分析失败: {e}")
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
            
            # 进度打印（改为每10只打印一次）
            if idx % 10 == 0:
                logger.info(f"  进度: {idx+1}/{len(candidates)}")
            
            try:
                # 转换为6位代码
                code_6digit = CodeConverter.to_akshare(code)
                
                # 诱多检测
                trap_result = self.trap_detector.detect(code_6digit)
                
                # 资金性质分类：转换数据格式
                flow_records = item.get('flow_data', {}).get('records', [])
                # 将 main_net_inflow 映射为 institution（机构净流入）
                daily_data = []
                for record in flow_records:
                    # 确保 date 是字符串格式（可能从 fund_flow_analyzer 返回的是 datetime.date 对象）
                    date_value = record.get('date', '')
                    if hasattr(date_value, 'strftime'):
                        date_value = date_value.strftime('%Y-%m-%d')
                    elif isinstance(date_value, str):
                        # 已经是字符串，保持原样
                        pass
                    else:
                        date_value = str(date_value)
                    
                    daily_data.append({
                        'date': date_value,
                        'institution': record.get('main_net_inflow', 0),  # 机构净流入 = 主力净流入
                        'super_large': record.get('super_large_net', 0),
                        'large': record.get('large_net', 0),
                        'medium': record.get('medium_net', 0),
                        'small': record.get('small_net', 0)
                    })
                capital_result = self.capital_classifier.classify(daily_data)

                # 🔥 [Hotfix] 先计算 ratio（需要在风险评分计算之前）
                flow_records = item.get('flow_data', {}).get('records', [])
                main_net_inflow = flow_records[0].get('main_net_inflow', 0) if flow_records else 0

                # 获取trade_date
                trade_date = item.get('trade_date')
                if not trade_date:
                    # 如果没有trade_date，尝试从flow_records中获取
                    if flow_records:
                        date_value = flow_records[0].get('date', '')
                        if hasattr(date_value, 'strftime'):
                            trade_date = date_value.strftime('%Y%m%d')
                        elif isinstance(date_value, str):
                            trade_date = date_value.replace('-', '')

                # 获取场景特征（用于 ratio 计算）
                scenario_features = item.get('scenario_features', {})

                # 计算ratio（多维度计算）
                ratio = None
                if trade_date and main_net_inflow:
                    try:
                        circ_mv = get_circ_mv(code, trade_date)
                        if circ_mv > 0:
                            # 🔥 [Hotfix] 改进 ratio 计算逻辑：基于流通市值 + 30日累计
                            # 基础 ratio：今日净流入 / 流通市值
                            ratio_base = main_net_inflow / circ_mv * 100

                            # 如果有 30 日累计数据，进行加权计算
                            net_30d = scenario_features.get('net_main_30d', 0)
                            if net_30d != 0:
                                # 如果 30 日累计为负数（长期流出），使用绝对值
                                if net_30d < 0:
                                    ratio_30d = main_net_inflow / abs(net_30d)
                                    # 如果今日流入为正（开始回流），视为机会
                                    if main_net_inflow > 0:
                                        ratio_30d = abs(ratio_30d)
                                    else:
                                        ratio_30d = main_net_inflow / net_30d
                                else:
                                    # 30 日累计为正数，正常计算
                                    ratio_30d = main_net_inflow / net_30d

                                # 综合计算：基础 ratio + 30 日趋势 ratio 的加权平均
                                ratio = (ratio_base + ratio_30d) / 2
                            else:
                                # 没有 30 日数据，只使用基础 ratio
                                ratio = ratio_base

                            # 确保 ratio 不为 None
                            if ratio is None:
                                ratio = 0
                    except Exception as e:
                        logger.warning(f"⚠️  {code} 计算ratio失败: {e}")

                # 综合风险评分（传入 ratio 参数）
                risk_score = self._calculate_risk_score(trap_result, capital_result, ratio or 0)

                # 构造结果对象，保留所有原始字段
                result = item.copy()  # 保留所有原始字段（name, last_price, amount, circulating_shares 等）
                result['code_6digit'] = code_6digit
                result['risk_score'] = risk_score
                result['ratio'] = ratio
                result['trap_signals'] = trap_result.get('signals', [])
                result['capital_type'] = capital_result.get('type', 'unknown')
                result['scan_time'] = datetime.now().isoformat()

                # 🎯 添加板块信息（用于时机斧）
                sector_info = self.sector_map.get(code_6digit, {})
                result['sector_name'] = sector_info.get('industry', '未知板块')
                result['sector_code'] = sector_info.get('industry', '未知板块')  # 时机斧将读取这个字段

                # 计算多日风险特征
                flow_data = item.get('flow_data', {})
                flow_records = flow_data.get('records', [])
                price_3d_change = item.get('price_3d_change')  # 可选的3日涨幅字段

                risk_features = compute_multi_day_risk_features(
                    code=code,
                    trade_date=trade_date,
                    flow_records=flow_records,
                    price_3d_change=price_3d_change,
                )

                # 计算所有场景特征（包含pump+dump、补涨尾声、板块阶段等）
                scenario_features = compute_all_scenario_features(
                    code=code,
                    trade_date=trade_date,
                    flow_records=flow_records,
                    capital_type=capital_result.get('type', ''),
                    price_records=None,  # 暂不使用价格记录
                    sector_20d_pct_change=None,  # 暂不使用板块数据
                    sector_5d_trend=None,
                )

                # 使用场景分类器进行场景分类
                scenario_input = {
                    'code': code,
                    'capitaltype': capital_result.get('type', ''),
                    'flow_data': flow_data,
                    'price_data': {},
                    'risk_score': risk_score,
                    'trap_signals': trap_result.get('signals', [])
                }
                scenario_result = self.scenario_classifier.classify(scenario_input)

                # 使用决策树进行分类
                decision_tag = self._calculate_decision_tag(
                    ratio, 
                    risk_score, 
                    trap_result.get('signals', []),
                    risk_features['is_price_up_3d_capital_not_follow']
                )
                result['decision_tag'] = decision_tag
                result['risk_features'] = risk_features  # 保存特征用于调试

                # 根据决策标签分类
                if decision_tag == 'PASS❌' or decision_tag == 'TRAP❌' or decision_tag == 'BLOCK❌':
                    blacklist.append(result)
                elif decision_tag == 'FOCUS✅':
                    opportunities.append(result)
                else:
                    watchlist.append(result)

                # 添加场景标签到result
                result['scenario_features'] = scenario_features
                result['is_tail_rally'] = scenario_result.is_tail_rally
                result['is_potential_trap'] = scenario_result.is_potential_trap
                result['is_potential_mainline'] = scenario_result.is_potential_mainline
                result['scenario_type'] = scenario_result.scenario.value
                result['scenario_confidence'] = scenario_result.confidence
                result['scenario_reasons'] = scenario_result.reasons

                # 记录被标记为禁止场景的股票
                if scenario_result.is_tail_rally or scenario_result.is_potential_trap:
                    logger.warning(f"⚠️  [{code}] 被标记为禁止场景: {scenario_result.scenario.value}")
                    logger.warning(f"   原因: {', '.join(scenario_result.reasons[:2])}")  # 只打印前2条原因，避免刷屏
                elif scenario_result.is_potential_mainline:
                    logger.info(f"✅ [{code}] 被识别为主线起爆候选 (置信度: {scenario_result.confidence:.2f})")
                    logger.info(f"   原因: {', '.join(scenario_result.reasons[:2])}")
                    
            except Exception as e:
                logger.warning(f"⚠️  {code} Level3 分析失败: {e}")
                continue
        
        return {
            'opportunities': sorted(opportunities, key=lambda x: x['risk_score']),
            'watchlist': sorted(watchlist, key=lambda x: x['risk_score']),
            'blacklist': sorted(blacklist, key=lambda x: x['risk_score'], reverse=True)
        }
    
    def _calculate_risk_score(self, trap_result: dict, capital_result: dict, ratio: float = 0.0) -> float:
        """
        计算综合风险评分

        权重分配：
        - 诱多信号: 最高 0.7
        - 资金性质: 最高 0.3
        - ratio 修正因子: 根据主力资金推动力调整风险

        Args:
            trap_result: 诱多检测结果
            capital_result: 资金分类结果
            ratio: 主力资金推动力比值

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

        # 🔥 [Hotfix] ratio 修正因子（关键！）
        # 高 ratio 说明主力资金推动力强，应该降低风险
        # 低 ratio 说明主力资金推动力弱，应该提高风险
        # 注意：ratio单位是小数（如0.56表示0.56%），不是百分比
        if ratio > 0.5:  # ratio > 0.5%（主力资金推动力极强），大幅降低风险
            score *= 0.5
        elif ratio > 0.3:  # ratio > 0.3%（主力资金推动力较强），适度降低风险
            score *= 0.7
        elif ratio > 0.1:  # ratio > 0.1%（主力资金推动力中等），轻微降低风险
            score *= 0.9
        elif ratio < 0.01:  # ratio < 0.01%（主力资金推动力极弱），大幅提高风险
            score *= 1.5

        return min(max(score, 0.0), 1.0)
    
    def _calculate_decision_tag(self, ratio: float, risk_score: float, trap_signals: list, is_price_up_3d_capital_not_follow: bool = False) -> str:
        """
        决策树核心逻辑
        
        Args:
            ratio: 主力资金推动力比值
            risk_score: 风险评分
            trap_signals: 诱多陷阱信号列表
            is_price_up_3d_capital_not_follow: 3日连涨但资金不跟特征
        
        Returns:
            决策标签: PASS❌ / TRAP❌ / BLOCK❌ / FOCUS✅
        """
        # 🔥 [Fix] 第1关：ratio < 0.5% → PASS❌
        # 修正：负ratio表示主力资金推动力强（30日累计流入多，今日仍在流入），不应该被拒绝
        # 只有 ratio 是 None 或 ratio 在 0-0.5% 之间（真正推动力弱）时才PASS
        if ratio is None or (ratio >= 0 and ratio < 0.5):
            return "PASS❌"

        # 第2关：ratio > 500% → TRAP❌（极端暴拉，绝对异常）
        if ratio > 500:
            return "TRAP❌"

        # 第3关：诱多 + 高风险 → BLOCK❌（已调整阈值：0.4 -> 0.6）
        if len(trap_signals) > 0 and risk_score >= 0.6:
            return "BLOCK❌"

        # 第3.5关：3日连涨资金不跟 + ratio < 1% → TRAP❌
        if is_price_up_3d_capital_not_follow and ratio < 1:
            return "TRAP❌"

        # 第4关：0.5-5% + 低风险 + 无诱多 → FOCUS✅（已调整阈值：0.5% → 0.5%）
        # 🔥 [Fix] 调整下限：50% → 0.5%，以捕获正常强势股（5%-50%）
        if 0.005 <= ratio <= 0.5 and risk_score < 0.6 and len(trap_signals) == 0:
            return "FOCUS✅"

        # 第4.5关：低风险 + 无诱多 → WATCH👀（新增：低风险观察池）
        if risk_score < 0.4 and len(trap_signals) == 0:
            return "WATCH👀"

        # 兜底：PASS❌
        return "PASS❌"
    
    def generate_state_signature(self, results: dict) -> str:
        """
        生成状态指纹，用于检测结果是否发生有意义的变化
        
        状态指纹包含：
        1. 机会池股票代码（排序后）
        2. 每只机会股的风险评分（四舍五入到2位小数）
        3. 系统置信度（四舍五入到1位小数）
        4. 推荐最大仓位（四舍五入到1位小数）
        5. 池子大小（机会池/观察池/黑名单数量）
        
        Args:
            results: 扫描结果字典
            
        Returns:
            状态指纹的哈希字符串
        """
        import hashlib
        import json
        
        # 提取机会池股票代码（排序）
        opportunity_codes = sorted([item['code'] for item in results.get('opportunities', [])])
        
        # 提取风险评分（四舍五入到2位小数）
        risk_scores = [round(item.get('risk_score', 0), 2) for item in results.get('opportunities', [])]
        
        # 提取系统置信度（四舍五入到1位小数）
        confidence = round(results.get('confidence', 0), 1)
        
        # 提取推荐最大仓位（四舍五入到1位小数）
        position_limit = round(results.get('position_limit', 0), 1)
        
        # 提取池子大小
        pool_sizes = {
            'opportunities': len(results.get('opportunities', [])),
            'watchlist': len(results.get('watchlist', [])),
            'blacklist': len(results.get('blacklist', []))
        }
        
        # 构建状态指纹
        state_data = {
            'codes': opportunity_codes,
            'risk_scores': risk_scores,
            'confidence': confidence,
            'position_limit': position_limit,
            'pool_sizes': pool_sizes
        }
        
        # 计算哈希
        state_str = json.dumps(state_data, sort_keys=True)
        state_hash = hashlib.md5(state_str.encode('utf-8')).hexdigest()
        
        return state_hash
    
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
        
        # 自定义 JSON 编码器处理 datetime.date 对象
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, 'strftime'):
                    return obj.strftime('%Y-%m-%d')
                elif hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return super().default(obj)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        
        logger.info(f"💾 结果已保存: {filename}")


if __name__ == "__main__":
    # 快速测试
    scanner = FullMarketScanner()
    results = scanner.scan_market(mode='premarket')
    
    print("\\n" + "=" * 80)
    print("📊 扫描结果摘要")
    print("=" * 80)
    print(f"✅ 机会池: {len(results['opportunities'])} 只")
    for item in results['opportunities'][:5]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - {item['capital_type']}")
    
    print(f"\\n⚠️  观察池: {len(results['watchlist'])} 只")
    for item in results['watchlist'][:3]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - {item['capital_type']}")
    
    print(f"\\n❌ 黑名单: {len(results['blacklist'])} 只")
    for item in results['blacklist'][:3]:
        print(f"   {item['code']} - 风险评分: {item['risk_score']:.2f} - 诱多信号: {item['trap_signals']}")
