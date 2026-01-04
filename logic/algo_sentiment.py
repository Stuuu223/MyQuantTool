"""
市场情绪、涨停板、龙虎榜分析模块
基于拾荒网技术文章实现
"""
import pandas as pd
import numpy as np

class MarketSentimentAnalyzer:
    """市场情绪分析器"""
    
    @staticmethod
    def get_market_sentiment_index():
        """
        获取市场情绪指数
        
        指标包括:
        - 涨停数量/跌停数量
        - 连板高度分布
        - 涨停打开率
        - 市场整体情绪评分
        """
        try:
            import akshare as ak
            
            # 获取涨跌停数据
            limit_stocks = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))
            
            if limit_stocks.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日暂无涨跌停数据'
                }
            
            # 统计涨停数据
            zt_count = len(limit_stocks)
            zt_open_count = len(limit_stocks[limit_stocks['涨跌幅'] < 9.9])  # 涨停打开
            zt_open_rate = (zt_open_count / zt_count * 100) if zt_count > 0 else 0
            
            # 统计连板高度
            if '连板数' in limit_stocks.columns:
                board_heights = limit_stocks['连板数'].value_counts().to_dict()
            else:
                board_heights = {}
            
            # 计算情绪指数 (0-100)
            # 涨停数量权重: 30%
            # 连板高度权重: 30%
            # 打开率权重: 20%
            # 涨跌幅权重: 20%
            
            zt_score = min(zt_count / 100 * 30, 30)  # 最多30分
            
            # 连板高度评分
            high_board_count = sum([count for height, count in board_heights.items() if height >= 3])
            board_score = min(high_board_count / 50 * 30, 30)
            
            # 打开率评分 (越低越好)
            open_score = max(30 - zt_open_rate * 0.3, 0)
            
            # 涨跌幅评分
            avg_change = limit_stocks['涨跌幅'].mean()
            change_score = min(avg_change / 10 * 20, 20)
            
            sentiment_score = round(zt_score + board_score + open_score + change_score, 2)
            
            # 情绪等级
            if sentiment_score >= 80:
                sentiment_level = "🔥 极热"
                sentiment_desc = "市场情绪极度亢奋,注意风险"
            elif sentiment_score >= 60:
                sentiment_level = "📈 活跃"
                sentiment_desc = "市场情绪活跃,可以参与"
            elif sentiment_score >= 40:
                sentiment_level = "🟡 一般"
                sentiment_desc = "市场情绪一般,谨慎操作"
            elif sentiment_score >= 20:
                sentiment_level = "📉 情绪低迷"
                sentiment_desc = "市场情绪低迷,观望为主"
            else:
                sentiment_level = "❄️ 冰点"
                sentiment_desc = "市场情绪冰点,机会来临"
            
            return {
                '数据状态': '正常',
                '情绪指数': sentiment_score,
                '情绪等级': sentiment_level,
                '情绪描述': sentiment_desc,
                '涨停数量': zt_count,
                '涨停打开数': zt_open_count,
                '涨停打开率': round(zt_open_rate, 2),
                '连板分布': board_heights,
                '详细数据': limit_stocks
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def analyze_limit_up_stocks():
        """
        涨停板深度分析
        
        分析内容:
        - 封板强度
        - 连板成功率
        - 板块分布
        - 龙头股识别
        """
        try:
            import akshare as ak
            
            # 获取涨停数据
            limit_stocks = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))
            
            if limit_stocks.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日暂无涨跌停数据'
                }
            
            # 分析封板强度
            limit_stocks['封板强度'] = limit_stocks.apply(
                lambda row: MarketSentimentAnalyzer._calculate_sealing_strength(row),
                axis=1
            )
            
            # 识别龙头股
            dragon_stocks = []
            for _, row in limit_stocks.iterrows():
                dragon_analysis = MarketSentimentAnalyzer.analyze_dragon_stock_for_limit_up(row)
                if dragon_analysis['龙头评分'] >= 60:
                    dragon_stocks.append({
                        '代码': row['代码'],
                        '名称': row['名称'],
                        '涨停价': row['最新价'],
                        '涨跌幅': row['涨跌幅'],
                        '封板强度': row['封板强度'],
                        '龙头评分': dragon_analysis['龙头评分'],
                        '龙头评级': dragon_analysis['龙头评级']
                    })
            
            # 按龙头评分排序
            dragon_stocks.sort(key=lambda x: x['龙头评分'], reverse=True)
            
            # 统计板块分布
            if '所属行业' in limit_stocks.columns:
                sector_distribution = limit_stocks['所属行业'].value_counts().head(10).to_dict()
            else:
                sector_distribution = {}
            
            # 统计连板成功率
            if '连板数' in limit_stocks.columns:
                board_stats = limit_stocks.groupby('连板数').size().to_dict()
            else:
                board_stats = {}
            
            return {
                '数据状态': '正常',
                '涨停总数': len(limit_stocks),
                '龙头股': dragon_stocks,
                '板块分布': sector_distribution,
                '连板统计': board_stats,
                '详细数据': limit_stocks
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def _calculate_sealing_strength(row):
        """
        计算封板强度
        
        考虑因素:
        - 涨跌幅 (越接近10%越强)
        - 换手率 (适中最佳)
        - 成交额 (越大越强)
        - 封单量 (如果有的话)
        """
        score = 0
        
        # 涨跌幅评分
        change_pct = row.get('涨跌幅', 0)
        if change_pct >= 9.9:
            score += 30
        elif change_pct >= 9.5:
            score += 25
        elif change_pct >= 9.0:
            score += 20
        else:
            score += 10
        
        # 换手率评分
        turnover = row.get('换手率', 0)
        if 5 <= turnover <= 15:
            score += 30
        elif 2 <= turnover < 5:
            score += 20
        elif 15 < turnover <= 25:
            score += 20
        elif turnover > 25:
            score += 10
        else:
            score += 5
        
        # 成交额评分
        amount = row.get('成交额', 0)
        if amount >= 1000000000:  # 10亿以上
            score += 40
        elif amount >= 500000000:  # 5亿以上
            score += 30
        elif amount >= 200000000:  # 2亿以上
            score += 20
        elif amount >= 100000000:  # 1亿以上
            score += 10
        else:
            score += 5
        
        return score
    
    @staticmethod
    def analyze_dragon_stock_for_limit_up(row):
        """
        针对涨停股的龙头分析
        
        Args:
            row: 涨停股票数据行
        
        Returns:
            龙头分析结果
        """
        score = 0
        reasons = []
        
        # 价格条件 (20分)
        price = row.get('最新价', 0)
        if price <= 10:
            score += 20
            reasons.append("价格低廉")
        elif price <= 15:
            score += 15
            reasons.append("价格适中")
        else:
            score += 5
        
        # 封板强度 (30分)
        strength = MarketSentimentAnalyzer._calculate_sealing_strength(row)
        if strength >= 80:
            score += 30
            reasons.append("封板极强")
        elif strength >= 60:
            score += 25
            reasons.append("封板较强")
        elif strength >= 40:
            score += 15
            reasons.append("封板一般")
        else:
            score += 5
        
        # 连板高度 (30分)
        board_count = row.get('连板数', 1)
        if board_count == 1:
            score += 30
            reasons.append("首板启动")
        elif board_count == 2:
            score += 25
            reasons.append("二板确认")
        elif board_count == 3:
            score += 20
            reasons.append("三板加速")
        elif board_count >= 4:
            score += 10
            reasons.append(f"{board_count}板接力")
        
        # 换手率 (20分)
        turnover = row.get('换手率', 0)
        if 5 <= turnover <= 15:
            score += 20
            reasons.append("换手适中")
        elif 2 <= turnover < 5:
            score += 15
            reasons.append("换手偏低")
        elif 15 < turnover <= 25:
            score += 15
            reasons.append("换手偏高")
        else:
            score += 5
        
        # 评级
        if score >= 80:
            rating = "🔥 强龙头"
        elif score >= 60:
            rating = "📈 潜力龙头"
        elif score >= 40:
            rating = "⚠️ 弱龙头"
        else:
            rating = "❌ 非龙头"
        
        return {
            '龙头评分': score,
            '龙头评级': rating,
            '评分原因': reasons
        }
    
    @staticmethod
    def deep_analyze_lhb():
        """
        深度龙虎榜分析
        
        分析内容:
        - 机构vs游资动向
        - 热门营业部追踪
        - 龙虎榜质量评估
        - 次日表现预测
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            
            # 获取最近7天龙虎榜数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            
            if lhb_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '暂无龙虎榜数据'
                }
            
            # 只取最新数据
            latest_date = lhb_df.iloc[:, 3].max()
            latest_lhb = lhb_df[lhb_df.iloc[:, 3] == latest_date]
            
            # 统计机构vs游资
            institution_net_buy = 0
            hot_seat_net_buy = 0
            
            # 热门营业部列表
            hot_seats = [
                '东方证券股份有限公司上海源深路证券营业部',
                '东方财富证券股份有限公司拉萨团结路第二证券营业部',
                '东方财富证券股份有限公司拉萨东环路第二证券营业部',
                '国泰君安证券股份有限公司上海分公司',
                '华鑫证券有限责任公司上海分公司'
            ]
            
            hot_seat_trades = []
            
            for _, row in latest_lhb.iterrows():
                # 机构净买入
                if '机构' in str(row.iloc[7]):  # 买入营业部
                    institution_net_buy += row.iloc[9]  # 净买入额
                
                # 热门营业部
                for seat in hot_seats:
                    if seat in str(row.iloc[7]):
                        hot_seat_net_buy += row.iloc[9]
                        hot_seat_trades.append({
                            '营业部': seat,
                            '股票代码': row.iloc[1],
                            '股票名称': row.iloc[2],
                            '净买入': row.iloc[9]
                        })
            
            # 龙虎榜质量评估
            from logic.algo import QuantAlgo
            quality_analysis = QuantAlgo.analyze_lhb_quality()
            
            return {
                '数据状态': '正常',
                '数据日期': latest_date,
                '上榜数量': len(latest_lhb),
                '机构净买入': institution_net_buy,
                '热门营业部净买入': hot_seat_net_buy,
                '热门营业部交易': hot_seat_trades,
                '质量分析': quality_analysis
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def analyze_sentiment_cycle():
        """
        分析情绪周期五阶段
        
        基于拾荒网情绪周期理论:
        1. 情绪冰点期: 空间板被压缩至2板
        2. 情绪复苏期: 空间板突破2板,达到3-4板
        3. 情绪活跃期: 空间板达到5-7板,涨停数量增加
        4. 情绪高潮期: 空间板达到7板以上,市场极度活跃
        5. 情绪退潮期: 空间板开始下降,涨停数量减少
        """
        try:
            import akshare as ak
            
            # 获取涨停数据
            limit_stocks = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))
            
            if limit_stocks.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日暂无涨跌停数据'
                }
            
            # 获取连板高度
            if '连板数' in limit_stocks.columns:
                max_board = limit_stocks['连板数'].max()
                board_distribution = limit_stocks['连板数'].value_counts().to_dict()
            else:
                max_board = 0
                board_distribution = {}
            
            # 统计涨停数量
            zt_count = len(limit_stocks)
            
            # 统计涨停打开率
            zt_open_count = len(limit_stocks[limit_stocks['涨跌幅'] < 9.9])
            zt_open_rate = (zt_open_count / zt_count * 100) if zt_count > 0 else 0
            
            # 计算情绪指数
            sentiment_index = MarketSentimentAnalyzer.get_market_sentiment_index()
            
            # 判断情绪周期阶段
            cycle_stage = ""
            stage_desc = ""
            operation_advice = ""
            
            # 判断逻辑
            if max_board <= 2:
                cycle_stage = "❄️ 情绪冰点期"
                stage_desc = "空间板被压缩至2板,市场情绪极度低落"
                operation_advice = "🎯 市场处于冰点,是布局良机,可关注首板和2板股票"
            elif max_board == 3:
                cycle_stage = "🌱 情绪复苏期"
                stage_desc = "空间板突破2板,达到3板,情绪开始复苏"
                operation_advice = "📈 情绪开始复苏,可以参与3板及以下股票"
            elif max_board in [4, 5]:
                cycle_stage = "🔥 情绪活跃期"
                stage_desc = f"空间板达到{max_board}板,涨停数量增多,市场活跃"
                operation_advice = "🚀 市场活跃,可参与中高位接力,注意风险控制"
            elif max_board >= 6:
                cycle_stage = "⚡ 情绪高潮期"
                stage_desc = f"空间板达到{max_board}板,市场极度活跃,需谨慎"
                operation_advice = "⚠️ 市场高潮,注意风险,建议减仓或观望"
            else:
                cycle_stage = "📉 情绪退潮期"
                stage_desc = "空间板开始下降,情绪逐步退潮"
                operation_advice = "🛑 情绪退潮,建议观望为主,等待下一轮周期"
            
            # 补充判断
            if zt_open_rate > 30:
                cycle_stage += " (炸板率高)"
                operation_advice += ",炸板率较高,需谨慎"
            
            return {
                '数据状态': '正常',
                '情绪周期阶段': cycle_stage,
                '阶段描述': stage_desc,
                '操作建议': operation_advice,
                '空间板高度': max_board,
                '涨停数量': zt_count,
                '涨停打开率': round(zt_open_rate, 2),
                '连板分布': board_distribution,
                '情绪指数': sentiment_index.get('情绪指数', 0),
                '情绪等级': sentiment_index.get('情绪等级', ''),
                '详细数据': limit_stocks
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }