#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定时任务监控系统

功能：
1. 每天9:10检查Redis是否启动，未启动则自动启动
2. 检查早盘前需要运行的Python文件
3. 检查收盘后复盘需要运行的文件
4. 检查每周需要运行的文件
5. UI提示和控制台告警

Author: iFlow CLI
Version: V1.0
"""

import os
import sys
import subprocess
import time
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Any
import json
import schedule
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from logic.logger import get_logger
from logic.data_manager import DataManager

logger = get_logger(__name__)


class ScheduledTaskMonitor:
    """定时任务监控系统"""
    
    def __init__(self):
        """初始化监控系统"""
        self.dm = DataManager()
        self.alerts = []
        self.alert_file = "data/scheduled_alerts.json"
        self.running = False
        
        # 定时任务配置
        self.tasks = {
            # 早盘前检查（9:10）
            'pre_market_check': {
                'time': '09:10',
                'enabled': True,
                'description': '早盘前系统检查'
            },
            # 收盘后复盘（15:30）
            'post_market_review': {
                'time': '15:30',
                'enabled': True,
                'description': '收盘后复盘'
            },
            # 每周检查（周日20:00）
            'weekly_check': {
                'time': '20:00',
                'day': 'sunday',
                'enabled': True,
                'description': '每周系统检查'
            }
        }
        
        # 需要运行的Python文件配置
        self.required_files = {
            'pre_market': [
                'main.py',  # 主程序
            ],
            'post_market': [
                'logic/review_manager.py',  # 复盘管理器
                'logic/auto_reviewer_v18_7.py',  # 智能复盘
            ],
            'weekly': [
                'check_system_health.py',  # 系统健康检查
            ]
        }
        
        self._init_alert_file()
    
    def _init_alert_file(self):
        """初始化告警文件"""
        os.makedirs(os.path.dirname(self.alert_file), exist_ok=True)
        if not os.path.exists(self.alert_file):
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'alerts': [],
                    'last_check': None,
                    'created_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=4)
    
    def _save_alert(self, alert_type: str, severity: str, message: str, details: Dict = None):
        """保存告警信息"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'severity': severity,
            'message': message,
            'details': details or {}
        }
        
        try:
            with open(self.alert_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['alerts'].append(alert)
            data['last_check'] = datetime.now().isoformat()
            
            # 保留最近100条告警
            if len(data['alerts']) > 100:
                data['alerts'] = data['alerts'][-100:]
            
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            self.alerts.append(alert)
            logger.warning(f"🚨 [告警] {severity}: {message}")
            
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def check_redis_status(self) -> bool:
        """检查Redis服务状态"""
        try:
            # 检查Redis进程
            result = subprocess.run(['tasklist'], capture_output=True, text=True)
            redis_running = 'redis-server.exe' in result.stdout
            
            if redis_running:
                logger.info("✅ Redis服务正在运行")
                return True
            else:
                logger.warning("⚠️ Redis服务未运行")
                self._save_alert(
                    'redis_status',
                    'WARNING',
                    'Redis服务未运行',
                    {'action': '尝试自动启动Redis'}
                )
                return False
                
        except Exception as e:
            logger.error(f"检查Redis状态失败: {e}")
            self._save_alert(
                'redis_status',
                'ERROR',
                f'检查Redis状态失败: {str(e)}',
                {}
            )
            return False
    
    def start_redis_service(self) -> bool:
        """启动Redis服务"""
        try:
            logger.info("🔄 尝试启动Redis服务...")
            
            # 检查Redis服务是否存在
            result = subprocess.run(['sc', 'query', 'Redis'], capture_output=True, text=True)
            
            if 'RUNNING' in result.stdout:
                logger.info("✅ Redis服务已在运行")
                return True
            
            # 尝试启动Redis服务
            subprocess.run(['sc', 'start', 'Redis'], capture_output=True, timeout=10)
            time.sleep(2)
            
            # 再次检查
            result = subprocess.run(['sc', 'query', 'Redis'], capture_output=True, text=True)
            if 'RUNNING' in result.stdout:
                logger.info("✅ Redis服务启动成功")
                self._save_alert(
                    'redis_status',
                    'INFO',
                    'Redis服务启动成功',
                    {}
                )
                return True
            else:
                logger.error("❌ Redis服务启动失败")
                self._save_alert(
                    'redis_status',
                    'CRITICAL',
                    'Redis服务启动失败',
                    {'suggestion': '请手动启动Redis或使用start_with_redis.bat'}
                )
                return False
                
        except Exception as e:
            logger.error(f"启动Redis服务失败: {e}")
            self._save_alert(
                'redis_status',
                'CRITICAL',
                f'启动Redis服务失败: {str(e)}',
                {'suggestion': '请手动启动Redis或使用start_with_redis.bat'}
            )
            return False
    
    def check_required_files(self, category: str) -> Dict[str, bool]:
        """检查必需的Python文件是否存在"""
        results = {}
        files = self.required_files.get(category, [])
        
        for file_path in files:
            full_path = os.path.join(project_root, file_path)
            exists = os.path.exists(full_path)
            results[file_path] = exists
            
            if not exists:
                self._save_alert(
                    'missing_file',
                    'CRITICAL',
                    f'缺少必需文件: {file_path}',
                    {'category': category, 'path': full_path}
                )
        
        return results
    
    def check_auction_snapshot(self) -> bool:
        """检查竞价快照功能"""
        try:
            # 检查AuctionSnapshotManager是否可用
            if hasattr(self.dm, 'auction_snapshot_manager') and self.dm.auction_snapshot_manager:
                status = self.dm.auction_snapshot_manager.get_snapshot_status()
                
                if status['is_available']:
                    logger.info(f"✅ 竞价快照功能正常 (Redis已连接)")
                    return True
                else:
                    logger.warning("⚠️ 竞价快照功能不可用 (Redis未连接)")
                    self._save_alert(
                        'auction_snapshot',
                        'WARNING',
                        '竞价快照功能不可用',
                        {'reason': 'Redis未连接'}
                    )
                    return False
            else:
                logger.warning("⚠️ 竞价快照管理器未初始化")
                return False
                
        except Exception as e:
            logger.error(f"检查竞价快照失败: {e}")
            return False
    
    def run_pre_market_check(self):
        """早盘前检查（9:10）"""
        logger.info("=" * 80)
        logger.info("🕐 早盘前系统检查 (9:10)")
        logger.info("=" * 80)
        
        # 1. 检查Redis
        redis_ok = self.check_redis_status()
        if not redis_ok:
            logger.info("🔄 尝试自动启动Redis...")
            self.start_redis_service()
        
        # 2. 检查竞价快照
        auction_ok = self.check_auction_snapshot()
        
        # 3. 检查必需文件
        pre_market_files = self.check_required_files('pre_market')
        files_ok = all(pre_market_files.values())
        
        # 4. 生成检查报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'redis_ok': redis_ok,
            'auction_ok': auction_ok,
            'files_ok': files_ok,
            'files_status': pre_market_files,
            'overall_status': 'OK' if redis_ok and auction_ok and files_ok else 'WARNING'
        }
        
        logger.info(f"📊 早盘前检查完成: {report['overall_status']}")
        
        if report['overall_status'] != 'OK':
            self._save_alert(
                'pre_market_check',
                'WARNING',
                '早盘前检查发现问题',
                report
            )
        
        return report
    
    def run_post_market_review(self):
        """收盘后复盘（15:30）"""
        logger.info("=" * 80)
        logger.info("🕐 收盘后复盘 (15:30)")
        logger.info("=" * 80)
        
        try:
            # 1. 检查必需文件
            post_market_files = self.check_required_files('post_market')
            
            if not all(post_market_files.values()):
                logger.error("❌ 缺少复盘必需文件")
                return False
            
            # 2. 运行复盘管理器
            from logic.review_manager import ReviewManager
            rm = ReviewManager()
            
            # 获取今天的日期
            today = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"🔄 开始执行 {today} 每日复盘...")
            result = rm.run_daily_review(date=today)
            
            if result:
                logger.info("✅ 收盘后复盘完成")
                self._save_alert(
                    'post_market_review',
                    'INFO',
                    f'收盘后复盘完成: {today}',
                    {}
                )
                return True
            else:
                logger.warning("⚠️ 收盘后复盘失败或无数据")
                self._save_alert(
                    'post_market_review',
                    'WARNING',
                    f'收盘后复盘失败或无数据: {today}',
                    {}
                )
                return False
                
        except Exception as e:
            logger.error(f"收盘后复盘失败: {e}")
            self._save_alert(
                'post_market_review',
                'ERROR',
                f'收盘后复盘失败: {str(e)}',
                {}
            )
            return False
    
    def run_weekly_check(self):
        """每周系统检查（周日20:00）"""
        logger.info("=" * 80)
        logger.info("🕐 每周系统检查 (周日20:00)")
        logger.info("=" * 80)
        
        try:
            # 1. 运行系统健康检查
            logger.info("🔄 运行系统健康检查...")
            import subprocess
            result = subprocess.run(
                ['python', 'check_system_health.py'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ 系统健康检查通过")
            else:
                logger.warning("⚠️ 系统健康检查发现问题")
                self._save_alert(
                    'weekly_check',
                    'WARNING',
                    '系统健康检查发现问题',
                    {'output': result.stdout, 'error': result.stderr}
                )
            
            # 2. 检查必需文件
            weekly_files = self.check_required_files('weekly')
            
            # 3. 生成检查报告
            report = {
                'timestamp': datetime.now().isoformat(),
                'health_check': result.returncode == 0,
                'files_ok': all(weekly_files.values()),
                'files_status': weekly_files
            }
            
            logger.info(f"📊 每周检查完成")
            self._save_alert(
                'weekly_check',
                'INFO',
                '每周系统检查完成',
                report
            )
            
            return report
            
        except Exception as e:
            logger.error(f"每周系统检查失败: {e}")
            self._save_alert(
                'weekly_check',
                'ERROR',
                f'每周系统检查失败: {str(e)}',
                {}
            )
            return False
    
    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """获取最近的告警"""
        try:
            with open(self.alert_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data['alerts'][-limit:]
        except Exception as e:
            logger.error(f"获取告警失败: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        redis_ok = self.check_redis_status()
        auction_ok = self.check_auction_snapshot()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'redis_ok': redis_ok,
            'auction_ok': auction_ok,
            'alerts_count': len(self.get_alerts()),
            'recent_alerts': self.get_alerts(5)
        }
    
    def start(self):
        """启动定时任务监控"""
        logger.info("🚀 启动定时任务监控系统")
        
        # 设置定时任务
        schedule.every().day.at(self.tasks['pre_market_check']['time']).do(self.run_pre_market_check)
        schedule.every().day.at(self.tasks['post_market_review']['time']).do(self.run_post_market_review)
        schedule.every().sunday.at(self.tasks['weekly_check']['time']).do(self.run_weekly_check)
        
        self.running = True
        
        logger.info("✅ 定时任务已设置:")
        logger.info(f"  - 早盘前检查: {self.tasks['pre_market_check']['time']}")
        logger.info(f"  - 收盘后复盘: {self.tasks['post_market_review']['time']}")
        logger.info(f"  - 每周检查: 周日 {self.tasks['weekly_check']['time']}")
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        monitor_thread.start()
        
        return monitor_thread
    
    def _run_scheduler(self):
        """运行调度器"""
        logger.info("📅 定时任务监控器已启动")
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("🛑 定时任务监控器已停止")


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 MyQuantTool 定时任务监控系统")
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    monitor = ScheduledTaskMonitor()
    
    # 立即执行一次早盘前检查
    print("\n🔍 执行早盘前检查...")
    monitor.run_pre_market_check()
    
    # 启动定时任务
    print("\n📅 启动定时任务监控...")
    monitor.start()
    
    print("\n✅ 监控系统已启动，按 Ctrl+C 停止")
    print("\n📊 当前系统状态:")
    status = monitor.get_system_status()
    print(f"  - Redis: {'✅ 正常' if status['redis_ok'] else '❌ 异常'}")
    print(f"  - 竞价快照: {'✅ 正常' if status['auction_ok'] else '❌ 异常'}")
    print(f"  - 告警数: {status['alerts_count']}")
    
    if status['recent_alerts']:
        print("\n🚨 最近告警:")
        for alert in status['recent_alerts']:
            print(f"  - [{alert['severity']}] {alert['timestamp']}: {alert['message']}")
    
    # 保持运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止监控系统...")
        monitor.stop()
        print("✅ 监控系统已停止")


if __name__ == '__main__':
    main()