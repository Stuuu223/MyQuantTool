# -*- coding: utf-8 -*-
"""
IPythonApiClient 占位符

注意：这是 xtquant 的底层通信模块，通常由 QMT 官方提供。
完整的 IPythonApiClient 需要从 QMT 安装目录的 bin.x64/Lib/site-packages 中复制。

临时解决方案：
1. 从 QMT 客户端安装目录复制 IPythonApiClient.py 和 xtpythonclient.py 到此目录
2. 或者设置 PYTHONPATH 指向 QMT 的 bin.x64/Lib/site-packages

如果无法获取，QMT 数据接口将无法使用，但不影响其他数据源（easyquotation、AkShare）。

Author: iFlow CLI
Date: 2026-01-28
Version: V1.1
"""


class IPythonApiClient:
    """占位符类"""
    def __init__(self, config):
        self.config = config
        raise NotImplementedError(
            "IPythonApiClient 需要从 QMT 官方安装目录获取。\n"
            "请从 QMT 客户端的 bin.x64/Lib/site-packages 复制以下文件到 xtquant 目录：\n"
            "  - IPythonApiClient.py\n"
            "  - xtpythonclient.py\n"
            "或设置 PYTHONPATH 环境变量指向 QMT 安装目录。"
        )


def rpc_init(config_file):
    """
    RPC 初始化函数占位符

    Returns:
        int: 初始化状态码（-1 表示失败）
    """
    import warnings
    warnings.warn(
        "QMT IPythonApiClient 模块未正确安装。\n"
        "如需使用 QMT 数据接口，请从 QMT 客户端安装目录复制必要文件。",
        UserWarning
    )
    return -1


def register_create_nparray(func):
    """
    注册 numpy 数组创建函数占位符

    Args:
        func: 数组创建函数

    Returns:
        None
    """
    import warnings
    warnings.warn(
        "QMT IPythonApiClient 模块未正确安装，register_create_nparray 被禁用。",
        UserWarning
    )
    pass