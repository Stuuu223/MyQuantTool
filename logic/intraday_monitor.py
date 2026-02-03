"""
盘中实时监控器 (Intraday Monitor)

功能:
1. 判断当前是否交易时间
2. 获取盘中实时快照（QMT数据源）
3. 对比昨日历史数据，识别趋势变化
4. 检测诱多风险（今日是否大额流出）
5. 输出标准化的实时决策数据

依赖:
- data_sources/qmt_source.py (QMT数据源)
- logic/trap_detector.py (诱多检测器)
- logic/capital_classifier.py (资金分类器)

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-03
"""

from datetime import datetime, time
from typing import Dict, Any
import json
import os


class IntraDayMonitor:
    """盘中实时监控器"""
    
    def __init__(self):
        """初始化监控器"""
        # 交易时间定义
        self.trading_hours = {
            'morning_start': time(9, 30),
            'morning_end': time(11, 30),
            'afternoon_start': time(13, 0),
            'afternoon_end': time(15, 0)
        }
        
        # 数据源（使用项目中已有的 QMTSupplement）
        try:
            from logic.qmt_supplement import QMTSupplement
            self.qmt = QMTSupplement()
        except ImportError:
            print("警告: 无法导入 QMTSupplement，实时数据功能不可用")
            self.qmt = None
    
    def is_trading_time(self) -> bool:
        """
        判断当前是否交易时间
        
        Returns:
            bool: True=交易时间, False=非交易时间
        """
        now = datetime.now()
        current_time = now.time()
        
        # 检查是否周末
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False
        
        # 检查时间段
        morning = (self.trading_hours['morning_start'] <= current_time <= 
                   self.trading_hours['morning_end'])
        afternoon = (self.trading_hours['afternoon_start'] <= current_time <= 
                     self.trading_hours['afternoon_end'])
        
        return morning or afternoon
    
    def get_trading_time_info(self) -> Dict[str, Any]:
        """
        获取交易时间信息
        
        Returns:
            Dict: 包含当前时间、是否交易时间、距离收盘时间等
        """
        now = datetime.now()
        now_time = now.time()
        
        is_trading = self.is_trading_time()
        
        # 计算距离收盘时间
        morning_end = datetime.combine(now.date(), self.trading_hours['morning_end'])
        afternoon_end = datetime.combine(now.date(), self.trading_hours['afternoon_end'])
        
        if is_trading:
            if now_time <= self.trading_hours['morning_end']:
                # 上午交易时间
                minutes_to_close = int((morning_end - now).total_seconds() / 60)
                next_close = self.trading_hours['morning_end']
            else:
                # 下午交易时间
                minutes_to_close = int((afternoon_end - now).total_seconds() / 60)
                next_close = self.trading_hours['afternoon_end']
        else:
            minutes_to_close = None
            next_close = None
        
        return {
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading': is_trading,
            'trading_period': self._get_trading_period(now_time),
            'minutes_to_close': minutes_to_close,
            'next_close_time': next_close.strftime('%H:%M') if next_close else None
        }
    
    def _get_trading_period(self, now_time: time) -> str:
        """获取当前交易时段"""
        if self.trading_hours['morning_start'] <= now_time <= self.trading_hours['morning_end']:
            return '上午交易时段'
        elif self.trading_hours['afternoon_start'] <= now_time <= self.trading_hours['afternoon_end']:
            return '下午交易时段'
        elif now_time < self.trading_hours['morning_start']:
            return '交易前'
        elif now_time > self.trading_hours['afternoon_end']:
            return '交易后'
        else:
            return '午休时间'
    
    def get_intraday_snapshot(self, stock_code: str) -> Dict[str, Any]:
        """
        获取盘中实时快照
        
        Args:
            stock_code: 股票代码（如 '300997'）
        
        Returns:
            {
                'success': bool,
                'error': str | None,
                'time': '2026-02-03 14:30:00',
                'is_trading_time': True,
                'price': 24.63,
                'open': 23.81,
                'high': 24.85,
                'low': 23.80,
                'volume': 1500000,  # 成交量（手）
                'amount': 36500000,  # 成交额（元）
                'turnover_rate': 12.5,  # 换手率
                'pct_change': 3.44,  # 涨跌幅
                'bid_ask_pressure': -0.81,  # 买卖盘压力 (-1到+1)
                'signal': '卖盘压力大，游资出货',
                'data_source': 'QMT_REALTIME'
            }
        """
        result = {
            'success': False,
            'error': None,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading_time': self.is_trading_time(),
            'data_source': 'QMT_REALTIME'
        }
        
        # 检查是否交易时间
        if not result['is_trading_time']:
            result['error'] = '非交易时间，无法获取盘中数据'
            return result
        
        # 检查QMT数据源
        if self.qmt is None:
            result['error'] = 'QMT数据源未初始化'
            return result
        
        try:
            # 转换为 QMT 代码格式
            from logic.code_converter import CodeConverter
            converter = CodeConverter()
            qmt_code = converter.to_qmt(stock_code)
            
            # 获取全市场 Tick 数据（QMT 实时数据）
            from xtquant import xtdata
            tick_data = xtdata.get_full_tick([qmt_code])
            
            if tick_data is None or len(tick_data) == 0 or qmt_code not in tick_data:
                result['error'] = f'无法获取 {stock_code} 的实时数据'
                return result
            
            tick = tick_data[qmt_code]
            
            # 提取基础数据
            price = float(tick.get('lastPrice', 0))
            open_price = float(tick.get('open', 0))
            high_price = float(tick.get('high', 0))
            low_price = float(tick.get('low', 0))
            volume = float(tick.get('volume', 0))  # 股
            amount = float(tick.get('amount', 0))  # 元
            
            # 计算涨跌幅
            last_close = float(tick.get('lastClose', 0))
            if last_close > 0:
                pct_change = (price - last_close) / last_close * 100
            else:
                pct_change = 0.0
            
            # 提取买卖盘
            bid_prices = tick.get('bidPrice', [])
            ask_prices = tick.get('askPrice', [])
            bid_vols = tick.get('bidVol', [])
            ask_vols = tick.get('askVol', [])
            
            bid = []
            ask = []
            for i in range(min(5, len(bid_prices))):
                if bid_prices[i] > 0:
                    bid.append({
                        "price": round(bid_prices[i], 2),
                        "volume": round(bid_vols[i], 2) if i < len(bid_vols) else 0
                    })
            
            for i in range(min(5, len(ask_prices))):
                if ask_prices[i] > 0:
                    ask.append({
                        "price": round(ask_prices[i], 2),
                        "volume": round(ask_vols[i], 2) if i < len(ask_vols) else 0
                    })
            
            # 计算买卖盘压力
            bid_total = sum([b['volume'] for b in bid])
            ask_total = sum([a['volume'] for a in ask])
            bid_ask_pressure = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0.0
            
            result.update({
                'success': True,
                'price': round(price, 2),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'last_close': round(last_close, 2),
                'volume': int(volume),  # 股
                'volume_hands': int(volume / 100),  # 手
                'amount': round(amount, 2),  # 元
                'amount_wan': round(amount / 10000, 2),  # 万元
                'pct_change': round(pct_change, 2),
                'bid': bid,
                'ask': ask,
                'bid_total': round(bid_total, 2),
                'ask_total': round(ask_total, 2),
                'bid_ask_pressure': round(bid_ask_pressure, 2)
            })
            
            # 生成信号
            result['signal'] = self._generate_intraday_signal(result)
            
            return result
            
        except Exception as e:
            result['error'] = f'获取实时数据异常: {str(e)}'
            return result
    
    
    
    def _generate_intraday_signal(self, snapshot: Dict) -> str:
        """
        生成盘中信号
        
        Args:
            snapshot: 实时快照数据
        
        Returns:
            str: 信号描述
        """
        pressure = snapshot.get('bid_ask_pressure', 0)
        pct_change = snapshot.get('pct_change', 0)
        turnover = snapshot.get('turnover_rate', 0)
        
        # 信号生成逻辑
        if pressure < -0.7 and pct_change < 0:
            return '卖盘压力大，游资出货，建议减仓'
        elif pressure < -0.5 and turnover > 15:
            return '高换手+卖压，可能是诱多，警惕'
        elif pressure > 0.6 and pct_change > 2:
            return '买盘强势，机构吸筹，可继续持有'
        elif pressure > 0.3 and pct_change > 0:
            return '温和上涨，买盘占优，观察'
        elif abs(pressure) < 0.2:
            return '盘面平稳，多空均衡，观望'
        else:
            return '盘面震荡，等待明确信号'
    
    def compare_with_yesterday(
        self, 
        stock_code: str, 
        yesterday_file: str
    ) -> Dict[str, Any]:
        """
        对比今日盘中数据 vs 昨日收盘数据
        
        Args:
            stock_code: 股票代码
            yesterday_file: 昨日分析结果JSON文件路径
        
        Returns:
            {
                'success': bool,
                'today': {...},  # 今日快照
                'yesterday': {...},  # 昨日数据
                'comparison': {
                    'price_change_pct': 2.3,  # 相比昨日收盘的涨跌幅
                    'volume_change_pct': 150,  # 成交量变化百分比
                    'flow_5d_trend': 'REVERSAL',  # 5日滚动趋势
                    'trap_risk': 0.85,  # 诱多风险评分
                    'signal': '今天卖压明显增大，昨天的反弹可能是诱多'
                }
            }
        """
        result = {
            'success': False,
            'error': None
        }
        
        # 获取今日快照
        today = self.get_intraday_snapshot(stock_code)
        
        if not today['success']:
            result['error'] = today['error']
            return result
        
        # 加载昨日数据
        if not os.path.exists(yesterday_file):
            result['error'] = f'昨日数据文件不存在: {yesterday_file}'
            return result
        
        try:
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                yesterday_data = json.load(f)
        except Exception as e:
            result['error'] = f'加载昨日数据失败: {str(e)}'
            return result
        
        # 提取昨日最后一天的数据
        yesterday_latest = yesterday_data['fund_flow']['daily_data'][-1]
        
        # 对比分析
        comparison = self._compare_metrics(today, yesterday_latest, yesterday_data)
        
        result.update({
            'success': True,
            'today': today,
            'yesterday': yesterday_latest,
            'yesterday_90d_summary': {
                'total_institution': yesterday_data['fund_flow']['total_institution'],
                'trend': yesterday_data['fund_flow']['trend'],
                'capital_type': yesterday_data.get('capital_classification', {}).get('type', 'UNKNOWN'),
                'trap_risk': yesterday_data.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
            },
            'comparison': comparison
        })
        
        return result
    
    def _compare_metrics(
        self, 
        today: Dict, 
        yesterday: Dict,
        yesterday_full: Dict
    ) -> Dict[str, Any]:
        """
        对比今日 vs 昨日的关键指标
        
        Args:
            today: 今日快照
            yesterday: 昨日最后一天数据
            yesterday_full: 昨日完整分析数据
        
        Returns:
            对比结果字典
        """
        comparison = {}
        
        # 价格变化（相比昨日收盘）
        # 注意: 需要从yesterday中获取收盘价（AkShare数据中没有，需要补充）
        # 这里假设yesterday中有'close'字段，实际需要调整
        yesterday_close = yesterday.get('close', today['open'])
        comparison['price_change_pct'] = round(
            (today['price'] - yesterday_close) / yesterday_close * 100, 2
        )
        
        # 成交量变化（需要从QMT历史数据获取昨日成交量）
        # 这里假设yesterday中有'volume'字段
        yesterday_volume = yesterday.get('volume', 0)
        if yesterday_volume > 0:
            comparison['volume_change_pct'] = round(
                (today['volume'] - yesterday_volume) / yesterday_volume * 100, 2
            )
        else:
            comparison['volume_change_pct'] = None
        
        # 5日滚动趋势判断
        yesterday_flow_5d = yesterday.get('flow_5d_net', 0)
        if yesterday_flow_5d is not None:
            if yesterday_flow_5d > 0:
                comparison['flow_5d_trend'] = 'POSITIVE'
            elif yesterday_flow_5d < -1000:
                comparison['flow_5d_trend'] = 'NEGATIVE'
            else:
                comparison['flow_5d_trend'] = 'NEUTRAL'
        else:
            comparison['flow_5d_trend'] = 'UNKNOWN'
        
        # 诱多风险评分（来自昨日分析）
        comparison['trap_risk'] = yesterday_full.get('trap_detection', {}).get(
            'comprehensive_risk_score', 0.5
        )
        
        # 资金性质
        comparison['capital_type'] = yesterday_full.get('capital_classification', {}).get(
            'type', 'UNKNOWN'
        )
        
        # 生成对比信号
        comparison['signal'] = self._generate_comparison_signal(
            today, yesterday, comparison
        )
        
        return comparison
    
    def _generate_comparison_signal(
        self, 
        today: Dict, 
        yesterday: Dict,
        comparison: Dict
    ) -> str:
        """生成对比信号"""
        
        pressure = today.get('bid_ask_pressure', 0)
        price_change = comparison.get('price_change_pct', 0)
        flow_5d_trend = comparison.get('flow_5d_trend', 'UNKNOWN')
        trap_risk = comparison.get('trap_risk', 0.5)
        capital_type = comparison.get('capital_type', 'UNKNOWN')
        
        # 诱多检测逻辑
        if (flow_5d_trend == 'POSITIVE' and 
            pressure < -0.5 and 
            capital_type == 'HOT_MONEY'):
            return '警告: 昨天5日转正，今天卖压增大，疑似游资诱多！'
        
        # 趋势反转检测
        if flow_5d_trend == 'NEGATIVE' and pressure > 0.5:
            return '昨天趋势负，今天买盘强，可能反转，观察1-2天'
        
        # 延续下跌
        if flow_5d_trend == 'NEGATIVE' and pressure < -0.3:
            return '延续昨天弱势，继续下跌，建议减仓'
        
        # 震荡
        if abs(pressure) < 0.3:
            return '延续昨天走势，无明显变化，继续观察'
        
        return '盘面正常，按计划执行'
    
    def save_snapshot(self, stock_code: str, snapshot: Dict, output_dir: str = 'data/intraday'):
        """
        保存实时快照到文件
        
        Args:
            stock_code: 股票代码
            snapshot: 快照数据
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{stock_code}_intraday_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        print(f"实时快照已保存: {filepath}")


# 使用示例
if __name__ == '__main__':
    monitor = IntraDayMonitor()
    
    # 检查是否交易时间
    print(f"当前是否交易时间: {monitor.is_trading_time()}")
    
    # 获取实时快照
    snapshot = monitor.get_intraday_snapshot('300997')
    
    if snapshot['success']:
        print(f"\n实时快照:")
        print(f"时间: {snapshot['time']}")
        print(f"价格: {snapshot['price']}")
        print(f"涨跌幅: {snapshot['pct_change']}%")
        print(f"买卖盘压力: {snapshot['bid_ask_pressure']}")
        print(f"信号: {snapshot['signal']}")
        
        # 对比昨日数据
        yesterday_file = 'data/stock_analysis/300997_20260203_115807_90days_enhanced.json'
        comparison = monitor.compare_with_yesterday('300997', yesterday_file)
        
        if comparison['success']:
            print(f"\n对比分析:")
            print(f"相比昨日涨跌: {comparison['comparison']['price_change_pct']}%")
            print(f"5日趋势: {comparison['comparison']['flow_5d_trend']}")
            print(f"诱多风险: {comparison['comparison']['trap_risk']}")
            print(f"对比信号: {comparison['comparison']['signal']}")
    else:
        print(f"错误: {snapshot['error']}")
