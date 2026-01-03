"""
测试 API Key 配置
"""
from config import Config
import os

# 加载配置
config = Config()

# 获取 API Key
api_key_from_config = config.get('api_key', '')
api_key_from_env = os.getenv("SILICONFLOW_API_KEY")

# 优先级:环境变量 > 配置文件 > 默认值
final_api_key = api_key_from_env or api_key_from_config or 'sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet'

print("=" * 50)
print("API Key 配置检查")
print("=" * 50)
print(f"环境变量 API Key: {'已设置' if api_key_from_env else '未设置'}")
print(f"配置文件 API Key: {'已设置' if api_key_from_config else '未设置'}")
print(f"最终使用的 API Key: {final_api_key[:20]}...{final_api_key[-10:]}")
print(f"API Key 长度: {len(final_api_key)}")
print(f"API Key 是否有效: {'是' if len(final_api_key) >= 10 else '否'}")
print("=" * 50)

# 检查自选股
watchlist = config.get('watchlist', [])
print(f"\n自选股列表: {watchlist if watchlist else '暂无自选股'}")
print("=" * 50)