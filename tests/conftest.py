# -*- coding: utf-8 -*-
"""
pytest配置文件

【CTO V183 性能优化】
解决logic/__init__.py导入链触发xtquant加载的问题：
- logic/__init__.py → true_dictionary.py → xtquant (2秒加载)
- 预注册logic模块，跳过__init__.py执行
- 仅影响测试环境，不影响生产代码

Author: CTO
Date: 2026-03-15
"""

import sys
from pathlib import Path

# 预注册logic模块，跳过logic/__init__.py的自动执行
# 这样 from logic.core.physics_sensors import ... 就不会触发xtquant加载
if 'logic' not in sys.modules:
    import types
    logic_module = types.ModuleType('logic')
    logic_module.__path__ = [str(Path(__file__).parent.parent / 'logic')]
    logic_module.__file__ = None
    sys.modules['logic'] = logic_module
