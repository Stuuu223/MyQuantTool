"""
用户偏好设置模块
提供用户偏好设置功能
"""

import json
import os


class UserPreferences:
    """用户偏好设置管理器"""

    def __init__(self, config_file='data/user_preferences.json'):
        self.config_file = config_file
        self.preferences = self._load_preferences()

    def _load_preferences(self):
        """加载用户偏好"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_default_preferences()
        except:
            return self._get_default_preferences()

    def _get_default_preferences(self):
        """获取默认偏好"""
        return {
            # 显示偏好
            'display': {
                '主题': 'light',
                '图表类型': 'candlestick',
                '显示网格': True,
                '显示成交量': True
            },
            # 分析偏好
            'analysis': {
                '默认分析天数': 60,
                '默认均线周期': [5, 10, 20, 60],
                '默认技术指标': ['MACD', 'RSI', 'KDJ'],
                '默认止损比例': 0.05,
                '默认止盈比例': 0.10
            },
            # 预警偏好
            'alert': {
                '启用声音提醒': False,
                '启用弹窗提醒': True,
                '默认预警频率': '实时',
                '预警刷新间隔': 60
            },
            # 风险控制偏好
            'risk': {
                '单笔风险比例': 0.02,
                '最大持仓数量': 5,
                '最大回撤限制': 0.10,
                '启用自动止损': False
            },
            # 其他偏好
            'other': {
                '自动刷新': False,
                '刷新间隔': 300,
                '保存历史记录': True,
                '历史记录保留天数': 30
            }
        }

    def save_preferences(self):
        """保存用户偏好"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存偏好失败: {e}")
            return False

    def get(self, category, key, default=None):
        """获取偏好值"""
        try:
            return self.preferences[category][key]
        except:
            return default

    def set(self, category, key, value):
        """设置偏好值"""
        if category not in self.preferences:
            self.preferences[category] = {}
        self.preferences[category][key] = value
        return self.save_preferences()

    def get_all(self):
        """获取所有偏好"""
        return self.preferences

    def reset_to_default(self):
        """重置为默认偏好"""
        self.preferences = self._get_default_preferences()
        return self.save_preferences()