#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 智能复盘系统测试脚本

测试内容：
1. AutoReviewerV18_7 功能测试
2. 数据获取性能测试
3. UI 渲染测试

Author: iFlow CLI
Version: V18.6.1
"""

import sys
import time
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.version import get_version, print_version
from logic.auto_reviewer_v18_7 import get_auto_reviewer_v18_7

logger = get_logger(__name__)


def test_version():
    """测试版本号"""
    print("\n" + "="*60)
    print("测试 1: 版本号管理")
    print("="*60)
    
    print_version()
    
    version = get_version()
    assert version == "V18.6.1", f"版本号错误: {version}"
    
    print("✅ 版本号测试通过")
    return True


def test_auto_reviewer():
    """测试 AutoReviewerV18_7 功能"""
    print("\n" + "="*60)
    print("测试 2: AutoReviewerV18_7 功能")
    print("="*60)
    
    try:
        # 初始化
        reviewer = get_auto_reviewer_v18_7()
        
        # 测试获取昨天数据
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        
        print(f"📅 测试日期: {date_str}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 生成复盘数据
        data = reviewer.generate_report_data(date_str)
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"⏱️  复盘耗时: {elapsed_time:.2f} 秒")
        
        # 验证数据结构
        assert 'summary' in data, "缺少 summary 字段"
        assert 'missed_opportunities' in data, "缺少 missed_opportunities 字段"
        assert 'avoided_traps' in data, "缺少 avoided_traps 字段"
        assert 'execution_score' in data, "缺少 execution_score 字段"
        
        # 验证摘要数据
        summary = data['summary']
        assert 'date' in summary, "缺少 date 字段"
        assert 'total_limit_up' in summary, "缺少 total_limit_up 字段"
        assert 'market_temperature' in summary, "缺少 market_temperature 字段"
        assert 'system_capture_rate' in summary, "缺少 system_capture_rate 字段"
        
        print("✅ AutoReviewerV18_7 功能测试通过")
        print(f"   - 测试日期: {summary['date']}")
        print(f"   - 涨停数量: {summary['total_limit_up']}")
        print(f"   - 市场温度: {summary['market_temperature']}")
        print(f"   - 系统捕获率: {summary['system_capture_rate']}")
        print(f"   - 执行力评分: {data['execution_score']}")
        print(f"   - 错失机会: {len(data['missed_opportunities'])} 只")
        print(f"   - 避开陷阱: {len(data['avoided_traps'])} 只")
        
        # 性能评估
        if elapsed_time < 3:
            print(f"✅ 性能优秀: {elapsed_time:.2f} 秒")
        elif elapsed_time < 10:
            print(f"⚠️  性能一般: {elapsed_time:.2f} 秒")
        else:
            print(f"❌ 性能较差: {elapsed_time:.2f} 秒")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ AutoReviewerV18_7 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_module():
    """测试 UI 模块"""
    print("\n" + "="*60)
    print("测试 3: UI 模块导入")
    print("="*60)
    
    try:
        # 尝试导入 UI 模块
        from ui.v18_7_review_dashboard import render_review_dashboard
        
        print("✅ UI 模块导入成功")
        print("   - 模块名称: v18_7_review_dashboard")
        print("   - 函数名称: render_review_dashboard")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ UI 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("测试 4: 系统集成")
    print("="*60)
    
    try:
        # 测试主程序是否包含 V18.7 复盘功能
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否导入了 V18.7 复盘模块
        assert 'v18_7_review_dashboard' in content, "main.py 没有导入 V18.7 复盘模块"
        
        # 检查是否包含了智能复盘选项
        assert '智能复盘' in content, "main.py 没有包含智能复盘选项"
        
        print("✅ 系统集成测试通过")
        print("   - main.py 已导入 V18.7 复盘模块")
        print("   - main.py 已包含智能复盘选项")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 系统集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("V18.7 智能复盘系统测试")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(("版本号管理", test_version()))
    results.append(("AutoReviewerV18_7 功能", test_auto_reviewer()))
    results.append(("UI 模块导入", test_ui_module()))
    results.append(("系统集成", test_integration()))
    
    # 打印测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    
    if failed == 0:
        print("\n🎉 所有测试通过！V18.7 智能复盘系统开发成功！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())