import pandas as pd
import numpy as np

class DeepSeekAgent:
    """
    本地智能分析系统
    基于规则和机器学习的股票分析，不依赖外部 API
    """
    def __init__(self, api_key=None):
        # 保留 api_key 参数以兼容主程序，但实际不使用
        self.api_key = api_key
        # 可以在这里加载预训练的模型（如果需要）
        self.model = None
    
    def analyze_stock(self, symbol, price_change, technical_data):
        """
        本地智能分析股票
        
        Args:
            symbol: 股票代码
            price_change: 涨跌幅
            technical_data: 技术指标字典
        """
        try:
            # 1. 计算各项指标得分
            scores = self._calculate_scores(price_change, technical_data)
            
            # 2. 判断市场状态
            market_state = self._judge_market_state(scores, price_change)
            
            # 3. 识别风险点
            risks = self._identify_risks(technical_data, scores)
            
            # 4. 生成操作建议
            operation = self._generate_operation(scores, market_state, risks, technical_data)
            
            # 5. 组装分析报告
            report = self._format_report(symbol, technical_data, market_state, risks, operation)
            
            return report
        except Exception as e:
            return f"❌ 分析失败: {str(e)}"
    
    def _calculate_scores(self, price_change, technical_data):
        """计算各项技术指标的得分"""
        scores = {}
        
        # 1. 涨跌幅得分
        if price_change > 5:
            scores['涨跌幅'] = 20
        elif price_change > 3:
            scores['涨跌幅'] = 15
        elif price_change > 0:
            scores['涨跌幅'] = 10
        elif price_change > -3:
            scores['涨跌幅'] = 5
        else:
            scores['涨跌幅'] = 0
        
        # 2. MACD 得分
        macd = technical_data.get('macd', {})
        if macd.get('Trend') == '多头':
            scores['MACD'] = 20
        elif macd.get('Trend') == '空头':
            scores['MACD'] = 0
        else:
            scores['MACD'] = 10
        
        # 3. RSI 得分
        rsi = technical_data.get('rsi', {})
        rsi_value = rsi.get('RSI', 50)
        if 30 <= rsi_value <= 70:
            scores['RSI'] = 20
        elif rsi_value < 30:
            scores['RSI'] = 15  # 超卖，可能反弹
        elif rsi_value > 70:
            scores['RSI'] = 5   # 超买，风险高
        else:
            scores['RSI'] = 10
        
        # 4. 布林带得分
        bollinger = technical_data.get('bollinger', {})
        current_price = technical_data.get('current_price', 0)
        lower_band = bollinger.get('下轨', 0)
        upper_band = bollinger.get('上轨', 0)
        
        if lower_band > 0 and upper_band > 0:
            position = (current_price - lower_band) / (upper_band - lower_band) * 100
            if position < 20:
                scores['布林带'] = 20  # 接近下轨
            elif position > 80:
                scores['布林带'] = 5   # 接近上轨
            else:
                scores['布林带'] = 15  # 中间区域
        else:
            scores['布林带'] = 10
        
        # 5. 资金流向得分
        money_flow = technical_data.get('money_flow', {})
        flow_type = money_flow.get('资金流向', '')
        if flow_type == '净流入':
            scores['资金流向'] = 20
        elif flow_type == '净流出':
            scores['资金流向'] = 0
        else:
            scores['资金流向'] = 10
        
        # 6. 成交量得分
        volume = technical_data.get('volume', {})
        volume_ratio = volume.get('量比', 1)
        if volume_ratio > 2:
            scores['成交量'] = 20
        elif volume_ratio > 1.5:
            scores['成交量'] = 15
        elif volume_ratio > 1:
            scores['成交量'] = 10
        else:
            scores['成交量'] = 5
        
        # 7. 形态识别得分
        patterns = technical_data.get('patterns', {})
        pattern_score = 10
        if patterns.get('double_bottom', {}).get('is_double_bottom'):
            pattern_score = 20
        elif patterns.get('double_top', {}).get('is_double_top'):
            pattern_score = 0
        elif patterns.get('head_shoulders', {}).get('pattern') == 'head_shoulders_bottom':
            pattern_score = 20
        elif patterns.get('head_shoulders', {}).get('pattern') == 'head_shoulders_top':
            pattern_score = 0
        scores['形态'] = pattern_score
        
        return scores
    
    def _judge_market_state(self, scores, price_change):
        """判断市场状态"""
        total_score = sum(scores.values())
        max_score = len(scores) * 20
        
        # 计算得分比例
        score_ratio = total_score / max_score
        
        if score_ratio >= 0.7:
            return "强势上涨"
        elif score_ratio >= 0.5:
            return "温和上涨"
        elif score_ratio >= 0.3:
            return "震荡整理"
        elif score_ratio >= 0.2:
            return "弱势下跌"
        else:
            return "深度调整"
    
    def _identify_risks(self, technical_data, scores):
        """识别风险点"""
        risks = []
        
        # 1. RSI 超买风险
        rsi = technical_data.get('rsi', {})
        if rsi.get('RSI', 50) > 70:
            risks.append("RSI超买，短期可能回调")
        
        # 2. 接近阻力位
        resistance = technical_data.get('resistance_levels', [])
        current_price = technical_data.get('current_price', 0)
        if resistance and current_price > 0:
            nearest_resistance = min([r for r in resistance if r > current_price], default=None)
            if nearest_resistance and nearest_resistance - current_price < current_price * 0.02:
                risks.append(f"接近阻力位¥{nearest_resistance:.2f}")
        
        # 3. 资金流出风险
        money_flow = technical_data.get('money_flow', {})
        if money_flow.get('资金流向') == '净流出':
            risks.append("资金净流出，主力在撤退")
        
        # 4. 高位风险
        bollinger = technical_data.get('bollinger', {})
        if bollinger.get('当前位置', 50) > 80:
            risks.append("价格接近布林带上轨，存在回调风险")
        
        # 5. 形态风险
        patterns = technical_data.get('patterns', {})
        if patterns.get('double_top', {}).get('is_double_top'):
            risks.append("双顶形态，可能见顶")
        elif patterns.get('head_shoulders', {}).get('pattern') == 'head_shoulders_top':
            risks.append("头肩顶形态，注意风险")
        
        return risks if risks else ["无明显风险"]
    
    def _generate_operation(self, scores, market_state, risks, technical_data):
        """生成操作建议"""
        total_score = sum(scores.values())
        max_score = len(scores) * 20
        score_ratio = total_score / max_score
        
        operation = {
            '建议': '',
            '理由': '',
            '参考价位': []
        }
        
        # 根据得分和市场状态给出建议
        if score_ratio >= 0.7:
            operation['建议'] = '买入'
            operation['理由'] = f'各项指标向好，{market_state}趋势明确，建议积极介入'
        elif score_ratio >= 0.5:
            operation['建议'] = '持有'
            operation['理由'] = f'整体走势平稳，{market_state}中，建议继续持有'
        elif score_ratio >= 0.3:
            operation['建议'] = '观望'
            operation['理由'] = f'市场处于{market_state}状态，建议观望等待明确信号'
        else:
            operation['建议'] = '卖出'
            operation['理由'] = f'多项指标走弱，{market_state}中，建议减仓或清仓'
        
        # 参考价位
        current_price = technical_data.get('current_price', 0)
        support = technical_data.get('support_levels', [])
        resistance = technical_data.get('resistance_levels', [])
        
        if current_price > 0:
            if operation['建议'] == '买入':
                # 买入参考位：支撑位附近
                if support:
                    nearest_support = max([s for s in support if s < current_price], default=current_price * 0.98)
                    operation['参考价位'].append(f'买入参考：¥{nearest_support:.2f}')
                operation['参考价位'].append(f'止损参考：¥{current_price * 0.95:.2f}')
            
            elif operation['建议'] == '卖出':
                # 卖出参考位：阻力位附近
                if resistance:
                    nearest_resistance = min([r for r in resistance if r > current_price], default=current_price * 1.02)
                    operation['参考价位'].append(f'止盈参考：¥{nearest_resistance:.2f}')
                operation['参考价位'].append(f'止损参考：¥{current_price * 0.95:.2f}')
        
        return operation
    
    def _format_report(self, symbol, technical_data, market_state, risks, operation):
        """格式化分析报告"""
        current_price = technical_data.get('current_price', 0)
        
        # 构建报告
        report_parts = []
        
        # 1. 当前状态
        report_parts.append(f"📊 **当前状态**：{market_state}")
        report_parts.append(f"当前价格 ¥{current_price:.2f}，整体走势{'向好' if '上涨' in market_state else '走弱' if '下跌' in market_state else '平稳'}。")
        
        # 2. 风险提示
        report_parts.append(f"\n⚠️ **风险提示**：{'; '.join(risks)}")
        
        # 3. 操作建议
        report_parts.append(f"\n🎯 **操作建议**：{operation['建议']}")
        report_parts.append(operation['理由'])
        
        # 4. 参考价位
        if operation['参考价位']:
            report_parts.append(f"\n💰 **参考价位**：{' | '.join(operation['参考价位'])}")
        
        return '\n'.join(report_parts)
