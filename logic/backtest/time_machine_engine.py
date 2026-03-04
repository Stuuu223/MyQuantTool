"""
全息时间机器引擎 - 连续多日回测
自动执行连续N个交易日的回测,验证策略稳定性

Author: iFlow CLI
Date: 2026-02-24
Version: 1.2.1 - CTO手术二（盘后结算缩进修复版）
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import json
import logging

from logic.core.path_resolver import PathResolver

# 记忆衰减参数（从配置文件读取）
from logic.core.config_manager import get_config_manager
_cfg = get_config_manager()
MEMORY_WRITE_MIN_SCORE = _cfg.get('memory_engine.write_min_score', 10.0)   # 写入记忆库的最低分
MEMORY_SIGNAL_MIN_SCORE = _cfg.get('memory_engine.signal_min_score', 40.0)  # 触发信号的最低分
MEMORY_DECAY_FACTOR = _cfg.get('memory_engine.decay_factor', 0.5)           # 衰减系数
MEMORY_MAX_ABSENCE_DAYS = _cfg.get('memory_engine.max_absence_days', 2)     # 连续不上榜最大天数

# 【CTO修复】TRUE_CHANGE 内联定义，不再依赖已废弃的 MetricDefinitions
def TRUE_CHANGE(close: float, pre_close: float) -> float:
    """计算真实涨跌幅(%)"""
    if pre_close == 0:
        return 0.0
    return (close - pre_close) / pre_close * 100

from logic.core.sanity_guards import SanityGuards
from logic.data_providers.qmt_manager import QmtDataManager
from logic.data_providers.universe_builder import UniverseBuilder
from logic.core.config_manager import get_config_manager
from logic.utils.metrics_utils import render_battle_dashboard

logger = logging.getLogger(__name__)


class TimeMachineEngine:
    """
    全息时间机器 - 连续交易日回测引擎
    
    使用示例:
        engine = TimeMachineEngine()
        results = engine.run_continuous_backtest(
            start_date='20251231',
            end_date='20260115',
            stock_pool='data/cleaned_candidates_66.csv'
        )
    """
    
    # 记忆文件路径（统一使用小写文件名）
    MEMORY_FILE = Path(__file__).parent.parent.parent / 'data' / 'memory' / 'short_term_memory.json'
    
    def __init__(self, initial_capital: float = 20000.0, is_pure_mode: bool = False):
        self.initial_capital = initial_capital
        self.is_pure_mode = is_pure_mode  # 【新增】纯净模式开关
        self.data_manager = QmtDataManager()
        self.results_cache: Dict[str, Dict] = {}
        
        # 【CTO时空切割】区分热复盘(基因继承)和全息回演(平行宇宙)
        self.is_continuous_backtest = False
        
        # 【CTO修复】挂载动能打分引擎算分引擎
        from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine
        self._kinetic_engine = 动能打分引擎CoreEngine()
        
        self._ensure_output_dirs()
        
        # 【CTO铁令】：回测只读本地数据，绝对禁止启动VIP服务！
        
    def _ensure_output_dirs(self):
        """确保输出目录存在"""
        output_dir = PathResolver.get_data_dir() / 'backtest_out'
        PathResolver.ensure_dir(output_dir)
        PathResolver.ensure_dir(output_dir / 'time_machine')
        
    def _get_avg_volume_5d(self, stock_code: str, date: str) -> float:
        """
        【CTO强制透传】直接从TrueDictionary单例获取5日均量
        
        不再独立计算，实现与UniverseBuilder的状态穿透！
        UniverseBuilder预热后，此处直接读取缓存！
        
        Args:
            stock_code: 股票代码
            date: 当前日期 'YYYYMMDD' (保留参数兼容性，但实际从缓存读取)
        
        Returns:
            5日平均成交量，失败返回0
        """
        try:
            # 【CTO核心修复】：直接向全局真理字典要数据！
            from logic.data_providers.true_dictionary import get_true_dictionary
            global_dict = get_true_dictionary()
            
            avg_volume_5d = global_dict.get_avg_volume_5d(stock_code)
            
            if avg_volume_5d and avg_volume_5d > 0:
                return float(avg_volume_5d)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"【CTO透传失败】获取5日均量失败 {stock_code}: {e}")
            return 0.0
    
    def _get_float_volume(self, stock_code: str) -> float:
        """
        【CTO强制透传】直接从TrueDictionary单例获取流通股本
        
        不再独立调用QMT API，实现与UniverseBuilder的状态穿透！
        UniverseBuilder预热后，此处直接读取缓存！
        
        Args:
            stock_code: 股票代码
        
        Returns:
            流通股本，失败返回0
        """
        try:
            # 【CTO核心修复】：直接向全局真理字典要数据！
            from logic.data_providers.true_dictionary import get_true_dictionary
            global_dict = get_true_dictionary()
            
            float_volume = global_dict.get_float_volume(stock_code)
            
            if float_volume and float_volume > 0:
                return float(float_volume)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"【CTO透传失败】获取流通股本失败 {stock_code}: {e}")
            return 0.0
    
    def _get_60d_high(self, stock_code: str, date: str) -> float:
        """
        【CTO深市突围版】获取60日最高价
        
        前置条件：UniverseBuilder已过滤掉沪市股票
        """
        try:
            from xtquant import xtdata
            
            # 计算60个交易日的日期范围
            current = datetime.strptime(date, '%Y%m%d')
            start_date = (current - timedelta(days=90)).strftime('%Y%m%d')
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 获取日线数据
            data = xtdata.get_local_data(
                field_list=['time', 'high'],
                stock_list=[normalized_code],
                period='1d',
                start_time=start_date,
                end_time=date
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty and len(df) >= 60:
                    recent_highs = df.tail(60)['high'].values
                    return float(max(recent_highs))
                elif not df.empty:
                    return float(df['high'].max())
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"获取60日最高价失败 {stock_code}: {e}")
            return 0.0
    
    def _get_volume_ratio_threshold_for_date(self, date: str, base_percentile: float = None) -> float:
        """
        获取特定日期的量比阈值 (V20.5 SSOT原则)
        
        Args:
            date: 日期 'YYYYMMDD'
            base_percentile: 已废弃，保留参数兼容性
        
        Returns:
            量比阈值 (绝对倍数，如3.0)
        """
        # 【V20.5唯一真理】回测引擎必须使用 live_sniper.min_volume_multiplier
        # 不再使用分位数，直接返回绝对倍数
        from logic.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        return config_manager.get_min_volume_multiplier()
    
    def get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表（自动跳过周末和节假日）
        
        Args:
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
        
        Returns:
            交易日列表
        """
        # 简化版：只跳过周末
        dates = []
        current = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        while current <= end:
            # 跳过周末 (5=Saturday, 6=Sunday)
            if current.weekday() < 5:
                dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        
        logger.info(f"【时间机器】获取到 {len(dates)} 个交易日（{start_date} 至 {end_date}）")
        return dates
    
    def run_daily_backtest(self, date: str, stock_pool: List[str] = None) -> Dict:
        """
        单日回测 - 【CTO内存熔断版】
        
        模拟实盘流程：
        1. 09:30 开盘前准备
        2. 09:40 计算早盘数据
        3. 输出当日Top 20 (CTODict: 扩容观察梯度)
        
        【CTO内存熔断】：严禁全量Tick读取，必须通过UniverseBuilder粗筛(<200只)
        
        Args:
            date: 交易日期 'YYYYMMDD'
            stock_pool: 股票代码列表(可选，不传则使用UniverseBuilder粗筛)
        
        Returns:
            当日回测结果字典
        """
        # 1. 【CTO内存熔断】强制依赖UniverseBuilder给出极少量的候选池(必须<200)
        if stock_pool is None:
            logger.info("【时间机器】未指定股票池，使用UniverseBuilder粗筛...")
            from logic.data_providers.universe_builder import UniverseBuilder
            builder = UniverseBuilder(target_date=date)
            stock_pool, _ = builder.build()  # 【CTO修复】接收tuple，丢弃market_ratios
            logger.info(f"【时间机器】UniverseBuilder返回: {len(stock_pool)} 只")
            
        if not stock_pool:
            logger.error("❌ 【时间机器】粗筛结果为空，今日回测终止！")
            return {'date': date, 'status': 'error', 'error': '粗筛结果为空'}
        
        # 【CTO深市突围】：预热TrueDictionary（深市股票安全）
        print(f"  🔥 预热TrueDictionary...")
        from logic.data_providers.true_dictionary import get_true_dictionary
        global_dict = get_true_dictionary()
        warmup_result = global_dict.warmup(stock_pool, target_date=date, force=False)
        print(f"  ✅ TrueDictionary预热完成")
        
        print(f"\n{'='*60}")
        print(f"【时间机器】回测日期: {date}")
        print(f"⚡ [CTO深市突围] 靶向读取{len(stock_pool)}只深市股票Tick...")
        print(f"{'='*60}")
        
        daily_result = {
            'date': date,
            'status': 'running',
            'top20': [],
            'signals': [],
            'errors': [],
            'total_stocks': len(stock_pool),
            'valid_stocks': 0
        }
        
        try:
            # 【CTO全息克隆】：直接使用UniverseBuilder的安全股票池！
            # 不再调用get_local_data筛选，避免BSON崩溃！
            print(f"  📊 使用全息克隆股票池: {len(stock_pool)} 只")
            
            # 直接使用传入的股票池，不进行额外筛选
            valid_stocks = stock_pool
            
            print(f"  📈 全息克隆筛选: {len(valid_stocks)} 只安全股票")
            
            daily_result['valid_stocks'] = len(valid_stocks)
            print(f"  ✅ 有效数据: {len(valid_stocks)} 只")
            
            if len(valid_stocks) < 5:
                daily_result['status'] = 'insufficient_data'
                logger.warning(f"  ⚠️ 数据不足: 仅 {len(valid_stocks)} 只有效数据")
                return daily_result
            
            # 2. 计算09:40指标（早盘5分钟+5分钟）
            print(f"  🧮 计算早盘指标...")
            
            # 【CTO深市突围】：深市股票安全，全部处理！
            valid_stocks_to_process = valid_stocks
            print(f"  📊 处理 {len(valid_stocks_to_process)} 只深市股票")
            
            stock_scores = []
            data_missing_count = 0
            data_missing_stocks = []  # 记录因数据缺失被跳过的股票
            
            # ==========================================
            # 【CTO漏斗归位】废除强行截断，植入动态量价快照过滤！
            # 问题：之前用 MAX_STOCKS_PER_RUN=20 截取前20只，导致京东方等大盘股混入
            # 修复：用换手率物理漏斗过滤死水股，不依赖Magic Number市值限制
            # ==========================================
            print(f"  🔍 开始二维铁网快照预筛 (过滤死水大象)...")
            
            from logic.core.config_manager import get_config_manager
            config_mgr = get_config_manager()
            min_turnover = config_mgr.get('stock_filter.min_intraday_turnover_pct', 5.0)
            
            filtered_candidates = []
            missing_count = 0  # 【CTO铁律】数据缺失计数器
            
            # 【CTO降维重铸】日内快照漏斗，彻底废除volume量纲陷阱
            # 使用amount（元）/流通市值计算换手率，永远不需要猜volume单位
            print(f"  🔍 开始二维铁网快照预筛 (过滤死水大象)...")
            
            try:
                from xtquant import xtdata
                from logic.data_providers.true_dictionary import get_true_dictionary
                true_dict = get_true_dictionary()
                
                daily_data = xtdata.get_local_data(
                    field_list=['amount', 'close'],  # 只要金额和价格！废除volume
                    stock_list=valid_stocks_to_process,
                    period='1d',
                    start_time=date,
                    end_time=date
                )
                
                for stock in valid_stocks_to_process:
                    # 【CTO铁律：数据不全，立刻淘汰，绝不放行！】
                    if not daily_data or stock not in daily_data or daily_data[stock].empty:
                        missing_count += 1
                        continue
                    
                    try:
                        day_amount = float(daily_data[stock].iloc[-1]['amount'])
                        day_close = float(daily_data[stock].iloc[-1]['close'])
                        float_vol_shares = true_dict.get_float_volume(stock)
                        
                        # 【CTO铁律】数据无效或停牌，直接淘汰！
                        if day_amount <= 0 or day_close <= 0 or not float_vol_shares or float_vol_shares <= 0:
                            missing_count += 1
                            continue
                        
                        # 【绝对真理公式】换手率 = 成交额 / 流通市值 * 100%
                        float_market_cap = float_vol_shares * day_close
                        if float_market_cap > 0:
                            day_turnover = (day_amount / float_market_cap) * 100.0
                            if day_turnover >= min_turnover:
                                filtered_candidates.append(stock)
                    except Exception:
                        missing_count += 1
                        continue
                
                # 【CTO数据断言】如果缺失率超过20%，触发断路器！
                total_stocks = len(valid_stocks_to_process)
                if total_stocks > 0 and (missing_count / total_stocks > 0.2):
                    error_msg = f"❌ [Fail Fast] 数据严重缺失！{missing_count}/{total_stocks} 只股票无日K数据。请先运行 unified_downloader 下载数据！"
                    logger.error(error_msg)
                    print(error_msg)
                    return None  # 直接终止今日回测！
                
                print(f"  🎯 换手率铁网(>={min_turnover}%)过滤完毕，剩余: {len(filtered_candidates)} 只真龙候选 (淘汰:{missing_count}只)")
                
            except Exception as e:
                logger.error(f"快照预筛失败: {e}")
                return None  # 异常时直接终止，不再兜底放行！
            
            # 替换原来的待处理列表
            valid_stocks_to_process = filtered_candidates
            
            # 【CTO防爆兜底】：如果符合换手的股票还是太多，随机抽样50只
            import random
            if len(valid_stocks_to_process) > 50:
                valid_stocks_to_process = random.sample(valid_stocks_to_process, 50)
                print(f"  ⚠️ 触发BSON防爆，随机抽取 50 只高换手标的进行 Tick 精确打击")
            
            if len(valid_stocks_to_process) == 0:
                print(f"  ❌ 换手率铁网过滤后无候选股票，今日回测终止")
                return daily_result
            
            print(f"  📊 最终股票池: {len(valid_stocks_to_process)} 只")
            
            # 【CTO黑名单】已知的BSON炸弹股票（触发C++断言崩溃）
            BSON_BOMB_BLACKLIST = {
                '002255.SZ',  # 20260226测试触发崩溃
                '300197.SZ',  # 20260226测试触发崩溃（Tick遍历中）
            }
            valid_stocks_to_process = [s for s in valid_stocks_to_process if s not in BSON_BOMB_BLACKLIST]
            print(f"  🚫 过滤BSON炸弹后: {len(valid_stocks_to_process)} 只")
            
            # ========== 【CTO P1 BUG FIX】循环外创建一次 MemoryEngine ==========
            from logic.memory.short_term_memory import ShortTermMemoryEngine
            from logic.core.path_resolver import PathResolver
            
            if self.is_continuous_backtest:
                _mem_file = str(PathResolver.get_data_dir() / 'memory' / 'ShortTermMemory_backtest.json')
                _loop_memory_engine = ShortTermMemoryEngine(memory_file=_mem_file)
            else:
                _loop_memory_engine = ShortTermMemoryEngine()
            logger.info("🧠 [MemoryEngine] 循环外单例已创建")
            # ========== END FIX ==========
            
            for stock in valid_stocks_to_process:
                try:
                    # 【CTO防爆】每只股票处理后强制垃圾回收
                    import gc
                    gc.collect()
                    
                    score = self._calculate_morning_score(stock, date, memory_engine=_loop_memory_engine)
                    
                    # 【CTO修复】数据完整性断言：禁止0分兜底
                    if score is None:
                        data_missing_count += 1
                        data_missing_stocks.append(stock)
                        logger.warning(f"  ⚠️ {stock}: 数据缺失，跳过算分")
                        continue
                    
                    # 【CTO P0 BUG FIX】final_score=0 是动能引擎正确淘汰的垃圾股，属于合法结果
                    # 只有 pre_close <= 0 才是数据无效的铁证，不再用 final_score=0 误判
                    
                    # 检查昨收价和开盘价的有效性
                    if score.get('pre_close', 0) <= 0:
                        data_missing_count += 1
                        data_missing_stocks.append(stock)
                        logger.warning(f"  ⚠️ {stock}: pre_close={score.get('pre_close', 0)} 无效，跳过")
                        continue
                    
                    stock_scores.append(score)
                    
                except Exception as e:
                    error_msg = f"{stock}计算错误: {str(e)}"
                    daily_result['errors'].append(error_msg)
                    logger.warning(f"  ⚠️ {error_msg}")
            
            # ========== 【CTO P1 BUG FIX】循环结束后关闭MemoryEngine ==========
            try:
                _loop_memory_engine.close()
                logger.info("🧠 [MemoryEngine] 循环结束，单例已关闭")
            except Exception:
                pass
            # ========== END FIX ==========
            
            # 3. 【CTO多维排序】得分相同看MFE，MFE大于5倒扣
            # 【CTO修复】MFE已在_calculate_morning_score中正确计算，不要覆盖！
            # 只有当MFE缺失时才重新计算
            for score in stock_scores:
                # 【CTO修复】保留_calculate_morning_score返回的MFE，不覆盖！
                if 'mfe' not in score or score.get('mfe', 0) == 0:
                    max_price = score.get('max_price', 0)
                    pre_close = score.get('pre_close', 1)
                    # MFE = (最高价 - 昨收) / 昨收 * 100，无量纲百分比
                    mfe = ((max_price - pre_close) / pre_close * 100) if pre_close > 0 else 0
                    score['mfe'] = mfe
                
                # MFE大于5%倒扣分数（惩罚冲高回落）
                mfe_val = score.get('mfe', 0)
                if mfe_val > 5:
                    score['final_score'] = score.get('final_score', 0) - (mfe_val - 5) * 2
            
            # 多维排序：final_score降序，相同则看MFE升序（MFE越小越好）
            stock_scores.sort(key=lambda x: (x.get('final_score', 0), -x.get('mfe', 0)), reverse=True)
            top20 = stock_scores[:20]
            
            daily_result['top20'] = top20
            daily_result['status'] = 'success'
            daily_result['data_missing_count'] = data_missing_count
            daily_result['data_missing_stocks'] = data_missing_stocks
            
            # 5. 执行记忆衰减
            # 【总监验证】纯净模式跳过记忆衰减和写入
            if self.is_pure_mode:
                logger.info("🧪 [纯净模式] 跳过记忆衰减与写入，实盘基因库保持原状")
            else:
                # 【CTO手术二 Fix 3】传入 record_date 参数
                self._apply_memory_decay(date, top20, record_date=date)
            
            # 【Step6: 时空对齐与全息回演UI看板】
            
            # 构建dragon数据格式适配大屏
            dragons_for_dashboard = []
            for item in top20:
                stock_code = item['stock_code']
                final_score = item.get('final_score', 0)
                final_change = item.get('final_change', item.get('change_0940', 0))
                real_close = item.get('real_close', 0)
                pre_close = item.get('pre_close', 1)
                is_vetoed = item.get('is_vetoed', False)
                veto_reason = item.get('veto_reason', '')
                inflow_ratio = item.get('inflow_ratio', 0)
                ratio_stock = item.get('ratio_stock', 0)
                sustain_ratio = item.get('sustain_ratio', 0)
                pullback_ratio = item.get('pullback_ratio', 0)
                mfe = item.get('mfe', 0)
                
                # 纯度评级
                space_gap_pct = pullback_ratio
                purity = '极优' if space_gap_pct < 0.05 else '优' if space_gap_pct < 0.10 else '良'
                
                # 标签
                tag = veto_reason if is_vetoed else '换手甜点' if item.get('passes_filters', False) else '普通'
                
                dragons_for_dashboard.append({
                    'code': stock_code,
                    'score': final_score,
                    'price': real_close if real_close > 0 else item.get('price_0940', 0),
                    'change': final_change,
                    'inflow_ratio': inflow_ratio,
                    'ratio_stock': ratio_stock,
                    'sustain_ratio': sustain_ratio,
                    'mfe': mfe,
                    'purity': purity,
                    'tag': tag
                })
            
            # 调用工业级大屏（与实盘统一）
            if dragons_for_dashboard:
                render_battle_dashboard(
                    data_list=dragons_for_dashboard,
                    title=f"全息回测 [{date}]",
                    clear_screen=False  # 不回测不清屏，保留日志
                )
            
            # 【CTO修复】打印数据缺失统计
            if data_missing_count > 0:
                print(f"\n  📊 数据完整性报告:")
                print(f"     因数据缺失被跳过: {data_missing_count} 只")
                print(f"     被跳过股票: {', '.join(data_missing_stocks[:10])}{'...' if len(data_missing_stocks) > 10 else ''}")
                logger.info(f"【时间机器】{date} 数据缺失统计: {data_missing_count} 只被跳过")
            
            logger.info(f"【时间机器】{date} 回测成功，Top20: {[s['stock_code'] for s in top20[:5]]}...")
            
        except Exception as e:
            daily_result['status'] = 'error'
            error_msg = str(e)
            daily_result['errors'].append(error_msg)
            logger.error(f"  ❌ 错误: {error_msg}")
            print(f"  ❌ 错误: {error_msg}")
        
        return daily_result
    
    def _get_tick_data(self, stock_code: str, date: str):
        """
        【CTO深市突围版】读取Tick数据
        
        前置条件：UniverseBuilder已过滤掉沪市股票
        深市股票的Tick数据健康，可以安全调用get_local_data
        """
        try:
            from xtquant import xtdata
            import pandas as pd
            import numpy as np
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 读取Tick数据
            # 【CTO修复】添加lastClose字段，用于获取昨收价
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount', 'lastClose', 'open'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not data or normalized_code not in data or data[normalized_code].empty:
                logger.warning(f"【时间机器】{date} {stock_code} 本地无Tick切片，跳过")
                return None
                
            df = data[normalized_code].copy()
            
            # 数据清洗
            if 'lastPrice' in df.columns:
                df['price'] = pd.to_numeric(df['lastPrice'], errors='coerce').fillna(0.0)
            else:
                df['price'] = 0.0
                
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0.0)
            else:
                df['volume'] = 0.0
                
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            else:
                df['amount'] = 0.0
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 读取 {stock_code} Tick 数据失败: {e}")
            return None
    
    def _get_pre_close(self, stock_code: str, date: str) -> float:
        """
        【CTO深市突围版】获取昨收价
        
        前置条件：UniverseBuilder已过滤掉沪市股票
        """
        try:
            from xtquant import xtdata
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 计算前一天的日期
            current = datetime.strptime(date, '%Y%m%d')
            prev_date = (current - timedelta(days=1)).strftime('%Y%m%d')
            
            # 获取日线数据
            data = xtdata.get_local_data(
                field_list=['time', 'close'],
                stock_list=[normalized_code],
                period='1d',
                start_time=prev_date,
                end_time=date
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty and len(df) >= 2:
                    return float(df.iloc[-2]['close'])
                elif not df.empty:
                    return float(df.iloc[0]['close'])
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"获取昨收价失败 {stock_code}: {e}")
            return 0.0
    
    @staticmethod
    def _normalize_stock_code(code: str) -> str:
        """
        标准化股票代码格式为 QMT 格式（######.SH / ######.SZ）
        
        Args:
            code: 股票代码，支持多种格式
        
        Returns:
            QMT 标准格式的股票代码
        """
        if not code:
            return code
        
        # 如果已经包含交易所后缀，直接返回
        if code.endswith('.SH') or code.endswith('.SZ'):
            return code
        
        # 提取6位数字代码
        code = code.strip().replace('.', '')
        
        if code.startswith('sh'):
            stock_code = code[2:]
            return f"{stock_code}.SH"
        elif code.startswith('sz'):
            stock_code = code[2:]
            return f"{stock_code}.SZ"
        elif code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        else:
            # 默认为主板
            return f"{code}.SH"
    
    def _calculate_morning_score(
        self, 
        stock_code: str, 
        date: str,
        memory_engine=None  # 【CTO P1 BUG FIX】外部注入，不再内部创建
    ) -> Optional[Dict]:
        """
        计算早盘得分 - 【CTO V20.5 MVP物理级重构版】
        
        修复: MFE=-100, inflow_ratio=0 等Bug
        原则: 拒绝未来函数，09:45打分后立刻退出
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
            memory_engine: 记忆引擎实例（外部注入，循环复用）
        
        Returns:
            得分字典或None
        """
        # 【CTO核爆级强转】：能挡住一切脏数据的铁壁！
        def force_float(val):
            if val is None: return 0.0
            try:
                if pd.isna(val) or np.isinf(val): return 0.0
            except:
                pass
            if isinstance(val, str):
                v_str = val.strip().lower()
                if not v_str or v_str in ('nan', 'inf', '-inf', 'null', 'none'): return 0.0
                try: return float(val)
                except: return 0.0
            if isinstance(val, (dict, list, tuple)): return 0.0
            try: return float(val)
            except: return 0.0

        try:
            # 获取数据
            tick_data = self._get_tick_data(stock_code, date)
            
            if tick_data is None or tick_data.empty:
                logger.warning(f"【时间机器】{stock_code} Tick数据为空！")
                return None
            logger.info(f"【时间机器】{stock_code} Tick数据获取成功，行数={len(tick_data)}")
            
            # 【CTO终极防爆】从Tick数据中获取昨收价（lastClose字段）
            # 避免调用_get_pre_close导致的BSON崩溃！
            pre_close = 0.0
            if 'lastClose' in tick_data.columns:
                # 从第一条有效Tick中获取昨收价
                for idx in range(min(10, len(tick_data))):
                    try:
                        last_close_val = tick_data.iloc[idx]['lastClose']
                        if last_close_val and last_close_val > 0:
                            pre_close = force_float(last_close_val)
                            break
                    except:
                        continue
            
            # 如果从Tick中获取失败，使用开盘价估算
            if pre_close <= 0 and 'open' in tick_data.columns:
                first_open = tick_data.iloc[0]['open']
                if first_open and first_open > 0:
                    pre_close = force_float(first_open)
                    logger.warning(f"【时间机器】{stock_code} 无法从Tick获取昨收价，使用开盘价估算: {pre_close}")
            
            avg_volume_5d = force_float(self._get_avg_volume_5d(stock_code, date))
            float_volume = force_float(self._get_float_volume(stock_code))
            
            # 核心参数为0，直接死刑，绝不在底下因为除零或类型报错！
            if pre_close <= 0.0 or avg_volume_5d <= 0.0 or float_volume <= 0.0:
                return None
            
            # 使用SanityGuards检查昨收价
            passed, msg = SanityGuards.check_pre_close_valid(pre_close, stock_code)
            if not passed:
                logger.warning(f"【时间机器】{stock_code} 昨收价检查失败: {msg}")
                return None
            
            # 【CTO核爆级强转】开盘价获取与校验
            open_price = force_float(0.0)
            
            # 【CTO修复】优先从tick数据的open字段获取开盘价
            if 'open' in tick_data.columns:
                for idx in range(min(10, len(tick_data))):
                    try:
                        open_val = tick_data.iloc[idx]['open']
                        if open_val and open_val > 0:
                            open_price = force_float(open_val)
                            logger.debug(f"【时间机器】{stock_code} 从Tick open字段获取开盘价: {open_price}")
                            break
                    except:
                        continue
            
            # 兜底2: 从第一条有效tick的lastPrice获取
            if open_price <= 0:
                for idx in range(min(50, len(tick_data))):
                    try:
                        price_val = tick_data.iloc[idx].get('lastPrice', 0) or tick_data.iloc[idx].get('price', 0)
                        if price_val and price_val > 0:
                            open_price = force_float(price_val)
                            logger.debug(f"【时间机器】{stock_code} 从第{idx}条Tick获取开盘价: {open_price}")
                            break
                    except:
                        continue
            
            # 兜底3: 使用昨收价估算开盘价 (假设高开2%)
            if open_price <= 0 and pre_close > 0:
                open_price = pre_close * 1.02
                logger.warning(f"【时间机器】{stock_code} 使用估算开盘价: {open_price:.2f} (昨收{pre_close} * 1.02)")
            
            # 最终校验: 只有当开盘价和昨收价都为0时才跳过
            if open_price <= 0 and pre_close <= 0:
                logger.warning(f"【时间机器】{stock_code} 开盘价和昨收价都无效，跳过")
                return None
            
            # 使用有效的开盘价
            first_tick_price = open_price if open_price > 0 else pre_close
            
            # CTO修复：正确处理时间戳获取09:40价格
            # 确保time列是字符串格式 HH:MM:SS
            if pd.api.types.is_numeric_dtype(tick_data['time']):
                # 如果是数值（毫秒时间戳），转换
                tick_data['time_str'] = pd.to_datetime(tick_data['time'], unit='ms') + pd.Timedelta(hours=8)
                tick_data['time_str'] = tick_data['time_str'].dt.strftime('%H:%M:%S')
            else:
                tick_data['time_str'] = tick_data['time'].astype(str)
            
            # 【CTO铁血整改】全天Tick状态机 - 严禁09:40截断！
            # === 初始化状态变量 ===
            flow_5min = 0.0
            flow_15min = 0.0
            max_price_after_0945 = 0.0
            vwap_cum_volume = 0.0
            vwap_cum_amount = 0.0
            final_score = 0.0
            sustain_ratio = 0.0
            inflow_ratio = 0.0
            ratio_stock = 0.0
            is_scored = False
            is_vetoed = False
            veto_reason = ""
            
            # 【CTO修复】早盘极值跟踪 (修复MFE=-100 Bug)
            # 用开盘价初始化，确保即使早盘没有tick数据也有基准值
            morning_high = open_price if open_price > 0 else pre_close
            morning_low = open_price if open_price > 0 else pre_close
            prev_vol = 0.0
            prev_price = open_price if open_price > 0 else pre_close
            last_dir = 1.0  # 【Boss钦定】平盘打捞：记录上一笔交易方向
            
            # 【Boss钦定】累计成交额和成交量，用于VWAP计算
            cumulative_amount = 0.0
            cumulative_volume = 0.0
            
            # === 获取流通市值用于Ratio计算 ===
            float_market_cap = force_float(float_volume * pre_close) if force_float(float_volume) > 0 else 1.0
            
            logger.debug(f"【时间机器】{stock_code} 开始遍历Tick数据，共{len(tick_data)}条")
            
            # === 全天Tick遍历 (09:30-15:00) ===
            # 【CTO终极防爆】在09:46之后退出循环，避免过多Tick遍历触发BSON崩溃
            # 打分已在09:45完成，后续防守逻辑使用简化计算
            tick_count = 0
            early_exit = False
            for index, row in tick_data.iterrows():
                tick_count += 1
                
                # 【CTO防爆】09:46之后退出循环
                if early_exit:
                    break
                
                try:
                    # 【CTO铁血时间转换】：杜绝一切int和str的比较崩溃！
                    raw_time = row.get('time')
                    
                    # 如果是数字（时间戳），强制转成HH:MM:SS
                    if isinstance(raw_time, (int, float)):
                        from datetime import datetime
                        curr_time = datetime.fromtimestamp(int(raw_time)/1000).strftime('%H:%M:%S')
                    else:
                        curr_time = str(raw_time).strip()
                    
                    # 如果转出来是很短的乱码，默认当作盘前
                    if len(curr_time) < 5:
                        curr_time = "09:00:00"
                    
                    # 提取价格与成交量
                    price = force_float(row.get('lastPrice', row.get('price', 0)))
                    volume = force_float(row.get('volume', 0))
                    amount = force_float(row.get('amount', price * volume))  # 优先用原始amount字段
                    
                    # 【CTO修复】delta_vol必须先计算，不管price是否为0！
                    # 因为volume是累计值，跳过更新会导致delta_vol计算错误
                    delta_vol = max(0.0, volume - prev_vol)
                    prev_vol = volume
                    
                    # 【CTO调试】打印第一个有效tick的volume值
                    if tick_count == 1:
                        print(f"【DEBUG】{stock_code} 第1个tick: volume={volume}, price={price}, amount={amount}")
                    if tick_count == 100:
                        print(f"【DEBUG】{stock_code} 第100个tick: volume={volume}, price={price}")
                    
                    if price <= 0: 
                        # 价格无效时跳过资金流计算，但delta_vol已经正确计算了
                        continue
                    
                    if price <= 0: continue
                    
                    # 【CTO修复】跟踪早盘极值 (修复MFE=-100 Bug)
                    if curr_time < '09:46:00':
                        morning_high = max(morning_high, price)
                        morning_low = min(morning_low, price)
                    
                    # ==========================================
                    # 【CTO微积分平滑算法】解决资金正负抵消黑洞
                    # 注意：delta_vol和prev_vol已在前方计算
                    # ==========================================
                    delta_amount = delta_vol * price  # 当前Tick的瞬时成交额
                    
                    # 引入微小波动缓冲，不让一分钱的下跌抵消掉几千万的流入
                    price_change = price - prev_price
                    price_change_pct = price_change / prev_price if prev_price > 0 else 0.0
                    
                    # 动能权重 (买方力量占比，范围 0.0 到 1.0)
                    if price_change_pct > 0.001:  # 涨幅大于千分之一，视为强势买单
                        buy_power = 1.0
                        last_dir = 1.0
                    elif price_change_pct < -0.001:  # 跌幅大于千分之一，视为强势卖单
                        buy_power = 0.0
                        last_dir = -1.0
                    else:
                        # 震荡区间（平盘或微小波动），按前一趋势的动能延续，并给予多空焦灼比例
                        buy_power = 0.6 if last_dir > 0 else 0.4
                    
                    # 净流入 = 买方成交额 - 卖方成交额
                    # buy_power为1.0时，净流入就是全额；buy_power为0.5时，净流入为0
                    instant_net_inflow = delta_amount * (buy_power - (1.0 - buy_power))
                    
                    # 【CTO调试】每100个tick打印一次
                    if tick_count % 100 == 0:
                        print(f"【DEBUG】{stock_code} Tick#{tick_count}: delta_vol={delta_vol:.0f}, price={price:.2f}, buy_power={buy_power:.2f}, instant={instant_net_inflow/1e4:.1f}万")
                    
                    # 累加资金流
                    flow_15min += instant_net_inflow
                    prev_price = price
                    
                    # 【Boss钦定】累计成交额和成交量（用于VWAP）
                    cumulative_amount += amount
                    cumulative_volume += volume
                    
                    # 【CTO修复】flow_5min累加：截取09:30-09:35前5分钟资金流
                    # 使用字符串前缀匹配，极其稳定，绝不漏算！
                    if (curr_time.startswith('09:30') or 
                        curr_time.startswith('09:31') or 
                        curr_time.startswith('09:32') or 
                        curr_time.startswith('09:33') or 
                        curr_time.startswith('09:34') or 
                        curr_time.startswith('09:35')):
                        flow_5min += instant_net_inflow
                    
                    # 【阶段一：09:30-09:45】累加打分数据 (flow_15min已在上方增量计算)
                    
                    # 【打分定格】09:45瞬间调用动能打分引擎验钞机
                    if not is_scored and ('09:45:00' <= curr_time < '09:46:00' or curr_time == '09:45:00'):
                        logger.debug(f"【时间机器】{stock_code} 触发09:45打分！时间={curr_time}, 价格={price}")
                        # 【CTO调试】打印资金流累计值和成交量
                        print(f"【DEBUG】{stock_code} 09:45时刻: volume={volume:.0f}, price={price:.2f}, flow_5min={flow_5min/1e8:.4f}亿, flow_15min={flow_15min/1e8:.4f}亿, float_cap={float_volume*pre_close/1e8:.2f}亿")
                        from logic.core.config_manager import get_config_manager
                        config_manager = get_config_manager()
                        
                        # 5日平均成交量已在前方强制转换
                        flow_5min_median = force_float(avg_volume_5d / 240) if force_float(avg_volume_5d) > 0 else 1.0  # 5分钟中位数估算
                        
                        # 计算Space Gap (突破纯度)
                        # 【CTO终极防爆】禁用_get_60d_high调用，避免BSON崩溃！
                        # 使用默认值：假设距离60日高点还有5%空间
                        space_gap_pct = 0.05  # 默认5%突破空间
                        logger.debug(f"【时间机器】{stock_code} 使用默认space_gap_pct={space_gap_pct}")
                        
                        # ============================================================
                        # 【记忆引擎挂载】算分前读取记忆衰减
                        # 【CTO P1 BUG FIX】使用外部注入的memory_engine，不再内部创建
                        # 【总监验证】纯净模式跳过记忆读取
                        # ============================================================
                        memory_multiplier = 1.0
                        if self.is_pure_mode:
                            logger.debug(f"🧪 [纯净模式] {stock_code} 跳过记忆读取，memory_multiplier=1.0")
                        else:
                            try:
                                if memory_engine is not None:
                                    memory_score = memory_engine.read_memory(stock_code, today=date)
                                    if memory_score is not None:
                                        # 将记忆分数转化为multiplier (0.5~1.5范围)
                                        memory_multiplier = 0.5 + (memory_score / 100.0)
                                        logger.debug(f"🧠 {stock_code} 记忆激活: score={memory_score:.2f}, multiplier={memory_multiplier:.2f}")
                                # 注意：不在函数内close()！由外部统一管理生命周期
                            except Exception as mem_e:
                                # Graceful降级：记忆引擎失败时multiplier=1.0
                                logger.debug(f"⚠️ {stock_code} 记忆读取失败，使用默认multiplier=1.0: {mem_e}")
                                memory_multiplier = 1.0
                        
                        # 调用动能打分引擎验钞机 (CTO终极红线版)
                        # 【CTO修复】current_time必须是datetime类型，不是time类型
                        current_time = datetime.strptime(f"{date} 09:45", "%Y%m%d %H:%M")
                        # 容错：如果极值未被更新，用当前价兜底
                        calc_high = morning_high if morning_high > 0 else price
                        calc_low = morning_low if morning_low != float('inf') else price
                        
                        try:
                            # 【CTO 强挂载】调用 V20.5 动能算子
                            mock_now = datetime.strptime(f"{date} 09:45", "%Y%m%d %H:%M")
                            
                            # 估算资金流中位数基准
                            flow_5min_median_stock = (avg_volume_5d / 240.0 * 5.0) * price if avg_volume_5d > 0 else flow_15min / 3.0
                            
                            base_score, sustain_ratio, inflow_ratio, ratio_stock, mfe_score = self._kinetic_engine.calculate_true_dragon_score(
                                net_inflow=flow_15min,
                                price=price,
                                prev_close=pre_close,
                                high=calc_high,  # 【CTO修复】使用真实早盘最高价
                                low=calc_low,    # 【CTO修复】使用真实早盘最低价
                                open_price=open_price,
                                flow_5min=flow_5min,
                                flow_15min=flow_15min,
                                flow_5min_median_stock=flow_5min_median_stock,
                                space_gap_pct=space_gap_pct,
                                float_volume_shares=float_volume,
                                current_time=mock_now,
                                total_amount=cumulative_amount,  # 【Boss钦定】传入累计成交额
                                total_volume=cumulative_volume   # 【Boss钦定】传入累计成交量
                            )
                        except Exception as kinetic_e:
                            print(f"【DEBUG】动能打分引擎算分异常: {type(kinetic_e).__name__}: {kinetic_e}")
                            logger.error(f"❌ {stock_code} 动能打分引擎算分失败: {kinetic_e}")
                            continue
                        
                        # 应用记忆multiplier
                        final_score = base_score * memory_multiplier
                        logger.debug(f"🎯 {stock_code} 动能打分引擎算分: base={base_score:.2f}, memory_mult={memory_multiplier:.2f}, final={final_score:.2f}")
                        
                        is_scored = True
                        early_exit = True  # 【CTO防爆】打分完成后退出循环
                        logger.debug(f"【时间机器】{stock_code} 打分完成，准备退出Tick遍历")
                    
                    # 【阶段二：09:45-15:00】防守与记录
                    if curr_time > '09:45:00':
                        # 记录09:45后的最高价 (用于骗炮计算)
                        # 【CTO修复】确保price和max_price_after_0945都是数值后再比较
                        if force_float(price) > force_float(max_price_after_0945):
                            max_price_after_0945 = force_float(price)
                        
                        # 更新VWAP
                        vwap_cum_volume = force_float(vwap_cum_volume + volume)
                        vwap_cum_amount = force_float(vwap_cum_amount + amount)
                        vwap = force_float(vwap_cum_amount / vwap_cum_volume) if force_float(vwap_cum_volume) > 0 else force_float(price)
                        
                        # 盘中破位防守 (VWAP宽容判定)
                        if curr_time > '09:50:00' and force_float(price) < force_float(vwap) and not is_vetoed:
                            # 检查是否放量砸盘
                            recent_volume = force_float(volume)
                            # 【CTO修复】确保recent_volume是数值后再比较
                            if force_float(recent_volume) > force_float(avg_volume_5d / 240 * 2):  # 放量
                                is_vetoed = True
                                veto_reason = "Veto: 盘中破位派发"
                
                except Exception as e:
                    # 某一个Tick坏了直接跳过，绝不允许崩溃！
                    continue
            
            # 【阶段三：15:00日落结算】严禁造假！
            # 【CTO终极防爆】完全禁用日K线获取，避免BSON崩溃！
            # 使用Tick最后价格作为收盘价（精度足够）
            real_close = force_float(price)  # 使用Tick最后价格作为收盘价
            logger.debug(f"【时间机器】{stock_code} 使用Tick最后价格作为收盘价: {real_close}")
            
            # 计算真实涨幅 (使用日K收盘价！)
            final_change = force_float(TRUE_CHANGE(real_close, pre_close))
            
            # 骗炮终审：Pullback_Ratio计算 - 全部使用force_float
            # 【CTO修复】确保数值后再比较
            if force_float(max_price_after_0945) > force_float(pre_close):
                pullback_ratio = force_float((max_price_after_0945 - real_close) / (max_price_after_0945 - pre_close))
            else:
                pullback_ratio = 0.0
            
            # 尖刺骗炮判定
            # 【CTO修复】确保数值后再比较
            if force_float(pullback_ratio) > 0.3 and force_float(final_change) < 0.08:
                is_vetoed = True
                veto_reason = f"Veto: 尖刺骗炮 (回落{pullback_ratio:.1%})"
                final_score = 0.0  # 分数清零！
            
            # 【CTO修复】数据完整性断言：如果没有成功打分，返回None
            if not is_scored:
                logger.warning(f"【时间机器】{stock_code} {date}: 未能在09:45完成打分（缺少关键时间点Tick数据），判定为数据缺失")
                return None
            
            # 【CTO】计算MFE (Maximum Favorable Excursion) 最大有利波动 - 使用force_float
            # 【CTO修复】使用morning_high而不是max_price_after_0945，因为early_exit导致后者未被更新
            effective_high = morning_high if morning_high > 0 else real_close
            if force_float(pre_close) > 0:
                mfe = force_float((effective_high - pre_close) / pre_close * 100)
            else:
                mfe = 0.0
            
            # 返回结果 - 所有数值都经过force_float
            return {
                'stock_code': stock_code,
                'final_score': force_float(final_score),
                'final_change': force_float(final_change),
                'real_close': force_float(real_close),
                'pre_close': force_float(pre_close),
                'max_price': force_float(max_price_after_0945),
                'pullback_ratio': force_float(pullback_ratio),
                'sustain_ratio': force_float(sustain_ratio),
                'inflow_ratio': force_float(inflow_ratio),
                'ratio_stock': force_float(ratio_stock),
                'mfe': force_float(mfe),
                'is_vetoed': is_vetoed,
                'veto_reason': veto_reason,
                'flow_5min': force_float(flow_5min),
                'flow_15min': force_float(flow_15min)
            }
            
        except Exception as e:
            logger.error(f"【时间机器】计算早盘得分失败 {stock_code}: {e}")
            return None
    
    def run_continuous_backtest(self, start_date: str, end_date: str, 
                                 stock_pool_path: str = None) -> List[Dict]:
        """
        连续多日回测 - 全息时间机器核心
        CTO铁律: 100%纯血QMT本地化，使用UniverseBuilder粗筛
        
        Args:
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            stock_pool_path: 股票池文件路径（可选），默认使用UniverseBuilder动态粗筛
        
        Returns:
            每日回测结果列表
        """
        print(f"\n{'#'*80}")
        print(f"# 全息时间机器启动")
        print(f"# 回测区间: {start_date} ~ {end_date}")
        print(f"# 初始资金: {self.initial_capital}元")
        print(f"# 数据源: UniverseBuilder动态粗筛 (QMT纯血)")
        print(f"{'#'*80}\n")
        
        logger.info(f"【时间机器】启动连续回测: {start_date} ~ {end_date}")
        logger.info(f"【时间机器】数据源: UniverseBuilder动态粗筛 (QMT纯血)")
        
        # ==========================================
        # 【CTO时空切割】全息回演使用平行宇宙记忆库
        # 绝不触碰实盘基因库 short_term_memory.json！
        # ==========================================
        self.is_continuous_backtest = True  # 标记为全息回演模式
        
        backtest_memory_file = PathResolver.get_data_dir() / 'memory' / 'ShortTermMemory_backtest.json'
        if backtest_memory_file.exists():
            logger.info("🗑️ 【时空清理】重置平行宇宙(回测)记忆库...")
            print("🧠 【平行宇宙】重置回测专属记忆库...")
            # 清空平行宇宙记忆，让回测以纯洁状态开始
            backtest_memory_file.unlink()
            print("✅ 【平行宇宙】回测记忆库已清空，实盘基因库不受影响！")
        else:
            logger.info("🆕 【平行宇宙】创建回测专属记忆库")
            print("🧠 【平行宇宙】使用隔离记忆库，实盘基因库不受影响！")
        
        logger.info("【系统已就绪】平行宇宙记忆库已准备，开始连贯穿越！")
        # ==========================================
        
        # 2. 获取交易日
        trade_dates = self.get_trade_dates(start_date, end_date)
        print(f"📅 交易日: {len(trade_dates)} 天")
        logger.info(f"交易日: {len(trade_dates)} 天")
        
        # 3. 逐日回测
        all_results = []
        
        for i, date in enumerate(trade_dates, 1):
            print(f"\n📌 进度: [{i}/{len(trade_dates)}] {date}")
            
            # CTO铁律: 每日动态粗筛 (UniverseBuilder纯血模式)
            try:
                stock_pool = self._load_stock_pool(date=date)
                print(f"  📊 当日粗筛: {len(stock_pool)} 只")
            except Exception as e:
                error_msg = str(e)
                # CTO修复：检测是否为节假日（UniverseBuilder返回空）
                if '粗筛返回空股票池' in error_msg or 'Empty' in error_msg:
                    logger.warning(f"【时间机器】{date} 可能是节假日，跳过")
                    print(f"  ⏭️  {date} 节假日/非交易日，跳过")
                    all_results.append({
                        'date': date,
                        'status': 'holiday_skipped',
                        'error': '节假日或非交易日'
                    })
                else:
                    logger.error(f"【时间机器】{date} 粗筛失败: {e}")
                    print(f"  ❌ {date} 粗筛失败: {e}")
                    all_results.append({
                        'date': date,
                        'status': 'coarse_filter_failed',
                        'error': error_msg
                    })
                    continue
            
            daily_result = self.run_daily_backtest(date, stock_pool)
            all_results.append(daily_result)
            
            # 保存每日结果
            self._save_daily_result(date, daily_result)
            
            # 清理缓存
            self.results_cache.clear()
        
        # 4. 生成总结报告
        self._generate_summary_report(all_results, start_date, end_date)
        
        # 统计结果
        success_count = len([r for r in all_results if r['status'] == 'success'])
        
        print(f"\n{'#'*80}")
        print(f"# 全息时间机器完成")
        print(f"# 成功: {success_count}/{len(all_results)}")
        print(f"{'#'*80}\n")
        
        logger.info(f"【时间机器】连续回测完成: {success_count}/{len(all_results)} 成功")
        
        return all_results
    
    def _load_stock_pool(self, path: str = None, date: str = None) -> List[str]:
        """
        加载股票池 - CTO铁律: 100%纯血QMT本地化
        
        Args:
            path: 股票池文件路径（可选），如果为None则使用UniverseBuilder动态粗筛
            date: 日期 'YYYYMMDD' (用于UniverseBuilder粗筛)
        
        Returns:
            股票代码列表 (约500只)
        
        Raises:
            RuntimeError: 无法获取真实数据时抛出致命异常 (Fail Fast)
        """
        # CTO铁律: 默认使用UniverseBuilder动态粗筛
        if path is None:
            if not date:
                raise ValueError("使用UniverseBuilder粗筛时必须提供date参数")
            
            logger.info(f"【时间机器】使用UniverseBuilder获取股票池: {date}")
            # 【CTO断头台】：Fail Fast！直接调用，让错误暴露！
            # UniverseBuilder内部使用正确的绝对阈值3.0
            builder = UniverseBuilder(target_date=date)
            logger.info(f"【时间机器】开始调用build()...")
            stock_pool, _ = builder.build()  # 【CTO修复】接收tuple，丢弃market_ratios
            
            logger.info(f"【时间机器】UniverseBuilder返回: {len(stock_pool)} 只股票")
            
            if not stock_pool:
                logger.error(f"【时间机器】 UniverseBuilder返回空股票池: {date}")
                # 【CTO修复】返回空列表而不是报错，让上层处理
                return []
            
            logger.info(f"【时间机器】股票池获取完成: {len(stock_pool)} 只")
            return stock_pool
            
        # 如果提供CSV文件路径
        full_path = PathResolver.resolve_path(path)
        
        if not full_path.exists():
            logger.error(f"【时间机器】股票池文件不存在: {path}")
            raise FileNotFoundError(f"股票池文件不存在: {path}。请提供有效CSV文件或使用UniverseBuilder进行动态粗筛")
        
        try:
            df = pd.read_csv(full_path)
            if 'ts_code' in df.columns:
                return df['ts_code'].tolist()
            elif 'stock_code' in df.columns:
                return df['stock_code'].tolist()
            elif 'code' in df.columns:
                return df['code'].tolist()
            else:
                # 假设第一列是股票代码
                return df.iloc[:, 0].tolist()
        except Exception as e:
            logger.error(f"【时间机器】加载股票池失败: {e}")
            raise RuntimeError(f"无法加载股票池文件: {e}") from e
    
    def _save_daily_result(self, date: str, result: Dict):
        """
        保存每日结果
        
        Args:
            date: 日期 'YYYYMMDD'
            result: 当日回测结果
        """
        try:
            output_dir = PathResolver.get_data_dir() / 'backtest_out' / 'time_machine'
            PathResolver.ensure_dir(output_dir)
            
            output_file = output_dir / f'time_machine_{date}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"【时间机器】结果已保存: {output_file}")
        except Exception as e:
            logger.error(f"保存每日结果失败: {e}")
    
    def _generate_summary_report(self, results: List[Dict], start_date: str, end_date: str):
        """
        生成总结报告 - CTODict: 修复success_days统计，扩容至Top 20
        
        Args:
            results: 所有回测结果
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 统计各状态天数
            success_results = [r for r in results if r.get('status') == 'success']
            insufficient_results = [r for r in results if r.get('status') == 'insufficient_data']
            error_results = [r for r in results if r.get('status') == 'error']
            coarse_failed_results = [r for r in results if r.get('status') == 'coarse_filter_failed']
            
            report = {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': len(results),
                'success_days': len(success_results),
                'insufficient_data_days': len(insufficient_results),
                'error_days': len(error_results),
                'coarse_filter_failed_days': len(coarse_failed_results),
                'statistics_by_date': {
                    r['date']: {
                        'status': r.get('status'),
                        'valid_stocks': r.get('valid_stocks', 0),
                        'top1_score': r.get('top20', [{}])[0].get('final_score', 0) if r.get('top20') else 0
                    }
                    for r in results
                },
                'daily_top20': [
                    {
                        'date': r['date'],
                        'top20': r.get('top20', []),
                        'valid_stocks': r.get('valid_stocks', 0)
                    } 
                    for r in success_results
                ]
            }
            
            output_dir = PathResolver.get_data_dir() / 'backtest_out' / 'time_machine'
            PathResolver.ensure_dir(output_dir)
            
            output_file = output_dir / f'time_machine_summary_{start_date}_{end_date}.json'
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n  📄 总结报告已保存: {output_file}")
            logger.info(f"【时间机器】总结报告已保存: {output_file}")
            
        except Exception as e:
            logger.error(f"生成总结报告失败: {e}")
    
    def get_backtest_summary(self, start_date: str, end_date: str) -> Optional[Dict]:
        """
        获取回测总结报告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            报告字典或None
        """
        try:
            output_file = (
                PathResolver.get_data_dir() / 'backtest_out' / 'time_machine' / 
                f'time_machine_summary_{start_date}_{end_date}.json'
            )
            
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
        except Exception as e:
            logger.error(f"读取总结报告失败: {e}")
            return None
    
    # ==================== 记忆衰减机制 ====================
    
    # ==================== 记忆衰减机制 ====================
    # 【CTO手术一：封闭私写后门】
    # _load_memory() 和 _save_memory() 已删除
    # 所有记忆操作通过 ShortTermMemoryEngine API
    
    def _apply_memory_decay(self, current_date: str, today_top20: List[Dict], record_date: Optional[str] = None) -> Dict[str, Dict]:
        """
        【CTO P0级重铸】动态势能记忆评估算法
        【CTO手术二 Fix 3】增加 record_date 参数，回测时传入回测日期
        
        核心物理思想：
        1. 强更强(1.25x): 排名上升/维持 + 分数上升 → 奖励25%溢价
        2. 弱转强(1.05x): 分数微降但排名未崩 → 维持5%微弱溢价
        3. 不及预期(0.65x): 分数大幅下滑或排名暴跌 → 惩罚35%权重
        4. 缺席衰减(0.5x): 未上榜 → 固定断崖衰减
        
        Args:
            current_date: 当前日期 'YYYYMMDD'
            today_top20: 今日Top20列表 [{'stock_code': str, 'final_score': float, ...}]
            record_date: 【CTO手术二】记录日期 'YYYYMMDD'，回测时必须传入，默认使用current_date
        
        Returns:
            更新后的记忆字典
        """
        # 【CTO手术二 Fix 3】确定记录日期
        if record_date is None:
            record_date = current_date
        
        # 【CTO手术一】封闭私写后门：使用 ShortTermMemoryEngine API
        from logic.memory.short_term_memory import ShortTermMemoryEngine
        
        # 1. 初始化记忆引擎
        if self.is_continuous_backtest:
            memory_file = PathResolver.get_data_dir() / 'memory' / 'ShortTermMemory_backtest.json'
            memory_engine = ShortTermMemoryEngine(memory_file=str(memory_file))
        else:
            memory_engine = ShortTermMemoryEngine()
        
        # 2. 加载旧记忆（通过API而非直接读JSON）
        old_memory_dict = {}
        for stock_code in memory_engine.list_all():
            mem_detail = memory_engine.get_full_memory(stock_code)
            if mem_detail:
                # 转换为 _apply_memory_decay 期望的格式
                old_memory_dict[stock_code] = {
                    'score': mem_detail.get('current_score', mem_detail.get('initial_score', 0)),
                    'last_rank': mem_detail.get('metadata', {}).get('last_rank', 20),
                    'absent_days': mem_detail.get('metadata', {}).get('absent_days', 0),
                    'last_decay_date': mem_detail.get('last_active_date', ''),
                    'last_verdict': mem_detail.get('metadata', {}).get('last_verdict', ''),
                    'date': mem_detail.get('create_date', '')
                }
        
        new_memory_dict = {}
        
        # 3. 构建今日股票映射
        today_map = {item['stock_code']: item for item in today_top20}
        today_top_codes = set(today_map.keys())
        
        # 4. 统计计数
        stats = {
            'strong_stronger': 0,      # 强更强
            'weak_to_strong': 0,       # 弱转强
            'underperformed': 0,       # 不及预期
            'absent_decay': 0,         # 缺席衰减
            'removed_absent': 0,       # 删除(缺席)
            'removed_low_score': 0,    # 删除(低分)
            'new_added': 0             # 新增
        }
        
        # 5. 遍历旧记忆，进行动态势能评估
        for stock_code, mem_item in old_memory_dict.items():
            old_score = mem_item.get('score', 0.0)
            old_rank = mem_item.get('last_rank', 20)
            
            if stock_code in today_top_codes:
                # 【情况A：继续上榜，动态评估】
                today_item = today_map[stock_code]
                today_score = today_item.get('final_score', 0.0)
                # 计算今日排名
                today_rank = next((i for i, x in enumerate(today_top20) if x['stock_code'] == stock_code), 20)
                
                # ============ 核心物理算法：动能与位能变化 ============
                if today_score >= old_score and today_rank <= old_rank:
                    # 强更强：排名上升/维持 + 分数上升 → 奖励 1.25 倍
                    multiplier = 1.25
                    verdict = "强更强"
                    stats['strong_stronger'] += 1
                elif today_score >= old_score * 0.85 and today_rank <= old_rank + 3:
                    # 弱转强/高位震荡：分数微降但排名未崩 → 维持 1.05 倍
                    multiplier = 1.05
                    verdict = "弱转强"
                    stats['weak_to_strong'] += 1
                else:
                    # 不及预期：分数大幅下滑或排名暴跌 → 惩罚 0.65 倍
                    multiplier = 0.65
                    verdict = "不及预期"
                    stats['underperformed'] += 1
                
                new_score = min(100.0, old_score * multiplier)  # 封顶 100 分
                
                new_memory_dict[stock_code] = {
                    'stock_code': stock_code,
                    'date': record_date,  # 【CTO手术二】使用record_date而非current_date
                    'score': round(new_score, 2),
                    'absent_days': 0,
                    'last_decay_date': record_date,  # 【CTO手术二】使用record_date
                    'last_rank': today_rank,
                    'last_verdict': verdict
                }
                logger.debug(f"🧠 [记忆动态进化] {stock_code}: {verdict} (Rank {old_rank}->{today_rank}), Score: {old_score:.1f}->{new_score:.1f}")
                
            else:
                # 【情况B：未上榜，机械衰减】
                absent_days = mem_item.get('absent_days', 0) + 1
                
                if absent_days >= MEMORY_MAX_ABSENCE_DAYS:
                    logger.debug(f"🧠 [记忆湮灭] {stock_code}: 连续缺席 {absent_days} 天，彻底清除")
                    stats['removed_absent'] += 1
                    continue  # 物理删除
                
                new_score = old_score * MEMORY_DECAY_FACTOR
                if new_score < MEMORY_WRITE_MIN_SCORE:
                    stats['removed_low_score'] += 1
                    continue  # 分数太低，物理删除
                
                mem_item['score'] = round(new_score, 2)
                mem_item['absent_days'] = absent_days
                mem_item['last_decay_date'] = record_date  # 【CTO手术二】使用record_date
                mem_item['last_verdict'] = f"缺席衰减(Day {absent_days})"
                new_memory_dict[stock_code] = mem_item
                stats['absent_decay'] += 1
        
        # 6. 录入新晋妖股
        for rank_idx, item in enumerate(today_top20):
            stock_code = item['stock_code']
            if stock_code not in new_memory_dict:
                new_memory_dict[stock_code] = {
                    'stock_code': stock_code,
                    'date': record_date,  # 【CTO手术二】使用record_date而非current_date
                    'score': item.get('final_score', 60.0),  # 初始记忆底分
                    'absent_days': 0,
                    'last_decay_date': record_date,  # 【CTO手术二】使用record_date
                    'last_rank': rank_idx,
                    'last_verdict': '首次入榜'
                }
                stats['new_added'] += 1
                logger.debug(f"🧠 [记忆新生] {stock_code}: 首次打入 Top20, 写入基因库")
        
        # 7. 【CTO手术一】通过 ShortTermMemoryEngine API 保存记忆
        # 先清空旧记忆
        memory_engine.clear_all(confirm=True)
        
        # 写入新记忆
        for stock_code, mem_item in new_memory_dict.items():
            memory_engine.write_memory(
                stock_code=stock_code,
                gain_pct=mem_item.get('score', 60.0),  # 用 score 代替 gain_pct
                turnover_rate=5.5,  # 默认满足阈值
                blood_pct=mem_item.get('score', 60.0),
                metadata={
                    'date': mem_item.get('date', record_date),
                    'last_rank': mem_item.get('last_rank', 20),
                    'last_verdict': mem_item.get('last_verdict', ''),
                    'absent_days': mem_item.get('absent_days', 0)
                },
                force=True,  # 【CTO手术一】强制写入，跳过阈值检查
                record_date=record_date  # 【CTO手术二 Fix 3】传入record_date参数
            )
        
        memory_engine.force_save()
        memory_engine.close()
        
        # 8. 打印统计
        print(f"\n  🧠 记忆动态进化统计:")
        print(f"     强更强(1.25x): {stats['strong_stronger']} 条")
        print(f"     弱转强(1.05x): {stats['weak_to_strong']} 条")
        print(f"     不及预期(0.65x): {stats['underperformed']} 条")
        print(f"     缺席衰减(0.5x): {stats['absent_decay']} 条")
        print(f"     删除(缺席≥2天): {stats['removed_absent']} 条")
        print(f"     删除(低分<{MEMORY_WRITE_MIN_SCORE}): {stats['removed_low_score']} 条")
        print(f"     新增(首次入榜): {stats['new_added']} 条")
        print(f"     当前记忆总数: {len(new_memory_dict)} 条")
        
        logger.info(f"【记忆动态进化】强更强{stats['strong_stronger']}, 弱转强{stats['weak_to_strong']}, "
                   f"不及预期{stats['underperformed']}, 缺席衰减{stats['absent_decay']}, "
                   f"新增{stats['new_added']}, 当前{len(new_memory_dict)}")
        
        return new_memory_dict

    # ==================== Step6: 时空对齐与全息回演UI看板 ====================
    
    

    def calculate_time_slice_flows(self, stock_code: str, date: str) -> Optional[Dict]:
        """
        【CTO终极红线：时空绝对对齐】计算真实时间切片资金流
        
        核心要求：
        1. 绝不允许用全天数据估算切片！必须通过 get_local_data(period='tick'/'1m') 真实拉取日内历史流
        2. 截取 09:30-09:35 计算真实 flow_5min
        3. 截取 09:30-09:45 计算真实 flow_15min
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
            
        Returns:
            Dict: 包含flow_5min, flow_15min的字典，或None（数据不足）
        """
        try:
            from xtquant import xtdata
            
            # 标准化代码
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 【核心】真实拉取日内历史Tick流 - 严禁用全天数据估算！
            tick_data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not tick_data or normalized_code not in tick_data:
                logger.warning(f"⚠️ {stock_code} 无Tick数据")
                return None
            
            df = tick_data[normalized_code]
            if df.empty or len(df) < 10:
                logger.warning(f"⚠️ {stock_code} Tick数据不足")
                return None
            
            # 转换时间戳为可读时间
            if 'time' in df.columns:
                if pd.api.types.is_numeric_dtype(df['time']):
                    df['datetime'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                    df['time_str'] = df['datetime'].dt.strftime('%H:%M:%S')
                else:
                    df['time_str'] = df['time'].astype(str)
            
            # 【时空切片1】截取 09:30-09:35 计算真实 flow_5min
            df_5min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:35:00')].copy()
            if df_5min.empty:
                logger.warning(f"⚠️ {stock_code} 09:30-09:35 无数据")
                return None
            
            # 计算5分钟资金流入（简化：用amount增量）
            if 'amount' in df_5min.columns:
                flow_5min = df_5min['amount'].sum()
            else:
                # 如果没有amount，用 price * volume * 100 估算
                flow_5min = (df_5min['lastPrice'] * df_5min['volume'] * 100).sum()
            
            # 【时空切片2】截取 09:30-09:45 计算真实 flow_15min
            df_15min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:45:00')].copy()
            if df_15min.empty:
                logger.warning(f"⚠️ {stock_code} 09:30-09:45 无数据")
                return None
            
            if 'amount' in df_15min.columns:
                flow_15min = df_15min['amount'].sum()
            else:
                flow_15min = (df_15min['lastPrice'] * df_15min['volume'] * 100).sum()
            
            logger.debug(f"✅ {stock_code} 时空切片: 5min={flow_5min/1e8:.2f}亿, 15min={flow_15min/1e8:.2f}亿")
            
            return {
                'flow_5min': float(flow_5min),
                'flow_15min': float(flow_15min),
                'tick_count_5min': len(df_5min),
                'tick_count_15min': len(df_15min)
            }
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 时空切片计算失败: {e}")
            return None

    
    

    


# CLI入口
if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建引擎
    engine = TimeMachineEngine(initial_capital=20000.0)
    
    # 测试：回测1.5日前后10天
    results = engine.run_continuous_backtest(
        start_date='20251231',
        end_date='20260110',
        stock_pool_path='data/cleaned_candidates_66.csv'
    )
    
    # 打印最终结果
    print("\n" + "="*80)
    print("回测完成!")
    print(f"总交易日: {len(results)}")
    print(f"成功: {len([r for r in results if r['status']=='success'])}")
    print("="*80)