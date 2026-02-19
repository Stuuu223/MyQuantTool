#!/usr/bin/env python3
"""
顽主杯Top 150股票Tick数据下载
下载2025-11-21至2026-02-13的Tick数据

使用xtdatacenter本地服务+Token方式

环境要求:
1. 需要安装xtquant模块 (通常在venv_qmt虚拟环境中)
2. 需要有效的QMT VIP Token
3. QMT终端需要启动（或使用独立数据服务）

运行方式:
    python scripts/download_wanzhu_top150_tick.py
"""
import sys
import csv
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 检查是否在QMT虚拟环境中
IN_VENV_QMT = os.path.exists(PROJECT_ROOT / 'venv_qmt')

try:
    from xtquant import xtdatacenter as xtdc
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    print("⚠️  警告: xtquant模块未安装")
    print("💡 请确保:")
    print("   1. 安装了QMT客户端")
    print("   2. 激活QMT虚拟环境: venv_qmt\\Scripts\\activate")
    print("   3. 安装了xtquant: pip install xtquant")
    print()

from logic.utils.logger import get_logger

logger = get_logger(__name__)

# VIP Token
VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"


def start_token_service():
    """启动 xtdatacenter 行情服务 (Token 模式)"""
    if not QMT_AVAILABLE:
        raise RuntimeError("xtquant模块不可用，无法启动Token服务")

    # 1. 设置数据目录
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    logger.info(f"📂 数据目录: {data_dir}")
    print(f"📂 数据目录: {data_dir}")

    # 2. 设置Token
    xtdc.set_token(VIP_TOKEN)
    logger.info(f"🔑 Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")
    print(f"🔑 Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")

    # 3. 初始化并监听端口（使用动态端口避免冲突）
    xtdc.init()
    listen_port = xtdc.listen(port=(58800, 58850))
    logger.info(f"🚀 行情服务已启动，监听端口: {listen_port}")
    print(f"🚀 行情服务已启动，监听端口: {listen_port}")

    return listen_port


def determine_market(code_str: str) -> str:
    """根据股票代码判断市场"""
    code_str = str(code_str).strip()

    # 科创板（8开头，6位，例如688110）
    if code_str.startswith('688'):
        return 'SH'

    # 主板（6开头，6位，例如600000）
    if code_str.startswith('6'):
        return 'SH'

    # 创业板（3开头，6位，例如300058）
    if code_str.startswith('3'):
        return 'SZ'

    # 深圳主板（0开头，6位，例如000001）
    if code_str.startswith('0'):
        return 'SZ'

    # 北交所（8开头，但688开头已排除，例如830799）
    if code_str.startswith('8'):
        return 'BJ'

    # 默认规则：根据代码长度判断
    if len(code_str) == 6:
        if code_str[0] in ['6', '9']:
            return 'SH'
        else:
            return 'SZ'

    # 其他情况，根据第一位判断
    if code_str[0] in ['6', '9']:
        return 'SH'
    else:
        return 'SZ'


def pad_stock_code(code: str) -> str:
    """补全股票代码到6位"""
    code_str = str(code).strip()
    return code_str.zfill(6)


def load_stock_list(csv_path: Path) -> list:
    """从CSV文件加载股票列表"""
    stocks = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = pad_stock_code(row['code'])
            name = row['name']
            market = determine_market(code)
            stocks.append({
                'code': code,
                'name': name,
                'market': market
            })
    return stocks


def download_tick_with_retry(xtdata, qmt_code: str, start_date: str, end_date: str, max_retries: int = 3) -> bool:
    """带重试机制的tick下载
    
    Args:
        xtdata: xtdata模块
        qmt_code: QMT格式的股票代码(如000001.SZ)
        start_date: 开始日期(YYYYMMDD格式)
        end_date: 结束日期(YYYYMMDD格式)
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            # 下载Tick数据 - 使用完整的日期范围
            start_time = f'{start_date}000000'
            end_time = f'{end_date}150000'  # 收盘时间
            
            xtdata.download_history_data(
                stock_code=qmt_code,
                period='tick',
                start_time=start_time,
                end_time=end_time
            )
            return True
        except Exception as e:
            logger.warning(f"下载失败 (尝试 {attempt + 1}/{max_retries}): {qmt_code} - {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                logger.error(f"下载彻底失败: {qmt_code}")
                return False


def download_tick_batch(stocks: list, start_date: str, end_date: str):
    """批量下载Tick数据"""
    if not QMT_AVAILABLE:
        print("\n" + "=" * 80)
        print("❌ 错误: QMT不可用")
        print("=" * 80)
        print("\n无法启动下载任务，原因:")
        print("1. xtquant模块未安装")
        print("2. 请按以下步骤操作:")
        print("   - 激活QMT虚拟环境: venv_qmt\\Scripts\\activate")
        print("   - 或安装xtquant: pip install xtquant")
        print("\n" + "=" * 80)
        return

    print(f"=" * 80)
    print(f"📥 下载顽主杯Top 150股票Tick数据")
    print(f"=" * 80)
    print(f"\n股票数: {len(stocks)}")
    print(f"日期范围: {start_date} 至 {end_date}")

    logger.info(f"开始下载Top 150股票Tick数据，共{len(stocks)}只")

    # 1. 启动Token服务
    print(f"\n🌐 启动Token服务...")
    try:
        listen_port = start_token_service()
    except Exception as e:
        logger.error(f"启动Token服务失败: {e}")
        print(f"❌ 启动Token服务失败: {e}")
        print("\n可能的原因:")
        print("1. VIP Token已过期")
        print("2. 网络连接问题")
        print("3. QMT服务未启动")
        return

    # 2. 连接到行情服务
    _, port = listen_port
    xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)

    # 等待连接成功
    print(f"\n⏳ 连接行情服务...")
    for i in range(10):
        try:
            if xtdata.get_market_data(['close'], ['600519.SH'], count=1):
                print("✅ 成功连接到行情服务！")
                logger.info("成功连接到行情服务")
                break
        except Exception as e:
            pass
        time.sleep(1)
        print(f"  等待中... {i+1}/10")
    else:
        print("❌ 连接失败")
        logger.error("连接行情服务失败")
        return

    # 3. 转换日期格式
    start = start_date.replace('-', '')
    end = end_date.replace('-', '')
    start_time = f'{start}000000'
    end_time_fmt = f'{end}150000'

    # 4. 下载每只股票的数据
    print(f"\n{'=' * 80}")
    print(f"🚀 开始下载Tick数据...")
    print(f"{'=' * 80}\n")

    success_count = 0
    fail_count = 0
    fail_stocks = []

    start_time_total = time.time()

    for i, stock in enumerate(stocks, 1):
        qmt_code = f"{stock['code']}.{stock['market']}"

        # 计算进度
        progress = i / len(stocks) * 100
        elapsed = time.time() - start_time_total
        remaining = elapsed / i * (len(stocks) - i) if i > 0 else 0

        print(f"\r[{i}/{len(stocks)}] {progress:.1f}% | {stock['name']} ({qmt_code}) | "
              f"✅{success_count} ❌{fail_count} | ETA: {remaining/60:.1f}min", end='', flush=True)

        # 尝试下载
        if download_tick_with_retry(xtdata, qmt_code, start, end_date.replace('-', ''), max_retries=3):
            success_count += 1
            logger.info(f"[{i}/{len(stocks)}] 下载成功: {stock['name']} ({qmt_code})")
        else:
            fail_count += 1
            fail_stocks.append(stock)
            logger.error(f"[{i}/{len(stocks)}] 下载失败: {stock['name']} ({qmt_code})")

        # 避免请求过快
        time.sleep(0.3)

    print(f"\n\n{'=' * 80}")
    print(f"📊 下载完成统计")
    print(f"{'=' * 80}")
    print(f"总股票数: {len(stocks)}")
    print(f"成功: {success_count} 只 ({success_count/len(stocks)*100:.1f}%)")
    print(f"失败: {fail_count} 只 ({fail_count/len(stocks)*100:.1f}%)")
    print(f"总耗时: {(time.time() - start_time_total)/60:.1f} 分钟")

    if fail_stocks:
        print(f"\n❌ 失败股票列表:")
        for stock in fail_stocks:
            qmt_code = f"{stock['code']}.{stock['market']}"
            print(f"  - {stock['name']} ({qmt_code})")

        # 保存失败列表
        fail_list_path = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'
        with open(fail_list_path, 'w', encoding='utf-8') as f:
            for stock in fail_stocks:
                qmt_code = f"{stock['code']}.{stock['market']}"
                f.write(f"{stock['name']},{qmt_code}\n")
        print(f"\n📝 失败列表已保存: {fail_list_path}")

    logger.info(f"下载完成: 成功{success_count}只, 失败{fail_count}只")
    print(f"\n{'=' * 80}")
    print(f"🎉 任务完成！数据已保存到本地。")
    print(f"{'=' * 80}")


def main():
    """主函数"""
    # 设置日志
    log_file = PROJECT_ROOT / 'logs' / 'tick_download_150.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"📝 日志文件: {log_file}\n")

    # 读取股票列表
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'

    if not csv_path.exists():
        print(f"❌ 股票列表不存在: {csv_path}")
        logger.error(f"股票列表不存在: {csv_path}")
        return

    stocks = load_stock_list(csv_path)

    print(f"\n✅ 成功加载 {len(stocks)} 只股票")
    print(f"上海市场: {sum(1 for s in stocks if s['market'] == 'SH')} 只")
    print(f"深圳市场: {sum(1 for s in stocks if s['market'] == 'SZ')} 只")
    print(f"北京市场: {sum(1 for s in stocks if s['market'] == 'BJ')} 只")

    # 检查QMT可用性
    if not QMT_AVAILABLE:
        print("\n" + "=" * 80)
        print("⚠️  环境检查警告")
        print("=" * 80)
        print("\n当前环境未安装xtquant模块，无法使用QMT下载Tick数据")
        print("\n请选择以下方案之一:")
        print("\n方案1: 使用QMT虚拟环境（推荐）")
        print("  venv_qmt\\Scripts\\activate")
        print("  python scripts/download_wanzhu_top150_tick.py")
        print("\n方案2: 使用AkShare下载K线数据（替代方案）")
        print("  python scripts/download_wanzhu_top150_kline.py")
        print("\n" + "=" * 80)
        return

    # 开始下载 - 日期范围: 2025-11-15 至 2026-02-13
    download_tick_batch(
        stocks,
        start_date='2025-11-15',
        end_date='2026-02-13'
    )


if __name__ == '__main__':
    main()
