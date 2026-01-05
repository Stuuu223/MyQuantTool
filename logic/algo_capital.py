"""
游资席位分析模块
分析龙虎榜游资、追踪操作模式、识别知名游�?"""

import pandas as pd
from logic.data_manager import DataManager


class CapitalAnalyzer:
    """游资席位分析模块""

    # 知名游资席位列表（包含常见变体）
    FAMOUS_CAPITALISTS = {
        "章盟主 [
            "中信证券股份有限公司杭州延安路证券营业部",
            "国泰君安证券股份有限公司上海江苏路证券营业部",
            "国泰君安证券股份有限公司上海分公�?,
            "国泰君安证券股份有限公司上海江苏�?,
            "中信证券杭州延安�?,
            "国泰君安上海江苏�?
        ],
        "方新�?: [
            "兴业证券股份有限公司陕西分公�?,
            "中信证券股份有限公司西安朱雀大街证券营业�?,
            "兴业证券陕西分公�?,
            "中信证券西安朱雀大街",
            "兴业证券股份有限公司陕西"
        ],
        "徐翔": [
            "国泰君安证券股份有限公司上海福山路证券营业部",
            "光大证券股份有限公司宁波解放南路证券营业�?,
            "国泰君安上海福山�?,
            "光大证券宁波解放南路",
            "国泰君安上海福山路证�?
        ],
        "赵老哥": [
            "中国银河证券股份有限公司绍兴证券营业�?,
            "华泰证券股份有限公司浙江分公�?,
            "银河证券绍兴",
            "华泰证券浙江分公�?,
            "中国银河证券绍兴"
        ],
        "乔帮�?: [
            "中信证券股份有限公司上海淮海中路证券营业�?,
            "国泰君安证券股份有限公司上海分公�?,
            "中信证券上海淮海中路",
            "国泰君安上海分公�?
        ],
        "成都�?: [
            "华泰证券股份有限公司成都蜀金路证券营业�?,
            "国泰君安证券股份有限公司成都北一环路证券营业�?,
            "华泰证券成都蜀金路",
            "国泰君安成都北一环路",
            "华泰证券成都"
        ],
        "佛山�?: [
            "光大证券股份有限公司佛山绿景路证券营业部",
            "长江证券股份有限公司佛山顺德新宁路证券营业部",
            "光大证券佛山绿景�?,
            "长江证券佛山顺德新宁�?,
            "光大证券佛山"
        ],
        "瑞鹤�?: [
            "中国中金财富证券有限公司深圳分公�?,
            "华泰证券股份有限公司深圳益田路荣超商务中心证券营业部",
            "中金财富深圳",
            "华泰证券深圳益田�?,
            "中国中金财富深圳"
        ],
        "作手新一": [
            "国泰君安证券股份有限公司南京太平南路证券营业�?,
            "华泰证券股份有限公司南京江东中路证券营业�?,
            "国泰君安南京太平南路",
            "华泰证券南京江东中路",
            "国泰君安南京"
        ],
        "小鳄�?: [
            "中国银河证券股份有限公司北京中关村大街证券营业部",
            "中信证券股份有限公司北京总部证券营业�?,
            "银河证券北京中关村大�?,
            "中信证券北京总部",
            "银河证券北京"
        ]
    }

    @staticmethod
    def analyze_longhubu_capital(date=None):
        """
        分析龙虎榜游�?        返回当日龙虎榜中的游资席位分�?        """
        try:
            import akshare as ak
            from datetime import datetime

            # 获取龙虎榜数�?            try:
                if date:
                    if isinstance(date, str):
                        date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")
                    lhb_df = ak.stock_lhb_detail_em(date=date_str)
                    print(f"获取 {date_str} 的龙虎榜数据，共 {len(lhb_df)} 条记�?)
                else:
                    # 获取最近几天的数据
                    today = datetime.now()
                    lhb_df = ak.stock_lhb_detail_em(date=today.strftime("%Y%m%d"))
                    print(f"获取今日龙虎榜数据，�?{len(lhb_df)} 条记�?)
                    
                    # 如果今日无数据，尝试获取昨天�?                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        lhb_df = ak.stock_lhb_detail_em(date=yesterday.strftime("%Y%m%d"))
                        print(f"今日无数据，获取昨日龙虎榜数据，�?{len(lhb_df)} 条记�?)
            except Exception as e:
                print(f"获取龙虎榜数据失�? {e}")
                return {
                    '数据状�?: '获取龙虎榜数据失�?,
                    '错误信息': str(e),
                    '说明': '可能是网络问题或数据源限制，请稍后重�?
                }

            if lhb_df is None or lhb_df.empty:
                print("龙虎榜数据为�?)
                return {
                    '数据状�?: '无数�?,
                    '说明': '暂无龙虎榜数据，可能今日无龙虎榜或数据未更新。建议选择其他日期查看�?
                }
            
            # 打印列名，帮助调�?            print(f"龙虎榜数据列�? {lhb_df.columns.tolist()}")
            print(f"�?条数据示�?\n{lhb_df.head(3)}")

            # 分析游资席位
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            # 打印所有营业部名称，帮助调�?            unique_seats = lhb_df['营业部名�?].unique()
            print(f"共找�?{len(unique_seats)} 个不同的营业�?)
            print(f"营业部列�? {unique_seats[:10]}...")  # 只打印前10�?
            for _, row in lhb_df.iterrows():
                seat_name = str(row['营业部名�?])
                
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
                            '日期': row['上榜�?],
                            '买入金额': row['买入金额'],
                            '卖出金额': row['卖出金额'],
                            '净买入': row['买入金额'] - row['卖出金额']
                        }
                        capital_stats[capital_name]['操作股票'].append(stock_info)

                        capital_analysis.append({
                            '游资名称': capital_name,
                            '营业部名�?: row['营业部名�?],
                            '股票代码': row['代码'],
                            '股票名称': row['名称'],
                            '上榜�?: row['上榜�?],
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
                    style = "激进买�?
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖�?
                elif net_flow > 0:
                    style = "偏多�?
                else:
                    style = "偏空�?

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次�?: total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票�?: len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            print(f"分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游�?)

            return {
                '数据状�?: '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录�?: matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(lhb_df),
                '说明': f'�?{len(lhb_df)} 条龙虎榜记录中，找到 {matched_count} 条游资操作记�?
            }

            return {
                '数据状�?: '正常',
                '游资分析列表': capital_analysis,
                '游资统计汇�?: capital_summary,
                '活跃游资�?: len(capital_stats),
                '总操作次�?: len(capital_analysis)
            }

        except Exception as e:
            return {
                '数据状�?: '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限�?
            }

    @staticmethod
    def track_capital_pattern(capital_name, days=30):
        """
        追踪游资操作模式
        分析特定游资在指定时间内的操作规�?        """
        try:
            import akshare as ak

            if capital_name not in CapitalAnalyzer.FAMOUS_CAPITALISTS:
                return {
                    '数据状�?: '未知游资',
                    '说明': f'未找到游�? {capital_name}'
                }

            # 获取该游资的席位列表
            seats = CapitalAnalyzer.FAMOUS_CAPITALISTS[capital_name]
            print(f"游资 {capital_name} 的席位列�? {seats}")

            # 获取历史龙虎榜数�?            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []
            checked_dates = 0
            matched_dates = 0

            # 获取每日龙虎榜数�?            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                checked_dates += 1

                try:
                    lhb_df = ak.stock_lhb_detail_em(date=date_str)

                    if not lhb_df.empty:
                        print(f"{date_str}: 获取�?{len(lhb_df)} 条龙虎榜记录")
                        
                        # 筛选该游资的操作（使用模糊匹配�?                        for _, row in lhb_df.iterrows():
                            seat_name = str(row['营业部名�?])
                            
                            # 精确匹配或模糊匹�?                            if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                matched_dates += 1
                                all_operations.append({
                                    '日期': row['上榜�?],
                                    '股票代码': row['代码'],
                                    '股票名称': row['名称'],
                                    '买入金额': row.get('买入金额', 0),
                                    '卖出金额': row.get('卖出金额', 0),
                                    '净买入': row.get('买入金额', 0) - row.get('卖出金额', 0),
                                    '营业部名�?: seat_name
                                })
                                print(f"  匹配�? {seat_name} - {row['名称']}({row['代码']})")
                except Exception as e:
                    print(f"{date_str}: 获取数据失败 - {e}")
                    pass

                current_date += pd.Timedelta(days=1)

            print(f"检查了 {checked_dates} 天，�?{matched_dates} 天找到操作记录，�?{len(all_operations)} 条操�?)

            # 如果没有操作记录，显示所有找到的营业部名�?            if not all_operations:
                # 获取最近几天的龙虎榜数据，收集所有营业部名称
                found_seats = []
                sample_date = start_date
                
                for _ in range(min(5, days)):  # 最多检�?�?                    date_str = sample_date.strftime("%Y%m%d")
                    try:
                        lhb_df = ak.stock_lhb_detail_em(date=date_str)
                        if not lhb_df.empty:
                            all_seats = lhb_df['营业部名�?].unique()
                            found_seats.extend(all_seats)
                            print(f"{date_str}: 找到 {len(all_seats)} 个营业部")
                            if len(found_seats) >= 50:  # 收集足够多的营业�?                                break
                    except:
                        pass
                    sample_date += pd.Timedelta(days=1)
                
                # 去重并排�?                found_seats = sorted(list(set(found_seats)))
                
                return {
                    '数据状�?: '无操作记�?,
                    '说明': f'{capital_name} 在最�?{days} 天内无操作记录。可能原因：1) 该游资近期未上榜 2) 席位名称不匹�?3) 数据源限制。请查看下方调试信息中的实际营业部名称进行对比�?,
                    '检查天�?: checked_dates,
                    '匹配天数': matched_dates,
                    '游资席位': seats,
                    '实际营业�?: found_seats[:30]  # 只返回前30�?                }

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
                        # 计算操作�?天的涨跌�?                        op_price = df.iloc[0]['close']
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
                style = "均衡操作�?

            return {
                '数据状�?: '正常',
                '游资名称': capital_name,
                '分析天数': days,
                '操作次数': len(all_operations),
                '操作频率': round(operation_frequency, 2),
                '总买入金�?: total_buy,
                '总卖出金�?: total_sell,
                '买入比例': round(buy_ratio * 100, 1),
                '平均操作金额': round(avg_operation_amount, 0),
                '操作成功�?: round(success_rate, 1),
                '操作风格': style,
                '操作记录': all_operations
            }

        except Exception as e:
            return {
                '数据状�?: '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限�?
            }

    @staticmethod
    def predict_capital_next_move(capital_name):
        """
        预测游资下一步操�?        基于历史操作模式预测
        """
        try:
            # 获取游资操作模式
            pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=30)

            if pattern_result['数据状�?] != '正常':
                return pattern_result

            # 获取最近操�?            recent_operations = pattern_result['操作记录'][-5:]  # 最�?次操�?
            # 分析最近操作倾向
            recent_buy = sum(op['买入金额'] for op in recent_operations)
            recent_sell = sum(op['卖出金额'] for op in recent_operations)

            # 预测
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '预测类型': '继续买入',
                    '概率': '�?,
                    '说明': f'{capital_name} 最近大幅买入，可能继续加仓'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '预测类型': '继续卖出',
                    '概率': '�?,
                    '说明': f'{capital_name} 最近大幅卖出，可能继续减仓'
                })
            else:
                predictions.append({
                    '预测类型': '观望或小幅操�?,
                    '概率': '�?,
                    '说明': f'{capital_name} 最近操作均衡，可能观望'
                })

            # 根据成功率预�?            if pattern_result['操作成功�?] > 60:
                predictions.append({
                    '预测类型': '关注其操�?,
                    '概率': '�?,
                    '说明': f'{capital_name} 历史成功率高，建议关注其操作'
                })

            return {
                '数据状�?: '正常',
                '游资名称': capital_name,
                '预测列表': predictions
            }

        except Exception as e:
            return {
                '数据状�?: '预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问�?
            }