"""
PathResolver单元测试

测试策略:
    1. 单例模式测试 - 确保全局状态一致性
    2. 自动检测测试 - 验证根目录自动推断逻辑
    3. 路径解析测试 - 验证各目录路径正确性
    4. 边界条件测试 - 异常情况处理
    5. 配置读取测试 - QMT路径配置解析
"""
import unittest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 确保可以导入被测模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from logic.core.path_resolver import PathResolver


class TestPathResolver(unittest.TestCase):
    """PathResolver测试类"""
    
    def setUp(self):
        """每个测试前重置PathResolver状态"""
        PathResolver.reset()
    
    def tearDown(self):
        """每个测试后清理"""
        PathResolver.reset()
    
    # ==========================================================================
    # 基本功能测试
    # ==========================================================================
    
    def test_singleton_pattern(self):
        """测试单例模式 - 多次获取应该是同一实例"""
        resolver1 = PathResolver()
        resolver2 = PathResolver()
        self.assertIs(resolver1, resolver2)
    
    def test_auto_detect_root(self):
        """测试自动检测项目根目录"""
        root = PathResolver.get_root()
        self.assertIsInstance(root, Path)
        self.assertTrue(root.exists())
        
        # 验证根目录包含预期文件/目录
        self.assertTrue((root / 'main.py').exists() or (root / 'logic').exists())
    
    def test_manual_initialize(self):
        """测试手动初始化"""
        test_dir = Path(tempfile.mkdtemp())
        try:
            # 创建必要的标记文件
            (test_dir / 'main.py').touch()
            
            PathResolver.initialize(test_dir)
            self.assertEqual(PathResolver.get_root(), test_dir)
        finally:
            shutil.rmtree(test_dir)
    
    # ==========================================================================
    # 目录路径测试
    # ==========================================================================
    
    def test_get_data_dir(self):
        """测试获取数据目录"""
        PathResolver.initialize()
        data_dir = PathResolver.get_data_dir()
        
        self.assertIsInstance(data_dir, Path)
        self.assertEqual(data_dir.name, 'data')
        self.assertEqual(data_dir.parent, PathResolver.get_root())
    
    def test_get_config_dir(self):
        """测试获取配置目录"""
        PathResolver.initialize()
        config_dir = PathResolver.get_config_dir()
        
        self.assertIsInstance(config_dir, Path)
        self.assertEqual(config_dir.name, 'config')
        self.assertEqual(config_dir.parent, PathResolver.get_root())
    
    def test_get_logs_dir(self):
        """测试获取日志目录"""
        PathResolver.initialize()
        logs_dir = PathResolver.get_logs_dir()
        
        self.assertIsInstance(logs_dir, Path)
        self.assertEqual(logs_dir.name, 'logs')
        self.assertEqual(logs_dir.parent, PathResolver.get_root())
    
    def test_get_backtest_dir(self):
        """测试获取回测目录"""
        PathResolver.initialize()
        backtest_dir = PathResolver.get_backtest_dir()
        
        self.assertIsInstance(backtest_dir, Path)
        self.assertEqual(backtest_dir.name, 'backtest')
    
    def test_get_logic_dir(self):
        """测试获取逻辑层目录"""
        PathResolver.initialize()
        logic_dir = PathResolver.get_logic_dir()
        
        self.assertIsInstance(logic_dir, Path)
        self.assertEqual(logic_dir.name, 'logic')
    
    def test_get_tasks_dir(self):
        """测试获取任务目录"""
        PathResolver.initialize()
        tasks_dir = PathResolver.get_tasks_dir()
        
        self.assertIsInstance(tasks_dir, Path)
        self.assertEqual(tasks_dir.name, 'tasks')
    
    def test_get_tools_dir(self):
        """测试获取工具目录"""
        PathResolver.initialize()
        tools_dir = PathResolver.get_tools_dir()
        
        self.assertIsInstance(tools_dir, Path)
        self.assertEqual(tools_dir.name, 'tools')
    
    def test_get_tests_dir(self):
        """测试获取测试目录"""
        PathResolver.initialize()
        tests_dir = PathResolver.get_tests_dir()
        
        self.assertIsInstance(tests_dir, Path)
        self.assertEqual(tests_dir.name, 'tests')
    
    def test_get_docs_dir(self):
        """测试获取文档目录"""
        PathResolver.initialize()
        docs_dir = PathResolver.get_docs_dir()
        
        self.assertIsInstance(docs_dir, Path)
        self.assertEqual(docs_dir.name, 'docs')
    
    # ==========================================================================
    # QMT数据目录测试
    # ==========================================================================
    
    def test_get_qmt_data_dir_from_config(self):
        """测试从配置文件读取QMT数据目录"""
        # 创建临时目录结构
        temp_root = Path(tempfile.mkdtemp())
        try:
            config_dir = temp_root / 'config'
            config_dir.mkdir()
            
            # 创建假的QMT目录
            fake_qmt_dir = temp_root / 'fake_qmt' / 'datadir'
            fake_qmt_dir.mkdir(parents=True)
            
            # 创建配置文件
            config_file = config_dir / 'data_paths.json'
            with open(config_file, 'w') as f:
                json.dump({'qmt_data_dir': str(fake_qmt_dir)}, f)
            
            PathResolver.initialize(temp_root)
            qmt_dir = PathResolver.get_qmt_data_dir()
            
            self.assertEqual(qmt_dir, fake_qmt_dir)
        finally:
            PathResolver.reset()
            shutil.rmtree(temp_root)
    
    def test_get_qmt_data_dir_config_not_exists(self):
        """测试配置文件不存在时的处理"""
        temp_root = Path(tempfile.mkdtemp())
        try:
            PathResolver.initialize(temp_root)
            
            # 应该抛出RuntimeError
            with self.assertRaises(RuntimeError) as context:
                PathResolver.get_qmt_data_dir()
            
            self.assertIn("QMT数据目录未配置", str(context.exception))
        finally:
            PathResolver.reset()
            shutil.rmtree(temp_root)
    
    def test_get_qmt_data_dir_invalid_config(self):
        """测试配置文件格式错误时的处理"""
        temp_root = Path(tempfile.mkdtemp())
        try:
            config_dir = temp_root / 'config'
            config_dir.mkdir()
            
            # 创建无效的配置文件
            config_file = config_dir / 'data_paths.json'
            with open(config_file, 'w') as f:
                f.write('invalid json')
            
            PathResolver.initialize(temp_root)
            
            with self.assertRaises(RuntimeError) as context:
                PathResolver.get_qmt_data_dir()
            
            self.assertIn("配置文件格式错误", str(context.exception))
        finally:
            PathResolver.reset()
            shutil.rmtree(temp_root)
    
    def test_get_qmt_data_dir_path_not_exists(self):
        """测试配置中的路径不存在时的处理"""
        temp_root = Path(tempfile.mkdtemp())
        try:
            config_dir = temp_root / 'config'
            config_dir.mkdir()
            
            config_file = config_dir / 'data_paths.json'
            with open(config_file, 'w') as f:
                json.dump({'qmt_data_dir': '/nonexistent/path'}, f)
            
            PathResolver.initialize(temp_root)
            
            with self.assertRaises(RuntimeError) as context:
                PathResolver.get_qmt_data_dir()
            
            self.assertIn("不存在", str(context.exception))
        finally:
            PathResolver.reset()
            shutil.rmtree(temp_root)
    
    # ==========================================================================
    # ensure_dir工具方法测试
    # ==========================================================================
    
    def test_ensure_dir_creates_directory(self):
        """测试ensure_dir创建不存在的目录"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            new_dir = temp_dir / 'subdir' / 'nested'
            
            result = PathResolver.ensure_dir(new_dir)
            
            self.assertEqual(result, new_dir)
            self.assertTrue(new_dir.exists())
            self.assertTrue(new_dir.is_dir())
        finally:
            shutil.rmtree(temp_dir)
    
    def test_ensure_dir_existing_directory(self):
        """测试ensure_dir处理已存在的目录"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            existing_dir = temp_dir / 'existing'
            existing_dir.mkdir()
            
            # 不应该抛出异常
            result = PathResolver.ensure_dir(existing_dir)
            
            self.assertEqual(result, existing_dir)
            self.assertTrue(existing_dir.exists())
        finally:
            shutil.rmtree(temp_dir)
    
    def test_ensure_dir_with_string_path(self):
        """测试ensure_dir接受字符串路径"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            new_dir = str(temp_dir / 'string_path')
            
            result = PathResolver.ensure_dir(new_dir)
            
            self.assertEqual(str(result), new_dir)
            self.assertTrue(Path(new_dir).exists())
        finally:
            shutil.rmtree(temp_dir)
    
    # ==========================================================================
    # resolve_path工具方法测试
    # ==========================================================================
    
    def test_resolve_path_relative(self):
        """测试解析相对路径"""
        PathResolver.initialize()
        root = PathResolver.get_root()
        
        resolved = PathResolver.resolve_path('data/test.txt')
        expected = root / 'data' / 'test.txt'
        
        self.assertEqual(resolved, expected)
    
    def test_resolve_path_absolute(self):
        """测试resolve_path保持绝对路径不变"""
        absolute_path = Path('C:/absolute/path').resolve()
        
        resolved = PathResolver.resolve_path(absolute_path)
        
        self.assertEqual(resolved, absolute_path)
    
    def test_resolve_path_with_path_object(self):
        """测试resolve_path接受Path对象"""
        PathResolver.initialize()
        root = PathResolver.get_root()
        
        relative = Path('logs/app.log')
        resolved = PathResolver.resolve_path(relative)
        expected = root / 'logs' / 'app.log'
        
        self.assertEqual(resolved, expected)
    
    # ==========================================================================
    # 自动检测根目录测试
    # ==========================================================================
    
    def test_is_project_root_with_git(self):
        """测试.git目录作为项目根标记"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            (temp_dir / '.git').mkdir()
            
            result = PathResolver._is_project_root(temp_dir)
            
            self.assertTrue(result)
        finally:
            shutil.rmtree(temp_dir)
    
    def test_is_project_root_with_config(self):
        """测试config目录作为项目根标记"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            (temp_dir / 'config').mkdir()
            
            result = PathResolver._is_project_root(temp_dir)
            
            self.assertTrue(result)
        finally:
            shutil.rmtree(temp_dir)
    
    def test_is_project_root_with_main_py(self):
        """测试main.py作为项目根标记"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            (temp_dir / 'main.py').touch()
            
            result = PathResolver._is_project_root(temp_dir)
            
            self.assertTrue(result)
        finally:
            shutil.rmtree(temp_dir)
    
    def test_is_project_root_not_root(self):
        """测试非项目根目录的判断"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # 空目录，没有任何标记
            result = PathResolver._is_project_root(temp_dir)
            
            self.assertFalse(result)
        finally:
            shutil.rmtree(temp_dir)
    
    # ==========================================================================
    # 重置功能测试
    # ==========================================================================
    
    def test_reset_clears_state(self):
        """测试reset清除所有状态"""
        # 先初始化
        PathResolver.initialize()
        root1 = PathResolver.get_root()
        
        # 重置
        PathResolver.reset()
        
        # 验证内部状态被清除
        self.assertIsNone(PathResolver._root_dir)
        self.assertFalse(PathResolver._initialized)


class TestPathResolverIntegration(unittest.TestCase):
    """PathResolver集成测试 - 测试实际项目结构"""
    
    @classmethod
    def setUpClass(cls):
        """类级设置 - 初始化一次"""
        PathResolver.reset()
        PathResolver.initialize()
    
    @classmethod
    def tearDownClass(cls):
        """类级清理"""
        PathResolver.reset()
    
    def test_actual_project_structure(self):
        """测试实际项目目录结构"""
        root = PathResolver.get_root()
        
        # 验证主要目录存在
        self.assertTrue((root / 'main.py').exists(), "main.py应该存在")
        self.assertTrue((root / 'logic').exists(), "logic目录应该存在")
        self.assertTrue((root / 'config').exists(), "config目录应该存在")
        self.assertTrue((root / 'data').exists(), "data目录应该存在")
    
    def test_path_consistency(self):
        """测试路径一致性"""
        root = PathResolver.get_root()
        
        # 验证所有路径都在根目录下
        self.assertTrue(str(PathResolver.get_data_dir()).startswith(str(root)))
        self.assertTrue(str(PathResolver.get_config_dir()).startswith(str(root)))
        self.assertTrue(str(PathResolver.get_logs_dir()).startswith(str(root)))
    
    def test_path_resolver_module_location(self):
        """测试PathResolver模块的实际位置"""
        resolver_file = Path(__file__).parent.parent.parent.parent / 'logic' / 'core' / 'path_resolver.py'
        self.assertTrue(resolver_file.exists(), "path_resolver.py应该存在")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
