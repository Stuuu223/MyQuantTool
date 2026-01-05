"""
历史记录管理模块
提供分析历史记录和导出功能
"""

import pandas as pd
import json
from datetime import datetime
import os


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, history_dir='data/history'):
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)

    def save_analysis(self, analysis_type, symbol, result):
        """
        保存分析结果

        Args:
            analysis_type: 分析类型
            symbol: 股票代码
            result: 分析结果
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{analysis_type}_{symbol}_{timestamp}.json"
            filepath = os.path.join(self.history_dir, filename)

            # 添加元数据
            record = {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': analysis_type,
                'symbol': symbol,
                'result': result
            }

            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            return {
                '状态': '成功',
                '文件路径': filepath
            }

        except Exception as e:
            return {
                '状态': '失败',
                '错误信息': str(e)
            }

    def get_history(self, analysis_type=None, symbol=None, limit=10):
        """
        获取历史记录

        Args:
            analysis_type: 分析类型（可选）
            symbol: 股票代码（可选）
            limit: 返回记录数量

        Returns:
            历史记录列表
        """
        try:
            # 获取所有历史文件
            files = os.listdir(self.history_dir)

            # 过滤文件
            if analysis_type:
                files = [f for f in files if f.startswith(analysis_type)]

            if symbol:
                files = [f for f in files if symbol in f]

            # 按时间排序（最新的在前）
            files.sort(reverse=True)

            # 读取记录
            records = []
            for filename in files[:limit]:
                filepath = os.path.join(self.history_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        record = json.load(f)
                        records.append(record)
                except:
                    continue

            return {
                '状态': '成功',
                '记录数量': len(records),
                '记录列表': records
            }

        except Exception as e:
            return {
                '状态': '失败',
                '错误信息': str(e)
            }

    def export_to_excel(self, analysis_type, symbol=None):
        """
        导出历史记录到Excel

        Args:
            analysis_type: 分析类型
            symbol: 股票代码（可选）

        Returns:
            导出结果
        """
        try:
            # 获取历史记录
            history_result = self.get_history(analysis_type, symbol, limit=100)

            if history_result['状态'] != '成功' or not history_result['记录列表']:
                return {
                    '状态': '失败',
                    '说明': '没有可导出的记录'
                }

            # 转换为DataFrame
            records = history_result['记录列表']
            df_data = []

            for record in records:
                row = {
                    '时间': record['timestamp'],
                    '分析类型': record['analysis_type'],
                    '股票代码': record['symbol']
                }

                # 添加结果数据
                result = record['result']
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, (int, float, str)):
                            row[key] = value
                        elif isinstance(value, list) and len(value) > 0:
                            # 如果是列表，取第一个元素
                            row[f"{key}_示例"] = str(value[0])[:100]
                        else:
                            row[key] = str(value)[:100]

                df_data.append(row)

            df = pd.DataFrame(df_data)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{analysis_type}_导出_{timestamp}.xlsx"
            filepath = os.path.join(self.history_dir, filename)

            # 导出到Excel
            df.to_excel(filepath, index=False, engine='openpyxl')

            return {
                '状态': '成功',
                '文件路径': filepath,
                '记录数量': len(df)
            }

        except Exception as e:
            return {
                '状态': '失败',
                '错误信息': str(e)
            }

    def clear_old_history(self, days=30):
        """
        清除旧的历史记录

        Args:
            days: 保留天数

        Returns:
            清除结果
        """
        try:
            from datetime import timedelta

            # 计算截止时间
            cutoff_time = datetime.now() - timedelta(days=days)

            # 获取所有文件
            files = os.listdir(self.history_dir)

            deleted_count = 0
            for filename in files:
                try:
                    # 从文件名提取时间
                    parts = filename.replace('.json', '').split('_')
                    if len(parts) >= 2:
                        file_time_str = parts[-2] + parts[-1]
                        file_time = datetime.strptime(file_time_str, "%Y%m%d%H%M%S")

                        # 如果文件时间早于截止时间，删除
                        if file_time < cutoff_time:
                            filepath = os.path.join(self.history_dir, filename)
                            os.remove(filepath)
                            deleted_count += 1
                except:
                    continue

            return {
                '状态': '成功',
                '删除数量': deleted_count
            }

        except Exception as e:
            return {
                '状态': '失败',
                '错误信息': str(e)
            }