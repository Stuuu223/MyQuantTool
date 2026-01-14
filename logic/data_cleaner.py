"""
数据清洗模块

统一处理股票数据的标准化和清洗工作
包括：手/股换算、涨跌幅阈值、停牌标记等
"""

from logic.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """
    数据清洗器
    
    功能：
    1. 统一手/股换算逻辑
    2. 统一涨跌幅阈值（ST/科创/创业）
    3. 统一停牌/复牌标记
    4. 数据质量检查（异常值过滤）
    """
    
    # 涨跌幅阈值常量
    LIMIT_UP_THRESHOLD_MAIN = 9.5      # 主板涨停阈值
    LIMIT_UP_THRESHOLD_ST = 4.5        # ST股涨停阈值
    LIMIT_UP_THRESHOLD_20CM = 19.5     # 20cm涨停阈值（创业板/科创板）
    
    # 涨跌幅下限
    LIMIT_DOWN_THRESHOLD_MAIN = -9.5   # 主板跌停阈值
    LIMIT_DOWN_THRESHOLD_ST = -4.5     # ST股跌停阈值
    LIMIT_DOWN_THRESHOLD_20CM = -19.5  # 20cm跌停阈值
    
    @staticmethod
    def clean_stock_code(code):
        """
        清洗股票代码，确保格式统一（6位数字）
        
        Args:
            code: 股票代码（可能是 'sh600000'、'600000'、'000001' 等格式）
        
        Returns:
            str: 标准化的6位股票代码
        """
        if not code:
            return None
        
        # 移除前缀
        code = code.replace('sh', '').replace('sz', '').replace('SH', '').replace('SZ', '')
        
        # 确保是6位数字
        if len(code) == 6 and code.isdigit():
            return code
        
        return None
    
    @staticmethod
    def is_20cm_stock(code):
        """
        判断是否为20cm股票（创业板/科创板）
        
        Args:
            code: 股票代码（6位数字）
        
        Returns:
            bool: 是否为20cm股票
        """
        if not code or len(code) != 6:
            return False
        
        # 创业板：30开头
        # 科创板：68开头
        return code.startswith('30') or code.startswith('68')
    
    @staticmethod
    def is_st_stock(name):
        """
        判断是否为ST股票
        
        Args:
            name: 股票名称
        
        Returns:
            bool: 是否为ST股票
        """
        if not name:
            return False
        
        return 'ST' in name.upper() or '*ST' in name.upper()
    
    @staticmethod
    def get_limit_thresholds(code, name):
        """
        获取股票的涨跌幅阈值
        
        Args:
            code: 股票代码（6位数字）
            name: 股票名称
        
        Returns:
            dict: {'limit_up': 涨停阈值, 'limit_down': 跌停阈值}
        """
        # 判断是否为ST
        is_st = DataCleaner.is_st_stock(name)
        
        # 判断是否为20cm
        is_20cm = DataCleaner.is_20cm_stock(code)
        
        if is_st:
            return {
                'limit_up': DataCleaner.LIMIT_UP_THRESHOLD_ST,
                'limit_down': DataCleaner.LIMIT_DOWN_THRESHOLD_ST,
                'type': 'ST'
            }
        elif is_20cm:
            return {
                'limit_up': DataCleaner.LIMIT_UP_THRESHOLD_20CM,
                'limit_down': DataCleaner.LIMIT_DOWN_THRESHOLD_20CM,
                'type': '20CM'
            }
        else:
            return {
                'limit_up': DataCleaner.LIMIT_UP_THRESHOLD_MAIN,
                'limit_down': DataCleaner.LIMIT_DOWN_THRESHOLD_MAIN,
                'type': 'MAIN'
            }
    
    @staticmethod
    def check_limit_status(code, name, current_pct):
        """
        检查股票的涨跌停状态
        
        Args:
            code: 股票代码（6位数字）
            name: 股票名称
            current_pct: 当前涨跌幅（百分比）
        
        Returns:
            dict: {
                'is_limit_up': 是否涨停,
                'is_limit_down': 是否跌停,
                'status': 状态描述,
                'thresholds': 涨跌幅阈值
            }
        """
        thresholds = DataCleaner.get_limit_thresholds(code, name)
        
        is_limit_up = current_pct >= thresholds['limit_up']
        is_limit_down = current_pct <= thresholds['limit_down']
        
        # 判断状态描述
        if is_limit_up:
            status = "涨停封死"
        elif is_limit_down:
            status = "跌停封死"
        elif DataCleaner.is_20cm_stock(code) and 10.0 <= current_pct < 19.5:
            status = "半路板（加速逼空）"
        elif current_pct > 0:
            status = "上涨"
        elif current_pct < 0:
            status = "下跌"
        else:
            status = "平盘"
        
        return {
            'is_limit_up': is_limit_up,
            'is_limit_down': is_limit_down,
            'status': status,
            'thresholds': thresholds
        }
    
    @staticmethod
    def convert_volume_to_shares(volume, unit='shares'):
        """
        统一成交量换算，统一转为手数
        
        Args:
            volume: 成交量
            unit: 原始单位 ('shares' 股数, 'hands' 手数, 'lots' 手数)
        
        Returns:
            float: 手数（1手 = 100股）
        """
        if volume is None or volume == 0:
            return 0
        
        if unit in ['shares', '股']:
            # 股数转手数
            return volume / 100
        elif unit in ['hands', 'lots', '手']:
            # 已经是手数
            return volume
        else:
            logger.warning(f"未知的成交量单位: {unit}")
            return volume / 100
    
    @staticmethod
    def convert_amount_to_wan(amount, unit='yuan'):
        """
        统一成交额换算，统一转为万元
        
        Args:
            amount: 成交额
            unit: 原始单位 ('yuan' 元, 'wan' 万元, 'yi' 亿元)
        
        Returns:
            float: 万元
        """
        if amount is None or amount == 0:
            return 0
        
        if unit in ['yuan', '元']:
            # 元转万元
            return amount / 10000
        elif unit in ['wan', '万元']:
            # 已经是万元
            return amount
        elif unit in ['yi', '亿元']:
            # 亿元转万元
            return amount * 10000
        else:
            logger.warning(f"未知的成交额单位: {unit}")
            return amount / 10000
    
    @staticmethod
    def validate_price(price):
        """
        验证价格数据是否有效
        
        Args:
            price: 价格
        
        Returns:
            bool: 价格是否有效
        """
        if price is None:
            return False
        
        if not isinstance(price, (int, float)):
            return False
        
        if price <= 0:
            return False
        
        if price > 10000:  # 股价不可能超过1万元
            logger.warning(f"价格异常: {price}")
            return False
        
        return True
    
    @staticmethod
    def validate_volume(volume):
        """
        验证成交量数据是否有效
        
        Args:
            volume: 成交量（股数）
        
        Returns:
            bool: 成交量是否有效
        """
        if volume is None:
            return False
        
        if not isinstance(volume, (int, float)):
            return False
        
        if volume < 0:
            return False
        
        if volume > 1e10:  # 成交量不可能超过100亿股
            logger.warning(f"成交量异常: {volume}")
            return False
        
        return True
    
    @staticmethod
    def clean_realtime_data(data):
        """
        清洗实时行情数据
        
        Args:
            data: 原始实时数据字典
        
        Returns:
            dict: 清洗后的数据
        """
        if not data:
            return None
        
        cleaned = {}
        
        # 清洗股票代码
        code = DataCleaner.clean_stock_code(data.get('code', ''))
        if not code:
            return None
        cleaned['code'] = code
        
        # 清洗股票名称
        cleaned['name'] = data.get('name', '')
        
        # 清洗价格数据
        price_fields = {
            'now': '最新价',
            'open': '开盘价',
            'close': '昨收价',
            'high': '最高价',
            'low': '最低价',
            'bid1': '买一价',
            'ask1': '卖一价',
            'bid2': '买二价',
            'ask2': '卖二价',
            'bid3': '买三价',
            'ask3': '卖三价',
            'bid4': '买四价',
            'ask4': '卖四价',
            'bid5': '买五价',
            'ask5': '卖五价'
        }
        
        for field, display_name in price_fields.items():
            value = data.get(field)
            if DataCleaner.validate_price(value):
                cleaned[field] = float(value)
            else:
                cleaned[field] = 0.0
        
        # 清洗成交量数据（统一转为股数）
        volume_fields = {
            'volume': '成交量',
            'turnover': '成交额',
            'bid1_volume': '买一量',
            'ask1_volume': '卖一量',
            'bid2_volume': '买二量',
            'ask2_volume': '卖二量',
            'bid3_volume': '买三量',
            'ask3_volume': '卖三量',
            'bid4_volume': '买四量',
            'ask4_volume': '卖四量',
            'bid5_volume': '买五量',
            'ask5_volume': '卖五量'
        }
        
        for field, display_name in volume_fields.items():
            value = data.get(field)
            if DataCleaner.validate_volume(value):
                cleaned[field] = float(value)
            else:
                cleaned[field] = 0.0
        
        # 计算涨跌幅
        if cleaned.get('now', 0) > 0 and cleaned.get('close', 0) > 0:
            cleaned['change_pct'] = (cleaned['now'] - cleaned['close']) / cleaned['close'] * 100
        else:
            cleaned['change_pct'] = 0.0
        
        # 判断涨跌停状态
        limit_status = DataCleaner.check_limit_status(
            cleaned['code'],
            cleaned['name'],
            cleaned['change_pct']
        )
        cleaned['limit_status'] = limit_status
        
        return cleaned
    
    @staticmethod
    def calculate_volume_ratio(current_volume, avg_volume):
        """
        计算量比
        
        Args:
            current_volume: 当前成交量（手数）
            avg_volume: 平均成交量（手数）
        
        Returns:
            float: 量比
        """
        if avg_volume is None or avg_volume == 0:
            return 1.0
        
        if current_volume is None or current_volume == 0:
            return 0.0
        
        return current_volume / avg_volume