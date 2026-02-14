"""
简单的回测模块
用于测试网格交易策略的历史表现和战法成功率
"""
import pandas as pd
import numpy as np

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
    
    def run_grid_strategy_backtest(self, df, atr_multiplier=0.5, grid_ratio=0.1, transaction_cost=0.001):
        """
        运行网格策略回测
        
        Args:
            df: 历史K线数据
            atr_multiplier: ATR倍数
            grid_ratio: 每次交易的比例
            transaction_cost: 交易手续费（默认0.1%）
        
        Returns:
            回测结果字典
        """
        # 计算ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 计算网格线
        df['grid_center'] = df['close'].rolling(20).mean()
        df['grid_upper'] = df['grid_center'] + (df['atr'] * atr_multiplier)
        df['grid_lower'] = df['grid_center'] - (df['atr'] * atr_multiplier)
        
        # 初始化回测状态
        capital = self.initial_capital
        position = 0  # 持仓数量
        trades = []
        
        for i in range(20, len(df)):  # 从第20天开始，确保指标计算完成
            current_price = df.iloc[i]['close']
            grid_upper = df.iloc[i]['grid_upper']
            grid_lower = df.iloc[i]['grid_lower']
            
            # 买入信号：价格跌破下轨且没有持仓
            if current_price < grid_lower and position == 0:
                buy_amount = capital * grid_ratio
                shares = int(buy_amount / current_price)
                if shares > 0:
                    position = shares
                    capital -= shares * current_price * (1 + transaction_cost)
                    trades.append({
                        'date': df.iloc[i]['date'],
                        'type': '买入',
                        'price': current_price,
                        'shares': shares,
                        'capital': capital
                    })
            
            # 卖出信号：价格突破上轨且有持仓
            elif current_price > grid_upper and position > 0:
                capital += position * current_price * (1 - transaction_cost)
                trades.append({
                    'date': df.iloc[i]['date'],
                    'type': '卖出',
                    'price': current_price,
                    'shares': position,
                    'capital': capital
                })
                position = 0
        
        # 计算最终资产价值
        final_price = df.iloc[-1]['close']
        final_capital = capital + position * final_price
        
        # 计算收益
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # 计算基准收益（买入持有）
        first_price = df.iloc[20]['close']
        benchmark_return = (final_price - first_price) / first_price * 100
        
        return {
            '初始资金': self.initial_capital,
            '最终资金': round(final_capital, 2),
            '总收益率': round(total_return, 2),
            '基准收益率': round(benchmark_return, 2),
            '超额收益': round(total_return - benchmark_return, 2),
            '交易次数': len(trades),
            '交易记录': pd.DataFrame(trades) if trades else pd.DataFrame()
        }
    
    def generate_backtest_report(self, backtest_result):
        """生成回测报告"""
        report = f"""
## 📊 回测报告

### 资金表现
- 初始资金：¥{backtest_result['初始资金']:,.2f}
- 最终资金：¥{backtest_result['最终资金']:,.2f}
- 总收益率：{backtest_result['总收益率']:.2f}%

### 策略对比
- 基准收益率（买入持有）：{backtest_result['基准收益率']:.2f}%
- 超额收益：{backtest_result['超额收益']:.2f}%

### 交易统计
- 总交易次数：{backtest_result['交易次数']} 次

### 结论
"""
        if backtest_result['超额收益'] > 0:
            report += "✅ 网格策略表现优于买入持有策略，超额收益为正。"
        else:
            report += "❌ 网格策略表现不如买入持有策略，建议优化参数或策略。"
        
        return report
    
    def detect_pattern_signals(self, df, pattern_type='all'):
        """
        检测历史数据中的战法信号
        
        Args:
            df: 历史K线数据
            pattern_type: 战法类型 ('all', 'dragon', 'box', 'double_bottom', 'double_top', 'head_shoulders')
        
        Returns:
            信号列表,每个信号包含日期、类型、价格等信息
        """
        signals = []
        
        if len(df) < 30:
            return signals
        
        # 遍历历史数据,检测每个时间点的信号
        for i in range(30, len(df)):
            current_df = df.iloc[:i+1]
            current_date = df.iloc[i]['date']
            current_price = df.iloc[i]['close']
            
            # 龙头战法信号
            if pattern_type in ['all', 'dragon']:
                # 检查是否涨停
                prev_close = df.iloc[i-1]['close']
                # 防止除以零
                if prev_close != 0:
                    change_pct = (current_price - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0
                
                if change_pct >= 9.9:  # 涨停
                    # 检查价格条件
                    if current_price <= 15:
                        # 检查成交量
                        volume_avg = df.iloc[i-5:i]['volume'].mean()
                        volume_ratio = df.iloc[i]['volume'] / volume_avg if volume_avg > 0 else 1
                        
                        if volume_ratio > 1.5:
                            signals.append({
                                'date': current_date,
                                'pattern': '龙头战法',
                                'type': '买入',
                                'price': current_price,
                                'change_pct': change_pct,
                                'volume_ratio': volume_ratio
                            })
            
            # 箱体突破信号
            if pattern_type in ['all', 'box']:
                # 计算箱体
                lookback = 20
                if i >= lookback:
                    recent_df = df.iloc[i-lookback:i]
                    box_high = recent_df['high'].max()
                    box_low = recent_df['low'].min()
                    
                    # 向上突破
                    if current_price > box_high:
                        signals.append({
                            'date': current_date,
                            'pattern': '箱体突破',
                            'type': '买入',
                            'price': current_price,
                            'box_high': box_high,
                            'box_low': box_low
                        })
                    
                    # 向下突破
                    elif current_price < box_low:
                        signals.append({
                            'date': current_date,
                            'pattern': '箱体突破',
                            'type': '卖出',
                            'price': current_price,
                            'box_high': box_high,
                            'box_low': box_low
                        })
            
            # 双底信号
            if pattern_type in ['all', 'double_bottom']:
                if i >= 40:
                    # 检查最近40天是否有双底
                    recent_df = df.iloc[i-40:i+1]
                    lows = recent_df['low'].tolist()
                    
                    # 寻找两个低点
                    if len(lows) >= 2:
                        min_idx1 = lows.index(min(lows[:20]))
                        min_idx2 = 20 + lows[20:].index(min(lows[20:]))
                        
                        if abs(lows[min_idx1] - lows[min_idx2]) / lows[min_idx1] < 0.05:
                            # 检查是否突破颈线
                            neck_line = max(df.iloc[i-40:i-20]['high'])
                            if current_price > neck_line:
                                signals.append({
                                    'date': current_date,
                                    'pattern': '双底',
                                    'type': '买入',
                                    'price': current_price,
                                    'neck_line': neck_line,
                                    'first_bottom': lows[min_idx1],
                                    'second_bottom': lows[min_idx2]
                                })
            
            # 双顶信号
            if pattern_type in ['all', 'double_top']:
                if i >= 40:
                    recent_df = df.iloc[i-40:i+1]
                    highs = recent_df['high'].tolist()
                    
                    if len(highs) >= 2:
                        max_idx1 = highs.index(max(highs[:20]))
                        max_idx2 = 20 + highs[20:].index(max(highs[20:]))
                        
                        if abs(highs[max_idx1] - highs[max_idx2]) / highs[max_idx1] < 0.05:
                            # 检查是否跌破颈线
                            neck_line = min(df.iloc[i-40:i-20]['low'])
                            if current_price < neck_line:
                                signals.append({
                                    'date': current_date,
                                    'pattern': '双顶',
                                    'type': '卖出',
                                    'price': current_price,
                                    'neck_line': neck_line,
                                    'first_top': highs[max_idx1],
                                    'second_top': highs[max_idx2]
                                })
            
            # 头肩顶/头肩底信号
            if pattern_type in ['all', 'head_shoulders']:
                if i >= 60:
                    recent_df = df.iloc[i-60:i+1]
                    
                    # 寻找极值点
                    pivot_highs = []
                    pivot_lows = []
                    
                    for j in range(5, len(recent_df)-5):
                        if recent_df.iloc[j]['high'] == recent_df.iloc[j-5:j+5]['high'].max():
                            pivot_highs.append((j, recent_df.iloc[j]['high']))
                        if recent_df.iloc[j]['low'] == recent_df.iloc[j-5:j+5]['low'].min():
                            pivot_lows.append((j, recent_df.iloc[j]['low']))
                    
                    # 检测头肩顶
                    if len(pivot_highs) >= 3:
                        recent_highs = pivot_highs[-3:]
                        if (recent_highs[1][1] > recent_highs[0][1] and 
                            recent_highs[1][1] > recent_highs[2][1]):
                            # 检查是否跌破颈线
                            neck_line = min(recent_df.iloc[:recent_highs[1][0]]['low'].min(),
                                          recent_df.iloc[recent_highs[1][0]:]['low'].min())
                            if current_price < neck_line:
                                signals.append({
                                    'date': current_date,
                                    'pattern': '头肩顶',
                                    'type': '卖出',
                                    'price': current_price,
                                    'neck_line': neck_line,
                                    'left_shoulder': recent_highs[0][1],
                                    'head': recent_highs[1][1],
                                    'right_shoulder': recent_highs[2][1]
                                })
                    
                    # 检测头肩底
                    if len(pivot_lows) >= 3:
                        recent_lows = pivot_lows[-3:]
                        if (recent_lows[1][1] < recent_lows[0][1] and 
                            recent_lows[1][1] < recent_lows[2][1]):
                            # 检查是否突破颈线
                            neck_line = max(recent_df.iloc[:recent_lows[1][0]]['high'].max(),
                                          recent_df.iloc[recent_lows[1][0]:]['high'].max())
                            if current_price > neck_line:
                                signals.append({
                                    'date': current_date,
                                    'pattern': '头肩底',
                                    'type': '买入',
                                    'price': current_price,
                                    'neck_line': neck_line,
                                    'left_shoulder': recent_lows[0][1],
                                    'head': recent_lows[1][1],
                                    'right_shoulder': recent_lows[2][1]
                                })
        
        return signals
    
    def calculate_pattern_success_rate(self, df, signals, hold_days=5, profit_threshold=0.03, loss_threshold=-0.03):
        """
        计算战法信号的成功率
        
        Args:
            df: 历史K线数据
            signals: 信号列表
            hold_days: 持有天数
            profit_threshold: 盈利阈值(3%)
            loss_threshold: 亏损阈值(-3%)
        
        Returns:
            成功率统计结果
        """
        if not signals:
            return {
                '总信号数': 0,
                '成功率': 0,
                '盈利信号数': 0,
                '亏损信号数': 0,
                '平局信号数': 0,
                '平均盈利': 0,
                '平均亏损': 0,
                '盈亏比': 0,
                '详细统计': pd.DataFrame()
            }
        
        results = []
        success_count = 0
        loss_count = 0
        tie_count = 0
        
        for signal in signals:
            signal_date = signal['date']
            signal_price = signal['price']
            signal_type = signal['type']
            
            # 找到信号日期在df中的索引
            signal_idx = df[df['date'] == signal_date].index
            
            if len(signal_idx) == 0:
                continue
            
            signal_idx = signal_idx[0]
            
            # 计算持有期后的价格
            end_idx = min(signal_idx + hold_days, len(df) - 1)
            
            if end_idx > signal_idx:
                end_price = df.iloc[end_idx]['close']
                
                # 计算收益率
                if signal_type == '买入':
                    return_pct = (end_price - signal_price) / signal_price
                else:  # 卖出
                    return_pct = (signal_price - end_price) / signal_price
                
                # 判断成功/失败
                if return_pct >= profit_threshold:
                    result = '盈利'
                    success_count += 1
                elif return_pct <= loss_threshold:
                    result = '亏损'
                    loss_count += 1
                else:
                    result = '平局'
                    tie_count += 1
                
                # 构建结果记录,包含所有信号信息
                result_record = {
                    '信号日期': signal_date,
                    '战法类型': signal['pattern'],
                    '信号类型': signal_type,
                    '信号价格': signal_price,
                    '结束日期': df.iloc[end_idx]['date'],
                    '结束价格': end_price,
                    '收益率': round(return_pct * 100, 2),
                    '结果': result,
                    '持有天数': hold_days
                }
                
                # 添加信号的特殊信息
                for key in ['change_pct', 'volume_ratio', 'box_high', 'box_low', 
                           'first_bottom', 'second_bottom', 'neck_line',
                           'first_top', 'second_top', 'left_shoulder', 'head', 'right_shoulder']:
                    if key in signal:
                        result_record[key] = signal[key]
                
                results.append(result_record)
        
        # 计算统计数据
        total_signals = len(results)
        success_rate = (success_count / total_signals * 100) if total_signals > 0 else 0
        
        # 计算平均盈利和平均亏损
        profitable_returns = [r['收益率'] for r in results if r['结果'] == '盈利']
        loss_returns = [r['收益率'] for r in results if r['结果'] == '亏损']
        
        avg_profit = sum(profitable_returns) / len(profitable_returns) if profitable_returns else 0
        avg_loss = sum(loss_returns) / len(loss_returns) if loss_returns else 0
        
        # 盈亏比
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        return {
            '总信号数': total_signals,
            '成功率': round(success_rate, 2),
            '盈利信号数': success_count,
            '亏损信号数': loss_count,
            '平局信号数': tie_count,
            '平均盈利': round(avg_profit, 2),
            '平均亏损': round(avg_loss, 2),
            '盈亏比': round(profit_loss_ratio, 2),
            '详细统计': pd.DataFrame(results) if results else pd.DataFrame()
        }
    
    def run_pattern_backtest(self, df, pattern_type='all', hold_days=5, profit_threshold=0.03, loss_threshold=-0.03):
        """
        运行战法成功率回测
        
        Args:
            df: 历史K线数据
            pattern_type: 战法类型
            hold_days: 持有天数
            profit_threshold: 盈利阈值
            loss_threshold: 亏损阈值
        
        Returns:
            回测结果
        """
        # 检测信号
        signals = self.detect_pattern_signals(df, pattern_type)
        
        # 计算成功率
        success_stats = self.calculate_pattern_success_rate(
            df, signals, hold_days, profit_threshold, loss_threshold
        )
        
        # 按战法类型分组统计
        if not success_stats['详细统计'].empty:
            pattern_stats = success_stats['详细统计'].groupby('战法类型').agg({
                '信号日期': 'count',
                '收益率': ['mean', 'std', 'min', 'max'],
                '结果': lambda x: (x == '盈利').sum()
            }).round(2)
            
            pattern_stats.columns = ['信号数', '平均收益率', '收益率标准差', '最小收益率', '最大收益率', '成功数']
            pattern_stats['成功率'] = (pattern_stats['成功数'] / pattern_stats['信号数'] * 100).round(2)
            
            # 按成功率排序
            pattern_stats = pattern_stats.sort_values('成功率', ascending=False)
            
            # 添加排名
            pattern_stats['排名'] = range(1, len(pattern_stats) + 1)
            
            # 重新排列列顺序
            pattern_stats = pattern_stats[['排名', '信号数', '成功数', '成功率', '平均收益率', '收益率标准差', '最小收益率', '最大收益率']]
        else:
            pattern_stats = pd.DataFrame()
        
        return {
            '战法类型': pattern_type,
            '持有天数': hold_days,
            '盈利阈值': f"{profit_threshold*100:.1f}%",
            '亏损阈值': f"{loss_threshold*100:.1f}%",
            '总体统计': success_stats,
            '分战法统计': pattern_stats,
            '所有信号': signals
        }
    
    def generate_pattern_backtest_report(self, backtest_result):
        """生成战法回测报告"""
        stats = backtest_result['总体统计']
        
        report = f"""
## 📊 战法成功率回测报告

### 回测参数
- 战法类型: {backtest_result['战法类型']}
- 持有天数: {backtest_result['持有天数']} 天
- 盈利阈值: {backtest_result['盈利阈值']}
- 亏损阈值: {backtest_result['亏损阈值']}

### 总体统计
- 总信号数: {stats['总信号数']}
- 成功率: {stats['成功率']}% ✅
- 盈利信号: {stats['盈利信号数']} 次
- 亏损信号: {stats['亏损信号数']} 次
- 平局信号: {stats['平局信号数']} 次

### 收益统计
- 平均盈利: {stats['平均盈利']}%
- 平均亏损: {stats['平均亏损']}%
- 盈亏比: {stats['盈亏比']}

### 结论
"""
        if stats['成功率'] >= 70:
            report += "🔥 **战法表现优秀** - 成功率超过70%,可以考虑使用此战法"
        elif stats['成功率'] >= 50:
            report += "📈 **战法表现良好** - 成功率超过50%,可以谨慎使用"
        elif stats['成功率'] >= 30:
            report += "⚠️ **战法表现一般** - 成功率较低,建议结合其他指标使用"
        else:
            report += "❌ **战法表现较差** - 成功率低于30%,不建议单独使用"
        
        if stats['盈亏比'] >= 2:
            report += "\n\n💰 **盈亏比优秀** - 平均盈利是平均亏损的2倍以上,风险收益比良好"
        elif stats['盈亏比'] >= 1:
            report += "\n\n📊 **盈亏比正常** - 平均盈利和平均亏损基本平衡"
        else:
            report += "\n\n⚠️ **盈亏比较低** - 平均亏损大于平均盈利,需要优化止损策略"
        
        return report
    
    def run_portfolio_backtest(self, symbols, pattern_type='all', hold_days=5, 
                              profit_threshold=0.03, loss_threshold=-0.03,
                              start_date=None, end_date=None, data_manager=None):
        """
        策略组合回测 - 同时回测多个股票
        
        Args:
            symbols: 股票代码列表
            pattern_type: 战法类型
            hold_days: 持有天数
            profit_threshold: 盈利阈值
            loss_threshold: 亏损阈值
            start_date: 开始日期
            end_date: 结束日期
            data_manager: 数据管理器
        
        Returns:
            组合回测结果
        """
        if not data_manager:
            from logic.data_manager import DataManager
            data_manager = DataManager()
        
        portfolio_results = []
        
        for symbol in symbols:
            try:
                # 获取历史数据
                df = data_manager.get_history_data(symbol, start_date=start_date, end_date=end_date)
                
                if not df.empty and len(df) > 60:
                    # 运行单股票回测
                    result = self.run_pattern_backtest(
                        df, pattern_type=pattern_type,
                        hold_days=hold_days,
                        profit_threshold=profit_threshold,
                        loss_threshold=loss_threshold
                    )
                    
                    # 添加股票信息
                    result['股票代码'] = symbol
                    result['股票名称'] = self._get_stock_name(symbol)
                    portfolio_results.append(result)
            except Exception as e:
                print(f"回测股票 {symbol} 失败: {e}")
                continue
        
        # 汇总统计
        if portfolio_results:
            portfolio_df = pd.DataFrame([{
                '股票代码': r['股票代码'],
                '股票名称': r['股票名称'],
                '总信号数': r['总体统计']['总信号数'],
                '成功率': r['总体统计']['成功率'],
                '盈利信号数': r['总体统计']['盈利信号数'],
                '亏损信号数': r['总体统计']['亏损信号数'],
                '平均盈利': r['总体统计']['平均盈利'],
                '平均亏损': r['总体统计']['平均亏损'],
                '盈亏比': r['总体统计']['盈亏比']
            } for r in portfolio_results])
            
            # 按成功率排序
            portfolio_df = portfolio_df.sort_values('成功率', ascending=False)
            
            # 计算组合统计
            total_signals = portfolio_df['总信号数'].sum()
            total_profit = portfolio_df['盈利信号数'].sum()
            total_loss = portfolio_df['亏损信号数'].sum()
            avg_success_rate = portfolio_df['成功率'].mean()
            
            return {
                '组合统计': {
                    '股票数量': len(portfolio_results),
                    '总信号数': total_signals,
                    '总盈利信号': total_profit,
                    '总亏损信号': total_loss,
                    '平均成功率': round(avg_success_rate, 2),
                    '组合成功率': round(total_profit / total_signals * 100, 2) if total_signals > 0 else 0
                },
                '详细结果': portfolio_df,
                '各股回测': portfolio_results
            }
        else:
            return {
                '组合统计': {},
                '详细结果': pd.DataFrame(),
                '各股回测': []
            }
    
    def optimize_parameters(self, df, pattern_type='all', param_ranges=None):
        """
        参数优化 - 寻找最优的回测参数
        
        Args:
            df: 历史K线数据
            pattern_type: 战法类型
            param_ranges: 参数范围字典,格式: {'hold_days': [3,5,7], 'profit_threshold': [0.02,0.03,0.05]}
        
        Returns:
            最优参数和结果
        """
        if param_ranges is None:
            param_ranges = {
                'hold_days': [3, 5, 7, 10],
                'profit_threshold': [0.02, 0.03, 0.05],
                'loss_threshold': [-0.05, -0.03, -0.02]
            }
        
        best_result = None
        best_params = None
        best_score = -1
        
        optimization_results = []
        
        # 网格搜索
        for hold_days in param_ranges['hold_days']:
            for profit_threshold in param_ranges['profit_threshold']:
                for loss_threshold in param_ranges['loss_threshold']:
                    try:
                        # 运行回测
                        result = self.run_pattern_backtest(
                            df, pattern_type=pattern_type,
                            hold_days=hold_days,
                            profit_threshold=profit_threshold,
                            loss_threshold=loss_threshold
                        )
                        
                        stats = result['总体统计']
                        
                        # 计算综合评分 (成功率 * 0.6 + 盈亏比 * 20)
                        score = stats['成功率'] * 0.6 + min(stats['盈亏比'], 5) * 20
                        
                        optimization_results.append({
                            '持有天数': hold_days,
                            '盈利阈值': profit_threshold,
                            '亏损阈值': loss_threshold,
                            '成功率': stats['成功率'],
                            '盈亏比': stats['盈亏比'],
                            '综合评分': score,
                            '总信号数': stats['总信号数']
                        })
                        
                        # 更新最优结果
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'hold_days': hold_days,
                                'profit_threshold': profit_threshold,
                                'loss_threshold': loss_threshold
                            }
                            best_result = result
                    
                    except Exception as e:
                        print(f"参数优化失败: {e}")
                        continue
        
        # 转换为DataFrame
        opt_df = pd.DataFrame(optimization_results)
        if not opt_df.empty:
            opt_df = opt_df.sort_values('综合评分', ascending=False)
        
        return {
            '最优参数': best_params,
            '最优结果': best_result,
            '所有结果': opt_df
        }
    
    def calculate_risk_metrics(self, backtest_result):
        """
        计算风险指标
        
        Args:
            backtest_result: 回测结果
        
        Returns:
            风险指标字典
        """
        detail_df = backtest_result['总体统计']['详细统计']
        
        if detail_df.empty:
            return {
                '最大回撤': 0,
                '夏普比率': 0,
                '卡尔马比率': 0,
                '波动率': 0,
                '胜率': 0
            }
        
        returns = detail_df['收益率'].values / 100  # 转换为小数
        
        # 计算累计收益曲线
        cumulative_returns = (1 + returns).cumprod()
        
        # 转换为pandas Series以便使用expanding()
        cumulative_returns_series = pd.Series(cumulative_returns)
        
        # 最大回撤
        peak = cumulative_returns_series.expanding().max()
        drawdown = (peak - cumulative_returns_series) / peak
        max_drawdown = drawdown.max()
        
        # 年化收益率
        total_return = cumulative_returns[-1] - 1
        avg_daily_return = returns.mean()
        annualized_return = (1 + avg_daily_return) ** 252 - 1
        
        # 波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 卡尔马比率
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
        
        # 胜率
        win_rate = backtest_result['总体统计']['成功率'] / 100
        
        return {
            '最大回撤': round(max_drawdown * 100, 2),
            '夏普比率': round(sharpe_ratio, 2),
            '卡尔马比率': round(calmar_ratio, 2),
            '波动率': round(volatility * 100, 2),
            '年化收益率': round(annualized_return * 100, 2),
            '胜率': round(win_rate * 100, 2)
        }
    
    def analyze_pattern_combination(self, df, patterns=['dragon', 'box', 'double_bottom'], 
                                   hold_days=5, profit_threshold=0.03, loss_threshold=-0.03):
        """
        战法组合分析 - 分析多个战法组合使用的效果
        
        Args:
            df: 历史K线数据
            patterns: 战法列表
            hold_days: 持有天数
            profit_threshold: 盈利阈值
            loss_threshold: 亏损阈值
        
        Returns:
            战法组合分析结果
        """
        single_results = {}
        combination_signals = []
        
        # 单个战法回测
        for pattern in patterns:
            result = self.run_pattern_backtest(
                df, pattern_type=pattern,
                hold_days=hold_days,
                profit_threshold=profit_threshold,
                loss_threshold=loss_threshold
            )
            single_results[pattern] = result
            
            # 收集信号
            if result['所有信号']:
                for signal in result['所有信号']:
                    signal['战法'] = pattern
                    combination_signals.append(signal)
        
        # 战法组合策略:当多个战法同时发出信号时才买入
        if combination_signals:
            signal_df = pd.DataFrame(combination_signals)
            signal_df['日期'] = pd.to_datetime(signal_df['date'])
            
            # 按日期分组,统计每天的信号数量
            daily_signals = signal_df.groupby('日期').agg({
                'pattern': list,
                'price': 'first',
                'type': 'first'
            }).reset_index()
            
            # 找出多个战法同时发出的信号
            combined_signals = daily_signals[daily_signals['pattern'].apply(len) >= 2]
            
            # 计算组合信号的成功率
            if not combined_signals.empty:
                combined_success = 0
                combined_total = len(combined_signals)
                
                for _, row in combined_signals.iterrows():
                    signal_date = row['日期']
                    signal_price = row['price']
                    
                    # 找到该日期在df中的索引
                    signal_idx = df[df['date'] == signal_date].index
                    if len(signal_idx) > 0:
                        signal_idx = signal_idx[0]
                        end_idx = min(signal_idx + hold_days, len(df) - 1)
                        
                        if end_idx > signal_idx:
                            end_price = df.iloc[end_idx]['close']
                            return_pct = (end_price - signal_price) / signal_price
                            
                            if return_pct >= profit_threshold:
                                combined_success += 1
                
                combination_success_rate = combined_success / combined_total * 100 if combined_total > 0 else 0
            else:
                combination_success_rate = 0
        else:
            combination_success_rate = 0
        
        # 战法相关性分析
        correlation_data = []
        for i, pattern1 in enumerate(patterns):
            for pattern2 in patterns[i+1:]:
                # 计算两个战法信号的重叠度
                if pattern1 in single_results and pattern2 in single_results:
                    signals1 = set([s['date'] for s in single_results[pattern1]['所有信号']])
                    signals2 = set([s['date'] for s in single_results[pattern2]['所有信号']])
                    
                    if signals1 and signals2:
                        overlap = len(signals1 & signals2)
                        union = len(signals1 | signals2)
                        jaccard = overlap / union if union > 0 else 0
                    else:
                        jaccard = 0
                    
                    correlation_data.append({
                        '战法1': pattern1,
                        '战法2': pattern2,
                        '重叠信号数': overlap if signals1 and signals2 else 0,
                        'Jaccard相似度': round(jaccard, 3)
                    })
        
        correlation_df = pd.DataFrame(correlation_data)
        
        return {
            '单个战法结果': single_results,
            '组合策略成功率': round(combination_success_rate, 2),
            '组合信号数': len(combined_signals) if not combined_signals.empty else 0,
            '相关性分析': correlation_df
        }
    
    def compare_backtests(self, backtest_results):
        """
        回测对比功能 - 对比不同参数或不同策略的回测结果
        
        Args:
            backtest_results: 回测结果列表,每个元素包含结果和描述
        
        Returns:
            对比结果
        """
        comparison_data = []
        
        for i, result in enumerate(backtest_results):
            stats = result['结果']['总体统计']
            risk_metrics = self.calculate_risk_metrics(result['结果'])
            
            comparison_data.append({
                '策略名称': result.get('名称', f'策略{i+1}'),
                '总信号数': stats['总信号数'],
                '成功率': stats['成功率'],
                '平均盈利': stats['平均盈利'],
                '平均亏损': stats['平均亏损'],
                '盈亏比': stats['盈亏比'],
                '最大回撤': risk_metrics['最大回撤'],
                '夏普比率': risk_metrics['夏普比率'],
                '卡尔马比率': risk_metrics['卡尔马比率']
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        return {
            '对比表格': comparison_df,
            '最优策略': comparison_df.loc[comparison_df['成功率'].idxmax()].to_dict() if not comparison_df.empty else None
        }
    
    def export_backtest_results(self, backtest_result, file_path=None):
        """
        导出回测结果
        
        Args:
            backtest_result: 回测结果
            file_path: 导出文件路径,如果为None则返回Excel对象
        
        Returns:
            Excel文件对象或文件路径
        """
        import io
        
        # 创建Excel写入器
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 写入总体统计
            stats_df = pd.DataFrame([backtest_result['总体统计']])
            stats_df.to_excel(writer, sheet_name='总体统计', index=False)
            
            # 写入分战法统计
            if not backtest_result['分战法统计'].empty:
                backtest_result['分战法统计'].to_excel(writer, sheet_name='分战法统计')
            
            # 写入详细信号记录
            if not backtest_result['总体统计']['详细统计'].empty:
                backtest_result['总体统计']['详细统计'].to_excel(writer, sheet_name='详细信号记录')
            
            # 写入所有信号
            if backtest_result['所有信号']:
                signals_df = pd.DataFrame(backtest_result['所有信号'])
                signals_df.to_excel(writer, sheet_name='所有信号')
        
        output.seek(0)
        
        if file_path:
            with open(file_path, 'wb') as f:
                f.write(output.getvalue())
            return file_path
        else:
            return output
    
    def _get_stock_name(self, symbol):
        """获取股票名称"""
        try:
            from logic.core.algo import QuantAlgo
            return QuantAlgo.get_stock_name(symbol)
        except:
            return symbol
    
    def detect_swing_signals(self, df, ma_short=5, ma_long=20, rsi_period=14, 
                           rsi_oversold=30, rsi_overbought=70):
        """
        检测短线波段信号
        
        策略逻辑:
        1. 买入信号: 短期均线上穿长期均线(金叉) 且 RSI超卖反弹
        2. 卖出信号: 短期均线下穿长期均线(死叉) 或 RSI超买 或 达到目标收益
        
        Args:
            df: 历史K线数据
            ma_short: 短期均线周期
            ma_long: 长期均线周期
            rsi_period: RSI周期
            rsi_oversold: RSI超卖阈值
            rsi_overbought: RSI超买阈值
        
        Returns:
            信号列表
        """
        if len(df) < ma_long + 10:
            return []
        
        signals = []
        
        # 计算技术指标
        df['ma_short'] = df['close'].rolling(window=ma_short).mean()
        df['ma_long'] = df['close'].rolling(window=ma_long).mean()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 检测信号
        for i in range(ma_long, len(df)):
            current_price = df.iloc[i]['close']
            current_date = df.iloc[i]['date']
            
            # 金叉信号
            if (df.iloc[i]['ma_short'] > df.iloc[i]['ma_long'] and 
                df.iloc[i-1]['ma_short'] <= df.iloc[i-1]['ma_long']):
                
                # 检查RSI条件
                rsi_value = df.iloc[i]['rsi']
                if rsi_value < rsi_overbought:  # RSI不过热
                    signals.append({
                        'date': current_date,
                        'pattern': '波段买入',
                        'type': '买入',
                        'price': current_price,
                        'ma_short': df.iloc[i]['ma_short'],
                        'ma_long': df.iloc[i]['ma_long'],
                        'rsi': rsi_value,
                        'macd': df.iloc[i]['macd'],
                        '触发原因': '均线金叉'
                    })
            
            # 死叉信号
            elif (df.iloc[i]['ma_short'] < df.iloc[i]['ma_long'] and 
                  df.iloc[i-1]['ma_short'] >= df.iloc[i-1]['ma_long']):
                
                signals.append({
                    'date': current_date,
                    'pattern': '波段卖出',
                    'type': '卖出',
                    'price': current_price,
                    'ma_short': df.iloc[i]['ma_short'],
                    'ma_long': df.iloc[i]['ma_long'],
                    'rsi': df.iloc[i]['rsi'],
                    'macd': df.iloc[i]['macd'],
                    '触发原因': '均线死叉'
                })
            
            # RSI超卖反弹
            elif (df.iloc[i]['rsi'] < rsi_oversold and 
                  df.iloc[i-1]['rsi'] >= rsi_oversold):
                
                signals.append({
                    'date': current_date,
                    'pattern': '波段买入',
                    'type': '买入',
                    'price': current_price,
                    'ma_short': df.iloc[i]['ma_short'],
                    'ma_long': df.iloc[i]['ma_long'],
                    'rsi': df.iloc[i]['rsi'],
                    'macd': df.iloc[i]['macd'],
                    '触发原因': 'RSI超卖反弹'
                })
            
            # RSI超买
            elif (df.iloc[i]['rsi'] > rsi_overbought and 
                  df.iloc[i-1]['rsi'] <= rsi_overbought):
                
                signals.append({
                    'date': current_date,
                    'pattern': '波段卖出',
                    'type': '卖出',
                    'price': current_price,
                    'ma_short': df.iloc[i]['ma_short'],
                    'ma_long': df.iloc[i]['ma_long'],
                    'rsi': df.iloc[i]['rsi'],
                    'macd': df.iloc[i]['macd'],
                    '触发原因': 'RSI超买'
                })
            
            # MACD金叉
            elif (df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and 
                  df.iloc[i-1]['macd'] <= df.iloc[i-1]['macd_signal']):
                
                signals.append({
                    'date': current_date,
                    'pattern': '波段买入',
                    'type': '买入',
                    'price': current_price,
                    'ma_short': df.iloc[i]['ma_short'],
                    'ma_long': df.iloc[i]['ma_long'],
                    'rsi': df.iloc[i]['rsi'],
                    'macd': df.iloc[i]['macd'],
                    '触发原因': 'MACD金叉'
                })
            
            # MACD死叉
            elif (df.iloc[i]['macd'] < df.iloc[i]['macd_signal'] and 
                  df.iloc[i-1]['macd'] >= df.iloc[i-1]['macd_signal']):
                
                signals.append({
                    'date': current_date,
                    'pattern': '波段卖出',
                    'type': '卖出',
                    'price': current_price,
                    'ma_short': df.iloc[i]['ma_short'],
                    'ma_long': df.iloc[i]['ma_long'],
                    'rsi': df.iloc[i]['rsi'],
                    'macd': df.iloc[i]['macd'],
                    '触发原因': 'MACD死叉'
                })
        
        return signals
    
    def run_swing_strategy_backtest(self, df, ma_short=5, ma_long=20, rsi_period=14,
                                   rsi_oversold=30, rsi_overbought=70,
                                   stop_loss_pct=0.05, take_profit_pct=0.10,
                                   max_hold_days=10):
        """
        运行短线波段策略回测
        
        Args:
            df: 历史K线数据
            ma_short: 短期均线周期
            ma_long: 长期均线周期
            rsi_period: RSI周期
            rsi_oversold: RSI超卖阈值
            rsi_overbought: RSI超买阈值
            stop_loss_pct: 止损百分比
            take_profit_pct: 止盈百分比
            max_hold_days: 最大持仓天数
        
        Returns:
            回测结果
        """
        # 检测信号
        signals = self.detect_swing_signals(df, ma_short, ma_long, rsi_period, 
                                           rsi_oversold, rsi_overbought)
        
        if not signals:
            return {
                '交易次数': 0,
                '成功率': 0,
                '总收益率': 0,
                '最大回撤': 0,
                '交易记录': pd.DataFrame()
            }
        
        # 模拟交易
        trades = []
        position = None  # 当前持仓
        
        for i, signal in enumerate(signals):
            if signal['type'] == '买入' and position is None:
                # 开仓
                position = {
                    '买入日期': signal['date'],
                    '买入价格': signal['price'],
                    '触发原因': signal['触发原因'],
                    'ma_short': signal['ma_short'],
                    'ma_long': signal['ma_long'],
                    'rsi': signal['rsi'],
                    'macd': signal['macd']
                }
            
            elif signal['type'] == '卖出' and position is not None:
                # 平仓
                sell_price = signal['price']
                sell_date = signal['date']
                sell_reason = signal['触发原因']
                
                # 计算收益
                return_pct = (sell_price - position['买入价格']) / position['买入价格']
                
                trades.append({
                    '买入日期': position['买入日期'],
                    '卖出日期': sell_date,
                    '买入价格': position['买入价格'],
                    '卖出价格': sell_price,
                    '收益率': round(return_pct * 100, 2),
                    '持仓天数': self._calculate_hold_days(position['买入日期'], sell_date, df),
                    '买入触发': position['触发原因'],
                    '卖出触发': sell_reason,
                    '买入RSI': round(position['rsi'], 2),
                    '买入MACD': round(position['macd'], 4)
                })
                
                position = None
        
        # 检查未平仓的持仓
        if position is not None:
            last_date = df.iloc[-1]['date']
            last_price = df.iloc[-1]['close']
            return_pct = (last_price - position['买入价格']) / position['买入价格']
            
            trades.append({
                '买入日期': position['买入日期'],
                '卖出日期': last_date,
                '买入价格': position['买入价格'],
                '卖出价格': last_price,
                '收益率': round(return_pct * 100, 2),
                '持仓天数': self._calculate_hold_days(position['买入日期'], last_date, df),
                '买入触发': position['触发原因'],
                '卖出触发': '未平仓',
                '买入RSI': round(position['rsi'], 2),
                '买入MACD': round(position['macd'], 4)
            })
        
        # 计算统计数据
        if not trades:
            return {
                '交易次数': 0,
                '成功率': 0,
                '总收益率': 0,
                '最大回撤': 0,
                '交易记录': pd.DataFrame()
            }
        
        trades_df = pd.DataFrame(trades)
        
        # 成功率
        successful_trades = trades_df[trades_df['收益率'] > 0]
        success_rate = len(successful_trades) / len(trades_df) * 100
        
        # 总收益率
        total_return = (1 + trades_df['收益率'] / 100).prod() - 1
        
        # 最大回撤
        cumulative_returns = (1 + trades_df['收益率'] / 100).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (peak - cumulative_returns) / peak
        max_drawdown = drawdown.max()
        
        return {
            '交易次数': len(trades_df),
            '成功率': round(success_rate, 2),
            '总收益率': round(total_return * 100, 2),
            '平均收益率': round(trades_df['收益率'].mean(), 2),
            '最大盈利': round(trades_df['收益率'].max(), 2),
            '最大亏损': round(trades_df['收益率'].min(), 2),
            '平均持仓天数': round(trades_df['持仓天数'].mean(), 1),
            '最大回撤': round(max_drawdown * 100, 2),
            '交易记录': trades_df
        }
    
    def _calculate_hold_days(self, start_date, end_date, df):
        """计算持仓天数"""
        try:
            start_idx = df[df['date'] == start_date].index[0]
            end_idx = df[df['date'] == end_date].index[0]
            return end_idx - start_idx
        except:
            return 0