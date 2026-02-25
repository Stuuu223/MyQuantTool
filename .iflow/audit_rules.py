#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iFlow红线审计规则脚本 - 自愈断言系统
CTO黑科技2: Self-Healing Assertions

职责: 在代码提交前自动扫描红线违规
触发: iflow_config.yaml中redline_hooks.pre_commit_checks
输出: 违规报告，自动打回违规代码

Author: CTO架构规范
Version: V20.0
"""

import re
import sys
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json


class RedlineAuditor:
    """红线审计员 - 代码提交前强制检查"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.violations: List[Dict] = []
        self.errors = 0
        self.warnings = 0
        
    def audit_file(self, file_path: Path) -> bool:
        """审计单个文件"""
        if not file_path.exists():
            return True
            
        content = file_path.read_text(encoding='utf-8')
        
        # 检查1: 魔法数字硬编码
        self._check_magic_numbers(file_path, content)
        
        # 检查2: Tushare残留
        self._check_tushare_residue(file_path, content)
        
        # 检查3: 硬编码路径
        self._check_hardcoded_paths(file_path, content)
        
        # 检查4: For循环遍历Tick
        self._check_for_loop_tick_iteration(file_path, content)
        
        # 检查5: ConfigManager使用
        self._check_config_manager_usage(file_path, content)
        
        return self.errors == 0
    
    def _check_magic_numbers(self, file_path: Path, content: str):
        """检查魔法数字硬编码"""
        # 检测模式: 在特定上下文中出现的疑似阈值数字
        patterns = [
            (r'volume_ratio\s*[>=<]+\s*0\.[0-9]+', "量比阈值硬编码"),
            (r'turnover\s*[>=<]+\s*[0-9]+\.[0-9]+', "换手率阈值硬编码"),
            (r'threshold\s*=\s*0\.[0-9]+', "threshold硬编码"),
            (r'change_pct\s*[>=<]+\s*[0-9]+\.[0-9]+', "涨跌幅阈值硬编码"),
        ]
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # 排除从config读取的合法情况
                line_num = content[:match.start()].count('\n') + 1
                line_content = content.split('\n')[line_num - 1].strip()
                
                if 'config' not in line_content.lower() and 'get_config' not in line_content.lower():
                    self.violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'magic_number',
                        'severity': 'error',
                        'message': f"{desc}: {match.group()}",
                        'fix': '必须从ConfigManager读取配置'
                    })
                    self.errors += 1
    
    def _check_tushare_residue(self, file_path: Path, content: str):
        """检查Tushare残留"""
        patterns = [
            (r'import\s+tushare', "导入tushare模块"),
            (r'from\s+tushare', "从tushare导入"),
            (r'ts\.pro_api', "调用tushare API"),
            (r'daily_basic', "tushare daily_basic接口"),
            (r'ts_code', "tushare代码格式"),
            (r'TUSHARE_TOKEN', "tushare token引用"),
        ]
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                self.violations.append({
                    'file': str(file_path),
                    'line': line_num,
                    'type': 'tushare_residue',
                    'severity': 'error',
                    'message': desc,
                    'fix': '必须使用QMT本地数据(xtdata)'
                })
                self.errors += 1
    
    def _check_hardcoded_paths(self, file_path: Path, content: str):
        """检查硬编码路径"""
        # Windows路径: C:\xxx, D:\xxx
        # Linux/Mac路径: /home/xxx, /Users/xxx
        patterns = [
            (r'[C-Z]:\\\\[^\s\'"]+', "Windows硬编码路径"),
            (r'/home/[^\s\'"]+', "Linux硬编码路径"),
            (r'/Users/[^\s\'"]+', "Mac硬编码路径"),
        ]
        
        allowed_contexts = ['__file__', 'PathResolver', 'get_root', 'Path(__file__)']
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                line_content = content.split('\n')[line_num - 1].strip()
                
                # 检查是否在允许上下文中
                if not any(ctx in line_content for ctx in allowed_contexts):
                    self.violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'hardcoded_path',
                        'severity': 'warning',
                        'message': desc,
                        'fix': '使用PathResolver动态解析路径'
                    })
                    self.warnings += 1
    
    def _check_for_loop_tick_iteration(self, file_path: Path, content: str):
        """检查For循环遍历Tick"""
        # 检测可疑的for循环遍历Tick数据
        patterns = [
            (r'for\s+\w+\s+in\s+ticks', "for循环遍历ticks"),
            (r'for\s+\w+\s+in\s+df\.', "for循环遍历DataFrame行"),
            (r'for\s+\w+\s+in\s+tick_data', "for循环遍历tick_data"),
        ]
        
        # 允许的合法上下文（事件驱动模拟部分）
        allowed_contexts = ['event_driven', 'micro_defense', 'simulation', 'matching']
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                
                # 获取上下文（前后5行）
                lines = content.split('\n')
                context_start = max(0, line_num - 6)
                context_end = min(len(lines), line_num + 5)
                context = '\n'.join(lines[context_start:context_end])
                
                # 检查是否在允许的合法上下文中
                if not any(ctx in context.lower() for ctx in allowed_contexts):
                    self.violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'for_loop_tick',
                        'severity': 'error',
                        'message': desc,
                        'fix': '使用Pandas向量化操作(df.cumsum/apply)，严禁For循环遍历Tick'
                    })
                    self.errors += 1
    
    def _check_config_manager_usage(self, file_path: Path, content: str):
        """检查ConfigManager正确使用"""
        # 检查是否导入了ConfigManager
        has_config_import = 'get_config_manager' in content or 'ConfigManager' in content
        
        # 检查是否有硬编码阈值（在应有ConfigManager的文件中）
        if has_config_import:
            # 如果文件使用了ConfigManager，但仍有硬编码数字
            hardcoded_patterns = [
                (r'volume_ratio\s*=\s*0\.[0-9]+', "量比硬编码"),
                (r'turnover.*=\s*[0-9]+\.[0-9]+', "换手率硬编码"),
            ]
            
            for pattern, desc in hardcoded_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    self.violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'type': 'config_usage',
                        'severity': 'error',
                        'message': f"{desc}（文件已导入ConfigManager，必须从配置读取）",
                        'fix': '使用config.get("live_sniper.volume_ratio_percentile")读取配置'
                    })
                    self.errors += 1
    
    def audit_project(self, target_paths: Optional[List[str]] = None) -> Dict:
        """审计整个项目或指定路径"""
        if target_paths is None:
            target_paths = ['logic/', 'tools/', 'tasks/']
        
        for target in target_paths:
            target_path = self.project_root / target
            if target_path.is_file():
                self.audit_file(target_path)
            elif target_path.is_dir():
                for py_file in target_path.rglob('*.py'):
                    # 跳过测试文件和缓存
                    if 'test_' not in py_file.name and '__pycache__' not in str(py_file):
                        self.audit_file(py_file)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """生成审计报告"""
        report = {
            'summary': {
                'total_errors': self.errors,
                'total_warnings': self.warnings,
                'total_violations': len(self.violations),
                'pass': self.errors == 0
            },
            'violations': self.violations,
            'recommendations': []
        }
        
        if self.errors > 0:
            report['recommendations'].append("存在致命违规，必须修复后才能提交")
            report['recommendations'].append(f"共发现{self.errors}个错误，{self.warnings}个警告")
            
            # 按类型分组
            by_type = {}
            for v in self.violations:
                vtype = v['type']
                by_type[vtype] = by_type.get(vtype, 0) + 1
            
            report['by_type'] = by_type
        else:
            report['recommendations'].append("✅ 代码通过所有红线审计")
        
        return report
    
    def print_report(self, report: Dict):
        """打印审计报告"""
        print("=" * 70)
        print("🔍 iFlow红线审计报告")
        print("=" * 70)
        
        summary = report['summary']
        if summary['pass']:
            print("\n✅ 所有检查通过！代码符合CTO架构规范")
        else:
            print(f"\n❌ 审计失败: {summary['total_errors']}个错误, {summary['total_warnings']}个警告")
            print("\n违规详情:")
            print("-" * 70)
            
            for v in report['violations']:
                severity_emoji = "🔴" if v['severity'] == 'error' else "🟡"
                print(f"\n{severity_emoji} [{v['type'].upper()}] {v['file']}:{v['line']}")
                print(f"   问题: {v['message']}")
                print(f"   修复: {v['fix']}")
        
        print("\n" + "=" * 70)
        
        return summary['pass']


def main():
    """主入口 - 命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='iFlow红线审计工具')
    parser.add_argument('--path', '-p', nargs='+', help='审计路径')
    parser.add_argument('--json', '-j', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    
    auditor = RedlineAuditor()
    report = auditor.audit_project(args.path)
    
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if report['summary']['pass'] else 1)
    else:
        passed = auditor.print_report(report)
        sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
