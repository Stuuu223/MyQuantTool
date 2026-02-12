"""
错误处理模块

提供统一的错误处理装饰器和异常类
"""

import functools
from typing import Callable, Any, Optional
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """应用基础异常类"""
    def __init__(self, message: str, user_message: Optional[str] = None) -> None:
        self.message = message
        self.user_message = user_message or message
        super().__init__(self.message)


class DataError(AppError):
    """数据相关异常"""
    pass


class NetworkError(AppError):
    """网络相关异常"""
    pass


class ValidationError(AppError):
    """参数验证异常"""
    pass


class ConfigError(AppError):
    """配置相关异常"""
    pass


def handle_errors(func: Callable = None, *, show_user_message: bool = True) -> Callable:
    """
    统一的错误处理装饰器
    
    捕获函数执行过程中的各种异常，并记录日志。
    可以选择是否向用户显示友好的错误信息。
    
    Args:
        func: 被装饰的函数
        show_user_message: 是否显示用户友好的错误信息，默认 True
        
    Returns:
        装饰后的函数
        
    Raises:
        AppError: 应用自定义异常（会被捕获并记录）
        ValueError: 参数错误（会被捕获并记录）
        ConnectionError: 网络连接错误（会被捕获并记录）
        TimeoutError: 超时错误（会被捕获并记录）
        KeyError: 键错误（会被捕获并记录）
        Exception: 其他未知异常（会被捕获并记录）
        
    Example:
        >>> @handle_errors(show_user_message=True)
        >>> def get_stock_data(symbol: str):
        >>>     # 业务逻辑
        >>>     pass
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return f(*args, **kwargs)
                
            except AppError as e:
                # 应用自定义异常
                logger.error(f"{f.__name__} 失败: {e.message}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.error(f"❌ {e.user_message}")
                return None
                
            except ValueError as e:
                # 参数错误
                logger.error(f"{f.__name__} 参数错误: {e}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.error(f"❌ 参数错误: {str(e)}")
                return None
                
            except ConnectionError as e:
                # 网络连接错误
                logger.error(f"{f.__name__} 网络错误: {e}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.error("❌ 网络连接失败，请检查网络连接")
                return None
                
            except TimeoutError as e:
                # 超时错误
                logger.error(f"{f.__name__} 超时: {e}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.warning("⏱️ 请求超时，请稍后重试")
                return None
                
            except KeyError as e:
                # 键错误
                logger.error(f"{f.__name__} 键错误: {e}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.error(f"❌ 数据格式错误: {str(e)}")
                return None
                
            except Exception as e:
                # 未知错误
                logger.error(f"{f.__name__} 未知错误: {type(e).__name__}: {e}", exc_info=True)
                if show_user_message:
                    import streamlit as st
                    st.error(f"❌ 操作失败，请稍后重试")
                return None
                
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def safe_execute(func: Callable, default_value: Any = None, log_error: bool = True) -> Any:
    """
    安全执行函数，捕获所有异常
    
    在不确定函数是否会抛出异常时使用此函数，避免程序崩溃。
    
    Args:
        func: 要执行的函数
        default_value: 发生异常时返回的默认值，默认 None
        log_error: 是否记录错误日志，默认 True
        
    Returns:
        函数执行结果或默认值
        
    Example:
        >>> result = safe_execute(lambda: risky_operation(), default_value=0)
        >>> print(result)
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"函数执行失败: {func.__name__}: {e}", exc_info=True)
        return default_value


def validate_stock_code(code: str) -> bool:
    """
    验证股票代码格式
    
    Args:
        code: 股票代码
        
    Returns:
        是否有效
        
    Raises:
        ValidationError: 代码格式无效
    """
    import re
    
    if not code or not isinstance(code, str):
        raise ValidationError("股票代码不能为空")
    
    if not re.match(r'^\d{6}$', code):
        raise ValidationError(f"股票代码格式错误: {code}，应为6位数字")
    
    return True


def validate_date(date_str: str) -> bool:
    """
    验证日期格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        是否有效
        
    Raises:
        ValidationError: 日期格式无效
    """
    import re
    from datetime import datetime
    
    if not date_str or not isinstance(date_str, str):
        raise ValidationError("日期不能为空")
    
    if not re.match(r'^\d{8}$', date_str):
        raise ValidationError(f"日期格式错误: {date_str}，应为YYYYMMDD格式")
    
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValidationError(f"日期无效: {date_str}")
    
    return True