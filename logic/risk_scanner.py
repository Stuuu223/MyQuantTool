"""
个股风险扫描器 (Risk Scanner)
V10.1.8 - Prey Alert System (猎物预警系统)

识别游资收割"小白"的三大经典套路：
1. 开盘核按钮预警 (The Opening Guillotine)
2. 纸老虎封单预警 (The Hollow Board)
3. 尾盘偷袭预警 (The Late Sneak)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, time

logger = logging.getLogger(__name__)


class RiskScanner:
    """
    个股风险扫描器
    
    功能：
    1. 扫描个股是否存在危险信号
    2. 识别游资收割套路
    3. 生成风险预警报告
    """
    
    def __init__(self):
        self.risk_warnings = []
    
    def scan_stock_risk(self, stock_data: Dict) -> Dict:
        """
        扫描单只股票的风险
        
        Args:
            stock_data: 股票数据字典，必须包含以下字段：
                - name: 股票名称
                - code: 股票代码
                - open_pct: 开盘涨幅 (%)
                - pct: 当前涨幅 (%)
                - turnover: 成交额
                - bid_amount: 封单金额 (如果有)
                - is_limit_up: 是否涨停
                - timestamp: 时间戳
        
        Returns:
            dict: 风险扫描结果
                - risk_level: 风险等级 (无/低/中/高/极高)
                - warnings: 预警列表
                - advice: 操作建议
        """
        warnings = []
        risk_level = "无"
        
        try:
            # 1. 开盘核按钮预警 (The Opening Guillotine)
            opening_warning = self._check_opening_guillotine(stock_data)
            if opening_warning:
                warnings.append(opening_warning)
                risk_level = "极高"
            
            # 2. 纸老虎封单预警 (The Hollow Board)
            hollow_warning = self._check_hollow_board(stock_data)
            if hollow_warning:
                warnings.append(hollow_warning)
                if risk_level != "极高":
                    risk_level = "高"
            
            # 3. 尾盘偷袭预警 (The Late Sneak)
            sneak_warning = self._check_late_sneak(stock_data)
            if sneak_warning:
                warnings.append(sneak_warning)
                if risk_level in ["无", "低"]:
                    risk_level = "中"
            
            # 生成操作建议
            advice = self._generate_advice(warnings, risk_level)
            
            return {
                'risk_level': risk_level,
                'warnings': warnings,
                'advice': advice
            }
        
        except Exception as e:
            logger.error(f"扫描股票风险失败: {e}")
            return {
                'risk_level': '未知',
                'warnings': [],
                'advice': '风险扫描失败，请谨慎操作'
            }
    
    def _check_opening_guillotine(self, stock_data: Dict) -> Optional[str]:
        """
        检查开盘核按钮 (The Opening Guillotine)
        
        逻辑：防止"不及预期"的硬接飞刀
        场景：高开但开盘后直线跳水（跌破开盘价）
        
        Args:
            stock_data: 股票数据
        
        Returns:
            str: 预警信息，如果没有风险则返回 None
        """
        try:
            open_pct = stock_data.get('open_pct', 0)
            current_pct = stock_data.get('pct', 0)
            
            # 判断条件：高开 > 5% 且 当前涨幅 < (开盘涨幅 - 3%)
            # 即：高开 8%，但现在已经跌到 5% 以下
            if open_pct > 5.0 and current_pct < (open_pct - 3.0):
                drop_amount = open_pct - current_pct
                return f"☠️ 开盘瀑布杀：高开 {open_pct:.1f}% 后跳水 {drop_amount:.1f}%，主力出货，严禁接飞刀！"
            
            return None
        
        except Exception as e:
            logger.warning(f"检查开盘核按钮失败: {e}")
            return None
    
    def _check_hollow_board(self, stock_data: Dict) -> Optional[str]:
        """
        检查纸老虎封单 (The Hollow Board)
        
        逻辑：识别"虚假强势"
        场景：涨停了但封单金额极弱（不足成交额的 2%）
        
        Args:
            stock_data: 股票数据
        
        Returns:
            str: 预警信息，如果没有风险则返回 None
        """
        try:
            pct = stock_data.get('pct', 0)
            turnover = stock_data.get('turnover', 0)
            bid_amount = stock_data.get('bid_amount', 0)
            
            # 判断条件：涨停 且 封单不足成交额的 2%
            if pct > 9.8 and turnover > 0:
                seal_ratio = bid_amount / turnover
                if seal_ratio < 0.02:
                    return f"👻 纸老虎：封单仅占成交额 {seal_ratio*100:.1f}%，随时炸板，撤单保平安！"
            
            return None
        
        except Exception as e:
            logger.warning(f"检查纸老虎封单失败: {e}")
            return None
    
    def _check_late_sneak(self, stock_data: Dict) -> Optional[str]:
        """
        检查尾盘偷袭 (The Late Sneak)
        
        逻辑：所有的尾盘偷袭，非奸即盗
        场景：全天弱势但在 14:40 后突然直线拉涨停
        
        Args:
            stock_data: 股票数据
        
        Returns:
            str: 预警信息，如果没有风险则返回 None
        """
        try:
            pct = stock_data.get('pct', 0)
            timestamp = stock_data.get('timestamp')
            
            # 判断条件：当前时间 > 14:40 且 涨停 且 全天平均涨幅 < 3%
            if timestamp:
                try:
                    current_time = datetime.fromtimestamp(timestamp).time()
                    if current_time > time(14, 40):
                        if pct > 9.8:
                            # 假设 stock_data 中有 average_pct_before_1430 字段
                            avg_pct = stock_data.get('average_pct_before_1430', 0)
                            if avg_pct < 3.0:
                                return f"🦊 尾盘偷袭：全天弱势（{avg_pct:.1f}%）尾盘强拉，非奸即盗，明日大概率低开。"
                except Exception as e:
                    logger.warning(f"解析时间戳失败: {e}")
            
            return None
        
        except Exception as e:
            logger.warning(f"检查尾盘偷袭失败: {e}")
            return None
    
    def _generate_advice(self, warnings: List[str], risk_level: str) -> str:
        """
        生成操作建议
        
        Args:
            warnings: 预警列表
            risk_level: 风险等级
        
        Returns:
            str: 操作建议
        """
        if not warnings:
            return "✅ 未检测到明显风险信号，可正常操作"
        
        if risk_level == "极高":
            return "🚫 极度危险！立即撤单，严禁买入！"
        elif risk_level == "高":
            return "⚠️ 高风险！建议减仓或观望，不要追高"
        elif risk_level == "中":
            return "⚡ 中风险！谨慎操作，控制仓位"
        else:
            return "风险提示：请结合盘感判断"
    
    def batch_scan_stocks(self, stock_list: List[Dict]) -> Dict[str, Dict]:
        """
        批量扫描股票风险
        
        Args:
            stock_list: 股票数据列表
        
        Returns:
            dict: {股票代码: 风险扫描结果}
        """
        results = {}
        
        for stock in stock_list:
            code = stock.get('code', '')
            if code:
                results[code] = self.scan_stock_risk(stock)
        
        return results