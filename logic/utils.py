#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V10 系统通用工具模块
提取所有脏活累活，避免代码重复
"""

import pandas as pd
from datetime import datetime
import pytz
import re


class Utils:
    """通用工具类"""
    
    # 🆕 Bug B 修复：服务器时间偏移量（秒）
    _time_offset = 0.0  # 本地时间与服务器时间的偏移量
    _last_sync_time = None  # 上次同步时间
    
    @staticmethod
    def safe_float(value, default=0.0):
        """
        安全转浮点数，处理 None/NaN/空字符串
        
        Args:
            value: 待转换的值
            default: 默认值
        
        Returns:
            float: 转换后的浮点数
        """
        try:
            if value is None or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value, default=0):
        """
        安全转整数，处理 None/NaN/空字符串
        
        Args:
            value: 待转换的值
            default: 默认值
        
        Returns:
            int: 转换后的整数
        """
        try:
            if value is None or value == '':
                return default
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def calculate_amount(volume_lots, price):
        """
        统一计算金额：手 -> 元
        
        Args:
            volume_lots: 手数
            price: 价格（元/股）
        
        Returns:
            float: 金额（元）
        """
        # 1手 = 100股
        return Utils.safe_float(volume_lots) * 100 * Utils.safe_float(price)
    
    @staticmethod
    def get_beijing_time():
        """
        统一获取北京时间（Bug B 修复：支持服务器时间对齐）
        
        Returns:
            datetime: 北京时间的datetime对象
        """
        try:
            # 尝试使用 pytz
            utc_now = datetime.now(pytz.utc)
            beijing_tz = pytz.timezone('Asia/Shanghai')
            beijing_time = utc_now.astimezone(beijing_tz)
            
            # 🆕 Bug B 修复：应用服务器时间偏移量
            if Utils._time_offset != 0.0:
                beijing_time = beijing_time + pd.Timedelta(seconds=Utils._time_offset)
            
            return beijing_time
        except ImportError:
            # 如果没有 pytz，假设系统是本地时间
            now = datetime.now()
            # 如果小时数 < 8，可能是 UTC 时间，转换为北京时间（+8 小时）
            if now.hour < 8:
                now = now.replace(hour=now.hour + 8)
            
            # 🆕 Bug B 修复：应用服务器时间偏移量
            if Utils._time_offset != 0.0:
                now = now + pd.Timedelta(seconds=Utils._time_offset)
            
            return now
    
    @staticmethod
    def sync_server_time(stock_time: str):
        """
        🆕 Bug B 修复：从行情数据中提取服务器时间并计算偏移量
        
        Args:
            stock_time: 股票数据中的时间字符串（格式：HH:MM:SS）
        """
        try:
            # 解析服务器时间
            server_time = datetime.strptime(stock_time, '%H:%M:%S').time()
            
            # 获取当前本地时间
            local_time = Utils.get_beijing_time().time()
            
            # 计算时间差（秒）
            local_seconds = local_time.hour * 3600 + local_time.minute * 60 + local_time.second
            server_seconds = server_time.hour * 3600 + server_time.minute * 60 + server_time.second
            
            # 计算偏移量（如果差异超过 2 秒，才更新）
            time_diff = server_seconds - local_seconds
            
            # 处理跨天情况
            if time_diff > 43200:  # 超过 12 小时，说明服务器时间是第二天
                time_diff -= 86400
            elif time_diff < -43200:  # 小于 -12 小时，说明本地时间是第二天
                time_diff += 86400
            
            # 只有当时间差超过 2 秒时才更新偏移量
            if abs(time_diff) > 2:
                Utils._time_offset = time_diff
                Utils._last_sync_time = datetime.now()
                print(f"🕐 [时间同步] 本地时间与服务器时间偏差 {time_diff:.2f} 秒，已自动校准")
        except Exception as e:
            print(f"⚠️ [时间同步失败] {e}")
    
    @staticmethod
    def format_number(num, precision=2):
        """
        统一把数字转成 1.2亿 或 5000万 的格式
        
        Args:
            num: 数字
            precision: 小数位数
        
        Returns:
            str: 格式化后的字符串
        """
        num = Utils.safe_float(num, 0)
        
        if num >= 1_0000_0000:  # 亿
            return f"{num/1_0000_0000:.{precision}f}亿"
        elif num >= 1_0000:  # 万
            return f"{num/1_0000:.{precision}f}万"
        else:
            return f"{num:.{precision}f}"
    
    @staticmethod
    def format_percentage(pct, precision=2):
        """
        格式化百分比
        
        Args:
            pct: 百分比值（如 0.05 表示 5%）
            precision: 小数位数
        
        Returns:
            str: 格式化后的百分比字符串
        """
        return f"{Utils.safe_float(pct) * 100:.{precision}f}%"
    
    @staticmethod
    def clean_stock_code(code):
        """
        清洗股票代码，统一格式
        
        Args:
            code: 股票代码（可能包含 sh/sz 前缀）
        
        Returns:
            str: 清洗后的股票代码（6位数字）
        """
        if not code:
            return ''
        # 移除 sh/sz 前缀
        code = str(code).replace('sh', '').replace('sz', '')
        # 移除非数字字符
        code = re.sub(r'[^\d]', '', code)
        # 补齐到6位
        return code.zfill(6)
    
    @staticmethod
    def is_limit_up(change_pct, code):
        """
        判断是否涨停
        
        Args:
            change_pct: 涨跌幅（如 0.10 表示 10%，0.098 表示 9.8%）
            code: 股票代码（可能包含 sh/sz/ST 前缀）
        
        Returns:
            bool: 是否涨停
        """
        change_pct = Utils.safe_float(change_pct)
        original_code = str(code)
        
        # 判断是否是 ST 股（在清洗之前）
        is_st = 'ST' in original_code.upper()
        
        # 清洗代码
        code = Utils.clean_stock_code(code)
        
        # 创业板/科创板：20% 涨停
        if code.startswith(('30', '68')):
            return change_pct >= 0.198  # 19.8%涨停
        # ST股：5% 涨停
        elif is_st:
            return change_pct >= 0.048   # 4.8%涨停
        else:
            # 主板：10% 涨停
            return change_pct >= 0.098   # 9.8%涨停
    
    @staticmethod
    def is_limit_down(change_pct, code):
        """
        判断是否跌停
        
        Args:
            change_pct: 涨跌幅（如 -0.10 表示 -10%，-0.098 表示 -9.8%）
            code: 股票代码（可能包含 sh/sz/ST 前缀）
        
        Returns:
            bool: 是否跌停
        """
        change_pct = Utils.safe_float(change_pct)
        original_code = str(code)
        
        # 判断是否是 ST 股（在清洗之前）
        is_st = 'ST' in original_code.upper()
        
        # 清洗代码
        code = Utils.clean_stock_code(code)
        
        # 创业板/科创板：20% 跌停
        if code.startswith(('30', '68')):
            return change_pct <= -0.198  # 19.8%跌停
        # ST股：5% 跌停
        elif is_st:
            return change_pct <= -0.048   # 4.8%跌停
        else:
            # 主板：10% 跌停
            return change_pct <= -0.098   # 9.8%跌停
    
    @staticmethod
    def calculate_ma(data, period):
        """
        计算移动平均线
        
        Args:
            data: 价格序列（list或Series）
            period: 周期
        
        Returns:
            float: MA值，如果数据不足返回None
        """
        if len(data) < period:
            return None
        return sum(data[-period:]) / period
    
    @staticmethod
    def truncate_string(text, max_length=50, suffix='...'):
        """
        截断字符串
        
        Args:
            text: 原字符串
            max_length: 最大长度
            suffix: 后缀
        
        Returns:
            str: 截断后的字符串
        """
        if not text:
            return ''
        text = str(text)
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def safe_divide(a, b, default=0.0):
        """
        安全除法，避免除零错误
        
        Args:
            a: 被除数
            b: 除数
            default: 默认值
        
        Returns:
            float: 除法结果
        """
        try:
            b = Utils.safe_float(b, 0)
            if b == 0:
                return default
            return Utils.safe_float(a, 0) / b
        except (ValueError, TypeError, ZeroDivisionError):
            return default
    
    @staticmethod
    def format_timestamp(timestamp):
        """
        格式化时间戳
        
        Args:
            timestamp: 时间戳（秒或毫秒）
        
        Returns:
            str: 格式化后的时间字符串
        """
        try:
            ts = Utils.safe_float(timestamp, 0)
            # 如果是毫秒时间戳，转换为秒
            if ts > 1_000_000_0000:  # 毫秒时间戳
                ts = ts / 1000
            
            dt = datetime.fromtimestamp(ts)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, OSError):
            return '未知时间'
    
    @staticmethod
    def get_color_by_value(value, thresholds):
        """
        根据数值返回颜色
        
        Args:
            value: 数值
            thresholds: 颜色阈值字典，如 {'high': 80, 'low': 30}
        
        Returns:
            str: 颜色名称
        """
        value = Utils.safe_float(value)
        
        if value >= thresholds.get('high', 100):
            return 'red'
        elif value <= thresholds.get('low', 0):
            return 'green'
        else:
            return 'orange'