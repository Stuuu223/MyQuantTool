"""
游资席位分析模块
分析龙虎榜游资、追踪操作模式、识别知名游资
"""

import pandas as pd
from logic.data_manager import DataManager


class CapitalAnalyzer:
    """游资席位分析器"""

    # 知名游资席位列表
    FAMOUS_CAPITALISTS = {
        "章盟主": ["中信证券股份有限公司杭州延安路证券营业部", "国泰君安证券股份有限公司上海江苏路证券营业部"],
        "方新侠": ["兴业证券股份有限公司陕西分公司", "中信证券股份有限公司西安朱雀大街证券营业部"],
        "徐翔": ["国泰君安证券股份有限公司上海福山路证券营业部", "光大证券股份有限公司宁波解放南路证券营业部"],
        "赵老哥": ["中国银河证券股份有限公司绍兴证券营业部", "华泰证券股份有限公司浙江分公司"],
        "乔帮主": ["中信证券股份有限公司上海淮海中路证券营业部", "国泰君安证券股份有限公司上海分公司"],
        "成都帮": ["华泰证券股份有限公司成都蜀金路证券营业部", "国泰君安证券股份有限公司成都北一环路证券营业部"],
        "佛山帮": ["光大证券股份有限公司佛山绿景路证券营业部", "长江证券股份有限公司佛山顺德新宁路证券营业部"],
        "瑞鹤仙": ["中国中金财富证券有限公司深圳分公司", "华泰证券股份有限公司深圳益田路荣超商务中心证券营业部"],
        "作手新一": ["国泰君安证券股份有限公司南京太平南路证券营业部", "华泰证券股份有限公司南京江东中路证券营业部"],
        "小鳄鱼": ["中国银河证券股份有限公司北京中关村大街证券营业部", "中信证券股份有限公司北京总部证券营业部"]
    }

    @staticmethod
    def analyze_longhubu_capital(date=None):
        """
        分析龙虎榜游资
        返回当日龙虎榜中的游资席位分析
        """
        try:
            import akshare as ak
            from datetime import datetime

            # 获取龙虎榜数据
            try:
                if date:
                    if isinstance(date, str):
                        date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")
                    lhb_df = ak.stock_lhb_detail_daily_em(date=date_str)
                    print(f"获取 {date_str} 的龙虎榜数据，共 {len(lhb_df)} 条记录")
                else:
                    # 获取最近几天的数据
                    today = datetime.now()
                    lhb_df = ak.stock_lhb_detail_daily_em(date=today.strftime("%Y%m%d"))
                    print(f"获取今日龙虎榜数据，共 {len(lhb_df)} 条记录")
                    
                    # 如果今日无数据，尝试获取昨天的
                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        lhb_df = ak.stock_lhb_detail_daily_em(date=yesterday.strftime("%Y%m%d"))
                        print(f"今日无数据，获取昨日龙虎榜数据，共 {len(lhb_df)} 条记录")
            except Exception as e:
                print(f"获取龙虎榜数据失败: {e}")
                return {
                    '数据状态': '获取龙虎榜数据失败',
                    '错误信息': str(e),
                    '说明': '可能是网络问题或数据源限制，请稍后重试'
                }

            if lhb_df is None or lhb_df.empty:
                print("龙虎榜数据为空")
                return {
                    '数据状态': '无数据',
                    '说明': '暂无龙虎榜数据，可能今日无龙虎榜或数据未更新。建议选择其他日期查看。'
                }
            
            # 打印列名，帮助调试
            print(f"龙虎榜数据列名: {lhb_df.columns.tolist()}")
            print(f"前3条数据示例:\n{lhb_df.head(3)}")

            # 分析游资席位
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            # 打印所有营业部名称，帮助调试
            unique_seats = lhb_df['营业部名称'].unique()
            print(f"共找到 {len(unique_seats)} 个不同的营业部")
            print(f"营业部列表: {unique_seats[:10]}...")  # 只打印前10个

            for _, row in lhb_df.iterrows():
                seat_name = str(row['营业部名称'])
                
                # 检查是否为知名游资席位（使用模糊匹配）
                for capital_name, seats in CapitalAnalyzer.FAMOUS_CAPITALISTS.items():
                    # 精确匹配
                    if seat_name in seats:
                        matched = True
                    # 模糊匹配：检查是否包含关键词
                    else:
                        matched = any(keyword in seat_name for keyword in seats)
                    
                    if matched:
                        matched_count += 1
                        # 统计游资操作
                        if capital_name not in capital_stats:
                            capital_stats[capital_name] = {
                                '买入次数': 0,
                                '卖出次数': 0,
                                '买入金额': 0,
                                '卖出金额': 0,
                                '操作股票': []
                            }

                        # 判断买卖方向
                        buy_amount = row.get('买入金额', 0)
                        sell_amount = row.get('卖出金额', 0)
                        
                        if buy_amount > 0:
                            capital_stats[capital_name]['买入次数'] += 1
                            capital_stats[capital_name]['买入金额'] += buy_amount
                        elif row['卖出金额'] > 0:
                            capital_stats[capital_name]['卖出次数'] += 1
                            capital_stats[capital_name]['卖出金额'] += row['卖出金额']

                        # 记录操作股票
                        stock_info = {
                            '代码': row['代码'],
                            '名称': row['名称'],
                            '日期': row['上榜日'],
                            '买入金额': row['买入金额'],
                            '卖出金额': row['卖出金额'],
                            '净买入': row['买入金额'] - row['卖出金额']
                        }
                        capital_stats[capital_name]['操作股票'].append(stock_info)

                        capital_analysis.append({
                            '游资名称': capital_name,
                            '营业部名称': row['营业部名称'],
                            '股票代码': row['代码'],
                            '股票名称': row['名称'],
                            '上榜日': row['上榜日'],
                            '买入金额': row['买入金额'],
                            '卖出金额': row['卖出金额'],
                            '净买入': row['买入金额'] - row['卖出金额']
                        })

            # 计算游资统计
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['买入金额'] - stats['卖出金额']
                total_trades = stats['买入次数'] + stats['卖出次数']

                # 判断操作风格
                if stats['买入金额'] > stats['卖出金额'] * 2:
                    style = "激进买入"
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖出"
                elif net_flow > 0:
                    style = "偏多头"
                else:
                    style = "偏空头"

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次数': total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票数': len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            print(f"分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游资")

            return {
                '数据状态': '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录数': matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(lhb_df),
                '说明': f'在 {len(lhb_df)} 条龙虎榜记录中，找到 {matched_count} 条游资操作记录'
            }

            return {
                '数据状态': '正常',
                '游资分析列表': capital_analysis,
                '游资统计汇总': capital_summary,
                '活跃游资数': len(capital_stats),
                '总操作次数': len(capital_analysis)
            }

        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def track_capital_pattern(capital_name, days=30):
        """
        追踪游资操作模式
        分析特定游资在指定时间内的操作规律
        """
        try:
            import akshare as ak

            if capital_name not in CapitalAnalyzer.FAMOUS_CAPITALISTS:
                return {
                    '数据状态': '未知游资',
                    '说明': f'未找到游资: {capital_name}'
                }

            # 获取该游资的席位列表
            seats = CapitalAnalyzer.FAMOUS_CAPITALISTS[capital_name]

            # 获取历史龙虎榜数据
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []

            # 获取每日龙虎榜数据
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")

                try:
                    lhb_df = ak.stock_lhb_detail_daily_em(date=date_str)

                    if not lhb_df.empty:
                        # 筛选该游资的操作
                        for _, row in lhb_df.iterrows():
                            if row['营业部名称'] in seats:
                                all_operations.append({
                                    '日期': row['上榜日'],
                                    '股票代码': row['代码'],
                                    '股票名称': row['名称'],
                                    '买入金额': row['买入金额'],
                                    '卖出金额': row['卖出金额'],
                                    '净买入': row['买入金额'] - row['卖出金额']
                                })
                except:
                    pass

                current_date += pd.Timedelta(days=1)

            if not all_operations:
                return {
                    '数据状态': '无操作记录',
                    '说明': f'{capital_name} 在最近 {days} 天内无操作记录'
                }

            # 分析操作模式
            df_ops = pd.DataFrame(all_operations)

            # 1. 操作频率
            operation_frequency = len(all_operations) / days

            # 2. 买卖偏好
            total_buy = df_ops['买入金额'].sum()
            total_sell = df_ops['卖出金额'].sum()
            buy_ratio = total_buy / (total_buy + total_sell) if (total_buy + total_sell) > 0 else 0

            # 3. 单次操作金额
            avg_operation_amount = df_ops['净买入'].abs().mean()

            # 4. 操作成功率（后续3天涨跌）
            success_count = 0
            total_count = 0

            db = DataManager()
            for op in all_operations:
                try:
                    symbol = op['股票代码']
                    op_date = op['日期']

                    # 获取历史数据
                    start_date_str = op_date
                    end_date_str = (pd.Timestamp(op_date) + pd.Timedelta(days=5)).strftime("%Y%m%d")

                    df = db.get_history_data(symbol, start_date=start_date_str, end_date=end_date_str)

                    if not df.empty and len(df) > 3:
                        # 计算操作后3天的涨跌幅
                        op_price = df.iloc[0]['close']
                        future_price = df.iloc[3]['close']
                        future_return = (future_price - op_price) / op_price * 100

                        if future_return > 0:
                            success_count += 1
                        total_count += 1
                except:
                    pass

            db.close()

            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            # 5. 判断操作风格
            if buy_ratio > 0.7:
                style = "激进买入型"
            elif buy_ratio < 0.3:
                style = "激进卖出型"
            elif avg_operation_amount > 50000000:
                style = "大资金操作型"
            else:
                style = "均衡操作型"

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '分析天数': days,
                '操作次数': len(all_operations),
                '操作频率': round(operation_frequency, 2),
                '总买入金额': total_buy,
                '总卖出金额': total_sell,
                '买入比例': round(buy_ratio * 100, 1),
                '平均操作金额': round(avg_operation_amount, 0),
                '操作成功率': round(success_rate, 1),
                '操作风格': style,
                '操作记录': all_operations
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def predict_capital_next_move(capital_name):
        """
        预测游资下一步操作
        基于历史操作模式预测
        """
        try:
            # 获取游资操作模式
            pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=30)

            if pattern_result['数据状态'] != '正常':
                return pattern_result

            # 获取最近操作
            recent_operations = pattern_result['操作记录'][-5:]  # 最近5次操作

            # 分析最近操作倾向
            recent_buy = sum(op['买入金额'] for op in recent_operations)
            recent_sell = sum(op['卖出金额'] for op in recent_operations)

            # 预测
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '预测类型': '继续买入',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大幅买入，可能继续加仓'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '预测类型': '继续卖出',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大幅卖出，可能继续减仓'
                })
            else:
                predictions.append({
                    '预测类型': '观望或小幅操作',
                    '概率': '中',
                    '说明': f'{capital_name} 最近操作均衡，可能观望'
                })

            # 根据成功率预测
            if pattern_result['操作成功率'] > 60:
                predictions.append({
                    '预测类型': '关注其操作',
                    '概率': '高',
                    '说明': f'{capital_name} 历史成功率高，建议关注其操作'
                })

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '预测列表': predictions
            }

        except Exception as e:
            return {
                '数据状态': '预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }