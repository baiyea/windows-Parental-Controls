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
from core.state_machine import StateMachine, AppState, AppEvent, StateTransition
from ui import create_tray_image, get_tray_menu, ExitConfirm
from ui.tray import set_controller
from utils import get_logger

logger = get_logger(__name__)


def get_audio_path():
    """获取音频文件路径，优先使用打包后的音频"""
    import sys
    import os
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        path = os.path.join(sys._MEIPASS, 'audio', 'Ring04.wav')
        if os.path.exists(path):
            return path
    # 回退到开发环境的路径
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'doc', 'audio', 'Ring04.wav')
    if os.path.exists(local_path):
        return local_path
    # 最后尝试系统默认音频
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
        self.break_end_time = None
        self.lock_manager = LockScreenManager()
        self.force_lock_flag = threading.Event()
        self.remind_shown = False
        self.timer = None

        # 初始化状态机
        self.state_machine = StateMachine(AppState.IDLE)
        self._setup_state_machine()

        # 设置控制器引用到ui模块
        set_controller(self)

    def _setup_state_machine(self):
        """配置状态机的转换规则和动作"""
        sm = self.state_machine
        
        # ===== 定义状态转换 =====
        
        # IDLE -> WORKING (启动)
        sm.add_transition(StateTransition(
            from_state=AppState.IDLE,
            event=AppEvent.START,
            to_state=AppState.WORKING,
            action=self._start_work_timer
        ))
        
        # IDLE -> LOCKED (恢复锁屏状态)
        sm.add_transition(StateTransition(
            from_state=AppState.IDLE,
            event=AppEvent.RESTORE_STATE,
            to_state=AppState.LOCKED,
            action=self._restore_lock_screen,
            guard=lambda **kw: kw.get('has_lock_state', False)
        ))
        
        # WORKING -> REMINDING (到达提醒时间)
        sm.add_transition(StateTransition(
            from_state=AppState.WORKING,
            event=AppEvent.REMIND_TIME,
            to_state=AppState.REMINDING,
            action=self._show_reminder
        ))
        
        # WORKING -> LOCKED (强制锁屏)
        sm.add_transition(StateTransition(
            from_state=AppState.WORKING,
            event=AppEvent.FORCE_LOCK,
            to_state=AppState.LOCKED,
            action=self._lock_screen
        ))
        
        # REMINDING -> LOCKED (工作时间到)
        sm.add_transition(StateTransition(
            from_state=AppState.REMINDING,
            event=AppEvent.WORK_TIME_UP,
            to_state=AppState.LOCKED,
            action=self._lock_screen
        ))
        
        # REMINDING -> LOCKED (强制锁屏)
        sm.add_transition(StateTransition(
            from_state=AppState.REMINDING,
            event=AppEvent.FORCE_LOCK,
            to_state=AppState.LOCKED,
            action=self._lock_screen
        ))
        
        # LOCKED -> WORKING (休息时间到)
        sm.add_transition(StateTransition(
            from_state=AppState.LOCKED,
            event=AppEvent.BREAK_TIME_UP,
            to_state=AppState.WORKING,
            action=self._start_work_timer
        ))
        
        # LOCKED -> WORKING (密码解锁)
        sm.add_transition(StateTransition(
            from_state=AppState.LOCKED,
            event=AppEvent.PASSWORD_UNLOCK,
            to_state=AppState.WORKING,
            action=self._start_work_timer
        ))
        
        # 任意状态 -> EXITING (退出)
        for state in AppState:
            if state != AppState.EXITING:
                sm.add_transition(StateTransition(
                    from_state=state,
                    event=AppEvent.EXIT,
                    to_state=AppState.EXITING,
                    action=self._cleanup,
                    guard=self._can_exit
                ))
        
        # ===== 定义状态进入/退出动作 =====
        
        sm.add_entry_action(AppState.WORKING, self._on_enter_working)
        sm.add_exit_action(AppState.WORKING, self._on_exit_working)
        
        sm.add_entry_action(AppState.LOCKED, self._on_enter_locked)
        sm.add_exit_action(AppState.LOCKED, self._on_exit_locked)
        
        sm.add_entry_action(AppState.REMINDING, self._on_enter_reminding)

    def get_remaining_time(self):
        """获取剩余时间"""
        state = self.state_machine.get_state()
        
        if state == AppState.LOCKED:
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
        # 检查是否需要恢复锁屏状态
        break_end_time = config.g_config.get("break_end_time")
        if break_end_time:
            try:
                break_end = datetime.strptime(break_end_time, '%Y-%m-%d %H:%M:%S')
                now = datetime.now()

                if now < break_end:
                    # 仍在锁屏期间，恢复锁屏
                    remaining_seconds = int((break_end - now).total_seconds())
                    logger.info(f"检测到未完成的锁屏期间，剩余 {remaining_seconds} 秒，正在恢复锁屏...")
                    self.break_end_time = break_end
                    self.state_machine.trigger(AppEvent.RESTORE_STATE, has_lock_state=True, remaining_seconds=remaining_seconds)
                    # 启动后台线程
                    threading.Thread(target=self.monitor_loop, daemon=True).start()
                    threading.Thread(target=self.refresh_tray_loop, daemon=True).start()
                    # 主线程运行托盘
                    self._run_tray()
                    return
                else:
                    # 锁屏期间已过，清除状态
                    config.g_config["break_end_time"] = None
                    config.save_config()
            except (ValueError, TypeError):
                config.g_config["break_end_time"] = None
                config.save_config()

        # 正常启动 - 触发 START 事件
        self.state_machine.trigger(AppEvent.START)

        # 启动后台线程
        threading.Thread(target=self.monitor_loop, daemon=True).start()
        threading.Thread(target=self.refresh_tray_loop, daemon=True).start()

        # 主线程运行托盘
        self._run_tray()

    def _run_tray(self):
        """运行托盘图标"""
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
        logger.info("托盘已激活")

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
                    logger.error(f"刷新托盘失败: {e}")

    # ===== 状态机动作方法 =====

    def _start_work_timer(self, **kwargs):
        """开始工作计时"""
        work_minutes = config.g_config.get("work_minutes", 30)
        self.work_end_time = datetime.now() + timedelta(minutes=work_minutes)
        
        # 保存状态
        config.g_config["work_end_time"] = self.work_end_time.strftime('%Y-%m-%d %H:%M:%S')
        config.g_config["break_end_time"] = None
        config.save_config()
        
        logger.info(f"工作计时开始，结束时间: {self.work_end_time.strftime('%H:%M:%S')}")

    def _show_reminder(self, **kwargs):
        """显示提醒"""
        if not self.work_end_time:
            return
            
        remaining = self.work_end_time - datetime.now()
        remaining_minutes = int(remaining.total_seconds() / 60)
        
        try:
            notification.notify(
                title="家长控制提醒",
                message=f"距离锁屏还剩 {remaining_minutes} 分钟，请保存工作！",
                timeout=5
            )
            winsound.PlaySound(get_audio_path(), winsound.SND_FILENAME)
            logger.info("已发送提前提醒")
        except Exception as e:
            logger.error(f"发送提醒失败: {e}")

    def _lock_screen(self, **kwargs):
        """锁定屏幕"""
        # 计算休息结束时间
        break_minutes = config.g_config.get("break_minutes", 30)
        self.break_end_time = datetime.now() + timedelta(minutes=break_minutes)
        
        # 保存状态
        config.g_config["break_end_time"] = self.break_end_time.strftime('%Y-%m-%d %H:%M:%S')
        config.save_config()
        
        # 显示锁屏
        is_forced = kwargs.get('forced', False)
        remaining_seconds = kwargs.get('remaining_seconds')
        
        # 设置解锁回调
        self.lock_manager.on_unlock_callback = self._on_unlock_callback
        
        threading.Thread(
            target=self.lock_manager.show_lock,
            args=(is_forced, remaining_seconds),
            daemon=True
        ).start()
        
        logger.info(f"锁屏开始，结束时间: {self.break_end_time.strftime('%H:%M:%S')}")
        
        # 播放音效
        try:
            winsound.PlaySound(get_audio_path(), winsound.SND_FILENAME)
        except:
            pass

        # 锁屏后立即重启计算机
        import subprocess
        subprocess.run(['shutdown', '/r', '/t', '0', '/f'], check=False)
        logger.info("正在强制重启计算机")

    def _restore_lock_screen(self, **kwargs):
        """恢复锁屏状态（重启后）"""
        remaining_seconds = kwargs.get('remaining_seconds')
        
        # 设置解锁回调
        self.lock_manager.on_unlock_callback = self._on_unlock_callback
        
        # 在新线程显示锁屏，传入剩余时间
        threading.Thread(
            target=self.lock_manager.show_lock,
            args=(False, remaining_seconds),
            daemon=True
        ).start()
        
        # 等待锁屏显示
        time.sleep(3)
        
        logger.info(f"恢复锁屏状态，剩余 {remaining_seconds} 秒")

    def _cleanup(self, **kwargs):
        """清理资源"""
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.info("程序退出")

    def _on_unlock_callback(self):
        """解锁回调"""
        logger.info("密码解锁成功")
        self.state_machine.trigger(AppEvent.PASSWORD_UNLOCK)

    # ===== 状态进入/退出动作 =====

    def _on_enter_working(self, **kwargs):
        """进入工作状态"""
        self.remind_shown = False
        logger.info("进入工作状态")

    def _on_exit_working(self, **kwargs):
        """离开工作状态"""
        if self.timer:
            self.timer.cancel()
        logger.info("离开工作状态")

    def _on_enter_locked(self, **kwargs):
        """进入锁屏状态"""
        logger.info("进入锁屏状态")

    def _on_exit_locked(self, **kwargs):
        """离开锁屏状态"""
        config.g_config["break_end_time"] = None
        config.save_config()
        logger.info("离开锁屏状态")

    def _on_enter_reminding(self, **kwargs):
        """进入提醒状态"""
        self.remind_shown = True
        logger.info("进入提醒状态")

    # ===== 守卫条件 =====

    def _can_exit(self, **kwargs) -> bool:
        """检查是否可以退出"""
        # 锁屏期间不允许退出
        if self.state_machine.is_in_state(AppState.LOCKED):
            if self.break_end_time:
                remaining = (self.break_end_time - datetime.now()).total_seconds()
                if remaining > 0:
                    logger.info("锁屏期间不允许退出")
                    return False
        return True

    # ===== 定时器管理 =====

    def _schedule_event(self, target_time: datetime, event: AppEvent):
        """调度事件"""
        delay = (target_time - datetime.now()).total_seconds()
        if delay > 0:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(delay, lambda: self.state_machine.trigger(event))
            self.timer.daemon = True
            self.timer.start()
            logger.debug(f"调度事件 {event} 在 {delay:.1f} 秒后执行")

    def monitor_loop(self):
        """监控循环 - 检测时间和强制锁屏信号"""
        while self.running:
            # 检查强制锁屏信号
            if self.force_lock_flag.is_set() and not self.lock_manager.lock_screen:
                logger.info("执行强制锁屏")
                self.force_lock_flag.clear()
                self.state_machine.trigger(AppEvent.FORCE_LOCK, forced=True)
                time.sleep(2)
                continue

            # 根据当前状态检查时间
            current_state = self.state_machine.get_state()
            
            if current_state == AppState.WORKING:
                # 检查提前提醒
                if self.work_end_time and not self.remind_shown:
                    remaining = self.work_end_time - datetime.now()
                    remaining_minutes = remaining.total_seconds() / 60
                    remind_before_minutes = config.g_config.get("remind_before_minutes", 5)

                    if 0 < remaining_minutes <= remind_before_minutes:
                        self.state_machine.trigger(AppEvent.REMIND_TIME)
                
                # 检查工作时间是否到
                if self.work_end_time and datetime.now() >= self.work_end_time:
                    self.state_machine.trigger(AppEvent.WORK_TIME_UP)
                    time.sleep(2)
                    
            elif current_state == AppState.REMINDING:
                # 检查工作时间是否到
                if self.work_end_time and datetime.now() >= self.work_end_time:
                    self.state_machine.trigger(AppEvent.WORK_TIME_UP)
                    time.sleep(2)
                    
            elif current_state == AppState.LOCKED:
                # 检查休息时间是否到
                if self.break_end_time and datetime.now() >= self.break_end_time:
                    self.state_machine.trigger(AppEvent.BREAK_TIME_UP)
                    time.sleep(2)

            time.sleep(1)

    def on_break_complete(self):
        """休息完成，重新计时（已废弃，由状态机管理）"""
        # 这个方法保留是为了兼容性，实际逻辑已移到状态机
        pass

    def force_lock(self):
        """触发强制锁屏（线程安全）"""
        if not self.lock_manager.lock_screen:
            self.force_lock_flag.set()

    def confirm_exit(self):
        """退出验证"""
        # 如果正在锁屏，直接拒绝退出
        if self.state_machine.is_in_state(AppState.LOCKED):
            if self.break_end_time:
                remaining = (self.break_end_time - datetime.now()).total_seconds()
                if remaining > 0:
                    messagebox.showwarning("提示", "休息期间不能退出程序！")
                    return False
        # 显示密码验证窗口
        return ExitConfirm().run()

    def exit_app(self):
        """退出应用"""
        if self.state_machine.trigger(AppEvent.EXIT):
            global g_icon
            if g_icon:
                g_icon.stop()
            import os
            os._exit(0)

    def refresh_tray_menu(self):
        """刷新托盘菜单"""
        global g_icon
        if g_icon:
            g_icon.menu = get_tray_menu()
