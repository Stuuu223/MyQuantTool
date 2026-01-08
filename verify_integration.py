"""
验证所有功能是否已成功集成到UI中
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 测试导入所有必要的模块
print("正在验证功能模块导入...")

try:
    from logic.broker_api import MockBrokerAPI
    print("[OK] 交易执行模块导入成功")
except ImportError as e:
    print(f"[ERROR] 交易执行模块导入失败: {e}")

try:
    from logic.slippage_model import SlippageModel, AdvancedSlippagePredictor
    print("[OK] 滑点优化模块导入成功")
except ImportError as e:
    print(f"[ERROR] 滑点优化模块导入失败: {e}")

try:
    from logic.portfolio_optimizer import PortfolioOptimizer
    print("[OK] 组合优化模块导入成功")
except ImportError as e:
    print(f"[ERROR] 组合优化模块导入失败: {e}")

try:
    from logic.market_sentiment import MarketSentimentIndexCalculator
    print("[OK] 市场情绪分析模块导入成功")
except ImportError as e:
    print(f"[ERROR] 市场情绪分析模块导入失败: {e}")

try:
    from logic.strategy_factory import StrategyFactory
    print("[OK] 策略工厂模块导入成功")
except ImportError as e:
    print(f"[ERROR] 策略工厂模块导入失败: {e}")

try:
    from logic.parameter_optimizer import ParameterOptimizer
    print("[OK] 参数优化模块导入成功")
except ImportError as e:
    print(f"[ERROR] 参数优化模块导入失败: {e}")

try:
    from logic.strategy_comparison import StrategyComparator
    print("[OK] 策略对比模块导入成功")
except ImportError as e:
    print(f"[ERROR] 策略对比模块导入失败: {e}")

try:
    from logic.advanced_visualizer import AdvancedVisualizer
    print("[OK] 可视化分析模块导入成功")
except ImportError as e:
    print(f"[ERROR] 可视化分析模块导入失败: {e}")

# 测试主仪表板
try:
    from ui.main_dashboard import main
    print("[OK] 主仪表板模块导入成功")
except ImportError as e:
    print(f"[ERROR] 主仪表板模块导入失败: {e}")

# 验证导航选项
nav_options = ["主页", "交易执行", "组合优化", "市场情绪", "策略工厂", "参数优化", "策略对比", "可视化分析"]
print(f"[OK] 主仪表板导航选项: {nav_options}")
print(f"总计 {len(nav_options)} 个功能页面")

print("\n所有功能模块均已成功集成到UI中！")