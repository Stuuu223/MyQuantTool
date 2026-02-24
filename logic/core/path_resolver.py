"""
路径解析器 - 系统唯一可信的路径来源
禁止任何硬编码路径！

使用方法:
    from logic.core.path_resolver import PathResolver
    
    # 自动初始化（推荐）
    root = PathResolver.get_root()
    
    # 手动初始化
    PathResolver.initialize("/path/to/project")
    
    # 获取各种目录
    data_dir = PathResolver.get_data_dir()
    config_dir = PathResolver.get_config_dir()
    qmt_dir = PathResolver.get_qmt_data_dir()
"""
from pathlib import Path
import os
import json
from typing import Optional, Union


class PathResolver:
    """
    单例路径解析器 - 管理系统所有路径的统一入口
    
    设计原则:
        1. 单一可信源 - 所有路径必须从此类获取
        2. 动态推断 - 自动检测项目根目录
        3. 配置优先 - 优先从配置文件读取，而非硬编码
        4. 路径存在性验证 - 返回前验证路径有效性
    """
    
    _instance: Optional['PathResolver'] = None
    _root_dir: Optional[Path] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'PathResolver':
        """确保单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, root_dir: Optional[Union[str, Path]] = None) -> None:
        """
        初始化根目录
        
        Args:
            root_dir: 项目根目录路径。如果为None，则自动推断
        
        Note:
            自动推断逻辑：从本文件位置向上追溯，直到找到包含特定标记的目录
            标记优先级：.git > config/ > main.py > 通用根目录
        """
        if cls._initialized and root_dir is None:
            return  # 已经初始化且未指定新路径
            
        if root_dir is None:
            cls._root_dir = cls._auto_detect_root()
        else:
            cls._root_dir = Path(root_dir).resolve()
            
        cls._initialized = True
    
    @classmethod
    def _auto_detect_root(cls) -> Path:
        """
        自动检测项目根目录
        
        Returns:
            Path: 检测到的项目根目录
            
        Raises:
            RuntimeError: 无法检测到有效的项目根目录
        """
        # 从当前文件开始向上追溯
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent
        
        # 向上追溯最多5层
        for _ in range(5):
            if cls._is_project_root(current_dir):
                return current_dir
            parent = current_dir.parent
            if parent == current_dir:  # 到达文件系统根
                break
            current_dir = parent
        
        # 如果找不到标记，使用当前文件的爷爷目录（logic/core/ -> logic/ -> root/）
        fallback = current_file.parent.parent
        return fallback
    
    @classmethod
    def _is_project_root(cls, path: Path) -> bool:
        """
        检查给定路径是否为项目根目录
        
        Args:
            path: 待检查的路径
            
        Returns:
            bool: 如果是项目根目录则返回True
        """
        markers = [
            '.git',
            'config',
            'main.py',
            'requirements.txt',
            'README.md'
        ]
        
        for marker in markers:
            if (path / marker).exists():
                return True
        return False
    
    @classmethod
    def get_root(cls) -> Path:
        """
        获取项目根目录
        
        Returns:
            Path: 项目根目录的绝对路径
        """
        if cls._root_dir is None:
            cls.initialize()
        return cls._root_dir
    
    @classmethod
    def get_data_dir(cls) -> Path:
        """
        获取数据目录
        
        Returns:
            Path: 数据目录路径 (project_root/data)
        """
        return cls.get_root() / "data"
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """
        获取配置目录
        
        Returns:
            Path: 配置目录路径 (project_root/config)
        """
        return cls.get_root() / "config"
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """
        获取日志目录
        
        Returns:
            Path: 日志目录路径 (project_root/logs)
        """
        return cls.get_root() / "logs"
    
    @classmethod
    def get_backtest_dir(cls) -> Path:
        """
        获取回测目录
        
        Returns:
            Path: 回测目录路径 (project_root/backtest)
        """
        return cls.get_root() / "backtest"
    
    @classmethod
    def get_logic_dir(cls) -> Path:
        """
        获取逻辑层目录
        
        Returns:
            Path: 逻辑层目录路径 (project_root/logic)
        """
        return cls.get_root() / "logic"
    
    @classmethod
    def get_tasks_dir(cls) -> Path:
        """
        获取任务目录
        
        Returns:
            Path: 任务目录路径 (project_root/tasks)
        """
        return cls.get_root() / "tasks"
    
    @classmethod
    def get_tools_dir(cls) -> Path:
        """
        获取工具目录
        
        Returns:
            Path: 工具目录路径 (project_root/tools)
        """
        return cls.get_root() / "tools"
    
    @classmethod
    def get_tests_dir(cls) -> Path:
        """
        获取测试目录
        
        Returns:
            Path: 测试目录路径 (project_root/tests)
        """
        return cls.get_root() / "tests"
    
    @classmethod
    def get_docs_dir(cls) -> Path:
        """
        获取文档目录
        
        Returns:
            Path: 文档目录路径 (project_root/docs)
        """
        return cls.get_root() / "docs"
    
    @classmethod
    def get_qmt_data_dir(cls) -> Path:
        """
        获取QMT数据目录 - 从环境变量或配置文件读取，禁止硬编码
        
        Returns:
            Path: QMT数据目录的绝对路径
            
        Raises:
            RuntimeError: QMT数据目录未配置且默认路径不存在
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
            KeyError: 配置文件中缺少必要的键
        """
        # 首先尝试从环境变量读取
        qmt_path_env = os.getenv("QMT_PATH")
        if qmt_path_env:
            path = Path(qmt_path_env)
            if path.exists():
                return path.resolve()
            else:
                raise RuntimeError(f"环境变量QMT_PATH指定的路径不存在: {path}")
        
        config_file = cls.get_config_dir() / "data_paths.json"
        
        # 尝试从配置文件读取
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    qmt_path = config.get('qmt_data_dir')
                    if qmt_path:
                        path = Path(qmt_path)
                        if path.exists():
                            return path.resolve()
                        else:
                            raise RuntimeError(f"配置中的QMT数据目录不存在: {path}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"配置文件格式错误: {config_file}") from e
        
        # 智能检测：尝试从xtdata获取当前连接的数据路径信息
        try:
            from xtquant import xtdata
            # xtdata在连接时会显示数据路径信息，我们利用这一点
            # 检查当前系统上可能的QMT安装位置
            import platform
            possible_paths = []
            
            # 检查环境变量中可能存在的其他QMT相关路径
            for env_var in ['USERPROFILE', 'HOMEDRIVE', 'SystemDrive']:
                env_value = os.getenv(env_var)
                if env_value:
                    if env_var == 'HOMEDRIVE':
                        # 尝试常见安装位置
                        qmt_path = Path(f"{env_value}/QMT/userdata_mini")
                        if qmt_path.exists():
                            possible_paths.append(qmt_path)
                        qmt_path2 = Path(f"{env_value}/国金证券QMT交易端/userdata_mini")
                        if qmt_path2.exists():
                            possible_paths.append(qmt_path2)
            
            # 检查常见驱动器
            import string
            for drive_letter in string.ascii_uppercase:
                drive_path = f"{drive_letter}:"
                if os.path.exists(drive_path):
                    # 检查这个驱动器上是否有QMT安装
                    qmt_path = Path(f"{drive_letter}:/QMT/userdata_mini")
                    if qmt_path.exists():
                        possible_paths.append(qmt_path)
                    qmt_path2 = Path(f"{drive_letter}:/国金证券QMT交易端/userdata_mini")
                    if qmt_path2.exists():
                        possible_paths.append(qmt_path2)
            
            # 返回第一个找到的有效路径
            for path in possible_paths:
                if path.exists():
                    return path.resolve()
                    
        except ImportError:
            # xtquant不可用时跳过智能检测
            pass
        except Exception:
            # 其他异常也跳过智能检测
            pass
        
        raise RuntimeError(
            f"QMT数据目录未配置或无法找到。\n"
            f"❌ 错误：系统无法找到QMT数据目录，请检查以下配置：\n"
            f"1. 环境变量QMT_PATH是否正确设置 (当前值: {os.getenv('QMT_PATH', '未设置')})\n"
            f"2. QMT客户端是否已正确安装\n"
            f"3. QMT数据目录路径是否存在\n"
            f"4. .env文件中QMT_PATH配置是否正确\n\n"
            f"💡 解决方案：\n"
            f"   设置环境变量: set QMT_PATH=H:\\QMT\\userdata_mini (替换为实际路径)\n"
            f"   或创建配置文件: {config_file} 并添加: {{'qmt_data_dir': '你的实际路径'}}\n\n"
            f"📋 常见QMT安装路径: H:\\QMT\\userdata_mini, E:\\QMT\\userdata_mini, D:\\国金证券QMT交易端\\userdata_mini"
        )
    
    @classmethod
    def ensure_dir(cls, path: Union[str, Path]) -> Path:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            path: 目录路径
            
        Returns:
            Path: 确保存在后的目录路径
            
        Raises:
            PermissionError: 无权限创建目录
            OSError: 创建目录时发生其他错误
        """
        path = Path(path)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"无权限创建目录: {path}") from e
        except OSError as e:
            raise OSError(f"创建目录失败: {path}") from e
        return path
    
    @classmethod
    def resolve_path(cls, relative_path: Union[str, Path]) -> Path:
        """
        将相对路径解析为绝对路径（基于项目根目录）
        
        Args:
            relative_path: 相对于项目根目录的路径
            
        Returns:
            Path: 绝对路径
        """
        if isinstance(relative_path, str):
            relative_path = Path(relative_path)
        
        if relative_path.is_absolute():
            return relative_path
        
        return cls.get_root() / relative_path
    
    @classmethod
    def reset(cls) -> None:
        """
        重置解析器状态（主要用于测试）
        
        Warning:
            此方法会清除已初始化的状态，仅在测试中使用
        """
        cls._root_dir = None
        cls._initialized = False
        cls._instance = None
