"""夜间限制工具函数"""
import config
from utils import get_logger
from utils.trusted_time import trusted_now

logger = get_logger(__name__)


def is_in_night_restrict_hours(now=None):
    """判断当前是否在夜间限制时段"""
    # 确保配置已加载
    if config.g_config is None:
        config.load_config()

    night_config = config.g_config.get("restrict_night_hours", {})

    # 如果未启用，直接返回 False
    if not night_config.get("enabled", False):
        return False

    if now is None:
        now = trusted_now()

    current_hour = now.hour
    start_hour = night_config.get("start_hour", 21)
    end_hour = night_config.get("end_hour", 6)

    # 处理跨天情况（如 21:00 到次日 6:00）
    if end_hour > start_hour:
        # 简单情况：21:00-23:00
        return start_hour <= current_hour < end_hour
    else:
        # 跨天情况：21:00-06:00
        return current_hour >= start_hour or current_hour < end_hour
