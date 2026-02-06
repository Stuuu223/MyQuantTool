#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成交记录工具

用法：
    # 记录买入
    python tasks/record_trade.py --action buy --code 603607 --amount 10000 --note "看到FOCUS，按纪律执行"
    
    # 记录卖出
    python tasks/record_trade.py --action sell --code 603607 --amount 5000 --note "风险上升，减仓"
    
    # 查看今日成交
    python tasks/record_trade.py --list

Author: iFlow CLI
Version: V1.0
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

def get_trade_record_path():
    """获取成交记录文件路径"""
    # 使用今天的日期
    today = datetime.now().strftime('%Y-%m-%d')
    file_path = Path(f"data/trade_records_{today}.json")
    file_path.parent.mkdir(exist_ok=True)
    return file_path

def load_trades():
    """加载今日成交记录"""
    file_path = get_trade_record_path()
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('trades', [])
    return []

def save_trades(trades):
    """保存今日成交记录"""
    file_path = get_trade_record_path()
    today = datetime.now().strftime('%Y-%m-%d')
    data = {
        'date': today,
        'trades': trades
    }
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_trade(action, code, amount, note=''):
    """添加成交记录"""
    trades = load_trades()
    
    trade = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'action': action,  # buy/sell
        'code': code.upper(),
        'amount': float(amount),
        'note': note
    }
    
    trades.append(trade)
    save_trades(trades)
    
    print(f"✅ 记录成功：{action} {code} {amount}元")
    if note:
        print(f"   备注：{note}")

def list_trades():
    """列出今日成交记录"""
    trades = load_trades()
    
    if not trades:
        print("📭 今日暂无成交记录")
        return
    
    print(f"\n📊 今日成交记录（{len(trades)}笔）")
    print("=" * 80)
    print(f"{'时间':<10} {'操作':<6} {'代码':<10} {'金额(元)':>10} {'备注':<30}")
    print("-" * 80)
    
    for trade in trades:
        print(f"{trade['time']:<10} {trade['action']:<6} {trade['code']:<10} {trade['amount']:>10.0f} {trade['note']:<30}")
    
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='成交记录工具')
    parser.add_argument('--action', choices=['buy', 'sell'], help='操作类型')
    parser.add_argument('--code', help='股票代码')
    parser.add_argument('--amount', type=float, help='成交金额（元）')
    parser.add_argument('--note', default='', help='备注')
    parser.add_argument('--list', action='store_true', help='列出今日成交记录')
    
    args = parser.parse_args()
    
    if args.list:
        list_trades()
    elif args.action and args.code and args.amount:
        add_trade(args.action, args.code, args.amount, args.note)
    else:
        parser.print_help()
