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


# KBDLLHOOKSTRUCT 结构定义
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.wintypes.ULONG_PTR)
    ]


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
                kb_struct = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
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
