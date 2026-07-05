import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import config
import core.controller as controller_module
from core.controller import ParentControl
from core.state_machine import AppEvent, AppState


class CapturingThread:
    created = []

    def __init__(self, *args, **kwargs):
        self.target = kwargs.get("target")
        self.args = kwargs.get("args", ())
        self.daemon = kwargs.get("daemon", False)
        CapturingThread.created.append(self)

    def start(self):
        return None


class FakeLockManager:
    def __init__(self):
        self.lock_screen = object()
        self.on_unlock_callback = None
        self.closed = False

    def close_lock(self):
        self.closed = True
        self.lock_screen = None


class FakeExitConfirm:
    def run(self):
        return True


class LockScreenFlowTest(unittest.TestCase):
    def setUp(self):
        self.original_config = config.g_config
        config.g_config = {
            "password": "0829",
            "work_minutes": 30,
            "break_minutes": 30,
            "work_end_time": None,
            "break_end_time": None,
            "remind_before_minutes": 5,
            "auto_restart_after_lock": False,
            "debug_mode": False,
            "restrict_night_hours": {
                "enabled": False,
                "start_hour": 21,
                "end_hour": 6,
                "password_unlock_grace_minutes": 30,
                "override_until": None,
            },
            "trusted_time": {
                "enabled": True,
                "servers": ["ntp.aliyun.com", "ntp.tencent.com"],
                "sync_interval_minutes": 10,
                "timeout_seconds": 3,
            },
        }
        CapturingThread.created = []

    def tearDown(self):
        config.g_config = self.original_config

    def test_normal_lock_screen_receives_break_countdown(self):
        now = datetime(2026, 7, 5, 14, 0, 0)
        control = ParentControl()

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(config, "save_config"),
            patch.object(controller_module.threading, "Thread", CapturingThread),
            patch.object(controller_module.winsound, "PlaySound"),
        ):
            control._lock_screen()

        self.assertEqual(CapturingThread.created[0].args, (False, 30 * 60))

    def test_debug_mode_enters_lock_state_without_showing_lock_screen(self):
        now = datetime(2026, 7, 5, 14, 0, 0)
        config.g_config["debug_mode"] = True
        control = ParentControl()

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(config, "save_config"),
            patch.object(controller_module.threading, "Thread", CapturingThread),
            patch.object(controller_module.notification, "notify") as notify_mock,
            patch.object(controller_module.winsound, "PlaySound"),
        ):
            control._lock_screen()

        self.assertEqual(CapturingThread.created, [])
        self.assertEqual(control.break_end_time, now + timedelta(minutes=30))
        notify_mock.assert_called_once()

    def test_break_time_transition_closes_lock_screen(self):
        now = datetime(2026, 7, 5, 14, 30, 0)
        control = ParentControl()
        fake_lock_manager = FakeLockManager()
        control.lock_manager = fake_lock_manager
        control.break_end_time = now
        control.state_machine.current_state = AppState.LOCKED

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(config, "save_config"),
        ):
            control.state_machine.trigger(AppEvent.BREAK_TIME_UP)

        self.assertTrue(fake_lock_manager.closed)
        self.assertEqual(control.state_machine.get_state(), AppState.WORKING)

    def test_start_restores_unfinished_work_timer(self):
        now = datetime(2026, 7, 5, 14, 0, 0)
        saved_work_end = now + timedelta(minutes=10)
        config.g_config["work_end_time"] = saved_work_end.strftime("%Y-%m-%d %H:%M:%S")

        control = ParentControl()

        with (
            patch.object(control, "_sync_trusted_time", return_value=now),
            patch.object(control, "_now", return_value=now),
            patch.object(control, "_run_tray"),
            patch.object(config, "save_config"),
            patch.object(controller_module.threading, "Thread", CapturingThread),
        ):
            control.start()

        self.assertEqual(control.state_machine.get_state(), AppState.WORKING)
        self.assertEqual(control.work_end_time, saved_work_end)

    def test_start_locks_when_saved_work_timer_expired(self):
        now = datetime(2026, 7, 5, 14, 0, 0)
        expired_work_end = now - timedelta(seconds=1)
        config.g_config["work_end_time"] = expired_work_end.strftime("%Y-%m-%d %H:%M:%S")

        control = ParentControl()

        with (
            patch.object(control, "_sync_trusted_time", return_value=now),
            patch.object(control, "_now", return_value=now),
            patch.object(control, "_run_tray"),
            patch.object(config, "save_config"),
            patch.object(controller_module.threading, "Thread", CapturingThread),
            patch.object(controller_module.winsound, "PlaySound"),
        ):
            control.start()

        self.assertEqual(control.state_machine.get_state(), AppState.LOCKED)
        self.assertEqual(control.break_end_time, now + timedelta(minutes=30))

    def test_night_password_unlock_sets_temporary_override(self):
        now = datetime(2026, 7, 5, 22, 0, 0)
        config.g_config["restrict_night_hours"]["enabled"] = True
        control = ParentControl()
        control.state_machine.current_state = AppState.LOCKED

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(config, "save_config") as save_mock,
        ):
            control._on_unlock_callback()

        self.assertEqual(control.state_machine.get_state(), AppState.WORKING)
        self.assertEqual(
            config.g_config["restrict_night_hours"]["override_until"],
            "2026-07-05 22:30:00",
        )
        save_mock.assert_called()

    def test_night_locked_exit_uses_password_confirmation(self):
        now = datetime(2026, 7, 5, 22, 0, 0)
        config.g_config["restrict_night_hours"]["enabled"] = True
        control = ParentControl()
        control.state_machine.current_state = AppState.LOCKED
        control.break_end_time = None

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(controller_module, "ExitConfirm", return_value=FakeExitConfirm()) as exit_confirm_mock,
            patch.object(controller_module.messagebox, "showwarning") as warning_mock,
        ):
            result = control.confirm_exit()

        self.assertTrue(result)
        exit_confirm_mock.assert_called_once()
        warning_mock.assert_not_called()

    def test_normal_break_locked_exit_still_blocked(self):
        now = datetime(2026, 7, 5, 14, 0, 0)
        control = ParentControl()
        control.state_machine.current_state = AppState.LOCKED
        control.break_end_time = now + timedelta(minutes=10)

        with (
            patch.object(control, "_now", return_value=now),
            patch.object(controller_module, "ExitConfirm") as exit_confirm_mock,
            patch.object(controller_module.messagebox, "showwarning") as warning_mock,
        ):
            result = control.confirm_exit()

        self.assertFalse(result)
        exit_confirm_mock.assert_not_called()
        warning_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
