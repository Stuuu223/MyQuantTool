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
    def check_stock_risks(symbol):
        """
        检查股票风险（扫雷）
        symbol: 股票代码（6位数字）
        """
        try:
            import akshare as ak
            
            risks = []
            risk_level = "低"  # 低、中、高
            
            # 1. 先尝试获取股票名称
            stock_name = QuantAlgo.get_stock_name(symbol)
            
            # 2. 检查退市股票（名称中包含"退"字或查询失败）
            if '退' in stock_name or '查询失败' in stock_name:
                risks.append("🔴 退市股票：已退市或即将退市，无法交易，强烈建议远离")
                risk_level = "高"
            
            # 3. 检查ST股票
            if 'ST' in stock_name or '*ST' in stock_name:
                if '*ST' in stock_name:
                    risks.append("🔴 *ST退市风险警示：退市风险极高，强烈建议远离")
                    risk_level = "高"
                else:
                    if risk_level != "高":
                        risks.append("🟠 ST特别处理：存在退市风险，建议谨慎")
                        risk_level = "高"
            
            # 4. 检查股票代码格式（9开头可能是退市股票）
            if symbol.startswith('9') and risk_level != "高":
                risks.append("🟠 北交所退市股票：代码以9开头，可能是退市股票")
                risk_level = "高"
            
            # 如果已经检测到高风险，直接返回
            if risk_level == "高":
                return {
                    '风险等级': risk_level,
                    '风险列表': risks,
                    '股票名称': stock_name
                }
            
            # 5. 尝试获取更多详细信息
            try:
                stock_info = ak.stock_individual_info_em(symbol=symbol)
                
                if not stock_info.empty:
                    # 转换为字典
                    info_dict = dict(zip(stock_info['item'], stock_info['value']))
                    
                    # 检查财务状况
                    # 检查是否亏损
                    profit = info_dict.get('净利润', '')
                    if profit and '-' in str(profit):
                        try:
                            profit_value = float(profit.replace('亿', '').replace('万', '').replace('元', ''))
                            if profit_value < -1:  # 亏损超过1亿
                                risks.append("🔴 严重亏损：净利润为负，亏损金额较大")
                                risk_level = "高"
                            else:
                                risks.append("🟡 净利润亏损：公司盈利能力较弱")
                                if risk_level == "低":
                                    risk_level = "中"
                        except:
                            risks.append("🟡 净利润亏损：公司盈利能力较弱")
                            if risk_level == "低":
                                risk_level = "中"
                    
                    # 检查负债率
                    debt_ratio = info_dict.get('负债率', '')
                    if debt_ratio:
                        try:
                            debt_value = float(debt_ratio.replace('%', ''))
                            if debt_value > 90:
                                risks.append("🔴 负债率极高：财务风险非常大")
                                risk_level = "高"
                            elif debt_value > 80:
                                risks.append("🟡 负债率过高：财务风险较大")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif debt_ratio > 60:
                                risks.append("🟢 负债率偏高：需关注财务状况")
                        except:
                            pass
                    
                    # 检查市盈率
                    pe = info_dict.get('市盈率-动态', '')
                    if pe:
                        try:
                            pe_value = float(pe)
                            if pe_value < 0:
                                risks.append("🟡 市盈率为负：公司亏损")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif pe_value > 100:
                                risks.append("🟢 市盈率过高：估值可能偏高")
                        except:
                            pass
                    
                    # 检查市净率
                    pb = info_dict.get('市净率', '')
                    if pb:
                        try:
                            pb_value = float(pb)
                            if pb_value < 1:
                                risks.append("🟢 市净率低于1：股价跌破净资产")
                            elif pb_value > 10:
                                risks.append("🟢 市净率过高：估值可能偏高")
                        except:
                            pass
                    
                    # 检查是否停牌
                    status = info_dict.get('交易状态', '')
                    if '停牌' in status:
                        risks.append("🔴 股票停牌：无法交易")
                        risk_level = "高"
                    
                    # 检查是否新股
                    listing_date = info_dict.get('上市日期', '')
                    if listing_date:
                        try:
                            from datetime import datetime
                            days_since_listing = (datetime.now() - datetime.strptime(listing_date, '%Y-%m-%d')).days
                            if days_since_listing < 180:  # 上市不到半年
                                risks.append("🟢 次新股：上市时间短，波动较大")
                        except:
                            pass
            except Exception as e:
                # 如果获取详细信息失败，不影响其他风险检测
                pass
            
            # 6. 检查公告风险（立案调查、诉讼仲裁等）
            try:
                announcements = ak.stock_news_em(symbol=symbol)
                if not announcements.empty:
                    risk_keywords = ['立案', '调查', '诉讼', '仲裁', '处罚', '违规', '退市', '停牌', 'ST', '*ST', '内控', '缺陷', '证监', '证监会']
                    found_risks = set()
                    risk_details = {}  # 存储具体的风险详情
                    
                    # 检查公告标题和内容
                    for idx in range(min(30, len(announcements))):  # 检查最近30条公告
                        title = str(announcements.iloc[idx, 1])
                        content = str(announcements.iloc[idx, 2])
                        date = str(announcements.iloc[idx, 3])
                        full_text = title + ' ' + content
                        
                        for keyword in risk_keywords:
                            if keyword in full_text:
                                if keyword not in found_risks:
                                    found_risks.add(keyword)
                                    # 保存具体的风险详情
                                    if keyword not in risk_details:
                                        risk_details[keyword] = []
                                    risk_details[keyword].append({
                                        '日期': date,
                                        '标题': title[:50] + '...' if len(title) > 50 else title
                                    })
                    
                    # 根据发现的关键词添加详细风险
                    if '立案' in found_risks or '调查' in found_risks:
                        details = risk_details.get('立案', []) + risk_details.get('调查', [])
                        details_str = '; '.join([f"{d['日期']}:{d['标题']}" for d in details[:2]])  # 只显示前2条
                        risks.append(f"🔴 立案调查风险：公司涉及立案调查，存在重大法律风险 ({details_str})")
                        risk_level = "高"
                    elif '内控' in found_risks and '缺陷' in found_risks:
                        details = risk_details.get('内控', []) + risk_details.get('缺陷', [])
                        details_str = '; '.join([f"{d['日期']}:{d['标题']}" for d in details[:2]])
                        risks.append(f"🟠 内控缺陷风险：公司内部控制存在缺陷 ({details_str})")
                        if risk_level == "低":
                            risk_level = "中"
                    elif '诉讼' in found_risks or '仲裁' in found_risks:
                        details = risk_details.get('诉讼', []) + risk_details.get('仲裁', [])
                        details_str = '; '.join([f"{d['日期']}:{d['标题']}" for d in details[:2]])
                        risks.append(f"🟡 诉讼仲裁风险：公司涉及诉讼或仲裁案件 ({details_str})")
                        if risk_level == "低":
                            risk_level = "中"
                    elif '处罚' in found_risks or '违规' in found_risks:
                        details = risk_details.get('处罚', []) + risk_details.get('违规', [])
                        details_str = '; '.join([f"{d['日期']}:{d['标题']}" for d in details[:2]])
                        risks.append(f"🟡 监管处罚风险：公司受到监管处罚 ({details_str})")
                        if risk_level == "低":
                            risk_level = "中"
                    elif 'ST' in found_risks or '*ST' in found_risks:
                        # ST风险已经在前面检测过了，这里不再重复
                        pass
            except Exception as e:
                # 如果获取公告失败，不影响其他风险检测
                pass
            
            # 7. 检查财报风险
            try:
                # 获取财务报表数据
                financial_report = ak.stock_financial_analysis_indicator(symbol=symbol)
                if not financial_report.empty:
                    # 转换为字典
                    financial_dict = dict(zip(financial_report['指标'], financial_report['最新值']))
                    
                    # 检查财务指标
                    # 检查资产负债率
                    asset_liability_ratio = financial_dict.get('资产负债率', '')
                    if asset_liability_ratio:
                        try:
                            ratio_value = float(asset_liability_ratio.replace('%', ''))
                            if ratio_value > 80:
                                risks.append("🔴 资产负债率过高：财务结构风险大")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif ratio_value > 60:
                                risks.append("🟡 资产负债率偏高：财务压力较大")
                                if risk_level == "低":
                                    risk_level = "中"
                        except:
                            pass
                    
                    # 检查流动比率
                    current_ratio = financial_report.get('流动比率', '')
                    if current_ratio:
                        try:
                            ratio_value = float(current_ratio)
                            if ratio_value < 1:
                                risks.append("🟡 流动比率偏低：短期偿债能力弱")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif ratio_value < 0.5:
                                risks.append("🔴 流动比率过低：短期偿债风险大")
                                risk_level = "高"
                        except:
                            pass
                    
                    # 检查速动比率
                    quick_ratio = financial_report.get('速动比率', '')
                    if quick_ratio:
                        try:
                            ratio_value = float(quick_ratio)
                            if ratio_value < 0.8:
                                risks.append("🟡 速动比率偏低：流动性风险")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif ratio_value < 0.5:
                                risks.append("🔴 速动比率过低：流动性风险大")
                                risk_level = "高"
                        except:
                            pass
                    
                    # 检查毛利率
                    gross_margin = financial_report.get('销售毛利率', '')
                    if gross_margin:
                        try:
                            margin_value = float(gross_margin.replace('%', ''))
                            if margin_value < 10:
                                risks.append("🟡 毛利率过低：盈利能力弱")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif margin_value < 0:
                                risks.append("🔴 毛利率为负：严重亏损")
                                risk_level = "高"
                        except:
                            pass
                    
                    # 检查净资产收益率
                    roe = financial_report.get('净资产收益率', '')
                    if roe:
                        try:
                            roe_value = float(roe.replace('%', ''))
                            if roe_value < 0:
                                risks.append("🟡 净资产收益率为负：股东回报率低")
                                if risk_level == "低":
                                    risk_level = "中"
                            elif roe_value < 5:
                                risks.append("🟢 净资产收益率偏低：盈利能力一般")
                        except:
                            pass
            except Exception as e:
                # 如果获取财报数据失败，不影响其他风险检测
                pass
            
            # 如果没有发现风险
            if not risks:
                risks.append("✅ 未发现明显风险")
            
            return {
                '风险等级': risk_level,
                '风险列表': risks,
                '股票名称': stock_name
            }
        except Exception as e:
            return {
                '风险等级': '未知',
                '风险列表': [f'风险检测失败: {str(e)}']
            }
    
    @staticmethod
    def get_stock_code_by_name(name):
        """
        通过股票名称查找股票代码
        name: 股票名称
        返回: 股票代码列表（可能有多个匹配）
        """
        try:
            import akshare as ak
            
            # 获取A股代码名称表
            stock_info_df = ak.stock_info_a_code_name()
            
            # 查找匹配的股票（支持部分匹配）
            matched_stocks = stock_info_df[stock_info_df['name'].str.contains(name, na=False)]
            
            if not matched_stocks.empty:
                # 返回匹配的股票代码列表
                return matched_stocks['code'].tolist()
            else:
                return []
        except Exception as e:
            return []
    
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
    def get_turnover_rate(df):
        """
        从历史数据中获取换手率
        df: 历史数据DataFrame
        """
        try:
            if df.empty:
                return {
                    '数据状态': '数据为空',
                    '换手率': None
                }
            
            # 检查是否有换手率列（可能是中文或英文）
            turnover_col = None
            if '换手率' in df.columns:
                turnover_col = '换手率'
            elif 'turnover_rate' in df.columns:
                turnover_col = 'turnover_rate'
            
            if turnover_col is None:
                return {
                    '数据状态': '换手率列不存在',
                    '换手率': None
                }
            
            # 获取最新的换手率
            latest_data = df.iloc[-1]
            turnover_rate = latest_data[turnover_col]
            
            # 检查换手率是否为有效值
            if pd.isna(turnover_rate) or turnover_rate is None:
                return {
                    '数据状态': '换手率数据为空',
                    '换手率': None,
                    '说明': '旧数据不包含换手率，请重新获取数据'
                }
            
            return {
                '数据状态': '正常',
                '换手率': round(float(turnover_rate), 2),
                '日期': latest_data.get('date', latest_data.get('日期', ''))
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '换手率': None,
                '错误信息': str(e)
            }
    
    @staticmethod
    def analyze_turnover_and_volume(turnover_rate, volume_ratio):
        """
        根据换手率和量比分析个股情况
        turnover_rate: 换手率（百分比）
        volume_ratio: 量比
        """
        if turnover_rate is None:
            return {
                '分析状态': '换手率数据缺失',
                '建议': '无法进行分析'
            }
        
        # 换手率判断
        if turnover_rate > 10:
            turnover_level = "极高"
            turnover_desc = "换手率极高，交易非常活跃"
        elif turnover_rate > 5:
            turnover_level = "高"
            turnover_desc = "换手率较高，交易活跃"
        elif turnover_rate > 2:
            turnover_level = "中等"
            turnover_desc = "换手率适中，交易正常"
        elif turnover_rate > 0.5:
            turnover_level = "低"
            turnover_desc = "换手率较低，交易清淡"
        else:
            turnover_level = "极低"
            turnover_desc = "换手率极低，交易非常清淡"
        
        # 量比判断
        if volume_ratio > 2:
            volume_level = "放量"
            volume_desc = "成交量显著放大"
        elif volume_ratio > 1.5:
            volume_level = "温和放量"
            volume_desc = "成交量温和放大"
        elif volume_ratio < 0.5:
            volume_level = "缩量"
            volume_desc = "成交量萎缩"
        else:
            volume_level = "正常"
            volume_desc = "成交量正常"
        
        # 综合分析
        analysis_result = []
        risk_level = "中等"
        
        # 高换手率 + 放量 = 主力活跃
        if turnover_rate > 5 and volume_ratio > 1.5:
            analysis_result.append("✅ 换手率高且放量，主力资金活跃，值得关注")
            risk_level = "中等偏高"
        # 高换手率 + 缩量 = 可能是出货
        elif turnover_rate > 5 and volume_ratio < 0.8:
            analysis_result.append("⚠️ 换手率高但缩量，可能是主力出货，需谨慎")
            risk_level = "高"
        # 低换手率 + 放量 = 可能是建仓
        elif turnover_rate < 2 and volume_ratio > 1.5:
            analysis_result.append("💡 换手率低但放量，可能是主力建仓，可关注")
            risk_level = "低"
        # 低换手率 + 缩量 = 观望
        elif turnover_rate < 2 and volume_ratio < 0.8:
            analysis_result.append("📊 换手率低且缩量，市场观望情绪浓厚")
            risk_level = "低"
        # 中等换手率 + 放量 = 稳健上涨
        elif 2 <= turnover_rate <= 5 and volume_ratio > 1.5:
            analysis_result.append("📈 换手率适中且放量，走势稳健，可继续持有")
            risk_level = "中等"
        # 中等换手率 + 缩量 = 调整中
        elif 2 <= turnover_rate <= 5 and volume_ratio < 0.8:
            analysis_result.append("📉 换手率适中但缩量，可能处于调整期")
            risk_level = "中等"
        else:
            analysis_result.append("📊 换手率和量比均正常，走势平稳")
            risk_level = "中等"
        
        return {
            '换手率': turnover_rate,
            '换手率等级': turnover_level,
            '换手率说明': turnover_desc,
            '量比': volume_ratio,
            '量比等级': volume_level,
            '量比说明': volume_desc,
            '综合分析': analysis_result,
            '风险等级': risk_level
        }
    
    @staticmethod
    def check_limit_up(df):
        """
        检查是否涨停
        df: 历史数据DataFrame
        返回: 是否涨停、涨停日期列表
        """
        try:
            if df.empty or len(df) < 2:
                return {
                    '是否涨停': False,
                    '涨停日期': []
                }
            
            # 计算涨跌幅
            df['change_pct'] = df['close'].pct_change() * 100
            
            # 判断涨停（涨跌幅 >= 9.9%）
            limit_up_days = df[df['change_pct'] >= 9.9]
            
            if not limit_up_days.empty:
                return {
                    '是否涨停': True,
                    '涨停日期': limit_up_days['date'].tolist(),
                    '涨停次数': len(limit_up_days),
                    '最新涨停': limit_up_days.iloc[-1]['date'] if len(limit_up_days) > 0 else None
                }
            else:
                return {
                    '是否涨停': False,
                    '涨停日期': [],
                    '涨停次数': 0
                }
        except Exception as e:
            return {
                '是否涨停': False,
                '涨停日期': [],
                '错误信息': str(e)
            }
    
    @staticmethod
    def analyze_dragon_stock(df, current_price=None, symbol=None, current_pct=None):
        """
        龙头战法分析 V4.0 - 游资掠食者版
        根据五个条件和识别特征进行综合分析，区分 20cm 和 10cm
        
        Args:
            df: 历史数据DataFrame
            current_price: 当前价格（可选）
            symbol: 股票代码（用于区分 20cm 和 10cm）
            current_pct: 当前涨跌幅（用于判断是否涨停）
        """
        try:
            if df.empty or len(df) < 20:
                return {
                    '龙头评级': '数据不足',
                    '评级得分': 0,
                    '不符合原因': '数据不足，无法分析'
                }
            
            # 判断是否为 20cm 标的
            is_20cm = symbol and (symbol.startswith('30') or symbol.startswith('68'))
            
            # 设置涨停阈值
            if is_20cm:
                limit_threshold = 19.5
                acc_threshold = 10.0  # 加速段阈值
            else:
                limit_threshold = 9.8
                acc_threshold = 5.0   # 加速段阈值
            
            # 判断是否涨停
            is_limit_up = current_pct and current_pct >= limit_threshold
            # 判断是否在加速段
            in_acc_zone = current_pct and acc_threshold <= current_pct < limit_threshold
            
            # 1. 检查是否从涨停板开始（调整为 20cm 适配）
            limit_up_info = QuantAlgo.check_limit_up(df)
            condition1_score = 0
            condition1_desc = []
            
            # 如果当前已经涨停，直接给满分
            if is_limit_up:
                condition1_score = 25  # 涨停给满分（25分）
                condition1_desc.append(f"✅ 当前已涨停（{current_pct:.2f}%），真龙特征")
            # 如果在加速段（尤其是 20cm），也给高分
            elif in_acc_zone:
                condition1_score = 20
                condition1_desc.append(f"✅ 处于加速逼空段（{current_pct:.2f}%），主力做多意愿强")
            # 否则检查历史涨停记录
            elif limit_up_info['是否涨停']:
                condition1_score = 15
                condition1_desc.append(f"✅ 有涨停板记录（{limit_up_info['涨停次数']}次）")
            else:
                condition1_desc.append("❌ 无涨停板记录，当前不在涨停板，不能做龙头")
            
            # 2. 价格评分（移除价格歧视）
            current_price = current_price if current_price else df.iloc[-1]['close']
            condition2_score = 20  # 龙头战法不看价格，直接给满分
            condition2_desc = [f"✅ 价格 ¥{current_price:.2f}，龙头就是用来创新高的"]
            
            # 3. 检查成交量（攻击性放量）
            volume_data = QuantAlgo.analyze_volume(df)
            condition3_score = 0
            condition3_desc = []
            
            if volume_data['量比'] > 2:
                condition3_score = 25  # 放量给更高分
                condition3_desc.append(f"✅ 攻击性放量（量比{volume_data['量比']}），资金合力强")
            elif volume_data['量比'] > 1.5:
                condition3_score = 20
                condition3_desc.append(f"✅ 温和放量（量比{volume_data['量比']}），资金活跃")
            elif volume_data['量比'] > 1.0:
                condition3_score = 15
                condition3_desc.append(f"⚠️ 正常放量（量比{volume_data['量比']}）")
            else:
                condition3_desc.append(f"❌ 缩量（量比{volume_data['量比']}），资金不活跃")
            
            # 4. 20cm 半路博弈逻辑（替代 KDJ）
            condition4_score = 0
            condition4_desc = []
            
            if is_20cm and in_acc_zone:
                condition4_score = 25
                condition4_desc.append(f"✅ 20cm 加速逼空段（{current_pct:.2f}%），半路博弈最佳时机")
            elif is_limit_up:
                condition4_score = 20
                condition4_desc.append(f"✅ 涨停封死，龙头确立")
            elif current_pct and current_pct >= 5:
                condition4_score = 15
                condition4_desc.append(f"✅ 涨幅 {current_pct:.2f}%，具备上涨动能")
            else:
                condition4_desc.append(f"❌ 涨幅不足（{current_pct:.2f}%），缺乏辨识度")
            
            # 5. 检查换手率
            turnover_data = QuantAlgo.get_turnover_rate(df)
            condition5_score = 0
            condition5_desc = []
            
            if turnover_data.get('换手率'):
                tr = turnover_data['换手率']
                if 5 <= tr <= 15:
                    condition5_score = 20
                    condition5_desc.append(f"✅ 换手率适中（{tr}%），资金活跃")
                elif 2 <= tr < 5:
                    condition5_score = 15
                    condition5_desc.append(f"⚠️ 换手率偏低（{tr}%），资金参与度一般")
                elif tr > 15:
                    condition5_score = 10
                    condition5_desc.append(f"⚠️ 换手率过高（{tr}%），风险较大")
                else:
                    condition5_desc.append(f"❌ 换手率过低（{tr}%），资金不活跃")
            else:
                condition5_desc.append("❌ 换手率数据缺失")
            
            # 计算总分（满分 115 分，需要归一化到 100 分）
            total_score = condition1_score + condition2_score + condition3_score + condition4_score + condition5_score
            normalized_score = int(total_score / 115 * 100)
            
            # 评级标准（调整后）
            if normalized_score >= 90:
                rating = "🔥🔥 真龙/妖股"
                rating_desc = "监管安全 + 板块核心 + 竞价爆量/加速中，猛干"
            elif normalized_score >= 80:
                rating = "🔥 强龙头"
                rating_desc = "符合龙头战法大部分条件，重点关注"
            elif normalized_score >= 60:
                rating = "📈 潜力龙头"
                rating_desc = "具备龙头股特征，可关注"
            elif normalized_score >= 40:
                rating = "⚠️ 弱龙头"
                rating_desc = "部分符合条件，谨慎关注"
            else:
                rating = "❌ 非龙头"
                rating_desc = "不符合龙头战法条件"
            
            # 综合分析
            analysis = []
            if condition1_score >= 20:
                analysis.append("该股具备涨停板特征，是龙头的发源地")
            if condition2_score > 0:
                analysis.append("价格适中，具备炒作空间，容易得到市场追捧")
            if condition3_score > 0:
                analysis.append("成交量放大，显示主力资金活跃")
            if condition4_score > 0:
                if is_20cm and in_acc_zone:
                    analysis.append("20cm 加速逼空段，半路博弈最佳时机")
                elif is_limit_up:
                    analysis.append("涨停封死，龙头确立")
                else:
                    analysis.append("具备上涨动能")
            if condition5_score > 0:
                analysis.append("换手率适中，资金参与度较高")
            
            return {
                '龙头评级': rating,
                '评级得分': normalized_score,
                '评级说明': rating_desc,
                '条件1_涨停板': {
                    '得分': condition1_score,
                    '说明': condition1_desc
                },
                '条件2_价格': {
                    '得分': condition2_score,
                    '说明': condition2_desc
                },
                '条件3_成交量': {
                    '得分': condition3_score,
                    '说明': condition3_desc
                },
                '条件4_加速段': {
                    '得分': condition4_score,
                    '说明': condition4_desc
                },
                '条件5_换手率': {
                    '得分': condition5_score,
                    '说明': condition5_desc
                },
                '综合分析': analysis,
                '操作建议': QuantAlgo.get_dragon_operation_suggestion_v4(normalized_score, is_limit_up, in_acc_zone, is_20cm, current_pct)
            }
        except Exception as e:
            return {
                '龙头评级': '分析失败',
                '评级得分': 0,
                '错误信息': str(e)
            }
    
    @staticmethod
    def get_dragon_operation_suggestion(total_score, limit_up_info, kdj_data):
        """
        根据龙头战法给出操作建议
        """
        suggestions = []
        
        if total_score >= 80:
            suggestions.append("🎯 **强龙头策略**")
            suggestions.append("1. 追涨策略：在涨停开闸放水时买入")
            suggestions.append("2. 回调策略：等待股价回到第一个涨停板启涨点附近买入")
            suggestions.append("3. 止损点：以第一个涨停板为止损点")
            suggestions.append("4. 持有：耐心持有，直到不再涨停，收盘前10分钟卖出")
        elif total_score >= 60:
            suggestions.append("💡 **潜力龙头策略**")
            suggestions.append("1. 分批买入：先试探性买入，确认强势后再加仓")
            suggestions.append("2. 关注KDJ：等待KDJ金叉确认后再重仓")
            suggestions.append("3. 止损点：弱势市场以3%为止损点")
            suggestions.append("4. 观察放量：确认攻击性放量后再追涨")
        elif total_score >= 40:
            suggestions.append("⚠️ **弱龙头策略**")
            suggestions.append("1. 轻仓尝试：小仓位试探，不宜重仓")
            suggestions.append("2. 严格止损：设置3%止损，严格执行")
            suggestions.append("3. 观望为主：等待更多信号确认")
        else:
            suggestions.append("❌ **非龙头建议**")
            suggestions.append("1. 不建议操作：不符合龙头战法条件")
            suggestions.append("2. 观望等待：等待出现更好的机会")
        
        return suggestions
    
    @staticmethod
    def get_dragon_operation_suggestion_v4(score, is_limit_up, in_acc_zone, is_20cm, current_pct):
        """
        根据龙头战法 V4.0 游资掠食者版给出操作建议
        
        Args:
            score: 评分（归一化后的 0-100 分）
            is_limit_up: 是否涨停
            in_acc_zone: 是否在加速段
            is_20cm: 是否为 20cm 标的
            current_pct: 当前涨跌幅
        """
        suggestions = []
        
        if score >= 90:
            # 真龙/妖股
            suggestions.append("🔥🔥 **真龙/妖股策略**")
            suggestions.append("1. 🟢 猛干（扫板/排板）：监管安全 + 板块核心 + 竞价爆量/加速中")
            suggestions.append("2. 仓位：重仓")
            
            if is_20cm and is_limit_up:
                suggestions.append("3. 20cm 涨停封死：持有，关注明天溢价")
            elif is_20cm and in_acc_zone:
                suggestions.append("3. 20cm 加速逼空段：半路扫货，无需等待，直接博弈封板！")
            elif is_limit_up:
                suggestions.append("3. 10cm 涨停封死：排板确认，关注明天溢价")
        
        elif score >= 80:
            # 强龙头
            suggestions.append("🔥 **强龙头策略**")
            suggestions.append("1. 🟢 博弈（半路/跟随）：逻辑正宗 + 形态好")
            suggestions.append("2. 仓位：半仓")
            
            if is_20cm and in_acc_zone:
                suggestions.append("3. 20cm 半路（12-18%）：分时承接极强，无需等待，直接博弈封板！")
            elif is_20cm and is_limit_up:
                suggestions.append("3. 20cm 涨停封死：持有，关注明天溢价")
            elif is_limit_up:
                suggestions.append("3. 10cm 涨停：打板确认")
        
        elif score >= 60:
            # 潜力龙头
            suggestions.append("📈 **潜力龙头策略**")
            suggestions.append("1. 🟡 低吸/观望：没涨停但板块热，或涨幅<5%等待补涨")
            suggestions.append("2. 仓位：轻仓")
            
            if is_20cm and in_acc_zone:
                suggestions.append("3. 20cm 加速段：关注分时承接，确认强势后再加仓")
            elif is_20cm and current_pct < 10:
                suggestions.append("3. 20cm 低位：等待突破 10% 加速段")
            elif current_pct < 5:
                suggestions.append("3. 低位：等待补涨机会")
        
        elif score >= 40:
            # 弱龙头
            suggestions.append("⚠️ **弱龙头策略**")
            suggestions.append("1. 🔵 只看不买：跟风回落，谨慎关注")
            suggestions.append("2. 仓位：观望")
            
            if current_pct < 5:
                suggestions.append("3. 涨幅不足：缺乏辨识度，不建议参与")
        
        else:
            # 非龙头
            suggestions.append("❌ **非龙头建议**")
            suggestions.append("1. 🔴 跑/核按钮：ST / 监管雷 / 跟风回落 / 趋势向下")
            suggestions.append("2. 仓位：空仓")
        
        return suggestions
    
    @staticmethod
    def scan_dragon_stocks(limit=50, min_score=60):
        """
        扫描市场中的潜在龙头股
        limit: 扫描的股票数量限制
        min_score: 最低评分门槛
        返回: 符合条件的龙头股列表
        """
        try:
            import akshare as ak
            from logic.data_manager import DataManager
            
            # 获取涨停板股票（使用 Easyquotation 极速接口）
            db = DataManager()
            
            try:
                # 使用 akshare 获取股票列表
                stock_list_df = ak.stock_info_a_code_name()
                if stock_list_df.empty:
                    db.close()
                    return {
                        '数据状态': '无法获取股票列表',
                        '说明': '可能是数据源限制'
                    }
                
                # 获取全市场所有股票
                stock_list = stock_list_df['code'].tolist()
                
                # 使用 Easyquotation 极速获取实时数据
                realtime_data = db.get_fast_price(stock_list)
                
                if not realtime_data:
                    db.close()
                    return {
                        '数据状态': '无法获取实时数据',
                        '说明': 'Easyquotation 未初始化或网络问题',
                        '扫描数量': len(stock_list)
                    }
            
            # 转换为列表格式
            all_stocks = []
            for full_code, data in realtime_data.items():
                try:
                    current_price = float(data.get('now', 0))
                    last_close = float(data.get('close', 0))
                    
                    if current_price == 0 or last_close == 0:
                        continue
                    
                    pct_change = (current_price - last_close) / last_close * 100
                    
                    # 提取股票代码（去掉前缀）
                    # Easyquotation 返回的 key 可能是 '000001' 或 'sz000001'
                    if len(full_code) == 6:
                        code = full_code  # 直接使用
                    elif len(full_code) > 6:
                        code = full_code[2:]  # 去掉前缀
                    else:
                        continue  # 代码格式不对
                    
                    name = data.get('name', '')
                    
                    # 只保留 A 股股票（6位数字，以 0、3、6 开头）
                    if not (len(code) == 6 and code.isdigit() and code[0] in ['0', '3', '6']):
                        continue
                    
                    all_stocks.append({
                        '代码': code,
                        '名称': name,
                        '最新价': current_price,
                        '涨跌幅': pct_change
                    })
                except Exception as e:
                    continue
            
            # 筛选涨停板股票（涨跌幅 >= 9.9%）
            limit_up_stocks = [s for s in all_stocks if s['涨跌幅'] >= 9.9]
            
            # 按涨跌幅排序，取前 limit 只
            limit_up_stocks.sort(key=lambda x: x['涨跌幅'], reverse=True)
            stocks_to_analyze = limit_up_stocks[:limit]
            
            if not stocks_to_analyze:
                db.close()
                return {
                    '数据状态': '无涨停板股票',
                    '说明': '当前市场无涨停板股票',
                    '扫描数量': len(stock_list),
                    '涨停板数量': len(limit_up_stocks)
                }
            
            # 分析每只涨停板股票
            dragon_stocks = []
            
            # 构建股票代码到实时数据的映射（方便查找）
            realtime_map = {}
            for full_code, data in realtime_data.items():
                code = full_code if len(full_code) == 6 else full_code[2:]
                realtime_map[code] = data
            
            for stock_info in stocks_to_analyze:
                symbol = stock_info['代码']
                name = stock_info['名称']
                current_price = stock_info['最新价']
                
                # 过滤 ST 股
                if 'ST' in name or '*ST' in name:
                    print(f"⚠️ 跳过 ST 股: {name}({symbol})")
                    continue
                
                try:
                    # 获取历史数据
                    df = db.get_history_data(symbol)
                    
                    if not df.empty and len(df) > 20:
                        # 龙头战法分析（传入股票代码和涨跌幅）
                        dragon_analysis = QuantAlgo.analyze_dragon_stock(df, current_price, symbol, stock_info['涨跌幅'])
                        
                        # 获取实时数据（用于计算量比、换手率等）
                        realtime_data_item = realtime_map.get(symbol, {})
                        
                        # 计算量比
                        volume_ratio = 0
                        if not df.empty and len(df) > 5:
                            avg_volume = df['volume'].tail(5).mean()  # 5日平均成交量
                            current_volume = realtime_data_item.get('volume', 0)
                            if avg_volume > 0:
                                volume_ratio = current_volume / avg_volume
                        
                        # 计算换手率（使用历史数据中的换手率）
                        turnover_rate = 0
                        if not df.empty:
                            # 使用最近一天的换手率
                            turnover_rate = df['turnover_rate'].iloc[-1] if 'turnover_rate' in df.columns else 0
                        
                        # 获取竞价量（买一量 + 卖一量）
                        auction_volume = 0
                        bid1_volume = realtime_data_item.get('bid1_volume', 0)
                        ask1_volume = realtime_data_item.get('ask1_volume', 0)
                        auction_volume = (bid1_volume + ask1_volume) / 100  # 转换为手
                        
                        # 添加调试信息
                        score = dragon_analysis.get('评级得分', 0)
                        print(f"{name}({symbol}) - 涨幅:{stock_info['涨跌幅']:.2f}% - 评分:{score} - {dragon_analysis['龙头评级']}")
                        
                        # 只保留评分达到门槛的股票
                        if dragon_analysis.get('评级得分', 0) >= min_score:
                            dragon_stocks.append({
                                '代码': symbol,
                                '名称': name,
                                '最新价': current_price,
                                '涨跌幅': stock_info['涨跌幅'],
                                '龙头评级': dragon_analysis['龙头评级'],
                                '评级得分': dragon_analysis['评级得分'],
                                '评级说明': dragon_analysis['评级说明'],
                                '详情': dragon_analysis,
                                '量比': round(volume_ratio, 2),
                                '换手率': round(turnover_rate, 2),
                                '竞价量': int(auction_volume)
                            })
                except Exception as e:
                    print(f"分析股票 {symbol} 失败: {e}")
                    continue
            
            # 按评分排序
            dragon_stocks.sort(key=lambda x: x['评级得分'], reverse=True)
            
            # 关闭数据库连接
            db.close()
            
            return {
                '数据状态': '正常',
                '扫描数量': len(stock_list),
                '涨停板数量': len(limit_up_stocks),
                '分析数量': len(stocks_to_analyze),
                '符合条件数量': len(dragon_stocks),
                '龙头股列表': dragon_stocks
            }
        except Exception as e:
            # 确保在异常情况下也关闭数据库连接
            try:
                db.close()
            except:
                pass
            
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
        date: 日期，格式 YYYY-MM-DD，默认为最近一天
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta

            # 计算日期
            if date:
                if isinstance(date, str):
                    date_obj = pd.to_datetime(date)
                else:
                    date_obj = date
                date_str = date_obj.strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')

            # 先尝试使用新浪接口获取数据
            try:
                lhb_df = ak.stock_lhb_detail_daily_sina(date=date_str)

                if not lhb_df.empty:
                    # 转换数据为列表格式
                    stocks = []
                    for _, row in lhb_df.iterrows():
                        stocks.append({
                            '代码': row['股票代码'],
                            '名称': row['股票名称'],
                            '收盘价': row['收盘价'],
                            '涨跌幅': row['涨跌幅'],
                            '龙虎榜净买入': row['成交额'],  # 新浪接口使用成交额
                            '上榜原因': row['指数']
                        })

                    return {
                        '数据状态': '正常',
                        '股票列表': stocks,
                        '数据日期': date_str
                    }
            except Exception as e:
                print(f"新浪接口获取失败: {e}")

            # 如果新浪接口失败，使用东方财富接口
            try:
                # 计算日期范围（最近7天）
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

                # 获取东方财富龙虎榜数据（支持日期范围）
                lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

                if lhb_df.empty:
                    return {
                        '数据状态': '无法获取数据',
                        '说明': '可能是数据源限制或非交易日'
                    }

                # 只取最新日期的数据
                latest_date = lhb_df.iloc[:, 3].max()  # 上榜日期列
                latest_data = lhb_df[lhb_df.iloc[:, 3] == latest_date]

                # 转换数据为列表格式（使用列索引避免中文乱码）
                stocks = []
                for _, row in latest_data.head(30).iterrows():  # 取最新日期的30只股票
                    stocks.append({
                        '代码': row.iloc[1],      # 股票代码
                        '名称': row.iloc[2],      # 股票名称
                        '收盘价': row.iloc[5],    # 收盘价
                        '涨跌幅': row.iloc[6],    # 涨跌幅
                        '龙虎榜净买入': row.iloc[9],  # 龙虎榜净买入额
                        '上榜原因': row.iloc[16]   # 上榜原因
                    })

                return {
                    '数据状态': '正常',
                    '股票列表': stocks,
                    '数据日期': latest_date
                }
            except Exception as e:
                print(f"东方财富接口获取失败: {e}")

            return {
                '数据状态': '无法获取数据',
                '说明': '所有数据源均无法获取数据'
            }

        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def analyze_lhb_summary(date=None):
                """
                龙虎榜综合分析
                分析机构席位、营业部席位、资金流向、上榜原因等
                """
                try:
                    import akshare as ak
                    from datetime import datetime, timedelta
                    
                    # 计算日期范围
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
                    
                    # 获取机构统计
                    try:
                        jg_stat = ak.stock_lhb_jgstatistic_em()
                        jg_stat = jg_stat[jg_stat.iloc[:, 0] == start_date]  # 筛选指定日期
                    except:
                        jg_stat = None
                    
                    # 获取活跃营业部
                    try:
                        active_yyb = ak.stock_lhb_yyb_detail_em()
                    except:
                        active_yyb = None
                    
                    # 获取龙虎榜详情用于分析上榜原因
                    lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
                    latest_date = lhb_df.iloc[:, 3].max()
                    latest_data = lhb_df[lhb_df.iloc[:, 3] == latest_date]
                    
                    # 统计上榜原因
                    reason_stats = {}
                    for _, row in latest_data.iterrows():
                        reason = row.iloc[16]
                        if reason in reason_stats:
                            reason_stats[reason] += 1
                        else:
                            reason_stats[reason] = 1
                    
                    # 计算资金流向
                    total_net_buy = latest_data.iloc[:, 9].sum()  # 龙虎榜净买入总额
                    total_volume = latest_data.iloc[:, 10].sum()  # 总成交额
                    
                    return {
                        '数据状态': '正常',
                        '数据日期': latest_date,
                        '上榜股票数量': len(latest_data),
                        '龙虎榜净买入总额': total_net_buy,
                        '总成交额': total_volume,
                        '上榜原因统计': reason_stats,
                        '机构统计': jg_stat,
                        '活跃营业部': active_yyb
                    }
                except Exception as e:
                    return {
                        '数据状态': '获取失败',
                        '错误信息': str(e),
                        '说明': '可能是网络问题或数据源限制'
                    }

    @staticmethod
    def analyze_lhb_quality():
        """
        龙虎榜质量分析
        分析哪些是好榜、坏榜，哪些值得次日介入
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            # 获取龙虎榜详情
            lhb_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            latest_date = lhb_df.iloc[:, 3].max()
            latest_data = lhb_df[lhb_df.iloc[:, 3] == latest_date]
            
            # 分析每只股票的质量
            stock_analysis = []
            for _, row in latest_data.iterrows():
                code = row.iloc[1]
                name = row.iloc[2]
                close_price = row.iloc[5]
                change_pct = row.iloc[6]
                net_buy = row.iloc[9]
                total_volume = row.iloc[10]
                reason = row.iloc[16]
                
                # 评分系统（0-100分）
                score = 0
                reasons = []
                
                # 1. 净买入额（30分）
                if net_buy > 100000000:  # 净买入超过1亿
                    score += 30
                    reasons.append('净买入>1亿')
                elif net_buy > 50000000:  # 净买入超过5000万
                    score += 20
                    reasons.append('净买入>5000万')
                elif net_buy > 0:  # 净买入为正
                    score += 10
                    reasons.append('净买入为正')
                elif net_buy > -50000000:  # 净买入小于5000万
                    score += 0
                else:  # 净卖出超过5000万
                    score -= 10
                    reasons.append('净卖出>5000万')
                
                # 2. 涨跌幅（20分）
                if 3 <= abs(change_pct) <= 7:  # 涨跌幅适中
                    score += 20
                    reasons.append('涨跌幅适中')
                elif 7 < abs(change_pct) <= 10:
                    score += 10
                    reasons.append('涨跌幅较大')
                elif abs(change_pct) > 10:
                    score -= 10
                    reasons.append('涨跌幅过大')
                
                # 3. 成交额（15分）
                if total_volume > 500000000:  # 成交额超过5亿
                    score += 15
                    reasons.append('成交额>5亿')
                elif total_volume > 200000000:  # 成交额超过2亿
                    score += 10
                    reasons.append('成交额>2亿')
                elif total_volume > 100000000:  # 成交额超过1亿
                    score += 5
                    reasons.append('成交额>1亿')
                
                # 4. 上榜原因（20分）
                good_reasons = ['机构买入', '机构专用', '连续涨停', '换手率']
                bad_reasons = ['跌停', '跌停价', 'ST']
                
                if any(keyword in reason for keyword in good_reasons):
                    score += 20
                    reasons.append('上榜原因优质')
                elif any(keyword in reason for keyword in bad_reasons):
                    score -= 20
                    reasons.append('上榜原因较差')
                else:
                    score += 10
                    reasons.append('上榜原因一般')
                
                # 5. 净买入占比（15分）
                net_buy_ratio = net_buy / total_volume * 100 if total_volume > 0 else 0
                if net_buy_ratio > 10:
                    score += 15
                    reasons.append('净买入占比>10%')
                elif net_buy_ratio > 5:
                    score += 10
                    reasons.append('净买入占比>5%')
                elif net_buy_ratio > 0:
                    score += 5
                    reasons.append('净买入占比>0')
                
                # 判断榜单质量
                if score >= 70:
                    quality = '🟢 优质榜'
                    recommendation = '强烈推荐'
                elif score >= 50:
                    quality = '🟡 良好榜'
                    recommendation = '推荐关注'
                elif score >= 30:
                    quality = '🟠 一般榜'
                    recommendation = '谨慎观望'
                else:
                    quality = '🔴 劣质榜'
                    recommendation = '不建议介入'
                
                stock_analysis.append({
                    '代码': code,
                    '名称': name,
                    '收盘价': close_price,
                    '涨跌幅': change_pct,
                    '净买入': net_buy,
                    '净买入占比': net_buy_ratio,
                    '成交额': total_volume,
                    '上榜原因': reason,
                    '评分': score,
                    '榜单质量': quality,
                    '推荐': recommendation,
                    '评分原因': reasons
                })
            
            # 按评分排序
            stock_analysis.sort(key=lambda x: x['评分'], reverse=True)
            
            # 统计
            good_count = len([s for s in stock_analysis if s['评分'] >= 70])
            medium_count = len([s for s in stock_analysis if 50 <= s['评分'] < 70])
            poor_count = len([s for s in stock_analysis if s['评分'] < 50])
            
            return {
                '数据状态': '正常',
                '数据日期': latest_date,
                '股票分析': stock_analysis,
                '统计': {
                    '优质榜数量': good_count,
                    '良好榜数量': medium_count,
                    '劣质榜数量': poor_count,
                    '总数': len(stock_analysis)
                }
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
            
            # 做T机会分析
            t_opportunity = QuantAlgo.analyze_t_trading(df, atr, current_price, bollinger_data, rsi_data, volume_data)
            plan['做T机会'] = t_opportunity
            
            plan['分析依据'] = signals
            
            return plan
        except Exception as e:
            return {
                '错误': str(e),
                '说明': '生成操作预案失败'
            }
    
    @staticmethod
    def analyze_t_trading(df, atr, current_price, bollinger_data, rsi_data, volume_data):
        """
        分析做T机会
        做T：日内交易，低买高卖赚取差价
        """
        # 计算昨日收盘价和今日开盘价
        prev_close = df.iloc[-2]['close']
        today_open = df.iloc[-1]['open']
        
        # 计算日内波动率
        intraday_high = df.iloc[-1]['high']
        intraday_low = df.iloc[-1]['low']
        intraday_range = intraday_high - intraday_low
        
        # 做T机会评分（0-100）
        t_score = 0
        t_signals = []
        
        # 1. 波动性分析（权重30%）
        if atr > 0:
            volatility_ratio = atr / current_price
            if volatility_ratio > 0.03:  # 日内波动超过3%
                t_score += 30
                t_signals.append(f"波动性良好（ATR波动{volatility_ratio*100:.2f}%）")
            elif volatility_ratio > 0.02:  # 日内波动超过2%
                t_score += 20
                t_signals.append(f"波动性一般（ATR波动{volatility_ratio*100:.2f}%）")
        
        # 2. 布林带位置（权重25%）
        if current_price < bollinger_data['中轨']:
            t_score += 25
            t_signals.append("价格在中轨下方，适合低吸")
        elif current_price > bollinger_data['中轨'] and current_price < bollinger_data['上轨']:
            t_score += 15
            t_signals.append("价格在中轨附近，震荡机会")
        
        # 3. RSI超买超卖（权重20%）
        if rsi_data['RSI'] < 30:
            t_score += 20
            t_signals.append("RSI超卖，反弹概率大")
        elif rsi_data['RSI'] > 70:
            t_score += 20
            t_signals.append("RSI超买，回调概率大")
        elif 40 <= rsi_data['RSI'] <= 60:
            t_score += 10
            t_signals.append("RSI中性，震荡区间")
        
        # 4. 成交量（权重15%）
        if volume_data['信号'] == '放量显著':
            t_score += 15
            t_signals.append("放量显著，流动性好")
        elif volume_data['信号'] == '温和放量':
            t_score += 10
            t_signals.append("温和放量，流动性尚可")
        
        # 5. 开盘缺口（权重10%）
        # 防止除以零
        if prev_close != 0:
            gap = (today_open - prev_close) / prev_close
        else:
            gap = 0.0
        if abs(gap) > 0.02:  # 缺口超过2%
            t_score += 10
            if gap > 0:
                t_signals.append(f"高开{gap*100:.2f}%，可能回补")
            else:
                t_signals.append(f"低开{gap*100:.2f}%，可能反弹")
        
        # 判断做T机会
        if t_score >= 70:
            t_opportunity = '优秀'
            t_level = '🔥'
        elif t_score >= 50:
            t_opportunity = '良好'
            t_level = '🟡'
        elif t_score >= 30:
            t_opportunity = '一般'
            t_level = '🟢'
        else:
            t_opportunity = '较差'
            t_level = '⚪'
        
        # 计算做T点位
        # 买入点：当前价格向下1-2个ATR
        # 卖出点：当前价格向上1-2个ATR
        if t_score >= 30:
            t_buy_points = [
                current_price - atr * 0.5,  # 小幅回调
                current_price - atr * 1.0,  # 中幅回调
                current_price - atr * 1.5   # 大幅回调
            ]
            t_sell_points = [
                current_price + atr * 0.5,  # 小幅上涨
                current_price + atr * 1.0,  # 中幅上涨
                current_price + atr * 1.5   # 大幅上涨
            ]
        else:
            t_buy_points = []
            t_sell_points = []
        
        return {
            '做T机会': t_opportunity,
            '做T评分': t_score,
            '做T信号': t_signals,
            '做T买入点': [round(p, 2) for p in t_buy_points],
            '做T卖出点': [round(p, 2) for p in t_sell_points],
            '风险提示': '做T风险较高，建议小仓位操作，严格止损',
            '操作建议': f"{t_level} {t_opportunity}，{'适合做T' if t_score >= 50 else '不建议做T'}"
        }
    
    @staticmethod
    def get_auction_data():
        """
        获取集合竞价数据
        返回当前市场所有股票的集合竞价信息
        """
        try:
            import akshare as ak
            
            # 获取A股实时行情数据（包含集合竞价信息）
            stock_df = ak.stock_zh_a_spot_em()
            
            if stock_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制'
                }
            
            # 筛选需要的列
            auction_stocks = []
            for _, row in stock_df.iterrows():
                auction_stocks.append({
                    '代码': row['代码'],
                    '名称': row['名称'],
                    '最新价': row['最新价'],
                    '涨跌幅': row['涨跌幅'],
                    '成交量': row['成交量'],
                    '成交额': row['成交额'],
                    '量比': row['量比'],
                    '换手率': row['换手率'],
                    '市盈率': row['市盈率-动态'],
                    '总市值': row['总市值'],
                    '流通市值': row['流通市值']
                })
            
            return {
                '数据状态': '正常',
                '股票列表': auction_stocks,
                '总数': len(auction_stocks)
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    @staticmethod
    def detect_auction_weak_to_strong(df, symbol=None):
        """
        检测竞价弱转强战法
        适用于烂板、炸板股次日竞价超预期的情况
        
        策略逻辑：
        1. 前一天是烂板或炸板（弱势）
        2. 次日竞价放量高开（超预期）
        3. 说明有资金抢筹，值得重点关注
        
        df: 历史数据DataFrame
        symbol: 股票代码（可选，用于获取更多信息）
        """
        try:
            if df.empty or len(df) < 5:
                return {
                    '检测状态': '数据不足',
                    '是否弱转强': False,
                    '说明': '需要至少5天历史数据'
                }
            
            # 获取最近两天的数据
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            
            # 1. 检查前一天是否是烂板或炸板
            yesterday_change_pct = (yesterday['close'] - yesterday['open']) / yesterday['open'] * 100
            yesterday_high_change = (yesterday['high'] - yesterday['open']) / yesterday['open'] * 100
            
            is_weak_yesterday = False
            weak_type = ""
            
            # 炸板：盘中涨停但收盘未涨停
            if yesterday_high_change >= 9.9 and yesterday_change_pct < 9.9:
                is_weak_yesterday = True
                weak_type = "炸板"
            # 烂板：涨停但抛压大（换手率高）
            elif yesterday_change_pct >= 9.9:
                # 检查换手率
                turnover = yesterday.get('turnover_rate', 0)
                if turnover > 10:  # 换手率超过10%视为烂板
                    is_weak_yesterday = True
                    weak_type = "烂板"
            
            if not is_weak_yesterday:
                return {
                    '检测状态': '不符合条件',
                    '是否弱转强': False,
                    '说明': '前一天不是烂板或炸板，不符合弱转强条件'
                }
            
            # 2. 检查今日竞价情况
            today_open = today['open']
            yesterday_close = yesterday['close']
            gap_pct = (today_open - yesterday_close) / yesterday_close * 100
            
            # 计算今日成交量相对于昨日
            today_volume = today.get('volume', 0)
            yesterday_volume = yesterday.get('volume', 0)
            volume_ratio = today_volume / yesterday_volume if yesterday_volume > 0 else 1
            
            # 3. 判断是否弱转强
            # 条件：高开且放量
            is_weak_to_strong = False
            signals = []
            
            if gap_pct > 2:  # 高开超过2%
                signals.append(f"✅ 高开{gap_pct:.2f}%，超预期")
                is_weak_to_strong = True
            elif gap_pct > 0:  # 小幅高开
                signals.append(f"⚠️ 小幅高开{gap_pct:.2f}%")
            elif gap_pct > -2:  # 平开或小幅低开
                signals.append(f"⚠️ 平开/低开{gap_pct:.2f}%")
            else:  # 大幅低开
                signals.append(f"❌ 大幅低开{gap_pct:.2f}%，不符合弱转强")
                return {
                    '检测状态': '不符合条件',
                    '是否弱转强': False,
                    '说明': '大幅低开，不符合弱转强条件',
                    '信号': signals
                }
            
            if volume_ratio > 1.5:  # 放量超过1.5倍
                signals.append(f"✅ 放量{volume_ratio:.2f}倍，资金抢筹")
                is_weak_to_strong = True
            elif volume_ratio > 1:
                signals.append(f"⚠️ 温和放量{volume_ratio:.2f}倍")
            else:
                signals.append(f"❌ 缩量{volume_ratio:.2f}倍，资金不活跃")
            
            # 综合判断
            if is_weak_to_strong and gap_pct > 2 and volume_ratio > 1.5:
                rating = "🔥 强弱转强"
                suggestion = "重点关注，竞价超预期，资金抢筹，可考虑参与"
            elif is_weak_to_strong:
                rating = "🟡 弱弱转强"
                suggestion = "谨慎关注，信号一般，观察盘中走势"
            else:
                rating = "❌ 非弱转强"
                suggestion = "不符合弱转强条件，不建议参与"
            
            return {
                '检测状态': '正常',
                '是否弱转强': is_weak_to_strong,
                '前一天类型': weak_type,
                '昨日涨跌幅': round(yesterday_change_pct, 2),
                '今日开盘涨跌幅': round(gap_pct, 2),
                '量比': round(volume_ratio, 2),
                '评级': rating,
                '信号': signals,
                '操作建议': suggestion
            }
        except Exception as e:
            return {
                '检测状态': '检测失败',
                '是否弱转强': False,
                '错误信息': str(e)
            }
    
    @staticmethod
    def auction_diffusion_method(limit=50):
        """
        集合竞价扩散法
        通过一字板强势股挖掘同题材概念股
        
        策略逻辑：
        1. 9:20之后，找出一字涨停的股票
        2. 筛选首板、二板，且封单金额超过流通盘5%
        3. 剔除热炒题材，保留新题材
        4. 根据题材找出同概念股，关注未涨停但高开的股票
        
        limit: 扫描的股票数量限制
        """
        try:
            import akshare as ak
            
            # 获取实时行情数据
            stock_df = ak.stock_zh_a_spot_em()
            
            if stock_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制'
                }
            
            # 1. 筛选一字涨停的股票（涨跌幅 >= 9.9%）
            limit_up_stocks = stock_df[stock_df['涨跌幅'] >= 9.9].head(limit)
            
            if limit_up_stocks.empty:
                return {
                    '数据状态': '无涨停板股票',
                    '说明': '当前市场无涨停板股票'
                }
            
            # 2. 筛选强势一字板股票
            strong_stocks = []
            for _, row in limit_up_stocks.iterrows():
                symbol = row['代码']
                name = row['名称']
                current_price = row['最新价']
                turnover_rate = row['换手率']
                market_cap = row['流通市值']
                
                # 计算封单金额（估算：成交量 * 当前价格）
                volume = row['成交量']
                seal_amount = volume * current_price
                
                # 封单金额占流通市值比例
                seal_ratio = seal_amount / market_cap if market_cap > 0 else 0
                
                # 筛选条件：封单超过流通盘5%，且换手率适中（说明是一字板）
                if seal_ratio > 0.05 and turnover_rate < 5:
                    strong_stocks.append({
                        '代码': symbol,
                        '名称': name,
                        '最新价': current_price,
                        '涨跌幅': row['涨跌幅'],
                        '封单金额': round(seal_amount, 2),
                        '封单占比': round(seal_ratio * 100, 2),
                        '换手率': turnover_rate,
                        '流通市值': market_cap
                    })
            
            if not strong_stocks:
                return {
                    '数据状态': '无符合条件的强势股',
                    '说明': '未找到封单充足的强势一字板股票'
                }
            
            # 3. 按封单占比排序
            strong_stocks.sort(key=lambda x: x['封单占比'], reverse=True)
            
            # 4. 提取题材概念（这里简化处理，实际需要获取概念数据）
            # 注意：由于AkShare的限制，这里无法直接获取概念数据
            # 实际使用时，用户需要根据股票名称或代码手动查找相关概念
            
            return {
                '数据状态': '正常',
                '强势一字板股票': strong_stocks,
                '说明': '请根据强势股票的名称或代码，手动查找相关概念股',
                '操作建议': [
                    '1. 关注封单占比最高的一字板股票',
                    '2. 查找该股票的题材概念',
                    '3. 搜索同概念的其他股票',
                    '4. 关注未涨停但高开的同概念股',
                    '5. 竞价后直接参与或打板介入'
                ]
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    @staticmethod
    def scan_auction_stocks(limit=100):
        """
        集合竞价选股扫描
        综合运用竞价弱转强和集合竞价扩散法
        
        limit: 扫描的股票数量限制
        """
        try:
            import akshare as ak
            from logic.data_manager import DataManager
            
            # 获取实时行情数据
            stock_df = ak.stock_zh_a_spot_em()
            
            if stock_df.empty:
                return {
                    '数据状态': '无法获取数据',
                    '说明': '可能是数据源限制'
                }
            
            # 快速初筛：过滤掉明显不符合集合竞价特征的股票
            # 1. 排除ST、*ST股票
            # 2. 排除跌停股票（涨跌幅 <= -9.5%）
            # 3. 排除停牌股票（成交量为0）
            # 4. 排除价格异常（最新价 <= 0）
            # 5. 只保留有竞价特征的股票：量比>1 或 涨跌幅>1%
            pre_filtered = stock_df[
                (~stock_df['名称'].str.contains('ST|退', na=False)) &  # 排除ST和退市股
                (stock_df['涨跌幅'] > -9.5) &  # 排除跌停
                (stock_df['成交量'] > 0) &  # 排除停牌
                (stock_df['最新价'] > 0) &  # 排除价格异常
                ((stock_df['量比'] > 1) | (stock_df['涨跌幅'] > 1))  # 有竞价特征
            ]
            
            if pre_filtered.empty:
                return {
                    '数据状态': '无符合条件的股票',
                    '说明': '初筛后无符合条件的股票'
                }
            
            # 按综合指标排序（量比和涨跌幅加权），取前limit只进行深度分析
            pre_filtered['综合得分'] = pre_filtered['量比'] * 0.6 + pre_filtered['涨跌幅'] * 0.4
            filtered_stocks = pre_filtered.nlargest(limit, '综合得分')
            
            if filtered_stocks.empty:
                return {
                    '数据状态': '无符合条件的股票',
                    '说明': '当前市场无放量或涨幅明显的股票'
                }
            
            # 分析每只股票
            db = DataManager()
            auction_stocks = []
            
            for _, row in filtered_stocks.iterrows():
                symbol = row['代码']
                name = row['名称']
                current_price = row['最新价']
                change_pct = row['涨跌幅']
                volume_ratio = row['量比']
                turnover_rate = row['换手率']
                
                try:
                    # 获取历史数据
                    df = db.get_history_data(symbol)
                    
                    if not df.empty and len(df) > 5:
                        # 检测竞价弱转强
                        weak_to_strong = QuantAlgo.detect_auction_weak_to_strong(df, symbol)
                        
                        # 计算综合评分
                        score = 0
                        signals = []
                        
                        # 量比评分
                        if volume_ratio > 3:
                            score += 30
                            signals.append(f"大幅放量（量比{volume_ratio:.2f}）")
                        elif volume_ratio > 2:
                            score += 25
                            signals.append(f"放量（量比{volume_ratio:.2f}）")
                        elif volume_ratio > 1.5:
                            score += 20
                            signals.append(f"温和放量（量比{volume_ratio:.2f}）")
                        
                        # 涨跌幅评分
                        if change_pct > 5:
                            score += 25
                            signals.append(f"大幅高开{change_pct:.2f}%")
                        elif change_pct > 3:
                            score += 20
                            signals.append(f"高开{change_pct:.2f}%")
                        elif change_pct > 0:
                            score += 15
                            signals.append(f"小幅高开{change_pct:.2f}%")
                        
                        # 换手率评分
                        if 2 <= turnover_rate <= 10:
                            score += 25
                            signals.append(f"换手率适中（{turnover_rate:.2f}%）")
                        elif turnover_rate > 10:
                            score += 15
                            signals.append(f"换手率较高（{turnover_rate:.2f}%）")
                        
                        # 弱转强加分
                        if weak_to_strong.get('是否弱转强'):
                            score += 20
                            signals.append("竞价弱转强")
                        
                        # 评级
                        if score >= 80:
                            rating = "🔥 强势"
                            suggestion = "重点关注，竞价强势，可考虑参与"
                        elif score >= 60:
                            rating = "🟡 活跃"
                            suggestion = "关注，竞价活跃，观察盘中走势"
                        elif score >= 40:
                            rating = "🟢 一般"
                            suggestion = "一般，信号较弱，观望为主"
                        else:
                            rating = "⚪ 弱势"
                            suggestion = "弱势，不建议参与"
                        
                        auction_stocks.append({
                            '代码': symbol,
                            '名称': name,
                            '最新价': current_price,
                            '涨跌幅': change_pct,
                            '量比': volume_ratio,
                            '换手率': turnover_rate,
                            '评分': score,
                            '评级': rating,
                            '信号': signals,
                            '操作建议': suggestion,
                            '弱转强': weak_to_strong.get('是否弱转强', False)
                        })
                except Exception as e:
                    print(f"分析股票 {symbol} 失败: {e}")
                    continue
            
            db.close()
            
            # 按评分排序
            auction_stocks.sort(key=lambda x: x['评分'], reverse=True)
            
            return {
                '数据状态': '正常',
                '扫描数量': len(filtered_stocks),
                '符合条件数量': len(auction_stocks),
                '竞价股票列表': auction_stocks
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
