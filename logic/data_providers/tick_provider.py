#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TickProvider - QMT Tick数据下载统一封装类

功能：
1. 封装xtdata/QMT连接、重试、限流、路径管理
2. 提供统一方法：download_ticks(stock_list, start_date, end_date)
3. 封装Token服务启动和管理
4. 提供数据覆盖率检查

Author: iFlow CLI (T4任务)
Date: 2026-02-19
Version: 1.0.0
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 配置日志
logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DownloadResult:
    """单个股票下载结果"""
    stock_code: str
    status: DownloadStatus
    message: str = ""
    retry_count: int = 0
    duration_ms: float = 0.0


@dataclass
class BatchDownloadResult:
    """批量下载结果"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[DownloadResult] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """获取总耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total > 0:
            return self.success / self.total
        return 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total': self.total,
            'success': self.success,
            'failed': self.failed,
            'skipped': self.skipped,
            'success_rate': f"{self.success_rate:.2%}",
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'results': [
                {
                    'stock_code': r.stock_code,
                    'status': r.status.value,
                    'message': r.message,
                    'retry_count': r.retry_count,
                    'duration_ms': r.duration_ms
                }
                for r in self.results
            ]
        }


class TickProvider:
    """
    QMT Tick数据下载统一封装类
    
    使用示例：
        provider = TickProvider()
        if provider.connect():
            result = provider.download_ticks(
                stock_codes=['000001.SZ', '600000.SH'],
                start_date='20250101',
                end_date='20250131'
            )
            print(f"成功率: {result.success_rate:.2%}")
            provider.close()
    """
    
    # 默认VIP Token
    DEFAULT_VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"
    
    # 默认数据目录为QMT客户端目录（不得下载到项目内）
    DEFAULT_DATA_DIR = Path('E:/qmt/userdata_mini/datadir')
    
    # 默认重试配置
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY_BASE = 2  # 指数退避基数（秒）
    DEFAULT_RATE_LIMIT_DELAY = 0.3  # 请求间隔（秒）
    
    # 默认端口范围
    DEFAULT_PORT_RANGE = (58800, 58850)
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化TickProvider
        
        Args:
            config_path: 配置文件路径，默认为None（使用默认配置）
        """
        self.config = self._load_config(config_path)
        self._xtdata = None
        self._xtdc = None
        self._connected = False
        self._listen_port = None
        self._data_dir = Path(self.config.get('data_dir', self.DEFAULT_DATA_DIR))
        
        # 重试和限流配置
        self.max_retries = self.config.get('max_retries', self.DEFAULT_MAX_RETRIES)
        self.retry_delay_base = self.config.get('retry_delay_base', self.DEFAULT_RETRY_DELAY_BASE)
        self.rate_limit_delay = self.config.get('rate_limit_delay', self.DEFAULT_RATE_LIMIT_DELAY)
        
        # VIP Token
        self.vip_token = self.config.get('vip_token', self.DEFAULT_VIP_TOKEN)
        
        # 端口范围
        self.port_range = tuple(self.config.get('port_range', self.DEFAULT_PORT_RANGE))
        
        # 确保数据目录存在
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"TickProvider初始化完成，数据目录: {self._data_dir}")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        if config_path is None:
            # 尝试加载默认配置
            default_config_path = PROJECT_ROOT / 'config' / 'tick_provider_config.json'
            if default_config_path.exists():
                config_path = str(default_config_path)
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        return {}
    
    def _ensure_xtquant(self) -> bool:
        """确保xtquant模块可用"""
        if self._xtdata is not None and self._xtdc is not None:
            return True
        
        try:
            # 尝试导入xtquant
            from xtquant import xtdatacenter as xtdc
            from xtquant import xtdata
            self._xtdata = xtdata
            self._xtdc = xtdc
            logger.info("xtquant模块导入成功")
            return True
        except ImportError as e:
            logger.error(f"xtquant模块导入失败: {e}")
            return False
    
    def connect(self, timeout: int = 30) -> bool:
        """
        连接到QMT行情服务
        
        Args:
            timeout: 连接超时时间（秒）
            
        Returns:
            是否连接成功
        """
        if self._connected:
            logger.info("已经连接到行情服务")
            return True
        
        # 检查xtquant是否可用
        if not self._ensure_xtquant():
            logger.error("xtquant模块不可用，无法连接")
            return False
        
        try:
            # 1. 设置数据目录
            self._xtdc.set_data_home_dir(str(self._data_dir))
            logger.info(f"📂 数据目录: {self._data_dir}")
            
            # 2. 设置Token
            self._xtdc.set_token(self.vip_token)
            logger.info(f"🔑 Token: {self.vip_token[:6]}...{self.vip_token[-4:]}")
            
            # 3. 初始化
            self._xtdc.init()
            
            # 4. 启动监听端口
            self._listen_port = self._xtdc.listen(port=self.port_range)
            _, port = self._listen_port
            logger.info(f"🚀 行情服务已启动，监听端口: {self._listen_port}")
            
            # 5. 连接到行情服务
            self._xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)
            
            # 6. 等待连接成功
            logger.info("⏳ 等待连接行情服务...")
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 测试连接
                    test_data = self._xtdata.get_market_data(['close'], ['600519.SH'], period='1d', count=1)
                    if test_data is not None:
                        self._connected = True
                        logger.info("✅ 成功连接到行情服务！")
                        return True
                except Exception:
                    pass
                time.sleep(1)
            
            logger.error(f"❌ 连接行情服务超时（{timeout}秒）")
            return False
            
        except Exception as e:
            logger.error(f"❌ 连接行情服务失败: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def close(self):
        """关闭连接并清理资源"""
        if self._connected and self._xtdata:
            try:
                # xtdata没有显式的disconnect方法，但我们可以清理引用
                pass
            except Exception as e:
                logger.warning(f"关闭连接时出错: {e}")
        
        self._connected = False
        self._listen_port = None
        logger.info("TickProvider连接已关闭")
    
    def _normalize_stock_code(self, code: str) -> str:
        """
        标准化股票代码格式为QMT格式（######.SH / ######.SZ）
        
        Args:
            code: 股票代码，支持多种格式（600519, sh600519, 600519.SH等）
            
        Returns:
            QMT标准格式的股票代码
        """
        if not code:
            return code
        
        code = code.strip().upper()
        
        # 如果已经包含交易所后缀，直接返回
        if code.endswith('.SH') or code.endswith('.SZ') or code.endswith('.BJ'):
            return code
        
        # 移除可能的分隔符
        code = code.replace('.', '')
        
        # 提取6位数字代码
        if code.startswith('SH'):
            return f"{code[2:]}.SH"
        elif code.startswith('SZ'):
            return f"{code[2:]}.SZ"
        elif code.startswith('BJ'):
            return f"{code[2:]}.BJ"
        elif code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        elif code.startswith(('8', '4')):
            return f"{code}.BJ"
        else:
            # 默认为上海主板
            return f"{code}.SH"
    
    def _download_single_tick(
        self, 
        stock_code: str, 
        start_time: str, 
        end_time: str
    ) -> DownloadResult:
        """
        下载单只股票的Tick数据（带重试）
        
        Args:
            stock_code: QMT格式股票代码（如000001.SZ）
            start_time: 开始时间（格式：YYYYMMDDHHMMSS）
            end_time: 结束时间（格式：YYYYMMDDHHMMSS）
            
        Returns:
            DownloadResult: 下载结果
        """
        start_ms = time.time() * 1000
        
        for attempt in range(self.max_retries):
            try:
                self._xtdata.download_history_data(
                    stock_code=stock_code,
                    period='tick',
                    start_time=start_time,
                    end_time=end_time
                )
                
                duration_ms = time.time() * 1000 - start_ms
                logger.debug(f"下载成功: {stock_code} (耗时{duration_ms:.0f}ms)")
                
                return DownloadResult(
                    stock_code=stock_code,
                    status=DownloadStatus.SUCCESS,
                    message="下载成功",
                    retry_count=attempt,
                    duration_ms=duration_ms
                )
                
            except Exception as e:
                logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.max_retries}): {stock_code} - {e}")
                
                if attempt < self.max_retries - 1:
                    # 指数退避
                    sleep_time = self.retry_delay_base ** attempt
                    logger.info(f"等待{sleep_time}秒后重试...")
                    time.sleep(sleep_time)
                else:
                    duration_ms = time.time() * 1000 - start_ms
                    return DownloadResult(
                        stock_code=stock_code,
                        status=DownloadStatus.FAILED,
                        message=str(e),
                        retry_count=attempt,
                        duration_ms=duration_ms
                    )
        
        # 不应该到达这里
        return DownloadResult(
            stock_code=stock_code,
            status=DownloadStatus.FAILED,
            message="未知错误"
        )
    
    def download_ticks(
        self,
        stock_codes: Union[str, List[str]],
        start_date: str,
        end_date: str,
        progress_callback: Optional[callable] = None
    ) -> BatchDownloadResult:
        """
        批量下载Tick数据（统一方法）
        
        Args:
            stock_codes: 股票代码或代码列表，支持多种格式（600519, 600519.SH等）
            start_date: 开始日期（格式：YYYYMMDD或YYYY-MM-DD）
            end_date: 结束日期（格式：YYYYMMDD或YYYY-MM-DD）
            progress_callback: 进度回调函数，接收(current, total, stock_code, result)
            
        Returns:
            BatchDownloadResult: 批量下载结果
        """
        if not self._connected:
            logger.error("未连接到行情服务，请先调用connect()")
            return BatchDownloadResult(
                total=0,
                failed=0,
                results=[],
                message="未连接到行情服务"
            )
        
        # 标准化输入
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        # 标准化日期格式
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        # 构建时间字符串
        start_time = f"{start_date}000000"
        end_time = f"{end_date}150000"
        
        # 标准化股票代码
        normalized_codes = [self._normalize_stock_code(code) for code in stock_codes]
        
        # 初始化结果
        result = BatchDownloadResult(
            total=len(normalized_codes),
            start_time=datetime.now()
        )
        
        logger.info(f"开始下载{len(normalized_codes)}只股票的Tick数据")
        logger.info(f"日期范围: {start_date} 至 {end_date}")
        
        # 批量下载
        for i, code in enumerate(normalized_codes, 1):
            # 下载单只股票
            download_result = self._download_single_tick(code, start_time, end_time)
            result.results.append(download_result)
            
            # 更新统计
            if download_result.status == DownloadStatus.SUCCESS:
                result.success += 1
            elif download_result.status == DownloadStatus.FAILED:
                result.failed += 1
            elif download_result.status == DownloadStatus.SKIPPED:
                result.skipped += 1
            
            # 进度回调
            if progress_callback:
                try:
                    progress_callback(i, len(normalized_codes), code, download_result)
                except Exception as e:
                    logger.warning(f"进度回调出错: {e}")
            
            # 限流
            if i < len(normalized_codes):
                time.sleep(self.rate_limit_delay)
        
        result.end_time = datetime.now()
        
        # 打印统计
        duration = result.duration_seconds
        logger.info(f"下载完成: 成功{result.success}只, 失败{result.failed}只, 总耗时{duration/60:.1f}分钟")
        
        return result
    
    def check_coverage(
        self,
        stock_codes: Union[str, List[str]],
        date: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        检查数据覆盖率
        
        Args:
            stock_codes: 股票代码或代码列表
            date: 要检查的日期（格式：YYYYMMDD或YYYY-MM-DD），默认为今天
            
        Returns:
            覆盖率检查结果，格式：{
                "000001.SZ": {
                    "exists": True,
                    "tick_count": 10000,
                    "date": "20250101"
                }
            }
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        else:
            date = date.replace('-', '')
        
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        normalized_codes = [self._normalize_stock_code(code) for code in stock_codes]
        
        results = {}
        
        for code in normalized_codes:
            code_part, market = code.split('.')
            
            # 构建预期的数据路径
            # QMT数据存储格式: datadir/{market}/0/{code}/{date}.tick
            data_path = self._data_dir / 'datadir' / market / '0' / code_part / f"{date}.tick"
            
            exists = data_path.exists()
            tick_count = 0
            
            if exists:
                # 尝试读取tick数量
                try:
                    if self._connected:
                        data = self._xtdata.get_local_data(
                            field_list=['time'],
                            stock_list=[code],
                            period='tick',
                            start_time=f"{date}000000",
                            end_time=f"{date}150000"
                        )
                        if data and 'time' in data and code in data['time'].index:
                            tick_count = len(data['time'].loc[code])
                except Exception as e:
                    logger.debug(f"获取{code}的tick数量失败: {e}")
            
            results[code] = {
                'exists': exists,
                'tick_count': tick_count,
                'date': date,
                'data_path': str(data_path) if exists else None
            }
        
        return results
    
    def get_missing_stocks(
        self,
        stock_codes: Union[str, List[str]],
        date: Optional[str] = None
    ) -> List[str]:
        """
        获取缺失数据的股票列表
        
        Args:
            stock_codes: 股票代码或代码列表
            date: 要检查的日期（格式：YYYYMMDD或YYYY-MM-DD），默认为今天
            
        Returns:
            缺失数据的股票代码列表
        """
        coverage = self.check_coverage(stock_codes, date)
        return [code for code, info in coverage.items() if not info['exists']]
    
    def download_minute_data(
        self,
        stock_codes: Union[str, List[str]],
        start_date: str,
        end_date: str,
        period: str = '1m',
        progress_callback: Optional[callable] = None
    ) -> BatchDownloadResult:
        """
        批量下载分钟K线数据
        
        Args:
            stock_codes: 股票代码或代码列表
            start_date: 开始日期（格式：YYYYMMDD或YYYY-MM-DD）
            end_date: 结束日期（格式：YYYYMMDD或YYYY-MM-DD）
            period: K线周期（1m, 5m, 15m, 1h, 1d等）
            progress_callback: 进度回调函数
            
        Returns:
            BatchDownloadResult: 批量下载结果
        """
        if not self._connected:
            logger.error("未连接到行情服务，请先调用connect()")
            return BatchDownloadResult(total=0, failed=0, results=[])
        
        # 标准化输入
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        
        # 标准化日期格式
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        # 构建时间字符串
        start_time = f"{start_date}000000"
        end_time = f"{end_date}150000"
        
        # 标准化股票代码
        normalized_codes = [self._normalize_stock_code(code) for code in stock_codes]
        
        # 初始化结果
        result = BatchDownloadResult(
            total=len(normalized_codes),
            start_time=datetime.now()
        )
        
        logger.info(f"开始下载{len(normalized_codes)}只股票的{period}K线数据")
        
        # 批量下载
        for i, code in enumerate(normalized_codes, 1):
            start_ms = time.time() * 1000
            
            try:
                self._xtdata.download_history_data(
                    stock_code=code,
                    period=period,
                    start_time=start_time,
                    end_time=end_time
                )
                
                duration_ms = time.time() * 1000 - start_ms
                download_result = DownloadResult(
                    stock_code=code,
                    status=DownloadStatus.SUCCESS,
                    message=f"{period}数据下载成功",
                    duration_ms=duration_ms
                )
                result.success += 1
                
            except Exception as e:
                duration_ms = time.time() * 1000 - start_ms
                download_result = DownloadResult(
                    stock_code=code,
                    status=DownloadStatus.FAILED,
                    message=str(e),
                    duration_ms=duration_ms
                )
                result.failed += 1
            
            result.results.append(download_result)
            
            # 进度回调
            if progress_callback:
                try:
                    progress_callback(i, len(normalized_codes), code, download_result)
                except Exception as e:
                    logger.warning(f"进度回调出错: {e}")
            
            # 限流
            if i < len(normalized_codes):
                time.sleep(self.rate_limit_delay)
        
        result.end_time = datetime.now()
        
        logger.info(f"下载完成: 成功{result.success}只, 失败{result.failed}只")
        
        return result
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False


# 全局TickProvider实例（单例模式）
_tick_provider: Optional[TickProvider] = None


def get_tick_provider(config_path: Optional[str] = None) -> TickProvider:
    """
    获取全局TickProvider实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TickProvider实例
    """
    global _tick_provider
    if _tick_provider is None:
        _tick_provider = TickProvider(config_path)
    return _tick_provider


def download_ticks(
    stock_codes: Union[str, List[str]],
    start_date: str,
    end_date: str,
    config_path: Optional[str] = None
) -> BatchDownloadResult:
    """
    便捷的批量下载函数（使用全局实例）
    
    Args:
        stock_codes: 股票代码或代码列表
        start_date: 开始日期
        end_date: 结束日期
        config_path: 配置文件路径
        
    Returns:
        BatchDownloadResult: 批量下载结果
        
    使用示例：
        result = download_ticks(
            stock_codes=['000001.SZ', '600000.SH'],
            start_date='20250101',
            end_date='20250131'
        )
        print(f"成功率: {result.success_rate:.2%}")
    """
    provider = get_tick_provider(config_path)
    
    if not provider.is_connected():
        if not provider.connect():
            return BatchDownloadResult(
                total=len(stock_codes) if isinstance(stock_codes, list) else 1,
                failed=len(stock_codes) if isinstance(stock_codes, list) else 1,
                results=[],
                message="连接失败"
            )
    
    return provider.download_ticks(stock_codes, start_date, end_date)


# 兼容旧接口的别名
TickDataProvider = TickProvider


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("🧪 TickProvider 测试")
    print("=" * 80)
    
    # 使用上下文管理器
    with TickProvider() as provider:
        print(f"连接状态: {provider.is_connected()}")
        
        # 测试覆盖率检查
        test_codes = ['000001.SZ', '600000.SH']
        coverage = provider.check_coverage(test_codes, '20250101')
        print(f"\n覆盖率检查:")
        for code, info in coverage.items():
            print(f"  {code}: {'✅' if info['exists'] else '❌'}")
        
        # 测试下载（只下载1只股票测试）
        print(f"\n测试下载:")
        result = provider.download_ticks(
            stock_codes=['600519.SH'],  # 贵州茅台
            start_date='20250101',
            end_date='20250101'
        )
        print(f"成功率: {result.success_rate:.2%}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
