"""
清理管理器 - 确保程序退出时正确清理所有资源
"""

import atexit
from logic.logger import get_logger

logger = get_logger(__name__)


def cleanup_manager():
    """
    清理管理器 - 注册退出时执行的清理函数
    
    注意：Streamlit 在非主线程中运行，不支持 signal.signal()
    因此仅使用 atexit.register 来注册清理函数
    """
    def cleanup():
        """执行清理操作"""
        try:
            logger.info("🧹 开始清理资源...")
            
            # 清理数据库连接
            from logic.database_manager import get_db_manager
            db = get_db_manager()
            db.close()
            
            logger.info("✅ 资源清理完成")
        except Exception as e:
            logger.error(f"❌ 清理资源失败: {e}")
    
    # 注册退出函数（Streamlit 支持这种方式）
    atexit.register(cleanup)
    logger.debug("✅ 清理管理器已注册")


# 自动注册
cleanup_manager()