"""托盘图标模块"""
import warnings
from PIL import Image, ImageDraw
import pystray

from platform import toggle_startup, is_in_startup
from .password_dialog import PasswordConfirm

# 全局变量用于存储控制器引用
g_controller = None


def create_tray_image():
    """创建托盘图标图像"""
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


def set_controller(controller):
    """设置控制器引用"""
    global g_controller
    g_controller = controller
