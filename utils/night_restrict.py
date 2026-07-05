"""夜间限制工具函数"""
from datetime import datetime, timedelta
import config
from utils import get_logger
from utils.trusted_time import trusted_now

logger = get_logger(__name__)
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_night_config():
    """获取夜间限制配置并补齐运行期默认值。"""
    if config.g_config is None:
        config.load_config()

    night_config = config.g_config.setdefault("restrict_night_hours", {})
    night_config.setdefault("enabled", True)
    night_config.setdefault("start_hour", 21)
    night_config.setdefault("end_hour", 6)
    night_config.setdefault("password_unlock_grace_minutes", 30)
    night_config.setdefault("override_until", None)
    return night_config


def is_in_night_restrict_hours(now=None):
    """判断当前是否在夜间限制时段"""
    night_config = _get_night_config()

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


def get_night_unlock_override_until():
    """读取夜间临时放行截止时间。"""
    override_until = _get_night_config().get("override_until")
    if not override_until:
        return None

    try:
        return datetime.strptime(override_until, DATETIME_FORMAT)
    except (TypeError, ValueError):
        logger.warning(f"夜间临时放行时间格式非法: {override_until}")
        return None


def is_night_unlock_override_active(now=None):
    """判断夜间密码解锁临时放行是否仍有效。"""
    if now is None:
        now = trusted_now()

    override_until = get_night_unlock_override_until()
    return override_until is not None and now < override_until


def is_night_restrict_enforced(now=None):
    """判断夜间限制当前是否实际生效。"""
    if not is_in_night_restrict_hours(now=now):
        return False

    if now is None:
        now = trusted_now()
    return not is_night_unlock_override_active(now=now)


def activate_night_unlock_override(now=None):
    """启用夜间密码解锁临时放行。"""
    if now is None:
        now = trusted_now()

    night_config = _get_night_config()
    grace_minutes = night_config.get("password_unlock_grace_minutes", 30)
    override_until = now + timedelta(minutes=grace_minutes)
    night_config["override_until"] = override_until.strftime(DATETIME_FORMAT)
    config.save_config()
    logger.info(f"夜间密码解锁临时放行至: {night_config['override_until']}")
    return override_until
