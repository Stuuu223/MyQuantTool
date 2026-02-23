"""
全息时间机器引擎 - 连续多日回测
自动执行连续N个交易日的回测，验证策略稳定性

Author: iFlow CLI
Date: 2026-02-23
Version: 1.1.0 - 添加记忆衰减机制
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
    
    def run_daily_backtest(self, date: str, stock_pool: List[str]) -> Dict:
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
            print(f"  📥 向VIP节点请求 {date} Tick数据并阻塞等待...")
            from logic.data_providers.qmt_manager import QmtDataManager
            downloader = QmtDataManager()
            download_results = downloader.download_tick_data(
                stock_list=stock_pool,  # CTO修复：下载全部88只
                trade_date=date,
                use_vip=True,
                check_existing=True
            )
            success_downloads = sum(1 for r in download_results.values() if r.success)
            print(f"  ✅ 下载完成: {success_downloads}/{len(stock_pool)} 只")
            
            # 2. 获取当日股票池数据
            print(f"  📊 获取 {len(stock_pool)} 只股票数据...")
            
            valid_stocks = []
            for stock in stock_pool:  # CTO修复：检查全部88只
                try:
                    # 检查数据完整性
                    tick_data = self._get_tick_data(stock, date)
                    if tick_data is not None and len(tick_data) > 100:
                        valid_stocks.append(stock)
                        logger.debug(f"  ✓ {stock}: {len(tick_data)} 条Tick数据")
                except Exception as e:
                    error_msg = f"{stock}: {str(e)}"
                    daily_result['errors'].append(error_msg)
                    logger.warning(f"  ⚠️ {error_msg}")
            
            daily_result['valid_stocks'] = len(valid_stocks)
            print(f"  ✅ 有效数据: {len(valid_stocks)} 只")
            
            if len(valid_stocks) < 5:
                daily_result['status'] = 'insufficient_data'
                logger.warning(f"  ⚠️ 数据不足: 仅 {len(valid_stocks)} 只有效数据")
                return daily_result
            
            # 2. 计算09:40指标（早盘5分钟+5分钟）
            print(f"  🧮 计算早盘指标...")
            
            stock_scores = []
            for stock in valid_stocks:
                try:
                    score = self._calculate_morning_score(stock, date)
                    if score:
                        stock_scores.append(score)
                except Exception as e:
                    error_msg = f"{stock}计算错误: {str(e)}"
                    daily_result['errors'].append(error_msg)
                    logger.warning(f"  ⚠️ {error_msg}")
            
            # 3. 排序选出Top 20 (CTODict: 扩容至Top 20观察梯度)
            stock_scores.sort(key=lambda x: x['final_score'], reverse=True)
            top20 = stock_scores[:20]
            
            daily_result['top20'] = top20
            daily_result['status'] = 'success'
            
            # 5. 执行记忆衰减
            self._apply_memory_decay(date, top20)
            
            # 6. 打印结果 (仅显示前5，但保存Top 20)
            print(f"\n  🏆 当日Top 20 (显示前5):")
            for i, item in enumerate(top20[:5], 1):
                print(f"    {i}. {item['stock_code']} - 得分: {item['final_score']:.2f}")
                print(f"       09:40涨幅: {item.get('change_0940', 0):.2f}%, 状态: {item.get('status', 'N/A')}")
            if len(top20) > 5:
                print(f"    ... 共 {len(top20)} 只 (详见JSON)")
            
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
        获取Tick数据
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
        
        Returns:
            DataFrame包含time, price等字段，或None
        """
        try:
            from xtquant import xtdata
            
            # 标准化代码
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 获取本地数据
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if data and normalized_code in data:
                df = data[normalized_code]
                if not df.empty:
                    # 转换时间格式
                    if 'time' in df.columns:
                        df['time'] = df['time'].apply(
                            lambda x: datetime.fromtimestamp(x/1000).strftime('%H:%M:%S') 
                            if isinstance(x, (int, float)) else str(x)
                        )
                    # 重命名价格列为标准格式
                    if 'lastPrice' in df.columns:
                        df = df.rename(columns={'lastPrice': 'price'})
                    return df
            
            return None
            
        except Exception as e:
            logger.warning(f"获取Tick数据失败 {stock_code}: {e}")
            return None
    
    def _get_pre_close(self, stock_code: str, date: str) -> float:
        """
        获取昨收价
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
        
        Returns:
            昨收价，失败返回0
        """
        try:
            from xtquant import xtdata
            
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
            # 获取数据
            tick_data = self._get_tick_data(stock_code, date)
            
            if tick_data is None or tick_data.empty or len(tick_data) < 10:
                return None
            
            # 获取昨收价
            pre_close = self._get_pre_close(stock_code, date)
            if pre_close <= 0:
                return None
            
            # 使用SanityGuards检查昨收价
            passed, msg = SanityGuards.check_pre_close_valid(pre_close, stock_code)
            if not passed:
                logger.warning(f"【时间机器】{stock_code} 昨收价检查失败: {msg}")
                return None
            
            # CTO修复：正确处理时间戳获取09:40价格
            # 确保time列是字符串格式 HH:MM:SS
            if pd.api.types.is_numeric_dtype(tick_data['time']):
                # 如果是数值（毫秒时间戳），转换
                tick_data['time_str'] = pd.to_datetime(tick_data['time'], unit='ms') + pd.Timedelta(hours=8)
                tick_data['time_str'] = tick_data['time_str'].dt.strftime('%H:%M:%S')
            else:
                tick_data['time_str'] = tick_data['time'].astype(str)
            
            # 截取早盘数据
            tick_0940 = tick_data[tick_data['time_str'] <= '09:40:00']
            if tick_0940.empty:
                logger.warning(f"【时间机器】{stock_code} 09:40前无数据")
                return None
            
            price_0940 = float(tick_0940.iloc[-1]['price'])
            
            # 使用MetricDefinitions计算真实涨幅
            try:
                change_pct = MetricDefinitions.TRUE_CHANGE(price_0940, pre_close)
            except (ValueError, TypeError) as e:
                logger.warning(f"【时间机器】{stock_code} 涨幅计算失败: {e}")
                return None
            
            # Sanity Check - 涨幅合理性检查
            passed, msg = SanityGuards.check_price_change(change_pct, stock_code)
            if not passed:
                logger.warning(f"【时间机器】{stock_code} 涨幅检查失败: {msg}")
                return None
            
            # 简单评分（后续替换为完整V18评分）
            base_score = min(abs(change_pct) * 5, 100)  # 涨幅越大分越高
            
            # 确定状态
            if change_pct > 5:
                status = 'strong'
            elif change_pct > 2:
                status = 'normal'
            else:
                status = 'weak'
            
            return {
                'stock_code': stock_code,
                'final_score': base_score,
                'change_0940': change_pct,
                'price_0940': price_0940,
                'pre_close': pre_close,
                'status': status
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
                    logger.error(f"【时间机器】{date} 粗筛失败: {e}")
                    print(f"  ❌ {date} 粗筛失败: {e}")
                    # 记录失败并继续下一日
                    all_results.append({
                        'date': date,
                        'status': 'coarse_filter_failed',
                        'error': str(e)
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
            
            logger.info(f"【时间机器】使用Tushare实时粗筛: {date}")
            try:
                builder = UniverseBuilder()
                stock_pool = builder.get_daily_universe(date)
                
                if not stock_pool:
                    raise RuntimeError(f"Tushare粗筛返回空股票池: {date}")
                
                logger.info(f"【时间机器】Tushare粗筛完成: {len(stock_pool)} 只")
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
