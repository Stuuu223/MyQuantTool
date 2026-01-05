"""
提取并迁移UI模块功能
"""

import re

# 定义要提取的功能及其对应的行号范围
FUNCTIONS = {
    'limit_up': {
        'start': 4114,
        'end': 4258,
        'file': 'main_old.py',
        'placeholder': 'st.info("💡 打板预测功能正在开发中...")'
    },
    'smart_recommend': {
        'start': 4259,
        'end': 4407,
        'file': 'main_old.py',
        'placeholder': 'st.info("💡 智能推荐功能正在开发中...")'
    },
    'risk': {
        'start': 4408,
        'end': 4516,
        'file': 'main_old.py',
        'placeholder': 'st.info("💡 风险管理功能正在开发中...")'
    },
    'history': {
        'start': 4517,
        'end': 4598,
        'file': 'main_old.py',
        'placeholder': 'st.info("💡 历史记录功能正在开发中...")'
    },
    'settings': {
        'start': 4599,
        'end': 4685,
        'file': 'main_old.py',
        'placeholder': 'st.info("💡 系统设置功能正在开发中...")'
    }
}

def extract_code(file_path, start_line, end_line):
    """从文件中提取指定行号的代码"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 提取代码（行号从1开始）
        code_lines = lines[start_line-1:end_line]
        code = ''.join(code_lines)

        # 移除with tab_xxx:声明
        code = re.sub(r'with tab_\w+:\s*', '', code)

        return code
    except Exception as e:
        print(f"Error extracting code: {e}")
        return None

def update_ui_module(module_name, code, placeholder):
    """更新UI模块文件"""
    module_path = f'ui/{module_name}.py'

    try:
        # 读取现有模块
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换占位符
        new_content = content.replace(placeholder, code)

        # 写回文件
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"Success: {module_name} updated")
        return True
    except Exception as e:
        print(f"Error updating {module_name}: {e}")
        return False

if __name__ == '__main__':
    print("Extracting and migrating UI modules...")
    print("=" * 50)

    for func_name, info in FUNCTIONS.items():
        print(f"\nProcessing {func_name}...")
        code = extract_code(info['file'], info['start'], info['end'])
        placeholder = info.get('placeholder', '    st.info("功能正在开发中...")')

        if code:
            success = update_ui_module(func_name, code, placeholder)
            if success:
                print(f"  -> {func_name} migrated successfully")
            else:
                print(f"  -> {func_name} migration failed")
        else:
            print(f"  -> {func_name} extraction failed")

    print("\n" + "=" * 50)
    print("Migration complete!")