"""
风险控制模块
提供仓位管理、止损止盈提醒等功能
"""

import pandas as pd
from datetime import datetime
from logic.data_manager import DataManager


class RiskManager:
    """风险管理器"""

    @staticmethod
    def calculate_position_size(capital, risk_per_trade=0.02, stop_loss_pct=0.05):
        """
        计算建议仓位大小

        Args:
            capital: 总资金
            risk_per_trade: 单笔交易风险比例（默认2%）
            stop_loss_pct: 止损比例（默认5%）

        Returns:
            建议仓位大小
        """
        # 单笔交易允许的最大损失
        max_loss_per_trade = capital * risk_per_trade

        # 建议仓位 = 最大损失 / 止损比例
        position_size = max_loss_per_trade / stop_loss_pct

        return {
            '总资金': capital,
            '单笔风险比例': f"{risk_per_trade * 100}%",
            '止损比例': f"{stop_loss_pct * 100}%",
            '单笔最大损失': max_loss_per_trade,
            '建议仓位': position_size,
            '仓位占比': f"{position_size / capital * 100:.2f}%"
        }

    @staticmethod
    def check_stop_loss(symbol, current_price, buy_price, stop_loss_pct=0.05, take_profit_pct=0.10):
        """
        检查止损止盈

        Args:
            symbol: 股票代码
            current_price: 当前价格
            buy_price: 买入价格
            stop_loss_pct: 止损比例（默认5%）
            take_profit_pct: 止盈比例（默认10%）

        Returns:
            止损止盈检查结果
        """
        # 计算盈亏比例
        profit_loss_pct = (current_price - buy_price) / buy_price

        # 计算止损价和止盈价
        stop_loss_price = buy_price * (1 - stop_loss_pct)
        take_profit_price = buy_price * (1 + take_profit_pct)

        # 判断是否触发止损止盈
        if current_price <= stop_loss_price:
            return {
                '状态': '止损',
                '当前价格': current_price,
                '买入价格': buy_price,
                '盈亏比例': f"{profit_loss_pct * 100:.2f}%",
                '止损价': stop_loss_price,
                '止盈价': take_profit_price,
                '建议': f'价格已跌破止损价 {stop_loss_price:.2f}，建议止损'
            }
        elif current_price >= take_profit_price:
            return {
                '状态': '止盈',
                '当前价格': current_price,
                '买入价格': buy_price,
                '盈亏比例': f"{profit_loss_pct * 100:.2f}%",
                '止损价': stop_loss_price,
                '止盈价': take_profit_price,
                '建议': f'价格已达到止盈价 {take_profit_price:.2f}，建议止盈'
            }
        else:
            # 计算距离止损止盈的距离
            distance_to_stop = (current_price - stop_loss_price) / buy_price * 100
            distance_to_profit = (take_profit_price - current_price) / buy_price * 100

            return {
                '状态': '持有',
                '当前价格': current_price,
                '买入价格': buy_price,
                '盈亏比例': f"{profit_loss_pct * 100:.2f}%",
                '止损价': stop_loss_price,
                '止盈价': take_profit_price,
                '距离止损': f"{distance_to_stop:.2f}%",
                '距离止盈': f"{distance_to_profit:.2f}%",
                '建议': '继续持有，关注价格变化'
            }

    @staticmethod
    def calculate_max_drawdown(prices):
        """
        计算最大回撤

        Args:
            prices: 价格序列

        Returns:
            最大回撤信息
        """
        if len(prices) < 2:
            return {
                '最大回撤': 0,
                '回撤比例': '0%'
            }

        # 计算累计收益
        cumulative_returns = (1 + pd.Series(prices).pct_change()).cumprod()

        # 计算最大回撤
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            '最大回撤': f"{abs(max_drawdown) * 100:.2f}%",
            '最大回撤值': abs(max_drawdown),
            '最高点': running_max.max(),
            '最低点': cumulative_returns.min()
        }

    @staticmethod
    def assess_portfolio_risk(positions):
        """
        评估组合风险

        Args:
            positions: 持仓列表，格式为 [{'代码': '600519', '数量': 100, '成本价': 1500}, ...]

        Returns:
            组合风险评估
        """
        if not positions:
            return {
                '持仓数量': 0,
                '总市值': 0,
                '风险等级': '无持仓'
            }

        total_value = 0
        total_cost = 0
        position_details = []

        db = DataManager()

        for pos in positions:
            symbol = pos['代码']
            quantity = pos['数量']
            cost_price = pos['成本价']

            try:
                # 获取当前价格
                df = db.get_history_data(symbol)
                if not df.empty:
                    current_price = df.iloc[-1]['close']
                else:
                    current_price = cost_price

                # 计算市值和盈亏
                market_value = current_price * quantity
                cost_value = cost_price * quantity
                profit_loss = market_value - cost_value
                profit_loss_pct = (profit_loss / cost_value) * 100

                position_details.append({
                    '代码': symbol,
                    '数量': quantity,
                    '成本价': cost_price,
                    '当前价': current_price,
                    '市值': market_value,
                    '盈亏': profit_loss,
                    '盈亏比例': f"{profit_loss_pct:.2f}%"
                })

                total_value += market_value
                total_cost += cost_value
            except Exception as e:
                print(f"评估持仓 {symbol} 失败: {e}")
                continue

        db.close()

        # 计算组合整体盈亏
        total_profit_loss = total_value - total_cost
        total_profit_loss_pct = (total_profit_loss / total_cost) * 100 if total_cost > 0 else 0

        # 评估风险等级
        if total_profit_loss_pct > 20:
            risk_level = "低风险"
        elif total_profit_loss_pct > 0:
            risk_level = "中等风险"
        elif total_profit_loss_pct > -10:
            risk_level = "较高风险"
        else:
            risk_level = "高风险"

        return {
            '持仓数量': len(positions),
            '总市值': total_value,
            '总成本': total_cost,
            '总盈亏': total_profit_loss,
            '总盈亏比例': f"{total_profit_loss_pct:.2f}%",
            '风险等级': risk_level,
            '持仓详情': position_details
        }

    @staticmethod
    def generate_risk_alert(positions, stop_loss_pct=0.05, take_profit_pct=0.10):
        """
        生成风险预警

        Args:
            positions: 持仓列表
            stop_loss_pct: 止损比例
            take_profit_pct: 止盈比例

        Returns:
            风险预警列表
        """
        alerts = []
        db = DataManager()

        for pos in positions:
            symbol = pos['代码']
            quantity = pos['数量']
            cost_price = pos['成本价']

            try:
                # 获取当前价格
                df = db.get_history_data(symbol)
                if not df.empty:
                    current_price = df.iloc[-1]['close']

                    # 检查止损止盈
                    check_result = RiskManager.check_stop_loss(
                        symbol, current_price, cost_price,
                        stop_loss_pct, take_profit_pct
                    )

                    if check_result['状态'] in ['止损', '止盈']:
                        alerts.append({
                            '股票代码': symbol,
                            '预警类型': check_result['状态'],
                            '当前价格': current_price,
                            '成本价': cost_price,
                            '盈亏比例': check_result['盈亏比例'],
                            '建议': check_result['建议']
                        })
            except Exception as e:
                print(f"检查 {symbol} 风险失败: {e}")
                continue

        db.close()

        return {
            '预警数量': len(alerts),
            '预警列表': alerts
        }