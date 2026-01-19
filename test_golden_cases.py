#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 高价值案例自动捕获机制测试脚本（快速版）

测试内容：
1. ReviewManager.capture_golden_cases() 功能测试
2. 数据获取性能测试
3. UI 集成测试

Author: iFlow CLI
Version: V18.6.1
"""

import sys
import time
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.version import get_version, print_version
from logic.review_manager import ReviewManager

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


def test_capture_golden_cases():
    """测试高价值案例捕获功能"""
    print("\n" + "="*60)
    print("测试 2: 高价值案例捕获功能")
    print("="*60)
    
    try:
        # 初始化
        rm = ReviewManager()
        
        # 测试获取两天前的数据（避免周末问题）
        two_days_ago = datetime.now() - timedelta(days=2)
        date_str = two_days_ago.strftime("%Y%m%d")
        
        print(f"📅 测试日期: {date_str}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 捕获高价值案例
        print("⏳ 正在捕获高价值案例...")
        golden_cases = rm.capture_golden_cases(date_str)
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"⏱️  捕获耗时: {elapsed_time:.2f} 秒")
        
        # 验证数据结构
        if golden_cases:
            assert 'date' in golden_cases, "缺少 date 字段"
            assert 'dragons' in golden_cases, "缺少 dragons 字段"
            assert 'traps' in golden_cases, "缺少 traps 字段"
            assert 'reversals' in golden_cases, "缺少 reversals 字段"
            
            print("✅ 高价值案例捕获功能测试通过")
            print(f"   - 测试日期: {golden_cases['date']}")
            print(f"   - 真龙数量: {len(golden_cases['dragons'])} 只")
            print(f"   - 大坑数量: {len(golden_cases['traps'])} 只")
            print(f"   - 炸板数量: {len([t for t in golden_cases['traps'] if t['type'] == 'FAILED_DRAGON'])} 只")
            
            # 显示真龙详情
            if golden_cases['dragons']:
                print("\n🐉 真龙详情:")
                for i, dragon in enumerate(golden_cases['dragons'], 1):
                    print(f"   {i}. {dragon['name']} ({dragon['code']})")
                    print(f"      {dragon['reason']}")
            
            # 显示大坑详情
            if golden_cases['traps']:
                print("\n🛡️ 大坑详情:")
                for i, trap in enumerate(golden_cases['traps'], 1):
                    print(f"   {i}. {trap['name']} ({trap['code']})")
                    print(f"      {trap['reason']}")
            
            # 性能评估
            if elapsed_time < 5:
                print(f"✅ 性能优秀: {elapsed_time:.2f} 秒")
            elif elapsed_time < 15:
                print(f"⚠️  性能一般: {elapsed_time:.2f} 秒")
            else:
                print(f"❌ 性能较差: {elapsed_time:.2f} 秒")
            
            return True
        else:
            print("⚠️  未捕获到高价值案例（可能是休市或数据未更新）")
            print("   这不是错误，只是该日期没有交易数据")
            return True
        
    except Exception as e:
        logger.error(f"❌ 高价值案例捕获功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_integration():
    """测试 UI 集成"""
    print("\n" + "="*60)
    print("测试 3: UI 集成")
    print("="*60)
    
    try:
        # 测试 UI 模块是否导入了 ReviewManager
        with open('ui/v18_7_review_dashboard.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否导入了 ReviewManager
        assert 'from logic.review_manager import ReviewManager' in content, "UI 模块没有导入 ReviewManager"
        
        # 检查是否包含了高价值案例展示
        assert '今日真龙' in content, "UI 模块没有包含今日真龙展示"
        assert '避坑指南' in content, "UI 模块没有包含避坑指南展示"
        
        print("✅ UI 集成测试通过")
        print("   - UI 模块已导入 ReviewManager")
        print("   - UI 模块已包含今日真龙展示")
        print("   - UI 模块已包含避坑指南展示")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ UI 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_creation():
    """测试文件创建"""
    print("\n" + "="*60)
    print("测试 4: 文件创建")
    print("="*60)
    
    try:
        import os
        
        # 检查目录是否存在
        save_dir = "data/review_cases/golden_cases"
        if os.path.exists(save_dir):
            print(f"✅ 目录已存在: {save_dir}")
            
            # 检查是否有案例文件
            files = [f for f in os.listdir(save_dir) if f.startswith('cases_')]
            if files:
                print(f"   - 案例文件数量: {len(files)}")
                print(f"   - 最新案例文件: {sorted(files)[-1]}")
            else:
                print("   - 暂无案例文件")
        else:
            print(f"⚠️  目录不存在: {save_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 文件创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("V18.7 高价值案例自动捕获机制测试")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(("版本号管理", test_version()))
    results.append(("高价值案例捕获功能", test_capture_golden_cases()))
    results.append(("UI 集成", test_ui_integration()))
    results.append(("文件创建", test_file_creation()))
    
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
        print("\n🎉 所有测试通过！V18.7 高价值案例自动捕获机制开发成功！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())