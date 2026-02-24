"""日志配置模块"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


def get_log_dir():
    """获取日志目录路径"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe 时，使用 exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发时，使用项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    log_dir = os.path.join(base_dir, 'log')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logger(name='ParentControl', level=logging.INFO):
    """
    配置日志系统
    
    Args:
        name: logger名称
        level: 日志级别
    
    Returns:
        配置好的logger实例
    """
    # 配置根logger
    root_logger = logging.getLogger()
    
    # 避免重复配置
    if root_logger.handlers:
        return logging.getLogger(name)
    
    root_logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器 - 按日期命名
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(name)


def get_logger(name=None):
    """
    获取logger实例
    
    Args:
        name: logger名称，如果为None则使用调用模块的名称
    
    Returns:
        logger实例
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'ParentControl')
    
    return logging.getLogger(name)
