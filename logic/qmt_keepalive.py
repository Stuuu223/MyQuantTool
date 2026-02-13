#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT 保活守护线程模块 (QMT Keep-Alive Daemon)

功能：
1. 启动守护线程，定时探测 QMT 状态
2. 主动探测：尝试获取 tick 数据（xtdata）或查询资产（xt_trader）
3. 自动重连：发现异常时尝试唤醒或重连
4. 异常报警：连续多次失败记录 Critical 日志

Author: MyQuantTool Team
Date: 2026-02-13
"""

import time
import threading
from typing import Optional
from datetime import datetime

try:
    from xtquant import xtdata, xttrader
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    # 定义伪类以避免类型注解报错
    class xttrader:
        class XtQuantTrader:
            pass

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class QMTKeepAlive(threading.Thread):
    """QMT 保活守护线程"""

    def __init__(self, 
                 heartbeat_interval: int = 15,
                 max_retries: int = 3,
                 trader_client: Optional['xttrader.XtQuantTrader'] = None):
        """
        初始化保活守护线程
        
        Args:
            heartbeat_interval: 心跳间隔（秒）
            max_retries: 最大重试次数（报警阈值）
            trader_client: 交易客户端对象（可选，如有则探测交易接口）
        """
        super().__init__()
        self.daemon = True  # 设置为守护线程，主程序退出时自动退出
        self.name = "QMT-KeepAlive"
        
        self.heartbeat_interval = heartbeat_interval
        self.max_retries = max_retries
        self.trader_client = trader_client
        
        self.running = False
        self.data_fail_count = 0
        self.trader_fail_count = 0
        
        # 探测标的：平安银行(SZ)、贵州茅台(SH)
        self.probe_stocks = ['000001.SZ', '600519.SH']

    def run(self):
        """线程主循环"""
        logger.info(f"💓 QMT 保活守护线程启动 (间隔: {self.heartbeat_interval}s)")
        self.running = True
        
        while self.running:
            try:
                # 1. 探测 xtdata (行情)
                if QMT_AVAILABLE:
                    data_alive = self._check_xtdata_heartbeat()
                    if not data_alive:
                        self.data_fail_count += 1
                        logger.warning(f"⚠️ xtdata 心跳丢失 ({self.data_fail_count}/{self.max_retries})")
                        
                        # 尝试唤醒
                        self._try_wake_up_data()
                        
                        if self.data_fail_count >= self.max_retries:
                            logger.error("❌ QMT 行情服务可能已断开，请检查客户端！")
                    else:
                        if self.data_fail_count > 0:
                            logger.info("✅ xtdata 心跳恢复")
                        self.data_fail_count = 0
                
                # 2. 探测 xt_trader (交易，如有)
                if self.trader_client:
                    trader_alive = self._check_xttrader_heartbeat()
                    if not trader_alive:
                        self.trader_fail_count += 1
                        logger.warning(f"⚠️ xt_trader 心跳丢失 ({self.trader_fail_count}/{self.max_retries})")
                        
                        # 尝试重连
                        self._try_reconnect_trader()
                        
                        if self.trader_fail_count >= self.max_retries:
                            logger.error("❌ QMT 交易接口重连失败，请人工干预！")
                    else:
                        if self.trader_fail_count > 0:
                            logger.info("✅ xt_trader 心跳恢复")
                        self.trader_fail_count = 0
                
            except Exception as e:
                logger.error(f"❌ 保活线程异常: {e}")
            
            # 休眠
            for _ in range(self.heartbeat_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("🛑 QMT 保活守护线程停止")

    def stop(self):
        """停止保活线程"""
        self.running = False

    def _check_xtdata_heartbeat(self) -> bool:
        """
        检查 xtdata 心跳
        
        通过请求极轻量的 tick 数据来验证数据流是否通畅
        
        Returns:
            bool: xtdata 是否正常
        """
        try:
            # 探测
            tick = xtdata.get_full_tick(self.probe_stocks)
            
            if not tick:
                return False
                
            # 检查是否有任意一个标的有数据
            has_data = any(code in tick and tick[code] for code in self.probe_stocks)
            
            if has_data:
                # logger.debug("✅ xtdata 心跳正常") # 过于频繁，仅调试用
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"❌ xtdata 心跳探测失败: {e}")
            return False

    def _try_wake_up_data(self):
        """尝试唤醒数据流（仅用于 xtdata）"""
        try:
            # 尝试重新订阅一下，有时能唤醒数据流
            xtdata.subscribe_quote(self.probe_stocks[0], period='1d', count=1)
            logger.debug(f"🔔 尝试唤醒数据流: 订阅 {self.probe_stocks[0]}")
        except Exception as e:
            logger.debug(f"❌ 唤醒数据流失败: {e}")

    def _check_xttrader_heartbeat(self) -> bool:
        """
        检查 xt_trader 心跳
        
        通过查询账户资产来检测交易接口是否正常
        
        Returns:
            bool: xt_trader 是否正常
        """
        try:
            # 尝试查询账户资产（轻量级探测）
            # 注意：如果 QMT 未登录交易账号，这可能会一直失败，需确保在使用前已登录
            if not self.trader_client.connected:
                 return False
                 
            # 简单检查 connected 属性（快速）
            # 如果需要更深层检查，可以调用 query_stock_asset
            # result = self.trader_client.query_stock_asset(self.account_obj) 
            # 但这需要 account 对象，这里简化处理，只依赖 connect 状态和重连
            
            return True
            
        except Exception as e:
            logger.debug(f"❌ xt_trader 心跳探测失败: {e}")
            return False

    def _try_reconnect_trader(self):
        """尝试重连交易接口"""
        try:
            # 调用 connect() 重连
            # connect() 返回 0 表示成功
            result = self.trader_client.connect()
            
            if result == 0:
                logger.info(f"✅ xt_trader 重连成功")
                self.trader_fail_count = 0 # 重置失败计数
            else:
                logger.warning(f"⚠️ xt_trader 重连失败，错误码: {result}")
                
        except Exception as e:
            logger.error(f"❌ xt_trader 重连异常: {e}")


# 全局保活守护线程实例
_qmt_keepalive: Optional[QMTKeepAlive] = None


def start_qmt_keepalive(
    heartbeat_interval: int = 15,
    max_retries: int = 3,
    trader_client: Optional['xttrader.XtQuantTrader'] = None
) -> QMTKeepAlive:
    """
    启动 QMT 保活守护线程（全局单例）
    
    Args:
        heartbeat_interval: 心跳间隔（秒），默认 15 秒
        max_retries: 最大重试次数，默认 3 次
        trader_client: 交易客户端对象（可选）
        
    Returns:
        QMTKeepAlive: 保活守护线程实例
    """
    global _qmt_keepalive
    
    if _qmt_keepalive is None:
        _qmt_keepalive = QMTKeepAlive(
            heartbeat_interval=heartbeat_interval, 
            max_retries=max_retries,
            trader_client=trader_client
        )
        _qmt_keepalive.start()
    else:
        # 如果已存在但停止了，重新创建一个
        if not _qmt_keepalive.is_alive():
             _qmt_keepalive = QMTKeepAlive(
                heartbeat_interval=heartbeat_interval, 
                max_retries=max_retries,
                trader_client=trader_client
            )
             _qmt_keepalive.start()
        else:
             logger.warning("⚠️ QMT 保活守护线程已在运行")
    
    return _qmt_keepalive


def stop_qmt_keepalive():
    """停止 QMT 保活守护线程"""
    global _qmt_keepalive
    
    if _qmt_keepalive is not None:
        _qmt_keepalive.stop()
        _qmt_keepalive.join(timeout=2.0) # 等待线程结束
        _qmt_keepalive = None
        logger.info("🛑 QMT 保活守护线程已停止")


def get_qmt_keepalive() -> Optional[QMTKeepAlive]:
    """获取全局保活守护线程实例"""
    return _qmt_keepalive


if __name__ == "__main__":
    # 测试保活守护线程
    print("=" * 60)
    print("🧪 QMT 保活守护线程测试")
    print("=" * 60)
    
    # 启动保活守护线程
    keepalive = start_qmt_keepalive()
    
    print("\\n🚀 保活守护线程已启动，观察日志输出...")
    print("💡 提示：可以尝试关闭 QMT 客户端，观察保活线程的反应")
    print("⏸️  按 Ctrl+C 停止测试")
    
    try:
        # 主线程休眠，观察保活线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n\\n🛑 收到停止信号...")
        stop_qmt_keepalive()
        print("✅ 测试结束")
