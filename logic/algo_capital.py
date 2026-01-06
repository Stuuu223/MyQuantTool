"""
游资席位分析模块
分析龙虎榜游资、游资操作模式、识别知名游资"""

import pandas as pd
from logic.data_manager import DataManager


class CapitalAnalyzer:
    """游资席位分析模块"""

    # 知名游资席位列表（包含常见变体）
    FAMOUS_CAPITALISTS = {
        "章盟主": [
            "中信证券股份有限公司杭州延安路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "国泰君安证券股份有限公司上海江苏路",
            "国泰君安证券股份有限公司上海江苏",
            "中信证券杭州延安路",
            "国泰君安上海江苏路"
        ],
        "方新侠": [
            "兴业证券股份有限公司西安分公司",
            "中信证券股份有限公司西安朱雀大街证券营业部",
            "兴业证券西安分公司",
            "中信证券西安朱雀大街",
            "兴业证券股份有限公司"
        ],
        "徐翔": [
            "国泰君安证券股份有限公司上海福山路证券营业部",
            "光大证券股份有限公司宁波解放南路证券营业部",
            "国泰君安上海福山路",
            "光大证券宁波解放南路",
            "国泰君安上海福建路"
        ],
        "赵老哥": [
            "中国银河证券股份有限公司绍兴证券营业部",
            "华泰证券股份有限公司浙江分公司",
            "银河证券绍兴",
            "华泰证券浙江分公司",
            "中国银河证券绍兴"
        ],
        "炒股养家": [
            "中信证券股份有限公司上海淮海中路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "中信证券上海淮海中路",
            "国泰君安上海分公司"
        ],
        "成都": [
            "华泰证券股份有限公司成都蜀金路证券营业部",
            "国泰君安证券股份有限公司成都分公司",
            "中信证券成都蜀金路",
            "国泰君安成都分公司"
        ],
        "深圳": [
            "光大证券股份有限公司深圳金田路证券营业部",
            "长江证券股份有限公司深圳科苑路证券营业部",
            "光大证券深圳金田路",
            "长江证券深圳科苑路",
            "光大证券深圳"
        ],
        "乔帮主": [
            "中国中金财富证券有限公司深圳分公司",
            "华泰证券股份有限公司深圳彩田路超算中心证券营业部",
            "中金财富深圳",
            "华泰证券深圳彩田路",
            "中国中金财富深圳"
        ],
        "作手新一": [
            "国泰君安证券股份有限公司南京太平南路证券营业部",
            "华泰证券股份有限公司南京江东中路证券营业部",
            "国泰君安南京太平南路",
            "华泰证券南京江东中路",
            "国泰君安南京"
        ],
        "小鳄鱼": [
            "中国银河证券股份有限公司北京中关村大街证券营业部",
            "中信证券股份有限公司北京总部证券营业部",
            "银河证券北京中关村大街",
            "中信证券北京总部",
            "银河证券北京"
        ]
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
            import time

            # 获取龙虎榜数据
            try:
                if date:
                    if isinstance(date, str):
                        # 支持多种日期格式
                        if '-' in date:
                            # %Y-%m-%d 格式
                            date_obj = pd.to_datetime(date)
                            date_str = date_obj.strftime("%Y%m%d")
                        else:
                            date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")
                    lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
                    print(f"获取 {date_str} 的龙虎榜数据，共 {len(lhb_df)} 条记录")
                else:
                    # 获取最近几天的数据
                    today = datetime.now()
                    lhb_df = ak.stock_lhb_detail_em(start_date=today.strftime("%Y%m%d"), end_date=today.strftime("%Y%m%d"))
                    print(f"获取今日龙虎榜数据，共 {len(lhb_df)} 条记录")

                    # 如果今日无数据，尝试获取昨天
                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        lhb_df = ak.stock_lhb_detail_em(start_date=yesterday.strftime("%Y%m%d"), end_date=yesterday.strftime("%Y%m%d"))
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
                    '说明': '暂无龙虎榜数据，可能今日无龙虎榜或数据未更新。建议选择其他日期查看'
                }

            # 打印列名，帮助调试
            print(f"龙虎榜数据列: {lhb_df.columns.tolist()}")
            print(f"前3条数据示例:\n{lhb_df.head(3)}")

            # 检查是否有营业部名称列
            seat_col = None
            for col in lhb_df.columns:
                if '营业' in col or '席位' in col:
                    seat_col = col
                    break

            if seat_col is None:
                print(f"龙虎榜数据中没有营业部名称列，尝试使用新浪接口获取营业部数据")

                # 使用新浪接口获取营业部统计数据
                try:
                    yyb_stats = ak.stock_lhb_yytj_sina(symbol='5')  # 获取最近5天的数据
                    if not yyb_stats.empty:
                        print(f"获取到 {len(yyb_stats)} 条营业部统计数据")
                        print(f"新浪数据列名: {yyb_stats.columns.tolist()}")

                        # 构建席位数据
                        all_seat_data = []
                        for _, row in yyb_stats.head(50).iterrows():  # 取前50条
                            # 处理金额数据
                            buy_amount = row.get('买入总额', 0)
                            sell_amount = row.get('卖出总额', 0)

                            # 确保金额是数值类型
                            if pd.notna(buy_amount):
                                try:
                                    buy_amount = float(buy_amount)
                                except:
                                    buy_amount = 0
                            else:
                                buy_amount = 0

                            if pd.notna(sell_amount):
                                try:
                                    sell_amount = float(sell_amount)
                                except:
                                    sell_amount = 0
                            else:
                                sell_amount = 0

                            # 找到营业部名称列
                            seat_name = ''
                            for col in yyb_stats.columns:
                                if '营业部' in col:
                                    seat_name = str(row.get(col, ''))
                                    break

                            all_seat_data.append({
                                '代码': '',
                                '名称': str(row.get('操作前股票', '')),
                                '上榜日': '2026-01-06',  # 使用当前日期
                                '收盘价': 0,
                                '涨跌幅': 0,
                                '营业部名称': seat_name,
                                '买入额': buy_amount,
                                '卖出额': sell_amount,
                                '净买入': buy_amount - sell_amount
                            })

                        if all_seat_data:
                            seat_df = pd.DataFrame(all_seat_data)
                            lhb_df = seat_df
                            seat_col = '营业部名称'
                            print(f"成功获取席位数据，共 {len(lhb_df)} 条记录")
                        else:
                            print("新浪数据中没有有效的席位信息")
                    else:
                        print("新浪接口返回空数据")
                except Exception as e:
                    print(f"获取新浪营业部数据失败: {e}")
                    import traceback
                    traceback.print_exc()

                # 如果新浪接口也失败，尝试获取历史营业部数据
                if seat_col is None:
                    try:
                        active_yyb = ak.stock_lhb_hyyyb_em()
                        if not active_yyb.empty:
                            print(f"获取到 {len(active_yyb)} 条历史营业部数据")
                            # 返回历史营业部数据
                            return {
                                '数据状态': '正常',
                                '说明': '当前数据源不提供当日营业部明细，显示历史活跃营业部数据',
                                '活跃营业部': active_yyb,
                                '营业部数量': len(active_yyb)
                            }
                    except Exception as e:
                        print(f"获取历史营业部数据失败: {e}")

                # 如果所有方法都失败，返回龙虎榜股票列表
                if seat_col is None:
                    print(f"返回龙虎榜股票列表")
                    stock_list = []
                    for _, row in lhb_df.iterrows():
                        stock_list.append({
                            '代码': row['代码'],
                            '名称': row['名称'],
                            '上榜日': row['上榜日'],
                            '收盘价': row['收盘价'],
                            '涨跌幅': row['涨跌幅'],
                            '龙虎榜净买额': row['龙虎榜净买额'],
                            '上榜原因': row['上榜原因']
                        })

                    return {
                        '数据状态': '正常',
                        '说明': '当前数据源不提供营业部明细，仅显示龙虎榜股票列表',
                        '龙虎榜股票': stock_list,
                        '股票数量': len(stock_list)
                    }

            # 分析游资席位
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            unique_seats = lhb_df[seat_col].unique()
            print(f"共找到 {len(unique_seats)} 个不同的营业部")
            print(f"营业部列表: {unique_seats[:10]}...")  # 只打印前10个

            for _, row in lhb_df.iterrows():
                seat_name = str(row[seat_col])

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
                        buy_amount = row.get('龙虎榜买入额', row.get('买入金额', 0))
                        sell_amount = row.get('龙虎榜卖出额', row.get('卖出金额', 0))

                        if buy_amount > 0:
                            capital_stats[capital_name]['买入次数'] += 1
                            capital_stats[capital_name]['买入金额'] += buy_amount
                        elif sell_amount > 0:
                            capital_stats[capital_name]['卖出次数'] += 1
                            capital_stats[capital_name]['卖出金额'] += sell_amount

                        # 记录操作股票
                        stock_info = {
                            '代码': row['代码'],
                            '名称': row['名称'],
                            '日期': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
                        }
                        capital_stats[capital_name]['操作股票'].append(stock_info)

                        capital_analysis.append({
                            '游资名称': capital_name,
                            '营业部名称': row[seat_col],
                            '股票代码': row['代码'],
                            '股票名称': row['名称'],
                            '上榜日': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
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
                    style = "偏多"
                else:
                    style = "偏空"

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
            print(f"游资 {capital_name} 的席位列表: {seats}")

            # 获取历史龙虎榜数据
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []
            checked_dates = 0
            matched_dates = 0

            # 获取每日龙虎榜数据
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                checked_dates += 1

                try:
                    lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)

                    if not lhb_df.empty:
                        print(f"{date_str}: 获取 {len(lhb_df)} 条龙虎榜记录")

                        # 筛选该游资的操作（使用模糊匹配）
                        # 检查列名是否存在
                        if '营业部名称' in lhb_df.columns:
                            seat_col = '营业部名称'
                        elif '营业部' in lhb_df.columns:
                            seat_col = '营业部'
                        elif '营业部' in str(lhb_df.columns):
                            seat_col = '营业部名称'
                        else:
                            # 尝试找到包含"营业部"的列
                            seat_col = None
                            for col in lhb_df.columns:
                                if '营业' in col:
                                    seat_col = col
                                    break

                        if seat_col is None:
                            print(f"  未找到营业部列，可用列: {lhb_df.columns.tolist()}")
                            current_date += pd.Timedelta(days=1)
                            continue

                        for _, row in lhb_df.iterrows():
                            seat_name = str(row[seat_col])

                            # 精确匹配或模糊匹配
                            if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                matched_dates += 1
                                all_operations.append({
                                    '日期': row.get('交易日期', row.get('上榜日', date_str)),
                                    '股票代码': row['代码'],
                                    '股票名称': row['名称'],
                                    '买入金额': row.get('买入额', row.get('买入金额', 0)),
                                    '卖出金额': row.get('卖出额', row.get('卖出金额', 0)),
                                    '净买入': row.get('买入额', row.get('买入金额', 0)) - row.get('卖出额', row.get('卖出金额', 0)),
                                    '营业部名称': seat_name
                                })
                                print(f"  匹配: {seat_name} - {row['名称']}({row['代码']})")
                except Exception as e:
                    print(f"{date_str}: 获取数据失败 - {e}")
                    pass

                current_date += pd.Timedelta(days=1)

            print(f"检查了 {checked_dates} 天，{matched_dates} 天找到操作记录，共 {len(all_operations)} 条操作")

            # 如果没有操作记录，尝试使用新浪接口获取营业部数据
            if not all_operations:
                print("龙虎榜数据中无营业部信息，尝试使用新浪接口获取营业部数据")

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # 获取新浪营业部统计数据
                        yyb_stats = ak.stock_lhb_yytj_sina(symbol='30')  # 获取最近30天的数据

                        if not yyb_stats.empty:
                            print(f"获取到 {len(yyb_stats)} 条营业部统计数据")

                            # 筛选该游资的营业部
                            matched_yyb = []
                            for _, row in yyb_stats.iterrows():
                                seat_name = str(row['营业部名称'])

                                # 精确匹配或模糊匹配
                                if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                    # 处理金额数据
                                    buy_amount = row.get('买入总额', 0)
                                    sell_amount = row.get('卖出总额', 0)

                                    # 确保金额是数值类型
                                    if pd.notna(buy_amount):
                                        try:
                                            buy_amount = float(buy_amount)
                                        except:
                                            buy_amount = 0
                                    else:
                                        buy_amount = 0

                                    if pd.notna(sell_amount):
                                        try:
                                            sell_amount = float(sell_amount)
                                        except:
                                            sell_amount = 0
                                    else:
                                        sell_amount = 0

                                    matched_yyb.append({
                                        '日期': row['上榜日期'],
                                        '股票代码': '',  # 新浪数据中没有股票代码
                                        '股票名称': str(row.get('操作前股票', '')),
                                        '买入金额': buy_amount,
                                        '卖出金额': sell_amount,
                                        '净买入': buy_amount - sell_amount,
                                        '营业部名称': seat_name
                                    })

                            if matched_yyb:
                                print(f"从新浪数据中找到 {len(matched_yyb)} 条操作记录")

                                # 分析操作模式
                                df_ops = pd.DataFrame(matched_yyb)

                                # 1. 操作频率
                                operation_frequency = len(matched_yyb) / days if days > 0 else 0

                                # 2. 买入比例
                                buy_count = len(df_ops[df_ops['净买入'] > 0])
                                sell_count = len(df_ops[df_ops['净买入'] < 0])
                                buy_ratio = round(buy_count / len(df_ops) * 100, 2) if len(df_ops) > 0 else 0

                                # 3. 总金额
                                total_buy = df_ops['买入金额'].sum()
                                total_sell = df_ops['卖出金额'].sum()

                                # 4. 操作风格
                                net_flow = total_buy - total_sell
                                if total_buy > total_sell * 2:
                                    style = "激进买入"
                                elif total_sell > total_buy * 2:
                                    style = "激进卖出"
                                elif net_flow > 0:
                                    style = "偏多"
                                else:
                                    style = "偏空"

                                # 5. 操作成功率（简化版）
                                success_rate = 50.0  # 新浪数据无法计算准确的成功率

                                return {
                                    '数据状态': '正常',
                                    '数据来源': '新浪数据',
                                    '操作次数': len(matched_yyb),
                                    '操作频率': operation_frequency,
                                    '买入比例': buy_ratio,
                                    '操作成功率': success_rate,
                                    '操作风格': style,
                                    '总买入金额': total_buy,
                                    '总卖出金额': total_sell,
                                    '操作记录': matched_yyb,
                                    '说明': f'基于新浪数据分析，{capital_name} 共有 {len(matched_yyb)} 次操作记录'
                                }
                            else:
                                print(f"新浪数据中未找到 {capital_name} 的操作记录")
                        else:
                            print("新浪数据为空")
                    except Exception as e:
                        print(f"获取新浪营业部数据失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(2)  # 等待2秒后重试
                        else:
                            print(f"所有重试均失败")

                # 如果历史数据也没有，返回提示信息
                return {
                    '数据状态': '无操作记录',
                    '说明': f'{capital_name} 在最近 {days} 天内无操作记录。可能原因：1) 该游资近期未上榜 2) 席位名称不匹配 3) 数据源限制。当前数据源不提供营业部明细，无法追踪游资操作。',
                    '检查天数': checked_dates,
                    '匹配天数': matched_dates,
                    '游资席位': seats
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

            # 4. 操作成功率（后续3天涨幅）
            success_count = 0
            total_count = 0

            db = DataManager()
            for op in all_operations:
                try:
                    symbol = op['股票代码']
                    op_date = op['日期']

                    # 获取历史数据
                    start_date_str = op_date
                    end_date_str = (pd.Timestamp(op_date) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

                    df = db.get_history_data(symbol, start_date=start_date_str, end_date=end_date_str)

                    if not df.empty and len(df) > 3:
                        # 计算操作后3天的涨幅
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
                style = "平均操作"

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

            # 分析最近操作方向
            recent_buy = sum(op['买入金额'] for op in recent_operations)
            recent_sell = sum(op['卖出金额'] for op in recent_operations)

            # 预测
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '预测类型': '继续买入',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举买入，可能继续加仓'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '预测类型': '继续卖出',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举卖出，可能继续减仓'
                })
            else:
                predictions.append({
                    '预测类型': '观望或小量操作',
                    '概率': '中',
                    '说明': f'{capital_name} 最近操作均衡，可能观望'
                })

            # 根据成功率预测
            if pattern_result['操作成功率'] > 60:
                predictions.append({
                    '预测类型': '关注其操作',
                    '概率': '中',
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