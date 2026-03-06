# 托盘版本号功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 在托盘菜单显示版本号，每次 build.sh 执行后自动递增版本号

**Architecture:** 版本号存储在 pyproject.toml 中，config.py 提供读取函数，build.sh 脚本负责递增

**Tech Stack:** Python, pystray, bash, tomllib

---

## Task 1: 修改 pyproject.toml 添加版本号

**Files:**
- Modify: `pyproject.toml`

**Step 1: 修改版本号**

将 pyproject.toml 中的 version 从 "0.1.0" 改为 "1.7.00":

```toml
version = "1.7.00"
```

---

## Task 2: 修改 config.py 添加 get_version() 函数

**Files:**
- Modify: `config.py`

**Step 1: 添加 tomllib 导入**

在 import 语句中添加：

```python
import tomllib
```

**Step 2: 添加 get_version() 函数**

在 config.py 中添加：

```python
def get_version():
    """从 pyproject.toml 读取版本号"""
    pyproject_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyproject.toml')
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
            return data.get('project', {}).get('version', '1.7.00')
    except Exception:
        return '1.7.00'


# 兼容旧代码
VERSION = get_version()
```

---

## Task 3: 修改托盘菜单显示版本号

**Files:**
- Modify: `ui/tray.py`

**Step 1: 添加 VERSION 导入**

在 `ui/tray.py` 添加：

```python
from config import VERSION
```

**Step 2: 移除分隔线菜单项**

删除：`pystray.MenuItem("─", lambda icon, item: None, enabled=False),`

**Step 3: 添加版本号菜单项**

在 `return pystray.Menu(...)` 末尾添加：

```python
pystray.MenuItem(f"版本号 {VERSION}", lambda icon, item: None, enabled=False),
```

---

## Task 4: 修改 build.sh 自动递增版本号

**Files:**
- Modify: `build.sh`

**Step 1: 添加版本读取和递增逻辑**

在 pyinstaller 打包成功后（`if [ $? -eq 0 ]; then` 块内），添加：

```bash
# 递增版本号
VERSION_FILE="pyproject.toml"
# 提取当前版本号
CURRENT_VERSION=$(grep -oP 'version = "\K[0-9.]+' "$VERSION_FILE")
# 提取最后两位数字
MAJOR_VERSION=$(echo "$CURRENT_VERSION" | cut -d'.' -f1-2)
MINOR_VERSION=$(echo "$CURRENT_VERSION" | cut -d'.' -f3)
# 递增（处理 99 后回到 00）
if [ "$MINOR_VERSION" -eq 99 ]; then
    NEW_MINOR="00"
else
    NEW_MINOR=$(printf "%02d" $((10#$MINOR_VERSION + 1)))
fi
NEW_VERSION="${MAJOR_VERSION}.${NEW_MINOR}"
# 写回 pyproject.toml
sed -i "s/version = \"[0-9.]*\"/version = \"$NEW_VERSION\"/" "$VERSION_FILE"
echo "版本号已更新: $CURRENT_VERSION -> $NEW_VERSION"
```

---

## Task 5: 验证功能

**Step 1: 运行 build.sh**

```bash
./build.sh
```

**Step 2: 检查 pyproject.toml 中的 version 是否递增**

```bash
grep "version" pyproject.toml | head -1
```

预期输出: `version = "1.7.01"`

**Step 3: 运行程序检查托盘菜单**

```bash
uv run python main.py
```

托盘菜单应显示 "版本号 1.7.01"
