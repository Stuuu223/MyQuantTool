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

            # 获取板块数据
            try:
                # 获取概念板块数据
                concept_df = ak.stock_board_concept_name_em()
                industry_df = ak.stock_board_industry_name_em()
            except:
                return {
                    '数据状态': '无法获取板块数据',
                    '说明': '可能是数据源限制'
                }

            # 分析概念板块异动
            hot_concepts = []
            if not concept_df.empty:
                # 筛选涨幅较大、成交量放大的板块
                concept_df['综合得分'] = (
                    concept_df['涨跌幅'] * 0.5 +
                    concept_df['涨家数'] * 0.3 +
                    concept_df['量比'] * 0.2
                )
                hot_concepts = concept_df.nlargest(limit, '综合得分')

            # 分析行业板块异动
            hot_industries = []
            if not industry_df.empty:
                industry_df['综合得分'] = (
                    industry_df['涨跌幅'] * 0.5 +
                    industry_df['涨家数'] * 0.3 +
                    industry_df['量比'] * 0.2
                )
                hot_industries = industry_df.nlargest(limit, '综合得分')

            # 识别每个板块的龙头股
            db = DataManager()
            topic_leaders = {}

            # 分析概念板块龙头
            for _, row in hot_concepts.iterrows():
                concept_name = row['板块名称']
                try:
                    # 获取板块成分股
                    concept_stocks = ak.stock_board_concept_cons_em(symbol=row['板块代码'])

                    if not concept_stocks.empty:
                        # 筛选出强势股（涨幅大、成交量大）
                        concept_stocks['龙头得分'] = (
                            concept_stocks['涨跌幅'] * 0.4 +
                            concept_stocks['最新价'] / concept_stocks['昨收'] * 0.3 +
                            concept_stocks['成交额'] / concept_stocks['成交额'].mean() * 0.3
                        )

                        # 取前3只作为龙头
                        top_stocks = concept_stocks.nlargest(3, '龙头得分')

                        topic_leaders[concept_name] = {
                            '板块类型': '概念',
                            '涨跌幅': row['涨跌幅'],
                            '涨家数': row['涨家数'],
                            '跌家数': row['跌家数'],
                            '量比': row['量比'],
                            '龙头股': [
                                {
                                    '代码': s['代码'],
                                    '名称': s['名称'],
                                    '涨跌幅': s['涨跌幅'],
                                    '最新价': s['最新价'],
                                    '成交额': s['成交额']
                                }
                                for _, s in top_stocks.iterrows()
                            ]
                        }
                except Exception as e:
                    print(f"分析板块 {concept_name} 失败: {e}")
                    continue

            # 分析行业板块龙头
            for _, row in hot_industries.iterrows():
                industry_name = row['板块名称']
                try:
                    # 获取板块成分股
                    industry_stocks = ak.stock_board_industry_cons_em(symbol=row['板块代码'])

                    if not industry_stocks.empty:
                        # 筛选出强势股
                        industry_stocks['龙头得分'] = (
                            industry_stocks['涨跌幅'] * 0.4 +
                            industry_stocks['最新价'] / industry_stocks['昨收'] * 0.3 +
                            industry_stocks['成交额'] / industry_stocks['成交额'].mean() * 0.3
                        )

                        # 取前3只作为龙头
                        top_stocks = industry_stocks.nlargest(3, '龙头得分')

                        topic_leaders[industry_name] = {
                            '板块类型': '行业',
                            '涨跌幅': row['涨跌幅'],
                            '涨家数': row['涨家数'],
                            '跌家数': row['跌家数'],
                            '量比': row['量比'],
                            '龙头股': [
                                {
                                    '代码': s['代码'],
                                    '名称': s['名称'],
                                    '涨跌幅': s['涨跌幅'],
                                    '最新价': s['最新价'],
                                    '成交额': s['成交额']
                                }
                                for _, s in top_stocks.iterrows()
                            ]
                        }
                except Exception as e:
                    print(f"分析板块 {industry_name} 失败: {e}")
                    continue

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
                '概念板块数': len(hot_concepts),
                '行业板块数': len(hot_industries)
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

            db = DataManager()

            # 获取板块历史数据
            try:
                # 尝试获取概念板块历史数据
                topic_df = ak.stock_board_concept_hist_em(
                    symbol=topic_name,
                    period="daily",
                    start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                    end_date=pd.Timestamp.now().strftime("%Y%m%d")
                )
            except:
                try:
                    # 尝试获取行业板块历史数据
                    topic_df = ak.stock_board_industry_hist_em(
                        symbol=topic_name,
                        period="daily",
                        start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y%m%d"),
                        end_date=pd.Timestamp.now().strftime("%Y%m%d")
                    )
                except:
                    return {
                        '数据状态': '无法获取板块历史数据',
                        '说明': '可能是数据源限制或板块名称错误'
                    }

            if topic_df.empty:
                return {
                    '数据状态': '无历史数据',
                    '说明': '该板块可能刚上市或数据不足'
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
                '操作建议': suggestion
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