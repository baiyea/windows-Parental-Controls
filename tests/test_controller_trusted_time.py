import unittest
from unittest.mock import patch

import config
import core.controller as controller_module
from core.controller import ParentControl
from core.state_machine import AppEvent
from utils.trusted_time import TrustedTimeUnavailable


class FakeThread:
    def __init__(self, *args, **kwargs):
        self.daemon = kwargs.get("daemon", False)

    def start(self):
        return None


class ControllerTrustedTimeTest(unittest.TestCase):
    def setUp(self):
        self.original_config = config.g_config
        config.g_config = {
            "work_minutes": 30,
            "break_minutes": 30,
            "work_end_time": None,
            "break_end_time": None,
            "remind_before_minutes": 5,
            "auto_restart_after_lock": False,
            "restrict_night_hours": {
                "enabled": True,
                "start_hour": 21,
                "end_hour": 6,
            },
            "trusted_time": {
                "enabled": True,
                "servers": ["ntp.aliyun.com", "ntp.tencent.com"],
                "sync_interval_minutes": 10,
                "timeout_seconds": 3,
            },
        }

    def tearDown(self):
        config.g_config = self.original_config

    def test_start_locks_when_trusted_time_unavailable(self):
        control = ParentControl()
        events = []

        def fake_trigger(event, **kwargs):
            events.append((event, kwargs))
            return True

        with (
            patch.object(controller_module, "sync_now", side_effect=TrustedTimeUnavailable("offline"), create=True),
            patch.object(controller_module.threading, "Thread", FakeThread),
            patch.object(control, "_run_tray"),
            patch.object(control.state_machine, "trigger", side_effect=fake_trigger),
            patch.object(config, "save_config"),
        ):
            control.start()

        self.assertEqual(events[0][0], AppEvent.RESTORE_STATE)
        self.assertEqual(events[0][1]["remaining_seconds"], -1)
        self.assertTrue(events[0][1]["has_lock_state"])

    def test_now_raises_when_trusted_time_unavailable(self):
        control = ParentControl()

        with patch.object(
            controller_module,
            "trusted_now",
            side_effect=TrustedTimeUnavailable("offline"),
            create=True,
        ):
            with self.assertRaises(TrustedTimeUnavailable):
                control._now()


if __name__ == "__main__":
    unittest.main()
