"""自动更新模块"""
import os
import sys
import json
import shutil
import urllib.request
import urllib.error
from typing import Optional
import config
from utils import get_logger

logger = get_logger(__name__)

GITEE_API_URL = "https://gitee.com/api/v5/repos/degao/parental-control/releases/latest"


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


def check_for_update() -> tuple[bool, Optional[str]]:
    """检查是否有新版本
    返回: (是否有新版本, 新版本下载URL)
    """
    try:
        # 确保配置已加载
        if config.g_config is None:
            config.load_config()

        # 检查是否启用自动更新
        auto_update = config.g_config.get('auto_update', {})
        if not auto_update.get('enabled', True):
            logger.info("自动更新已禁用")
            return False, None

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
            # 查找 exe 下载链接
            assets = data.get('assets', [])
            for asset in assets:
                if asset.get('name', '').endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    logger.info(f"发现新版本: {latest_version}, 下载URL: {download_url}")
                    return True, download_url

        logger.info("当前已是最新版本")
        return False, None

    except urllib.error.URLError as e:
        logger.error(f"检查更新失败: 网络错误 - {e}")
        return False, None
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        return False, None


def download_update(url: str) -> Optional[str]:
    """下载更新包
    返回: 下载后的文件路径，失败返回 None
    """
    update_dir = get_update_dir()
    dest_path = os.path.join(update_dir, 'ParentControl.exe')

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
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(dest_path + '.tmp', 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

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
    update_dir = get_update_dir()
    new_exe = os.path.join(update_dir, 'ParentControl.exe')

    if not os.path.exists(new_exe):
        logger.info("没有待更新的文件")
        return False

    try:
        # 获取当前 exe 路径
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            logger.info("开发模式，跳过更新应用")
            return False

        logger.info(f"应用更新: {new_exe} -> {current_exe}")

        # 备份当前 exe
        backup_exe = current_exe + '.bak'
        if os.path.exists(backup_exe):
            os.remove(backup_exe)
        shutil.copy2(current_exe, backup_exe)

        # 替换为新 exe
        shutil.copy2(new_exe, current_exe)

        # 清理更新目录
        os.remove(new_exe)

        logger.info("更新应用成功")
        return True

    except Exception as e:
        logger.error(f"应用更新失败: {e}")
        return False


def run_auto_update():
    """执行自动更新流程"""
    # 1. 先检查并应用待更新
    if apply_pending_update():
        logger.info("已应用上次的更新")

    # 2. 检查新版本
    has_update, download_url = check_for_update()
    if has_update and download_url:
        # 3. 下载更新包
        downloaded = download_update(download_url)
        if downloaded:
            logger.info("更新包已下载，重启后自动应用")
