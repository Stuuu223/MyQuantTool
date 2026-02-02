# QMT 环境配置指南 - Python 3.10

## 🎯 目标

将系统从 Python 3.14 降级到 Python 3.10，以启用 QMT 极速数据接口。

**性能提升预期**：
- 实时数据延迟：3秒 → 0.05秒（60倍提升）
- 数据源：EasyQuotation（HTTP轮询）→ QMT（推流模式）

---

## 📋 第1步：下载 Python 3.10.11

### 官方下载链接
https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

**文件名**：python-3.10.11-amd64.exe

---

## 🔧 第2步：安装 Python 3.10.11

### 安装步骤

1. **运行安装程序**
   - 双击运行下载的 python-3.10.11-amd64.exe

2. **初始界面**
   - 不要勾选 Add Python 3.10 to PATH
   - 点击 Customize installation

3. **Optional Features**
   - 勾选所有选项
   - 点击 Next

4. **Advanced Options**
   - 安装路径设置为：C:\Python310
   - 勾选所有选项
   - 点击 Install

5. **等待安装完成**
   - 看到 Setup was successful 即表示安装成功

6. **点击 Close 完成安装

---

## ✅ 第3步：验证安装

打开 PowerShell 或 CMD，执行：

C:\Python310\python.exe --version

**预期输出**：Python 3.10.11

---

## 🏗️ 第4步：创建 Python 3.10 虚拟环境

cd E:\MyQuantTool

# 使用 Python 3.10 创建虚拟环境
C:\Python310\python.exe -m venv venv_qmt

# 激活虚拟环境
.\venv_qmt\Scripts\activate

# 验证虚拟环境
python --version

**预期输出**：Python 3.10.11

---

## 📦 第5步：安装项目依赖

# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

---

## 🧪 第6步：测试 QMT 连接

确保 QMT 客户端已启动并登录，然后运行：

python scripts/init_qmt.py

**预期输出**：✅ QMT 数据接口连接测试完成

---

## 🚀 第7步：启动系统

python main.py

---

## 🔄 后续使用

### 每次启动系统时

# 1. 激活虚拟环境
.\venv_qmt\Scripts\activate

# 2. 启动系统
python main.py

---

## 📊 性能对比

| 指标 | Python 3.14 + EasyQuotation | Python 3.10 + QMT |
|------|----------------------------|-------------------|
| 数据延迟 | 2-3秒 | 50-100毫秒 |
| 数据质量 | 依赖网络 | 官方数据 |
| 连接方式 | HTTP 轮询 | 推流模式 |

---

## 🎉 完成后

恭喜！你已经成功配置了 QMT 环境，系统将使用毫秒级数据延迟的 QMT 接口。

**创建时间**：2026-01-28
**版本**：V1.0
**状态**：待执行
