# -*- coding: utf-8 -*-
"""
股票池构建器 - 统一构建各类股票池

职责：
- 从配置读取基础股票列表
- 支持多种股票池构建策略
- 返回标准化的股票池结构

使用示例:
    from logic.analyzers.universe_builder import build_wanzhu_top150
    universe = build_wanzhu_top150()
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_json_config(config_path: Path) -> Dict:
    """加载JSON配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_stock_code(code: str) -> tuple:
    """解析股票代码
    
    Args:
        code: 原始代码（如 '600519.SH' 或 '600519'）
    
    Returns:
        (qmt_code, market, full_code)
    """
    if code.endswith('.SH'):
        return code[:-3], 'SH', code
    elif code.endswith('.SZ'):
        return code[:-3], 'SZ', code
    elif code.startswith('6'):
        return code, 'SH', f"{code}.SH"
    elif code.startswith('0') or code.startswith('3'):
        return code, 'SZ', f"{code}.SZ"
    else:
        return code, 'UNKNOWN', code


def build_wanzhu_top150() -> List[Dict]:
    """构建顽主Top150股票池
    
    前120只来自 config/wanzhu_top_120.json
    后30只来自 config/universe_bluechips.json
    
    Returns:
        标准化股票列表，每项包含：
        - code: 完整代码 (如 '600519.SH')
        - qmt_code: QMT代码 (如 '600519')
        - market: 市场 (SH/SZ)
        - name: 股票名称
        - rank: 排名
        - source: 来源 (wanzhu_top120 / bluechip)
    """
    stocks_150 = []
    
    # 1. 加载顽主前120
    top120_path = PROJECT_ROOT / 'config' / 'wanzhu_top_120.json'
    if not top120_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {top120_path}")
    
    top120_data = load_json_config(top120_path)
    
    # 支持两种格式：直接列表或 dict{'stocks': [...]}
    if isinstance(top120_data, dict):
        top120 = top120_data.get('stocks', [])
    else:
        top120 = top120_data
    
    # 取前120只
    for i, stock in enumerate(top120[:120], 1):
        code = stock.get('code', '')
        if not code:
            continue
        
        qmt_code, market, full_code = parse_stock_code(code)
        
        stocks_150.append({
            "code": full_code,
            "qmt_code": qmt_code,
            "market": market,
            "name": stock.get('name', ''),
            "rank": i,
            "source": "wanzhu_top120"
        })
    
    # 2. 加载蓝筹扩展30只
    bluechip_path = PROJECT_ROOT / 'config' / 'universe_bluechips.json'
    if not bluechip_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {bluechip_path}")
    
    bluechip_data = load_json_config(bluechip_path)
    bluechips = bluechip_data.get('stocks', [])
    
    for i, stock in enumerate(bluechips, 121):
        stocks_150.append({
            "code": stock['code'],
            "qmt_code": stock['qmt_code'],
            "market": stock['market'],
            "name": stock['name'],
            "rank": i,
            "source": "bluechip",
            "sector": stock.get('sector', '')
        })
    
    return stocks_150


def build_wanzhu_selected() -> List[Dict]:
    """构建顽主精选150股票池（从CSV）
    
    从 data/wanzhu_data/processed/wanzhu_selected_150.csv 读取
    
    Returns:
        标准化股票列表
    """
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"找不到CSV文件: {csv_path}")
    
    df = pd.read_csv(csv_path)
    stocks = []
    
    for idx, row in df.iterrows():
        code = str(row['code']).zfill(6)
        qmt_code, market, full_code = parse_stock_code(code)
        
        stocks.append({
            "code": full_code,
            "qmt_code": qmt_code,
            "market": market,
            "name": row.get('name', ''),
            "rank": idx + 1,
            "source": "wanzhu_selected"
        })
    
    return stocks


def save_universe(universe: List[Dict], output_path: Path, format: str = 'json'):
    """保存股票池到文件
    
    Args:
        universe: 股票列表
        output_path: 输出路径
        format: 格式 ('json' 或 'csv')
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(universe, f, ensure_ascii=False, indent=2)
    elif format == 'csv':
        df = pd.DataFrame(universe)
        df.to_csv(output_path, index=False, encoding='utf-8')
    else:
        raise ValueError(f"不支持的格式: {format}")
    
    print(f"✅ 股票池已保存: {output_path}")
    print(f"   股票数量: {len(universe)}")


def get_universe_summary(universe: List[Dict]) -> Dict:
    """获取股票池摘要统计
    
    Args:
        universe: 股票列表
    
    Returns:
        统计信息字典
    """
    sh_count = sum(1 for s in universe if s['market'] == 'SH')
    sz_count = sum(1 for s in universe if s['market'] == 'SZ')
    
    sources = {}
    for s in universe:
        src = s.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    return {
        'total': len(universe),
        'sh_count': sh_count,
        'sz_count': sz_count,
        'sources': sources
    }


if __name__ == '__main__':
    # 测试构建
    print("=" * 60)
    print("股票池构建测试")
    print("=" * 60)
    
    # 测试 wanzhu_top150
    print("\n构建 wanzhu_top150...")
    universe = build_wanzhu_top150()
    summary = get_universe_summary(universe)
    print(f"  总数: {summary['total']}")
    print(f"  上海: {summary['sh_count']}, 深圳: {summary['sz_count']}")
    print(f"  来源: {summary['sources']}")
    print("\n前5只股票:")
    for s in universe[:5]:
        print(f"  {s['rank']:3d}. {s['name']} ({s['code']})")
    
    # 保存测试
    output = PROJECT_ROOT / 'config' / 'wanzhu_top150_tick_download.json'
    save_universe(universe, output, 'json')
