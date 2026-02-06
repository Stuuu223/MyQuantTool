#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘工具

用法：
    python tasks/review_daily.py --date 2026-02-06
    python tasks/review_daily.py --date today

功能：
1. 自动对齐系统FOCUS和实际成交
2. 生成A/B/C三类样本
3. 输出Markdown格式的复盘报告

Author: iFlow CLI
Version: V1.0
"""

import argparse
import json
import glob
from datetime import datetime, date
from pathlib import Path

def get_date_from_str(date_str):
    """解析日期字符串"""
    if date_str.lower() == 'today':
        return datetime.now().strftime('%Y-%m-%d')
    return date_str

def get_scan_snapshots(date_str):
    """获取指定日期的所有扫描快照"""
    import os
    
    # 使用Path来处理路径，确保跨平台兼容
    scan_dir = Path("data/scan_results")
    pattern = f"{date_str}_*_intraday.json"
    
    # 使用glob匹配文件
    files = list(scan_dir.glob(pattern))
    
    # 转换为字符串路径
    file_paths = [str(f) for f in files]
    
    # 按时间排序
    file_paths.sort()
    
    snapshots = {}
    for file_path in file_paths:
        # 提取时间点：2026-02-06_092157_intraday.json -> 092157
        filename = os.path.basename(file_path)
        time_part = filename.split('_')[1][:6]
        with open(file_path, 'r', encoding='utf-8') as f:
            snapshots[time_part] = json.load(f)
    
    return snapshots

def get_trade_records(date_str):
    """获取指定日期的成交记录"""
    file_path = Path(f"data/trade_records_{date_str}.json")
    
    if not file_path.exists():
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('trades', [])

def calculate_decision_tag(item):
    """计算决策标签"""
    # 获取占比
    flow_data = item.get('flow_data', {})
    latest = flow_data.get('latest', {})
    main_net_yuan = latest.get('main_net_inflow', 0)
    
    # 计算流通市值
    circulating_market_cap = item.get('circulating_market_cap', 0)
    if circulating_market_cap > 0:
        ratio = main_net_yuan / circulating_market_cap * 100
    else:
        ratio = 0
    
    # 获取风险和诱多信号
    risk_score = item.get('risk_score', 0)
    trap_signals = item.get('trap_signals', [])
    
    # 判断是否是标准FOCUS
    is_standard_focus = (
        ratio >= 1.0 and           # 占比 ≥ 1%
        risk_score <= 0.2 and      # 风险 ≤ 0.2
        len(trap_signals) == 0     # 无诱多信号
    )
    
    return is_standard_focus, ratio, risk_score, trap_signals

def analyze_snapshot(snapshot, traded_codes):
    """分析单个快照，返回A/B/C类"""
    results = snapshot.get('results', {})
    opportunities = results.get('opportunities', [])
    
    class_a = []  # 系统FOCUS + 有上
    class_b = []  # 系统FOCUS + 没上
    class_c = []  # 系统没FOCUS + 乱上
    
    for item in opportunities:
        code = item.get('code', '')
        
        # 判断是否是标准FOCUS
        is_standard_focus, ratio, risk_score, trap_signals = calculate_decision_tag(item)
        
        if is_standard_focus:
            if code in traded_codes:
                class_a.append({
                    'code': code,
                    'ratio': ratio,
                    'risk_score': risk_score,
                    'trap_signals': trap_signals,
                    'time': item.get('scan_time', '')
                })
            else:
                class_b.append({
                    'code': code,
                    'ratio': ratio,
                    'risk_score': risk_score,
                    'trap_signals': trap_signals,
                    'time': item.get('scan_time', '')
                })
    
    # 处理C类（系统没FOCUS + 乱上）
    for item in opportunities:
        code = item.get('code', '')
        is_standard_focus, ratio, risk_score, trap_signals = calculate_decision_tag(item)
        
        if not is_standard_focus and code in traded_codes:
            class_c.append({
                'code': code,
                'ratio': ratio,
                'risk_score': risk_score,
                'trap_signals': trap_signals,
                'time': item.get('scan_time', '')
            })
    
    return class_a, class_b, class_c

def generate_review_report(date_str, all_class_a, all_class_b, all_class_c):
    """生成Markdown格式的复盘报告"""
    report = f"""# 复盘报告：{date_str}

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 统计摘要

- 🔥 **B类样本**（系统FOCUS + 没上）：{len(all_class_b)} 只
- ✅ **A类样本**（系统FOCUS + 有上）：{len(all_class_a)} 只
- ❌ **C类样本**（系统没FOCUS + 乱上）：{len(all_class_c)} 只

---

## 🔥 B类样本（系统FOCUS + 没上）

"""
    
    if not all_class_b:
        report += "🎉 太棒了！今天没有B类样本，说明你严格执行了纪律！\n\n"
    else:
        # 去重（同一只股票可能多次出现）
        unique_b = {}
        for item in all_class_b:
            code = item['code']
            if code not in unique_b:
                unique_b[code] = item
        
        for item in unique_b.values():
            report += f"""### {item['code']}
- **风险**：L{item['risk_score']:.1f}
- **占比**：{item['ratio']:.2f}%
- **诱多信号**：{', '.join(item['trap_signals']) if item['trap_signals'] else '无'}
- **时间**：{item['time']}

**问题**：为什么没上？

**教训**：

**下次**：

---

"""
    
    report += """## ✅ A类样本（系统FOCUS + 有上）

"""
    
    if not all_class_a:
        report += "今天没有A类样本。\n\n"
    else:
        # 去重
        unique_a = {}
        for item in all_class_a:
            code = item['code']
            if code not in unique_a:
                unique_a[code] = item
        
        for item in unique_a.values():
            report += f"""### {item['code']}
- **风险**：L{item['risk_score']:.1f}
- **占比**：{item['ratio']:.2f}%
- **诱多信号**：{', '.join(item['trap_signals']) if item['trap_signals'] else '无'}
- **时间**：{item['time']}

**执行**：符合纪律 ✅

---

"""
    
    report += """## ❌ C类样本（系统没FOCUS + 乱上）

"""
    
    if not all_class_c:
        report += "今天没有C类样本，做得好！\n\n"
    else:
        # 去重
        unique_c = {}
        for item in all_class_c:
            code = item['code']
            if code not in unique_c:
                unique_c[code] = item
        
        for item in unique_c.values():
            report += f"""### {item['code']}
- **风险**：L{item['risk_score']:.1f}
- **占比**：{item['ratio']:.2f}%
- **诱多信号**：{', '.join(item['trap_signals']) if item['trap_signals'] else '无'}
- **时间**：{item['time']}

**问题**：为什么没有系统信号就上？

**教训**：不看系统信号就上车 = 赌博

**下次**：先看系统信号，再决定是否上车

---

"""
    
    report += f"""---

## 💡 复盘总结

**今日表现**：
- B类样本数量：{len(all_class_b)}
- 执行质量：{'优秀' if len(all_class_b) == 0 and len(all_class_c) == 0 else '需要改进'}

**改进方向**：
"""
    
    if all_class_b:
        report += "- 重点关注B类样本，分析为什么没上\n"
    if all_class_c:
        report += "- 严格执行纪律，系统没FOCUS就不要上\n"
    if not all_class_b and not all_class_c:
        report += "- 继续保持，执行纪律！\n"
    
    report += "\n---\n\n*本报告由系统自动生成，请手动填写\"问题\"、\"教训\"、\"下次\"部分。*"
    
    return report

def save_review_report(date_str, report):
    """保存复盘报告"""
    review_dir = Path("data/review")
    review_dir.mkdir(exist_ok=True)
    
    file_path = review_dir / f"{date_str}_review.md"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return file_path

def main():
    parser = argparse.ArgumentParser(description='每日复盘工具')
    parser.add_argument('--date', required=True, help='复盘日期（格式：YYYY-MM-DD）')
    
    args = parser.parse_args()
    
    date_str = get_date_from_str(args.date)
    
    print(f"📊 开始复盘：{date_str}")
    print("=" * 80)
    
    # 1. 获取扫描快照
    print("📖 读取扫描快照...")
    snapshots = get_scan_snapshots(date_str)
    
    if not snapshots:
        print(f"❌ 未找到 {date_str} 的扫描快照")
        return
    
    print(f"✅ 找到 {len(snapshots)} 个快照")
    
    # 2. 获取成交记录
    print("📖 读取成交记录...")
    trades = get_trade_records(date_str)
    
    if not trades:
        print(f"⚠️  未找到 {date_str} 的成交记录")
        print("💡 提示：请先使用 record_trade.py 记录成交")
        # 继续执行，因为即使没有成交记录，也需要分析B类样本
    
    print(f"✅ 找到 {len(trades)} 笔成交")
    
    # 3. 提取成交的股票代码
    traded_codes = set()
    for trade in trades:
        traded_codes.add(trade['code'])
    
    # 4. 分析所有快照
    print("🔍 分析快照...")
    all_class_a = []
    all_class_b = []
    all_class_c = []
    
    for time_point, snapshot in snapshots.items():
        class_a, class_b, class_c = analyze_snapshot(snapshot, traded_codes)
        all_class_a.extend(class_a)
        all_class_b.extend(class_b)
        all_class_c.extend(class_c)
    
    print(f"✅ 分析完成：A类{len(all_class_a)}只，B类{len(all_class_b)}只，C类{len(all_class_c)}只")
    
    # 5. 生成复盘报告
    print("📝 生成复盘报告...")
    report = generate_review_report(date_str, all_class_a, all_class_b, all_class_c)
    
    # 6. 保存复盘报告
    file_path = save_review_report(date_str, report)
    
    print(f"✅ 复盘报告已保存：{file_path}")
    print("=" * 80)
    print(f"\n💡 请打开复盘报告，手动填写B类样本的\"问题\"、\"教训\"、\"下次\"部分")
    print(f"   文件路径：{file_path}")
    print()

if __name__ == "__main__":
    main()