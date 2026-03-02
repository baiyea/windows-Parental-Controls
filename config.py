"""配置管理模块"""
import os
import sys
import json
from utils import get_logger

logger = get_logger(__name__)


def get_config_path():
    """获取配置文件路径（使用程序所在目录）"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe 时，使用 exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发时，使用脚本所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.json')

    logger.debug(f"配置文件路径: {config_path}")
    logger.debug(f"exe所在目录: {base_dir}")
    logger.debug(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    return config_path


def load_config():
    """加载配置"""
    global g_config
    config_path = get_config_path()
    default_config = {
        "password": "0829",
        "work_minutes": 30,
        "break_minutes": 30,
        "work_end_time": None,
        "remind_before_minutes": 5,
        "auto_restart_after_lock": False,
        "restrict_night_hours": {
            "enabled": True,
            "start_hour": 21,
            "end_hour": 6
        }
    }

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        logger.info("配置文件不存在，准备创建...")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            logger.info(f"已创建默认配置文件: {config_path}")
        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
            logger.info("尝试在用户目录创建...")
            # 备用方案：尝试在用户目录创建
            try:
                backup_path = os.path.join(os.path.expanduser("~"), "parental_control_config.json")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=4)
                logger.info(f"已创建备用配置文件: {backup_path}")
                return g_config
            except Exception as e2:
                logger.error(f"创建备用配置文件也失败: {e2}")

    # 加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            g_config = json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {e}, 使用默认配置")
        g_config = default_config

    # 确保必要字段存在
    if "work_end_time" not in g_config:
        g_config["work_end_time"] = None
    # 锁屏结束时间
    if "break_end_time" not in g_config:
        g_config["break_end_time"] = None
    # 夜间限制配置
    if "restrict_night_hours" not in g_config:
        g_config["restrict_night_hours"] = {
            "enabled": True,
            "start_hour": 21,
            "end_hour": 6
        }

    return g_config


def save_config():
    """保存当前配置到 config.json"""
    global g_config
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(g_config, f, ensure_ascii=False, indent=4)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"保存配置失败: {e}")


# 全局配置变量
g_config = None
