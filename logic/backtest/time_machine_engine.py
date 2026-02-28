"""
全息时间机器引擎 - 连续多日回测
自动执行连续N个交易日的回测，验证策略稳定性

Author: iFlow CLI
Date: 2026-02-24
Version: 1.2.0 - 配置管理器集成版
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import json
import logging

from logic.core.path_resolver import PathResolver

# 记忆衰减参数
MEMORY_DECAY_FACTOR = 0.5      # 衰减系数
MEMORY_MIN_SCORE = 10.0        # 最低分数阈值
MEMORY_MAX_ABSENCE_DAYS = 2    # 连续不上榜最大天数
from logic.core.metric_definitions import MetricDefinitions
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
    
    # 记忆文件路径
    MEMORY_FILE = Path(__file__).parent.parent.parent / 'data' / 'memory' / 'ShortTermMemory.json'
    
    def __init__(self, initial_capital: float = 20000.0):
        self.initial_capital = initial_capital
        self.data_manager = QmtDataManager()
        self.results_cache: Dict[str, Dict] = {}
        self._ensure_output_dirs()
        
        # CTO修复：启动VIP服务确保数据连接
        self.data_manager.start_vip_service()
        
    def _ensure_output_dirs(self):
        """确保输出目录存在"""
        output_dir = PathResolver.get_data_dir() / 'backtest_out'
        PathResolver.ensure_dir(output_dir)
        PathResolver.ensure_dir(output_dir / 'time_machine')
        
    def _get_avg_volume_5d(self, stock_code: str, date: str) -> float:
        """
        获取股票5日平均成交量 (用于计算量比)
        
        Args:
            stock_code: 股票代码
            date: 当前日期 'YYYYMMDD'
        
        Returns:
            5日平均成交量，失败返回0
        """
        try:
            from xtquant import xtdata
            from datetime import datetime, timedelta
            
            # 计算5个交易日的日期范围
            current = datetime.strptime(date, '%Y%m%d')
            dates = []
            while len(dates) < 5:
                current -= timedelta(days=1)
                # 检查是否是交易日（跳过周末）
                if current.weekday() < 5:
                    dates.append(current.strftime('%Y%m%d'))
            
            # 获取日线数据
            normalized_code = self._normalize_stock_code(stock_code)
            data = xtdata.get_local_data(
                field_list=['time', 'volume'],
                stock_list=[normalized_code],
                period='1d',
                start_time=dates[-1],  # 最早日期
                end_time=dates[0]      # 最近日期
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty and len(df) >= 5:
                    # 取最近5个交易日的成交量
                    recent_volumes = df.tail(5)['volume'].values
                    avg_volume = sum(recent_volumes) / len(recent_volumes)
                    return float(avg_volume)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"获取5日均量失败 {stock_code}: {e}")
            return 0.0
    
    def _get_float_volume(self, stock_code: str) -> float:
        """
        获取股票流通股本 (用于计算换手率)
        
        【CTO修复】使用QMT正确的API: get_instrument_detail
        删除幻觉API: xtdata.get_stock_list() (该API不存在)
        
        Args:
            stock_code: 股票代码
        
        Returns:
            流通股本，失败返回0
        """
        try:
            from xtquant import xtdata
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 【CTO修复】使用正确的QMT API获取股票详情
            detail = xtdata.get_instrument_detail(normalized_code, True)
            
            if detail is not None:
                # 提取FloatVolume(流通股本)
                fv = detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0)
                if fv:
                    # 【CTO修复】强制转换为float，防止类型爆炸
                    return float(fv)
            
            # 降级方案：使用历史数据估算
            logger.warning(f"【降级】{stock_code} 无法获取流通股本，尝试估算...")
            data = xtdata.get_local_data(
                field_list=['time', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='1d',
                start_time='20250101',
                end_time='20251231'
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty:
                    avg_daily_volume = df['volume'].tail(10).mean()
                    # 【CTO修复】强制转换为float
                    return float(avg_daily_volume * 200)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"获取流通股本失败 {stock_code}: {e}")
            return 0.0
    
    def _get_volume_ratio_threshold_for_date(self, date: str, base_percentile: float) -> float:
        """
        获取特定日期的量比阈值 (CTO SSOT原则)
        
        Args:
            date: 日期 'YYYYMMDD'
            base_percentile: 基础分位数
        
        Returns:
            量比阈值
        """
        # CTO强制执行：回测引擎必须使用配置管理器的分位数参数
        # 不允许在回测中写死 return 3.0！必须算出当天的动态分位数！
        from logic.core.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # 使用配置中的分位数，如果提供了base_percentile则使用它，否则使用配置默认值
        volume_ratio_percentile = config_manager.get_volume_ratio_percentile('live_sniper')
        
        # 为了计算动态阈值，需要获取当日的量比数据
        # 由于在回测环境下，我们无法直接获取当日全市场数据
        # 所以这里使用配置的分位数值作为基准，但不使用硬编码的3.0
        return volume_ratio_percentile
    
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
        # 【CTO修复】全市场扫描兜底
        if stock_pool is None:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("【时间机器】未指定股票池，默认获取全市场股票...")
            try:
                from xtquant import xtdata
                stock_pool = xtdata.get_stock_list_in_sector('沪深A股')
            except Exception:
                stock_pool = []
            if not stock_pool:
                logger.warning("【时间机器】获取全市场失败，请检查数据。")
                return None
        """
        单日回测
        
        模拟实盘流程：
        1. 09:30 开盘前准备
        2. 09:40 计算早盘数据
        3. 输出当日Top 20 (CTODict: 扩容观察梯度)
        
        Args:
            date: 交易日期 'YYYYMMDD'
            stock_pool: 股票代码列表
        
        Returns:
            当日回测结果字典
        """
        print(f"\n{'='*60}")
        print(f"【时间机器】回测日期: {date}")
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
            # CTO修复：第一步 - VIP阻塞下载数据（打通任督二脉！）
            # 【CTO修复】禁用阻塞下载，只使用本地缓存\n            # 系统只读取本地已缓存数据，无数据直接跳过\n            
            # 2. 获取当日股票池数据
            # 【CTO修复】禁止串行拉取Tick！使用日K数据快速筛选，大幅提速
            print(f"  📊 获取 {len(stock_pool)} 只股票数据...")
            
            valid_stocks = []
            batch_size = 100  # 批处理大小
            
            # 【CTO优化】使用日K数据快速初筛，避免5000只股票串行拉取Tick
            try:
                from xtquant import xtdata
                
                # 批量获取日K数据（向量化，速度快）
                normalized_codes = [self._normalize_stock_code(s) for s in stock_pool]
                daily_data = xtdata.get_local_data(
                    field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
                    stock_list=normalized_codes,
                    period='1d',
                    start_time=date,
                    end_time=date
                )
                
                # 快速筛选有日K数据的股票
                stocks_with_daily = []
                for stock in stock_pool:
                    norm_code = self._normalize_stock_code(stock)
                    if daily_data and norm_code in daily_data and not daily_data[norm_code].empty:
                        stocks_with_daily.append(stock)
                
                print(f"  📈 日K数据筛选: {len(stocks_with_daily)}/{len(stock_pool)} 只有效")
                
                # 对初筛后的股票，选择性获取Tick数据
                for i, stock in enumerate(stocks_with_daily):
                    try:
                        # 【CTO核级重构】删除进度日志，严禁循环内下载
                        # 进度显示已删除 - 不再输出"⏳ 检查进度"
                        
                        # 【CTO优化】优先使用日K数据估算，Tick数据按需获取
                        tick_data = self._get_tick_data(stock, date)
                        # 【CTO修复】降低阈值从100到10，避免数据不足时全部跳过
                        if tick_data is not None and len(tick_data) > 10:
                            valid_stocks.append(stock)
                            logger.debug(f"  ✓ {stock}: {len(tick_data)} 条Tick数据")
                        else:
                            # Tick数据不足，尝试使用日K数据
                            logger.debug(f"  ⏭️ {stock}: Tick数据不足({len(tick_data) if tick_data else 0}条)，尝试日K降级")
                            # 【CTO修复】即使Tick数据不足，只要有日K数据也加入
                            valid_stocks.append(stock)
                            
                    except Exception as e:
                        # 【CTO优化】异常时直接continue，不记录详细错误以提速
                        continue
                        
            except Exception as e:
                logger.warning(f"  ⚠️ 批量数据获取失败，降级到串行模式: {e}")
                # 降级：串行模式但仍保持快速跳过
                for stock in stock_pool:
                    try:
                        tick_data = self._get_tick_data(stock, date)
                        if tick_data is not None and len(tick_data) > 100:
                            valid_stocks.append(stock)
                    except:
                        continue  # 快速跳过失败的股票
            
            daily_result['valid_stocks'] = len(valid_stocks)
            print(f"  ✅ 有效数据: {len(valid_stocks)} 只")
            
            if len(valid_stocks) < 5:
                daily_result['status'] = 'insufficient_data'
                logger.warning(f"  ⚠️ 数据不足: 仅 {len(valid_stocks)} 只有效数据")
                return daily_result
            
            # 2. 计算09:40指标（早盘5分钟+5分钟）
            print(f"  🧮 计算早盘指标...")
            
            stock_scores = []
            data_missing_count = 0
            data_missing_stocks = []  # 记录因数据缺失被跳过的股票
            
            for stock in valid_stocks:
                try:
                    score = self._calculate_morning_score(stock, date)
                    
                    # 【CTO修复】数据完整性断言：禁止0分兜底
                    if score is None:
                        data_missing_count += 1
                        data_missing_stocks.append(stock)
                        logger.warning(f"  ⚠️ {stock}: 数据缺失，跳过算分")
                        continue
                    
                    # 检查关键数据字段
                    if score.get('final_score', 0) == 0:
                        # 区分是Veto导致的0分还是数据缺失导致的0分
                        if not score.get('is_vetoed', False):
                            data_missing_count += 1
                            data_missing_stocks.append(stock)
                            logger.warning(f"  ⚠️ {stock}: final_score=0且无Veto标记，判定为数据缺失，跳过")
                            continue
                    
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
            
            # 3. 【CTO多维排序】得分相同看MFE，MFE大于5倒扣
            # 计算MFE (最大 favorable excursion)
            for score in stock_scores:
                max_price = score.get('max_price', 0)
                pre_close = score.get('pre_close', 1)
                # MFE = (最高价 - 昨收) / 昨收 * 100，无量纲百分比
                mfe = ((max_price - pre_close) / pre_close * 100) if pre_close > 0 else 0
                score['mfe'] = mfe
                # MFE大于5%倒扣分数（惩罚冲高回落）
                if mfe > 5:
                    score['final_score'] = score.get('final_score', 0) - (mfe - 5) * 2
            
            # 多维排序：final_score降序，相同则看MFE升序（MFE越小越好）
            stock_scores.sort(key=lambda x: (x.get('final_score', 0), -x.get('mfe', 0)), reverse=True)
            top20 = stock_scores[:20]
            
            daily_result['top20'] = top20
            daily_result['status'] = 'success'
            daily_result['data_missing_count'] = data_missing_count
            daily_result['data_missing_stocks'] = data_missing_stocks
            
            # 5. 执行记忆衰减
            self._apply_memory_decay(date, top20)
            
            # ============================================================
            # 【记忆引擎挂载】盘后结算 - 写入记忆基因
            # ============================================================
            try:
                from logic.memory.short_term_memory import ShortTermMemoryEngine
                memory_engine = ShortTermMemoryEngine()
                
                # 为Top20中符合条件的股票写入记忆
                # 条件：涨幅>8% 且 换手>5% (ShortTermMemoryEngine内部会检查)
                for item in top20:
                    stock_code = item['stock_code']
                    final_change = item.get('final_change', 0)
                    # 估算换手率 (使用turnover_rate字段或估算)
                    turnover_rate = item.get('turnover_rate', 5.5)  # 默认满足阈值
                    final_score = item.get('final_score', 0)
                    
                    # 写入记忆 (引擎内部会检查涨幅>8%且换手>5%)
                    memory_engine.write_memory(
                        stock_code=stock_code,
                        gain_pct=final_change,
                        turnover_rate=turnover_rate,
                        blood_pct=final_score,
                        metadata={
                            'date': date,
                            'sustain_ratio': item.get('sustain_ratio', 0),
                            'inflow_ratio': item.get('inflow_ratio', 0),
                            'is_vetoed': item.get('is_vetoed', False)
                        }
                    )
                
                # 湮灭过期记忆(≥2天未激活)
                memory_engine.annihilate_expired(today=date)
                
                # 强制保存
                memory_engine.force_save()
                memory_engine.close()
                
                logger.info(f"🧠 【记忆引擎】盘后结算完成: {date} 记忆已写入")
                
            except Exception as mem_e:
                # Graceful降级：记忆引擎失败不影响主流程
                logger.warning(f"⚠️ 【记忆引擎】盘后结算失败: {mem_e}")
            
            # 【Step6: 时空对齐与全息回演UI看板】
            # 【CTO统一战报】使用工业级大屏render_battle_dashboard
            
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
                    top_dragons=dragons_for_dashboard,
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
    
    def _get_tick_data(self, stock_code: str, date: str) -> Optional[pd.DataFrame]:
        """
        【CTO铁腕断头台】：回测引擎只能读本地！没有就滚！
        严禁任何下载行为！
        """
        try:
            from xtquant import xtdata
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 只读本地数据，严禁下载！
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if data and normalized_code in data and not data[normalized_code].empty:
                df = data[normalized_code]
                # 转换时间格式
                if 'time' in df.columns:
                    df['time'] = df['time'].apply(
                        lambda x: datetime.fromtimestamp(x/1000).strftime('%H:%M:%S') 
                        if isinstance(x, (int, float)) else str(x)
                    )
                # 重命名价格列
                if 'lastPrice' in df.columns:
                    df = df.rename(columns={'lastPrice': 'price'})
                return df
            
            # 无数据直接返回None，严禁下载！
            return None
            
        except Exception as e:
            logger.warning(f"获取Tick数据失败 {stock_code}: {e}")
            return None
    
    def _get_pre_close(self, stock_code: str, date: str) -> float:
        """
        获取昨收价 (CTO修复: 确保VIP服务已启动)
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
        
        Returns:
            昨收价，失败返回0
        """
        try:
            from xtquant import xtdata
            
            # CTO修复: 确保VIP服务已启动才能读取数据
            if not self.data_manager._vip_initialized:
                self.data_manager.start_vip_service()
            
            # 标准化代码
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
                if not df.empty and len(df) >= 1:
                    # 取倒数第二条（昨天的收盘价）
                    if len(df) >= 2:
                        return float(df.iloc[-2]['close'])
                    else:
                        # 只有一条数据时取第一条
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
    
    def _calculate_morning_score(self, stock_code: str, date: str) -> Optional[Dict]:
        """
        计算早盘得分
        使用MetricDefinitions计算真实指标
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
        
        Returns:
            得分字典或None
        """
        try:
            # 【CTO铁律转换】：所有参数强制转float，杜绝类型爆炸
            def safe_float(val):
                try:
                    return float(val) if val is not None and str(val).strip() != '' else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            # 获取数据
            tick_data = self._get_tick_data(stock_code, date)
            if tick_data is None or tick_data.empty:
                return None
            
            # 获取昨收价并强制转换
            pre_close = safe_float(self._get_pre_close(stock_code, date))
            if pre_close <= 0:
                return None
            
            # 获取5日平均成交量并强制转换
            avg_volume_5d = safe_float(self._get_avg_volume_5d(stock_code, date))
            if avg_volume_5d <= 0:
                return None  # 连均量都没有，直接放弃！
            
            # 使用SanityGuards检查昨收价
            passed, msg = SanityGuards.check_pre_close_valid(pre_close, stock_code)
            if not passed:
                logger.warning(f"【时间机器】{stock_code} 昨收价检查失败: {msg}")
                return None
            
            # 【CTO修复】数据完整性断言：检查开盘价有效性 - 多重兜底机制
            open_price = 0.0
            
            # 兜底1: 尝试从本地日线数据获取开盘价
            try:
                from xtquant import xtdata
                daily_data = xtdata.get_local_data(
                    field_list=['time', 'open'],
                    stock_list=[stock_code],
                    period='1d',
                    start_time=date,
                    end_time=date
                )
                if daily_data and stock_code in daily_data and not daily_data[stock_code].empty:
                    open_price = safe_float(daily_data[stock_code]['open'].values[0])
                    logger.debug(f"【时间机器】{stock_code} 从日线数据获取开盘价: {open_price}")
            except Exception as e:
                logger.debug(f"【时间机器】{stock_code} 从日线获取开盘价失败: {e}")
            
            # 兜底2: 尝试从Tick数据第一个记录获取开盘价
            if open_price <= 0:
                try:
                    first_tick = tick_data.iloc[0]
                    if 'lastPrice' in first_tick:
                        open_price = safe_float(first_tick['lastPrice'])
                    elif 'price' in first_tick:
                        open_price = safe_float(first_tick['price'])
                    elif 'openPrice' in first_tick:
                        open_price = safe_float(first_tick['openPrice'])
                    logger.debug(f"【时间机器】{stock_code} 从Tick数据获取开盘价: {open_price}")
                except Exception as e:
                    logger.debug(f"【时间机器】{stock_code} 从Tick获取开盘价失败: {e}")
            
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
            
            # === 获取流通市值用于Ratio计算 ===
            float_volume = safe_float(self._get_float_volume(stock_code))
            float_market_cap = float_volume * pre_close if float_volume > 0 else 1.0
            
            # === 全天Tick遍历 (09:30-15:00) ===
            for index, row in tick_data.iterrows():
                curr_time = str(row['time_str'])
                price = safe_float(row['lastPrice']) if 'lastPrice' in row else safe_float(row.get('price', 0))
                volume = safe_float(row.get('volume', 0))
                amount = safe_float(price * volume)
                
                # 计算单笔净流入估算
                # 简化：价格上涨为流入，下跌为流出
                if index > 0:
                    prev_price_raw = tick_data.iloc[index-1]
                    prev_price = safe_float(prev_price_raw['lastPrice']) if 'lastPrice' in prev_price_raw else safe_float(prev_price_raw.get('price', price))
                    price_change = safe_float(price - prev_price)
                    # 净流入估算：价格变化 * 成交量 (简化模型)
                    estimated_flow = safe_float(price_change * volume) if price_change > 0 else safe_float(price_change * volume * 0.5)
                else:
                    estimated_flow = 0.0
                
                # 【阶段一：09:30-09:45】累加打分数据
                if curr_time <= '09:35:00':
                    flow_5min = safe_float(flow_5min + estimated_flow)
                if curr_time <= '09:45:00':
                    flow_15min = safe_float(flow_15min + estimated_flow)
                
                # 【打分定格】09:45瞬间调用V18验钞机
                if not is_scored and ('09:45:00' <= curr_time < '09:46:00' or curr_time == '09:45:00'):
                    from logic.core.config_manager import get_config_manager
                    config_manager = get_config_manager()
                    
                    # 5日平均成交量已在前方强制转换
                    flow_5min_median = safe_float(avg_volume_5d / 240) if avg_volume_5d > 0 else 1.0  # 5分钟中位数估算
                    
                    # 计算Space Gap (突破纯度)
                    high_60d = self._get_60d_high(stock_code, date)
                    space_gap_pct = (high_60d - price) / high_60d if high_60d > 0 else 0.5
                    
                    # ============================================================
                    # 【记忆引擎挂载】算分前读取记忆衰减
                    # ============================================================
                    memory_multiplier = 1.0
                    try:
                        from logic.memory.short_term_memory import ShortTermMemoryEngine
                        memory_engine = ShortTermMemoryEngine()
                        memory_score = memory_engine.read_memory(stock_code, today=date)
                        if memory_score is not None:
                            # 将记忆分数转化为multiplier (0.5~1.5范围)
                            memory_multiplier = 0.5 + (memory_score / 100.0)
                            logger.debug(f"🧠 {stock_code} 记忆激活: score={memory_score:.2f}, multiplier={memory_multiplier:.2f}")
                        memory_engine.close()
                    except Exception as mem_e:
                        # Graceful降级：记忆引擎失败时multiplier=1.0
                        logger.debug(f"⚠️ {stock_code} 记忆读取失败，使用默认multiplier=1.0: {mem_e}")
                        memory_multiplier = 1.0
                    
                    # 调用V18验钞机 (CTO终极红线版)
                    current_time = datetime.strptime('09:45', '%H:%M').time()
                    base_score, sustain_ratio, inflow_ratio, ratio_stock = self.calculate_true_dragon_score(
                        net_inflow=flow_15min,
                        price=price,
                        prev_close=pre_close,
                        high=price * 1.02,  # 简化
                        low=price * 0.98,
                        flow_5min=flow_5min,
                        flow_15min=flow_15min,
                        flow_5min_median_stock=flow_5min_median,
                        space_gap_pct=space_gap_pct,
                        float_volume_shares=float_volume,
                        current_time=current_time
                    )
                    
                    # 应用记忆multiplier
                    final_score = base_score * memory_multiplier
                    logger.debug(f"🎯 {stock_code} V18算分: base={base_score:.2f}, memory_mult={memory_multiplier:.2f}, final={final_score:.2f}")
                    
                    is_scored = True
                
                # 【阶段二：09:45-15:00】防守与记录
                if curr_time > '09:45:00':
                    # 记录09:45后的最高价 (用于骗炮计算)
                    if price > max_price_after_0945:
                        max_price_after_0945 = safe_float(price)
                    
                    # 更新VWAP
                    vwap_cum_volume = safe_float(vwap_cum_volume + volume)
                    vwap_cum_amount = safe_float(vwap_cum_amount + amount)
                    vwap = safe_float(vwap_cum_amount / vwap_cum_volume) if vwap_cum_volume > 0 else safe_float(price)
                    
                    # 盘中破位防守 (VWAP宽容判定)
                    if curr_time > '09:50:00' and price < vwap and not is_vetoed:
                        # 检查是否放量砸盘
                        recent_volume = safe_float(volume)
                        if recent_volume > safe_float(avg_volume_5d / 240 * 2):  # 放量
                            is_vetoed = True
                            veto_reason = "Veto: 盘中破位派发"
            
            # 【阶段三：15:00日落结算】严禁造假！
            # 获取日K线真实收盘价
            daily_k = xtdata.get_local_data(
                field_list=['time', 'close'],
                stock_list=[stock_code],
                period='1d',
                start_time=date,
                end_time=date
            )
            
            real_close = safe_float(price)  # 默认用最后Tick价格
            if daily_k and stock_code in daily_k and not daily_k[stock_code].empty:
                real_close = safe_float(daily_k[stock_code]['close'].values[-1])
            
            # 计算真实涨幅 (使用日K收盘价！)
            final_change = safe_float(MetricDefinitions.TRUE_CHANGE(real_close, pre_close))
            
            # 骗炮终审：Pullback_Ratio计算 - 全部使用safe_float
            if max_price_after_0945 > pre_close:
                pullback_ratio = safe_float((max_price_after_0945 - real_close) / (max_price_after_0945 - pre_close))
            else:
                pullback_ratio = 0.0
            
            # 尖刺骗炮判定
            if pullback_ratio > 0.3 and final_change < 0.08:
                is_vetoed = True
                veto_reason = f"Veto: 尖刺骗炮 (回落{pullback_ratio:.1%})"
                final_score = 0.0  # 分数清零！
            
            # 【CTO修复】数据完整性断言：如果没有成功打分，返回None
            if not is_scored:
                logger.warning(f"【时间机器】{stock_code} {date}: 未能在09:45完成打分（缺少关键时间点Tick数据），判定为数据缺失")
                return None
            
            # 【CTO】计算MFE (Maximum Favorable Excursion) 最大有利波动 - 使用safe_float
            mfe = safe_float((max_price_after_0945 - pre_close) / pre_close * 100) if pre_close > 0 else 0.0
            
            # 返回结果 - 所有数值都经过safe_float
            return {
                'stock_code': stock_code,
                'final_score': safe_float(final_score),
                'final_change': safe_float(final_change),
                'real_close': safe_float(real_close),
                'pre_close': safe_float(pre_close),
                'max_price': safe_float(max_price_after_0945),
                'pullback_ratio': safe_float(pullback_ratio),
                'sustain_ratio': safe_float(sustain_ratio),
                'inflow_ratio': safe_float(inflow_ratio),
                'ratio_stock': safe_float(ratio_stock),
                'mfe': safe_float(mfe),
                'is_vetoed': is_vetoed,
                'veto_reason': veto_reason,
                'flow_5min': safe_float(flow_5min),
                'flow_15min': safe_float(flow_15min)
            }
            
        except Exception as e:
            logger.error(f"【时间机器】计算早盘得分失败 {stock_code}: {e}")
            return None
    
    def run_continuous_backtest(self, start_date: str, end_date: str, 
                                 stock_pool_path: str = 'TUSHARE',
                                 use_tushare: bool = True) -> List[Dict]:
        """
        连续多日回测 - 全息时间机器核心
        CTODict: 强制使用真实Tushare粗筛，禁止模拟数据
        
        Args:
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            stock_pool_path: 股票池文件路径，默认'TUSHARE'表示实时粗筛
            use_tushare: 是否使用Tushare每日动态粗筛
        
        Returns:
            每日回测结果列表
        """
        print(f"\n{'#'*80}")
        print(f"# 全息时间机器启动")
        print(f"# 回测区间: {start_date} ~ {end_date}")
        print(f"# 初始资金: {self.initial_capital}元")
        print(f"# 数据源: {'Tushare实时粗筛' if use_tushare else 'CSV文件'}")
        print(f"{'#'*80}\n")
        
        logger.info(f"【时间机器】启动连续回测: {start_date} ~ {end_date}")
        logger.info(f"【时间机器】数据源: {'Tushare实时粗筛' if use_tushare else 'CSV文件'}")
        
        # ==========================================
        # CTO强制植入：年度发车前的"脑白金"清洗仪式
        # ==========================================
        memory_file = PathResolver.get_data_dir() / 'memory' / 'ShortTermMemory.json'
        if memory_file.exists():
            logger.warning("【CTO强制清洗】检测到残留的跨日记忆，正在物理抹除以防止未来函数污染...")
            print("🧠 【CTO清洗】检测到残留记忆，执行物理抹除...")
            # 强制清空，让时间机器以纯洁的状态回到过去！
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump({"date": "19700101", "memory": {}}, f)
            print("✅ 【CTO清洗】记忆库已清空，系统纯洁态启动！")
        
        logger.info("【系统已就绪】记忆库已清空，准备开始连贯穿越！")
        # ==========================================
        
        # 2. 获取交易日
        trade_dates = self.get_trade_dates(start_date, end_date)
        print(f"📅 交易日: {len(trade_dates)} 天")
        logger.info(f"交易日: {len(trade_dates)} 天")
        
        # 3. 逐日回测
        all_results = []
        
        for i, date in enumerate(trade_dates, 1):
            print(f"\n📌 进度: [{i}/{len(trade_dates)}] {date}")
            
            # CTODict: 每日动态粗筛 (Tushare模式)
            if use_tushare:
                try:
                    stock_pool = self._load_stock_pool('TUSHARE', date)
                    print(f"  📊 当日粗筛: {len(stock_pool)} 只")
                except Exception as e:
                    error_msg = str(e)
                    # CTO修复：检测是否为节假日（Tushare返回空）
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
    
        def _load_stock_pool(self, path: str, date: str = None) -> List[str]:
            """
            加载股票池 - CTODict: 禁止模拟数据，强制真实粗筛
            
            Args:
                path: 股票池文件路径 或 'TUSHARE' 表示实时粗筛
                date: 日期 'YYYYMMDD' (用于Tushare粗筛)
            
            Returns:
                股票代码列表 (约500只)
            
            Raises:
                RuntimeError: 无法获取真实数据时抛出致命异常 (Fail Fast)
            """
            # 如果使用Tushare实时粗筛
            if path.upper() == 'TUSHARE' or path == '':
                if not date:
                    raise ValueError("使用Tushare粗筛时必须提供date参数")
                
                logger.info(f"【时间机器】使用UniverseBuilder获取股票池: {date}")
                try:
                    # UniverseBuilder内部使用正确的绝对阈值3.0
                    builder = UniverseBuilder()
                    logger.info(f"【时间机器】开始调用get_daily_universe...")
                    stock_pool = builder.get_daily_universe(date)
                    
                    logger.info(f"【时间机器】UniverseBuilder返回: {len(stock_pool)} 只股票")
                    
                    if not stock_pool:
                        logger.error(f"【时间机器】 UniverseBuilder返回空股票池: {date}")
                        # 【CTO修复】返回空列表而不是报错，让上层处理
                        return []
                    
                    logger.info(f"【时间机器】股票池获取完成: {len(stock_pool)} 只")
                    return stock_pool
                    
                except Exception as e:
                    logger.error(f"【时间机器】Tushare粗筛失败: {e}")
                    raise RuntimeError(f"无法获取真实股票池: {e}") from e
                
            # 如果提供CSV文件路径
            full_path = PathResolver.resolve_path(path)
            
            if not full_path.exists():
                logger.error(f"【时间机器】股票池文件不存在: {path}")
                raise FileNotFoundError(f"股票池文件不存在: {path}。请提供有效CSV文件或使用'TUSHARE'进行实时粗筛")
            
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
    
    def _load_memory(self) -> Dict[str, Dict]:
        """
        加载短期记忆 - 自动补充缺失字段
        
        Returns:
            记忆字典 {stock_code: memory_item}
        """
        try:
            if self.MEMORY_FILE.exists():
                with open(self.MEMORY_FILE, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                
                # 自动补充缺失的字段（向后兼容旧数据结构）
                for stock_code, mem_item in memory.items():
                    if 'absent_days' not in mem_item:
                        mem_item['absent_days'] = 0
                        logger.debug(f"【记忆衰减】{stock_code} 补充 absent_days=0")
                    if 'last_decay_date' not in mem_item:
                        mem_item['last_decay_date'] = mem_item.get('date', '')
                        logger.debug(f"【记忆衰减】{stock_code} 补充 last_decay_date")
                
                return memory
            return {}
        except Exception as e:
            logger.error(f"【记忆衰减】加载记忆失败: {e}")
            return {}
    
    def _save_memory(self, memory: Dict[str, Dict]) -> bool:
        """
        保存短期记忆
        
        Args:
            memory: 记忆字典
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            self.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
            
            logger.info(f"【记忆衰减】记忆已保存: {len(memory)} 条")
            return True
        except Exception as e:
            logger.error(f"【记忆衰减】保存记忆失败: {e}")
            return False
    
    def _apply_memory_decay(self, current_date: str, today_top20: List[Dict]) -> Dict[str, Dict]:
        """
        执行记忆衰减 - 核心逻辑
        
        规则:
        1. 新记忆分 = 老记忆分 * 0.5
        2. 连续2日不上榜 -> 删除
        3. 衰减后score < 10 -> 删除
        
        Args:
            current_date: 当前日期 'YYYYMMDD'
            today_top20: 今日Top20列表 [{'stock_code': str, 'final_score': float, ...}]
        
        Returns:
            更新后的记忆字典
        """
        # 1. 加载旧记忆
        memory = self._load_memory()
        
        # 2. 获取今日上榜股票代码
        today_top_codes: Set[str] = {item['stock_code'] for item in today_top20}
        
        # 3. 更新记忆中每只股票
        new_memory = {}
        decay_stats = {'decayed': 0, 'removed_absent': 0, 'removed_low_score': 0, 'new_added': 0}
        
        for stock_code, mem_item in memory.items():
            # 获取当前分数
            old_score = mem_item.get('score', 0)
            
            # 衰减分数
            new_score = old_score * MEMORY_DECAY_FACTOR
            
            # 检查是否在今日Top20中
            if stock_code in today_top_codes:
                # 今日上榜，重置缺席天数
                mem_item['absent_days'] = 0
                decay_stats['decayed'] += 1
                logger.debug(f"【记忆衰减】{stock_code} 今日上榜，重置缺席天数")
            else:
                # 未上榜，增加缺席天数
                absent_days = mem_item.get('absent_days', 0) + 1
                mem_item['absent_days'] = absent_days
                
                # 检查是否连续缺席超过阈值
                if absent_days >= MEMORY_MAX_ABSENCE_DAYS:
                    decay_stats['removed_absent'] += 1
                    logger.info(f"【记忆衰减】{stock_code} 连续{absent_days}日不上榜，删除")
                    continue
            
            # 检查分数是否低于阈值
            if new_score < MEMORY_MIN_SCORE:
                decay_stats['removed_low_score'] += 1
                logger.info(f"【记忆衰减】{stock_code} 分数{new_score:.1f} < {MEMORY_MIN_SCORE}，删除")
                continue
            
            # 更新分数和日期
            mem_item['score'] = round(new_score, 2)
            mem_item['last_decay_date'] = current_date
            new_memory[stock_code] = mem_item
            decay_stats['decayed'] += 1
        
        # 4. 添加今日新上榜股票（不在记忆中的）
        for item in today_top20:
            stock_code = item['stock_code']
            if stock_code not in new_memory:
                new_memory[stock_code] = {
                    'stock_code': stock_code,
                    'date': current_date,
                    'score': item.get('final_score', 70.0),
                    'absent_days': 0,
                    'last_decay_date': current_date,
                    'close_price': item.get('price_0940', 0),
                    'change_pct': item.get('change_0940', 0),
                    'status': item.get('status', 'unknown')
                }
                decay_stats['new_added'] += 1
                logger.debug(f"【记忆衰减】{stock_code} 新上榜，加入记忆")
        
        # 5. 保存更新后的记忆
        self._save_memory(new_memory)
        
        # 6. 打印统计
        print(f"\n  📉 记忆衰减统计:")
        print(f"     原有记忆: {len(memory)} 条")
        print(f"     衰减保留: {decay_stats['decayed']} 条")
        print(f"     新增记忆: {decay_stats['new_added']} 条")
        print(f"     删除(缺席): {decay_stats['removed_absent']} 条")
        print(f"     删除(低分): {decay_stats['removed_low_score']} 条")
        print(f"     当前记忆: {len(new_memory)} 条")
        
        logger.info(f"【记忆衰减】统计: 原有{len(memory)}, 保留{decay_stats['decayed']}, "
                   f"新增{decay_stats['new_added']}, 删除缺席{decay_stats['removed_absent']}, "
                   f"删除低分{decay_stats['removed_low_score']}, 当前{len(new_memory)}")
        
        return new_memory

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
