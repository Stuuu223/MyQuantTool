"""
下载顽主杯缺失的104只股票Tick数据
复用现有Token服务
"""

import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# ================= 配置 =================
MISSING_FILE = PROJECT_ROOT / 'config' / 'wanzhu_missing.json'

def download_missing_stocks():
    """下载缺失的顽主杯股票Tick数据"""
    from xtquant import xtdata

    # 读取缺失股票列表
    with open(MISSING_FILE, 'r', encoding='utf-8') as f:
        missing_codes = json.load(f)

    logger.info("=" * 60)
    logger.info(f"💎 下载顽主杯缺失股票Tick数据（{len(missing_codes)}只）")
    logger.info("=" * 60)

    # 连接到现有Token服务（端口58620）
    try:
        xtdata.connect(port=58620)
        logger.info("✅ 成功连接到现有Token服务（端口58620）")
    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
        logger.info("提示：请确保Token服务正在运行")
        return

    time.sleep(2)

    start_time = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d%H%M%S')

    for idx, code in enumerate(missing_codes):
        logger.info(f"   [{idx+1}/{len(missing_codes)}] 下载: {code} ...")
        try:
            xtdata.download_history_data(code, period='tick', start_time=start_time)
        except Exception as e:
            logger.warning(f"   ⚠️  {code} 下载失败: {e}")
        time.sleep(0.1)

    logger.info("✅ 顽主杯缺失股票Tick数据下载完毕！")

if __name__ == "__main__":
    try:
        download_missing_stocks()
        logger.info("🎉 任务完成！")
    except KeyboardInterrupt:
        logger.info("👋 停止运行")
    except Exception as e:
        logger.exception(f"❌ 发生错误: {e}")