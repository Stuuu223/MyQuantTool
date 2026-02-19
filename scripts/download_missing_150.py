#!/usr/bin/env python3
"""
下载顽主杯Top150中缺失的73只股票Tick数据
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 检查QMT虚拟环境
IN_VENV_QMT = os.path.exists(PROJECT_ROOT / 'venv_qmt')

try:
    from xtquant import xtdatacenter as xtdc
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    print("❌ 错误: xtquant模块未安装")
    print("💡 请运行: venv_qmt\\Scripts\\activate")
    sys.exit(1)

from logic.utils.logger import get_logger

logger = get_logger(__name__)

VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"

def start_token_service():
    """启动xtdatacenter服务"""
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    xtdc.set_token(VIP_TOKEN)
    xtdc.init()
    listen_port = xtdc.listen(port=(58800, 58850))
    logger.info(f"行情服务已启动，端口: {listen_port}")
    return listen_port

def load_missing_stocks():
    """从缺失列表加载"""
    missing_file = PROJECT_ROOT / 'logs' / 'tick_missing_150.txt'
    if not missing_file.exists():
        print("❌ 未找到缺失列表，请先运行检查脚本")
        sys.exit(1)
    
    stocks = []
    with open(missing_file, 'r') as f:
        for line in f:
            qmt_code = line.strip()
            if qmt_code:
                stocks.append(qmt_code)
    
    return stocks

def download_tick(qmt_code, max_retries=3):
    """下载单只股票Tick数据"""
    for attempt in range(max_retries):
        try:
            xtdata.download_history_data(
                stock_code=qmt_code,
                period='tick',
                start_time='20251115000000',
                end_time='20260213150000'
            )
            return True
        except Exception as e:
            logger.warning(f"下载失败 (尝试 {attempt + 1}/{max_retries}): {qmt_code} - {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"下载彻底失败: {qmt_code}")
                return False

def main():
    print("=" * 70)
    print("🚀 顽主杯Top150缺失股票Tick数据下载")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载缺失列表
    stocks = load_missing_stocks()
    print(f"📋 需要下载: {len(stocks)} 只股票")
    print()
    
    if not stocks:
        print("✅ 没有缺失的股票，无需下载")
        return
    
    # 启动Token服务
    print("🌐 启动Token服务...")
    try:
        listen_port = start_token_service()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return
    
    # 连接行情服务
    _, port = listen_port
    xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)
    
    print("⏳ 连接行情服务...")
    time.sleep(3)
    
    # 开始下载
    print()
    print("=" * 70)
    print("🚀 开始下载Tick数据...")
    print("=" * 70)
    print()
    
    success_count = 0
    fail_count = 0
    fail_stocks = []
    
    start_time = time.time()
    
    for i, qmt_code in enumerate(stocks, 1):
        # 显示进度
        progress = i / len(stocks) * 100
        elapsed = time.time() - start_time
        eta = elapsed / i * (len(stocks) - i) if i > 0 else 0
        
        print(f"\r[{i}/{len(stocks)}] {progress:.1f}% | {qmt_code} | "
              f"✅{success_count} ❌{fail_count} | ETA: {eta/60:.1f}min", end='', flush=True)
        
        # 下载
        if download_tick(qmt_code):
            success_count += 1
            logger.info(f"[{i}/{len(stocks)}] 成功: {qmt_code}")
        else:
            fail_count += 1
            fail_stocks.append(qmt_code)
            logger.error(f"[{i}/{len(stocks)}] 失败: {qmt_code}")
        
        time.sleep(0.3)  # 避免请求过快
    
    # 完成统计
    print()
    print()
    print("=" * 70)
    print("📊 下载完成统计")
    print("=" * 70)
    print(f"总股票数: {len(stocks)}")
    print(f"成功: {success_count} 只 ({success_count/len(stocks)*100:.1f}%)")
    print(f"失败: {fail_count} 只 ({fail_count/len(stocks)*100:.1f}%)")
    print(f"总耗时: {(time.time() - start_time)/60:.1f} 分钟")
    
    if fail_stocks:
        print()
        print(f"❌ 失败股票 ({len(fail_stocks)} 只):")
        for code in fail_stocks:
            print(f"  - {code}")
    
    print()
    print("=" * 70)
    print("🎉 任务完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
