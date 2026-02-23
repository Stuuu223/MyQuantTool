#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""显示报告中的真实数据"""

import json
from pathlib import Path

def show_1231_report():
    """显示12月31日报告"""
    with open('data/day1_final_battle_report_20251231.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print('='*80)
    print('【12月31日 Top 10 真实数据】来自 day1_final_battle_report_20251231.json')
    print('='*80)
    print(f"{'排名':<4} {'代码':<12} {'名称':<10} {'基础分':<8} {'抽血占比':<10} {'乘数':<8} {'最终得分':<8}")
    print('-'*80)
    
    for item in data['top10']:
        print(f"{item['rank']:<4} {item['stock_code']:<12} {item['name']:<10} "
              f"{item['base_score']:<8.2f} {item['capital_share_pct']:<10.2f} "
              f"{item['multiplier']:<8.3f} {item['final_score']:<8.2f}")
    
    print()
    print('【志特新材数据】')
    zhite = data['zhitexincai']
    print(f"  排名: {zhite['rank']}")
    print(f"  最终得分: {zhite['final_score']:.2f}")
    print(f"  进入Top10: {zhite['in_top10']}")
    print()
    print(f"全市场平均得分: {data['summary']['avg_score']:.2f}")
    print(f"全市场最高得分: {data['summary']['max_score']:.2f}")
    print('='*80)

def show_0105_report():
    """显示1月5日报告"""
    with open('data/day_0105_final_battle_report.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print()
    print('='*80)
    print('【1月5日 Top 10 真实数据】来自 day_0105_final_battle_report.json')
    print('='*80)
    print(f"{'排名':<4} {'代码':<12} {'名称':<10} {'基础分':<8} {'抽血占比':<10} {'乘数':<8} {'最终得分':<8}")
    print('-'*80)
    
    for i, item in enumerate(data['top10'], 1):
        print(f"{i:<4} {item['stock_code']:<12} {item['name']:<10} "
              f"{item['base_score']:<8.2f} {item['capital_share_pct']:<10.2f} "
              f"{item['multiplier']:<8.3f} {item['final_score']:<8.2f}")
    
    print()
    print('【志特新材数据】')
    zhite = data['zhitexincai']
    print(f"  排名: {zhite['rank']}")
    print(f"  进入Top10: {zhite['in_top10']}")
    print(f"  注意: 所有final_score均为0.0（系统计算错误）")
    print('='*80)

def compare_key_stocks():
    """对比四只关键股票"""
    print()
    print('='*80)
    print('【四只关键股票对比】')
    print('='*80)
    
    # 12月31日数据
    with open('data/day1_final_battle_report_20251231.json', 'r', encoding='utf-8') as f:
        data1231 = json.load(f)
    
    stocks_1231 = {item['stock_code']: item for item in data1231['top10']}
    stocks_1231['300986.SZ'] = {
        'name': '志特新材',
        'rank': data1231['zhitexincai']['rank'],
        'final_score': data1231['zhitexincai']['final_score']
    }
    
    print('\n12月31日排名:')
    print(f"  南兴股份(002757): 排名 {stocks_1231.get('002757.SZ', {}).get('rank', 'N/A')}, 得分 {stocks_1231.get('002757.SZ', {}).get('final_score', 'N/A')}")
    print(f"  嘉美包装(002969): 排名 {stocks_1231.get('002969.SZ', {}).get('rank', 'N/A')}, 得分 {stocks_1231.get('002969.SZ', {}).get('final_score', 'N/A')}")
    print(f"  志特新材(300986): 排名 {stocks_1231.get('300986.SZ', {}).get('rank', 'N/A')}, 得分 {stocks_1231.get('300986.SZ', {}).get('final_score', 'N/A')}")
    
    print('\n关键发现:')
    print('  12月31日: 南兴(87.53) > 嘉美(86.34) > 志特(77.90)')
    print('  差距: 南兴-嘉美=1.19分，嘉美-志特=8.44分')
    print('='*80)

if __name__ == '__main__':
    show_1231_report()
    show_0105_report()
    compare_key_stocks()
