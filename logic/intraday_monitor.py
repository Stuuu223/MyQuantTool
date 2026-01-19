#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19 盘中动态修正模块 (Intraday Correction)

功能：
1. 执行力警报：在盘中10:30检测执行力
2. 情绪纠偏：自动降低买入阈值，逼用户出手
3. 实时监控：持续跟踪市场情绪和用户操作

Author: iFlow CLI
Version: V19
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from logic.logger import get_logger
from logic.sentiment_analyzer import SentimentAnalyzer
from logic.data_manager import DataManager
import json
import os

logger = get_logger(__name__)


class IntradayMonitor:
    """
    V19 盘中动态修正模块
    
    功能：
    1. 执行力警报：在盘中10:30检测执行力
    2. 情绪纠偏：自动降低买入阈值，逼用户出手
    3. 实时监控：持续跟踪市场情绪和用户操作
    """
    
    def __init__(self, data_manager: DataManager):
        """
        初始化盘中监控器
        
        Args:
            data_manager: 数据管理器实例
        """
        self.dm = data_manager
        self.sentiment_analyzer = SentimentAnalyzer(data_manager)
        
        # 执行力警报配置
        self.execution_alert_time = "10:30"  # 10:30触发执行力警报
        self.min_captured_dragons = 3  # 最少捕获涨停数
        self.max_allowed_misses = 0  # 最大允许漏失数
        
        # 买入阈值配置
        self.default_buy_threshold = 0.7  # 默认买入阈值（70%置信度）
        self.emergency_buy_threshold = 0.5  # 紧急买入阈值（50%置信度）
        
        # 执行力记录
        self.execution_record_file = "data/execution_record.json"
        self._init_execution_record()
    
    def _init_execution_record(self):
        """初始化执行力记录文件"""
        if not os.path.exists(self.execution_record_file):
            os.makedirs(os.path.dirname(self.execution_record_file), exist_ok=True)
            with open(self.execution_record_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "records": [],
                    "created_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=4)
    
    def check_execution_alert(self) -> Dict[str, Any]:
        """
        检查是否需要触发执行力警报
        
        逻辑：
        1. 检查当前时间是否在10:30
        2. 获取今日涨停池
        3. 获取用户今日买入记录
        4. 如果捕获了涨停但未买入，触发警报
        
        Returns:
            dict: 警报信息，包含：
                - should_alert: 是否应该触发警报
                - captured_count: 捕获的涨停数量
                - bought_count: 实际买入数量
                - missed_count: 漏失数量
                - severity: 警报严重程度（WARNING/CRITICAL）
                - message: 警报消息
                - suggested_action: 建议操作
        """
        alert_info = {
            'should_alert': False,
            'captured_count': 0,
            'bought_count': 0,
            'missed_count': 0,
            'severity': 'INFO',
            'message': '',
            'suggested_action': ''
        }
        
        try:
            # 1. 检查当前时间
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            if current_time < self.execution_alert_time:
                # 还没到10:30，不触发警报
                alert_info['message'] = f"当前时间 {current_time}，还未到执行力检查时间 {self.execution_alert_time}"
                return alert_info
            
            # 2. 获取今日涨停池
            mood = self.sentiment_analyzer.analyze_market_mood(force_refresh=True)
            
            if mood is None:
                logger.warning("⚠️ 无法获取市场情绪数据")
                return alert_info
            
            captured_count = mood.get('limit_up', 0)
            alert_info['captured_count'] = captured_count
            
            # 3. 获取用户今日买入记录（这里暂时返回空列表）
            # TODO: 实现从交易日志获取今日买入记录的逻辑
            bought_count = 0
            alert_info['bought_count'] = bought_count
            
            # 4. 计算漏失数量
            missed_count = max(0, captured_count - bought_count)
            alert_info['missed_count'] = missed_count
            
            # 5. 判断是否需要触发警报
            if captured_count >= self.min_captured_dragons and missed_count > self.max_allowed_misses:
                alert_info['should_alert'] = True
                
                # 判断严重程度
                if missed_count >= 3:
                    alert_info['severity'] = 'CRITICAL'
                    alert_info['message'] = f"🚨 执行力严重不足！系统捕获了 {captured_count} 只涨停，但你一单没开！"
                    alert_info['suggested_action'] = f"立即降低买入阈值至 {self.emergency_buy_threshold*100:.0f}%，强制出手！"
                elif missed_count >= 1:
                    alert_info['severity'] = 'WARNING'
                    alert_info['message'] = f"⚠️ 执行力不足！系统捕获了 {captured_count} 只涨停，但你只买了 {bought_count} 只。"
                    alert_info['suggested_action'] = f"建议降低买入阈值至 {(self.default_buy_threshold + self.emergency_buy_threshold)/2*100:.0f}%，提高出手频率。"
                
                # 记录执行力
                self._record_execution(captured_count, bought_count, missed_count, alert_info['severity'])
                
                logger.warning(f"🚨 执行力警报: {alert_info['message']}")
            
            return alert_info
        
        except Exception as e:
            logger.error(f"❌ 检查执行力警报失败: {e}")
            return alert_info
    
    def _record_execution(self, captured_count: int, bought_count: int, missed_count: int, severity: str):
        """
        记录执行力数据
        
        Args:
            captured_count: 捕获的涨停数量
            bought_count: 实际买入数量
            missed_count: 漏失数量
            severity: 严重程度
        """
        try:
            with open(self.execution_record_file, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
            
            # 添加新记录
            record_data['records'].append({
                'date': datetime.now().strftime("%Y%m%d"),
                'time': datetime.now().strftime("%H:%M"),
                'captured_count': captured_count,
                'bought_count': bought_count,
                'missed_count': missed_count,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            })
            
            # 保存到文件
            with open(self.execution_record_file, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ 执行力记录已保存: 捕获{captured_count}, 买入{bought_count}, 漏失{missed_count}")
        
        except Exception as e:
            logger.error(f"❌ 记录执行力数据失败: {e}")
    
    def get_execution_history(self, days: int = 7) -> List[Dict]:
        """
        获取执行力历史记录
        
        Args:
            days: 回看天数
        
        Returns:
            list: 执行力历史记录
        """
        try:
            if not os.path.exists(self.execution_record_file):
                return []
            
            with open(self.execution_record_file, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
            
            # 筛选指定天数的记录
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            filtered_records = [
                r for r in record_data['records']
                if r['date'] >= cutoff_date
            ]
            
            return filtered_records
        
        except Exception as e:
            logger.error(f"❌ 获取执行力历史失败: {e}")
            return []
    
    def get_dynamic_buy_threshold(self) -> float:
        """
        获取动态买入阈值
        
        逻辑：
        1. 检查执行力历史
        2. 如果执行力不足，自动降低阈值
        3. 返回调整后的阈值
        
        Returns:
            float: 买入阈值（0-1）
        """
        try:
            # 获取最近7天的执行力记录
            history = self.get_execution_history(days=7)
            
            if not history:
                return self.default_buy_threshold
            
            # 计算平均漏失率
            total_captured = sum(r['captured_count'] for r in history)
            total_missed = sum(r['missed_count'] for r in history)
            
            if total_captured == 0:
                return self.default_buy_threshold
            
            miss_rate = total_missed / total_captured
            
            # 根据漏失率调整阈值
            if miss_rate >= 0.7:
                # 漏失率>=70%，严重不足，大幅降低阈值
                return self.emergency_buy_threshold
            elif miss_rate >= 0.5:
                # 漏失率>=50%，不足，适度降低阈值
                return (self.default_buy_threshold + self.emergency_buy_threshold) / 2
            elif miss_rate >= 0.3:
                # 漏失率>=30%，轻微不足，小幅降低阈值
                return self.default_buy_threshold * 0.9
            else:
                # 漏失率<30%，执行力良好，保持默认阈值
                return self.default_buy_threshold
        
        except Exception as e:
            logger.error(f"❌ 获取动态买入阈值失败: {e}")
            return self.default_buy_threshold


# 单例测试
if __name__ == "__main__":
    from logic.data_manager import DataManager
    
    dm = DataManager()
    monitor = IntradayMonitor(dm)
    
    # 测试执行力警报
    print("="*60)
    print("测试执行力警报")
    print("="*60)
    alert = monitor.check_execution_alert()
    print(f"是否应该触发警报: {alert['should_alert']}")
    print(f"捕获涨停数: {alert['captured_count']}")
    print(f"实际买入数: {alert['bought_count']}")
    print(f"漏失数量: {alert['missed_count']}")
    print(f"严重程度: {alert['severity']}")
    print(f"警报消息: {alert['message']}")
    print(f"建议操作: {alert['suggested_action']}")
    
    # 测试动态买入阈值
    print("\n" + "="*60)
    print("测试动态买入阈值")
    print("="*60)
    threshold = monitor.get_dynamic_buy_threshold()
    print(f"当前买入阈值: {threshold*100:.0f}%")
    
    # 测试执行力历史
    print("\n" + "="*60)
    print("测试执行力历史")
    print("="*60)
    history = monitor.get_execution_history(days=7)
    print(f"执行力记录数: {len(history)}")
    for i, record in enumerate(history):
        print(f"  {i+1}. {record['date']} {record['time']}: 捕获{record['captured_count']}, 买入{record['bought_count']}, 漏失{record['missed_count']}")