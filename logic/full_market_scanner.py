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
        self.limiter = RateLimiter(max_calls=18, period=60)  # AkShare 限速
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
    
    def _level1_technical_filter(self) -> List[str]:
        """
        Level 1: 技术面粗筛
        
        从全市场 5000+ 只压缩到 300-500 只
        
        筛选条件：
        1. |涨跌幅| > 3%
        2. 成交额 > 3000万
        3. 换手率 > 2%
        4. 剔除 ST、退市、科创板
        
        Returns:
            候选股票代码列表
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
                logger.info(f"  批次 {batch_num}/{total_batches}: 获取 {len(batch)} 只股票 (命中: {len([c for c in batch if self._check_level1_criteria(c, tick_data.get(c, {}))])} 只)")
                
                # 本地过滤
                for code in batch:
                    tick = tick_data.get(code, {})
                    if tick and self._check_level1_criteria(code, tick):
                        candidates.append(code)
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
            
            # 获取价格数据
            last_close = tick.get('lastClose', 0)
            last_price = tick.get('lastPrice', 0)
            amount = tick.get('amount', 0)
            turnover = tick.get('turnoverRate', 0)
            
            # 计算涨跌幅
            if last_close == 0:
                return False
            pct_chg = abs((last_price - last_close) / last_close * 100)
            
            cfg = self.config['level1']
            
            # 三个条件必须同时满足
            if pct_chg < cfg['pct_chg_min']:
                return False
            if amount < cfg['amount_min']:
                return False
            if turnover < cfg['turnover_min']:
                return False
            
            return True
            
        except Exception as e:
            return False
    
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
            
            # 限速
            with self.limiter:
                try:
                    # 转换为6位代码（AkShare格式）
                    code_6digit = self.converter.to_6digit(code)
                    
                    # 获取资金流向
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
            
            # 条件 1: 主力净流入必须为正
            main_inflow = flow_data.get('main_net_inflow', 0)
            if main_inflow <= 0:
                return False
            
            # 条件 2: 超大单占比
            super_ratio = flow_data.get('super_ratio', 0)
            if super_ratio < cfg['super_ratio_min']:
                return False
            
            return True
            
        except Exception:
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
                code_6digit = self.converter.to_6digit(code)
                
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
