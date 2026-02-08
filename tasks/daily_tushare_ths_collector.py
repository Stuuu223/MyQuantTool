"""
Daily Tushare THS Moneyflow Collector
Run once per day after market close to collect THS moneyflow data
"""

import sys
sys.path.append('E:/MyQuantTool')

import tushare as ts
from datetime import datetime, timedelta
import pandas as pd
import json
import os

from logic.email_alert_service import EmailAlertService
from logic.wechat_notification_service import wechat_service
from logic.logger import get_logger

logger = get_logger(__name__)

# Tushare token
TOKEN = "1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b"

# 配置微信通知
wechat_service.configure("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=371e6089-3365-4146-a801-ed2acc9dff24")

# Configuration
OUTPUT_DIR = "E:/MyQuantTool/data/tushare_ths_moneyflow"
EMAIL_RECIPIENT = "stu223@qq.com"  # 用户提供的邮箱

# Initialize email service（QQ邮箱）
email_service = EmailAlertService(
    smtp_server='smtp.qq.com',  # QQ邮箱 SMTP
    smtp_port=587,
    sender_email='stu223@qq.com',
    sender_password='btmfglrbdhlqhhhb'  # QQ邮箱授权码
)


def ensure_output_dir():
    """Ensure output directory exists"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")


def get_latest_trade_date():
    """Get latest trade date"""
    # Get today's date
    today = datetime.now()
    
    # If it's weekend, go back to Friday
    if today.weekday() >= 5:  # Saturday (5) or Sunday (6)
        days_to_subtract = today.weekday() - 4  # Go back to Friday
        today = today - timedelta(days=days_to_subtract)
    
    # If it's after 15:00, use today's date; otherwise use yesterday
    if today.hour >= 15:
        trade_date = today
    else:
        trade_date = today - timedelta(days=1)
    
    return trade_date.strftime('%Y%m%d')


def collect_ths_moneyflow(trade_date):
    """
    Collect THS moneyflow data for a specific date
    
    Args:
        trade_date: Trade date (YYYYMMDD format)
    
    Returns:
        DataFrame with THS moneyflow data, or None if failed
    """
    ts.set_token(TOKEN)
    pro = ts.pro_api()
    
    try:
        logger.info(f"Collecting THS moneyflow data for {trade_date}...")
        
        # Get THS moneyflow data for all stocks
        df = pro.moneyflow_ths(
            trade_date=trade_date
        )
        
        if df is not None and len(df) > 0:
            logger.info(f"✅ Successfully collected {len(df)} records for {trade_date}")
            return df
        else:
            logger.warning(f"⚠️ No data returned for {trade_date}")
            return None
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to collect THS moneyflow for {trade_date}: {e}")
        
        # Check if it's a rate limit error
        if "每分钟" in error_msg or "每小时" in error_msg or "分钟" in error_msg or "小时" in error_msg:
            logger.warning("⚠️ Rate limited. Will try again tomorrow.")
        
        return None


def save_to_json(df, trade_date):
    """
    Save DataFrame to JSON file
    
    Args:
        df: DataFrame to save
        trade_date: Trade date (YYYYMMDD format)
    
    Returns:
        Path to saved file, or None if failed
    """
    try:
        # Create filename
        filename = f"ths_moneyflow_{trade_date}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Convert DataFrame to dict and save
        data = {
            'trade_date': trade_date,
            'collect_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'record_count': len(df),
            'data': df.to_dict('records')
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Saved data to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Failed to save data: {e}")
        return None


def send_notification(trade_date, success, record_count=0, error_msg=None):
    """
    Send notification (email + WeChat)
    
    Args:
        trade_date: Trade date
        success: Whether collection was successful
        record_count: Number of records collected
        error_msg: Error message if failed
    """
    # Send email notification
    if email_service.enabled:
        if success:
            subject = f"✅ THS Moneyflow Collection Success: {trade_date}"
            body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #f0fdf4; border-left: 4px solid #32b898; padding: 15px;">
        <h2 style="color: #32b898; margin: 0;">THS Moneyflow Collection Success</h2>
        <p><strong>Trade Date:</strong> {trade_date}</p>
        <p><strong>Records Collected:</strong> {record_count}</p>
        <p><strong>Collection Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="color: #999; font-size: 12px;">Data saved to: {OUTPUT_DIR}</p>
    </div>
</body>
</html>
            """
        else:
            subject = f"❌ THS Moneyflow Collection Failed: {trade_date}"
            body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #fff5f5; border-left: 4px solid #ff5459; padding: 15px;">
        <h2 style="color: #ff5459; margin: 0;">THS Moneyflow Collection Failed</h2>
        <p><strong>Trade Date:</strong> {trade_date}</p>
        <p><strong>Error:</strong> {error_msg}</p>
        <p><strong>Collection Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="color: #999; font-size: 12px;">Will try again tomorrow.</p>
    </div>
</body>
</html>
            """
        
        # Send email
        try:
            email_service._send_email(
                recipient=EMAIL_RECIPIENT,
                subject=subject,
                body=body,
                alert_type='ths_collection',
                priority='high'
            )
            logger.info(f"✅ Email notification sent to {EMAIL_RECIPIENT}")
        except Exception as e:
            logger.error(f"❌ Failed to send email notification: {e}")
    else:
        logger.warning("Email service not configured, skipping email notification")
    
    # Send WeChat notification
    if wechat_service.enabled:
        try:
            wechat_service.send_ths_collection_notification(
                trade_date=trade_date,
                success=success,
                record_count=record_count,
                error_msg=error_msg
            )
            logger.info("✅ WeChat notification sent")
        except Exception as e:
            logger.error(f"❌ Failed to send WeChat notification: {e}")
    else:
        logger.warning("WeChat service not configured, skipping WeChat notification")


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Daily Tushare THS Moneyflow Collector")
    logger.info("=" * 60)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure output directory exists
    ensure_output_dir()
    
    # Get latest trade date
    trade_date = get_latest_trade_date()
    logger.info(f"Collecting data for trade date: {trade_date}")
    
    # Collect THS moneyflow data
    df = collect_ths_moneyflow(trade_date)
    
    if df is not None:
        # Save to JSON
        filepath = save_to_json(df, trade_date)
        
        # Send success notification
        send_notification(trade_date, success=True, record_count=len(df))
    else:
        # Send failure notification
        send_notification(trade_date, success=False, error_msg="Failed to collect data or rate limited")
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()