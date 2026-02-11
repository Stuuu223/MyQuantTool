#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单股票实时监控脚本（Phase 1 验证版本）

目标：
- 监控1-5只重点股票（如300997欢乐家）
- 验证QPST四维分析算法的有效性
- 捕捉诱多预警信号

使用方法：
    python tasks/monitor_single_stock.py --codes 300997.SZ,603697.SH --interval 5

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from logic.smart_flow_estimator import SmartFlowEstimator
from logic.logger import get_logger

logger = get_logger(__name__)


class SingleStockMonitor:
    """
    单股票实时监控器
    
    功能：
    1. 实时监控指定股票的资金流动
    2. 每隔指定时间执行一次QPST四维分析
    3. 触发诱多预警时发送通知
    4. 保存监控日志
    """
    
    def __init__(self, codes: list, interval: int = 5):
        """
        初始化监控器
        
        Args:
            codes: 要监控的股票代码列表（如 ['300997.SZ', '603697.SH']）
            interval: 刷新间隔（秒）
        """
        self.codes = codes
        self.interval = interval
        
        # 初始化智能资金流估算器
        self.estimator = SmartFlowEstimator(
            tick_window=20,
            day_window=5,
            enable_persistence=True
        )
        
        # 预警历史（避免重复发送）
        self.alert_history = {code: [] for code in codes}
        
        logger.info("="*80)
        logger.info("🚀 单股票实时监控启动")
        logger.info("="*80)
        logger.info(f"监控股票: {', '.join(codes)}")
        logger.info(f"刷新间隔: {interval}秒")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
    
    def run(self):
        """
        启动监控循环
        """
        try:
            while True:
                self._monitor_cycle()
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            logger.info("\n" + "="*80)
            logger.info("⏸️  用户中断监控")
            logger.info("="*80)
            self._print_summary()
        
        except Exception as e:
            logger.error(f"❌ 监控异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            self.estimator.close()
            logger.info("✅ 监控已停止")
    
    def _monitor_cycle(self):
        """
        单次监控循环
        """
        for code in self.codes:
            try:
                # 执行QPST四维分析
                result = self.estimator.estimate_flow_multi_dim(code)
                
                # 打印结果
                self._print_result(code, result)
                
                # 检查预警
                if result['final_signal'] == 'TRAP_WARNING':
                    self._handle_trap_warning(code, result)
                
            except Exception as e:
                logger.error(f"❌ 监控{code}失败: {e}")
    
    def _print_result(self, code: str, result: dict):
        """
        打印监控结果
        """
        signal = result['final_signal']
        confidence = result['confidence']
        reason = result['reason']
        timestamp = result['timestamp']
        
        # 信号表情
        signal_emoji = {
            'STRONG_INFLOW': '🟢',
            'WEAK_INFLOW': '🟡',
            'NEUTRAL': '⚪',
            'WEAK_OUTFLOW': '🟠',
            'STRONG_OUTFLOW': '🔴',
            'TRAP_WARNING': '⚠️'
        }
        
        emoji = signal_emoji.get(signal, '❓')
        
        # 基础信息
        logger.info(f"\n[{timestamp}] {code}")
        logger.info(f"  信号: {emoji} {signal} (置信度: {confidence:.0%})")
        logger.info(f"  原因: {reason}")
        
        # 诱多预警
        if result.get('trap_signals'):
            logger.warning(f"  ⚠️  诱多预警: {result['trap_signals']}")
        
        # 维度详情（只在DEBUG模式显示）
        if result['dimensions']:
            dims = result['dimensions']
            logger.debug(f"  维度详情:")
            logger.debug(f"    成交量: {dims.get('quantity', {}).get('signal', 'N/A')}")
            logger.debug(f"    价格: {dims.get('price', {}).get('signal', 'N/A')}")
            logger.debug(f"    换手率: {dims.get('space', {}).get('signal', 'N/A')}")
            logger.debug(f"    持续性: {dims.get('time', {}).get('signal', 'N/A')}")
        
        logger.info("-" * 80)
    
    def _handle_trap_warning(self, code: str, result: dict):
        """
        处理诱多预警
        
        功能：
        1. 记录预警历史
        2. 发送通知（钉钉/企业微信/邮件）
        3. 保存到预警日志
        """
        trap_signals = result['trap_signals']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否已发送过相同预警（避免重复）
        recent_alerts = self.alert_history[code][-5:]  # 最近5条
        if trap_signals in recent_alerts:
            return
        
        # 记录预警历史
        self.alert_history[code].append(trap_signals)
        
        # 构建预警消息
        alert_msg = f"""
⚠️  诱多预警 ⚠️

股票代码: {code}
时间: {timestamp}
预警信号: {'; '.join(trap_signals)}
置信度: {result['confidence']:.0%}
原因: {result['reason']}

建议: 立即停止买入，观察1-3个交易日
        """
        
        logger.warning(alert_msg)
        
        # 保存到预警日志
        self._save_alert_log(code, alert_msg)
        
        # TODO: 发送通知到钉钉/企业微信/邮件
        # self._send_notification(alert_msg)
    
    def _save_alert_log(self, code: str, alert_msg: str):
        """
        保存预警日志到文件
        """
        log_dir = Path('logs/trap_alerts')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{code.replace('.', '_')}_alerts.log"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(alert_msg + "\n" + "="*80 + "\n")
    
    def _print_summary(self):
        """
        打印监控总结
        """
        logger.info("\n📊 监控总结")
        logger.info("="*80)
        
        for code in self.codes:
            alert_count = len(self.alert_history[code])
            logger.info(f"{code}: 触发诱多预警 {alert_count} 次")
            
            if alert_count > 0:
                logger.info(f"  最近预警: {self.alert_history[code][-1]}")
        
        logger.info("="*80)


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='单股票实时监控（Phase 1 验证）')
    parser.add_argument(
        '--codes',
        type=str,
        required=True,
        help='要监控的股票代码，多个用逗号分隔（如: 300997.SZ,603697.SH）'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='刷新间隔（秒），默认5秒'
    )
    
    args = parser.parse_args()
    
    # 解析股票代码
    codes = [code.strip() for code in args.codes.split(',')]
    
    # 验证股票代码格式
    for code in codes:
        if not (
            (code.endswith('.SZ') or code.endswith('.SH')) and 
            len(code.split('.')[0]) == 6
        ):
            logger.error(f"❌ 无效的股票代码: {code}")
            logger.error("   正确格式: 300997.SZ 或 601869.SH")
            sys.exit(1)
    
    # 启动监控
    monitor = SingleStockMonitor(codes=codes, interval=args.interval)
    monitor.run()


if __name__ == '__main__':
    main()
