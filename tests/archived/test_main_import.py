"""测试main.py导入速度"""
import time
import os
import sys

# 禁用 tqdm 进度条
os.environ['TQDM_DISABLE'] = '1'

print("开始测试main.py导入速度...")

# 逐步导入，找出阻塞点
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
]

total_time = 0
for step_name, code in steps:
    start = time.time()
    exec(code)
    elapsed = time.time() - start
    total_time += elapsed
    print(f"{step_name}: {elapsed:.2f}秒")

print(f"\n基础模块总导入时间: {total_time:.2f}秒")

# 现在测试导入main.py
start = time.time()
import main
elapsed = time.time() - start
print(f"\n导入main.py总耗时: {elapsed:.2f}秒")