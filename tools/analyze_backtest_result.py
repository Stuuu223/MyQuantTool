import json
import pandas as pd
from pyecharts.charts import Line, Bar, Pie, Page
from pyecharts import options as opts
from pathlib import Path
import datetime

# 配置
BACKTEST_DIR = Path("backtest/results")
OUTPUT_DIR = Path("backtest/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_latest_result():
    """加载最新的回测结果"""
    files = sorted(BACKTEST_DIR.glob("comprehensive_backtest_*.json"))
    if not files:
        raise FileNotFoundError("没有找到回测结果文件")
    return files[-1]

def generate_report():
    """生成回测分析报告"""
    json_file = load_latest_result()
    print(f"📊 正在分析: {json_file.name}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查数据结构
    if 'trades' not in data or not data['trades']:
        print("⚠️  警告: 回测结果中没有交易记录")
        print(f"📊 可用字段: {list(data.keys())}")
        return
    
    if 'equity_curve' not in data or not data['equity_curve']:
        print("⚠️  警告: 回测结果中没有权益曲线")
        return
    
    trades = pd.DataFrame(data['trades'])
    equity = pd.DataFrame(data['equity_curve'])
    
    print(f"\n📊 交易记录: {len(trades)} 条")
    print(f"📈 权益曲线: {len(equity)} 个数据点")
    
    # 1. 核心指标计算
    total_trades = len(trades[trades['action'] == 'SELL'])
    
    if total_trades == 0:
        print("⚠️  没有完成的交易记录（只有买入没有卖出）")
        return
    
    win_trades = len(trades[(trades['action'] == 'SELL') & (trades['profit'] > 0)])
    win_rate = win_trades / total_trades if total_trades > 0 else 0
    
    profit_trades = trades[(trades['action'] == 'SELL') & (trades['profit'] > 0)]
    loss_trades = trades[(trades['action'] == 'SELL') & (trades['profit'] < 0)]
    
    avg_profit = profit_trades['profit_pct'].mean() if len(profit_trades) > 0 else 0
    avg_loss = loss_trades['profit_pct'].mean() if len(loss_trades) > 0 else 0
    wl_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
    
    total_profit = trades[trades['action'] == 'SELL']['profit'].sum()
    
    print(f"\n{'='*60}")
    print(f"📊 核心指标摘要")
    print(f"{'='*60}")
    print(f"交易次数: {total_trades}")
    print(f"胜率: {win_rate:.2%} ({win_trades}/{total_trades})")
    print(f"总盈亏: {total_profit:.2f}")
    print(f"平均盈利: {avg_profit:.2f}%")
    print(f"平均亏损: {avg_loss:.2f}%")
    print(f"盈亏比: {wl_ratio:.2f}")
    
    # 2. 策略归因分析
    strategy_trades = trades[trades['action'] == 'SELL'].copy()
    
    if 'strategy' in strategy_trades.columns:
        strategy_perf = strategy_trades.groupby('strategy').agg({
            'profit': 'sum',
            'profit_pct': 'mean',
            'code': 'count'
        }).rename(columns={'code': 'trades'})
        
        strategy_perf['win_rate'] = strategy_trades.groupby('strategy').apply(
            lambda x: len(x[x['profit']>0])/len(x)
        )
        
        # 按总盈亏排序
        strategy_perf = strategy_perf.sort_values('profit', ascending=False)
        
        print(f"\n{'='*60}")
        print(f"📊 策略表现归因分析")
        print(f"{'='*60}")
        print(strategy_perf.to_string())
        
        # 识别拖后腿的策略
        worst_strategy = strategy_perf['profit'].idxmin() if len(strategy_perf) > 0 else None
        if worst_strategy and strategy_perf.loc[worst_strategy, 'profit'] < 0:
            print(f"\n⚠️  警告: '{worst_strategy}' 策略正在拖后腿（亏损 {strategy_perf.loc[worst_strategy, 'profit']:.2f}）")
    else:
        print("\n⚠️  警告: 交易记录中缺少 'strategy' 字段，无法进行策略归因分析")
    
    # 3. 退出原因分析
    if 'reason' in strategy_trades.columns:
        reason_stats = strategy_trades.groupby('reason').agg({
            'code': 'count',
            'profit': 'sum'
        }).rename(columns={'code': 'count', 'profit': 'total_loss'})
        
        print(f"\n{'='*60}")
        print(f"📊 退出原因分析")
        print(f"{'='*60}")
        print(reason_stats.to_string())
    
    # 4. 亏损单特征分析
    if len(loss_trades) > 0:
        print(f"\n{'='*60}")
        print(f"📊 亏损单特征分析（亏损最大的5笔）")
        print(f"{'='*60}")
        
        worst_loss_trades = loss_trades.nsmallest(5, 'profit')
        for idx, trade in worst_loss_trades.iterrows():
            print(f"\n{idx+1}. {trade['code']} ({trade.get('strategy', 'N/A')})")
            print(f"   日期: {trade['date']}")
            print(f"   亏损: {trade['profit']:.2f} ({trade['profit_pct']:.2f}%)")
            print(f"   原因: {trade.get('reason', 'N/A')}")
    
    # 5. 绘图 (HTML)
    try:
        page = Page(layout=Page.SimplePageLayout)
        
        # 图1: 净值曲线
        line = (
            Line()
            .add_xaxis(equity['date'].tolist())
            .add_yaxis("总权益", equity['equity'].round(2).tolist(), 
                       is_smooth=True, 
                       label_opts=opts.LabelOpts(is_show=False),
                       areastyle_opts=opts.AreaStyleOpts(opacity=0.3))
            .set_global_opts(
                title_opts=opts.TitleOpts(title="账户净值曲线"),
                tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross")
            )
        )
        
        # 图2: 策略盈亏分布 (Bar)
        if 'strategy' in strategy_trades.columns:
            bar = (
                Bar()
                .add_xaxis(strategy_perf.index.tolist())
                .add_yaxis("总盈亏", strategy_perf['profit'].round(2).tolist())
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="各策略总盈亏"),
                    tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow")
                )
            )
        else:
            bar = None
        
        # 图3: 胜率分布 (Pie)
        if 'strategy' in strategy_trades.columns:
            pie = (
                Pie()
                .add("", [list(z) for z in zip(strategy_perf.index.tolist(), strategy_perf['win_rate'].round(2).tolist())])
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="各策略胜率"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos="left")
                )
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
            )
        else:
            pie = None
        
        page.add(line)
        if bar:
            page.add(bar)
        if pie:
            page.add(pie)
        
        output_file = OUTPUT_DIR / f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        page.render(str(output_file))
        print(f"\n{'='*60}")
        print(f"✅ 交互式报告已生成: {output_file}")
        print(f"{'='*60}")
        print(f"请用浏览器打开该文件查看详细图表。")
        
    except Exception as e:
        print(f"\n⚠️  警告: 图表生成失败: {e}")
        print(f"   可能原因: pyecharts未安装或依赖缺失")

if __name__ == "__main__":
    try:
        generate_report()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()