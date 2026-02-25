import re

# 读取main.py文件
with open('C:\\Users\\pc\\Desktop\\Astock\\MyQuantTool\\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 改进非交易时间提示
content = content.replace(
    "f\"⚠️ 当前时间 {now.strftime('%H:%M')} 已超过截停时间 {cutoff_time}\"",
    "f\"⚠️ 当前时间 {now.strftime('%H:%M')} 已超过截停时间 {cutoff_time}，等待下一交易日\""
)

content = content.replace(
    "click.style(\"⚠️ 根据右侧起爆纪律，系统将监控但不发单！\", fg='yellow')",
    "click.style(\"⚠️ 系统进入收盘后监控模式，等待下一交易日\", fg='yellow')"
)

content = content.replace(
    "f\"⏳ 等待开盘... (距开盘 {wait_seconds}秒)\"",
    "f\"⏳ 非交易时间，等待开盘... (距9:30开盘 {wait_seconds}秒)\""
)

# 改进引擎启动提示
content = content.replace(
    "click.echo(\"⚡ Step 2: 挂载 EventDriven 引擎...\")",
    "click.echo(\"⚡ Step 2: 启动实盘监控引擎...\")"
)

content = content.replace(
    "f\"📊 实盘引擎量比分位数阈值设置为: {volume_percentile}\"",
    "f\"📊 实盘引擎量比分位数阈值设置为: {volume_percentile} (右侧起爆标准)\""
)

# 保存文件
with open('C:\\Users\\pc\\Desktop\\Astock\\MyQuantTool\\main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main.py提示信息已改进')
