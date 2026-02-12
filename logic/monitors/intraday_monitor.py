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

# 🔧 新增：导入日志系统
from logic.logger import get_logger
logger = get_logger(__name__)

# 尝试导入AkShare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("✅ AkShare 导入成功")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("❌ AkShare 导入失败")


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
            logger.info("✅ [IntraDayMonitor] xtdata 导入成功")
        except Exception as e:
            logger.warning(f"❌ [IntraDayMonitor] xtdata 导入失败: {e}")
            # 不要return，继续初始化其他组件

        # 尝试加载 CodeConverter
        try:
            from logic.code_converter import CodeConverter
            self.converter = CodeConverter()
            logger.info("✅ [IntraDayMonitor] CodeConverter 初始化成功")
        except Exception as e:
            logger.warning(f"❌ [IntraDayMonitor] CodeConverter 初始化失败: {e}")
            # 只有xtdata可以工作也可以继续

        # 如果xtdata和converter都成功，启用 QMT
        if self.xtdata is not None and self.converter is not None:
            self.qmt = True
            logger.info("✅ [IntraDayMonitor] QMT 数据源已启用")
        elif self.xtdata is not None:
            logger.warning("⚠️ [IntraDayMonitor] xtdata可用但CodeConverter失败，QMT功能受限")
        else:
            logger.warning("⚠️ [IntraDayMonitor] QMT功能不可用")

        # AkShare 状态
        if self.akshare_available:
            try:
                import akshare as ak
                self.ak = ak
                logger.info("✅ AkShare 数据源可用")
            except Exception as e:
                logger.warning(f"❌ AkShare 初始化失败: {e}")
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
        获取当前交易阶段（增强版）
        
        Returns:
            'OPENING_AUCTION' | 'MORNING' | 'LUNCH_BREAK' | 'AFTERNOON' | 
            'CLOSING_AUCTION' | 'AFTER_HOURS' | 'WEEKEND'
        """
        now = datetime.now()
        hour, minute = now.hour, now.minute
        current_time = now.time()
        
        # 周末
        if now.weekday() >= 5:
            return 'WEEKEND'
        
        # 🔧 新增：开盘竞价（09:15-09:30）
        if hour == 9 and 15 <= minute < 30:
            return 'OPENING_AUCTION'
        
        # 上午连续竞价（09:30-11:30）
        if self.trading_hours['morning_start'] <= current_time <= self.trading_hours['morning_end']:
            return 'MORNING'
        
        # 午休（11:30-13:00）
        if self.trading_hours['morning_end'] < current_time < self.trading_hours['afternoon_start']:
            return 'LUNCH_BREAK'
        
        # 下午连续竞价（13:00-14:57）
        if self.trading_hours['afternoon_start'] <= current_time <= time(14, 57):
            return 'AFTERNOON'
        
        # 🔧 新增：收盘竞价（14:57-15:00）
        if hour == 14 and minute >= 57:
            return 'CLOSING_AUCTION'
        
        # 收盘后
        return 'AFTER_HOURS'
    
    def get_intraday_snapshot(self, stock_code: str, auto_fallback: bool = True) -> Dict[str, Any]:
        """
        获取盘中实时快照（增强版：自动降级 + 阶段特殊处理）

        策略:
        1. 开盘竞价（09:15-09:30）→ 返回警告
        2. 收盘竞价（14:57-15:00）→ 使用14:57前最后数据 + 警告
        3. 交易时间内 → 尝试QMT实时数据
        4. AkShare实时行情（东方财富，有盘口数据）
        5. AkShare分钟线（备用，无盘口数据）
        6. QMT分时历史（最后一笔）

        Args:
            stock_code: 股票代码
            auto_fallback: 是否启用自动降级（QMT失败 → AkShare）

        Returns:
            {
                'success': bool,
                'data_source': 'QMT_REALTIME' | 'AKSHARE_REALTIME' | 'AKSHARE_MINUTE' | 'QMT_HISTORY',
                'data_freshness': 'FRESH' | 'DELAYED' | 'STALE',
                'phase': str,  # 当前交易阶段
                'warning': str | None,  # 警告信息
                'time': '2026-02-03 14:30:00',
                'price': 24.63,
                'pct_change': 3.44,
                'bid_ask_pressure': -0.81,
                'signal': '...'
            }
        """
        phase = self.get_trading_phase()

        result = {
            'success': False,
            'error': None,
            'data_source': None,
            'data_freshness': None,
            'phase': phase,
            'warning': None,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trading_phase': phase
        }

        # 🔧 新增：开盘竞价特殊处理（09:15-09:30）
        if phase == 'OPENING_AUCTION':
            return self._handle_opening_auction(stock_code)

        # 🔧 新增：收盘竞价特殊处理（14:57-15:00）
        if phase == 'CLOSING_AUCTION':
            return self._handle_closing_auction(stock_code)

        # 策略1: QMT实时数据（仅连续竞价时间）
        if self.is_trading_time() and self.qmt:
            logger.debug(f"🔍 尝试策略1: QMT实时数据")
            snapshot = self._get_qmt_realtime(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'QMT_REALTIME'
                snapshot['data_freshness'] = 'FRESH'
                snapshot['phase'] = phase
                logger.debug(f"✅ QMT实时数据获取成功")
                return snapshot
            else:
                logger.debug(f"❌ QMT失败: {snapshot.get('error')}")

        # 策略2: AkShare实时行情（东方财富，有盘口数据）
        if self.akshare_available:
            logger.debug(f"🔍 尝试策略2: AkShare实时行情")
            snapshot = self._get_akshare_realtime(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'AKSHARE_REALTIME'
                snapshot['phase'] = phase

                # 判断数据新鲜度
                if phase in ['MORNING', 'AFTERNOON']:
                    snapshot['data_freshness'] = 'FRESH'
                elif phase == 'LUNCH_BREAK':
                    snapshot['data_freshness'] = 'DELAYED'  # 午休取上午最后
                else:
                    snapshot['data_freshness'] = 'STALE'  # 收盘后

                logger.debug(f"✅ AkShare实时行情获取成功")
                return snapshot
            else:
                logger.debug(f"❌ AkShare实时行情失败: {snapshot.get('error')}")

        # 策略3: AkShare分钟线（备用）
        if self.akshare_available:
            logger.debug(f"🔍 尝试策略3: AkShare分钟线")
            snapshot = self._get_akshare_minute_last(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'AKSHARE_MINUTE'
                snapshot['data_freshness'] = 'DELAYED'
                snapshot['phase'] = phase
                logger.debug(f"✅ AkShare分钟线获取成功")
                return snapshot
            else:
                logger.debug(f"❌ AkShare分钟线失败: {snapshot.get('error')}")

        # 策略4: QMT分时历史（最后一笔）
        if self.qmt:
            logger.debug(f"🔍 尝试策略4: QMT分时历史")
            snapshot = self._get_qmt_minute_last(stock_code)
            if snapshot['success']:
                snapshot['data_source'] = 'QMT_HISTORY'
                snapshot['data_freshness'] = 'DELAYED'
                snapshot['phase'] = phase
                logger.debug(f"✅ QMT分时历史获取成功")
                return snapshot
            else:
                logger.debug(f"❌ QMT分时历史失败: {snapshot.get('error')}")

        # 策略5: 全部失败
        error_msg = '所有数据源均不可用，请检查网络或QMT连接'
        logger.error(f"❌ {error_msg}")
        result['error'] = error_msg
        return result
    
    def _get_qmt_realtime(self, stock_code: str) -> Dict[str, Any]:
        """获取QMT实时数据（使用get_full_tick）"""
        result = {'success': False}
        
        if not self.qmt:
            result['error'] = 'QMT接口不可用'
            return result
        
        try:
            # 转换股票代码为QMT格式
            qmt_code = self.converter.to_qmt(stock_code)
            
            # 使用 get_full_tick 获取实时数据（已测试可用）
            data = self.xtdata.get_full_tick([qmt_code])
            
            if not data or qmt_code not in data:
                result['error'] = 'QMT返回空数据'
                return result
            
            stock_data = data[qmt_code]
            
            # 计算涨跌幅
            last_price = stock_data.get('lastPrice', 0)
            last_close = stock_data.get('lastClose', 0)
            pct_change = (last_price - last_close) / last_close * 100 if last_close > 0 else 0
            
            result.update({
                'success': True,
                'price': float(last_price),
                'open': float(stock_data.get('open', 0)),
                'high': float(stock_data.get('high', 0)),
                'low': float(stock_data.get('low', 0)),
                'volume': int(stock_data.get('volume', 0)),
                'amount': float(stock_data.get('amount', 0)),
                'turnover_rate': 0.0,  # get_full_tick没有换手率
                'pct_change': pct_change,
            })
            
            # 计算买卖压力（使用五档行情）
            bid_prices = stock_data.get('bidPrice', [])
            ask_prices = stock_data.get('askPrice', [])
            bid_vols = stock_data.get('bidVol', [])
            ask_vols = stock_data.get('askVol', [])
            
            bid_total = sum(bid_vols) if bid_vols else 0
            ask_total = sum(ask_vols) if ask_vols else 0
            
            if bid_total + ask_total > 0:
                result['bid_ask_pressure'] = (bid_total - ask_total) / (bid_total + ask_total)
            else:
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
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
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
                
                # 确保数据有效性
                price = float(row['最新价']) if pd.notna(row['最新价']) and row['最新价'] != '-' else 0.0
                pct_change = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) and row['涨跌幅'] != '-' else 0.0
                high = float(row['最高']) if pd.notna(row['最高']) and row['最高'] != '-' else 0.0
                low = float(row['最低']) if pd.notna(row['最低']) and row['最低'] != '-' else 0.0
                open_price = float(row['今开']) if pd.notna(row['今开']) and row['今开'] != '-' else 0.0
                volume = int(float(row['成交量'])) if pd.notna(row['成交量']) and row['成交量'] != '-' else 0
                amount = float(row['成交额']) if pd.notna(row['成交额']) and row['成交额'] != '-' else 0.0
                turnover_rate = float(row.get('换手率', 0)) if pd.notna(row.get('换手率', 0)) else 0.0
                
                result.update({
                    'success': True,
                    'price': price,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'volume': volume,
                    'amount': amount,
                    'turnover_rate': turnover_rate,
                    'pct_change': pct_change,
                    'bid_ask_pressure': self._calculate_bid_ask_pressure_from_spot(row)
                })
                
                # 信号
                result['signal'] = self._generate_intraday_signal(result)
                
                return result
                
            except Exception as e:
                error_msg = f'AkShare实时数据获取失败: {str(e)}'

                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ 第{attempt + 1}次尝试失败，{retry_delay}秒后重试...")
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
        获取QMT分时历史的最后一笔数据（使用get_full_tick）
        
        用途: 午休/收盘后，取最近一笔分时数据
        """
        result = {'success': False}
        
        if not self.qmt:
            result['error'] = 'QMT接口不可用'
            return result
        
        try:
            # 转换股票代码为QMT格式
            qmt_code = self.converter.to_qmt(stock_code)
            
            # 使用 get_full_tick 获取实时数据（即使收盘后也能获取最后的数据）
            data = self.xtdata.get_full_tick([qmt_code])
            
            if not data or qmt_code not in data:
                result['error'] = 'QMT返回空数据'
                return result
            
            stock_data = data[qmt_code]
            
            # 计算涨跌幅
            last_price = stock_data.get('lastPrice', 0)
            last_close = stock_data.get('lastClose', 0)
            pct_change = (last_price - last_close) / last_close * 100 if last_close > 0 else 0
            
            result.update({
                'success': True,
                'price': float(last_price),
                'open': float(stock_data.get('open', 0)),
                'high': float(stock_data.get('high', 0)),
                'low': float(stock_data.get('low', 0)),
                'volume': int(stock_data.get('volume', 0)),
                'amount': float(stock_data.get('amount', 0)),
                'turnover_rate': 0.0,  # get_full_tick没有换手率
                'pct_change': pct_change,
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
                    logger.warning(f"⚠️ 第{attempt + 1}次尝试失败，{retry_delay}秒后重试...")
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

    def _handle_opening_auction(self, stock_code: str) -> Dict[str, Any]:
        """
        开盘竞价处理（09:15-09:30）

        策略:
        1. 返回警告信息
        2. 建议等待开盘后30分钟再分析
        """
        return {
            'success': True,
            'data_source': 'NONE',
            'data_freshness': 'STALE',
            'phase': 'OPENING_AUCTION',
            'warning': '⚠️ 开盘竞价期间（09:15-09:30），数据不可信，建议等待09:45后重新分析',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': 0,
            'pct_change': 0,
            'bid_ask_pressure': 0,
            'signal': '开盘竞价中，数据暂不可用'
        }

    def _handle_closing_auction(self, stock_code: str) -> Dict[str, Any]:
        """
        收盘竞价处理（14:57-15:00）

        策略:
        1. 获取14:57前最后一笔数据
        2. 标注为 STALE（已过期）
        3. 给出明确警告
        4. 🔧 新增：保存竞价数据用于Phase 3集合竞价分析
        """
        # 尝试获取最后一笔数据
        last_snapshot = None

        # 优先尝试 AkShare 实时行情
        if self.akshare_available:
            last_snapshot = self._get_akshare_realtime(stock_code)
            if last_snapshot['success']:
                last_snapshot['data_source'] = 'AKSHARE_LAST_TICK'
                last_snapshot['data_freshness'] = 'STALE'
                last_snapshot['phase'] = 'CLOSING_AUCTION'
                last_snapshot['warning'] = '⚠️ 收盘竞价中（14:57-15:00），数据为14:57前最后一笔，建议等待15:05后重新分析'
                logger.debug(f"✅ 获取到14:57前最后一笔数据: {last_snapshot.get('price', 0)}")

                # 🔧 新增：保存竞价数据
                self._save_auction_data(stock_code, last_snapshot)

                return last_snapshot

        # 备选：尝试 QMT 分时历史
        if self.qmt:
            last_snapshot = self._get_qmt_minute_last(stock_code)
            if last_snapshot['success']:
                last_snapshot['data_source'] = 'QMT_LAST_TICK'
                last_snapshot['data_freshness'] = 'STALE'
                last_snapshot['phase'] = 'CLOSING_AUCTION'
                last_snapshot['warning'] = '⚠️ 收盘竞价中（14:57-15:00），数据为14:57前最后一笔，建议等待15:05后重新分析'
                logger.debug(f"✅ 获取到14:57前最后一笔数据: {last_snapshot.get('price', 0)}")

                # 🔧 新增：保存竞价数据
                self._save_auction_data(stock_code, last_snapshot)

                return last_snapshot

        # 全部失败
        return {
            'success': False,
            'error': '收盘竞价期间无法获取14:57前数据，建议等待15:05后重新分析',
            'data_source': 'NONE',
            'data_freshness': 'STALE',
            'phase': 'CLOSING_AUCTION',
            'warning': '⚠️ 收盘竞价中（14:57-15:00），数据暂不可用，建议等待15:05后重新分析',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': 0,
            'pct_change': 0,
            'bid_ask_pressure': 0,
            'signal': '收盘竞价中，数据暂不可用'
        }

    def _save_auction_data(self, stock_code: str, auction_data: Dict[str, Any]) -> bool:
        """
        保存收盘竞价数据（Phase 3集合竞价分析用）

        Args:
            stock_code: 股票代码
            auction_data: 竞价数据字典

        Returns:
            是否保存成功
        """
        try:
            # 创建竞价缓存目录
            auction_cache_dir = Path("data/auction_cache")
            auction_cache_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名：{code}_{date}.json
            today_str = datetime.now().strftime("%Y%m%d")
            cache_file = auction_cache_dir / f"{stock_code}_{today_str}.json"

            # 准备保存的数据
            save_data = {
                "stock_code": stock_code,
                "date": today_str,
                "auction_phase": "CLOSING_AUCTION",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": {
                    "last_price": auction_data.get('price', 0),
                    "volume": auction_data.get('volume', 0),
                    "amount": auction_data.get('amount', 0),
                    "pct_change": auction_data.get('pct_change', 0),
                    "bid_ask_pressure": auction_data.get('bid_ask_pressure', 0),
                    "high": auction_data.get('high', 0),
                    "low": auction_data.get('low', 0),
                    "open": auction_data.get('open', 0)
                },
                "metadata": {
                    "data_source": auction_data.get('data_source', 'UNKNOWN'),
                    "data_freshness": auction_data.get('data_freshness', 'STALE'),
                    "warning": auction_data.get('warning', ''),
                    "signal": auction_data.get('signal', '')
                }
            }

            # 保存到JSON文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 收盘竞价数据已保存: {cache_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存竞价数据失败: {e}")
            return False

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
    logger.info(f"当前交易阶段: {phase}")

    # 获取实时快照（任何时候都能用）
    snapshot = monitor.get_intraday_snapshot('300997')

    if snapshot['success']:
        logger.info(f"\n实时快照:")
        logger.info(f"数据来源: {snapshot['data_source']}")
        logger.info(f"数据新鲜度: {snapshot['data_freshness']}")
        logger.info(f"时间: {snapshot['time']}")
        logger.info(f"价格: {snapshot['price']}")
        logger.info(f"涨跌幅: {snapshot['pct_change']}%")
        logger.info(f"买卖压力: {snapshot['bid_ask_pressure']}")
        logger.info(f"信号: {snapshot['signal']}")
    else:
        logger.error(f"错误: {snapshot['error']}")
