import tkinter as tk
from tkinter import messagebox
import time
import threading
import sys
import os
from datetime import datetime, timedelta
import pystray
from PIL import Image, ImageDraw
import socket
import atexit
from plyer import notification
import winsound


def get_audio_path():
    """获取音频文件路径，优先使用打包后的音频"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        path = os.path.join(sys._MEIPASS, 'Ring04.wav')
        if os.path.exists(path):
            return path
    # 回退到当前目录或系统默认
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Ring04.wav')
    if os.path.exists(local_path):
        return local_path
    return r"C:\Windows\Media\Ring04.wav"


# ============ 单实例锁 ============
class SingleInstance:
    def __init__(self, port=37429):
        self.port = port
        self.sock = None
        
    def try_lock(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.bind(('127.0.0.1', self.port))
            self.sock.listen(1)
            atexit.register(self.release)
            return True
        except socket.error:
            self.sock.close()
            self.sock = None
            return False
            
    def release(self):
        if self.sock:
            self.sock.close()

# ============ 全局变量 ============
g_controller = None
g_icon = None
g_config = None

def get_config_path():
    """获取配置文件路径（使用程序所在目录）"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe 时，使用 exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发时，使用脚本所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.json')

    # 写日志到文件
    log_path = os.path.join(base_dir, 'parent_control.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as log:
            log.write(f"[DEBUG] 配置文件路径: {config_path}\n")
            log.write(f"[DEBUG] exe所在目录: {base_dir}\n")
            log.write(f"[DEBUG] sys.frozen: {getattr(sys, 'frozen', False)}\n")
    except:
        pass

    print(f"[DEBUG] 配置文件路径: {config_path}")
    print(f"[DEBUG] exe所在目录: {base_dir}")
    print(f"[DEBUG] sys.frozen: {getattr(sys, 'frozen', False)}")
    return config_path

# ============ 加载配置 ============
def load_config():
    global g_config
    config_path = get_config_path()
    default_config = {"password": "0829", "work_minutes": 30, "break_minutes": 30, "work_end_time": None, "remind_before_minutes": 5}

    # 写日志
    def write_log(msg):
        log_path = os.path.join(os.path.dirname(config_path), 'parent_control.log')
        try:
            with open(log_path, 'a', encoding='utf-8') as log:
                log.write(f"{msg}\n")
        except:
            pass
        print(msg)

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        write_log(f"[{datetime.now().strftime('%H:%M:%S')}] 配置文件不存在，准备创建...")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            write_log(f"[{datetime.now().strftime('%H:%M:%S')}] 已创建默认配置文件: {config_path}")
        except Exception as e:
            write_log(f"[ERROR] 创建配置文件失败: {e}")
            write_log(f"[ERROR] 尝试在用户目录创建...")
            # 备用方案：尝试在用户目录创建
            try:
                backup_path = os.path.join(os.path.expanduser("~"), "parental_control_config.json")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(default_config, f, ensure_ascii=False, indent=4)
                write_log(f"[{datetime.now().strftime('%H:%M:%S')}] 已创建备用配置文件: {backup_path}")
                return g_config
            except Exception as e2:
                write_log(f"[ERROR] 创建备用配置文件也失败: {e2}")

    # 加载配置
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            g_config = json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}, 使用默认配置")
        g_config = default_config

    # 确保必要字段存在
    if "work_end_time" not in g_config:
        g_config["work_end_time"] = None
    # 锁屏结束时间
    if "break_end_time" not in g_config:
        g_config["break_end_time"] = None

    return g_config


def save_config():
    """保存当前配置到 config.json"""
    global g_config
    config_path = get_config_path()
    try:
        import json
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(g_config, f, ensure_ascii=False, indent=4)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 配置已保存")
    except Exception as e:
        print(f"保存配置失败: {e}")

# ============ 锁屏窗口 ============
class LockScreen:
    def __init__(self, on_unlock_callback, is_forced=False, remaining_seconds=None):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='#1a1a2e')
        self.on_unlock = on_unlock_callback
        self.is_forced = is_forced  # 是否强制锁屏（用于区分正常休息）

        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Escape>', lambda e: 'break')

        frame = tk.Frame(self.root, bg='#1a1a2e')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        title = "🔒 强制锁屏" if is_forced else "⏰ 休息时间到！"
        tk.Label(frame, text=title, font=('Microsoft YaHei', 48, 'bold'),
                fg='#e94560', bg='#1a1a2e').pack(pady=20)

        if is_forced:
            tk.Label(frame, text="家长强制锁定",
                    font=('Microsoft YaHei', 20), fg='#ffd700', bg='#1a1a2e').pack()

        self.time_label = tk.Label(frame, text="休息倒计时: 30:00",
                                  font=('Microsoft YaHei', 20), fg='#4ecca3', bg='#1a1a2e')
        self.time_label.pack(pady=10)

        pwd_frame = tk.Frame(frame, bg='#1a1a2e')
        pwd_frame.pack(pady=30)

        tk.Label(pwd_frame, text="输入密码解锁:", font=('Microsoft YaHei', 16),
                fg='#eaeaea', bg='#1a1a2e').pack(side='left', padx=10)

        self.pwd_entry = tk.Entry(pwd_frame, show='●', font=('Arial', 16), width=15)
        self.pwd_entry.pack(side='left')
        self.pwd_entry.bind('<Return>', lambda e: self.check_password())
        self.pwd_entry.focus()

        tk.Button(pwd_frame, text="解锁", command=self.check_password,
                 font=('Microsoft YaHei', 12), bg='#e94560', fg='white',
                 padx=20, pady=5).pack(side='left', padx=10)

        # 休息时间：如果传入了剩余秒数则使用，否则从配置读取
        if remaining_seconds is not None:
            self.remaining = remaining_seconds
        else:
            self.remaining = g_config.get("break_minutes", 5) * 60
        self.update_timer()
        
    def update_timer(self):
        mins, secs = divmod(self.remaining, 60)
        self.time_label.config(text=f"休息倒计时: {mins:02d}:{secs:02d}")
        if self.remaining > 0:
            self.remaining -= 1
            self.root.after(1000, self.update_timer)
        else:
            self.time_label.config(text="✓ 休息完成！", fg='#4ecca3')
            # 自动解锁
            self.root.after(1000, self.auto_unlock)

    def auto_unlock(self):
        """倒计时结束后自动解锁"""
        self.root.destroy()
        if self.on_unlock:
            self.on_unlock()
            
    def check_password(self):
        if self.pwd_entry.get() == g_config.get("password", "1234"):
            self.root.destroy()
            self.on_unlock()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')
            
    def run(self):
        self.root.mainloop()

# ============ 退出验证窗口 ============
class ExitConfirm:
    """退出前密码验证"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("验证")
        self.root.geometry("300x150")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#2d2d44')
        
        self.result = False
        
        tk.Label(self.root, text="输入密码退出程序:", 
                font=('Microsoft YaHei', 12), fg='white', bg='#2d2d44').pack(pady=15)
        
        self.pwd_entry = tk.Entry(self.root, show='●', font=('Arial', 12), width=20)
        self.pwd_entry.pack()
        self.pwd_entry.bind('<Return>', lambda e: self.check())
        self.pwd_entry.focus()
        
        btn_frame = tk.Frame(self.root, bg='#2d2d44')
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="确认", command=self.check,
                 bg='#e94560', fg='white', width=8).pack(side='left', padx=5)
        tk.Button(btn_frame, text="取消", command=self.cancel,
                 bg='#666', fg='white', width=8).pack(side='left', padx=5)
        
    def check(self):
        if self.pwd_entry.get() == g_config.get("password", "1234"):
            self.result = True
            self.root.destroy()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')
            
    def cancel(self):
        self.root.destroy()
        
    def run(self):
        self.root.mainloop()
        return self.result

# ============ 通用密码验证窗口 ============
class PasswordConfirm:
    """通用密码验证窗口"""
    def __init__(self, title="验证"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("300x120")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#2d2d44')

        self.result = False

        tk.Label(self.root, text="输入密码确认操作:",
                font=('Microsoft YaHei', 12), fg='white', bg='#2d2d44').pack(pady=15)

        self.pwd_entry = tk.Entry(self.root, show='●', font=('Arial', 12), width=20)
        self.pwd_entry.pack()
        self.pwd_entry.bind('<Return>', lambda e: self.check())
        self.pwd_entry.focus()

        btn_frame = tk.Frame(self.root, bg='#2d2d44')
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="确认", command=self.check,
                 bg='#4ecca3', fg='white', width=8).pack()

    def check(self):
        if self.pwd_entry.get() == g_config.get("password", "1234"):
            self.result = True
            self.root.destroy()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')

    def run(self):
        self.root.mainloop()
        return self.result

# ============ 托盘图标 ============
def create_tray_image():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(img)
        dc.ellipse([2, 2, 62, 62], fill='#e94560', outline='#ff6b6b', width=2)
        dc.rectangle([30, 10, 34, 34], fill='white')
        dc.rectangle([30, 30, 48, 34], fill='white')
        dc.ellipse([26, 26, 38, 38], fill='white')
        return img

def on_tray_clicked(icon, item):
    """托盘菜单点击处理"""
    global g_controller
    text = str(item)

    if text == "🔒 立即锁屏" and g_controller:
        g_controller.force_lock()

    elif text == "🚪 退出":
        # 先验证密码
        if g_controller and g_controller.confirm_exit():
            icon.stop()
            if g_controller:
                g_controller.running = False
            os._exit(0)

    elif "开机启动" in text:
        # 弹出密码验证窗口
        if PasswordConfirm("开机启动").run():
            _, new_state = toggle_startup()
            # 刷新托盘菜单显示新状态
            g_controller.refresh_tray_menu()
        return

def get_tray_menu():
    global g_controller
    if not g_controller:
        return pystray.Menu(
            pystray.MenuItem("启动中...", lambda icon, item: None, enabled=False),
            pystray.MenuItem("退出", on_tray_clicked),
        )

    # 检查开机启动状态
    startup_status = "✓ 开机启动" if is_in_startup() else "✗ 开机启动"

    return pystray.Menu(
        pystray.MenuItem(
            f"⏱ {g_controller.get_remaining_time()}",
            lambda icon, item: None, enabled=False
        ),
        pystray.MenuItem("🔒 立即锁屏", on_tray_clicked, enabled=not g_controller.lock_manager.lock_screen),
        pystray.MenuItem("─", lambda icon, item: None, enabled=False),
        pystray.MenuItem(startup_status, on_tray_clicked),
        pystray.MenuItem("🚪 退出", on_tray_clicked),
    )

# ============ 锁屏管理 ============
class LockScreenManager:
    """在独立线程中管理锁屏"""
    def __init__(self):
        self.lock_screen = None
        self.on_unlock_callback = None

    def show_lock(self, forced=False, remaining_seconds=None):
        """在新线程中显示锁屏"""
        if self.lock_screen:
            return

        # 计算锁屏结束时间并保存
        break_end_time = datetime.now() + timedelta(minutes=g_config.get("break_minutes", 5))
        g_config["break_end_time"] = break_end_time.strftime('%Y-%m-%d %H:%M:%S')
        save_config()

        self.lock_screen = LockScreen(self.on_break_complete, is_forced=forced, remaining_seconds=remaining_seconds)
        self.lock_screen.run()

    def on_break_complete(self):
        """解锁回调"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 解锁")
        self.lock_screen = None
        # 清除锁屏状态
        g_config["break_end_time"] = None
        save_config()
        if self.on_unlock_callback:
            self.on_unlock_callback()

# ============ 主控制器 ============
class ParentControl:
    def __init__(self):
        global g_controller
        g_controller = self

        self.running = True
        self.work_end_time = None
        self.lock_manager = LockScreenManager()
        self.force_lock_flag = threading.Event()
        self.remind_shown = False
        # 使用 plyer 发送通知

    def get_remaining_time(self):
        if self.lock_manager.lock_screen:
            return "休息中"
        if not self.work_end_time:
            return "00:00"
        remaining = self.work_end_time - datetime.now()
        if remaining.total_seconds() <= 0:
            return "00:00"
        mins, secs = divmod(int(remaining.total_seconds()), 60)
        return f"{mins:02d}:{secs:02d}"

    def start(self):
        # 重置提醒状态
        self.remind_shown = False

        # 检查是否在锁屏期间（重启后恢复锁屏）
        break_end_time = g_config.get("break_end_time")
        if break_end_time:
            try:
                break_end = datetime.strptime(break_end_time, '%Y-%m-%d %H:%M:%S')
                now = datetime.now()

                if now < break_end:
                    # 仍在锁屏期间，计算剩余时间
                    remaining_seconds = int((break_end - now).total_seconds())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检测到未完成的锁屏期间，剩余 {remaining_seconds} 秒，正在恢复锁屏...")
                    # 设置解锁回调
                    self.lock_manager.on_unlock_callback = self.on_break_complete
                    # 在新线程显示锁屏，传入剩余时间
                    threading.Thread(target=self.lock_manager.show_lock, args=(False, remaining_seconds), daemon=True).start()
                    # 等待锁屏显示
                    time.sleep(3)
                else:
                    # 锁屏期间已过，清除状态
                    g_config["break_end_time"] = None
                    save_config()
            except (ValueError, TypeError):
                g_config["break_end_time"] = None
                save_config()

        # 尝试从配置中恢复工作结束时间
        saved_end_time = g_config.get("work_end_time")
        if saved_end_time:
            try:
                saved_time = datetime.strptime(saved_end_time, '%Y-%m-%d %H:%M:%S')
                # 如果保存的时间在未来，则继续使用
                if saved_time > datetime.now():
                    self.work_end_time = saved_time
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 恢复计时，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
                else:
                    # 时间已过期，创建新的计时
                    work_minutes = g_config.get("work_minutes", 30)
                    self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
                    g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
                    save_config()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
            except (ValueError, TypeError):
                # 解析失败，创建新的计时
                work_minutes = g_config.get("work_minutes", 30)
                self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
                g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
                save_config()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
        else:
            # 没有保存的时间，创建新的计时
            work_minutes = g_config.get("work_minutes", 30)
            self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
            g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
            save_config()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动，可用至 {self.work_end_time.strftime('%H:%M:%S')}")

        # 设置解锁回调
        self.lock_manager.on_unlock_callback = self.on_break_complete

        # 启动后台线程
        threading.Thread(target=self.monitor_loop, daemon=True).start()
        threading.Thread(target=self.refresh_tray_loop, daemon=True).start()

        # 主线程运行托盘
        global g_icon
        g_icon = pystray.Icon(
            "ParentControl",
            create_tray_image(),
            "家长控制 - 运行中",
            get_tray_menu(),
        )

        g_icon.run(self.on_tray_ready)

    def on_tray_ready(self, icon):
        global g_icon
        g_icon = icon
        icon.visible = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 托盘已激活")

    def refresh_tray_loop(self):
        global g_icon
        while self.running:
            time.sleep(1)
            if g_icon and self.running:
                try:
                    g_icon.menu = get_tray_menu()
                    g_icon.title = f"家长控制 - {self.get_remaining_time()}"
                except Exception as e:
                    print(f"刷新失败: {e}")

    def monitor_loop(self):
        """监控循环 - 同时检测时间和强制锁屏信号"""
        while self.running:
            # 检查强制锁屏信号
            if self.force_lock_flag.is_set() and not self.lock_manager.lock_screen:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 执行强制锁屏")
                self.force_lock_flag.clear()
                threading.Thread(target=self.lock_manager.show_lock, args=(True,), daemon=True).start()
                time.sleep(2)
                continue

            # 检查提前提醒
            if self.work_end_time and not self.lock_manager.lock_screen:
                remaining = self.work_end_time - datetime.now()
                remaining_minutes = remaining.total_seconds() / 60
                remind_before_minutes = g_config.get("remind_before_minutes", 5)

                # 调试输出
                if remaining_minutes <= remind_before_minutes + 1:
                    print(f"[DEBUG] remaining_minutes={remaining_minutes:.1f}, remind_before={remind_before_minutes}, remind_shown={self.remind_shown}")

                if 0 < remaining_minutes <= remind_before_minutes and not self.remind_shown:
                    self.remind_shown = True
                    try:
                        notification.notify(
                            title="家长控制提醒",
                            message=f"距离锁屏还剩 {int(remaining_minutes)} 分钟，请保存工作！",
                            timeout=5
                        )
                        winsound.PlaySound(get_audio_path(), winsound.SND_FILENAME)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 已发送提前提醒")
                    except Exception as e:
                        print(f"发送提醒失败: {e}")

            # 检查正常时间到
            now = datetime.now()
            if now >= self.work_end_time and not self.lock_manager.lock_screen:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 时间到，锁屏")
                winsound.PlaySound(get_audio_path(), winsound.SND_FILENAME)
                threading.Thread(target=self.lock_manager.show_lock, args=(False,), daemon=True).start()
                time.sleep(2)

            time.sleep(1)

    def on_break_complete(self):
        """休息完成，重新计时"""
        work_minutes = g_config.get("work_minutes", 30)
        self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
        g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
        self.remind_shown = False
        save_config()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 重新计时，可用至 {self.work_end_time.strftime('%H:%M:%S')}")

    def force_lock(self):
        """触发强制锁屏（线程安全）"""
        if not self.lock_manager.lock_screen:
            self.force_lock_flag.set()

    def confirm_exit(self):
        """退出验证"""
        # 如果正在锁屏，直接拒绝退出
        if self.lock_manager.lock_screen:
            messagebox.showwarning("提示", "休息期间不能退出程序！")
            return False
        # 显示密码验证窗口
        return ExitConfirm().run()

    def exit_app(self):
        self.running = False
        global g_icon
        if g_icon:
            g_icon.stop()

    def refresh_tray_menu(self):
        """刷新托盘菜单"""
        global g_icon
        if g_icon:
            g_icon.menu = get_tray_menu()

# ============ 开机启动 ============
def get_exe_path():
    """获取程序路径"""
    return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])

def is_in_startup():
    """检查是否已设置开机启动"""
    import winreg as reg
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
    import winreg as reg
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
    import winreg as reg
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

# ============ 主入口 ============
if __name__ == "__main__":
    load_config()  # 加载配置
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    
    if args.install:
        add_to_startup()
        sys.exit(0)
    
    locker = SingleInstance()
    if not locker.try_lock():
        print("程序已在运行")
        tk.Tk().withdraw()
        messagebox.showinfo("家长控制", "程序已经在运行！")
        sys.exit(0)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 单实例锁检查通过")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 家长控制启动...")
    app = ParentControl()
    app.start()