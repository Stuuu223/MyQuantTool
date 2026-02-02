"""
多日资金流向分析报告
完整列出每天的资金流向情况并分析趋势
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.fund_flow_collector import FundFlowCollector, get_fund_flow_collector


class MultiDayAnalysis:
    """多日资金流向分析"""

    def __init__(self):
        """初始化分析器"""
        self.collector = get_fund_flow_collector()

    def analyze(self, stock_code: str, days: int = 10) -> str:
        """
        生成多日分析报告

        Args:
            stock_code: 股票代码
            days: 分析最近几天

        Returns:
            格式化的分析报告
        """
        # 收集今日数据
        collect_result = self.collector.collect(stock_code)

        # 获取历史数据
        history = self.collector.get_history(stock_code, days)

        if not history:
            return f"❌ 股票 {stock_code} 暂无历史数据"

        # 生成报告
        report = self._generate_report(stock_code, history)

        return report

    def _generate_report(self, stock_code: str, history: List[Dict]) -> str:
        """生成报告"""
        report = f"""
{'='*80}
## 多日资金流向分析报告

**股票代码**: {stock_code}
**分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**数据天数**: {len(history)} 天

{'='*80}

### 📊 每日资金流向详情

| 日期 | 超大单(万) | 大单(万) | 中单(万) | 小单(万) | 机构资金(万) | 散户资金(万) | 信号 | 模式 |
|------|-----------|---------|---------|---------|-------------|-------------|------|------|
"""

        # 计算每日信号
        daily_signals = []

        for day in history:
            super_large = day['super_large_net'] / 10000
            large = day['large_net'] / 10000
            medium = day['medium_net'] / 10000
            small = day['small_net'] / 10000
            inst_net = day['institution_net'] / 10000
            retail_net = day['retail_net'] / 10000

            # 判断信号
            if inst_net < 0 and retail_net > 0:
                signal = "⛔"
                signal_text = "BEARISH"
                pattern = "机构减仓，散户接盘"
            elif inst_net > 0 and retail_net < 0:
                signal = "🟢"
                signal_text = "BULLISH"
                pattern = "机构吸筹，散户恐慌"
            elif inst_net > 0 and retail_net > 0:
                signal = "🟢"
                signal_text = "BULLISH"
                pattern = "共同看好"
            else:
                signal = "⚪"
                signal_text = "NEUTRAL"
                pattern = "共同看淡"

            daily_signals.append({
                "date": day['date'],
                "signal": signal_text,
                "pattern": pattern,
                "institution_net": inst_net,
                "retail_net": retail_net
            })

            report += f"| {day['date']} | {super_large:>8.2f} | {large:>7.2f} | {medium:>7.2f} | {small:>7.2f} | {inst_net:>10.2f} | {retail_net:>10.2f} | {signal} {signal_text} | {pattern} |\n"

        # 统计
        bullish_days = sum(1 for d in daily_signals if d['signal'] == 'BULLISH')
        bearish_days = len(daily_signals) - bullish_days

        report += f"""
{'='*80}

### 📈 趋势统计

- **总天数**: {len(daily_signals)} 天
- **看多信号**: {bullish_days} 天 ({bullish_days/len(daily_signals)*100:.1f}%)
- **看空信号**: {bearish_days} 天 ({bearish_days/len(daily_signals)*100:.1f}%)

{'='*80}

### 🎯 每日详细解读

"""

        # 列出每日详细解读
        for i, day_sig in enumerate(daily_signals, 1):
            report += f"**第 {i} 天 ({day_sig['date']})**\n"
            report += f"- 机构资金: {day_sig['institution_net']:.2f} 万元\n"
            report += f"- 散户资金: {day_sig['retail_net']:.2f} 万元\n"
            report += f"- 信号: {day_sig['signal']}\n"
            report += f"- 模式: {day_sig['pattern']}\n"

            # 详细解读
            if day_sig['signal'] == 'BEARISH':
                report += "- 解读: ⚠️ 机构在减仓，散户在接盘，风险较高\n"
            elif day_sig['signal'] == 'BULLISH':
                report += "- 解读: ✅ 机构在吸筹，散户在恐慌，底部机会\n"

            report += "\n"

        # 趋势判断
        report += f"""
{'='*80}

### 🔍 整体趋势判断

"""

        if bullish_days > bearish_days * 1.5:
            report += "**整体趋势**: 🟢 **强势吸筹趋势**\n"
            report += "- 机构持续流入，散户持续流出\n"
            report += "- 建议关注，可能存在底部机会\n"
        elif bullish_days > bearish_days:
            report += "**整体趋势**: 🟡 **吸筹趋势**\n"
            report += "- 机构净流入，但力度不够强\n"
            report += "- 建议谨慎关注\n"
        elif bearish_days > bullish_days * 1.5:
            report += "**整体趋势**: 🔴 **强势减仓趋势**\n"
            report += "- 机构持续流出，散户持续流入\n"
            report += "- 建议回避，风险较高\n"
        else:
            report += "**整体趋势**: ⚪ **震荡趋势**\n"
            report += "- 机构和散户博弈激烈\n"
            report += "- 建议观望，等待方向明确\n"

        # 最新趋势
        if len(daily_signals) >= 3:
            latest_3 = daily_signals[-3:]
            latest_bullish = sum(1 for d in latest_3 if d['signal'] == 'BULLISH')

            report += f"""
**最近 3 天趋势**: """

            if latest_bullish >= 2:
                report += "🟢 **近期转强**\n"
                report += "- 最近 3 天中有 {latest_bullish} 天出现吸筹信号\n"
                report += "- 可能是底部反转信号\n"
            elif latest_bullish == 0:
                report += "🔴 **近期转弱**\n"
                report += "- 最近 3 天全是减仓信号\n"
                report += "- 风险在加大\n"
            else:
                report += "⚪ **近期震荡**\n"
                report += "- 最近 3 天信号不统一\n"
                report += "- 等待方向明确\n"

        # 机构态度
        total_inst_net = sum(d['institution_net'] for d in daily_signals)
        report += f"""
**机构总体态度**: """

        if total_inst_net > 0:
            report += f"🟢 **净流入 {total_inst_net:.2f} 万元**\n"
            report += "- 机构总体在买入\n"
        elif total_inst_net < 0:
            report += f"🔴 **净流出 {abs(total_inst_net):.2f} 万元**\n"
            report += "- 机构总体在卖出\n"
        else:
            report += "⚪ **持平**\n"
            report += "- 机构买卖平衡\n"

        report += f"""
{'='*80}

### 💡 操作建议

"""

        # 根据趋势给出建议
        if bullish_days > bearish_days * 1.5:
            report += "**建议**: 🟢 **可以考虑低吸**\n"
            report += "- 机构持续吸筹，底部可能确立\n"
            report += "- 设定止损，分批参与\n"
        elif bullish_days > bearish_days:
            report += "**建议**: 🟡 **谨慎关注**\n"
            report += "- 有吸筹迹象，但力度不够\n"
            report += "- 建议等待更明确的信号\n"
        elif bearish_days > bullish_days * 1.5:
            report += "**建议**: 🔴 **建议回避**\n"
            report += "- 机构持续减仓，风险较高\n"
            report += "- 不要盲目抄底\n"
        else:
            report += "**建议**: ⚪ **观望**\n"
            report += "- 趋势不明，方向不清\n"
            report += "- 等待更明确的信号\n"

        report += f"""
{'='*80}

**免责声明**: 本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

        return report


# 便捷函数
def analyze_multi_day(stock_code: str, days: int = 10) -> str:
    """分析多日资金流向"""
    analyzer = MultiDayAnalysis()
    return analyzer.analyze(stock_code, days)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "300997"

    print(analyze_multi_day(stock_code, days=10))