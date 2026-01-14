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