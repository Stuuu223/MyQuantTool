"""
反包模式、板块轮动、连板高度分析模块
基于拾荒网技术文章实现
"""
import pandas as pd
import numpy as np

class AdvancedPatternAnalyzer:
    """高级模式分析器"""
    
    @staticmethod
    def detect_fanbao_pattern(df, symbol):
        """
        识别反包模式
        
        反包模式:首板炸板→次日反包→二板加速
        
        Args:
            df: 历史K线数据
            symbol: 股票代码
        
        Returns:
            反包信号列表
        """
        try:
            signals = []
            
            if len(df) < 5:
                return signals
            
            # 计算涨跌幅
            df['change_pct'] = df['close'].pct_change() * 100
            
            for i in range(2, len(df)):
                # 检查首板炸板
                today_change = df.iloc[i]['change_pct']
                prev_change = df.iloc[i-1]['change_pct']
                
                # 首板炸板:前一天涨停(>9%),今天大跌(<-5%)
                if prev_change >= 9.9 and today_change <= -5:
                    # 检查次日是否反包
                    if i+1 < len(df):
                        next_change = df.iloc[i+1]['change_pct']
                        # 反包:次日大涨(>5%)
                        if next_change >= 5:
                            signals.append({
                                '日期': df.iloc[i]['date'],
                                '模式': '反包',
                                '首板日期': df.iloc[i-1]['date'],
                                '炸板日期': df.iloc[i]['date'],
                                '反包日期': df.iloc[i+1]['date'],
                                '首板涨幅': round(prev_change, 2),
                                '炸板跌幅': round(today_change, 2),
                                '反包涨幅': round(next_change, 2),
                                '信号强度': '强' if next_change >= 9.9 else '中'
                            })
            
            return signals
        except Exception as e:
            print(f"识别反包模式失败: {e}")
            return []
    
    @staticmethod
    def calculate_fanbao_success_rate(symbols, db):
        """
        计算反包成功率
        
        Args:
            symbols: 股票代码列表
            db: 数据库连接
        
        Returns:
            反包成功率统计
        """
        try:
            total_signals = 0
            success_count = 0
            fail_count = 0
            fanbao_records = []
            
            for symbol in symbols:
                try:
                    # 获取历史数据
                    df = db.get_history_data(symbol)
                    
                    if df.empty or len(df) < 10:
                        continue
                    
                    # 识别反包信号
                    signals = AdvancedPatternAnalyzer.detect_fanbao_pattern(df, symbol)
                    
                    for signal in signals:
                        total_signals += 1
                        
                        # 找到反包日期的索引
                        fanbao_idx = df[df['date'] == signal['反包日期']].index[0]
                        
                        # 检查反包后3天的表现
                        if fanbao_idx + 3 < len(df):
                            fanbao_price = df.iloc[fanbao_idx]['close']
                            future_price = df.iloc[fanbao_idx + 3]['close']
                            future_return = (future_price - fanbao_price) / fanbao_price * 100
                            
                            if future_return >= 3:
                                success_count += 1
                                result = '成功'
                            elif future_return <= -3:
                                fail_count += 1
                                result = '失败'
                            else:
                                result = '平局'
                            
                            fanbao_records.append({
                                '代码': symbol,
                                '反包日期': signal['反包日期'],
                                '反包涨幅': signal['反包涨幅'],
                                '3日后收益率': round(future_return, 2),
                                '结果': result
                            })
                except Exception as e:
                    print(f"分析股票 {symbol} 失败: {e}")
                    continue
            
            success_rate = (success_count / total_signals * 100) if total_signals > 0 else 0
            
            return {
                '总信号数': total_signals,
                '成功数': success_count,
                '失败数': fail_count,
                '成功率': round(success_rate, 2),
                '详细记录': pd.DataFrame(fanbao_records) if fanbao_records else pd.DataFrame()
            }
        except Exception as e:
            return {
                '错误': str(e)
            }
    
    @staticmethod
    def predict_fanbao_future(df, signal_date):
        """
        预测反包后的走势
        
        Args:
            df: 历史K线数据
            signal_date: 反包信号日期
        
        Returns:
            走势预测
        """
        try:
            # 找到反包日期的索引
            signal_idx = df[df['date'] == signal_date].index[0]
            
            # 计算技术指标
            from logic.algo import QuantAlgo
            
            signal_df = df.iloc[:signal_idx+1]
            
            macd_data = QuantAlgo.calculate_macd(signal_df)
            rsi_data = QuantAlgo.calculate_rsi(signal_df)
            volume_data = QuantAlgo.analyze_volume(signal_df)
            
            # 综合评分
            score = 0
            reasons = []
            
            # MACD趋势
            if macd_data['Trend'] == '多头':
                score += 30
                reasons.append("MACD多头趋势")
            else:
                score += 10
            
            # RSI位置
            if rsi_data['RSI'] < 50:
                score += 30
                reasons.append("RSI低位,有上涨空间")
            elif rsi_data['RSI'] < 70:
                score += 20
                reasons.append("RSI中性")
            else:
                score += 10
                reasons.append("RSI高位,注意风险")
            
            # 成交量
            if volume_data['量比'] > 1.5:
                score += 20
                reasons.append("放量上涨")
            elif volume_data['量比'] > 1:
                score += 15
                reasons.append("温和放量")
            else:
                score += 10
            
            # 价格位置
            current_price = df.iloc[signal_idx]['close']
            ma5 = df.iloc[signal_idx]['close'].rolling(5).mean().iloc[-1]
            
            if current_price > ma5:
                score += 20
                reasons.append("价格站上5日线")
            else:
                score += 10
            
            # 预测结果
            if score >= 80:
                prediction = "🔥 强烈看涨"
                suggestion = "建议积极参与"
            elif score >= 60:
                prediction = "📈 看涨"
                suggestion = "可以参与"
            elif score >= 40:
                prediction = "🟡 中性"
                suggestion = "谨慎观望"
            else:
                prediction = "📉 看跌"
                suggestion = "不建议参与"
            
            return {
                '评分': score,
                '预测': prediction,
                '建议': suggestion,
                '原因': reasons
            }
        except Exception as e:
            return {
                '错误': str(e)
            }
    
    @staticmethod
    def monitor_sector_rotation():
        """
        监控板块轮动
        
        分析内容:
        - 板块资金流向
        - 板块热度排名
        - 龙头股追踪
        """
        try:
            import akshare as ak
            
            # 获取板块资金流向
            sector_flow_df = ak.stock_sector_fund_flow_rank()
            
            if sector_flow_df.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '暂无板块数据'
                }
            
            # 处理数据
            sectors = []
            for _, row in sector_flow_df.head(30).iterrows():
                sectors.append({
                    '板块名称': row.iloc[1],
                    '涨跌幅': row.iloc[2],
                    '主力净流入': row.iloc[3],
                    '主力净流入占比': row.iloc[4],
                    '热度评分': AdvancedPatternAnalyzer._calculate_sector_heat(row)
                })
            
            # 按热度评分排序
            sectors.sort(key=lambda x: x['热度评分'], reverse=True)
            
            # 识别热门板块
            hot_sectors = [s for s in sectors if s['热度评分'] >= 60]
            cold_sectors = [s for s in sectors if s['热度评分'] <= 30]
            
            return {
                '数据状态': '正常',
                '板块列表': sectors,
                '热门板块': hot_sectors[:10],
                '冷门板块': cold_sectors[:10],
                '最强板块': sectors[0] if sectors else None
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def _calculate_sector_heat(row):
        """
        计算板块热度评分
        
        考虑因素:
        - 涨跌幅
        - 主力净流入
        - 净流入占比
        """
        score = 0
        
        # 涨跌幅评分
        change_pct = row.iloc[2]
        if change_pct >= 5:
            score += 40
        elif change_pct >= 3:
            score += 30
        elif change_pct >= 1:
            score += 20
        elif change_pct >= 0:
            score += 10
        else:
            score += 0
        
        # 主力净流入评分
        net_flow = row.iloc[3]
        if net_flow >= 1000000000:  # 10亿以上
            score += 30
        elif net_flow >= 500000000:  # 5亿以上
            score += 25
        elif net_flow >= 100000000:  # 1亿以上
            score += 20
        elif net_flow >= 0:
            score += 10
        else:
            score += 0
        
        # 净流入占比评分
        flow_ratio = row.iloc[4]
        if flow_ratio >= 10:
            score += 30
        elif flow_ratio >= 5:
            score += 25
        elif flow_ratio >= 2:
            score += 20
        elif flow_ratio >= 0:
            score += 10
        else:
            score += 0
        
        return score
    
    @staticmethod
    def track_sector_leaders(sector_name):
        """
        追踪板块龙头股
        
        Args:
            sector_name: 板块名称
        
        Returns:
            龙头股列表
        """
        try:
            import akshare as ak
            
            # 先获取板块列表,找到对应的板块代码
            try:
                # 获取概念板块列表
                concept_list = ak.stock_board_concept_name_em()
                
                # 查找匹配的板块
                sector_code = None
                for _, row in concept_list.iterrows():
                    if sector_name in row['板块名称']:
                        sector_code = row['板块代码']
                        break
                
                if not sector_code:
                    return {
                        '数据状态': '无数据',
                        '说明': f'未找到板块: {sector_name}'
                    }
                
                # 获取板块成分股
                concept_stocks = ak.stock_board_concept_cons_em(symbol=sector_code)
                
            except Exception as e:
                # 如果概念板块失败,尝试行业板块
                try:
                    industry_list = ak.stock_board_industry_name_em()
                    
                    sector_code = None
                    for _, row in industry_list.iterrows():
                        if sector_name in row['板块名称']:
                            sector_code = row['板块代码']
                            break
                    
                    if not sector_code:
                        return {
                            '数据状态': '无数据',
                            '说明': f'未找到板块: {sector_name}'
                        }
                    
                    concept_stocks = ak.stock_board_industry_cons_em(symbol=sector_code)
                    
                except Exception as e2:
                    return {
                        '数据状态': '获取失败',
                        '说明': f'获取板块数据失败: {str(e)}, {str(e2)}'
                    }
            
            if concept_stocks.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '该板块暂无成分股'
                }
            
            # 筛选涨跌停股票
            leaders = []
            for _, row in concept_stocks.iterrows():
                change_pct = row['涨跌幅']
                
                # 涨停或接近涨停
                if change_pct >= 9.5:
                    leaders.append({
                        '代码': row['代码'],
                        '名称': row['名称'],
                        '最新价': row['最新价'],
                        '涨跌幅': change_pct,
                        '成交额': row['成交额'],
                        '换手率': row['换手率'],
                        '龙头评分': AdvancedPatternAnalyzer._calculate_leader_score(row)
                    })
            
            # 按龙头评分排序
            leaders.sort(key=lambda x: x['龙头评分'], reverse=True)
            
            return {
                '数据状态': '正常',
                '板块名称': sector_name,
                '龙头股': leaders[:5]
            }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def _calculate_leader_score(row):
        """
        计算龙头评分
        
        考虑因素:
        - 涨跌幅
        - 成交额
        - 换手率
        """
        score = 0
        
        # 涨跌幅评分
        change_pct = row['涨跌幅']
        if change_pct >= 9.9:
            score += 40
        elif change_pct >= 9.5:
            score += 30
        else:
            score += 20
        
        # 成交额评分
        amount = row['成交额']
        if amount >= 1000000000:  # 10亿以上
            score += 30
        elif amount >= 500000000:  # 5亿以上
            score += 25
        elif amount >= 200000000:  # 2亿以上
            score += 20
        else:
            score += 10
        
        # 换手率评分
        turnover = row['换手率']
        if 5 <= turnover <= 15:
            score += 30
        elif 2 <= turnover < 5:
            score += 20
        elif 15 < turnover <= 25:
            score += 20
        else:
            score += 10
        
        return score
    
    @staticmethod
    def analyze_board_height():
        """
        连板高度分析
        
        分析内容:
        - 不同板数的胜率
        - 连板股特征分析
        - 高度预警系统
        """
        try:
            import akshare as ak
            
            # 获取涨停数据
            limit_stocks = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))
            
            if limit_stocks.empty:
                return {
                    '数据状态': '无数据',
                    '说明': '今日暂无涨跌停数据'
                }
            
            # 统计连板高度
            if '连板数' in limit_stocks.columns:
                board_stats = limit_stocks.groupby('连板数').agg({
                    '代码': 'count',
                    '涨跌幅': 'mean',
                    '成交额': 'mean',
                    '换手率': 'mean'
                }).rename(columns={'代码': '数量'})
                
                # 计算胜率(基于历史数据,这里简化处理)
                board_stats['胜率'] = board_stats.index.map(
                    lambda x: AdvancedPatternAnalyzer._estimate_win_rate(x)
                )
                
                # 识别高板数风险
                high_risk_boards = board_stats[board_stats.index >= 5]
                
                # 预警系统
                warnings = []
                if len(high_risk_boards) > 0:
                    total_high_risk = high_risk_boards['数量'].sum()
                    if total_high_risk >= 5:
                        warnings.append(f"⚠️ 高板数股票过多({total_high_risk}只),注意风险")
                
                # 分析连板股特征
                board_features = []
                for _, row in limit_stocks.iterrows():
                    board_count = row.get('连板数', 1)
                    features = {
                        '代码': row['代码'],
                        '名称': row['名称'],
                        '连板数': board_count,
                        '涨跌幅': row['涨跌幅'],
                        '成交额': row['成交额'],
                        '换手率': row['换手率'],
                        '风险等级': AdvancedPatternAnalyzer._assess_risk_level(board_count, row)
                    }
                    board_features.append(features)
                
                return {
                    '数据状态': '正常',
                    '连板统计': board_stats,
                    '连板特征': board_features,
                    '风险预警': warnings,
                    '高板数股票': high_risk_boards
                }
            else:
                return {
                    '数据状态': '无连板数据',
                    '说明': '数据中不包含连板数信息'
                }
        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e)
            }
    
    @staticmethod
    def _estimate_win_rate(board_count):
        """
        估算不同板数的胜率
        
        基于经验数据:
        - 首板: 胜率约30%
        - 二板: 胜率约50%
        - 三板: 胜率约60%
        - 四板: 胜率约50%
        - 五板及以上: 胜率约30%
        """
        if board_count == 1:
            return 30
        elif board_count == 2:
            return 50
        elif board_count == 3:
            return 60
        elif board_count == 4:
            return 50
        else:
            return 30
    
    @staticmethod
    def _assess_risk_level(board_count, row):
        """
        评估风险等级
        
        Args:
            board_count: 连板数
            row: 股票数据行
        
        Returns:
            风险等级
        """
        if board_count >= 7:
            return "🔴 极高风险"
        elif board_count >= 5:
            return "🟠 高风险"
        elif board_count >= 3:
            return "🟡 中风险"
        else:
            return "🟢 低风险"