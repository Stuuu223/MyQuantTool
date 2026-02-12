"""
一体化股票分析工具 (Unified Stock Analyzer)

功能:
1. 自动判断调用场景（开盘/午休/收盘/周末）
2. 智能选择分析模式（实时/复盘/深度）
3. 三层数据降级策略（QMT → AkShare → 历史）
4. 双格式输出（JSON + TXT）
5. 时间序列日志（CSV）
6. 统一命令行接口

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-03

使用示例:
    # 自动判断场景
    python tools/stock_analyzer.py 300997
    
    # 强制指定模式
    python tools/stock_analyzer.py 300997 --mode realtime
    python tools/stock_analyzer.py 300997 --mode historical
    
    # 带持仓信息
    python tools/stock_analyzer.py 300997 --position 1.0 --entry-price 26.50
    
    # 指定输出格式
    python tools/stock_analyzer.py 300997 --format txt
    python tools/stock_analyzer.py 300997 --format json
    python tools/stock_analyzer.py 300997 --format both
"""

import sys
import os
import json
import csv
from datetime import datetime
from typing import Dict, Any, Literal

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.monitors.intraday_monitor import IntraDayMonitor
from tools.intraday_decision import IntraDayDecisionTool
from tools.enhanced_stock_analyzer import EnhancedStockAnalyzer


class UnifiedStockAnalyzer:
    """一体化股票分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.monitor = IntraDayMonitor()
        self.decision_tool = IntraDayDecisionTool()
        self.historical_analyzer = EnhancedStockAnalyzer()
        
    def analyze(
        self, 
        stock_code: str,
        mode: Literal['auto', 'realtime', 'historical'] = 'auto',
        position: float = 0.0,
        entry_price: float | None = None,
        output_format: Literal['json', 'txt', 'both'] = 'both'
    ) -> Dict[str, Any]:
        """
        智能分析（自动判断场景）
        
        Args:
            stock_code: 股票代码
            mode: 分析模式（auto=自动判断，realtime=实时，historical=历史）
            position: 当前持仓比例（0-1）
            entry_price: 建仓价格
            output_format: 输出格式（json/txt/both）
        
        Returns:
            统一分析结果
        """
        # 获取交易阶段
        phase = self.monitor.get_trading_phase()
        
        # 自动判断模式
        if mode == 'auto':
            if phase in ['MORNING', 'AFTERNOON']:
                mode = 'realtime'
            elif phase == 'LUNCH_BREAK':
                mode = 'lunchtime'
            elif phase == 'AFTER_HOURS':
                mode = 'after_hours'
            elif phase == 'WEEKEND':
                mode = 'weekend'
        
        # 根据模式调用不同分析
        if mode == 'realtime':
            result = self._realtime_analysis(stock_code, position, entry_price)
        elif mode == 'lunchtime':
            result = self._lunchtime_analysis(stock_code, position, entry_price)
        elif mode == 'after_hours':
            result = self._after_hours_analysis(stock_code, position, entry_price)
        elif mode == 'weekend':
            result = self._weekend_analysis(stock_code)
        elif mode == 'historical':
            result = self._historical_analysis(stock_code)
        else:
            result = {
                'success': False,
                'error': f'未知分析模式: {mode}'
            }
        
        # 输出结果
        if result['success']:
            self._output_result(stock_code, result, output_format)
            self._log_decision(stock_code, result)
        
        return result
    
    def _realtime_analysis(
        self, 
        stock_code: str, 
        position: float, 
        entry_price: float | None
    ) -> Dict[str, Any]:
        """
        实时分析（开盘中）- 三层数据融合
        
        策略:
        1. Layer 1: 获取实时快照（QMT/AkShare）
        2. Layer 2: 获取今日分时走势（分钟K线）
        3. Layer 3: 加载历史分析（90天数据）
        4. 综合三层数据生成智能决策
        5. 输出三层数据融合报告
        """
        print(f"\n{'='*60}")
        print(f"⏰ 盘中实时分析（三层数据融合） - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 查找昨日分析文件
        yesterday_file = self._find_latest_analysis(stock_code)
        
        # 生成基础决策（获取 Layer 1 数据）
        decision = self.decision_tool.make_decision(
            stock_code=stock_code,
            yesterday_file=yesterday_file,
            current_position=position,
            entry_price=entry_price
        )
        
        if not decision:
            return {
                'success': False,
                'error': '决策生成失败',
                'mode': 'realtime'
            }
        
        # Layer 1: 实时快照
        today_data = decision.get('data', {}).get('today', {})
        realtime_snapshot = {
            'data_source': today_data.get('data_source', 'UNKNOWN'),
            'data_freshness': today_data.get('data_freshness', 'UNKNOWN'),
            'price': today_data.get('price', 0),
            'pct_change': today_data.get('pct_change', 0),
            'bid_ask_pressure': today_data.get('bid_ask_pressure', 0),
            'signal': today_data.get('signal', '')
        }
        
        # Layer 2: 今日分时走势
        intraday_trend = self._get_intraday_trend(stock_code, minutes_count=120)
        if intraday_trend['success']:
            intraday_trend['pattern'] = self._analyze_intraday_pattern(intraday_trend['trend_data'])
        
        # Layer 3: 历史分析
        historical_analysis = {}
        if yesterday_file and os.path.exists(yesterday_file):
            try:
                with open(yesterday_file, 'r', encoding='utf-8') as f:
                    historical_analysis = json.load(f)
            except:
                pass
        
        # 综合三层数据生成智能决策
        integrated_decision = self._make_integrated_decision(
            realtime_snapshot=realtime_snapshot,
            intraday_trend=intraday_trend,
            historical_analysis=historical_analysis,
            position=position,
            entry_price=entry_price
        )
        
        result = {
            'success': True,
            'mode': 'realtime',
            'phase': 'TRADING',
            'stock_code': stock_code,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'layer1_realtime': realtime_snapshot,
            'layer2_intraday': intraday_trend,
            'layer3_historical': historical_analysis,
            'integrated_decision': integrated_decision,
            'position_info': {
                'current_position': position,
                'entry_price': entry_price
            }
        }
        
        # 打印三层数据融合报告
        self._print_integrated_report(
            stock_code=stock_code,
            realtime_snapshot=realtime_snapshot,
            intraday_trend=intraday_trend,
            historical_analysis=historical_analysis,
            decision=integrated_decision
        )
        
        return result
    
    def _lunchtime_analysis(
        self, 
        stock_code: str, 
        position: float, 
        entry_price: float | None
    ) -> Dict[str, Any]:
        """
        午休分析（11:30-13:00）
        
        策略:
        1. 获取上午收盘数据（AkShare）
        2. 分析上午表现
        3. 预测下午走势
        4. 调整持仓策略
        """
        print(f"\n{'='*60}")
        print(f"🌙 午休复盘分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 获取上午数据
        snapshot = self.monitor.get_intraday_snapshot(stock_code)
        
        if not snapshot['success']:
            return {
                'success': False,
                'error': snapshot['error'],
                'mode': 'lunchtime'
            }
        
        # 查找昨日分析
        yesterday_file = self._find_latest_analysis(stock_code)
        
        # 生成决策
        decision = self.decision_tool.make_decision(
            stock_code=stock_code,
            yesterday_file=yesterday_file,
            current_position=position,
            entry_price=entry_price
        )
        
        result = {
            'success': True,
            'mode': 'lunchtime',
            'phase': 'LUNCH_BREAK',
            'stock_code': stock_code,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'morning_summary': {
                'data_freshness': 'DELAYED',
                'price': snapshot.get('price', 0),
                'pct_change': snapshot.get('pct_change', 0),
                'morning_high': snapshot.get('high', 0),
                'morning_low': snapshot.get('low', 0),
                'signal': snapshot.get('signal', '')
            },
            'afternoon_strategy': {
                'action': decision['decision'],
                'confidence': decision['confidence'],
                'reason': decision['reason']
            },
            'risk_assessment': decision.get('risk_assessment', {})
        }
        
        # 打印报告
        self._print_lunchtime_report(result)
        
        return result
    
    def _after_hours_analysis(
        self,
        stock_code: str,
        position: float,
        entry_price: float | None
    ) -> Dict[str, Any]:
        """
        收盘后分析（15:00-次日09:30）

        策略（增强版）:
        1. 生成90天历史分析（优先）
        2. 从历史分析提取今日数据（不尝试获取五档）
        3. 检查数据新鲜度
        4. 预测明日走势
        5. 输出明日策略
        """
        print(f"\n{'='*60}")
        print(f"🌆 收盘后深度分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 生成90天历史分析（优先）
        print("正在生成90天历史分析（增强版）...")
        historical_result = self.historical_analyzer.comprehensive_analysis(stock_code, days=90, output_all_data=True)

        # 从历史分析提取今日数据
        today_data = {
            'data_freshness': 'HISTORICAL',
            'close': 0,
            'pct_change': 0,
            'high': 0,
            'low': 0
        }

        # 尝试从历史分析结果中提取数据
        if isinstance(historical_result, str):
            # 如果返回的是字符串（报告），尝试解析
            print("⚠️ 历史分析返回字符串，无法提取今日数据")
        else:
            # 尝试从字典中提取数据
            if isinstance(historical_result, dict):
                today_data = self._extract_today_from_history(historical_result)

        # 🔧 修复：收盘后不尝试获取五档（QMT/AkShare 实时快照），直接使用历史K线数据
        # 原因：收盘后（如20:55）QMT客户端可能已关闭，五档数据返回0
        if today_data['close'] == 0:
            print("⚠️ 历史分析无今日数据，尝试从 AkShare 获取当日K线...")
            today_data = self._get_today_kline_from_akshare(stock_code)

        # 🔧 新增：检查数据新鲜度
        freshness_warning = self._check_data_freshness(today_data)

        # 生成明日策略
        tomorrow_strategy = self._generate_tomorrow_strategy(
            historical_result if isinstance(historical_result, dict) else {},
            position,
            entry_price
        )

        result = {
            'success': True,
            'mode': 'after_hours',
            'phase': 'AFTER_HOURS',
            'stock_code': stock_code,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'historical_report': historical_result,
            'today_summary': today_data,
            'data_freshness_warning': freshness_warning,  # 🔧 新增
            'tomorrow_strategy': tomorrow_strategy,
            'output_file': None  # 收盘后分析不保存单独的JSON文件
        }

        # 打印报告
        self._print_after_hours_report(result)

        return result
    
    def _extract_today_from_history(self, historical_data: Dict) -> Dict[str, Any]:
        """
        从90天历史分析中提取今日数据

        优先级:
        1. QMT K线数据（最准确）
        2. 资金流向数据（次选）
        3. 返回空数据
        """
        today_data = {
            'data_freshness': 'HISTORICAL',
            'close': 0,
            'pct_change': 0,
            'high': 0,
            'low': 0
        }

        # 优先：QMT K线数据
        qmt_data = historical_data.get('qmt', {})
        if qmt_data and 'kline_1d' in qmt_data and qmt_data['kline_1d']:
            last_day = qmt_data['kline_1d'][-1]
            today_data.update({
                'close': last_day.get('close', 0),
                'pct_change': last_day.get('pct_change', 0),
                'high': last_day.get('high', 0),
                'low': last_day.get('low', 0),
                'data_freshness': 'QMT_KLINE'
            })
            print(f"✅ 从QMT K线提取今日数据: 收盘 {today_data['close']:.2f}")
            return today_data

        # 次选：资金流向数据（只有日期，没有价格）
        fund_flow = historical_data.get('fund_flow', {})
        if fund_flow and 'daily_data' in fund_flow and fund_flow['daily_data']:
            last_day = fund_flow['daily_data'][-1]
            print(f"⚠️ 资金流向数据无价格信息，日期: {last_day.get('date', 'N/A')}")

        print(f"❌ 历史分析中无今日数据")
        return today_data

    def _check_data_freshness(self, data: dict) -> str | None:
        """
        检查数据新鲜度（新增方法）

        Args:
            data: 数据字典

        Returns:
            警告信息（如果数据过期），否则返回 None
        """
        if not data:
            return None

        # 检查数据新鲜度标签
        freshness = data.get('data_freshness', '')
        if freshness == 'STALE':
            return f"⚠️ 数据已过期（来源: {data.get('data_source', 'N/A')}）"

        # 检查 K 线数据日期
        if freshness == 'QMT_KLINE':
            kline_date = data.get('date', '')
            if kline_date:
                current_date = datetime.now().strftime('%Y-%m-%d')
                if kline_date != current_date:
                    return f"⚠️ K线数据非当日（{kline_date} vs {current_date}）"

        # 检查价格是否有效
        if data.get('close', 0) == 0:
            return "⚠️ 收盘价格为0，数据可能无效"

        return None

    def _get_today_kline_from_akshare(self, stock_code: str) -> Dict[str, Any]:
        """
        从 AkShare 获取当日 K 线数据（新增方法）

        用途：收盘后分析，获取当日完整的 K 线数据

        Args:
            stock_code: 股票代码

        Returns:
            {
                'data_freshness': 'AKSHARE_DAILY',
                'close': float,
                'pct_change': float,
                'high': float,
                'low': float,
                'date': str
            }
        """
        today_data = {
            'data_freshness': 'AKSHARE_DAILY',
            'close': 0,
            'pct_change': 0,
            'high': 0,
            'low': 0,
            'date': ''
        }

        try:
            from datetime import timedelta
            import akshare as ak

            # 获取今日 K 线
            today = datetime.now()
            today_str = today.strftime('%Y%m%d')

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=today_str,
                end_date=today_str,
                adjust="qfq"
            )

            if df is not None and not df.empty:
                row = df.iloc[0]
                today_data.update({
                    'close': float(row['收盘']),
                    'pct_change': float(row['涨跌幅']),
                    'high': float(row['最高']),
                    'low': float(row['最低']),
                    'date': str(row['日期'])
                })
                print(f"✅ 从 AkShare 获取今日 K 线: 收盘 {today_data['close']:.2f}")
            else:
                print(f"⚠️ AkShare 今日 K 线数据为空，尝试获取最近1天...")
                # 备选：获取最近1天的数据
                yesterday = today - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y%m%d')

                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=yesterday_str,
                    end_date=yesterday_str,
                    adjust="qfq"
                )

                if df is not None and not df.empty:
                    row = df.iloc[0]
                    today_data.update({
                        'close': float(row['收盘']),
                        'pct_change': float(row['涨跌幅']),
                        'high': float(row['最高']),
                        'low': float(row['最低']),
                        'date': str(row['日期'])
                    })
                    print(f"✅ 从 AkShare 获取昨日 K 线: 收盘 {today_data['close']:.2f}")

        except Exception as e:
            print(f"❌ 从 AkShare 获取 K 线数据失败: {e}")

        return today_data

    def _weekend_analysis(self, stock_code: str) -> Dict[str, Any]:
        """
        周末深度分析
        
        策略:
        1. 90天历史分析
        2. 资金流向趋势
        3. 诱多风险评估
        4. 下周交易计划
        """
        print(f"\n{'='*60}")
        print(f"📊 周末深度分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 生成90天历史分析
        print("正在生成90天历史分析（增强版）...")
        historical_report = self.historical_analyzer.comprehensive_analysis(stock_code, days=90, output_all_data=True)
        
        result = {
            'success': True,
            'mode': 'weekend',
            'phase': 'WEEKEND',
            'stock_code': stock_code,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'historical_report': historical_report,
            'output_file': None  # 周末分析不保存单独的JSON文件
        }
        
        # 打印报告
        self._print_weekend_report(result)
        
        return result
    
    def _historical_analysis(self, stock_code: str) -> Dict[str, Any]:
        """
        历史分析（强制模式）
        
        用途: 手动触发90天分析
        """
        print(f"\n{'='*60}")
        print(f"📈 历史数据分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 生成90天历史分析
        historical_report = self.historical_analyzer.comprehensive_analysis(stock_code, days=90, output_all_data=True)
        
        return {
            'success': True,
            'mode': 'historical',
            'stock_code': stock_code,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'historical_report': historical_report,
            'output_file': None  # 历史分析不保存单独的JSON文件
        }
    
    def _get_intraday_trend(self, stock_code: str, minutes_count: int = 120) -> Dict[str, Any]:
        """
        获取今日分时走势（三层数据融合 Layer 2）
        
        Args:
            stock_code: 股票代码
            minutes_count: 获取的分钟数（默认120分钟=2小时）
        
        Returns:
            {
                'success': bool,
                'data_source': 'QMT' | 'AKSHARE',
                'trend_data': [...],  # 分钟K线数据
                'pattern': 'PUMP_AND_DUMP' | 'SUSTAINED_RISE' | 'NARROW_TRADING' | 'UNKNOWN',
                'high_price': 0.0,
                'low_price': 0.0,
                'volatility': 0.0
            }
        """
        result = {
            'success': False,
            'data_source': None,
            'trend_data': [],
            'pattern': 'UNKNOWN',
            'high_price': 0.0,
            'low_price': 0.0,
            'volatility': 0.0
        }
        
        try:
            from datetime import timedelta
            
            # 策略1: 尝试使用 AkShare 分钟线
            if self.monitor.akshare_available:
                df = self.monitor.ak.stock_zh_a_hist_min_em(
                    symbol=stock_code,
                    period='1',  # 1分钟
                    adjust='qfq',  # 前复权
                    start_date=(datetime.now() - timedelta(minutes=minutes_count)).strftime('%Y-%m-%d %H:%M:%S'),
                    end_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                
                if df is not None and not df.empty:
                    result['success'] = True
                    result['data_source'] = 'AKSHARE'
                    
                    # 转换为列表格式
                    for idx, row in df.iterrows():
                        result['trend_data'].append({
                            'time': row['时间'],
                            'open': float(row['开盘']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['收盘']),
                            'volume': int(row['成交量'])
                        })
                    
                    # 计算统计
                    if result['trend_data']:
                        result['high_price'] = max(d['high'] for d in result['trend_data'])
                        result['low_price'] = min(d['low'] for d in result['trend_data'])
                        result['volatility'] = (result['high_price'] - result['low_price']) / result['low_price'] * 100 if result['low_price'] > 0 else 0
                    return result
            
        except Exception as e:
            pass
        
        return result
    
    def _analyze_intraday_pattern(self, trend_data: list) -> str:
        """
        识别分时模式（三层数据融合 Layer 2）
        
        Args:
            trend_data: 分钟K线数据列表
        
        Returns:
            'PUMP_AND_DUMP' | 'SUSTAINED_RISE' | 'NARROW_TRADING' | 'UNKNOWN'
        """
        if not trend_data or len(trend_data) < 10:
            return 'UNKNOWN'
        
        # 计算关键指标
        prices = [d['close'] for d in trend_data]
        volumes = [d['volume'] for d in trend_data]
        
        first_price = prices[0]
        last_price = prices[-1]
        max_price = max(prices)
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        
        # 冲高回落判断
        if max_price > avg_price * 1.02 and last_price < avg_price * 0.99:
            return 'PUMP_AND_DUMP'
        
        # 持续拉升判断
        if prices[-1] > prices[0] * 1.01 and prices[-1] > prices[-5] * 1.005:
            return 'SUSTAINED_RISE'
        
        # 窄幅震荡判断
        if max_price < avg_price * 1.01 and min_price > avg_price * 0.99:
            return 'NARROW_TRADING'
        
        return 'UNKNOWN'
    
    def _make_integrated_decision(
        self,
        realtime_snapshot: Dict,
        intraday_trend: Dict,
        historical_analysis: Dict,
        position: float,
        entry_price: float | None
    ) -> Dict[str, Any]:
        """
        综合三层数据的智能决策引擎（三层数据融合 Layer 3）
        
        Args:
            realtime_snapshot: Layer 1 - 实时快照
            intraday_trend: Layer 2 - 今日分时走势
            historical_analysis: Layer 3 - 90天历史分析
            position: 当前持仓
            entry_price: 建仓价格
        
        Returns:
            {
                'decision': 'BUY' | 'SELL' | 'HOLD' | 'WAIT',
                'confidence': 0.0,
                'reason': '',
                'action': {...}
            }
        """
        decision = {
            'decision': 'WAIT',
            'confidence': 0.0,
            'reason': '',
            'action': {
                'type': 'WAIT',
                'target_position': position,
                'stop_loss': None,
                'stop_profit': None,
                'urgency': 'LOW'
            }
        }
        
        # 提取关键指标
        # Layer 1: 实时数据
        bid_ask_pressure = realtime_snapshot.get('bid_ask_pressure', 0)
        current_price = realtime_snapshot.get('price', 0)
        pct_change = realtime_snapshot.get('pct_change', 0)
        
        # Layer 2: 分时模式
        pattern = intraday_trend.get('pattern', 'UNKNOWN')
        
        # Layer 3: 历史数据
        trap_risk = historical_analysis.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
        capital_type = historical_analysis.get('capital_classification', {}).get('type', 'UNKNOWN')
        flow_5d_trend = historical_analysis.get('fund_flow', {}).get('trend', 'UNKNOWN')
        
        # 止损/止盈检查
        if entry_price and position > 0:
            profit_pct = (current_price - entry_price) / entry_price * 100
            if profit_pct <= -3.0:
                decision['decision'] = 'SELL'
                decision['confidence'] = 0.9
                decision['reason'] = f'触发止损：亏损{profit_pct:.2f}%'
                decision['action'] = {
                    'type': 'SELL',
                    'target_position': 0,
                    'stop_loss': entry_price * 0.97,
                    'stop_profit': None,
                    'urgency': 'HIGH'
                }
                return decision
            elif profit_pct >= 10.0:
                decision['decision'] = 'SELL'
                decision['confidence'] = 0.8
                decision['reason'] = f'触发止盈：盈利{profit_pct:.2f}%'
                decision['action'] = {
                    'type': 'SELL',
                    'target_position': 0,
                    'stop_loss': entry_price * 0.97,
                    'stop_profit': None,
                    'urgency': 'MEDIUM'
                }
                return decision
        
        # 高风险 + 冲高回落 → 减仓止损
        if trap_risk > 0.7 and pattern == 'PUMP_AND_DUMP':
            decision['decision'] = 'SELL'
            decision['confidence'] = 0.85
            decision['reason'] = '高风险+冲高回落，建议减仓止损'
            decision['action'] = {
                'type': 'SELL',
                'target_position': max(0, position - 0.5),
                'stop_loss': entry_price * 0.97 if entry_price else None,
                'stop_profit': None,
                'urgency': 'HIGH'
            }
            return decision
        
        # 游资 + 持续下跌 → 清仓离场
        if capital_type == 'HOT_MONEY' and pattern == 'SUSTAINED_FALL' and bid_ask_pressure < -0.5:
            decision['decision'] = 'SELL'
            decision['confidence'] = 0.8
            decision['reason'] = '游资+持续下跌，建议清仓离场'
            decision['action'] = {
                'type': 'SELL',
                'target_position': 0,
                'stop_loss': entry_price * 0.97 if entry_price else None,
                'stop_profit': None,
                'urgency': 'HIGH'
            }
            return decision
        
        # 低风险 + 持续拉升 + 买盘强 → 适度加仓
        if trap_risk < 0.3 and pattern == 'SUSTAINED_RISE' and bid_ask_pressure > 0.5:
            decision['decision'] = 'BUY'
            decision['confidence'] = 0.7
            decision['reason'] = '低风险+持续拉升+买盘强，可适度加仓'
            decision['action'] = {
                'type': 'BUY',
                'target_position': min(1.0, position + 0.2),
                'stop_loss': entry_price * 0.97 if entry_price else None,
                'stop_profit': entry_price * 1.1 if entry_price else None,
                'urgency': 'MEDIUM'
            }
            return decision
        
        # 震荡横盘 → 观望
        if pattern == 'NARROW_TRADING':
            decision['decision'] = 'WAIT'
            decision['confidence'] = 0.6
            decision['reason'] = '震荡横盘，继续观望'
            decision['action'] = {
                'type': 'WAIT',
                'target_position': position,
                'stop_loss': entry_price * 0.97 if entry_price else None,
                'stop_profit': entry_price * 1.1 if entry_price else None,
                'urgency': 'LOW'
            }
            return decision
        
        # 默认：观望
        decision['decision'] = 'WAIT'
        decision['confidence'] = 0.5
        decision['reason'] = '盘面不明确，继续观察'
        
        return decision
    
    def _print_integrated_report(
        self,
        stock_code: str,
        realtime_snapshot: Dict,
        intraday_trend: Dict,
        historical_analysis: Dict,
        decision: Dict
    ):
        """
        打印三层数据融合报告
        """
        print("\n" + "="*80)
        print(f"📊 三层数据融合分析报告 - {stock_code}")
        print("="*80)
        
        # Layer 1: 实时快照
        print("\n【Layer 1】实时快照")
        print(f"  数据来源: {realtime_snapshot.get('data_source', 'N/A')}")
        print(f"  数据新鲜度: {realtime_snapshot.get('data_freshness', 'N/A')}")
        print(f"  当前价格: {realtime_snapshot.get('price', 0):.2f}")
        print(f"  涨跌幅: {realtime_snapshot.get('pct_change', 0):.2f}%")
        print(f"  买卖压力: {realtime_snapshot.get('bid_ask_pressure', 0):.2f}")
        print(f"  信号: {realtime_snapshot.get('signal', 'N/A')}")
        
        # Layer 2: 分时走势
        print("\n【Layer 2】今日分时走势")
        if intraday_trend['success']:
            print(f"  数据来源: {intraday_trend['data_source']}")
            print(f"  模式: {self._translate_pattern(intraday_trend['pattern'])}")
            print(f"  最高价: {intraday_trend['high_price']:.2f}")
            print(f"  最低价: {intraday_trend['low_price']:.2f}")
            print(f"  波动率: {intraday_trend['volatility']:.2f}%")
            print(f"  K线数量: {len(intraday_trend['trend_data'])}根")
        else:
            print("  暂无分时数据")
        
        # Layer 3: 历史分析
        print("\n【Layer 3】90天历史分析")
        trap_risk = historical_analysis.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
        capital_type = historical_analysis.get('capital_classification', {}).get('type', 'UNKNOWN')
        total_institution = historical_analysis.get('fund_flow', {}).get('total_institution', 0)
        
        print(f"  诱多风险: {trap_risk:.2f}")
        print(f"  资金性质: {self._translate_capital_type(capital_type)}")
        print(f"  【90天累计】机构净流入: {total_institution:.2f}万元")
        
        # 综合决策
        print("\n【智能决策】")
        print(f"  决策: {decision['decision']}")
        print(f"  置信度: {decision['confidence']:.0%}")
        print(f"  理由: {decision['reason']}")
        
        if decision['action']:
            print(f"\n  操作建议:")
            action = decision['action']
            print(f"    动作类型: {action.get('type', 'N/A')}")
            print(f"    目标仓位: {action.get('target_position', 0):.0%}")
            if action.get('stop_loss'):
                print(f"    止损价: {action['stop_loss']:.2f}")
            if action.get('stop_profit'):
                print(f"    止盈价: {action['stop_profit']:.2f}")
            print(f"    紧急程度: {action.get('urgency', 'N/A')}")
        
        print("\n" + "="*80 + "\n")
    
    def _translate_pattern(self, pattern: str) -> str:
        """翻译模式名称"""
        pattern_map = {
            'PUMP_AND_DUMP': '冲高回落',
            'SUSTAINED_RISE': '持续拉升',
            'NARROW_TRADING': '窄幅震荡',
            'UNKNOWN': '未知'
        }
        return pattern_map.get(pattern, pattern)
    
    def _translate_capital_type(self, capital_type: str) -> str:
        """翻译资金性质"""
        type_map = {
            'HOT_MONEY': '短期游资',
            'INSTITUTION': '机构资金',
            'UNKNOWN': '未知'
        }
        return type_map.get(capital_type, capital_type)
    
    def _find_latest_analysis(self, stock_code: str) -> str | None:
        """查找最新的历史分析文件"""
        analysis_dir = f'data/stock_analysis/{stock_code}'
        
        if not os.path.exists(analysis_dir):
            return None
        
        # 查找最新的 enhanced.json 文件
        files = [f for f in os.listdir(analysis_dir) if f.endswith('_enhanced.json')]
        
        if not files:
            return None
        
        # 按修改时间排序
        files.sort(key=lambda x: os.path.getmtime(os.path.join(analysis_dir, x)), reverse=True)
        
        return os.path.join(analysis_dir, files[0])
    
    def _generate_tomorrow_strategy(
        self, 
        historical_data: Dict, 
        position: float, 
        entry_price: float | None
    ) -> Dict[str, Any]:
        """生成明日策略"""
        trap_risk = historical_data.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
        capital_type = historical_data.get('capital_classification', {}).get('type', 'UNKNOWN')
        trend = historical_data.get('fund_flow', {}).get('trend', 'UNKNOWN')
        
        strategy = {
            'open_action': 'WAIT',
            'target_position': position,
            'stop_loss': None,
            'stop_profit': None,
            'notes': []
        }
        
        # 高风险 → 减仓或空仓
        if trap_risk > 0.7:
            strategy['open_action'] = 'SELL' if position > 0 else 'AVOID'
            strategy['target_position'] = 0.0
            strategy['notes'].append('诱多风险高，开盘减仓')
        
        # 游资盘 + 下跌趋势 → 观望
        elif capital_type == 'HOT_MONEY' and trend == 'DOWNTREND':
            strategy['open_action'] = 'WAIT'
            strategy['notes'].append('游资出逃，等待企稳')
        
        # 低风险 + 上升趋势 → 适度参与
        elif trap_risk < 0.3 and trend == 'UPTREND':
            strategy['open_action'] = 'BUY' if position < 1.0 else 'HOLD'
            strategy['target_position'] = min(1.0, position + 0.2)
            strategy['notes'].append('趋势向好，适度加仓')
        
        # 其他 → 观察
        else:
            strategy['open_action'] = 'WAIT'
            strategy['notes'].append('盘面不明确，开盘观察10分钟')
        
        return strategy
    
    def _generate_weekly_plan(self, historical_data: Dict) -> Dict[str, Any]:
        """生成下周计划"""
        trap_risk = historical_data.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
        capital_type = historical_data.get('capital_classification', {}).get('type', 'UNKNOWN')
        total_flow = historical_data.get('fund_flow', {}).get('total_institution', 0)
        
        plan = {
            'week_strategy': 'DEFENSIVE',
            'entry_timing': [],
            'exit_timing': [],
            'notes': []
        }
        
        # 防守策略（高风险）
        if trap_risk > 0.6 or total_flow < -5000:
            plan['week_strategy'] = 'DEFENSIVE'
            plan['exit_timing'].append('周一开盘减仓50%')
            plan['exit_timing'].append('反弹不超3%立即清仓')
            plan['notes'].append('风险高，以防守为主')
        
        # 进攻策略（低风险 + 机构吸筹）
        elif trap_risk < 0.3 and capital_type == 'INSTITUTION' and total_flow > 5000:
            plan['week_strategy'] = 'OFFENSIVE'
            plan['entry_timing'].append('周一开盘适度建仓20%')
            plan['entry_timing'].append('回调2-3%加仓20%')
            plan['notes'].append('机构吸筹，可适度参与')
        
        # 观望策略
        else:
            plan['week_strategy'] = 'WAIT_AND_SEE'
            plan['notes'].append('盘面不明确，等待信号')
        
        return plan
    
    def _output_result(
        self, 
        stock_code: str, 
        result: Dict, 
        output_format: str
    ):
        """输出分析结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f'data/stock_analysis/{stock_code}'
        os.makedirs(output_dir, exist_ok=True)
        
        # JSON格式
        if output_format in ['json', 'both']:
            json_file = os.path.join(output_dir, f'{stock_code}_{timestamp}_analysis.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ JSON结果已保存: {json_file}")
        
        # TXT格式
        if output_format in ['txt', 'both']:
            txt_file = os.path.join(output_dir, f'{stock_code}_{timestamp}_analysis.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(self._format_to_txt(result))
            print(f"✅ TXT结果已保存: {txt_file}")
    
    def _format_to_txt(self, result: Dict) -> str:
        """格式化为TXT（人类可读）- 包含完整90天历史明细"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"📊 股票分析报告")
        lines.append("=" * 80)
        lines.append(f"股票代码: {result.get('stock_code', 'N/A')}")
        lines.append(f"分析模式: {result.get('mode', 'N/A')}")
        lines.append(f"分析时间: {result.get('analysis_time', 'N/A')}")
        lines.append("=" * 80)
        
        # 🔥 收盘后/周末/历史分析 - 输出完整90天明细
        if result.get('mode') in ['after_hours', 'weekend', 'historical']:
            # 检查是否包含完整的90天历史分析报告
            historical_report = result.get('historical_report', '')
            
            if historical_report:
                # 直接使用完整的90天历史报告
                lines.append("\n" + historical_report)
            else:
                # Fallback: 处理结构化数据
                historical_data = result.get('historical_analysis') or result.get('data', {})
                
                if historical_data:
                    lines.append("\n" + "=" * 80)
                    lines.append("📈 第一部分：资金流向分析（90天明细）")
                    lines.append("=" * 80)
                    
                    # 资金流向每日明细
                    fund_flow = historical_data.get('fund_flow', {})
                    if fund_flow.get('daily_data'):
                        lines.append(f"\n数据范围: {fund_flow.get('date_range', 'N/A')}")
                        lines.append(f"总天数: {fund_flow.get('total_days', 0)} 天")
                        lines.append("\n📅 每日资金流向详情（单位：万元）：\n")
                        
                        # 按月份分组显示
                        from collections import defaultdict
                        monthly_data = defaultdict(list)
                        
                        for day in fund_flow['daily_data']:
                            date_str = day.get('date', 'N/A')
                            if date_str != 'N/A':
                                month = date_str[:7]  # 提取年月部分，如 '2025-09'
                                monthly_data[month].append(day)
                        
                        # 按月份显示数据
                        for month in sorted(monthly_data.keys(), reverse=True):  # 从最新月份开始
                            lines.append(f"\n📅 {month}月数据（最新）\n")
                            lines.append(f"{'日期':<12} {'超大单':>10} {'大单':>10} {'中单':>10} {'小单':>10} {'机构':>10} {'散户':>10} {'信号':<10}")
                            lines.append("-" * 90)
                            
                            # 按日期倒序显示该月数据（最新的在前）
                            month_days = sorted(monthly_data[month], key=lambda x: x.get('date', ''), reverse=True)
                            for day in month_days:
                                signal = "🟢 吸筹" if day.get('institution', 0) > 0 else "⛔ 接盘"
                                lines.append(
                                    f"{day.get('date', 'N/A'):<12} "
                                    f"{day.get('super_large', 0):>10.2f} "
                                    f"{day.get('large', 0):>10.2f} "
                                    f"{day.get('medium', 0):>10.2f} "
                                    f"{day.get('small', 0):>10.2f} "
                                    f"{day.get('institution', 0):>10.2f} "
                                    f"{day.get('retail', 0):>10.2f} "
                                    f"{signal:<10}"
                                )                        
                        lines.append("\n📊 资金流向统计：")
                        lines.append(f"  吸筹天数: {fund_flow.get('buying_days', 0)} 天 ({fund_flow.get('buying_ratio', 0):.1%})")
                        lines.append(f"  减仓天数: {fund_flow.get('selling_days', 0)} 天 ({fund_flow.get('selling_ratio', 0):.1%})")
                        lines.append(f"  【90天累计】机构: {fund_flow.get('total_institution', 0):>10.2f} 万元")
                        lines.append(f"  【90天累计】散户: {fund_flow.get('total_retail', 0):>10.2f} 万元")
                        lines.append(f"  整体趋势: {fund_flow.get('trend', 'N/A')}")
                    
                    # QMT技术分析每日明细
                    lines.append("\n" + "=" * 80)
                    lines.append("📊 第二部分：技术分析（QMT）")
                    lines.append("=" * 80)
                    
                    qmt_data = historical_data.get('qmt', {})
                    if qmt_data.get('kline_1d'):
                        lines.append(f"\n数据范围: {qmt_data.get('date_range', 'N/A')}")
                        lines.append(f"总天数: {len(qmt_data['kline_1d'])} 天")
                        lines.append("\n📅 每日技术指标详情（最近30天）：\n")
                        lines.append(f"{'日期':<12} {'开盘':>7} {'最高':>7} {'最低':>7} {'收盘':>7} {'成交量':>9} {'MA5':>7} {'MA10':>7} {'MA20':>7} {'BIAS5':>7} {'RSI':>6} {'MACD':>7}")
                        lines.append("-" * 130)
                        
                        # 只显示最近30天（避免过长）
                        recent_days = qmt_data['kline_1d'][-30:]
                        for day in recent_days:
                            lines.append(
                                f"{day.get('date', 'N/A'):<12} "
                                f"{day.get('open', 0):>7.2f} "
                                f"{day.get('high', 0):>7.2f} "
                                f"{day.get('low', 0):>7.2f} "
                                f"{day.get('close', 0):>7.2f} "
                                f"{day.get('volume', 0):>9.0f} "
                                f"{day.get('MA5', 0):>7.2f} "
                                f"{day.get('MA10', 0):>7.2f} "
                                f"{day.get('MA20', 0):>7.2f} "
                                f"{day.get('BIAS_5', 0):>7.2%} "
                                f"{day.get('RSI', 0):>6.2f} "
                                f"{day.get('MACD', 0):>7.3f}"
                            )
                        
                        # 技术面总结
                        last_day = qmt_data['kline_1d'][-1]
                        lines.append("\n📊 技术面分析（最新）：")
                        lines.append(f"  当前价格: {last_day.get('close', 0):.2f}")
                        lines.append(f"  涨跌幅: {last_day.get('pct_change', 0):.2f}%")
                        lines.append(f"  均线: MA5={last_day.get('MA5', 0):.2f} | MA10={last_day.get('MA10', 0):.2f} | MA20={last_day.get('MA20', 0):.2f}")
                        lines.append(f"  乖离率: BIAS_5={last_day.get('BIAS_5', 0):.2%} | BIAS_10={last_day.get('BIAS_10', 0):.2%}")
                        lines.append(f"  RSI: {last_day.get('RSI', 0):.2f}")
                        lines.append(f"  MACD: {last_day.get('MACD', 0):.3f}")
                        lines.append(f"  布林带: 上轨={last_day.get('BOLL_UB', 0):.2f} | 中轨={last_day.get('BOLL_MB', 0):.2f} | 下轨={last_day.get('BOLL_LB', 0):.2f}")
                        lines.append(f"  ATR: {last_day.get('ATR', 0):.2f}")
                    
                    # DDE分析
                    if qmt_data.get('tick'):
                        tick = qmt_data['tick']
                        lines.append("\n📊 第三部分：DDE 大单分析")
                        lines.append("=" * 80)
                        lines.append(f"  买盘压力: {tick.get('bid_pressure', 0):.2%}")
                        lines.append(f"  卖盘压力: {tick.get('ask_pressure', 0):.2%}")
                        lines.append(f"  买价: {tick.get('bid_price', 0):.2f}")
                        lines.append(f"  卖价: {tick.get('ask_price', 0):.2f}")
                        lines.append(f"  价差: {tick.get('spread', 0):.2f}")
                        lines.append(f"  买盘总量: {tick.get('bid_volume', 0):.0f}手")
                        lines.append(f"  卖盘总量: {tick.get('ask_volume', 0):.0f}手")
                    
                    # 诱多陷阱检测
                    trap_detection = historical_data.get('trap_detection', {})
                    if trap_detection:
                        lines.append("\n📊 第四部分：诱多陷阱检测")
                        lines.append("=" * 80)
                        lines.append(f"  综合风险评分: {trap_detection.get('comprehensive_risk_score', 0):.2f}")
                        lines.append(f"  风险等级: {trap_detection.get('risk_level', 'N/A')}")
                        lines.append(f"  建议: {trap_detection.get('advice', 'N/A')}")
            
            # 今日总结（收盘后模式）
            if result.get('mode') == 'after_hours':
                today = result.get('today_summary', {})
                tomorrow = result.get('tomorrow_strategy', {})
                
                lines.append("\n" + "=" * 80)
                lines.append("🌆 今日总结:")
                lines.append("=" * 80)
                lines.append(f"  收盘价: {today.get('close', 0):.2f}")
                lines.append(f"  涨跌幅: {today.get('pct_change', 0):.2f}%")
                lines.append(f"  最高: {today.get('high', 0):.2f}")
                lines.append(f"  最低: {today.get('low', 0):.2f}")
                
                lines.append("\n🔮 明日策略:")
                lines.append(f"  开盘动作: {tomorrow.get('open_action', 'N/A')}")
                lines.append(f"  目标仓位: {tomorrow.get('target_position', 0):.0%}")
                if tomorrow.get('notes'):
                    for note in tomorrow['notes']:
                        lines.append(f"  - {note}")
            
            # 下周计划（周末模式）
            elif result.get('mode') == 'weekend':
                plan = result.get('next_week_plan', {})
                
                lines.append("\n" + "=" * 80)
                lines.append("📅 下周交易计划")
                lines.append("=" * 80)
                lines.append(f"  策略: {plan.get('week_strategy', 'N/A')}")
                
                if plan.get('entry_timing'):
                    lines.append("  进场时机:")
                    for timing in plan['entry_timing']:
                        lines.append(f"    - {timing}")
                
                if plan.get('exit_timing'):
                    lines.append("  离场时机:")
                    for timing in plan['exit_timing']:
                        lines.append(f"    - {timing}")
                
                if plan.get('notes'):
                    lines.append("  备注:")
                    for note in plan['notes']:
                        lines.append(f"    - {note}")
        
        # 实时分析
        elif result.get('mode') == 'realtime':
            snapshot = result.get('realtime_snapshot', {})
            decision = result.get('decision', {})
            
            lines.append("\n⏰ 实时快照:")
            lines.append(f"  数据来源: {snapshot.get('data_source', 'N/A')}")
            lines.append(f"  数据新鲜度: {snapshot.get('data_freshness', 'N/A')}")
            lines.append(f"  当前价格: {snapshot.get('price', 0):.2f}")
            lines.append(f"  涨跌幅: {snapshot.get('pct_change', 0):.2f}%")
            lines.append(f"  买卖压力: {snapshot.get('bid_ask_pressure', 0):.2f}")
            
            lines.append("\n🎯 交易决策:")
            lines.append(f"  决策: {decision.get('action', 'N/A')}")
            lines.append(f"  置信度: {decision.get('confidence', 0):.0%}")
            lines.append(f"  理由: {decision.get('reason', 'N/A')}")
        
        # 午休分析
        elif result.get('mode') == 'lunchtime':
            morning = result.get('morning_summary', {})
            afternoon = result.get('afternoon_strategy', {})
            
            lines.append("\n🌙 上午表现:")
            lines.append(f"  价格: {morning.get('price', 0):.2f}")
            lines.append(f"  涨跌幅: {morning.get('pct_change', 0):.2f}%")
            lines.append(f"  最高: {morning.get('morning_high', 0):.2f}")
            lines.append(f"  最低: {morning.get('morning_low', 0):.2f}")
            
            lines.append("\n🔮 下午策略:")
            lines.append(f"  建议: {afternoon.get('action', 'N/A')}")
            lines.append(f"  置信度: {afternoon.get('confidence', 0):.0%}")
            lines.append(f"  理由: {afternoon.get('reason', 'N/A')}")
        
        lines.append("\n" + "=" * 80)
        lines.append("风险提示: 本分析仅供参考，不构成投资建议")
        lines.append("=" * 80)
        
        return '\n'.join(lines)
    
    def _log_decision(self, stock_code: str, result: Dict):
        """记录决策日志（CSV时间序列）"""
        log_dir = 'data/decision_logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'{stock_code}_decisions.csv')
        
        # 提取关键指标
        log_entry = {
            'timestamp': result.get('analysis_time', ''),
            'mode': result.get('mode', ''),
            'phase': result.get('phase', ''),
            'decision': '',
            'confidence': 0,
            'price': 0,
            'pct_change': 0,
            'risk_score': 0
        }
        
        if result.get('mode') == 'realtime':
            decision = result.get('decision', {})
            snapshot = result.get('realtime_snapshot', {})
            risk = result.get('risk_assessment', {})
            
            log_entry.update({
                'decision': decision.get('action', ''),
                'confidence': decision.get('confidence', 0),
                'price': snapshot.get('price', 0),
                'pct_change': snapshot.get('pct_change', 0),
                'risk_score': risk.get('risk_score', 0)
            })
        
        # 写入CSV
        file_exists = os.path.exists(log_file)
        
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=log_entry.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(log_entry)
    
    def _print_lunchtime_report(self, result: Dict):
        """打印午休报告"""
        morning = result.get('morning_summary', {})
        afternoon = result.get('afternoon_strategy', {})
        risk = result.get('risk_assessment', {})
        
        print("\n" + "="*60)
        print(f"🌙 上午表现总结")
        print("="*60)
        print(f"价格: {morning.get('price', 0):.2f} ({morning.get('pct_change', 0):.2f}%)")
        print(f"区间: {morning.get('morning_low', 0):.2f} - {morning.get('morning_high', 0):.2f}")
        print(f"信号: {morning.get('signal', 'N/A')}")
        
        print(f"\n🔮 下午策略建议")
        print("="*60)
        print(f"建议: {afternoon.get('action', 'N/A')} (置信度: {afternoon.get('confidence', 0):.0%})")
        print(f"理由: {afternoon.get('reason', 'N/A')}")
        
        print(f"\n🚨 风险评估")
        print("="*60)
        print(f"综合风险: {risk.get('overall_risk', 'N/A')}")
        print(f"诱多风险: {risk.get('trap_risk', 0):.2f}")
        print(f"资金性质: {risk.get('capital_type', 'N/A')}")
        print("\n" + "="*60 + "\n")
    
    def _print_after_hours_report(self, result: Dict):
        """打印收盘后报告（增强版）"""
        today = result.get('today_summary', {})
        tomorrow = result.get('tomorrow_strategy', {})
        freshness_warning = result.get('data_freshness_warning', None)

        print("\n" + "="*60)
        print(f"🌆 今日交易总结")
        print("="*60)

        # 🔧 新增：显示数据新鲜度警告
        if freshness_warning:
            print(f"\n⚠️ 数据新鲜度警告: {freshness_warning}")

        print(f"数据来源: {today.get('data_freshness', 'N/A')}")
        print(f"收盘价: {today.get('close', 0):.2f} ({today.get('pct_change', 0):.2f}%)")
        print(f"区间: {today.get('low', 0):.2f} - {today.get('high', 0):.2f}")

        print(f"\n🔮 明日策略")
        print("="*60)
        print(f"开盘动作: {tomorrow.get('open_action', 'N/A')}")
        print(f"目标仓位: {tomorrow.get('target_position', 0):.0%}")

        if tomorrow.get('notes'):
            print("\n备注:")
            for note in tomorrow['notes']:
                print(f"  - {note}")

        print(f"\n📁 详细分析已保存: {result.get('output_file', 'N/A')}")
        print("\n" + "="*60 + "\n")
    
    def _print_weekend_report(self, result: Dict):
        """打印周末报告"""
        plan = result.get('next_week_plan', {})
        
        print("\n" + "="*60)
        print(f"📅 下周交易计划")
        print("="*60)
        print(f"策略定位: {plan.get('week_strategy', 'N/A')}")
        
        if plan.get('entry_timing'):
            print("\n进场时机:")
            for timing in plan['entry_timing']:
                print(f"  ✅ {timing}")
        
        if plan.get('exit_timing'):
            print("\n离场时机:")
            for timing in plan['exit_timing']:
                print(f"  ❌ {timing}")
        
        if plan.get('notes'):
            print("\n策略要点:")
            for note in plan['notes']:
                print(f"  📌 {note}")
        
        print(f"\n📁 详细分析已保存: {result.get('output_file', 'N/A')}")
        print("\n" + "="*60 + "\n")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='一体化股票分析工具')
    parser.add_argument('stock_code', help='股票代码（如 300997）')
    parser.add_argument('--mode', 
                        choices=['auto', 'realtime', 'historical'], 
                        default='auto',
                        help='分析模式（auto=自动判断，realtime=实时，historical=历史）')
    parser.add_argument('--position', type=float, default=0.0,
                        help='当前持仓比例（0-1）')
    parser.add_argument('--entry-price', type=float, default=None,
                        help='建仓价格')
    parser.add_argument('--format', 
                        choices=['json', 'txt', 'both'], 
                        default='both',
                        help='输出格式（json/txt/both）')
    
    args = parser.parse_args()
    
    # 执行分析
    analyzer = UnifiedStockAnalyzer()
    result = analyzer.analyze(
        stock_code=args.stock_code,
        mode=args.mode,
        position=args.position,
        entry_price=args.entry_price,
        output_format=args.format
    )
    
    # 处理错误
    if not result['success']:
        print(f"\n❌ 分析失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
