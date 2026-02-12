#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 AutoReviewer - 智能复盘系统 (Mirror of Truth)

功能：
1. 返回结构化数据供 UI 调用
2. 分析错失的机会和避开的陷阱
3. 生成每日复盘报告

使用：
每天15:30收盘后运行，生成《每日异常交易报告》
"""

import pandas as pd
import datetime
from typing import Dict, List
from logic.data_manager import DataManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class AutoReviewerV18_7:
    """
    V18.7 智能复盘系统
    """
    
    def __init__(self):
        """初始化"""
        self.data_manager = DataManager()
        logger.info("✅ V18.7 智能复盘系统初始化完成")
    
    def generate_report_data(self, date_str: str = None) -> Dict:
        """
        生成结构化的复盘数据，供 UI 调用
        
        Args:
            date_str: 日期字符串，格式 YYYYMMDD，默认为今天
        
        Returns:
            dict: 复盘数据，包含：
                - summary: 摘要信息
                - missed_opportunities: 错失的机会
                - avoided_traps: 避开的陷阱
                - execution_score: 执行力评分
        """
        if date_str is None:
            date_str = datetime.datetime.now().strftime("%Y%m%d")
        
        logger.info(f"🔍 正在复盘日期: {date_str}")
        
        try:
            # 1. 获取当日涨停数据（使用 akshare）
            import akshare as ak
            df_zt = ak.stock_zt_pool_em(date=date_str)
            
            if df_zt is None or df_zt.empty:
                logger.warning(f"⚠️ {date_str} 没有涨停数据，可能是休市或数据未更新")
                return self._get_empty_report(date_str)
            
            total_limit_up = len(df_zt)
            
            # 2. 获取市场温度（根据涨停数量）
            market_temperature = self._calculate_market_temperature(total_limit_up)
            
            # 3. 获取历史信号数据
            missed_opportunities = self._get_missed_opportunities(date_str, df_zt)
            avoided_traps = self._get_avoided_traps(date_str)
            
            # 4. 计算执行力评分
            execution_score = self._calculate_execution_score(
                total_limit_up, 
                len(missed_opportunities), 
                len(avoided_traps)
            )
            
            # 5. 计算系统捕获率
            system_capture_rate = self._calculate_system_capture_rate(
                total_limit_up, 
                len(missed_opportunities)
            )
            
            review_data = {
                "summary": {
                    "date": date_str,
                    "total_limit_up": total_limit_up,
                    "market_temperature": market_temperature,
                    "system_capture_rate": system_capture_rate
                },
                "missed_opportunities": missed_opportunities,
                "avoided_traps": avoided_traps,
                "execution_score": execution_score
            }
            
            logger.info(f"✅ 复盘完成: {date_str}, 涨停{total_limit_up}只, 错失{len(missed_opportunities)}只, 避开{len(avoided_traps)}只")
            
            return review_data
            
        except Exception as e:
            logger.error(f"❌ 复盘失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_report(date_str)
    
    def _get_empty_report(self, date_str: str) -> Dict:
        """获取空报告（当数据不可用时）"""
        return {
            "summary": {
                "date": date_str,
                "total_limit_up": 0,
                "market_temperature": "❓ 数据不可用",
                "system_capture_rate": "N/A"
            },
            "missed_opportunities": [],
            "avoided_traps": [],
            "execution_score": 0
        }
    
    def _calculate_market_temperature(self, total_limit_up: int) -> str:
        """计算市场温度"""
        if total_limit_up >= 100:
            return "🔥 沸腾"
        elif total_limit_up >= 50:
            return "🌡️ 炙热"
        elif total_limit_up >= 20:
            return "🌤️ 温和"
        elif total_limit_up >= 10:
            return "❄️ 寒冷"
        else:
            return "🧊 冰点"
    
    def _get_missed_opportunities(self, date_str: str, df_zt: pd.DataFrame) -> List[Dict]:
        """获取错失的机会"""
        missed_opportunities = []
        
        try:
            # 这里可以接入你的历史信号系统
            # 暂时返回空列表，后续可以接入真实的信号历史
            # TODO: 从 signal_history 获取历史信号，对比涨停板
            
            # 示例数据（实际使用时应该从真实数据源获取）
            if not df_zt.empty:
                # 取前3只涨停板作为示例
                for idx, row in df_zt.head(3).iterrows():
                    missed_opportunities.append({
                        "code": row['代码'],
                        "name": row['名称'],
                        "reason": "需要接入信号历史系统",
                        "growth": f"{row['涨跌幅']:.2f}%",
                        "limit_up_count": row.get('连板数', 1)
                    })
            
        except Exception as e:
            logger.error(f"获取错失机会失败: {e}")
        
        return missed_opportunities
    
    def _get_avoided_traps(self, date_str: str) -> List[Dict]:
        """获取避开的陷阱"""
        avoided_traps = []
        
        try:
            # 这里可以接入你的风控系统
            # 暂时返回空列表，后续可以接入真实的风控历史
            # TODO: 从风控系统获取被拦截的股票
            
            # 示例数据（实际使用时应该从真实数据源获取）
            # avoided_traps = [
            #     {"code": "300711", "name": "广哈通信", "risk_msg": "DDE大幅流出", "drop": "-5.4%"}
            # ]
            pass
            
        except Exception as e:
            logger.error(f"获取避开陷阱失败: {e}")
        
        return avoided_traps
    
    def _calculate_execution_score(self, total_limit_up: int, missed_count: int, avoided_count: int) -> int:
        """计算执行力评分"""
        # 基础分：60分
        score = 60
        
        # 错失惩罚：每错失一只扣5分
        score -= missed_count * 5
        
        # 避开奖励：每避开一只加10分
        score += avoided_count * 10
        
        # 市场环境加成：涨停越多，难度越大，给适当加成
        if total_limit_up >= 50:
            score += 10
        elif total_limit_up >= 20:
            score += 5
        
        # 限制分数范围：0-100
        score = max(0, min(100, score))
        
        return score
    
    def _calculate_system_capture_rate(self, total_limit_up: int, missed_count: int) -> str:
        """计算系统捕获率"""
        if total_limit_up == 0:
            return "N/A"
        
        captured = total_limit_up - missed_count
        capture_rate = (captured / total_limit_up) * 100
        
        return f"{capture_rate:.1f}%"


# 单例模式
_instance = None

def get_auto_reviewer_v18_7() -> AutoReviewerV18_7:
    """获取 V18.7 智能复盘系统单例"""
    global _instance
    
    if _instance is None:
        _instance = AutoReviewerV18_7()
    
    return _instance