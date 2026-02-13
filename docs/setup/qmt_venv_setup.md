# QMT虚拟环境快速设置指南

## 概述

QMT（迅投量化交易）需要在专用的Python虚拟环境中运行，以确保xtquant模块的正常工作。

---

## 🚀 快速设置（3步完成）

### 步骤1：创建QMT虚拟环境

```bash
# 在项目根目录执行
python -m venv venv_qmt
```

### 步骤2：激活虚拟环境并安装xtquant

```bash
# Windows
venv_qmt\Scripts\activate

# 安装xtquant
pip install xtquant
```

### 步骤3：验证安装

```bash
# 检查xtquant模块
python -c "import xtquant; print('xtquant version:', xtquant.__version__)"

# 运行测试
scripts\test_auction_collector.bat
```

---

## 📂 目录结构

```
E:\MyQuantTool\
├── venv_qmt/                 # QMT虚拟环境
│   ├── Scripts/
│   │   ├── python.exe        # QMT Python解释器
│   │   ├── activate.bat      # 激活脚本
│   │   └── pip.exe
│   └── Lib/
│       └── site-packages/
│           └── xtquant/      # QMT量化模块
├── scripts/
│   ├── start_auction_collector.bat    # 启动脚本（自动使用venv_qmt）
│   └── test_auction_collector.bat     # 测试脚本（自动使用venv_qmt）
└── tasks/
    └── scheduled_auction_collector.py # 采集器主程序
```

---

## 🔧 常见问题

### Q1: 虚拟环境创建失败？

**症状：**
```
Error: Command '['...\\venv_qmt\\Scripts\\python.exe', '-Im', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1.
```

**解决方案：**
1. 使用Python 3.8+创建虚拟环境
2. 确保有管理员权限
3. 尝试指定Python路径：
   ```bash
   C:\Python39\python.exe -m venv venv_qmt
   ```

### Q2: xtquant安装失败？

**症状：**
```
ERROR: Could not find a version that satisfies the requirement xtquant
```

**解决方案：**
1. xtquant需要从QMT官方获取，pip可能无法直接安装
2. 从QMT安装目录复制xtquant模块到虚拟环境：
   ```bash
   # QMT xtquant通常在：
   # C:\QMT\userdata\xtquant\
   xcopy C:\QMT\userdata\xtquant\* venv_qmt\Lib\site-packages\ /E /I /Y
   ```

### Q3: 启动时提示"模块不存在"？

**症状：**
```
ModuleNotFoundError: No module named 'xtquant'
```

**解决方案：**
1. 确认虚拟环境已激活：
   ```bash
   venv_qmt\Scripts\activate
   ```
2. 重新安装xtquant：
   ```bash
   pip install xtquant
   ```
3. 或从QMT目录复制xtquant模块

---

## 📊 验证清单

运行以下命令验证安装：

```bash
# 1. 检查虚拟环境
dir venv_qmt\Scripts\python.exe

# 2. 检查xtquant
venv_qmt\Scripts\python.exe -c "import xtquant; print('OK')"

# 3. 运行测试
scripts\test_auction_collector.bat

# 4. 检查QMT连接
# （需要在QMT客户端运行后才能通过）
```

---

## 🎯 最佳实践

1. **专用虚拟环境**：QMT使用单独的venv_qmt，不影响其他模块
2. **版本控制**：将xtquant版本号写入requirements.txt
3. **定期更新**：QMT更新后同步更新xtquant
4. **测试先行**：修改代码前先运行测试

---

## 📞 技术支持

**遇到问题？**
1. 检查虚拟环境路径：`venv_qmt\Scripts\python.exe`
2. 检查xtquant安装：`venv_qmt\Lib\site-packages\xtquant\`
3. 查看QMT配置：`config\qmt_config.json`
4. 运行测试：`scripts\test_auction_collector.bat`

---

## 🔗 相关文档

- [竞价采集器使用指南](./auction_collector_guide.md)
- [QMT完整配置指南](./QMT完整配置指南.md)
- [Redis配置指南](./redis_setup_guide.md)