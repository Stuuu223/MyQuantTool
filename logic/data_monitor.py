# logic/data_monitor.py
"""
数据质量监控模块 - 提供龙虎榜数据的实时健康检查
功能：检查API可用性、数据完整性、响应时间等指标
"""

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """数据质量监控类"""
    
    # 健康分数权重配置
    WEIGHTS = {
        'api_availability': 0.25,        # API 可用性
        'data_completeness': 0.25,       # 数据完整性
        'response_time': 0.15,           # 响应时间
        'data_freshness': 0.15,          # 数据新鲜度
        'consistency': 0.10,             # 数据一致性
        'error_rate': 0.10,              # 错误率
    }
    
    def __init__(self):
        self.check_results = {}
        self.last_check_time = None
        self.health_history = []
        
    def check_data_quality(self, date=None) -> Dict[str, Any]:
        """
        执行完整的数据质量检查
        返回健康报告和详细检查结果
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d") if isinstance(date, datetime) else date
        
        report = {
            '检查时间': datetime.now().isoformat(),
            '检查日期': date_str,
            '检查项目': [],
            '警告': [],
            '错误': [],
            '健康分数': 0,
            '整体质量': '未知',
        }
        
        # 执行 7 个检查项
        checks = [
            ('龙虎榜数据可用性', self._check_lhb_availability, date_str),
            ('营业部明细可用性', self._check_seat_availability, date_str),
            ('列名正确性', self._check_column_names, date_str),
            ('API响应时间', self._check_response_time, date_str),
            ('数据完整性', self._check_data_completeness, date_str),
            ('重複記錄検測', self._check_duplicates, date_str),
            ('数据新鲜度', self._check_data_freshness, date_str),
        ]
        
        total_score = 0
        check_count = 0
        
        for check_name, check_func, *args in checks:
            try:
                score, result = check_func(*args)
                
                item = {
                    '项目': check_name,
                    '正常': score >= 80,
                    '分数': score,
                    '信息': result.get('message', ''),
                    '详情': result,
                }
                
                report['检查项目'].append(item)
                total_score += score
                check_count += 1
                
                # 警告和错误
                if score < 60:
                    report['错误'].append(f"{check_name}: {result.get('message', '未知错误')}")
                elif score < 80:
                    report['警告'].append(f"{check_name}: {result.get('message', '轻微问题')}")
                    
            except Exception as e:
                logger.error(f"执行检查 {check_name} 失败: {e}")
                report['检查项目'].append({
                    '项目': check_name,
                    '正常': False,
                    '分数': 0,
                    '信息': f'检查失败: {str(e)}',
                })
                report['错误'].append(f"{check_name}: {str(e)}")
        
        # 计算总体健康分数
        report['健康分数'] = int(total_score / check_count) if check_count > 0 else 0
        
        # 确定整体质量等级
        if report['健康分数'] >= 80:
            report['整体质量'] = '优秘'
        elif report['健康分数'] >= 60:
            report['整体质量'] = '良好'
        elif report['健康分数'] >= 40:
            report['整体质量'] = '一般'
        else:
            report['整体质量'] = '不佳'
        
        self.check_results = report
        self.last_check_time = datetime.now()
        self.health_history.append(report['健康分数'])
        
        return report
    
    def _check_lhb_availability(self, date_str: str) -> tuple:
        """检查龙虎榜数据可用性"""
        try:
            start_time = time.time()
            lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
            elapsed = time.time() - start_time
            
            if lhb_df.empty:
                return 50, {
                    'message': '当日无龙虎榜数据',
                    'count': 0,
                    'response_time': elapsed,
                }
            
            count = len(lhb_df)
            score = min(100, 80 + (count / 10))  # 数据越多分数越高
            
            return score, {
                'message': f'正常，获取 {count} 条记录',
                'count': count,
                'columns': lhb_df.columns.tolist(),
                'response_time': elapsed,
            }
        except Exception as e:
            return 0, {
                'message': f'API不可用: {str(e)}',
                'error': str(e),
            }
    
    def _check_seat_availability(self, date_str: str) -> tuple:
        """检查营业部明细数据可用性"""
        try:
            # 先获取龙虎榜股票列表
            lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
            
            if lhb_df.empty:
                return 50, {
                    'message': '龙虎榜无数据，无法检查营业部明细',
                }
            
            # 抽样检查前3只股票
            sample_size = min(3, len(lhb_df))
            success = 0
            total_seats = 0
            
            for idx in range(sample_size):
                try:
                    code = lhb_df.iloc[idx]['代码']
                    seat_df = ak.stock_lhb_stock_detail_em(symbol=code, date=date_str)
                    
                    if not seat_df.empty:
                        success += 1
                        total_seats += len(seat_df)
                except:
                    pass
            
            if success == 0:
                return 0, {
                    'message': f'营业部明细查询失败 (0/{sample_size})',
                    'sample_size': sample_size,
                    'success': success,
                }
            
            score = (success / sample_size) * 100
            
            return score, {
                'message': f'正常，成功抽样 {success}/{sample_size}，共 {total_seats} 条明细',
                'sample_size': sample_size,
                'success': success,
                'total_seats': total_seats,
            }
        except Exception as e:
            return 0, {
                'message': f'营业部明细检查失败: {str(e)}',
                'error': str(e),
            }
    
    def _check_column_names(self, date_str: str) -> tuple:
        """检查返回数据的列名是否正确"""
        try:
            lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
            
            if lhb_df.empty:
                return 50, {
                    'message': '龙虎榜无数据，无法检查列名',
                }
            
            expected_columns = ['代码', '名称', '收盘价', '涨跌幅']
            actual_columns = lhb_df.columns.tolist()
            
            missing = [col for col in expected_columns if col not in actual_columns]
            
            if not missing:
                return 100, {
                    'message': '列名正确',
                    'columns': actual_columns,
                }
            
            return 60, {
                'message': f'缺失列: {missing}',
                'expected': expected_columns,
                'actual': actual_columns,
                'missing': missing,
            }
        except Exception as e:
            return 0, {
                'message': f'列名检查失败: {str(e)}',
                'error': str(e),
            }
    
    def _check_response_time(self, date_str: str) -> tuple:
        """检查API响应时间"""
        try:
            times = []
            
            # 测试 3 次查询
            for _ in range(3):
                start = time.time()
                ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            
            # 评分标准：2秒内 100分，5秒内 80分，10秒内 40分
            if avg_time <= 2:
                score = 100
            elif avg_time <= 5:
                score = 80
            elif avg_time <= 10:
                score = 40
            else:
                score = 20
            
            return score, {
                'message': f'平均响应时间 {avg_time:.2f}秒',
                'avg_time': avg_time,
                'times': times,
                'evaluation': '优秘' if score >= 80 else '良好' if score >= 40 else '不佳',
            }
        except Exception as e:
            return 0, {
                'message': f'响应时间检查失败: {str(e)}',
                'error': str(e),
            }
    
    def _check_data_completeness(self, date_str: str) -> tuple:
        """检查数据完整性（是否有缺失值）"""
        try:
            lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
            
            if lhb_df.empty:
                return 50, {
                    'message': '龙虎榜无数据',
                }
            
            total_cells = lhb_df.shape[0] * lhb_df.shape[1]
            missing_cells = lhb_df.isna().sum().sum()
            completeness = (total_cells - missing_cells) / total_cells * 100
            
            score = completeness
            
            return score, {
                'message': f'完整性 {completeness:.2f}% (缺失 {missing_cells}/{total_cells})',
                'total_cells': total_cells,
                'missing_cells': missing_cells,
                'completeness': completeness,
            }
        except Exception as e:
            return 0, {
                'message': f'完整性检查失败: {str(e)}',
                'error': str(e),
            }
    
    def _check_duplicates(self, date_str: str) -> tuple:
        """检查重複記錄"""
        try:
            lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
            
            if lhb_df.empty:
                return 50, {
                    'message': '龙虎榜无数据',
                }
            
            duplicates = lhb_df.duplicated(subset=['代码']).sum()
            
            if duplicates == 0:
                return 100, {
                    'message': '无重複記錄',
                    'total': len(lhb_df),
                    'duplicates': 0,
                }
            
            score = max(0, 100 - (duplicates / len(lhb_df) * 100))
            
            return score, {
                'message': f'發現 {duplicates} 条重複',
                'total': len(lhb_df),
                'duplicates': duplicates,
                'duplicate_rate': duplicates / len(lhb_df),
            }
        except Exception as e:
            return 0, {
                'message': f'重複检查失败: {str(e)}',
                'error': str(e),
            }
    
    def _check_data_freshness(self, date_str: str) -> tuple:
        """检查数据新鲜度（距现在多少天）"""
        try:
            target_date = datetime.strptime(date_str, "%Y%m%d")
            now = datetime.now()
            days_old = (now - target_date).days
            
            if days_old == 0:
                score = 100
                freshness = '最新'
            elif days_old == 1:
                score = 90
                freshness = '1天前'
            elif days_old <= 3:
                score = 80
                freshness = f'{days_old}天前'
            elif days_old <= 7:
                score = 60
                freshness = f'{days_old}天前'
            else:
                score = 30
                freshness = f'{days_old}天前'
            
            return score, {
                'message': f'数据来自 {freshness}',
                'target_date': target_date.isoformat(),
                'days_old': days_old,
                'freshness': freshness,
            }
        except Exception as e:
            return 0, {
                'message': f'新鲜度检查失败: {str(e)}',
                'error': str(e),
            }
    
    def generate_health_report(self) -> str:
        """生成可读的健康报告"""
        if not self.check_results:
            return "❌ 未执行检查，请先调用 check_data_quality()"
        
        report = self.check_results
        
        # 构建报告字符串
        output = f"""
▐═══════════════════════════════════════════════▐
░           📊 MyQuantTool 数据质量健康报告                       ░
▐═══════════════════════════════════════════════▐

检查时间: {report['检查时间']}
检查日期: {report['检查日期']}

【整体评分】
─────────────────────────────────────────────
健康分数: {report['健康分数']}/100
整体质量: {report['整体质量']}

{self._get_health_emoji(report['健康分数'])} {self._get_health_desc(report['健康分数'])}

【詳細检查項】
─────────────────────────────────────────────
"""
        
        for item in report['检查项目']:
            status = "✅" if item['正常'] else "❌"
            output += f"{status} {item['项目']} ({item['分数']}/100)\n"
            output += f"   {item['信息']}\n"
        
        if report['警告']:
            output += f"""
【⚠️  警告】
─────────────────────────────────────────────
"""
            for warning in report['警告']:
                output += f"⚠️  {warning}\n"
        
        if report['错误']:
            output += f"""
【❌ 错误】
─────────────────────────────────────────────
"""
            for error in report['错误']:
                output += f"❌ {error}\n"
        
        output += """
▐═══════════════════════════════════════════════▐
"""
        
        return output
    
    @staticmethod
    def _get_health_emoji(score: int) -> str:
        """根据分数获取对应的 emoji"""
        if score >= 80:
            return "🞫"
        elif score >= 60:
            return "🞪"
        elif score >= 40:
            return "🜴"
        else:
            return "⚠️"
    
    @staticmethod
    def _get_health_desc(score: int) -> str:
        """获取健康状态描述"""
        if score >= 80:
            return "系统健康，所有指标正常"
        elif score >= 60:
            return "系统基本健康，存在轻微问题"
        elif score >= 40:
            return "系统有问题，建议检查"
        else:
            return "系统出现严重问题，需要立即处理"
    
    def get_health_trend(self) -> Dict[str, Any]:
        """获取健康趋势"""
        return {
            '历史记录': self.health_history[-10:],  # 最近 10 次
            '当前分数': self.check_results.get('健康分数', 0) if self.check_results else 0,
            '平均分数': sum(self.health_history) / len(self.health_history) if self.health_history else 0,
            '最高分': max(self.health_history) if self.health_history else 0,
            '最低分': min(self.health_history) if self.health_history else 0,
        }


# 全局监控器实例
_monitor_instance = None


def get_monitor() -> DataQualityMonitor:
    """获取全局监控器实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = DataQualityMonitor()
    return _monitor_instance
