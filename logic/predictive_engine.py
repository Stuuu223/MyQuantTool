#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V12 核心组件：预测引擎 (Predictive Engine)
基于历史复盘数据计算概率模型
"""

import pandas as pd
import json
from logic.database_manager import get_db_manager
from logic.logger import get_logger

logger = get_logger(__name__)


class PredictiveEngine:
    """
    V12 核心组件：预测引擎
    基于历史复盘数据计算概率模型
    """
    
    def __init__(self):
        self.db = get_db_manager()
    
    def get_promotion_probability(self, current_height: int) -> float:
        """
        计算连板晋级概率
        
        逻辑：统计历史数据中，当最高板达到 N 时，次日出现 N+1 的次数
        
        Args:
            current_height: 当前连板高度（如 5 表示 5 板）
        
        Returns:
            float: 晋级成功率（百分比，如 45.5 表示 45.5%）
        """
        try:
            # 1. 获取历史最高板序列
            sql = "SELECT highest_board FROM market_summary ORDER BY date DESC LIMIT 60"
            results = self.db.sqlite_query(sql)
            
            if len(results) < 10:
                logger.warning(f"⚠️ 样本不足（{len(results)}天），返回盲区状态")
                return -1.0  # 样本不足，返回盲区状态
                
            boards = [r[0] for r in results]
            boards.reverse()  # 转为正序
            
            # 2. 统计当前高度晋级的次数
            total_cases = 0
            success_cases = 0
            
            for i in range(len(boards) - 1):
                if boards[i] == current_height:
                    total_cases += 1
                    if boards[i+1] > current_height:
                        success_cases += 1
            
            if total_cases == 0:
                logger.info(f"📊 历史回测：{current_height}板 无历史记录，返回 0%")
                return 0.0
                
            prob = (success_cases / total_cases) * 100
            logger.info(f"📊 历史回测：{current_height}板 晋级成功率为 {prob:.2f}% (样本数: {total_cases})")
            return round(prob, 2)
            
        except Exception as e:
            logger.error(f"计算晋级概率失败: {e}")
            return 0.0
    
    def detect_sentiment_pivot(self) -> dict:
        """
        检测情绪转折点 (防守雷达)
        
        逻辑：昨日溢价连降 + 最高板降低 = 触发强力防守
        
        Returns:
            dict: {
                'action': 'DEFENSE' | 'NORMAL' | 'HOLD',
                'reason': 触发原因
            }
        """
        try:
            # 获取最近3天的复盘记录
            sql = "SELECT highest_board, date FROM market_summary ORDER BY date DESC LIMIT 3"
            results = self.db.sqlite_query(sql)
            
            if len(results) < 3:
                return {"action": "HOLD", "reason": "样本不足"}
            
            # 这里简化逻辑，实际溢价率需要结合实时计算
            # 假设我们只根据最高板高度判定
            h3, h2, h1 = results[0][0], results[1][0], results[2][0]
            
            if h1 < h2 < h3:  # 最高板高度逐日下降
                logger.warning("🚨 警报：市场高度持续坍塌，触发强力防守指令！")
                return {"action": "DEFENSE", "reason": "市场高度连降，情绪退潮期"}
                
            return {"action": "NORMAL", "reason": "情绪稳定"}
            
        except Exception as e:
            logger.error(f"情绪转折检测失败: {e}")
            return {"action": "HOLD", "reason": "检测异常"}
    
    def get_sector_loyalty(self, sector_name: str) -> dict:
        """
        [V13 预研] 获取板块忠诚度（持续性）
        
        逻辑：查找该板块过去出现在 top_sectors 的记录，看次日市场溢价
        
        Args:
            sector_name: 板块名称（如"人工智能"、"新能源"）
        
        Returns:
            dict: {
                'sector': 板块名称,
                'loyalty_score': 忠诚度评分 (0-100),
                'appearance_count': 出现次数,
                'avg_next_day_profit': 次日平均溢价,
                'status': '真命天子' | '短命渣男' | '数据积累中...'
            }
        """
        try:
            # 获取最近 60 天的复盘记录
            sql = "SELECT date, top_sectors, highest_board FROM market_summary ORDER BY date DESC LIMIT 60"
            results = self.db.sqlite_query(sql)
            
            if len(results) < 3:
                return {
                    "sector": sector_name,
                    "loyalty_score": "数据积累中...",
                    "appearance_count": 0,
                    "avg_next_day_profit": 0,
                    "status": "数据积累中..."
                }
            
            # 统计该板块的出现次数和次日表现
            appearance_count = 0
            next_day_profits = []
            
            for i in range(len(results) - 1):
                date, top_sectors_json, highest_board = results[i]
                
                # 解析 top_sectors
                try:
                    top_sectors = json.loads(top_sectors_json) if top_sectors_json else []
                except:
                    top_sectors = []
                
                # 检查该板块是否在当日 top_sectors 中
                if sector_name in top_sectors:
                    appearance_count += 1
                    
                    # 获取次日最高板变化（作为次日表现的代理指标）
                    if i + 1 < len(results):
                        next_day_highest_board = results[i + 1][2]
                        # 计算次日最高板变化（正数表示次日高度更高，情绪更好）
                        profit = next_day_highest_board - highest_board
                        next_day_profits.append(profit)
            
            if appearance_count == 0:
                return {
                    "sector": sector_name,
                    "loyalty_score": 0,
                    "appearance_count": 0,
                    "avg_next_day_profit": 0,
                    "status": "无记录"
                }
            
            # 计算平均次日表现
            avg_next_day_profit = sum(next_day_profits) / len(next_day_profits) if next_day_profits else 0
            
            # 计算忠诚度评分（基于出现次数和次日表现）
            # 出现次数越多、次日表现越好，忠诚度越高
            loyalty_score = min(100, (appearance_count * 10) + (avg_next_day_profit * 20))
            
            # 判断板块类型
            if loyalty_score >= 70:
                status = "真命天子"
            elif loyalty_score >= 40:
                status = "一般"
            else:
                status = "短命渣男"
            
            logger.info(f"📊 板块忠诚度分析: {sector_name} - 评分: {loyalty_score:.1f}, 状态: {status}")
            
            return {
                "sector": sector_name,
                "loyalty_score": round(loyalty_score, 2),
                "appearance_count": appearance_count,
                "avg_next_day_profit": round(avg_next_day_profit, 2),
                "status": status
            }
            
        except Exception as e:
            logger.error(f"获取板块忠诚度失败: {e}")
            return {
                "sector": sector_name,
                "loyalty_score": 0,
                "appearance_count": 0,
                "avg_next_day_profit": 0,
                "status": "计算异常"
            }


# 单例测试
if __name__ == "__main__":
    pe = PredictiveEngine()
    print(f"5板晋级6板概率: {pe.get_promotion_probability(5)}%")
    print(f"情绪转折点检测: {pe.detect_sentiment_pivot()}")
    print(f"板块忠诚度测试: {pe.get_sector_loyalty('人工智能')}")