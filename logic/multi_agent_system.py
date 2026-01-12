"""
多智能体金融分析系统
基于多智能体协作的智能化股票分析和交易建议系统

核心智能体：
1. 数据分析师 - 负责数据获取、清洗、预处理
2. 技术分析师 - 负责技术指标计算、形态识别
3. 基本面分析师 - 负责财务数据、行业分析
4. 情绪分析师 - 负责市场情绪、资金流向分析
5. 风险评估师 - 负责风险评估、止损建议
6. 策略研究员 - 负责策略生成、优化
7. 决策协调员 - 负责协调各智能体，生成最终建议
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class AgentMessage:
    """智能体之间的消息"""
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: datetime


@dataclass
class AnalysisResult:
    """分析结果"""
    agent_name: str
    score: float  # 0-100
    confidence: float  # 0-1
    findings: List[str]
    recommendations: List[str]
    data: Dict[str, Any]


class BaseAgent:
    """基础智能体"""
    
    def __init__(self, name: str):
        self.name = name
        self.messages: List[AgentMessage] = []
    
    def receive_message(self, message: AgentMessage):
        """接收消息"""
        self.messages.append(message)
    
    def send_message(self, receiver: str, content: Dict[str, Any]) -> AgentMessage:
        """发送消息"""
        message = AgentMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            timestamp=datetime.now()
        )
        return message
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """分析数据（子类需要实现）"""
        raise NotImplementedError
    
    def get_name(self) -> str:
        """获取智能体名称"""
        return self.name


class DataAnalystAgent(BaseAgent):
    """数据分析师 - 负责数据获取、清洗、预处理"""
    
    def __init__(self):
        super().__init__("数据分析师")
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """分析数据质量"""
        findings = []
        recommendations = []
        score = 0
        confidence = 0.9
        
        df = data.get('df', None)
        if df is None:
            return AnalysisResult(
                agent_name=self.name,
                score=0,
                confidence=0,
                findings=["数据为空"],
                recommendations=["请提供有效的股票数据"],
                data={}
            )
        
        # 1. 检查数据完整性
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            findings.append(f"缺少必要列: {', '.join(missing_columns)}")
            score += 0
        else:
            findings.append("数据列完整")
            score += 30
        
        # 2. 检查数据量
        data_length = len(df)
        if data_length >= 60:
            findings.append(f"数据量充足: {data_length}天")
            score += 30
        elif data_length >= 30:
            findings.append(f"数据量适中: {data_length}天")
            score += 20
        else:
            findings.append(f"数据量不足: {data_length}天，建议至少30天")
            score += 10
            recommendations.append("建议获取更多历史数据")
        
        # 3. 检查数据质量
        null_count = df.isnull().sum().sum()
        if null_count == 0:
            findings.append("数据无缺失值")
            score += 20
        else:
            findings.append(f"数据有{null_count}个缺失值")
            score += 10
            recommendations.append("建议处理缺失值")
        
        # 4. 检查数据连续性
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            date_range = (df['date'].max() - df['date'].min()).days
            expected_days = len(df)
            if date_range / expected_days < 1.5:  # 考虑周末和节假日
                findings.append("数据连续性良好")
                score += 20
            else:
                findings.append("数据存在较多缺失日期")
                score += 10
        
        return AnalysisResult(
            agent_name=self.name,
            score=min(score, 100),
            confidence=confidence,
            findings=findings,
            recommendations=recommendations,
            data={
                'data_length': data_length,
                'null_count': null_count,
                'missing_columns': missing_columns
            }
        )


class TechnicalAnalystAgent(BaseAgent):
    """技术分析师 - 负责技术指标计算、形态识别"""
    
    def __init__(self):
        super().__init__("技术分析师")
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """技术分析"""
        findings = []
        recommendations = []
        score = 0
        confidence = 0.85
        
        df = data.get('df', None)
        if df is None or len(df) < 20:
            return AnalysisResult(
                agent_name=self.name,
                score=0,
                confidence=0,
                findings=["数据不足"],
                recommendations=["请提供至少20天的数据"],
                data={}
            )
        
        latest = df.iloc[-1]
        
        # 1. 趋势分析
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        
        if latest['close'] > ma5 > ma10 > ma20:
            findings.append("多头排列，趋势向上")
            score += 25
            recommendations.append("趋势向好，可考虑逢低买入")
        elif latest['close'] < ma5 < ma10 < ma20:
            findings.append("空头排列，趋势向下")
            score += 5
            recommendations.append("趋势走弱，建议观望或减仓")
        else:
            findings.append("趋势震荡")
            score += 15
        
        # 2. 动量分析
        if len(df) >= 5:
            momentum = (latest['close'] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            if momentum > 5:
                findings.append(f"短期动量强劲（{momentum:.2f}%）")
                score += 20
            elif momentum > 0:
                findings.append(f"短期动量向上（{momentum:.2f}%）")
                score += 15
            elif momentum > -5:
                findings.append(f"短期动量向下（{momentum:.2f}%）")
                score += 10
            else:
                findings.append(f"短期动量疲弱（{momentum:.2f}%）")
                score += 5
        
        # 3. 成交量分析
        if len(df) >= 5:
            volume_ma5 = df['volume'].rolling(5).mean().iloc[-1]
            volume_ratio = latest['volume'] / volume_ma5
            
            if volume_ratio > 2:
                findings.append(f"成交量显著放大（{volume_ratio:.2f}倍）")
                score += 20
            elif volume_ratio > 1.5:
                findings.append(f"成交量温和放大（{volume_ratio:.2f}倍）")
                score += 15
            elif volume_ratio > 1:
                findings.append(f"成交量正常（{volume_ratio:.2f}倍）")
                score += 10
            else:
                findings.append(f"成交量萎缩（{volume_ratio:.2f}倍）")
                score += 5
        
        # 4. 波动率分析
        if len(df) >= 10:
            volatility = df['close'].rolling(10).std().iloc[-1] / latest['close'] * 100
            if volatility < 1:
                findings.append(f"波动率较低（{volatility:.2f}%），走势平稳")
                score += 15
            elif volatility < 2:
                findings.append(f"波动率适中（{volatility:.2f}%）")
                score += 10
            else:
                findings.append(f"波动率较高（{volatility:.2f}%），风险较大")
                score += 5
        
        # 5. 支撑阻力位
        if len(df) >= 20:
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            distance_to_high = (recent_high - latest['close']) / latest['close'] * 100
            distance_to_low = (latest['close'] - recent_low) / latest['close'] * 100
            
            if distance_to_high < 2:
                findings.append(f"接近近期高点阻力位（{distance_to_high:.2f}%）")
                score += 5
                recommendations.append(f"注意阻力位{recent_high:.2f}")
            
            if distance_to_low < 2:
                findings.append(f"接近近期低点支撑位（{distance_to_low:.2f}%）")
                score += 10
                recommendations.append(f"关注支撑位{recent_low:.2f}")
        
        return AnalysisResult(
            agent_name=self.name,
            score=min(score, 100),
            confidence=confidence,
            findings=findings,
            recommendations=recommendations,
            data={
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'momentum': momentum if len(df) >= 5 else 0,
                'volume_ratio': volume_ratio if len(df) >= 5 else 1,
                'volatility': volatility if len(df) >= 10 else 0
            }
        )


class RiskAssessmentAgent(BaseAgent):
    """风险评估师 - 负责风险评估、止损建议"""
    
    def __init__(self):
        super().__init__("风险评估师")
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """风险评估"""
        findings = []
        recommendations = []
        score = 0
        confidence = 0.9
        
        df = data.get('df', None)
        if df is None or len(df) < 10:
            return AnalysisResult(
                agent_name=self.name,
                score=0,
                confidence=0,
                findings=["数据不足"],
                recommendations=["请提供至少10天的数据"],
                data={}
            )
        
        latest = df.iloc[-1]
        
        # 1. 价格波动风险
        if len(df) >= 10:
            volatility = df['close'].rolling(10).std().iloc[-1] / latest['close'] * 100
            if volatility < 1:
                findings.append(f"价格波动率低（{volatility:.2f}%），风险较小")
                score += 30
            elif volatility < 2:
                findings.append(f"价格波动率适中（{volatility:.2f}%），风险可控")
                score += 20
            else:
                findings.append(f"价格波动率高（{volatility:.2f}%），风险较大")
                score += 10
        
        # 2. 回撤风险
        if len(df) >= 20:
            recent_high = df['high'].tail(20).max()
            drawdown = (recent_high - latest['close']) / recent_high * 100
            
            if drawdown < 5:
                findings.append(f"距近期高点回撤较小（{drawdown:.2f}%）")
                score += 30
            elif drawdown < 10:
                findings.append(f"距近期高点回撤适中（{drawdown:.2f}%）")
                score += 20
            elif drawdown < 20:
                findings.append(f"距近期高点回撤较大（{drawdown:.2f}%），注意风险")
                score += 10
            else:
                findings.append(f"距近期高点回撤很大（{drawdown:.2f}%），风险较高")
                score += 5
        
        # 3. 止损建议
        if len(df) >= 10:
            recent_low = df['low'].tail(10).min()
            stop_loss = recent_low * 0.98  # 最低价下方2%
            stop_loss_ratio = (latest['close'] - stop_loss) / latest['close'] * 100
            
            findings.append(f"建议止损位：{stop_loss:.2f}（-{stop_loss_ratio:.2f}%）")
            recommendations.append(f"跌破{stop_loss:.2f}建议止损")
            
            if stop_loss_ratio < 3:
                score += 20
            elif stop_loss_ratio < 5:
                score += 15
            else:
                score += 10
        
        # 4. 仓位建议
        if score >= 70:
            findings.append("风险较低，可适当增加仓位")
            recommendations.append("建议仓位30-50%")
        elif score >= 50:
            findings.append("风险适中，建议控制仓位")
            recommendations.append("建议仓位20-30%")
        else:
            findings.append("风险较高，建议轻仓或观望")
            recommendations.append("建议仓位10-20%")
        
        return AnalysisResult(
            agent_name=self.name,
            score=min(score, 100),
            confidence=confidence,
            findings=findings,
            recommendations=recommendations,
            data={
                'volatility': volatility if len(df) >= 10 else 0,
                'drawdown': drawdown if len(df) >= 20 else 0,
                'stop_loss': stop_loss if len(df) >= 10 else latest['close'] * 0.95,
                'stop_loss_ratio': stop_loss_ratio if len(df) >= 10 else 5
            }
        )


class DecisionCoordinatorAgent(BaseAgent):
    """决策协调员 - 负责协调各智能体，生成最终建议"""
    
    def __init__(self):
        super().__init__("决策协调员")
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """协调决策"""
        # 获取各智能体的分析结果
        agent_results = data.get('agent_results', [])
        
        if not agent_results:
            return AnalysisResult(
                agent_name=self.name,
                score=0,
                confidence=0,
                findings=["没有智能体分析结果"],
                recommendations=["请先运行其他智能体"],
                data={}
            )
        
        # 计算综合得分
        total_score = sum(result.score for result in agent_results)
        avg_score = total_score / len(agent_results)
        
        # 计算加权得分（根据置信度）
        weighted_score = sum(result.score * result.confidence for result in agent_results)
        weighted_avg = weighted_score / sum(result.confidence for result in agent_results)
        
        # 收集所有发现和建议
        all_findings = []
        all_recommendations = []
        
        for result in agent_results:
            all_findings.extend([f"[{result.agent_name}] {f}" for f in result.findings])
            all_recommendations.extend([f"[{result.agent_name}] {r}" for r in result.recommendations])
        
        # 生成最终建议
        final_recommendation = self._generate_final_recommendation(weighted_avg, agent_results)
        
        findings = [
            f"综合得分: {weighted_avg:.1f}/100",
            f"参与智能体: {len(agent_results)}个",
            f"最高得分: {max(result.score for result in agent_results):.1f} ({max(agent_results, key=lambda x: x.score).agent_name})",
            f"最低得分: {min(result.score for result in agent_results):.1f} ({min(agent_results, key=lambda x: x.score).agent_name})"
        ]
        
        return AnalysisResult(
            agent_name=self.name,
            score=weighted_avg,
            confidence=0.95,
            findings=findings,
            recommendations=[final_recommendation] + all_recommendations,
            data={
                'total_score': total_score,
                'avg_score': avg_score,
                'weighted_score': weighted_score,
                'agent_count': len(agent_results)
            }
        )
    
    def _generate_final_recommendation(self, score: float, agent_results: List[AnalysisResult]) -> str:
        """生成最终建议"""
        if score >= 70:
            return "[买入] 建议买入：多智能体综合评分较高，各项指标向好"
        elif score >= 50:
            return "[持有] 建议持有：多智能体综合评分中等，走势平稳"
        elif score >= 30:
            return "[观望] 建议观望：多智能体综合评分偏低，建议等待明确信号"
        else:
            return "[卖出] 建议卖出：多智能体综合评分较低，风险较高"


class MultiAgentSystem:
    """多智能体系统"""
    
    def __init__(self):
        self.agents = {
            '数据分析师': DataAnalystAgent(),
            '技术分析师': TechnicalAnalystAgent(),
            '风险评估师': RiskAssessmentAgent(),
            '决策协调员': DecisionCoordinatorAgent()
        }
        self.message_history: List[AgentMessage] = []
    
    def analyze_stock(self, df: pd.DataFrame, stock_code: str = None) -> Dict[str, Any]:
        """
        多智能体协作分析股票
        
        Args:
            df: 股票数据
            stock_code: 股票代码
        
        Returns:
            分析结果字典
        """
        results = {}
        
        # 准备数据
        data = {'df': df, 'stock_code': stock_code}
        
        # 1. 数据分析师
        print(f"[{self.agents['数据分析师'].name}] 开始分析...")
        data_result = self.agents['数据分析师'].analyze(data)
        results['数据分析师'] = data_result
        print(f"[{self.agents['数据分析师'].name}] 完成，得分: {data_result.score:.1f}")
        
        # 如果数据质量太差，直接返回
        if data_result.score < 30:
            return {
                'success': False,
                'message': '数据质量不足，无法进行有效分析',
                'results': results
            }
        
        # 2. 技术分析师
        print(f"[{self.agents['技术分析师'].name}] 开始分析...")
        tech_result = self.agents['技术分析师'].analyze(data)
        results['技术分析师'] = tech_result
        print(f"[{self.agents['技术分析师'].name}] 完成，得分: {tech_result.score:.1f}")
        
        # 3. 风险评估师
        print(f"[{self.agents['风险评估师'].name}] 开始分析...")
        risk_result = self.agents['风险评估师'].analyze(data)
        results['风险评估师'] = risk_result
        print(f"[{self.agents['风险评估师'].name}] 完成，得分: {risk_result.score:.1f}")
        
        # 4. 决策协调员
        print(f"[{self.agents['决策协调员'].name}] 开始协调...")
        coordinator_data = {'agent_results': list(results.values())}
        final_result = self.agents['决策协调员'].analyze(coordinator_data)
        results['决策协调员'] = final_result
        print(f"[{self.agents['决策协调员'].name}] 完成，综合得分: {final_result.score:.1f}")
        
        # 生成综合报告
        report = self._generate_comprehensive_report(results, stock_code)
        
        return {
            'success': True,
            'message': '分析完成',
            'results': results,
            'report': report,
            'final_score': final_result.score,
            'final_recommendation': final_result.recommendations[0] if final_result.recommendations else ""
        }
    
    def _generate_comprehensive_report(self, results: Dict[str, AnalysisResult], stock_code: str = None) -> str:
        """生成综合报告"""
        report_parts = []
        
        # 标题
        title = f"多智能体股票分析报告"
        if stock_code:
            title += f" - {stock_code}"
        report_parts.append(title)
        report_parts.append("")
        
        # 综合评分
        final_result = results.get('决策协调员')
        if final_result:
            report_parts.append(f"综合评分: {final_result.score:.1f}/100")
            report_parts.append("")
            
            # 最终建议
            if final_result.recommendations:
                report_parts.append(f"{final_result.recommendations[0]}")
                report_parts.append("")
            
            # 综合发现
            report_parts.append("综合发现")
            for finding in final_result.findings:
                report_parts.append(f"- {finding}")
            report_parts.append("")
        
        # 各智能体分析结果
        report_parts.append("各智能体分析结果")
        report_parts.append("")
        
        for agent_name, result in results.items():
            if agent_name == '决策协调员':
                continue
            
            report_parts.append(f"{agent_name}")
            report_parts.append(f"得分: {result.score:.1f}/100 | 置信度: {result.confidence*100:.0f}%")
            report_parts.append("")
            
            if result.findings:
                report_parts.append("发现:")
                for finding in result.findings:
                    report_parts.append(f"- {finding}")
                report_parts.append("")
            
            if result.recommendations:
                report_parts.append("建议:")
                for rec in result.recommendations:
                    report_parts.append(f"- {rec}")
                report_parts.append("")
        
        return '\n'.join(report_parts)
    
    def get_agent_names(self) -> List[str]:
        """获取所有智能体名称"""
        return list(self.agents.keys())


# 使用示例
if __name__ == "__main__":
    # 创建多智能体系统
    mas = MultiAgentSystem()
    
    # 创建测试数据
    dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
    np.random.seed(42)
    
    # 模拟上涨趋势
    close_prices = 100 + np.cumsum(np.random.randn(60) * 0.5 + 0.3)
    high_prices = close_prices + np.random.rand(60) * 2
    low_prices = close_prices - np.random.rand(60) * 2
    open_prices = close_prices + np.random.randn(60)
    volumes = np.random.randint(1000000, 5000000, 60)
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    
    # 分析股票
    print("=" * 60)
    print("开始多智能体分析...")
    print("=" * 60)
    
    result = mas.analyze_stock(df, "600519")
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)
    print(f"\n综合得分: {result['final_score']:.1f}/100")
    print(f"最终建议: {result['final_recommendation']}")
    print("\n" + result['report'])
