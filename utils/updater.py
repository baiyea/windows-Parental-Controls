"""自动更新模块"""
import os
import sys
import json
import shutil
import urllib.request
import urllib.error
import re
import subprocess
import threading
import time
from typing import Optional
import config
from utils import get_logger

logger = get_logger(__name__)

GITEE_API_URL = "https://gitee.com/api/v5/repos/degao/parental-control/releases/latest"
DEFAULT_UPDATE_CHECK_INTERVAL_SECONDS = 10 * 60


def get_update_dir() -> str:
    """获取更新目录路径"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    update_dir = os.path.join(base_dir, 'update')
    os.makedirs(update_dir, exist_ok=True)
    return update_dir


def parse_version(version_str: str) -> tuple:
    """解析版本号为元组用于比较"""
    # 去掉 v 前缀
    v = version_str.lstrip('v')
    parts = v.split('.')
    # 补齐到3位
    while len(parts) < 3:
        parts.append('0')
    return tuple(int(p) for p in parts)


def normalize_version_for_filename(version_str: str) -> str:
    """转换为打包文件名使用的版本号格式"""
    return re.sub(r'\.0+([0-9])', r'.\1', version_str.lstrip('v'))


def find_pending_update() -> Optional[str]:
    """查找已经下载但尚未应用的更新包。"""
    update_dir = get_update_dir()
    for f in os.listdir(update_dir):
        if re.fullmatch(r"ParentControl\.windows\.\d+(?:\.\d+)*\.exe", f):
            return os.path.join(update_dir, f)
    return None


def check_for_update() -> tuple[bool, Optional[str], Optional[str]]:
    """检查是否有新版本
    返回: (是否有新版本, 新版本下载URL, 最新版本号)
    """
    try:
        # 确保配置已加载
        if config.g_config is None:
            config.load_config()

        # 检查是否启用自动更新
        auto_update = config.g_config.get('auto_update', {})
        if not auto_update.get('enabled', True):
            logger.info("自动更新已禁用")
            return False, None, None

        # 调用 Gitee API
        logger.info(f"检查更新: {GITEE_API_URL}")
        req = urllib.request.Request(GITEE_API_URL)
        req.add_header('User-Agent', 'ParentControl/1.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # 获取最新版本号
        latest_version = data.get('tag_name', '').lstrip('v')
        current_version = config.get_version()

        logger.info(f"当前版本: {current_version}, 最新版本: {latest_version}")

        # 比较版本
        if parse_version(current_version) < parse_version(latest_version):
            expected_asset_name = f"ParentControl.windows.{normalize_version_for_filename(latest_version)}.exe"
            # 查找 exe 下载链接
            assets = data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '')
                if name == expected_asset_name:
                    download_url = asset.get('browser_download_url')
                    if not download_url:
                        logger.warning(f"更新资产缺少下载链接: {expected_asset_name}")
                        return False, None, None
                    logger.info(f"发现新版本: {latest_version}, 下载URL: {download_url}")
                    return True, download_url, latest_version

            logger.warning(f"未找到匹配版本的更新资产: {expected_asset_name}")

        logger.info("当前已是最新版本")
        return False, None, None

    except urllib.error.URLError as e:
        logger.error(f"检查更新失败: 网络错误 - {e}")
        return False, None, None
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        return False, None, None


def download_update(url: str, latest_version: str) -> Optional[str]:
    """下载更新包
    返回: 下载后的文件路径，失败返回 None
    """
    update_dir = get_update_dir()
    # 对版本号去零（与打包文件名一致）
    latest_version_no_zero = normalize_version_for_filename(latest_version)
    dest_path = os.path.join(update_dir, f'ParentControl.windows.{latest_version_no_zero}.exe')

    try:
        logger.info(f"下载更新包: {url}")

        # 检查磁盘空间（简单检查）
        disk = shutil.disk_usage(update_dir)
        if disk.free < 50 * 1024 * 1024:  # 少于50MB
            logger.error("磁盘空间不足")
            return None

        # 下载文件
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ParentControl/1.0')

        with urllib.request.urlopen(req, timeout=60) as response:
            chunk_size = 8192

            with open(dest_path + '.tmp', 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)

        # 重命名完成
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(dest_path + '.tmp', dest_path)

        logger.info(f"更新包下载成功: {dest_path}")
        return dest_path

    except urllib.error.URLError as e:
        logger.error(f"下载更新失败: 网络错误 - {e}")
        # 清理不完整文件
        if os.path.exists(dest_path + '.tmp'):
            os.remove(dest_path + '.tmp')
        return None
    except Exception as e:
        logger.error(f"下载更新失败: {e}")
        if os.path.exists(dest_path + '.tmp'):
            os.remove(dest_path + '.tmp')
        return None


def apply_pending_update() -> bool:
    """应用待更新的 exe
    返回: 是否成功应用更新
    """
    new_exe = find_pending_update()

    if not new_exe:
        logger.info("没有待更新的文件")
        return False

    # 从文件名提取版本号
    current_version = os.path.basename(new_exe).replace('ParentControl.windows.', '').replace('.exe', '')

    try:
        # 获取当前 exe 路径
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            logger.info("开发模式，跳过更新应用")
            return False

        logger.info(f"准备更新: {new_exe} -> {current_exe}")

        # 获取程序所在目录
        app_dir = os.path.dirname(current_exe)
        version_txt = os.path.join(app_dir, 'version.txt')
        config_json = os.path.join(app_dir, 'config.json')

        # 创建更新脚本（用于重启后替换 exe）
        update_script = os.path.join(app_dir, 'update.bat')
        script_content = f'''@echo off
timeout /t 2 /nobreak >nul
copy /y "{new_exe}" "{current_exe}" || exit /b 1
del "{new_exe}"
echo {current_version} > "{version_txt}"
if exist "{config_json}" del /f /q "{config_json}"
del "%~f0"
start "" "{current_exe}"
'''
        with open(update_script, 'w', encoding='utf-8') as f:
            f.write(script_content)

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            f'"{update_script}"',
            shell=True,
            cwd=app_dir,
            creationflags=creationflags,
        )

        logger.info(f"更新脚本已启动，将应用更新 (版本: {current_version})")
        return True

    except Exception as e:
        logger.error(f"应用更新失败: {e}")
        return False


def check_and_download_update():
    """检查并下载更新包，但不应用更新。"""
    if find_pending_update():
        logger.info("已有待应用更新包，跳过本次下载")
        return "download_pending"

    has_update, download_url, latest_version = check_for_update()
    if has_update and download_url and latest_version:
        downloaded = download_update(download_url, latest_version)
        if downloaded:
            logger.info("更新包已下载，请重启应用以完成更新")
            return "download_complete"

    return None


def run_auto_update():
    """执行自动更新流程"""
    # 1. 先检查并应用待更新
    if apply_pending_update():
        logger.info("已应用上次的更新")
        return "update_applied"

    return check_and_download_update()


def get_update_check_interval_seconds() -> int:
    """读取自动更新轮询间隔。"""
    auto_update = config.g_config.get("auto_update", {}) if config.g_config else {}
    minutes = auto_update.get("check_interval_minutes", 10)
    try:
        return max(1, int(minutes)) * 60
    except (TypeError, ValueError):
        return DEFAULT_UPDATE_CHECK_INTERVAL_SECONDS


def periodic_update_check_loop(interval_seconds: Optional[int] = None, stop_event=None):
    """后台定时检查更新。运行中只下载更新，不直接应用。"""
    if interval_seconds is None:
        interval_seconds = get_update_check_interval_seconds()

    logger.info(f"自动更新后台检查已启动，间隔 {interval_seconds // 60} 分钟")
    while True:
        if stop_event is None:
            time.sleep(interval_seconds)
        elif stop_event.wait(interval_seconds):
            return

        try:
            check_and_download_update()
        except Exception as e:
            logger.error(f"后台检查更新失败: {e}")


def start_periodic_update_check(interval_seconds: Optional[int] = None):
    """启动后台自动更新检查线程。"""
    auto_update = config.g_config.get("auto_update", {}) if config.g_config else {}
    if not auto_update.get("enabled", True):
        logger.info("自动更新已禁用，不启动后台检查")
        return None

    thread = threading.Thread(
        target=periodic_update_check_loop,
        kwargs={"interval_seconds": interval_seconds},
        daemon=True,
    )
    thread.start()
    return thread
