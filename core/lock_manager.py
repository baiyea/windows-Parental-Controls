"""锁屏管理模块"""
from datetime import datetime, timedelta
import config
from ui.lock_screen import LockScreen
from utils import get_logger

logger = get_logger(__name__)


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
        break_end_time = datetime.now() + timedelta(minutes=config.g_config.get("break_minutes", 5))
        config.g_config["break_end_time"] = break_end_time.strftime('%Y-%m-%d %H:%M:%S')
        config.save_config()

        self.lock_screen = LockScreen(self.on_break_complete, is_forced=forced, remaining_seconds=remaining_seconds)
        self.lock_screen.run()

    def on_break_complete(self):
        """解锁回调"""
        logger.info("锁屏解锁")
        self.lock_screen = None
        # 清除锁屏状态
        config.g_config["break_end_time"] = None
        config.save_config()
        if self.on_unlock_callback:
            self.on_unlock_callback()
