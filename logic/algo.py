import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from logic.logger import get_logger
from datetime import time
from typing import Dict, Any, Optional, List, Tuple, Union

# 🆕 V9.0: 导入游资掠食者系统
from logic.predator_system import PredatorSystem

# 🆕 V8.5: 导入算法数学库
from logic.algo_math import calculate_true_auction_aggression

logger = get_logger(__name__)


def get_time_weight(current_time=None, is_review_mode=False):
    """
    ⏰ V9.12.1 时间衰减因子：越早越贵，越晚越废
    
    游资心法：涨停的时间越早，溢价越高；涨停的时间越晚，气质越弱。
    
    Args:
        current_time: 当前时间（time对象），如果不提供则自动获取
        is_review_mode: 复盘模式开关。如果为 True，则忽略时间衰减，权重恒为 1.0
    
    Returns:
        float: 时间权重 (0.0 - 1.0)
    
    权重说明：
        1.0 - 👑 黄金半小时 (09:30-10:00)：秒板/硬板，满分
        0.9 - ⚔️ 上午博弈区 (10:00-11:30)：换手板，轻微衰减
        0.7 - 💤 下午昏睡区 (13:00-14:30)：跟风/磨叽，显著衰减
        0.4 - 🦊 尾盘偷袭区 (14:30-14:50)：非奸即盗，极低分
        0.0 - ☠️ 最后一击 (14:50-15:00)：直接一票否决
        1.0 - 其他情况（竞价期间等）
    
    🆕 V9.12.1 修复：复盘模式
        - 当 is_review_mode=True 时，返回 1.0，禁用时间衰减
        - 用于盘后复盘、回测分析等场景
    """
    # 🌟 V9.12.1 核心修复：如果是复盘模式，直接满分，还原股票本身的硬度
    if is_review_mode:
        return 1.0
    
    if current_time is None:
        from datetime import datetime
        from logic.market_status import get_market_status_checker
        checker = get_market_status_checker()
        current_time = checker.get_current_time()
    
    t_0930 = time(9, 30)
    t_1000 = time(10, 0)
    t_1130 = time(11, 30)
    t_1430 = time(14, 30)
    t_1450 = time(14, 50)
    
    # 1. 👑 黄金半小时 (秒板/硬板)
    if t_0930 <= current_time <= t_1000:
        return 1.0  # 满分
        
    # 2. ⚔️ 上午博弈区 (换手板)
    elif t_1000 < current_time <= t_1130:
        return 0.9  # 轻微衰减
        
    # 3. 💤 下午昏睡区 (跟风/磨叽)
    elif time(13, 0) <= current_time <= t_1430:
        return 0.7  # 显著衰减
        
    # 4. 🦊 尾盘偷袭区 (非奸即盗)
    elif t_1430 < current_time <= t_1450:
        return 0.4  # 极低分，基本不看
        
    # 5. ☠️ 最后一击 (通常是为了做K线骗人)
    elif current_time > t_1450:
        return 0.0  # 直接一票否决
        
    return 1.0  # 竞价期间或其他情况

class QuantAlgo:

    # 股票名称缓存
    _stock_names_cache = {}

    @staticmethod
    def check_limit_status(code, current_pct, name=""):
        """
        精准判定涨停状态
        返回: (is_limit_up, is_20cm, status_text)
        """
        # 1. 判定是否为 20cm 标的 (创业板 30/科创板 68)
        is_20cm = code.startswith(('30', '68'))

        # 2. 判定是否为 ST (5% 涨停)
        is_st = 'ST' in name.upper()

        # 3. 设定阈值
        if is_20cm:
            limit_threshold = 19.5
        elif is_st:
            limit_threshold = 4.8
        else:
            limit_threshold = 9.5

        is_limit_up = current_pct >= limit_threshold

        # 4. 生成状态文本
        if is_limit_up:
            status_text = "涨停封死"
        elif is_20cm and 10.0 <= current_pct < 19.5:
            status_text = "半路板（加速逼空）"
        elif current_pct >= 9.5:
            status_text = "接近涨停"
        else:
            status_text = "正常交易"

        return is_limit_up, is_20cm, status_text

    

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
        # 🆕 V8.3: 修复单位换算BUG
        # df['volume']来自akshare，是股数，需要转换为手数（除以100）
        current_volume = df['volume'].iloc[-1] / 100  # 转换为手数
        avg_volume = df['volume'].rolling(window=period).mean().iloc[-1] / 100  # 转换为手数
        
        # 🆕 V8.3: 添加异常值检测
        # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
        if avg_volume < 1000:
            volume_ratio = 1  # 不计算，避免异常值
        elif avg_volume > 0:
            volume_ratio = current_volume / avg_volume
        else:
            volume_ratio = 1
        
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
    def filter_active_stocks(all_stocks: list, min_change_pct: float = 3.0, 
                            min_volume: float = 10000, min_amount: float = 5000,
                            watchlist: list = None) -> list:
        """
        🆕 V9.9：股票池过滤（基于快照数据的粗筛）
        🆕 V9.10 修复：添加核心监控池白名单功能
        
        Args:
            all_stocks: 全市场股票列表（来自get_fast_price）
            min_change_pct: 最小涨幅（默认3%）
            min_volume: 最小成交量（手，默认10000手）
            min_amount: 最小成交额（万元，默认5000万）
            watchlist: 核心监控池白名单（这些股票跳过过滤条件）
        
        Returns:
            过滤后的活跃股票列表
        """
        if watchlist is None:
            watchlist = []
        
        # 转换监控池为集合，提高查找效率
        watchlist_set = set(watchlist)
        
        filtered_stocks = []
        watchlist_matched = []
        
        for stock in all_stocks:
            try:
                code = stock.get('代码', '')
                
                # 🆕 V9.10 修复：如果股票在监控池中，跳过过滤条件
                if code in watchlist_set:
                    watchlist_matched.append(stock)
                    logger.debug(f"✅ 监控池命中: {code} ({stock.get('名称', '')})")
                    continue
                
                # 1. 涨幅过滤
                if stock.get('涨跌幅', 0) < min_change_pct:
                    continue
                
                # 2. 成交量过滤
                if stock.get('成交量', 0) < min_volume:
                    continue
                
                # 3. 成交额过滤
                if stock.get('成交额', 0) < min_amount:
                    continue
                
                # 4. 排除ST股票（可选）
                name = stock.get('名称', '')
                if 'ST' in name.upper() or '退' in name:
                    continue
                
                # 5. 排除停牌股票（价格为0或成交量为0）
                if stock.get('最新价', 0) == 0 or stock.get('成交量', 0) == 0:
                    continue
                
                filtered_stocks.append(stock)
            except Exception as e:
                continue
        
        # 🆕 V9.10 修复：监控池股票优先返回
        result = watchlist_matched + filtered_stocks
        
        logger.info(f"🔍 股票池过滤：全市场 {len(all_stocks)} 只 → 监控池 {len(watchlist_matched)} 只 + 活跃股票 {len(filtered_stocks)} 只")
        return result
    
    @staticmethod
    def scan_dragon_stocks(limit=50, min_score=60, min_change_pct=9.9, min_volume=5000, min_amount=3000, watchlist=None, use_history=False, date=None):
        """
        扫描市场中的潜在龙头股
        
        Args:
            limit: 扫描的股票数量限制
            min_score: 最低评分门槛
            min_change_pct: 最小涨幅（默认9.9%，即涨停板）
            min_volume: 最小成交量（手，默认5000手）
            min_amount: 最小成交额（万元，默认3000万）
            watchlist: 核心监控池白名单（这些股票跳过过滤条件）
            use_history: 是否使用历史数据（复盘模式）
            date: 复盘日期（格式：YYYYMMDD），默认为今天
        
        返回: 符合条件的龙头股列表
        """
        try:
            import akshare as ak
            from logic.data_manager import DataManager
            from datetime import datetime
            
            # 获取涨停板股票
            if use_history:
                # 🚀 V19.4.4 新增：复盘模式，使用 akshare 获取涨停板数据
                if date is None:
                    date = datetime.now().strftime("%Y%m%d")
                
                logger.info(f"🔄 [复盘模式] 获取 {date} 的涨停板数据...")
                zt_df = ak.stock_zt_pool_em(date=date)
                
                if zt_df is None or zt_df.empty:
                    return {
                        '数据状态': '无法获取涨停板数据',
                        '说明': f'可能是日期 {date} 没有数据或数据源限制',
                        '扫描数量': 0
                    }
                
                # 转换为列表格式
                all_stocks = []
                for _, row in zt_df.iterrows():
                    all_stocks.append({
                        '代码': row['代码'],
                        '名称': row['名称'],
                        '最新价': row['最新价'],
                        '涨跌幅': row['涨跌幅'],
                        '成交量': row['成交量'] / 100 if '成交量' in row else 0,  # 转换为手
                        '成交额': row['成交额'] / 10000 if '成交额' in row else 0,  # 转换为万元
                        '开盘价': row['开盘价'] if '开盘价' in row else 0,
                        '昨收价': row['昨收价'] if '昨收价' in row else 0,
                        '最高价': row['最高价'] if '最高价' in row else 0,
                        '最低价': row['最低价'] if '最低价' in row else 0,
                        '买一价': 0,
                        '卖一价': 0,
                        '买一量': 0,
                        '卖一量': 0
                    })
                
                logger.info(f"✅ [复盘模式] 获取到 {len(all_stocks)} 只涨停板股票")
                
                # 🆕 V9.9 新增：先进行股票池过滤，减少需要下载K线的股票数量
                # 筛选涨停板股票（涨跌幅 >= min_change_pct）
                limit_up_stocks = [s for s in all_stocks if s['涨跌幅'] >= min_change_pct]
                
                # 🚀 V19.4.7 新增：记录过滤前的数量
                logger.info(f"🔍 [复盘模式] 过滤前：{len(all_stocks)} 只涨停板股票")
                
                # 🆕 V9.9 新增：对涨停板股票进行二次过滤（成交量、成交额等）
                # 🆕 V9.10 修复：添加监控池白名单
                active_stocks = QuantAlgo.filter_active_stocks(
                    limit_up_stocks, 
                    min_change_pct=min_change_pct,
                    min_volume=min_volume,
                    min_amount=min_amount,
                    watchlist=watchlist
                )
                
                # 🚀 V19.4.7 新增：记录过滤后的数量
                logger.info(f"🔍 [复盘模式] 过滤后：{len(active_stocks)} 只股票（被过滤掉 {len(limit_up_stocks) - len(active_stocks)} 只）")
                
                # 🚀 V19.4.7 新增：记录被过滤掉的股票（前10只）
                if len(active_stocks) < len(limit_up_stocks):
                    filtered_out = limit_up_stocks[:10]
                    logger.info(f"🔍 [复盘模式] 被过滤掉的股票（前10只）：")
                    for stock in filtered_out:
                        logger.info(f"  - {stock['代码']} {stock['名称']}: 涨幅={stock['涨跌幅']:.2f}%, 成交量={stock['成交量']:.0f}手, 成交额={stock['成交额']:.0f}万元")
                
                logger.info(f"🔍 [复盘模式] 股票池过滤：全市场 {len(all_stocks)} 只 → 监控池 0 只 + 活跃股票 {len(active_stocks)} 只")
                
                if not active_stocks:
                    return {
                        '数据状态': '无符合条件的涨停板股票',
                        '说明': f'{date} 无符合条件的涨停板股票（已过滤成交量和成交额）',
                        '扫描数量': len(all_stocks),
                        '全市场数量': len(all_stocks),
                        '涨停板数量': len(limit_up_stocks),
                        '过滤后数量': len(active_stocks)
                    }
                
                # 按涨跌幅排序，取前 limit 只
                active_stocks.sort(key=lambda x: x['涨跌幅'], reverse=True)
                stocks_to_analyze = active_stocks[:limit]
                
                # 🚀 批量预加载历史数据，避免每次都查询数据库
                logger.info(f"开始批量加载 {len(stocks_to_analyze)} 只涨停板股票的历史数据...")
                history_data_cache = {}
                for stock in stocks_to_analyze:
                    symbol = stock['代码']
                    try:
                        # 获取历史数据（包括当天）
                        df = db.get_history_data(symbol)
                        if not df.empty and len(df) > 20:
                            history_data_cache[symbol] = df
                    except Exception as e:
                        logger.warning(f"加载股票 {symbol} 历史数据失败: {e}")
                logger.info(f"✅ 历史数据加载完成，成功加载 {len(history_data_cache)} 只股票")
                
                # 🚀 使用多线程并行分析
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                # 定义分析函数
                def analyze_single_stock(stock_info):
                    """分析单只股票"""
                    symbol = stock_info['代码']
                    name = stock_info['名称']
                    current_price = stock_info['最新价']
                    
                    # 过滤 ST 股
                    if 'ST' in name or '*ST' in name:
                        return None
                    
                    try:
                        # 从缓存中获取历史数据
                        df = history_data_cache.get(symbol)
                        
                        if not df.empty and len(df) > 20:
                            # 龙头战法分析（传入股票代码和涨跌幅）
                            dragon_analysis = QuantAlgo.analyze_dragon_stock(df, current_price, symbol, stock_info['涨跌幅'])
                            
                            # 计算开盘涨幅
                            open_price = stock_info.get('开盘价', 0)
                            last_close = stock_info.get('昨收价', 0)
                            if open_price > 0 and last_close > 0:
                                open_gap_pct = (open_price - last_close) / last_close * 100
                            else:
                                open_gap_pct = 0
                            
                            # 计算量比（使用成交额来计算，更准确）
                            volume_ratio = 0
                            if not df.empty and len(df) > 5:
                                if 'turnover' in df.columns:
                                    avg_turnover = df['turnover'].tail(5).mean()
                                    current_turnover = stock_info.get('成交额', 0) * 10000  # 转换为元
                                    if avg_turnover > 0:
                                        volume_ratio = current_turnover / avg_turnover
                                else:
                                    avg_volume = df['volume'].tail(5).mean() / 100
                                    current_volume = stock_info.get('成交量', 0)
                                    if avg_volume < 1000:
                                        volume_ratio = 1
                                    elif avg_volume > 0:
                                        volume_ratio = current_volume / avg_volume
                            
                            # 计算换手率
                            turnover_rate = 0
                            if not df.empty and len(df) > 5:
                                if 'turnover_rate' in df.columns:
                                    avg_turnover_rate = df['turnover_rate'].tail(5).mean()
                                    current_turnover_rate = df['turnover_rate'].iloc[-1]
                                    if avg_turnover_rate > 0:
                                        turnover_rate = current_turnover_rate / avg_turnover_rate
                            
                            # 计算封单金额
                            limit_up_amount = 0
                            if stock_info['买一价'] > 0 and stock_info['买一量'] > 0:
                                limit_up_amount = stock_info['买一价'] * stock_info['买一量'] * 100
                            
                            # 计算封单比
                            limit_up_ratio = 0
                            if stock_info['成交额'] > 0 and limit_up_amount > 0:
                                limit_up_ratio = limit_up_amount / (stock_info['成交额'] * 10000)
                            
                            # 计算连板数
                            lianban_count = 0
                            if not df.empty and len(df) > 5:
                                for i in range(1, min(6, len(df))):
                                    if df.iloc[-i]['涨跌幅'] >= 9.5:
                                        lianban_count += 1
                                    else:
                                        break
                            
                            # 计算评分
                            score = dragon_analysis['评级得分']
                            
                            # 评分调整（基于量比、换手率、封单比、连板数）
                            if volume_ratio >= 2.0:
                                score += 5
                            elif volume_ratio >= 1.5:
                                score += 3
                            
                            if turnover_rate >= 2.0:
                                score += 5
                            elif turnover_rate >= 1.5:
                                score += 3
                            
                            if limit_up_ratio >= 0.1:
                                score += 5
                            elif limit_up_ratio >= 0.05:
                                score += 3
                            
                            if lianban_count >= 2:
                                score += 5
                            elif lianban_count == 1:
                                score += 3
                            
                            score = min(score, 100)
                            
                            return {
                                '代码': symbol,
                                '名称': name,
                                '最新价': current_price,
                                '涨跌幅': stock_info['涨跌幅'],
                                '评级得分': score,
                                '量比': volume_ratio,
                                '换手率': turnover_rate,
                                '封单比': limit_up_ratio,
                                '连板数': lianban_count,
                                '开盘涨幅': open_gap_pct,
                                '成交额': stock_info.get('成交额', 0),
                                '成交量': stock_info.get('成交量', 0),
                                '角色': dragon_analysis.get('role', '未知'),
                                'lianban_status': f"{lianban_count}板" if lianban_count > 0 else "首板"
                            }
                    except Exception as e:
                        logger.error(f"分析股票 {symbol} 失败: {e}")
                        return None
                
                # 并行分析
                results = []
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(analyze_single_stock, stock): stock for stock in stocks_to_analyze}
                    
                    for future in as_completed(futures):
                        stock = futures[future]
                        try:
                            result = future.result(timeout=10)
                            if result and result['评级得分'] >= min_score:
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"分析股票 {stock['代码']} 超时或失败: {e}")
                
                # 按评分排序
                results.sort(key=lambda x: x['评级得分'], reverse=True)
                
                return {
                    '数据状态': '正常',
                    '扫描数量': len(all_stocks),
                    '分析数量': len(stocks_to_analyze),
                    '符合条件数量': len(results),
                    '龙头股列表': results
                }
            else:
                # 原有的实时扫描模式
                db = DataManager()
                
                # 使用 akshare 获取股票列表
                stock_list_df = ak.stock_info_a_code_name()
                if stock_list_df.empty:
                    return {
                        '数据状态': '无法获取股票列表',
                        '说明': '可能是数据源限制'
                    }
                
                # 获取全市场所有股票
                stock_list = stock_list_df['code'].tolist()

                # 使用 Easyquotation 极速获取全市场实时数据
                logger.info(f"开始扫描全市场 {len(stock_list)} 只股票的实时行情...")
                realtime_data = db.get_fast_price(stock_list)
                logger.info(f"✅ 实时行情获取完成，获取到 {len(realtime_data)} 只股票数据")
                
                if not realtime_data:
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
                            '涨跌幅': pct_change,
                            # 保存完整的实时数据，包括买卖盘口
                            '买一价': data.get('bid1', 0),
                            '卖一价': data.get('ask1', 0),
                            '买一量': data.get('bid1_volume', 0),
                            '卖一量': data.get('ask1_volume', 0),
                            '成交量': data.get('volume', 0) / 100,  # 转换为手
                            '成交额': data.get('turnover', 0),
                            '开盘价': data.get('open', 0),
                            '昨收价': data.get('close', 0),
                            '最高价': data.get('high', 0),
                            '最低价': data.get('low', 0)
                        })
                    except Exception as e:
                        continue
            
            # 🆕 V9.9 新增：先进行股票池过滤，减少需要下载K线的股票数量
            # 筛选涨停板股票（涨跌幅 >= min_change_pct）
            limit_up_stocks = [s for s in all_stocks if s['涨跌幅'] >= min_change_pct]

            # 🆕 V9.9 新增：对涨停板股票进行二次过滤（成交量、成交额等）
            # 🆕 V9.10 修复：添加监控池白名单
            active_stocks = QuantAlgo.filter_active_stocks(
                limit_up_stocks, 
                min_change_pct=min_change_pct,
                min_volume=min_volume,
                min_amount=min_amount,
                watchlist=watchlist
            )

            # 按涨跌幅排序，取前 limit 只
            active_stocks.sort(key=lambda x: x['涨跌幅'], reverse=True)
            stocks_to_analyze = active_stocks[:limit]

            if not stocks_to_analyze:
                return {
                    '数据状态': '无符合条件的涨停板股票',
                    '说明': '当前市场无符合条件的涨停板股票（已过滤成交量和成交额）',
                    '扫描数量': len(stock_list),
                    '全市场数量': len(all_stocks),
                    '涨停板数量': len(limit_up_stocks),
                    '过滤后数量': len(active_stocks)
                }

            # 🚀 批量预加载历史数据，避免每次都查询数据库
            logger.info(f"开始批量加载 {len(stocks_to_analyze)} 只涨停板股票的历史数据...")
            history_data_cache = {}
            for stock in stocks_to_analyze:
                symbol = stock['代码']
                try:
                    df = db.get_history_data(symbol)
                    if not df.empty and len(df) > 20:
                        history_data_cache[symbol] = df
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 历史数据失败: {e}")
            logger.info(f"✅ 历史数据加载完成，成功加载 {len(history_data_cache)} 只股票")

            # 🚀 使用多线程并行分析
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            # 构建股票代码到实时数据的映射（方便查找）
            realtime_map = {}
            for full_code, data in realtime_data.items():
                code = full_code if len(full_code) == 6 else full_code[2:]
                realtime_map[code] = data

            # 定义分析函数
            def analyze_single_stock(stock_info):
                """分析单只股票"""
                symbol = stock_info['代码']
                name = stock_info['名称']
                current_price = stock_info['最新价']

                # 过滤 ST 股
                if 'ST' in name or '*ST' in name:
                    return None

                try:
                    # 从缓存中获取历史数据
                    df = history_data_cache.get(symbol)
                    
                    if not df.empty and len(df) > 20:
                        # 龙头战法分析（传入股票代码和涨跌幅）
                        dragon_analysis = QuantAlgo.analyze_dragon_stock(df, current_price, symbol, stock_info['涨跌幅'])
                        
                        # 获取实时数据（用于计算量比、换手率等）
                        realtime_data_item = realtime_map.get(symbol, {})
                        
                        # 优先使用 stock_info 中的买卖盘口数据，如果没有则使用 realtime_data_item
                        bid1_volume = stock_info.get('买一量', 0) or realtime_data_item.get('bid1_volume', 0)
                        ask1_volume = stock_info.get('卖一量', 0) or realtime_data_item.get('ask1_volume', 0)
                        bid1_price = stock_info.get('买一价', 0) or realtime_data_item.get('bid1', 0)
                        ask1_price = stock_info.get('卖一价', 0) or realtime_data_item.get('ask1', 0)
                        
                        # 计算开盘涨幅
                        open_price = realtime_data_item.get('open', 0)
                        last_close = realtime_data_item.get('close', 0)
                        if open_price > 0 and last_close > 0:
                            open_gap_pct = (open_price - last_close) / last_close * 100
                        else:
                            open_gap_pct = 0
                        
                        # 计算量比（使用成交额来计算，更准确）
                        volume_ratio = 0
                        if not df.empty and len(df) > 5:
                            # 检查是否有 turnover 列
                            if 'turnover' in df.columns:
                                avg_turnover = df['turnover'].tail(5).mean()  # 5日平均成交额
                                current_turnover = realtime_data_item.get('turnover', 0)  # 当前成交额
                                if avg_turnover > 0:
                                    volume_ratio = current_turnover / avg_turnover
                            else:
                                # 🆕 V8.1: 修复单位换算BUG
                                # 如果没有 turnover 列，使用成交量计算
                                # 历史数据的volume是股数（来自akshare），需要转换为手数（除以100）
                                # 实时数据的volume是股数（来自easyquotation），也需要转换为手数
                                avg_volume = df['volume'].tail(5).mean() / 100  # 转换为手数
                                current_volume = realtime_data_item.get('volume', 0) / 100  # 转换为手数
                                
                                # 🆕 V8.3: 添加异常值检测
                                # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
                                if avg_volume < 1000:
                                    volume_ratio = 1  # 不计算，避免异常值
                                elif avg_volume > 0:
                                    volume_ratio = current_volume / avg_volume
                        
                        # 计算换手率（使用历史数据中的换手率）
                        turnover_rate = 0
                        if not df.empty:
                            # 使用最近一天的换手率
                            turnover_rate = df['turnover_rate'].iloc[-1] if 'turnover_rate' in df.columns else 0
                        
                        # 获取竞价数据
                        bid1_volume = realtime_data_item.get('bid1_volume', 0)  # 买一量（手数，来自Easyquotation）
                        ask1_volume = realtime_data_item.get('ask1_volume', 0)  # 卖一量（手数，来自Easyquotation）
                        bid1_price = realtime_data_item.get('bid1', 0)  # 买一价
                        ask1_price = realtime_data_item.get('ask1', 0)  # 卖一价
                        
                        # 🆕 V9.2 修复：竞价量应该是集合竞价期间的成交量，不是买一量加卖一量
                        # 🆕 V9.2 新增：优先从 Redis 恢复竞价数据
                        auction_volume = realtime_data_item.get('竞价量', 0)  # 从 DataManager 传递过来的竞价量（可能来自 Redis）
                        
                        # 如果 auction_volume 仍然是 0，尝试从 DataManager 快照管理器恢复
                        if auction_volume == 0 and hasattr(db, 'auction_snapshot_manager') and db.auction_snapshot_manager:
                            snapshot = db.auction_snapshot_manager.load_auction_snapshot(symbol)
                            if snapshot:
                                auction_volume = snapshot.get('auction_volume', 0)
                                logger.debug(f"✅ [竞价恢复] {symbol} 竞价数据已从 Redis 恢复")
                        
                        # 🆕 V8.5: 使用标准竞价抢筹度计算器（修复 6900% BUG）
                        auction_ratio = 0
                        if not df.empty and len(df) > 1:
                            # 获取昨日全天成交量（手数）
                            yesterday_volume = df['volume'].iloc[-2] / 100  # 昨日成交量（手数）
                            
                            # 获取流通股本（股数）
                            circulating_cap = None
                            if 'circulating_cap' in df.columns:
                                circulating_cap = df['circulating_cap'].iloc[-1]
                            
                            # 判断是否为新股
                            is_new_stock = (symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688'))
                            
                            # 使用标准计算器
                            auction_ratio = calculate_true_auction_aggression(
                                auction_vol=auction_volume,
                                prev_day_vol=yesterday_volume,
                                circulating_share_capital=circulating_cap,
                                is_new_stock=is_new_stock
                            ) / 100  # 转换为比例

                    # 计算封单金额（针对涨停股）
                    seal_amount = 0
                    # 只有当卖一价为 0（真正涨停）时才计算封单金额
                    if ask1_price == 0 and stock_info['涨跌幅'] >= 9.5:  # 涨停板
                        # 涨停时，封单金额 = 买一量（手数）× 100（股/手）× 价格
                        seal_amount = bid1_volume * 100 * current_price / 10000  # 转换为万
                        # 计算买卖盘口价差
                        price_gap = 0
                        if bid1_price > 0 and ask1_price > 0:
                            price_gap = (ask1_price - bid1_price) / bid1_price * 100

                        # 添加调试信息
                        score = dragon_analysis.get('评级得分', 0)
                        print(f"{name}({symbol}) - 涨幅:{stock_info['涨跌幅']:.2f}% - 评分:{score} - {dragon_analysis['龙头评级']}")

                        # 只保留评分达到门槛的股票
                        if dragon_analysis.get('评级得分', 0) >= min_score:
                            return {
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
                                '竞价量': int(auction_volume),
                                '买一价': round(bid1_price, 2),
                                '卖一价': round(ask1_price, 2),
                                '买一量': int(bid1_volume),
                                '卖一量': int(ask1_volume),
                                '竞价抢筹度': round(auction_ratio, 4),
                                '开盘涨幅': round(open_gap_pct, 2),
                                '封单金额': round(seal_amount, 2),
                                '买卖价差': round(price_gap, 2)
                            }
                except Exception as e:
                    print(f"分析股票 {symbol} 失败: {e}")
                    return None

            # 🚀 使用线程池并行分析
            dragon_stocks = []
            max_workers = min(8, len(stocks_to_analyze))  # 最多 8 个线程

            logger.info(f"开始并行分析 {len(stocks_to_analyze)} 只股票（使用 {max_workers} 个线程）...")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有分析任务
                future_to_stock = {
                    executor.submit(analyze_single_stock, stock): stock
                    for stock in stocks_to_analyze
                }

                # 收集结果
                for future in as_completed(future_to_stock):
                    result = future.result()
                    if result is not None:
                        dragon_stocks.append(result)

            logger.info(f"✅ 并行分析完成，找到 {len(dragon_stocks)} 只符合条件的股票")
            
            # 按评分排序
            dragon_stocks.sort(key=lambda x: x['评级得分'], reverse=True)
            
            return {
                '数据状态': '正常',
                '扫描数量': len(stock_list),
                '涨停板数量': len(limit_up_stocks),
                '分析数量': len(stocks_to_analyze),
                '符合条件数量': len(dragon_stocks),
                '龙头股列表': dragon_stocks
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
        使用 Easyquotation 极速接口
        """
        try:
            from logic.data_manager import DataManager
            
            # 使用 Easyquotation 获取实时数据
            db = DataManager()
            
            # 获取股票列表
            import akshare as ak
            stock_list_df = ak.stock_info_a_code_name()
            
            if stock_list_df.empty:
                db.close()
                return {
                    '数据状态': '无法获取股票列表',
                    '说明': '可能是数据源限制'
                }
            
            stock_list = stock_list_df['code'].tolist()
            
            # 使用 Easyquotation 极速获取实时数据
            realtime_data = db.get_fast_price(stock_list)
            
            if not realtime_data:
                db.close()
                return {
                    '数据状态': '无法获取实时数据',
                    '说明': 'Easyquotation 未初始化或网络问题'
                }
            
            # 筛选需要的列
            auction_stocks = []
            for full_code, data in realtime_data.items():
                try:
                    # 提取股票代码
                    if len(full_code) == 6:
                        code = full_code
                    elif len(full_code) > 6:
                        code = full_code[2:]
                    else:
                        continue
                    
                    current_price = float(data.get('now', 0))
                    last_close = float(data.get('close', 0))
                    
                    if current_price == 0 or last_close == 0:
                        continue
                    
                    pct_change = (current_price - last_close) / last_close * 100
                    
                    # 获取竞价量
                    bid1_volume = data.get('bid1_volume', 0)  # 买一量（手数，来自Easyquotation）
                    ask1_volume = data.get('ask1_volume', 0)  # 卖一量（手数，来自Easyquotation）
                    
                    # 🆕 V9.2 修复：竞价量应该是集合竞价期间的成交量，不是买一量加卖一量
                    # 在连续竞价期间（9:30-15:00），竞价量应该为 0
                    auction_volume = 0  # 连续竞价期间，竞价量为 0
                    
                    # 获取成交量（Easyquotation 返回的是股数，需要转换为手数）
                    volume = data.get('volume', 0) / 100  # 转换为手
                    
                    # 计算开盘涨幅
                    open_price = data.get('open', 0)
                    if open_price > 0 and last_close > 0:
                        open_gap_pct = (open_price - last_close) / last_close * 100
                    else:
                        open_gap_pct = 0
                    
                    # 计算封单金额（针对涨停股）
                    seal_amount = 0
                    # 只有当卖一价为 0（真正涨停）时才计算封单金额
                    ask1_price = data.get('ask1', 0)
                    if ask1_price == 0 and pct_change >= 9.5:  # 涨停板
                        # 封单金额 = 买一量（手数）× 100（股/手）× 价格
                        seal_amount = bid1_volume * 100 * current_price / 10000  # 转换为万
                    
                    # 计算买卖盘口价差
                    bid1_price = data.get('bid1', 0)
                    ask1_price = data.get('ask1', 0)
                    price_gap = 0
                    if bid1_price > 0 and ask1_price > 0:
                        price_gap = (ask1_price - bid1_price) / bid1_price * 100
                    
                    auction_stocks.append({
                        '代码': code,
                        '名称': data.get('name', ''),
                        '最新价': current_price,
                        '涨跌幅': pct_change,
                        '成交量': volume,
                        '成交额': data.get('turnover', 0) / 10000,  # 转换为万元
                        '量比': 0,  # 需要从历史数据计算
                        '换手率': 0,  # 需要从历史数据计算
                        '竞价量': int(auction_volume),
                        '买一量': int(bid1_volume),
                        '卖一量': int(ask1_volume),
                        '买一价': bid1_price,
                        '卖一价': ask1_price,
                        '竞价抢筹度': 0,  # 需要从历史数据计算
                        '开盘涨幅': round(open_gap_pct, 2),
                        '封单金额': round(seal_amount, 2),
                        '买卖价差': round(price_gap, 2)
                    })
                except Exception as e:
                    continue
            
            db.close()
            
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
            # 🆕 V8.3: 修复单位换算BUG
            # today和yesterday来自akshare，是股数，需要转换为手数（除以100）
            today_volume = today.get('volume', 0) / 100  # 转换为手数
            yesterday_volume = yesterday.get('volume', 0) / 100  # 转换为手数
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
                
                # 计算封单金额（估算：成交量 * 100 * 当前价格）
                volume = row['成交量']
                seal_amount = volume * 100 * current_price
                
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
        使用 Easyquotation 极速接口
        
        limit: 扫描的股票数量限制
        """
        try:
            from logic.data_manager import DataManager
            
            # 获取股票列表
            import akshare as ak
            stock_list_df = ak.stock_info_a_code_name()
            
            if stock_list_df.empty:
                return {
                    '数据状态': '无法获取股票列表',
                    '说明': '可能是数据源限制'
                }
            
            stock_list = stock_list_df['code'].tolist()

            # 使用 Easyquotation 极速获取全市场实时数据
            db = DataManager()
            logger.info(f"开始扫描全市场 {len(stock_list)} 只股票的集合竞价数据...")
            realtime_data = db.get_fast_price(stock_list)
            logger.info(f"✅ 集合竞价数据获取完成，获取到 {len(realtime_data)} 只股票数据")
            
            if not realtime_data:
                db.close()
                return {
                    '数据状态': '无法获取实时数据',
                    '说明': 'Easyquotation 未初始化或网络问题'
                }
            
            # 转换为列表格式
            all_stocks = []
            for full_code, data in realtime_data.items():
                try:
                    # 提取股票代码
                    if len(full_code) == 6:
                        code = full_code
                    elif len(full_code) > 6:
                        code = full_code[2:]
                    else:
                        continue
                    
                    # 只保留 A 股股票（6位数字，以 0、3、6 开头）
                    if not (len(code) == 6 and code.isdigit() and code[0] in ['0', '3', '6']):
                        continue
                    
                    name = data.get('name', '')
                    
                    # 排除 ST 股
                    if 'ST' in name or '*ST' in name:
                        continue
                    
                    current_price = float(data.get('now', 0))
                    last_close = float(data.get('close', 0))
                    
                    if current_price == 0 or last_close == 0:
                        continue
                    
                    pct_change = (current_price - last_close) / last_close * 100
                    
                    # 获取成交量（Easyquotation 返回的是股数，需要转换为手数）
                    volume = data.get('volume', 0) / 100
                    
                    # 获取竞价量
                    bid1_volume = data.get('bid1_volume', 0)  # 买一量（手数，来自Easyquotation）
                    ask1_volume = data.get('ask1_volume', 0)  # 卖一量（手数，来自Easyquotation）
                    
                    # 🆕 V9.2 修复：竞价量应该是集合竞价期间的成交量，不是买一量加卖一量
                    # 在连续竞价期间（9:30-15:00），竞价量应该为 0
                    auction_volume = 0  # 连续竞价期间，竞价量为 0
                    
                    # 快速初筛：只保留有成交量 且 涨跌幅 > 1% 的股票
                    if volume > 0 and pct_change > 1:
                        all_stocks.append({
                            '代码': code,
                            '名称': name,
                            '最新价': current_price,
                            '涨跌幅': pct_change,
                            '成交量': volume,
                            '竞价量': int(auction_volume),
                            '买一价': data.get('bid1', 0),
                            '卖一价': data.get('ask1', 0),
                            '买一量': bid1_volume,
                            '卖一量': ask1_volume
                        })
                except Exception as e:
                    continue
            
            # 不要关闭数据库连接，后面还要用
            # db.close()

            if not all_stocks:
                return {
                    '数据状态': '无符合条件的股票',
                    '说明': '当前市场无放量或涨幅明显的股票'
                }

            # 🚀 优化：先按涨跌幅和竞价量初步排序，限制候选股票数量
            # 避免加载过多历史数据导致超时
            max_candidates = min(200, len(all_stocks))  # 最多 200 只候选股票
            all_stocks.sort(key=lambda x: (x['涨跌幅'], x['竞价量']), reverse=True)
            all_stocks = all_stocks[:max_candidates]
            logger.info(f"初步筛选后保留 {len(all_stocks)} 只候选股票")

            # 按综合指标排序（竞价量和涨跌幅加权），取前limit只进行深度分析
            # 🚀 批量预加载历史数据
            logger.info(f"开始批量加载 {len(all_stocks)} 只候选股票的历史数据...")
            history_data_cache = {}
            for stock in all_stocks:
                symbol = stock['代码']
                try:
                    df = db.get_history_data(symbol)
                    if not df.empty and len(df) > 5:
                        history_data_cache[symbol] = df
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 历史数据失败: {e}")
            logger.info(f"✅ 历史数据加载完成，成功加载 {len(history_data_cache)} 只股票")

            for stock in all_stocks:
                # 计算量比（使用缓存的历史数据）
                try:
                    df = history_data_cache.get(stock['代码'])
                    if df is not None and not df.empty and len(df) > 5:
                        # 🆕 V8.1: 修复单位换算BUG
                        # 历史数据的volume是股数（来自akshare），需要转换为手数（除以100）
                        # 实时数据的成交量已经是手数（在前面已除以100）
                        avg_volume = df['volume'].tail(5).mean() / 100  # 转换为手数
                        
                        # 🆕 V8.3: 添加异常值检测
                        # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
                        if avg_volume < 1000:
                            stock['量比'] = 1  # 不计算，避免异常值
                        elif avg_volume > 0:
                            stock['量比'] = stock['成交量'] / avg_volume
                        else:
                            stock['量比'] = 1
                    else:
                        stock['量比'] = 1
                except:
                    stock['量比'] = 1
            
            # 计算综合得分
            for stock in all_stocks:
                stock['综合得分'] = stock['量比'] * 0.6 + stock['涨跌幅'] * 0.4
            
            # 按综合得分排序，取前 limit 只
            filtered_stocks = sorted(all_stocks, key=lambda x: x['综合得分'], reverse=True)[:limit]

            # 🚀 使用多线程并行分析
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # 构建股票代码到实时数据的映射（方便查找）
            realtime_map = {}
            for full_code, data in realtime_data.items():
                code = full_code if len(full_code) == 6 else full_code[2:]
                realtime_map[code] = data

            # 定义分析函数
            def analyze_auction_stock(stock):
                """分析单只集合竞价股票"""
                try:
                    symbol = stock['代码']
                    name = stock['名称']
                    current_price = stock['最新价']
                    change_pct = stock['涨跌幅']
                    volume_ratio = stock['量比']
                    auction_volume = stock['竞价量']

                    # 获取实时数据（用于计算额外指标）
                    realtime_data_item = realtime_map.get(symbol, {})

                    # 计算开盘涨幅
                    open_price = realtime_data_item.get('open', 0)
                    last_close = realtime_data_item.get('close', 0)
                    if open_price > 0 and last_close > 0:
                        open_gap_pct = (open_price - last_close) / last_close * 100
                    else:
                        open_gap_pct = 0

                    # 获取买卖盘口数据
                    bid1_volume = realtime_data_item.get('bid1_volume', 0)  # 买一量（手数，来自Easyquotation）
                    ask1_volume = realtime_data_item.get('ask1_volume', 0)  # 卖一量（手数，来自Easyquotation）
                    bid1_price = realtime_data_item.get('bid1', 0)  # 买一价
                    ask1_price = realtime_data_item.get('ask1', 0)  # 卖一价

                    # 🆕 V8.5: 使用标准竞价抢筹度计算器（修复 6900% BUG）
                    auction_ratio = 0
                    if not df.empty and len(df) > 1:
                        # 获取昨日全天成交量（手数）
                        yesterday_volume = df['volume'].iloc[-2] / 100  # 昨日成交量（手数）
                        
                        # 获取流通股本（股数）
                        circulating_cap = None
                        if 'circulating_cap' in df.columns:
                            circulating_cap = df['circulating_cap'].iloc[-1]
                        
                        # 判断是否为新股
                        is_new_stock = (symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688'))
                        
                        # 使用标准计算器
                        auction_ratio = calculate_true_auction_aggression(
                            auction_vol=auction_volume,
                            prev_day_vol=yesterday_volume,
                            circulating_share_capital=circulating_cap,
                            is_new_stock=is_new_stock
                        ) / 100  # 转换为比例

                    # 计算封单金额（针对涨停股）
                    seal_amount = 0
                    # 只有当卖一价为 0（真正涨停）时才计算封单金额
                    if ask1_price == 0 and change_pct >= 9.5:  # 涨停板
                        # 涨停时，封单金额 = 买一量（手数）× 100（股/手）× 价格
                        seal_amount = bid1_volume * 100 * current_price / 10000  # 转换为万

                    # 计算买卖盘口价差
                    price_gap = 0
                    if bid1_price > 0 and ask1_price > 0:
                        price_gap = (ask1_price - bid1_price) / bid1_price * 100

                    # 🆕 V8.1: 流动性陷阱检测（缩量拉升识别）
                    liquidity_trap = False
                    liquidity_trap_reason = ""
                    auction_amount = auction_volume * current_price  # 竞价金额（元）
                    auction_amount_wan = auction_amount / 10000  # 转换为万

                    # 流动性陷阱条件：
                    # 1. 竞价金额 < 500万（流动性不足）
                    # 2. 竞价抢筹度 < 2%（主力未大举抢筹）
                    # 3. 涨幅 > 5%（看似强势，但缺乏流动性支持）
                    is_trap = auction_amount_wan < 500 and auction_ratio < 0.02 and change_pct > 5
                    
                    # 🆕 V8.2: 豁免逻辑 - 绝对一字板龙头（The Absolute One-Word Board）
                    # 豁免条件：如果是"一字涨停"且"封单巨大"（封单额>1亿）
                    # 这种情况通常是重组复牌等超级利好，买都买不到，不是流动性陷阱
                    is_super_one_word = (ask1_price == 0 and change_pct >= 19.5 and seal_amount > 10000)
                    
                    # 🆕 V8.4: 深化次新股豁免逻辑（防止豁免权滥用）
                    # 次新股特性：筹码稳定，惜售缩量，炒作逻辑是情绪博弈，不是业绩驱动
                    # 但豁免必须有门槛：次新股可以竞价弱，但开盘必须强，或者位置必须好
                    is_sub_new = (symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688')) and auction_amount_wan < 500
                    
                    # 🆕 V8.4: 获取开盘涨幅（需要实时数据）
                    open_price = realtime_data_item.get('open', 0)
                    last_close = realtime_data_item.get('close', 0)
                    open_gap_pct = 0
                    if open_price > 0 and last_close > 0:
                        open_gap_pct = (open_price - last_close) / last_close * 100
                    
                    if is_trap and is_super_one_word:
                        liquidity_trap = False
                        liquidity_trap_reason = f"✅ 豁免：缩量一字板真龙（封单金额{seal_amount:.0f}万>1亿）"
                    elif is_trap and is_sub_new:
                        # 🆕 V8.4: 深化次新股豁免逻辑 - 只有 "红盘开盘" 或 "微跌但承接极强" 才豁免
                        if open_gap_pct > -2.0:  # 红盘开盘或微跌（< -2%）
                            liquidity_trap = False
                            liquidity_trap_reason = f"✅ 豁免：次新股惜售（竞价金额{auction_amount_wan:.0f}万<500万，开盘涨幅{open_gap_pct:.2f}%，情绪稳定）"
                        else:
                            # 如果竞价没钱，还低开 > -2%，那就是真没人要，不是惜售
                            liquidity_trap = True
                            liquidity_trap_reason = f"⚠️ 流动性陷阱：次新股无抵抗阴跌（竞价金额{auction_amount_wan:.0f}万<500万，开盘涨幅{open_gap_pct:.2f}%，缺乏承接）"
                    elif is_trap:
                        liquidity_trap = True
                        liquidity_trap_reason = f"⚠️ 流动性陷阱：竞价金额{auction_amount_wan:.0f}万<500万，竞价抢筹度{auction_ratio*100:.2f}%<2%，缩量拉升"

                    # 🆕 V8.1: 真龙识别（区分龙头vs跟风）
                    dragon_type = "未知"
                    dragon_reason = ""
                    current_turnover = realtime_data_item.get('turnover', 0) / 10000  # 当前成交额（万元）

                    # 真龙标准：
                    # 1. 成交额 > 5000万（大资金能进出）
                    # 2. 竞价抢筹度 > 2%（主力大举抢筹）
                    # 3. 涨幅 > 10%（强势）
                    if current_turnover > 5000 and auction_ratio > 0.02 and change_pct > 10:
                        dragon_type = "🐉 真龙"
                        dragon_reason = f"✅ 成交额{current_turnover:.0f}万>5000万，竞价抢筹度{auction_ratio*100:.2f}%>2%，真龙特征"
                    elif current_turnover > 2000 and auction_ratio > 0.01 and change_pct > 8:
                        dragon_type = "🐲 强跟风"
                        dragon_reason = f"⚠️ 成交额{current_turnover:.0f}万>2000万，竞价抢筹度{auction_ratio*100:.2f}%>1%，强跟风"
                    elif current_turnover < 500 or auction_ratio < 0.01:
                        dragon_type = "🐛 杂毛"
                        dragon_reason = f"❌ 成交额{current_turnover:.0f}万<500万或竞价抢筹度{auction_ratio*100:.2f}%<1%，杂毛"
                    else:
                        dragon_type = "🦆 弱跟风"
                        dragon_reason = f"⚠️ 成交额{current_turnover:.0f}万，竞价抢筹度{auction_ratio*100:.2f}%，弱跟风"

                    # 检测竞价弱转强
                    weak_to_strong = QuantAlgo.detect_auction_weak_to_strong(df, symbol)

                    # 获取换手率
                    turnover_rate = 0
                    if 'turnover_rate' in df.columns:
                        turnover_rate = df['turnover_rate'].iloc[-1]

                    # 🆕 V9.2 新增：数据完整性熔断检查
                    # 如果竞价量为0，说明数据缺失，不能给高分
                    if auction_volume == 0:
                        # 竞价数据缺失，大幅降低评分
                        score = 30  # 只给基础分
                        signals.append("⚠️ 竞价数据缺失（无法判断竞价强弱）")
                        signals.append("⚠️ 评分仅供参考（建议等待明日集合竞价数据）")
                    else:
                        # 正常的评分逻辑
                        # 计算综合评分
                        score = 0
                        
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
                    # 🆕 V8.4: 次新股动态换手率评分标准
                    is_sub_new_stock = symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688')
                    
                    if is_sub_new_stock:
                        # 次新股标准：必须充分换手
                        if turnover_rate < 15:
                            score -= 10  # 换手不够，大概率是庄股或僵尸
                            signals.append(f"⚠️ 次新股换手过低（{turnover_rate:.2f}%<15%），流动性枯竭")
                        elif turnover_rate > 70:
                            score -= 5  # 换手太高，可能是出货
                            signals.append(f"⚠️ 次新股换手过高（{turnover_rate:.2f}%>70%），可能出货")
                        elif turnover_rate > 30:
                            score += 30  # 30%-50% 是次新妖股的黄金区间
                            signals.append(f"✅ 次新股换手活跃（{turnover_rate:.2f}%），妖股特征")
                        else:
                            score += 20  # 15%-30% 是次新股正常区间
                            signals.append(f"✅ 次新股换手适中（{turnover_rate:.2f}%）")
                    else:
                        # 普通股标准 (原有逻辑)
                        if 2 <= turnover_rate <= 10:
                            score += 25
                            signals.append(f"换手率适中（{turnover_rate:.2f}%）")
                        elif turnover_rate > 10:
                            score += 15
                            signals.append(f"换手率较高（{turnover_rate:.2f}%）")

                    # 🆕 V8.1: 流动性陷阱惩罚
                    if liquidity_trap:
                        score -= 30  # 大幅降低评分
                        signals.append(liquidity_trap_reason)

                    # 🆕 V8.1: 真龙加分/跟风减分
                    if dragon_type == "🐉 真龙":
                        score += 30  # 真龙大幅加分
                        signals.append(dragon_reason)
                    elif dragon_type == "🐲 强跟风":
                        score += 10  # 强跟风小幅加分
                        signals.append(dragon_reason)
                    elif dragon_type == "🐛 杂毛":
                        score -= 20  # 杂毛大幅减分
                        signals.append(dragon_reason)
                    elif dragon_type == "🦆 弱跟风":
                        score -= 5  # 弱跟风小幅减分
                        signals.append(dragon_reason)

                    # 竞价量评分（新增）
                    if auction_volume > 1000:  # 竞价量超过1000手
                        score += 10
                        signals.append(f"竞价量充足（{auction_volume}手）")
                    elif auction_volume > 100:
                        score += 5
                        signals.append(f"竞价量一般（{auction_volume}手）")

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

                    return {
                        '代码': symbol,
                        '名称': name,
                        '最新价': current_price,
                        '涨跌幅': change_pct,
                        '量比': round(volume_ratio, 2),
                        '换手率': round(turnover_rate, 2),
                        '竞价量': auction_volume,
                        '竞价金额': round(auction_amount_wan, 2),  # 🆕 V8.1: 添加竞价金额
                        '成交额': round(current_turnover, 2),  # 🆕 V8.1: 添加成交额
                        '买一价': round(bid1_price, 2),
                        '卖一价': round(ask1_price, 2),
                        '买一量': int(bid1_volume),
                        '卖一量': int(ask1_volume),
                        '竞价抢筹度': round(auction_ratio, 4),
                        '开盘涨幅': round(open_gap_pct, 2),
                        '封单金额': round(seal_amount, 2),
                        '流动性陷阱': liquidity_trap,  # 🆕 V8.1: 添加流动性陷阱标记
                        '流动性陷阱原因': liquidity_trap_reason,  # 🆕 V8.2: 添加流动性陷阱原因
                        '一字板龙头': is_super_one_word,  # 🆕 V8.2: 添加一字板龙头标记
                        '真龙类型': dragon_type,  # 🆕 V8.1: 添加真龙类型标记
                        '买卖价差': round(price_gap, 2),
                        '评分': score,
                        '评级': rating,
                        '信号': signals,
                        '操作建议': suggestion,
                        '弱转强': weak_to_strong.get('是否弱转强', False),
                        # 🆕 V9.0: 添加日内弱转强相关字段（用于StrategyOrchestrator）
                        'auction_data': {
                            'auction_amount': auction_amount_wan,
                            'auction_ratio': auction_ratio,
                            'auction_volume': auction_volume,
                            'open_price': current_price,
                            'open_gap_pct': change_pct
                        },
                        'intraday_data': None  # 日内数据需要在开盘后获取
                    }
                except Exception as e:
                    print(f"分析股票 {symbol} 失败: {e}")
                    return None

            # 🚀 使用线程池并行分析
            auction_stocks = []
            max_workers = min(8, len(filtered_stocks))  # 最多 8 个线程

            logger.info(f"开始并行分析 {len(filtered_stocks)} 只集合竞价股票（使用 {max_workers} 个线程）...")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有分析任务
                future_to_stock = {
                    executor.submit(analyze_auction_stock, stock): stock
                    for stock in filtered_stocks
                }

                # 收集结果
                for future in as_completed(future_to_stock):
                    result = future.result()
                    if result is not None:
                        auction_stocks.append(result)

            logger.info(f"✅ 并行分析完成，找到 {len(auction_stocks)} 只符合条件的股票")

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

    @staticmethod
    def scan_trend_stocks(limit=100, min_score=60):
        """
        趋势中军扫描模式 (专门抓 诺思格/宁德时代 这类机构票)
        特征：不一定天天涨停，但沿着 5日线/10日线不停涨
        资金：主要靠机构推土机式买入，而不是游资一日游
        """
        try:
            from logic.data_manager import DataManager

            # 获取股票列表
            import akshare as ak
            stock_list_df = ak.stock_info_a_code_name()

            if stock_list_df.empty:
                return {
                    '数据状态': '无法获取股票列表',
                    '说明': '可能是数据源限制'
                }

            stock_list = stock_list_df['code'].tolist()

            # 使用 Easyquotation 极速获取全市场实时数据
            db = DataManager()
            logger.info(f"🚀 开始扫描趋势中军 (Pool: {len(stock_list)})...")
            realtime_data = db.get_fast_price(stock_list)
            logger.info(f"✅ 实时数据获取完成，获取到 {len(realtime_data)} 只股票数据")

            if not realtime_data:
                db.close()
                return {
                    '数据状态': '无法获取实时数据',
                    '说明': 'Easyquotation 未初始化或网络问题'
                }

            # 转换为列表格式
            all_stocks = []
            for full_code, data in realtime_data.items():
                try:
                    # 提取股票代码
                    if len(full_code) == 6:
                        code = full_code
                    elif len(full_code) > 6:
                        code = full_code[2:]
                    else:
                        continue

                    # 只保留 A 股股票
                    if not (len(code) == 6 and code.isdigit() and code[0] in ['0', '3', '6']):
                        continue

                    name = data.get('name', '')

                    # 排除 ST 股
                    if 'ST' in name or '*ST' in name:
                        continue

                    current_price = float(data.get('now', 0))
                    last_close = float(data.get('close', 0))

                    if current_price == 0 or last_close == 0:
                        continue

                    pct_change = (current_price - last_close) / last_close * 100

                    # 趋势初筛规则
                    # 1. 拒绝暴涨暴跌 (趋势股通常涨 2% - 7%)
                    if pct_change < 1.5 or pct_change > 10:
                        continue

                    # 2. 获取成交量
                    volume = data.get('volume', 0) / 100  # 转换为手

                    all_stocks.append({
                        '代码': code,
                        '名称': name,
                        '最新价': current_price,
                        '涨跌幅': pct_change,
                        '成交量': volume,
                        '买一价': data.get('bid1', 0),
                        '卖一价': data.get('ask1', 0),
                        '买一量': data.get('bid1_volume', 0),
                        '卖一量': data.get('ask1_volume', 0)
                    })
                except Exception as e:
                    continue

            if not all_stocks:
                return {
                    '数据状态': '无符合条件的股票',
                    '说明': '当前市场无符合趋势特征的股票'
                }

            # 限制候选股票数量
            max_candidates = min(200, len(all_stocks))
            all_stocks.sort(key=lambda x: x['涨跌幅'], reverse=True)
            all_stocks = all_stocks[:max_candidates]
            logger.info(f"初步筛选后保留 {len(all_stocks)} 只候选股票")

            # 批量加载历史数据
            logger.info(f"开始批量加载 {len(all_stocks)} 只候选股票的历史数据...")
            history_data_cache = {}
            for stock in all_stocks:
                symbol = stock['代码']
                try:
                    df = db.get_history_data(symbol)
                    if not df.empty and len(df) > 5:
                        history_data_cache[symbol] = df
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 历史数据失败: {e}")
            logger.info(f"✅ 历史数据加载完成，成功加载 {len(history_data_cache)} 只股票")

            # 计算量比
            for stock in all_stocks:
                try:
                    df = history_data_cache.get(stock['代码'])
                    if df is not None and not df.empty and len(df) > 5:
                        # 🆕 V8.1: 修复单位换算BUG
                        # 历史数据的volume是股数（来自akshare），需要转换为手数（除以100）
                        # 实时数据的成交量已经是手数（在前面已除以100）
                        avg_volume = df['volume'].tail(5).mean() / 100  # 转换为手数
                        
                        # 🆕 V8.3: 添加异常值检测
                        # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
                        if avg_volume < 1000:
                            stock['量比'] = 1  # 不计算，避免异常值
                        elif avg_volume > 0:
                            stock['量比'] = stock['成交量'] / avg_volume
                        else:
                            stock['量比'] = 1
                    else:
                        stock['量比'] = 1
                except:
                    stock['量比'] = 1

            # 计算综合得分
            for stock in all_stocks:
                trend_score = 60  # 基础分

                # 1. 涨幅评分 (2% - 7% 是最佳趋势涨幅)
                pct = stock['涨跌幅']
                if 2.0 <= pct <= 6.0:
                    trend_score += 15  # 最佳趋势涨幅
                elif 6.0 < pct <= 8.0:
                    trend_score += 10  # 较强趋势
                elif 1.5 <= pct < 2.0:
                    trend_score += 5  # 弱趋势启动

                # 2. 量比评分 (机构喜欢温和放量 1.0 - 3.0)
                volume_ratio = stock['量比']
                
                # 🆕 V9.2 新增：检查量比是否为默认值
                bid1_volume = stock.get('买一量', 0)
                ask1_volume = stock.get('卖一量', 0)
                is_market_closed = (bid1_volume == 0 and ask1_volume == 0)
                
                # 如果量比是默认值1且收盘了，说明数据无效
                if volume_ratio == 1.0 and is_market_closed:
                    trend_score -= 5  # 数据无效，降低评分
                elif 1.0 <= volume_ratio <= 3.0:
                    trend_score += 15  # 温和放量
                elif 3.0 < volume_ratio <= 5.0:
                    trend_score += 10  # 较强放量
                elif volume_ratio > 5.0:
                    trend_score -= 5  # 爆量，可能是游资

                # 3. 价格评分 (机构喜欢高价股)
                price = stock['最新价']
                if price > 50:
                    trend_score += 10  # 机构偏好高价股
                elif price > 20:
                    trend_score += 5

                # 4. 板块加分
                code = stock['代码']
                if code.startswith('30'):
                    trend_score += 5  # 创业板弹性加分

                stock['趋势评分'] = trend_score

            # 按评分排序，取前 limit 只
            filtered_stocks = sorted(all_stocks, key=lambda x: x['趋势评分'], reverse=True)[:limit]

            # 使用多线程并行分析
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # 构建股票代码到实时数据的映射
            realtime_map = {}
            for full_code, data in realtime_data.items():
                code = full_code if len(full_code) == 6 else full_code[2:]
                realtime_map[code] = data

            def analyze_trend_stock(stock):
                """分析单只趋势股票"""
                try:
                    symbol = stock['代码']
                    name = stock['名称']
                    current_price = stock['最新价']
                    change_pct = stock['涨跌幅']
                    volume_ratio = stock['量比']

                    # 🆕 V9.2 新增：检查是否收盘（买一卖一都为0）
                    bid1_volume = stock.get('买一量', 0)
                    ask1_volume = stock.get('卖一量', 0)
                    is_market_closed = (bid1_volume == 0 and ask1_volume == 0)

                    # 获取历史数据
                    df = history_data_cache.get(symbol)
                    if df is None or df.empty:
                        return None

                    # 计算均线多头排列
                    ma5 = df['close'].tail(5).mean()
                    ma10 = df['close'].tail(10).mean()
                    ma20 = df['close'].tail(20).mean()

                    is_bullish = current_price > ma5 > ma10 > ma20

                    # 获取换手率
                    turnover_rate = 0
                    if 'turnover_rate' in df.columns:
                        turnover_rate = df['turnover_rate'].iloc[-1]

                    # 计算评分
                    score = stock['趋势评分']
                    signals = []

                    # 均线多头排列加分
                    if is_bullish:
                        score += 20
                        signals.append("均线多头排列")

                    # 换手率评分
                    # 🆕 V8.4: 次新股动态换手率评分标准
                    is_sub_new_stock = symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688')
                    
                    if is_sub_new_stock:
                        # 次新股标准：必须充分换手
                        if turnover_rate < 15:
                            score -= 5  # 换手不够
                            signals.append(f"⚠️ 次新股换手过低（{turnover_rate:.2f}%）")
                        elif turnover_rate > 70:
                            score -= 3  # 换手太高
                            signals.append(f"⚠️ 次新股换手过高（{turnover_rate:.2f}%）")
                        elif turnover_rate > 30:
                            score += 20  # 30%-50% 是次新妖股的黄金区间
                            signals.append(f"✅ 次新股换手活跃（{turnover_rate:.2f}%）")
                        else:
                            score += 15  # 15%-30% 是次新股正常区间
                            signals.append(f"✅ 次新股换手适中（{turnover_rate:.2f}%）")
                    else:
                        # 普通股标准 (原有逻辑)
                        if 2 <= turnover_rate <= 10:
                            score += 15
                            signals.append(f"换手率适中（{turnover_rate:.2f}%）")
                        elif turnover_rate > 10:
                            score += 10
                            signals.append(f"换手率较高（{turnover_rate:.2f}%）")

                    # 🆕 V9.2 新增：收盘数据警告
                    if is_market_closed:
                        signals.append("⚠️ 收盘数据（盘口已清空）")
                        # 收盘后，盘口数据无效，评分仅供参考
                    
                    # 评级
                    if score >= 90:
                        level = "🔥 强趋势中军"
                    elif score >= 80:
                        level = "📈 趋势中军"
                    elif score >= 70:
                        level = "⚠️ 弱趋势"
                    else:
                        level = "❌ 不符合"

                    if score >= min_score:
                        return {
                            '代码': symbol,
                            '名称': name,
                            '最新价': current_price,
                            '涨跌幅': change_pct,
                            '评分': score,
                            '评级': level,
                            '信号': ', '.join(signals),
                            '量比': round(volume_ratio, 2),
                            '换手率': round(turnover_rate, 2),
                            'MA5': round(ma5, 2),
                            'MA10': round(ma10, 2),
                            'MA20': round(ma20, 2),
                            '买一价': round(stock['买一价'], 2),
                            '卖一价': round(stock['卖一价'], 2),
                            '买一量': int(stock['买一量'] / 100),
                            '卖一量': int(stock['卖一量'] / 100)
                        }
                    return None
                except Exception as e:
                    logger.error(f"分析趋势股票 {stock['代码']} 失败: {e}")
                    return None

            # 并行分析
            trend_stocks = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(analyze_trend_stock, stock): stock for stock in filtered_stocks}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        trend_stocks.append(result)

            logger.info(f"✅ 并行分析完成，找到 {len(trend_stocks)} 只符合条件的股票")

            db.close()

            # 按评分排序
            trend_stocks.sort(key=lambda x: x['评分'], reverse=True)

            return {
                '数据状态': '正常',
                '扫描数量': len(filtered_stocks),
                '符合条件数量': len(trend_stocks),
                '趋势股票列表': trend_stocks
            }
        except Exception as e:
            logger.error(f"趋势中军扫描失败: {e}")
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def scan_halfway_stocks(limit=100, min_score=60):
        """
        半路战法扫描模式 (专门抓 20cm 股票在 10%-19% 区间的半路板)
        特征：20cm 股票在加速逼空段，但还未封板
        机会：半路扫货，博弈 20% 涨停
        """
        try:
            from logic.data_manager import DataManager

            # 获取股票列表
            import akshare as ak
            stock_list_df = ak.stock_info_a_code_name()

            if stock_list_df.empty:
                return {
                    '数据状态': '无法获取股票列表',
                    '说明': '可能是数据源限制'
                }

            stock_list = stock_list_df['code'].tolist()

            # 使用 Easyquotation 极速获取全市场实时数据
            db = DataManager()
            logger.info(f"🚀 开始扫描半路板 (Pool: {len(stock_list)})...")
            realtime_data = db.get_fast_price(stock_list)
            logger.info(f"✅ 实时数据获取完成，获取到 {len(realtime_data)} 只股票数据")

            if not realtime_data:
                db.close()
                return {
                    '数据状态': '无法获取实时数据',
                    '说明': 'Easyquotation 未初始化或网络问题'
                }

            # 转换为列表格式
            all_stocks = []
            for full_code, data in realtime_data.items():
                try:
                    # 提取股票代码
                    if len(full_code) == 6:
                        code = full_code
                    elif len(full_code) > 6:
                        code = full_code[2:]
                    else:
                        continue

                    # 🛑 V9.2 修复：半路战法必须只抓 20cm 标的
                    # 创业板：300xxx、301xxx
                    # 科创板：688xxx
                    is_chinext = code.startswith('300') or code.startswith('301')
                    is_star = code.startswith('688')
                    
                    if not (is_chinext or is_star):
                        continue  # 剔除主板股票（600xxx、000xxx等）

                    name = data.get('name', '')

                    # 排除 ST 股
                    if 'ST' in name or '*ST' in name:
                        continue

                    current_price = float(data.get('now', 0))
                    last_close = float(data.get('close', 0))

                    if current_price == 0 or last_close == 0:
                        continue

                    pct_change = (current_price - last_close) / last_close * 100

                    # 半路板初筛规则：10% - 18.5%（留1.5%空间给半路扫货）
                    # 🆕 V9.2 修复：严格卡死半路区间
                    if not (10.0 <= pct_change < 18.5):
                        continue
                    
                    # 🛑 V9.2 新增：严禁已经封死涨停的
                    # 检查卖一价是否为0（已封板）
                    # 注意：只有当涨幅接近涨停（>=19.0%）且卖一价为0时，才认为是已封板
                    ask1_price = data.get('ask1', 0)
                    if ask1_price == 0 and pct_change >= 19.0:
                        continue  # 已经封板，不是半路机会

                    # 获取成交量
                    volume = data.get('volume', 0) / 100  # 转换为手

                    all_stocks.append({
                        '代码': code,
                        '名称': name,
                        '最新价': current_price,
                        '涨跌幅': pct_change,
                        '成交量': volume,
                        '买一价': data.get('bid1', 0),
                        '卖一价': data.get('ask1', 0),
                        '买一量': data.get('bid1_volume', 0),
                        '卖一量': data.get('ask1_volume', 0)
                    })
                except Exception as e:
                    continue

            if not all_stocks:
                return {
                    '数据状态': '无符合条件的股票',
                    '说明': '当前市场无半路板机会'
                }

            # 限制候选股票数量
            max_candidates = min(100, len(all_stocks))
            all_stocks.sort(key=lambda x: x['涨跌幅'], reverse=True)
            all_stocks = all_stocks[:max_candidates]
            logger.info(f"初步筛选后保留 {len(all_stocks)} 只候选股票")

            # 批量加载历史数据
            logger.info(f"开始批量加载 {len(all_stocks)} 只候选股票的历史数据...")
            history_data_cache = {}
            for stock in all_stocks:
                symbol = stock['代码']
                try:
                    df = db.get_history_data(symbol)
                    if not df.empty and len(df) > 5:
                        history_data_cache[symbol] = df
                except Exception as e:
                    logger.warning(f"加载股票 {symbol} 历史数据失败: {e}")
            logger.info(f"✅ 历史数据加载完成，成功加载 {len(history_data_cache)} 只股票")

            # 🆕 V9.0: 游资掠食者系统检查
            logger.info("🦖 启动V9.0游资掠食者系统检查...")
            predator = PredatorSystem()
            predator_results = {}
            
            for stock in all_stocks:
                symbol = stock['代码']
                name = stock['名称']
                
                # 构建股票基本信息
                stock_info = {
                    'symbol': symbol,
                    'name': name,
                    'remark': ''
                }
                
                # 构建实时行情数据
                realtime_data = {
                    'change_percent': stock['涨跌幅'],
                    'volume_ratio': 1,  # 暂时设为1，后面会计算
                    'turnover_rate': 0  # 暂时设为0，后面会计算
                }
                
                # 运行V9.0检查
                result = predator.analyze_stock(stock_info, realtime_data)
                predator_results[symbol] = result
                
                # 🆕 V9.2 修复：半路战法只排除触发生死红线的股票
                # 忽略"身份与涨幅错配"检查，因为半路战法就是要抓涨幅在10%-19.5%之间的股票
                if result['signal'] == 'SELL' and '生死红线' in result['reason']:
                    logger.warning(f"🦖 V9.0排除（生死红线）：{symbol} {name} - {result['reason']}")
                elif result['signal'] == 'SELL' and '身份与涨幅错配' in result['reason']:
                    # 半路战法忽略身份与涨幅错配检查
                    logger.info(f"🦖 V9.0跳过（身份与涨幅错配）：{symbol} {name} - {result['reason']}")
            
            # 过滤掉被V9.0排除的股票（只排除触发生死红线的）
            filtered_stocks = [stock for stock in all_stocks 
                             if not (predator_results[stock['代码']]['signal'] == 'SELL' and 
                                   '生死红线' in predator_results[stock['代码']]['reason'])]
            logger.info(f"🦖 V9.0检查完成，从{len(all_stocks)}只中排除了{len(all_stocks)-len(filtered_stocks)}只，保留{len(filtered_stocks)}只")
            
            if not filtered_stocks:
                return {
                    '数据状态': 'V9.0游资掠食者系统全部排除',
                    '说明': '所有候选股票触发生死红线或身份与涨幅错配'
                }
            
            all_stocks = filtered_stocks

            # 计算量比
            for stock in all_stocks:
                try:
                    df = history_data_cache.get(stock['代码'])
                    if df is not None and not df.empty and len(df) > 5:
                        # 🆕 V8.1: 修复单位换算BUG
                        # 历史数据的volume是股数（来自akshare），需要转换为手数（除以100）
                        # 实时数据的成交量已经是手数（在前面已除以100）
                        avg_volume = df['volume'].tail(5).mean() / 100  # 转换为手数
                        
                        # 🆕 V8.3: 添加异常值检测
                        # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
                        if avg_volume < 1000:
                            stock['量比'] = 1  # 不计算，避免异常值
                        elif avg_volume > 0:
                            stock['量比'] = stock['成交量'] / avg_volume
                        else:
                            stock['量比'] = 1
                    else:
                        stock['量比'] = 1
                except:
                    stock['量比'] = 1

            # 计算综合得分
            for stock in all_stocks:
                halfway_score = 60  # 基础分

                # 1. 涨幅评分 (15% - 19% 是最佳半路区间)
                pct = stock['涨跌幅']
                if 15.0 <= pct < 19.5:
                    halfway_score += 20  # 最佳半路区间
                elif 12.0 <= pct < 15.0:
                    halfway_score += 15  # 较好半路区间
                elif 10.0 <= pct < 12.0:
                    halfway_score += 10  # 启动区间

                # 2. 量比评分 (半路板需要攻击性放量)
                volume_ratio = stock['量比']
                if volume_ratio > 5.0:
                    halfway_score += 20  # 攻击性放量
                elif volume_ratio > 3.0:
                    halfway_score += 15  # 较强放量
                elif volume_ratio > 2.0:
                    halfway_score += 10  # 温和放量

                # 3. 买卖盘口评分 (买一量大，卖一量小)
                bid1_volume = stock['买一量']
                ask1_volume = stock['卖一量']
                if ask1_volume == 0:
                    halfway_score += 15  # 无卖压
                elif bid1_volume > ask1_volume * 2:
                    halfway_score += 10  # 买盘强

                stock['半路评分'] = halfway_score

            # 按评分排序，取前 limit 只
            filtered_stocks = sorted(all_stocks, key=lambda x: x['半路评分'], reverse=True)[:limit]

            # 使用多线程并行分析
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # 构建股票代码到实时数据的映射
            realtime_map = {}
            for full_code, data in realtime_data.items():
                code = full_code if len(full_code) == 6 else full_code[2:]
                realtime_map[code] = data

            def analyze_halfway_stock(stock):
                """分析单只半路板股票"""
                try:
                    symbol = stock['代码']
                    name = stock['名称']
                    current_price = stock['最新价']
                    change_pct = stock['涨跌幅']
                    volume_ratio = stock['量比']

                    # 获取历史数据
                    df = history_data_cache.get(symbol)
                    if df is None or df.empty:
                        return None

                    # 获取换手率
                    turnover_rate = 0
                    if 'turnover_rate' in df.columns:
                        turnover_rate = df['turnover_rate'].iloc[-1]

                    # 计算评分
                    score = stock['半路评分']
                    signals = []

                    # 量比评分
                    if volume_ratio > 5.0:
                        signals.append(f"攻击性放量（量比{volume_ratio:.2f}）")
                    elif volume_ratio > 3.0:
                        signals.append(f"较强放量（量比{volume_ratio:.2f}）")

                    # 换手率评分
                    # 🆕 V8.4: 次新股动态换手率评分标准
                    is_sub_new_stock = symbol.startswith('301') or symbol.startswith('303') or symbol.startswith('688')
                    
                    if is_sub_new_stock:
                        # 次新股标准：必须充分换手
                        if turnover_rate < 15:
                            score -= 5  # 换手不够
                            signals.append(f"⚠️ 次新股换手过低（{turnover_rate:.2f}%）")
                        elif turnover_rate > 70:
                            score -= 3  # 换手太高
                            signals.append(f"⚠️ 次新股换手过高（{turnover_rate:.2f}%）")
                        elif turnover_rate > 30:
                            score += 20  # 30%-50% 是次新妖股的黄金区间
                            signals.append(f"✅ 次新股换手活跃（{turnover_rate:.2f}%）")
                        else:
                            score += 15  # 15%-30% 是次新股正常区间
                            signals.append(f"✅ 次新股换手适中（{turnover_rate:.2f}%）")
                    else:
                        # 普通股标准 (原有逻辑)
                        if 5 <= turnover_rate <= 15:
                            score += 15
                            signals.append(f"换手率适中（{turnover_rate:.2f}%）")
                        elif turnover_rate > 15:
                            score += 10
                            signals.append(f"换手率较高（{turnover_rate:.2f}%）")

                    # 评级
                    if score >= 90:
                        level = "🔥 强半路板"
                    elif score >= 80:
                        level = "📈 半路板"
                    elif score >= 70:
                        level = "⚠️ 弱半路板"
                    else:
                        level = "❌ 不符合"

                    if score >= min_score:
                        return {
                            '代码': symbol,
                            '名称': name,
                            '最新价': current_price,
                            '涨跌幅': change_pct,
                            '评分': score,
                            '评级': level,
                            '信号': ', '.join(signals),
                            '量比': round(volume_ratio, 2),
                            '换手率': round(turnover_rate, 2),
                            '买一价': round(stock['买一价'], 2),
                            '卖一价': round(stock['卖一价'], 2),
                            '买一量': int(stock['买一量'] / 100),
                            '卖一量': int(stock['卖一量'] / 100),
                            '操作建议': "🚀 半路扫货。当前处于加速逼空段，是上车博弈 20% 的机会，不要等回调！"
                        }
                    return None
                except Exception as e:
                    logger.error(f"分析半路板股票 {stock['代码']} 失败: {e}")
                    return None

            # 并行分析
            halfway_stocks = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(analyze_halfway_stock, stock): stock for stock in filtered_stocks}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        halfway_stocks.append(result)

            logger.info(f"✅ 并行分析完成，找到 {len(halfway_stocks)} 只符合条件的股票")

            db.close()

            # 按评分排序
            halfway_stocks.sort(key=lambda x: x['评分'], reverse=True)

            return {
                '数据状态': '正常',
                '扫描数量': len(filtered_stocks),
                '符合条件数量': len(halfway_stocks),
                '半路板列表': halfway_stocks
            }
        except Exception as e:
            logger.error(f"半路战法扫描失败: {e}")
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }
    
    # 🆕 V9.11: 竞价异动捕捉逻辑
    @staticmethod
    def analyze_auction_strength(stock_data: Dict[str, Any], last_close: float, is_review_mode=False, code=None, data_manager=None) -> Dict[str, Any]:
        """
        🔥 竞价抢筹力度分析（无需K线）
        
        Args:
            stock_data: 股票快照数据（来自Easyquotation）
            last_close: 昨日收盘价
            is_review_mode: 复盘模式开关（V9.12.1新增）
            code: 股票代码（V9.13新增，用于获取连板信息）
            data_manager: 数据管理器实例（V9.13新增，用于获取连板信息）
        
        Returns:
            竞价强度分析结果
        """
        if last_close == 0:
            return {
                "price": 0,
                "pct": 0,
                "score": 0,
                "status": "数据异常"
            }
        
        # 获取竞价当前的"虚拟开盘价"
        # 竞价阶段 bid1 和 ask1 通常是重合的，即为撮合价
        current_price = stock_data.get('bid1', 0)
        if current_price == 0:
            current_price = stock_data.get('now', 0)
        
        if current_price == 0:
            return {
                "price": 0,
                "pct": 0,
                "score": 0,
                "status": "无数据"
            }
        
        # 1. 竞价涨幅
        auction_pct = (current_price - last_close) / last_close * 100
        
        # 2. 匹配量（如有）
        # Easyquotation 部分接口可能不返回 matching_vol
        # 这里用 bid1_volume 近似代替，虽不精准但能看意图
        bid_vol = stock_data.get('bid1_volume', 0)
        ask_vol = stock_data.get('ask1_volume', 0)
        
        # 🆕 V9.11.2 修复：获取换手率和成交额
        turnover_rate = stock_data.get('turnover', 0)  # 换手率
        amount = stock_data.get('amount', 0)  # 成交额
        
        # 3. 评分逻辑
        # 基础分：50分
        score = 50
        
        # 🆕 V9.11.2 修复：识别"缩量一字板"（使用换手率替代绝对手数）
        # 一字板（涨幅>9.5%）且换手率极低（<0.1%）是最强的
        is_limit_up = auction_pct > 9.5
        is_shrinking = turnover_rate < 0.1  # 换手率<0.1%视为缩量
        
        if is_limit_up and is_shrinking:
            # 缩量一字板：换手率极低，资金锁死
            score += 40  # 基础一字板加分
            score += 10  # 缩量额外加分
            status = "缩量一字板"
        elif is_limit_up:
            # 放量一字板：换手率正常或放量
            score += 40  # 一字板加分
            if turnover_rate > 0.5:
                score += 10  # 放量一字板额外加分
            status = "放量一字板"
        elif 5.0 < auction_pct <= 9.0:
            score += 30  # 高开 5% ~ 9% = 强势
            status = "强势"
        elif 2.0 <= auction_pct <= 5.0:
            score += 20  # 高开 2% ~ 5% = 抢筹
            status = "抢筹"
        elif auction_pct > 0:
            status = "高开"
        elif auction_pct > -2.0:
            status = "平开"
        elif auction_pct < 0:
            score -= 20  # 低开 = 弱势
            status = "弱势"
        
        # 量能加分（非一字板）
        if not is_limit_up:
            if bid_vol > 0:
                # 有买盘，说明有资金关注
                score += 10
            elif bid_vol == 0 and auction_pct > 0:
                # 高开但无买盘，可能是竞价刚开始
                score += 5
        
        # 卖盘扣分
        if ask_vol > bid_vol * 2:
            # 卖盘远大于买盘，抛压重
            score -= 15
            if status == "平开":
                status = "抛压重"
        
        # 🆕 V9.12 修复：应用时间衰减因子
        # 游资心法：涨停的时间越早，溢价越高；涨停的时间越晚，气质越弱
        time_weight = get_time_weight(is_review_mode=is_review_mode)
        
        # 计算最终得分（应用时间权重）
        final_score = int(score * time_weight)
        
        # 🆕 V9.12 修复：添加时间权重信息到返回结果
        time_weight_desc = ""
        if is_review_mode:
            time_weight_desc = "📝 复盘模式 (不衰减)"
        elif time_weight == 1.0:
            time_weight_desc = "👑 黄金时段"
        elif time_weight == 0.9:
            time_weight_desc = "⚔️ 激战时段"
        elif time_weight == 0.7:
            time_weight_desc = "💤 垃圾时间"
        elif time_weight == 0.4:
            time_weight_desc = "🦊 偷袭时段"
        elif time_weight == 0.0:
            time_weight_desc = "☠️ 最后一击"
        
        # 🆕 V9.13 修复：弱转强识别和连板溢价
        lianban_count = 0
        yesterday_status = "未知"
        yesterday_pct = 0
        is_weak_to_strong = False
        weak_to_strong_bonus = 0
        lianban_bonus = 0
        high_risk_penalty = 0
        
        if code and data_manager:
            try:
                stock_status = data_manager.get_stock_status(code)
                lianban_count = stock_status.get('lianban_count', 0)
                yesterday_status = stock_status.get('yesterday_status', '未知')
                yesterday_pct = stock_status.get('yesterday_pct', 0)
                
                # 🚀 弱转强加分项
                # 如果昨天是"烂板"或"非涨停"，但今天"高开抢筹"
                if yesterday_status in ['烂板', '非涨停', '大跌'] and score > 70:
                    weak_to_strong_bonus = 15  # 巨大的加分！
                    is_weak_to_strong = True
                    final_score = min(100, final_score + weak_to_strong_bonus)
                
                # 🪜 连板溢价
                if lianban_count >= 2:
                    lianban_bonus = 10
                    final_score = min(100, final_score + lianban_bonus)
                elif lianban_count >= 4:
                    lianban_bonus = 15
                    final_score = min(100, final_score + lianban_bonus)
                
                # ⚠️ 高位风险（5板以上要注意核按钮）
                if lianban_count >= 5 and auction_pct < -3:
                    high_risk_penalty = 50
                    final_score = max(0, final_score - high_risk_penalty)
                
            except Exception as e:
                # 如果获取状态失败，不影响主流程
                pass
        
        return {
            "price": round(current_price, 2),
            "pct": round(auction_pct, 2),
            "score": min(100, max(0, final_score)),  # 限制在 0-100 分
            "base_score": min(100, max(0, score)),  # 原始得分（未应用时间权重）
            "time_weight": round(time_weight, 2),  # 时间权重
            "time_weight_desc": time_weight_desc,  # 时间权重描述
            "status": status,
            "turnover_rate": turnover_rate,
            "amount": amount,
            "bid_vol": bid_vol,
            "ask_vol": ask_vol,
            # 🆕 V9.13 修复：连板和弱转强信息
            "lianban_count": lianban_count,
            "yesterday_status": yesterday_status,
            "yesterday_pct": yesterday_pct,
            "is_weak_to_strong": is_weak_to_strong,
            "weak_to_strong_bonus": weak_to_strong_bonus,
            "lianban_bonus": lianban_bonus,
            "high_risk_penalty": high_risk_penalty
        }
    
    @staticmethod
    def batch_analyze_auction(stocks_data: Dict[str, Dict[str, Any]],
                                   last_closes: Dict[str, float],
                                   is_review_mode=False,
                                   data_manager=None) -> Dict[str, Dict[str, Any]]:
        """
        批量分析竞价强度
        
        Args:
            stocks_data: 股票快照数据字典 {code: stock_data}
            last_closes: 昨日收盘价字典 {code: last_close}
            is_review_mode: 复盘模式开关（V9.12.1新增）
            data_manager: 数据管理器实例（V9.13新增，用于获取连板信息）
            
        Returns:
            竞价分析结果字典 {code: analysis_result}
        """
        results = {}
        
        for code, stock_data in stocks_data.items():
            last_close = last_closes.get(code, 0)
            result = QuantAlgo.analyze_auction_strength(
                stock_data, 
                last_close, 
                is_review_mode,
                code=code,
                data_manager=data_manager
            )
            results[code] = result
        
        return results
