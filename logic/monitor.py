"""
实时监控和告警模块

监控市场变化，及时发出告警
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Callable, Optional
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner
from logic.market_sentiment import MarketSentiment

logger = get_logger(__name__)


class Monitor:
    """
    监控器
    
    功能：
    1. 实时监控股票价格变化
    2. 实时监控市场情绪变化
    3. 触发告警
    """
    
    def __init__(self):
        """初始化监控器"""
        self.db = DataManager()
        self.monitored_stocks = {}  # {code: {'price': 价格, 'change_pct': 涨跌幅}}
        self.alerts = []
        self.is_running = False
        self.monitor_thread = None
        self.alert_callbacks = []  # 告警回调函数列表
    
    def add_stock(self, code: str, name: str = None):
        """
        添加监控股票
        
        Args:
            code: 股票代码
            name: 股票名称
        """
        if code in self.monitored_stocks:
            logger.warning(f"股票 {code} 已在监控列表中")
            return
        
        # 获取初始价格
        try:
            realtime_data = self.db.get_fast_price([code])
            if realtime_data:
                full_code = list(realtime_data.keys())[0]
                data = realtime_data[full_code]
                
                self.monitored_stocks[code] = {
                    'name': name or data.get('name', ''),
                    'price': data.get('now', 0),
                    'change_pct': (data.get('now', 0) - data.get('close', 0)) / data.get('close', 1) * 100 if data.get('close', 0) > 0 else 0,
                    'high': data.get('now', 0),
                    'low': data.get('now', 0),
                    'volume': data.get('volume', 0)
                }
                
                logger.info(f"添加监控股票: {name or code}({code})")
            else:
                logger.error(f"无法获取 {code} 的实时数据")
        except Exception as e:
            logger.error(f"添加监控股票失败: {e}")
    
    def remove_stock(self, code: str):
        """
        移除监控股票
        
        Args:
            code: 股票代码
        """
        if code in self.monitored_stocks:
            del self.monitored_stocks[code]
            logger.info(f"移除监控股票: {code}")
    
    def add_alert_callback(self, callback: Callable):
        """
        添加告警回调函数
        
        Args:
            callback: 回调函数，接收告警信息作为参数
        """
        self.alert_callbacks.append(callback)
        logger.info(f"添加告警回调函数")
    
    def start_monitoring(self, interval: int = 30):
        """
        开始监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.is_running:
            logger.warning("监控已在运行")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"开始监控，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("停止监控")
    
    def _monitor_loop(self, interval: int):
        """
        监控循环
        
        Args:
            interval: 监控间隔（秒）
        """
        while self.is_running:
            try:
                self._check_stocks()
                self._check_market_sentiment()
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(5)  # 出错后等待5秒再继续
    
    def _check_stocks(self):
        """检查监控股票"""
        if not self.monitored_stocks:
            return
        
        try:
            codes = list(self.monitored_stocks.keys())
            realtime_data = self.db.get_fast_price(codes)
            
            for full_code, data in realtime_data.items():
                # 清洗股票代码
                code = DataCleaner.clean_stock_code(full_code)
                if not code:
                    continue
                
                if code not in self.monitored_stocks:
                    continue
                
                old_data = self.monitored_stocks[code]
                
                # 获取新数据
                new_price = data.get('now', 0)
                new_change_pct = (new_price - data.get('close', 0)) / data.get('close', 1) * 100 if data.get('close', 0) > 0 else 0
                new_volume = data.get('volume', 0)
                
                # 检查价格变化
                price_change = new_price - old_data['price']
                price_change_pct = price_change / old_data['price'] * 100 if old_data['price'] > 0 else 0
                
                # 检查涨跌停
                limit_status = DataCleaner.check_limit_status(code, old_data['name'], new_change_pct)
                
                # 触发告警
                if limit_status['is_limit_up']:
                    self._trigger_alert({
                        'type': 'LIMIT_UP',
                        'code': code,
                        'name': old_data['name'],
                        'price': new_price,
                        'change_pct': new_change_pct,
                        'message': f"{old_data['name']}({code}) 涨停！价格: ¥{new_price:.2f}, 涨幅: {new_change_pct:.2f}%"
                    })
                elif limit_status['is_limit_down']:
                    self._trigger_alert({
                        'type': 'LIMIT_DOWN',
                        'code': code,
                        'name': old_data['name'],
                        'price': new_price,
                        'change_pct': new_change_pct,
                        'message': f"{old_data['name']}({code}) 跌停！价格: ¥{new_price:.2f}, 涨幅: {new_change_pct:.2f}%"
                    })
                elif abs(price_change_pct) > 5:  # 价格变化超过5%
                    self._trigger_alert({
                        'type': 'PRICE_CHANGE',
                        'code': code,
                        'name': old_data['name'],
                        'price': new_price,
                        'change_pct': new_change_pct,
                        'price_change_pct': price_change_pct,
                        'message': f"{old_data['name']}({code}) 价格大幅变化！价格: ¥{new_price:.2f}, 变化: {price_change_pct:.2f}%"
                    })
                
                # 更新数据
                self.monitored_stocks[code].update({
                    'price': new_price,
                    'change_pct': new_change_pct,
                    'high': max(old_data['high'], new_price),
                    'low': min(old_data['low'], new_price),
                    'volume': new_volume
                })
        
        except Exception as e:
            logger.error(f"检查股票失败: {e}")
    
    def _check_market_sentiment(self):
        """检查市场情绪"""
        try:
            market_sentiment = MarketSentiment()
            old_regime = market_sentiment.current_regime
            
            # 获取新的市场状态
            regime_info = market_sentiment.get_market_regime()
            new_regime = regime_info['regime']
            
            # 检查市场状态是否变化
            if old_regime and old_regime != new_regime:
                self._trigger_alert({
                    'type': 'MARKET_REGIME_CHANGE',
                    'old_regime': old_regime,
                    'new_regime': new_regime,
                    'message': f"市场状态变化！从 {old_regime} 变为 {new_regime}，策略建议：{regime_info['strategy']}"
                })
            
            market_sentiment.close()
        
        except Exception as e:
            logger.error(f"检查市场情绪失败: {e}")
    
    def _trigger_alert(self, alert: Dict):
        """
        触发告警
        
        Args:
            alert: 告警信息
        """
        alert['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.alerts.append(alert)
        
        logger.info(f"触发告警: {alert['message']}")
        
        # 调用回调函数
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调函数执行失败: {e}")
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        """
        获取告警列表
        
        Args:
            limit: 返回数量限制
        
        Returns:
            list: 告警列表
        """
        return self.alerts[-limit:]
    
    def clear_alerts(self):
        """清空告警列表"""
        self.alerts = []
        logger.info("清空告警列表")
    
    def get_monitored_stocks(self) -> Dict:
        """
        获取监控股票列表
        
        Returns:
            dict: 监控股票信息
        """
        return self.monitored_stocks.copy()
    
    def close(self):
        """关闭监控器"""
        self.stop_monitoring()
        if self.db:
            self.db.close()


class FlashCrashDetector:
    """
    🆕 V7.1: 闪崩探测器
    
    功能：
    1. 高频监控市场下跌速率
    2. 检测闪崩信号
    3. 触发紧急清仓信号
    """
    
    def __init__(self):
        """初始化闪崩探测器"""
        self.db = DataManager()
        self.price_history = {}  # {index_code: [(timestamp, price), ...]}
        self.limit_down_history = {}  # 跌停家数历史
        self.is_monitoring = False
        self.emergency_callback = None
        
        # 闪崩阈值配置
        self.index_drop_threshold_5min = 0.01  # 5分钟内指数下跌1%
        self.limit_down_surge_threshold = 20   # 跌停家数激增20家
        self.monitoring_interval = 60  # 监控间隔（秒）
        
        logger.info("闪崩探测器初始化完成")
    
    def start_monitoring(self, callback: Callable = None):
        """
        开始监控
        
        Args:
            callback: 紧急回调函数
        """
        if self.is_monitoring:
            logger.warning("闪崩探测器已经在运行中")
            return
        
        self.emergency_callback = callback
        self.is_monitoring = True
        
        logger.info("闪崩探测器开始监控")
        
        # 启动监控线程
        import threading
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("闪崩探测器停止监控")
    
    def _monitor_loop(self):
        """监控循环"""
        import time
        from datetime import datetime, timedelta
        
        while self.is_monitoring:
            try:
                # 获取指数数据
                indices = self._get_index_data()
                
                # 获取跌停家数
                limit_down_count = self._get_limit_down_count()
                
                # 检测闪崩信号
                flash_crash_signal = self._detect_flash_crash(indices, limit_down_count)
                
                if flash_crash_signal['is_flash_crash']:
                    logger.warning(f"🚨 检测到闪崩信号: {flash_crash_signal['reason']}")
                    
                    # 触发紧急回调
                    if self.emergency_callback:
                        self.emergency_callback(flash_crash_signal)
                
                # 等待下一次监控
                time.sleep(self.monitoring_interval)
            
            except Exception as e:
                logger.error(f"闪崩监控异常: {e}")
                time.sleep(self.monitoring_interval)
    
    def _get_index_data(self) -> Dict[str, float]:
        """
        获取指数数据
        
        Returns:
            dict: {index_code: current_price}
        """
        try:
            # 获取主要指数的实时数据
            index_codes = ['000001', '399001', '399006']  # 上证指数、深证成指、创业板指
            
            realtime_data = self.db.get_fast_price(index_codes)
            
            indices = {}
            for full_code, data in realtime_data.items():
                # 清洗股票代码
                code = full_code[2:]  # 去掉sh/sz前缀
                price = data.get('now', 0)
                if price > 0:
                    indices[code] = price
            
            return indices
        
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return {}
    
    def _get_limit_down_count(self) -> int:
        """
        获取跌停家数
        
        Returns:
            int: 跌停家数
        """
        try:
            from logic.market_cycle import MarketCycleManager
            mcm = MarketCycleManager()
            
            result = mcm.get_limit_up_down_count()
            limit_down_count = result.get('limit_down_count', 0)
            
            mcm.close()
            
            return limit_down_count
        
        except Exception as e:
            logger.error(f"获取跌停家数失败: {e}")
            return 0
    
    def _detect_flash_crash(self, 
                           current_indices: Dict[str, float], 
                           current_limit_down_count: int) -> Dict[str, Any]:
        """
        检测闪崩信号
        
        Args:
            current_indices: 当前指数价格
            current_limit_down_count: 当前跌停家数
        
        Returns:
            dict: {
                'is_flash_crash': bool,
                'reason': str,
                'severity': 'LOW' | 'MEDIUM' | 'HIGH',
                'index_drop_rate': float,
                'limit_down_surge': int
            }
        """
        is_flash_crash = False
        reason = ""
        severity = "LOW"
        index_drop_rate = 0.0
        limit_down_surge = 0
        
        now = datetime.now()
        
        # 🆕 V8.0: 双重确认机制
        index_drop_triggered = False
        limit_down_triggered = False
        
        # 检查每个指数的下跌速率
        for index_code, current_price in current_indices.items():
            # 获取5分钟前的价格
            if index_code not in self.price_history:
                # 初始化历史数据
                self.price_history[index_code] = [(now, current_price)]
                continue
            
            # 过滤5分钟内的历史数据
            five_minutes_ago = now - timedelta(minutes=5)
            recent_history = [
                (timestamp, price) 
                for timestamp, price in self.price_history[index_code]
                if timestamp > five_minutes_ago
            ]
            
            if len(recent_history) < 2:
                # 数据不足，添加当前数据
                self.price_history[index_code].append((now, current_price))
                continue
            
            # 计算下跌速率
            oldest_price = recent_history[0][1]
            drop_rate = (oldest_price - current_price) / oldest_price if oldest_price > 0 else 0
            
            if drop_rate > self.index_drop_threshold_5min:
                index_drop_triggered = True
                is_flash_crash = True
                index_drop_rate = max(index_drop_rate, drop_rate)
                reason += f"指数{index_code} 5分钟内下跌{drop_rate*100:.2f}%；"
                
                # 判断严重程度
                if drop_rate > 0.02:
                    severity = "HIGH"
                elif drop_rate > 0.015:
                    severity = "MEDIUM"
            
            # 更新历史数据
            self.price_history[index_code].append((now, current_price))
            
            # 保留最近10分钟的数据
            ten_minutes_ago = now - timedelta(minutes=10)
            self.price_history[index_code] = [
                (timestamp, price) 
                for timestamp, price in self.price_history[index_code]
                if timestamp > ten_minutes_ago
            ]
        
        # 检查跌停家数激增
        if index_code in self.limit_down_history:
            previous_limit_down_count = self.limit_down_history[index_code]
            limit_down_surge = current_limit_down_count - previous_limit_down_count
            
            if limit_down_surge >= self.limit_down_surge_threshold:
                limit_down_triggered = True
                is_flash_crash = True
                reason += f"跌停家数激增{limit_down_surge}家；"
                
                if limit_down_surge >= 50:
                    severity = "HIGH"
                elif limit_down_surge >= 30:
                    severity = "MEDIUM"
        
        # 🆕 V8.0: 双重确认机制
        # 只有同时满足两个条件才触发闪崩
        if index_drop_triggered and limit_down_triggered:
            # 双重确认：指数下跌 + 跌停家数激增
            is_flash_crash = True
            reason = f"🚨 双重确认：{reason}"
        elif index_drop_triggered and index_drop_rate > 0.015:
            # 指数大幅下跌（>1.5%）单独触发
            is_flash_crash = True
            reason = f"⚠️ 指数大幅下跌：{reason}"
        elif limit_down_triggered and limit_down_surge >= 50:
            # 跌停家数大幅激增（>50家）单独触发
            is_flash_crash = True
            reason = f"⚠️ 跌停家数大幅激增：{reason}"
        else:
            # 单一条件不触发，避免被假摔震出局
            is_flash_crash = False
            reason = ""
        
        # 更新跌停家数历史
        for index_code in current_indices.keys():
            self.limit_down_history[index_code] = current_limit_down_count
        
        return {
            'is_flash_crash': is_flash_crash,
            'reason': reason.strip(),
            'severity': severity,
            'index_drop_rate': index_drop_rate,
            'limit_down_surge': limit_down_surge,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def close(self):
        """关闭闪崩探测器"""
        self.stop_monitoring()
        if self.db:
            self.db.close()