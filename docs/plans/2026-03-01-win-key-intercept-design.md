# Win 键拦截功能设计文档

## 1. 背景与目标

### 问题描述
当前锁屏功能使用 tkinter 的 `-fullscreen` 和 `-topmost` 属性实现全屏置顶，但无法拦截系统级按键（如 Win 键）。用户在锁屏状态下仍可按 Win 键打开 Windows 开始菜单，存在安全漏洞。

### 目标
在锁屏期间拦截 Win 键，防止用户通过 Win 键切换到其他应用或打开开始菜单。

---

## 2. 技术方案

### 方案选择
使用 Windows API `SetWindowsHookEx` 键盘钩子拦截 Win 键。

**选择理由：**
- 无需管理员权限
- 能拦截所有按键，包括 Win 键（LWin=0x5B, RWin=0x5C）
- 兼容性好，不影响其他应用程序

### 实现原理
1. 锁屏启动时，安装低级别键盘钩子（WH_KEYBOARD_LL = 13）
2. 钩子回调函数检测按键是否为 Win 键
3. 如果是 Win 键，返回 1 阻止按键事件传递
4. 锁屏结束时卸载钩子

---

## 3. 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                      锁屏流程                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   LockScreen.__init__()                                 │
│        │                                                │
│        ▼                                                │
│   KeyInterceptor.start()  ──► 安装键盘钩子              │
│        │                                                │
│        ▼                                                │
│   锁屏显示，用户无法按 Win 键                            │
│        │                                                │
│        ▼                                                │
│   LockScreen.destroy()                                  │
│        │                                                │
│        ▼                                                │
│   KeyInterceptor.stop()   ──► 卸载键盘钩子              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 文件结构
```
parental-control/
├── utils/
│   └── key_interceptor.py    # 新增：键盘拦截器
└── ui/
    └── lock_screen.py        # 修改：集成键盘拦截
```

---

## 4. 核心实现

### 4.1 KeyInterceptor 类

```python
import ctypes
import ctypes.wintypes
from ctypes import windll

class KeyInterceptor:
    """键盘拦截器 - 使用 Windows 钩子拦截 Win 键"""

    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    VK_LWIN = 0x5B  # 左 Win 键
    VK_RWIN = 0x5C  # 右 Win 键

    def __init__(self):
        self.hook_id = None
        self.hook_proc = None

    def _keyboard_hook_callback(self, code, wparam, lparam):
        """键盘钩子回调函数"""
        if code >= 0 and wparam == self.WM_KEYDOWN:
            vk_code = ctypes.wintypes.DWORD.from_address(lparam).value
            # 拦截 Win 键
            if vk_code in (self.VK_LWIN, self.VK_RWIN):
                return 1  # 返回 1 阻止按键传递
        return windll.user32.CallNextHookEx(self.hook_id, code, wparam, lparam)

    def start(self):
        """启动键盘拦截"""
        # 创建钩子回调函数（需要保持引用）
        self.hook_proc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM
        )(self._keyboard_hook_callback)

        # 安装低级别键盘钩子
        self.hook_id = windll.user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            self.hook_proc,
            None,
            0
        )

    def stop(self):
        """停止键盘拦截"""
        if self.hook_id:
            windll.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
```

### 4.2 锁屏集成

在 `ui/lock_screen.py` 中：

```python
from utils.key_interceptor import KeyInterceptor

class LockScreen:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.key_interceptor = KeyInterceptor()
        self.key_interceptor.start()

    def run(self):
        self.root.mainloop()

    def auto_unlock(self):
        self.key_interceptor.stop()  # 停止拦截
        self.root.destroy()
        if self.on_unlock:
            self.on_unlock()

    def check_password(self):
        self.key_interceptor.stop()  # 停止拦截
        self.root.destroy()
        self.on_unlock()
```

---

## 5. 边界情况处理

| 场景 | 处理方式 |
|------|----------|
| 用户通过任务管理器结束进程 | 进程结束后钩子自动卸载 |
| 程序异常退出 | 钩子可能残留，但重启后恢复 |
| 多显示器环境 | 只在主屏幕显示锁屏，Win 键在所有显示器均被拦截 |
| 其他组合键（如 Win+D） | 会被一起拦截，这是预期行为 |

---

## 6. 测试要点

1. **功能测试**
   - 锁屏状态下按 Win 键无法打开开始菜单
   - 锁屏状态下按 Win+E、Win+R 等组合键无法工作
   - 正确输入密码后锁屏解除，Win 键恢复正常

2. **兼容性测试**
   - 在不同分辨率下全屏显示正常
   - 与其他键盘钩子应用共存（如键盘改键软件）

---

## 7. 风险与限制

- **局限**：无法拦截 `Ctrl+Alt+Delete` 组合键（由系统处理）
- **局限**：理论上可通过屏幕键盘绕过，但实际使用中概率极低
- **风险**：如果钩子回调函数执行时间过长会影响系统响应，需保持轻量
