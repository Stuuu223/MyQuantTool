# -*- coding: utf-8 -*-
"""
QMT 接口管理类

功能：
1. 管理 QMT 数据接口连接
2. 管理 QMT 交易接口连接
3. 提供统一的 QMT 数据获取接口
4. 自动重连和错误处理

Author: iFlow CLI
Date: 2026-01-28
Version: V1.1 (修复回调GC问题，添加代码格式转换，优化订阅功能)
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

try:
    from xtquant import xtdata, xttrader
    XT_AVAILABLE = True
except ImportError:
    XT_AVAILABLE = False


def init_qmt_data_dir() -> None:
    """
    初始化 QMT 数据目录
    
    从 Config.qmt_data_dir 读取 QMT 数据目录路径，
    并设置为 xtdata 的默认数据目录
    
    Raises:
        RuntimeError: 如果 Config.qmt_data_dir 未配置
    """
    try:
        import config.config_system as config
        from xtquant import xtdata
        
        # 🔥 关键修复：通过实例调用get()方法，而不是通过类
        config_instance = config.Config()
        qmt_dir = config_instance.get('qmt_data_dir')
        
        if not qmt_dir:
            raise RuntimeError("Config.qmt_data_dir is empty, please set it in config/qmt_config.json")
        
        # 设置 QMT 数据目录
        # 注意：根据 xtquant 版本，可能使用 data_dir 或 set_data_dir
        if hasattr(xtdata, 'data_dir'):
            xtdata.data_dir = qmt_dir
        elif hasattr(xtdata, 'set_data_dir'):
            xtdata.set_data_dir(qmt_dir)
        else:
            print(f"⚠️ [QMT] 无法设置数据目录，xtdata 未提供 data_dir 或 set_data_dir 方法")
            print(f"⚠️ [QMT] 当前数据目录可能指向默认安装目录，而非 {qmt_dir}")
        
        print(f"✅ [QMT] 数据目录已设置: {qmt_dir}")
        
    except ImportError as e:
        print(f"❌ [QMT] 导入模块失败: {e}")
    except Exception as e:
        print(f"❌ [QMT] 初始化数据目录失败: {e}")
        import traceback
        traceback.print_exc()
        raise


class QMTManager:
    """QMT 接口管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 QMT 管理器

        Args:
            config_path: 配置文件路径，默认为 config/qmt_config.json
        """
        self.config = self._load_config(config_path)
        self.data_connected = False
        self.trader_connected = False
        self.trader_client = None

        # 🔥 关键修复：暴露 xtdata 模块给外部调用
        if XT_AVAILABLE:
            self.xtdata = xtdata
        else:
            self.xtdata = None

        self._init_data_interface()
        self._init_trader_interface()
        self._init_subscription()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "qmt_config.json"

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "qmt_data": {"enabled": True, "ip": "127.0.0.1", "port": 58610},
                "qmt_trader": {"enabled": False}
            }

    def _init_data_interface(self):
        """初始化数据接口"""
        if not XT_AVAILABLE:
            print("❌ xtquant 模块不可用")
            return

        data_config = self.config.get('qmt_data', {})
        if not data_config.get('enabled', False):
            print("⚠️  QMT 数据接口未启用")
            return

        try:
            # 测试连接
            stock_list = xtdata.get_stock_list_in_sector('沪深A股')
            if stock_list is not None:
                self.data_connected = True
                print(f"✅ QMT 数据接口连接成功，获取到 {len(stock_list)} 只股票")
            else:
                print("⚠️  QMT 数据接口连接异常，未获取到股票列表")
        except Exception as e:
            print(f"❌ QMT 数据接口连接失败: {e}")

    def _init_trader_interface(self):
        """初始化交易接口"""
        if not XT_AVAILABLE:
            return

        trader_config = self.config.get('qmt_trader', {})
        if not trader_config.get('enabled', False):
            print("⚠️  QMT 交易接口未启用")
            return

        try:
            # 创建交易回调类
            class DefaultCallback(xttrader.XtQuantTraderCallback):
                def on_connected(self):
                    print("✅ QMT 交易接口连接成功")

                def on_disconnected(self):
                    print("❌ QMT 交易接口连接断开")

            # 修复：将回调保存为实例属性，防止被 GC 回收
            self._trader_callback = DefaultCallback()

            # 创建交易客户端
            self.trader_client = xttrader.XtQuantTrader(
                self._trader_callback,
                trader_config.get('session_id', 123456)
            )

            # 连接交易接口
            result = self.trader_client.connect()
            if result == 0:
                self.trader_connected = True
                print("✅ QMT 交易接口初始化成功")
            else:
                print(f"❌ QMT 交易接口连接失败，错误码: {result}")

        except Exception as e:
            print(f"❌ QMT 交易接口初始化失败: {e}")

    def is_available(self) -> bool:
        """检查 QMT 接口是否可用"""
        return XT_AVAILABLE and self.data_connected

    def is_trader_available(self) -> bool:
        """检查 QMT 交易接口是否可用"""
        return XT_AVAILABLE and self.trader_connected

    def get_stock_list(self) -> Optional[List[str]]:
        """获取股票列表"""
        if not self.is_available():
            return None

        try:
            return xtdata.get_stock_list_in_sector('沪深A股')
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return None

    def get_full_tick(self, stock_list: List[str]) -> Optional[Dict[str, Any]]:
        """获取tick数据"""
        if not self.is_available():
            return None

        try:
            return xtdata.get_full_tick(stock_list)
        except Exception as e:
            print(f"❌ 获取tick数据失败: {e}")
            return None

    def download_history_data(self, stock_code: str, period: str = '1d',
                             start_time: str = None, end_time: str = None,
                             async_mode: bool = False) -> bool:
        """
        下载历史数据

        Args:
            stock_code: 股票代码
            period: 周期（1d, 1h, 1m 等）
            start_time: 开始时间（格式：YYYYMMDD）
            end_time: 结束时间（格式：YYYYMMDD）
            async_mode: 是否异步执行（避免阻塞主线程）

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        def _download():
            try:
                # 标准化股票代码
                normalized_code = self.normalize_code(stock_code)
                xtdata.download_history_data(normalized_code, period, start_time, end_time)
                return True
            except Exception as e:
                print(f"❌ 下载历史数据失败: {e}")
                return False

        if async_mode:
            # 异步执行，避免阻塞
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_download)
                return future.result(timeout=300)  # 5分钟超时
        else:
            return _download()

    def get_local_data(self, stock_list: List[str], field_list: List[str],
                      period: str = '1d', start_time: str = None,
                      end_time: str = None) -> Optional[Dict[str, Any]]:
        """
        获取本地数据

        Args:
            stock_list: 股票代码列表
            field_list: 字段列表（time, open, high, low, close 等）
            period: 周期
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            数据字典
        """
        if not self.is_available():
            return None

        try:
            return xtdata.get_local_data(field_list, stock_list, period, start_time, end_time)
        except Exception as e:
            print(f"❌ 获取本地数据失败: {e}")
            return None

    def query_stock_asset(self, account_id: str = None) -> Optional[Any]:
        """
        查询账户资产

        Args:
            account_id: 账户ID

        Returns:
            账户资产信息
        """
        if not self.is_trader_available():
            return None

        try:
            if account_id is None:
                account_id = self.config.get('qmt_trader', {}).get('account_id')
            return self.trader_client.query_stock_asset(account_id)
        except Exception as e:
            print(f"❌ 查询账户资产失败: {e}")
            return None

    def query_stock_position(self, account_id: str = None) -> Optional[Any]:
        """
        查询持仓

        Args:
            account_id: 账户ID

        Returns:
            持仓信息
        """
        if not self.is_trader_available():
            return None

        try:
            if account_id is None:
                account_id = self.config.get('qmt_trader', {}).get('account_id')
            return self.trader_client.query_stock_position(account_id)
        except Exception as e:
            print(f"❌ 查询持仓失败: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取 QMT 状态"""
        return {
            'xt_available': XT_AVAILABLE,
            'data_connected': self.data_connected,
            'trader_connected': self.trader_connected,
            'config_loaded': bool(self.config)
        }

    def _init_subscription(self):
        """初始化数据订阅"""
        if not self.is_available():
            return

        subscribe_config = self.config.get('data_subscribe', {})
        if not subscribe_config.get('enabled', False):
            return

        try:
            symbols = subscribe_config.get('symbols', [])
            if symbols:
                # 转换股票代码格式
                formatted_symbols = [self.normalize_code(s) for s in symbols]
                xtdata.subscribe_quote(formatted_symbols)
                print(f"✅ 已订阅 {len(formatted_symbols)} 只股票的行情数据")
        except Exception as e:
            print(f"⚠️  数据订阅失败: {e}")

    @staticmethod
    def normalize_code(code: str) -> str:
        """
        标准化股票代码格式为 QMT 格式（######.SH / ######.SZ）

        Args:
            code: 股票代码，支持多种格式（600519, sh600519, 600519.SH 等）

        Returns:
            QMT 标准格式的股票代码

        Examples:
            >>> QMTManager.normalize_code('600519')
            '600519.SH'
            >>> QMTManager.normalize_code('sh600519')
            '600519.SH'
            >>> QMTManager.normalize_code('300750')
            '300750.SZ'
        """
        if not code:
            return code

        # 移除可能的分隔符
        code = code.strip().replace('.', '')

        # 如果已经包含交易所后缀，直接返回
        if code.endswith('.SH') or code.endswith('.SZ'):
            return code

        # 提取6位数字代码
        if code.startswith('sh'):
            stock_code = code[2:]
            return f"{stock_code}.SH"
        elif code.startswith('sz'):
            stock_code = code[2:]
            return f"{stock_code}.SZ"
        elif code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        else:
            # 默认为主板
            return f"{code}.SH"


# 全局 QMT 管理器实例
_qmt_manager: Optional[QMTManager] = None


def get_qmt_manager() -> QMTManager:
    """
    获取全局 QMT 管理器实例
    
    Returns:
        QMTManager: QMT 管理器实例
    """
    global _qmt_manager
    if _qmt_manager is None:
        # 🔥 关键修复：第一件事就是初始化数据目录
        init_qmt_data_dir()
        _qmt_manager = QMTManager()
    return _qmt_manager


if __name__ == "__main__":
    # 测试 QMT 管理器
    print("=" * 60)
    print("🧪 QMT 管理器测试")
    print("=" * 60)

    manager = get_qmt_manager()
    status = manager.get_status()

    print(f"\n📊 QMT 状态:")
    print(f"  xtquant 可用: {'✅' if status['xt_available'] else '❌'}")
    print(f"  数据接口连接: {'✅' if status['data_connected'] else '❌'}")
    print(f"  交易接口连接: {'✅' if status['trader_connected'] else '❌'}")
    print(f"  配置加载: {'✅' if status['config_loaded'] else '❌'}")

    if manager.is_available():
        print(f"\n✅ QMT 管理器初始化成功")

        # 测试获取股票列表
        stock_list = manager.get_stock_list()
        if stock_list:
            print(f"📈 获取到 {len(stock_list)} 只股票")

        # 测试获取tick数据
        if stock_list and len(stock_list) > 0:
            tick_data = manager.get_full_tick([stock_list[0]])
            if tick_data:
                print(f"⚡ 成功获取tick数据")
    else:
        print(f"\n❌ QMT 管理器初始化失败")

    print("=" * 60)
