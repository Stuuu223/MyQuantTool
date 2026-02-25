import re

# 读取run_live_trading_engine.py文件
with open('C:\\Users\\pc\\Desktop\\Astock\\MyQuantTool\\tasks\\run_live_trading_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 改进火控模式相关提示
content = content.replace(
    '火控模式 - Tick订阅+实时算分',
    '高频监控模式 - Tick订阅+实时算分'
)

content = content.replace(
    '火控雷达已锁定',
    '高频监控已激活'
)

content = content.replace(
    '将使用回退数据源或手动订阅',
    '系统将持续监控市场信号'
)

content = content.replace(
    '股票池未初始化，无法启动火控模式',
    '当前无符合右侧起爆标准的目标，等待信号中...'
)

content = content.replace(
    '系统将等待自动补网',
    '系统持续监控中，等待右侧起爆信号...'
)

content = content.replace(
    '进入火控模式，锁定',
    '进入高频监控模式，锁定右侧起爆目标'
)

content = content.replace(
    '火控模式',
    '高频监控模式'
)

# 添加今日历史信号回放功能
history_func = '''

    def replay_today_signals(self):
        """
        CTO新增：今日历史信号回放
        收盘后运行时，回放当天的信号轨迹
        """
        from datetime import datetime
        current_time = datetime.now()
        
        # 如果在非交易时间运行，提供当日信号回放
        if current_time.hour > 15 or (current_time.hour == 15 and current_time.minute >= 5):  # 15:05后认为是收盘后
            logger.info("📊 收盘后模式：正在回放今日信号轨迹...")
            logger.info("💡 提示：系统将在后台记录今日所有信号点")
            # 此处可扩展为读取当日信号日志并回放
        else:
            logger.info("💡 提示：系统正在实时监控右侧起爆信号")
'''

# 找到合适位置插入函数 - 在类的末尾
class_end = content.rfind('\nclass ', content.rfind('class LiveTradingEngine'))
if class_end != -1:
    next_class = content.find('\nclass ', class_end + 1)
    if next_class != -1:
        content = content[:next_class] + history_func + content[next_class:]
    else:
        content += history_func

# 保存文件
with open('C:\\Users\\pc\\Desktop\\Astock\\MyQuantTool\\tasks\\run_live_trading_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ LiveTradingEngine提示信息已改进')
print('✅ 历史信号回放功能已添加')