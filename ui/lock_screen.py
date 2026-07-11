"""锁屏窗口模块"""
import tkinter as tk
from tkinter import messagebox
import config
from utils.key_interceptor import KeyInterceptor


class LockScreen:
    """锁屏窗口类"""

    FOCUS_GUARD_INTERVAL_MS = 500

    def __init__(self, on_unlock_callback, is_forced=False, remaining_seconds=None):
        self.root = tk.Tk()
        # 启动键盘拦截器
        self.key_interceptor = KeyInterceptor()
        self.key_interceptor.start()
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='#1a1a2e')
        self.on_unlock = on_unlock_callback
        self.is_forced = is_forced  # 是否强制锁屏（用于区分正常休息）
        self.closed = False
        self._focus_guard_scheduled = False

        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Escape>', lambda e: 'break')
        self.root.bind('<FocusOut>', self.enforce_lock_focus)
        self.root.bind('<Visibility>', self.enforce_lock_focus)

        frame = tk.Frame(self.root, bg='#1a1a2e')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        title = "🔒 强制锁屏" if is_forced else "⏰ 休息时间到！"
        tk.Label(frame, text=title, font=('Microsoft YaHei', 48, 'bold'),
                fg='#e94560', bg='#1a1a2e').pack(pady=20)

        if is_forced:
            tk.Label(frame, text="家长强制锁定",
                    font=('Microsoft YaHei', 20), fg='#ffd700', bg='#1a1a2e').pack()

        # 休息时间：如果 remaining_seconds 为 -1，表示无限期（夜间限制）
        if remaining_seconds is not None and remaining_seconds >= 0:
            self.remaining = remaining_seconds
            self.is_countdown = True
        else:
            self.remaining = 0  # 无限期，不倒计时
            self.is_countdown = False

        # 夜间限制时显示额外提示
        if not self.is_countdown:
            tk.Label(frame, text="⚠️ 夜间限制时段，密码解锁后立即开始工作",
                    font=('Microsoft YaHei', 16), fg='#ff6b6b', bg='#1a1a2e').pack(pady=10)

        self.time_label = tk.Label(frame, text="",
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

        self.update_timer()
        self.enforce_lock_focus()

    def enforce_lock_focus(self, _event=None):
        """持续把锁屏窗口拉回最前，避免被开始菜单或浏览器盖住。"""
        if self.closed:
            return

        try:
            self.root.attributes('-fullscreen', True)
            self.root.attributes('-topmost', True)
            self.root.lift()
            self.root.focus_force()
            self.pwd_entry.focus_force()
        except tk.TclError:
            return

        self._schedule_focus_guard()

    def _schedule_focus_guard(self):
        if self.closed or self._focus_guard_scheduled:
            return
        try:
            self._focus_guard_scheduled = True
            self.root.after(self.FOCUS_GUARD_INTERVAL_MS, self._run_focus_guard)
        except tk.TclError:
            self._focus_guard_scheduled = False

    def _run_focus_guard(self):
        self._focus_guard_scheduled = False
        self.enforce_lock_focus()

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

    def auto_unlock(self):
        """倒计时结束后自动解锁"""
        self.close()
        if self.on_unlock:
            self.on_unlock()

    def check_password(self):
        if self.pwd_entry.get() == config.g_config.get("password", "1234"):
            self.close()
            self.on_unlock()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')

    def close(self):
        """关闭锁屏窗口。可由控制器跨线程请求关闭。"""
        try:
            self.root.after(0, self._close_now)
        except Exception:
            self._close_now()

    def _close_now(self):
        if self.closed:
            return
        self.closed = True
        self.key_interceptor.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()
