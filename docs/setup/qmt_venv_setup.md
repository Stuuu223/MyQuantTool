# QMT 虚拟环境配置指南

## 📋 概述

QMT 模块需要 Python 3.10.11，项目使用 `venv_qmt` 虚拟环境（277 MB，已加入 .gitignore）。

**为什么需要虚拟环境？**
- QMT 的编译模块（`.pyd` 文件）是为 Python 3.10 编译的
- 系统可能是 Python 3.14 或其他版本，无法加载 QMT 模块
- 虚拟环境确保每个设备都有相同的 Python 3.10.11 环境

---

## 🚀 跨设备首次配置

### 前提条件

1. **QMT 客户端已安装**: `E:\qmt\`
2. **Python 3.10.11 已安装**: `C:\Python310\python.exe`

### 配置步骤

#### 1. 下载 Python 3.10.11

```bash
# 官方下载链接
https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

# 安装配置
- 安装路径: C:\Python310
- 勾选所有 Optional Features
- 勾选所有 Advanced Options
```

#### 2. 创建虚拟环境

```bash
cd E:\MyQuantTool
C:\Python310\python.exe -m venv venv_qmt
```

#### 3. 升级 pip

```bash
venv_qmt\Scripts\python.exe -m pip install --upgrade pip
```

#### 4. 安装核心依赖

```bash
venv_qmt\Scripts\pip.exe install akshare pandas numpy requests
```

#### 5. 安装 xtquant

```bash
venv_qmt\Scripts\pip.exe install xtquant
```

#### 6. 复制 QMT 模块文件

从 `E:\qmt\bin.x64\Lib\site-packages\xtquant\` 复制以下文件到 `E:\MyQuantTool\xtquant\`:

```
E:\qmt\bin.x64\Lib\site-packages\xtquant\
├── IPythonApiClient.cp310-win_amd64.pyd  → E:\MyQuantTool\xtquant\
├── xtpythonclient.cp310-win_amd64.pyd    → E:\MyQuantTool\xtquant\
└── xtdata.py                              → E:\MyQuantTool\xtquant\
```

**批量复制命令**:
```bash
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\IPythonApiClient.cp310-win_amd64.pyd" "E:\MyQuantTool\xtquant\"
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\xtpythonclient.cp310-win_amd64.pyd" "E:\MyQuantTool\xtquant\"
copy "E:\qmt\bin.x64\Lib\site-packages\xtquant\xtdata.py" "E:\MyQuantTool\xtquant\"
```

#### 7. 验证配置

```bash
venv_qmt\Scripts\python.exe -c "from xtquant import xtdata; print('QMT 可用')"
# 期望输出: QMT 可用
```

---

## 💻 使用虚拟环境

### 方式1: VSCode 自动使用（推荐）

**VSCode 已配置默认使用 `venv_qmt` 虚拟环境**：

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv_qmt/Scripts/python.exe"
}
```

直接在 VSCode 终端运行即可：

```bash
# 自动使用虚拟环境
python analyze.py 300997 90 --supplement
```

### 方式2: 命令行激活

**Windows CMD**:
```bash
E:\MyQuantTool\venv_qmt\Scripts\activate.bat
python --version  # 应显示 Python 3.10.11
```

**Windows PowerShell**:
```bash
E:\MyQuantTool\venv_qmt\Scripts\Activate.ps1
python --version  # 应显示 Python 3.10.11
```

### 方式3: 使用启动脚本

项目提供了便捷启动脚本：

```bash
# 运行分析（自动使用虚拟环境）
analyze_supplement.bat 300997 90 --supplement
```

**启动脚本内容**:
```batch
@echo off
E:\MyQuantTool\venv_qmt\Scripts\python.exe analyze.py %*
pause
```

---

## 🔧 常见问题

### Q1: DLL 加载失败

**错误**: `DLL load failed while importing IPythonApiClient: 找不到指定的模块`

**原因**: 使用了错误的 Python 版本（如 Python 3.14）

**解决**: 确保使用虚拟环境中的 Python 3.10.11

```bash
# 检查 Python 版本
venv_qmt\Scripts\python.exe --version
# 应显示: Python 3.10.11
```

### Q2: xtdata 导入失败

**错误**: `No module named 'xtdata'`

**原因**: QMT 模块文件未正确复制

**解决**: 检查 `xtquant` 目录中是否有 `xtdata.py` 和 `.pyd` 文件

```bash
dir E:\MyQuantTool\xtquant\*.pyd
dir E:\MyQuantTool\xtquant\xtdata.py
```

### Q3: VSCode 中看不到虚拟环境

**原因**: `files.exclude` 配置隐藏了虚拟环境文件夹

**解决**: `.vscode/settings.json` 中已移除隐藏配置

```json
{
  "files.exclude": {
    // 不再隐藏 venv_qmt
  }
}
```

### Q4: 跨设备开发需要重复配置吗？

**是的**，因为虚拟环境（277 MB）已加入 `.gitignore`，不会提交到 Git。

**建议**:
- 保留本文档作为配置参考
- 每次在新设备上按步骤重新配置
- 约 10 分钟完成配置

---

## 📚 相关文档

- [QMT 环境配置指南 - Python 3.10](QMT环境配置指南-Python310.md)
- [QMT 模块安装问题解决方案](QMT模块安装问题解决方案.md)
- [QMT 接口配置指南](qmt_setup_guide.md)

---

**创建时间**: 2026-02-03  
**版本**: 1.0
**维护者**: iFlow CLI