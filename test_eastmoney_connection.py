"""测试东方财富API连接"""
import requests
from logic.logger import get_logger

logger = get_logger(__name__)

def test_eastmoney_api():
    """测试东方财富API连接"""
    urls = [
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://hq.sinajs.cn/list=sh600519"
    ]

    for url in urls:
        try:
            logger.info(f"测试连接: {url}")
            response = requests.get(url, timeout=10)
            logger.info(f"✅ 连接成功: {url}, 状态码: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error(f"❌ 连接超时: {url}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ 连接错误: {url}, 错误: {e}")
        except Exception as e:
            logger.error(f"❌ 未知错误: {url}, 错误: {e}")

if __name__ == "__main__":
    test_eastmoney_api()