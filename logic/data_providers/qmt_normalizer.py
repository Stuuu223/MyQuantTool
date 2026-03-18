# -*- coding: utf-8 -*-
"""
[DEPRECATED in V192]

此模块已被架构级废弃。运行时量纲猜测已由盘前静态数据泵替代。

保留此空文件仅为防止历史导入引发 ModuleNotFoundError。
原始功能已迁移至 TrueDictionary 内部处理。

Author: CTO Architecture Team
Date: 2026-03-17
"""


def __getattr__(name):
    raise DeprecationWarning(
        f"qmt_normalizer 模块已被废弃 (V192)。"
        f"无法访问 {name}。请使用 TrueDictionary 获取量纲校正后的数据。"
    )
