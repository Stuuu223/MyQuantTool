# -*- coding: utf-8 -*-
"""
战报渲染器

将 UniversalTracker.get_full_report() 产出的结构化数据渲染为：
1. 终端 ASCII 表格（scan 结束时自动打印）
2. JSON 文件（已由 universal_tracker 处理）
3. 可选 HTML 文件（简单，方便浏览器查看）

Author: CTO Research Lab
Date: 2026-03-16
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def format_pct(value: float, with_sign: bool = True) -> str:
    """
    格式化百分比，带颜色标记（ANSI escape codes）
    
    Args:
        value: 百分比值（如 5.5 表示 5.5%）
        with_sign: 是否带正负号
        
    Returns:
        格式化后的字符串，正数绿色，负数红色
    """
    # ANSI颜色码
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    
    # 检测是否支持ANSI（Windows兼容）
    try:
        # 尝试获取终端宽度，失败则不支持ANSI
        _ = os.get_terminal_size()
        supports_ansi = True
    except Exception:
        supports_ansi = False
    
    if with_sign:
        formatted = f"{value:+.2f}%"
    else:
        formatted = f"{value:.2f}%"
    
    if not supports_ansi:
        return formatted
    
    if value > 0:
        return f"{GREEN}{formatted}{RESET}"
    elif value < 0:
        return f"{RED}{formatted}{RESET}"
    else:
        return formatted


def render_terminal_battle_report(report: Dict) -> None:
    """
    终端渲染战报
    
    Args:
        report: UniversalTracker.get_full_report() 返回的战报数据
    """
    session_id = report.get('session_id', 'unknown')
    summary = report.get('summary', {})
    all_stocks = report.get('all_stocks', [])
    
    # 表格宽度
    width = 90
    
    print()
    print("╔" + "═" * (width - 2) + "╗")
    print(f"║ {'📊 今日战报 | ' + session_id + ' | 沙盘模式':^{width-4}} ║")
    print("╠" + "═" * 8 + "╦" + "═" * 10 + "╦" + "═" * 8 + "╦" + "═" * 8 + "╦" + "═" * 10 + "╦" + "═" * 8 + "╦" + "═" * 10 + "╣")
    print(f"║ {'代码':^6} ║ {'首次上榜':^8} ║ {'峰值分':^6} ║ {'首榜价':^6} ║ {'最高涨幅':^8} ║ {'买入':^4} ║ {'实际盈亏':^8} ║")
    print("╠" + "═" * 8 + "╬" + "═" * 10 + "╬" + "═" * 8 + "╬" + "═" * 8 + "╬" + "═" * 10 + "╬" + "═" * 8 + "╬" + "═" * 10 + "╣")
    
    # 显示前20只股票
    for i, stock in enumerate(all_stocks[:20]):
        code = stock.get('code', '')[:8]
        first_time = stock.get('first_appear_time', '')[-8:]  # 只取时间部分
        peak_score = stock.get('peak_score', 0)
        first_price = stock.get('first_appear_price', 0)
        max_gain = stock.get('max_gain_pct', 0)
        was_bought = stock.get('was_bought', False)
        actual_pnl = stock.get('actual_pnl_pct', 0)
        missed_gain = stock.get('missed_gain_pct', 0)
        
        # 买入标记
        buy_mark = "✅" if was_bought else "❌"
        
        # 盈亏显示
        if was_bought:
            pnl_str = format_pct(actual_pnl)
        else:
            pnl_str = f"错过{format_pct(missed_gain, with_sign=False)}"
        
        print(f"║ {code:^6} ║ {first_time:^8} ║ {peak_score:^6.1f} ║ {first_price:^6.2f} ║ {format_pct(max_gain):^8} ║ {buy_mark:^4} ║ {pnl_str:^18} ║")
    
    print("╚" + "═" * 8 + "╩" + "═" * 10 + "╩" + "═" * 8 + "╩" + "═" * 8 + "╩" + "═" * 10 + "╩" + "═" * 8 + "╩" + "═" * 10 + "╝")
    
    # 摘要行
    total_appeared = summary.get('total_appeared', 0)
    bought_count = summary.get('bought_count', 0)
    best_missed = summary.get('best_missed', {})
    
    print()
    print(f"📋 总结: 今日上榜 {total_appeared} 只 | 实际买入 {bought_count} 次", end="")
    
    if best_missed:
        best_missed_code = best_missed.get('code', '')
        best_missed_gain = best_missed.get('max_gain_pct', 0)
        print(f" | 最可惜错过: {best_missed_code} ({format_pct(best_missed_gain)})")
    else:
        print()
    
    # 双引擎对比（如果有）
    if 'paper_vs_friction' in report:
        pvf = report['paper_vs_friction']
        print()
        print("══════════════════════════════════════════════════════════════════════════════")
        print(f"📊 双引擎对比:")
        print(f"   理想收益(零摩擦): {format_pct(pvf.get('paper_pnl_pct', 0))}")
        print(f"   真实收益(含摩擦): {format_pct(pvf.get('friction_pnl_pct', 0))}")
        print(f"   摩擦损耗: {pvf.get('alpha_lost_to_friction', 0):+.2f}pp")
        
        verdict = pvf.get('verdict', 'UNKNOWN')
        if verdict == 'FRICTION_ACCEPTABLE':
            print(f"   裁定: ✅ 摩擦可接受（损耗<1.5pp）")
        else:
            print(f"   裁定: ⚠️ 摩擦过高（损耗>=1.5pp）")
        print("══════════════════════════════════════════════════════════════════════════════")


def render_html_battle_report(report: Dict, output_path: str) -> None:
    """
    渲染简单 HTML 战报（无外部依赖，纯 f-string 拼接）
    
    Args:
        report: UniversalTracker.get_full_report() 返回的战报数据
        output_path: 输出文件路径
    """
    session_id = report.get('session_id', 'unknown')
    summary = report.get('summary', {})
    all_stocks = report.get('all_stocks', [])
    
    # 构建HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>战报 - {session_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }}
        h1 {{
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #16213e;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #888;
            font-size: 14px;
        }}
        .card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #00d4ff;
        }}
        .card.positive .value {{ color: #00ff88; }}
        .card.negative .value {{ color: #ff6b6b; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #2a2a4a;
        }}
        th {{
            background: #0f3460;
            color: #00d4ff;
            font-weight: 600;
        }}
        tr:hover {{
            background: #1f4068;
        }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff6b6b; }}
        .bought {{ background: rgba(0, 255, 136, 0.1); }}
        .missed {{ background: rgba(255, 107, 107, 0.05); }}
        .verdict {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-size: 18px;
        }}
        .verdict.accept {{ background: rgba(0, 255, 136, 0.2); color: #00ff88; }}
        .verdict.reject {{ background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }}
    </style>
</head>
<body>
    <h1>📊 今日战报 | {session_id}</h1>
    
    <div class="summary-cards">
        <div class="card">
            <h3>上榜总数</h3>
            <div class="value">{summary.get('total_appeared', 0)}</div>
        </div>
        <div class="card">
            <h3>实际买入</h3>
            <div class="value">{summary.get('bought_count', 0)}</div>
        </div>
        <div class="card">
            <h3>错过只数</h3>
            <div class="value">{summary.get('missed_count', 0)}</div>
        </div>
        <div class="card {'positive' if summary.get('avg_bought_pnl', 0) > 0 else 'negative'}">
            <h3>平均买入盈亏</h3>
            <div class="value">{summary.get('avg_bought_pnl', 0):+.2f}%</div>
        </div>
        <div class="card positive">
            <h3>平均错过涨幅</h3>
            <div class="value">{summary.get('avg_missed_gain', 0):.2f}%</div>
        </div>
    </div>
    
    <h2>📋 详细记录</h2>
    <table>
        <thead>
            <tr>
                <th>代码</th>
                <th>首次上榜</th>
                <th>峰值分</th>
                <th>首榜价</th>
                <th>最高涨幅</th>
                <th>买入</th>
                <th>实际盈亏</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for stock in all_stocks:
        code = stock.get('code', '')
        first_time = stock.get('first_appear_time', '')
        peak_score = stock.get('peak_score', 0)
        first_price = stock.get('first_appear_price', 0)
        max_gain = stock.get('max_gain_pct', 0)
        was_bought = stock.get('was_bought', False)
        actual_pnl = stock.get('actual_pnl_pct', 0)
        missed_gain = stock.get('missed_gain_pct', 0)
        
        row_class = 'bought' if was_bought else 'missed'
        buy_mark = '✅' if was_bought else '❌'
        pnl_class = 'positive' if actual_pnl > 0 else 'negative' if actual_pnl < 0 else ''
        
        if was_bought:
            pnl_str = f"<span class='{pnl_class}'>{actual_pnl:+.2f}%</span>"
        else:
            pnl_str = f"错过 <span class='positive'>{missed_gain:.2f}%</span>"
        
        html += f"""            <tr class="{row_class}">
                <td>{code}</td>
                <td>{first_time}</td>
                <td>{peak_score:.1f}</td>
                <td>{first_price:.2f}</td>
                <td class="positive">{max_gain:+.2f}%</td>
                <td>{buy_mark}</td>
                <td>{pnl_str}</td>
            </tr>
"""
    
    html += """        </tbody>
    </table>
"""
    
    # 双引擎对比
    if 'paper_vs_friction' in report:
        pvf = report['paper_vs_friction']
        verdict = pvf.get('verdict', 'UNKNOWN')
        verdict_class = 'accept' if verdict == 'FRICTION_ACCEPTABLE' else 'reject'
        
        html += f"""
    <h2>📊 双引擎对比</h2>
    <div class="summary-cards">
        <div class="card">
            <h3>理想收益(零摩擦)</h3>
            <div class="value {'positive' if pvf.get('paper_pnl_pct', 0) > 0 else 'negative'}">{pvf.get('paper_pnl_pct', 0):+.2f}%</div>
        </div>
        <div class="card">
            <h3>真实收益(含摩擦)</h3>
            <div class="value {'positive' if pvf.get('friction_pnl_pct', 0) > 0 else 'negative'}">{pvf.get('friction_pnl_pct', 0):+.2f}%</div>
        </div>
        <div class="card negative">
            <h3>摩擦损耗</h3>
            <div class="value">{pvf.get('alpha_lost_to_friction', 0):+.2f}pp</div>
        </div>
    </div>
    <div class="verdict {verdict_class}">
        裁定: {'✅ 摩擦可接受（损耗<1.5pp）' if verdict == 'FRICTION_ACCEPTABLE' else '⚠️ 摩擦过高（损耗>=1.5pp）'}
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"[OK] HTML战报已生成: {output_path}")


def render_battle_report_to_files(report: Dict, output_dir: str = 'data/battle_reports') -> Dict[str, str]:
    """
    将战报渲染到多个文件
    
    Args:
        report: UniversalTracker.get_full_report() 返回的战报数据
        output_dir: 输出目录
        
    Returns:
        生成的文件路径字典
    """
    session_id = report.get('session_id', 'unknown')
    
    os.makedirs(output_dir, exist_ok=True)
    
    files = {}
    
    # JSON已由universal_tracker处理
    
    # HTML战报
    html_path = os.path.join(output_dir, f"{session_id}_report.html")
    try:
        render_html_battle_report(report, html_path)
        files['html'] = html_path
    except Exception as e:
        logger.warning(f"[WARN] HTML战报生成失败: {e}")
    
    # 终端打印
    try:
        render_terminal_battle_report(report)
        files['terminal'] = 'printed'
    except Exception as e:
        logger.warning(f"[WARN] 终端战报打印失败: {e}")
    
    return files
