"""
API 请求速率限制器
防止频繁请求导致被封IP
"""
import time
from datetime import datetime, timedelta
from threading import Lock
from collections import deque
import json
import os


class RateLimiter:
    """
    API 请求速率限制器

    功能：
    - 限制每分钟请求数
    - 限制每小时请求数
    - 自动请求间隔
    - 请求队列管理
    - 请求历史记录
    """

    def __init__(
        self,
        max_requests_per_minute=20,  # 每分钟最多20次请求
        max_requests_per_hour=200,   # 每小时最多200次请求
        min_request_interval=3,       # 最小请求间隔3秒
        enable_logging=True
    ):
        self.max_rpm = max_requests_per_minute
        self.max_rph = max_requests_per_hour
        self.min_interval = min_request_interval
        self.enable_logging = enable_logging

        self.request_history = deque()
        self.last_request_time = None
        self.lock = Lock()

        # 加载历史记录
        self.history_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'rate_limiter_history.json')
        self._load_history()

    def _load_history(self):
        """加载请求历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 只加载最近1小时的历史
                    now = datetime.now()
                    one_hour_ago = now - timedelta(hours=1)
                    valid_history = [
                        (datetime.fromisoformat(ts), url)
                        for ts, url in data
                        if datetime.fromisoformat(ts) > one_hour_ago
                    ]
                    self.request_history = deque(valid_history)
        except Exception as e:
            if self.enable_logging:
                print(f"⚠️ [RateLimiter] 加载历史记录失败: {e}")

    def _save_history(self):
        """保存请求历史"""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                # 只保存最近100条记录
                data = list(self.request_history)[-100:]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if self.enable_logging:
                print(f"⚠️ [RateLimiter] 保存历史记录失败: {e}")

    def _clean_old_history(self):
        """清理过期的历史记录"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        while self.request_history and self.request_history[0][0] < one_hour_ago:
            self.request_history.popleft()

    def can_request(self, url=None):
        """
        检查是否可以发起请求

        Args:
            url: 请求的URL（用于记录）

        Returns:
            tuple: (bool, str) - (是否可以请求, 原因)
        """
        with self.lock:
            self._clean_old_history()

            now = datetime.now()

            # 检查请求间隔
            if self.last_request_time:
                elapsed = (now - self.last_request_time).total_seconds()
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    return False, f"请求间隔过短，需等待 {wait_time:.1f} 秒"

            # 检查每分钟限制
            one_minute_ago = now - timedelta(minutes=1)
            recent_minute = sum(1 for ts, _ in self.request_history if ts > one_minute_ago)
            if recent_minute >= self.max_rpm:
                return False, f"达到每分钟限制 ({self.max_rpm}次/分钟)"

            # 检查每小时限制
            recent_hour = len(self.request_history)
            if recent_hour >= self.max_rph:
                return False, f"达到每小时限制 ({self.max_rph}次/小时)"

            return True, "可以请求"

    def record_request(self, url=None):
        """
        记录一次请求

        Args:
            url: 请求的URL
        """
        with self.lock:
            now = datetime.now()
            self.request_history.append((now, url or 'unknown'))
            self.last_request_time = now

            # 定期保存历史
            if len(self.request_history) % 10 == 0:
                self._save_history()

    def wait_if_needed(self, url=None):
        """
        如果需要，等待到可以请求

        Args:
            url: 请求的URL
        """
        while True:
            can_request, reason = self.can_request(url)
            if can_request:
                break

            if self.enable_logging:
                print(f"⏳ [RateLimiter] {reason}")

            # 等待后重试
            time.sleep(1)

    def get_stats(self):
        """
        获取统计信息

        Returns:
            dict: 统计信息
        """
        with self.lock:
            self._clean_old_history()

            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            one_hour_ago = now - timedelta(hours=1)

            recent_minute = sum(1 for ts, _ in self.request_history if ts > one_minute_ago)
            recent_hour = len(self.request_history)

            return {
                'recent_minute': recent_minute,
                'recent_hour': recent_hour,
                'max_per_minute': self.max_rpm,
                'max_per_hour': self.max_rph,
                'remaining_minute': self.max_rpm - recent_minute,
                'remaining_hour': self.max_rph - recent_hour,
                'last_request': self.last_request_time.isoformat() if self.last_request_time else None
            }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print(f"\n{'='*60}")
        print(f"📊 RateLimiter 统计信息")
        print(f"{'='*60}")
        print(f"  最近1分钟: {stats['recent_minute']}/{stats['max_per_minute']} 次")
        print(f"  最近1小时: {stats['recent_hour']}/{stats['max_per_hour']} 次")
        print(f"  剩余配额: {stats['remaining_minute']} (分钟) | {stats['remaining_hour']} (小时)")
        if stats['last_request']:
            print(f"  最后请求: {stats['last_request']}")
        print(f"{'='*60}\n")


# 全局限流器实例
_global_limiter = None
_limiter_lock = Lock()


def get_rate_limiter():
    """
    获取全局限流器实例（单例模式）

    Returns:
        RateLimiter: 全局限流器实例
    """
    global _global_limiter

    with _limiter_lock:
        if _global_limiter is None:
            _global_limiter = RateLimiter(
                max_requests_per_minute=20,
                max_requests_per_hour=200,
                min_request_interval=3,
                enable_logging=True
            )

        return _global_limiter


def safe_request(request_func, *args, **kwargs):
    """
    安全的请求包装器

    Args:
        request_func: 请求函数
        *args, **kwargs: 传递给请求函数的参数

    Returns:
        请求函数的返回值
    """
    limiter = get_rate_limiter()

    # 等待直到可以请求
    limiter.wait_if_needed()

    # 记录请求
    limiter.record_request()

    try:
        return request_func(*args, **kwargs)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        raise


if __name__ == "__main__":
    # 测试
    limiter = RateLimiter(max_requests_per_minute=5, min_request_interval=2)

    print("测试速率限制器...\n")

    # 模拟10次请求
    for i in range(10):
        can_request, reason = limiter.can_request()
        print(f"[{i+1}] {reason}")

        if can_request:
            limiter.record_request()
            print(f"  ✅ 请求已记录")
        else:
            print(f"  ⏳ 等待中...")
            time.sleep(1)

        time.sleep(1)

    # 打印统计信息
    limiter.print_stats()