# 自动更新功能实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在程序启动时自动检查 Gitee releases 是否有新版本，静默下载更新包，下次重启时自动替换

**Architecture:** 新增 utils/updater.py 模块处理更新检查和下载，修改 config.py 支持打包后的版本读取，修改 main.py 集成更新流程

**Tech Stack:** Python 标准库 (urllib, shutil, os, json)

---

## 文件结构

- **新增**: `utils/updater.py` - 自动更新核心逻辑
- **修改**: `config.py` - 版本号读取优化 + auto_update 配置
- **修改**: `main.py` - 启动时检查更新
- **修改**: `build.sh` - 打包后写入 version.txt

---

## Chunk 1: 配置模块更新

### Task 1: 更新 config.py 版本号读取逻辑

**Files:**
- Modify: `config.py`

- [ ] **Step 1: 更新 get_version() 函数，优先读取 version.txt**

```python
def get_version():
    """从 version.txt 或 pyproject.toml 读取版本号"""
    # 1. 优先读取 version.txt（打包后使用）
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    version_file = os.path.join(base_dir, 'version.txt')
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass

    # 2. 备选：从 pyproject.toml 读取
    pyproject_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyproject.toml')
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
            return data.get('project', {}).get('version', '1.7.00')
    except Exception:
        return '1.7.00'
```

- [ ] **Step 2: 添加 auto_update 配置加载**

在 `load_config()` 函数中，在 `restrict_night_hours` 检查之后添加：

```python
# 自动更新配置
if "auto_update" not in g_config:
    g_config["auto_update"] = {
        "enabled": True,
        "last_check_time": None
    }
```

- [ ] **Step 3: 运行测试验证**

```bash
cd /d/Code/parental-control
uv run python -c "from config import get_version; print(get_version())"
```
Expected: 输出当前版本号

- [ ] **Step 4: Commit**

```bash
git add config.py
git commit -m "feat: 更新版本号读取逻辑支持打包后版本，添加 auto_update 配置"
```

---

## Chunk 3: 集成到主程序

### Task 3: 修改 main.py 集成更新流程

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在 main.py 导入 updater 模块并在启动时调用**

在 `from config import load_config` 之后添加：

```python
from utils.updater import run_auto_update
```

在 `load_config()` 之后添加更新检查：

```python
def main():
    """主入口函数"""
    load_config()  # 加载配置

    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()

    if args.install:
        add_to_startup()
        sys.exit(0)

    # 执行自动更新检查
    run_auto_update()

    # 检查单实例锁
    locker = SingleInstance()
    # ... 其余代码不变
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /d/Code/parental-control
uv run python main.py --help
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: 启动时自动检查更新"
```

---

## Chunk 4: 打包脚本更新

### Task 4: 修改 build.sh 写入 version.txt

**Files:**
- Modify: `build.sh`

- [ ] **Step 1: 在 build.sh 打包成功后添加 version.txt 写入**

在 `echo "版本号已更新: $CURRENT_VERSION -> $NEW_VERSION"` 之后，`echo -e "${GREEN}✓ 打包成功..."` 之前添加：

```bash
# 写入版本号文件
echo "$NEW_VERSION" > dist/version.txt
echo "版本号已写入: dist/version.txt"
```

- [ ] **Step 2: Commit**

```bash
git add build.sh
git commit -m "feat: 打包时写入 version.txt 支持自动更新"
```

---

## 执行顺序

1. Chunk 1: 更新 config.py
2. Chunk 2: 创建 utils/updater.py
3. Chunk 3: 修改 main.py
4. Chunk 4: 修改 build.sh

---

## Chunk 2: 自动更新模块

### Task 2: 创建 utils/updater.py

**Files:**
- Create: `utils/updater.py`

- [ ] **Step 1: 编写 updater.py 模块**

```python
"""自动更新模块"""
import os
import sys
import json
import shutil
import urllib.request
import urllib.error
from typing import Optional
import config
from utils import get_logger

logger = get_logger(__name__)

GITEE_API_URL = "https://gitee.com/api/v5/repos/degao/parental-control/releases/latest"


def get_update_dir() -> str:
    """获取更新目录路径"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    update_dir = os.path.join(base_dir, 'update')
    os.makedirs(update_dir, exist_ok=True)
    return update_dir


def parse_version(version_str: str) -> tuple:
    """解析版本号为元组用于比较"""
    # 去掉 v 前缀
    v = version_str.lstrip('v')
    parts = v.split('.')
    # 补齐到3位
    while len(parts) < 3:
        parts.append('0')
    return tuple(int(p) for p in parts)


def check_for_update() -> tuple[bool, Optional[str]]:
    """检查是否有新版本
    返回: (是否有新版本, 新版本下载URL)
    """
    try:
        # 确保配置已加载
        if config.g_config is None:
            config.load_config()

        # 检查是否启用自动更新
        auto_update = config.g_config.get('auto_update', {})
        if not auto_update.get('enabled', True):
            logger.info("自动更新已禁用")
            return False, None

        # 调用 Gitee API
        logger.info(f"检查更新: {GITEE_API_URL}")
        req = urllib.request.Request(GITEE_API_URL)
        req.add_header('User-Agent', 'ParentControl/1.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # 获取最新版本号
        latest_version = data.get('tag_name', '').lstrip('v')
        current_version = config.get_version()

        logger.info(f"当前版本: {current_version}, 最新版本: {latest_version}")

        # 比较版本
        if parse_version(current_version) < parse_version(latest_version):
            # 查找 exe 下载链接
            assets = data.get('assets', [])
            for asset in assets:
                if asset.get('name', '').endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    logger.info(f"发现新版本: {latest_version}, 下载URL: {download_url}")
                    return True, download_url

        logger.info("当前已是最新版本")
        return False, None

    except urllib.error.URLError as e:
        logger.error(f"检查更新失败: 网络错误 - {e}")
        return False, None
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        return False, None


def download_update(url: str) -> Optional[str]:
    """下载更新包
    返回: 下载后的文件路径，失败返回 None
    """
    update_dir = get_update_dir()
    dest_path = os.path.join(update_dir, 'ParentControl.exe')

    try:
        logger.info(f"下载更新包: {url}")

        # 检查磁盘空间（简单检查）
        disk = shutil.disk_usage(update_dir)
        if disk.free < 50 * 1024 * 1024:  # 少于50MB
            logger.error("磁盘空间不足")
            return None

        # 下载文件
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ParentControl/1.0')

        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(dest_path + '.tmp', 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

        # 重命名完成
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(dest_path + '.tmp', dest_path)

        logger.info(f"更新包下载成功: {dest_path}")
        return dest_path

    except urllib.error.URLError as e:
        logger.error(f"下载更新失败: 网络错误 - {e}")
        # 清理不完整文件
        if os.path.exists(dest_path + '.tmp'):
            os.remove(dest_path + '.tmp')
        return None
    except Exception as e:
        logger.error(f"下载更新失败: {e}")
        if os.path.exists(dest_path + '.tmp'):
            os.remove(dest_path + '.tmp')
        return None


def apply_pending_update() -> bool:
    """应用待更新的 exe
    返回: 是否成功应用更新
    """
    update_dir = get_update_dir()
    new_exe = os.path.join(update_dir, 'ParentControl.exe')

    if not os.path.exists(new_exe):
        logger.info("没有待更新的文件")
        return False

    try:
        # 获取当前 exe 路径
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            logger.info("开发模式，跳过更新应用")
            return False

        logger.info(f"应用更新: {new_exe} -> {current_exe}")

        # 备份当前 exe
        backup_exe = current_exe + '.bak'
        if os.path.exists(backup_exe):
            os.remove(backup_exe)
        shutil.copy2(current_exe, backup_exe)

        # 替换为新 exe
        shutil.copy2(new_exe, current_exe)

        # 清理更新目录
        os.remove(new_exe)

        logger.info("更新应用成功")
        return True

    except Exception as e:
        logger.error(f"应用更新失败: {e}")
        return False


def run_auto_update():
    """执行自动更新流程"""
    # 1. 先检查并应用待更新
    if apply_pending_update():
        logger.info("已应用上次的更新")

    # 2. 检查新版本
    has_update, download_url = check_for_update()
    if has_update and download_url:
        # 3. 下载更新包
        downloaded = download_update(download_url)
        if downloaded:
            logger.info("更新包已下载，重启后自动应用")
