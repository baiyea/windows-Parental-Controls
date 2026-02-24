"""单实例锁模块"""
import socket
import atexit


class SingleInstance:
    """单实例锁类，确保程序只运行一个实例"""

    def __init__(self, port=37429):
        self.port = port
        self.sock = None

    def try_lock(self):
        """尝试获取锁"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.bind(('127.0.0.1', self.port))
            self.sock.listen(1)
            atexit.register(self.release)
            return True
        except socket.error:
            self.sock.close()
            self.sock = None
            return False

    def release(self):
        """释放锁"""
        if self.sock:
            self.sock.close()
