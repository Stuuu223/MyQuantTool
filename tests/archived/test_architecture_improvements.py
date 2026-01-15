"""
测试架构性改进模块
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(__file__))

def test_enhanced_ml_predictor():
    """测试增强型ML预测器"""
    print("\n=== 测试增强型ML预测器 ===")
    try:
        from logic.enhanced_ml_predictor import EnhancedMLPredictor, PredictionResult

        # 创建示例数据
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)  # 为了可重复性
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)  # 随机游走价格
        volumes = np.random.randint(1000000, 5000000, size=100)  # 随机交易量

        df = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + abs(np.random.randn(100) * 0.2),
            'low': prices - abs(np.random.randn(100) * 0.2),
            'close': prices,
            'volume': volumes
        })

        # 创建预测器实例
        predictor = EnhancedMLPredictor(lookback_days=30, prediction_horizon='short')
        print("  [INFO] EnhancedMLPredictor 创建成功")

        # 尝试训练（仅使用集成学习模型，因为深度学习模型可能没有安装依赖）
        success = predictor.fit(df, '000001')
        print(f"  [INFO] 模型训练{'成功' if success else '失败'}")

        # 尝试预测
        result = predictor.predict(df, '000001')
        if result:
            print(f"  [SUCCESS] 预测成功: {result.predicted_price:.2f}, 置信度: {result.confidence:.2f}")
            print(f"  [INFO] 预测时间范围: {result.prediction_horizon}, 风险评分: {result.risk_score:.2f}")
        else:
            print("  [INFO] 预测未执行（可能因为模型未训练）")

        return True

    except Exception as e:
        print(f"  [ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_risk_manager():
    """测试高级风险管理器"""
    print("\n=== 测试高级风险管理器 ===")
    try:
        from logic.advanced_risk_manager import AdvancedRiskManager, RiskMetrics

        # 创建风险管理器实例
        risk_manager = AdvancedRiskManager(initial_capital=100000, max_position_size=0.1)
        print("  [INFO] AdvancedRiskManager 创建成功")

        # 创建示例数据
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        prices = 100 + np.cumsum(np.random.randn(50) * 0.2)
        volumes = np.random.randint(1000000, 5000000, size=50)

        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'volume': volumes,
            'high': prices + abs(np.random.randn(50) * 0.15),
            'low': prices - abs(np.random.randn(50) * 0.15)
        })

        # 计算风险指标
        metrics = risk_manager.calculate_risk_metrics(
            df, current_price=105.0, position_size=1000, sector='科技'
        )
        print(f"  [SUCCESS] 风险计算成功: 总风险 {metrics.total_risk:.2f}, 建议仓位 {metrics.suggested_position:.2f}")
        print(f"  [INFO] 风险等级: {metrics.risk_level}, 股票代码: {metrics.stock_code}")

        # 获取风险建议
        recommendation = risk_manager.get_risk_recommendation(metrics)
        print(f"  [INFO] 风险建议: {recommendation}")

        # 更新持仓
        risk_manager.update_position('000001', '科技', 1000, 105.0)
        print("  [SUCCESS] 持仓更新成功")

        # 获取投资组合风险摘要
        portfolio_summary = risk_manager.get_portfolio_risk_summary()
        print(f"  [INFO] 投资组合摘要: {portfolio_summary}")

        return True

    except Exception as e:
        print(f"  [ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_quality_monitor():
    """测试数据质量监控器"""
    print("\n=== 测试数据质量监控器 ===")
    try:
        from logic.data_quality_monitor import DataQualityMonitor, DataQualityReport

        # 创建监控器实例
        monitor = DataQualityMonitor()
        print("  [INFO] DataQualityMonitor 创建成功")

        # 创建示例数据
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        prices = 100 + np.cumsum(np.random.randn(30) * 0.2)

        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, size=30),
            'high': prices + abs(np.random.randn(30) * 0.15),
            'low': prices - abs(np.random.randn(30) * 0.15)
        })

        # 添加一些缺失值和异常值来测试监控功能
        df.loc[5, 'volume'] = np.nan  # 缺失值
        df.loc[10, 'high'] = df['close'].iloc[10] - 1  # 逻辑错误：high < low
        df.loc[15, 'low'] = df['close'].iloc[15] + 1   # 逻辑错误：low > high

        # 检查数据质量
        report = monitor.check_data_quality(df, 'test_data')
        print(f"  [SUCCESS] 数据质量检查成功: 总体评分 {report.overall_score:.2f}, 质量等级: {report.quality_level}")
        print(f"  [INFO] 完整性: {report.completeness:.2f}, 准确性: {report.accuracy:.2f}")
        print(f"  [INFO] 一致性: {report.consistency:.2f}, 及时性: {report.timeliness:.2f}")

        if report.issues:
            print(f"  [INFO] 发现问题: {len(report.issues)} 个")
            for issue in report.issues[:2]:  # 显示前两个问题
                print(f"    - {issue}")

        if report.recommendations:
            print(f"  [INFO] 改进建议: {report.recommendations[0]}")

        # 测试API状态监控（使用一些示例URL，可能不可用但测试功能）
        api_urls = ['https://httpbin.org/get', 'https://httpbin.org/status/200']
        api_status = monitor.monitor_api_status(api_urls, timeout=5)
        print(f"  [SUCCESS] API状态监控完成，检查了 {len(api_status)} 个接口")

        # 获取API状态摘要
        api_summary = monitor.get_api_status_summary()
        print(f"  [INFO] API状态摘要: 可用率 {api_summary['availability_rate']:.2f}")

        # 获取监控摘要
        summary = monitor.get_monitoring_summary(days=7)
        print(f"  [INFO] 监控摘要: {summary.get('total_checks', 0)} 次检查，平均得分 {summary.get('avg_overall_score', 0):.2f}")

        return True

    except Exception as e:
        print(f"  [ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("="*60)
    print("架构性改进模块测试开始...")
    print("="*60)

    success_count = 0
    total_tests = 3

    # 测试增强型ML预测器
    if test_enhanced_ml_predictor():
        success_count += 1

    # 测试高级风险管理器
    if test_advanced_risk_manager():
        success_count += 1

    # 测试数据质量监控器
    if test_data_quality_monitor():
        success_count += 1

    print("\n"+"="*60)
    print(f"测试完成！成功: {success_count}/{total_tests}")
    if success_count == total_tests:
        print("所有架构性改进模块测试通过！")
    else:
        print("部分测试失败，请检查相关模块。")
    print("="*60)


if __name__ == "__main__":
    main()
