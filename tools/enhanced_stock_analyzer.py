"""
增强版个股分析工具
结合 AkShare 资金流向 + QMT 历史K线 + QMT Tick 数据
支持完整的技术指标分析
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 导入速率限制器
from logic.core.rate_limiter import get_rate_limiter, safe_request

# 导入新模块
from logic.analyzers.trap_detector import TrapDetector
from logic.analyzers.capital_classifier import CapitalClassifier
from logic.analyzers.rolling_metrics import RollingMetricsCalculator


class EnhancedStockAnalyzer:
    """增强版个股分析器"""

    def __init__(self, use_qmt=True):
        """
        初始化分析器

        Args:
            use_qmt: 是否使用 QMT 数据
        """
        self.use_qmt = use_qmt
        self.qmt_available = False

        # 尝试连接 QMT
        if use_qmt:
            try:
                from xtquant import xtdata
                from logic.utils.code_converter import CodeConverter
                self.xtdata = xtdata
                self.converter = CodeConverter()
                self.qmt_available = True
            except ImportError:
                print("⚠️ 无法导入 QMT 模块，将跳过 QMT 数据分析")
                self.qmt_available = False

        # 初始化新模块
        self.trap_detector = TrapDetector()
        self.capital_classifier = CapitalClassifier()
        self.rolling_calculator = RollingMetricsCalculator()

    def calculate_technical_indicators(self, df):
        """
        计算技术指标

        Args:
            df: 包含 OHLCV 的 DataFrame

        Returns:
            DataFrame: 添加了技术指标的 DataFrame
        """
        if df.empty or 'close' not in df.columns:
            return df

        # 均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()

        # 乖离率
        df['BIAS_5'] = (df['close'] - df['MA5']) / df['MA5'] * 100
        df['BIAS_10'] = (df['close'] - df['MA10']) / df['MA10'] * 100
        df['BIAS_20'] = (df['close'] - df['MA20']) / df['MA20'] * 100

        # 布林带
        df['BOLL_MID'] = df['close'].rolling(window=20).mean()
        df['BOLL_STD'] = df['close'].rolling(window=20).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + 2 * df['BOLL_STD']
        df['BOLL_LOWER'] = df['BOLL_MID'] - 2 * df['BOLL_STD']
        df['BOLL_WIDTH'] = (df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID'] * 100

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']

        # KDJ
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['K'] = rsv.ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']

        # ATR (平均真实波幅)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

        # 涨跌幅
        df['PCT_CHG'] = df['close'].pct_change() * 100

        # 振幅
        df['AMPLITUDE'] = (df['high'] - df['low']) / df['close'].shift(1) * 100

        # 成交量相关
        df['VOLUME_MA5'] = df['volume'].rolling(window=5).mean()
        df['VOLUME_MA10'] = df['volume'].rolling(window=10).mean()
        df['VOLUME_RATIO'] = df['volume'] / df['VOLUME_MA10']  # 量比

        return df

    def calculate_dde_from_tick(self, tick_data):
        """
        从 Tick 数据计算 DDE（资金流向）

        Args:
            tick_data: QMT tick 数据

        Returns:
            dict: DDE 相关指标
        """
        try:
            # 计算买卖压力
            total_bid = sum(tick_data.get(f'bidVol{i}', 0) for i in range(1, 6))
            total_ask = sum(tick_data.get(f'askVol{i}', 0) for i in range(1, 6))

            if total_bid + total_ask > 0:
                buy_pressure = total_bid / (total_bid + total_ask) * 100
                sell_pressure = total_ask / (total_bid + total_ask) * 100
            else:
                buy_pressure = 0
                sell_pressure = 0

            # 计算加权价格
            bid_prices = [tick_data.get(f'bidPrice{i}', 0) for i in range(1, 6) if tick_data.get(f'bidPrice{i}', 0) > 0]
            ask_prices = [tick_data.get(f'askPrice{i}', 0) for i in range(1, 6) if tick_data.get(f'askPrice{i}', 0) > 0]

            bid_price = sum(bid_prices) / len(bid_prices) if bid_prices else 0
            ask_price = sum(ask_prices) / len(ask_prices) if ask_prices else 0

            # 计算价差
            price_gap = ask_price - bid_price if (bid_price > 0 and ask_price > 0) else 0

            return {
                'buy_pressure': buy_pressure,
                'sell_pressure': sell_pressure,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'price_gap': price_gap,
                'total_bid': total_bid,
                'total_ask': total_ask
            }
        except Exception as e:
            return {'error': str(e)}

    def get_qmt_history_data(self, stock_code, days=60):
        """
        获取 QMT 历史数据

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            DataFrame: QMT 历史数据
        """
        if not self.qmt_available:
            return None

        try:
            # 转换代码格式
            qmt_code = self.converter.to_qmt(stock_code)

            # 计算日期范围
            # 为了计算所有技术指标，需要至少60天数据（MA20需要20天，RSI需要14天等）
            # 但如果用户要求的天数更多，则使用用户要求的天数
            required_days = max(days, 60)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=required_days + 30)  # 多取30天确保数据完整

            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

            # 获取历史数据
            history_data = self.xtdata.get_market_data(
                stock_list=[qmt_code],
                period='1d',
                start_time=start_str,
                end_time=end_str,
                dividend_type='front'
            )

            # 处理空数据
            if history_data is None or len(history_data) == 0:
                print(f"⚠️ 未找到 {stock_code} 的历史数据，可能需要先下载")
                return None

            # QMT返回格式：字典，每个键对应一个DataFrame(1行x N列日期)
            # 需要将所有列的数据合并成一个DataFrame，日期作为索引
            if not isinstance(history_data, dict):
                print(f"⚠️ QMT数据格式异常: {type(history_data)}")
                return None

            # 提取所有需要的列
            required_fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
            df_dict = {}

            for field in required_fields:
                if field in history_data:
                    data = history_data[field]
                    if isinstance(data, pd.DataFrame) and not data.empty:
                        # 转置数据：将日期变成行
                        df_transposed = data.T
                        # 提取第一列（股票代码列）的值
                        df_dict[field] = df_transposed.iloc[:, 0]
                    else:
                        print(f"⚠️ 字段 {field} 数据格式异常")
                        return None
                else:
                    print(f"⚠️ 缺少字段: {field}")
                    return None

            # 创建DataFrame
            df = pd.DataFrame(df_dict)

            # 处理时间索引
            if 'time' in df.columns:
                # QMT返回的时间是毫秒时间戳
                df.index = pd.to_datetime(df['time'], unit='ms')
                df = df.drop(columns=['time'])
            else:
                # 如果没有时间字段，使用索引
                df.index = pd.to_datetime(df.index, format='%Y%m%d', errors='coerce')

            # 去除无效日期
            df = df[df.index.notna()]
            df = df.sort_index()

            if df.empty:
                print(f"⚠️ 没有有效的历史数据")
                return None

            # 计算涨跌幅
            if 'close' in df.columns and 'preClose' in history_data:
                # 正确处理preClose数据
                preclose_df = history_data['preClose'].T
                preclose_series = preclose_df.iloc[:, 0]

                # 使用time列的时间戳来转换preClose的索引，确保与df索引匹配
                if 'time' in history_data:
                    time_df = history_data['time'].T
                    time_series = time_df.iloc[:, 0]
                    # 将time_series的索引转换为datetime格式
                    time_series.index = pd.to_datetime(time_series.index, format='%Y%m%d', errors='coerce')
                    # 用时间戳作为索引
                    preclose_series.index = pd.to_datetime(time_series, unit='ms').values
                else:
                    # 如果没有time列，使用原始索引
                    preclose_series.index = pd.to_datetime(preclose_series.index, format='%Y%m%d', errors='coerce')

                # 确保索引匹配
                df['preClose'] = preclose_series.reindex(df.index)
                # 计算涨跌幅
                df['pct_chg'] = ((df['close'] - df['preClose']) / df['preClose'] * 100).round(2)
            elif 'close' in df.columns:
                # 如果没有preClose，使用前一日收盘价计算
                df['pct_chg'] = df['close'].pct_change() * 100

            # 计算振幅
            if 'high' in df.columns and 'low' in df.columns and 'preClose' in df.columns:
                df['AMPLITUDE'] = ((df['high'] - df['low']) / df['preClose'] * 100).round(2)
            elif 'high' in df.columns and 'low' in df.columns:
                # 如果没有preClose，使用close代替
                df['AMPLITUDE'] = ((df['high'] - df['low']) / df['close'] * 100).round(2)

            return df

        except Exception as e:
            print(f"❌ 获取 QMT 历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_qmt_tick_data(self, stock_code):
        """
        获取 QMT Tick 数据

        Args:
            stock_code: 股票代码

        Returns:
            dict: Tick 数据
        """
        if not self.qmt_available:
            return None

        try:
            # 转换代码格式
            qmt_code = self.converter.to_qmt(stock_code)

            # 获取 Tick 数据
            tick_data = self.xtdata.get_full_tick([qmt_code])

            if tick_data is not None and len(tick_data) > 0:
                return tick_data[qmt_code]

            return None

        except Exception as e:
            print(f"❌ 获取 QMT Tick 数据失败: {e}")
            return None

    def _get_risk_level(self, score: float) -> str:
        """
        获取风险等级

        Args:
            score: 风险评分（0-1）

        Returns:
            str: 风险等级
        """
        if score >= 0.8:
            return 'CRITICAL'
        elif score >= 0.6:
            return 'HIGH'
        elif score >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _get_recommendation(self, score: float, capital_classification: dict) -> str:
        """
        获取操作建议

        Args:
            score: 风险评分（0-1）
            capital_classification: 资金分类结果

        Returns:
            str: 操作建议
        """
        capital_type = capital_classification.get('type', 'UNCLEAR')
        capital_confidence = capital_classification.get('confidence', 0)

        if score >= 0.8:
            return 'AVOID - 高风险诱多陷阱，建议立即回避'
        elif score >= 0.6:
            if capital_type == 'HOT_MONEY' and capital_confidence >= 0.7:
                return 'WAIT_AND_WATCH - 疑似游资操盘，观察1-3天后再决策'
            else:
                return 'CAUTIOUS - 谨慎观察，设置严格止损'
        elif score >= 0.4:
            return 'MODERATE - 中等风险，可小仓位参与'
        else:
            if capital_type == 'LONG_TERM' and capital_confidence >= 0.7:
                return 'OPPORTUNITY - 长线资金进场，可考虑布局'
            elif capital_type == 'INSTITUTIONAL' and capital_confidence >= 0.7:
                return 'FOLLOW - 机构稳健吸筹，可考虑跟随'
            else:
                return 'NEUTRAL - 无明显信号，继续观察'

    def analyze_fund_flow(self, stock_code, days=60):
        """
        分析资金流向

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            tuple: (DataFrame, dict) - 资金流向数据和统计信息
        """
        # 判断市场
        if stock_code.startswith('6'):
            market = 'sh'
        else:
            market = 'sz'

        try:
            # 使用速率限制器安全调用
            df = safe_request(ak.stock_individual_fund_flow, stock=stock_code, market=market)

            if df.empty:
                return None, None

            # 计算机构和散户净流入
            df['机构净流入'] = df['超大单净流入-净额'] + df['大单净流入-净额']
            df['散户净流入'] = df['中单净流入-净额'] + df['小单净流入-净额']

            # 转换为万元
            df['机构(万)'] = df['机构净流入'] / 10000
            df['散户(万)'] = df['散户净流入'] / 10000

            # 获取最近 days 天数据
            recent_df = df.tail(days).copy()

            # 计算信号
            signals = []
            for _, row in recent_df.iterrows():
                inst_net = row['机构(万)']
                retail_net = row['散户(万)']

                if inst_net < 0 and retail_net > 0:
                    signal = "BEARISH"
                elif inst_net > 0 and retail_net < 0:
                    signal = "BULLISH"
                elif inst_net > 0 and retail_net > 0:
                    signal = "BULLISH"
                else:
                    signal = "BEARISH"

                signals.append(signal)

            # 统计信息
            bullish_count = sum(1 for s in signals if s == 'BULLISH')
            bearish_count = len(signals) - bullish_count
            total_inst = recent_df['机构(万)'].sum()
            total_retail = recent_df['散户(万)'].sum()

            stats = {
                'total_days': len(recent_df),
                'bullish_days': bullish_count,
                'bearish_days': bearish_count,
                'total_institution': total_inst,
                'total_retail': total_retail,
                'data_range': f"{df['日期'].min()} 至 {df['日期'].max()}",
                'latest_date': df['日期'].max()
            }

            return recent_df, stats

        except Exception as e:
            print(f"❌ 资金流向分析失败: {e}")
            return None, None

    def comprehensive_analysis(self, stock_code, days=60, output_all_data=True, pure_data=False):
        """
        综合分析

        Args:
            stock_code: 股票代码
            days: 分析天数
            output_all_data: 是否输出所有数据
            pure_data: 是否只输出纯数据（不包含主观判断和建议）

        Returns:
            str: 分析报告
        """
        report = []
        report.append("=" * 80)
        report.append(f"📊 {stock_code} 增强版综合分析报告")
        report.append("=" * 80)
        report.append(f"分析天数: 最近 {days} 天")
        report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)

        # ========== 第一部分：资金流向分析 ==========
        report.append(f"\n## 第一部分：资金流向分析（AkShare）\n")

        fund_df, fund_stats = self.analyze_fund_flow(stock_code, days)

        if fund_df is not None and fund_stats is not None:
            report.append(f"数据范围: {fund_stats['data_range']}")
            report.append(f"总数据: {len(fund_df)} 天 | 分析: {fund_stats['total_days']} 天\n")

            # 输出详细数据
            if output_all_data:
                report.append("📅 每日资金流向详情（单位：万元）：\n")
                fund_df_display = fund_df[['日期', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额', '机构(万)', '散户(万)']].copy()
                fund_df_display.columns = ['日期', '超大单', '大单', '中单', '小单', '机构', '散户']
                fund_df_display['超大单'] = fund_df_display['超大单'] / 10000
                fund_df_display['大单'] = fund_df_display['大单'] / 10000
                fund_df_display['中单'] = fund_df_display['中单'] / 10000
                fund_df_display['小单'] = fund_df_display['小单'] / 10000
                report.append(fund_df_display.to_string(index=False))
                report.append("")
            else:
                # 只显示最近10天
                report.append("📅 最近 10 天资金流向（单位：万元）：\n")
                recent_10 = fund_df.tail(10).copy()
                fund_df_display = recent_10[['日期', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额', '机构(万)', '散户(万)']].copy()
                fund_df_display.columns = ['日期', '超大单', '大单', '中单', '小单', '机构', '散户']
                fund_df_display['超大单'] = fund_df_display['超大单'] / 10000
                fund_df_display['大单'] = fund_df_display['大单'] / 10000
                fund_df_display['中单'] = fund_df_display['中单'] / 10000
                fund_df_display['小单'] = fund_df_display['小单'] / 10000
                report.append(fund_df_display.to_string(index=False))
                report.append("")

            # 每日信号
            report.append("📊 每日信号分析：\n")
            signals = []
            for _, row in fund_df.iterrows():
                inst_net = row['机构(万)']
                retail_net = row['散户(万)']

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
            report.append(f"\n📈 资金流向统计：")
            report.append(f"  总天数: {fund_stats['total_days']} 天")
            report.append(f"  吸筹信号: {fund_stats['bullish_days']} 天 ({fund_stats['bullish_days']/fund_stats['total_days']*100:.1f}%)")
            report.append(f"  接盘信号: {fund_stats['bearish_days']} 天 ({fund_stats['bearish_days']/fund_stats['total_days']*100:.1f}%)")
            report.append(f"  【{days}天累计】机构: {fund_stats['total_institution']:>10.2f} 万元")
            report.append(f"  【{days}天累计】散户: {fund_stats['total_retail']:>10.2f} 万元")
            
            # 添加资金来源说明
            if fund_stats['total_institution'] < 0 and fund_stats['total_retail'] > 0:
                report.append(f"\n💰 资金来源说明：")
                report.append(f"  - 【{days}天累计】机构净流出 {abs(fund_stats['total_institution']):.2f} 万元（主力出货）")
                report.append(f"  - 【{days}天累计】散户净流入 {fund_stats['total_retail']:.2f} 万元（散户接盘）")
                report.append(f"  - 说明：资金从机构流向散户，通常意味着主力在出货")
            elif fund_stats['total_institution'] > 0 and fund_stats['total_retail'] < 0:
                report.append(f"\n💰 资金来源说明：")
                report.append(f"  - 【{days}天累计】机构净流入 {fund_stats['total_institution']:.2f} 万元（主力吸筹）")
                report.append(f"  - 【{days}天累计】散户净流出 {abs(fund_stats['total_retail']):.2f} 万元（散户割肉）")
                report.append(f"  - 说明：资金从散户流向机构，通常意味着主力在吸筹")
            elif fund_stats['total_institution'] > 0 and fund_stats['total_retail'] > 0:
                report.append(f"\n💰 资金来源说明：")
                report.append(f"  - 【{days}天累计】机构和散户同时净流入")
                report.append(f"  - 说明：市场共同看好，可能有大行情")
            elif fund_stats['total_institution'] < 0 and fund_stats['total_retail'] < 0:
                report.append(f"\n💰 资金来源说明：")
                report.append(f"  - 【{days}天累计】机构和散户同时净流出")
                report.append(f"  - 说明：市场整体悲观，注意风险")

            # 纯数据模式不输出趋势判断和建议
            if not pure_data:
                # 趋势判断
                if fund_stats['bullish_days'] > fund_stats['bearish_days'] * 1.5:
                    fund_trend = "🟢 强势吸筹趋势"
                    fund_action = "可以考虑低吸"
                elif fund_stats['bullish_days'] > fund_stats['bearish_days']:
                    fund_trend = "🟡 吸筹趋势"
                    fund_action = "谨慎关注"
                elif fund_stats['bearish_days'] > fund_stats['bullish_days'] * 1.5:
                    fund_trend = "🔴 强势减仓趋势"
                    fund_action = "建议回避"
                else:
                    fund_trend = "⚪ 震荡趋势"
                    fund_action = "观望"

                report.append(f"\n整体趋势: {fund_trend}")
                report.append(f"操作建议: {fund_action}")

        else:
            report.append("❌ 未找到资金流向数据")

        # ========== 第二部分：QMT 技术分析 ==========
        if self.qmt_available:
            report.append(f"\n{'=' * 80}")
            report.append(f"## 第二部分：QMT 技术分析")
            report.append("=" * 80)

            # 获取历史数据
            qmt_df = self.get_qmt_history_data(stock_code, days)

            if qmt_df is not None and not qmt_df.empty and 'close' in qmt_df.columns:
                # 先计算技术指标（需要足够的历史数据）
                qmt_df = self.calculate_technical_indicators(qmt_df)
                
                # 然后截取用户需要的天数
                qmt_df = qmt_df.tail(days)

                report.append(f"\n数据范围: {qmt_df.index[0].strftime('%Y-%m-%d')} 至 {qmt_df.index[-1].strftime('%Y-%m-%d')} ({len(qmt_df)}天)\n")

                # 输出详细数据
                if output_all_data:
                    report.append("📅 每日技术指标详情：\n")
                    # 只显示存在的列
                    available_cols = [col for col in ['open', 'high', 'low', 'close', 'volume', 'MA5', 'MA10', 'MA20', 'BIAS_5', 'BIAS_10', 'RSI', 'MACD'] if col in qmt_df.columns]
                    if available_cols:
                        tech_df_display = qmt_df[available_cols].copy()
                        tech_df_display.index.name = '日期'
                        report.append(tech_df_display.to_string())
                        report.append("")
                    else:
                        report.append("⚠️ 未找到技术指标数据\n")

                # 技术面分析
                latest = qmt_df.iloc[-1]
                report.append("📊 技术面分析：")
                report.append(f"  当前价格: {latest['close']:.2f}")
                
                if 'pct_chg' in qmt_df.columns:
                    report.append(f"  涨跌幅: {latest['pct_chg']:.2f}%")
                if 'AMPLITUDE' in qmt_df.columns:
                    report.append(f"  振幅: {latest['AMPLITUDE']:.2f}%")
                if 'volume' in qmt_df.columns:
                    report.append(f"  成交量: {latest['volume']:.0f}")
                if 'VOLUME_RATIO' in qmt_df.columns:
                    report.append(f"  量比: {latest['VOLUME_RATIO']:.2f}")
                
                report.append("")
                
                if 'MA5' in qmt_df.columns and 'MA10' in qmt_df.columns and 'MA20' in qmt_df.columns:
                    report.append(f"  均线: MA5={latest['MA5']:.2f} | MA10={latest['MA10']:.2f} | MA20={latest['MA20']:.2f}")
                
                if 'BIAS_5' in qmt_df.columns and 'BIAS_10' in qmt_df.columns:
                    report.append(f"  乖离率: BIAS_5={latest['BIAS_5']:.2f}% | BIAS_10={latest['BIAS_10']:.2f}%")
                
                if 'RSI' in qmt_df.columns:
                    report.append(f"  RSI: {latest['RSI']:.2f}")
                
                if 'MACD' in qmt_df.columns:
                    report.append(f"  MACD: {latest['MACD']:.2f}")
                    if 'MACD_SIGNAL' in qmt_df.columns:
                        report.append(f"  MACD 信号: {latest['MACD_SIGNAL']:.2f}")
                    if 'MACD_HIST' in qmt_df.columns:
                        report.append(f"  MACD 柱状: {latest['MACD_HIST']:.2f}")
                
                if 'BOLL_UPPER' in qmt_df.columns:
                    report.append(f"  布林带: 上轨={latest['BOLL_UPPER']:.2f} | 中轨={latest['BOLL_MID']:.2f} | 下轨={latest['BOLL_LOWER']:.2f}")
                
                if 'ATR' in qmt_df.columns:
                    report.append(f"  ATR: {latest['ATR']:.2f}")

                # 技术面信号
                tech_signals = []
                
                if 'MA5' in qmt_df.columns and 'MA10' in qmt_df.columns:
                    if latest['close'] > latest['MA5'] > latest['MA10']:
                        tech_signals.append("🟢 短期趋势向上")
                    elif latest['close'] < latest['MA5'] < latest['MA10']:
                        tech_signals.append("🔴 短期趋势向下")
                
                if 'BIAS_5' in qmt_df.columns:
                    if abs(latest['BIAS_5']) > 5:
                        if latest['BIAS_5'] > 0:
                            tech_signals.append("⚠️ 短期超买")
                        else:
                            tech_signals.append("⚠️ 短期超卖")
                
                if 'RSI' in qmt_df.columns:
                    if latest['RSI'] > 70:
                        tech_signals.append("⚠️ RSI 超买")
                    elif latest['RSI'] < 30:
                        tech_signals.append("✅ RSI 超卖")
                
                if 'MACD' in qmt_df.columns and 'MACD_SIGNAL' in qmt_df.columns:
                    if latest['MACD'] > latest['MACD_SIGNAL']:
                        tech_signals.append("🟢 MACD 金叉")
                    else:
                        tech_signals.append("🔴 MACD 死叉")
                
                if 'BOLL_UPPER' in qmt_df.columns and 'BOLL_LOWER' in qmt_df.columns:
                    if latest['close'] > latest['BOLL_UPPER']:
                        tech_signals.append("⚠️ 突破布林带上轨")
                    elif latest['close'] < latest['BOLL_LOWER']:
                        tech_signals.append("✅ 触及布林带下轨")
                
                if 'VOLUME_RATIO' in qmt_df.columns:
                    if latest['VOLUME_RATIO'] > 2:
                        tech_signals.append("🟢 放量")
                    elif latest['VOLUME_RATIO'] < 0.5:
                        tech_signals.append("⚠️ 缩量")

                if tech_signals:
                    report.append(f"\n技术面信号：")
                    for signal in tech_signals:
                        report.append(f"  {signal}")

                # 多日趋势
                report.append(f"\n多日趋势：")
                
                if 'MA5' in qmt_df.columns and 'MA10' in qmt_df.columns:
                    ma5_trend = "向上" if qmt_df['MA5'].iloc[-1] > qmt_df['MA5'].iloc[-5] else "向下"
                    ma10_trend = "向上" if qmt_df['MA10'].iloc[-1] > qmt_df['MA10'].iloc[-5] else "向下"
                    report.append(f"  MA5趋势: {ma5_trend}")
                    report.append(f"  MA10趋势: {ma10_trend}")
                
                if 'BOLL_UPPER' in qmt_df.columns and 'BOLL_LOWER' in qmt_df.columns:
                    price_position = ""
                    if latest['close'] > latest['BOLL_UPPER']:
                        price_position = "突破上轨（强势）"
                    elif latest['close'] < latest['BOLL_LOWER']:
                        price_position = "跌破下轨（弱势）"
                    else:
                        price_position = "在布林带通道内（中性）"
                    report.append(f"  价格位置: {price_position}")

            else:
                report.append(f"\n❌ 无法获取 QMT 历史数据")

            # Tick 数据分析
            report.append(f"\n{'=' * 80}")
            report.append(f"## 第三部分：QMT 实时盘口")
            report.append("=" * 80)

            tick_data = self.get_qmt_tick_data(stock_code)

            if tick_data is not None:
                report.append(f"\n当前价格: {tick_data.get('lastPrice', 'N/A')}")
                report.append(f"涨停价: {tick_data.get('upLimitPrice', 'N/A')}")
                report.append(f"跌停价: {tick_data.get('downLimitPrice', 'N/A')}")
                report.append(f"涨跌幅: {tick_data.get('pctChg', 'N/A')}%")
                report.append(f"成交量: {tick_data.get('volume', 'N/A')}")
                report.append(f"成交额: {tick_data.get('amount', 'N/A')}")

                # 五档盘口
                report.append(f"\n五档盘口：")
                for i in range(1, 6):
                    bid_price = tick_data.get(f'bidPrice{i}', 0)
                    bid_vol = tick_data.get(f'bidVol{i}', 0)
                    ask_price = tick_data.get(f'askPrice{i}', 0)
                    ask_vol = tick_data.get(f'askVol{i}', 0)
                    report.append(f"  买{i}: {bid_price} ({bid_vol}手)  卖{i}: {ask_price} ({ask_vol}手)")

                # DDE 分析
                dde_data = self.calculate_dde_from_tick(tick_data)
                if 'error' not in dde_data:
                    report.append(f"\nDDE 分析：")
                    report.append(f"  买盘压力: {dde_data['buy_pressure']:.1f}%")
                    report.append(f"  卖盘压力: {dde_data['sell_pressure']:.1f}%")
                    report.append(f"  买价: {dde_data['bid_price']:.2f}")
                    report.append(f"  卖价: {dde_data['ask_price']:.2f}")
                    report.append(f"  价差: {dde_data['price_gap']:.2f}")
                    report.append(f"  买盘总量: {dde_data['total_bid']}手")
                    report.append(f"  卖盘总量: {dde_data['total_ask']}手")

                    if dde_data['buy_pressure'] > 60:
                        report.append(f"  信号: 🟢 买盘强势")
                    elif dde_data['sell_pressure'] > 60:
                        report.append(f"  信号: 🔴 卖盘强势")
                    else:
                        report.append(f"  信号: ⚪ 买卖均衡")
                else:
                    report.append(f"\n❌ DDE 计算失败: {dde_data['error']}")
            else:
                report.append(f"\n⚠️ 无法获取实时盘口数据")
                report.append(f"   可能原因：非交易时间、QMT客户端未连接或未登录")
                report.append(f"   说明：历史K线数据可以正常获取，实时盘口仅在交易时间可用")
                report.append(f"   建议：交易时间重试，或检查QMT客户端连接状态")

        else:
            report.append(f"\n{'=' * 80}")
            report.append(f"## 第二部分：QMT 数据")
            report.append("=" * 80)
            report.append(f"\n❌ QMT 模块未连接，跳过 QMT 数据分析")

        # ========== 第三部分：综合建议 ==========
        if not pure_data:
            report.append(f"\n{'=' * 80}")
            report.append(f"## 第三部分：综合建议")
            report.append("=" * 80)

            report.append(f"\n综合评分：")

            if fund_stats:
                report.append(f"  - 资金面: {'强势' if fund_stats['bullish_days'] > fund_stats['bearish_days'] else '弱势'}")
                report.append(f"  - 吸筹: {fund_stats['bullish_days']}天 | 减仓: {fund_stats['bearish_days']}天")
                report.append(f"  - 【{days}天累计】机构: {fund_stats['total_institution']:.2f}万元")

            if self.qmt_available and qmt_df is not None and not qmt_df.empty:
                if 'close' in qmt_df.columns and 'MA5' in qmt_df.columns:
                    report.append(f"  - 技术面: {'强势' if qmt_df['close'].iloc[-1] > qmt_df['MA5'].iloc[-1] else '弱势'}")
                if 'RSI' in qmt_df.columns:
                    report.append(f"  - RSI: {qmt_df['RSI'].iloc[-1]:.2f}")

            report.append(f"\n风险提示：")
            report.append(f"  - 本分析仅供参考，不构成投资建议")
            report.append(f"  - 投资有风险，入市需谨慎")
            report.append(f"  - 请结合其他因素综合判断")

            report.append(f"\n{'=' * 80}")

        return "\n".join(report)


def analyze_stock_enhanced(stock_code, days=60, output_all_data=True, use_qmt=True, pure_data=False):
    """
    增强版个股分析（便捷接口）

    Args:
        stock_code: 股票代码
        days: 分析天数
        output_all_data: 是否输出所有数据
        use_qmt: 是否使用 QMT 数据
        pure_data: 是否只输出纯数据（不包含主观判断和建议）

    Returns:
        str: 分析报告
    """
    analyzer = EnhancedStockAnalyzer(use_qmt=use_qmt)
    return analyzer.comprehensive_analysis(stock_code, days=days, output_all_data=output_all_data, pure_data=pure_data)


def analyze_stock_json(stock_code, days=60, use_qmt=True, auto_download=True, pure_data=False):
    """
    增强版个股分析（JSON格式 - 便于AI调用）

    Args:
        stock_code: 股票代码
        days: 分析天数
        use_qmt: 是否使用 QMT 数据
        auto_download: 是否自动下载QMT数据(如果未找到)
        pure_data: 是否只输出纯数据（不包含主观判断和建议）

    Returns:
        dict: 分析结果
    """
    analyzer = EnhancedStockAnalyzer(use_qmt=use_qmt)

    # 获取资金流向数据
    fund_df, fund_stats = analyzer.analyze_fund_flow(stock_code, days)

    # 构建结果
    result = {
        'stock_code': stock_code,
        'analyze_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'analyze_days': days,
        'fund_flow': {},
        'qmt': {},
        'summary': {}
    }

    # 资金流向数据
    if fund_df is not None and fund_stats is not None:
        result['fund_flow'] = {
            'data_range': fund_stats['data_range'],
            'total_days': fund_stats['total_days'],
            'bullish_days': fund_stats['bullish_days'],
            'bearish_days': fund_stats['bearish_days'],
            'total_institution': fund_stats['total_institution'],
            'total_retail': fund_stats['total_retail'],
            'trend': 'strong_bullish' if fund_stats['bullish_days'] > fund_stats['bearish_days'] * 1.5 else
                     'bullish' if fund_stats['bullish_days'] > fund_stats['bearish_days'] else
                     'strong_bearish' if fund_stats['bearish_days'] > fund_stats['bullish_days'] * 1.5 else
                     'neutral',
            'daily_data': []
        }

        # 逐日数据
        for _, row in fund_df.iterrows():
            inst_net = row['机构(万)']
            retail_net = row['散户(万)']

            if inst_net < 0 and retail_net > 0:
                signal = "接盘"
                sig_type = "BEARISH"
                desc = "机构减仓，散户接盘"
            elif inst_net > 0 and retail_net < 0:
                signal = "吸筹"
                sig_type = "BULLISH"
                desc = "机构吸筹，散户恐慌"
            elif inst_net > 0 and retail_net > 0:
                signal = "共买"
                sig_type = "BULLISH"
                desc = "共同看好"
            else:
                signal = "共卖"
                sig_type = "BEARISH"
                desc = "共同看淡"

            result['fund_flow']['daily_data'].append({
                'date': str(row['日期']),
                'super_large': round(row['超大单净流入-净额'] / 10000, 2),
                'large': round(row['大单净流入-净额'] / 10000, 2),
                'medium': round(row['中单净流入-净额'] / 10000, 2),
                'small': round(row['小单净流入-净额'] / 10000, 2),
                'institution': round(inst_net, 2),
                'retail': round(retail_net, 2),
                'signal': signal,
                'signal_type': sig_type,
                'description': desc
            })

        # ========== 新增：滚动指标计算 ==========
        if result['fund_flow']['daily_data']:
            daily_data = result['fund_flow']['daily_data'].copy()
            enriched_data = analyzer.rolling_calculator.add_rolling_metrics(daily_data)
            result['fund_flow']['daily_data'] = enriched_data

            # 添加滚动指标汇总
            rolling_summary = analyzer.rolling_calculator.get_rolling_summary(enriched_data)
            result['fund_flow']['rolling_summary'] = rolling_summary

            # ========== 新增：诱多陷阱检测 ==========
            trap_detection = analyzer.trap_detector.comprehensive_trap_scan(enriched_data)
            result['trap_detection'] = trap_detection

            # ========== 新增：资金性质分类 ==========
            capital_classification = analyzer.capital_classifier.classify(enriched_data, window=30)
            result['capital_analysis'] = capital_classification

            # ========== 新增：综合风险评分 ==========
            trap_risk_score = trap_detection.get('comprehensive_risk_score', 0.0)
            capital_type = capital_classification.get('type', 'UNCLEAR')

            # 调整风险评分（游资类型风险更高）
            adjusted_risk_score = trap_risk_score
            if capital_type == 'HOT_MONEY':
                adjusted_risk_score = min(trap_risk_score + 0.15, 1.0)
            elif capital_type == 'LONG_TERM':
                adjusted_risk_score = max(trap_risk_score - 0.15, 0.0)
            elif capital_type == 'INSTITUTIONAL':
                adjusted_risk_score = max(trap_risk_score - 0.10, 0.0)

            result['risk_assessment'] = {
                'trap_risk_score': round(trap_risk_score, 2),
                'adjusted_risk_score': round(adjusted_risk_score, 2),
                'risk_level': analyzer._get_risk_level(adjusted_risk_score),
                'recommendation': analyzer._get_recommendation(adjusted_risk_score, capital_classification)
            }

    # QMT数据
    if use_qmt and analyzer.qmt_available:
        qmt_df = analyzer.get_qmt_history_data(stock_code, days)

        # 如果数据为空且自动下载开启，尝试下载
        if (qmt_df is None or qmt_df.empty) and auto_download:
            try:
                from logic.utils.code_converter import CodeConverter
                converter = CodeConverter()
                qmt_code = converter.to_qmt(stock_code)

                end_date = datetime.now()
                start_date = end_date - timedelta(days=days + 30)

                analyzer.xtdata.download_history_data(
                    stock_code=qmt_code,
                    period='1d',
                    start_time=start_date.strftime('%Y%m%d'),
                    end_time=end_date.strftime('%Y%m%d')
                )

                # 重新获取数据
                qmt_df = analyzer.get_qmt_history_data(stock_code, days)
            except Exception as e:
                pass

        if qmt_df is not None and not qmt_df.empty:
            # 先计算技术指标（需要足够的历史数据）
            qmt_df = analyzer.calculate_technical_indicators(qmt_df)
            
            # 然后截取用户需要的天数
            qmt_df = qmt_df.tail(days)

            result['qmt'] = {
                'data_range': f"{qmt_df.index[0].strftime('%Y-%m-%d')} 至 {qmt_df.index[-1].strftime('%Y-%m-%d')}",
                'total_days': len(qmt_df),
                'latest': {},
                'daily_data': []
            }

            # 最新数据
            latest = qmt_df.iloc[-1]
            result['qmt']['latest'] = {
                'close': float(latest['close']) if 'close' in latest else None,
                'pct_chg': float(latest['pct_chg']) if 'pct_chg' in latest else None,
                'volume': float(latest['volume']) if 'volume' in latest else None,
            }

            if 'MA5' in latest:
                result['qmt']['latest']['MA5'] = float(latest['MA5'])
            if 'MA10' in latest:
                result['qmt']['latest']['MA10'] = float(latest['MA10'])
            if 'MA20' in latest:
                result['qmt']['latest']['MA20'] = float(latest['MA20'])
            if 'BIAS_5' in latest:
                result['qmt']['latest']['BIAS_5'] = float(latest['BIAS_5'])
            if 'BIAS_10' in latest:
                result['qmt']['latest']['BIAS_10'] = float(latest['BIAS_10'])
            if 'RSI' in latest:
                result['qmt']['latest']['RSI'] = float(latest['RSI'])
            if 'MACD' in latest:
                result['qmt']['latest']['MACD'] = float(latest['MACD'])
            if 'MACD_SIGNAL' in latest:
                result['qmt']['latest']['MACD_SIGNAL'] = float(latest['MACD_SIGNAL'])
            if 'MACD_HIST' in latest:
                result['qmt']['latest']['MACD_HIST'] = float(latest['MACD_HIST'])

            # 逐日数据
            for idx, row in qmt_df.iterrows():
                day_data = {
                    'date': idx.strftime('%Y-%m-%d'),
                    'close': float(row['close']) if 'close' in row else None,
                }

                if 'open' in row:
                    day_data['open'] = float(row['open'])
                if 'high' in row:
                    day_data['high'] = float(row['high'])
                if 'low' in row:
                    day_data['low'] = float(row['low'])
                if 'volume' in row:
                    day_data['volume'] = float(row['volume'])
                if 'pct_chg' in row:
                    day_data['pct_chg'] = float(row['pct_chg'])

                # 技术指标
                if 'MA5' in row:
                    day_data['MA5'] = float(row['MA5'])
                if 'MA10' in row:
                    day_data['MA10'] = float(row['MA10'])
                if 'MA20' in row:
                    day_data['MA20'] = float(row['MA20'])
                if 'BIAS_5' in row:
                    day_data['BIAS_5'] = float(row['BIAS_5'])
                if 'BIAS_10' in row:
                    day_data['BIAS_10'] = float(row['BIAS_10'])
                if 'RSI' in row:
                    day_data['RSI'] = float(row['RSI'])
                if 'MACD' in row:
                    day_data['MACD'] = float(row['MACD'])

                result['qmt']['daily_data'].append(day_data)

# 综合建议（纯数据模式不包含主观判断）
    if not pure_data:
        result['summary'] = {
            'fund_strength': '强势' if fund_stats and fund_stats['bullish_days'] > fund_stats['bearish_days'] else '弱势',
            'tech_strength': None,
            'recommendation': None
        }

        if fund_stats:
            result['summary']['bullish_days'] = fund_stats['bullish_days']
            result['summary']['bearish_days'] = fund_stats['bearish_days']
            result['summary']['total_institution'] = fund_stats['total_institution']
            result['summary']['total_institution_unit'] = f'{days}天累计（万元）'
            result['summary']['total_retail'] = fund_stats['total_retail']
            result['summary']['total_retail_unit'] = f'{days}天累计（万元）'

        if use_qmt and analyzer.qmt_available and qmt_df is not None and not qmt_df.empty:
            if 'close' in qmt_df.columns and 'MA5' in qmt_df.columns:
                result['summary']['tech_strength'] = '强势' if qmt_df['close'].iloc[-1] > qmt_df['MA5'].iloc[-1] else '弱势'

        # 综合建议
        if fund_stats:
            if fund_stats['bearish_days'] > fund_stats['bullish_days'] * 1.5:
                result['summary']['recommendation'] = '建议回避'
            elif fund_stats['bullish_days'] > fund_stats['bearish_days']:
                result['summary']['recommendation'] = '可以考虑低吸'
            else:
                result['summary']['recommendation'] = '谨慎观望'
    else:
        # 纯数据模式：只包含统计数据，不包含主观判断
        result['summary'] = {
            'bullish_days': fund_stats['bullish_days'] if fund_stats else None,
            'bearish_days': fund_stats['bearish_days'] if fund_stats else None,
            'total_institution': fund_stats['total_institution'] if fund_stats else None,
            'total_institution_unit': f'{days}天累计（万元）' if fund_stats else None,
            'total_retail': fund_stats['total_retail'] if fund_stats else None,
            'total_retail_unit': f'{days}天累计（万元）' if fund_stats else None,
            'total_days': fund_stats['total_days'] if fund_stats else None,
        }

        if qmt_df is not None and not qmt_df.empty:
            result['summary']['close'] = float(qmt_df['close'].iloc[-1]) if 'close' in qmt_df.columns else None
            result['summary']['pct_chg'] = float(qmt_df['pct_chg'].iloc[-1]) if 'pct_chg' in qmt_df.columns else None
            result['summary']['RSI'] = float(qmt_df['RSI'].iloc[-1]) if 'RSI' in qmt_df.columns else None
            result['summary']['MACD'] = float(qmt_df['MACD'].iloc[-1]) if 'MACD' in qmt_df.columns else None

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "300997"

    if len(sys.argv) > 2:
        days = int(sys.argv[2])
    else:
        days = 60

    if len(sys.argv) > 3:
        output_all_data = sys.argv[3].lower() == 'true'
    else:
        output_all_data = True

    print(analyze_stock_enhanced(stock_code, days=days, output_all_data=output_all_data))