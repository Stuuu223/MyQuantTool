"""
提取并迁移UI模块功能
"""

import re

# 定义要提取的功能及其对应的行号范围
FUNCTIONS = {
    'backtest': {
        'start': 1094,
        'end': 1803,
        'file': 'main_old.py'
    },
    'long_hu_bang': {
        'start': 1936,
        'end': 2156,
        'file': 'main_old.py'
    },
    'auction': {
        'start': 2360,
        'end': 2734,
        'file': 'main_old.py'
    },
    'sentiment': {
        'start': 2735,
        'end': 3469,
        'file': 'main_old.py'
    },
    'hot_topics': {
        'start': 3470,
        'end': 3619,
        'file': 'main_old.py'
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

def update_ui_module(module_name, code):
    """更新UI模块文件"""
    module_path = f'ui/{module_name}.py'
    
    try:
        # 读取现有模块
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换占位符
        new_content = content.replace('    st.info("功能正在开发中...")', code)
        
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
        
        if code:
            success = update_ui_module(func_name, code)
            if success:
                print(f"  -> {func_name} migrated successfully")
            else:
                print(f"  -> {func_name} migration failed")
        else:
            print(f"  -> {func_name} extraction failed")
    
    print("\n" + "=" * 50)
    print("Migration complete!")