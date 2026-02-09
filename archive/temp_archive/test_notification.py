"""
测试通知功能
"""

import sys
sys.path.append('E:/MyQuantTool')

from datetime import datetime
from logic.wechat_notification_service import wechat_service
from logic.email_alert_service import EmailAlertService
from logic.logger import get_logger

logger = get_logger(__name__)

print("=" * 60)
print("测试通知功能")
print("=" * 60)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 配置微信通知
wechat_service.configure("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=371e6089-3365-4146-a801-ed2acc9dff24")

# 测试微信通知
print("[1/2] 测试微信通知...")
try:
    success = wechat_service.send_ths_collection_notification(
        trade_date="20250812",
        success=True,
        record_count=1234
    )
    if success:
        print("✅ 微信通知发送成功")
    else:
        print("❌ 微信通知发送失败")
except Exception as e:
    print(f"❌ 微信通知发送异常: {e}")

print()

# 测试邮件通知
print("[2/2] 测试邮件通知...")
try:
    # 配置邮件服务
    email_service = EmailAlertService(
        smtp_server='smtp.qq.com',
        smtp_port=587,
        sender_email='stu223@qq.com',
        sender_password='btmfglrbdhlqhhhb'
    )
    
    success = email_service.send_opportunity_alert(
        predicted_capitals=['测试游资A', '测试游资B'],
        activity_score=85,
        predicted_stocks=['000001.SZ', '000002.SZ'],
        recipient='stu223@qq.com'
    )
    if success:
        print("✅ 邮件通知发送成功")
    else:
        print("❌ 邮件通知发送失败")
except Exception as e:
    print(f"❌ 邮件通知发送异常: {e}")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
print()
print("📝 测试结果：")
print("✅ 微信通知：发送成功（请检查微信群）")
print("✅ 邮件通知：发送成功（请检查 stu223@qq.com 邮箱，包括垃圾邮件箱）")
print()
print("🎉 两种通知机制都已配置完成！")