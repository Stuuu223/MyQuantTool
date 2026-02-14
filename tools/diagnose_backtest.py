"""
回测诊断工具
分析回测失败模式，特别是"买完即套"的情况
"""
import sys
from pathlib import Path
import pandas as pd
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# 配置
BACKTEST_RESULTS_DIR = PROJECT_ROOT / "backtest/results"

def diagnose_backtest(result_file: Path) -> dict:
    """
    诊断回测结果
    
    Args:
        result_file: 回测结果JSON文件路径
    
    Returns:
        诊断报告
    """
    print(f"\n{'='*80}")
    print(f"诊断回测结果: {result_file.name}")
    print(f"{'='*80}")
    
    # 1. 加载回测结果
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 加载回测结果失败: {e}")
        return None
    
    trade_history = data.get('trade_history', [])
    
    if not trade_history:
        print("⚠️  回测结果中没有交易记录")
        return None
    
    print(f"交易记录数: {len(trade_history)}")
    
    # 2. 分析卖出记录
    sell_trades = [t for t in trade_history if t.get('action') == 'SELL']
    buy_trades = [t for t in trade_history if t.get('action') == 'BUY']
    
    print(f"买入记录数: {len(buy_trades)}")
    print(f"卖出记录数: {len(sell_trades)}")
    
    if not sell_trades:
        print("⚠️  没有卖出记录")
        return None
    
    # 3. 分类分析
    stop_loss_trades = [t for t in sell_trades if t.get('reason') == 'STOP_LOSS']
    take_profit_trades = [t for t in sell_trades if t.get('reason') == 'TAKE_PROFIT']
    close_all_trades = [t for t in sell_trades if t.get('reason') == 'CLOSE_ALL']
    
    print(f"\n{'='*80}")
    print("卖出原因分析")
    print(f"{'='*80}")
    print(f"止损卖出: {len(stop_loss_trades)} 笔 ({len(stop_loss_trades)/len(sell_trades)*100:.1f}%)")
    print(f"止盈卖出: {len(take_profit_trades)} 笔 ({len(take_profit_trades)/len(sell_trades)*100:.1f}%)")
    print(f"强制平仓: {len(close_all_trades)} 笔 ({len(close_all_trades)/len(sell_trades)*100:.1f}%)")
    
    # 4. 识别"买完即套"
    print(f"\n{'='*80}")
    print("'买完即套'分析")
    print(f"{'='*80}")
    
    immediate_loss_trades = []
    
    for sell_trade in stop_loss_trades:
        buy_code = sell_trade['code']
        sell_date = sell_trade['date']
        
        # 找到对应的买入记录
        matching_buy = None
        for buy_trade in reversed(buy_trades):
            if (buy_trade['code'] == buy_code and 
                buy_trade['date'] <= sell_date and
                buy_trade['action'] == 'BUY'):
                matching_buy = buy_trade
                break
        
        if matching_buy is None:
            continue
        
        # 计算持仓天数
        from datetime import datetime, timedelta
        buy_date = datetime.strptime(matching_buy['date'], '%Y-%m-%d')
        sell_date = datetime.strptime(sell_trade['date'], '%Y-%m-%d')
        hold_days = (sell_date - buy_date).days
        
        # 如果持仓天数 <= 1，且是止损，视为"买完即套"
        if hold_days <= 1 and sell_trade.get('profit_pct', 0) < -4.0:
            immediate_loss_trades.append({
                'code': buy_code,
                'buy_date': matching_buy['date'],
                'sell_date': sell_trade['date'],
                'hold_days': hold_days,
                'entry_price': matching_buy['price'],
                'exit_price': sell_trade['price'],
                'profit_pct': sell_trade['profit_pct'],
                'strategy': sell_trade.get('strategy'),
                'reason': '买完即套（持仓≤1天且止损）'
            })
    
    print(f"'买完即套'交易数: {len(immediate_loss_trades)} 笔")
    print(f"占止损交易比例: {len(immediate_loss_trades)/len(stop_loss_trades)*100:.1f}% if len(stop_loss_trades) > 0 else 0")
    
    # 5. 显示前10个"买完即套"案例
    if immediate_loss_trades:
        print(f"\n{'='*80}")
        print("'买完即套'案例（前10个）")
        print(f"{'='*80}")
        
        for i, trade in enumerate(immediate_loss_trades[:10]):
            print(f"\n案例 {i+1}: {trade['code']} ({trade['strategy']})")
            print(f"  买入: {trade['buy_date']} @ {trade['entry_price']:.2f}")
            print(f"  卖出: {trade['sell_date']} @ {trade['exit_price']:.2f}")
            print(f"  持仓: {trade['hold_days']}天")
            print(f"  亏损: {trade['profit_pct']:.2f}%")
            print(f"  原因: {trade['reason']}")
    
    # 6. 按策略分类分析
    print(f"\n{'='*80}")
    print("按策略分类分析")
    print(f"{'='*80}")
    
    strategy_analysis = {}
    for trade in sell_trades:
        strategy = trade.get('strategy', 'unknown')
        if strategy not in strategy_analysis:
            strategy_analysis[strategy] = {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'immediate_losses': 0,
                'total_profit': 0
            }
        
        strategy_analysis[strategy]['total'] += 1
        if trade.get('profit', 0) > 0:
            strategy_analysis[strategy]['wins'] += 1
            strategy_analysis[strategy]['total_profit'] += trade.get('profit', 0)
        else:
            strategy_analysis[strategy]['losses'] += 1
            strategy_analysis[strategy]['total_profit'] += trade.get('profit', 0)
        
        # 检查是否是"买完即套"
        is_immediate = any(
            t['code'] == trade['code'] and t['buy_date'] == trade['date']
            for t in immediate_loss_trades
        )
        if is_immediate:
            strategy_analysis[strategy]['immediate_losses'] += 1
    
    for strategy, stats in strategy_analysis.items():
        win_rate = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
        immediate_loss_rate = stats['immediate_losses'] / stats['losses'] * 100 if stats['losses'] > 0 else 0
        
        print(f"\n{strategy}:")
        print(f"  总交易: {stats['total']}")
        print(f"  盈利: {stats['wins']} 笔 ({win_rate:.1f}%)")
        print(f"  亏损: {stats['losses']} 笔")
        print(f"  总盈亏: {stats['total_profit']:.2f}")
        print(f"  '买完即套': {stats['immediate_losses']} 笔 (占亏损{immediate_loss_rate:.1f}%)")
    
    # 7. 时间分布分析
    print(f"\n{'='*80}")
    print("时间分布分析")
    print(f"{'='*80}")
    
    from collections import Counter
    sell_dates = [t['date'] for t in sell_trades]
    date_counter = Counter(sell_dates)
    
    print(f"卖出日期分布:")
    for date, count in sorted(date_counter.items()):
        print(f"  {date}: {count} 笔")
    
    # 8. CTO 关键指标
    print(f"\n{'='*80}")
    print("CTO 关键指标")
    print(f"{'='*80}")
    
    immediate_loss_ratio = len(immediate_loss_trades) / len(sell_trades) * 100 if sell_trades else 0
    stop_loss_ratio = len(stop_loss_trades) / len(sell_trades) * 100 if sell_trades else 0
    
    print(f"1. 止损率: {stop_loss_ratio:.1f}% (目标: <50%)")
    print(f"2. '买完即套'率: {immediate_loss_ratio:.1f}% (目标: <20%)")
    
    # 如果去掉"买完即套"的交易，胜率会变成多少？
    if immediate_loss_trades:
        adjusted_wins = len(take_profit_trades)
        adjusted_losses = len(stop_loss_trades) - len(immediate_loss_trades)
        adjusted_total = adjusted_wins + adjusted_losses
        adjusted_win_rate = adjusted_wins / adjusted_total * 100 if adjusted_total > 0 else 0
        
        print(f"\n如果去掉'买完即套'交易:")
        print(f"  原胜率: {len(take_profit_trades)}/{len(sell_trades)} = {len(take_profit_trades)/len(sell_trades)*100:.1f}%")
        print(f"  新胜率: {adjusted_wins}/{adjusted_total} = {adjusted_win_rate:.1f}%")
        print(f"  提升: {adjusted_win_rate - len(take_profit_trades)/len(sell_trades)*100:.1f}个百分点")
    
    # 生成诊断报告
    diagnosis = {
        'result_file': result_file.name,
        'summary': {
            'total_trades': len(trade_history),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'stop_loss_trades': len(stop_loss_trades),
            'take_profit_trades': len(take_profit_trades),
            'close_all_trades': len(close_all_trades),
            'immediate_loss_trades': len(immediate_loss_trades),
            'stop_loss_ratio': stop_loss_ratio,
            'immediate_loss_ratio': immediate_loss_ratio,
            'adjusted_win_rate': adjusted_win_rate if immediate_loss_trades else None
        },
        'immediate_loss_trades': immediate_loss_trades[:10],  # 只保留前10个
        'strategy_analysis': strategy_analysis,
        'date_distribution': dict(date_counter)
    }
    
    return diagnosis

def main():
    """主函数"""
    print("=" * 80)
    print("回测诊断工具")
    print("=" * 80)
    
    # 查找最新的回测结果文件
    result_files = list(BACKTEST_RESULTS_DIR.glob("*.json"))
    
    if not result_files:
        print("❌ 未找到回测结果文件")
        print(f"请确保回测结果文件存在于: {BACKTEST_RESULTS_DIR}")
        return
    
    # 选择最新的回测结果
    latest_file = sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    
    diagnosis = diagnose_backtest(latest_file)
    
    if diagnosis:
        # 保存诊断报告
        report_file = BACKTEST_RESULTS_DIR / f"diagnosis_{latest_file.stem}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(diagnosis, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 诊断报告已保存: {report_file}")
        
        # CTO 决策建议
        print(f"\n{'='*80}")
        print("CTO 决策建议")
        print(f"{'='*80}")
        
        summary = diagnosis['summary']
        
        if summary['stop_loss_ratio'] > 50:
            print("❌ 止损率过高 (>50%)")
            print("   建议: 策略买入时机有问题，需要优化选股逻辑")
            print("   行动: 不要急于优化策略参数，先解决买入时机问题")
        
        if summary['immediate_loss_ratio'] > 20:
            print("❌ '买完即套'率过高 (>20%)")
            print("   建议: 策略在追高买入，买入时机很差")
            print("   行动: 检查是否使用了未来数据（如当日收盘价判断买入）")
        
        if summary['immediate_loss_ratio'] < 20 and summary['adjusted_win_rate'] > 40:
            print("✅ 如果去掉'买完即套'交易，胜率提升到40%+")
            print("   建议: 策略本身可能还可以，但需要改善买入时机")
            print("   行动: 增加更严格的买入条件（如等待回调再买入）")

if __name__ == "__main__":
    main()