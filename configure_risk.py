"""
风险监控告警配置助手
"""

import json
from config import Config


def configure_risk_monitor():
    """
    配置风险监控告警
    """
    config = Config()
    
    print("=" * 50)
    print("风险监控告警配置")
    print("=" * 50)
    
    # 启用风险监控
    print("\n是否启用风险监控?")
    enabled = input("启用? (y/n, 默认: y): ").strip().lower()
    enabled = enabled != 'n'
    
    # 配置风险阈值
    print("\n配置风险阈值:")
    
    max_position_ratio = input("最大持仓比例 (0.5-1.0, 默认: 0.95): ").strip()
    max_position_ratio = float(max_position_ratio) if max_position_ratio else 0.95
    
    max_daily_loss_ratio = input("单日最大亏损比例 (0.01-0.2, 默认: 0.05): ").strip()
    max_daily_loss_ratio = float(max_daily_loss_ratio) if max_daily_loss_ratio else 0.05
    
    max_drawdown_ratio = input("最大回撤比例 (0.1-0.5, 默认: 0.2): ").strip()
    max_drawdown_ratio = float(max_drawdown_ratio) if max_drawdown_ratio else 0.2
    
    max_consecutive_losses = input("最大连续亏损次数 (默认: 5): ").strip()
    max_consecutive_losses = int(max_consecutive_losses) if max_consecutive_losses else 5
    
    # 配置邮件告警
    print("\n是否启用邮件告警?")
    email_enabled = input("启用邮件告警? (y/n, 默认: n): ").strip().lower()
    email_enabled = email_enabled == 'y'
    
    email_config = {
        'enabled': email_enabled
    }
    
    if email_enabled:
        print("\n配置邮件服务器:")
        smtp_host = input("SMTP服务器 (默认: smtp.gmail.com): ").strip() or 'smtp.gmail.com'
        smtp_port = input("SMTP端口 (默认: 587): ").strip() or '587'
        username = input("用户名: ").strip()
        password = input("密码: ").strip()
        to_addr = input("收件人邮箱: ").strip()
        
        email_config.update({
            'smtp_host': smtp_host,
            'smtp_port': int(smtp_port),
            'username': username,
            'password': password,
            'to_addr': to_addr
        })
    
    # 保存配置
    risk_config = {
        'enabled': enabled,
        'max_position_ratio': max_position_ratio,
        'max_daily_loss_ratio': max_daily_loss_ratio,
        'max_drawdown_ratio': max_drawdown_ratio,
        'max_consecutive_losses': max_consecutive_losses,
        'email_alert': email_config
    }
    
    config.update({'risk_monitor': risk_config})
    
    print("\n配置已保存!")
    print(f"配置文件: config.json")


def test_email_alert():
    """
    测试邮件告警
    """
    config = Config()
    risk_config = config.get_risk_config()
    email_config = risk_config.get('email_alert', {})
    
    if not email_config.get('enabled'):
        print("\n邮件告警未启用")
        return
    
    print("\n测试邮件告警...")
    
    try:
        from logic.risk_monitor import EmailAlertHandler
        
        handler = EmailAlertHandler(email_config)
        
        # 创建测试告警
        test_alert = {
            'level': 'WARNING',
            'message': '这是一条测试告警',
            'data': {'test': True}
        }
        
        handler(test_alert)
        
        print("✅ 测试邮件已发送")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def show_risk_config():
    """显示当前风险配置"""
    config = Config()
    risk_config = config.get_risk_config()
    
    print("\n当前风险监控配置:")
    print("=" * 50)
    
    print(f"启用状态: {'✅ 已启用' if risk_config.get('enabled') else '❌ 未启用'}")
    print(f"最大持仓比例: {risk_config.get('max_position_ratio', 0):.2%}")
    print(f"单日最大亏损: {risk_config.get('max_daily_loss_ratio', 0):.2%}")
    print(f"最大回撤: {risk_config.get('max_drawdown_ratio', 0):.2%}")
    print(f"最大连续亏损: {risk_config.get('max_consecutive_losses', 0)} 次")
    
    email_config = risk_config.get('email_alert', {})
    print(f"邮件告警: {'✅ 已启用' if email_config.get('enabled') else '❌ 未启用'}")
    
    if email_config.get('enabled'):
        print(f"  SMTP服务器: {email_config.get('smtp_host', '')}:{email_config.get('smtp_port', '')}")
        print(f"  用户名: {email_config.get('username', '')}")
        print(f"  收件人: {email_config.get('to_addr', '')}")
    
    print("=" * 50)


if __name__ == '__main__':
    print("\n风险监控告警配置工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 配置风险监控")
        print("2. 测试邮件告警")
        print("3. 显示当前配置")
        print("4. 退出")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            configure_risk_monitor()
        elif choice == '2':
            test_email_alert()
        elif choice == '3':
            show_risk_config()
        elif choice == '4':
            print("\n退出")
            break
        else:
            print("\n无效选项")