import os
import shutil
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Set
import logging
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目现有模块
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # 如果导入失败，使用标准logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)


class ArchiveCleanupAnalyzer:
    """归档文件清理分析器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.backup_dir = self.project_root / "temp" / "cleanup_backup"
        self.log_dir = self.project_root / "logs"

        # 配置
        self.max_age_hours = 24  # 最大保留时间（小时）
        self.protected_patterns = [
            # 绝对保护的目录和文件
            "qmt_data",
            "datadir",
            "log",
            "quoter",
            "cache",
            "data/stock_names.json",
            "data/stock_sector_map.json",
            "data/monitor_state.json",
            "data/scheduled_alerts.json",
            "*.db",
            "*.sqlite",
            "*.lock",
        ]

        # 高价值案例（保留）
        self.preserve_cases = [
            "300997",  # 欢乐家诱多案例
            "603697",  # 有友食品游资案例
        ]

        # 统计信息
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'expired_files': 0,
            'expired_size': 0,
            'protected_files': 0,
            'preserved_files': 0,
            'deleted_files': 0,
            'deleted_size': 0,
            'backed_up_files': 0,
            'backed_up_size': 0,
        }

        logger.info(f"✅ [归档清理] 初始化完成，项目根目录: {self.project_root}")

    def scan_data_directory(self) -> List[Dict]:
        """扫描data目录，分析文件情况"""
        logger.info(f"📊 [归档清理] 开始扫描data目录: {self.data_dir}")

        if not self.data_dir.exists():
            logger.warning(f"⚠️ [归档清理] data目录不存在: {self.data_dir}")
            return []

        files_info = []
        current_time = time.time()

        # 遍历data目录
        for item in self.data_dir.rglob("*"):
            if not item.is_file():
                continue

            try:
                # 获取文件信息
                file_stat = item.stat()
                file_size = file_stat.st_size
                mod_time = file_stat.st_mtime
                age_hours = (current_time - mod_time) / 3600

                # 判断是否过期
                is_expired = age_hours > self.max_age_hours

                # 判断是否受保护
                is_protected = self._is_protected(item)

                # 判断是否是高价值案例
                is_preserve = self._is_preserve_case(item)

                file_info = {
                    'path': str(item.relative_to(self.project_root)),
                    'full_path': str(item),
                    'size': file_size,
                    'age_hours': age_hours,
                    'mod_time': datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_expired': is_expired,
                    'is_protected': is_protected,
                    'is_preserve': is_preserve,
                    'extension': item.suffix,
                    'directory': str(item.parent.relative_to(self.project_root)),
                }

                files_info.append(file_info)

                # 更新统计
                self.stats['total_files'] += 1
                self.stats['total_size'] += file_size

                if is_expired:
                    self.stats['expired_files'] += 1
                    self.stats['expired_size'] += file_size

                if is_protected:
                    self.stats['protected_files'] += 1

                if is_preserve:
                    self.stats['preserved_files'] += 1

            except Exception as e:
                logger.error(f"❌ [归档清理] 分析文件失败: {item} - {e}")
                continue

        logger.info(
            f"✅ [归档清理] 扫描完成: "
            f"总文件{self.stats['total_files']}个, "
            f"总大小{self._format_size(self.stats['total_size'])}, "
            f"过期{self.stats['expired_files']}个 "
            f"({self._format_size(self.stats['expired_size'])})"
        )

        return files_info

    def analyze_cleanup_candidates(self, files_info: List[Dict], force: bool = False) -> List[Dict]:
        """分析清理候选文件"""
        logger.info(f"🔍 [归档清理] 分析清理候选文件 (force={force})")

        candidates = []

        for file_info in files_info:
            # 跳过受保护的文件
            if file_info['is_protected']:
                continue

            # 跳过高价值案例
            if file_info['is_preserve']:
                continue

            # 判断是否需要清理
            if force:
                # 强制模式：删除所有过期文件
                if file_info['is_expired']:
                    candidates.append(file_info)
            else:
                # 保守模式：只清理明显无用的文件
                # 1. 已过期且无依赖的日志文件
                # 2. 已过期且无依赖的临时文件
                # 3. 已过期且无依赖的分析结果文件
                if file_info['is_expired']:
                    # 检查文件扩展名
                    ext = file_info['extension'].lower()
                    directory = file_info['directory']

                    # 保守清理条件
                    if (
                        ext in ['.log', '.txt', '.tmp', '.bak'] or  # 日志和临时文件
                        'stock_analysis' in directory or  # 股票分析结果
                        'scan_results' in directory or  # 扫描结果
                        'rebuild_snapshots' in directory  # 重建快照
                    ):
                        candidates.append(file_info)

        logger.info(
            f"✅ [归档清理] 分析完成: "
            f"清理候选{len(candidates)}个, "
            f"大小{self._format_size(sum(f['size'] for f in candidates))}"
        )

        return candidates

    def backup_files(self, candidates: List[Dict]) -> bool:
        """备份文件到temp/cleanup_backup/"""
        if not candidates:
            return True

        logger.info(f"💾 [归档清理] 开始备份{len(candidates)}个文件...")

        try:
            # 创建备份目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / timestamp
            backup_path.mkdir(parents=True, exist_ok=True)

            # 备份文件
            for file_info in candidates:
                src_path = Path(file_info['full_path'])
                rel_path = Path(file_info['path'])
                dst_path = backup_path / rel_path

                # 创建目标目录
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                # 复制文件
                shutil.copy2(src_path, dst_path)

                self.stats['backed_up_files'] += 1
                self.stats['backed_up_size'] += file_info['size']

            logger.info(
                f"✅ [归档清理] 备份完成: "
                f"{self.stats['backed_up_files']}个文件, "
                f"{self._format_size(self.stats['backed_up_size'])}, "
                f"备份目录: {backup_path}"
            )

            return True

        except Exception as e:
            logger.error(f"❌ [归档清理] 备份失败: {e}")
            return False

    def cleanup_files(self, candidates: List[Dict], dry_run: bool = False) -> bool:
        """清理文件"""
        if not candidates:
            logger.info("ℹ️ [归档清理] 没有文件需要清理")
            return True

        if dry_run:
            logger.info(f"🔍 [归档清理] 模拟运行模式，不会实际删除文件")
            for file_info in candidates:
                logger.info(f"  将删除: {file_info['path']} ({self._format_size(file_info['size'])})")
            return True

        logger.info(f"🗑️ [归档清理] 开始清理{len(candidates)}个文件...")

        try:
            for file_info in candidates:
                file_path = Path(file_info['full_path'])

                # 删除文件
                file_path.unlink()

                self.stats['deleted_files'] += 1
                self.stats['deleted_size'] += file_info['size']

                logger.debug(f"✅ 已删除: {file_info['path']}")

            logger.info(
                f"✅ [归档清理] 清理完成: "
                f"{self.stats['deleted_files']}个文件, "
                f"{self._format_size(self.stats['deleted_size'])}"
            )

            return True

        except Exception as e:
            logger.error(f"❌ [归档清理] 清理失败: {e}")
            return False

    def generate_report(self, candidates: List[Dict], dry_run: bool = False) -> Tuple[str, str]:
        """生成清理报告（JSON + TXT）"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # JSON报告
        json_report = {
            'timestamp': timestamp,
            'dry_run': dry_run,
            'stats': self.stats,
            'protected_patterns': self.protected_patterns,
            'preserve_cases': self.preserve_cases,
            'candidates': candidates,
        }

        json_path = self.log_dir / f"cleanup_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        # TXT报告
        txt_lines = [
            "=" * 80,
            "归档文件清理报告",
            "=" * 80,
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"项目根目录: {self.project_root}",
            f"运行模式: {'模拟运行' if dry_run else '实际清理'}",
            "",
            "-" * 80,
            "统计信息",
            "-" * 80,
            f"总文件数: {self.stats['total_files']}",
            f"总大小: {self._format_size(self.stats['total_size'])}",
            f"过期文件数: {self.stats['expired_files']}",
            f"过期大小: {self._format_size(self.stats['expired_size'])}",
            f"受保护文件数: {self.stats['protected_files']}",
            f"高价值案例数: {self.stats['preserved_files']}",
            f"备份文件数: {self.stats['backed_up_files']}",
            f"备份大小: {self._format_size(self.stats['backed_up_size'])}",
            f"删除文件数: {self.stats['deleted_files']}",
            f"删除大小: {self._format_size(self.stats['deleted_size'])}",
            "",
            "-" * 80,
            "清理候选文件",
            "-" * 80,
        ]

        for i, file_info in enumerate(candidates, 1):
            txt_lines.append(
                f"{i}. {file_info['path']} "
                f"({self._format_size(file_info['size'])}, "
                f"过期{file_info['age_hours']:.1f}小时)"
            )

        txt_lines.extend([
            "",
            "-" * 80,
            "受保护模式",
            "-" * 80,
        ])

        for pattern in self.protected_patterns:
            txt_lines.append(f"  - {pattern}")

        txt_lines.extend([
            "",
            "-" * 80,
            "高价值案例",
            "-" * 80,
        ])

        for case in self.preserve_cases:
            txt_lines.append(f"  - {case}")

        txt_lines.extend([
            "",
            "=" * 80,
            f"JSON报告: {json_path}",
            "=" * 80,
        ])

        txt_path = self.log_dir / f"cleanup_report_{timestamp}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(txt_lines))

        logger.info(f"✅ [归档清理] 报告已生成: {txt_path}")

        return str(json_path), str(txt_path)

    def _is_protected(self, file_path: Path) -> bool:
        """判断文件是否受保护"""
        relative_path = str(file_path.relative_to(self.project_root))

        for pattern in self.protected_patterns:
            if pattern in relative_path:
                return True

        return False

    def _is_preserve_case(self, file_path: Path) -> bool:
        """判断文件是否是高价值案例"""
        relative_path = str(file_path.relative_to(self.project_root))

        for case in self.preserve_cases:
            if case in relative_path:
                return True

        return False

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f}TB"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='归档文件自动化清理脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 模拟运行（推荐先执行）
  python tools/cleanup_archives.py --dry-run

  # 实际清理（保守方案）
  python tools/cleanup_archives.py

  # 实际清理（激进方案）
  python tools/cleanup_archives.py --force

  # 不创建备份（不推荐）
  python tools/cleanup_archives.py --no-backup
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟运行，不实际删除文件'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='强制清理，删除所有过期文件'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='不创建备份（不推荐）'
    )

    args = parser.parse_args()

    # 创建分析器
    analyzer = ArchiveCleanupAnalyzer()

    # 扫描data目录
    files_info = analyzer.scan_data_directory()

    if not files_info:
        logger.info("ℹ️ [归档清理] 没有发现需要清理的文件")
        return

    # 分析清理候选文件
    candidates = analyzer.analyze_cleanup_candidates(files_info, force=args.force)

    if not candidates:
        logger.info("ℹ️ [归档清理] 没有发现需要清理的文件")
        return

    # 备份文件
    if not args.no_backup:
        if not analyzer.backup_files(candidates):
            logger.error("❌ [归档清理] 备份失败，终止清理")
            return

    # 清理文件
    if not analyzer.cleanup_files(candidates, dry_run=args.dry_run):
        logger.error("❌ [归档清理] 清理失败")
        return

    # 生成报告
    json_path, txt_path = analyzer.generate_report(candidates, dry_run=args.dry_run)

    # 输出总结
    print("\n" + "=" * 80)
    print("归档文件清理完成")
    print("=" * 80)
    print(f"扫描文件数: {analyzer.stats['total_files']}")
    print(f"扫描大小: {analyzer._format_size(analyzer.stats['total_size'])}")
    print(f"清理文件数: {analyzer.stats['deleted_files']}")
    print(f"清理大小: {analyzer._format_size(analyzer.stats['deleted_size'])}")
    print(f"备份文件数: {analyzer.stats['backed_up_files']}")
    print(f"备份大小: {analyzer._format_size(analyzer.stats['backed_up_size'])}")
    print(f"\n报告文件:")
    print(f"  - {txt_path}")
    print(f"  - {json_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()