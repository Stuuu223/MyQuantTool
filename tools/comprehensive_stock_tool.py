"""
综合个股分析工具
结合 AkShare 和 QMT 数据，提供完整的个股分析
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入速率限制器
from logic.rate_limiter import get_rate_limiter, safe_request


def calculate_bollinger_bands(prices, window=20, num_std=2):
    """计算布林带"""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return sma, upper_band, lower_band


def calculate_rsi(prices, window=14):
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram


def comprehensive_stock_analysis(stock_code, days=10, use_qmt=True, auto_save=False):
    """
    综合个股分析

    Args:
        stock_code: 股票代码（如 '300997'）
        days: 分析最近几天（默认10天）
        use_qmt: 是否使用 QMT 数据（默认 True）
        auto_save: 是否自动保存报告到文件（默认 False）

    Returns:
        str: 格式化的综合分析报告
        如果 auto_save=True，还会返回文件路径
    """
    # 自动判断市场
    if stock_code.startswith('6'):
        market = 'sh'
    else:
        market = 'sz'

    report = []
    report.append("=" * 80)
    report.append(f"📊 {stock_code} 综合分析报告")
    report.append("=" * 80)
    report.append(f"分析天数: 最近 {days} 天")
    report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)

    # ========== 第一部分：AkShare 资金流向分析 ==========
    report.append(f"\n## 第一部分：资金流向分析（AkShare）\n")

    try:
        # 使用速率限制器安全调用
        df = safe_request(ak.stock_individual_fund_flow, stock=stock_code, market=market)

        if df.empty:
            report.append("❌ 未找到资金流向数据")
        else:
            # 计算机构和散户净流入
            df['机构净流入'] = df['超大单净流入-净额'] + df['大单净流入-净额']
            df['散户净流入'] = df['中单净流入-净额'] + df['小单净流入-净额']

            # 获取最近 days 天数据
            recent_df = df.tail(days).copy()

            # 转换为万元
            recent_df_wan = recent_df.copy()
            recent_df_wan['超大单'] = recent_df_wan['超大单净流入-净额'] / 10000
            recent_df_wan['大单'] = recent_df_wan['大单净流入-净额'] / 10000
            recent_df_wan['中单'] = recent_df_wan['中单净流入-净额'] / 10000
            recent_df_wan['小单'] = recent_df_wan['小单净流入-净额'] / 10000
            recent_df_wan['机构'] = recent_df_wan['机构净流入'] / 10000
            recent_df_wan['散户'] = recent_df_wan['散户净流入'] / 10000

            report.append(f"数据范围: {df['日期'].min()} 至 {df['日期'].max()} ({len(df)}天)")
            report.append(f"\n📅 最近 {days} 天资金流向（单位：万元）：\n")
            report.append(recent_df_wan[['日期', '超大单', '大单', '中单', '小单', '机构', '散户']].to_string(index=False))

            # 每日信号
            report.append(f"\n每日信号分析：\n")
            signals = []
            for _, row in recent_df_wan.iterrows():
                inst_net = row['机构']
                retail_net = row['散户']

                if inst_net < 0 and retail_net > 0:
                    signal = "⛔ 接盘"
                    desc = "机构减仓，散户接盘"
                    sig_type = "BEARISH"
                elif inst_net > 0 and retail_net < 0:
                    signal = "🟢 吸筹"
                    desc = "机构吸筹，散户恐慌"
                    sig_type = "BULLISH"
                elif inst_net > 0 and retail_net > 0:
                    signal = "🟢 共买"
                    desc = "共同看好"
                    sig_type = "BULLISH"
                else:
                    signal = "⚪ 共卖"
                    desc = "共同看淡"
                    sig_type = "BEARISH"

                signals.append(sig_type)
                report.append(f"  {row['日期']}: {signal} | 机构 {inst_net:>8.2f}万, 散户 {retail_net:>8.2f}万 | {desc}")

            # 统计
            bullish_count = sum(1 for s in signals if s == 'BULLISH')
            bearish_count = len(signals) - bullish_count
            total_inst = recent_df_wan['机构'].sum()
            total_retail = recent_df_wan['散户'].sum()

            report.append(f"\n趋势统计：")
            report.append(f"  吸筹信号: {bullish_count} 天 ({bullish_count/len(recent_df_wan)*100:.1f}%)")
            report.append(f"  接盘信号: {bearish_count} 天 ({bearish_count/len(recent_df_wan)*100:.1f}%)")
            report.append(f"  累计机构: {total_inst:>10.2f} 万元")
            report.append(f"  累计散户: {total_retail:>10.2f} 万元")

            # 趋势判断
            if bullish_count > bearish_count * 1.5:
                fund_trend = "🟢 强势吸筹趋势"
                fund_action = "可以考虑低吸"
            elif bullish_count > bearish_count:
                fund_trend = "🟡 吸筹趋势"
                fund_action = "谨慎关注"
            elif bearish_count > bullish_count * 1.5:
                fund_trend = "🔴 强势减仓趋势"
                fund_action = "建议回避"
            else:
                fund_trend = "⚪ 震荡趋势"
                fund_action = "观望"

            report.append(f"\n整体趋势: {fund_trend}")
            report.append(f"操作建议: {fund_action}")

    except Exception as e:
        report.append(f"❌ 资金流向分析失败: {str(e)}")

    # ========== 第二部分：QMT 数据分析 ==========
    if use_qmt:
        report.append(f"\n{'=' * 80}")
        report.append(f"## 第二部分：QMT 实时数据")
        report.append("=" * 80)

        try:
            # 尝试导入 QMT
            from logic.code_converter import CodeConverter
            import xtdata

            # 转换代码格式
            converter = CodeConverter()
            qmt_code = converter.to_qmt(stock_code)

            report.append(f"\nQMT 代码: {qmt_code}")

            # 获取 Tick 数据
            tick_data = xtdata.get_full_tick([qmt_code])

            if tick_data is not None and len(tick_data) > 0:
                tick = tick_data[qmt_code]
                report.append(f"\n当前价格: {tick.get('lastPrice', 'N/A')}")
                report.append(f"涨停价: {tick.get('upLimitPrice', 'N/A')}")
                report.append(f"跌停价: {tick.get('downLimitPrice', 'N/A')}")
                report.append(f"涨跌幅: {tick.get('pctChg', 'N/A')}%")
                report.append(f"成交量: {tick.get('volume', 'N/A')}")
                report.append(f"成交额: {tick.get('amount', 'N/A')}")

                # 五档盘口
                report.append(f"\n五档盘口：")
                for i in range(1, 6):
                    bid_price = tick.get(f'bidPrice{i}', 0)
                    bid_vol = tick.get(f'bidVol{i}', 0)
                    ask_price = tick.get(f'askPrice{i}', 0)
                    ask_vol = tick.get(f'askVol{i}', 0)
                    report.append(f"  买{i}: {bid_price} ({bid_vol}手)  卖{i}: {ask_price} ({ask_vol}手)")

                # 计算买卖压力
                total_bid = sum(tick.get(f'bidVol{i}', 0) for i in range(1, 6))
                total_ask = sum(tick.get(f'askVol{i}', 0) for i in range(1, 6))

                if total_bid + total_ask > 0:
                    buy_pressure = total_bid / (total_bid + total_ask) * 100
                    report.append(f"\n买盘压力: {buy_pressure:.1f}% | 卖盘压力: {100-buy_pressure:.1f}%")
            else:
                report.append(f"\n❌ 无法获取 Tick 数据")

            # 获取历史数据计算技术指标
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

            try:
                history_data = xtdata.get_market_data(
                    stock_list=[qmt_code],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date,
                    dividend_type='front'
                )

                if history_data is not None and 'close' in history_data:
                    close_df = history_data['close'].T
                    close_df.index = pd.to_datetime(close_df.index, format='%Y%m%d')
                    close_df = close_df.sort_index()

                    report.append(f"\n{'=' * 80}")
                    report.append(f"## 第三部分：技术指标分析")
                    report.append("=" * 80)

                    # 计算均线
                    close_df['MA5'] = close_df['close'].rolling(window=5).mean()
                    close_df['MA10'] = close_df['close'].rolling(window=10).mean()
                    close_df['MA20'] = close_df['close'].rolling(window=20).mean()
                    close_df['MA60'] = close_df['close'].rolling(window=60).mean()

                    # 计算乖离率
                    close_df['BIAS_5'] = (close_df['close'] - close_df['MA5']) / close_df['MA5'] * 100
                    close_df['BIAS_10'] = (close_df['close'] - close_df['MA10']) / close_df['MA10'] * 100

                    # 计算布林带
                    sma, upper_band, lower_band = calculate_bollinger_bands(close_df['close'])
                    close_df['BOLL_MID'] = sma
                    close_df['BOLL_UPPER'] = upper_band
                    close_df['BOLL_LOWER'] = lower_band

                    # 计算RSI
                    close_df['RSI'] = calculate_rsi(close_df['close'])

                    # 计算MACD
                    macd, signal_line, histogram = calculate_macd(close_df['close'])
                    close_df['MACD'] = macd
                    close_df['MACD_SIGNAL'] = signal_line
                    close_df['MACD_HIST'] = histogram

                    # 获取最近数据
                    recent_tech = close_df.tail(days)

                    report.append(f"\n📅 最近 {days} 天技术指标：\n")
                    report.append(recent_tech[['日期' if '日期' in recent_tech.columns else 'index', 'close', 'MA5', 'MA10', 'MA20', 'BIAS_5', 'BIAS_10', 'RSI']].to_string(index=False))

                    # 技术面分析
                    latest = close_df.iloc[-1]
                    report.append(f"\n技术面分析：")
                    report.append(f"  当前价格: {latest['close']:.2f}")
                    report.append(f"  MA5: {latest['MA5']:.2f} | MA10: {latest['MA10']:.2f} | MA20: {latest['MA20']:.2f}")
                    report.append(f"  BIAS_5: {latest['BIAS_5']:.2f}% | BIAS_10: {latest['BIAS_10']:.2f}%")
                    report.append(f"  RSI: {latest['RSI']:.2f}")
                    report.append(f"  MACD: {latest['MACD']:.2f} | 信号: {latest['MACD_SIGNAL']:.2f}")

                    # 技术面信号
                    tech_signals = []
                    if latest['close'] > latest['MA5'] > latest['MA10']:
                        tech_signals.append("🟢 短期趋势向上")
                    elif latest['close'] < latest['MA5'] < latest['MA10']:
                        tech_signals.append("🔴 短期趋势向下")

                    if abs(latest['BIAS_5']) > 5:
                        if latest['BIAS_5'] > 0:
                            tech_signals.append("⚠️ 短期超买")
                        else:
                            tech_signals.append("⚠️ 短期超卖")

                    if latest['RSI'] > 70:
                        tech_signals.append("⚠️ RSI 超买")
                    elif latest['RSI'] < 30:
                        tech_signals.append("✅ RSI 超卖")

                    if latest['MACD'] > latest['MACD_SIGNAL']:
                        tech_signals.append("🟢 MACD 金叉")
                    else:
                        tech_signals.append("🔴 MACD 死叉")

                    if tech_signals:
                        report.append(f"\n技术面信号：")
                        for signal in tech_signals:
                            report.append(f"  {signal}")

            except Exception as e:
                report.append(f"\n❌ 技术指标分析失败: {str(e)}")

        except ImportError:
            report.append(f"\n❌ 无法导入 QMT 模块，跳过 QMT 数据分析")
        except Exception as e:
            report.append(f"\n❌ QMT 数据分析失败: {str(e)}")

    # ========== 第四部分：综合建议 ==========
    report.append(f"\n{'=' * 80}")
    report.append(f"## 第四部分：综合建议")
    report.append("=" * 80)

    report.append(f"\n综合评分：")
    report.append(f"  - 资金面: {'强势' if bullish_count > bearish_count else '弱势'}")
    
    # 检查是否有技术面数据
    if 'latest' in locals():
        report.append(f"  - 技术面: {'强势' if latest['close'] > latest['MA5'] else '弱势'}")
    else:
        report.append(f"  - 技术面: N/A（QMT 数据不可用）")

    report.append(f"\n风险提示：")
    report.append(f"  - 本分析仅供参考，不构成投资建议")
    report.append(f"  - 投资有风险，入市需谨慎")
    report.append(f"  - 请结合其他因素综合判断")

    report.append(f"\n{'=' * 80}")

    # 生成最终报告
    final_report = "\n".join(report)

    # 自动保存到文件
    if auto_save:
        file_path = save_comprehensive_report(stock_code, days, final_report)
        return final_report, file_path

    return final_report


def save_comprehensive_report(stock_code, days, report_text):
    """
    保存综合分析报告到文件

    Args:
        stock_code: 股票代码
        days: 分析天数
        report_text: 报告文本内容

    Returns:
        str: 保存的文件路径
    """
    # 基础目录（使用相对路径，与 stock_ai_tool.py 保持一致）
    base_dir = 'data/stock_analysis'

    # 按股票代码分类
    stock_dir = os.path.join(base_dir, stock_code)

    # 确保目录存在
    os.makedirs(stock_dir, exist_ok=True)

    # 生成文件名：股票代码_日期_天数days_report.txt
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"{stock_code}_{date_str}_{days}days_report.txt"

    file_path = os.path.join(stock_dir, filename)

    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    return file_path


def quick_analysis(stock_code, days=5):
    """
    快速分析（简洁版）

    Args:
        stock_code: 股票代码
        days: 分析天数

    Returns:
        str: 简洁的分析报告
    """
    if stock_code.startswith('6'):
        market = 'sh'
    else:
        market = 'sz'

    try:
        # 使用速率限制器安全调用
        df = safe_request(ak.stock_individual_fund_flow, stock=stock_code, market=market)

        if df.empty:
            return f"❌ 未找到股票 {stock_code} 的数据"

        df['机构净流入'] = df['超大单净流入-净额'] + df['大单净流入-净额']
        df['散户净流入'] = df['中单净流入-净额'] + df['小单净流入-净额']

        recent_df = df.tail(days).copy()
        recent_df_wan = recent_df.copy()
        recent_df_wan['机构'] = recent_df_wan['机构净流入'] / 10000
        recent_df_wan['散户'] = recent_df_wan['散户净流入'] / 10000

        signals = []
        for _, row in recent_df_wan.iterrows():
            inst_net = row['机构']
            retail_net = row['散户']

            if inst_net < 0 and retail_net > 0:
                sig_type = "BEARISH"
            elif inst_net > 0 and retail_net < 0:
                sig_type = "BULLISH"
            elif inst_net > 0 and retail_net > 0:
                sig_type = "BULLISH"
            else:
                sig_type = "BEARISH"

            signals.append(sig_type)

        bullish_count = sum(1 for s in signals if s == 'BULLISH')
        total_inst = recent_df_wan['机构'].sum()

        if bullish_count > len(signals) * 0.6:
            trend = "🟢 吸筹"
            action = "关注"
        elif bullish_count < len(signals) * 0.4:
            trend = "🔴 减仓"
            action = "回避"
        else:
            trend = "⚪ 震荡"
            action = "观望"

        result = f"""
{stock_code} 快速分析（最近{days}天）
--------------------------------
趋势: {trend}
建议: {action}
吸筹: {bullish_count}天 | 减仓: {len(signals)-bullish_count}天
机构累计: {total_inst:.2f}万元
"""

        return result.strip()

    except Exception as e:
        return f"❌ 分析失败: {str(e)}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "300997"

    if len(sys.argv) > 2:
        days = int(sys.argv[2])
    else:
        days = 10

    # 检查是否启用自动保存
    auto_save = '--save' in sys.argv or '-s' in sys.argv

    if len(sys.argv) > 3 and sys.argv[3] == 'quick':
        result = quick_analysis(stock_code, days)
        print(result)
    else:
        result = comprehensive_stock_analysis(stock_code, days, auto_save=auto_save)
        if auto_save:
            report, file_path = result
            print(report)
            print(f"\n✅ 报告已保存到: {file_path}")
        else:
            print(result)