"""
数据源管理模块
提供多数据源切换和备份功能
"""

import akshare as ak
import pandas as pd


class DataSourceManager:
    """数据源管理器"""

    # 可用的数据源
    DATA_SOURCES = {
        'akshare': {
            'name': 'AkShare',
            'description': '开源财经数据接口',
            'priority': 1
        },
        'tushare': {
            'name': 'TuShare',
            'description': 'TuShare Pro数据接口',
            'priority': 2,
            'requires_token': True
        }
    }

    def __init__(self, primary_source='akshare', fallback_sources=None):
        """
        初始化数据源管理器

        Args:
            primary_source: 主数据源
            fallback_sources: 备用数据源列表
        """
        self.primary_source = primary_source
        self.fallback_sources = fallback_sources or ['akshare']
        self.current_source = primary_source

    def get_stock_list(self):
        """
        获取股票列表
        尝试主数据源，失败后尝试备用数据源
        """
        # 尝试主数据源
        try:
            if self.current_source == 'akshare':
                df = ak.stock_zh_a_spot_em()
                return {
                    '状态': '成功',
                    '数据源': self.current_source,
                    '数据': df
                }
        except Exception as e:
            print(f"主数据源 {self.current_source} 失败: {e}")

        # 尝试备用数据源
        for source in self.fallback_sources:
            if source == self.current_source:
                continue

            try:
                if source == 'akshare':
                    df = ak.stock_zh_a_spot_em()
                    self.current_source = source
                    return {
                        '状态': '成功（使用备用数据源）',
                        '数据源': source,
                        '数据': df
                    }
            except Exception as e:
                print(f"备用数据源 {source} 失败: {e}")
                continue

        return {
            '状态': '失败',
            '说明': '所有数据源均不可用'
        }

    def get_stock_data(self, symbol, start_date, end_date):
        """
        获取股票历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        from logic.data_manager import DataManager

        db = DataManager()
        try:
            df = db.get_history_data(symbol, start_date=start_date, end_date=end_date)
            db.close()

            if df.empty:
                return {
                    '状态': '无数据',
                    '说明': '未找到股票数据'
                }

            return {
                '状态': '成功',
                '数据源': self.current_source,
                '数据': df
            }
        except Exception as e:
            db.close()
            return {
                '状态': '失败',
                '错误信息': str(e),
                '说明': '可能是数据源问题'
            }

    def get_board_data(self, board_type='concept'):
        """
        获取板块数据

        Args:
            board_type: 板块类型 ('concept' 或 'industry')
        """
        try:
            if board_type == 'concept':
                df = ak.stock_board_concept_name_em()
            else:
                df = ak.stock_board_industry_name_em()

            return {
                '状态': '成功',
                '数据源': self.current_source,
                '数据': df
            }
        except Exception as e:
            print(f"获取板块数据失败: {e}")
            return {
                '状态': '失败',
                '错误信息': str(e),
                '说明': '可能是数据源问题'
            }

    def get_lhb_data(self, date=None):
        """
        获取龙虎榜数据

        Args:
            date: 日期（可选）
        """
        try:
            if date:
                df = ak.stock_lhb_detail_daily_em(date=date)
            else:
                df = ak.stock_lhb_detail_daily_em()

            return {
                '状态': '成功',
                '数据源': self.current_source,
                '数据': df
            }
        except Exception as e:
            print(f"获取龙虎榜数据失败: {e}")
            return {
                '状态': '失败',
                '错误信息': str(e),
                '说明': '可能是数据源问题'
            }

    def get_limit_up_data(self):
        """
        获取涨停板数据
        """
        try:
            df = ak.stock_zt_pool_em()
            return {
                '状态': '成功',
                '数据源': self.current_source,
                '数据': df
            }
        except Exception as e:
            print(f"获取涨停板数据失败: {e}")
            return {
                '状态': '失败',
                '错误信息': str(e),
                '说明': '可能是数据源问题'
            }

    def check_data_quality(self, df):
        """
        检查数据质量

        Args:
            df: DataFrame数据
        """
        if df.empty:
            return {
                '质量评分': 0,
                '状态': '无数据'
            }

        score = 100
        issues = []

        # 检查缺失值
        missing_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        if missing_ratio > 0.1:
            score -= 20
            issues.append(f"缺失值比例过高: {missing_ratio:.2%}")

        # 检查数据量
        if len(df) < 10:
            score -= 30
            issues.append(f"数据量不足: {len(df)}条")

        # 检查数据范围
        if 'close' in df.columns:
            price_range = df['close'].max() - df['close'].min()
            if price_range <= 0:
                score -= 50
                issues.append("价格数据异常")

        # 检查数据连续性
        if 'date' in df.columns:
            date_diff = df['date'].diff().dropna()
            if date_diff.max() > pd.Timedelta(days=7):
                score -= 10
                issues.append("数据不连续")

        return {
            '质量评分': max(0, score),
            '状态': '优秀' if score >= 80 else '良好' if score >= 60 else '较差',
            '问题列表': issues
        }

    def get_data_source_info(self):
        """获取数据源信息"""
        return {
            '当前数据源': self.current_source,
            '主数据源': self.primary_source,
            '备用数据源': self.fallback_sources,
            '可用数据源': list(self.DATA_SOURCES.keys())
        }

    def switch_data_source(self, new_source):
        """
        切换数据源

        Args:
            new_source: 新数据源名称
        """
        if new_source in self.DATA_SOURCES:
            self.current_source = new_source
            return {
                '状态': '成功',
                '当前数据源': new_source
            }
        else:
            return {
                '状态': '失败',
                '说明': f'数据源 {new_source} 不存在'
            }