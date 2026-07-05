import unittest
from datetime import datetime, timedelta

from utils.trusted_time import TrustedClock, TrustedTimeUnavailable


class FakeNtpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request_time(self, server, timeout):
        self.calls.append((server, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeMonotonic:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class TrustedClockTest(unittest.TestCase):
    def test_sync_uses_first_available_server(self):
        server_time = datetime(2026, 7, 5, 14, 30, 0)
        monotonic = FakeMonotonic(100.0)
        client = FakeNtpClient([OSError("down"), server_time])
        clock = TrustedClock(
            servers=["ntp.aliyun.com", "ntp.tencent.com"],
            client=client,
            monotonic=monotonic,
            timeout_seconds=2,
        )

        synced_time = clock.sync()

        self.assertEqual(synced_time, server_time)
        self.assertEqual(
            client.calls,
            [("ntp.aliyun.com", 2), ("ntp.tencent.com", 2)],
        )
        self.assertTrue(clock.is_available())

    def test_now_projects_from_monotonic_time(self):
        server_time = datetime(2026, 7, 5, 14, 30, 0)
        monotonic = FakeMonotonic(100.0)
        clock = TrustedClock(
            servers=["ntp.aliyun.com"],
            client=FakeNtpClient([server_time]),
            monotonic=monotonic,
        )
        clock.sync()

        monotonic.value = 165.5

        self.assertEqual(clock.now(), server_time + timedelta(seconds=65.5))

    def test_sync_raises_when_all_servers_fail(self):
        clock = TrustedClock(
            servers=["ntp.aliyun.com", "ntp.tencent.com"],
            client=FakeNtpClient([TimeoutError("timeout"), OSError("down")]),
            monotonic=FakeMonotonic(100.0),
        )

        with self.assertRaises(TrustedTimeUnavailable):
            clock.sync()

        self.assertFalse(clock.is_available())

    def test_now_raises_before_successful_sync(self):
        clock = TrustedClock(
            servers=["ntp.aliyun.com"],
            client=FakeNtpClient([]),
            monotonic=FakeMonotonic(100.0),
        )

        with self.assertRaises(TrustedTimeUnavailable):
            clock.now()


if __name__ == "__main__":
    unittest.main()
