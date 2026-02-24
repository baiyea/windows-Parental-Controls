"""密码验证窗口模块"""
import tkinter as tk
from tkinter import messagebox
import config


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
        if self.pwd_entry.get() == config.g_config.get("password", "1234"):
            self.result = True
            self.root.destroy()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')

    def run(self):
        self.root.mainloop()
        return self.result


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
        if self.pwd_entry.get() == config.g_config.get("password", "1234"):
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
