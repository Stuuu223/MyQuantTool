"""
高级量化策略模块
包含热点题材挖掘、智能预警、量价关系战法等高级功能
"""

import pandas as pd
import numpy as np
from logic.data_manager import DataManager


class AdvancedAlgo:
    """高级量化策略类"""

    @staticmethod
    def scan_hot_topics(limit=20):
        """
        热点题材挖掘
        检测板块异动、识别龙头股、分析题材持续度
        """
        try:
            import akshare as ak

            # 获取板块数据（添加超时处理）
            try:
                # 获取概念板块数据
                concept_df = ak.stock_board_concept_name_em()
            except Exception as e:
                print(f"获取概念板块失败: {e}")
                concept_df = pd.DataFrame()
            
            try:
                # 获取行业板块数据
                industry_df = ak.stock_board_industry_name_em()
            except Exception as e:
                print(f"获取行业板块失败: {e}")
                industry_df = pd.DataFrame()

            if concept_df.empty and industry_df.empty:
                return {
                    '数据状态': '无法获取板块数据',
                    '说明': '网络连接超时，请稍后再试'
                }

            # 合并概念板块和行业板块
            all_boards = []
            if not concept_df.empty:
                concept_df['板块类型'] = '概念'
                all_boards.append(concept_df)
            if not industry_df.empty:
                industry_df['板块类型'] = '行业'
                all_boards.append(industry_df)
            
            if not all_boards:
                return {
                    '数据状态': '无法获取板块数据',
                    '说明': '网络连接超时，请稍后再试'
                }
            
            # 合并所有板块
            combined_df = pd.concat(all_boards, ignore_index=True)

            # 过滤掉没有参考价值的板块（昨日涨停、昨日连板等）
            exclude_keywords = ['昨日涨停', '昨日连板', '含一字']
            combined_df = combined_df[~combined_df['板块名称'].str.contains('|'.join(exclude_keywords), na=False)]

            # 计算综合得分
            # 主要看涨跌幅和换手率，降低上涨家数的权重
            # 标准化上涨家数（除以100），避免数值差异过大
            combined_df['综合得分'] = (
                combined_df['涨跌幅'] * 0.6 +
                (combined_df['上涨家数'] / 100) * 0.2 +
                combined_df['换手率'] * 0.2
            )

            # 统一排序，取前limit个最热的板块
            hot_boards = combined_df.nlargest(limit, '综合得分')

            # 识别每个板块的龙头股
            db = DataManager()
            topic_leaders = {}

            # 获取昨日涨停和连板股票列表
            yesterday_limit_up_stocks = set()
            try:
                # 获取昨日涨停数据
                yesterday = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime('%Y%m%d')
                limit_up_df = ak.stock_zt_pool_em(date=yesterday)
                if not limit_up_df.empty:
                    # 获取连板数大于等于1的股票（即昨日已经涨停的）
                    if '代码' in limit_up_df.columns:
                        yesterday_limit_up_stocks = set(limit_up_df['代码'].tolist())
            except:
                pass  # 如果获取失败，继续执行

            # 添加板块基本信息（不获取成分股，提高扫描速度）
            for _, row in hot_boards.iterrows():
                board_name = row['板块名称']
                topic_leaders[board_name] = {
                    '板块类型': row['板块类型'],
                    '涨跌幅': row['涨跌幅'],
                    '涨家数': row['上涨家数'],
                    '跌家数': row['下跌家数'],
                    '量比': row['换手率'],
                    '龙头股': []  # 初始为空，用户点击"分析题材持续度"时再获取
                }

            db.close()

            # 按涨跌幅排序
            sorted_topics = sorted(
                topic_leaders.items(),
                key=lambda x: x[1]['涨跌幅'],
                reverse=True
            )

            return {
                '数据状态': '正常',
                '热点题材': dict(sorted_topics),
                '扫描板块数': len(hot_boards)
            }

        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def analyze_topic_continuity(topic_name, days=30):
        """
        分析题材持续度
        返回题材的历史表现和持续性分析
        """
        try:
            import akshare as ak
            from functools import lru_cache

            db = DataManager()

            # 获取板块历史数据
            topic_df = None
            
            # 首先尝试获取概念板块历史数据
            try:
                concept_boards = ak.stock_board_concept_name_em()
                if not concept_boards.empty and '板块名称' in concept_boards.columns:
                    # 尝试精确匹配或模糊匹配
                    matched_board = concept_boards[concept_boards['板块名称'].str.contains(topic_name, na=False)]
                    if not matched_board.empty:
                        # 使用找到的板块名称
                        actual_board_name = matched_board.iloc[0]['板块名称']
                        topic_df = ak.stock_board_concept_hist_em(
                            symbol=actual_board_name,
                            period="daily",
                            start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp.now().strftime("%Y%m%d")
                        )
                        print(f"使用概念板块: {actual_board_name}")
                    else:
                        print(f"未在概念板块中找到: {topic_name}")
            except Exception as e:
                print(f"获取概念板块历史数据失败: {e}")

            # 如果概念板块未找到，尝试行业板块
            if topic_df is None or topic_df.empty:
                try:
                    industry_boards = ak.stock_board_industry_name_em()
                    if not industry_boards.empty and '板块名称' in industry_boards.columns:
                        # 尝试精确匹配或模糊匹配
                        matched_board = industry_boards[industry_boards['板块名称'].str.contains(topic_name, na=False)]
                        if not matched_board.empty:
                            # 使用找到的板块名称
                            actual_board_name = matched_board.iloc[0]['板块名称']
                            topic_df = ak.stock_board_industry_hist_em(
                                symbol=actual_board_name,
                                period="daily",
                                start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                                end_date=pd.Timestamp.now().strftime("%Y%m%d")
                            )
                            print(f"使用行业板块: {actual_board_name}")
                        else:
                            print(f"未在行业板块中找到: {topic_name}")
                except Exception as e:
                    print(f"获取行业板块历史数据失败: {e}")

            # 如果仍然没有数据，尝试更宽松的匹配
            if topic_df is None or topic_df.empty:
                try:
                    # 再次尝试概念板块，使用更宽松的匹配
                    concept_boards = ak.stock_board_concept_name_em()
                    if not concept_boards.empty and '板块名称' in concept_boards.columns:
                        # 查找包含相似名称的板块
                        for idx, row in concept_boards.iterrows():
                            if topic_name.lower() in row['板块名称'].lower() or \
                               row['板块名称'].lower() in topic_name.lower():
                                actual_board_name = row['板块名称']
                                topic_df = ak.stock_board_concept_hist_em(
                                    symbol=actual_board_name,
                                    period="daily",
                                    start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                                    end_date=pd.Timestamp.now().strftime("%Y%m%d")
                                )
                                print(f"使用相似概念板块: {actual_board_name}")
                                break
                except Exception as e:
                    print(f"宽松匹配概念板块失败: {e}")

            # 如果仍然没有数据，尝试行业板块的宽松匹配
            if topic_df is None or topic_df.empty:
                try:
                    industry_boards = ak.stock_board_industry_name_em()
                    if not industry_boards.empty and '板块名称' in industry_boards.columns:
                        # 查找包含相似名称的板块
                        for idx, row in industry_boards.iterrows():
                            if topic_name.lower() in row['板块名称'].lower() or \
                               row['板块名称'].lower() in topic_name.lower():
                                actual_board_name = row['板块名称']
                                topic_df = ak.stock_board_industry_hist_em(
                                    symbol=actual_board_name,
                                    period="daily",
                                    start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                                    end_date=pd.Timestamp.now().strftime("%Y%m%d")
                                )
                                print(f"使用相似行业板块: {actual_board_name}")
                                break
                except Exception as e:
                    print(f"宽松匹配行业板块失败: {e}")

            # 如果还是找不到数据，返回错误信息
            if topic_df is None or topic_df.empty:
                return {
                    '数据状态': '无法获取板块历史数据',
                    '说明': f'可能是数据源限制、板块名称错误（尝试搜索："船舶制造", "船舶", "军工船舶"等）'
                }

            # 计算持续度指标
            avg_change = topic_df['涨跌幅'].mean()
            max_change = topic_df['涨跌幅'].max()
            min_change = topic_df['涨跌幅'].min()
            positive_days = (topic_df['涨跌幅'] > 0).sum()
            total_days = len(topic_df)

            # 计算波动率
            volatility = topic_df['涨跌幅'].std()

            # 计算趋势强度
            if len(topic_df) >= 5:
                recent_5_avg = topic_df['涨跌幅'].tail(5).mean()
                trend_strength = recent_5_avg - avg_change
            else:
                trend_strength = 0

            # 判断题材阶段
            if trend_strength > 2 and positive_days / total_days > 0.6:
                stage = "上升期"
                suggestion = "题材强势，积极参与"
            elif trend_strength > 0 and positive_days / total_days > 0.5:
                stage = "活跃期"
                suggestion = "题材活跃，关注龙头"
            elif trend_strength < -2 and positive_days / total_days < 0.4:
                stage = "衰退期"
                suggestion = "题材衰退，谨慎参与"
            else:
                stage = "震荡期"
                suggestion = "题材震荡，观望为主"

            # 获取板块成分股和龙头股
            dragon_stocks = []
            try:
                # 获取板块成分股
                stocks_df = None
                try:
                    stocks_df = ak.stock_board_concept_cons_em(symbol=actual_board_name)
                except:
                    try:
                        stocks_df = ak.stock_board_industry_cons_em(symbol=actual_board_name)
                    except:
                        pass

                if stocks_df is not None and not stocks_df.empty and '代码' in stocks_df.columns:
                    # 只选择涨幅为正的股票（不过滤昨日涨停和连板）
                    positive_stocks = stocks_df[stocks_df['涨跌幅'] > 0]

                    if not positive_stocks.empty:
                        # 计算龙头得分
                        positive_stocks['龙头得分'] = (
                            positive_stocks['涨跌幅'] * 0.5 +
                            (positive_stocks['成交额'] / (positive_stocks['成交额'].mean() + 1e-6)) * 0.3 +
                            positive_stocks['换手率'] * 0.2
                        )

                        # 取前5只龙头股
                        leaders = positive_stocks.nlargest(5, '龙头得分')
                        dragon_stocks = leaders.to_dict('records')
            except Exception as e:
                print(f"获取龙头股失败: {e}")

            db.close()

            return {
                '数据状态': '正常',
                '平均涨跌幅': round(avg_change, 2),
                '最大涨幅': round(max_change, 2),
                '最大跌幅': round(min_change, 2),
                '上涨天数': positive_days,
                '总天数': total_days,
                '上涨概率': round(positive_days / total_days * 100, 1),
                '波动率': round(volatility, 2),
                '趋势强度': round(trend_strength, 2),
                '当前阶段': stage,
                '操作建议': suggestion,
                '龙头股': dragon_stocks,
                '实际板块名称': actual_board_name  # 添加实际使用的板块名称
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def detect_volume_price_signals(df):
        """
        量价关系战法
        检测缩量回调、放量突破、背离信号
        """
        try:
            if len(df) < 20:
                return {
                    '数据状态': '数据不足',
                    '说明': '需要至少20天数据'
                }

            signals = []

            # 1. 检测缩量回调（买入信号）
            # 条件：价格在上升趋势中，成交量萎缩
            ma5 = df['close'].rolling(5).mean()
            ma10 = df['close'].rolling(10).mean()
            ma20 = df['close'].rolling(20).mean()
            ma5_vol = df['volume'].rolling(5).mean()

            # 判断上升趋势
            is_uptrend = (ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1])

            # 判断缩量回调
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2]
            current_vol = df['volume'].iloc[-1]
            avg_vol = ma5_vol.iloc[-1]

            price_decline = (prev_price - current_price) / prev_price
            volume_shrink = (avg_vol - current_vol) / avg_vol

            if is_uptrend and 0.01 < price_decline < 0.05 and volume_shrink > 0.3:
                signals.append({
                    '信号类型': '缩量回调',
                    '信号强度': '强',
                    '操作建议': '买入',
                    '说明': f'上升趋势中缩量回调{price_decline*100:.2f}%，成交量萎缩{volume_shrink*100:.1f}%，是良好的买入时机'
                })

            # 2. 检测放量突破（买入信号）
            # 条件：价格突破关键压力位，成交量放大
            resistance = df['high'].rolling(20).max().iloc[-2]  # 20日最高价作为压力位
            volume_ratio = current_vol / df['volume'].rolling(20).mean().iloc[-1]

            if current_price > resistance and volume_ratio > 2:
                signals.append({
                    '信号类型': '放量突破',
                    '信号强度': '强',
                    '操作建议': '买入',
                    '说明': f'放量突破{resistance:.2f}压力位，量比{volume_ratio:.2f}，确认突破有效'
                })

            # 3. 检测顶背离（卖出信号）
            # 条件：价格创新高，但指标未创新高
            if len(df) >= 10:
                # 计算MACD
                exp1 = df['close'].ewm(span=12, adjust=False).mean()
                exp2 = df['close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2

                # 检查价格和MACD的相对位置
                recent_high_price = df['close'].tail(10).max()
                recent_high_macd = macd.tail(10).max()
                prev_high_price = df['close'].iloc[-20:-10].max()
                prev_high_macd = macd.iloc[-20:-10].max()

                if recent_high_price > prev_high_price and recent_high_macd < prev_high_macd:
                    signals.append({
                        '信号类型': '顶背离',
                        '信号强度': '中',
                        '操作建议': '卖出',
                        '说明': '价格创新高但MACD未创新高，出现顶背离信号，注意风险'
                    })

            # 4. 检测底背离（买入信号）
            # 条件：价格创新低，但指标未创新低
            if len(df) >= 10:
                recent_low_price = df['close'].tail(10).min()
                recent_low_macd = macd.tail(10).min()
                prev_low_price = df['close'].iloc[-20:-10].min()
                prev_low_macd = macd.iloc[-20:-10].min()

                if recent_low_price < prev_low_price and recent_low_macd > prev_low_macd:
                    signals.append({
                        '信号类型': '底背离',
                        '信号强度': '中',
                        '操作建议': '买入',
                        '说明': '价格创新低但MACD未创新低，出现底背离信号，可能反弹'
                    })

            return {
                '数据状态': '正常',
                '信号数量': len(signals),
                '信号列表': signals
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def analyze_moving_average(df, short=5, medium=10, long=20):
        """
        均线战法
        分析均线多头排列、金叉死叉、支撑压力
        """
        try:
            if len(df) < long:
                return {
                    '数据状态': '数据不足',
                    '说明': f'需要至少{long}天数据'
                }

            # 计算均线
            ma_short = df['close'].rolling(short).mean()
            ma_medium = df['close'].rolling(medium).mean()
            ma_long = df['close'].rolling(long).mean()

            signals = []

            # 1. 检测均线多头排列
            is_bullish = (ma_short.iloc[-1] > ma_medium.iloc[-1] > ma_long.iloc[-1])

            if is_bullish:
                signals.append({
                    '信号类型': '均线多头排列',
                    '信号强度': '强',
                    '操作建议': '持有',
                    '说明': f'{short}日、{medium}日、{long}日均线呈多头排列，趋势向上'
                })

            # 2. 检测金叉（短期均线上穿长期均线）
            if len(df) >= 2:
                # 短期与中期金叉
                if ma_short.iloc[-2] < ma_medium.iloc[-2] and ma_short.iloc[-1] > ma_medium.iloc[-1]:
                    signals.append({
                        '信号类型': f'{short}日均线金叉{medium}日均线',
                        '信号强度': '强',
                        '操作建议': '买入',
                        '说明': f'{short}日均线上穿{medium}日均线，金叉信号'
                    })

                # 中期与长期金叉
                if ma_medium.iloc[-2] < ma_long.iloc[-2] and ma_medium.iloc[-1] > ma_long.iloc[-1]:
                    signals.append({
                        '信号类型': f'{medium}日均线金叉{long}日均线',
                        '信号强度': '强',
                        '操作建议': '买入',
                        '说明': f'{medium}日均线上穿{long}日均线，金叉信号'
                    })

            # 3. 检测死叉（短期均线下穿长期均线）
            if len(df) >= 2:
                # 短期与中期死叉
                if ma_short.iloc[-2] > ma_medium.iloc[-2] and ma_short.iloc[-1] < ma_medium.iloc[-1]:
                    signals.append({
                        '信号类型': f'{short}日均线死叉{medium}日均线',
                        '信号强度': '强',
                        '操作建议': '卖出',
                        '说明': f'{5}日均线下穿{10}日均线，死叉信号'
                    })

                # 中期与长期死叉
                if ma_medium.iloc[-2] > ma_long.iloc[-2] and ma_medium.iloc[-1] < ma_long.iloc[-1]:
                    signals.append({
                        '信号类型': f'{medium}日均线死叉{long}日均线',
                        '信号强度': '强',
                        '操作建议': '卖出',
                        '说明': f'{medium}日均线下穿{long}日均线，死叉信号'
                    })

            # 4. 均线支撑压力
            current_price = df['close'].iloc[-1]

            # 计算价格与均线的距离
            support = ma_long.iloc[-1]
            resistance = ma_short.iloc[-1]

            if current_price > ma_short.iloc[-1]:
                signals.append({
                    '信号类型': '均线压力',
                    '信号强度': '中',
                    '操作建议': '观望',
                    '说明': f'价格在{short}日均线之上，短期均线可能形成压力'
                })
            elif current_price < ma_long.iloc[-1]:
                signals.append({
                    '信号类型': '均线支撑',
                    '信号强度': '中',
                    '操作建议': '关注',
                    '说明': f'价格在{long}日均线之下，长期均线可能形成支撑'
                })

            return {
                '数据状态': '正常',
                '信号数量': len(signals),
                '信号列表': signals,
                'MA5': round(ma_short.iloc[-1], 2),
                'MA10': round(ma_medium.iloc[-1], 2),
                'MA20': round(ma_long.iloc[-1], 2)
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def analyze_new_stock(df, symbol, listing_date=None):
        """
        次新股战法
        分析开板次新股、情绪周期、换手率
        """
        try:
            import akshare as ak

            if len(df) < 10:
                return {
                    '数据状态': '数据不足',
                    '说明': '需要至少10天数据'
                }

            signals = []

            # 获取股票基本信息
            try:
                stock_info = ak.stock_individual_info_em(symbol=symbol)
                if not stock_info.empty:
                    info_dict = dict(zip(stock_info['item'], stock_info['value']))
                    listing_date = info_dict.get('上市日期', '')
            except:
                pass

            # 计算上市天数
            if listing_date:
                try:
                    days_since_listing = (pd.Timestamp.now() - pd.Timestamp(listing_date)).days
                except:
                    days_since_listing = 999
            else:
                days_since_listing = 999

            # 判断是否为次新股（上市180天内）
            is_new_stock = days_since_listing < 180

            if not is_new_stock:
                return {
                    '数据状态': '非次新股',
                    '说明': f'该股票已上市{days_since_listing}天，不属于次新股'
                }

            # 1. 检测开板信号
            # 次新股开板后换手率通常会大幅放大
            turnover_rates = df['volume'] / df['volume'].rolling(5).mean()

            if len(turnover_rates) >= 5:
                recent_turnover = turnover_rates.tail(5).mean()
                avg_turnover = turnover_rates.iloc[:-5].mean()

                if recent_turnover > avg_turnover * 3:
                    signals.append({
                        '信号类型': '开板信号',
                        '信号强度': '强',
                        '操作建议': '观望',
                        '说明': f'换手率大幅放大，可能刚开板，建议观察几天再决定'
                    })

            # 2. 分析情绪周期
            # 次新股通常经历：开板-调整-反弹-分化
            if days_since_listing < 30:
                stage = "开板期"
                suggestion = "刚开板，波动大，建议观望"
            elif days_since_listing < 60:
                stage = "调整期"
                suggestion = "调整阶段，可关注低吸机会"
            elif days_since_listing < 120:
                stage = "反弹期"
                suggestion = "反弹阶段，关注强势股"
            else:
                stage = "分化期"
                suggestion = "分化阶段，精选个股"

            # 3. 换手率分析
            current_turnover = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]

            if current_turnover > 5:
                signals.append({
                    '信号类型': '换手率过高',
                    '信号强度': '中',
                    '操作建议': '谨慎',
                    '说明': f'换手率过高（{current_turnover:.2f}倍），可能存在风险'
                })
            elif current_turnover > 3:
                signals.append({
                    '信号类型': '换手率活跃',
                    '信号强度': '中',
                    '操作建议': '关注',
                    '说明': f'换手率活跃（{current_turnover:.2f}倍），资金参与度高'
                })

            return {
                '数据状态': '正常',
                '上市天数': days_since_listing,
                '当前阶段': stage,
                '操作建议': suggestion,
                '信号数量': len(signals),
                '信号列表': signals
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

class AdvancedPatternAnalyzer:
    """高级形态分析器"""

    @staticmethod
    def detect_fanbao_pattern(df, symbol):
        """
        识别反包形态
        反包形态：股票昨日跌停或大跌，今日涨停或大涨，形成反包
        """
        try:
            signals = []

            if len(df) < 5:
                return signals

            for i in range(1, len(df)):
                today = df.iloc[i]
                yesterday = df.iloc[i - 1]

                # 昨日大跌（跌幅超过5%）
                if yesterday['close'] < yesterday['open'] * 0.95:
                    # 今日大涨（涨幅超过5%）
                    if today['close'] > today['open'] * 1.05:
                        # 今日收盘价超过昨日开盘价（反包）
                        if today['close'] > yesterday['open']:
                            signals.append({
                                '反包日期': df.index[i],
                                '昨日跌幅': round((yesterday['close'] - yesterday['open']) / yesterday['open'] * 100, 2),
                                '今日涨幅': round((today['close'] - today['open']) / today['open'] * 100, 2),
                                '反包强度': round((today['close'] - yesterday['open']) / yesterday['open'] * 100, 2)
                            })

            return signals

        except Exception as e:
            print(f"识别反包形态失败: {e}")
            return []

    @staticmethod
    def predict_fanbao_future(df, fanbao_date):
        """
        预测反包后的走势
        """
        try:
            # 找到反包日的索引
            fanbao_idx = df.index.get_loc(fanbao_date)

            if fanbao_idx + 3 >= len(df):
                return {
                    '预测': '数据不足',
                    '评分': 0,
                    '建议': '数据不足，无法预测'
                }

            # 查看反包后3天的表现
            next_3_days = df.iloc[fanbao_idx + 1:fanbao_idx + 4]

            # 计算平均涨跌幅
            avg_change = next_3_days['close'].pct_change().mean() * 100

            # 评分
            if avg_change > 3:
                prediction = '强势上涨'
                score = 80
                suggestion = '反包后表现强势，可以继续持有'
            elif avg_change > 0:
                prediction = '温和上涨'
                score = 60
                suggestion = '反包后表现良好，可以适量参与'
            elif avg_change > -3:
                prediction = '震荡整理'
                score = 40
                suggestion = '反包后震荡整理，建议观望'
            else:
                prediction = '弱势下跌'
                score = 20
                suggestion = '反包后表现不佳，建议减仓'

            return {
                '预测': prediction,
                '评分': score,
                '建议': suggestion
            }

        except Exception as e:
            print(f"预测反包走势失败: {e}")
            return {
                '预测': '预测失败',
                '评分': 0,
                '建议': '预测失败，请稍后再试'
            }

    @staticmethod
    def monitor_sector_rotation():
        """
        监控板块轮动
        分析板块资金流向、热度排名
        """
        try:
            import akshare as ak

            # 获取概念板块数据
            concept_df = ak.stock_board_concept_name_em()

            if concept_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '无法获取板块数据'
                }

            # 计算热度评分（涨跌幅 + 换手率）
            concept_df['热度评分'] = (
                concept_df['涨跌幅'] * 0.6 +
                concept_df['换手率'] * 0.4
            )

            # 排序
            concept_df = concept_df.sort_values('热度评分', ascending=False)

            # 热门板块（前10）
            hot_sectors = concept_df.head(10).to_dict('records')

            # 冷门板块（后10）
            cold_sectors = concept_df.tail(10).to_dict('records')

            # 最强板块
            strongest = hot_sectors[0] if hot_sectors else None

            return {
                '数据状态': '正常',
                '最强板块': strongest,
                '热门板块': hot_sectors,
                '冷门板块': cold_sectors
            }

        except Exception as e:
            return {
                '数据状态': '监控失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def track_sector_leaders(sector_name):
        """
        追踪板块龙头股
        """
        try:
            import akshare as ak

            # 获取板块成分股
            sector_df = ak.stock_board_concept_cons_em(symbol=sector_name)

            if sector_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': f'无法获取板块 {sector_name} 的成分股'
                }

            # 计算龙头得分
            sector_df['龙头得分'] = (
                sector_df['涨跌幅'] * 0.5 +
                sector_df['成交额'] / sector_df['成交额'].mean() * 0.3 +
                sector_df['换手率'] * 0.2
            )

            # 排序
            leaders = sector_df.nlargest(5, '龙头得分')

            return {
                '数据状态': '正常',
                '龙头股': leaders.to_dict('records')
            }

        except Exception as e:
            return {
                '数据状态': '追踪失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def analyze_board_height():
        """
        分析连板高度
        统计不同连板数的股票数量和胜率
        """
        try:
            import akshare as ak

            # 获取涨停数据
            limit_up_df = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))

            if limit_up_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日无涨停数据'
                }

            # 统计连板高度
            if '连板数' in limit_up_df.columns:
                board_stats = limit_up_df['连板数'].value_counts().sort_index()

                # 计算胜率（简化版本，实际需要历史数据）
                board_df = pd.DataFrame({
                    '股票数量': board_stats,
                    '胜率': [50.0] * len(board_stats)  # 简化处理，实际需要计算历史胜率
                })
            else:
                board_df = pd.DataFrame()

            return {
                '数据状态': '正常',
                '连板统计': board_df,
                '涨停总数': len(limit_up_df)
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
