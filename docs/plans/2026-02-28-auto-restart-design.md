# 锁屏后自动重启功能设计

## 需求概述

在锁屏后 1 分钟自动强制重启计算机，无需任何确认或延迟检测。

## 实现方案

使用 Windows `shutdown` 命令实现重启：

```bash
shutdown /r /t 60 /f
```

参数说明：
- `/r` — 重启计算机
- `/t 60` — 60 秒后执行（根据需求设置为 60 秒）
- `/f` — 强制关闭正在运行的程序

## 技术设计

### 1. 新增配置项

在 `config.json` 中添加：

```json
{
    "auto_restart_after_lock_seconds": 60
}
```

- 默认值：60 秒
- 可由用户配置

### 2. 修改代码位置

在 `core/state_machine.py` 中，当状态从 `WORKING` 切换到 `LOCKED` 时：

```python
def _on_enter_locked(self):
    """进入锁屏状态时，启动自动重启计时器"""
    restart_delay = self.config.get('auto_restart_after_lock_seconds', 60)
    if restart_delay > 0:
        self._schedule_restart(restart_delay)

def _schedule_restart(self, delay_seconds):
    """安排自动重启"""
    def do_restart():
        import subprocess
        subprocess.run(['shutdown', '/r', '/t', '0', '/f'], check=False)
        logger.info("正在强制重启计算机")

    self._restart_timer = threading.Timer(delay_seconds, do_restart)
    self._restart_timer.start()
    logger.info(f"已安排 {delay_delay} 秒后自动重启")
```

### 3. 取消重启机制

在以下情况需要取消重启：
- 用户输入正确密码解锁时
- 程序正常退出时

```python
def _cancel_restart(self):
    """取消自动重启"""
    if hasattr(self, '_restart_timer') and self._restart_timer:
        self._restart_timer.cancel()
        self._restart_timer = None
        logger.info("已取消自动重启")
```

### 4. 配置更新

在 `config.py` 中添加新配置项的加载逻辑。

## 数据流

```
工作计时结束
    ↓
进入 LOCKED 状态
    ↓
触发 _on_enter_locked()
    ↓
启动 60 秒 Timer
    ↓
    ├─ 用户解锁 → 取消 Timer → 正常继续工作
    └─ 60 秒后 → 执行 shutdown 命令 → 计算机重启
```

## 配置项变更

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| auto_restart_after_lock_seconds | int | 60 | 锁屏后多少秒自动重启（0 表示禁用） |

## 日志记录

- 启动重启计时时记录：`已安排 X 秒后自动重启`
- 取消重启时记录：`已取消自动重启`
- 执行重启时记录：`正在强制重启计算机`
