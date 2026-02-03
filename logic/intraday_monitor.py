"""
盘中实时监控器 v2.0 (Intraday Monitor - Enhanced)

新增功能:
1. 三层数据降级策略（QMT → AkShare → QMT历史 → 昨日）
2. 午休时间也能获取数据（取上午11:30最后一笔）
3. 收盘后也能获取数据（取15:00最后一笔）
4. 明确标注数据时效性

修复问题:
- 原版只在交易时间内工作
- 午休/收盘后返回"无法决策"

作者: MyQuantTool Team
版本: v2.0
更新日期: 2026-02-03
"""

# 🚀 [最高优先级] 禁用代理：必须在 import 其他库之前执行！
from logic.network_utils import disable_proxy
disable_proxy()

from datetime import datetime, time
from typing import Dict, Any
import json
import os

# 尝试导入AkShare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    print("✅ AkShare 导入成功")
except ImportError:
    AKSHARE_AVAILABLE = False
    print("❌ AkShare 导入失败")


class IntraDayMonitor:
    """盘中实时监控器（增强版）"""
    
    def __init__(self):
        """初始化监控器"""
        # 交易时间定义
        self.trading_hours = {
            'morning_start': time(9, 30),
            'morning_end': time(11, 30),
            'afternoon_start': time(13, 0),
            'afternoon_end': time(15, 0)
        }
        
        # 数据源初始化
        self.xtdata = None
        self.converter = None
        self.qmt = False
        self.akshare_available = AKSHARE_AVAILABLE
        
        # 尝试加载 xtquant
        try:
            from xtquant import xtdata as xt_module
            self.xtdata = xt_module
            print("✅ [IntraDayMonitor] xtdata 导入成功")
        except Exception as e:
            print(f"❌ [IntraDayMonitor] xtdata 导入失败: {e}")
            return
        
        # 尝试加载 CodeConverter
        try:
            from logic.code_converter import CodeConverter
            self.converter = CodeConverter()
            print("✅ [IntraDayMonitor] CodeConverter 初始化成功")
        except Exception as e:
            print(f"❌ [IntraDayMonitor] CodeConverter 初始化失败: {e}")
            self.xtdata = None
            return
        
        # 全部成功，启用 QMT
        self.qmt = True
        print("✅ [IntraDayMonitor] QMT 数据源已启用")
        
        # AkShare 状态
        if self.akshare_available:
            try:
                import akshare as ak
                self.ak = ak
                print("✅ AkShare 数据源可用")
            except Exception as e:
                print(f"❌ AkShare 初始化失败: {e}")
                self.akshare_available = False
    
    def is_trading_time(self) -> bool:
        """判断当前是否交易时间"""
        now = datetime.now()
        current_time = now.time()
        
        # 检查是否周末
        if now.weekday() >= 5:
            return False
        
        # 检查时间段
        morning = (self.trading_hours['morning_start'] <= current_time <= 
                   self.trading_hours['morning_end'])
        afternoon = (self.trading_hours['afternoon_start'] <= current_time <= 
                     self.trading_hours['afternoon_end'])
        
        return morning or afternoon
    
    def get_trading_phase(self) -> str:
        """
        获取当前交易阶段
        
        Returns:
            'MORNING' | 'LUNCH_BREAK' | 'AFTERNOON' | 'AFTER_HOURS' | 'WEEKEND'
        """
        now = datetime.now()
        current_time = now.time()
        
        # 周末
        if now.weekday() >= 5:
            return 'WEEKEND'
        
        # 上午
        if self.trading_hours['morning_start'] <= current_time <= self.trading_hours['morning_end']:
            return 'MORNING'
        
        # 午休
        if self.trading_hours['morning_end'] < current_time < self.trading_hours['afternoon_start']:
            return 'LUNCH_BREAK'
        
        # 下午
        if self.trading_hours['afternoon_start'] <= current_time <= self.trading_hours['afternoon_end']:
            return 'AFTERNOON'
        
        # 收盘后
        return 'AFTER_HOURS'
    
    def get_intraday_snapshot(self, stock_code: str) -> Dict[str, Any]:
        """
        获取盘中实时快照（增强版）
        
        策略:
        1. 交易时间内 → 尝试QMT实时数据
        2. AkShare实时行情（东方财富，有盘口数据）
        3. AkShare分钟线（备用，无盘口数据）
        4. QMT分时历史（最后一笔）
        
        Returns:
            {
                'success': bool,
                'data_source': 'QMT_REALTIME' | 'AKSHARE_REALTIME' | 'AKSHARE_MINUTE' | 'QMT_HISTORY',
                'data_freshness': 'FRESH' | 'DELAYED' | 'STALE',
                'time': '2026-02-03 14:30:00',
                'price': 24.63,
                'pct_change': 3.44,
                'bid_ask_pressure': -0.81,
                'signal': '...'
            }
        """
        result = {
            'success': False,
            'error': None,
            'data_source': None,
            'data_freshness': None,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trading_phase': self.get_trading_phase()
        }
        
        # 策略1: QMT实时数据（仅交易时间）
        if self.is_trading_time() and self.qmt:
            print(f"🔍 尝试策略1: QMT实时数据")
            snapshot = self._get_qmt_realtime(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'QMT_REALTIME'
                snapshot['data_freshness'] = 'FRESH'
                print(f"✅ QMT实时数据获取成功")
                return snapshot
            else:
                print(f"❌ QMT失败: {snapshot.get('error')}")
        
        # 策略2: AkShare实时行情（东方财富，有盘口数据）
        if self.akshare_available:
            print(f"🔍 尝试策略2: AkShare实时行情")
            snapshot = self._get_akshare_realtime(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'AKSHARE_REALTIME'
                
                # 判断数据新鲜度
                phase = self.get_trading_phase()
                if phase in ['MORNING', 'AFTERNOON']:
                    snapshot['data_freshness'] = 'FRESH'
                elif phase == 'LUNCH_BREAK':
                    snapshot['data_freshness'] = 'DELAYED'  # 午休取上午最后
                else:
                    snapshot['data_freshness'] = 'STALE'  # 收盘后
                
                print(f"✅ AkShare实时行情获取成功")
                return snapshot
            else:
                print(f"❌ AkShare实时行情失败: {snapshot.get('error')}")
        
        # 策略3: AkShare分钟线（备用）
        if self.akshare_available:
            print(f"🔍 尝试策略3: AkShare分钟线")
            snapshot = self._get_akshare_minute_last(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'AKSHARE_MINUTE'
                snapshot['data_freshness'] = 'DELAYED'
                print(f"✅ AkShare分钟线获取成功")
                return snapshot
            else:
                print(f"❌ AkShare分钟线失败: {snapshot.get('error')}")
        
        # 策略4: QMT分时历史（最后一笔）
        if self.qmt:
            print(f"🔍 尝试策略4: QMT分时历史")
            snapshot = self._get_qmt_minute_last(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'QMT_HISTORY'
                snapshot['data_freshness'] = 'DELAYED'
                print(f"✅ QMT分时历史获取成功")
                return snapshot
            else:
                print(f"❌ QMT分时历史失败: {snapshot.get('error')}")
        
        # 策略5: 全部失败
        error_msg = '所有数据源均不可用，请检查网络或QMT连接'
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        return result
    
    def _get_qmt_realtime(self, stock_code: str) -> Dict[str, Any]:
        """获取QMT实时数据（使用xtdata）"""
        result = {'success': False}
        
        if not self.qmt:
            result['error'] = 'QMT接口不可用'
            return result
        
        try:
            # 转换股票代码为QMT格式
            qmt_code = self.converter.to_qmt(stock_code)
            
            # QMT实时快照
            from datetime import timedelta
            start_time = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d 09:30:00')
            end_time = datetime.now().strftime('%Y%m%d 15:00:00')
            
            snapshot = self.xtdata.get_market_data(
                stock_list=[qmt_code],
                period='1d',
                start_time=start_time,
                end_time=end_time,
                dividend_type='front'  # 前复权
            )
            
            if snapshot is None or qmt_code not in snapshot or len(snapshot[qmt_code]) == 0:
                result['error'] = 'QMT返回空数据'
                return result
            
            # 解析数据（取最后一根日线）
            latest = snapshot[qmt_code].iloc[-1]
            
            result.update({
                'success': True,
                'price': float(latest['close']),
                'open': float(latest['open']),
                'high': float(latest['high']),
                'low': float(latest['low']),
                'volume': int(latest['volume']),
                'amount': float(latest['amount']),
                'turnover_rate': 0.0,  # xtdata日线数据没有换手率
                'pct_change': float((latest['close'] - latest['open']) / latest['open'] * 100) if latest['open'] > 0 else 0,
            })
            
            # QMT没有直接的五档行情，使用默认值
            result['bid_ask_pressure'] = 0.0
            
            # 信号
            result['signal'] = self._generate_intraday_signal(result)
            
            return result
            
        except Exception as e:
            result['error'] = f'QMT实时数据获取失败: {str(e)}'
            return result
    
    def _get_akshare_realtime(self, stock_code: str) -> Dict[str, Any]:
        """
        获取AkShare实时行情（带重试）
        
        使用接口: stock_zh_a_spot_em() - 东方财富实时行情
        优势: 有五档盘口数据
        """
        result = {'success': False}
        
        import time
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 获取A股实时行情
                df = self.ak.stock_zh_a_spot_em()
                
                # 查找目标股票
                stock_data = df[df['代码'] == stock_code]
                
                if stock_data.empty:
                    result['error'] = f'AkShare未找到股票 {stock_code}'
                    return result
                
                row = stock_data.iloc[0]
                
                result.update({
                    'success': True,
                    'price': float(row['最新价']),
                    'open': float(row['今开']),
                    'high': float(row['最高']),
                    'low': float(row['最低']),
                    'volume': int(row['成交量']),
                    'amount': float(row['成交额']),
                    'turnover_rate': float(row.get('换手率', 0)),
                    'pct_change': float(row['涨跌幅']),
                    'bid_ask_pressure': self._calculate_bid_ask_pressure_from_spot(row)
                })
                
                # 信号
                result['signal'] = self._generate_intraday_signal(result)
                
                return result
                
            except Exception as e:
                error_msg = f'AkShare实时数据获取失败: {str(e)}'
                
                if attempt < max_retries - 1:
                    print(f"⚠️ 第{attempt + 1}次尝试失败，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    result['error'] = error_msg
                    return result
        
        result['error'] = f'AkShare实时数据获取失败（重试{max_retries}次后仍失败）'
        return result
    
    def _calculate_bid_ask_pressure_from_spot(self, row) -> float:
        """计算买卖压力（基于东方财富实时行情的盘口数据）"""
        try:
            # 买一到买五
            bid_vol = sum([
                int(row.get(f'买{i}量', 0)) for i in range(1, 6)
            ])
            
            # 卖一到卖五
            ask_vol = sum([
                int(row.get(f'卖{i}量', 0)) for i in range(1, 6)
            ])
            
            if ask_vol == 0:
                return 1.0 if bid_vol > 0 else 0.0
            
            # 压力 = (买盘 - 卖盘) / (买盘 + 卖盘)
            pressure = (bid_vol - ask_vol) / (bid_vol + ask_vol)
            return round(pressure, 2)
            
        except Exception:
            return 0.0
    
    def _get_qmt_minute_last(self, stock_code: str) -> Dict[str, Any]:
        """
        获取QMT分时历史的最后一笔数据（使用xtdata）
        
        用途: 午休/收盘后，取最近一笔分时数据
        """
        result = {'success': False}
        
        if not self.qmt:
            result['error'] = 'QMT接口不可用'
            return result
        
        try:
            # 转换股票代码为QMT格式
            qmt_code = self.converter.to_qmt(stock_code)
            
            # 获取今日分时数据（1分钟K线）
            from datetime import timedelta
            start_time = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d 09:30:00')
            end_time = datetime.now().strftime('%Y%m%d 15:00:00')
            
            # 使用xtdata获取历史数据
            df = self.xtdata.get_market_data(
                stock_list=[qmt_code],
                period='1m',
                start_time=start_time,
                end_time=end_time,
                dividend_type='front'  # 前复权
            )
            
            if df is None or qmt_code not in df or len(df[qmt_code]) == 0:
                result['error'] = 'QMT分时数据为空'
                return result
            
            # 取最后一笔
            latest = df[qmt_code].iloc[-1]
            
            result.update({
                'success': True,
                'price': float(latest['close']),
                'open': float(latest['open']),
                'high': float(latest['high']),
                'low': float(latest['low']),
                'volume': int(latest['volume']),
                'amount': float(latest['amount']),
                'turnover_rate': 0.0,  # 分时数据没有换手率
                'pct_change': float((latest['close'] - latest['open']) / latest['open'] * 100) if latest['open'] > 0 else 0,
                'bid_ask_pressure': 0.0  # 历史数据没有盘口
            })
            
            # 信号
            result['signal'] = self._generate_intraday_signal(result)
            
            return result
            
        except Exception as e:
            result['error'] = f'QMT分时历史获取失败: {str(e)}'
            return result
    
    def _get_akshare_minute_last(self, stock_code: str) -> Dict[str, Any]:
        """
        获取AkShare最新分钟线（备用方案，带重试）
        
        用途: 当实时行情接口失败时，使用分钟线作为备用
        """
        result = {'success': False}
        
        import time
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                from datetime import timedelta
                
                # 获取最新1分钟K线
                df = self.ak.stock_zh_a_hist_min_em(
                    symbol=stock_code,
                    period='1',  # 1分钟
                    adjust='qfq',  # 前复权
                    start_date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    end_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                
                if df.empty:
                    result['error'] = 'AkShare分钟线数据为空'
                    return result
                
                # 取最新一条
                row = df.iloc[-1]
                
                result.update({
                    'success': True,
                    'price': float(row['收盘']),
                    'open': float(row['开盘']),
                    'high': float(row['最高']),
                    'low': float(row['最低']),
                    'volume': int(row['成交量']),
                    'amount': float(row['成交额']),
                    'pct_change': ((float(row['收盘']) - float(row['开盘'])) / float(row['开盘']) * 100) if float(row['开盘']) > 0 else 0,
                    'bid_ask_pressure': 0.0,  # 分钟线无盘口数据
                    'turnover_rate': 0.0
                })
                
                result['signal'] = self._generate_intraday_signal(result)
                
                return result
                
            except Exception as e:
                error_msg = f'AkShare分钟线获取失败: {str(e)}'
                
                if attempt < max_retries - 1:
                    print(f"⚠️ 第{attempt + 1}次尝试失败，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    result['error'] = error_msg
                    return result
        
        result['error'] = f'AkShare分钟线获取失败（重试{max_retries}次后仍失败）'
        return result
    
    def _calculate_bid_ask_pressure(self, tick_data: Dict) -> float:
        """计算买卖盘压力（五档行情）"""
        try:
            bid_volumes = [
                tick_data.get('bidVol1', 0),
                tick_data.get('bidVol2', 0),
                tick_data.get('bidVol3', 0),
                tick_data.get('bidVol4', 0),
                tick_data.get('bidVol5', 0)
            ]
            
            ask_volumes = [
                tick_data.get('askVol1', 0),
                tick_data.get('askVol2', 0),
                tick_data.get('askVol3', 0),
                tick_data.get('askVol4', 0),
                tick_data.get('askVol5', 0)
            ]
            
            bid_total = sum(bid_volumes)
            ask_total = sum(ask_volumes)
            
            if bid_total + ask_total == 0:
                return 0.0
            
            pressure = (bid_total - ask_total) / (bid_total + ask_total)
            return round(pressure, 2)
            
        except Exception:
            return 0.0
    
    def _generate_intraday_signal(self, snapshot: Dict) -> str:
        """生成盘中信号"""
        pressure = snapshot.get('bid_ask_pressure', 0)
        pct_change = snapshot.get('pct_change', 0)
        turnover = snapshot.get('turnover_rate', 0)
        
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
        """对比今日盘中数据 vs 昨日收盘数据"""
        result = {'success': False}
        
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
        
        # 提取昨日最后一天数据
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
        """对比今日 vs 昨日的关键指标"""
        comparison = {}
        
        # 价格变化
        yesterday_close = yesterday.get('close', today['open'])
        comparison['price_change_pct'] = round(
            (today['price'] - yesterday_close) / yesterday_close * 100, 2
        )
        
        # 成交量变化
        yesterday_volume = yesterday.get('volume', 0)
        if yesterday_volume > 0:
            comparison['volume_change_pct'] = round(
                (today['volume'] - yesterday_volume) / yesterday_volume * 100, 2
            )
        else:
            comparison['volume_change_pct'] = None
        
        # 5日滚动趋势
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
        
        # 诱多风险
        comparison['trap_risk'] = yesterday_full.get('trap_detection', {}).get(
            'comprehensive_risk_score', 0.5
        )
        
        # 资金性质
        comparison['capital_type'] = yesterday_full.get('capital_classification', {}).get(
            'type', 'UNKNOWN'
        )
        
        # 生成对比信号
        comparison['signal'] = self._generate_comparison_signal(today, yesterday, comparison)
        
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
        
        # 诱多检测
        if (flow_5d_trend == 'POSITIVE' and 
            pressure < -0.5 and 
            capital_type == 'HOT_MONEY'):
            return '警告: 昨天5日转正，今天卖压增大，疑似游资诱多！'
        
        # 趋势反转
        if flow_5d_trend == 'NEGATIVE' and pressure > 0.5:
            return '昨天趋势负，今天买盘强，可能反转，观察1-2天'
        
        # 延续下跌
        if flow_5d_trend == 'NEGATIVE' and pressure < -0.3:
            return '延续昨天弱势，继续下跌，建议减仓'
        
        # 震荡
        if abs(pressure) < 0.3:
            return '延续昨天走势，无明显变化，继续观察'
        
        return '盘面正常，按计划执行'


# 使用示例
if __name__ == '__main__':
    monitor = IntraDayMonitor()
    
    # 检查交易阶段
    phase = monitor.get_trading_phase()
    print(f"当前交易阶段: {phase}")
    
    # 获取实时快照（任何时候都能用）
    snapshot = monitor.get_intraday_snapshot('300997')
    
    if snapshot['success']:
        print(f"\n实时快照:")
        print(f"数据来源: {snapshot['data_source']}")
        print(f"数据新鲜度: {snapshot['data_freshness']}")
        print(f"时间: {snapshot['time']}")
        print(f"价格: {snapshot['price']}")
        print(f"涨跌幅: {snapshot['pct_change']}%")
        print(f"买卖压力: {snapshot['bid_ask_pressure']}")
        print(f"信号: {snapshot['signal']}")
    else:
        print(f"错误: {snapshot['error']}")
