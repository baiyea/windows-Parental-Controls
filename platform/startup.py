"""开机启动管理模块"""
import sys
import os
import winreg as reg


def get_exe_path():
    """获取程序路径"""
    return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])


def is_in_startup():
    """检查是否已设置开机启动"""
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, reg.KEY_READ)
        value, _ = reg.QueryValueEx(key, "ParentControl")
        reg.CloseKey(key)
        return value == f'"{get_exe_path()}"'
    except FileNotFoundError:
        return False
    except Exception:
        return False


def add_to_startup():
    """添加开机启动"""
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, reg.KEY_WRITE)
        reg.SetValueEx(key, "ParentControl", 0, reg.REG_SZ, f'"{get_exe_path()}"')
        reg.CloseKey(key)
        return True
    except Exception as e:
        print(f"✗ 添加开机启动失败: {e}")
        return False


def remove_from_startup():
    """移除开机启动"""
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, reg.KEY_WRITE)
        reg.DeleteValue(key, "ParentControl")
        reg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        print(f"✗ 移除开机启动失败: {e}")
        return False


def toggle_startup():
    """切换开机启动状态，返回新状态"""
    if is_in_startup():
        return (remove_from_startup(), False)
    else:
        return (add_to_startup(), True)
