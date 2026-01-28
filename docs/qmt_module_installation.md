# QMT 模块完整安装指南

## 📌 重要说明

QMT 的 xtquant 模块包含一些底层通信模块（IPythonApiClient 和 xtpythonclient），这些模块需要从 QMT 客户端安装目录复制到项目中。

## 🔧 安装步骤

### 方法1：复制官方模块（推荐）

1. **找到 QMT 安装目录**
   - 通常位于：`C:\QMT\QMT客户端\bin.x64\Lib\site-packages\`
   - 或：`D:\QMT\QMT\bin.x64\Lib\site-packages\`

2. **复制必要文件**
   从 QMT 安装目录的 `Lib\site-packages` 中复制以下文件到项目的 `xtquant` 目录：
   ```
   QMT/bin.x64/Lib/site-packages/          →  E:\MyQuantTool\xtquant\
   ├── IPythonApiClient.py                →  IPythonApiClient.py
   └── xtpythonclient.py                  →  xtpythonclient.py
   ```

3. **验证安装**
   ```bash
   python test_qmt_connection.py
   ```

### 方法2：设置 PYTHONPATH 环境变量

1. **临时设置（当前会话）**
   ```powershell
   $env:PYTHONPATH = "C:\QMT\QMT客户端\bin.x64\Lib\site-packages;$env:PYTHONPATH"
   ```

2. **永久设置**
   - 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
   - 在"系统变量"中新建 `PYTHONPATH`
   - 值：`C:\QMT\QMT客户端\bin.x64\Lib\site-packages`

3. **验证**
   ```bash
   python -c "import xtquant; print('QMT 模块已加载')"
   ```

### 方法3：使用软链接（Linux/WSL）

```bash
cd E:\MyQuantTool\xtquant
ln -s /mnt/c/QMT/QMT客户端/bin.x64/Lib/site-packages/IPythonApiClient.py
ln -s /mnt/c/QMT/QMT客户端/bin.x64/Lib/site-packages/xtpythonclient.py
```

## ✅ 验证安装

运行测试脚本验证 QMT 模块是否正确安装：

```bash
python test_qmt_connection.py
```

期望输出：
```
============================================================
🧪 股票代码格式转换测试
============================================================

📝 测试代码格式转换:
  600519     -> 600519.SH
  sh600519   -> 600519.SH
  300750     -> 300750.SZ
  sz300750   -> 300750.SZ
  000001     -> 000001.SZ

✅ 代码格式转换测试通过


============================================================
🧪 QMT 基础连接测试
============================================================

1️⃣  导入 xtdata 模块...
   ✅ 导入成功

2️⃣  获取沪深A股股票列表...
   ✅ 成功获取 XXXX 只股票

3️⃣  测试获取tick数据...
   ✅ 成功获取tick数据

============================================================
✅ QMT 基础连接测试完成
============================================================
```

## 🚨 常见问题

### Q1: 找不到 QMT 安装目录

**解决方法：**
- 打开 QMT 客户端，查看"帮助" → "关于"中的安装路径
- 或者搜索 `xtdata.py` 文件的位置

### Q2: 复制文件后仍然报错

**可能原因：**
1. 文件复制不完整
2. QMT 版本不兼容
3. 缺少依赖的 DLL 文件

**解决方法：**
- 确保复制了所有必要文件
- 检查 QMT 客户端版本是否与项目兼容
- 复制 `bin.x64` 目录下的所有 DLL 文件到项目根目录

### Q3: 不想安装 QMT 模块

**没关系！** 你的项目已经有多个数据源：

- ✅ **easyquotation** - 实时行情（主要使用）
- ✅ **AkShare** - 市场数据（主要使用）
- ⚠️ **QMT** - 补充数据源（可选）

如果不使用 QMT，可以完全忽略这些错误，系统仍然可以正常运行。

## 📊 数据源优先级

你的系统支持多数据源自动切换：

1. **实时行情**：
   - 优先：easyquotation
   - 备用：QMT tick 数据

2. **历史数据**：
   - 优先：AkShare
   - 备用：QMT 历史数据

3. **灾备机制**：
   - 如果 easyquotation 失败 → 降级到 AkShare
   - 如果 AkShare 失败 → 降级到本地文件
   - 如果本地文件不存在 → 返回核心资产列表

## 🎯 总结

**QMT 模块是可选的，不是必需的！**

- 如果你有 QMT 客户端 → 按上述步骤安装，可以获得更好的数据质量
- 如果没有 QMT 客户端 → 完全不影响系统运行，继续使用 easyquotation + AkShare

你的系统已经设计好了多数据源架构，不会因为缺少 QMT 而无法运行。

---

**Author**: iFlow CLI
**Date**: 2026-01-28
**Version**: V1.0