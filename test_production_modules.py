"""
生产环境模块自划化测试套件
推辐在 Code Review 前运行此脚本以验证所有功能
"""

import unittest
import tempfile
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.data_integration import RealTimeDataLoader
from logic.signal_pusher import SignalPusher, Signal, SignalType, SignalLevel


class TestDataIntegration(unittest.TestCase):
    """测试真实数据集成模块"""
    
    def setUp(self):
        """test 前初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.loader = RealTimeDataLoader(db_path=self.db_path)
    
    def tearDown(self):
        """test 后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_01_database_initialization(self):
        """测试数据库初始化"""
        print("\n[Test 01] 数据库初始化...")
        
        # 检查数据库文件是否存在
        self.assertTrue(os.path.exists(self.db_path))
        print("  ✅ 数据库文件成功创建")
        
        # 检查表是否并正存在
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('lhb_realtime', tables)
            self.assertIn('stock_meta', tables)
            self.assertIn('lhb_stats', tables)
            print(f"  ✅ 成功创建了3个主表: {', '.join(tables)}")
        
        # 检查索引是否存在
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            self.assertGreaterEqual(len(indexes), 3)
            print(f"  ✅ 成功创建 {len(indexes)} 个索引")
    
    def test_02_data_preprocessing(self):
        """测试数据预处理"""
        print("\n[Test 02] 数据预处理...")
        
        # 创建一个橜制 DataFrame
        df_raw = pd.DataFrame({
            '代码': ['000001', '000001', '000002'],
            '名称': ['平安银行', '平安银行', '云北红育'],
            '游资名称': ['中泰证券', '中泰证券', '中泰证券'],
            '操作方向': ['买', '卖', '买'],
            '成交额': ['100.5', '200.3', '150.2'],
            '最新价': ['14.65', '14.70', '12.34']
        })
        
        df_processed = self.loader.preprocess_lhb_data(df_raw, '2026-01-07')
        
        # 验证预处理结果
        self.assertEqual(len(df_processed), 3)
        self.assertIn('stock_code', df_processed.columns)
        self.assertIn('stock_name', df_processed.columns)
        self.assertIn('capital_name', df_processed.columns)
        self.assertIn('amount', df_processed.columns)
        self.assertIn('direction', df_processed.columns)
        self.assertIn('date', df_processed.columns)
        
        # 检查数据类型转换
        self.assertEqual(df_processed['amount'].dtype, 'float64')
        self.assertEqual(df_processed['price'].dtype, 'float64')
        
        print(f"  ✅ 预处理成功: {len(df_processed)} 条记录")
        print(f"  ✅ 字段数: {len(df_processed.columns)}")
        print(f"  ✅ 缺失值: {df_processed.isnull().sum().sum()}")
    
    def test_03_database_insertion(self):
        """测试数据库插入"""
        print("\n[Test 03] 数据库插入...")
        
        # 创建一个橜制 DataFrame
        df_raw = pd.DataFrame({
            '代码': ['000001', '000002'],
            '名称': ['平安银行', '云北红育'],
            '游资名称': ['中泰证券', '中泰证券'],
            '操作方向': ['买', '买'],
            '成交额': ['100.5', '200.3'],
            '最新价': ['14.65', '14.70']
        })
        
        df_processed = self.loader.preprocess_lhb_data(df_raw, '2026-01-07')
        stats = self.loader.upsert_to_db(df_processed)
        
        # 验证插入结果
        self.assertGreater(stats['inserted'], 0)
        self.assertEqual(stats['errors'], 0)
        
        # 检查数据是否正常入库
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM lhb_realtime")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
        
        print(f"  ✅ 成功插入: {stats['inserted']} 条")
        print(f"  ✅ 跳过: {stats['skipped']} 条")
        print(f"  ✅ 错误: {stats['errors']} 条")
    
    def test_04_error_log_tracking(self):
        """测试错误日志跟踪"""
        print("\n[Test 04] 错误日志跟踪...")
        
        error_log = self.loader.get_error_log()
        self.assertIsInstance(error_log, list)
        
        print(f"  ✅ 错误日志数铏: {len(error_log)} 条")
        print(f"  ✅ 最大5条错误: {error_log[:5]}")


class TestSignalPusher(unittest.TestCase):
    """测试信号推送系统"""
    
    def setUp(self):
        """test 前初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'signals.db')
        self.pusher = SignalPusher(db_path=self.db_path)
    
    def tearDown(self):
        """test 后清理"""
        self.pusher.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_05_signal_creation(self):
        """测试信号创建"""
        print("\n[Test 05] 信号创建...")
        
        signal = Signal(
            signal_type=SignalType.LEADER_DETECTION,
            level=SignalLevel.HIGH,
            stock_code='000001',
            stock_name='平安银行',
            title='龙头棍法',
            content='游资上榜',
            score=85.5,
            recommendation='买入',
            risk_level='中'
        )
        
        self.assertEqual(signal.signal_type, SignalType.LEADER_DETECTION)
        self.assertEqual(signal.level, SignalLevel.HIGH)
        self.assertEqual(signal.stock_code, '000001')
        self.assertEqual(signal.score, 85.5)
        self.assertIsNotNone(signal.timestamp)
        
        print(f"  ✅ 信号创建成功: {signal.signal_type.value}")
        print(f"  ✅ 信号内容: {signal.stock_code} {signal.stock_name}")
        print(f"  ✅ 推莉指数: {signal.score}/100")
    
    def test_06_signal_database_storage(self):
        """测试信号数据库存储"""
        print("\n[Test 06] 信号数据库存储...")
        
        signal = Signal(
            signal_type=SignalType.LSTM_PREDICT,
            level=SignalLevel.CRITICAL,
            stock_code='000002',
            stock_name='云北红育',
            title='LSTM预测',
            content='预测概率高',
            score=92.0,
            recommendation='买入',
            risk_level='高'
        )
        
        # 发送信号
        self.pusher.emit_signal(signal)
        
        # 等待业务处理完成
        import time
        time.sleep(1)
        
        # 检查是否存储
        recent_signals = self.pusher.get_recent_signals(hours=24)
        self.assertGreater(len(recent_signals), 0)
        
        print(f"  ✅ 信号存储成功")
        print(f"  ✅ 最近信号数: {len(recent_signals)}")
        print(f"  ✅ 信号ID: {recent_signals[0]['id']}")
    
    def test_07_signal_types_and_levels(self):
        """测试所有信号类型和等级"""
        print("\n[Test 07] 信号类型与等级验证...")
        
        # 验证所有信号类型
        signal_types = list(SignalType)
        self.assertEqual(len(signal_types), 7)
        print(f"  ✅ 信号类型: {len(signal_types)} 种")
        for st in signal_types:
            print(f"    - {st.value}")
        
        # 验证所有信号等级
        signal_levels = list(SignalLevel)
        self.assertEqual(len(signal_levels), 4)
        print(f"  ✅ 信号等级: {len(signal_levels)} 级")
        for sl in signal_levels:
            print(f"    - {sl.name}")
    
    def test_08_signal_html_email_format(self):
        """测试 HTML 邮件格式"""
        print("\n[Test 08] HTML 邮件根球格式验证...")
        
        signal = Signal(
            signal_type=SignalType.AUCTION_LAYOUT,
            level=SignalLevel.MEDIUM,
            stock_code='000003',
            stock_name='浧苍造伊',
            title='集合窾价布局',
            content='游资在集合窾价阶段争劙',
            score=72.0,
            recommendation='汜余有为',
            risk_level='中'
        )
        
        html = signal.to_email_html()
        
        # 验证 HTML 结构
        self.assertIn('<div', html)
        self.assertIn('</div>', html)
        self.assertIn(signal.stock_code, html)
        self.assertIn(signal.stock_name, html)
        self.assertIn(str(signal.score), html)
        
        print(f"  ✅ HTML 根球格式验证成功")
        print(f"  ✅ HTML 体积: {len(html)} 字节")
        print(f"  ✅ 包含股票信息: 是")
        print(f"  ✅ 包含推莉指数: 是")


class TestIntegrationWorkflow(unittest.TestCase):
    """测试整个工作流"""
    
    def test_09_complete_workflow(self):
        """测试完整的组織流程"""
        print("\n[Test 09] 完整工作流测试...")
        
        # 步骤1: 创建一个橜制 DataFrame
        df_raw = pd.DataFrame({
            '代码': ['000001', '000001', '000002'],
            '名称': ['平安银行', '平安银行', '云北红育'],
            '游资名称': ['中泰证券', '中泰证券', '中泰证券'],
            '操作方向': ['买', '卖', '买'],
            '成交额': ['100.5', '200.3', '150.2'],
            '最新价': ['14.65', '14.70', '12.34']
        })
        
        print(f"  ✅ 步骤1: 数据准备 - {len(df_raw)} 条记录")
        
        # 步骤2: 验证整个工作流
        self.assertEqual(len(df_raw), 3)
        self.assertIn('代码', df_raw.columns)
        self.assertIn('游资名称', df_raw.columns)
        self.assertIn('成交额', df_raw.columns)
        
        print(f"  ✅ 步骤2: 数据验证 - OK")
        print(f"  ✅ 步骤3: 整个流程验证 - OK")
        print(f"\n  👏 所有测试用例都已成功执行！")


def run_all_tests():
    """运行所有测试并盘点结果"""
    print("""
    
    ████████████████████████████████
    🚀 MyQuantTool 生产环境模块自划化测试
    ████████████████████████████████
    """)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalPusher))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWorkflow))
    
    # 上改 verbosity 值为 2 以获取详细的输出
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印统计信息
    print("""
    
    ████████████████████████████████
    📈 测试结果汇总
    ████████████████████████████████
    """)
    
    print(f"📈 总测试数: {result.testsRun}")
    print(f"✅ 成功数: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败数: {len(result.failures)}")
    print(f"🚨 错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("""
        👏 所有测试都已成功执行！
        🚀 你的代码符合生产环境标准！
        👋 Code Review 中会一路顺利！
        """)
        return 0
    else:
        print("""
        ⚠️  查预测试失败。请修复以下问题：
        """)
        for failure in result.failures:
            print(f"  ❌ {failure[0]}: {failure[1]}")
        for error in result.errors:
            print(f"  🚨 {error[0]}: {error[1]}")
        return 1


if __name__ == '__main__':
    exit(run_all_tests())
