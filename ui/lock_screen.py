"""锁屏窗口模块"""
import tkinter as tk
from tkinter import messagebox
import config
from utils.key_interceptor import KeyInterceptor


class LockScreen:
    """锁屏窗口类"""

    def __init__(self, on_unlock_callback, is_forced=False, remaining_seconds=None):
        self.root = tk.Tk()
        # 启动键盘拦截器
        self.key_interceptor = KeyInterceptor()
        self.key_interceptor.start()
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
            self.remaining = config.g_config.get("break_minutes", 5) * 60
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
        self.key_interceptor.stop()  # 停止拦截
        self.root.destroy()
        if self.on_unlock:
            self.on_unlock()

    def check_password(self):
        if self.pwd_entry.get() == config.g_config.get("password", "1234"):
            self.key_interceptor.stop()  # 停止拦截
            self.root.destroy()
            self.on_unlock()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')

    def run(self):
        self.root.mainloop()
