"""
格式化工具模块
提供统一的格式化函数
"""


class Formatter:
    """格式化工具类"""

    @staticmethod
    def format_price(price):
        """
        格式化价格显示
        
        Args:
            price: 价格数值
            
        Returns:
            格式化后的价格字符串
        """
        if price is None:
            return "-"
        return f"¥{price:.2f}"

    @staticmethod
    def format_amount(amount):
        """
        格式化金额显示，自动转换为万或亿单位
        
        Args:
            amount: 金额数值
            
        Returns:
            格式化后的金额字符串
        """
        if amount is None:
            return "-"
        
        abs_amount = abs(amount)
        if abs_amount >= 100000000:  # 1亿以上
            return f"¥{amount/100000000:.2f}亿"
        elif abs_amount >= 10000:  # 1万以上
            return f"¥{amount/10000:.2f}万"
        else:
            return f"¥{amount:.0f}"

    @staticmethod
    def format_amount_no_symbol(amount):
        """
        格式化金额显示（不带货币符号），自动转换为万或亿单位
        
        Args:
            amount: 金额数值
            
        Returns:
            格式化后的金额字符串
        """
        if amount is None:
            return "-"
        
        abs_amount = abs(amount)
        if abs_amount >= 100000000:  # 1亿以上
            return f"{amount/100000000:.2f}亿"
        elif abs_amount >= 10000:  # 1万以上
            return f"{amount/10000:.2f}万"
        else:
            return f"{amount:.0f}"

    @staticmethod
    def format_percentage(value, decimal_places=2):
        """
        格式化百分比显示
        
        Args:
            value: 百分比数值（如 0.05 表示 5%）
            decimal_places: 小数位数
            
        Returns:
            格式化后的百分比字符串
        """
        if value is None:
            return "-"
        return f"{value * 100:.{decimal_places}f}%"

    @staticmethod
    def format_change(change_pct):
        """
        格式化涨跌幅显示（带颜色标记）
        
        Args:
            change_pct: 涨跌幅数值（如 0.05 表示 5%）
            
        Returns:
            格式化后的涨跌幅字符串
        """
        if change_pct is None:
            return "-"
        
        sign = "+" if change_pct > 0 else ""
        return f"{sign}{change_pct * 100:.2f}%"

    @staticmethod
    def format_volume(volume):
        """
        格式化成交量显示
        
        Args:
            volume: 成交量数值
            
        Returns:
            格式化后的成交量字符串
        """
        if volume is None:
            return "-"
        
        abs_volume = abs(volume)
        if abs_volume >= 100000000:  # 1亿手以上
            return f"{volume/100000000:.2f}亿手"
        elif abs_volume >= 10000:  # 1万手以上
            return f"{volume/10000:.2f}万手"
        else:
            return f"{volume:.0f}手"

    @staticmethod
    def format_number(number, decimal_places=2):
        """
        格式化数字显示（千分位分隔）
        
        Args:
            number: 数值
            decimal_places: 小数位数
            
        Returns:
            格式化后的数字字符串
        """
        if number is None:
            return "-"
        return f"{number:,.{decimal_places}f}"

    @staticmethod
    def format_ratio(value, decimal_places=2):
        """
        格式化比例显示
        
        Args:
            value: 比例数值（如 0.5 表示 50%）
            decimal_places: 小数位数
            
        Returns:
            格式化后的比例字符串
        """
        if value is None:
            return "-"
        return f"{value * 100:.{decimal_places}f}%"

    @staticmethod
    def format_date(date):
        """
        格式化日期显示
        
        Args:
            date: 日期对象或字符串
            
        Returns:
            格式化后的日期字符串
        """
        if date is None:
            return "-"
        
        if isinstance(date, str):
            return date
        
        return date.strftime("%Y-%m-%d")

    @staticmethod
    def format_datetime(datetime_obj):
        """
        格式化日期时间显示
        
        Args:
            datetime_obj: 日期时间对象
            
        Returns:
            格式化后的日期时间字符串
        """
        if datetime_obj is None:
            return "-"
        
        return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_rank(rank, total=None):
        """
        格式化排名显示
        
        Args:
            rank: 排名
            total: 总数（可选）
            
        Returns:
            格式化后的排名字符串
        """
        if rank is None:
            return "-"
        
        if total is not None:
            return f"{rank}/{total}"
        
        return f"第{rank}名"

    @staticmethod
    def format_score(score, max_score=100):
        """
        格式化评分显示
        
        Args:
            score: 评分
            max_score: 满分
            
        Returns:
            格式化后的评分字符串
        """
        if score is None:
            return "-"
        
        percentage = score / max_score * 100
        return f"{score:.0f}/{max_score} ({percentage:.0f}%)"

    @staticmethod
    def format_duration(seconds):
        """
        格式化时长显示
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化后的时长字符串
        """
        if seconds is None:
            return "-"
        
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"

    @staticmethod
    def format_distance(value, unit=""):
        """
        格式化距离显示
        
        Args:
            value: 数值
            unit: 单位
            
        Returns:
            格式化后的距离字符串
        """
        if value is None:
            return "-"
        
        sign = "+" if value > 0 else ""
        return f"{sign}{value * 100:.2f}%{unit}"

    @staticmethod
    def get_color_class(value, threshold_zero=0, threshold_positive=0, threshold_negative=0):
        """
        根据数值返回颜色类名
        
        Args:
            value: 数值
            threshold_zero: 零阈值
            threshold_positive: 正值阈值
            threshold_negative: 负值阈值
            
        Returns:
            颜色类名
        """
        if value is None:
            return "text-gray"
        
        if value > threshold_positive:
            return "text-red"  # 涨幅用红色
        elif value < threshold_negative:
            return "text-green"  # 跌幅用绿色
        else:
            return "text-gray"  # 平盘用灰色

    @staticmethod
    def format_with_color(value, formatter_func=None):
        """
        格式化数值并返回带颜色标记的字符串
        
        Args:
            value: 数值
            formatter_func: 格式化函数
            
        Returns:
            格式化后的字符串（带颜色标记）
        """
        if value is None:
            return "-"
        
        # 格式化数值
        if formatter_func:
            formatted = formatter_func(value)
        else:
            formatted = str(value)
        
        # 添加颜色标记
        if value > 0:
            return f"🔺 {formatted}"
        elif value < 0:
            return f"🔻 {formatted}"
        else:
            return f"➖ {formatted}"