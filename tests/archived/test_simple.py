"""简单测试导入"""
import time
import os
os.environ['TQDM_DISABLE'] = '1'

print("开始测试...")

# 测试导入main.py
start = time.time()
import main
elapsed = time.time() - start
print(f"导入main.py耗时: {elapsed:.2f}秒")