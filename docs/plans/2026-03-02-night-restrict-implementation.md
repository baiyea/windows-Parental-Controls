# 夜间限制功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在锁屏后，如果是晚上9点之后，就不再进行休息倒计时，只能通过密码解锁。

**Architecture:** 在锁屏时检查当前时间，如果是夜间限制时段，则跳过休息倒计时，直接显示密码输入界面。

**Tech Stack:** Python, tkinter, threading

---

### Task 1: 添加配置项

**Files:**
- Modify: `config.py:30-37` (添加默认配置)
- Modify: `config.py:67-73` (确保字段存在)

**Step 1: 添加默认配置项**

在 `config.py` 的 `default_config` 字典中添加：

```python
"restrict_night_hours": {
    "enabled": True,
    "start_hour": 21,
    "end_hour": 6
}
```

**Step 2: 确保配置加载时字段存在**

在 `load_config()` 函数的字段检查部分（约第67-73行）添加：

```python
if "restrict_night_hours" not in g_config:
    g_config["restrict_night_hours"] = {
        "enabled": True,
        "start_hour": 21,
        "end_hour": 6
    }
```

**Step 3: 测试运行**

Run: `cd D:/Code/parental-control && uv run python -c "import config; config.load_config(); print(config.g_config.get('restrict_night_hours'))"`

Expected: 输出 `{'enabled': True, 'start_hour': 21, 'end_hour': 6}`

**Step 4: Commit**

```bash
git add config.py
git commit -m "feat: 添加夜间限制配置项"
```

---

### Task 2: 创建夜间限制时间判断函数

**Files:**
- Create: `utils/night_restrict.py`

**Step 1: 创建工具函数**

创建 `utils/night_restrict.py`:

```python
"""夜间限制工具函数"""
from datetime import datetime
import config
from utils import get_logger

logger = get_logger(__name__)


def is_in_night_restrict_hours():
    """判断当前是否在夜间限制时段"""
    night_config = config.g_config.get("restrict_night_hours", {})

    # 如果未启用，直接返回 False
    if not night_config.get("enabled", False):
        return False

    current_hour = datetime.now().hour
    start_hour = night_config.get("start_hour", 21)
    end_hour = night_config.get("end_hour", 6)

    # 处理跨天情况（如 21:00 到次日 6:00）
    if end_hour > start_hour:
        # 简单情况：21:00-23:00
        return start_hour <= current_hour < end_hour
    else:
        # 跨天情况：21:00-06:00
        return current_hour >= start_hour or current_hour < end_hour
```

**Step 2: 测试函数**

Run: `cd D:/Code/parental-control && uv run python -c "from utils.night_restrict import is_in_night_restrict_hours; print(is_in_night_restrict_hours())"`

Expected: 输出 True 或 False（取决于当前时间）

**Step 3: Commit**

```bash
git add utils/night_restrict.py
git commit -m "feat: 添加夜间限制时间判断函数"
```

---

### Task 3: 修改锁屏逻辑

**Files:**
- Modify: `controller.py:273-308` (_lock_screen 方法)

**Step 1: 修改 _lock_screen 方法**

在 `controller.py` 的 `_lock_screen` 方法中，添加夜间限制检查：

```python
def _lock_screen(self, **kwargs):
    """锁定屏幕"""
    # 检查是否在夜间限制时段
    from utils.night_restrict import is_in_night_restrict_hours
    is_night_restrict = is_in_night_restrict_hours()

    if is_night_restrict:
        # 夜间限制：跳过休息倒计时
        self.break_end_time = None  # 不设置结束时间
        logger.info("夜间限制时段，锁屏不设置休息倒计时")
    else:
        # 正常：计算休息结束时间
        break_minutes = config.g_config.get("break_minutes", 30)
        self.break_end_time = datetime.now() + timedelta(minutes=break_minutes)
        config.g_config["break_end_time"] = self.break_end_time.strftime('%Y-%m-%d %H:%M:%S')
        config.save_config()

    # 显示锁屏
    is_forced = kwargs.get('forced', False)
    remaining_seconds = kwargs.get('remaining_seconds')

    # 夜间限制时传入 -1 表示无限期（只有密码能解锁）
    if is_night_restrict:
        remaining_seconds = -1

    # 设置解锁回调
    self.lock_manager.on_unlock_callback = self._on_unlock_callback

    threading.Thread(
        target=self.lock_manager.show_lock,
        args=(is_forced, remaining_seconds),
        daemon=True
    ).start()

    if is_night_restrict:
        logger.info("夜间限制锁屏开始")
    else:
        logger.info(f"锁屏开始，结束时间: {self.break_end_time.strftime('%H:%M:%S')}")

    # 播放音效
    try:
        winsound.PlaySound(get_audio_path(), winsound.SND_FILENAME)
    except:
        pass

    # 锁屏后立即重启计算机
    if config.g_config.get('auto_restart_after_lock', False):
        import subprocess
        subprocess.run(['shutdown', '/r', '/t', '0', '/f'], check=False)
        logger.info("正在强制重启计算机")
```

**Step 2: Commit**

```bash
git add controller.py
git commit -m "feat: 锁屏时检查夜间限制时段"
```

---

### Task 4: 修改锁屏界面支持无限期模式

**Files:**
- Modify: `ui/lock_screen.py:36-71` (修改倒计时逻辑)

**Step 1: 修改 LockScreen 类**

修改 `ui/lock_screen.py` 中的 `__init__` 和 `update_timer` 方法：

在 `__init__` 中（约第55-60行）修改：

```python
# 休息时间：如果 remaining_seconds 为 -1，表示无限期（夜间限制）
if remaining_seconds is not None and remaining_seconds >= 0:
    self.remaining = remaining_seconds
    self.is_countdown = True
else:
    self.remaining = 0  # 无限期，不倒计时
    self.is_countdown = False
```

修改 `update_timer` 方法（约第62-71行）：

```python
def update_timer(self):
    if self.is_countdown:
        mins, secs = divmod(self.remaining, 60)
        self.time_label.config(text=f"休息倒计时: {mins:02d}:{secs:02d}")
        if self.remaining > 0:
            self.remaining -= 1
            self.root.after(1000, self.update_timer)
        else:
            self.time_label.config(text="✓ 休息完成！", fg='#4ecca3')
            # 自动解锁
            self.root.after(1000, self.auto_unlock)
    else:
        # 无限期模式，显示提示信息
        self.time_label.config(text="夜间限制时段，只能密码解锁", fg='#ff6b6b')
```

在无限期模式下添加一个更明显的提示（约在第28-34行的 title 后面）：

```python
# 夜间限制时显示额外提示
if not self.is_countdown:
    tk.Label(frame, text="⚠️ 夜间限制时段，密码解锁后立即开始工作",
            font=('Microsoft YaHei', 16), fg='#ff6b6b', bg='#1a1a2e').pack(pady=10)
```

**Step 2: 测试运行**

Run: `cd D:/Code/parental-control && uv run python -c "from ui.lock_screen import LockScreen; print('OK')"`

Expected: 无错误输出

**Step 3: Commit**

```bash
git add ui/lock_screen.py
git commit -m "feat: 锁屏界面支持无限期模式"
```

---

### Task 5: 修改休息时间到自动解锁逻辑

**Files:**
- Modify: `controller.py:430-434` (monitor_loop 中检查休息时间)

**Step 1: 修改 monitor_loop**

由于夜间限制时 `break_end_time` 为 None，需要在 monitor_loop 中添加检查：

```python
elif current_state == AppState.LOCKED:
    # 检查休息时间是否到（只在有倒计时时检查）
    if self.break_end_time and datetime.now() >= self.break_end_time:
        self.state_machine.trigger(AppEvent.BREAK_TIME_UP)
        time.sleep(2)
```

由于已经添加了 `if self.break_end_time and`，这个条件在夜间限制时（break_end_time 为 None）不会触发，正好符合需求。

**Step 2: Commit**

```bash
git add controller.py
git commit -m "fix: 夜间限制时跳过休息时间检查"
```

---

### Task 6: 更新默认配置文件

**Files:**
- Modify: `config.json`

**Step 1: 更新 config.json**

```bash
cd D:/Code/parental-control && uv run python -c "import json; c = json.load(open('config.json')); c['restrict_night_hours'] = {'enabled': True, 'start_hour': 21, 'end_hour': 6}; json.dump(c, open('config.json', 'w'), ensure_ascii=False, indent=4)"
```

**Step 2: Commit**

```bash
git add config.json
git commit -m "feat: 更新配置文件添加夜间限制设置"
```

---

### Task 7: 测试完整流程

**Step 1: 启动程序测试**

Run: `cd D:/Code/parental-control && uv run main.py`

测试场景：
1. 正常工作时间后锁屏 -> 验证有30分钟倒计时
2. 在夜间9点后锁屏 -> 验证无倒计时，只能密码解锁

**Step 2: Commit**

```bash
git commit -m "test: 夜间限制功能测试"
```

---

## 完成

所有任务完成后，夜间限制功能将实现以下效果：
- 锁屏时检查当前时间是否在21:00-次日6:00
- 如果是夜间限制时段，不显示休息倒计时，直接显示"夜间限制时段，只能密码解锁"
- 密码解锁后立即开始新的30分钟工作计时
- 可以通过修改 config.json 中的 `restrict_night_hours.enabled` 来开关此功能
