"""测试导入速度"""
import time
import os
import sys

# 禁用 tqdm 进度条
os.environ['TQDM_DISABLE'] = '1'

print("开始测试导入速度...")

# 测试各个模块的导入时间
modules = [
    ('pandas', 'import pandas as pd'),
    ('streamlit', 'import streamlit as st'),
    ('plotly', 'import plotly.graph_objects as go'),
    ('data_manager', 'from logic.data_manager import DataManager'),
    ('algo', 'from logic.algo import QuantAlgo'),
    ('ai_agent', 'from logic.ai_agent import DeepSeekAgent'),
    ('comparator', 'from logic.comparator import StockComparator'),
    ('backtest', 'from logic.backtest import BacktestEngine'),
]

results = {}
for name, import_stmt in modules:
    start = time.time()
    exec(import_stmt)
    elapsed = time.time() - start
    results[name] = elapsed
    print(f"{name}: {elapsed:.2f}秒")

print(f"\n总导入时间: {sum(results.values()):.2f}秒")