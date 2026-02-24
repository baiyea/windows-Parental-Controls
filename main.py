"""家长控制程序入口"""
import sys
import argparse
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from config import load_config
from platform import SingleInstance, add_to_startup
from core import ParentControl


def main():
    """主入口函数"""
    load_config()  # 加载配置

    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()

    if args.install:
        add_to_startup()
        sys.exit(0)

    # 检查单实例锁
    locker = SingleInstance()
    if not locker.try_lock():
        print("程序已在运行")
        tk.Tk().withdraw()
        messagebox.showinfo("家长控制", "程序已经在运行！")
        sys.exit(0)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 单实例锁检查通过")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 家长控制启动...")
    app = ParentControl()
    app.start()


if __name__ == "__main__":
    main()
