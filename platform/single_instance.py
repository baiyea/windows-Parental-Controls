"""单实例锁模块"""
import atexit
import ctypes
import ctypes.wintypes


ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    """单实例锁类，确保程序只运行一个实例"""

    def __init__(self, port=37429):
        self.port = port
        self.handle = None
        self.mutex_name = "Local\\ParentControl.SingleInstance"

    def try_lock(self):
        """尝试获取锁"""
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            ctypes.wintypes.BOOL,
            ctypes.wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
        kernel32.GetLastError.restype = ctypes.wintypes.DWORD
        kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
        kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

        handle = kernel32.CreateMutexW(None, False, self.mutex_name)
        if not handle:
            return False

        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self.handle = handle
        atexit.register(self.release)
        return True

    def release(self):
        """释放锁"""
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
