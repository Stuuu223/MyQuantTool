"""
测试新功能模块
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_new_features():
    """测试新功能模块"""
    print("="*50)
    print("测试新功能模块开始...")
    print("="*50)
    
    # 1. 测试半路战法模块
    print("\n1. 测试半路战法模块...")
    try:
        from logic.midway_strategy import MidwayStrategyAnalyzer, MidwaySignal
        analyzer = MidwayStrategyAnalyzer()
        print("   [SUCCESS] MidwayStrategyAnalyzer 创建成功")
        print(f"   [INFO] 默认回看天数: {analyzer.lookback_days}")
    except Exception as e:
        print(f"   [ERROR] 测试失败: {e}")
    
    # 2. 测试买点扫描器模块
    print("\n2. 测试买点扫描器模块...")
    try:
        from logic.buy_point_scanner import BuyPointScanner, BuySignal
        scanner = BuyPointScanner()
        print("   [SUCCESS] BuyPointScanner 创建成功")
    except Exception as e:
        print(f"   [ERROR] 测试失败: {e}")
    
    # 3. 测试复盘助手模块
    print("\n3. 测试复盘助手模块...")
    try:
        from logic.backtesting_review import BacktestingReview, ReviewReport, TradeRecord
        from logic.backtest_engine import BacktestMetrics
        reviewer = BacktestingReview()
        print("   [SUCCESS] BacktestingReview 创建成功")
    except Exception as e:
        print(f"   [ERROR] 测试失败: {e}")
    
    # 4. 测试UI模块
    print("\n4. 测试UI模块...")
    try:
        from ui.midway_strategy import render_midway_strategy_tab
        from ui.buy_point_scanner import render_buy_point_scanner_tab
        from ui.backtesting_review import render_backtesting_review_tab
        print("   [SUCCESS] 所有UI模块导入成功")
    except Exception as e:
        print(f"   [ERROR] UI模块测试失败: {e}")
    
    # 5. 测试数据结构
    print("\n5. 测试数据结构...")
    try:
        # 测试 MidwaySignal
        signal = MidwaySignal(
            stock_code="000001",
            stock_name="平安银行",
            signal_date="2024-01-01",
            entry_price=10.0,
            stop_loss=9.5,
            target_price=11.0,
            signal_strength=0.8,
            risk_level="中",
            reasons=["均线支撑", "成交量配合"],
            confidence=0.75
        )
        print(f"   [SUCCESS] MidwaySignal 创建成功: {signal.stock_name}")
        
        # 测试 BuySignal
        buy_signal = BuySignal(
            stock_code="000002",
            stock_name="万科A",
            scan_date="2024-01-01",
            signal_type="突破买点",
            entry_price=20.0,
            stop_loss=19.0,
            target_price=22.0,
            signal_score=85,
            risk_level="低",
            reasons=["突破MA20", "RSI金叉"],
            technical_indicators={"rsi": 60.0, "macd": 0.5}
        )
        print(f"   [SUCCESS] BuySignal 创建成功: {buy_signal.stock_name}")
        
        # 测试 TradeRecord
        trade = TradeRecord(
            date="2024-01-01",
            stock_code="000001",
            stock_name="平安银行",
            action="BUY",
            price=10.0,
            quantity=1000,
            amount=10000,
            pnl=500,
            pnl_ratio=0.05,
            strategy="测试策略"
        )
        print(f"   [SUCCESS] TradeRecord 创建成功: {trade.action} {trade.stock_name}")
        
    except Exception as e:
        print(f"   [ERROR] 数据结构测试失败: {e}")
    
    print("\n"+"="*50)
    print("所有测试完成！")
    print("="*50)


if __name__ == "__main__":
    test_new_features()