#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全清理脚本：从 Git 历史中删除敏感配置文件

P0 安全事故处理：
1. config/config.json 包含明文 API Key
2. 需要从 Git 历史中彻底删除
3. 需要轮换 API Key

使用方法：
1. python scripts/security_cleanup.py --check  # 检查敏感文件
2. python scripts/security_cleanup.py --remove  # 从 Git 历史中删除
3. python scripts/security_cleanup.py --rotate  # 生成新的 API Key 占位符
"""

import sys
from pathlib import Path
import json
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_sensitive_files():
    """检查敏感文件"""
    print("=" * 80)
    print("🔍 敏感文件检查")
    print("=" * 80)
    print()

    config_json = project_root / 'config' / 'config.json'
    gitignore = project_root / '.gitignore'

    # 检查 config.json 是否在 .gitignore 中
    if gitignore.exists():
        with open(gitignore, 'r', encoding='utf-8') as f:
            gitignore_content = f.read()

        if 'config/config.json' in gitignore_content:
            print("✅ config/config.json 已在 .gitignore 中")
        else:
            print("⚠️  config/config.json 未在 .gitignore 中！")
    else:
        print("⚠️  .gitignore 文件不存在！")

    print()

    # 检查 config.json 是否在 Git 索引中
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'ls-files', 'config/config.json'],
            capture_output=True,
            text=True,
            cwd=project_root
        )

        if result.stdout.strip():
            print("⚠️  config/config.json 仍在 Git 索引中！")
            print("   需要执行：git rm --cached config/config.json")
        else:
            print("✅ config/config.json 已从 Git 索引中删除")
    except:
        print("❌ Git 命令执行失败")

    print()

    # 检查 API Key 是否泄露
    if config_json.exists():
        with open(config_json, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        api_key = config_data.get('api_key', '')
        if api_key and api_key.startswith('sk-'):
            print("⚠️  检测到明文 API Key！")
            print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
            print("   需要立即轮换！")
        else:
            print("✅ 未检测到明文 API Key")
    else:
        print("⚠️  config/config.json 文件不存在")

    print()


def show_api_key_history():
    """显示 API Key 提交历史"""
    print("=" * 80)
    print("📜 API Key 提交历史")
    print("=" * 80)
    print()

    import subprocess
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', '--all', '--', 'config/config.json'],
            capture_output=True,
            text=True,
            cwd=project_root
        )

        if result.stdout.strip():
            print("config/config.json 提交历史：")
            print(result.stdout)
        else:
            print("✅ config/config.json 无提交历史")
    except:
        print("❌ Git 命令执行失败")

    print()


def generate_cleanup_commands():
    """生成清理命令"""
    print("=" * 80)
    print("🛠️  清理命令生成")
    print("=" * 80)
    print()

    print("步骤1：从 Git 索引中删除（保留本地文件）")
    print("  git rm --cached config/config.json")
    print()

    print("步骤2：提交删除操作")
    print('  git commit -m "security: 移除敏感配置文件（config.json）"')
    print()

    print("步骤3：从 Git 历史中彻底删除（需要 force push）")
    print("  ⚠️  警告：此操作会重写 Git 历史，需要团队协作！")
    print()
    print("  方法1：使用 git filter-branch（旧版）")
    print("  git filter-branch --force --index-filter \\")
    print('    "git rm --cached --ignore-unmatch config/config.json" \\')
    print("    --prune-empty --tag-name-filter cat -- --all")
    print()
    print("  方法2：使用 git filter-repo（推荐，需要安装）")
    print("  pip install git-filter-repo")
    print("  git filter-repo --path config/config.json --invert-paths")
    print()

    print("步骤4：强制推送到远程")
    print("  git push origin --force --all")
    print("  git push origin --force --tags")
    print()

    print("步骤5：轮换 API Key")
    print("  1. 联系服务提供商轮换 API Key")
    print("  2. 更新 config/config.json 中的 api_key")
    print("  3. 确保新的 API Key 不会提交到 Git")
    print()

    print("步骤6：配置环境变量（推荐）")
    print("  export API_KEY='your_new_api_key'")
    print("  或在 .env 文件中配置")
    print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='安全清理脚本')
    parser.add_argument('--check', action='store_true', help='检查敏感文件')
    parser.add_argument('--history', action='store_true', help='显示 API Key 提交历史')
    parser.add_argument('--commands', action='store_true', help='生成清理命令')

    args = parser.parse_args()

    if args.check:
        check_sensitive_files()
    elif args.history:
        show_api_key_history()
    elif args.commands:
        generate_cleanup_commands()
    else:
        print("🚀 安全清理脚本")
        print()
        print("使用方法：")
        print("  python scripts/security_cleanup.py --check      # 检查敏感文件")
        print("  python scripts/security_cleanup.py --history    # 显示提交历史")
        print("  python scripts/security_cleanup.py --commands   # 生成清理命令")
        print()
        print("⚠️  警告：config/config.json 包含明文 API Key，需要立即处理！")


if __name__ == "__main__":
    main()