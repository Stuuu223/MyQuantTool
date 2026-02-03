"""
盘中决策工具 (Intraday Decision Tool)

功能:
1. 基于实时快照 + 历史数据，给出明确的买/卖/等建议
2. 计算止损价、止盈价、仓位建议
3. 输出结构化的决策报告
4. 支持命令行快速查询

依赖:
- logic/intraday_monitor.py (实时监控器)
- logic/trap_detector.py (诱多检测器)

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-03

使用示例:
    python tools/intraday_decision.py 300997
    python tools/intraday_decision.py 300997 --yesterday data/stock_analysis/300997_latest.json
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Literal

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.intraday_analyzer import IntraDayAnalyzer


class IntraDayDecisionTool:
    """盘中决策工具"""
    
    def __init__(self):
        """初始化决策工具"""
        self.analyzer = IntraDayAnalyzer()
        
        # 决策阈值配置
        self.thresholds = {
            'sell': {
                'trap_risk_high': 0.7,  # 诱多风险 >0.7 → 卖出
                'pressure_critical': -0.7,  # 卖压 < -0.7 → 卖出
                'loss_limit': -10.0,  # 亏损 > 10% → 止损
            },
            'hold': {
                'trap_risk_medium': 0.4,  # 诱多风险 0.4-0.7 → 观察
                'pressure_neutral': (-0.3, 0.3),  # 压力 -0.3~0.3 → 观察
            },
            'buy': {
                'flow_5d_positive': 0,  # 5日流入 > 0
                'pressure_strong': 0.5,  # 买压 > 0.5
                'trap_risk_low': 0.3,  # 诱多风险 < 0.3
            }
        }
    
    def make_decision(
        self, 
        stock_code: str, 
        yesterday_file: str | None = None,
        current_position: float = 0.0,
        entry_price: float | None = None
    ) -> Dict[str, Any]:
        """
        生成交易决策
        
        Args:
            stock_code: 股票代码
            yesterday_file: 昨日分析文件路径（可选）
            current_position: 当前持仓比例（0-1，默认0=空仓）
            entry_price: 建仓价格（如果有持仓）
        
        Returns:
            {
                'decision': 'SELL' | 'HOLD' | 'BUY' | 'WAIT',
                'confidence': 0.85,  # 决策置信度
                'reason': '诱多风险高 + 卖盘压力大',
                'action': {
                    'type': 'REDUCE',  # REDUCE/EXIT/HOLD/ADD/ENTER
                    'target_position': 0.5,  # 目标仓位
                    'stop_loss_price': 23.50,  # 止损价
                    'stop_profit_price': 26.80,  # 止盈价
                    'expected_return': '5-10%',
                    'holding_period': '1-3天'
                },
                'risk_assessment': {
                    'trap_risk': 0.85,
                    'capital_type': 'HOT_MONEY',
                    'flow_5d_trend': 'POSITIVE',
                    'bid_ask_pressure': -0.81,
                    'overall_risk': 'HIGH'
                },
                'data': {
                    'today': {...},
                    'yesterday': {...},
                    'comparison': {...}
                }
            }
        """
        result = {
            'decision': 'WAIT',
            'confidence': 0.0,
            'reason': '',
            'action': {},
            'risk_assessment': {},
            'data': {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 检查是否交易时间
        if not self.analyzer.is_trading_time():
            result['decision'] = 'WAIT'
            result['reason'] = '非交易时间，无法做出决策'
            return result
        
        # 获取实时数据
        if yesterday_file:
            # 先加载昨天的数据
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                yesterday_data = json.load(f)
            
            comparison = self.analyzer.compare_with_yesterday(stock_code, yesterday_data)
            if 'error' in comparison:
                result['reason'] = comparison['error']
                return result
            
            today = comparison['today']
            yesterday = comparison['yesterday']
            comp = comparison['comparison']
            
            # 从 yesterday_data 中提取 90天摘要
            yesterday_summary = {
                'total_institution': yesterday_data['fund_flow']['total_institution'],
                'trend': yesterday_data['fund_flow']['trend'],
                'capital_type': yesterday_data.get('capital_classification', {}).get('type', 'UNKNOWN'),
                'trap_risk': yesterday_data.get('trap_detection', {}).get('comprehensive_risk_score', 0.5)
            }
        else:
            # 仅实时快照
            today = self.analyzer.get_intraday_snapshot(stock_code)
            if 'error' in today:
                result['reason'] = today['error']
                return result
            
            yesterday = None
            comp = {}
            yesterday_summary = {}
        
        # 存储数据
        result['data'] = {
            'today': today,
            'yesterday': yesterday,
            'comparison': comp
        }
        
        # 风险评估
        risk = self._assess_risk(today, comp, yesterday_summary)
        result['risk_assessment'] = risk
        
        # 生成决策
        decision_result = self._generate_decision(
            today, comp, risk, current_position, entry_price
        )
        
        result.update(decision_result)
        
        return result
    
    def _assess_risk(
        self, 
        today: Dict, 
        comparison: Dict,
        yesterday_summary: Dict
    ) -> Dict[str, Any]:
        """风险评估"""
        
        risk = {
            'trap_risk': yesterday_summary.get('trap_risk', 0.5),
            'capital_type': yesterday_summary.get('capital_type', 'UNKNOWN'),
            'flow_5d_trend': comparison.get('flow_5d_trend', 'UNKNOWN'),
            'bid_ask_pressure': today.get('bid_ask_pressure', 0),
            'overall_risk': 'MEDIUM'
        }
        
        # 综合风险判断
        risk_score = 0
        
        # 诱多风险权重 40%
        if risk['trap_risk'] > 0.7:
            risk_score += 4
        elif risk['trap_risk'] > 0.4:
            risk_score += 2
        
        # 资金性质权重 30%
        if risk['capital_type'] == 'HOT_MONEY':
            risk_score += 3
        elif risk['capital_type'] == 'UNCLEAR':
            risk_score += 1.5
        
        # 买卖盘压力权重 30%
        if risk['bid_ask_pressure'] < -0.7:
            risk_score += 3
        elif risk['bid_ask_pressure'] < -0.3:
            risk_score += 1.5
        
        # 综合评级
        if risk_score >= 7:
            risk['overall_risk'] = 'CRITICAL'
        elif risk_score >= 5:
            risk['overall_risk'] = 'HIGH'
        elif risk_score >= 3:
            risk['overall_risk'] = 'MEDIUM'
        else:
            risk['overall_risk'] = 'LOW'
        
        risk['risk_score'] = round(risk_score, 2)
        
        return risk
    
    def _generate_decision(
        self,
        today: Dict,
        comparison: Dict,
        risk: Dict,
        current_position: float,
        entry_price: float | None
    ) -> Dict[str, Any]:
        """
        生成决策
        
        决策矩阵:
        - SELL: 诱多风险高 OR 卖压大 OR 亏损超止损线
        - HOLD: 风险中等 AND 无明确信号
        - BUY: 风险低 AND 买盘强 AND 5日转正
        - WAIT: 其他情况
        """
        decision = {
            'decision': 'WAIT',
            'confidence': 0.0,
            'reason': '',
            'action': {}
        }
        
        # 提取关键指标
        trap_risk = risk['trap_risk']
        pressure = risk['bid_ask_pressure']
        capital_type = risk['capital_type']
        flow_5d = comparison.get('flow_5d_trend', 'UNKNOWN')
        overall_risk = risk['overall_risk']
        
        current_price = today['price']
        
        # 计算盈亏（如果有持仓）
        if current_position > 0 and entry_price:
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = 0
        
        # 决策逻辑
        reasons = []
        
        # 规则1: 强制止损
        if profit_pct < self.thresholds['sell']['loss_limit']:
            decision['decision'] = 'SELL'
            decision['confidence'] = 0.95
            reasons.append(f'亏损{profit_pct:.1f}%，触发止损线')
            decision['action'] = {
                'type': 'EXIT',
                'target_position': 0.0,
                'urgency': 'IMMEDIATE'
            }
        
        # 规则2: 诱多 + 卖压 → 卖出
        elif (trap_risk > self.thresholds['sell']['trap_risk_high'] and 
              pressure < self.thresholds['sell']['pressure_critical']):
            decision['decision'] = 'SELL'
            decision['confidence'] = 0.85
            reasons.append(f'诱多风险{trap_risk:.2f}')
            reasons.append(f'卖盘压力{pressure:.2f}')
            
            if current_position > 0:
                decision['action'] = {
                    'type': 'REDUCE',
                    'target_position': max(0, current_position - 0.5),
                    'urgency': 'HIGH'
                }
            else:
                decision['action'] = {'type': 'AVOID'}
        
        # 规则3: 游资 + 卖压 → 卖出
        elif (capital_type == 'HOT_MONEY' and 
              pressure < self.thresholds['sell']['pressure_critical'] and
              flow_5d == 'POSITIVE'):
            decision['decision'] = 'SELL'
            decision['confidence'] = 0.75
            reasons.append('游资盘，5日转正后卖压增大')
            reasons.append('疑似诱多出货')
            
            if current_position > 0:
                decision['action'] = {
                    'type': 'EXIT',
                    'target_position': 0.0,
                    'urgency': 'HIGH'
                }
        
        # 规则4: 低风险 + 买盘强 → 买入
        elif (overall_risk == 'LOW' and 
              pressure > self.thresholds['buy']['pressure_strong'] and
              flow_5d == 'POSITIVE'):
            decision['decision'] = 'BUY'
            decision['confidence'] = 0.7
            reasons.append('低风险')
            reasons.append(f'买盘强势{pressure:.2f}')
            reasons.append('5日转正')
            
            if current_position < 1.0:
                decision['action'] = {
                    'type': 'ADD' if current_position > 0 else 'ENTER',
                    'target_position': min(1.0, current_position + 0.15),
                    'urgency': 'MEDIUM'
                }
        
        # 规则5: 中等风险 → 观察
        elif overall_risk in ['MEDIUM', 'HIGH']:
            decision['decision'] = 'HOLD'
            decision['confidence'] = 0.6
            reasons.append(f'风险{overall_risk}，观察1-2天')
            
            if current_position > 0:
                decision['action'] = {
                    'type': 'HOLD',
                    'target_position': current_position,
                    'stop_loss_price': current_price * 0.95,  # 5%止损
                    'urgency': 'LOW'
                }
        
        # 规则6: 其他 → 等待
        else:
            decision['decision'] = 'WAIT'
            decision['confidence'] = 0.5
            reasons.append('盘面不明确，继续观察')
        
        decision['reason'] = '; '.join(reasons)
        
        # 补充止损止盈价
        if 'stop_loss_price' not in decision['action'] and current_position > 0:
            decision['action']['stop_loss_price'] = round(current_price * 0.95, 2)
            decision['action']['stop_profit_price'] = round(current_price * 1.1, 2)
        
        # 补充预期收益
        if decision['decision'] == 'BUY':
            decision['action']['expected_return'] = '5-10%'
            decision['action']['holding_period'] = '1-3天' if capital_type == 'HOT_MONEY' else '3-7天'
        
        return decision
    
    def print_decision_report(self, decision: Dict):
        """打印决策报告（命令行格式）"""
        
        print("\n" + "="*60)
        print(f"📊 盘中决策报告 - {decision['timestamp']}")
        print("="*60)
        
        # 数据时效性
        if 'data' in decision and 'today' in decision['data']:
            today = decision['data']['today']
            print(f"\n⏰ 数据时间: {today.get('time', 'N/A')}")
            print(f"🔴 实时价格: {today.get('price', 'N/A')} ({today.get('pct_change', 0):.2f}%)")
        
        # 风险评估
        print("\n🚨 风险评估:")
        risk = decision['risk_assessment']
        print(f"  综合风险: {risk.get('overall_risk', 'N/A')} (评分: {risk.get('risk_score', 'N/A')})")
        
        # 处理 trap_risk 可能是字符串的情况
        trap_risk = risk.get('trap_risk', 0)
        if isinstance(trap_risk, (int, float)):
            print(f"  诱多风险: {trap_risk:.2f}")
        else:
            print(f"  诱多风险: {trap_risk}")
        
        print(f"  资金性质: {risk.get('capital_type', 'N/A')}")
        print(f"  5日趋势: {risk.get('flow_5d_trend', 'N/A')}")
        
        # 处理 bid_ask_pressure 可能是字符串的情况
        bid_ask_pressure = risk.get('bid_ask_pressure', 0)
        if isinstance(bid_ask_pressure, (int, float)):
            print(f"  买卖压力: {bid_ask_pressure:.2f}")
        else:
            print(f"  买卖压力: {bid_ask_pressure}")
        
        # 决策建议
        print(f"\n🎯 决策建议:")
        print(f"  决策: {decision['decision']} (置信度: {decision['confidence']:.0%})")
        print(f"  理由: {decision['reason']}")
        
        # 操作建议
        if decision['action']:
            print(f"\n💼 操作建议:")
            action = decision['action']
            print(f"  动作类型: {action.get('type', 'N/A')}")
            
            if 'target_position' in action:
                print(f"  目标仓位: {action['target_position']:.0%}")
            
            if 'stop_loss_price' in action:
                print(f"  止损价: {action['stop_loss_price']:.2f}")
            
            if 'stop_profit_price' in action:
                print(f"  止盈价: {action['stop_profit_price']:.2f}")
            
            if 'expected_return' in action:
                print(f"  预期收益: {action['expected_return']}")
            
            if 'holding_period' in action:
                print(f"  持仓周期: {action['holding_period']}")
            
            print(f"  紧急程度: {action.get('urgency', 'N/A')}")
        
        print("\n" + "="*60 + "\n")
    
    def save_decision(self, stock_code: str, decision: Dict, output_dir: str = 'data/decisions'):
        """保存决策到文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{stock_code}_decision_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(decision, f, ensure_ascii=False, indent=2)
        
        print(f"决策已保存: {filepath}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='盘中决策工具')
    parser.add_argument('stock_code', help='股票代码（如 300997）')
    parser.add_argument('--yesterday', help='昨日分析文件路径', default=None)
    parser.add_argument('--position', type=float, help='当前持仓比例（0-1）', default=0.0)
    parser.add_argument('--entry-price', type=float, help='建仓价格', default=None)
    parser.add_argument('--save', action='store_true', help='保存决策到文件')
    
    args = parser.parse_args()
    
    # 自动查找昨日文件（如果未指定）
    if args.yesterday is None:
        possible_file = f'data/stock_analysis/{args.stock_code}_latest.json'
        if os.path.exists(possible_file):
            args.yesterday = possible_file
            print(f"自动使用昨日文件: {args.yesterday}")
    
    # 生成决策
    tool = IntraDayDecisionTool()
    decision = tool.make_decision(
        stock_code=args.stock_code,
        yesterday_file=args.yesterday,
        current_position=args.position,
        entry_price=args.entry_price
    )
    
    # 打印报告
    tool.print_decision_report(decision)
    
    # 保存（可选）
    if args.save:
        tool.save_decision(args.stock_code, decision)


if __name__ == '__main__':
    main()
