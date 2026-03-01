"""密码验证窗口模块 - 现代液态玻璃效果"""
import tkinter as tk
from tkinter import messagebox
import config


class PasswordConfirm:
    """通用密码验证窗口 - 带玻璃效果"""

    def __init__(self, title="验证"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("320x150")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True, '-alpha', 0.95)
        self.root.configure(bg='#1a1a2e')

        # 移除窗口装饰
        self.root.overrideredirect(True)

        self.result = False

        # 创建画布背景
        self.canvas = tk.Canvas(self.root, width=320, height=150,
                                highlightthickness=0, bg='#1a1a2e')
        self.canvas.pack(fill='both', expand=True)

        # 绘制渐变背景
        self._draw_gradient_background()

        # 主容器
        main_frame = tk.Frame(self.canvas, bg='transparent')
        main_frame.place(relx=0.5, rely=0.5, anchor='center', width=280, height=120)

        # 标题标签
        tk.Label(main_frame, text="🔐 输入密码确认操作:",
                font=('Microsoft YaHei', 13, 'bold'), fg='#ffffff', bg='transparent').pack(pady=10)

        # 密码输入框
        input_frame = tk.Frame(main_frame, bg='transparent')
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="🔑", font=('Arial', 14),
                fg='#4ecca3', bg='transparent').pack(side='left', padx=5)

        self.pwd_entry = tk.Entry(input_frame, show='●', font=('Arial', 14), width=16,
                                  bg='rgba(255, 255, 255, 0.1)', fg='#ffffff',
                                  insertbackground='#4ecca3', relief='flat',
                                  highlightthickness=1, highlightbackground='#4ecca3',
                                  highlightcolor='#e94560')
        self.pwd_entry.pack(side='left', padx=5)
        self.pwd_entry.bind('<Return>', lambda e: self.check())
        self.pwd_entry.focus()

        # 按钮
        btn = self._create_glass_button(main_frame, "✓ 确认", self.check, '#4ecca3', '#66ffaa')
        btn.pack(pady=15)

        # 绑定拖动
        self._make_draggable()

    def _draw_gradient_background(self):
        """绘制渐变背景"""
        colors = ['#1a1a2e', '#2d2d44', '#3d2d44', '#2d2d44', '#1a1a2e']
        height = 150
        step = height // len(colors)

        for i, color in enumerate(colors):
            y1 = i * step
            y2 = (i + 1) * step
            self.canvas.create_rectangle(0, y1, 320, y2, fill=color, outline=color)

        # 添加装饰光晕
        self.canvas.create_oval(250, -20, 340, 70, outline='#4ecca3', width=2, stipple='gray20')
        self.canvas.create_oval(-30, 80, 50, 170, outline='#e94560', width=2, stipple='gray15')

    def _create_glass_button(self, parent, text, command, bg_color, highlight_color):
        """创建玻璃质感按钮"""
        btn = tk.Button(parent, text=text, command=command,
                       font=('Microsoft YaHei', 12, 'bold'),
                       bg=bg_color, fg='#1a1a2e',
                       activebackground=highlight_color,
                       activeforeground='#1a1a2e',
                       relief='raised', bd=0,
                       padx=30, pady=8,
                       cursor='hand2',
                       highlightthickness=2,
                       highlightbackground='rgba(255,255,255,0.2)')

        def on_enter(e):
            e.widget.config(bg=highlight_color)
        def on_leave(e):
            e.widget.config(bg=bg_color)

        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        return btn

    def _make_draggable(self):
        """使窗口可拖动"""
        def on_mouse_press(event):
            self.root._drag_start_x = event.x
            self.root._drag_start_y = event.y

        def on_mouse_drag(event):
            x = self.root.winfo_x() - self.root._drag_start_x + event.x
            y = self.root.winfo_y() - self.root._drag_start_y + event.y
            self.root.geometry(f"+{x}+{y}")

        self.canvas.bind('<ButtonPress-1>', on_mouse_press)
        self.canvas.bind('<B1-Motion>', on_mouse_drag)

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
    """退出前密码验证 - 带玻璃效果"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("验证")
        self.root.geometry("320x180")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True, '-alpha', 0.95)
        self.root.configure(bg='#1a1a2e')

        # 移除窗口装饰
        self.root.overrideredirect(True)

        self.result = False

        # 创建画布背景
        self.canvas = tk.Canvas(self.root, width=320, height=180,
                                highlightthickness=0, bg='#1a1a2e')
        self.canvas.pack(fill='both', expand=True)

        # 绘制渐变背景
        self._draw_gradient_background()

        # 主容器
        main_frame = tk.Frame(self.canvas, bg='transparent')
        main_frame.place(relx=0.5, rely=0.5, anchor='center', width=280, height=150)

        # 标题标签
        tk.Label(main_frame, text="🚪 输入密码退出程序:",
                font=('Microsoft YaHei', 13, 'bold'), fg='#ffffff', bg='transparent').pack(pady=10)

        # 密码输入框
        input_frame = tk.Frame(main_frame, bg='transparent')
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="🔑", font=('Arial', 14),
                fg='#e94560', bg='transparent').pack(side='left', padx=5)

        self.pwd_entry = tk.Entry(input_frame, show='●', font=('Arial', 14), width=16,
                                  bg='rgba(255, 255, 255, 0.1)', fg='#ffffff',
                                  insertbackground='#e94560', relief='flat',
                                  highlightthickness=1, highlightbackground='#e94560',
                                  highlightcolor='#4ecca3')
        self.pwd_entry.pack(side='left', padx=5)
        self.pwd_entry.bind('<Return>', lambda e: self.check())
        self.pwd_entry.focus()

        # 按钮组
        btn_frame = tk.Frame(main_frame, bg='transparent')
        btn_frame.pack(pady=15)

        confirm_btn = self._create_glass_button(btn_frame, "✓ 确认", self.check, '#e94560', '#ff6b6b')
        confirm_btn.pack(side='left', padx=10)

        cancel_btn = self._create_glass_button(btn_frame, "✗ 取消", self.cancel, '#4a4a5a', '#6a6a7a')
        cancel_btn.pack(side='left', padx=10)

        # 绑定拖动
        self._make_draggable()

    def _draw_gradient_background(self):
        """绘制渐变背景"""
        colors = ['#1a1a2e', '#2d2d44', '#3d2d44', '#2d2d44', '#1a1a2e']
        height = 180
        step = height // len(colors)

        for i, color in enumerate(colors):
            y1 = i * step
            y2 = (i + 1) * step
            self.canvas.create_rectangle(0, y1, 320, y2, fill=color, outline=color)

        # 添加装饰光晕
        self.canvas.create_oval(250, -20, 340, 70, outline='#e94560', width=2, stipple='gray20')
        self.canvas.create_oval(-30, 100, 50, 200, outline='#ffd700', width=2, stipple='gray15')

    def _create_glass_button(self, parent, text, command, bg_color, highlight_color):
        """创建玻璃质感按钮"""
        btn = tk.Button(parent, text=text, command=command,
                       font=('Microsoft YaHei', 12, 'bold'),
                       bg=bg_color, fg='white',
                       activebackground=highlight_color,
                       activeforeground='white',
                       relief='raised', bd=0,
                       padx=25, pady=8,
                       cursor='hand2',
                       highlightthickness=2,
                       highlightbackground='rgba(255,255,255,0.1)')

        def on_enter(e):
            e.widget.config(bg=highlight_color)
        def on_leave(e):
            e.widget.config(bg=bg_color)

        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        return btn

    def _make_draggable(self):
        """使窗口可拖动"""
        def on_mouse_press(event):
            self.root._drag_start_x = event.x
            self.root._drag_start_y = event.y

        def on_mouse_drag(event):
            x = self.root.winfo_x() - self.root._drag_start_x + event.x
            y = self.root.winfo_y() - self.root._drag_start_y + event.y
            self.root.geometry(f"+{x}+{y}")

        self.canvas.bind('<ButtonPress-1>', on_mouse_press)
        self.canvas.bind('<B1-Motion>', on_mouse_drag)

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
