"""
智能推荐系统
根据市场行情自动推荐相关战法
"""

import pandas as pd
from datetime import datetime
from logic.data_providers.data_manager import DataManager


class SmartRecommender:
    """智能推荐器"""

    @staticmethod
    def analyze_market_condition():
        """
        分析市场整体情况

        Returns:
            市场情况分析结果
        """
        try:
            import akshare as ak

            # 获取市场数据
            market_df = ak.stock_zh_a_spot_em()

            if market_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制'
                }

            # 计算市场指标
            total_stocks = len(market_df)
            up_stocks = len(market_df[market_df['涨跌幅'] > 0])
            down_stocks = len(market_df[market_df['涨跌幅'] < 0])
            limit_up_stocks = len(market_df[market_df['涨跌幅'] >= 9.9])
            limit_down_stocks = len(market_df[market_df['涨跌幅'] <= -9.9])

            # 计算涨跌比
            up_down_ratio = up_stocks / down_stocks if down_stocks > 0 else float('inf')

            # 计算平均涨跌幅
            avg_change = market_df['涨跌幅'].mean()

            # 判断市场情绪
            if up_down_ratio > 3 and avg_change > 1:
                market_sentiment = "强势"
                sentiment_desc = "市场强势上涨，多头占优"
            elif up_down_ratio > 1.5 and avg_change > 0:
                market_sentiment = "偏强"
                sentiment_desc = "市场偏强，多方主导"
            elif up_down_ratio < 0.5 and avg_change < -1:
                market_sentiment = "弱势"
                sentiment_desc = "市场弱势下跌，空头占优"
            elif up_down_ratio < 1 and avg_change < 0:
                market_sentiment = "偏弱"
                sentiment_desc = "市场偏弱，空方主导"
            else:
                market_sentiment = "震荡"
                sentiment_desc = "市场震荡整理，多空平衡"

            return {
                '数据状态': '正常',
                '总股票数': total_stocks,
                '上涨股票': up_stocks,
                '下跌股票': down_stocks,
                '涨停股票': limit_up_stocks,
                '跌停股票': limit_down_stocks,
                '涨跌比': round(up_down_ratio, 2),
                '平均涨跌幅': round(avg_change, 2),
                '市场情绪': market_sentiment,
                '情绪描述': sentiment_desc
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def recommend_strategies(market_condition):
        """
        根据市场情况推荐战法

        Args:
            market_condition: 市场情况分析结果

        Returns:
            推荐的战法列表
        """
        if market_condition['数据状态'] != '正常':
            return {
                '推荐数量': 0,
                '推荐列表': []
            }

        recommendations = []
        sentiment = market_condition['市场情绪']
        limit_up_count = market_condition['涨停股票']
        up_down_ratio = market_condition['涨跌比']

        # 根据市场情绪推荐战法
        if sentiment == "强势":
            recommendations.append({
                '战法名称': '龙头战法',
                '推荐理由': '市场强势上涨，龙头股表现突出',
                '适用场景': '追涨龙头',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '集合竞价战法',
                '推荐理由': '市场强势，竞价阶段容易出现强势股',
                '适用场景': '竞价选股',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '打板战法',
                '推荐理由': '涨停数量多，打板成功率较高',
                '适用场景': '打板追涨',
                '优先级': '中'
            })

        elif sentiment == "偏强":
            recommendations.append({
                '战法名称': '热点题材挖掘',
                '推荐理由': '市场偏强，题材股活跃',
                '适用场景': '跟踪热点',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '量价关系战法',
                '推荐理由': '市场偏强，量价关系信号可靠',
                '适用场景': '量价分析',
                '优先级': '中'
            })

        elif sentiment == "弱势":
            recommendations.append({
                '战法名称': '智能预警系统',
                '推荐理由': '市场弱势，建议设置预警等待机会',
                '适用场景': '等待机会',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '游资席位分析',
                '推荐理由': '市场弱势，关注游资动向寻找机会',
                '适用场景': '跟随游资',
                '优先级': '中'
            })

        elif sentiment == "偏弱":
            recommendations.append({
                '战法名称': '均线战法',
                '推荐理由': '市场偏弱，均线支撑位可能提供买点',
                '适用场景': '低吸反弹',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '次新股战法',
                '推荐理由': '市场偏弱，次新股可能独立行情',
                '适用场景': '关注次新',
                '优先级': '中'
            })

        else:  # 震荡
            recommendations.append({
                '战法名称': '量价关系战法',
                '推荐理由': '市场震荡，量价关系信号较为可靠',
                '适用场景': '量价分析',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '均线战法',
                '推荐理由': '市场震荡，均线支撑压力位有效',
                '适用场景': '高抛低吸',
                '优先级': '高'
            })
            recommendations.append({
                '战法名称': '智能预警系统',
                '推荐理由': '市场震荡，设置预警等待突破',
                '适用场景': '等待突破',
                '优先级': '中'
            })

        # 根据涨停数量推荐
        if limit_up_count > 50:
            recommendations.append({
                '战法名称': '打板成功率预测',
                '推荐理由': f'今日涨停{limit_up_count}只，市场活跃，可评估打板机会',
                '适用场景': '打板分析',
                '优先级': '高'
            })

        # 根据涨跌比推荐
        if up_down_ratio > 2:
            recommendations.append({
                '战法名称': '情绪分析',
                '推荐理由': '涨跌比较高，市场情绪较好，可分析情绪周期',
                '适用场景': '情绪跟踪',
                '优先级': '中'
            })

        # 按优先级排序
        priority_order = {'高': 0, '中': 1, '低': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['优先级'], 3))

        return {
            '推荐数量': len(recommendations),
            '推荐列表': recommendations
        }

    @staticmethod
    def generate_daily_report():
        """
        生成每日报告

        Returns:
            每日报告内容
        """
        # 分析市场情况
        market_condition = SmartRecommender.analyze_market_condition()

        if market_condition['数据状态'] != '正常':
            return {
                '数据状态': '无法生成报告',
                '说明': '无法获取市场数据'
            }

        # 推荐战法
        strategy_recommendations = SmartRecommender.recommend_strategies(market_condition)

        # 生成报告
        report = {
            '日期': datetime.now().strftime("%Y-%m-%d"),
            '市场情绪': market_condition['市场情绪'],
            '情绪描述': market_condition['情绪描述'],
            '市场数据': {
                '涨跌比': market_condition['涨跌比'],
                '平均涨跌幅': f"{market_condition['平均涨跌幅']}%",
                '涨停数': market_condition['涨停股票'],
                '跌停数': market_condition['跌停股票']
            },
            '推荐战法': strategy_recommendations['推荐列表'],
            '操作建议': SmartRecommender._generate_operation_advice(market_condition)
        }

        return report

    @staticmethod
    def _generate_operation_advice(market_condition):
        """
        生成操作建议

        Args:
            market_condition: 市场情况

        Returns:
            操作建议
        """
        sentiment = market_condition['市场情绪']
        avg_change = market_condition['平均涨跌幅']

        if sentiment == "强势":
            return "市场强势上涨，建议积极参与，关注龙头股和热点题材，注意控制仓位"
        elif sentiment == "偏强":
            return "市场偏强，可以适当参与，关注量价关系和题材轮动，保持谨慎乐观"
        elif sentiment == "弱势":
            return "市场弱势下跌，建议观望为主，设置预警等待机会，严格控制仓位"
        elif sentiment == "偏弱":
            return "市场偏弱，建议谨慎操作，关注均线支撑位，等待市场企稳"
        else:  # 震荡
            return "市场震荡整理，建议高抛低吸，关注量价关系和关键位置，控制风险"