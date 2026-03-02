# -*- coding: utf-8 -*-
import os

file_path = 'main.py'
if not os.path.exists(file_path):
    print(f"❌ 找不到 {file_path}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 毒瘤 1：删除导致崩溃的那句 print
    if 'click.echo(f"📊 绝对量比阈值: {volume_percentile}x")' in line or 'click.echo(f"📊 量比分位数: {volume_percentile}")' in line:
        # 替换为从配置文件读取并打印（缩进保持原来的缩进）
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + "from logic.core.config_manager import get_config_manager\n")
        new_lines.append(indent + "config_manager = get_config_manager()\n")
        new_lines.append(indent + "min_vol = config_manager.get('live_sniper.min_volume_multiplier', 3.0)\n")
        new_lines.append(indent + 'click.echo(f"📊 绝对量比阈值: {min_vol}x (配置驱动)")\n')
        continue

    # 毒瘤 2：删除错误的实盘日志打印
    if 'click.echo(f"📊 实盘引擎绝对量比阈值设置为: {volume_percentile}x' in line or 'click.echo(f"📊 实盘引擎量比分位数阈值设置为: {volume_percentile}' in line:
        continue # 直接删掉这句废话

    # 毒瘤 3：删除反向污染配置的代码
    if "config_manager._config['live_sniper']['min_volume_multiplier'] = volume_percentile" in line or "config_manager._config['halfway']['volume_surge_percentile'] = volume_percentile" in line:
        continue # 直接删掉这句废话
        
    # 毒瘤 4：修复 LiveTradingEngine 的调用传参
    if "volume_percentile=volume_percentile" in line:
        # 如果这行只有这个参数，直接跳过
        if line.strip() == "volume_percentile=volume_percentile," or line.strip() == "volume_percentile=volume_percentile":
             continue
        # 如果在一行里，把它替换掉
        line = line.replace("volume_percentile=volume_percentile,", "")
        line = line.replace("volume_percentile=volume_percentile", "")

    new_lines.append(line)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ main.py 毒瘤已全部使用动态游标拔除！")
