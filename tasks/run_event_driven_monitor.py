#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动的实时监控器 (Event-Driven Realtime Monitor)

架构设计：
    1. 独立进程运行，不阻塞主策略循环
    2. 基于文件变更或定时器触发 Level 1 扫描
    3. 维护热点候选池 (Hot Candidates Pool)
    4. 实时更新 CLI 仪表盘

Author: MyQuantTool Team
Date: 2026-02-05
"""

# 添加项目根目录到 Python 路径
import os
import sys
from pathlib import Path

# 获取项目根目录（tasks 目录的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import queue
import logging

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich import box

from logic.strategies.full_market_scanner import FullMarketScanner
from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.data_providers import get_provider
from logic.scoring.opportunity_scorer import (
    OpportunityScorer, OpportunityFactors, 
    get_opportunity_scorer, select_best_opportunity
)

# 配置日志
logger = get_logger("EventDrivenMonitor")

class EventDrivenMonitor:
    """
    事件驱动的实时监控器
    
    核心功能：
    - 维护一个固定大小的候选池 (Candidate Pool)
    - 定期执行 Level 1 全市场扫描，更新候选池
    - 对候选池内的股票进行高频 Level 2/3 监控
    - 实时输出 CLI 仪表盘
    """
    
    def __init__(self, config_path: str = "config/market_scan_config.json"):
        """初始化监控器"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # 初始化扫描器
        self.scanner = FullMarketScanner(config_path)
        
        # 候选池状态
        self.candidates: Dict[str, dict] = {}  # code -> candidate_info
        self.candidates_lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'last_scan_time': None,
            'scan_count': 0,
            'opportunities_count': 0,
            'watchlist_count': 0,
            'blacklist_count': 0,
            'market_temperature': 50.0,  # 市场温度（0-100）
            'status': 'Initializing'
        }
        
        # 监控控制
        self.running = False
        self.scan_thread = None
        self.display_thread = None
        self.stop_event = threading.Event()
        
        # 消息队列（用于日志显示）
        self.log_queue = queue.Queue(maxsize=100)
        
        # 候选池参数
        pool_config = self.config.get('monitor', {}).get('candidate_pool', {})
        self.max_candidates = pool_config.get('max_size', 100)
        self.candidate_ttl = pool_config.get('ttl_minutes', 10) * 60
        
        # QMT 数据检查
        self.data_provider = get_provider('level1')
        
        # 🔥 [V11.0.1] 初始化交易守门人
        from logic.core.trade_gatekeeper import TradeGatekeeper
        self.gatekeeper = TradeGatekeeper(self.config)
        
        # 记录已处理的股票集合（防止重复添加）
        self.hot_candidates_set: Set[str] = set()
        
        logger.info(f"✅ 监控器初始化完成 (候选池容量: {self.max_candidates})")

    def _load_config(self, config_path: str) -> dict:
        """加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️  加载配置失败: {e}，使用默认配置")
            return {}

    def start(self):
        """启动监控器"""
        if self.running:
            logger.warning("⚠️  监控器已经在运行中")
            return
            
        self.running = True
        self.stop_event.clear()
        
        # 启动扫描线程
        self.scan_thread = threading.Thread(target=self._scan_loop, name="ScanThread", daemon=True)
        self.scan_thread.start()
        
        # 启动显示线程（主线程运行）
        try:
            self._display_loop()
        except KeyboardInterrupt:
            logger.info("🛑 用户中断，正在停止监控器...")
            self.stop()

    def stop(self):
        """停止监控器"""
        self.running = False
        self.stop_event.set()
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5.0)
        logger.info("✅ 监控器已停止")

    def _scan_loop(self):
        """扫描循环（后台线程）"""
        logger.info("🚀 扫描线程已启动")
        
        while not self.stop_event.is_set():
            try:
                # 1. 执行全市场扫描（Level 1）
                self.stats['status'] = 'Scanning Level 1...'
                start_time = time.time()
                
                # 获取全市场候选
                candidates_l1 = self.scanner.run_level1_screening()
                
                # 更新候选池
                self._update_candidates_from_market_scan(candidates_l1)
                
                # 2. 对候选池进行深入分析（Level 2 & 3）
                self.stats['status'] = 'Analyzing Candidates...'
                self._analyze_candidates()
                
                # 更新统计
                self.stats['last_scan_time'] = datetime.now()
                self.stats['scan_count'] += 1
                self.stats['scan_duration'] = time.time() - start_time
                self.stats['status'] = 'Idle'
                
                # 导出状态（用于 CLI 工具或其他消费者）
                self._export_state()
                
                # 休眠（避免过度消耗资源）
                # 动态调整休眠时间：盘中短休眠，盘后长休眠
                sleep_time = self._calculate_sleep_time()
                self.stop_event.wait(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ 扫描循环异常: {e}")
                self.log_queue.put(f"❌ [Error] {str(e)}")
                self.stop_event.wait(10.0)  # 出错后暂停 10 秒

    def _calculate_sleep_time(self) -> float:
        """计算休眠时间"""
        now = datetime.now().time()
        # 交易时间：9:30-11:30, 13:00-15:00
        is_trading_hours = (
            (now >= datetime.strptime("09:30", "%H:%M").time() and now <= datetime.strptime("11:30", "%H:%M").time()) or
            (now >= datetime.strptime("13:00", "%H:%M").time() and now <= datetime.strptime("15:00", "%H:%M").time())
        )
        
        if is_trading_hours:
            return 30.0  # 盘中 30 秒一轮（Level 1 比较重）
        else:
            return 60.0  # 盘后 60 秒一轮

    def _update_candidates_from_market_scan(self, candidates_l1: List[dict]):
        """从全市场扫描结果更新候选池"""
        current_time = time.time()
        
        # 转换格式：List[dict] -> Dict
        new_candidates = {}
        for c in candidates_l1:
            code = c['code']
            # 计算优先级分数（基于涨幅、量比、成交额）
            priority_score = self._calculate_priority_score(c)
            c['priority_score'] = priority_score
            c['added_time'] = current_time
            c['last_update'] = current_time
            new_candidates[code] = c
            
        # 维护候选池
        with self.candidates_lock:
            # 1. 移除过期候选
            expired = [
                code for code, info in self.candidates.items() 
                if current_time - info['added_time'] > self.candidate_ttl and code not in new_candidates
            ]
            for code in expired:
                del self.candidates[code]
                if code in self.hot_candidates_set:
                    self.hot_candidates_set.remove(code)
            
            # 2. 添加新候选 / 更新现有候选
            # 🔥 [修复] 聚合日志，避免刷屏
            dropped_count = 0
            
            for code, info in new_candidates.items():
                # 尝试添加，如果因满池失败则不打印日志 (suppress_log=True)
                if not self._add_candidate(code, info, suppress_log=True):
                    # 如果不在现有集合中（即是新来的且被拒绝），增加计数
                    if code not in self.hot_candidates_set:
                        dropped_count += 1
            
            # 统一汇报被拒绝的数量
            if dropped_count > 0:
                logger.warning(f"⚠️ 候选池已满，已忽略 {dropped_count} 只低优先级候选股票（日志已聚合）")
            
            # 更新日志
            if len(new_candidates) > 0:
                self.log_queue.put(f"🔍 Level 1 扫描完成: 发现 {len(new_candidates)} 只异动股, 候选池: {len(self.candidates)}/{self.max_candidates}")

    def _calculate_priority_score(self, candidate: dict) -> float:
        """
        计算候选优先级分数
        
        分数越高，优先级越高。用于候选池满时决定淘汰谁。
        
        权重：
        - 涨跌幅: 40% (越接近涨停越高，但也考虑跌停撬板)
        - 量比: 30% (放量优先)
        - 成交额: 30% (大额优先)
        """
        try:
            pct_chg = abs(candidate.get('pct_chg', 0))
            # 归一化涨跌幅 (0-20%) -> 0-100
            score_pct = min(pct_chg * 5, 100)
            
            # 量比 (0-10) -> 0-100
            # 注意：volume_ratio 可能是字符串 "数据缺失"
            vr_str = candidate.get('volume_ratio_str', '0')
            try:
                vr = float(vr_str)
            except ValueError:
                vr = 0
            score_vr = min(vr * 10, 100)
            
            # 成交额 (3000万 - 10亿) -> 0-100
            amount = candidate.get('amount', 0)
            score_amount = min(max((amount - 30000000) / 10000000, 0), 100)
            
            # 综合评分
            total_score = score_pct * 0.4 + score_vr * 0.3 + score_amount * 0.3
            return total_score
            
        except Exception:
            return 0.0

    def _add_candidate(self, code: str, info: dict, suppress_log: bool = False) -> bool:
        """
        向候选池添加股票
        
        如果池已满，且新股票优先级高于池中最低优先级的股票，则替换。
        
        Args:
            code: 股票代码
            info: 候选信息
            suppress_log: 是否抑制日志输出（防止刷屏）
            
        Returns:
            bool: 是否成功添加/更新
        """
        # 如果已存在，直接更新
        if code in self.candidates:
            self.candidates[code].update(info)
            return True
            
        # 如果未满，直接添加
        if len(self.candidates) < self.max_candidates:
            self.candidates[code] = info
            self.hot_candidates_set.add(code)
            return True
            
        # 池已满，尝试替换最低优先级的
        min_code = min(self.candidates, key=lambda k: self.candidates[k].get('priority_score', 0))
        min_score = self.candidates[min_code].get('priority_score', 0)
        new_score = info.get('priority_score', 0)
        
        if new_score > min_score:
            # 替换
            del self.candidates[min_code]
            if min_code in self.hot_candidates_set:
                self.hot_candidates_set.remove(min_code)
            
            self.candidates[code] = info
            self.hot_candidates_set.add(code)
            if not suppress_log:
                logger.info(f"🔄 候选池置换: {code}({new_score:.1f}) 替换 {min_code}({min_score:.1f})")
            return True
        else:
            # 优先级不足，无法进入
            if not suppress_log:
                logger.warning(f"⚠️ 候选池满且优先级不足: {code}({new_score:.1f}) < {min_code}({min_score:.1f})")
            return False

    def _analyze_candidates(self):
        """分析候选池中的股票（Level 2 & 3）"""
        with self.candidates_lock:
            current_candidates = list(self.candidates.values())
            
        if not current_candidates:
            return

        # 1. Level 2: 资金流向分析
        # 注意：这里我们只对候选池中的股票做资金分析，大大减少了请求量
        candidates_l2 = self.scanner._level2_capital_analysis(current_candidates)
        
        # 2. Level 3: 诱多检测与分类
        results = self.scanner._level3_trap_classification(candidates_l2)
        
        # 更新统计
        self.stats['opportunities_count'] = len(results['opportunities'])
        self.stats['watchlist_count'] = len(results['watchlist'])
        self.stats['blacklist_count'] = len(results['blacklist'])
        
        # 将最新的分析结果合并回候选池
        with self.candidates_lock:
            for cat in ['opportunities', 'watchlist', 'blacklist']:
                for item in results[cat]:
                    code = item['code']
                    if code in self.candidates:
                        # 更新分析结果
                        self.candidates[code].update(item)
                        # 标记分类
                        self.candidates[code]['category'] = cat
        
        # 输出日志
        if results['opportunities']:
            self.log_queue.put(f"✨ 发现 {len(results['opportunities'])} 个机会: {', '.join([c['code'] for c in results['opportunities'][:3]])}...")
            
        # 🔥 [V11.0.1] 调用 Gatekeeper 进行最终过滤和自动交易（如果开启）
        self._process_trading_signals(results)

    def _process_trading_signals(self, results: dict):
        """处理交易信号"""
        # 1. 使用 Gatekeeper 过滤机会池
        opportunities_final, opportunities_blocked, timing_downgraded = self.gatekeeper.filter_opportunities(
            results['opportunities'],
            results
        )
        
        # 2. 更新统计
        self.stats['opportunities_count'] = len(opportunities_final)
        
        # 3. (未来扩展) 自动下单逻辑
        # if self.config.get('auto_trade', False):
        #     for opp in opportunities_final:
        #         self.trader.buy(...)

    def _export_state(self):
        """导出状态到文件（供 CLI 读取）"""
        state = {
            'updated_at': datetime.now().isoformat(),
            'stats': self.stats,
            'log_tail': list(self.log_queue.queue)[-10:], # 最近10条日志
            'top_opportunities': [],
            'daily_pick': {  # V17新增：每日首选和备选
                'primary': None,
                'alternatives': [],
                'disclaimer': '系统建议，仅供参考，不自动下单，最终决策由人工拍板'
            }
        }
        
        # 提取机会并进行评分
        with self.candidates_lock:
            opps = [c for c in self.candidates.values() if c.get('category') == 'opportunities']
            
            # 使用机会评分器
            opportunities_for_scoring = []
            for opp in opps:
                factors = OpportunityFactors(
                    pattern_type=opp.get('pattern_type', 'halfway'),
                    pattern_quality=opp.get('pattern_quality', 0.5),
                    platform_volatility=opp.get('platform_volatility', 0.03),
                    breakout_strength=opp.get('breakout_strength', 0.01),
                    volume_surge=opp.get('volume_ratio', 1.0),
                    capital_inflow=opp.get('main_inflow', 0),
                    capital_strength=opp.get('capital_strength', 0.5),
                    capital_sustained=opp.get('capital_sustained', False),
                    is_trap=opp.get('is_trap', False),
                    sector_risk=opp.get('sector_risk', 0),
                    market_sentiment=self.stats.get('market_temperature', 50) / 100
                )
                opportunities_for_scoring.append((opp['code'], factors))
            
            # 评分并选择首选/备选
            if opportunities_for_scoring:
                scorer = get_opportunity_scorer()
                daily_pick = scorer.select_daily_pick(opportunities_for_scoring)
                
                # V17修复：将score写回opp对象
                all_scored = daily_pick.get('all_scored', [])
                for scored_item in all_scored:
                    code = scored_item['stock_code']
                    # 找到对应的opp并写入score
                    for opp in opps:
                        if opp['code'] == code:
                            opp['score'] = scored_item['score']
                            opp['score_details'] = scored_item.get('details', {})
                            break
                
                # 记录首选
                if daily_pick['primary']:
                    state['daily_pick']['primary'] = daily_pick['primary']
                    logger.info(f"⭐ [系统首选] {daily_pick['primary']['stock_code']} "
                              f"评分:{daily_pick['primary']['score']:.2f} "
                              f"{'[可交易]' if daily_pick['primary']['passed'] else '[不及格]'}")
                
                # 记录备选
                for alt in daily_pick['alternatives']:
                    state['daily_pick']['alternatives'].append(alt)
                    logger.info(f"  [备选] {alt['stock_code']} 评分:{alt['score']:.2f}")
            
            # 按评分排序后提取Top机会
            opps.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # 转换为 JSON 可序列化格式
            for opp in opps[:5]:
                state['top_opportunities'].append({
                    'code': opp['code'],
                    'name': opp.get('name', 'N/A'),
                    'price': opp.get('last_price', 0),
                    'pct': opp.get('pct_chg', 0),
                    'score': opp.get('score', 0),  # V17新增：机会评分
                    'risk': opp.get('risk_score', 0),
                    'tag': opp.get('decision_tag', 'N/A'),
                    'capital_inflow': opp.get('main_inflow', 0)  # V17新增：资金流入
                })
        
        # V17明确声明：不自动下单
        state['auto_trade'] = False
        state['trade_mode'] = 'OBSERVE_ONLY'  # 观察模式，人工决策
        
        # 写入文件（原子操作）
        temp_file = "data/monitor_state.tmp"
        final_file = "data/monitor_state.json"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, final_file)
        except Exception as e:
            logger.error(f"导出状态失败: {e}")

    def _display_loop(self):
        """显示循环（主线程，使用 Rich）"""
        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=10)
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        with Live(layout, refresh_per_second=4, screen=True) as live:
            while self.running:
                # 更新 Header
                layout["header"].update(self._render_header())
                
                # 更新 Body
                layout["left"].update(self._render_candidates_table())
                layout["right"].update(self._render_opportunities_panel())
                
                # 更新 Footer (日志)
                layout["footer"].update(self._render_logs())
                
                time.sleep(0.25)

    def _render_header(self) -> Panel:
        """渲染头部"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        status_style = "green" if self.stats['status'] == 'Idle' else "yellow"
        grid.add_row(
            f"[bold cyan]MyQuantTool 实时监控器[/bold cyan] | Status: [{status_style}]{self.stats['status']}[/]",
            f"扫描次数: {self.stats['scan_count']} | 上次扫描: {self.stats.get('last_scan_time', 'N/A')}"
        )
        
        return Panel(grid, style="white on blue")

    def _render_candidates_table(self) -> Panel:
        """渲染候选池表格"""
        table = Table(expand=True, box=box.SIMPLE)
        table.add_column("代码", style="cyan")
        table.add_column("名称")
        table.add_column("涨幅", justify="right")
        table.add_column("量比", justify="right")
        table.add_column("优先级", justify="right")
        
        with self.candidates_lock:
            # 按优先级排序，取前 15 个
            sorted_candidates = sorted(
                self.candidates.values(), 
                key=lambda x: x.get('priority_score', 0), 
                reverse=True
            )[:15]
            
            for c in sorted_candidates:
                pct = c.get('pct_chg', 0)
                pct_style = "red" if pct > 0 else "green"
                table.add_row(
                    c['code'],
                    c.get('name', 'N/A'),
                    f"[{pct_style}]{pct:.2f}%[/]",
                    c.get('volume_ratio_str', 'N/A'),
                    f"{c.get('priority_score', 0):.1f}"
                )
                
        return Panel(table, title=f"🔥 热门候选池 (TOP 15 / {len(self.candidates)})", border_style="blue")

    def _render_opportunities_panel(self) -> Panel:
        """渲染机会面板"""
        table = Table(expand=True, box=box.SIMPLE)
        table.add_column("代码", style="bold green")
        table.add_column("名称")
        table.add_column("风险分", justify="right")
        table.add_column("决策", justify="center")
        table.add_column("原因")
        
        with self.candidates_lock:
            opps = [c for c in self.candidates.values() if c.get('category') == 'opportunities']
            opps.sort(key=lambda x: x.get('risk_score', 1.0))
            
            for opp in opps[:10]:
                risk = opp.get('risk_score', 0)
                risk_style = "green" if risk < 0.3 else "yellow"
                table.add_row(
                    opp['code'],
                    opp.get('name', 'N/A'),
                    f"[{risk_style}]{risk:.2f}[/]",
                    opp.get('decision_tag', 'N/A'),
                    opp.get('scenario_reasons', [''])[0] if opp.get('scenario_reasons') else ''
                )
                
        return Panel(table, title=f"✨ 机会池 ({len(opps)})", border_style="green")

    def _render_logs(self) -> Panel:
        """渲染日志"""
        log_text = Text()
        # 获取最近 8 条日志
        logs = list(self.log_queue.queue)[-8:]
        for log in logs:
            if "❌" in log:
                style = "bold red"
            elif "⚠️" in log:
                style = "yellow"
            elif "✨" in log:
                style = "bold green"
            else:
                style = "white"
            log_text.append(log + "\n", style=style)
            
        return Panel(log_text, title="📜 运行日志", border_style="grey50")

if __name__ == "__main__":
    monitor = EventDrivenMonitor()
    monitor.start()
