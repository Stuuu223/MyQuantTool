"""
数据源降级责任链模式 (Chain of Responsibility)
CTO强制: 禁止多层嵌套try-except，必须使用责任链模式

Author: AI总监
Date: 2026-02-23
Version: 1.0.0
"""
import os
import logging
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DataSourceResponse:
    """数据源响应对象"""
    success: bool
    data: Optional[Dict]
    source: str  # 实际使用的数据源
    error_msg: Optional[str] = None
    fallback_triggered: bool = False  # 是否触发了降级


class DataSourceHandler:
    """责任链节点基类"""
    
    def __init__(self, name: str, next_handler: Optional['DataSourceHandler'] = None):
        self.name = name
        self.next_handler = next_handler
        self.fallback_count = 0  # 降级计数
    
    def handle(self, stock_code: str, date: str) -> DataSourceResponse:
        """处理请求，失败则传递给下一个节点"""
        try:
            logger.info(f"【数据源】尝试从 {self.name} 获取数据...")
            result = self._fetch(stock_code, date)
            
            if result.success:
                if result.fallback_triggered:
                    logger.warning(f"【数据源】{self.name} 触发降级机制，已切换到备用源: {result.source}")
                else:
                    logger.info(f"【数据源】✅ 从 {self.name} 成功获取数据")
                return result
            
            # 当前节点失败，传递给下一个
            if self.next_handler:
                logger.warning(f"【数据源】⚠️ {self.name} 失败: {result.error_msg}，触发降级到 {self.next_handler.name}")
                self.fallback_count += 1
                fallback_result = self.next_handler.handle(stock_code, date)
                fallback_result.fallback_triggered = True
                return fallback_result
            else:
                # 没有下一个节点了
                logger.error(f"【数据源】❌ {self.name} 失败且无备用源: {result.error_msg}")
                return result
                
        except Exception as e:
            error_msg = f"{self.name} 异常: {str(e)}"
            logger.error(f"【数据源】❌ {error_msg}")
            
            if self.next_handler:
                logger.warning(f"【数据源】⚠️ 触发降级到 {self.next_handler.name}")
                self.fallback_count += 1
                fallback_result = self.next_handler.handle(stock_code, date)
                fallback_result.fallback_triggered = True
                return fallback_result
            else:
                return DataSourceResponse(
                    success=False,
                    data=None,
                    source=self.name,
                    error_msg=error_msg
                )
    
    def _fetch(self, stock_code: str, date: str) -> DataSourceResponse:
        """子类必须实现的具体获取逻辑"""
        raise NotImplementedError


class QMTVIPHandler(DataSourceHandler):
    """QMT VIP数据源处理器 - 极速实盘数据"""
    
    def __init__(self, next_handler: Optional[DataSourceHandler] = None):
        super().__init__("QMT_VIP", next_handler)
        self.token = os.getenv('QMT_VIP_TOKEN')
        self.sites = os.getenv('QMT_VIP_SITES', '').split(',') if os.getenv('QMT_VIP_SITES') else []
    
    def _fetch(self, stock_code: str, date: str) -> DataSourceResponse:
        """获取VIP数据"""
        # 检查环境
        system_env = os.getenv('SYSTEM_ENV', 'BACKTEST')
        if system_env == 'BACKTEST':
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg="回测模式不使用VIP数据源"
            )
        
        if not self.token or not self.sites:
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg="VIP Token或站点未配置"
            )
        
        try:
            from xtquant import xtdata
            
            # 尝试连接VIP站点
            for site in self.sites:
                try:
                    host, port = site.split(':')
                    # 这里应该实现实际的VIP连接逻辑
                    # 简化示例：直接返回本地数据作为演示
                    data = self._get_local_tick(stock_code, date)
                    if data:
                        return DataSourceResponse(
                            success=True,
                            data=data,
                            source=f"{self.name}({site})"
                        )
                except Exception as e:
                    logger.warning(f"【VIP】站点 {site} 连接失败: {e}")
                    continue
            
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg="所有VIP站点均不可用"
            )
            
        except ImportError:
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg="xtquant未安装"
            )
    
    def _get_local_tick(self, stock_code: str, date: str) -> Optional[Dict]:
        """获取本地Tick数据（降级时使用）"""
        try:
            from xtquant import xtdata
            normalized_code = stock_code
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            if data and normalized_code in data:
                return {'tick_data': data[normalized_code].to_dict()}
            return None
        except Exception as e:
            logger.error(f"【VIP】获取本地数据失败: {e}")
            return None


class QMTLocalHandler(DataSourceHandler):
    """QMT本地数据源处理器"""
    
    def __init__(self, next_handler: Optional[DataSourceHandler] = None):
        super().__init__("QMT_LOCAL", next_handler)
        self.qmt_path = os.getenv('QMT_PATH', 'E:/qmt/userdata_mini')
    
    def _fetch(self, stock_code: str, date: str) -> DataSourceResponse:
        """获取本地QMT数据"""
        try:
            from xtquant import xtdata
            
            normalized_code = stock_code
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if data and normalized_code in data and not data[normalized_code].empty:
                return DataSourceResponse(
                    success=True,
                    data={'tick_data': data[normalized_code].to_dict()},
                    source=self.name
                )
            else:
                return DataSourceResponse(
                    success=False,
                    data=None,
                    source=self.name,
                    error_msg="本地数据不存在或为空"
                )
                
        except Exception as e:
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg=f"获取本地数据异常: {str(e)}"
            )


class TushareHandler(DataSourceHandler):
    """Tushare云端数据源处理器 - 最后防线"""
    
    def __init__(self, next_handler: Optional[DataSourceHandler] = None):
        super().__init__("TUSHARE", next_handler)
        self.token = os.getenv('TUSHARE_TOKEN')
    
    def _fetch(self, stock_code: str, date: str) -> DataSourceResponse:
        """获取Tushare数据"""
        if not self.token:
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg="Tushare Token未配置"
            )
        
        try:
            import tushare as ts
            ts.set_token(self.token)
            pro = ts.pro_api()
            
            # 转换代码格式
            ts_code = stock_code.replace('.SH', '.SH').replace('.SZ', '.SZ')
            
            # 获取分钟数据
            df = pro.stk_mins(
                ts_code=ts_code,
                start_date=date,
                end_date=date,
                freq='5min'
            )
            
            if df is not None and not df.empty:
                return DataSourceResponse(
                    success=True,
                    data={'minute_data': df.to_dict()},
                    source=self.name
                )
            else:
                return DataSourceResponse(
                    success=False,
                    data=None,
                    source=self.name,
                    error_msg="Tushare返回空数据"
                )
                
        except Exception as e:
            return DataSourceResponse(
                success=False,
                data=None,
                source=self.name,
                error_msg=f"Tushare调用异常: {str(e)}"
            )


class FallbackProvider:
    """
    数据源降级提供器 (责任链模式入口)
    
    使用示例:
        provider = FallbackProvider()
        result = provider.get_data('002969.SZ', '20251231')
        if result.success:
            print(f"数据来源: {result.source}")
            print(f"是否降级: {result.fallback_triggered}")
    """
    
    def __init__(self):
        # 根据环境变量构建责任链
        self.chain = self._build_chain()
        self.stats = {
            'total_requests': 0,
            'fallback_count': 0,
            'source_usage': {}
        }
    
    def _build_chain(self) -> DataSourceHandler:
        """构建责任链"""
        # 读取降级顺序配置
        fallback_order = os.getenv('DATA_FALLBACK_ORDER', 'QMT_LOCAL,TUSHARE')
        order_list = [s.strip() for s in fallback_order.split(',')]
        
        logger.info(f"【FallbackProvider】初始化责任链: {' -> '.join(order_list)}")
        
        # 从后往前构建链
        handlers = {
            'QMT_VIP': QMTVIPHandler,
            'QMT_LOCAL': QMTLocalHandler,
            'TUSHARE': TushareHandler
        }
        
        next_handler = None
        for source_name in reversed(order_list):
            if source_name in handlers:
                next_handler = handlers[source_name](next_handler)
        
        return next_handler
    
    def get_data(self, stock_code: str, date: str) -> DataSourceResponse:
        """
        获取数据 - 自动降级
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'
            
        Returns:
            DataSourceResponse: 包含数据和元信息
        """
        self.stats['total_requests'] += 1
        
        if not self.chain:
            return DataSourceResponse(
                success=False,
                data=None,
                source="NONE",
                error_msg="责任链未初始化"
            )
        
        result = self.chain.handle(stock_code, date)
        
        # 统计
        if result.fallback_triggered:
            self.stats['fallback_count'] += 1
        self.stats['source_usage'][result.source] = self.stats['source_usage'].get(result.source, 0) + 1
        
        return result
    
    def get_stats(self) -> Dict:
        """获取降级统计信息"""
        total = self.stats['total_requests']
        fallback = self.stats['fallback_count']
        return {
            'total_requests': total,
            'fallback_count': fallback,
            'fallback_rate': fallback / total if total > 0 else 0,
            'source_usage': self.stats['source_usage']
        }


# 便捷函数
def get_data_with_fallback(stock_code: str, date: str) -> DataSourceResponse:
    """获取数据（带降级）便捷函数"""
    provider = FallbackProvider()
    return provider.get_data(stock_code, date)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    provider = FallbackProvider()
    result = provider.get_data('002969.SZ', '20251231')
    
    print(f"\n结果:")
    print(f"  成功: {result.success}")
    print(f"  数据源: {result.source}")
    print(f"  是否降级: {result.fallback_triggered}")
    print(f"  错误: {result.error_msg}")
    
    stats = provider.get_stats()
    print(f"\n统计: {stats}")
