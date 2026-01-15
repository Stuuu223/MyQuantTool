"""
🦖 V9.0 游资掠食者系统 (The Predator System)

核心理念：只杀硬伤，不听故事
- 生死红线：退市风险、*ST一律死刑
- 身份与涨幅错配：创业板10%不算涨停
- 资金结构恶化：主力出逃+融资接盘=出货盘口
- 半路板战法：针对创业板12%-15%博弈区间
"""

import re
from typing import Dict, Any, Tuple, Optional
from logic.logger import get_logger

logger = get_logger(__name__)


class PredatorSystem:
    """游资掠食者系统 - V9.0"""
    
    def __init__(self):
        """初始化游资掠食者系统"""
        self.kill_switch_keywords = [
            '退市风险', '退市', 'ST', '*ST', '终止上市', 
            '暂停上市', '强制退市', '财务退市', '面值退市'
        ]
        
        # 半路板战法配置
        self.halfway_config = {
            'main_board': {  # 主板（60/00）
                'limit_up': 10.0,
                'halfway_min': 5.0,
                'halfway_max': 8.0,
            },
            'chi_next': {  # 创业板（300/301）
                'limit_up': 20.0,
                'halfway_min': 12.0,
                'halfway_max': 15.0,
            },
            'star_market': {  # 科创板（688）
                'limit_up': 20.0,
                'halfway_min': 12.0,
                'halfway_max': 15.0,
            },
            'beijing': {  # 北交所（8/4）
                'limit_up': 30.0,
                'halfway_min': 18.0,
                'halfway_max': 22.0,
            }
        }
    
    def analyze_stock(self, stock_data: Dict[str, Any], 
                     realtime_data: Optional[Dict[str, Any]] = None,
                     fund_flow: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析单只股票
        
        Args:
            stock_data: 股票基本信息
            realtime_data: 实时行情数据
            fund_flow: 资金流向数据
        
        Returns:
            分析结果字典
        """
        result = {
            'symbol': stock_data.get('symbol', ''),
            'name': stock_data.get('name', ''),
            'score': 0,
            'role': '未知',
            'signal': 'HOLD',
            'confidence': 'LOW',
            'reason': '',
            'suggested_position': 0.0,
            'warning': '',
            'checks': {}
        }
        
        # Step 1: 生死红线检测（Kill Switch）
        kill_switch_result = self.check_kill_switch(stock_data)
        result['checks']['kill_switch'] = kill_switch_result
        
        if kill_switch_result['triggered']:
            result['score'] = 0
            result['role'] = '死刑'
            result['signal'] = 'SELL'
            result['confidence'] = 'HIGH'
            result['reason'] = kill_switch_result['reason']
            result['warning'] = '生死红线：退市风险/ST预警'
            return result
        
        # Step 2: 身份与涨幅错配检测
        identity_result = self.check_identity_mismatch(stock_data, realtime_data)
        result['checks']['identity_mismatch'] = identity_result
        
        if identity_result['triggered']:
            result['score'] = 0
            result['role'] = '陷阱'
            result['signal'] = 'SELL'
            result['confidence'] = 'HIGH'
            result['reason'] = identity_result['reason']
            result['warning'] = identity_result['warning']
            return result
        
        # Step 3: 资金结构恶化检测
        if fund_flow:
            structure_result = self.check_fund_structure(fund_flow)
            result['checks']['fund_structure'] = structure_result
            
            if structure_result['triggered']:
                result['score'] = 0
                result['role'] = '出货'
                result['signal'] = 'SELL'
                result['confidence'] = 'HIGH'
                result['reason'] = structure_result['reason']
                result['warning'] = structure_result['warning']
                return result
        
        # Step 4: 半路板战法分析
        if realtime_data:
            halfway_result = self.analyze_halfway_strategy(stock_data, realtime_data)
            result['checks']['halfway_strategy'] = halfway_result
            
            if halfway_result['triggered']:
                result['score'] = halfway_result['score']
                result['role'] = halfway_result['role']
                result['signal'] = halfway_result['signal']
                result['confidence'] = halfway_result['confidence']
                result['reason'] = halfway_result['reason']
                result['suggested_position'] = halfway_result['suggested_position']
            else:
                result['score'] = 0
                result['role'] = '观望'
                result['signal'] = 'HOLD'
                result['reason'] = '不符合半路板战法条件'
        
        return result
    
    def check_kill_switch(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生死红线检测（Kill Switch）
        
        凡是涉及退市风险、*ST的标的，无论K线多美，一律判死刑
        """
        result = {
            'triggered': False,
            'reason': '',
            'keywords': []
        }
        
        # 检查股票名称
        name = stock_data.get('name', '')
        for keyword in self.kill_switch_keywords:
            if keyword in name:
                result['triggered'] = True
                result['keywords'].append(keyword)
        
        # 检查股票代码（ST股票代码特殊）
        symbol = stock_data.get('symbol', '')
        if symbol.startswith('ST') or '*ST' in symbol:
            result['triggered'] = True
            result['keywords'].append('ST标识')
        
        # 检查备注信息
        remark = stock_data.get('remark', '')
        for keyword in self.kill_switch_keywords:
            if keyword in remark:
                result['triggered'] = True
                result['keywords'].append(keyword)
        
        if result['triggered']:
            result['reason'] = f"触发生死红线：检测到关键词 {result['keywords']}"
            logger.warning(f"生死红线触发：{symbol} {name} - {result['keywords']}")
        
        return result
    
    def check_identity_mismatch(self, stock_data: Dict[str, Any], 
                               realtime_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        身份与涨幅错配检测
        
        300/301开头股票，涨幅<19.5%不算涨停
        """
        result = {
            'triggered': False,
            'reason': '',
            'warning': ''
        }
        
        if not realtime_data:
            return result
        
        symbol = stock_data.get('symbol', '')
        change_pct = realtime_data.get('change_percent', 0)
        
        # 判断板块类型
        board_type = self._get_board_type(symbol)
        config = self.halfway_config.get(board_type, {})
        
        if not config:
            return result
        
        limit_up = config['limit_up']
        
        # 检查涨幅错配
        if board_type in ['chi_next', 'star_market']:
            # 创业板/科创板：20cm涨停
            if change_pct < 19.5 and change_pct > 10.0:
                result['triggered'] = True
                result['reason'] = f"{board_type}股票涨幅{change_pct:.2f}%非涨停，属于冲高回落或跟风上涨"
                result['warning'] = f"{board_type}股票涨幅<19.5%不算涨停，无溢价预期"
                logger.warning(f"身份与涨幅错配：{symbol} - {board_type}股票涨幅{change_pct:.2f}%")
        elif board_type == 'beijing':
            # 北交所：30cm涨停
            if change_pct < 29.5 and change_pct > 15.0:
                result['triggered'] = True
                result['reason'] = f"{board_type}股票涨幅{change_pct:.2f}%非涨停，属于冲高回落或跟风上涨"
                result['warning'] = f"{board_type}股票涨幅<29.5%不算涨停，无溢价预期"
                logger.warning(f"身份与涨幅错配：{symbol} - {board_type}股票涨幅{change_pct:.2f}%")
        
        return result
    
    def check_fund_structure(self, fund_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        资金结构恶化检测
        
        主力净流出+融资买入增加=出货盘口
        """
        result = {
            'triggered': False,
            'reason': '',
            'warning': ''
        }
        
        # 获取资金流向数据
        main_net_outflow = fund_flow.get('main_net_outflow', 0)  # 主力净流出
        financing_buy = fund_flow.get('financing_buy', 0)  # 融资买入
        
        # 检测资金结构恶化
        if main_net_outflow > 50000000 and financing_buy > 30000000:  # 主力流出>5000万，融资买入>3000万
            result['triggered'] = True
            result['reason'] = f"资金结构恶化：主力净流出{main_net_outflow/10000:.0f}万，融资买入{financing_buy/10000:.0f}万，典型的出货盘口"
            result['warning'] = "主力出逃，融资接盘，背离信号"
            logger.warning(f"资金结构恶化：主力净流出{main_net_outflow}，融资买入{financing_buy}")
        
        return result
    
    def analyze_halfway_strategy(self, stock_data: Dict[str, Any], 
                                realtime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        半路板战法分析
        
        针对创业板12%-15%博弈区间
        """
        result = {
            'triggered': False,
            'score': 0,
            'role': '',
            'signal': 'HOLD',
            'confidence': 'LOW',
            'reason': '',
            'suggested_position': 0.0
        }
        
        symbol = stock_data.get('symbol', '')
        change_pct = realtime_data.get('change_percent', 0)
        volume_ratio = realtime_data.get('volume_ratio', 1)
        turnover_rate = realtime_data.get('turnover_rate', 0)
        
        # 判断板块类型
        board_type = self._get_board_type(symbol)
        config = self.halfway_config.get(board_type, {})
        
        if not config:
            return result
        
        halfway_min = config['halfway_min']
        halfway_max = config['halfway_max']
        
        # 检查是否符合半路板条件
        if halfway_min <= change_pct <= halfway_max:
            result['triggered'] = True
            
            # 计算评分
            score = 60  # 基础分
            
            # 涨幅评分（越接近涨停板越好）
            if change_pct >= halfway_max:
                score += 20
            elif change_pct >= (halfway_min + halfway_max) / 2:
                score += 15
            else:
                score += 10
            
            # 量比评分
            if volume_ratio > 3:
                score += 15
            elif volume_ratio > 2:
                score += 10
            elif volume_ratio > 1.5:
                score += 5
            
            # 换手率评分
            if 5 <= turnover_rate <= 15:
                score += 10
            elif turnover_rate > 15:
                score += 5
            
            # 判断角色和信号
            if score >= 90:
                result['role'] = '🔥 强半路板'
                result['signal'] = 'BUY'
                result['confidence'] = 'HIGH'
                result['suggested_position'] = 0.3  # 建议仓位30%
            elif score >= 80:
                result['role'] = '📈 半路板'
                result['signal'] = 'BUY'
                result['confidence'] = 'MEDIUM'
                result['suggested_position'] = 0.2  # 建议仓位20%
            else:
                result['role'] = '弱半路板'
                result['signal'] = 'WATCH'
                result['confidence'] = 'LOW'
                result['suggested_position'] = 0.0
            
            result['score'] = score
            result['reason'] = f"半路板战法：涨幅{change_pct:.2f}%在{halfway_min}%-{halfway_max}%区间，量比{volume_ratio:.2f}，换手率{turnover_rate:.2f}%"
            logger.info(f"半路板战法：{symbol} - 涨幅{change_pct:.2f}%，评分{score}")
        else:
            result['reason'] = f"涨幅{change_pct:.2f}%不在半路板区间{halfway_min}%-{halfway_max}%"
        
        return result
    
    def _get_board_type(self, symbol: str) -> str:
        """
        根据股票代码判断板块类型
        
        Args:
            symbol: 股票代码
        
        Returns:
            板块类型
        """
        if symbol.startswith('688'):
            return 'star_market'  # 科创板
        elif symbol.startswith('301') or symbol.startswith('303'):
            return 'chi_next'  # 创业板
        elif symbol.startswith('300'):
            return 'chi_next'  # 创业板
        elif symbol.startswith('8') or symbol.startswith('4'):
            return 'beijing'  # 北交所
        elif symbol.startswith('6'):
            return 'main_board'  # 主板（沪市）
        else:
            return 'main_board'  # 主板（深市）
    
    def batch_analyze(self, stocks_data: Dict[str, Dict[str, Any]],
                     realtime_data: Dict[str, Dict[str, Any]],
                     fund_flow_data: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """
        批量分析股票
        
        Args:
            stocks_data: 股票基本信息字典
            realtime_data: 实时行情数据字典
            fund_flow_data: 资金流向数据字典
        
        Returns:
            分析结果字典
        """
        results = {}
        
        for symbol, stock_info in stocks_data.items():
            realtime = realtime_data.get(symbol, {})
            fund_flow = fund_flow_data.get(symbol) if fund_flow_data else None
            
            result = self.analyze_stock(stock_info, realtime, fund_flow)
            results[symbol] = result
        
        return results