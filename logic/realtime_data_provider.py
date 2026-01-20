#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时数据提供者
从新浪 API 获取实时行情数据
V17.1: 时区校准 - 统一使用北京时间
V18.6: 集成东方财富 DDE 数据适配器（异步化）
V18.6.1: 后台线程异步获取 DDE 数据，避免阻塞主线程
"""

from logic.data_provider_factory import DataProvider
from logic.logger import get_logger
from logic.utils import Utils
from logic.data_adapter_akshare import MoneyFlowAdapter
import config_system as config
from datetime import datetime
import threading
import time
from typing import Dict, Any, List

logger = get_logger(__name__)


class RealtimeDataProvider(DataProvider):
    """
    实时数据提供者

    功能：
    - 从新浪 API 获取实时行情数据
    - 支持并发请求提升性能
    - 自动处理数据清洗和格式化
    - 🆕 V16.2: 数据保质期校验
    - 🆕 V18.6.1: 后台线程异步获取 DDE 数据，避免阻塞主线程
    """

    def __init__(self, **kwargs):
        """初始化实时数据提供者"""
        super().__init__()
        self.timeout = config.API_TIMEOUT
        # 🚀 V19.1 优化：放宽数据保质期阈值，避免网络拥堵时误报数据过期
        self.data_freshness_threshold = 180  # 3分钟（原15秒）
        self.base_threshold = 180  # 基础阈值
        self.max_threshold = 600  # 最大阈值（10分钟）

        # 🆕 优化 2：ACTIVE_MONITOR 和 PASSIVE_WATCH 动态优先级机制
        self.active_monitor = set()  # 高频监控列表（每秒）
        self.passive_watch = set()  # 低频监控列表（每30秒）
        self.stock_priority = {}  # {stock_code: priority_score} 优先级分数
        self.last_update_time = {}  # {stock_code: last_update_time} 上次更新时间
        self.active_interval = 1  # 高频监控间隔（秒）
        self.passive_interval = 30  # 低频监控间隔（秒）

        # 🆕 V18.6.1: DDE 缓存和后台线程
        self.dde_cache = {}  # {stock_code: dde_data} DDE 数据缓存
        self.ma4_cache = {}  # {stock_code: ma4_value} MA4 缓存（用于快速计算乖离率）
        self.dde_velocity_cache = {}  # {stock_code: velocity} DDE 加速度缓存
        self.running = True  # 后台线程运行标志
        self.dde_update_interval = 30  # 🚀 V19 优化：DDE 更新间隔延长到 30 秒（降低 GIL 占用）
        self.monitor_list = []  # 监控股票列表

        # 启动后台线程抓取 DDE
        self.dde_thread = threading.Thread(target=self._background_fetch_dde, daemon=True)
        self.dde_thread.start()
        logger.info("✅ [V18.6.1] DDE 后台线程已启动")

    def _background_fetch_dde(self):
        """
        🆕 V18.6.1: 后台持续更新 DDE 数据，不阻塞主线程
        🚀 V19 优化：降低GIL占用，延长轮询间隔

        每 20-30 秒更新一次 DDE 数据，避免在主线程中阻塞网络请求
        添加 time.sleep(0.01) 主动释放 GIL，防止卡死主线程
        """
        logger.info("🔄 [V18.6.1] DDE 后台线程开始运行")

        while self.running:
            try:
                # 如果有监控列表，批量获取 DDE 数据
                if self.monitor_list:
                    # 保存上一次的 DDE 数据，用于计算加速度
                    last_dde_cache = self.dde_cache.copy()

                    # 批量获取 DDE 数据
                    new_data = MoneyFlowAdapter.batch_get_dde(self.monitor_list)

                    # 🚀 V19 优化：短暂休眠，主动释放 GIL，防止卡死主线程
                    time.sleep(0.01)

                    if new_data:
                        # 更新缓存
                        self.dde_cache.update(new_data)

                        # 计算 DDE 加速度（Derivative）
                        for code, dde_data in new_data.items():
                            if code in last_dde_cache:
                                last_dde = last_dde_cache[code].get('dde_net_amount', 0)
                                current_dde = dde_data.get('dde_net_amount', 0)
                                # 加速度 = (当前 DDE - 上次 DDE) / 时间间隔（秒）
                                velocity = (current_dde - last_dde) / self.dde_update_interval
                                self.dde_velocity_cache[code] = velocity

                                # 检测点火信号（加速度突然暴增）
                                if velocity > 1000000:  # 每秒净流入超过 100 万
                                    logger.info(f"🔥 [点火信号] {code} DDE 加速度暴增: {velocity/1000000:.2f}万/秒")

                    logger.info(f"✅ [V18.6.1] DDE 后台更新完成，共 {len(new_data)} 只股票")

            except Exception as e:
                logger.error(f"❌ [V18.6.1] DDE 后台线程错误: {e}")

            # 🚀 V19 优化：延长轮询间隔到 20-30 秒（DDE 变化没那么快，不需要频繁更新）
            # 这样可以大幅降低 GIL 占用，提升 UI 响应速度
            time.sleep(self.dde_update_interval)

        logger.info("🛑 [V18.6.1] DDE 后台线程已停止")

    def set_monitor_list(self, stock_list: List[str]):
        """
        设置监控股票列表

        Args:
            stock_list: 股票代码列表
        """
        self.monitor_list = stock_list
        logger.info(f"📊 [V18.6.1] 监控列表已更新，共 {len(stock_list)} 只股票")

        # 预计算 MA4（用于快速计算乖离率）
        self._precompute_ma4(stock_list)

    def _precompute_ma4(self, stock_list):
        """
        🆕 V18.6.1: 盘前预计算 MA4，用于快速计算实时 MA5
        🚀 V19.1 优化：使用 PreMarketCache 进行预计算，避免重复下载

        MA5 变化很慢，可以在盘前预计算昨天的 MA4，
        盘中只需要用 (Yesterday_MA4 * 4 + Current_Price) / 5 就能算出毫秒级精度的实时 MA5

        Args:
            stock_list: 股票代码列表
        """
        logger.info(f"🔄 [V18.6.1] 开始预计算 MA4，共 {len(stock_list)} 只股票")

        # 🚀 V19.1 优化：使用 PreMarketCache 进行预计算
        from logic.pre_market_cache import get_pre_market_cache
        cache = get_pre_market_cache()

        # 检查缓存是否有效
        if cache.is_cache_valid():
            logger.info(f"✅ [V18.6.1] 使用缓存中的MA4数据，共 {len(cache.ma4_cache)} 只股票")
            # 将缓存数据复制到本地
            self.ma4_cache = cache.ma4_cache.copy()
            return

        # 缓存无效，执行预计算
        success_count = cache.precompute_ma4(stock_list, max_stocks=len(stock_list))

        # 将缓存数据复制到本地
        self.ma4_cache = cache.ma4_cache.copy()

        logger.info(f"✅ [V18.6.1] MA4 预计算完成，共 {len(self.ma4_cache)} 只股票（成功: {success_count}）")

    def stop_background_thread(self):
        """停止后台线程"""
        self.running = False
        if self.dde_thread.is_alive():
            self.dde_thread.join(timeout=5)
        logger.info("🛑 [V18.6.1] DDE 后台线程已停止")

    def get_realtime_data(self, stock_list):
        """
        获取实时数据
        
        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表
        
        Returns:
            list: 股票数据列表
        """
        try:
            import easyquotation as eq
            
            # 初始化行情接口
            quotation = eq.use('sina')
            
            # 提取股票代码
            if isinstance(stock_list[0], dict):
                codes = [stock['code'] for stock in stock_list]
            else:
                codes = stock_list
            
            # 🚀 V19.4 盲扫模式：批次处理，防止扫描中断
            # 将大列表拆分为小批次，每次只请求 20 只，失败了不影响下一批
            batch_size = 20
            all_market_data = {}
            
            for i in range(0, len(codes), batch_size):
                batch = codes[i : i + batch_size]
                
                try:
                    # 获取实时数据
                    market_data = quotation.stocks(batch)
                    all_market_data.update(market_data)
                    
                    # 🚀 V19.4 优化：短暂休眠，主动释放 GIL，防止卡死主线程
                    import time
                    time.sleep(0.01)
                    
                except Exception as e:
                    # [关键] 捕获错误，打印日志，但绝不 crash！
                    logger.error(f"⚠️ 批次 {i} 扫描失败，跳过: {e}")
                    continue  # 继续下一批！
            
            market_data = all_market_data
            
            # V16.2 新增：数据保质期校验
            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            # 判断是否在竞价期间（9:15-9:30）
            is_auction_period = (current_hour == 9 and 15 <= current_minute < 30)
            
            # 格式化数据
            result = []
            for code, data in market_data.items():
                if not data:
                    continue
                
                # V16.2 新增：检查数据时间戳
                data_time_str = data.get('time', '')
                if data_time_str and not is_auction_period:
                    try:
                        # 解析数据时间（格式可能是 "09:30:05" 或类似）
                        data_time = datetime.strptime(data_time_str, '%H:%M:%S')
                        data_time = data_time.replace(year=current_time.year, month=current_time.month, day=current_time.day)

                        # 检查数据是否过期（超过阈值）
                        time_diff = (current_time - data_time).total_seconds()

                        # 🚀 V19.1 优化：动态阈值逻辑
                        from logic.market_status import MarketStatusChecker
                        checker = MarketStatusChecker()
                        current_time_time = current_time.time()

                        # 动态计算阈值
                        dynamic_threshold = self.base_threshold  # 默认180秒

                        # 1. 午休时段豁免（11:30-13:00）
                        is_lunch_break = checker.is_noon_break()
                        if is_lunch_break:
                            dynamic_threshold = 5500  # 1.5小时

                        # 2. 开盘初期豁免（9:30-9:35 和 13:00-13:05）
                        # 开盘初期数据更新可能有延迟，允许更大的延迟
                        from datetime import time as dt_time
                        morning_open_start = dt_time(9, 30)
                        morning_open_end = dt_time(9, 35)
                        afternoon_open_start = dt_time(13, 0)
                        afternoon_open_end = dt_time(13, 5)

                        is_morning_open = (morning_open_start <= current_time_time < morning_open_end)
                        is_afternoon_open = (afternoon_open_start <= current_time_time < afternoon_open_end)

                        if is_morning_open or is_afternoon_open:
                            # 开盘初期前10分钟允许更大的延迟
                            if (is_morning_open and current_time_time < dt_time(9, 40)) or \
                               (is_afternoon_open and current_time_time < dt_time(13, 10)):
                                dynamic_threshold = 600  # 10分钟
                            else:
                                dynamic_threshold = 300  # 5分钟

                        # 3. 收盘前豁免（14:50-15:00）
                        closing_start = dt_time(14, 50)
                        closing_end = dt_time(15, 0)
                        if closing_start <= current_time_time < closing_end:
                            dynamic_threshold = 300  # 5分钟

                        # 检查是否过期
                        if time_diff > dynamic_threshold:
                            logger.warning(f"⚠️ [数据过期] {code} 数据时间 {data_time_str} 距今 {time_diff:.0f}秒（阈值:{dynamic_threshold}秒），跳过交易")
                            continue
                    except Exception as e:
                        logger.warning(f"⚠️ [时间解析失败] {code} 无法解析时间戳 {data_time_str}: {e}")
                
                stock_info = {
                    'code': code,
                    'name': data.get('name', ''),
                    'price': data.get('now', 0),
                    'change_pct': data.get('percent', 0) / 100,  # 转换为小数
                    'volume': data.get('volume', 0),
                    'amount': data.get('amount', 0),
                    'open': data.get('open', 0),
                    'high': data.get('high', 0),
                    'low': data.get('low', 0),
                    'pre_close': data.get('close', 0),
                    'data_timestamp': data_time_str,  # V16.2 新增
                }
                result.append(stock_info)

            # 🆕 V18.6.1: 从内存缓存中瞬间注入 DDE 数据和乖离率（0 延迟）
            # 不再同步调用网络请求，避免阻塞主线程
            if result:
                for stock_info in result:
                    code = stock_info['code']

                    # 从缓存中注入 DDE 数据（瞬间完成）
                    if code in self.dde_cache:
                        dde_data = self.dde_cache[code]
                        stock_info['dde_net_amount'] = dde_data.get('dde_net_amount', 0)
                        stock_info['scramble_degree'] = dde_data.get('scramble_degree', 0)
                        stock_info['super_big_order'] = dde_data.get('super_big_order', 0)
                        stock_info['big_order'] = dde_data.get('big_order', 0)
                    else:
                        # 没有缓存数据时补 0，绝不发起网络请求
                        stock_info['dde_net_amount'] = 0
                        stock_info['scramble_degree'] = 0
                        stock_info['super_big_order'] = 0
                        stock_info['big_order'] = 0

                    # 注入 DDE 加速度
                    if code in self.dde_velocity_cache:
                        stock_info['dde_velocity'] = self.dde_velocity_cache[code]
                    else:
                        stock_info['dde_velocity'] = 0

                    # 注入乖离率（使用缓存或快速计算）
                    current_price = stock_info.get('price', 0)
                    if current_price > 0:
                        # 如果有 MA4 缓存，快速计算实时 MA5
                        if code in self.ma4_cache:
                            ma4 = self.ma4_cache[code]
                            # 实时 MA5 = (昨天 MA4 * 4 + 当前价格) / 5
                            realtime_ma5 = (ma4 * 4 + current_price) / 5
                            bias = (current_price - realtime_ma5) / realtime_ma5 * 100
                            stock_info['bias_rate'] = round(bias, 2)
                        else:
                            # 没有缓存，使用 Akshare 计算（较慢，但只在第一次调用时慢）
                            bias = MoneyFlowAdapter.calculate_ma_bias(code, current_price)
                            stock_info['bias_rate'] = bias
                    else:
                        stock_info['bias_rate'] = 0

            return result
            
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return []
    
    def get_market_data(self):
        """
        获取市场整体数据
        
        Returns:
            dict: 市场数据
        """
        try:
            from logic.data_manager import DataManager
            
            dm = DataManager()
            
            # 获取今日涨停股票
            limit_up_stocks = dm.get_limit_up_stocks()
            
            # 获取市场情绪
            from logic.market_sentiment import MarketSentiment
            ms = MarketSentiment()
            sentiment_data = ms.get_market_sentiment_score()
            
            return {
                'limit_up_count': len(limit_up_stocks),
                'market_heat': sentiment_data.get('score', 50),
                'mal_rate': sentiment_data.get('mal_rate', 0.3),
                'regime': sentiment_data.get('regime', 'CHAOS'),
            }
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return {
                'limit_up_count': 0,
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
            }
    
    def get_history_data(self, symbol: str, period: str = 'daily', adjust: str = 'qfq'):
        """
        获取历史数据（使用 AkShare）
        
        Args:
            symbol: 股票代码
            period: 周期（daily, weekly, monthly）
            adjust: 复权方式（qfq: 前复权, hfq: 后复权, none: 不复权）
        
        Returns:
            DataFrame: 历史数据
        """
        try:
            import akshare as ak
            import pandas as pd
            
            # 转换股票代码格式（AkShare 使用 'sh' 或 'sz' 前缀）
            if symbol.startswith('6'):
                ak_symbol = f'sh{symbol}'
            else:
                ak_symbol = f'sz{symbol}'
            
            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=ak_symbol, period=period, adjust=adjust)
            
            # 重命名列以保持一致性
            if not df.empty:
                df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '涨跌幅': 'change_pct',
                    '涨跌额': 'change_amount'
                }, inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            # 返回空的 DataFrame
            import pandas as pd
            return pd.DataFrame()
    
    def update_stock_priority(self, stock_code: str, priority_score: float):
        """
        🆕 优化 2：更新股票优先级
        
        Args:
            stock_code: 股票代码
            priority_score: 优先级分数（0-100）
        """
        self.stock_priority[stock_code] = priority_score
        
        # 动态切换监控级别
        if priority_score >= 70:
            # 高优先级：加入高频监控
            if stock_code not in self.active_monitor:
                self.active_monitor.add(stock_code)
                if stock_code in self.passive_watch:
                    self.passive_watch.remove(stock_code)
                logger.info(f"✅ [动态优先级] {stock_code} 切换为高频监控（优先级{priority_score:.1f}）")
        elif priority_score >= 40:
            # 中优先级：加入低频监控
            if stock_code not in self.passive_watch:
                self.passive_watch.add(stock_code)
                if stock_code in self.active_monitor:
                    self.active_monitor.remove(stock_code)
                logger.info(f"📊 [动态优先级] {stock_code} 切换为低频监控（优先级{priority_score:.1f}）")
        else:
            # 低优先级：移除监控
            if stock_code in self.active_monitor:
                self.active_monitor.remove(stock_code)
            if stock_code in self.passive_watch:
                self.passive_watch.remove(stock_code)
            logger.info(f"⚠️ [动态优先级] {stock_code} 移除监控（优先级{priority_score:.1f}）")
    
    def should_update_stock(self, stock_code: str) -> bool:
        """
        🆕 优化 2：判断是否应该更新股票数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            bool: 是否应该更新
        """
        current_time = datetime.now()
        
        # 检查是否在高频监控列表中
        if stock_code in self.active_monitor:
            if stock_code in self.last_update_time:
                time_diff = (current_time - self.last_update_time[stock_code]).total_seconds()
                return time_diff >= self.active_interval
            return True
        
        # 检查是否在低频监控列表中
        if stock_code in self.passive_watch:
            if stock_code in self.last_update_time:
                time_diff = (current_time - self.last_update_time[stock_code]).total_seconds()
                return time_diff >= self.passive_interval
            return True
        
        # 不在监控列表中，不更新
        return False
    
    def mark_stock_updated(self, stock_code: str):
        """
        🆕 优化 2：标记股票已更新
        
        Args:
            stock_code: 股票代码
        """
        self.last_update_time[stock_code] = datetime.now()
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """
        🆕 优化 2：获取监控统计信息
        
        Returns:
            dict: 监控统计信息
        """
        return {
            'active_monitor_count': len(self.active_monitor),
            'passive_watch_count': len(self.passive_watch),
            'total_stocks': len(self.stock_priority),
            'active_interval': self.active_interval,
            'passive_interval': self.passive_interval
        }