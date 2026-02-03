#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""导出分析数据为Python格式"""

import json
from datetime import datetime

# 读取JSON文件
file_path = 'E:/MyQuantTool/data/stock_analysis/300997/300997_20260203_140027_90days_enhanced.json'
with open(file_path, encoding='utf-8') as f:
    data = json.load(f)

# 提取关键数据
result = {
    'stock_code': data['stock_code'],
    'analyze_time': data['analyze_time'],
    'analyze_days': data['analyze_days'],
    
    # 资金流向摘要
    'fund_flow_summary': {
        'data_range': data['fund_flow']['data_range'],
        'total_days': data['fund_flow']['total_days'],
        'bullish_days': data['fund_flow']['bullish_days'],
        'bearish_days': data['fund_flow']['bearish_days'],
        'total_institution_90days(万元)': data['fund_flow']['total_institution'],  # 万元
        'total_retail_90days(万元)': data['fund_flow']['total_retail'],  # 万元
        'trend': data['fund_flow']['trend'],
    },
    
    # 资金分类
    'capital_classification': {
        'type': data.get('capital_analysis', {}).get('type', 'N/A'),
        'type_name': data.get('capital_analysis', {}).get('type_name', 'N/A'),
        'confidence': data.get('capital_analysis', {}).get('confidence', 0),
        'risk_level': data.get('capital_analysis', {}).get('risk_level', 'N/A'),
        'evidence': data.get('capital_analysis', {}).get('evidence', 'N/A'),
        'holding_period_estimate': data.get('capital_analysis', {}).get('holding_period_estimate', 'N/A'),
    },
    
    # 诱多检测
    'trap_detection': {
        'trap_count': len(data.get('trap_detection', {}).get('detected_traps', [])),
        'comprehensive_risk_score': data.get('trap_detection', {}).get('comprehensive_risk_score', 0),
        'total_outflow(万元)': data.get('trap_detection', {}).get('total_outflow', 0),
        'risk_assessment': data.get('trap_detection', {}).get('risk_assessment', 'N/A'),
    },
    
    # 最近7天资金流
    'recent_7days_flow': data['fund_flow']['daily_data'][-7:],
    
    # 5日趋势变化
    'flow_5d_trend': None,
}

# 获取最近的5日净流向趋势
recent_data = [d for d in data['fund_flow']['daily_data'] if d.get('flow_5d_net') is not None]
if recent_data:
    latest_5d = recent_data[-1].get('flow_5d_net', 0)
    if latest_5d > 0:
        result['flow_5d_trend'] = 'POSITIVE'
    elif latest_5d < 0:
        result['flow_5d_trend'] = 'NEGATIVE'
    else:
        result['flow_5d_trend'] = 'NEUTRAL'
    result['flow_5d_value'] = latest_5d

# 输出Python字典格式
print("# 300997 90天分析数据")
print(f"# 分析时间: {data['analyze_time']}")
print()
print("analysis_data = {")
print(f"    'stock_code': '{result['stock_code']}',")
print(f"    'analyze_time': '{result['analyze_time']}',")
print(f"    'analyze_days': {result['analyze_days']},")
print(f"    'fund_flow_summary': {{")
print(f"        'data_range': '{result['fund_flow_summary']['data_range']}',")
print(f"        'total_days': {result['fund_flow_summary']['total_days']},")
print(f"        'bullish_days': {result['fund_flow_summary']['bullish_days']},")
print(f"        'bearish_days': {result['fund_flow_summary']['bearish_days']},")
print(f"        '【90天累计】总机构(万元)': {result['fund_flow_summary']['total_institution_90days(万元)']:.2f},")
print(f"        '【90天累计】总散户(万元)': {result['fund_flow_summary']['total_retail_90days(万元)']:.2f},")
print(f"        'trend': '{result['fund_flow_summary']['trend']}',")
print(f"    }},")
print(f"    'capital_classification': {{")
print(f"        'type': '{result['capital_classification'].get('type', 'N/A')}',")
print(f"        'type_name': '{result['capital_classification'].get('type_name', 'N/A')}',")
print(f"        'confidence': {result['capital_classification'].get('confidence', 0)},")
print(f"        'risk_level': '{result['capital_classification'].get('risk_level', 'N/A')}',")
print(f"        'evidence': '{result['capital_classification'].get('evidence', 'N/A')}',")
print(f"        'holding_period_estimate': '{result['capital_classification'].get('holding_period_estimate', 'N/A')}',")
print(f"    }},")
print(f"    'trap_detection': {{")
print(f"        'trap_count': {result['trap_detection'].get('trap_count', 0)},")
print(f"        'comprehensive_risk_score': {result['trap_detection'].get('comprehensive_risk_score', 0)},")
print(f"        'total_outflow(万元)': {result['trap_detection'].get('total_outflow(万元)', 0):.2f},")
print(f"        'risk_assessment': '{result['trap_detection'].get('risk_assessment', 'N/A')}',")
print(f"    }},")
if result['flow_5d_trend']:
    print(f"    'flow_5d_trend': '{result['flow_5d_trend']}',")
    print(f"    'flow_5d_value(万元)': {result['flow_5d_value']:.2f},")
print(f"    'recent_7days_flow': [")
for day_data in result['recent_7days_flow']:
    print(f"        {{'date': '{day_data['date']}', 'institution': {day_data['institution']:.2f}, 'signal': '{day_data['signal']}'}},")
print(f"    ],")
print("}")