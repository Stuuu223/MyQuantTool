#!/bin/bash
# 顽主杯数据采集环境安装脚本

set -e

echo "=========================================="
echo "顽主杯小程序数据采集环境安装"
echo "=========================================="

# 检查Python版本
python3 --version || { echo "错误: 未找到Python3"; exit 1; }

# 创建虚拟环境
echo "[1/4] 创建Python虚拟环境..."
cd /root/wanzhu_data
python3 -m venv venv

# 激活虚拟环境
echo "[2/4] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "[3/4] 安装依赖包..."
pip install --upgrade pip
pip install requests pandas

# 设置脚本权限
echo "[4/4] 设置脚本权限..."
chmod +x /root/wanzhu_data/crawl_wanzhu_miniprogram.py

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 编辑配置文件: wanzhu_miniprogram_config.json"
echo "2. 填入抓包获取的真实API信息"
echo "3. 测试运行: ./venv/bin/python crawl_wanzhu_miniprogram.py"
echo "4. 设置定时任务: crontab -e"
echo ""
echo "示例定时任务（每天16:10运行）:"
echo "10 16 * * * cd /root/wanzhu_data && /root/wanzhu_data/venv/bin/python crawl_wanzhu_miniprogram.py >> crawl.log 2>&1"
echo ""