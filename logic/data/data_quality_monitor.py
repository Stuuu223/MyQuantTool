"""
数据质量监控器：数据质量实时监控

功能：
- 异常数据检测
- 数据延迟预警
- 数据完整性检查
- API 接口状态监控
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import time
import requests
from urllib.parse import urlparse
import warnings

logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """数据质量报告数据类"""
    check_time: str
    data_source: str
    completeness: float  # 完整性 0-1
    accuracy: float      # 准确性 0-1
    consistency: float   # 一致性 0-1
    timeliness: float    # 及时性 0-1
    overall_score: float # 总体评分 0-1
    issues: List[str]    # 发现的问题
    recommendations: List[str]  # 改进建议
    quality_level: str   # 质量等级: '优秀', '良好', '一般', '较差', '很差'


class DataQualityMonitor:
    """数据质量监控器"""

    def __init__(self, threshold_config: Dict[str, float] = None):
        """
        初始化数据质量监控器

        Args:
            threshold_config: 阈值配置字典
        """
        # 默认阈值配置
        self.threshold_config = threshold_config or {
            'completeness': 0.85,    # 完整性阈值
            'accuracy': 0.90,        # 准确性阈值
            'consistency': 0.88,     # 一致性阈值
            'timeliness': 0.95       # 及时性阈值
        }

        self.monitoring_history = []
        self.api_status = {}

    def check_data_quality(self, data: pd.DataFrame, data_source: str = "Unknown") -> DataQualityReport:
        """
        检查数据质量

        Args:
            data: 待检查的数据
            data_source: 数据来源

        Returns:
            DataQualityReport: 数据质量报告
        """
        if data is None or data.empty:
            return self._get_empty_data_report(data_source)

        # 计算各项质量指标
        completeness = self._check_completeness(data)
        accuracy = self._check_accuracy(data)
        consistency = self._check_consistency(data)
        timeliness = self._check_timeliness(data)

        # 计算总体评分（加权平均）
        overall_score = (completeness * 0.3 + accuracy * 0.3 + consistency * 0.2 + timeliness * 0.2)

        # 检测问题
        issues = self._detect_issues(data, completeness, accuracy, consistency, timeliness)

        # 生成建议
        recommendations = self._generate_recommendations(issues)

        # 确定质量等级
        if overall_score >= 0.9:
            quality_level = '优秀'
        elif overall_score >= 0.8:
            quality_level = '良好'
        elif overall_score >= 0.7:
            quality_level = '一般'
        elif overall_score >= 0.6:
            quality_level = '较差'
        else:
            quality_level = '很差'

        report = DataQualityReport(
            check_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data_source=data_source,
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            overall_score=overall_score,
            issues=issues,
            recommendations=recommendations,
            quality_level=quality_level
        )

        # 记录监控历史
        self.monitoring_history.append(report)

        return report

    def _check_completeness(self, data: pd.DataFrame) -> float:
        """检查数据完整性"""
        if data.empty:
            return 0.0

        # 计算缺失值比例
        total_values = data.size
        missing_values = data.isnull().sum().sum()
        completeness_ratio = 1 - (missing_values / total_values) if total_values > 0 else 1.0

        # 确保在0-1范围内
        return max(0.0, min(completeness_ratio, 1.0))

    def _check_accuracy(self, data: pd.DataFrame) -> float:
        """检查数据准确性（检测异常值）"""
        if data.empty:
            return 0.0

        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            return 0.8  # 没有数值列时返回中等准确性

        outliers_count = 0
        total_numeric_values = 0

        for col in numeric_columns:
            series = data[col].dropna()
            if len(series) < 3:  # 需要至少3个值才能计算统计量
                continue

            total_numeric_values += len(series)

            # 使用IQR方法检测异常值
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            outliers_count += len(outliers)

        # 准确性 = 1 - 异常值比例
        accuracy = 1 - (outliers_count / total_numeric_values) if total_numeric_values > 0 else 1.0
        return max(0.0, min(accuracy, 1.0))

    def _check_consistency(self, data: pd.DataFrame) -> float:
        """检查数据一致性（检测重复值和逻辑错误）"""
        if data.empty:
            return 0.0

        issues_count = 0
        total_checks = 0

        # 检查重复行
        total_checks += 1
        if data.duplicated().any():
            issues_count += 1

        # 检查特定列的逻辑一致性（例如：最高价不应低于最低价）
        if 'high' in data.columns and 'low' in data.columns:
            total_checks += 1
            inconsistent_rows = (data['high'] < data['low']).sum()
            if inconsistent_rows > 0:
                issues_count += 1

        if 'open' in data.columns and 'close' in data.columns:
            total_checks += 1
            # 检查开盘价和收盘价是否在合理的高低区间内（允许一定比例的例外）
            outside_range = ((data['open'] > data['high']) | (data['open'] < data['low']) |
                           (data['close'] > data['high']) | (data['close'] < data['low'])).sum()
            if outside_range / len(data) > 0.05:  # 超过5%的数据不符合逻辑
                issues_count += 1

        # 一致性 = 1 - 问题比例
        consistency = 1 - (issues_count / total_checks) if total_checks > 0 else 1.0
        return max(0.0, min(consistency, 1.0))

    def _check_timeliness(self, data: pd.DataFrame) -> float:
        """检查数据及时性（检查日期是否过期）"""
        if data.empty:
            return 0.0

        # 检查日期列（通常为'date'或'trade_date'等）
        date_columns = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
        if not date_columns:
            # 如果没有日期列，假设数据是最新的
            return 1.0

        date_col = date_columns[0]  # 使用第一个日期列
        try:
            dates = pd.to_datetime(data[date_col], errors='coerce').dropna()
            if dates.empty:
                return 0.5  # 日期转换失败，返回中等及时性

            # 获取最新的日期
            latest_date = dates.max()
            current_date = datetime.now().date()
            date_diff = abs((current_date - latest_date.date()).days)

            # 如果数据在1天内，认为是及时的；1-7天内认为一般；超过7天认为不及时
            if date_diff <= 1:
                timeliness = 1.0
            elif date_diff <= 7:
                timeliness = 0.7
            elif date_diff <= 30:
                timeliness = 0.4
            else:
                timeliness = 0.1

            return timeliness

        except Exception as e:
            logger.warning(f"日期列处理失败: {e}")
            return 0.5

    def _detect_issues(self, data: pd.DataFrame, completeness: float, accuracy: float, consistency: float, timeliness: float) -> List[str]:
        """检测数据问题"""
        issues = []

        # 检查完整性问题
        if completeness < self.threshold_config['completeness']:
            missing_info = data.isnull().sum()
            high_missing_cols = missing_info[missing_info > 0]
            if not high_missing_cols.empty:
                top_missing = high_missing_cols.nlargest(3)
                issues.append(f"数据完整性不足 ({completeness:.2%}): {dict(top_missing.head(2))}")

        # 检查准确性问题
        if accuracy < self.threshold_config['accuracy']:
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                issues.append(f"数据准确性不足 ({accuracy:.2%}): 存在异常值")

        # 检查一致性问题
        if consistency < self.threshold_config['consistency']:
            if data.duplicated().any():
                duplicated_count = data.duplicated().sum()
                issues.append(f"数据一致性不足 ({consistency:.2%}): 发现 {duplicated_count} 条重复记录")

            # 检查高低价逻辑
            if 'high' in data.columns and 'low' in data.columns:
                inconsistent_count = (data['high'] < data['low']).sum()
                if inconsistent_count > 0:
                    issues.append(f"价格逻辑错误: {inconsistent_count} 条记录最高价小于最低价")

        # 检查及时性问题
        if timeliness < self.threshold_config['timeliness']:
            issues.append(f"数据及时性不足 ({timeliness:.2%}): 数据可能存在延迟")

        return issues

    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """根据发现的问题生成建议"""
        recommendations = []

        if any('完整性' in issue for issue in issues):
            recommendations.append("建议检查数据采集流程，确保字段完整")

        if any('准确性' in issue for issue in issues):
            recommendations.append("建议增加异常值检测和清洗步骤")

        if any('一致性' in issue for issue in issues):
            recommendations.append("建议增加数据验证规则并去重")

        if any('及时性' in issue for issue in issues):
            recommendations.append("建议检查数据更新频率和采集延迟")

        if not recommendations:
            recommendations.append("数据质量良好，继续保持")

        return recommendations

    def _get_empty_data_report(self, data_source: str) -> DataQualityReport:
        """获取空数据报告"""
        return DataQualityReport(
            check_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data_source=data_source,
            completeness=0.0,
            accuracy=0.0,
            consistency=0.0,
            timeliness=0.0,
            overall_score=0.0,
            issues=["数据为空或无效"],
            recommendations=["检查数据源连接", "验证数据采集流程"],
            quality_level="很差"
        )

    def monitor_api_status(self, api_urls: List[str], timeout: int = 10) -> Dict[str, Dict[str, Any]]:
        """
        监控API接口状态

        Args:
            api_urls: API URL列表
            timeout: 超时时间（秒）

        Returns:
            Dict[str, Dict[str, Any]]: API状态信息
        """
        status_results = {}

        for url in api_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=timeout)
                response_time = time.time() - start_time

                status_results[url] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'available': response.status_code == 200,
                    'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': None
                }

                # 记录API状态
                self.api_status[url] = status_results[url]

            except requests.exceptions.Timeout:
                status_results[url] = {
                    'status_code': None,
                    'response_time': timeout,
                    'available': False,
                    'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': '请求超时'
                }
                self.api_status[url] = status_results[url]

            except requests.exceptions.RequestException as e:
                status_results[url] = {
                    'status_code': None,
                    'response_time': None,
                    'available': False,
                    'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': str(e)
                }
                self.api_status[url] = status_results[url]

        return status_results

    def get_api_status_summary(self) -> Dict[str, Any]:
        """获取API状态摘要"""
        if not self.api_status:
            return {
                'total_apis': 0,
                'available_apis': 0,
                'availability_rate': 0.0,
                'average_response_time': 0.0
            }

        total_apis = len(self.api_status)
        available_apis = sum(1 for status in self.api_status.values() if status['available'])
        availability_rate = available_apis / total_apis if total_apis > 0 else 0.0

        response_times = [status['response_time'] for status in self.api_status.values() 
                         if status['response_time'] is not None]
        avg_response_time = np.mean(response_times) if response_times else 0.0

        return {
            'total_apis': total_apis,
            'available_apis': available_apis,
            'availability_rate': availability_rate,
            'average_response_time': avg_response_time
        }

    def check_data_delay(self, data: pd.DataFrame, expected_frequency: str = 'daily') -> float:
        """
        检查数据延迟情况

        Args:
            data: 数据
            expected_frequency: 期望更新频率 ('daily', 'hourly', 'realtime')

        Returns:
            float: 延迟评分 (0-1，1表示无延迟)
        """
        if data.empty:
            return 0.0

        # 检查日期列
        date_columns = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
        if not date_columns:
            return 1.0  # 没有日期列，无法检查延迟

        date_col = date_columns[0]
        try:
            dates = pd.to_datetime(data[date_col], errors='coerce').dropna()
            if dates.empty:
                return 0.0

            latest_date = dates.max()
            current_time = datetime.now()

            if expected_frequency == 'daily':
                # 检查是否是今天的数据
                time_diff = current_time - latest_date
                if time_diff.days == 0:
                    delay_score = 1.0  # 今天的数据
                elif time_diff.days == 1:
                    delay_score = 0.7  # 昨天的数据
                elif time_diff.days <= 3:
                    delay_score = 0.4  # 3天内的数据
                else:
                    delay_score = 0.1  # 超过3天的数据
            elif expected_frequency == 'hourly':
                # 检查是否是最近几个小时的数据
                time_diff = current_time - latest_date
                hours_diff = time_diff.total_seconds() / 3600
                if hours_diff <= 1:
                    delay_score = 1.0
                elif hours_diff <= 4:
                    delay_score = 0.7
                elif hours_diff <= 24:
                    delay_score = 0.4
                else:
                    delay_score = 0.1
            else:  # realtime
                # 检查是否是最近几分钟的数据
                time_diff = current_time - latest_date
                minutes_diff = time_diff.total_seconds() / 60
                if minutes_diff <= 5:
                    delay_score = 1.0
                elif minutes_diff <= 15:
                    delay_score = 0.7
                elif minutes_diff <= 60:
                    delay_score = 0.4
                else:
                    delay_score = 0.1

            return max(0.0, min(delay_score, 1.0))

        except Exception as e:
            logger.warning(f"延迟检查失败: {e}")
            return 0.5  # 出错时返回中等延迟评分

    def get_monitoring_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取监控摘要（最近几天的）"""
        if not self.monitoring_history:
            return {}

        # 筛选最近几天的记录
        start_date = datetime.now() - timedelta(days=days)
        recent_reports = [
            report for report in self.monitoring_history
            if datetime.strptime(report.check_time, '%Y-%m-%d %H:%M:%S') >= start_date
        ]

        if not recent_reports:
            return {}

        # 计算平均指标
        avg_completeness = np.mean([r.completeness for r in recent_reports])
        avg_accuracy = np.mean([r.accuracy for r in recent_reports])
        avg_consistency = np.mean([r.consistency for r in recent_reports])
        avg_timeliness = np.mean([r.timeliness for r in recent_reports])
        avg_overall = np.mean([r.overall_score for r in recent_reports])

        # 统计问题类型
        all_issues = []
        for report in recent_reports:
            all_issues.extend(report.issues)

        issue_counts = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0]  # 获取问题类型
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        return {
            'period_days': days,
            'total_checks': len(recent_reports),
            'avg_completeness': avg_completeness,
            'avg_accuracy': avg_accuracy,
            'avg_consistency': avg_consistency,
            'avg_timeliness': avg_timeliness,
            'avg_overall_score': avg_overall,
            'top_issues': sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'quality_trend': 'improving' if avg_overall > 0.8 else ('stable' if 0.6 <= avg_overall <= 0.8 else 'declining')
        }