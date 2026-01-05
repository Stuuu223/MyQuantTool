"""
智能预警系统模块
包含价格预警、量能预警、技术指标预警等功能
"""

import pandas as pd
from logic.data_manager import DataManager
from logic.algo import QuantAlgo


class AlertSystem:
    """智能预警系统类"""

    @staticmethod
    def check_alerts(symbol, alert_conditions):
        """
        检查预警条件
        alert_conditions: 预警条件字典
        """
        try:
            db = DataManager()

            # 获取股票数据
            start_date = pd.Timestamp.now() - pd.Timedelta(days=60)
            s_date_str = start_date.strftime("%Y%m%d")
            e_date_str = pd.Timestamp.now().strftime("%Y%m%d")

            df = db.get_history_data(symbol, start_date=s_date_str, end_date=e_date_str)

            if df.empty or len(df) < 20:
                return {
                    '数据状态': '数据不足',
                    '说明': '需要至少20天数据'
                }

            alerts = []

            # 获取实时行情数据
            try:
                import akshare as ak
                stock_info = ak.stock_zh_a_spot_em()
                stock_row = stock_info[stock_info['代码'] == symbol]

                if not stock_row.empty:
                    current_price = stock_row.iloc[0]['最新价']
                    change_pct = stock_row.iloc[0]['涨跌幅']
                    volume_ratio = stock_row.iloc[0]['量比']
                else:
                    current_price = df.iloc[-1]['close']
                    change_pct = (current_price - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100
                    volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(5).mean().iloc[-1]
            except:
                current_price = df.iloc[-1]['close']
                change_pct = (current_price - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100
                volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(5).mean().iloc[-1]

            # 1. 价格预警
            if alert_conditions.get('price_alert_enabled', False):
                price_above = alert_conditions.get('price_above', 0)
                price_below = alert_conditions.get('price_below', 0)

                if price_above > 0 and current_price >= price_above:
                    alerts.append({
                        '预警类型': '价格突破',
                        '预警级别': '高',
                        '当前价格': current_price,
                        '预警条件': f'价格 >= {price_above}',
                        '说明': f'当前价格 {current_price:.2f} 已突破预警价 {price_above}'
                    })

                if price_below > 0 and current_price <= price_below:
                    alerts.append({
                        '预警类型': '价格跌破',
                        '预警级别': '高',
                        '当前价格': current_price,
                        '预警条件': f'价格 <= {price_below}',
                        '说明': f'当前价格 {current_price:.2f} 已跌破预警价 {price_below}'
                    })

            # 2. 涨跌幅预警
            if alert_conditions.get('change_alert_enabled', False):
                change_above = alert_conditions.get('change_above', 0)
                change_below = alert_conditions.get('change_below', 0)

                if change_above > 0 and change_pct >= change_above:
                    alerts.append({
                        '预警类型': '涨幅预警',
                        '预警级别': '高',
                        '当前涨跌幅': f"{change_pct:.2f}%",
                        '预警条件': f'涨跌幅 >= {change_above}%',
                        '说明': f'当前涨幅 {change_pct:.2f}% 已达到预警值'
                    })

                if change_below < 0 and change_pct <= change_below:
                    alerts.append({
                        '预警类型': '跌幅预警',
                        '预警级别': '高',
                        '当前涨跌幅': f"{change_pct:.2f}%",
                        '预警条件': f'涨跌幅 <= {change_below}%',
                        '说明': f'当前跌幅 {change_pct:.2f}% 已达到预警值'
                    })

            # 3. 量能预警
            if alert_conditions.get('volume_alert_enabled', False):
                volume_ratio_threshold = alert_conditions.get('volume_ratio_threshold', 2)

                if volume_ratio >= volume_ratio_threshold:
                    alerts.append({
                        '预警类型': '量能异动',
                        '预警级别': '中',
                        '当前量比': f"{volume_ratio:.2f}",
                        '预警条件': f'量比 >= {volume_ratio_threshold}',
                        '说明': f'当前量比 {volume_ratio:.2f}，成交量异常放大'
                    })

            # 4. 技术指标预警
            if alert_conditions.get('indicator_alert_enabled', False):
                # RSI预警
                rsi_data = QuantAlgo.calculate_rsi(df)
                rsi_value = rsi_data['RSI'].iloc[-1]

                if alert_conditions.get('rsi_overbought', False) and rsi_value > 70:
                    alerts.append({
                        '预警类型': 'RSI超买',
                        '预警级别': '中',
                        '当前RSI': f"{rsi_value:.2f}",
                        '预警条件': 'RSI > 70',
                        '说明': f'RSI {rsi_value:.2f}，进入超买区域，注意回调风险'
                    })

                if alert_conditions.get('rsi_oversold', False) and rsi_value < 30:
                    alerts.append({
                        '预警类型': 'RSI超卖',
                        '预警级别': '中',
                        '当前RSI': f"{rsi_value:.2f}",
                        '预警条件': 'RSI < 30',
                        '说明': f'RSI {rsi_value:.2f}，进入超卖区域，可能反弹'
                    })

                # MACD金叉死叉
                macd_data = QuantAlgo.calculate_macd(df)
                macd_diff = macd_data['MACD'].iloc[-1] - macd_data['Signal'].iloc[-1]

                if alert_conditions.get('macd_golden_cross', False) and macd_diff > 0:
                    alerts.append({
                        '预警类型': 'MACD金叉',
                        '预警级别': '中',
                        'MACD': f"{macd_data['MACD'].iloc[-1]:.4f}",
                        'Signal': f"{macd_data['Signal'].iloc[-1]:.4f}",
                        '说明': 'MACD金叉，多头信号'
                    })

                if alert_conditions.get('macd_death_cross', False) and macd_diff < 0:
                    alerts.append({
                        '预警类型': 'MACD死叉',
                        '预警级别': '中',
                        'MACD': f"{macd_data['MACD'].iloc[-1]:.4f}",
                        'Signal': f"{macd_data['Signal'].iloc[-1]:.4f}",
                        '说明': 'MACD死叉，空头信号'
                    })

            db.close()

            return {
                '数据状态': '正常',
                '预警数量': len(alerts),
                '预警列表': alerts,
                '股票代码': symbol,
                '当前价格': current_price,
                '当前涨跌幅': f"{change_pct:.2f}%"
            }

        except Exception as e:
            return {
                '数据状态': '检查失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }

    @staticmethod
    def scan_watchlist_alerts(watchlist, alert_conditions):
        """
        扫描自选股预警
        批量检查自选股中满足预警条件的股票
        """
        try:
            all_alerts = []

            for symbol in watchlist:
                alert_result = AlertSystem.check_alerts(symbol, alert_conditions)

                if alert_result['数据状态'] == '正常' and alert_result['预警数量'] > 0:
                    stock_name = QuantAlgo.get_stock_name(symbol)

                    for alert in alert_result['预警列表']:
                        all_alerts.append({
                            '股票代码': symbol,
                            '股票名称': stock_name,
                            '当前价格': alert_result['当前价格'],
                            '当前涨跌幅': alert_result['当前涨跌幅'],
                            **alert
                        })

            # 按预警级别排序
            priority_order = {'高': 0, '中': 1, '低': 2}
            all_alerts.sort(key=lambda x: priority_order.get(x['预警级别'], 3))

            return {
                '数据状态': '正常',
                '预警总数': len(all_alerts),
                '预警列表': all_alerts
            }

        except Exception as e:
            return {
                '数据状态': '扫描失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }