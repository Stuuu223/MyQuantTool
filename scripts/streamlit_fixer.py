"""
批量修复 Streamlit 弃用警告的脚本

将 use_container_width=True 替换为 width="stretch"
将 use_container_width=False 替换为 width="content"
"""

import re


def fix_streamlit_warnings(file_path='main.py'):
    """
    修复 Streamlit 弃用警告

    Args:
        file_path: 要修复的文件路径，默认为 main.py
    """
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 统计替换次数
        count_true = content.count('use_container_width=True')
        count_false = content.count('use_container_width=False')

        # 替换
        content = content.replace('use_container_width=True', 'width="stretch"')
        content = content.replace('use_container_width=False', 'width="content"')

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("OK: 修复完成！")
        print(f"   - 替换了 {count_true} 处 use_container_width=True")
        print(f"   - 替换了 {count_false} 处 use_container_width=False")
        print(f"   - 总计: {count_true + count_false} 处修改")

    except FileNotFoundError:
        print(f"ERROR: 找不到文件 {file_path}")
    except Exception as e:
        print(f"ERROR: {str(e)}")


if __name__ == '__main__':
    import os
    import sys

    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py_path = os.path.join(project_root, 'main.py')

    # 修复 main.py
    fix_streamlit_warnings(main_py_path)

    # 也可以修复其他文件
    # fix_streamlit_warnings(os.path.join(project_root, 'other_file.py'))