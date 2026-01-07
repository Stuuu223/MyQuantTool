"""
券商API配置助手
"""

import json
from config import Config


def configure_broker_api():
    """
    配置券商API
    
    交互式配置券商API密钥
    """
    config = Config()
    
    print("=" * 50)
    print("券商API配置")
    print("=" * 50)
    
    # 选择券商
    print("\n请选择要配置的券商:")
    print("1. 富途牛牛 (Futu)")
    print("2. 东方财富 (EastMoney)")
    print("3. 华泰证券 (Huatai)")
    print("4. 中信证券 (Citic)")
    print("5. 退出")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == '1':
        print("\n配置富途牛牛API")
        host = input("服务器地址 (默认: 127.0.0.1): ").strip() or '127.0.0.1'
        port = input("端口 (默认: 11111): ").strip() or '11111'
        password = input("密码: ").strip()
        
        broker_config = {
            'futu': {
                'enabled': True,
                'host': host,
                'port': int(port),
                'password': password
            }
        }
    
    elif choice == '2':
        print("\n配置东方财富API")
        account = input("账号: ").strip()
        password = input("密码: ").strip()
        
        broker_config = {
            'eastmoney': {
                'enabled': True,
                'account': account,
                'password': password
            }
        }
    
    elif choice == '3':
        print("\n配置华泰证券API")
        app_id = input("应用ID (app_id): ").strip()
        app_secret = input("应用密钥 (app_secret): ").strip()
        account = input("账号: ").strip()
        password = input("密码: ").strip()
        server_url = input("服务器地址 (默认: https://open.htsec.com): ").strip() or 'https://open.htsec.com'
        
        broker_config = {
            'huatai': {
                'enabled': True,
                'app_id': app_id,
                'app_secret': app_secret,
                'account': account,
                'password': password,
                'server_url': server_url
            }
        }
    
    elif choice == '4':
        print("\n配置中信证券API")
        app_id = input("应用ID (app_id): ").strip()
        app_secret = input("应用密钥 (app_secret): ").strip()
        account = input("账号: ").strip()
        password = input("密码: ").strip()
        server_url = input("服务器地址 (默认: https://open.citics.com): ").strip() or 'https://open.citics.com'
        
        broker_config = {
            'citic': {
                'enabled': True,
                'app_id': app_id,
                'app_secret': app_secret,
                'account': account,
                'password': password,
                'server_url': server_url
            }
        }
    
    elif choice == '5':
        print("\n退出配置")
        return
    
    else:
        print("\n无效选项")
        return
    
    # 保存配置
    config.update({'broker_apis': broker_config})
    
    print("\n配置已保存!")
    print(f"配置文件: config.json")


def test_broker_api(broker_name):
    """
    测试券商API连接
    
    Args:
        broker_name: 券商名称
    """
    config = Config()
    broker_config = config.get_broker_config(broker_name)
    
    if not broker_config or not broker_config.get('enabled'):
        print(f"\n{broker_name} API未配置或未启用")
        return
    
    print(f"\n测试 {broker_name} API连接...")
    
    try:
        if broker_name == 'futu':
            from logic.broker_api import BrokerAPIFactory
            api = BrokerAPIFactory.create_api('futu', broker_config)
            
            if api and api.connect():
                print("✅ 富途API连接成功")
                api.disconnect()
            else:
                print("❌ 富途API连接失败")
        
        elif broker_name == 'huatai':
            from logic.real_broker_api import HuataiRealAPI
            api = HuataiRealAPI(broker_config)
            
            if api.connect():
                print("✅ 华泰API连接成功")
                api.disconnect()
            else:
                print("❌ 华泰API连接失败")
        
        elif broker_name == 'citic':
            from logic.real_broker_api import CiticRealAPI
            api = CiticRealAPI(broker_config)
            
            if api.connect():
                print("✅ 中信API连接成功")
                api.disconnect()
            else:
                print("❌ 中信API连接失败")
        
        else:
            print(f"❌ 不支持的券商: {broker_name}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def list_broker_configs():
    """列出所有券商配置"""
    config = Config()
    broker_apis = config.get('broker_apis', {})
    
    print("\n券商API配置状态:")
    print("=" * 50)
    
    for broker_name, broker_config in broker_apis.items():
        enabled = broker_config.get('enabled', False)
        status = "✅ 已启用" if enabled else "❌ 未启用"
        print(f"{broker_name}: {status}")
    
    print("=" * 50)


if __name__ == '__main__':
    print("\n券商API配置工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 配置券商API")
        print("2. 测试券商API")
        print("3. 列出所有配置")
        print("4. 退出")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            configure_broker_api()
        elif choice == '2':
            list_broker_configs()
            broker_name = input("\n请输入要测试的券商名称: ").strip()
            test_broker_api(broker_name)
        elif choice == '3':
            list_broker_configs()
        elif choice == '4':
            print("\n退出")
            break
        else:
            print("\n无效选项")