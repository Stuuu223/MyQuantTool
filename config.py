"""
用户配置文件
用于存储用户的个性化设置
"""
import json
import os

class Config:
    """配置管理类"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_config = {
            'api_key': '',
            'default_symbol': '600519',
            'default_start_date': '2024-01-01',
            'atr_multiplier': 0.5,
            'grid_ratio': 0.1,
            'theme': 'light',
            'language': 'zh'
        }
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有字段都存在
                    return {**self.default_config, **config}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        return self.save_config()
    
    def update(self, updates):
        """批量更新配置"""
        self.config.update(updates)
        return self.save_config()
    
    def reset(self):
        """重置为默认配置"""
        self.config = self.default_config.copy()
        return self.save_config()