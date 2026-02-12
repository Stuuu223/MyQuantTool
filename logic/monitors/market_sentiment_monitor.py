"""
市场情绪监控器（Market Sentiment Monitor）
实现"情绪过热熔断机制"，自动识别"群魔乱舞"的风险
防止在题材高峰期追高被套
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MarketSentimentMonitor:
    """
    市场情绪监控器
    
    核心功能：
    1. 检查市场结构：真龙引领 vs 群魔乱舞
    2. 情绪过热熔断：防止在题材高峰期追高
    3. 龙头识别：找到真正的龙头
    4. 风险预警：提前提示市场退潮信号
    """
    
    def __init__(self):
        """初始化情绪监控器"""
        self.market_state = "UNKNOWN"
        self.warning_level = "LOW"
        self.dragon_candidates = []
    
    def check_market_structure(self, 
                             stocks_data: List[Dict[str, Any]],
                             timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        检查市场结构：是"真龙引领"还是"群魔乱舞"？
        
        Args:
            stocks_data: 股票数据列表，每个元素包含 symbol, score, change_percent 等
            timestamp: 时间戳（可选）
            
        Returns:
            市场结构分析结果
        """
        if not stocks_data:
            return {
                'market_state': 'NO_DATA',
                'warning_level': 'LOW',
                'message': '无数据'
            }
        
        # 统计不同评分区间的股票数量
        scores = [s.get('score', 0) for s in stocks_data]
        count_90_plus = len([s for s in scores if s >= 90])
        count_80_plus = len([s for s in scores if s >= 80])
        count_70_plus = len([s for s in scores if s >= 70])
        count_50_plus = len([s for s in scores if s >= 50])
        total_stocks = len(stocks_data)
        
        # 计算评分分布
        score_distribution = {
            '90_plus': count_90_plus,
            '80_plus': count_80_plus,
            '70_plus': count_70_plus,
            '50_plus': count_50_plus,
            'total': total_stocks,
            'avg_score': np.mean(scores) if scores else 0
        }
        
        # 识别龙头候选（90分以上）
        dragon_candidates = [s for s in stocks_data if s.get('score', 0) >= 90]
        if not dragon_candidates:
            # 如果没有90分以上，找80分以上的
            dragon_candidates = [s for s in stocks_data if s.get('score', 0) >= 80]
        
        # 按评分排序
        dragon_candidates = sorted(dragon_candidates, key=lambda x: x.get('score', 0), reverse=True)
        
        # 判断市场结构
        market_state, warning_level, message = self._classify_market_structure(
            count_90_plus, count_80_plus, total_stocks, dragon_candidates
        )
        
        self.market_state = market_state
        self.warning_level = warning_level
        self.dragon_candidates = dragon_candidates
        
        result = {
            'market_state': market_state,
            'warning_level': warning_level,
            'message': message,
            'score_distribution': score_distribution,
            'dragon_candidates': dragon_candidates[:3],  # 只返回前3个
            'timestamp': timestamp or datetime.now()
        }
        
        return result
    
    def _classify_market_structure(self,
                                   count_90_plus: int,
                                   count_80_plus: int,
                                   total_stocks: int,
                                   dragon_candidates: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        分类市场结构
        
        Args:
            count_90_plus: 90分以上股票数量
            count_80_plus: 80分以上股票数量
            total_stocks: 总股票数量
            dragon_candidates: 龙头候选列表
            
        Returns:
            (market_state, warning_level, message)
        """
        # 场景A：健康的龙头行情
        # 真龙引领：1-2个95分的真龙，其他都是40-50分的杂毛
        if count_90_plus >= 1 and count_80_plus <= 3 and total_stocks >= 10:
            dragon_score = dragon_candidates[0].get('score', 0) if dragon_candidates else 0
            if dragon_score >= 95:
                return "HEALTHY_FOCUS", "LOW", "资金聚焦龙头，众星捧月，可猛干"
            else:
                return "HEALTHY_TREND", "LOW", "趋势健康，有龙头引领"
        
        # 场景B：危险的群魔乱舞
        # 群魔乱舞：11个80分以上，但没有95分的真龙
        if count_80_plus >= 8 and count_90_plus == 0 and total_stocks >= 15:
            return "DANGEROUS_DIVERGENCE", "HIGH", "⚠️ 警告：高分标的过多且无真龙，情绪退潮信号！停止开仓！"
        
        # 场景C：平庸的扩散
        # 中等数量的高分标的，但没有明确的龙头
        if count_80_plus >= 5 and count_80_plus < 8 and count_90_plus <= 1:
            if dragon_candidates and dragon_candidates[0].get('score', 0) < 95:
                return "MEDIOCRE_DIFFUSION", "MEDIUM", "平庸扩散，资金分散，谨慎操作"
        
        # 场景D：情绪冰点
        # 没有高分标的，市场低迷
        if count_70_plus == 0:
            return "ICE_POINT", "LOW", "情绪冰点，等待机会"
        
        # 场景E：正常震荡市
        return "NORMAL", "LOW", "震荡市，正常操作"
    
    def check_circuit_breaker(self, 
                             market_structure: Dict[str, Any],
                             current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        检查是否触发熔断
        
        Args:
            market_structure: 市场结构分析结果
            current_time: 当前时间（可选）
            
        Returns:
            熔断检查结果
        """
        market_state = market_structure.get('market_state', 'UNKNOWN')
        warning_level = market_structure.get('warning_level', 'LOW')
        
        # 判断是否触发熔断
        should_break = False
        break_reason = ""
        break_action = ""
        
        if market_state == "DANGEROUS_DIVERGENCE":
            should_break = True
            break_reason = "检测到群魔乱舞，资金分散，无真龙引领"
            break_action = "STOP_ALL_OPENING"
        
        elif market_state == "MEDIOCRE_DIFFUSION":
            # 中等风险，视情况而定
            if warning_level == "MEDIUM":
                should_break = True
                break_reason = "检测到平庸扩散，资金分散"
                break_action = "REDUCE_POSITION"
        
        elif market_state == "HEALTHY_FOCUS":
            # 健康行情，不熔断
            should_break = False
            break_reason = ""
            break_action = "NORMAL_TRADING"
        
        return {
            'should_break': should_break,
            'break_reason': break_reason,
            'break_action': break_action,
            'timestamp': current_time or datetime.now()
        }
    
    def identify_dragon(self, 
                        stocks_data: List[Dict[str, Any]],
                        min_score: int = 85) -> Optional[Dict[str, Any]]:
        """
        识别真正的龙头
        
        Args:
            stocks_data: 股票数据列表
            min_score: 最低评分要求
            
        Returns:
            龙头信息，如果没有则返回 None
        """
        # 按评分排序
        sorted_stocks = sorted(stocks_data, key=lambda x: x.get('score', 0), reverse=True)
        
        # 找到第一个满足条件的龙头
        for stock in sorted_stocks:
            score = stock.get('score', 0)
            if score >= min_score:
                # 检查是否为真龙（需要满足额外条件）
                if self._is_true_dragon(stock, stocks_data):
                    return stock
        
        # 没有找到真龙
        return None
    
    def _is_true_dragon(self, 
                       stock: Dict[str, Any], 
                       all_stocks: List[Dict[str, Any]]) -> bool:
        """
        判断是否为真龙
        
        真龙标准：
        1. 评分领先（至少比第二名高10分）
        2. 涨幅领先（至少比第二名高3%）
        3. 成交额领先（至少是第二名的1.5倍）
        
        Args:
            stock: 候选股票
            all_stocks: 所有股票数据
            
        Returns:
            是否为真龙
        """
        stock_score = stock.get('score', 0)
        stock_change = stock.get('change_percent', 0)
        stock_amount = stock.get('amount', 0)
        
        # 找到第二名
        sorted_stocks = sorted(all_stocks, key=lambda x: x.get('score', 0), reverse=True)
        if len(sorted_stocks) < 2:
            return True  # 只有一只股票，默认为龙头
        
        second_best = sorted_stocks[1]
        second_score = second_best.get('score', 0)
        second_change = second_best.get('change_percent', 0)
        
        # 检查评分领先
        if stock_score - second_score < 10:
            return False
        
        # 检查涨幅领先
        if stock_change - second_change < 3:
            return False
        
        # 检查成交额领先（如果有数据）
        if stock_amount > 0 and second_best.get('amount', 0) > 0:
            if stock_amount / second_best.get('amount', 1) < 1.5:
                return False
        
        return True
    
    def get_market_summary(self, 
                         market_structure: Dict[str, Any]) -> str:
        """
        获取市场摘要
        
        Args:
            market_structure: 市场结构分析结果
            
        Returns:
            市场摘要文本
        """
        market_state = market_structure.get('market_state', 'UNKNOWN')
        warning_level = market_structure.get('warning_level', 'LOW')
        message = market_structure.get('message', '')
        score_dist = market_structure.get('score_distribution', {})
        dragons = market_structure.get('dragon_candidates', [])
        
        summary = f"""
【市场情绪监控】
市场状态: {market_state}
预警级别: {warning_level}
分析结论: {message}

【评分分布】
90分以上: {score_dist.get('90_plus', 0)} 只
80分以上: {score_dist.get('80_plus', 0)} 只
70分以上: {score_dist.get('70_plus', 0)} 只
平均评分: {score_dist.get('avg_score', 0):.1f}

【龙头候选】
"""
        
        for i, dragon in enumerate(dragons, 1):
            summary += f"{i}. {dragon.get('symbol', 'N/A')} - 评分:{dragon.get('score', 0)} 涨幅:{dragon.get('change_percent', 0):.2f}%\n"
        
        if not dragons:
            summary += "无明确龙头\n"
        
        # 添加操作建议
        if market_state == "DANGEROUS_DIVERGENCE":
            summary += "\n【操作建议】⚠️ 禁止开仓！空仓观望！"
        elif market_state == "HEALTHY_FOCUS":
            summary += "\n【操作建议】✅ 资金聚焦龙头，可猛干"
        elif market_state == "MEDIOCRE_DIFFUSION":
            summary += "\n【操作建议】⚠️ 资金分散，谨慎操作"
        else:
            summary += "\n【操作建议】正常操作"
        
        return summary


class CircuitBreaker:
    """
    熔断器
    
    用于在检测到危险信号时自动停止交易
    """
    
    def __init__(self, monitor: MarketSentimentMonitor):
        """
        初始化熔断器
        
        Args:
            monitor: 市场情绪监控器
        """
        self.monitor = monitor
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_reason = ""
        self.auto_recovery = True
        self.recovery_timeout = 300  # 5分钟后自动恢复
    
    def check_and_break(self, 
                       stocks_data: List[Dict[str, Any]],
                       force_check: bool = False) -> Dict[str, Any]:
        """
        检查并触发熔断
        
        Args:
            stocks_data: 股票数据列表
            force_check: 是否强制检查
            
        Returns:
            熔断结果
        """
        # 检查市场结构
        market_structure = self.monitor.check_market_structure(stocks_data)
        
        # 检查是否需要熔断
        breaker_result = self.monitor.check_circuit_breaker(market_structure)
        
        if breaker_result['should_break']:
            self.is_triggered = True
            self.trigger_time = datetime.now()
            self.trigger_reason = breaker_result['break_reason']
        
        # 检查是否自动恢复
        if self.is_triggered and self.auto_recovery:
            elapsed = (datetime.now() - self.trigger_time).total_seconds()
            if elapsed > self.recovery_timeout:
                self.is_triggered = False
                self.trigger_time = None
                self.trigger_reason = ""
        
        return {
            'is_triggered': self.is_triggered,
            'trigger_reason': self.trigger_reason,
            'market_structure': market_structure,
            'breaker_result': breaker_result,
            'timestamp': datetime.now()
        }
    
    def can_trade(self, symbol: Optional[str] = None) -> bool:
        """
        检查是否可以交易
        
        Args:
            symbol: 股票代码（可选）
            
        Returns:
            是否可以交易
        """
        if self.is_triggered:
            return False
        
        # 如果熔断器未触发，检查该股票是否被限制
        # 这里可以添加额外的限制逻辑
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取熔断器状态
        
        Returns:
            熔断器状态
        """
        return {
            'is_triggered': self.is_triggered,
            'trigger_time': self.trigger_time,
            'trigger_reason': self.trigger_reason,
            'auto_recovery': self.auto_recovery,
            'recovery_timeout': self.recovery_timeout,
            'elapsed_time': (datetime.now() - self.trigger_time).total_seconds() if self.trigger_time else 0
        }


# 使用示例
if __name__ == "__main__":
    # 创建监控器
    monitor = MarketSentimentMonitor()
    
    # 模拟"群魔乱舞"场景（11个80分的股票）
    stocks_data = []
    for i in range(11):
        stocks_data.append({
            'symbol': f'300{i:03d}',
            'score': 80 + np.random.randint(-2, 3),  # 78-83分
            'change_percent': 8 + np.random.uniform(-1, 2),
            'amount': 500000000 + np.random.randint(-100000000, 100000000)
        })
    
    # 添加一些低分股票
    for i in range(10):
        stocks_data.append({
            'symbol': f'600{i:03d}',
            'score': 40 + np.random.randint(-10, 10),
            'change_percent': 2 + np.random.uniform(-1, 3),
            'amount': 100000000 + np.random.randint(-50000000, 50000000)
        })
    
    # 检查市场结构
    structure = monitor.check_market_structure(stocks_data)
    
    print("="*60)
    print("市场情绪监控测试")
    print("="*60)
    
    # 打印市场摘要
    summary = monitor.get_market_summary(structure)
    print(summary)
    
    # 创建熔断器
    breaker = CircuitBreaker(monitor)
    
    # 检查并触发熔断
    breaker_result = breaker.check_and_break(stocks_data)
    
    print("\n" + "="*60)
    print("熔断器状态")
    print("="*60)
    print(f"是否触发: {'是' if breaker_result['is_triggered'] else '否'}")
    print(f"触发原因: {breaker_result['trigger_reason']}")
    print(f"市场状态: {breaker_result['market_structure']['market_state']}")
    print(f"预警级别: {breaker_result['market_structure']['warning_level']}")
    print(f"熔断动作: {breaker_result['breaker_result']['break_action']}")
    
    # 检查是否可以交易
    can_trade = breaker.can_trade()
    print(f"\n是否可以交易: {'是' if can_trade else '否'}")
    
    # 模拟"真龙引领"场景
    print("\n" + "="*60)
    print("对比：真龙引领场景")
    print("="*60)
    
    # 修改数据：1个95分的真龙，其他都是低分
    stocks_data_healthy = []
    stocks_data_healthy.append({
        'symbol': '300999',
        'score': 95,
        'change_percent': 15.0,
        'amount': 800000000
    })
    
    for i in range(10):
        stocks_data_healthy.append({
            'symbol': f'600{i:03d}',
            'score': 40 + np.random.randint(-10, 10),
            'change_percent': 2 + np.random.uniform(-1, 3),
            'amount': 100000000 + np.random.randint(-50000000, 50000000)
        })
    
    structure_healthy = monitor.check_market_structure(stocks_data_healthy)
    breaker_result_healthy = breaker.check_and_break(stocks_data_healthy)
    
    print(f"市场状态: {structure_healthy['market_state']}")
    print(f"预警级别: {structure_healthy['warning_level']}")
    print(f"分析结论: {structure_healthy['message']}")
    print(f"是否可以交易: {'是' if breaker.can_trade() else '否'}")