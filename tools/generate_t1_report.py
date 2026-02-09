# -*- coding: utf-8 -*-
"""生成T+1验证报告"""
import pandas as pd
from pathlib import Path
from datetime import datetime

CSV_PATH = Path("E:/MyQuantTool/data/tracking/scan_performance.csv")
REPORT_PATH = Path("E:/MyQuantTool/data/tracking/t1_verification_report_20260209.txt")

def generate_t1_report():
    """生成T+1验证报告"""

    # 读取CSV文件
    df = pd.read_csv(CSV_PATH)

    # 生成报告
    report = []
    report.append("=" * 80)
    report.append("T+1 验证报告")
    report.append("=" * 80)
    report.append(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"验证日期: 2026-02-09")
    report.append("")

    # 1. 股票表现详情
    report.append("1. 股票表现详情")
    report.append("-" * 80)
    report.append(f"{'代码':<12} {'名称':<10} {'角色':<20} {'初始价':<8} {'收盘价':<8} {'涨跌幅':<8} {'结果'}")
    report.append("-" * 80)

    total_valid = 0
    total_win = 0
    total_loss = 0
    total_draw = 0
    total_na = 0

    for index, row in df.iterrows():
        if row['code'] == "000000.SZ":
            continue

        code = row['code']
        name = row['name']
        role = row['role']
        initial = row['initial_price']
        close = row['t1_close']
        pct = row['pct_change']
        result = row['result']

        report.append(f"{code:<12} {name:<10} {role:<20} {initial:<8.2f} {close:<8.2f} {pct:>6.2f}% {result}")

        # 统计
        if result == "WIN":
            total_valid += 1
            total_win += 1
        elif result == "LOSS":
            total_valid += 1
            total_loss += 1
        elif result == "DRAW":
            total_valid += 1
            total_draw += 1
        elif result == "N/A":
            total_na += 1

    report.append("-" * 80)

    # 2. 统计汇总
    report.append("")
    report.append("2. 统计汇总")
    report.append("-" * 80)
    report.append(f"有效样本数: {total_valid}")
    report.append(f"胜利次数: {total_win}")
    report.append(f"失败次数: {total_loss}")
    report.append(f"平局次数: {total_draw}")
    report.append(f"数据缺失: {total_na}")

    if total_valid > 0:
        win_rate = total_win / total_valid * 100
        loss_rate = total_loss / total_valid * 100
        draw_rate = total_draw / total_valid * 100

        report.append("")
        report.append("胜率分析:")
        report.append(f"  - 胜率: {win_rate:.1f}%")
        report.append(f"  - 败率: {loss_rate:.1f}%")
        report.append(f"  - 平局率: {draw_rate:.1f}%")

    # 3. 盈亏比分析
    report.append("")
    report.append("3. 盈亏比分析")
    report.append("-" * 80)

    wins = df[df['result'] == 'WIN']
    losses = df[df['result'] == 'LOSS']

    if not wins.empty and not losses.empty:
        avg_win_pct = wins['pct_change'].mean()
        avg_loss_pct = losses['pct_change'].mean()

        if avg_loss_pct != 0:
            profit_loss_ratio = abs(avg_win_pct / avg_loss_pct)
            report.append(f"平均盈利: {avg_win_pct:.2f}%")
            report.append(f"平均亏损: {avg_loss_pct:.2f}%")
            report.append(f"盈亏比: {profit_loss_ratio:.2f}")
        else:
            report.append("无法计算盈亏比（平均亏损为0）")
    else:
        report.append("数据不足，无法计算盈亏比")

    # 4. 最大回撤分析
    report.append("")
    report.append("4. 最大回撤分析")
    report.append("-" * 80)

    if not losses.empty:
        max_drawdown = losses['pct_change'].min()
        max_drawdown_stock = losses.loc[losses['pct_change'].idxmin(), 'code']
        report.append(f"最大回撤: {max_drawdown:.2f}%")
        report.append(f"回撤股票: {max_drawdown_stock}")
    else:
        report.append("无回撤记录")

    # 5. 风险评估
    report.append("")
    report.append("5. 风险评估")
    report.append("-" * 80)

    # 5.1 核心股检查
    core_stock = df[df['code'] == "002514.SZ"]
    if not core_stock.empty:
        core_change = core_stock.iloc[0]['pct_change']
        if core_change < -4.0:
            report.append(f"❌ [严重] 核心股002514跌幅{core_change:.2f}% (< -4%)")
            report.append("   建议: 立即回滚到v9.4.5版本")
        elif core_change < -2.0:
            report.append(f"⚠️  [警告] 核心股002514跌幅{core_change:.2f}% (< -2%)")
            report.append("   建议: 密切监控，准备应对措施")
        else:
            report.append(f"✓ [正常] 核心股002514涨跌幅{core_change:.2f}%")

    # 5.2 胜率评估
    if total_valid > 0:
        if win_rate < 25:
            report.append(f"❌ [失败] 胜率{win_rate:.1f}% (< 25%)")
            report.append("   建议: 系统无法跑赢随机概率，需要紧急调整参数")
        elif win_rate < 50:
            report.append(f"⚠️  [边缘] 胜率{win_rate:.1f}% (25-50%)")
            report.append("   建议: 需要参数调优")
        elif win_rate < 75:
            report.append(f"✓ [良好] 胜率{win_rate:.1f}% (50-75%)")
            report.append("   建议: 准备进入Phase 3优化")
        else:
            report.append(f"✓✓ [优秀] 胜率{win_rate:.1f}% (≥ 75%)")
            report.append("   建议: 保持当前版本，继续监控一周")

    # 5.3 综合评估
    report.append("")
    report.append("6. 综合评估结论")
    report.append("-" * 80)

    core_critical = False
    system_failure = False
    marginal = False
    good = False
    excellent = False

    if total_valid > 0:
        if not core_stock.empty and core_stock.iloc[0]['pct_change'] < -4.0:
            core_critical = True
        elif win_rate < 25:
            system_failure = True
        elif win_rate < 50:
            marginal = True
        elif win_rate < 75:
            good = True
        else:
            excellent = True

    if core_critical:
        report.append("【评级: 严重失败】")
        report.append("原因: 核心股跌幅超过4%，触发红色警报")
        report.append("行动: 立即回滚到v9.4.5版本（git checkout v9.4.5）")
    elif system_failure:
        report.append("【评级: 系统失败】")
        report.append("原因: 胜率低于25%，无法跑赢随机概率")
        report.append("行动: 需要紧急参数调整")
    elif marginal:
        report.append("【评级: 边缘状态】")
        report.append("原因: 胜率在25-50%之间，表现不佳")
        report.append("行动: 需要参数调优")
    elif good:
        report.append("【评级: 良好】")
        report.append("原因: 胜率在50-75%之间，表现稳定")
        report.append("行动: 准备进入Phase 3优化")
    elif excellent:
        report.append("【评级: 优秀】")
        report.append("原因: 胜率≥75%，表现卓越")
        report.append("行动: 保持当前版本，继续监控一周")
    else:
        report.append("【评级: 待评估】")
        report.append("原因: 有效数据不足")

    # 7. 详细建议
    report.append("")
    report.append("7. 详细建议")
    report.append("-" * 80)

    if core_critical:
        report.append("1. 立即停止当前版本的交易")
        report.append("2. 执行git checkout v9.4.5回滚操作")
        report.append("3. 重新验证v9.4.5版本的表现")
        report.append("4. 分析v9.4.7版本的问题根源")
    elif system_failure:
        report.append("1. 暂停实盘交易，进入参数调整阶段")
        report.append("2. 检查三把斧的拦截阈值是否过严")
        report.append("3. 重新训练场景分类模型")
        report.append("4. 增加测试样本数量")
    elif marginal:
        report.append("1. 微调场景分类的置信度阈值")
        report.append("2. 优化板块共振的计算方法")
        report.append("3. 增加对候选股的筛选条件")
        report.append("4. 继续收集更多T+1验证数据")
    elif good or excellent:
        report.append("1. 继续监控一周，验证稳定性")
        report.append("2. 收集至少20个T+1验证样本")
        report.append("3. 准备进入Phase 3功能开发")
        report.append("4. 文档化当前版本的成功经验")

    # 8. 数据质量说明
    report.append("")
    report.append("8. 数据质量说明")
    report.append("-" * 80)
    report.append(f"候选股票总数: 4")
    report.append(f"有效数据: {total_valid}")
    report.append(f"数据缺失: {total_na}")

    if total_na > 0:
        report.append("")
        report.append("缺失数据说明:")
        for index, row in df.iterrows():
            if row['result'] == "N/A":
                report.append(f"  - {row['code']} ({row['name']}): {row['comment']}")

    report.append("")
    report.append("=" * 80)
    report.append("报告结束")
    report.append("=" * 80)

    # 保存报告
    report_text = "\n".join(report)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"报告已生成: {REPORT_PATH}")
    print("\n" + report_text)

if __name__ == "__main__":
    generate_t1_report()