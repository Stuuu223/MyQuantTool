# -*- coding: utf-8 -*-
"""
快速扫雷 - 单进程顺序版
使用subprocess隔离每只股票的测试
"""
import subprocess
import sys
import os
import json
from datetime import datetime

def quick_sweep(date: str = "20260226", max_stocks: int = 100, market: str = "sh"):
    """快速扫描"""
    # 获取股票列表
    from xtquant import xtdata
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    
    if market == "sh":
        target = [s for s in all_stocks if s.endswith('.SH')][:max_stocks]
    elif market == "sz":
        target = [s for s in all_stocks if s.endswith('.SZ')][:max_stocks]
    else:
        target = all_stocks[:max_stocks]
    
    print(f"🎯 快速扫描 {len(target)} 只股票 ({market.upper()})...")
    
    python_exe = r"E:\MyQuantTool\venv_qmt\Scripts\python.exe"
    worker = r"E:\MyQuantTool\tools\qmt_probe_worker.py"
    
    safe, mines, empty = [], [], []
    
    for i, stock in enumerate(target):
        try:
            result = subprocess.run(
                [python_exe, worker, "--stock", stock, "--date", date, "--period", "tick"],
                capture_output=True, text=True, timeout=8
            )
            code = result.returncode
            if code == 0:
                safe.append(stock)
                status = "✅"
            elif code == 2:
                empty.append(stock)
                status = "⚪"
            else:
                mines.append(stock)
                status = f"💥({code})"
        except subprocess.TimeoutExpired:
            mines.append(stock)
            status = "💥(timeout)"
        except Exception as e:
            mines.append(stock)
            status = f"❌({e})"
        
        print(f"{i+1:3d}. {stock} {status}")
        
        if (i + 1) % 20 == 0:
            print(f"--- 进度: {i+1}/{len(target)} | 安全:{len(safe)} 地雷:{len(mines)} ---")
    
    # 保存结果
    result_path = r"E:\MyQuantTool\data\quick_sweep_result.json"
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "date": date,
            "market": market,
            "total": len(target),
            "safe": safe,
            "mines": mines,
            "empty": empty
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*50}")
    print(f"✅ 扫描完成！")
    print(f"   安全: {len(safe)}")
    print(f"   地雷: {len(mines)}")
    print(f"   无数据: {len(empty)}")
    print(f"   结果已保存: {result_path}")
    
    if mines:
        print(f"\n💥 地雷列表: {mines}")
    
    return mines

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20260226")
    parser.add_argument("--max", type=int, default=50)
    parser.add_argument("--market", default="sh", choices=["sh", "sz", "all"])
    args = parser.parse_args()
    
    quick_sweep(args.date, args.max, args.market)
