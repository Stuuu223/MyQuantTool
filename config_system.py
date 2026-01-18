#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V10.1.9 系统配置文件
集中管理所有"开关"和"阈值"
"""

# ==========================================
# 市场情绪阈值
# ==========================================
THRESHOLD_MARKET_HEAT_HIGH = 80   # 市场高潮分
THRESHOLD_MARKET_HEAT_LOW = 30    # 市场冰点分
THRESHOLD_MALIGNANT_RATE = 0.4    # 恶性炸板率报警线 (40%)
THRESHOLD_HIGH_MALIGNANT_RATE = 0.3  # 高位分歧炸板率 (30%)
THRESHOLD_LOW_MALIGNANT_RATE = 0.2   # 低炸板率安全线 (20%)

# ==========================================
# 风险扫描阈值
# ==========================================
THRESHOLD_OPEN_KILL_GAP = 5.0     # 开盘核按钮：高开幅度 > 5%
THRESHOLD_FAKE_BOARD_RATIO = 0.02 # 纸老虎：封单/成交额 < 2%
THRESHOLD_LATE_SNEAK_TIME = 1440  # 尾盘偷袭：14:40 (整数表示，14:40 = 14*60 + 40 = 880)

# ==========================================
# 技术分析阈值
# ==========================================
THRESHOLD_BIAS_HIGH = 15          # 乖离率超买（%）
THRESHOLD_BIAS_LOW = -15          # 乖离率超跌（%）
THRESHOLD_MA_PERIOD = 20          # 均线周期（默认20日线）
THRESHOLD_HISTORY_DAYS = 60       # 历史数据天数

# ==========================================
# 系统设置
# ==========================================
MAX_SCAN_WORKERS = 8              # 并发线程数
API_TIMEOUT = 5.0                 # API 超时时间（秒）
MAX_SCAN_STOCKS = 8               # 最大扫描股票数
STOCK_POOL_SIZE = 10              # 股票池大小

# 🚨 重要：数据提供者默认模式
# - 'live': 实盘模式（默认，周一开盘使用）
# - 'replay': 历史回放模式（仅用于周末测试）
DATA_PROVIDER_MODE = 'live'       # 默认模式：实盘

# ==========================================
# 龙头战法阈值
# ==========================================
DRAGON_MIN_SCORE = 60             # 龙头最低评分
DRAGON_MIN_CHANGE_PCT = 7.0       # 龙头最低涨幅（%）
DRAGON_MIN_VOLUME_RATIO = 2.0     # 龙头最低量比
DRAGON_MIN_VOLUME = 5000          # 龙头最小成交量（手）
DRAGON_MIN_AMOUNT = 3000          # 龙头最小成交额（万元）

# ==========================================
# 趋势中军战法阈值
# ==========================================
TREND_MIN_SCORE = 55              # 趋势中军最低评分
TREND_MIN_CHANGE_PCT = 2.0        # 趋势中军最低涨幅（%）

# ==========================================
# 半路战法阈值
# ==========================================
HALFWAY_MIN_SCORE = 70            # 半路战法最低评分
HALFWAY_MIN_VOLUME_RATIO = 3.0    # 半路战法最低量比

# ==========================================
# 交易时间设置
# ==========================================
# 集合竞价时间（9:15-9:25）
CALL_AUCTION_START = 9 * 60 + 15   # 9:15 = 555分钟
CALL_AUCTION_END = 9 * 60 + 25     # 9:25 = 565分钟

# 🆕 V11 最小可靠时间（用于溢价计算）
MIN_RELIABLE_TIME = 9 * 60 + 25    # 9:25 = 565分钟（集合竞价定格后）

# 上午交易时间（9:30-11:30）
MORNING_TRADE_START = 9 * 60 + 30  # 9:30 = 570分钟
MORNING_TRADE_END = 11 * 60 + 30   # 11:30 = 690分钟

# 午间休盘（11:30-13:00）
NOON_BREAK_START = 11 * 60 + 30    # 11:30 = 690分钟
NOON_BREAK_END = 13 * 60          # 13:00 = 780分钟

# 下午交易时间（13:00-15:00）
AFTERNOON_TRADE_START = 13 * 60   # 13:00 = 780分钟
AFTERNOON_TRADE_END = 15 * 60     # 15:00 = 900分钟

# 尾盘偷袭时间（14:40-15:00）
LATE_SNEAK_START = 14 * 60 + 40    # 14:40 = 880分钟
LATE_SNEAK_END = 15 * 60          # 15:00 = 900分钟

# ==========================================
# 涨跌停阈值
# ==========================================
LIMIT_UP_MAIN = 0.10               # 主板涨停幅度（10%）
LIMIT_UP_GEM = 0.20                # 创业板/科创板涨停幅度（20%）
LIMIT_UP_ST = 0.05                 # ST股涨停幅度（5%）

LIMIT_DOWN_MAIN = -0.10            # 主板跌停幅度（-10%）
LIMIT_DOWN_GEM = -0.20             # 创业板/科创板跌停幅度（-20%）
LIMIT_DOWN_ST = -0.05              # ST股跌停幅度（-5%）

# ==========================================
# 风险控制阈值
# ==========================================
MAX_SINGLE_LOSS_RATIO = 0.02      # 单笔交易最大亏损（2%）
MAX_TOTAL_POSITION = 0.8           # 最大总仓位（80%）
DEFAULT_STOP_LOSS_RATIO = 0.05    # 默认止损比例（5%）

# ==========================================
# 数据缓存设置
# ==========================================
CACHE_EXPIRE_SECONDS = 10         # 缓存过期时间（秒）
KLINE_CACHE_DAYS = 30             # K线缓存天数

# ==========================================
# UI 显示设置
# ==========================================
MAX_DISPLAY_STOCKS = 20           # 最大显示股票数
REFRESH_INTERVAL = 30             # 自动刷新间隔（秒）

# ==========================================
# 日志设置
# ==========================================
LOG_LEVEL = 'INFO'                 # 日志级别
LOG_FILE = 'logs/app.log'          # 日志文件路径
LOG_MAX_SIZE = 10 * 1024 * 1024    # 日志文件最大大小（10MB）
LOG_BACKUP_COUNT = 5               # 日志备份数量

# ==========================================
# API 设置
# ==========================================
AKSHARE_RETRY_TIMES = 3           # AkShare 重试次数
AKSHARE_RETRY_DELAY = 1.0         # AkShare 重试延迟（秒）

# ==========================================
# 辅助函数
# ==========================================
def get_limit_up_threshold(code):
    """
    根据股票代码获取涨停阈值
    
    Args:
        code: 股票代码（可能包含 sh/sz/ST 前缀）
    
    Returns:
        float: 涨停阈值（如 0.10 表示 10%）
    """
    original_code = str(code)
    
    # 判断是否是 ST 股（在清洗之前）
    is_st = 'ST' in original_code.upper()
    
    # 清洗代码
    from logic.utils import Utils
    code = Utils.clean_stock_code(code)
    
    if code.startswith(('30', '68')):
        return LIMIT_UP_GEM
    elif is_st:
        return LIMIT_UP_ST
    else:
        return LIMIT_UP_MAIN


def get_limit_down_threshold(code):
    """
    根据股票代码获取跌停阈值
    
    Args:
        code: 股票代码（可能包含 sh/sz/ST 前缀）
    
    Returns:
        float: 跌停阈值（如 -0.10 表示 -10%）
    """
    original_code = str(code)
    
    # 判断是否是 ST 股（在清洗之前）
    is_st = 'ST' in original_code.upper()
    
    # 清洗代码
    from logic.utils import Utils
    code = Utils.clean_stock_code(code)
    
    if code.startswith(('30', '68')):
        return LIMIT_DOWN_GEM
    elif is_st:
        return LIMIT_DOWN_ST
    else:
        return LIMIT_DOWN_MAIN


def is_trading_time(current_time_minutes=None):
    """
    判断当前是否在交易时间
    
    Args:
        current_time_minutes: 当前时间（分钟数，如 570 表示 9:30）
    
    Returns:
        bool: 是否在交易时间
    """
    from logic.utils import Utils
    
    if current_time_minutes is None:
        now = Utils.get_beijing_time()
        current_time_minutes = now.hour * 60 + now.minute
    
    # 上午交易时间
    if MORNING_TRADE_START <= current_time_minutes < MORNING_TRADE_END:
        return True
    
    # 下午交易时间
    if AFTERNOON_TRADE_START <= current_time_minutes < AFTERNOON_TRADE_END:
        return True
    
    return False


def get_time_weight(current_time_minutes=None):
    """
    获取时间权重（根据交易时段）
    
    Args:
        current_time_minutes: 当前时间（分钟数）
    
    Returns:
        float: 时间权重（0.0-1.0）
    """
    from logic.utils import Utils
    
    if current_time_minutes is None:
        now = Utils.get_beijing_time()
        current_time_minutes = now.hour * 60 + now.minute
    
    # 黄金时段：9:30-10:30
    if MORNING_TRADE_START <= current_time_minutes < MORNING_TRADE_START + 60:
        return 1.0
    
    # 激战时段：10:30-11:30
    elif MORNING_TRADE_START + 60 <= current_time_minutes < MORNING_TRADE_END:
        return 0.9
    
    # 下午开盘：13:00-14:00
    elif AFTERNOON_TRADE_START <= current_time_minutes <= AFTERNOON_TRADE_START + 60:
        return 0.7
    
    # 垃圾时间：14:00-14:40
    elif AFTERNOON_TRADE_START + 60 < current_time_minutes < LATE_SNEAK_START:
        return 0.4
    
    # 最后一击：14:40-15:00
    elif LATE_SNEAK_START <= current_time_minutes < AFTERNOON_TRADE_END:
        return 0.0
    
    return 0.0


# ==========================================
# 配置管理器（用于读取 config.json）
# ==========================================
class Config:
    """
    配置管理器
    从 config.json 文件读取动态配置
    """
    
    _instance = None
    _config_data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        import json
        import os
        
        config_path = 'config.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
                self._config_data = {}
        else:
            print(f"⚠️ 配置文件不存在: {config_path}")
            self._config_data = {}
    
    def get(self, key, default=None):
        """
        获取配置值
        
        Args:
            key: 配置键（支持嵌套，如 'database.path'）
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        if self._config_data is None:
            return default
        
        # 支持嵌套键（如 'database.path'）
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """
        设置配置值（仅内存中，不保存到文件）
        
        Args:
            key: 配置键
            value: 配置值
        """
        if self._config_data is None:
            self._config_data = {}
        
        # 支持嵌套键（如 'database.path'）
        keys = key.split('.')
        config = self._config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_watchlist(self):
        """
        获取监控池（自选股）列表
        
        Returns:
            list: 股票代码列表
        """
        return self.get('watchlist', [])
    
    def set_watchlist(self, watchlist):
        """
        设置监控池（自选股）列表
        
        Args:
            watchlist: 股票代码列表
        
        Returns:
            bool: 是否成功
        """
        try:
            import json
            import os
            
            # 更新内存中的配置
            self.set('watchlist', watchlist)
            
            # 保存到配置文件
            config_path = 'config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {}
            
            # 更新配置
            config_data['watchlist'] = watchlist
            
            # 保存到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"⚠️ 设置监控池失败: {e}")
            return False


# 创建全局配置实例
config = Config()