import sys
import time
import inspect
from xtquant import xtdata

print("=== 1. 底层物理环境验证 ===")
print(f"Python版本: {sys.version.split(' ')[0]}")
try:
    print(f"xtdata文件物理路径: {inspect.getfile(xtdata)}")
except Exception as e:
    print(f"路径获取异常: {e}")

print("\n=== 2. 异步下载能力验证 ===")
try:
    xtdata.connect(port=58610)
    print("QMT连接状态: 成功")
    
    # 测试老接口
    t1 = time.time()
    xtdata.download_history_data('000001.SZ', '1d', '20260301', '20260303')
    t2 = time.time()
    print(f"download_history_data 耗时: {t2-t1:.4f}秒")
    
    # 测试新接口
    t3 = time.time()
    xtdata.download_history_data2(stock_list=['000002.SZ'], period='1d', start_time='20260301', end_time='20260303')
    t4 = time.time()
    elapsed = t4 - t3
    print(f"download_history_data2 耗时: {elapsed:.4f}秒")
    
    if elapsed < 0.1:
        print("物理结论: 当前环境的 download_history_data2 是【异步】的（非阻塞秒回）。")
    else:
        print("物理结论: 当前环境的 download_history_data2 是【同步】的（发生阻塞等待）。")
        
except Exception as e:
    print(f"测试失败: {e}")