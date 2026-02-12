#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyQuantTool Pre-Market Auto Execution Script

Functions:
- Scheduled execution of data warmup (08:00)
- QMT environment check (09:15)
- Auction data collection (09:25)
- Monitor startup (09:30)

Usage:
    python tasks/scheduled_premarket.py

Author: iFlow CLI
Version: V1.0
"""

import time
import argparse
import schedule
from datetime import datetime, time as dt_time
from pathlib import Path
import subprocess
import sys
import io

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger

logger = get_logger(__name__)


class PreMarketScheduler:
    """Pre-market task scheduler"""

    def __init__(self, date: str = None):
        """
        Initialize scheduler

        Args:
            date: Trading date (YYYY-MM-DD), default is today
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        self.date = date
        self.venv_python = project_root / "venv_qmt" / "Scripts" / "python.exe"

        logger.info("=" * 80)
        logger.info("[START] MyQuantTool Pre-Market Auto Execution Script")
        logger.info("=" * 80)
        logger.info(f"[DATE] Trading date: {date}")
        logger.info(f"[PYTHON] Python environment: {self.venv_python}")
        logger.info("")

        # Setup scheduled tasks
        self._setup_schedules()

    def _run_script(self, script_path: str, args: list = None) -> bool:
        """
        Run script

        Args:
            script_path: Script path (relative to project root)
            args: Argument list

        Returns:
            Success status
        """
        if args is None:
            args = []

        cmd = [str(self.venv_python), str(project_root / script_path)] + args

        logger.info(f"[EXEC] Execute command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.stdout:
                logger.info(result.stdout)

            if result.stderr:
                logger.warning(result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error(f"[FAIL] Script execution timeout: {script_path}")
            return False
        except Exception as e:
            logger.error(f"[FAIL] Script execution failed: {script_path} - {e}")
            return False

    # ===== Task Definitions =====

    def task_data_warmup(self):
        """Task 1: Data warmup (08:00)"""
        logger.info("")
        logger.info("[WARMUP] [08:00] Start data warmup...")
        logger.info("-" * 80)

        success = self._run_script("tasks/run_pre_market_warmup.py")

        if success:
            logger.info("[OK] Data warmup completed")
        else:
            logger.error("[FAIL] Data warmup failed")

        logger.info("-" * 80)

    def task_check_qmt(self):
        """Task 2: QMT environment check (09:15)"""
        logger.info("")
        logger.info("[CHECK] [09:15] Start QMT environment check...")
        logger.info("-" * 80)

        success = self._run_script("tools/check_qmt_environment.py")

        if success:
            logger.info("[OK] QMT environment check passed")
        else:
            logger.error("[FAIL] QMT environment check failed, please check QMT client")

        logger.info("-" * 80)

    def task_collect_auction(self):
        """Task 3: Collect auction data (09:25)"""
        logger.info("")
        logger.info("[DATA] [09:25] Start collecting auction data...")
        logger.info("-" * 80)

        success = self._run_script("tasks/collect_auction_snapshot.py", ["--date", self.date])

        if success:
            logger.info("[OK] Auction data collection completed")
        else:
            logger.error("[FAIL] Auction data collection failed")

        logger.info("-" * 80)

    def task_start_monitor(self):
        """Task 4: Start monitor (09:30)"""
        logger.info("")
        logger.info("[MONITOR] [09:30] Start CLI monitor...")
        logger.info("-" * 80)

        logger.info("[WARN] Monitor terminal will start, press Ctrl+C to stop")
        logger.info("[INFO] Or run separately: python tools/cli_monitor.py")

        logger.info("-" * 80)

    # ===== Schedule Setup =====

    def _setup_schedules(self):
        """Setup scheduled tasks"""
        # Task 1: Data warmup (08:00)
        schedule.every().day.at("08:00").do(self.task_data_warmup)
        logger.info("[TIME] [08:00] Data warmup - Scheduled")

        # Task 2: QMT environment check (09:15)
        schedule.every().day.at("09:15").do(self.task_check_qmt)
        logger.info("[TIME] [09:15] QMT environment check - Scheduled")

        # Task 3: Collect auction data (09:25)
        schedule.every().day.at("09:25").do(self.task_collect_auction)
        logger.info("[TIME] [09:25] Collect auction data - Scheduled")

        # Task 4: Start monitor (09:30)
        schedule.every().day.at("09:30").do(self.task_start_monitor)
        logger.info("[TIME] [09:30] Start monitor - Scheduled")

        logger.info("")
        logger.info("=" * 80)
        logger.info("[OK] All scheduled tasks configured")
        logger.info("=" * 80)
        logger.info("")

    # ===== Run Modes =====

    def run_immediate(self):
        """Run all tasks immediately (for testing)"""
        logger.info("[MODE] Immediate execution: will run all tasks in sequence")
        logger.info("")

        self.task_data_warmup()
        self.task_check_qmt()
        self.task_collect_auction()
        self.task_start_monitor()

    def run_scheduled(self):
        """Scheduled run mode (for production)"""
        logger.info("[MODE] Scheduled mode: waiting for trigger time...")
        logger.info("")

        # Show next run time
        self._show_next_run()

        # Run continuously
        while True:
            schedule.run_pending()
            time.sleep(1)

    def _show_next_run(self):
        """Show next run time"""
        next_run = schedule.next_run()
        if next_run:
            logger.info(f"[DATE] Next task: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("[WAIT] Waiting... (Press Ctrl+C to exit)")
            logger.info("")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Pre-market auto execution script')
    parser.add_argument('--date', type=str, help='Trading date (YYYY-MM-DD)')
    parser.add_argument('--immediate', action='store_true', help='Execute all tasks immediately (for testing)')
    parser.add_argument('--once', type=str, help='Execute specific task only: warmup|check|auction|monitor')

    args = parser.parse_args()

    # Initialize scheduler
    scheduler = PreMarketScheduler(args.date)

    # Execute specific task only
    if args.once:
        task_map = {
            'warmup': scheduler.task_data_warmup,
            'check': scheduler.task_check_qmt,
            'auction': scheduler.task_collect_auction,
            'monitor': scheduler.task_start_monitor
        }

        if args.once in task_map:
            logger.info(f"[TASK] Execute task only: {args.once}")
            task_map[args.once]()
        else:
            logger.error(f"[FAIL] Unknown task: {args.once}")
            logger.info(f"[INFO] Available tasks: {', '.join(task_map.keys())}")
        return

    # Run mode
    if args.immediate:
        # Execute all tasks immediately
        scheduler.run_immediate()
    else:
        # Scheduled run
        scheduler.run_scheduled()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 80)
        logger.info("[EXIT] User interrupted, program exiting")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"[ERROR] Program exception: {e}")
        raise