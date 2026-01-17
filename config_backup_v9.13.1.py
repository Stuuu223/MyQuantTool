"""
用户配置文件
用于存储用户的个性化设置
"""
import json
import os

class Config:
    """配置管理类"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_config = {
            'api_key': '',
            'default_symbol': '600519',
            'default_start_date': '2024-01-01',
            'atr_multiplier': 0.5,
            'grid_ratio': 0.1,
            'theme': 'light',
            'language': 'zh',
            # 🆕 V9.10.1: 核心监控池配置
            'watchlist': [],
            # 数据库配置
            'database': {
                'type': 'sqlite',
                'path': 'data/stock_data.db',
                'cache_path': 'data/cache.db',
                'history_path': 'data/history'
            },
            # 券商API配置
            'broker_apis': {
                'futu': {
                    'enabled': False,
                    'host': '127.0.0.1',
                    'port': 11111,
                    'password': ''
                },
                'eastmoney': {
                    'enabled': False,
                    'account': '',
                    'password': ''
                },
                'huatai': {
                    'enabled': False,
                    'app_id': '',
                    'app_secret': '',
                    'account': '',
                    'password': '',
                    'server_url': 'https://open.htsec.com'
                },
                'citic': {
                    'enabled': False,
                    'app_id': '',
                    'app_secret': '',
                    'account': '',
                    'password': '',
                    'server_url': 'https://open.citics.com'
                }
            },
            # 风险监控配置
            'risk_monitor': {
                'enabled': True,
                'max_position_ratio': 0.95,
                'max_daily_loss_ratio': 0.05,
                'max_drawdown_ratio': 0.20,
                'max_consecutive_losses': 5,
                'email_alert': {
                    'enabled': False,
                    'smtp_host': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'to_addr': ''
                }
            },
            # 机器学习配置
            'ml_config': {
                'lookback': 20,
                'epochs': 50,
                'batch_size': 32,
                'model_path': 'models/'
            },
            # 强化学习配置
            'rl_config': {
                'episodes': 100,
                'gamma': 0.99,
                'epsilon': 1.0,
                'epsilon_min': 0.01,
                'epsilon_decay': 0.995,
                'batch_size': 32
            }
        }
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有字段都存在
                    return self._deep_merge(self.default_config, config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def _deep_merge(self, base, update):
        """深度合并配置"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        return self.save_config()
    
    def update(self, updates):
        """批量更新配置"""
        self.config = self._deep_merge(self.config, updates)
        return self.save_config()
    
    def reset(self):
        """重置为默认配置"""
        self.config = self.default_config.copy()
        return self.save_config()
    
    def get_database_config(self):
        """获取数据库配置"""
        return self.config.get('database', {})
    
    def get_broker_config(self, broker_name):
        """获取券商配置"""
        return self.config.get('broker_apis', {}).get(broker_name, {})
    
    def get_risk_config(self):
        """获取风险监控配置"""
        return self.config.get('risk_monitor', {})
    
    def get_ml_config(self):
        """获取机器学习配置"""
        return self.config.get('ml_config', {})
    
    def get_rl_config(self):
        """获取强化学习配置"""
        return self.config.get('rl_config', {})
    
    # 🆕 V9.10.1: 核心监控池管理方法
    def get_watchlist(self):
        """
        获取核心监控池（白名单）
        
        Returns:
            list: 股票代码列表
        """
        return self.config.get('watchlist', [])
    
    def set_watchlist(self, codes):
        """
        设置核心监控池（白名单）
        
        Args:
            codes: 股票代码列表
            
        Returns:
            bool: 是否保存成功
        """
        return self.set('watchlist', codes)
    
    def add_to_watchlist(self, code):
        """
        添加股票到监控池
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否添加成功
        """
        watchlist = self.get_watchlist()
        if code not in watchlist:
            watchlist.append(code)
            return self.set_watchlist(watchlist)
        return False
    
    def remove_from_watchlist(self, code):
        """
        从监控池删除股票
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否删除成功
        """
        watchlist = self.get_watchlist()
        if code in watchlist:
            watchlist.remove(code)
            return self.set_watchlist(watchlist)
        return False
    
    def clear_watchlist(self):
        """
        清空监控池
        
        Returns:
            bool: 是否清空成功
        """
        return self.set_watchlist([])