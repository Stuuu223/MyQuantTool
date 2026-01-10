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
            
            # 计算封板强度（封单金额/成交额）
            if '封单金额' in limit_stocks.columns and '成交额' in limit_stocks.columns:
                # 计算平均封板强度
                # 封板强度 = 封单金额 / 成交额
                # >100% 说明封单金额超过成交额，资金抢筹意愿强
                seal_strength = (limit_stocks['封单金额'] / limit_stocks['成交额']).mean()
                zt_seal_strength = round(seal_strength * 100, 2)  # 转换为百分比
            else:
                # 如果没有封单数据，使用涨跌幅作为替代
                avg_change = limit_stocks['涨跌幅'].mean()
                zt_seal_strength = round(avg_change / 10 * 100, 2)  # 粗略估计
            
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
            
            # 打开率评分 (封板强度越高越好，转换为评分)
            # 封板强度 > 0.5 为强，0.3-0.5 为中，<0.3 为弱
            if 'zt_seal_strength' in locals():
                seal_strength_value = zt_seal_strength / 100
                open_score = min(seal_strength_value * 60, 30)  # 最多30分
            else:
                open_score = 15  # 默认中等
            
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
                '封板强度': zt_seal_strength,
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
                        '龙头评级': dragon_analysis['龙头评级'],
                        '成交额': row.get('成交额', 0),
                        '换手率': row.get('换手率', 0)
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
        
        补充判断:
        - 热点形成期: 少量涨停板,资金还未聚焦
        - 热点发展期: 出现连板股,有高标出现
        - 热点高潮期: 龙头成为市场高标,打出示范效应
        - 热点衰退期: 龙头断板,后排集中派面
        
        周期延续判断:
        - 新龙头卡位: 旧龙头断板,新龙头无缝衔接
        - 周期延伸: 旧龙头未退潮,出现更高空间板
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
            
            # 统计不同板数
            board_2_count = board_distribution.get(2, 0)
            board_3_4_count = sum([board_distribution.get(i, 0) for i in [3, 4]])
            board_5_7_count = sum([board_distribution.get(i, 0) for i in [5, 6, 7]])
            board_7plus_count = sum([board_distribution.get(i, 0) for i in range(8, 100)])
            
            # 计算情绪指数
            sentiment_index = MarketSentimentAnalyzer.get_market_sentiment_index()
            
            # 判断情绪周期阶段
            cycle_stage = ""
            stage_desc = ""
            operation_advice = ""
            cycle_features = []
            
            # 判断逻辑(更精确的判断)
            # 1. 情绪冰点期判断
            if max_board <= 2:
                cycle_stage = "❄️ 情绪冰点期"
                stage_desc = "空间板被压缩至2板,市场情绪极度低落"
                operation_advice = "🎯 市场处于冰点,是布局良机,可关注首板和2板股票"
                cycle_features.append("空间板高度: 2板")
                cycle_features.append(f"2板数量: {board_2_count}只")
                
                # 特殊情况:如果有高位一字板(公告利好),排除后判断
                high_limit = [stock for _, stock in limit_stocks.iterrows() 
                             if stock['连板数'] > 2 and stock['涨跌幅'] >= 9.9]
                if high_limit:
                    cycle_features.append(f"⚠️ 存在{len(high_limit)}只高位一字板(公告利好,不计入周期)")
            
            # 2. 情绪复苏期判断
            elif max_board == 3:
                cycle_stage = "🌱 情绪复苏期"
                stage_desc = "空间板突破2板,达到3板,情绪开始复苏"
                operation_advice = "📈 情绪开始复苏,可以参与3板及以下股票"
                cycle_features.append("空间板高度: 3板")
                cycle_features.append(f"3板数量: {board_distribution.get(3, 0)}只")
                cycle_features.append(f"2板数量: {board_2_count}只")
            
            # 3. 情绪活跃期判断
            elif max_board in [4, 5, 6]:
                if zt_count >= 30 and board_3_4_count >= 5:
                    cycle_stage = "🔥 热点发展期"
                    stage_desc = f"空间板达到{max_board}板,出现连板股,有高标出现"
                    operation_advice = "🚀 热点在发展期,可以关注龙一龙二"
                    cycle_features.append("热点阶段: 发展期")
                else:
                    cycle_stage = "🔥 情绪活跃期"
                    stage_desc = f"空间板达到{max_board}板,涨停数量增多,市场活跃"
                    operation_advice = "🚀 市场活跃,可参与中高位接力,注意风险控制"
                
                cycle_features.append(f"空间板高度: {max_board}板")
                cycle_features.append(f"涨停数量: {zt_count}只")
                cycle_features.append(f"3-4板数量: {board_3_4_count}只")
                cycle_features.append(f"5-7板数量: {board_5_7_count}只")
            
            # 4. 情绪高潮期判断
            elif max_board >= 7:
                if zt_count >= 50 and board_5_7_count >= 10:
                    cycle_stage = "⚡ 热点高潮期"
                    stage_desc = f"空间板达到{max_board}板,龙头成为市场高标,打出示范效应"
                    operation_advice = "⚠️ 热点高潮,各路资金聚焦,板块梯队完整,注意最后一棒风险"
                    cycle_features.append("热点阶段: 高潮期")
                    cycle_features.append("板块梯队: 完整")
                    cycle_features.append("跟风小弟: 众多且活跃")
                else:
                    cycle_stage = "⚡ 情绪高潮期"
                    stage_desc = f"空间板达到{max_board}板,市场极度活跃,需谨慎"
                    operation_advice = "⚠️ 市场高潮,注意风险,建议减仓或观望"
                
                cycle_features.append(f"空间板高度: {max_board}板")
                cycle_features.append(f"涨停数量: {zt_count}只")
                cycle_features.append(f"7板以上: {board_7plus_count}只")
            
            # 5. 情绪退潮期判断
            else:
                cycle_stage = "📉 热点衰退期"
                stage_desc = "龙头高标开始断板,后排开始集中派面"
                operation_advice = "🛑 热点衰退,板块亏钱效应放大,建议观望"
                cycle_features.append("龙头状态: 断板")
                cycle_features.append("后排状态: 集中派面")
                cycle_features.append("亏钱效应: 放大")
            
            # 补充判断
            if zt_open_rate > 30:
                cycle_stage += " (炸板率高)"
                operation_advice += ",炸板率较高,需谨慎"
                cycle_features.append(f"⚠️ 炸板率: {zt_open_rate:.1f}%")
            
            if zt_count < 20:
                cycle_features.append(f"⚠️ 涨停数量偏少: {zt_count}只")
            
            # 判断是否有周期延续迹象
            if max_board >= 5 and zt_count >= 40:
                cycle_features.append("💡 可能存在周期延续,观察是否有新龙头卡位")
            
            return {
                '数据状态': '正常',
                '情绪周期阶段': cycle_stage,
                '阶段描述': stage_desc,
                '操作建议': operation_advice,
                '周期特征': cycle_features,
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