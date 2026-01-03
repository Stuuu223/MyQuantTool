import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

class QuantAlgo:

    # 股票名称缓存

    _stock_names_cache = {}

    

    @staticmethod

    def get_stock_name(symbol):

        """

        获取股票名称

        symbol: 股票代码（6位数字）

        """

        try:

            # 检查缓存

            if symbol in QuantAlgo._stock_names_cache:

                return QuantAlgo._stock_names_cache[symbol]

            

            import akshare as ak

            

            # 获取A股代码名称表

            stock_info_df = ak.stock_info_a_code_name()

            

            # 查找股票名称

            stock_row = stock_info_df[stock_info_df['code'] == symbol]

            

            if not stock_row.empty:

                stock_name = stock_row.iloc[0]['name']

                # 缓存结果

                QuantAlgo._stock_names_cache[symbol] = stock_name

                return stock_name

            else:

                return f"未知股票({symbol})"

        except Exception as e:

            return f"查询失败({symbol})"

    

    @staticmethod

    def detect_box_pattern(df, lookback=20):
        """
        检测箱体震荡模式
        返回箱体上下边界和当前状态
        """
        if len(df) < lookback:
            return {
                'is_box': False,
                'message': '数据不足，无法判断箱体'
            }
        
        # 取最近 lookback 天的数据
        recent_df = df.tail(lookback)
        
        # 计算箱体
        box_high = recent_df['high'].max()
        box_low = recent_df['low'].min()
        box_width = box_high - box_low
        
        # 计算当前价格相对箱体的位置
        current_price = df.iloc[-1]['close']
        
        # 判断是否在箱体内
        if current_price >= box_low and current_price <= box_high:
            position_pct = ((current_price - box_low) / box_width) * 100
            
            # 判断箱体是否有效（价格波动在合理范围内）
            price_volatility = box_width / box_low
            if price_volatility < 0.05:  # 波动小于5%，太窄
                return {
                    'is_box': False,
                    'message': '波动太小，无明显箱体'
                }
            
            # 判断是否在箱体震荡
            # 检查最近几天的价格是否在箱体内
            last_5_days_in_box = sum(
                1 for i in range(min(5, len(df)))
                if df.iloc[-i-1]['close'] >= box_low and df.iloc[-i-1]['close'] <= box_high
            )
            
            if last_5_days_in_box >= 3:  # 最近5天有3天在箱体内
                return {
                    'is_box': True,
                    'box_high': round(box_high, 2),
                    'box_low': round(box_low, 2),
                    'box_width': round(box_width, 2),
                    'current_price': round(current_price, 2),
                    'position_pct': round(position_pct, 1),
                    'message': f'箱体震荡中 [{box_low:.2f}, {box_high:.2f}]'
                }
        
        # 检查是否突破箱体
        if current_price > box_high:
            return {
                'is_box': False,
                'is_breakout_up': True,
                'box_high': round(box_high, 2),
                'box_low': round(box_low, 2),
                'current_price': round(current_price, 2),
                'breakout_pct': round(((current_price - box_high) / box_high) * 100, 2),
                'message': f'⬆️ 向上突破箱体！突破价 {box_high:.2f}'
            }
        
        if current_price < box_low:
            return {
                'is_box': False,
                'is_breakout_down': True,
                'box_high': round(box_high, 2),
                'box_low': round(box_low, 2),
                'current_price': round(current_price, 2),
                'breakout_pct': round(((box_low - current_price) / box_low) * 100, 2),
                'message': f'⬇️ 向下突破箱体！跌破价 {box_low:.2f}'
            }
        
        return {
            'is_box': False,
            'message': '无明显箱体模式'
        }

    @staticmethod
    def detect_double_bottom(df, window=20):
        """
        检测双底形态
        双底：两次探底，第二次探底不创新低，形成W形
        """
        if len(df) < window * 2:
            return {'is_double_bottom': False, 'message': '数据不足'}
        
        # 寻找局部低点
        lows = df['low'].rolling(window=5, center=True).apply(
            lambda x: x[2] == min(x), raw=True
        )
        low_points = df[lows == 1]['low'].tolist()
        
        if len(low_points) < 2:
            return {'is_double_bottom': False, 'message': '未找到足够的低点'}
        
        # 检查最近的两个低点
        recent_lows = low_points[-2:]
        if len(recent_lows) >= 2:
            # 第二个低点不低于第一个低点太多（允许小幅波动）
            if abs(recent_lows[1] - recent_lows[0]) / recent_lows[0] < 0.05:
                return {
                    'is_double_bottom': True,
                    'first_bottom': round(recent_lows[0], 2),
                    'second_bottom': round(recent_lows[1], 2),
                    'message': f'⬆️ 双底形态形成！底部 {recent_lows[0]:.2f} 和 {recent_lows[1]:.2f}'
                }
        
        return {'is_double_bottom': False, 'message': '未检测到双底形态'}

    @staticmethod
    def detect_double_top(df, window=20):
        """
        检测双顶形态
        双顶：两次冲高，第二次冲高不创新高，形成M形
        """
        if len(df) < window * 2:
            return {'is_double_top': False, 'message': '数据不足'}
        
        # 寻找局部高点
        highs = df['high'].rolling(window=5, center=True).apply(
            lambda x: x[2] == max(x), raw=True
        )
        high_points = df[highs == 1]['high'].tolist()
        
        if len(high_points) < 2:
            return {'is_double_top': False, 'message': '未找到足够的高点'}
        
        # 检查最近的两个高点
        recent_highs = high_points[-2:]
        if len(recent_highs) >= 2:
            # 第二个高点不高于第一个高点太多
            if abs(recent_highs[1] - recent_highs[0]) / recent_highs[0] < 0.05:
                return {
                    'is_double_top': True,
                    'first_top': round(recent_highs[0], 2),
                    'second_top': round(recent_highs[1], 2),
                    'message': f'⬇️ 双顶形态形成！顶部 {recent_highs[0]:.2f} 和 {recent_highs[1]:.2f}'
                }
        
        return {'is_double_top': False, 'message': '未检测到双顶形态'}

    @staticmethod
    def detect_head_shoulders(df, window=30):
        """
        检测头肩顶/头肩底形态
        头肩顶：三个高点，中间最高（头），两边较低（肩）
        头肩底：三个低点，中间最低（头），两边较高（肩）
        """
        if len(df) < window * 3:
            return {'pattern': None, 'message': '数据不足'}
        
        # 寻找极值点
        highs = df['high'].rolling(window=5, center=True).apply(
            lambda x: x[2] == max(x), raw=True
        )
        lows = df['low'].rolling(window=5, center=True).apply(
            lambda x: x[2] == min(x), raw=True
        )
        
        high_points = df[highs == 1]['high'].tolist()
        low_points = df[lows == 1]['low'].tolist()
        
        # 检测头肩顶（需要至少3个高点）
        if len(high_points) >= 3:
            recent_highs = high_points[-3:]
            # 中间最高，两边较低
            if recent_highs[1] > recent_highs[0] and recent_highs[1] > recent_highs[2]:
                return {
                    'pattern': 'head_shoulders_top',
                    'left_shoulder': round(recent_highs[0], 2),
                    'head': round(recent_highs[1], 2),
                    'right_shoulder': round(recent_highs[2], 2),
                    'message': f'⚠️ 头肩顶形态！左肩 {recent_highs[0]:.2f}，头部 {recent_highs[1]:.2f}，右肩 {recent_highs[2]:.2f}'
                }
        
        # 检测头肩底（需要至少3个低点）
        if len(low_points) >= 3:
            recent_lows = low_points[-3:]
            # 中间最低，两边较高
            if recent_lows[1] < recent_lows[0] and recent_lows[1] < recent_lows[2]:
                return {
                    'pattern': 'head_shoulders_bottom',
                    'left_shoulder': round(recent_lows[0], 2),
                    'head': round(recent_lows[1], 2),
                    'right_shoulder': round(recent_lows[2], 2),
                    'message': f'✅ 头肩底形态！左肩 {recent_lows[0]:.2f}，头部 {recent_lows[1]:.2f}，右肩 {recent_lows[2]:.2f}'
                }
        
        return {'pattern': None, 'message': '未检测到头肩形态'}
    
    @staticmethod
    def calculate_resistance_support(df, n_clusters=5):
        if len(df) < 30: return []
        
        df['is_high'] = df['high'].rolling(window=5, center=True).apply(lambda x: x[2] == max(x), raw=True)
        df['is_low'] = df['low'].rolling(window=5, center=True).apply(lambda x: x[2] == min(x), raw=True)
        
        pivot_points = []
        pivot_points.extend(df[df['is_high'] == 1]['high'].tolist())
        pivot_points.extend(df[df['is_low'] == 1]['low'].tolist())
        
        if not pivot_points: return []

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        data = np.array(pivot_points).reshape(-1, 1)
        kmeans.fit(data)
        
        key_levels = sorted(kmeans.cluster_centers_.flatten().tolist())
        return key_levels

    @staticmethod
    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean().iloc[-1]

    @staticmethod
    def calculate_macd(df, fast=12, slow=26, signal=9):
        """计算 MACD 指标"""
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return {
            'MACD': round(macd.iloc[-1], 4),
            'Signal': round(signal_line.iloc[-1], 4),
            'Histogram': round(histogram.iloc[-1], 4),
            'Trend': '多头' if macd.iloc[-1] > signal_line.iloc[-1] else '空头'
        }

    @staticmethod
    def calculate_rsi(df, period=14):
        """计算 RSI 相对强弱指标"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_value = rsi.iloc[-1]
        
        # RSI 解读
        if rsi_value > 70:
            signal = '超买，可能回调'
        elif rsi_value < 30:
            signal = '超卖，可能反弹'
        else:
            signal = '正常区间'
        
        return {
            'RSI': round(rsi_value, 2),
            'Signal': signal
        }

    @staticmethod
    def calculate_bollinger_bands(df, period=20, std_dev=2):
        """计算布林带"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = df['close'].iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]
        
        # 布林带位置解读
        position_pct = ((current_price - current_lower) / (current_upper - current_lower)) * 100
        
        if position_pct > 80:
            position = '接近上轨，注意风险'
        elif position_pct < 20:
            position = '接近下轨，可能反弹'
        else:
            position = '在中轨附近震荡'
        
        return {
            '上轨': round(current_upper, 2),
            '中轨': round(current_sma, 2),
            '下轨': round(current_lower, 2),
            '当前位置': round(position_pct, 1),
            '解读': position
        }

    @staticmethod
    def generate_grid_strategy(current_price, atr):
        grid_width_val = atr * 0.5 
        
        plan = {
            "基准价": current_price,
            "网格宽度": round(grid_width_val, 2),
            "买入挂单": round(current_price - grid_width_val, 2),
            "卖出挂单": round(current_price + grid_width_val, 2),
            "止损红线": round(current_price - grid_width_val * 3, 2)
        }
        
        return plan

    @staticmethod
    def calculate_kdj(df, n=9, m1=3, m2=3):
        """
        计算 KDJ 指标
        KDJ 是一种超买超卖指标，结合了动量、强弱指标和移动平均线的优点
        """
        low_list = df['low'].rolling(window=n, min_periods=1).min()
        high_list = df['high'].rolling(window=n, min_periods=1).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        k_value = k.iloc[-1]
        d_value = d.iloc[-1]
        j_value = j.iloc[-1]
        
        # KDJ 信号判断
        signal = "正常"
        if k_value > 80 and d_value > 80:
            signal = "超买，注意风险"
        elif k_value < 20 and d_value < 20:
            signal = "超卖，可能反弹"
        elif k_value > d_value and j_value > 0:
            signal = "金叉，买入信号"
        elif k_value < d_value and j_value < 0:
            signal = "死叉，卖出信号"
        
        return {
            'K': round(k_value, 2),
            'D': round(d_value, 2),
            'J': round(j_value, 2),
            '信号': signal
        }

    @staticmethod
    def analyze_volume(df, period=5):
        """
        分析成交量
        判断成交量是否异常放大
        """
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(window=period).mean().iloc[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # 成交量判断
        if volume_ratio > 2:
            signal = "放量显著"
            meaning = "成交量放大超过2倍，关注主力动向"
        elif volume_ratio > 1.5:
            signal = "温和放量"
            meaning = "成交量温和放大，资金参与度提升"
        elif volume_ratio < 0.5:
            signal = "缩量"
            meaning = "成交量萎缩，观望为主"
        else:
            signal = "正常"
            meaning = "成交量在正常范围内"
        
        return {
            '当前成交量': current_volume,
            '平均成交量': avg_volume,
            '量比': round(volume_ratio, 2),
            '信号': signal,
            '含义': meaning
        }

    @staticmethod
    def analyze_money_flow(df, symbol="600519", market="sh"):
        """
        分析资金流向（真实数据）
        使用 AkShare 获取真实的资金流向数据
        """
        try:
            import akshare as ak
            
            # 获取个股资金流向数据
            fund_flow_df = ak.stock_individual_fund_flow(stock=symbol, market=market)
            
            if fund_flow_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制或股票代码错误'
                }
            
            # 获取最新的数据
            latest_data = fund_flow_df.iloc[0]
            
            # 计算总资金流向
            total_net_flow = (
                latest_data['主力净流入-净额'] +
                latest_data['超大单净流入-净额'] +
                latest_data['大单净流入-净额'] +
                latest_data['中单净流入-净额'] +
                latest_data['小单净流入-净额']
            )
            
            # 判断资金流向
            if total_net_flow > 0:
                flow_type = "净流入"
                meaning = "资金净流入，主力看好"
            elif total_net_flow < 0:
                flow_type = "净流出"
                meaning = "资金净流出，主力看空"
            else:
                flow_type = "持平"
                meaning = "资金进出平衡"
            
            return {
                '数据状态': '正常',
                '日期': latest_data['日期'],
                '收盘价': latest_data['收盘价'],
                '涨跌幅': latest_data['涨跌幅'],
                '主力净流入-净额': latest_data['主力净流入-净额'],
                '主力净流入-净占比': latest_data['主力净流入-净占比'],
                '超大单净流入-净额': latest_data['超大单净流入-净额'],
                '超大单净流入-净占比': latest_data['超大单净流入-净占比'],
                '大单净流入-净额': latest_data['大单净流入-净额'],
                '大单净流入-净占比': latest_data['大单净流入-净占比'],
                '中单净流入-净额': latest_data['中单净流入-净额'],
                '中单净流入-净占比': latest_data['中单净流入-净占比'],
                '小单净流入-净额': latest_data['小单净流入-净额'],
                '小单净流入-净占比': latest_data['小单净流入-净占比'],
                '资金流向': flow_type,
                '说明': meaning
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    @staticmethod
    def get_sector_rotation():
        """
        获取板块轮动数据
        返回各行业板块的资金流向和涨跌幅
        """
        try:
            import akshare as ak
            
            # 获取行业板块资金流向排名
            sector_flow_df = ak.stock_sector_fund_flow_rank()
            
            if sector_flow_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制'
                }
            
            # 转换数据为列表格式（使用列索引避免中文乱码）
            sectors = []
            for _, row in sector_flow_df.head(20).iterrows():  # 取前20个板块
                sectors.append({
                    '板块名称': row.iloc[1],  # 板块名称
                    '涨跌幅': row.iloc[2],    # 涨跌幅
                    '主力净流入': row.iloc[3],  # 主力净流入-净额
                    '主力净流入占比': row.iloc[4]  # 主力净流入-净占比
                })
            
            return {
                '数据状态': '正常',
                '板块列表': sectors
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    @staticmethod
    def get_lhb_data(date=None):
        """
        获取龙虎榜数据
        date: 日期，格式 YYYY-MM-DD，默认为最新交易日
        """
        try:
            import akshare as ak
            
            # 获取新浪龙虎榜每日详情
            lhb_df = ak.stock_lhb_detail_daily_sina()
            
            if lhb_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制或非交易日'
                }
            
            # 转换数据为列表格式（使用列索引避免中文乱码）
            stocks = []
            for _, row in lhb_df.head(30).iterrows():  # 取前30只股票
                stocks.append({
                    '代码': row.iloc[1],      # 股票代码
                    '名称': row.iloc[2],      # 股票名称
                    '收盘价': row.iloc[3],    # 收盘价
                    '涨跌幅': row.iloc[4],    # 对应值（涨跌幅）
                    '龙虎榜净买入': row.iloc[6],  # 净买入
                    '上榜原因': row.iloc[7],  # 指数（上榜原因）
                    '机构买入': 0,  # 该接口不提供机构买卖数据
                    '机构卖出': 0
                })
            
            return {
                '数据状态': '正常',
                '股票列表': stocks
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    @staticmethod
    def generate_trading_plan(df, symbol="600519"):
        """
        生成个股操作预案
        基于技术指标和形态识别，生成买入点、卖出点、止损点、止盈点
        """
        try:
            current_price = df.iloc[-1]['close']
            
            # 计算各项技术指标
            atr = QuantAlgo.calculate_atr(df)
            macd_data = QuantAlgo.calculate_macd(df)
            rsi_data = QuantAlgo.calculate_rsi(df)
            bollinger_data = QuantAlgo.calculate_bollinger_bands(df)
            kdj_data = QuantAlgo.calculate_kdj(df)
            volume_data = QuantAlgo.analyze_volume(df)
            money_flow_data = QuantAlgo.analyze_money_flow(df, symbol=symbol, market="sh" if symbol.startswith("6") else "sz")
            
            # 形态识别
            box_pattern = QuantAlgo.detect_box_pattern(df)
            double_bottom = QuantAlgo.detect_double_bottom(df)
            double_top = QuantAlgo.detect_double_top(df)
            head_shoulders = QuantAlgo.detect_head_shoulders(df)
            
            # 生成操作建议
            plan = {
                '股票代码': symbol,
                '当前价格': current_price,
                '操作建议': '观望',
                '买入点': None,
                '卖出点': None,
                '止损点': None,
                '止盈点': None,
                '风险等级': '中等',
                '持仓周期': '短期',
                '分析依据': []
            }
            
            # 综合分析
            signals = []
            
            # MACD信号
            if macd_data['Trend'] == '多头':
                signals.append({'指标': 'MACD', '信号': '看多', '强度': '强'})
                plan['操作建议'] = '买入'
            elif macd_data['Trend'] == '空头':
                signals.append({'指标': 'MACD', '信号': '看空', '强度': '强'})
                plan['操作建议'] = '卖出'
            
            # RSI信号
            if rsi_data['RSI'] < 30:
                signals.append({'指标': 'RSI', '信号': '超卖', '强度': '中'})
                if plan['操作建议'] == '观望':
                    plan['操作建议'] = '考虑买入'
            elif rsi_data['RSI'] > 70:
                signals.append({'指标': 'RSI', '信号': '超买', '强度': '中'})
                if plan['操作建议'] == '观望':
                    plan['操作建议'] = '考虑卖出'
            
            # KDJ信号
            if '金叉' in kdj_data['信号']:
                signals.append({'指标': 'KDJ', '信号': '金叉', '强度': '中'})
            elif '死叉' in kdj_data['信号']:
                signals.append({'指标': 'KDJ', '信号': '死叉', '强度': '中'})
            
            # 布林带信号
            if current_price < bollinger_data['下轨']:
                signals.append({'指标': '布林带', '信号': '触及下轨', '强度': '强'})
                plan['操作建议'] = '买入'
            elif current_price > bollinger_data['上轨']:
                signals.append({'指标': '布林带', '信号': '触及上轨', '强度': '强'})
                plan['操作建议'] = '卖出'
            
            # 成交量信号
            if volume_data['信号'] == '放量显著' or volume_data['信号'] == '温和放量':
                signals.append({'指标': '成交量', '信号': '放量', '强度': '中'})
            elif volume_data['信号'] == '缩量':
                signals.append({'指标': '成交量', '信号': '缩量', '强度': '弱'})
            
            # 资金流向信号
            if money_flow_data['数据状态'] == '正常':
                if money_flow_data['资金流向'] == '净流入':
                    signals.append({'指标': '资金流向', '信号': '净流入', '强度': '强'})
                elif money_flow_data['资金流向'] == '净流出':
                    signals.append({'指标': '资金流向', '信号': '净流出', '强度': '强'})
            
            # 形态识别信号
            if box_pattern.get('is_breakout_up'):
                signals.append({'指标': '箱体形态', '信号': '向上突破', '强度': '强'})
                plan['操作建议'] = '买入'
            elif box_pattern.get('is_breakout_down'):
                signals.append({'指标': '箱体形态', '信号': '向下突破', '强度': '强'})
                plan['操作建议'] = '卖出'
            
            if double_bottom.get('is_double_bottom'):
                signals.append({'指标': '形态', '信号': '双底', '强度': '强'})
                plan['操作建议'] = '买入'
            
            if double_top.get('is_double_top'):
                signals.append({'指标': '形态', '信号': '双顶', '强度': '强'})
                plan['操作建议'] = '卖出'
            
            if head_shoulders.get('pattern') == 'head_shoulders_top':
                signals.append({'指标': '形态', '信号': '头肩顶', '强度': '强'})
                plan['操作建议'] = '卖出'
            elif head_shoulders.get('pattern') == 'head_shoulders_bottom':
                signals.append({'指标': '形态', '信号': '头肩底', '强度': '强'})
                plan['操作建议'] = '买入'
            
            # 计算买入点、卖出点、止损点、止盈点
            if plan['操作建议'] == '买入':
                plan['买入点'] = current_price
                plan['止损点'] = current_price - atr * 2  # ATR的2倍作为止损
                plan['止盈点'] = current_price + atr * 3  # ATR的3倍作为止盈
                plan['风险等级'] = '中等'
                plan['持仓周期'] = '短期（3-5天）'
            elif plan['操作建议'] == '卖出':
                plan['卖出点'] = current_price
                plan['风险等级'] = '低'
                plan['持仓周期'] = '空仓观望'
            
            # 如果有多个强势信号，提高风险等级
            strong_signals = [s for s in signals if s['强度'] == '强']
            if len(strong_signals) >= 2:
                plan['风险等级'] = '高'
                if plan['操作建议'] == '买入':
                    plan['持仓周期'] = '中期（1-2周）'
            
            plan['分析依据'] = signals
            
            return plan
        except Exception as e:
            return {
                '错误': str(e),
                '说明': '生成操作预案失败'
            }
