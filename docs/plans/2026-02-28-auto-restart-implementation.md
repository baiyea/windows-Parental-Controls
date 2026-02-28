# 锁屏后自动重启功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在锁屏后 1 分钟自动强制重启计算机，无需任何确认或延迟检测。

**Architecture:** 使用 Windows shutdown 命令实现重启，在状态机进入 LOCKED 状态时启动定时器，用户解锁或程序退出时取消定时器。

**Tech Stack:** Python, subprocess, threading, JSON 配置

---

## Task 1: 更新配置文件和加载逻辑

**Files:**
- Modify: `config.json` (手动编辑)
- Modify: `config.py:30-36`

**Step 1: 更新默认配置**

打开 `config.json`，添加新配置项：

```json
{
    "password": "0829",
    "work_minutes": 30,
    "break_minutes": 30,
    "work_end_time": null,
    "remind_before_minutes": 5,
    "auto_restart_after_lock_seconds": 60
}
```

**Step 2: 更新 config.py 默认配置**

修改 `config.py` 第 30-36 行的 `default_config` 字典：

```python
default_config = {
    "password": "0829",
    "work_minutes": 30,
    "break_minutes": 30,
    "work_end_time": None,
    "remind_before_minutes": 5,
    "auto_restart_after_lock_seconds": 60  # 新增
}
```

**Step 3: 提交**

```bash
git add config.json config.py
git commit -m "feat: 添加 auto_restart_after_lock_seconds 配置项"
```

---

## Task 2: 在控制器中实现自动重启逻辑

**Files:**
- Modify: `core/controller.py:46-56` (添加实例变量)
- Modify: `core/controller.py:348-356` (_on_enter_locked 方法)
- Modify: `core/controller.py:352-356` (_on_exit_locked 方法)
- Modify: `core/controller.py:323-328` (_cleanup 方法)

**Step 1: 添加实例变量**

在 `__init__` 方法中（第 46-56 行附近）添加：

```python
self.restart_timer = None  # 自动重启计时器
```

**Step 2: 修改 _on_enter_locked 方法**

将 `core/controller.py` 第 348-350 行替换为：

```python
def _on_enter_locked(self, **kwargs):
    """进入锁屏状态"""
    logger.info("进入锁屏状态")

    # 启动自动重启计时器
    restart_delay = config.g_config.get('auto_restart_after_lock_seconds', 60)
    if restart_delay > 0:
        self._schedule_restart(restart_delay)
```

**Step 3: 添加 _schedule_restart 方法**

在 `_on_enter_locked` 方法后添加新方法：

```python
def _schedule_restart(self, delay_seconds):
    """安排自动重启"""
    def do_restart():
        import subprocess
        subprocess.run(['shutdown', '/r', '/t', '0', '/f'], check=False)
        logger.info("正在强制重启计算机")

    self._cancel_restart()  # 先取消已有的计时器
    self.restart_timer = threading.Timer(delay_seconds, do_restart)
    self.restart_timer.daemon = True
    self.restart_timer.start()
    logger.info(f"已安排 {delay_seconds} 秒后自动重启")
```

**Step 4: 添加 _cancel_restart 方法**

在 `_schedule_restart` 方法后添加：

```python
def _cancel_restart(self):
    """取消自动重启"""
    if self.restart_timer:
        self.restart_timer.cancel()
        self.restart_timer = None
        logger.info("已取消自动重启")
```

**Step 5: 修改 _on_exit_locked 方法**

在 `_on_exit_locked` 方法开头添加取消重启：

```python
def _on_exit_locked(self, **kwargs):
    """离开锁屏状态"""
    self._cancel_restart()  # 取消自动重启
    config.g_config["break_end_time"] = None
    config.save_config()
    logger.info("离开锁屏状态")
```

**Step 6: 修改 _cleanup 方法**

在 `_cleanup` 方法中添加取消重启：

```python
def _cleanup(self, **kwargs):
    """清理资源"""
    self.running = False
    if self.timer:
        self.timer.cancel()
    self._cancel_restart()  # 取消自动重启
    logger.info("程序退出")
```

**Step 7: 提交**

```bash
git add core/controller.py
git commit -m "feat: 实现锁屏后自动重启功能"
```

---

## Task 3: 测试功能

**Step 1: 运行开发模式测试**

```bash
cd D:/Code/parental-control
uv run main.py
```

观察日志中是否显示：
- 进入锁屏状态时：`已安排 60 秒后自动重启`
- 解锁时：`已取消自动重启`

**Step 2: 手动触发锁屏测试**

1. 等待工作计时结束，或
2. 通过托盘菜单手动锁定

观察 60 秒后是否执行重启。

**Step 3: 提交**

```bash
git commit -m "test: 验证自动重启功能"
```

---

## Task 4: 打包并验证

**Step 1: 打包成 exe**

```powershell
.\build.ps1
```

**Step 2: 验证 exe 运行**

运行 `dist/ParentControl.exe`，检查日志和功能正常。

**Step 3: 最终提交**

```bash
git commit -m "release: 1.5.0 添加锁屏后自动重启功能"
```
