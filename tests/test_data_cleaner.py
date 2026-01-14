"""
单元测试 - DataCleaner 模块

测试数据清洗器的所有功能
"""

import unittest
from logic.data_cleaner import DataCleaner


class TestDataCleaner(unittest.TestCase):
    """测试 DataCleaner 类"""
    
    def test_clean_stock_code(self):
        """测试股票代码清洗"""
        # 测试各种格式的股票代码
        self.assertEqual(DataCleaner.clean_stock_code('sh600000'), '600000')
        self.assertEqual(DataCleaner.clean_stock_code('sz000001'), '000001')
        self.assertEqual(DataCleaner.clean_stock_code('600000'), '600000')
        self.assertEqual(DataCleaner.clean_stock_code('000001'), '000001')
        self.assertIsNone(DataCleaner.clean_stock_code(''))
        self.assertIsNone(DataCleaner.clean_stock_code('abc123'))
        self.assertIsNone(DataCleaner.clean_stock_code('12345'))
    
    def test_is_20cm_stock(self):
        """测试20cm股票判断"""
        # 创业板
        self.assertTrue(DataCleaner.is_20cm_stock('300000'))
        self.assertTrue(DataCleaner.is_20cm_stock('300773'))
        # 科创板
        self.assertTrue(DataCleaner.is_20cm_stock('688000'))
        self.assertTrue(DataCleaner.is_20cm_stock('688047'))
        # 主板
        self.assertFalse(DataCleaner.is_20cm_stock('000001'))
        self.assertFalse(DataCleaner.is_20cm_stock('600000'))
        # 无效代码
        self.assertFalse(DataCleaner.is_20cm_stock(''))
        self.assertFalse(DataCleaner.is_20cm_stock('abc'))
    
    def test_is_st_stock(self):
        """测试ST股票判断"""
        self.assertTrue(DataCleaner.is_st_stock('ST平安'))
        self.assertTrue(DataCleaner.is_st_stock('*ST平安'))
        self.assertTrue(DataCleaner.is_st_stock('st pingan'))
        self.assertTrue(DataCleaner.is_st_stock('*st pingan'))
        self.assertFalse(DataCleaner.is_st_stock('平安银行'))
        self.assertFalse(DataCleaner.is_st_stock(''))
        self.assertFalse(DataCleaner.is_st_stock(None))
    
    def test_get_limit_thresholds(self):
        """测试涨跌幅阈值获取"""
        # 20cm股票
        thresholds_20cm = DataCleaner.get_limit_thresholds('300773', '拉卡拉')
        self.assertEqual(thresholds_20cm['limit_up'], 19.5)
        self.assertEqual(thresholds_20cm['limit_down'], -19.5)
        self.assertEqual(thresholds_20cm['type'], '20CM')
        
        # ST股票
        thresholds_st = DataCleaner.get_limit_thresholds('600000', 'ST平安')
        self.assertEqual(thresholds_st['limit_up'], 4.5)
        self.assertEqual(thresholds_st['limit_down'], -4.5)
        self.assertEqual(thresholds_st['type'], 'ST')
        
        # 主板股票
        thresholds_main = DataCleaner.get_limit_thresholds('000001', '平安银行')
        self.assertEqual(thresholds_main['limit_up'], 9.5)
        self.assertEqual(thresholds_main['limit_down'], -9.5)
        self.assertEqual(thresholds_main['type'], 'MAIN')
    
    def test_check_limit_status(self):
        """测试涨跌停状态检查"""
        # 20cm涨停
        status = DataCleaner.check_limit_status('300773', '拉卡拉', 20.01)
        self.assertTrue(status['is_limit_up'])
        self.assertFalse(status['is_limit_down'])
        self.assertEqual(status['status'], '涨停封死')
        
        # 20cm半路板
        status = DataCleaner.check_limit_status('300773', '拉卡拉', 15.22)
        self.assertFalse(status['is_limit_up'])
        self.assertFalse(status['is_limit_down'])
        self.assertEqual(status['status'], '半路板（加速逼空）')
        
        # 主板涨停
        status = DataCleaner.check_limit_status('000001', '平安银行', 10.01)
        self.assertTrue(status['is_limit_up'])
        self.assertFalse(status['is_limit_down'])
        self.assertEqual(status['status'], '涨停封死')
        
        # 跌停
        status = DataCleaner.check_limit_status('000001', 'ST平安', -5.01)
        self.assertFalse(status['is_limit_up'])
        self.assertTrue(status['is_limit_down'])
        self.assertEqual(status['status'], '跌停封死')
        
        # 正常上涨
        status = DataCleaner.check_limit_status('000001', '平安银行', 5.5)
        self.assertFalse(status['is_limit_up'])
        self.assertFalse(status['is_limit_down'])
        self.assertEqual(status['status'], '上涨')
    
    def test_convert_volume_to_shares(self):
        """测试成交量换算"""
        # 股数转手数
        self.assertEqual(DataCleaner.convert_volume_to_shares(10000, 'shares'), 100.0)
        self.assertEqual(DataCleaner.convert_volume_to_shares(100000, 'shares'), 1000.0)
        
        # 已经是手数
        self.assertEqual(DataCleaner.convert_volume_to_shares(100, 'hands'), 100.0)
        self.assertEqual(DataCleaner.convert_volume_to_shares(1000, 'lots'), 1000.0)
        
        # 无效数据
        self.assertEqual(DataCleaner.convert_volume_to_shares(0, 'shares'), 0.0)
        self.assertEqual(DataCleaner.convert_volume_to_shares(None, 'shares'), 0.0)
    
    def test_convert_amount_to_wan(self):
        """测试成交额换算"""
        # 元转万元
        self.assertEqual(DataCleaner.convert_amount_to_wan(1000000, 'yuan'), 100.0)
        self.assertEqual(DataCleaner.convert_amount_to_wan(10000000, 'yuan'), 1000.0)
        
        # 已经是万元
        self.assertEqual(DataCleaner.convert_amount_to_wan(100, 'wan'), 100.0)
        
        # 亿元转万元
        self.assertEqual(DataCleaner.convert_amount_to_wan(1, 'yi'), 10000.0)
        
        # 无效数据
        self.assertEqual(DataCleaner.convert_amount_to_wan(0, 'yuan'), 0.0)
        self.assertEqual(DataCleaner.convert_amount_to_wan(None, 'yuan'), 0.0)
    
    def test_validate_price(self):
        """测试价格验证"""
        # 有效价格
        self.assertTrue(DataCleaner.validate_price(10.5))
        self.assertTrue(DataCleaner.validate_price(100.0))
        self.assertTrue(DataCleaner.validate_price(0.01))
        
        # 无效价格
        self.assertFalse(DataCleaner.validate_price(0))
        self.assertFalse(DataCleaner.validate_price(-10.5))
        self.assertFalse(DataCleaner.validate_price(None))
        self.assertFalse(DataCleaner.validate_price('abc'))
        self.assertFalse(DataCleaner.validate_price(100000))  # 超过1万元
    
    def test_validate_volume(self):
        """测试成交量验证"""
        # 有效成交量
        self.assertTrue(DataCleaner.validate_volume(1000))
        self.assertTrue(DataCleaner.validate_volume(1000000))
        
        # 无效成交量
        self.assertFalse(DataCleaner.validate_volume(0))
        self.assertFalse(DataCleaner.validate_volume(-1000))
        self.assertFalse(DataCleaner.validate_volume(None))
        self.assertFalse(DataCleaner.validate_volume('abc'))
        self.assertFalse(DataCleaner.validate_volume(1e11))  # 超过100亿股
    
    def test_calculate_volume_ratio(self):
        """测试量比计算"""
        # 正常情况
        self.assertEqual(DataCleaner.calculate_volume_ratio(2000, 1000), 2.0)
        self.assertEqual(DataCleaner.calculate_volume_ratio(5000, 1000), 5.0)
        self.assertEqual(DataCleaner.calculate_volume_ratio(500, 1000), 0.5)
        
        # 边界情况
        self.assertEqual(DataCleaner.calculate_volume_ratio(0, 1000), 0.0)
        self.assertEqual(DataCleaner.calculate_volume_ratio(1000, 0), 1.0)
        self.assertEqual(DataCleaner.calculate_volume_ratio(None, 1000), 0.0)
        self.assertEqual(DataCleaner.calculate_volume_ratio(1000, None), 1.0)
    
    def test_clean_realtime_data(self):
        """测试实时数据清洗"""
        # 正常数据
        data = {
            'code': 'sh600000',
            'name': '平安银行',
            'now': 10.5,
            'open': 10.0,
            'close': 10.0,
            'high': 10.8,
            'low': 9.9,
            'volume': 1000000,
            'turnover': 10500000,
            'bid1': 10.5,
            'ask1': 10.51,
            'bid1_volume': 1000,
            'ask1_volume': 500
        }
        
        cleaned = DataCleaner.clean_realtime_data(data)
        
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned['code'], '600000')
        self.assertEqual(cleaned['name'], '平安银行')
        self.assertEqual(cleaned['now'], 10.5)
        self.assertEqual(cleaned['volume'], 1000000)
        self.assertEqual(cleaned['change_pct'], 5.0)
        self.assertIsNotNone(cleaned['limit_status'])
        
        # 无效数据
        invalid_data = {'code': 'abc'}
        cleaned = DataCleaner.clean_realtime_data(invalid_data)
        self.assertIsNone(cleaned)
        
        # 空数据
        cleaned = DataCleaner.clean_realtime_data(None)
        self.assertIsNone(cleaned)


if __name__ == '__main__':
    unittest.main()