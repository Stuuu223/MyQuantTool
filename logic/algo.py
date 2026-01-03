import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

class QuantAlgo:
    
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
            "止损红线": round(current_price - grid_width_val * 3, 2),
            "操作建议": f"建议在 {round(current_price - grid_width_val, 2)} 买入底仓的1/10，在 {round(current_price + grid_width_val, 2)} 卖出同等数量。"
        }
        return plan
