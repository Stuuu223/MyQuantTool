"""
QMT 状态自检模块

规范：
凡是用 QMT 数据做实时决策，必须显式检查：
1）行情主站是否登录成功
2）当前是否交易时间
3）行情模式是否为订阅模式（实时），不能只依赖本地文件模式

Author: MyQuantTool Team
Date: 2026-02-08
"""

from datetime import datetime, time as dt_time, timezone, timedelta
from typing import Dict, Any
import traceback

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.market_status import MarketStatusChecker
from logic.logger import get_logger

logger = get_logger(__name__)


class QMTHealthChecker:
    """QMT 状态健康检查器"""

    def __init__(self):
        """初始化检查器"""
        self.market_checker = MarketStatusChecker()
        self.last_check_result = None
        self.last_check_time = None

    def check_all(self) -> Dict[str, Any]:
        """
        执行完整的QMT状态检查

        Returns:
            {
                'status': 'HEALTHY' | 'WARNING' | 'ERROR',
                'qmt_client': {...},
                'market_status': {...},
                'trading_status': {...},
                'recommendations': [...]
            }
        """
        logger.info("=" * 80)
        logger.info("🏥 QMT 状态自检开始")
        logger.info("=" * 80)

        result = {
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'ERROR',
            'details': {},
            'recommendations': []
        }

        # 1. 检查 QMT 客户端状态
        qmt_status = self._check_qmt_client()
        result['details']['qmt_client'] = qmt_status

        if qmt_status['status'] == 'ERROR':
            result['status'] = 'ERROR'
            result['recommendations'].append('❌ QMT 客户端未启动，请先启动 QMT 终端')
            self._print_result(result)
            return result

        # 2. 检查行情主站登录状态
        server_status = self._check_server_login()
        result['details']['server_login'] = server_status

        if server_status['status'] == 'ERROR':
            result['status'] = 'ERROR'
            result['recommendations'].append('❌ 行情主站未登录，请在 QMT 终端登录行情主站')
            self._print_result(result)
            return result

        # 3. 检查当前市场状态
        market_status = self._check_market_status()
        result['details']['market_status'] = market_status

        # 4. 检查是否交易时间
        trading_status = self._check_trading_time()
        result['details']['trading_status'] = trading_status

        if trading_status['status'] == 'WARNING':
            result['status'] = 'WARNING'
            result['recommendations'].append('⚠️  当前不在交易时间，获取的是历史数据')

        # 5. 检查行情数据模式
        data_mode = self._check_data_mode()
        result['details']['data_mode'] = data_mode

        if data_mode['status'] == 'WARNING':
            result['status'] = 'WARNING'
            result['recommendations'].append('⚠️  当前使用本地文件模式，请检查实时订阅')

        # 6. 综合判断
        # 6. 综合判断（三态判定）
        errors = []
        warnings = []

        # 收集所有错误和警告
        for check_name, check_result in result['details'].items():
            if check_result.get('status') == 'ERROR':
                errors.append(f'{check_name}: {check_result.get("message", "未知错误")}')
            elif check_result.get('status') == 'WARNING':
                warnings.append(f'{check_name}: {check_result.get("message", "未知警告")}')

        # 根据 errors/warnings 确定状态
        if errors:
            result['status'] = 'ERROR'
            result['recommendations'] = [f'❌ {err}' for err in errors]
        elif warnings:
            result['status'] = 'WARNING'
            result['recommendations'] = [f'⚠️  {warn}' for warn in warnings]
        else:
            result['status'] = 'HEALTHY'
            result['recommendations'].append('✅ QMT 状态正常，可以进行实时决策')

        self._print_result(result)

        # 保存检查结果
        self.last_check_result = result
        self.last_check_time = datetime.now()

        return result

    def _check_qmt_client(self) -> Dict[str, Any]:
        """检查 QMT 客户端是否启动"""
        if not QMT_AVAILABLE:
            return {
                'status': 'ERROR',
                'message': 'xtquant 模块未安装',
                'installed': False
            }

        try:
            # 尝试获取股票列表
            stocks = xtdata.get_stock_list_in_sector('沪深A股')

            if not stocks:
                return {
                    'status': 'ERROR',
                    'message': '无法获取股票列表',
                    'installed': True,
                    'connected': False
                }

            return {
                'status': 'OK',
                'message': f'QMT 客户端已启动',
                'installed': True,
                'connected': True,
                'stock_count': len(stocks)
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'QMT 客户端连接失败: {str(e)}',
                'installed': True,
                'connected': False,
                'error': str(e)
            }

    def _check_server_login(self) -> Dict[str, Any]:
        """检查行情主站是否登录"""
        try:
            # 🔥 [P0修复] 使用多个探测标的，避免单一股票异常导致误判
            # 000001.SH 平安银行（沪市权重股）+ 600519.SH 贵州茅台（沪市龙头）
            test_codes = ['000001.SH', '600519.SH']
            tick = xtdata.get_full_tick(test_codes)

            if not tick:
                return {
                    'status': 'ERROR',
                    'message': '无法获取 Tick 数据，行情主站可能未登录',
                    'logged_in': False
                }

            # 检查至少有一个探测标的能获取到数据
            valid_tick = None
            valid_code = None
            for code in test_codes:
                if code in tick and tick[code]:
                    valid_tick = tick[code]
                    valid_code = code
                    break

            if not valid_tick:
                return {
                    'status': 'ERROR',
                    'message': f'探测标的 {test_codes} 均无数据，行情主站可能未登录',
                    'logged_in': False
                }

            # 检查数据时间戳
            timetag = valid_tick.get('timetag', '')
            stock_status = valid_tick.get('stockStatus', -1)

            return {
                'status': 'OK',
                'message': f'行情主站已连接（探测标的: {valid_code}）',
                'logged_in': True,
                'timetag': timetag,
                'stock_status': stock_status,
                'stock_status_desc': self._get_stock_status_desc(stock_status),
                'test_code': valid_code
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'行情主站检查失败: {str(e)}',
                'logged_in': False,
                'error': str(e)
            }

    def _check_market_status(self) -> Dict[str, Any]:
        """
        [Refactored] 使用本地系统时间判断市场状态，不再依赖 QMT
        """
        now = datetime.now().time()

        # 定义时间段
        is_auction = dt_time(9, 15) <= now <= dt_time(9, 25)
        is_morning = dt_time(9, 30) <= now <= dt_time(11, 30)
        is_afternoon = dt_time(13, 0) <= now <= dt_time(15, 0)

        status = "CLOSED"
        phase = "盘后"

        if is_auction:
            status = "AUCTION"
            phase = "集合竞价"
        elif is_morning:
            status = "TRADING"
            phase = "上午交易"
        elif is_afternoon:
            status = "TRADING"
            phase = "下午交易"
        elif dt_time(9, 25) <= now < dt_time(9, 30):
            phase = "竞价撮合"
        elif dt_time(11, 30) <= now < dt_time(13, 0):
            phase = "午间休市"

        return {
            'status': 'OK',
            'market_status': status,
            'market_phase': phase,
            'local_time': now.strftime("%H:%M:%S"),
            'is_trading_time': is_auction or is_morning or is_afternoon,
            'message': f'当前阶段: {phase}'
        }

    def _check_trading_time(self) -> Dict[str, Any]:
        """
        [Refactored] 使用本地系统时间检查是否交易时间
        """
        now = datetime.now().time()

        # 判断当前时间段
        is_auction = dt_time(9, 15) <= now <= dt_time(9, 25)
        is_morning = dt_time(9, 30) <= now <= dt_time(11, 30)
        is_afternoon = dt_time(13, 0) <= now <= dt_time(15, 0)

        is_trading_time = is_auction or is_morning or is_afternoon

        if is_trading_time:
            phase = "集合竞价" if is_auction else ("上午交易" if is_morning else "下午交易")
            return {
                'status': 'OK',
                'is_trading_time': True,
                'phase': phase,
                'message': f'当前在交易时间 ({phase})'
            }
        else:
            if now < dt_time(9, 15):
                phase = '盘前'
            elif dt_time(9, 25) <= now < dt_time(9, 30):
                phase = '竞价撮合'
            elif dt_time(11, 30) <= now < dt_time(13, 0):
                phase = '午间休市'
            else:
                phase = '盘后'

            return {
                'status': 'WARNING',
                'is_trading_time': False,
                'phase': phase,
                'message': f'当前不在交易时间 ({phase})'
            }

    def _check_data_mode(self) -> Dict[str, Any]:
        """检查行情数据模式"""
        try:
            # 🔥 [修复] 与 server_login 保持一致，使用多标的探测
            # 平安银行 + 贵州茅台 + 平安银行（深市），覆盖沪深两市
            test_codes = ['000001.SH', '600519.SH', '000001.SZ']
            tick = xtdata.get_full_tick(test_codes)

            # 检查至少有一个探测标的能获取到数据
            valid_tick = None
            valid_code = None
            for code in test_codes:
                if code in tick and tick[code]:
                    valid_tick = tick[code]
                    valid_code = code
                    break

            if not valid_tick:
                return {
                    'status': 'WARNING',
                    'message': f'所有探测标的 {test_codes} 均无数据',
                    'data_mode': 'UNKNOWN'
                }

            # 检查数据时间
            timetag = valid_tick.get('timetag', '')
            # 🔥 [修复] 使用北京时间（UTC+8）与 tick 时间戳比较，避免时区误判
            beijing_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(beijing_tz)

            # 如果时间戳超过1小时，可能是本地文件模式
            if timetag:
                try:
                    # tick 时间戳是无时区信息，但 QMT 返回的是北京时间
                    tick_time = datetime.strptime(timetag, '%Y%m%d %H:%M:%S')
                    # 为 tick_time 添加北京时间时区，使其与 current_time 具有时区信息
                    tick_time = tick_time.replace(tzinfo=beijing_tz)

                    time_diff = (current_time - tick_time).total_seconds()

                    if time_diff > 3600:  # 超过1小时
                        return {
                            'status': 'WARNING',
                            "message": f"数据时间滞后 {time_diff/60:.0f} 分钟，可能是本地文件模式（探测标的: {valid_code}）",
                            'data_mode': 'LOCAL_FILE',
                            'time_diff_seconds': time_diff,
                            'test_code': valid_code
                        }
                    else:
                        return {
                            'status': 'OK',
                            'message': f'数据实时更新（探测标的: {valid_code}）',
                            'data_mode': 'REALTIME_SUBSCRIPTION',
                            'time_diff_seconds': time_diff,
                            'test_code': valid_code
                        }
                except Exception as e:
                    logger.debug(f"时间戳解析失败: {e}")

            return {
                'status': 'WARNING',
                'message': f'无法判断数据模式（探测标的: {valid_code}）',
                'data_mode': 'UNKNOWN',
                'test_code': valid_code
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'数据模式检查失败: {str(e)}',
                'error': str(e)
            }

    def _get_stock_status_desc(self, status: int) -> str:
        """获取股票状态描述"""
        status_map = {
            0: '停牌',
            1: '交易中',
            2: '临时停牌',
            3: '退市',
            4: '未上市',
            5: '收盘'
        }
        return status_map.get(status, f'未知状态({status})')

    def _print_result(self, result: Dict[str, Any]):
        """打印检查结果"""
        logger.info("")
        logger.info("📊 QMT 状态检查结果")
        logger.info("=" * 80)

        # 打印状态
        status = result['status']
        status_emoji = {
            'HEALTHY': '✅',
            'WARNING': '⚠️ ',
            'ERROR': '❌'
        }.get(status, '❓')

        logger.info(f"整体状态: {status_emoji} {status}")
        logger.info(f"检查时间: {result['check_time']}")
        logger.info("")

        # 打印各项检查
        details = result['details']

        # QMT 客户端
        qmt = details.get('qmt_client', {})
        logger.info(f"QMT 客户端: {'✅ 已启动' if qmt.get('status') == 'OK' else '❌ 未启动'}")
        if qmt.get('status') == 'OK':
            logger.info(f"  - 股票数量: {qmt.get('stock_count', 0)} 只")
        logger.info(f"  - 消息: {qmt.get('message', 'N/A')}")

        # 行情主站
        server = details.get('server_login', {})
        logger.info(f"行情主站: {'✅ 已登录' if server.get('logged_in') else '❌ 未登录'}")
        if server.get('logged_in'):
            logger.info(f"  - 时间戳: {server.get('timetag', 'N/A')}")
            logger.info(f"  - 股票状态: {server.get('stock_status_desc', 'N/A')}")
        logger.info(f"  - 消息: {server.get('message', 'N/A')}")

        # 市场状态
        market = details.get('market_status', {})
        is_trading_time = market.get('is_trading_time', False)
        market_phase = market.get('market_phase', '未知')
        logger.info(f"市场状态: {'✅ 交易时间' if is_trading_time else '⚠️  非交易时间'} ({market_phase})")

        # 交易时间
        trading = details.get('trading_status', {})
        if trading.get('is_trading_time'):
            logger.info(f"交易时间: ✅ 当前在交易时间")
        else:
            logger.info(f"交易时间: ⚠️  当前不在交易时间 ({trading.get('phase', 'N/A')})")

        # 数据模式
        mode = details.get('data_mode', {})
        data_mode = mode.get('data_mode', 'UNKNOWN')
        if data_mode == 'REALTIME_SUBSCRIPTION':
            logger.info(f"数据模式: ✅ 实时订阅模式")
        elif data_mode == 'LOCAL_FILE':
            logger.info(f"数据模式: ⚠️  本地文件模式 (滞后 {mode.get('time_diff_seconds', 0)/60:.0f} 分钟)")
        else:
            logger.info(f"数据模式: ⚠️  {mode.get('message', 'N/A')}")

        # 打印建议
        logger.info("")
        logger.info("💡 建议:")
        for rec in result['recommendations']:
            logger.info(f"  {rec}")

        logger.info("=" * 80)
        logger.info("")


# 全局实例
_qmt_health_checker = QMTHealthChecker()


def check_qmt_health() -> Dict[str, Any]:
    """
    检查 QMT 状态（便捷函数）

    Returns:
        检查结果字典
    """
    return _qmt_health_checker.check_all()


def require_realtime_mode():
    """
    强制要求实时模式

    如果不满足实时模式要求，抛出异常

    Raises:
        RuntimeError: 如果 QMT 状态不满足实时决策要求
    """
    result = check_qmt_health()

    if result['status'] == 'ERROR':
        raise RuntimeError(
            f"QMT 状态错误，无法进行实时决策: {result['recommendations']}"
        )

    trading = result['details'].get('trading_status', {})
    if not trading.get('is_trading_time', False):
        raise RuntimeError(
            f"当前不在交易时间 ({trading.get('phase', 'N/A')})，无法进行实时决策"
        )

    mode = result['details'].get('data_mode', {})
    data_mode = mode.get('data_mode', 'UNKNOWN')
    if data_mode != 'REALTIME_SUBSCRIPTION':
        raise RuntimeError(
            f"数据模式不是实时订阅 ({data_mode})，无法进行实时决策"
        )


if __name__ == "__main__":
    # 测试
    print("QMT 状态自检")
    print("=" * 80)

    result = check_qmt_health()

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)