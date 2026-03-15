# 自动更新功能设计

## 概述

新增自动更新功能，在程序启动时自动检查 Gitee releases 是否有新版本，静默下载更新包，下次重启时自动替换。

## 需求

1. 程序启动时自动检查更新
2. 静默下载更新包，不打扰用户
3. 下载完成后记录待更新状态，下次重启自动替换
4. 更新失败不影响当前程序运行

## 技术方案

### API 调用

- **URL**: `https://gitee.com/api/v5/repos/degao/parental-control/releases/latest`
- **方法**: GET
- **响应示例**:
```json
{
  "tag_name": "v1.7.01",
  "assets": [
    {
      "name": "ParentControl.exe",
      "browser_download_url": "https://gitee.com/.../ParentControl.exe"
    }
  ]
}
```

### 版本比较

- 当前版本从 `pyproject.toml` 读取（已有 `config.get_version()` 函数）
- API 返回的版本号格式为 `v1.7.01`，需要去掉前缀 `v` 再比较
- 比较逻辑：`current_version < latest_version` 时有新版本

### 打包后版本号获取

- 打包时在 `build.sh` 中将版本号写入 `dist/version.txt`
- `config.get_version()` 优先读取 `version.txt`，若无则读取 `pyproject.toml`
- build.sh 需要在打包成功后添加：`echo "$NEW_VERSION" > dist/version.txt`

### 核心流程

```
启动 → 检查更新 → 有新版本? → 下载到临时目录 → 记录待更新状态 → 重启时替换
```

## 新增模块

### `utils/updater.py`

```python
def check_for_update() -> tuple[bool, str]:
    """检查是否有新版本
    返回: (是否有新版本, 新版本下载URL)
    """

def download_update(url: str, dest_path: str) -> bool:
    """下载更新包
    返回: 是否下载成功
    """

def apply_update(exe_path: str) -> bool:
    """应用更新，替换当前 exe
    返回: 是否替换成功
    """
```

### 配置项 (config.json)

```json
{
  "auto_update": {
    "enabled": true,
    "last_check_time": null
  }
}
```

## 更新文件位置

- **开发模式**: 下载到项目目录下的 `update/` 文件夹
- **打包模式**: 下载到 `exe所在目录/update/`

## 重启更新流程

1. 程序启动时检查 `update/` 目录是否有待更新的 exe
2. 如果有，备份当前 exe，替换为新 exe
3. 记录更新完成，清空 update 目录

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 网络请求失败 | 记录日志（error级别），忽略，继续运行 |
| 下载失败 | 记录日志，删除不完整文件，忽略，继续运行 |
| 替换失败 | 记录详细错误，下次再试 |
| 磁盘空间不足 | 下载前检查可用空间，不足则跳过 |

## 测试点

1. API 请求成功/失败场景
2. 版本号比较（当前版本 < 最新版本）
3. 下载过程中断场景
4. 重启后替换成功/失败场景
