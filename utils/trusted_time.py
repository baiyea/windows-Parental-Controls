"""可信线上时间工具。"""
from __future__ import annotations

from datetime import datetime, timedelta
import socket
import struct
import time
from typing import Callable, Iterable

from utils import get_logger

logger = get_logger(__name__)

NTP_DELTA = 2_208_988_800
NTP_PACKET_SIZE = 48


class TrustedTimeUnavailable(RuntimeError):
    """无法获取可信线上时间。"""


class NtpClient:
    """最小 NTP 客户端，仅读取服务器发送时间。"""

    def request_time(self, server: str, timeout: float) -> datetime:
        packet = b"\x1b" + 47 * b"\0"

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (server, 123))
            data, _ = sock.recvfrom(1024)

        if len(data) < NTP_PACKET_SIZE:
            raise TrustedTimeUnavailable(f"NTP 响应过短: {server}")

        seconds = struct.unpack("!12I", data[:NTP_PACKET_SIZE])[10]
        unix_seconds = seconds - NTP_DELTA
        if unix_seconds <= 0:
            raise TrustedTimeUnavailable(f"NTP 响应时间非法: {server}")

        return datetime.fromtimestamp(unix_seconds)


class TrustedClock:
    """用线上时间基准和单调时钟推算当前时间。"""

    def __init__(
        self,
        servers: Iterable[str],
        client: NtpClient | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        timeout_seconds: float = 3,
    ):
        self.servers = list(servers)
        self.client = client or NtpClient()
        self.monotonic = monotonic
        self.timeout_seconds = timeout_seconds
        self._base_time: datetime | None = None
        self._base_monotonic: float | None = None

    def sync(self) -> datetime:
        """从第一个可用服务器同步线上时间。"""
        last_error = None
        for server in self.servers:
            try:
                server_time = self.client.request_time(server, self.timeout_seconds)
            except Exception as exc:
                last_error = exc
                logger.warning(f"可信时间同步失败: {server}: {exc}")
                continue

            self._base_time = server_time
            self._base_monotonic = self.monotonic()
            logger.info(f"可信时间同步成功: {server} -> {server_time}")
            return server_time

        self._base_time = None
        self._base_monotonic = None
        raise TrustedTimeUnavailable(f"所有可信时间服务器不可用: {last_error}")

    def now(self) -> datetime:
        """返回可信当前时间。"""
        if self._base_time is None or self._base_monotonic is None:
            raise TrustedTimeUnavailable("可信时间尚未同步")

        elapsed = self.monotonic() - self._base_monotonic
        if elapsed < 0:
            raise TrustedTimeUnavailable("单调时钟异常回退")
        return self._base_time + timedelta(seconds=elapsed)

    def is_available(self) -> bool:
        """当前是否已有可用可信时间基准。"""
        return self._base_time is not None and self._base_monotonic is not None


def _load_config():
    import config

    if config.g_config is None:
        config.load_config()
    return config.g_config.get("trusted_time", {})


def _create_default_clock() -> TrustedClock:
    trusted_config = _load_config()
    return TrustedClock(
        servers=trusted_config.get("servers", ["ntp.aliyun.com", "ntp.tencent.com"]),
        timeout_seconds=trusted_config.get("timeout_seconds", 3),
    )


_default_clock: TrustedClock | None = None


def get_default_clock() -> TrustedClock:
    """获取模块级默认可信时钟。"""
    global _default_clock
    if _default_clock is None:
        _default_clock = _create_default_clock()
    return _default_clock


def sync_now() -> datetime:
    """立即同步默认可信时钟。"""
    trusted_config = _load_config()
    if not trusted_config.get("enabled", True):
        return datetime.now()
    return get_default_clock().sync()


def trusted_now() -> datetime:
    """读取默认可信时钟的当前时间。"""
    trusted_config = _load_config()
    if not trusted_config.get("enabled", True):
        return datetime.now()
    return get_default_clock().now()


def is_available() -> bool:
    """默认可信时钟是否可用。"""
    trusted_config = _load_config()
    if not trusted_config.get("enabled", True):
        return True
    return get_default_clock().is_available()
