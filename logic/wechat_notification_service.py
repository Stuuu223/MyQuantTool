"""
微信通知服务（企业微信机器人）
支持企业微信机器人的 Webhook 通知
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class WeChatMessage:
    """微信消息数据类"""
    msg_type: str  # 'text', 'markdown', 'image', 'news'
    content: str
    mentioned_list: Optional[List[str]] = None  # @的用户列表
    mentioned_mobile_list: Optional[List[str]] = None  # @的手机号列表


class WeChatNotificationService:
    """微信通知服务（企业微信机器人）"""
    
    def __init__(self, webhook_url: str = None):
        """
        初始化微信通知服务
        
        Args:
            webhook_url: 企业微信机器人的 Webhook URL
        """
        self.webhook_url = webhook_url
        self.enabled = webhook_url is not None and webhook_url != ""
        self.sent_messages = []  # 已发送消息日志
        
        if not self.enabled:
            logger.warning("微信通知未配置,功能禁用")
        else:
            logger.info("微信通知服务已启用")
    
    def send_text_message(
        self,
        content: str,
        mentioned_list: Optional[List[str]] = None,
        mentioned_mobile_list: Optional[List[str]] = None
    ) -> bool:
        """
        发送文本消息
        
        Args:
            content: 文本内容
            mentioned_list: @的用户列表
            mentioned_mobile_list: @的手机号列表
        
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("微信通知未配置,无法发送")
            return False
        
        data = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or [],
                "mentioned_mobile_list": mentioned_mobile_list or []
            }
        }
        
        return self._send_message(data, "text")
    
    def send_markdown_message(
        self,
        content: str
    ) -> bool:
        """
        发送 Markdown 消息
        
        Args:
            content: Markdown 内容
        
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("微信通知未配置,无法发送")
            return False
        
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        return self._send_message(data, "markdown")
    
    def send_ths_collection_notification(
        self,
        trade_date: str,
        success: bool,
        record_count: int = 0,
        error_msg: str = None
    ) -> bool:
        """
        发送 THS 数据收集通知
        
        Args:
            trade_date: 交易日期
            success: 是否成功
            record_count: 记录数量
            error_msg: 错误信息
        
        Returns:
            bool: 是否发送成功
        """
        if success:
            content = f"""## ✅ THS 资金流向数据收集成功

> **交易日期**: {trade_date}
> **记录数量**: {record_count}
> **收集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

数据已保存至 `data/tushare_ths_moneyflow/` 目录
"""
        else:
            content = f"""## ❌ THS 资金流向数据收集失败

> **交易日期**: {trade_date}
> **错误信息**: {error_msg}
> **收集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

将在明天重试
"""
        
        return self.send_markdown_message(content)
    
    def send_snapshot_rebuild_notification(
        self,
        trade_date: str,
        stock_count: int,
        success: bool,
        error_msg: str = None
    ) -> bool:
        """
        发送历史快照重建通知
        
        Args:
            trade_date: 交易日期
            stock_count: 股票数量
            success: 是否成功
            error_msg: 错误信息
        
        Returns:
            bool: 是否发送成功
        """
        if success:
            content = f"""## 🔄 历史快照重建成功

> **交易日期**: {trade_date}
> **股票数量**: {stock_count}
> **重建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

快照文件: `data/scan_results/full_market_snapshot_{trade_date}_rebuild.json`
"""
        else:
            content = f"""## ❌ 历史快照重建失败

> **交易日期**: {trade_date}
> **错误信息**: {error_msg}
> **重建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请检查日志获取详细信息
"""
        
        return self.send_markdown_message(content)
    
    def _send_message(self, data: Dict, msg_type: str) -> bool:
        """
        发送消息的内部方法
        
        Args:
            data: 消息数据
            msg_type: 消息类型
        
        Returns:
            bool: 是否发送成功
        """
        try:
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 检查响应
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"✅ 微信消息发送成功: {msg_type}")
                
                # 记录已发送
                self.sent_messages.append({
                    'type': msg_type,
                    'timestamp': datetime.now(),
                    'content': data
                })
                
                return True
            else:
                logger.error(f"❌ 微信消息发送失败: {result.get('errmsg')}")
                return False
        
        except requests.RequestException as e:
            logger.error(f"❌ 微信消息发送失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ 微信消息发送失败: {str(e)}")
            return False
    
    def configure(self, webhook_url: str):
        """
        配置微信通知服务
        
        Args:
            webhook_url: 企业微信机器人的 Webhook URL
        """
        self.webhook_url = webhook_url
        self.enabled = webhook_url is not None and webhook_url != ""
        logger.info(f"微信通知服务已配置: {'启用' if self.enabled else '禁用'}")


# 创建全局实例
wechat_service = WeChatNotificationService()


def configure_wechat(webhook_url: str):
    """
    配置微信通知服务（便捷函数）
    
    Args:
        webhook_url: 企业微信机器人的 Webhook URL
    """
    wechat_service.configure(webhook_url)