"""
下载顽主杯前120只热门股票的Tick数据
"""

import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# ================= 配置 =================
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'
WANZHU_120_FILE = PROJECT_ROOT / 'config' / 'wanzhu_top_120.json'

def start_token_service():
    """启动 xtdatacenter 行情服务 (Token 模式)"""
    try:
        from xtquant import xtdatacenter as xtdc
    except ImportError:
        logger.error("❌ 无法导入 xtquant，请检查环境")
        return None

    data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
    data_dir.mkdir(parents=True, exist_ok=True)
    xtdc.set_data_home_dir(str(data_dir))
    xtdc.set_token(VIP_TOKEN)
    xtdc.init()
    listen_port = xtdc.listen(port=(58620, 58630))
    logger.info(f"🚀 行情服务已启动，监听端口: {listen_port}")
    return listen_port

def download_wanzhu_120(listen_port):
    """下载顽主杯前120只股票Tick数据"""
    from xtquant import xtdata

    # 连接
    xtdata.connect(port=listen_port)
    time.sleep(2)

    # 读取顽主杯股票数据
    with open(WANZHU_120_FILE, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    logger.info("=" * 60)
    logger.info(f"💎 下载顽主杯热门股票Tick数据（{len(stocks)}只）")
    logger.info("=" * 60)

    start_time = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d%H%M%S')

    for idx, stock in enumerate(stocks):
        code = stock['code']
        name = stock['name']

        logger.info(f"   [{idx+1}/{len(stocks)}] 下载: {code} {name} ...")
        xtdata.download_history_data(code, period='tick', start_time=start_time)
        time.sleep(0.1)

    logger.success("✅ 顽主杯热门股票Tick数据下载完毕！")

if __name__ == "__main__":
    try:
        port = start_token_service()
        if port:
            download_wanzhu_120(port)
            logger.info("🎉 任务完成！按 Ctrl+C 退出...")
            while True: time.sleep(10)
    except KeyboardInterrupt:
        logger.info("👋 停止运行")
    except Exception as e:
        logger.exception(f"❌ 发生错误: {e}")