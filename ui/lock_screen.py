"""锁屏窗口模块 - 现代液态玻璃效果"""
import tkinter as tk
from tkinter import messagebox
import config


class LockScreen:
    """锁屏窗口类 - 带液态玻璃效果"""

    def __init__(self, on_unlock_callback, is_forced=False, remaining_seconds=None):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='#0f0f1a')
        self.on_unlock = on_unlock_callback
        self.is_forced = is_forced  # 是否强制锁屏（用于区分正常休息）

        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Escape>', lambda e: 'break')

        # 设置透明度
        self.root.attributes('-alpha', 0.95)

        # 创建主画布用于绘制渐变背景
        self.canvas = tk.Canvas(self.root, width=self.root.winfo_screenwidth(),
                                height=self.root.winfo_screenheight(),
                                highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # 绘制液态渐变背景
        self._draw_liquid_background()

        # 创建玻璃质感主容器
        glass_frame = tk.Frame(self.canvas, bg='rgba(30, 30, 50, 0.6)',
                               highlightthickness=0)
        glass_frame.place(relx=0.5, rely=0.5, anchor='center', width=500, height=400)

        # 绘制玻璃容器的圆角边框效果
        self._draw_glass_container(glass_frame)

        # 标题
        title = "🔒 强制锁屏" if is_forced else "⏰ 休息时间到！"
        title_label = tk.Label(glass_frame, text=title, font=('Microsoft YaHei', 42, 'bold'),
                               fg='#ffffff', bg='transparent')
        title_label.place(relx=0.5, rely=0.15, anchor='center')

        # 添加发光效果标签
        glow_label = tk.Label(glass_frame, text="▬" * 20, font=('Arial', 8),
                              fg='#e94560', bg='transparent')
        glow_label.place(relx=0.5, rely=0.25, anchor='center')

        if is_forced:
            tk.Label(glass_frame, text="👨‍👩 家长强制锁定",
                    font=('Microsoft YaHei', 16, 'bold'), fg='#ffd700', bg='transparent').place(
                        relx=0.5, rely=0.32, anchor='center')

        self.time_label = tk.Label(glass_frame, text="休息倒计时：30:00",
                                  font=('Microsoft YaHei', 24, 'bold'), fg='#4ecca3', bg='transparent')
        self.time_label.place(relx=0.5, rely=0.42, anchor='center')

        # 密码输入区域
        pwd_frame = tk.Frame(glass_frame, bg='transparent')
        pwd_frame.place(relx=0.5, rely=0.58, anchor='center', width=320, height=50)

        tk.Label(pwd_frame, text="🔑 ", font=('Arial', 16),
                fg='#eaeaea', bg='transparent').pack(side='left')

        self.pwd_entry = tk.Entry(pwd_frame, show='●', font=('Arial', 16), width=12,
                                  bg='rgba(255, 255, 255, 0.1)', fg='#ffffff',
                                  insertbackground='#4ecca3', relief='flat')
        self.pwd_entry.pack(side='left', padx=5)
        self.pwd_entry.bind('<Return>', lambda e: self.check_password())
        self.pwd_entry.focus()

        # 自定义按钮样式
        unlock_btn = self._create_glass_button(pwd_frame, "解锁", self.check_password,
                                               '#e94560', '#ff6b6b')
        unlock_btn.pack(side='left', padx=15)

        # 休息时间：如果传入了剩余秒数则使用，否则从配置读取
        if remaining_seconds is not None:
            self.remaining = remaining_seconds
        else:
            self.remaining = config.g_config.get("break_minutes", 5) * 60
        self.update_timer()

    def _draw_liquid_background(self):
        """绘制液态渐变背景"""
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()

        # 创建多层渐变效果
        colors_top = ['#0f0f1a', '#1a1a3e', '#2d1f3e', '#1a1a3e', '#0f0f1a']
        colors_bottom = ['#1a1a3e', '#2d1f3e', '#0f0f1a', '#2d1f3e', '#1a1a3e']

        # 绘制垂直渐变
        for i in range(height):
            ratio = i / height
            # 创建波浪效果
            wave = int(10 * (1 - abs(ratio - 0.5) * 2) * (1 if i % 200 < 100 else -1))
            self.canvas.create_line(0, i, width, i,
                                    fill=f'#{int(15 + wave):02x}{int(15):02x}{int(26 + wave * 2):02x}',
                                    width=1)

        # 添加装饰性圆形光晕
        self._draw_glow_orb(width * 0.2, height * 0.3, 200, '#e94560', 0.15)
        self._draw_glow_orb(width * 0.8, height * 0.7, 250, '#4ecca3', 0.1)
        self._draw_glow_orb(width * 0.5, height * 0.1, 150, '#ffd700', 0.08)

    def _draw_glow_orb(self, x, y, radius, color, alpha):
        """绘制发光圆球"""
        for i in range(int(radius), 0, -2):
            ratio = 1 - (i / radius)
            orb_alpha = int(alpha * 255 * ratio * (1 - ratio) * 4)
            if orb_alpha > 0:
                self.canvas.create_oval(x - i, y - i, x + i, y + i,
                                        outline=color, width=1,
                                        stipple=f'gray{min(orb_alpha, 100)}')

    def _draw_glass_container(self, frame):
        """绘制玻璃容器效果"""
        # 在画布上绘制圆角矩形边框
        x1, y1 = frame.winfo_reqwidth() // 2 - 250, frame.winfo_reqheight() // 2 - 200
        x2, y2 = x1 + 500, y1 + 400

        # 玻璃边框渐变
        for i in range(3):
            alpha = int(80 * (1 - i / 3))
            self.canvas.create_rectangle(x1 - i, y1 - i, x2 + i, y2 + i,
                                         outline=f'#4ecca3', width=1,
                                         stipple=f'gray{alpha}')

    def _create_glass_button(self, parent, text, command, bg_color, highlight_color):
        """创建玻璃质感按钮"""
        btn = tk.Button(parent, text=text, command=command,
                       font=('Microsoft YaHei', 14, 'bold'),
                       bg=bg_color, fg='white',
                       activebackground=highlight_color,
                       activeforeground='white',
                       relief='raised', bd=2,
                       padx=25, pady=8,
                       cursor='hand2')

        # 绑定悬停效果
        def on_enter(e):
            e.widget.config(bg=highlight_color)
        def on_leave(e):
            e.widget.config(bg=bg_color)

        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        return btn

    def update_timer(self):
        mins, secs = divmod(self.remaining, 60)
        self.time_label.config(text=f"休息倒计时：{mins:02d}:{secs:02d}")
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
        if self.pwd_entry.get() == config.g_config.get("password", "1234"):
            self.root.destroy()
            self.on_unlock()
        else:
            messagebox.showerror("错误", "密码错误！", parent=self.root)
            self.pwd_entry.delete(0, 'end')

    def run(self):
        self.root.mainloop()
