# 版本号显示问题修复计划

## 问题分析

### 问题 1: 版本号始终显示 1.7.00

**原因**: `dist/version.txt` 没有被保留在打包产物中

日志显示:
```
当前版本: 1.7.00, 最新版本: 1.7.11
```

config.py 中的 `get_version()` 函数：
1. 优先读取 `exe同目录/version.txt`
2. 找不到则 fallback 到 pyproject.toml
3. 再找不到则返回默认值 `'1.7.00'`

### 问题 2: 自动更新替换 exe 失败

**原因**: 程序正在运行时无法替换自身

日志显示:
```
[WinError 32] 另一个程序正在使用此文件，进程无法访问
```

---

## 修复方案

### 修复 1: 确保 version.txt 在 exe 同目录下

**方案**: 在 `apply_pending_update()` 函数中，更新 exe 后同时更新/创建 version.txt

修改 `utils/updater.py`:
- 创建 update.bat 脚本来替换 exe
- update.bat 中同时写入新的 version.txt

### 修复 2: 自动更新使用重启机制

**方案**: 创建一个更新脚本，程序退出后由外部脚本替换 exe

工作流程：
1. 程序启动时检查是否有 update.bat
2. 如果有，执行 update.bat 后退出
3. update.bat 替换 exe、写入 version.txt、重启程序
4. 如果有待下载的新版本，下载后提示用户重启

---

## 关键文件修改

| 文件 | 修改内容 |
|------|----------|
| `utils/updater.py` | apply_pending_update() 创建 update.bat 脚本 |
| `utils/updater.py` | run_auto_update() 返回更新状态 |
| `main.py` | 检查并执行 update.bat |
| `main.py` | 处理更新完成提示用户重启 |

---

## 验证方式

1. 手动在 dist 目录创建 version.txt，内容为 "1.7.11"
2. 运行程序，检查托盘图标版本号显示是否正确
3. 模拟自动更新流程，验证 version.txt 是否被正确更新
4. 构建新版本，验证更新机制正常工作

---

## 实施日期

2026-03-17
