"""
修复后台任务持续运行的问题

问题分析：
1. sector_rotation_analyzer 使用单例模式，实例在内存中持续存在
2. 即使 Streamlit 应用关闭，单例实例仍然存在
3. 可能导致后台任务持续运行

解决方案：
1. 添加清理方法，确保所有后台任务都能正确停止
2. 在程序退出时调用清理方法
3. 移除单例模式，或者添加清理机制
"""

import sys
import atexit
import signal
import asyncio
import threading
from logic.logger import get_logger

logger = get_logger(__name__)

class CleanupManager:
    """清理管理器 - 确保程序退出时正确清理所有资源"""
    
    def __init__(self):
        self._cleanup_handlers = []
        self._is_cleaning = False
        
        # 注册退出处理函数
        atexit.register(self.cleanup_all)
        
        # 🆕 V9.2 修复：只在主线程中注册信号处理函数
        # signal.signal() 只能在主线程中使用
        try:
            if threading.current_thread() is threading.main_thread():
                if hasattr(signal, 'SIGINT'):
                    signal.signal(signal.SIGINT, self._signal_handler)
                if hasattr(signal, 'SIGTERM'):
                    signal.signal(signal.SIGTERM, self._signal_handler)
                logger.info("✅ 信号处理函数已注册")
            else:
                logger.info("⚠️ 非主线程，跳过信号处理函数注册")
        except ValueError as e:
            # 捕获 ValueError: signal only works in main thread
            logger.warning(f"⚠️ 无法注册信号处理函数: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 注册信号处理函数失败: {e}")
    
    def register_cleanup_handler(self, handler):
        """注册清理处理函数"""
        self._cleanup_handlers.append(handler)
        logger.info(f"注册清理处理函数: {handler.__name__}")
    
    def cleanup_all(self):
        """执行所有清理操作"""
        # 防止重复清理
        if self._is_cleaning:
            return
        
        self._is_cleaning = True
        
        try:
            logger.info("开始清理所有资源...")
            
            for handler in self._cleanup_handlers:
                try:
                    logger.info(f"执行清理: {handler.__name__}")
                    handler()
                except asyncio.CancelledError:
                    # 忽略 asyncio 取消错误
                    logger.debug(f"清理操作被取消: {handler.__name__}")
                except RuntimeError as e:
                    # 忽略 RuntimeError（特别是事件循环关闭的错误）
                    if "Event loop is closed" in str(e) or "Event loop is closed" in str(e):
                        logger.debug(f"事件循环已关闭，跳过清理: {handler.__name__}")
                    else:
                        logger.error(f"清理失败: {handler.__name__}, 错误: {e}")
                except Exception as e:
                    logger.error(f"清理失败: {handler.__name__}, 错误: {e}")
            
            logger.info("所有资源清理完成")
        
        except Exception as e:
            logger.error(f"清理过程中发生错误: {e}")
        
        finally:
            self._is_cleaning = False
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"收到信号 {signum}，开始清理...")
        try:
            self.cleanup_all()
        except Exception as e:
            logger.error(f"清理过程中发生错误: {e}")
        finally:
            sys.exit(0)

# 全局清理管理器实例
try:
    cleanup_manager = CleanupManager()
    logger.info("✅ 清理管理器已初始化")
except Exception as e:
    logger.error(f"❌ 清理管理器初始化失败: {e}")
    # 创建一个空的清理管理器作为后备
    cleanup_manager = type('CleanupManager', (), {
        'register_cleanup_handler': lambda self, handler: None,
        'cleanup_all': lambda self: None
    })()

def cleanup_sector_rotation_analyzer():
    """清理板块轮动分析器"""
    try:
        # 清理单例实例
        from logic.sector_rotation_analyzer import get_sector_rotation_analyzer
        if hasattr(get_sector_rotation_analyzer, '_instance'):
            instance = get_sector_rotation_analyzer._instance
            # 清理缓存
            instance._industry_data_cache = None
            instance._sector_stocks_cache = None
            # 删除单例实例
            delattr(get_sector_rotation_analyzer, '_instance')
            logger.info("板块轮动分析器已清理")
    except Exception as e:
        logger.debug(f"清理板块轮动分析器失败: {e}")

def cleanup_data_manager():
    """清理数据管理器"""
    try:
        from logic.data_manager import DataManager
        # 清理单例实例
        if DataManager._instance is not None:
            try:
                DataManager._instance.close()
            except Exception as e:
                logger.debug(f"关闭数据库连接失败: {e}")
            DataManager._instance = None
            DataManager._initialized = False
            logger.info("数据管理器已清理")
    except Exception as e:
        logger.debug(f"清理数据管理器失败: {e}")

def cleanup_monitor():
    """清理监控器"""
    try:
        from logic.monitor import Monitor
        # 停止监控
        if hasattr(Monitor, '_instance') and Monitor._instance:
            try:
                Monitor._instance.stop_monitoring()
            except Exception as e:
                logger.debug(f"停止监控失败: {e}")
            delattr(Monitor, '_instance')
            logger.info("监控器已清理")
    except Exception as e:
        logger.debug(f"清理监控器失败: {e}")

# 注册所有清理处理函数
cleanup_manager.register_cleanup_handler(cleanup_sector_rotation_analyzer)
cleanup_manager.register_cleanup_handler(cleanup_data_manager)
cleanup_manager.register_cleanup_handler(cleanup_monitor)

if __name__ == '__main__':
    print("清理管理器已初始化")
    print("所有清理处理函数已注册")
    print("程序退出时会自动执行清理操作")