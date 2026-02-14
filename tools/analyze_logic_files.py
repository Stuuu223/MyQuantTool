"""
分析logic目录文件使用情况
找出未使用和过时的文件
"""
import os
import re
from pathlib import Path
from typing import Set, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGIC_DIR = PROJECT_ROOT / "logic"

# 识别过时/未使用文件的模式
PATTERNS_TO_DELETE = {
    # 备份文件
    r'.*_backup\.py$': '备份文件',
    r'.*_v\d+_.*\.py$': '旧版本文件',
    r'.*_v\d+\.py$': '旧版本文件',
    
    # 临时/测试文件
    r'test_.*\.py$': '测试文件',
    r'debug_.*\.py$': '调试文件',
    r'temp_.*\.py$': '临时文件',
    
    # 重复文件（有v12.1.0新版本）
    r'triple_funnel_scanner\.py$': '已被v121替代',
}

# 识别需要移动的文件
PATTERNS_TO_MOVE = {
    # 数据相关
    r'^data_.*\.py$': 'data',
    r'^fund_flow.*\.py$': 'data',
    r'^cache.*\.py$': 'data',
    r'^equity_data.*\.py$': 'data',
    r'^qmt_.*\.py$': 'data',
    r'^realtime_data.*\.py$': 'data',
    
    # 策略相关
    r'.*_strategy\.py$': 'strategies',
    r'.*_detector\.py$': 'strategies',
    r'.*_engine\.py$': 'strategies',
    r'^low_suction.*\.py$': 'strategies',
    r'^dragon_tactics\.py$': 'strategies',
    r'^trap_detector.*\.py$': 'strategies',
    
    # 信号相关
    r'^signal.*\.py$': 'signals',
    
    # 板块相关
    r'^sector.*\.py$': 'sectors',
    
    # 情绪相关
    r'^sentiment.*\.py$': 'sentiment',
    r'^market_cycle\.py$': 'sentiment',
    r'^market_phase.*\.py$': 'sentiment',
    r'^market_status\.py$': 'sentiment',
    
    # 竞价相关
    r'^auction.*\.py$': 'auction',
    
    # 回测相关
    r'^backtest.*\.py$': 'backtest',
    r'^slippage.*\.py$': 'backtest',
    
    # 监控相关
    r'^monitor.*\.py$': 'monitors',
    r'.*_monitor\.py$': 'monitors',
    
    # 风控相关
    r'^risk.*\.py$': 'risk',
    r'^position.*\.py$': 'risk',
    r'^trade_gatekeeper\.py$': 'risk',
    
    # 交易相关
    r'^broker.*\.py$': 'trading',
    r'^live_trading.*\.py$': 'trading',
    r'^paper_trading.*\.py$': 'trading',
    
    # AI/ML相关
    r'^lstm.*\.py$': 'ml',
    r'^ml_.*\.py$': 'ml',
    r'^ai_.*\.py$': 'ml',
    r'^feature_engineer\.py$': 'ml',
    r'.*_learning.*\.py$': 'ml',
    r'.*_predictor\.py$': 'ml',
    
    # 分析器相关
    r'^capital.*\.py$': 'analyzers',
    r'^kline.*\.py$': 'analyzers',
    r'^rolling.*\.py$': 'analyzers',
}

def analyze_files() -> Dict[str, List[str]]:
    """分析logic目录的文件"""
    files_to_delete = []
    files_to_move = {}
    
    # 扫描logic根目录的所有.py文件
    for file_path in LOGIC_DIR.glob("*.py"):
        filename = file_path.name
        
        # 检查是否需要删除
        for pattern, reason in PATTERNS_TO_DELETE.items():
            if re.match(pattern, filename):
                files_to_delete.append({
                    'file': filename,
                    'reason': reason
                })
                break
        else:
            # 检查是否需要移动
            for pattern, target_dir in PATTERNS_TO_MOVE.items():
                if re.match(pattern, filename):
                    files_to_move.setdefault(target_dir, []).append(filename)
                    break
    
    return {
        'delete': files_to_delete,
        'move': files_to_move
    }

def print_report(result: Dict):
    """打印分析报告"""
    print("=" * 80)
    print("Logic目录文件分析报告")
    print("=" * 80)
    
    # 统计
    total_files = len(list(LOGIC_DIR.glob("*.py")))
    delete_count = len(result['delete'])
    move_count = sum(len(files) for files in result['move'].values())
    keep_count = total_files - delete_count
    
    print(f"\n总文件数: {total_files}")
    print(f"建议删除: {delete_count} 个文件")
    print(f"建议移动: {move_count} 个文件")
    print(f"保留在根目录: {keep_count} 个文件")
    
    # 删除文件列表
    if result['delete']:
        print(f"\n{'='*80}")
        print("建议删除的文件:")
        print(f"{'='*80}")
        for item in sorted(result['delete'], key=lambda x: x['file']):
            print(f"  {item['file']:<50} ({item['reason']})")
    
    # 移动文件列表
    if result['move']:
        print(f"\n{'='*80}")
        print("建议移动的文件:")
        print(f"{'='*80}")
        for target_dir, files in sorted(result['move'].items()):
            print(f"\n  移动到 {target_dir}/ ({len(files)}个文件):")
            for filename in sorted(files)[:10]:  # 只显示前10个
                print(f"    - {filename}")
            if len(files) > 10:
                print(f"    ... 还有 {len(files) - 10} 个文件")
    
    # 保留在根目录的文件
    print(f"\n{'='*80}")
    print("保留在根目录的文件:")
    print(f"{'='*80}")
    deleted_filenames = {item['file'] for item in result['delete']}
    moved_filenames = set()
    for files in result['move'].values():
        moved_filenames.update(files)
    
    keep_files = []
    for file_path in sorted(LOGIC_DIR.glob("*.py")):
        if file_path.name not in deleted_filenames and file_path.name not in moved_filenames:
            keep_files.append(file_path.name)
    
    for filename in keep_files[:20]:  # 只显示前20个
        print(f"  - {filename}")
    if len(keep_files) > 20:
        print(f"  ... 还有 {len(keep_files) - 20} 个文件")

def main():
    """主函数"""
    result = analyze_files()
    print_report(result)
    
    # 保存详细报告
    with open(PROJECT_ROOT / "logic_analysis_report.txt", 'w', encoding='utf-8') as f:
        f.write(f"Logic目录文件分析报告\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"总文件数: {len(list(LOGIC_DIR.glob('*.py')))}\n")
        f.write(f"建议删除: {len(result['delete'])} 个文件\n")
        f.write(f"建议移动: {sum(len(files) for files in result['move'].values())} 个文件\n\n")
        
        if result['delete']:
            f.write("建议删除的文件:\n")
            for item in sorted(result['delete'], key=lambda x: x['file']):
                f.write(f"  {item['file']} ({item['reason']})\n")
        
        if result['move']:
            f.write("\n建议移动的文件:\n")
            for target_dir, files in sorted(result['move'].items()):
                f.write(f"\n{target_dir}/ ({len(files)}个文件):\n")
                for filename in sorted(files):
                    f.write(f"  - {filename}\n")
    
    print(f"\n详细报告已保存: {PROJECT_ROOT / 'logic_analysis_report.txt'}")

if __name__ == "__main__":
    main()