"""
QMT 竞价监控脚本

每30秒检查一次QMT状态、竞价快照、monitor_state.json和日志文件
持续监控10分钟，生成详细报告
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    from logic.qmt_health_check import check_qmt_health
except ImportError:
    print("警告: 无法导入qmt_health_check模块")
    check_qmt_health = None


class QMTAuctionMonitor:
    """QMT 竞价监控器"""

    def __init__(self, duration_minutes=10, interval_seconds=30):
        """
        初始化监控器

        Args:
            duration_minutes: 监控时长（分钟）
            interval_seconds: 检查间隔（秒）
        """
        self.duration_minutes = duration_minutes
        self.interval_seconds = interval_seconds
        self.start_time = None
        self.end_time = None
        self.check_results = []

        # 路径配置
        self.base_dir = Path('E:/MyQuantTool')
        self.auction_snapshot_dir = self.base_dir / 'data' / 'auction_snapshot'
        self.monitor_state_file = self.base_dir / 'data' / 'monitor_state.json'
        self.logs_dir = self.base_dir / 'logs'

        # 初始状态
        self.initial_monitor_state = None
        self.last_monitor_state = None

    def run(self):
        """执行监控"""
        print("=" * 80)
        print("🚀 QMT 竞价监控开始")
        print(f"监控时长: {self.duration_minutes} 分钟")
        print(f"检查间隔: {self.interval_seconds} 秒")
        print(f"预计检查次数: {int(self.duration_minutes * 60 / self.interval_seconds)}")
        print("=" * 80)
        print()

        self.start_time = datetime.now()

        # 记录初始状态
        self._record_initial_state()

        # 执行监控循环
        check_count = 0
        total_checks = int(self.duration_minutes * 60 / self.interval_seconds)

        while check_count < total_checks:
            check_count += 1
            current_time = datetime.now()
            elapsed = (current_time - self.start_time).total_seconds()

            print(f"\n{'=' * 80}")
            print(f"📊 检查 #{check_count}/{total_checks}")
            print(f"时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (已运行: {elapsed:.0f}秒)")
            print(f"{'=' * 80}")

            # 执行检查
            result = self._perform_check(current_time)
            self.check_results.append(result)

            # 打印检查结果
            self._print_check_result(result)

            # 如果不是最后一次检查，等待
            if check_count < total_checks:
                print(f"\n⏱️  等待 {self.interval_seconds} 秒...")
                time.sleep(self.interval_seconds)

        self.end_time = datetime.now()
        print("\n" + "=" * 80)
        print("✅ 监控完成")
        print("=" * 80)

        # 生成报告
        self._generate_report()

    def _record_initial_state(self):
        """记录初始状态"""
        print("📝 记录初始状态...")

        # 记录 monitor_state.json 初始状态
        if self.monitor_state_file.exists():
            with open(self.monitor_state_file, 'r', encoding='utf-8') as f:
                self.initial_monitor_state = json.load(f)
            print(f"  ✅ monitor_state.json 初始更新时间: {self.initial_monitor_state.get('update_time', 'N/A')}")
        else:
            print(f"  ⚠️  monitor_state.json 不存在")

        # 检查竞价快照目录
        if self.auction_snapshot_dir.exists():
            snapshots = list(self.auction_snapshot_dir.glob('*.json'))
            print(f"  ✅ 竞价快照目录存在，初始文件数: {len(snapshots)}")
        else:
            print(f"  ⚠️  竞价快照目录不存在")

        print()

    def _perform_check(self, check_time: datetime) -> Dict[str, Any]:
        """执行单次检查"""
        result = {
            'check_time': check_time.strftime('%Y-%m-%d %H:%M:%S'),
            'qmt_health': None,
            'auction_snapshots': None,
            'monitor_state': None,
            'log_updates': None,
            'anomalies': []
        }

        # 1. 检查 QMT 状态
        if check_qmt_health:
            try:
                qmt_result = check_qmt_health()
                result['qmt_health'] = qmt_result

                # 检查异常
                if qmt_result.get('status') != 'HEALTHY':
                    result['anomalies'].append({
                        'type': 'QMT_HEALTH',
                        'severity': qmt_result.get('status'),
                        'message': qmt_result.get('recommendations', [])
                    })
            except Exception as e:
                result['anomalies'].append({
                    'type': 'QMT_HEALTH_ERROR',
                    'severity': 'ERROR',
                    'message': f"QMT健康检查失败: {str(e)}"
                })

        # 2. 检查竞价快照
        if self.auction_snapshot_dir.exists():
            snapshots = list(self.auction_snapshot_dir.glob('*.json'))
            result['auction_snapshots'] = {
                'exists': True,
                'count': len(snapshots),
                'latest': None
            }

            if snapshots:
                latest_snapshot = max(snapshots, key=lambda p: p.stat().st_mtime)
                result['auction_snapshots']['latest'] = {
                    'name': latest_snapshot.name,
                    'modified': datetime.fromtimestamp(latest_snapshot.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                }

                # 检查快照时间是否正常
                latest_time = latest_snapshot.stat().st_mtime
                time_diff = (check_time.timestamp() - latest_time) / 60  # 分钟
                if time_diff > 5:  # 超过5分钟
                    result['anomalies'].append({
                        'type': 'AUCTION_SNAPSHOT_OLD',
                        'severity': 'WARNING',
                        'message': f"竞价快照滞后 {time_diff:.1f} 分钟"
                    })
        else:
            result['auction_snapshots'] = {
                'exists': False,
                'count': 0
            }
            result['anomalies'].append({
                'type': 'AUCTION_SNAPSHOT_MISSING',
                'severity': 'WARNING',
                'message': '竞价快照目录不存在'
            })

        # 3. 检查 monitor_state.json
        if self.monitor_state_file.exists():
            with open(self.monitor_state_file, 'r', encoding='utf-8') as f:
                current_state = json.load(f)

            result['monitor_state'] = {
                'exists': True,
                'update_time': current_state.get('update_time', 'N/A'),
                'scan_count': current_state.get('scan_count', 0),
                'signal_count': len(current_state.get('signals', []))
            }

            self.last_monitor_state = current_state

            # 检查更新时间
            if self.initial_monitor_state:
                last_update = self.initial_monitor_state.get('update_time', '')
                current_update = current_state.get('update_time', '')

                if last_update == current_update:
                    result['anomalies'].append({
                        'type': 'MONITOR_STATE_NOT_UPDATED',
                        'severity': 'WARNING',
                        'message': 'monitor_state.json 未更新'
                    })
        else:
            result['monitor_state'] = {
                'exists': False
            }
            result['anomalies'].append({
                'type': 'MONITOR_STATE_MISSING',
                'severity': 'ERROR',
                'message': 'monitor_state.json 不存在'
            })

        # 4. 检查日志文件
        log_files = list(self.logs_dir.glob('app_*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            log_size = latest_log.stat().st_size

            result['log_updates'] = {
                'exists': True,
                'latest_file': latest_log.name,
                'size': log_size,
                'last_modified': datetime.fromtimestamp(latest_log.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }

            # 读取最后几行
            try:
                with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if lines:
                        last_lines = lines[-5:]  # 最后5行
                        result['log_updates']['last_lines'] = [line.strip() for line in last_lines]
            except Exception as e:
                result['anomalies'].append({
                    'type': 'LOG_READ_ERROR',
                    'severity': 'ERROR',
                    'message': f"无法读取日志文件: {str(e)}"
                })
        else:
            result['log_updates'] = {
                'exists': False
            }
            result['anomalies'].append({
                'type': 'LOG_MISSING',
                'severity': 'WARNING',
                'message': '日志文件不存在'
            })

        return result

    def _print_check_result(self, result: Dict[str, Any]):
        """打印检查结果"""
        # QMT 状态
        qmt = result.get('qmt_health')
        if qmt:
            status = qmt.get('status', 'UNKNOWN')
            emoji = {'HEALTHY': '✅', 'WARNING': '⚠️', 'ERROR': '❌'}.get(status, '❓')
            print(f"QMT状态: {emoji} {status}")

            details = qmt.get('details', {})
            if details:
                server = details.get('server_login', {})
                if server.get('logged_in'):
                    timetag = server.get('timetag', 'N/A')
                    print(f"  时间戳: {timetag}")

                    # 检查时间戳是否异常
                    if timetag and timetag.endswith('00:00:00'):
                        print(f"  ⚠️  警告: 时间戳异常（显示为午夜）")
        else:
            print("QMT状态: ❓ 无法检查")

        # 竞价快照
        auction = result.get('auction_snapshots')
        if auction:
            if auction.get('exists'):
                count = auction.get('count', 0)
                latest = auction.get('latest')
                if latest:
                    print(f"竞价快照: ✅ {count} 个文件")
                    print(f"  最新: {latest['name']} ({latest['modified']})")
                else:
                    print(f"竞价快照: ⚠️  目录存在但无文件")
            else:
                print(f"竞价快照: ❌ 目录不存在")

        # monitor_state.json
        monitor = result.get('monitor_state')
        if monitor:
            if monitor.get('exists'):
                print(f"监控状态: ✅ 更新时间 {monitor.get('update_time', 'N/A')}")
                print(f"  扫描次数: {monitor.get('scan_count', 0)}")
                print(f"  信号数量: {monitor.get('signal_count', 0)}")
            else:
                print(f"监控状态: ❌ 文件不存在")

        # 日志文件
        log = result.get('log_updates')
        if log:
            if log.get('exists'):
                print(f"日志文件: ✅ {log.get('latest_file', 'N/A')}")
                print(f"  大小: {log.get('size', 0)} bytes")
                print(f"  最后修改: {log.get('last_modified', 'N/A')}")
            else:
                print(f"日志文件: ❌ 不存在")

        # 异常
        anomalies = result.get('anomalies', [])
        if anomalies:
            print(f"\n⚠️  发现 {len(anomalies)} 个异常:")
            for anomaly in anomalies:
                severity = anomaly.get('severity', 'UNKNOWN')
                emoji = {'ERROR': '❌', 'WARNING': '⚠️'}.get(severity, '❓')
                message = anomaly.get('message', 'N/A')
                print(f"  {emoji} {message}")

    def _generate_report(self):
        """生成监控报告"""
        print("\n" + "=" * 80)
        print("📊 监控报告")
        print("=" * 80)

        # 1. 监控时间范围
        duration = (self.end_time - self.start_time).total_seconds() / 60
        print(f"\n1. 监控时间范围")
        print(f"   开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   持续时长: {duration:.1f} 分钟")
        print(f"   检查次数: {len(self.check_results)}")

        # 2. QMT 状态变化
        print(f"\n2. QMT 状态变化情况")
        qmt_statuses = {}
        for result in self.check_results:
            qmt = result.get('qmt_health')
            if qmt:
                status = qmt.get('status', 'UNKNOWN')
                qmt_statuses[status] = qmt_statuses.get(status, 0) + 1

        for status, count in qmt_statuses.items():
            emoji = {'HEALTHY': '✅', 'WARNING': '⚠️', 'ERROR': '❌'}.get(status, '❓')
            print(f"   {emoji} {status}: {count} 次")

        # 3. 竞价快照生成情况
        print(f"\n3. 竞价快照生成情况")
        snapshot_counts = []
        for result in self.check_results:
            auction = result.get('auction_snapshots')
            if auction and auction.get('exists'):
                snapshot_counts.append(auction.get('count', 0))

        if snapshot_counts:
            initial_count = snapshot_counts[0]
            final_count = snapshot_counts[-1]
            new_snapshots = final_count - initial_count
            print(f"   初始文件数: {initial_count}")
            print(f"   最终文件数: {final_count}")
            print(f"   新增快照: {new_snapshots} 个")

            if new_snapshots > 0:
                avg_rate = new_snapshots / duration
                print(f"   生成速率: {avg_rate:.2f} 个/分钟")
            else:
                print(f"   ⚠️  监控期间未生成新快照")
        else:
            print(f"   ❌ 竞价快照目录不存在")

        # 4. Tick数据推送情况（通过日志分析）
        print(f"\n4. Tick数据推送情况")
        log_updates = []
        for result in self.check_results:
            log = result.get('log_updates')
            if log and log.get('exists'):
                log_updates.append(log.get('size', 0))

        if log_updates:
            initial_size = log_updates[0]
            final_size = log_updates[-1]
            size_increase = final_size - initial_size
            print(f"   日志文件大小变化: {size_increase:,} bytes")

            if size_increase > 0:
                print(f"   ✅ 日志文件在增长，说明有数据推送")
            else:
                print(f"   ⚠️  日志文件未增长，可能没有数据推送")
        else:
            print(f"   ❌ 无法判断（日志文件不存在）")

        # 5. 异常情况汇总
        print(f"\n5. 异常情况汇总")
        anomaly_summary = {}
        for result in self.check_results:
            for anomaly in result.get('anomalies', []):
                anomaly_type = anomaly.get('type', 'UNKNOWN')
                anomaly_summary[anomaly_type] = anomaly_summary.get(anomaly_type, 0) + 1

        if anomaly_summary:
            for anomaly_type, count in sorted(anomaly_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"   {anomaly_type}: {count} 次")
        else:
            print(f"   ✅ 未发现异常")

        # 6. 监控结论和建议
        print(f"\n6. 监控结论和建议")

        has_errors = any('ERROR' in a.get('severity', '') for r in self.check_results for a in r.get('anomalies', []))
        has_warnings = any('WARNING' in a.get('severity', '') for r in self.check_results for a in r.get('anomalies', []))
        qmt_healthy = any(r.get('qmt_health', {}).get('status') == 'HEALTHY' for r in self.check_results)
        has_snapshots = any(r.get('auction_snapshots', {}).get('exists') for r in self.check_results)

        if has_errors:
            print(f"   ❌ 发现严重错误，需要立即处理")
            print(f"   建议: 检查QMT连接、启动相关服务")
        elif has_warnings:
            print(f"   ⚠️  发现警告，建议关注")
            if not has_snapshots:
                print(f"   建议: 检查竞价快照服务是否正常运行")
            if not qmt_healthy:
                print(f"   建议: 检查QMT客户端状态")
        elif qmt_healthy:
            print(f"   ✅ QMT状态正常")
            if has_snapshots:
                print(f"   ✅ 竞价快照正常生成")
            else:
                print(f"   ⚠️  竞价快照未生成（可能不在竞价时间）")
        else:
            print(f"   ❓ 无法确定QMT状态")

        # 保存报告到文件
        report_file = self.base_dir / 'data' / f'qmt_auction_monitor_report_{self.start_time.strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'monitor_info': {
                'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': duration,
                'check_count': len(self.check_results),
                'check_interval_seconds': self.interval_seconds
            },
            'qmt_status_summary': qmt_statuses,
            'auction_snapshot_summary': {
                'initial_count': snapshot_counts[0] if snapshot_counts else 0,
                'final_count': snapshot_counts[-1] if snapshot_counts else 0,
                'new_snapshots': snapshot_counts[-1] - snapshot_counts[0] if snapshot_counts else 0
            },
            'log_update_summary': {
                'initial_size': log_updates[0] if log_updates else 0,
                'final_size': log_updates[-1] if log_updates else 0,
                'size_increase': log_updates[-1] - log_updates[0] if log_updates else 0
            },
            'anomaly_summary': anomaly_summary,
            'check_results': self.check_results
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n   📄 详细报告已保存到: {report_file}")

        print("\n" + "=" * 80)
        print("监控结束")
        print("=" * 80)


if __name__ == '__main__':
    monitor = QMTAuctionMonitor(duration_minutes=10, interval_seconds=30)
    monitor.run()
