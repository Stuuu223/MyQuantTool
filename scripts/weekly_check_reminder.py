"""
每周优化检查提醒脚本

功能：
1. 提醒用户检查优化清单
2. 显示本周待办事项
3. 记录检查历史

使用方式：
- 手动运行：python scripts/weekly_check_reminder.py
- 定时任务：使用 Windows 任务计划程序每周运行一次
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def print_header():
    """打印标题"""
    print("=" * 70)
    print("📅 MyQuantTool 每周优化检查提醒")
    print("=" * 70)
    print(f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 检查日期: {datetime.now().strftime('%Y年%m月%d日')} {['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.now().weekday()]}")
    print()

def print_weekly_tasks():
    """打印每周任务"""
    print("=" * 70)
    print("📋 本周待办事项")
    print("=" * 70)
    print()
    print("✅ 1. 检查系统日志，查找潜在问题")
    print("   - 查看 logs/ 目录下的日志文件")
    print("   - 搜索 ERROR 和 WARNING 关键词")
    print()
    print("✅ 2. 检查数据源可用性")
    print("   - 测试 AkShare 连接")
    print("   - 测试 QMT 连接")
    print("   - 检查数据更新是否正常")
    print()
    print("✅ 3. 检查测试覆盖率")
    print("   - 运行 pytest 测试")
    print("   - 查看测试覆盖率报告")
    print("   - 修复失败的测试")
    print()
    print("✅ 4. 更新优化进度")
    print("   - 查看 docs/dev/OPTIMIZATION_TODO.md")
    print("   - 更新已完成的优化项目")
    print("   - 规划下周的优化任务")
    print()

def print_optimization_focus():
    """打印当前优化重点"""
    print("=" * 70)
    print("🎯 当前优化重点（高优先级）")
    print("=" * 70)
    print()
    print("1️⃣  数据获取优化")
    print("   - [ ] 实现数据缓存机制")
    print("   - [ ] 优化 API 调用频率")
    print()
    print("2️⃣  代码质量优化")
    print("   - [ ] 统一代码风格（使用 Black）")
    print("   - [ ] 添加类型提示（Type Hints）")
    print("   - [ ] 完善文档字符串")
    print()
    print("3️⃣  测试覆盖")
    print("   - [ ] 核心功能单元测试（覆盖率 > 80%）")
    print("   - [ ] 集成测试")
    print("   - [ ] 边界条件测试")
    print()
    print("4️⃣  功能优化")
    print("   - [ ] 完善诱多陷阱检测算法")
    print("   - [ ] 优化资金分类准确性")
    print("   - [ ] 改进风险评分模型")
    print()

def print_quick_commands():
    """打印快速命令"""
    print("=" * 70)
    print("🔧 快速命令")
    print("=" * 70)
    print()
    print("查看优化清单:")
    print("  type docs\\dev\\OPTIMIZATION_TODO.md")
    print()
    print("运行测试:")
    print("  pytest")
    print()
    print("检查日志:")
    print("  dir logs\\")
    print()
    print("格式化代码:")
    print("  black .")
    print()
    print("提交代码:")
    print("  git add .")
    print("  git commit -m \"chore: 每周优化检查\"")
    print("  git push")
    print()

def print_resources():
    """打印资源链接"""
    print("=" * 70)
    print("📚 相关资源")
    print("=" * 70)
    print()
    print("优化清单:")
    print("  docs/dev/OPTIMIZATION_TODO.md")
    print()
    print("System Prompt:")
    print("  .iflow/SYSTEM_PROMPT.md")
    print()
    print("项目结构:")
    print("  PROJECT_STRUCTURE.md")
    print()
    print("用户指南:")
    print("  docs/user-guide/README_快速开始.md")
    print()

def record_check_history():
    """记录检查历史"""
    history_file = "docs/dev/check_history.txt"

    # 确保目录存在
    os.makedirs(os.path.dirname(history_file), exist_ok=True)

    # 记录检查
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 每周优化检查\n")

    print("=" * 70)
    print("📊 检查历史")
    print("=" * 70)
    print()
    print(f"✅ 检查记录已保存到: {history_file}")
    print()

    # 显示最近5次检查
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                print("最近检查记录:")
                for line in lines[-5:]:
                    print(f"  - {line.strip()}")
    except FileNotFoundError:
        print("这是第一次检查")
    print()

def main():
    """主函数"""
    print_header()
    print_weekly_tasks()
    print_optimization_focus()
    print_quick_commands()
    print_resources()
    record_check_history()

    print("=" * 70)
    print("🎉 检查完成！")
    print("=" * 70)
    print()
    print("💡 提示:")
    print("   - 建议每周执行一次此脚本")
    print("   - 可以使用 Windows 任务计划程序自动运行")
    print("   - 完成后记得更新 OPTIMIZATION_TODO.md")
    print()

if __name__ == "__main__":
    main()
