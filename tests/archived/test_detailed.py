"""详细测试导入过程"""
import time
import os
import sys

# 禁用 tqdm 进度条
os.environ['TQDM_DISABLE'] = '1'

print("=" * 50)
print("开始详细测试...")
print("=" * 50)

# 逐步测试
steps = [
    ("导入基础库", "import pandas as pd; import streamlit as st; import plotly.graph_objects as go"),
    ("导入配置", "from config import Config"),
    ("导入日志", "from logic.logger import get_logger"),
    ("导入错误处理", "from logic.error_handler import handle_errors, ValidationError"),
    ("导入数据管理器", "from logic.data_manager import DataManager"),
    ("导入算法", "from logic.algo import QuantAlgo"),
    ("导入AI代理", "from logic.ai_agent import DeepSeekAgent"),
    ("导入对比器", "from logic.comparator import StockComparator"),
    ("导入回测引擎", "from logic.backtest import BacktestEngine"),
    ("导入格式化器", "from logic.formatter import Formatter"),
    ("导入importlib", "import importlib"),
]

total_time = 0
for step_name, code in steps:
    start = time.time()
    exec(code)
    elapsed = time.time() - start
    total_time += elapsed
    print(f"[{total_time:.2f}s] {step_name}: {elapsed:.2f}秒")

print(f"\n基础模块总导入时间: {total_time:.2f}秒")

# 现在测试导入main.py，但是不执行它
print("\n开始导入main.py...")
start = time.time()

# 只导入main模块，但不执行它
import importlib.util
spec = importlib.util.spec_from_file_location("main", "main.py")
main_module = importlib.util.module_from_spec(spec)

elapsed = time.time() - start
print(f"创建main模块对象耗时: {elapsed:.2f}秒")

# 现在执行main模块
print("\n开始执行main.py...")
start = time.time()
spec.loader.exec_module(main_module)
elapsed = time.time() - start
print(f"执行main.py耗时: {elapsed:.2f}秒")