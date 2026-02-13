# -*- coding: utf-8 -*-
"""
统一代码格式转换器

功能：
- 在不同数据源之间转换股票代码格式
- 支持 QMT、AkShare、EasyQuotation 等多种格式

Author: iFlow CLI
Date: 2026-01-28
Version: V1.0
"""


class CodeConverter:
    """
    统一代码格式转换器

    支持的格式：
    - QMT: 600030.SH / 300750.SZ / 832566.BJ
    - AkShare: 600030 / 300750
    - EasyQuotation: sh600030 / sz300750
    - 标准格式: 600030 / 300750 (不带后缀)
    """

    @staticmethod
    def to_qmt(code: str) -> str:
        """
        转换为 QMT 格式 (######.SH/SZ/BJ)

        Args:
            code: 任意格式的股票代码

        Returns:
            QMT 格式的股票代码

        Examples:
            >>> CodeConverter.to_qmt('600030')
            '600030.SH'
            >>> CodeConverter.to_qmt('sh600030')
            '600030.SH'
            >>> CodeConverter.to_qmt('600030.SH')
            '600030.SH'
            >>> CodeConverter.to_qmt('300750')
            '300750.SZ'
        """
        if not code:
            return code

        code = str(code).strip()

        # 🔥 修复：如果已经是 QMT 格式，直接返回
        # QMT 格式特征：6位数字 + 交易所后缀
        import re
        if re.match(r'^\d{6}\.[A-Z]{2}$', code):
            return code

        # 清理代码（移除所有点，但只在不是 QMT 格式时执行）
        code = code.replace('.', '')

        # 提取纯数字代码
        if code.startswith('sh'):
            stock_code = code[2:]
        elif code.startswith('sz'):
            stock_code = code[2:]
        elif code.startswith('bj'):
            stock_code = code[2:]
        else:
            stock_code = code

        # 判断交易所并添加后缀
        if stock_code.startswith('6'):
            return f"{stock_code}.SH"
        elif stock_code.startswith(('0', '3')):
            return f"{stock_code}.SZ"
        elif stock_code.startswith(('8', '4')):
            return f"{stock_code}.BJ"  # 北交所
        else:
            # 默认为主板
            return f"{stock_code}.SH"

    @staticmethod
    def to_akshare(code: str) -> str:
        """
        转换为 AkShare 格式 (6位数字)

        Args:
            code: 任意格式的股票代码

        Returns:
            AkShare 格式的股票代码

        Examples:
            >>> CodeConverter.to_akshare('600030.SH')
            '600030'
            >>> CodeConverter.to_akshare('sh600030')
            '600030'
            >>> CodeConverter.to_akshare('600030')
            '600030'
        """
        if not code:
            return code

        # 移除所有非数字字符
        import re
        stock_code = re.sub(r'[^0-9]', '', str(code))

        # 确保是6位
        if len(stock_code) >= 6:
            return stock_code[:6]
        else:
            return stock_code

    @staticmethod
    def to_easyquotation(code: str) -> str:
        """
        转换为 EasyQuotation 格式 (sh###### / sz######)

        Args:
            code: 任意格式的股票代码

        Returns:
            EasyQuotation 格式的股票代码

        Examples:
            >>> CodeConverter.to_easyquotation('600030.SH')
            'sh600030'
            >>> CodeConverter.to_easyquotation('600030')
            'sh600030'
            >>> CodeConverter.to_easyquotation('300750')
            'sz300750'
        """
        if not code:
            return code

        # 先转为标准格式
        stock_code = CodeConverter.to_akshare(code)

        # 添加交易所前缀
        if stock_code.startswith('6'):
            return f"sh{stock_code}"
        elif stock_code.startswith(('0', '3')):
            return f"sz{stock_code}"
        elif stock_code.startswith(('8', '4')):
            return f"bj{stock_code}"
        else:
            return f"sh{stock_code}"

    @staticmethod
    def to_standard(code: str) -> str:
        """
        转换为标准格式 (6位数字，不带后缀)

        Args:
            code: 任意格式的股票代码

        Returns:
            标准格式的股票代码

        Examples:
            >>> CodeConverter.to_standard('600030.SH')
            '600030'
            >>> CodeConverter.to_standard('sh600030')
            '600030'
        """
        return CodeConverter.to_akshare(code)

    @staticmethod
    def get_market(code: str) -> str:
        """
        获取股票所属市场

        Args:
            code: 股票代码

        Returns:
            市场代码 (SH/SZ/BJ)

        Examples:
            >>> CodeConverter.get_market('600030')
            'SH'
            >>> CodeConverter.get_market('300750')
            'SZ'
        """
        stock_code = CodeConverter.to_standard(code)

        if stock_code.startswith('6'):
            return 'SH'
        elif stock_code.startswith(('0', '3')):
            return 'SZ'
        elif stock_code.startswith(('8', '4')):
            return 'BJ'
        else:
            return 'SH'

    @staticmethod
    def is_shanghai(code: str) -> bool:
        """判断是否为沪市股票"""
        return CodeConverter.get_market(code) == 'SH'

    @staticmethod
    def is_shenzhen(code: str) -> bool:
        """判断是否为深市股票"""
        return CodeConverter.get_market(code) == 'SZ'

    @staticmethod
    def is_beijing(code: str) -> bool:
        """判断是否为北交所股票"""
        return CodeConverter.get_market(code) == 'BJ'

    @staticmethod
    def is_20cm(code: str) -> bool:
        """
        判断是否为20cm涨跌幅限制的股票

        Returns:
            bool: 是否为20cm (创业板/科创板)
        """
        stock_code = CodeConverter.to_standard(code)
        return stock_code.startswith(('3', '688'))

    @staticmethod
    def is_30cm(code: str) -> bool:
        """
        判断是否为30cm涨跌幅限制的股票

        Returns:
            bool: 是否为30cm (北交所)
        """
        return CodeConverter.is_beijing(code)

    @staticmethod
    def batch_convert(codes: list, target_format: str = 'qmt') -> list:
        """
        批量转换股票代码格式

        Args:
            codes: 股票代码列表
            target_format: 目标格式 (qmt/akshare/easyquotation/standard)

        Returns:
            转换后的代码列表
        """
        converter_map = {
            'qmt': CodeConverter.to_qmt,
            'akshare': CodeConverter.to_akshare,
            'easyquotation': CodeConverter.to_easyquotation,
            'standard': CodeConverter.to_standard,
        }

        converter = converter_map.get(target_format, CodeConverter.to_standard)
        return [converter(code) for code in codes]


# 便捷函数
to_qmt = CodeConverter.to_qmt
to_akshare = CodeConverter.to_akshare
to_easyquotation = CodeConverter.to_easyquotation
to_standard = CodeConverter.to_standard


if __name__ == "__main__":
    # 测试代码转换
    print("=" * 60)
    print("🧪 代码格式转换测试")
    print("=" * 60)

    test_codes = ['600519', 'sh600519', '600519.SH', '300750', 'sz300750', '832566']

    print("\n📝 转换为 QMT 格式:")
    for code in test_codes:
        print(f"  {code:12s} -> {CodeConverter.to_qmt(code)}")

    print("\n📝 转换为 AkShare 格式:")
    for code in test_codes:
        print(f"  {code:12s} -> {CodeConverter.to_akshare(code)}")

    print("\n📝 转换为 EasyQuotation 格式:")
    for code in test_codes:
        print(f"  {code:12s} -> {CodeConverter.to_easyquotation(code)}")

    print("\n📝 市场判断:")
    for code in ['600519', '300750', '832566']:
        print(f"  {code:6s} -> {CodeConverter.get_market(code)} ({'20cm' if CodeConverter.is_20cm(code) else '10cm'})")

    print("\n✅ 测试完成")
    print("=" * 60)