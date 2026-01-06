"""
打板成功率预测模块
基于历史数据预测次日成功率
"""

import pandas as pd
from logic.data_manager import DataManager


class LimitUpPredictor:
    """打板成功率预测器"""

    @staticmethod
    def predict_limit_up_success_rate(symbol):
        """
        预测个股打板成功率
        基于历史涨停数据预测次日成功率
        """
        try:
            # 验证股票代码格式
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                return {
                    '数据状态': '股票代码错误',
                    '说明': '股票代码格式不正确，应为6位数字'
                }

            db = DataManager()

            # 获取历史数据
            start_date = pd.Timestamp.now() - pd.Timedelta(days=180)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)

            if df is None or df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': f'无法获取股票 {symbol} 的历史数据，请检查网络连接或股票代码'
                }

            if len(df) < 30:
                return {
                    '数据状态': '数据不足',
                    '说明': f'该股票只有 {len(df)} 天数据，需要至少30天历史数据'
                }

            # 识别涨停板
            df['change_pct'] = df['close'].pct_change() * 100
            limit_up_days = df[df['change_pct'] >= 9.9]

            if limit_up_days.empty:
                return {
                    '数据状态': '无涨停记录',
                    '说明': '该股票在最近180天内无涨停记录'
                }

            # 分析涨停后的表现
            total_limit_up = len(limit_up_days)
            success_count = 0
            fail_count = 0
            flat_count = 0

            limit_up_records = []

            for idx, row in limit_up_days.iterrows():
                # 找到涨停日的索引
                limit_up_idx = df.index.get_loc(idx)

                # 检查次日表现
                if limit_up_idx + 1 < len(df):
                    next_day = df.iloc[limit_up_idx + 1]
                    next_change = next_day['change_pct']

                    # 判断次日表现
                    if next_change >= 3:
                        result = '成功'
                        success_count += 1
                    elif next_change <= -3:
                        result = '失败'
                        fail_count += 1
                    else:
                        result = '平局'
                        flat_count += 1

                    limit_up_records.append({
                        '涨停日期': idx,
                        '涨停涨幅': round(row['change_pct'], 2),
                        '次日涨跌幅': round(next_change, 2),
                        '结果': result
                    })

            # 计算成功率
            success_rate = (success_count / total_limit_up * 100) if total_limit_up > 0 else 0

            # 分析影响因素
            factors = []

            # 1. 涨停频率
            limit_up_frequency = total_limit_up / len(df) * 100
            if limit_up_frequency > 10:
                factors.append({
                    '因素': '涨停频率',
                    '值': f"{limit_up_frequency:.1f}%",
                    '影响': '正面',
                    '说明': '涨停频率高，股性活跃'
                })
            elif limit_up_frequency > 5:
                factors.append({
                    '因素': '涨停频率',
                    '值': f"{limit_up_frequency:.1f}%",
                    '影响': '中性',
                    '说明': '涨停频率一般'
                })
            else:
                factors.append({
                    '因素': '涨停频率',
                    '值': f"{limit_up_frequency:.1f}%",
                    '影响': '负面',
                    '说明': '涨停频率低，股性不活跃'
                })

            # 2. 连板能力
            consecutive_limit_up = 0
            max_consecutive = 0

            for i in range(len(df) - 1):
                if df.iloc[i]['change_pct'] >= 9.9 and df.iloc[i + 1]['change_pct'] >= 9.9:
                    consecutive_limit_up += 1
                    max_consecutive = max(max_consecutive, consecutive_limit_up)
                else:
                    consecutive_limit_up = 0

            if max_consecutive >= 3:
                factors.append({
                    '因素': '连板能力',
                    '值': f"{max_consecutive}板",
                    '影响': '正面',
                    '说明': '连板能力强，值得关注'
                })
            elif max_consecutive >= 2:
                factors.append({
                    '因素': '连板能力',
                    '值': f"{max_consecutive}板",
                    '影响': '中性',
                    '说明': '有一定连板能力'
                })
            else:
                factors.append({
                    '因素': '连板能力',
                    '值': f"{max_consecutive}板",
                    '影响': '负面',
                    '说明': '连板能力弱'
                })

            # 3. 涨停后表现趋势
            if len(limit_up_records) >= 5:
                recent_5 = limit_up_records[-5:]
                recent_success = sum(1 for r in recent_5 if r['结果'] == '成功')
                recent_success_rate = recent_success / 5 * 100

                if recent_success_rate > 60:
                    factors.append({
                        '因素': '近期表现',
                        '值': f"{recent_success_rate:.0f}%",
                        '影响': '正面',
                        '说明': '近期涨停后表现良好'
                    })
                elif recent_success_rate < 40:
                    factors.append({
                        '因素': '近期表现',
                        '值': f"{recent_success_rate:.0f}%",
                        '影响': '负面',
                        '说明': '近期涨停后表现较差'
                    })
                else:
                    factors.append({
                        '因素': '近期表现',
                        '值': f"{recent_success_rate:.0f}%",
                        '影响': '中性',
                        '说明': '近期表现一般'
                    })

            # 4. 成交量特征
            # 先计算成交量均线，然后再筛选涨停日
            df['volume_ma5'] = df['volume'].rolling(5).mean()
            # 重新筛选包含成交量均线的涨停日
            limit_up_with_ma = df[df['change_pct'] >= 9.9].copy()
            limit_up_with_ma['volume_ratio'] = limit_up_with_ma['volume'] / limit_up_with_ma['volume_ma5']

            avg_volume_ratio = limit_up_with_ma['volume_ratio'].mean()

            if avg_volume_ratio > 2:
                factors.append({
                    '因素': '涨停量能',
                    '值': f"{avg_volume_ratio:.2f}倍",
                    '影响': '正面',
                    '说明': '涨停时放量明显，资金参与度高'
                })
            elif avg_volume_ratio > 1.5:
                factors.append({
                    '因素': '涨停量能',
                    '值': f"{avg_volume_ratio:.2f}倍",
                    '影响': '中性',
                    '说明': '涨停时量能一般'
                })
            else:
                factors.append({
                    '因素': '涨停量能',
                    '值': f"{avg_volume_ratio:.2f}倍",
                    '影响': '负面',
                    '说明': '涨停时量能不足'
                })

            # 综合评分
            score = 0
            positive_factors = sum(1 for f in factors if f['影响'] == '正面')
            negative_factors = sum(1 for f in factors if f['影响'] == '负面')

            score += positive_factors * 20
            score += success_rate * 0.3

            # 评级
            if score >= 80:
                rating = "🔥 优秀"
                suggestion = "打板成功率较高，可以积极参与"
            elif score >= 60:
                rating = "🟡 良好"
                suggestion = "打板成功率一般，谨慎参与"
            elif score >= 40:
                rating = "🟢 一般"
                suggestion = "打板成功率较低，建议观望"
            else:
                rating = "⚪ 较差"
                suggestion = "打板成功率低，不建议参与"

            db.close()

            return {
                '数据状态': '正常',
                '股票代码': symbol,
                '总涨停次数': total_limit_up,
                '成功次数': success_count,
                '失败次数': fail_count,
                '平局次数': flat_count,
                '成功率': round(success_rate, 2),
                '综合评分': round(score, 1),
                '评级': rating,
                '操作建议': suggestion,
                '影响因素': factors,
                '涨停记录': limit_up_records[-10:]  # 最近10次涨停记录
            }

        except Exception as e:
            return {
                '数据状态': '预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def batch_predict_limit_up(symbols):
        """
        批量预测多只股票的打板成功率
        """
        try:
            all_predictions = []

            for symbol in symbols:
                result = LimitUpPredictor.predict_limit_up_success_rate(symbol)

                if result['数据状态'] == '正常':
                    all_predictions.append({
                        '股票代码': symbol,
                        '成功率': result['成功率'],
                        '综合评分': result['综合评分'],
                        '评级': result['评级'],
                        '总涨停次数': result['总涨停次数']
                    })

            # 按成功率排序
            all_predictions.sort(key=lambda x: x['成功率'], reverse=True)

            return {
                '数据状态': '正常',
                '预测总数': len(all_predictions),
                '预测列表': all_predictions
            }

        except Exception as e:
            return {
                '数据状态': '批量预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def analyze_market_limit_up_success():
        """
        分析市场整体打板成功率
        """
        try:
            import akshare as ak

            # 获取今日涨停股票
            limit_up_df = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime("%Y%m%d"))

            if limit_up_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日无涨停股票'
                }

            # 随机抽取部分股票进行分析
            sample_size = min(20, len(limit_up_df))
            sample_stocks = limit_up_df.sample(sample_size)

            # 批量预测
            symbols = sample_stocks['代码'].tolist()
            predictions = LimitUpPredictor.batch_predict_limit_up(symbols)

            if predictions['数据状态'] != '正常':
                return predictions

            # 计算市场平均成功率
            avg_success_rate = sum(p['成功率'] for p in predictions['预测列表']) / len(predictions['预测列表'])

            # 统计评级分布
            rating_dist = {}
            for p in predictions['预测列表']:
                rating = p['评级']
                rating_dist[rating] = rating_dist.get(rating, 0) + 1

            return {
                '数据状态': '正常',
                '今日涨停数': len(limit_up_df),
                '分析样本数': sample_size,
                '市场平均成功率': round(avg_success_rate, 2),
                '评级分布': rating_dist,
                '详细预测': predictions['预测列表']
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }