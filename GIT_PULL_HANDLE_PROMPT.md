# Git Pull 处理本地未提交更改的 Prompt

## 请按以下步骤执行：

### 步骤 1：检查当前状态
```bash
git status
```
查看是否有未提交的更改（modified 或 untracked files）。

### 步骤 2：如果有未提交的更改，保存到 stash
```bash
git stash save "保存本地修改 - $(date +%Y%m%d_%H%M%S)"
```
这会将所有未提交的更改保存起来。

### 步骤 3：拉取最新代码
```bash
git pull origin master
```

### 步骤 4：恢复本地修改
```bash
git stash pop
```

### 步骤 5：检查是否有冲突
```bash
git status
```

#### 情况 A：没有冲突（正常）
直接提交并推送：
```bash
git add .
git commit -m "合并远程更新和本地修改"
git push origin master
```

#### 情况 B：有冲突（需要手动解决）

**步骤 5.1：查看冲突文件**
```bash
git status
```
会显示哪些文件有冲突（标记为 both modified）。

**步骤 5.2：打开冲突文件**
每个冲突文件会有类似这样的标记：
```
<<<<<<< HEAD
这里是你的本地修改
=======
这里是远程的修改
>>>>>>> origin/master
```

**步骤 5.3：手动解决冲突**
- 保留需要的代码部分
- 删除冲突标记（<<<<<<<, =======, >>>>>>>）
- 保存文件

**步骤 5.4：标记冲突已解决**
```bash
git add <冲突文件名>
```

**步骤 5.5：提交并推送**
```bash
git commit -m "解决冲突并合并远程更新"
git push origin master
```

## 完整的一键执行脚本（推荐）

如果不确定是否有冲突，可以直接运行这个脚本：

```bash
#!/bin/bash

echo "=== 开始处理 Git Pull ==="

# 1. 保存本地修改
echo "步骤 1: 保存本地修改..."
git stash save "自动保存 - $(date +%Y%m%d_%H%M%S)"

# 2. 拉取最新代码
echo "步骤 2: 拉取最新代码..."
git pull origin master

# 3. 恢复本地修改
echo "步骤 3: 恢复本地修改..."
git stash pop

# 4. 检查状态
echo "步骤 4: 检查状态..."
git status

# 5. 提交并推送
echo "步骤 5: 提交并推送..."
git add .
git commit -m "合并远程更新和本地修改"
git push origin master

echo "=== 完成 ==="
```

## 常见问题处理

### Q1: stash pop 时出现冲突
**解决方法：**
```bash
# 放弃 stash，重新开始
git stash drop
git pull origin master
# 然后手动重新应用你的修改
```

### Q2: pull 时出现 "refusing to merge unrelated histories"
**解决方法：**
```bash
git pull origin master --allow-unrelated-histories
```

### Q3: 想要放弃本地修改，直接使用远程代码
**解决方法：**
```bash
git reset --hard origin/master
git pull origin master
```

### Q4: 想要保留远程代码，放弃本地修改
**解决方法：**
```bash
git fetch origin
git reset --hard origin/master
```

## 推荐操作流程（最安全）

```bash
# 1. 先检查状态
git status

# 2. 如果有未提交的更改，先提交或stash
# 方案A：提交
git add .
git commit -m "本地修改"

# 或方案B：stash
git stash save "临时保存"

# 3. 拉取最新代码
git pull origin master

# 4. 如果用了stash，恢复
git stash pop

# 5. 解决冲突（如果有）

# 6. 推送
git push origin master
```

## 给AI执行的建议

**请按以下优先级执行：**

1. **优先使用 stash 方案**（最安全）
   - git stash save
   - git pull
   - git stash pop
   - 如果有冲突，手动解决后提交

2. **如果 stash 失败**，使用 commit 方案
   - git add .
   - git commit -m "本地修改"
   - git pull
   - 解决冲突
   - git push

3. **如果想放弃本地修改**，使用 reset 方案
   - git reset --hard origin/master
   - git pull

## 关键提示

- **执行前先备份**：确保重要的修改已备份
- **先查看状态**：git status 看清楚当前状态
- **逐步执行**：不要一次性运行多个命令
- **解决冲突要仔细**：确保代码正确后再提交
- **推送前测试**：确保代码能正常运行后再push

---

**请根据实际情况选择合适的方案执行！**