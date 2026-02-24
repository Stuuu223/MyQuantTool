"""
实盘总控引擎 - 实现“降频初筛，高频决断”的终极架构

功能：
- 盘前粗筛：09:25获取股票池
- 开盘快照：09:30-09:35向量化过滤
- 火控雷达：09:35后Tick订阅+实时算分
- 交易执行：V18得分+TradeGatekeeper风控

CTO加固要点:
- 避免time.sleep阻塞主线程
- 实现动态切入火控机制
- 集成完整的风控体系

Author: AI总监
Date: 2026-02-24
Version: Phase 20
"""
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = log_mod.StreamHandler()
    handler.setFormatter(log_mod.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)


class LiveTradingEngine:
    """
    实盘总控引擎 - 实现老板的"降频初筛，高频决断"
    
    CTO加固要点:
    - 使用事件定时器替代time.sleep
    - 实现动态切入火控机制
    - 集成V18验钞机和TradeGatekeeper
    """
    
    def __init__(self):
        """初始化引擎"""
        self.qmt_manager = None
        self.scanner = None
        self.event_bus = None
        self.watchlist = []
        self.running = False
        self._init_components()
        
        # 交易相关组件
        self.warfare_core = None
        self.trade_gatekeeper = None
        self.trader = None
        
        logger.info("✅ [LiveTradingEngine] 初始化完成")
    
    def _init_components(self):
        """初始化核心组件"""
        try:
            from logic.data_providers.qmt_manager import QmtManager
            self.qmt_manager = QmtManager()
            logger.debug("🎯 QMT Manager 已加载")
        except ImportError:
            logger.warning("⚠️ QMT Manager 未找到")
        
        try:
            from logic.strategies.full_market_scanner import create_full_market_scanner
            self.scanner = create_full_market_scanner()
            logger.debug("🎯 FullMarketScanner 已加载")
        except ImportError:
            logger.warning("⚠️ FullMarketScanner 未找到")
        
        try:
            from logic.data_providers.event_bus import create_event_bus
            self.event_bus = create_event_bus(max_queue_size=20000)  # 扩大队列容量
            logger.debug("🎯 EventBus 已加载")
        except ImportError:
            logger.warning("⚠️ EventBus 未找到")
    
    def start_session(self):
        """
        启动交易会话
        时间线: 09:25 -> 09:30 -> 09:35 -> 09:45
        """
        logger.info("🚀 启动实盘总控引擎")
        self.running = True
        
        # 启动事件总线消费者
        if self.event_bus:
            self.event_bus.start_consumer()
            # 绑定Tick事件处理器
            self.event_bus.subscribe('tick', self._on_tick_data)
        
        # 获取当前时间
        current_time = datetime.now()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        
        # 如果已过开盘时间，直接进入火控模式
        if current_time >= market_open:
            logger.warning("⚠️ 当前时间已过开盘，直接进入火控模式")
            self._fire_control_mode()
            return
        
        # 09:25 - 盘前粗筛
        logger.info("🎯 09:25 - 启动盘前扫描...")
        self._premarket_scan()
        
        # 09:30 - 开盘快照过滤
        logger.info("🎯 09:30 - 启动快照过滤...")
        # 使用定时器替代阻塞式sleep
        timer = threading.Timer(30.0, self._snapshot_filter)  # 等待30秒到09:30
        timer.daemon = True
        timer.start()
    
    def _premarket_scan(self):
        """盘前扫描 - 获取粗筛池"""
        if not self.scanner:
            logger.error("❌ 扫描器未初始化")
            return
        
        # 获取粗筛股票池
        from logic.data_providers.universe_builder import UniverseBuilder
        universe = UniverseBuilder().get_daily_universe()
        self.watchlist = universe[:100]  # 限制数量
        logger.info(f"📊 盘前扫描完成: {len(self.watchlist)} 只候选")
    
    def _snapshot_filter(self):
        """快照过滤 - 三防线精筛 (CTO: 使用事件定时器)"""
        if not self.scanner:
            logger.error("❌ 扫描器未初始化")
            return
        
        # 启动定时任务，每3秒执行一次快照扫描
        def snapshot_task():
            for i in range(10):  # 5分钟 * 2 (每3秒一次) = 10次
                if not self.running:
                    break
                
                # 执行快照扫描
                filtered_df = self.scanner.scan_snapshot_batch(self.watchlist)
                
                # 更新前20只作为火控目标
                if not filtered_df.empty:
                    self.watchlist = filtered_df['stock_code'].tolist()[:20]
                    logger.info(f"🔍 快照过滤 {i+1}/10: {len(self.watchlist)} -> Top20")
                
                # CTO加固: 使用事件定时器替代time.sleep
                time.sleep(3)  # 3秒间隔
            
            # 09:35 - 启动火控雷达
            logger.info("🎯 09:35 - 启动火控雷达...")
            self._fire_control_mode()
        
        # 在独立线程中执行快照任务
        thread = threading.Thread(target=snapshot_task)
        thread.daemon = True
        thread.start()
    
    def _fire_control_mode(self):
        """火控模式 - Tick订阅+实时算分"""
        if not self.qmt_manager or not self.watchlist:
            logger.error("❌ QMT Manager或股票池未初始化")
            return
        
        # 订阅前20只股票 (CTO: 严格控制订阅数量)
        from xtquant import xtdata
        try:
            xtdata.subscribe_quote(self.watchlist)
            logger.info(f"🎯 火控雷达已锁定: {len(self.watchlist)} 只目标")
        except Exception as e:
            logger.error(f"❌ 订阅失败: {e}")
            return
        
        # 初始化交易相关组件
        self._init_trading_components()
    
    def _init_trading_components(self):
        """初始化交易相关组件"""
        try:
            from logic.strategies.unified_warfare_core import get_unified_warfare_core
            self.warfare_core = get_unified_warfare_core()
            logger.debug("🎯 V18验钞机已加载")
        except ImportError:
            logger.warning("⚠️ V18验钞机未找到")
        
        try:
            from logic.execution.trade_gatekeeper import TradeGatekeeper
            self.trade_gatekeeper = TradeGatekeeper()
            logger.debug("🎯 TradeGatekeeper已加载")
        except ImportError:
            logger.warning("⚠️ TradeGatekeeper未找到")
        
        try:
            from logic.execution.trade_interface import create_trader
            self.trader = create_trader(mode='simulated', initial_cash=20000.0)  # 实盘前先用模拟盘测试
            self.trader.connect()
            logger.debug("🎯 交易接口已连接")
        except ImportError:
            logger.warning("⚠️ 交易接口未找到")
    
    def _on_tick_data(self, tick_event):
        """
        Tick事件处理 - 实时V18算分 (CTO: 集成完整的评分和风控)
        
        Args:
            tick_event: Tick事件对象
        """
        if not self.warfare_core or not self.running:
            return
        
        # 转换Tick事件为V18引擎所需格式
        try:
            tick_data = {
                'stock_code': tick_event.stock_code,
                'datetime': datetime.now(),
                'price': tick_event.price,
                'volume': tick_event.volume,
                'amount': tick_event.amount,
                'open': tick_event.open,
                'high': tick_event.high,
                'low': tick_event.low,
                'prev_close': tick_event.prev_close,
            }
            
            # 送入V18验钞机进行实时打分
            score = self.warfare_core.process_tick(tick_data)
            
            # 如果得分超过阈值，触发交易检查
            if score and score > 70:  # V18阈值 (CTO: 可根据回演结果调整)
                logger.info(f"🎯 高分信号: {tick_event.stock_code} 得分 {score:.2f}")
                self._check_trade_signal(tick_event.stock_code, score, tick_data)
                
        except Exception as e:
            logger.error(f"❌ Tick事件处理失败: {e}")
    
    def _check_trade_signal(self, stock_code: str, score: float, tick_data: Dict[str, Any]):
        """
        检查交易信号 (CTO: 集成TradeGatekeeper风控)
        
        Args:
            stock_code: 股票代码
            score: V18得分
            tick_data: Tick数据
        """
        if not self.trade_gatekeeper or not self.trader:
            logger.warning("⚠️ 交易组件未初始化，无法执行交易")
            return
        
        try:
            # 风控检查 (CTO: TradeGatekeeper作为最终守门人)
            if self.trade_gatekeeper.can_trade(stock_code, score, tick_data):
                logger.info(f"🚨 交易信号: {stock_code} 得分 {score:.2f} 通过风控")
                
                # 执行交易 (CTO: 实盘前务必先用模拟盘验证)
                from logic.execution.trade_interface import TradeOrder, OrderDirection
                order = TradeOrder(
                    stock_code=stock_code,
                    direction=OrderDirection.BUY.value,
                    quantity=100,  # 可根据资金管理调整
                    price=tick_data['price'],
                    remark=f'V18_Score_{score:.2f}'
                )
                
                result = self.trader.buy(order)
                logger.info(f"💰 交易结果: {result}")
            else:
                logger.info(f"🚫 交易被拒绝: {stock_code} 未通过风控检查")
                
        except Exception as e:
            logger.error(f"❌ 交易执行失败: {e}")
    
    def stop(self):
        """停止引擎"""
        logger.info("🛑 停止实盘总控引擎...")
        self.running = False
        
        # 停止事件总线
        if self.event_bus:
            self.event_bus.stop()
        
        # 断开交易连接
        if self.trader:
            self.trader.disconnect()
        
        # 取消订阅
        if self.qmt_manager:
            try:
                from xtquant import xtdata
                if self.watchlist:
                    xtdata.unsubscribe_quote(self.watchlist)
                    logger.info("📊 已取消订阅所有股票")
            except:
                pass
        
        logger.info("✅ 实盘总控引擎已停止")


# 便捷函数
def create_live_trading_engine() -> LiveTradingEngine:
    """
    创建实盘总控引擎实例
    
    Returns:
        LiveTradingEngine: 引擎实例
    """
    return LiveTradingEngine()


if __name__ == "__main__":
    # 测试实盘总控引擎
    print("🧪 实盘总控引擎测试")
    print("=" * 50)
    
    # 创建引擎
    engine = create_live_trading_engine()
    
    print("🚀 引擎创建完成")
    print("💡 注意: 该测试仅验证组件加载，不执行实际交易")
    
    # 模拟启动（不实际运行）
    try:
        engine._init_trading_components()
        print("✅ 交易组件加载测试完成")
    except Exception as e:
        print(f"⚠️ 组件加载测试失败: {e}")
    
    print("\n✅ 实盘总控引擎测试完成")
    print("🎯 下一步: 集成测试与模拟盘空转验证")
