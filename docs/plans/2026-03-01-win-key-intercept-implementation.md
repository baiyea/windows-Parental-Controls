# Win 键拦截功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在锁屏期间拦截 Win 键，防止用户通过 Win 键切换到其他应用或打开开始菜单。

**Architecture:** 使用 Windows API `SetWindowsHookEx` 键盘钩子，在锁屏时安装钩子拦截 Win 键，锁屏结束时卸载钩子。

**Tech Stack:** Python + ctypes + Windows API (user32.dll)

---

## Task 1: 创建键盘拦截器模块

**Files:**
- Create: `utils/key_interceptor.py`

**Step 1: 创建 key_interceptor.py 文件**

```python
"""键盘拦截器模块 - 使用 Windows 钩子拦截 Win 键"""
import ctypes
import ctypes.wintypes
from ctypes import windll

logger = None


def _get_logger():
    """延迟导入 logger，避免循环依赖"""
    global logger
    if logger is None:
        from utils.logger import get_logger
        logger = get_logger(__name__)
    return logger


class KeyInterceptor:
    """键盘拦截器 - 使用 Windows 钩子拦截 Win 键"""

    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    VK_LWIN = 0x5B  # 左 Win 键
    VK_RWIN = 0x5C  # 右 Win 键

    def __init__(self):
        self.hook_id = None
        self._hook_proc = None
        self._callback_ref = None  # 保持引用防止 GC

    def _keyboard_hook_callback(self, code, wparam, lparam):
        """键盘钩子回调函数"""
        try:
            if code >= 0 and wparam == self.WM_KEYDOWN:
                # 从 lparam 提取虚拟键码
                vk_code = ctypes.wintypes.WPARAM(wparam)
                # 获取实际按键状态
                kb_struct = ctypes.cast(lparam, ctypes.POINTER(ctypes.wintypes.KBDLLHOOKSTRUCT)).contents
                vk_code = kb_struct.vkCode

                # 拦截 Win 键
                if vk_code in (self.VK_LWIN, self.VK_RWIN):
                    _get_logger().debug("拦截到 Win 键")
                    return 1  # 返回 1 阻止按键传递
        except Exception as e:
            _get_logger().error(f"键盘钩子回调错误: {e}")

        return windll.user32.CallNextHookEx(self.hook_id, code, wparam, lparam)

    def start(self):
        """启动键盘拦截"""
        _get_logger().info("启动键盘拦截器")

        # 创建钩子回调函数（需要保持引用）
        self._hook_proc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM
        )(self._keyboard_hook_callback)

        # 保持引用防止 GC
        self._callback_ref = self._hook_proc

        # 安装低级别键盘钩子
        self.hook_id = windll.user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            self._hook_proc,
            None,
            0
        )

        if not self.hook_id:
            error = ctypes.get_last_error()
            _get_logger().error(f"安装键盘钩子失败，错误码: {error}")
            raise RuntimeError(f"Failed to install keyboard hook: {error}")

        _get_logger().info("键盘钩子安装成功")

    def stop(self):
        """停止键盘拦截"""
        if self.hook_id:
            _get_logger().info("卸载键盘钩子")
            windll.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            self._hook_proc = None
            self._callback_ref = None
            _get_logger().info("键盘钩子已卸载")


# KBDLLHOOKSTRUCT 结构定义
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.wintypes.ULONG_PTR)
    ]
```

**Step 2: 提交代码**

```bash
git add utils/key_interceptor.py
git commit -m "feat: 添加键盘拦截器模块"
```

---

## Task 2: 集成键盘拦截到锁屏

**Files:**
- Modify: `ui/lock_screen.py:1-20` - 添加导入
- Modify: `ui/lock_screen.py:10-20` - __init__ 中集成
- Modify: `ui/lock_screen.py:67-82` - destroy/ unlock 中停止拦截

**Step 1: 修改 lock_screen.py - 添加导入**

在文件开头添加：

```python
from utils.key_interceptor import KeyInterceptor
```

**Step 2: 修改 __init__ 方法 - 启动拦截器**

在 `self.root = tk.Tk()` 之后添加：

```python
# 启动键盘拦截器
self.key_interceptor = KeyInterceptor()
self.key_interceptor.start()
```

**Step 3: 修改 auto_unlock 方法 - 停止拦截器**

```python
def auto_unlock(self):
    """倒计时结束后自动解锁"""
    self.key_interceptor.stop()  # 停止拦截
    self.root.destroy()
    if self.on_unlock:
        self.on_unlock()
```

**Step 4: 修改 check_password 方法 - 停止拦截器**

```python
def check_password(self):
    if self.pwd_entry.get() == config.g_config.get("password", "1234"):
        self.key_interceptor.stop()  # 停止拦截
        self.root.destroy()
        self.on_unlock()
    else:
        messagebox.showerror("错误", "密码错误！", parent=self.root)
        self.pwd_entry.delete(0, 'end')
```

**Step 5: 提交代码**

```bash
git add ui/lock_screen.py
git commit -m "feat: 集成键盘拦截到锁屏功能"
```

---

## Task 3: 手动测试验证

**Step 1: 运行程序触发锁屏**

```bash
python main.py
```

**Step 2: 测试场景**

1. 锁屏显示后，按 Win 键 - 应该无法打开开始菜单
2. 按 Win+E、Win+R 等组合键 - 应该无法打开资源管理器/运行对话框
3. 输入正确密码解锁 - 锁屏关闭，Win 键恢复正常

**Step 3: 提交测试结果**

```bash
git commit --allow-empty -m "test: 验证 Win 键拦截功能"
```

---

## 完成

功能实现完成！设计文档已保存在 `docs/plans/2026-03-01-win-key-intercept-design.md`
