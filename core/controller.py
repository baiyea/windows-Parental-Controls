"""主控制器模块"""
import threading
import time
from datetime import datetime, timedelta

import pystray
import winsound
from plyer import notification
from tkinter import messagebox

import config
from core.lock_manager import LockScreenManager
from ui import create_tray_image, get_tray_menu, ExitConfirm
from ui.tray import set_controller


def get_audio_path():
    """获取音频文件路径，优先使用打包后的音频"""
    import sys
    import os
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        path = os.path.join(sys._MEIPASS, 'Ring04.wav')
        if os.path.exists(path):
            return path
    # 回退到当前目录或系统默认
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Ring04.wav')
    if os.path.exists(local_path):
        return local_path
    return r"C:\Windows\Media\Ring04.wav"


# 全局控制器实例
g_controller = None
g_icon = None


class ParentControl:
    """主控制器类"""

    def __init__(self):
        global g_controller
        g_controller = self

        self.running = True
        self.work_end_time = None
        self.lock_manager = LockScreenManager()
        self.force_lock_flag = threading.Event()
        self.remind_shown = False

        # 设置控制器引用到ui模块
        set_controller(self)

    def get_remaining_time(self):
        """获取剩余时间"""
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
        """启动控制器"""
        # 重置提醒状态
        self.remind_shown = False

        # 检查是否在锁屏期间（重启后恢复锁屏）
        break_end_time = config.g_config.get("break_end_time")
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
                    config.g_config["break_end_time"] = None
                    config.save_config()
            except (ValueError, TypeError):
                config.g_config["break_end_time"] = None
                config.save_config()

        # 尝试从配置中恢复工作结束时间
        saved_end_time = config.g_config.get("work_end_time")
        if saved_end_time:
            try:
                saved_time = datetime.strptime(saved_end_time, '%Y-%m-%d %H:%M:%S')
                # 如果保存的时间在未来，则继续使用
                if saved_time > datetime.now():
                    self.work_end_time = saved_time
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 恢复计时，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
                else:
                    # 时间已过期，创建新的计时
                    work_minutes = config.g_config.get("work_minutes", 30)
                    self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
                    config.g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
                    config.save_config()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
            except (ValueError, TypeError):
                # 解析失败，创建新的计时
                work_minutes = config.g_config.get("work_minutes", 30)
                self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
                config.g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
                config.save_config()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动，可用至 {self.work_end_time.strftime('%H:%M:%S')}")
        else:
            # 没有保存的时间，创建新的计时
            work_minutes = config.g_config.get("work_minutes", 30)
            self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
            config.g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
            config.save_config()
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
        """托盘就绪回调"""
        global g_icon
        g_icon = icon
        icon.visible = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 托盘已激活")

    def refresh_tray_loop(self):
        """刷新托盘菜单循环"""
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
                remind_before_minutes = config.g_config.get("remind_before_minutes", 5)

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
        work_minutes = config.g_config.get("work_minutes", 30)
        self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
        config.g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
        self.remind_shown = False
        config.save_config()
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
        """退出应用"""
        self.running = False
        global g_icon
        if g_icon:
            g_icon.stop()

    def refresh_tray_menu(self):
        """刷新托盘菜单"""
        global g_icon
        if g_icon:
            g_icon.menu = get_tray_menu()
