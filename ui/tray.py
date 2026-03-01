"""托盘图标模块 - 现代液态玻璃效果"""
import warnings
from PIL import Image, ImageDraw, ImageFilter
import pystray

from platform import toggle_startup, is_in_startup
from .password_dialog import PasswordConfirm

# 全局变量用于存储控制器引用
g_controller = None


def create_tray_image():
    """创建托盘图标图像 - 液态玻璃效果"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # 创建更大的图像以添加更多细节
        img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        dc = ImageDraw.Draw(img)

        # 外层发光晕圈
        for i in range(20, 0, -1):
            alpha = int(30 * (1 - i / 20))
            glow_color = (233, 69, 96, alpha)
            dc.ellipse([2 - i, 2 - i, 62 + i, 62 + i], fill=glow_color)

        # 主圆形背景 - 渐变效果
        # 绘制多层圆形模拟渐变
        for i in range(30, 0, -1):
            r = int(233 + (107 - 233) * (i / 30))
            g = int(69 + (107 - 69) * (i / 30))
            b = int(96 + (107 - 96) * (i / 30))
            dc.ellipse([i, i, 60 - i, 60 - i], fill=(r, g, b))

        # 内层玻璃质感高亮
        dc.ellipse([8, 8, 56, 56], fill='#ff6b6b')
        dc.ellipse([12, 12, 52, 52], fill='#e94560')

        # 顶部高光 - 玻璃效果
        highlight_points = [(15, 18), (25, 14), (35, 13), (45, 14), (50, 18)]
        dc.polygon(highlight_points, fill=(255, 255, 255, 180))

        # 中心图标 - 锁形图案（现代化设计）
        # 锁体
        dc.rounded_rectangle([24, 28, 40, 52], radius=4, fill='white')

        # 锁梁
        dc.arc([28, 18, 36, 30], start=180, end=0, fill='white', width=3)

        # 锁孔
        dc.ellipse([29, 38, 35, 44], fill='#e94560')
        dc.rectangle([31, 42, 33, 48], fill='#e94560')

        # 添加液态光泽效果
        dc.ellipse([18, 18, 30, 30], fill=(255, 255, 255, 100))

        # 应用轻微模糊使边缘更柔和
        img = img.filter(ImageFilter.GaussianBlur(radius=1))

        # 重新锐化以增强玻璃质感
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

        # 调整大小为标准的托盘图标大小
        img = img.resize((64, 64), Image.Resampling.LANCZOS)

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
            import os
            os._exit(0)

    elif "开机启动" in text:
        # 弹出密码验证窗口
        if PasswordConfirm("开机启动").run():
            _, new_state = toggle_startup()
            # 刷新托盘菜单显示新状态
            g_controller.refresh_tray_menu()
        return


def get_tray_menu():
    """获取托盘菜单"""
    global g_controller
    if not g_controller:
        return pystray.Menu(
            pystray.MenuItem("启动中...", lambda icon, item: None, enabled=False),
            pystray.MenuItem("退出", on_tray_clicked),
        )

    # 检查开机启动状态
    startup_status = "✓ 开机启动" if is_in_startup() else "✗ 开机启动"

    # 根据状态机状态判断是否可以锁屏
    from core.state_machine import AppState
    can_lock = not g_controller.state_machine.is_in_state(AppState.LOCKED)

    return pystray.Menu(
        pystray.MenuItem(
            f"⏱ {g_controller.get_remaining_time()}",
            lambda icon, item: None, enabled=False
        ),
        pystray.MenuItem("🔒 立即锁屏", on_tray_clicked, enabled=can_lock),
        pystray.MenuItem("─", lambda icon, item: None, enabled=False),
        pystray.MenuItem(startup_status, on_tray_clicked),
        pystray.MenuItem("🚪 退出", on_tray_clicked),
    )


def set_controller(controller):
    """设置控制器引用"""
    global g_controller
    g_controller = controller
